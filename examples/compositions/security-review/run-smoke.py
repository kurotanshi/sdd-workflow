#!/usr/bin/env python3
"""Execute the Security Review composition through standard SDD primitives."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


EXAMPLE = Path(__file__).resolve().parent
ROOT = EXAMPLE.parents[2]
RUNTIME = ROOT / "skills/sdd-workflow/scripts/sdd.py"
TEMPLATE = EXAMPLE / "project"
SHORT_NAME = "review-auth-boundary"


def invoke(project: Path, *arguments: str) -> dict[str, Any]:
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
    if completed.stderr:
        raise AssertionError(f"unexpected stderr for {arguments}: {completed.stderr}")
    if not document.get("ok"):
        raise AssertionError(f"runtime rejected {arguments}: {document}")
    return document


def run() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="sdd-security-review-") as directory:
        project = Path(directory) / "project"
        shutil.copytree(TEMPLATE, project)

        status = invoke(project, "status", SHORT_NAME)["data"]
        if status["status"] != "draft" or status["task_count"] != 3:
            raise AssertionError(f"unexpected draft projection: {status}")

        invoke(
            project,
            "approve",
            SHORT_NAME,
            "--expected-snapshot",
            status["snapshot"]["snapshot_digest"],
        )

        completed = 0
        while True:
            status = invoke(project, "status", SHORT_NAME)["data"]
            pending = next(
                (task for task in status["tasks"] if not task["completed"]),
                None,
            )
            if pending is None:
                break
            invoke(
                project,
                "complete-task",
                SHORT_NAME,
                str(pending["ordinal"]),
                "--expected-task-digest",
                pending["task_digest"],
                "--expected-snapshot",
                status["snapshot"]["snapshot_digest"],
            )
            completed += 1

        proposal = project / "sdd" / SHORT_NAME / "proposal.md"
        proposal.write_text(
            proposal.read_text(encoding="utf-8")
            + "\n- Reviewed the sample authentication boundary and trust assumptions.\n"
            + "- No release-blocking finding was observed in the bounded example.\n"
            + "- Re-run the review when authentication or authorization behavior changes.\n",
            encoding="utf-8",
        )
        status = invoke(project, "status", SHORT_NAME)["data"]
        if not status.get("research_conclusion"):
            raise AssertionError("research conclusion was not projected")

        archived = invoke(
            project,
            "archive",
            SHORT_NAME,
            "--expected-snapshot",
            status["snapshot"]["snapshot_digest"],
            "--summary",
            "Security Review composition completed with standard SDD state only.",
        )["data"]
        destination = Path(archived["destination"])
        allowed = {
            "proposal.md",
            "tasks.md",
            ".sdd/approval-manifest.json",
            ".sdd/metadata.json",
        }
        observed = {
            path.relative_to(destination).as_posix()
            for path in destination.rglob("*")
            if path.is_file()
        }
        if observed != allowed:
            raise AssertionError(f"composition introduced state: {sorted(observed)}")

        doctor = invoke(project, "doctor")["data"]
        if not doctor["healthy"]:
            raise AssertionError(f"composition repository is unhealthy: {doctor}")
        return {
            "ok": True,
            "composition": "security-review",
            "state_model": "sdd-protocol-only",
            "completed_tasks": completed,
            "terminal_status": "completed",
            "artifact_files": sorted(observed),
            "doctor_healthy": True,
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True))
