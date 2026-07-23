"""Aggregate token usage from valid Agent-eval runs."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any


class UsageSummaryError(ValueError):
    """Raised when valid eval evidence has no supported usage record."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise UsageSummaryError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise UsageSummaryError(f"expected JSON object: {path}")
    return value


def read_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise UsageSummaryError(f"cannot read events {path}: {error}") from error
    for line_number, line in enumerate(lines, 1):
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise UsageSummaryError(
                f"invalid JSON event {path}:{line_number}: {error}"
            ) from error
        if isinstance(value, dict):
            events.append(value)
    return events


def integer(usage: dict[str, Any], key: str) -> int:
    value = usage.get(key, 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise UsageSummaryError(f"usage field {key!r} must be a nonnegative integer")
    return value


def terminal_usage(run_directory: Path, agent: str) -> dict[str, int | str]:
    events = read_events(run_directory / "agent-events.jsonl")
    if agent == "codex":
        terminal = next(
            (
                event
                for event in reversed(events)
                if event.get("type") == "turn.completed"
                and isinstance(event.get("usage"), dict)
            ),
            None,
        )
        if terminal is None:
            raise UsageSummaryError(f"missing Codex terminal usage: {run_directory}")
        usage = terminal["usage"]
        context_input = integer(usage, "input_tokens")
        cache_read = integer(usage, "cached_input_tokens")
        cache_write = integer(usage, "cache_write_input_tokens")
        output = integer(usage, "output_tokens")
        semantics = "Codex input_tokens includes cached input; cache fields are subsets"
    elif agent == "claude":
        terminal = next(
            (
                event
                for event in reversed(events)
                if event.get("type") == "result"
                and isinstance(event.get("usage"), dict)
            ),
            None,
        )
        if terminal is None:
            raise UsageSummaryError(f"missing Claude terminal usage: {run_directory}")
        usage = terminal["usage"]
        uncached_input = integer(usage, "input_tokens")
        cache_read = integer(usage, "cache_read_input_tokens")
        cache_write = integer(usage, "cache_creation_input_tokens")
        context_input = uncached_input + cache_read + cache_write
        output = integer(usage, "output_tokens")
        semantics = "Claude context input is input + cache read + cache creation"
    else:
        raise UsageSummaryError(f"unsupported Agent host: {agent!r}")
    return {
        "context_input_tokens": context_input,
        "cache_read_input_tokens": cache_read,
        "cache_write_input_tokens": cache_write,
        "output_tokens": output,
        "total_tokens": context_input + output,
        "semantics": semantics,
    }


def metric_summary(values: list[int]) -> dict[str, int | float]:
    if not values:
        raise UsageSummaryError("cannot summarize an empty metric")
    return {
        "sum": sum(values),
        "median": statistics.median(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def summarize_usage(artifact_root: Path) -> dict[str, Any]:
    if not artifact_root.is_dir():
        raise UsageSummaryError(f"missing artifact root: {artifact_root}")
    runs: list[dict[str, int | str]] = []
    for score_path in sorted(artifact_root.rglob("score.json")):
        score = read_json(score_path)
        if not score.get("valid_run"):
            continue
        run_directory = score_path.parent
        metadata = read_json(run_directory / "run-metadata.json")
        agent = metadata.get("agent")
        if not isinstance(agent, str):
            raise UsageSummaryError(f"missing Agent identity: {run_directory}")
        usage = terminal_usage(run_directory, agent)
        runs.append({"agent": agent, **usage})
    if not runs:
        raise UsageSummaryError(f"no valid runs under {artifact_root}")

    by_agent: dict[str, Any] = {}
    metric_names = (
        "context_input_tokens",
        "cache_read_input_tokens",
        "cache_write_input_tokens",
        "output_tokens",
        "total_tokens",
    )
    for agent in sorted({str(run["agent"]) for run in runs}):
        selected = [run for run in runs if run["agent"] == agent]
        by_agent[agent] = {
            "valid_runs": len(selected),
            "semantics": selected[0]["semantics"],
            "metrics": {
                name: metric_summary([int(run[name]) for run in selected])
                for name in metric_names
            },
        }
    return {
        "summary_version": 1,
        "artifact_root": artifact_root.name,
        "valid_runs": len(runs),
        "diagnostic_only": True,
        "by_agent": by_agent,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize token usage from valid Agent-eval runs."
    )
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--json-output", type=Path)
    arguments = parser.parse_args(argv)
    try:
        summary = summarize_usage(arguments.artifact_root)
        if arguments.json_output is not None:
            arguments.json_output.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
        print(json.dumps({"ok": True, "summary": summary}, sort_keys=True))
        return 0
    except (OSError, UsageSummaryError) as error:
        print(
            json.dumps(
                {"ok": False, "errors": [{"code": "USAGE_SUMMARY_ERROR", "message": str(error)}]},
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
