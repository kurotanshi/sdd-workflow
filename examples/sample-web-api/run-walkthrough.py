#!/usr/bin/env python3
"""Replay proposal, drift, revision, reapproval, archive, and INDEX recovery."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


EXAMPLE = Path(__file__).resolve().parent
ROOT = EXAMPLE.parents[1]
RUNTIME = ROOT / "skills/sdd-workflow/scripts/sdd.py"
TEMPLATE = EXAMPLE / "project"
STEPS = EXAMPLE / "steps"
WALKTHROUGH = json.loads(
    (EXAMPLE / "walkthrough.json").read_text(encoding="utf-8")
)
SHORT_NAME = WALKTHROUGH["short_name"]


def invoke(
    project: Path,
    *arguments: str,
    expect_ok: bool = True,
) -> dict[str, Any]:
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
    if completed.stderr:
        raise AssertionError(f"unexpected stderr for {arguments}: {completed.stderr}")
    if bool(document.get("ok")) != expect_ok:
        raise AssertionError(f"unexpected runtime result for {arguments}: {document}")
    return document


def git(project: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(project), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise AssertionError(f"git {' '.join(arguments)} failed: {completed.stderr}")
    return completed.stdout


def commit(project: Path, message: str) -> None:
    git(project, "add", ".")
    git(project, "commit", "-qm", message)


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


def complete_next_task(project: Path) -> str:
    status = invoke(project, "status", SHORT_NAME)["data"]
    pending = next(task for task in status["tasks"] if not task["completed"])
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
    return pending["canonical_text"]


def apply_scope_drift(project: Path) -> None:
    proposal = project / "sdd" / SHORT_NAME / "proposal.md"
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace(
            "- Preserve the existing JSON 404 response for unknown paths.\n",
            "- Preserve the existing JSON 404 response for unknown paths.\n"
            "- Include the semantic service version in the health response.\n",
        ),
        encoding="utf-8",
    )
    tasks = project / "sdd" / SHORT_NAME / "tasks.md"
    tasks.write_text(
        tasks.read_text(encoding="utf-8").replace(
            "- [ ] Document the final health response contract\n",
            "- [ ] Include the service version in `/health` and update its test\n",
        ).replace(
            '- 情境：`/health` returns HTTP 200 and `{"status": "ok"}`\n',
            '- 情境：`/health` returns HTTP 200 with status `ok` and version `1.0.0`\n',
        ),
        encoding="utf-8",
    )


def run() -> dict[str, Any]:
    events: list[str] = []
    with tempfile.TemporaryDirectory(prefix="sdd-sample-web-api-") as directory:
        project = Path(directory) / "sample-web-api"
        shutil.copytree(TEMPLATE, project)
        git(project, "init", "-q")
        git(project, "config", "user.name", "SDD Example")
        git(project, "config", "user.email", "sdd-example@example.invalid")
        commit(project, "example: initial proposal")
        events.append("proposal")

        status = invoke(project, "status", SHORT_NAME)["data"]
        invoke(project, "validate", SHORT_NAME)
        invoke(
            project,
            "approve",
            SHORT_NAME,
            "--expected-snapshot",
            status["snapshot"]["snapshot_digest"],
        )
        commit(project, "sdd: approve health endpoint")
        events.append("approval")

        shutil.copyfile(STEPS / "task-1/app.py", project / "app.py")
        completed_task = complete_next_task(project)
        if not completed_task.startswith("Implement the `/health`"):
            raise AssertionError(f"wrong first task: {completed_task}")
        commit(project, "feat: implement health response")
        events.append("task-1")

        apply_scope_drift(project)
        commit(project, "external: add version requirement")
        events.append("scope-drift")
        drift = invoke(project, "status", SHORT_NAME, expect_ok=False)
        error = drift["errors"][0]
        if (
            error["code"] != WALKTHROUGH["expected_drift_code"]
            or error["action"] != WALKTHROUGH["expected_drift_action"]
        ):
            raise AssertionError(f"scope drift did not fail closed: {drift}")

        revision = invoke(
            project,
            "begin-revision",
            SHORT_NAME,
            "--expected-snapshot",
            drift["data"]["snapshot"]["snapshot_digest"],
        )["data"]
        if not revision["differences"]:
            raise AssertionError("revision did not retain field-level differences")
        revised = invoke(project, "status", SHORT_NAME)["data"]
        if revised["status"] != "draft" or revised["completed_count"] != 1:
            raise AssertionError(f"revision lost progress: {revised}")
        invoke(project, "validate", SHORT_NAME)
        commit(project, "sdd: begin reviewed scope revision")
        events.append("revision")

        invoke(
            project,
            "approve",
            SHORT_NAME,
            "--expected-snapshot",
            revised["snapshot"]["snapshot_digest"],
        )
        commit(project, "sdd: reapprove versioned health response")
        events.append("reapproval")

        (project / "tests").mkdir(exist_ok=True)
        shutil.copyfile(STEPS / "task-2/test_app.py", project / "tests/test_app.py")
        run_tests(project)
        complete_next_task(project)
        commit(project, "test: cover health and unknown routes")
        events.append("task-2")

        shutil.copyfile(STEPS / "task-3/app.py", project / "app.py")
        shutil.copyfile(STEPS / "task-3/test_app.py", project / "tests/test_app.py")
        run_tests(project)
        complete_next_task(project)
        commit(project, "feat: include service version")
        events.append("task-3")

        final_status = invoke(project, "status", SHORT_NAME)["data"]
        if (
            final_status["completed_count"] != 3
            or final_status["task_count"] != 3
        ):
            raise AssertionError(f"tasks are incomplete: {final_status}")
        run_tests(project)
        events.append("acceptance")

        archived = invoke(
            project,
            "archive",
            SHORT_NAME,
            "--expected-snapshot",
            final_status["snapshot"]["snapshot_digest"],
            "--summary",
            "Added a versioned dependency-free health response with regression tests.",
        )["data"]
        commit(project, "sdd: archive completed health endpoint")
        events.append("archive")
        archive_path = Path(archived["destination"])
        if not archive_path.is_dir():
            raise AssertionError("archive destination is missing")

        index = project / "sdd/archive/INDEX.md"
        index.unlink()
        commit(project, "example: delete derived archive index")
        events.append("index-delete")
        stale = invoke(project, "validate-index", expect_ok=False)
        if stale["errors"][0]["action"] != "rebuild_index":
            raise AssertionError(f"missing index did not request rebuild: {stale}")

        rebuilt = invoke(project, "rebuild-index")["data"]
        invoke(project, "validate-index")
        doctor = invoke(project, "doctor")["data"]
        if not rebuilt["changed"] or not doctor["healthy"]:
            raise AssertionError("INDEX recovery did not converge")
        commit(project, "sdd: rebuild archive index")
        events.append("index-rebuild")

        if events != WALKTHROUGH["stages"]:
            raise AssertionError(f"walkthrough stages diverged: {events}")
        if git(project, "status", "--porcelain"):
            raise AssertionError("walkthrough repository is dirty")
        history = [
            line
            for line in git(project, "log", "--format=%s").splitlines()
            if line
        ]
        return {
            "ok": True,
            "walkthrough_version": WALKTHROUGH["walkthrough_version"],
            "events": events,
            "drift_code": error["code"],
            "retained_completed_tasks": revised["completed_count"],
            "final_task_count": final_status["task_count"],
            "archive_committed": True,
            "index_rebuilt": True,
            "doctor_healthy": True,
            "git_commit_count": len(history),
            "git_history": history,
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True))
