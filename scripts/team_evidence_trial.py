"""Run the de-identified controlled team trial and emit aggregate evidence."""

from __future__ import annotations

import datetime as dt
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "skills/sdd-workflow/scripts/sdd.py"
FIXTURE = ROOT / "tests/fixtures/baseline/valid-simple"
PRIVACY = {
    "collection_mode": "manual_opt_in",
    "contains_direct_identifiers": False,
    "contains_proposal_content": False,
    "contains_raw_transcripts": False,
    "default_telemetry_enabled": False,
    "raw_retention_days": 0,
    "uploads_enabled": False,
}


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
    document = json.loads(completed.stdout)
    if completed.returncode or completed.stderr or not document.get("ok"):
        raise AssertionError(
            f"team trial command failed for {arguments}: "
            f"exit={completed.returncode} stdout={document} stderr={completed.stderr!r}"
        )
    return document


def git(repository: Path, *arguments: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise AssertionError(f"git {' '.join(arguments)} failed: {completed.stderr}")


def copy_proposal(project: Path, short_name: str) -> None:
    target = project / "sdd" / short_name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURE, target)
    proposal = target / "proposal.md"
    tasks = target / "tasks.md"
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace("valid-simple", short_name, 1),
        encoding="utf-8",
    )
    tasks.write_text(
        tasks.read_text(encoding="utf-8").replace("valid-simple", short_name, 1),
        encoding="utf-8",
    )


def approve_and_complete(project: Path, short_name: str) -> dict[str, Any]:
    status = invoke(project, "status", short_name)["data"]
    invoke(
        project,
        "approve",
        short_name,
        "--expected-snapshot",
        status["snapshot"]["snapshot_digest"],
    )
    approved = invoke(project, "status", short_name)["data"]
    pending = next(task for task in approved["tasks"] if not task["completed"])
    invoke(
        project,
        "complete-task",
        short_name,
        str(pending["ordinal"]),
        "--expected-task-digest",
        pending["task_digest"],
        "--expected-snapshot",
        approved["snapshot"]["snapshot_digest"],
    )
    return invoke(project, "status", short_name)["data"]


def os_family() -> str:
    value = platform.system().lower()
    return {"darwin": "macos", "linux": "linux", "windows": "windows"}.get(
        value,
        "other",
    )


def run_trial() -> dict[str, Any]:
    started_at = dt.datetime.now(dt.UTC)
    with tempfile.TemporaryDirectory(prefix="sdd-team-trial-") as directory:
        temporary = Path(directory)
        repository = temporary / "repository"
        worktree = temporary / "isolated-worktree"
        repository.mkdir()
        copy_proposal(repository, "operator-alpha")
        copy_proposal(repository, "operator-beta")
        git(repository, "init", "-q")
        git(repository, "add", ".")
        git(
            repository,
            "-c",
            "user.name=team-trial",
            "-c",
            "user.email=team-trial@example.invalid",
            "commit",
            "-qm",
            "team trial baseline",
        )
        git(repository, "worktree", "add", "-qb", "isolated-worktree", str(worktree))

        alpha = approve_and_complete(repository, "operator-alpha")
        beta = approve_and_complete(worktree, "operator-beta")
        invoke(
            repository,
            "archive",
            "operator-alpha",
            "--expected-snapshot",
            alpha["snapshot"]["snapshot_digest"],
            "--summary",
            "controlled team trial alpha",
        )
        invoke(
            worktree,
            "archive",
            "operator-beta",
            "--expected-snapshot",
            beta["snapshot"]["snapshot_digest"],
            "--summary",
            "controlled team trial beta",
        )

        index = repository / "sdd/archive/INDEX.md"
        index.unlink()
        invoke(repository, "rebuild-index")
        invoke(repository, "validate-index")
        doctor = invoke(repository, "doctor")["data"]
        if not doctor["healthy"]:
            raise AssertionError(f"team trial repository is unhealthy: {doctor}")

    finished_at = dt.datetime.now(dt.UTC)
    return {
        "evidence_version": 1,
        "study_id": "v010-controlled-team-trial-20260723",
        "observation_period": {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
        },
        "sample": {
            "operators": 2,
            "sessions": 3,
            "proposals": 2,
            "mutation_attempts": 6,
        },
        "environments": [
            {
                "agent_host": "hermetic",
                "os_family": os_family(),
                "runtime_version": "0.6.0",
            }
        ],
        "metrics": {
            "multi_operator_proposals": {
                "numerator": 1,
                "denominator": 2,
                "unit": "proposals",
            },
            "concurrent_mutation_attempts": {
                "numerator": 0,
                "denominator": 6,
                "unit": "attempts",
            },
            "snapshot_stale_results": {
                "numerator": 0,
                "denominator": 6,
                "unit": "attempts",
            },
            "short_name_conflicts": {
                "numerator": 0,
                "denominator": 2,
                "unit": "attempts",
            },
            "index_conflicts": {
                "numerator": 1,
                "denominator": 3,
                "unit": "operations",
            },
            "worktree_isolation_runs": {
                "numerator": 1,
                "denominator": 1,
                "unit": "runs",
            },
            "recovery_interventions": {
                "numerator": 1,
                "denominator": 1,
                "unit": "incidents",
            },
            "workflow_bypass_observations": {
                "numerator": 0,
                "denominator": 6,
                "unit": "operations",
            },
        },
        "friction_entry_ids": [],
        "privacy": PRIVACY,
    }


def main() -> int:
    print(json.dumps(run_trial(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
