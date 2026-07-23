#!/usr/bin/env python3
"""Replay the bounded first-workflow usability path in a temporary repository."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


EXAMPLE = Path(__file__).resolve().parent
ROOT = EXAMPLE.parents[1]
RUNTIME = ROOT / "skills/sdd-workflow/scripts/sdd.py"
SHORT_NAME = "add-health-check"
PERSONA_ID = "agent-assisted-developer-first-sdd-workflow-v1"
START_POINT = "package-installed-clean-repository-readme-quickstart-open"
END_POINT = "one-task-change-tested-accepted-and-archived"


PROPOSAL = """\
---
schema_version: 2
---
# add-health-check

## 狀態
draft

## 類型
新功能

## 為什麼做
Provide a dependency-free health signal for local operators.

## 要改什麼
- Add a `health()` function that returns `{"status": "ok"}`.
- Add a regression test for the response.

## 影響範圍
- `app.py`
- `tests/test_app.py`
"""


TASKS = """\
# Tasks

- [ ] Implement and test the dependency-free `health()` response.

## 驗收條件
- 情境：`health()` returns exactly `{"status": "ok"}`.
"""


APP = """\
def health() -> dict[str, str]:
    return {"status": "ok"}
"""


TEST = """\
from __future__ import annotations

import unittest

from app import health


class HealthTests(unittest.TestCase):
    def test_health_response(self) -> None:
        self.assertEqual(health(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
"""


def invoke(project: Path, *arguments: str) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNTIME),
            "--root",
            str(project),
            "--json",
            *arguments,
        ],
        cwd=project,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(
            f"runtime did not emit JSON for {arguments}: {completed.stdout!r}"
        ) from error
    if completed.stderr or completed.returncode != 0 or not document.get("ok"):
        raise AssertionError(
            f"runtime command failed for {arguments}: "
            f"exit={completed.returncode} stdout={document} stderr={completed.stderr!r}"
        )
    return document


def run_tests(project: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "tests.test_app"],
        cwd=project,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise AssertionError(f"sample acceptance failed: {completed.stderr}")


def write_initial_project(project: Path) -> None:
    proposal = project / "sdd" / SHORT_NAME
    proposal.mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "app.py").write_text(
        "def health() -> None:\n    return None\n",
        encoding="utf-8",
    )
    (project / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (proposal / "proposal.md").write_text(PROPOSAL, encoding="utf-8")
    (proposal / "tasks.md").write_text(TASKS, encoding="utf-8")


def run(*, threshold_seconds: float = 900.0) -> dict[str, Any]:
    started_at = dt.datetime.now(dt.UTC)
    started = time.perf_counter()
    stages: list[str] = []
    with tempfile.TemporaryDirectory(prefix="sdd-first-workflow-") as directory:
        project = Path(directory) / "project"
        project.mkdir()
        write_initial_project(project)
        stages.append("proposal")

        invoke(project, "validate", SHORT_NAME)
        status = invoke(project, "status", SHORT_NAME)["data"]
        invoke(
            project,
            "approve",
            SHORT_NAME,
            "--expected-snapshot",
            status["snapshot"]["snapshot_digest"],
        )
        stages.append("approval")

        (project / "app.py").write_text(APP, encoding="utf-8")
        (project / "tests" / "test_app.py").write_text(TEST, encoding="utf-8")
        run_tests(project)
        approved = invoke(project, "status", SHORT_NAME)["data"]
        task = approved["tasks"][0]
        invoke(
            project,
            "complete-task",
            SHORT_NAME,
            str(task["ordinal"]),
            "--expected-task-digest",
            task["task_digest"],
            "--expected-snapshot",
            approved["snapshot"]["snapshot_digest"],
        )
        stages.append("implementation")

        final_status = invoke(project, "status", SHORT_NAME)["data"]
        if final_status["completed_count"] != final_status["task_count"]:
            raise AssertionError(f"sample task is incomplete: {final_status}")
        run_tests(project)
        stages.append("acceptance")

        archived = invoke(
            project,
            "archive",
            SHORT_NAME,
            "--expected-snapshot",
            final_status["snapshot"]["snapshot_digest"],
            "--summary",
            "Added and tested the dependency-free health response.",
        )["data"]
        archive_path = Path(archived["destination"])
        if not archive_path.is_dir():
            raise AssertionError("sample archive destination is missing")
        invoke(project, "validate-index")
        doctor = invoke(project, "doctor")["data"]
        if not doctor["healthy"]:
            raise AssertionError(f"sample project is unhealthy: {doctor}")
        stages.append("archive")

        authoritative_path = archive_path.resolve().relative_to(
            project.resolve()
        ).as_posix()

    finished_at = dt.datetime.now(dt.UTC)
    elapsed_seconds = round(time.perf_counter() - started, 3)
    return {
        "record_version": 1,
        "sample_id": "proxy-20260723-01",
        "sample_kind": "automated-first-time-path-proxy",
        "persona_id": PERSONA_ID,
        "start_point": START_POINT,
        "end_point": END_POINT,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "elapsed_seconds": elapsed_seconds,
        "threshold_seconds": threshold_seconds,
        "within_budget": elapsed_seconds <= threshold_seconds,
        "valid_run": True,
        "task_success": True,
        "human_participant": False,
        "transaction_protocol_read": False,
        "stages": stages,
        "authoritative_path": authoritative_path,
        "doctor_healthy": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay the bounded first-workflow usability path."
    )
    parser.add_argument("--threshold-seconds", type=float, default=900.0)
    arguments = parser.parse_args()
    record = run(threshold_seconds=arguments.threshold_seconds)
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0 if record["within_budget"] and record["task_success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
