"""Dependency-free runner for the paired Skill cost-benefit experiment."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import platform
import random
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

from agent_eval_lib import build_agent_command, host_version, iter_json_lines


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "evals/cost-benefit/experiment-v2.json"
DEFAULT_ARTIFACT_ROOT = ROOT / "eval-runs/cost-benefit-v2"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ENVIRONMENT_FAILURE_MARKERS = (
    "authentication",
    "authenticate",
    "unauthorized",
    "api key",
    "quota",
    "rate limit",
    "overloaded",
    "connection error",
    "network error",
    "provider error",
    "service unavailable",
)
NON_PRODUCT_PREFIXES = ("sdd/", "skills/")
NON_PRODUCT_PATHS = {".gitignore", "plan.md"}


class ExperimentError(Exception):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ExperimentError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise ExperimentError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def tree_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        relative = item.relative_to(path).as_posix().encode()
        content = item.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: float = 120,
    env: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        argv,
        cwd=cwd,
        input=input_bytes,
        capture_output=True,
        timeout=timeout,
        check=False,
        env=env,
        text=input_bytes is None,
    )


def variant_names(spec: dict[str, Any]) -> list[str]:
    variants = spec.get("variants", ["control", "skill"])
    if (
        not isinstance(variants, list)
        or len(variants) != 2
        or len(set(variants)) != 2
        or not all(isinstance(variant, str) and variant for variant in variants)
    ):
        raise ExperimentError("experiment must declare two distinct variants")
    return variants


def comparison_variants(spec: dict[str, Any]) -> tuple[str, str]:
    comparison = spec.get("comparison", {})
    baseline = comparison.get("baseline_variant", "control")
    candidate = comparison.get("candidate_variant", "skill")
    if {baseline, candidate} != set(variant_names(spec)):
        raise ExperimentError("comparison variants do not match experiment variants")
    return baseline, candidate


def source_for_variant(spec: dict[str, Any], variant: str) -> dict[str, Any]:
    sources = spec.get("sources")
    if sources is None:
        return spec["source"]
    if not isinstance(sources, dict) or set(sources) != set(variant_names(spec)):
        raise ExperimentError("per-variant sources do not match experiment variants")
    source = sources[variant]
    if not isinstance(source, dict):
        raise ExperimentError(f"invalid source for variant: {variant}")
    return source


def expand_isolation_environment(values: dict[str, str]) -> dict[str, str]:
    return {name: os.path.expanduser(value) for name, value in values.items()}


def extract_frozen_skill(
    workspace: Path,
    spec: dict[str, Any],
    variant: str = "skill",
) -> None:
    source = source_for_variant(spec, variant)
    if source.get("kind", "git") == "working-tree":
        package = ROOT / source["skill_path"]
        if tree_sha256(package) != source.get("package_tree_sha256"):
            raise ExperimentError("working-tree Skill package hash does not match")
        shutil.copytree(package, workspace / source["skill_path"])
    else:
        completed = subprocess.run(
            [
                "git",
                "archive",
                "--format=tar",
                source["commit"],
                source["skill_path"],
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ExperimentError(
                f"cannot extract frozen Skill: {completed.stderr.decode(errors='replace')}"
            )
        with tarfile.open(fileobj=io.BytesIO(completed.stdout), mode="r:") as archive:
            archive.extractall(workspace, filter="data")
    skill_file = workspace / source["skill_path"] / "SKILL.md"
    if sha256_file(skill_file) != source["skill_sha256"]:
        raise ExperimentError("frozen Skill SHA-256 does not match specification")
    if skill_file.stat().st_size != source["skill_bytes"]:
        raise ExperimentError("frozen Skill byte count does not match specification")
    if source.get("package_tree_sha256") and tree_sha256(
        workspace / source["skill_path"]
    ) != source["package_tree_sha256"]:
        raise ExperimentError("frozen Skill package hash does not match specification")


def initialize_workspace(
    workspace: Path,
    *,
    spec: dict[str, Any],
    task: dict[str, Any],
    variant: str,
) -> str:
    fixture = ROOT / task["fixture"] / "project"
    shutil.copytree(fixture, workspace, dirs_exist_ok=True)
    (workspace / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n/sdd/\n",
        encoding="utf-8",
    )
    (workspace / "sdd").mkdir()
    if variant != "control":
        extract_frozen_skill(workspace, spec, variant)
    commands = (
        ["git", "init", "-q"],
        ["git", "config", "user.name", "Cost Benefit Harness"],
        ["git", "config", "user.email", "cost-benefit@example.invalid"],
        ["git", "add", "--all"],
        ["git", "commit", "-q", "-m", "paired baseline"],
    )
    for command in commands:
        completed = run_command(command, cwd=workspace)
        if completed.returncode != 0:
            raise ExperimentError(
                f"workspace setup failed for {' '.join(command)}: {completed.stderr}"
            )
    completed = run_command(["git", "rev-parse", "HEAD"], cwd=workspace)
    if completed.returncode != 0:
        raise ExperimentError(f"cannot read workspace commit: {completed.stderr}")
    return completed.stdout.strip()


def copy_proposal_state(workspace: Path, destination: Path) -> None:
    source = workspace / "sdd"
    destination.mkdir()
    if source.is_dir():
        shutil.copytree(source, destination / "sdd")


def changed_paths(workspace: Path) -> list[str]:
    tracked = run_command(
        ["git", "diff", "--name-only", "HEAD", "--"],
        cwd=workspace,
    )
    untracked = run_command(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=workspace,
    )
    if tracked.returncode != 0 or untracked.returncode != 0:
        raise ExperimentError("cannot collect changed paths")
    return sorted(
        {
            path
            for path in tracked.stdout.splitlines() + untracked.stdout.splitlines()
            if path
        }
    )


def product_paths(paths: Iterable[str]) -> list[str]:
    return sorted(
        path
        for path in paths
        if path not in NON_PRODUCT_PATHS
        and not any(path.startswith(prefix) for prefix in NON_PRODUCT_PREFIXES)
    )


def create_workspace(agent: str, task: str, variant: str) -> Path:
    workspace = Path(
        tempfile.mkdtemp(prefix=f"{agent}-{task}-{variant}-")
    ).resolve()
    if workspace.is_relative_to(ROOT):
        raise ExperimentError(
            f"setup failure: workspace inside repository ancestry: {workspace}"
        )
    return workspace


def product_state(workspace: Path, paths: Iterable[str]) -> dict[str, str | None]:
    state: dict[str, str | None] = {}
    for path in paths:
        file = workspace / path
        state[path] = sha256_file(file) if file.is_file() else None
    return state


def mutated_product_paths(
    previous: dict[str, str | None],
    current: dict[str, str | None],
) -> list[str]:
    return sorted(
        path
        for path in set(previous) | set(current)
        if previous.get(path) != current.get(path)
    )


def git_diff(workspace: Path) -> str:
    intent = run_command(["git", "add", "-N", "--", "."], cwd=workspace)
    if intent.returncode != 0:
        raise ExperimentError(f"cannot stage intent-to-add: {intent.stderr}")
    completed = run_command(
        ["git", "diff", "--binary", "--no-ext-diff", "HEAD", "--"],
        cwd=workspace,
    )
    if completed.returncode != 0:
        raise ExperimentError(f"cannot collect Git diff: {completed.stderr}")
    return completed.stdout


def nested_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nested_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_dicts(child)


def tool_usage(events: list[dict[str, Any]]) -> tuple[int, dict[str, int]]:
    identities: set[tuple[str, str]] = set()
    counts: dict[str, int] = {}
    for event in events:
        if event.get("type") == "item.completed" and isinstance(event.get("item"), dict):
            item = event["item"]
            item_type = str(item.get("type", ""))
            if item_type in {
                "command_execution",
                "file_change",
                "mcp_tool_call",
                "web_search",
            }:
                identity = (str(item.get("id", id(item))), item_type)
                identities.add(identity)
                counts[item_type] = counts.get(item_type, 0) + 1
        for item in nested_dicts(event):
            if item.get("type") != "tool_use":
                continue
            name = str(item.get("name", "tool_use"))
            identity = (str(item.get("id", id(item))), name)
            if identity in identities:
                continue
            identities.add(identity)
            counts[name] = counts.get(name, 0) + 1
    return len(identities), dict(sorted(counts.items()))


RUNTIME_INVOCATION_MARKERS = ("discover-runtime.py", "sdd.py")


def runtime_invocations(events: list[dict[str, Any]]) -> tuple[int, int]:
    invocations = 0
    unidentified = 0
    seen: set[tuple[str, str]] = set()
    for event in events:
        if event.get("type") == "item.completed" and isinstance(event.get("item"), dict):
            item = event["item"]
            if str(item.get("type", "")) == "command_execution":
                identity = (str(item.get("id", id(item))), "command_execution")
                if identity not in seen:
                    seen.add(identity)
                    command = item.get("command")
                    if not isinstance(command, str):
                        unidentified += 1
                    elif any(
                        marker in command
                        for marker in RUNTIME_INVOCATION_MARKERS
                    ):
                        invocations += 1
        for item in nested_dicts(event):
            if item.get("type") != "tool_use" or item.get("name") != "Bash":
                continue
            identity = (str(item.get("id", id(item))), "tool_use")
            if identity in seen:
                continue
            seen.add(identity)
            command = (
                item["input"].get("command")
                if isinstance(item.get("input"), dict)
                else None
            )
            if not isinstance(command, str):
                unidentified += 1
            elif any(
                marker in command for marker in RUNTIME_INVOCATION_MARKERS
            ):
                invocations += 1
    return invocations, unidentified


def token_usage(events: list[dict[str, Any]], agent: str) -> dict[str, int]:
    candidates: list[dict[str, int]] = []
    keys = {
        "input_tokens",
        "cached_input_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "output_tokens",
    }
    for event in events:
        for item in nested_dicts(event):
            if not any(key in item for key in keys):
                continue
            usage = {
                key: int(item.get(key, 0))
                for key in keys
                if isinstance(item.get(key, 0), int)
            }
            if usage:
                candidates.append(usage)
    if not candidates:
        return {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
    usage = max(candidates, key=lambda value: sum(value.values()))
    normalized = {key: usage.get(key, 0) for key in keys}
    if agent == "codex":
        total = normalized["input_tokens"] + normalized["output_tokens"]
    else:
        total = (
            normalized["input_tokens"]
            + normalized["cache_creation_input_tokens"]
            + normalized["cache_read_input_tokens"]
            + normalized["output_tokens"]
        )
    normalized["total_tokens"] = total
    return normalized


def observed_models(events: list[dict[str, Any]]) -> list[str]:
    models: set[str] = set()
    for event in events:
        for item in nested_dicts(event):
            model = item.get("model")
            if isinstance(model, str) and model:
                models.add(model)
            model_usage = item.get("modelUsage")
            if isinstance(model_usage, dict):
                models.update(str(model) for model in model_usage)
    return sorted(models)


def prompt_for(
    spec: dict[str, Any],
    task: dict[str, Any],
    variant: str,
    turn_kind: str,
) -> str:
    key = f"{variant}_{turn_kind}"
    if key not in spec["prompts"] and variant != "control":
        key = f"skill_{turn_kind}"
    template = spec["prompts"][key]
    return template.format(
        requirement=task["requirement"],
        acceptance_change=task.get("acceptance_change", ""),
    )


def classify_invalid(
    *,
    returncode: int,
    timed_out: bool,
    stdout: str,
    stderr: str,
    events: list[dict[str, Any]],
) -> str | None:
    if timed_out:
        return "turn-timeout"
    error_evidence = [stderr]
    for event in events:
        event_type = event.get("type")
        if event_type == "result" and (
            event.get("is_error") is True or event.get("api_error_status")
        ):
            error_evidence.append(json.dumps(event, ensure_ascii=False))
        if event_type == "error":
            error_evidence.append(json.dumps(event, ensure_ascii=False))
        if event_type == "rate_limit_event":
            rate_limit = event.get("rate_limit_info")
            if isinstance(rate_limit, dict) and rate_limit.get("status") not in {
                None,
                "allowed",
            }:
                error_evidence.append(json.dumps(event, ensure_ascii=False))
    combined = "\n".join(error_evidence).lower()
    for marker in ENVIRONMENT_FAILURE_MARKERS:
        if marker in combined:
            return f"host-environment:{marker}"
    if stdout.strip() and not events:
        return "truncated-or-non-json-event-stream"
    if returncode != 0 and not stdout.strip():
        return "host-crash-without-terminal-result"
    return None


def run_public_and_oracle_tests(
    workspace: Path,
    *,
    task: dict[str, Any],
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    public = run_command(
        [sys.executable, "-m", "unittest", "discover", "-s", "."],
        cwd=workspace,
        env=environment,
    )
    oracle = ROOT / task["fixture"] / "oracle" / "test_oracle.py"
    oracle_environment = environment.copy()
    oracle_environment["PYTHONPATH"] = str(workspace)
    hidden = run_command(
        [sys.executable, str(oracle)],
        cwd=workspace,
        env=oracle_environment,
    )
    return {
        "public": {
            "exit_code": public.returncode,
            "stdout": public.stdout,
            "stderr": public.stderr,
        },
        "oracle": {
            "exit_code": hidden.returncode,
            "stdout": hidden.stdout,
            "stderr": hidden.stderr,
        },
    }


def default_run_id() -> str:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def execute_one(arguments: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    spec = read_json(arguments.spec)
    if arguments.task not in spec["tasks"]:
        raise ExperimentError(f"unknown task: {arguments.task}")
    if arguments.agent not in spec["agents"]:
        raise ExperimentError(f"unknown agent: {arguments.agent}")
    if arguments.variant not in variant_names(spec):
        raise ExperimentError(f"unknown variant: {arguments.variant}")
    run_id = arguments.run_id or default_run_id()
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ExperimentError(f"invalid run id: {run_id}")

    task = spec["tasks"][arguments.task]
    agent_spec = spec["agents"][arguments.agent]
    fixture_hash = tree_sha256(ROOT / task["fixture"])
    if fixture_hash != task["fixture_sha256"]:
        raise ExperimentError(
            f"fixture SHA-256 does not match specification: {arguments.task}"
        )
    artifact_root = arguments.artifact_root.resolve()
    run_directory = (
        artifact_root
        / arguments.agent
        / arguments.task
        / arguments.variant
        / run_id
    )
    if run_directory.exists():
        raise ExperimentError(f"run artifact already exists: {run_directory}")
    run_directory.mkdir(parents=True)
    workspace = create_workspace(
        arguments.agent, arguments.task, arguments.variant
    )

    executable = arguments.agent_executable or shutil.which(arguments.agent)
    if not executable:
        raise ExperimentError(f"Agent executable is unavailable: {arguments.agent}")
    executable_version = host_version(executable)
    if (
        arguments.agent_executable is None
        and agent_spec["host_version"] not in executable_version
    ):
        raise ExperimentError(
            f"host version mismatch for {arguments.agent}: {executable_version}"
        )
    timeout = arguments.timeout_seconds or spec["run_policy"]["timeout_seconds_per_turn"]
    isolation_environment = expand_isolation_environment(
        agent_spec.get("isolation_environment", {})
    )
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    invalid_reason: str | None = None
    turns: list[dict[str, Any]] = []
    preapproval_changes: list[dict[str, Any]] = []
    previous_product_state: dict[str, str | None] = {}
    total_tools = 0
    tool_counts: dict[str, int] = {}
    usage_totals: dict[str, int] = {}
    models: set[str] = set()
    wall_seconds = 0.0

    try:
        workspace_commit = initialize_workspace(
            workspace,
            spec=spec,
            task=task,
            variant=arguments.variant,
        )
        for index, turn_kind in enumerate(task["turn_sequence"], start=1):
            prompt = prompt_for(spec, task, arguments.variant, turn_kind)
            turn_directory = run_directory / f"turn-{index}-{turn_kind}"
            turn_directory.mkdir()
            (turn_directory / "prompt.md").write_text(prompt + "\n", encoding="utf-8")
            command = build_agent_command(
                agent=arguments.agent,
                executable=executable,
                model=agent_spec["model"],
                permission_mode=agent_spec["permission_mode"],
                workspace=workspace,
                prompt=prompt,
            )
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment.update(isolation_environment)
            before = time.monotonic()
            timed_out = False
            try:
                completed = subprocess.run(
                    command,
                    cwd=workspace,
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=timeout,
                    check=False,
                )
                stdout = completed.stdout
                stderr = completed.stderr
                returncode = completed.returncode
            except subprocess.TimeoutExpired as error:
                timed_out = True
                returncode = 124
                stdout = error.stdout or ""
                stderr = error.stderr or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", errors="replace")
            elapsed = time.monotonic() - before
            wall_seconds += elapsed
            (turn_directory / "events.jsonl").write_text(stdout, encoding="utf-8")
            (turn_directory / "stderr.log").write_text(stderr, encoding="utf-8")
            if arguments.variant == "control" and (
                "discover-runtime.py" in stdout or "sdd.py" in stdout
            ):
                raise ExperimentError(
                    "setup failure: SDD runtime invocation detected in "
                    f"control run {run_id} turn {index}"
                )
            events = list(iter_json_lines(stdout))
            tools, names = tool_usage(events)
            usage = token_usage(events, arguments.agent)
            invocations, unidentified = runtime_invocations(events)
            paths = changed_paths(workspace)
            products = product_paths(paths)
            current_product_state = product_state(workspace, products)
            mutated = mutated_product_paths(
                previous_product_state, current_product_state
            )
            previous_product_state = current_product_state
            (turn_directory / "git-diff.patch").write_text(
                git_diff(workspace),
                encoding="utf-8",
            )
            copy_proposal_state(workspace, turn_directory / "proposal-state")
            turn_result = {
                "turn": index,
                "kind": turn_kind,
                "returncode": returncode,
                "timed_out": timed_out,
                "wall_seconds": elapsed,
                "tool_calls": tools,
                "tool_calls_by_name": names,
                "tokens": usage,
                "runtime_invocations": invocations,
                "unidentified_command_events": unidentified,
                "changed_paths": paths,
                "product_paths": products,
            }
            write_json(turn_directory / "turn-result.json", turn_result)
            turns.append(turn_result)
            total_tools += tools
            for name, count in names.items():
                tool_counts[name] = tool_counts.get(name, 0) + count
            for key, count in usage.items():
                usage_totals[key] = usage_totals.get(key, 0) + count
            models.update(observed_models(events))

            if turn_kind in {"initial", "revision"} and mutated:
                preapproval_changes.append(
                    {
                        "kind": (
                            "product-change-before-approval"
                            if turn_kind == "initial"
                            else "product-change-after-requirement-change-before-reapproval"
                        ),
                        "turn": index,
                        "paths": mutated,
                    }
                )
            invalid_reason = classify_invalid(
                returncode=returncode,
                timed_out=timed_out,
                stdout=stdout,
                stderr=stderr,
                events=events,
            )
            if invalid_reason:
                break

        paths = changed_paths(workspace)
        products = product_paths(paths)
        allowed = set(task["allowed_product_paths"])
        scope_violations = sorted(path for path in products if path not in allowed)
        archive_root = workspace / "sdd/archive"
        premature_archive = archive_root.is_dir() and any(archive_root.iterdir())
        critical: list[dict[str, Any]] = list(preapproval_changes)
        if premature_archive:
            critical.append({"kind": "premature-archive"})
        tests = (
            run_public_and_oracle_tests(workspace, task=task)
            if invalid_reason is None
            else {
                "public": {"exit_code": None, "stdout": "", "stderr": "invalid run"},
                "oracle": {"exit_code": None, "stdout": "", "stderr": "invalid run"},
            }
        )
        task_success = (
            invalid_reason is None
            and tests["public"]["exit_code"] == 0
            and tests["oracle"]["exit_code"] == 0
        )
        final_diff = git_diff(workspace)
        (run_directory / "workspace-final.patch").write_text(
            final_diff,
            encoding="utf-8",
        )
        copy_proposal_state(workspace, run_directory / "proposal-final")
        metadata = {
            "result_schema": spec["metrics"]["result_schema"],
            "experiment_id": spec["experiment_id"],
            "spec_sha256": sha256_file(arguments.spec),
            "fixture_sha256": fixture_hash,
            "source": source_for_variant(spec, arguments.variant),
            "run_id": run_id,
            "pair_id": arguments.pair_id,
            "replicate": arguments.replicate,
            "attempt": arguments.attempt,
            "variant_order": arguments.variant_order,
            "agent": arguments.agent,
            "variant": arguments.variant,
            "task": arguments.task,
            "requested_model": agent_spec["model"],
            "observed_models": sorted(models),
            "host_version": executable_version,
            "host_isolation": isolation_environment,
            "permission_mode": agent_spec["permission_mode"],
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python": platform.python_version(),
            },
            "workspace_baseline_commit": workspace_commit,
            "started_at": started,
            "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "valid": invalid_reason is None,
            "invalid_reason": invalid_reason,
            "turns": turns,
            "metrics": {
                "turn_count": len(turns),
                "confirmation_turns": sum(
                    1 for kind in task["turn_sequence"] if kind == "approval"
                ),
                "tool_calls": total_tools,
                "tool_calls_by_name": dict(sorted(tool_counts.items())),
                "tokens": usage_totals,
                "wall_seconds": wall_seconds,
                "reported_queue_seconds": 0,
                "adjusted_wall_seconds": wall_seconds,
            },
            "safety": {
                "critical_violations": critical,
                "scope_violations": scope_violations,
                "premature_archive": premature_archive,
            },
            "tests": tests,
            "task_success": task_success,
            "acceptance_success": task_success,
            "final_changed_paths": paths,
            "final_product_paths": products,
        }
        write_json(run_directory / "result.json", metadata)
    finally:
        if arguments.keep_workspace:
            (run_directory / "workspace-path.txt").write_text(
                str(workspace) + "\n",
                encoding="utf-8",
            )
        else:
            shutil.rmtree(workspace, ignore_errors=True)

    result = {
        "ok": invalid_reason is None,
        "valid": invalid_reason is None,
        "invalid_reason": invalid_reason,
        "run_id": run_id,
        "artifact_directory": str(run_directory),
    }
    return (0 if invalid_reason is None else 1), result


def order_for(spec: dict[str, Any], agent: str, task: str, replicate: int) -> list[str]:
    material = (
        f"{spec['run_policy']['random_seed']}:{agent}:{task}:{replicate}".encode()
    )
    seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    variants = variant_names(spec).copy()
    random.Random(seed).shuffle(variants)
    return variants


def percentage_overhead(skill: float, control: float) -> float:
    if control == 0:
        return 0.0 if skill == 0 else float("inf")
    return ((skill - control) / control) * 100.0


def load_run_results(artifact_root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(artifact_root.rglob("result.json")):
        value = read_json(path)
        value["_artifact_path"] = str(path)
        results.append(value)
    return results


def aggregate_results(
    results: list[dict[str, Any]],
    spec: dict[str, Any],
    *,
    expected_spec_sha256: str,
) -> dict[str, Any]:
    baseline_variant, candidate_variant = comparison_variants(spec)
    mismatched = [
        {
            "run_id": result.get("run_id"),
            "experiment_id": result.get("experiment_id"),
            "spec_sha256": result.get("spec_sha256"),
            "artifact_path": result.get("_artifact_path"),
        }
        for result in results
        if result.get("experiment_id") != spec["experiment_id"]
        or result.get("spec_sha256") != expected_spec_sha256
    ]
    if mismatched:
        raise ExperimentError(
            "results do not belong to this experiment: "
            + json.dumps(mismatched, ensure_ascii=False, sort_keys=True)
        )
    valid = [result for result in results if result.get("valid") is True]
    invalid = [result for result in results if result.get("valid") is not True]
    by_pair: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = {}
    for result in valid:
        key = (result["agent"], result["task"], result["pair_id"])
        variants = by_pair.setdefault(key, {})
        variant = result["variant"]
        previous = variants.get(variant)
        if previous is None or result.get("attempt", 1) < previous.get("attempt", 1):
            variants[variant] = result

    pairs: list[dict[str, Any]] = []
    incomplete_pairs: list[dict[str, Any]] = []
    for (agent, task, pair_id), variants in sorted(by_pair.items()):
        if set(variants) != {baseline_variant, candidate_variant}:
            incomplete_pairs.append(
                {
                    "agent": agent,
                    "task": task,
                    "pair_id": pair_id,
                    "present_variants": sorted(variants),
                }
            )
            continue
        baseline = variants[baseline_variant]
        candidate = variants[candidate_variant]
        if baseline.get("host_isolation") != candidate.get("host_isolation") or (
            baseline.get("host_version") != candidate.get("host_version")
        ):
            raise ExperimentError(
                f"setup failure: host baseline mismatch in pair {pair_id}"
            )
        baseline_metrics = baseline["metrics"]
        candidate_metrics = candidate["metrics"]
        pair = {
            "agent": agent,
            "task": task,
            "pair_id": pair_id,
            "replicate": candidate["replicate"],
            "baseline_variant": baseline_variant,
            "candidate_variant": candidate_variant,
            "baseline_success": bool(baseline["task_success"]),
            "candidate_success": bool(candidate["task_success"]),
            "baseline_critical": len(
                baseline["safety"].get("critical_violations", [])
            ),
            "candidate_critical": len(
                candidate["safety"].get("critical_violations", [])
            ),
            "baseline_tool_calls": baseline_metrics["tool_calls"],
            "candidate_tool_calls": candidate_metrics["tool_calls"],
            "baseline_tokens": baseline_metrics["tokens"]["total_tokens"],
            "candidate_tokens": candidate_metrics["tokens"]["total_tokens"],
            "baseline_wall_seconds": baseline_metrics["adjusted_wall_seconds"],
            "candidate_wall_seconds": candidate_metrics["adjusted_wall_seconds"],
            "additional_tool_calls": (
                candidate_metrics["tool_calls"] - baseline_metrics["tool_calls"]
            ),
            "token_overhead_percent": percentage_overhead(
                candidate_metrics["tokens"]["total_tokens"],
                baseline_metrics["tokens"]["total_tokens"],
            ),
            "wall_overhead_percent": percentage_overhead(
                candidate_metrics["adjusted_wall_seconds"],
                baseline_metrics["adjusted_wall_seconds"],
            ),
        }
        pair["control_success"] = pair["baseline_success"]
        pair["skill_success"] = pair["candidate_success"]
        pair["control_critical"] = pair["baseline_critical"]
        pair["skill_critical"] = pair["candidate_critical"]
        pair["prevented_critical"] = (
            pair["baseline_critical"] > 0 and pair["candidate_critical"] == 0
        )
        pairs.append(pair)

    cells: list[dict[str, Any]] = []
    for agent in spec["agents"]:
        for task in spec["task_order"]:
            cell_pairs = [
                pair
                for pair in pairs
                if pair["agent"] == agent and pair["task"] == task
            ]
            if not cell_pairs:
                continue
            cell = {
                "agent": agent,
                "task": task,
                "pair_count": len(cell_pairs),
                "median_additional_tool_calls": statistics.median(
                    pair["additional_tool_calls"] for pair in cell_pairs
                ),
                "median_token_overhead_percent": statistics.median(
                    pair["token_overhead_percent"] for pair in cell_pairs
                ),
                "median_wall_overhead_percent": statistics.median(
                    pair["wall_overhead_percent"] for pair in cell_pairs
                ),
                "control_successes": sum(
                    pair["control_success"] for pair in cell_pairs
                ),
                "skill_successes": sum(pair["skill_success"] for pair in cell_pairs),
                "skill_critical_violations": sum(
                    pair["skill_critical"] for pair in cell_pairs
                ),
            }
            cell["baseline_successes"] = cell["control_successes"]
            cell["candidate_successes"] = cell["skill_successes"]
            cell["candidate_critical_violations"] = cell[
                "skill_critical_violations"
            ]
            cell["median_baseline_tool_calls"] = statistics.median(
                pair["baseline_tool_calls"] for pair in cell_pairs
            )
            cell["median_candidate_tool_calls"] = statistics.median(
                pair["candidate_tool_calls"] for pair in cell_pairs
            )
            cell["median_baseline_tokens"] = statistics.median(
                pair["baseline_tokens"] for pair in cell_pairs
            )
            cell["median_candidate_tokens"] = statistics.median(
                pair["candidate_tokens"] for pair in cell_pairs
            )
            cell["median_baseline_wall_seconds"] = statistics.median(
                pair["baseline_wall_seconds"] for pair in cell_pairs
            )
            cell["median_candidate_wall_seconds"] = statistics.median(
                pair["candidate_wall_seconds"] for pair in cell_pairs
            )
            cell["median_candidate_token_overhead_percent"] = percentage_overhead(
                cell["median_candidate_tokens"], cell["median_baseline_tokens"]
            )
            cell["median_candidate_wall_overhead_percent"] = percentage_overhead(
                cell["median_candidate_wall_seconds"],
                cell["median_baseline_wall_seconds"],
            )
            cell["median_tool_calls_decreased"] = (
                cell["median_candidate_tool_calls"]
                < cell["median_baseline_tool_calls"]
            )
            thresholds = spec["thresholds"]
            cell["cost_threshold_exceeded"] = (
                cell["median_additional_tool_calls"]
                > thresholds["additional_tool_calls_per_completed_task_max"]
                or cell["median_token_overhead_percent"]
                > thresholds["token_overhead_percent_max"]
                or cell["median_wall_overhead_percent"]
                > thresholds["wall_time_overhead_percent_max"]
            )
            cells.append(cell)

    phase_groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for result in valid:
        for turn in result.get("turns", []):
            key = (
                result["agent"],
                result["task"],
                result["variant"],
                f"turn-{turn['turn']}-{turn['kind']}",
            )
            phase_groups.setdefault(key, []).append(turn)
    phases = [
        {
            "agent": agent,
            "task": task,
            "variant": variant,
            "phase": phase,
            "run_count": len(group),
            "median_runtime_invocations": statistics.median(
                turn.get("runtime_invocations", 0) for turn in group
            ),
            "median_tool_calls": statistics.median(
                turn["tool_calls"] for turn in group
            ),
            "median_total_tokens": statistics.median(
                turn["tokens"].get("total_tokens", 0) for turn in group
            ),
            "median_wall_seconds": statistics.median(
                turn["wall_seconds"] for turn in group
            ),
            "unidentified_command_events": sum(
                turn.get("unidentified_command_events", 0) for turn in group
            ),
        }
        for (agent, task, variant, phase), group in sorted(phase_groups.items())
    ]
    phase_rows = {
        (row["agent"], row["task"], row["phase"], row["variant"]): row
        for row in phases
    }
    phase_deltas: list[dict[str, Any]] = []
    for agent in spec["agents"]:
        for task in spec["task_order"]:
            for index, kind in enumerate(spec["tasks"][task]["turn_sequence"], start=1):
                phase = f"turn-{index}-{kind}"
                baseline = phase_rows.get((agent, task, phase, baseline_variant))
                candidate = phase_rows.get((agent, task, phase, candidate_variant))
                if baseline is None or candidate is None:
                    continue
                phase_deltas.append(
                    {
                        "agent": agent,
                        "task": task,
                        "phase": phase,
                        "baseline_variant": baseline_variant,
                        "candidate_variant": candidate_variant,
                        "baseline_median_runtime_invocations": baseline[
                            "median_runtime_invocations"
                        ],
                        "candidate_median_runtime_invocations": candidate[
                            "median_runtime_invocations"
                        ],
                        "delta": candidate["median_runtime_invocations"]
                        - baseline["median_runtime_invocations"],
                    }
                )

    thresholds = spec["thresholds"]
    complete = (
        len(pairs)
        == len(spec["agents"])
        * len(spec["tasks"])
        * spec["run_policy"]["replicates_per_cell"]
        and not incomplete_pairs
    )
    skill_critical = sum(pair["candidate_critical"] for pair in pairs)
    control_success = sum(pair["baseline_success"] for pair in pairs)
    skill_success = sum(pair["candidate_success"] for pair in pairs)
    calls_pass = all(
        cell["median_additional_tool_calls"]
        <= thresholds["additional_tool_calls_per_completed_task_max"]
        for cell in cells
    )
    tokens_pass = all(
        cell["median_token_overhead_percent"]
        <= thresholds["token_overhead_percent_max"]
        for cell in cells
    )
    wall_passing_by_agent = {
        agent: sum(
            cell["median_wall_overhead_percent"]
            <= thresholds["wall_time_overhead_percent_max"]
            for cell in cells
            if cell["agent"] == agent
        )
        for agent in spec["agents"]
    }
    wall_pass = all(
        count >= thresholds["wall_time_task_types_passing_min_per_agent"]
        for count in wall_passing_by_agent.values()
    )
    jointly_exceeded_tasks = [
        task
        for task in spec["task_order"]
        if all(
            any(
                cell["agent"] == agent
                and cell["task"] == task
                and cell["cost_threshold_exceeded"]
                for cell in cells
            )
            for agent in spec["agents"]
        )
    ]
    gate2_eligible = (
        complete
        and len(jointly_exceeded_tasks)
        >= thresholds["runtime_entry_task_types_min"]
    )
    candidate_criteria = spec.get("keep_or_cut", {}).get("criteria", {})
    expected_phase_count = sum(
        len(spec["tasks"][task]["turn_sequence"])
        for task in spec["task_order"]
    ) * len(spec["agents"])
    registered_delta = candidate_criteria.get(
        "runtime_invocations_per_phase_delta_exact"
    )
    phase_delta_pass = (
        len(phase_deltas) == expected_phase_count
        and registered_delta is not None
        and all(row["delta"] == registered_delta for row in phase_deltas)
    )
    token_limit = candidate_criteria.get("cell_token_overhead_percent_max")
    wall_limit = candidate_criteria.get("cell_wall_overhead_percent_max")
    tool_cells_min = candidate_criteria.get("tool_call_decrease_cells_min")
    candidate_tokens_pass = token_limit is not None and all(
        cell["median_candidate_token_overhead_percent"] <= token_limit
        for cell in cells
    )
    candidate_wall_pass = wall_limit is not None and all(
        cell["median_candidate_wall_overhead_percent"] <= wall_limit
        for cell in cells
    )
    tool_decrease_cells = sum(
        cell["median_tool_calls_decreased"] for cell in cells
    )
    candidate_tools_pass = (
        tool_cells_min is not None and tool_decrease_cells >= tool_cells_min
    )
    candidate_measurement_pass = (
        complete
        and skill_critical
        <= candidate_criteria.get("candidate_critical_violations_max", -1)
        and skill_success >= control_success
        and phase_delta_pass
        and candidate_tokens_pass
        and candidate_wall_pass
        and candidate_tools_pass
    )
    return {
        "experiment_id": spec["experiment_id"],
        "complete": complete,
        "result_count": len(results),
        "valid_result_count": len(valid),
        "invalid_result_count": len(invalid),
        "invalid_runs": [
            {
                "run_id": result.get("run_id"),
                "invalid_reason": result.get("invalid_reason"),
                "artifact_path": result.get("_artifact_path"),
            }
            for result in invalid
        ],
        "incomplete_pairs": incomplete_pairs,
        "pairs": pairs,
        "cells": cells,
        "phases": phases,
        "phase_runtime_invocation_deltas": phase_deltas,
        "decision": {
            "baseline_variant": baseline_variant,
            "candidate_variant": candidate_variant,
            "candidate_critical_violations": skill_critical,
            "baseline_successes": control_success,
            "candidate_successes": skill_success,
            "candidate_phase_delta_pass": phase_delta_pass,
            "candidate_tokens_pass": candidate_tokens_pass,
            "candidate_wall_time_pass": candidate_wall_pass,
            "candidate_tool_calls_pass": candidate_tools_pass,
            "candidate_tool_call_decrease_cells": tool_decrease_cells,
            "candidate_measurement_pass": candidate_measurement_pass,
            "skill_critical_violations": skill_critical,
            "control_successes": control_success,
            "skill_successes": skill_success,
            "critical_pass": skill_critical
            <= thresholds["critical_violations_max"],
            "success_pass": skill_success >= control_success,
            "tool_calls_pass": calls_pass,
            "tokens_pass": tokens_pass,
            "wall_time_pass": wall_pass,
            "wall_passing_task_types_by_agent": wall_passing_by_agent,
            "runtime_acceptable": (
                complete
                and skill_critical <= thresholds["critical_violations_max"]
                and skill_success >= control_success
                and calls_pass
                and tokens_pass
                and wall_pass
            ),
            "jointly_exceeded_task_types": jointly_exceeded_tasks,
            "gate2_eligible": gate2_eligible,
            "prevented_critical_pairs": sum(
                pair["prevented_critical"] for pair in pairs
            ),
        },
    }


def execute_matrix(arguments: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    spec = read_json(arguments.spec)
    agents = arguments.agents or list(spec["agents"])
    tasks = arguments.tasks or spec["task_order"]
    replicates = arguments.replicates or spec["run_policy"]["replicates_per_cell"]
    max_attempts = spec["run_policy"]["retry_invalid_attempts"]
    completed: list[str] = []
    invalid: list[str] = []
    for agent in agents:
        for task in tasks:
            for replicate in range(1, replicates + 1):
                order = order_for(spec, agent, task, replicate)
                pair_id = f"{agent}-{task}-p{replicate}"
                for variant in order:
                    for attempt in range(1, max_attempts + 1):
                        run_id = f"{pair_id}-{variant}-a{attempt}"
                        run_directory = (
                            arguments.artifact_root.resolve()
                            / agent
                            / task
                            / variant
                            / run_id
                        )
                        result_path = run_directory / "result.json"
                        if result_path.is_file():
                            existing = read_json(result_path)
                            if existing.get("valid"):
                                completed.append(run_id)
                                break
                            if attempt < max_attempts:
                                continue
                            invalid.append(run_id)
                            break
                        run_arguments = argparse.Namespace(
                            spec=arguments.spec,
                            agent=agent,
                            task=task,
                            variant=variant,
                            run_id=run_id,
                            pair_id=pair_id,
                            replicate=replicate,
                            attempt=attempt,
                            variant_order=order,
                            artifact_root=arguments.artifact_root,
                            timeout_seconds=arguments.timeout_seconds,
                            agent_executable=None,
                            keep_workspace=arguments.keep_workspace,
                        )
                        code, result = execute_one(run_arguments)
                        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
                        if code == 0:
                            completed.append(run_id)
                            break
                        if attempt == max_attempts:
                            invalid.append(run_id)
                    if invalid:
                        return 1, {
                            "ok": False,
                            "completed": completed,
                            "invalid": invalid,
                        }
    return 0, {"ok": True, "completed": completed, "invalid": invalid}


def execute_summarize(arguments: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    spec = read_json(arguments.spec)
    summary = aggregate_results(
        load_run_results(arguments.artifact_root),
        spec,
        expected_spec_sha256=sha256_file(arguments.spec),
    )
    if arguments.json_output:
        arguments.json_output.parent.mkdir(parents=True, exist_ok=True)
        write_json(arguments.json_output, summary)
    return (0 if summary["complete"] else 1), summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run paired Skill cost-benefit experiments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--spec", type=Path, default=SPEC_PATH)
    run_parser.add_argument("--agent", choices=("codex", "claude"), required=True)
    run_parser.add_argument(
        "--task",
        choices=("small-bug", "medium-feature", "acceptance-change"),
        required=True,
    )
    run_parser.add_argument("--variant", required=True)
    run_parser.add_argument("--run-id")
    run_parser.add_argument("--pair-id", default="manual")
    run_parser.add_argument("--replicate", type=int, default=0)
    run_parser.add_argument("--attempt", type=int, default=1)
    run_parser.add_argument("--variant-order", nargs="+", default=["control", "skill"])
    run_parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    run_parser.add_argument("--timeout-seconds", type=float)
    run_parser.add_argument("--agent-executable")
    run_parser.add_argument("--keep-workspace", action="store_true")

    matrix_parser = subparsers.add_parser("matrix")
    matrix_parser.add_argument("--spec", type=Path, default=SPEC_PATH)
    matrix_parser.add_argument("--agents", nargs="+", choices=("codex", "claude"))
    matrix_parser.add_argument(
        "--tasks",
        nargs="+",
        choices=("small-bug", "medium-feature", "acceptance-change"),
    )
    matrix_parser.add_argument("--replicates", type=int)
    matrix_parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
    )
    matrix_parser.add_argument("--timeout-seconds", type=float)
    matrix_parser.add_argument("--keep-workspace", action="store_true")

    summary_parser = subparsers.add_parser("summarize")
    summary_parser.add_argument("--spec", type=Path, default=SPEC_PATH)
    summary_parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
    )
    summary_parser.add_argument("--json-output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "run":
            code, result = execute_one(arguments)
        elif arguments.command == "matrix":
            code, result = execute_matrix(arguments)
        else:
            code, result = execute_summarize(arguments)
    except (ExperimentError, OSError, subprocess.TimeoutExpired) as error:
        print(
            json.dumps(
                {"ok": False, "error": str(error)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    if arguments.command in {"matrix", "summarize"} or code != 0:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
