"""Run versioned release-level recovery drill groups."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "recovery/drill-manifest-v1.json"
SELECTOR = re.compile(r"^tests\.test_[a-z0-9_]+(?:\.[A-Za-z0-9_]+){0,2}$")
TEST_COUNT = re.compile(r"Ran ([0-9]+) tests?")


class DrillRunnerError(ValueError):
    """Raised when a drill manifest or selection is invalid."""


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DrillRunnerError(f"cannot read drill manifest: {error}") from error
    if not isinstance(document, dict) or document.get("manifest_version") != 1:
        raise DrillRunnerError("unsupported or invalid drill manifest")
    drills = document.get("drills")
    if not isinstance(drills, list) or not drills:
        raise DrillRunnerError("drill manifest requires a non-empty drills array")
    identifiers: set[str] = set()
    for drill in drills:
        if not isinstance(drill, dict):
            raise DrillRunnerError("each drill must be an object")
        identifier = drill.get("id")
        selectors = drill.get("selectors")
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in identifiers
        ):
            raise DrillRunnerError("drill IDs must be unique non-empty strings")
        identifiers.add(identifier)
        if not isinstance(selectors, list) or not selectors:
            raise DrillRunnerError(f"drill {identifier} has no selectors")
        if any(not isinstance(item, str) or not SELECTOR.fullmatch(item) for item in selectors):
            raise DrillRunnerError(f"drill {identifier} has an unsafe selector")
    return document


def run_drills(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    selected_ids: list[str] | None = None,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    by_id = {drill["id"]: drill for drill in manifest["drills"]}
    requested = list(by_id) if not selected_ids else selected_ids
    unknown = [identifier for identifier in requested if identifier not in by_id]
    if unknown:
        raise DrillRunnerError(f"unknown drill ID: {unknown[0]}")
    if len(set(requested)) != len(requested):
        raise DrillRunnerError("duplicate drill selection")

    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    results: list[dict[str, Any]] = []
    for identifier in requested:
        selectors = by_id[identifier]["selectors"]
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", *selectors],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        match = TEST_COUNT.search(completed.stderr + completed.stdout)
        results.append(
            {
                "id": identifier,
                "passed": completed.returncode == 0,
                "selector_count": len(selectors),
                "test_count": int(match.group(1)) if match else None,
            }
        )
    passed = sum(bool(result["passed"]) for result in results)
    return {
        "runner_version": 1,
        "manifest_version": manifest["manifest_version"],
        "ok": passed == len(results),
        "summary": {
            "requested": len(results),
            "passed": passed,
            "failed": len(results) - passed,
        },
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run release recovery drills.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--drill", action="append", dest="drills")
    arguments = parser.parse_args(argv)
    try:
        result = run_drills(arguments.manifest, selected_ids=arguments.drills)
    except DrillRunnerError as error:
        result = {
            "runner_version": 1,
            "ok": False,
            "errors": [{"code": "INVALID_DRILL_REQUEST", "message": str(error)}],
        }
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
