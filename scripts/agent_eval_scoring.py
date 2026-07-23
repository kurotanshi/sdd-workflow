"""Rule-based scoring and aggregate summaries for Agent eval artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
EVAL_SPEC_PATH = ROOT / "evals/eval-spec-v1.json"
SCENARIO_MANIFEST_PATH = ROOT / "evals/fixtures/MANIFEST.json"
SCORING_RULES_PATH = ROOT / "evals/scoring-rules-v1.json"


class ScoringError(Exception):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ScoringError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise ScoringError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def scenario_paths() -> dict[str, Path]:
    manifest = read_json(SCENARIO_MANIFEST_PATH)
    return {
        entry["id"]: ROOT / entry["path"]
        for entry in manifest["scenarios"]
    }


def stable_tree(directory: Path) -> dict[str, str]:
    if not directory.is_dir():
        return {}
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.name != ".DS_Store"
    }


def read_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line]


class Evidence:
    def __init__(self, run_directory: Path, final_state: dict[str, Any]) -> None:
        self.run_directory = run_directory
        self.final_state = final_state
        self.transcript = self._text("transcript.md")
        self.tool_lines = read_lines(run_directory / "tool-calls.jsonl")
        self.cli_lines = read_lines(run_directory / "cli-outputs.jsonl")
        self.agent_lines = read_lines(run_directory / "agent-events.jsonl")
        self.git_diff = self._text("git-diff.patch")

    def _text(self, name: str) -> str:
        path = self.run_directory / name
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def source(self, name: str) -> str:
        sources = {
            "transcript": self.transcript,
            "tool_trace": "\n".join(self.tool_lines),
            "cli_trace": "\n".join(self.cli_lines),
            "git_diff": self.git_diff,
        }
        if name not in sources:
            raise ScoringError(f"unknown evidence source: {name}")
        return sources[name]

    def command_lines(self) -> list[str]:
        return self.cli_lines

    def ordered_trace(self) -> str:
        return "\n".join(self.agent_lines or self.cli_lines or self.tool_lines)

    def active_candidates(self) -> list[dict[str, Any]]:
        active = self.final_state.get("active_list", {})
        envelope = active.get("envelope", {}) if isinstance(active, dict) else {}
        data = envelope.get("data", {}) if isinstance(envelope, dict) else {}
        candidates = data.get("candidates", []) if isinstance(data, dict) else []
        return [item for item in candidates if isinstance(item, dict)]

    def active_candidate(self, short_name: str) -> dict[str, Any] | None:
        return next(
            (
                candidate
                for candidate in self.active_candidates()
                if candidate.get("short_name") == short_name
            ),
            None,
        )


def compare_number(actual: int, predicate: dict[str, Any]) -> bool:
    if "equals" in predicate and actual != predicate["equals"]:
        return False
    if "minimum" in predicate and actual < predicate["minimum"]:
        return False
    if "maximum" in predicate and actual > predicate["maximum"]:
        return False
    return True


def regex(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, re.IGNORECASE | re.DOTALL)
    except re.error as error:
        raise ScoringError(f"invalid scorer regex {pattern!r}: {error}") from error


def evaluate_predicate(predicate: dict[str, Any], evidence: Evidence) -> tuple[bool, Any]:
    op = predicate.get("op")
    if op == "all":
        results = [
            evaluate_predicate(item, evidence)
            for item in predicate.get("predicates", [])
        ]
        return all(result[0] for result in results), [result[1] for result in results]
    if op == "not":
        passed, detail = evaluate_predicate(predicate["predicate"], evidence)
        return not passed, {"negated": detail}
    if op == "text-regex":
        source = predicate["source"]
        matched = bool(regex(predicate["pattern"]).search(evidence.source(source)))
        return matched, {"source": source, "matched": matched}
    if op == "command-count":
        compiled = regex(predicate["pattern"])
        count = sum(bool(compiled.search(line)) for line in evidence.command_lines())
        return compare_number(count, predicate), {"count": count}
    if op == "trace-order":
        trace = evidence.ordered_trace()
        cursor = 0
        offsets: list[int] = []
        for pattern in predicate.get("patterns", []):
            match = regex(pattern).search(trace[cursor:])
            if match is None:
                return False, {"offsets": offsets, "missing": pattern}
            cursor += match.end()
            offsets.append(cursor)
        return True, {"offsets": offsets}
    if op == "tool-event-count":
        count = len(evidence.tool_lines)
        return compare_number(count, predicate), {"count": count}
    if op == "product-change-count":
        changes = evidence.final_state.get("product_changes", [])
        count = len(changes) if isinstance(changes, list) else 0
        return compare_number(count, predicate), {"count": count}
    if op == "product-file-text":
        files = evidence.final_state.get("changed_file_evidence", {})
        item = files.get(predicate["path"], {}) if isinstance(files, dict) else {}
        actual = item.get("utf8_text") if isinstance(item, dict) else None
        passed = actual == predicate["equals"]
        return passed, {"path": predicate["path"], "matched": passed}
    if op == "single-active-status":
        candidates = evidence.active_candidates()
        passed = len(candidates) == 1 and candidates[0].get("status") == predicate["status"]
        return passed, {
            "candidate_count": len(candidates),
            "status": candidates[0].get("status") if len(candidates) == 1 else None,
        }
    if op == "active-candidate-count":
        count = len(evidence.active_candidates())
        return compare_number(count, predicate), {"count": count}
    if op == "active-status":
        candidate = evidence.active_candidate(predicate["proposal"])
        actual = candidate.get("status") if candidate else None
        return actual == predicate["status"], {"status": actual}
    if op == "active-all-tasks-complete":
        candidate = evidence.active_candidate(predicate["proposal"])
        completed = candidate.get("completed_count") if candidate else None
        total = candidate.get("task_count") if candidate else None
        passed = (
            isinstance(completed, int)
            and isinstance(total, int)
            and total > 0
            and completed == total
        )
        return passed, {"completed": completed, "total": total}
    if op == "active-task-counts":
        candidate = evidence.active_candidate(predicate["proposal"])
        completed = candidate.get("completed_count") if candidate else None
        total = candidate.get("task_count") if candidate else None
        passed = completed == predicate["completed"] and total == predicate["total"]
        return passed, {"completed": completed, "total": total}
    if op == "proposal-tree-equal":
        before = stable_tree(evidence.run_directory / "proposal-before")
        after = stable_tree(evidence.run_directory / "proposal-after")
        return before == after, {
            "before_files": len(before),
            "after_files": len(after),
        }
    if op == "proposal-after-regex":
        relative = Path(predicate["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ScoringError(f"unsafe proposal evidence path: {relative}")
        path = evidence.run_directory / "proposal-after" / relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        matched = bool(regex(predicate["pattern"]).search(text))
        return matched, {"path": str(relative), "matched": matched}
    if op in {"archive-matches", "archive-not-matches"}:
        archives = evidence.final_state.get("archive_directories", [])
        values = archives if isinstance(archives, list) else []
        matched = any(regex(predicate["pattern"]).search(str(item)) for item in values)
        passed = matched if op == "archive-matches" else not matched
        return passed, {"matched": matched, "archive_count": len(values)}
    if op == "archive-index-exists":
        index = evidence.final_state.get("archive_index", {})
        exists = bool(index.get("exists")) if isinstance(index, dict) else False
        return exists, {"exists": exists}
    if op == "doctor-healthy":
        doctor = evidence.final_state.get("doctor", {})
        envelope = doctor.get("envelope", {}) if isinstance(doctor, dict) else {}
        data = envelope.get("data", {}) if isinstance(envelope, dict) else {}
        healthy = bool(data.get("healthy")) if isinstance(data, dict) else False
        return healthy, {"healthy": healthy}
    raise ScoringError(f"unknown scorer operation: {op}")


def invalid_reasons(
    run_directory: Path,
    metadata: dict[str, Any],
    scenario: dict[str, Any],
    spec: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    for name in spec["artifact_layout"]["required_files"]:
        if not (run_directory / name).exists():
            reasons.append(f"missing_artifact:{name}")
    required_metadata = (
        "run_id",
        "agent",
        "requested_model",
        "host_version",
        "skill_commit",
        "skill_sha256",
        "runtime",
        "scenario_id",
        "scenario_version",
        "scorer_version",
        "eval_spec_version",
        "permission_mode",
        "execution_started_at",
        "execution_finished_at",
        "platform",
        "agent_exit_code",
        "timed_out",
    )
    for key in required_metadata:
        if metadata.get(key) in (None, "", {}):
            reasons.append(f"incomplete_metadata:{key}")
    if metadata.get("prepare_only"):
        reasons.append("prepare_only")
    if metadata.get("timed_out"):
        reasons.append("timeout")
    if metadata.get("agent_exit_code") != 0:
        reasons.append("agent_host_failure")
    if metadata.get("scenario_id") != scenario.get("scenario_id"):
        reasons.append("scenario_id_mismatch")
    if metadata.get("scenario_version") != scenario.get("scenario_version"):
        reasons.append("scenario_version_mismatch")
    if metadata.get("scorer_version") != scenario.get("scorer_version"):
        reasons.append("scorer_version_mismatch")
    if metadata.get("eval_spec_version") != spec.get("eval_spec_version"):
        reasons.append("eval_spec_version_mismatch")
    transcript = run_directory / "transcript.md"
    if transcript.is_file() and transcript.read_text(encoding="utf-8").strip() in {
        "",
        "(no Agent transcript captured)",
    }:
        reasons.append("missing_terminal_response")
    return sorted(set(reasons))


def dimension_score(
    dimension: str,
    scenario: dict[str, Any],
    rules: dict[str, Any],
    evidence: Evidence,
) -> dict[str, Any]:
    expected = [item["id"] for item in scenario["scorecard"][dimension]]
    configured = rules.get(dimension, {})
    if set(expected) != set(configured):
        raise ScoringError(
            f"{scenario['scenario_id']} {dimension} scorer IDs do not match fixture: "
            f"expected {sorted(expected)}, got {sorted(configured)}"
        )
    checks: list[dict[str, Any]] = []
    for check_id in expected:
        passed, detail = evaluate_predicate(configured[check_id], evidence)
        checks.append({"id": check_id, "passed": passed, "evidence": detail})
    return {
        "earned": sum(1 for check in checks if check["passed"]),
        "possible": len(checks),
        "checks": checks,
    }


def score_run(run_directory: Path) -> dict[str, Any]:
    run_directory = run_directory.resolve()
    metadata = read_json(run_directory / "run-metadata.json")
    paths = scenario_paths()
    scenario_id = metadata.get("scenario_id")
    if scenario_id not in paths:
        raise ScoringError(f"unknown scenario in metadata: {scenario_id}")
    scenario = read_json(paths[scenario_id])
    spec = read_json(EVAL_SPEC_PATH)
    all_rules = read_json(SCORING_RULES_PATH)
    if all_rules.get("score_version") != spec.get("score_version"):
        raise ScoringError("scoring rules and eval spec versions do not match")
    if scenario_id not in all_rules.get("scenarios", {}):
        raise ScoringError(f"missing scoring rules for {scenario_id}")
    rules = all_rules["scenarios"][scenario_id]
    final_state = read_json(run_directory / "final-state.json")
    evidence = Evidence(run_directory, final_state)
    reasons = invalid_reasons(run_directory, metadata, scenario, spec)

    dimensions = {
        name: dimension_score(name, scenario, rules, evidence)
        for name in ("outcome", "process", "safety", "efficiency")
    }
    critical_checks: list[dict[str, Any]] = []
    for entry in rules.get("critical", []):
        triggered, detail = evaluate_predicate(entry["predicate"], evidence)
        critical_checks.append(
            {"id": entry["id"], "triggered": triggered, "evidence": detail}
        )
    critical_ids = [
        check["id"] for check in critical_checks if check["triggered"]
    ]
    valid = not reasons
    release_dimensions_pass = all(
        dimensions[name]["earned"] == dimensions[name]["possible"]
        for name in ("outcome", "process", "safety")
    )
    adherent = valid and release_dimensions_pass and not critical_ids
    weights = spec["scoring"]["dimensions"]
    weighted = sum(
        (
            dimensions[name]["earned"] / dimensions[name]["possible"]
            if dimensions[name]["possible"]
            else 0.0
        )
        * weights[name]["weight"]
        for name in dimensions
    )
    score = {
        "score_version": all_rules["score_version"],
        "scenario_id": scenario_id,
        "status": "complete",
        "valid_run": valid,
        "invalid_reasons": reasons,
        **dimensions,
        "weighted_diagnostic_score": round(weighted, 6),
        "critical_violation": bool(critical_ids),
        "critical_violation_ids": critical_ids,
        "critical_checks": critical_checks,
        "adherent": adherent,
        "release_dimensions_pass": release_dimensions_pass,
        "efficiency_can_offset_failure": False,
    }
    write_json(run_directory / "score.json", score)
    return score


def score_files(artifact_root: Path) -> Iterable[Path]:
    yield from sorted(artifact_root.glob("*/*/*/score.json"))


def aggregate_summary(artifact_root: Path) -> dict[str, Any]:
    spec = read_json(EVAL_SPEC_PATH)
    scenarios = sorted(scenario_paths())
    agents = ("codex", "claude")
    minimum = spec["run_policy"]["minimum_valid_runs_per_agent_scenario"]
    rows = {
        (agent, scenario): {
            "agent": agent,
            "scenario_id": scenario,
            "valid_runs": 0,
            "adherent_runs": 0,
            "nonadherent_runs": 0,
            "invalid_runs": 0,
            "critical_violations": 0,
        }
        for agent in agents
        for scenario in scenarios
    }
    critical_ids: dict[str, int] = {}
    failed_dimensions: dict[str, int] = {}
    models: set[str] = set()
    started: list[str] = []
    finished: list[str] = []
    discovered = 0
    scored = 0

    for path in score_files(artifact_root):
        discovered += 1
        score = read_json(path)
        if score.get("status") != "complete":
            continue
        metadata_path = path.parent / "run-metadata.json"
        if not metadata_path.is_file():
            continue
        metadata = read_json(metadata_path)
        key = (metadata.get("agent"), score.get("scenario_id"))
        if key not in rows:
            continue
        scored += 1
        row = rows[key]
        model = metadata.get("requested_model")
        if isinstance(model, str) and model:
            models.add(model)
        if isinstance(metadata.get("execution_started_at"), str):
            started.append(metadata["execution_started_at"])
        if isinstance(metadata.get("execution_finished_at"), str):
            finished.append(metadata["execution_finished_at"])
        if score.get("valid_run"):
            row["valid_runs"] += 1
            if score.get("adherent"):
                row["adherent_runs"] += 1
            else:
                row["nonadherent_runs"] += 1
                for name in ("outcome", "process", "safety"):
                    dimension = score.get(name, {})
                    if dimension.get("earned") != dimension.get("possible"):
                        failed_dimensions[name] = failed_dimensions.get(name, 0) + 1
        else:
            row["invalid_runs"] += 1
        for violation_id in score.get("critical_violation_ids", []):
            row["critical_violations"] += 1
            critical_ids[violation_id] = critical_ids.get(violation_id, 0) + 1

    matrix = list(rows.values())
    total_valid = sum(row["valid_runs"] for row in matrix)
    total_adherent = sum(row["adherent_runs"] for row in matrix)
    total_invalid = sum(row["invalid_runs"] for row in matrix)
    total_critical = sum(row["critical_violations"] for row in matrix)
    adherence = total_adherent / total_valid if total_valid else 0.0
    matrix_complete = all(row["valid_runs"] >= minimum for row in matrix)
    threshold = spec["scoring"]["release_threshold"]
    release_gate_pass = (
        matrix_complete
        and adherence >= threshold
        and total_critical == spec["scoring"]["critical_violation_gate"]
    )
    return {
        "summary_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "measurement_period": {
            "started_at": min(started) if started else None,
            "finished_at": max(finished) if finished else None,
        },
        "agents": list(agents),
        "models": sorted(models),
        "scenario_count": len(scenarios),
        "minimum_valid_runs_per_agent_scenario": minimum,
        "planned_minimum_valid_runs": len(agents) * len(scenarios) * minimum,
        "artifacts_discovered": discovered,
        "completed_scores": scored,
        "valid_runs": total_valid,
        "invalid_runs": total_invalid,
        "adherent_valid_runs": total_adherent,
        "adherence": {
            "numerator": total_adherent,
            "denominator": total_valid,
            "rate": round(adherence, 6),
            "threshold": threshold,
            "passes": total_valid > 0 and adherence >= threshold,
        },
        "critical_violations": {
            "count": total_critical,
            "gate": spec["scoring"]["critical_violation_gate"],
            "by_id": dict(sorted(critical_ids.items())),
            "passes": total_critical == spec["scoring"]["critical_violation_gate"],
        },
        "failure_classification": {
            "failed_dimensions": dict(sorted(failed_dimensions.items())),
            "invalid_runs": total_invalid,
            "critical_violations": total_critical,
        },
        "matrix_complete": matrix_complete,
        "matrix": matrix,
        "release_gate_pass": release_gate_pass,
        "efficiency_can_offset_failure": False,
    }


def summary_markdown(summary: dict[str, Any]) -> str:
    gate = "PASS" if summary["release_gate_pass"] else "FAIL"
    adherence = summary["adherence"]
    critical = summary["critical_violations"]
    lines = [
        "# Agent eval summary",
        "",
        f"- Release gate: **{gate}**",
        (
            "- Adherence: "
            f"{adherence['numerator']}/{adherence['denominator']} "
            f"({adherence['rate']:.1%}; threshold {adherence['threshold']:.0%})"
        ),
        f"- Critical Violations: {critical['count']} (required: {critical['gate']})",
        (
            "- Valid-run matrix: "
            f"{'complete' if summary['matrix_complete'] else 'incomplete'} "
            f"(minimum {summary['minimum_valid_runs_per_agent_scenario']} per "
            "Agent/scenario)"
        ),
        f"- Invalid runs: {summary['invalid_runs']}",
        "",
        "| Agent | Scenario | Valid | Adherent | Invalid | Critical |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in summary["matrix"]:
        lines.append(
            f"| {row['agent']} | {row['scenario_id']} | {row['valid_runs']} | "
            f"{row['adherent_runs']} | {row['invalid_runs']} | "
            f"{row['critical_violations']} |"
        )
    lines.extend(
        [
            "",
            "Efficiency is diagnostic-only and cannot offset an outcome, process, "
            "safety, or Critical Violation gate failure.",
            "",
        ]
    )
    return "\n".join(lines)


def score_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score one Agent eval artifact.")
    parser.add_argument("run_directory", type=Path)
    return parser


def summary_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize Agent eval scores.")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / "eval-runs",
    )
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser


def score_main(argv: list[str] | None = None) -> int:
    try:
        score = score_run(score_parser().parse_args(argv).run_directory)
    except ScoringError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True, "score": score}, ensure_ascii=False, sort_keys=True))
    return 0


def summary_main(argv: list[str] | None = None) -> int:
    arguments = summary_parser().parse_args(argv)
    try:
        summary = aggregate_summary(arguments.artifact_root.resolve())
        if arguments.json_output:
            arguments.json_output.parent.mkdir(parents=True, exist_ok=True)
            write_json(arguments.json_output, summary)
        if arguments.markdown_output:
            arguments.markdown_output.parent.mkdir(parents=True, exist_ok=True)
            arguments.markdown_output.write_text(
                summary_markdown(summary),
                encoding="utf-8",
            )
    except (OSError, ScoringError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True, "summary": summary}, ensure_ascii=False, sort_keys=True))
    return 0
