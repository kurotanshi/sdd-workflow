"""Dependency-free Agent eval workspace preparation and trace collection."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
EVAL_SPEC_PATH = ROOT / "evals/eval-spec-v1.json"
SCENARIO_MANIFEST_PATH = ROOT / "evals/fixtures/MANIFEST.json"
RUNTIME = ROOT / "skills/sdd-workflow/scripts/sdd.py"
SKILL = ROOT / "skills/sdd-workflow/SKILL.md"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class EvalError(Exception):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvalError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise EvalError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def relative_path(root: Path, value: str) -> Path:
    candidate = root / value
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise EvalError(f"path escapes workspace: {value}")
    return candidate


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: float = 120,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def invoke_runtime(workspace: Path, arguments: list[str]) -> dict[str, Any]:
    completed = run_command(
        [
            sys.executable,
            str(RUNTIME),
            "--root",
            str(workspace),
            "--json",
            *arguments,
        ],
        cwd=workspace,
    )
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise EvalError(
            f"setup CLI did not emit JSON for {' '.join(arguments)}: "
            f"{completed.stderr or completed.stdout}"
        ) from error
    if completed.returncode != 0 or not document.get("ok"):
        raise EvalError(
            f"setup CLI failed for {' '.join(arguments)}: "
            f"{json.dumps(document, ensure_ascii=False)}"
        )
    return document


def apply_cli_setup(workspace: Path, action: dict[str, Any]) -> None:
    proposal = action["proposal"]
    command = action["command"]
    if command == "approve":
        status = invoke_runtime(workspace, ["status", proposal])["data"]
        invoke_runtime(
            workspace,
            [
                "approve",
                proposal,
                "--expected-snapshot",
                status["snapshot"]["snapshot_digest"],
            ],
        )
        return
    if command == "complete-all-tasks":
        while True:
            status = invoke_runtime(workspace, ["status", proposal])["data"]
            pending = [task for task in status["tasks"] if not task["completed"]]
            if not pending:
                return
            task = pending[0]
            invoke_runtime(
                workspace,
                [
                    "complete-task",
                    proposal,
                    str(task["ordinal"]),
                    "--expected-task-digest",
                    task["task_digest"],
                    "--expected-snapshot",
                    status["snapshot"]["snapshot_digest"],
                ],
            )
    raise EvalError(f"unsupported setup CLI command: {command}")


def apply_action(workspace: Path, action: dict[str, Any]) -> None:
    kind = action["kind"]
    if kind == "cli":
        apply_cli_setup(workspace, action)
        return
    if kind == "session_boundary":
        return
    if kind == "write_file":
        target = relative_path(workspace, action["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(action["content"], encoding="utf-8")
        return
    target = relative_path(workspace, action["path"])
    if kind == "replace_text":
        original = target.read_text(encoding="utf-8")
        if action["old"] not in original:
            raise EvalError(f"fault text is absent from {action['path']}")
        target.write_text(
            original.replace(action["old"], action["new"], 1),
            encoding="utf-8",
        )
        return
    if kind == "hide_path":
        if not target.exists():
            raise EvalError(f"cannot hide missing path: {action['path']}")
        target.rename(target.with_name(target.name + ".unavailable"))
        return
    if kind == "remove_path":
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        return
    raise EvalError(f"unsupported state action: {kind}")


def copy_repository(workspace: Path) -> None:
    ignored_names = {
        ".git",
        "eval-runs",
        "sdd",
        "__pycache__",
        ".DS_Store",
    }

    def ignore(_: str, names: list[str]) -> set[str]:
        return {name for name in names if name in ignored_names or name.endswith(".pyc")}

    shutil.copytree(ROOT, workspace, dirs_exist_ok=True, ignore=ignore)


def materialize_state(
    workspace: Path,
    scenario_id: str,
    recipes: dict[str, Any],
) -> None:
    recipe = recipes["recipes"][scenario_id]
    seed = recipe["seed"]
    kind = seed["kind"]
    if kind == "project_tree":
        shutil.copytree(
            ROOT / seed["source"],
            workspace,
            dirs_exist_ok=True,
        )
    elif kind == "archive_tree":
        destination = relative_path(workspace, seed["destination"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            ROOT / seed["source"],
            destination,
            dirs_exist_ok=True,
        )
    elif kind != "empty":
        raise EvalError(f"unsupported seed kind: {kind}")

    for action in recipe["setup"]:
        apply_action(workspace, action)
    for action in recipe["faults"]:
        apply_action(workspace, action)


def initialize_git(workspace: Path) -> str:
    commands = [
        ["git", "init", "-q"],
        ["git", "config", "user.name", "SDD Eval Harness"],
        ["git", "config", "user.email", "eval@example.invalid"],
        ["git", "add", "--all"],
        ["git", "commit", "-q", "-m", "eval baseline"],
    ]
    for command in commands:
        completed = run_command(command, cwd=workspace)
        if completed.returncode != 0:
            raise EvalError(
                f"git setup failed for {' '.join(command)}: {completed.stderr}"
            )
    completed = run_command(["git", "rev-parse", "HEAD"], cwd=workspace)
    if completed.returncode != 0:
        raise EvalError(f"cannot resolve eval baseline commit: {completed.stderr}")
    return completed.stdout.strip()


def copy_proposal_state(workspace: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    source = workspace / "sdd"
    if source.is_dir():
        shutil.copytree(source, destination / "sdd")
    else:
        (destination / ".absent").write_text("sdd directory absent\n", encoding="utf-8")


def load_scenario(scenario_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = read_json(SCENARIO_MANIFEST_PATH)
    entries = {
        entry["id"]: entry["path"]
        for entry in manifest["scenarios"]
    }
    if scenario_id not in entries:
        raise EvalError(f"unknown scenario: {scenario_id}")
    scenario = read_json(ROOT / entries[scenario_id])
    recipes = read_json(ROOT / manifest["state_recipes"])
    spec = read_json(EVAL_SPEC_PATH)
    return scenario, recipes, spec


def host_version(executable: str) -> str:
    try:
        completed = run_command([executable, "--version"], cwd=ROOT, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise EvalError(f"cannot run Agent host {executable}: {error}") from error
    if completed.returncode != 0:
        raise EvalError(f"Agent host version failed: {completed.stderr}")
    return (completed.stdout or completed.stderr).strip().splitlines()[0]


def build_agent_command(
    *,
    agent: str,
    executable: str,
    model: str,
    permission_mode: str,
    workspace: Path,
    prompt: str,
) -> list[str]:
    if agent == "codex":
        return [
            executable,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--sandbox",
            permission_mode,
            "--json",
            "--model",
            model,
            "--cd",
            str(workspace),
            prompt,
        ]
    if agent == "claude":
        return [
            executable,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--no-session-persistence",
            "--permission-mode",
            permission_mode,
            "--allowedTools",
            "Bash,Edit,Write,Read,Glob,Grep",
            "--model",
            model,
            prompt,
        ]
    raise EvalError(f"unsupported Agent host: {agent}")


def iter_json_lines(text: str) -> Iterable[dict[str, Any]]:
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            yield value


def nested_values(value: Any, key: str) -> Iterable[Any]:
    if isinstance(value, dict):
        for item_key, item_value in value.items():
            if item_key == key:
                yield item_value
            yield from nested_values(item_value, key)
    elif isinstance(value, list):
        for item in value:
            yield from nested_values(item, key)


def extract_trace(stdout: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, list[str]]:
    events = list(iter_json_lines(stdout))
    tool_events: list[dict[str, Any]] = []
    cli_events: list[dict[str, Any]] = []
    cli_event_indexes: dict[tuple[str, str], int] = {}
    transcript_parts: list[str] = []
    observed_models: set[str] = set()

    for event in events:
        serialized = json.dumps(event, ensure_ascii=False, sort_keys=True)
        lowered = serialized.lower()
        if any(
            marker in lowered
            for marker in (
                "tool_use",
                "tool_result",
                "command_execution",
                "function_call",
                "\"tool\"",
            )
        ):
            tool_events.append(event)
        commands = [
            value
            for value in nested_values(event, "command")
            if isinstance(value, str)
        ]
        cli_commands = [
            command
            for command in commands
            if ("sdd.py" in command or "scripts/sdd" in command)
            and re.search(
                r"\b(?:list|validate|status|approve|begin-revision|"
                r"complete-task|archive|abandon-preflight|abandon|doctor|"
                r"rebuild-index)\b",
                command,
            )
        ]
        event_id = next(
            (
                value
                for value in nested_values(event, "id")
                if isinstance(value, str) and value
            ),
            None,
        )
        for command in cli_commands:
            if event_id is None:
                cli_events.append(event)
                continue
            key = (event_id, command)
            if key in cli_event_indexes:
                cli_events[cli_event_indexes[key]] = event
            else:
                cli_event_indexes[key] = len(cli_events)
                cli_events.append(event)
        for model in nested_values(event, "model"):
            if isinstance(model, str) and model:
                observed_models.add(model)
        for usage in nested_values(event, "modelUsage"):
            if isinstance(usage, dict):
                observed_models.update(str(model) for model in usage)
        for item in nested_values(event, "text"):
            if isinstance(item, str) and item.strip():
                transcript_parts.append(item.strip())
        for item in nested_values(event, "result"):
            if isinstance(item, str) and item.strip():
                transcript_parts.append(item.strip())

    if not transcript_parts and stdout.strip():
        transcript_parts.append(stdout.strip())
    transcript = "\n\n".join(dict.fromkeys(transcript_parts))
    return tool_events, cli_events, transcript, sorted(observed_models)


def write_jsonl(path: Path, values: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def git_evidence(workspace: Path) -> tuple[str, list[str], list[str]]:
    intent = run_command(["git", "add", "-N", "--", "."], cwd=workspace)
    if intent.returncode != 0:
        raise EvalError(f"cannot stage intent-to-add evidence: {intent.stderr}")
    diff = run_command(["git", "diff", "--binary", "--no-ext-diff"], cwd=workspace)
    if diff.returncode != 0:
        raise EvalError(f"cannot collect Git diff: {diff.stderr}")
    status = run_command(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=workspace,
    )
    if status.returncode != 0:
        raise EvalError(f"cannot collect Git status: {status.stderr}")
    names = run_command(["git", "diff", "--name-only"], cwd=workspace)
    if names.returncode != 0:
        raise EvalError(f"cannot collect changed paths: {names.stderr}")
    return diff.stdout, status.stdout.splitlines(), names.stdout.splitlines()


def capture_cli_envelope(workspace: Path, arguments: list[str]) -> dict[str, Any]:
    completed = run_command(
        [
            sys.executable,
            str(RUNTIME),
            "--root",
            str(workspace),
            "--json",
            *arguments,
        ],
        cwd=workspace,
    )
    try:
        envelope = json.loads(completed.stdout)
    except json.JSONDecodeError:
        envelope = {
            "ok": False,
            "harness_error": completed.stderr or completed.stdout,
        }
    return {
        "exit_code": completed.returncode,
        "envelope": envelope,
    }


def final_state(
    workspace: Path,
    *,
    agent_exit_code: int | None,
    timed_out: bool,
    git_status: list[str],
    changed_paths: list[str],
) -> dict[str, Any]:
    archive_root = workspace / "sdd/archive"
    archives = (
        sorted(
            path.name
            for path in archive_root.iterdir()
            if path.is_dir()
        )
        if archive_root.is_dir()
        else []
    )
    product_changes = [
        path
        for path in changed_paths
        if path != "sdd" and not path.startswith("sdd/")
    ]
    changed_file_evidence: dict[str, Any] = {}
    for path in product_changes:
        candidate = relative_path(workspace, path)
        if not candidate.is_file():
            changed_file_evidence[path] = {"kind": "absent"}
            continue
        content = candidate.read_bytes()
        evidence: dict[str, Any] = {
            "kind": "file",
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        if len(content) <= 65536:
            try:
                evidence["utf8_text"] = content.decode("utf-8")
            except UnicodeDecodeError:
                pass
        changed_file_evidence[path] = evidence
    index = archive_root / "INDEX.md"
    return {
        "final_state_version": 1,
        "agent_exit_code": agent_exit_code,
        "timed_out": timed_out,
        "active_list": capture_cli_envelope(workspace, ["list", "--state", "active"]),
        "doctor": capture_cli_envelope(workspace, ["doctor"]),
        "archive_directories": archives,
        "archive_index": {
            "exists": index.is_file(),
            "sha256": sha256(index) if index.is_file() else None,
        },
        "git_status": git_status,
        "product_changes": product_changes,
        "changed_file_evidence": changed_file_evidence,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_version() -> dict[str, Any]:
    completed = run_command(
        [sys.executable, str(RUNTIME), "--json", "--version"],
        cwd=ROOT,
    )
    if completed.returncode != 0:
        raise EvalError(f"cannot read runtime version: {completed.stderr}")
    return json.loads(completed.stdout)["data"]


def git_head() -> str:
    completed = run_command(["git", "rev-parse", "HEAD"], cwd=ROOT)
    if completed.returncode != 0:
        raise EvalError(f"cannot read Skill commit: {completed.stderr}")
    return completed.stdout.strip()


def default_run_id() -> str:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one isolated Claude Code or Codex SDD eval scenario.",
    )
    parser.add_argument("--agent", choices=("codex", "claude"), required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--replaces-run-id")
    parser.add_argument("--agent-executable")
    parser.add_argument("--artifact-root", type=Path, default=ROOT / "eval-runs")
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--permission-mode")
    parser.add_argument("--keep-workspace", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    return parser


def execute(arguments: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    scenario, recipes, spec = load_scenario(arguments.scenario)
    run_id = arguments.run_id or default_run_id()
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise EvalError(f"invalid run id: {run_id}")
    if arguments.replaces_run_id and not RUN_ID_PATTERN.fullmatch(arguments.replaces_run_id):
        raise EvalError(f"invalid replacement run id: {arguments.replaces_run_id}")
    timeout_seconds = arguments.timeout_seconds or spec["run_policy"]["timeout_seconds"]
    if timeout_seconds <= 0:
        raise EvalError("timeout must be greater than zero")

    permission_mode = arguments.permission_mode
    if not permission_mode:
        permission_mode = "workspace-write" if arguments.agent == "codex" else "acceptEdits"
    executable = arguments.agent_executable or shutil.which(arguments.agent)
    if not executable:
        raise EvalError(f"Agent executable is unavailable: {arguments.agent}")

    artifact_root = arguments.artifact_root.resolve()
    run_directory = artifact_root / arguments.agent / arguments.scenario / run_id
    if run_directory.exists():
        raise EvalError(f"run artifact already exists: {run_directory}")
    run_directory.mkdir(parents=True)
    workspace_root = artifact_root / ".workspaces"
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace = Path(
        tempfile.mkdtemp(
            prefix=f"{arguments.agent}-{arguments.scenario}-",
            dir=workspace_root,
        )
    )

    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    agent_exit_code: int | None = None
    timed_out = False
    observed_models: list[str] = []
    raw_stdout = ""
    raw_stderr = ""
    command: list[str] = []

    try:
        copy_repository(workspace)
        materialize_state(workspace, arguments.scenario, recipes)
        copy_proposal_state(workspace, run_directory / "proposal-before")
        baseline_commit = initialize_git(workspace)

        prompt = (
            "You are running inside an isolated SDD workflow evaluation repository. "
            "Read skills/sdd-workflow/SKILL.md completely before acting and follow it. "
            "Use the bundled CLI for all authoritative proposal state. Work only in this "
            "repository and finish with a concise user-facing response.\n\n"
            "User request:\n"
            f"{scenario['user_input']['text']}\n"
        )
        (run_directory / "input.md").write_text(prompt, encoding="utf-8")
        executable_version = host_version(executable)
        command = build_agent_command(
            agent=arguments.agent,
            executable=executable,
            model=arguments.model,
            permission_mode=permission_mode,
            workspace=workspace,
            prompt=prompt,
        )
        metadata = {
            "run_metadata_version": 1,
            "run_id": run_id,
            "replaces_run_id": arguments.replaces_run_id,
            "agent": arguments.agent,
            "requested_model": arguments.model,
            "observed_models": [],
            "host_version": executable_version,
            "host_command": command[:-1] + ["<prompt>"],
            "skill_commit": git_head(),
            "skill_sha256": sha256(SKILL),
            "runtime": runtime_version(),
            "scenario_id": arguments.scenario,
            "scenario_version": scenario["scenario_version"],
            "scenario_sha256": sha256(
                ROOT / next(
                    entry["path"]
                    for entry in read_json(SCENARIO_MANIFEST_PATH)["scenarios"]
                    if entry["id"] == arguments.scenario
                )
            ),
            "scorer_version": scenario["scorer_version"],
            "eval_spec_version": spec["eval_spec_version"],
            "permission_mode": permission_mode,
            "sampling": {
                "temperature": None,
                "temperature_control_supported": False,
            },
            "execution_started_at": started_at,
            "execution_finished_at": None,
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python": platform.python_version(),
            },
            "workspace_baseline_commit": baseline_commit,
            "prepare_only": arguments.prepare_only,
        }
        write_json(run_directory / "run-metadata.json", metadata)

        if arguments.prepare_only:
            raw_stdout = ""
            raw_stderr = "prepare-only: Agent host was not invoked\n"
            agent_exit_code = None
        else:
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            try:
                completed = subprocess.run(
                    command,
                    cwd=workspace,
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds,
                    check=False,
                )
                agent_exit_code = completed.returncode
                raw_stdout = completed.stdout
                raw_stderr = completed.stderr
            except subprocess.TimeoutExpired as error:
                timed_out = True
                agent_exit_code = 124
                raw_stdout = error.stdout or ""
                raw_stderr = error.stderr or ""
                if isinstance(raw_stdout, bytes):
                    raw_stdout = raw_stdout.decode("utf-8", errors="replace")
                if isinstance(raw_stderr, bytes):
                    raw_stderr = raw_stderr.decode("utf-8", errors="replace")

        tool_events, cli_events, transcript, observed_models = extract_trace(raw_stdout)
        (run_directory / "agent-events.jsonl").write_text(raw_stdout, encoding="utf-8")
        (run_directory / "agent-stderr.log").write_text(raw_stderr, encoding="utf-8")
        write_jsonl(run_directory / "tool-calls.jsonl", tool_events)
        write_jsonl(run_directory / "cli-outputs.jsonl", cli_events)
        (run_directory / "transcript.md").write_text(
            (transcript or "(no Agent transcript captured)") + "\n",
            encoding="utf-8",
        )

        git_diff, git_status, changed_paths = git_evidence(workspace)
        (run_directory / "git-diff.patch").write_text(git_diff, encoding="utf-8")
        copy_proposal_state(workspace, run_directory / "proposal-after")
        write_json(
            run_directory / "final-state.json",
            final_state(
                workspace,
                agent_exit_code=agent_exit_code,
                timed_out=timed_out,
                git_status=git_status,
                changed_paths=changed_paths,
            ),
        )
        write_json(
            run_directory / "score.json",
            {
                "score_version": scenario["scorer_version"],
                "scenario_id": arguments.scenario,
                "status": "pending",
                "valid_run": False,
                "critical_violation": False,
            },
        )

        metadata["observed_models"] = observed_models
        metadata["execution_finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        metadata["agent_exit_code"] = agent_exit_code
        metadata["timed_out"] = timed_out
        write_json(run_directory / "run-metadata.json", metadata)
    finally:
        if not arguments.keep_workspace:
            shutil.rmtree(workspace, ignore_errors=True)

    ok = arguments.prepare_only or (agent_exit_code == 0 and not timed_out)
    result = {
        "ok": ok,
        "run_id": run_id,
        "agent": arguments.agent,
        "scenario_id": arguments.scenario,
        "artifact_directory": str(run_directory),
        "agent_exit_code": agent_exit_code,
        "timed_out": timed_out,
        "observed_models": observed_models,
    }
    return (0 if ok else 1), result


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        code, result = execute(arguments)
    except EvalError as error:
        print(
            json.dumps(
                {"ok": False, "error": str(error)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code
