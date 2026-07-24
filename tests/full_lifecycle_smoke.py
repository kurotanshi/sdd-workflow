"""Fresh-install lifecycle smoke for the portable SDD distribution."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/sdd-workflow"


def _environment() -> dict[str, str]:
    allowed = ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR")
    return {key: os.environ[key] for key in allowed if key in os.environ}


def _run_json(
    script: Path,
    arguments: list[str],
    *,
    cwd: Path,
) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=cwd,
        env=_environment(),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.stderr:
        raise AssertionError(f"unexpected stderr: {result.stderr}")
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(f"command returned invalid JSON: {result.stdout}") from error
    if result.returncode != 0 or not envelope.get("ok"):
        raise AssertionError(f"command failed: {result.returncode} {envelope}")
    return envelope


def _tree_identity(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run_smoke() -> None:
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        host_root = temporary / "host-skills"
        installed = host_root / "sdd-workflow"
        shutil.copytree(
            PACKAGE,
            installed,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        project = temporary / "consumer"
        proposal = project / "sdd/portable-smoke"
        proposal.mkdir(parents=True)
        archive = project / "sdd/archive"
        archive.mkdir()
        (archive / "INDEX.md").write_text("# SDD Archive\n\n", encoding="utf-8")
        (proposal / "proposal.md").write_text(
            """---
schema_version: 2
---
# portable-smoke
## 狀態
draft
## 類型
新功能
## 為什麼做
Prove a clean installed lifecycle.
## 要改什麼
- Complete one synthetic task.
## 影響範圍
- Temporary smoke project only.
""",
            encoding="utf-8",
        )
        (proposal / "tasks.md").write_text(
            """# Tasks

- [ ] Complete the portable smoke lifecycle.

## 驗收條件

- 情境：the installed runtime completes and archives this proposal.
""",
            encoding="utf-8",
        )

        discovery = _run_json(
            installed / "scripts/discover-runtime.py",
            [],
            cwd=project,
        )
        self_identity = discovery["runtime"]["handshake"]
        if (
            self_identity["distribution_id"] != "sdd-workflow"
            or self_identity["handshake_version"] != 1
        ):
            raise AssertionError("installed handshake identity is incompatible")

        cli = installed / "scripts/sdd.py"
        status = _run_json(
            cli,
            ["--root", str(project), "--json", "status", "portable-smoke"],
            cwd=project,
        )["data"]
        approved = _run_json(
            cli,
            [
                "--root",
                str(project),
                "--json",
                "approve",
                "portable-smoke",
                "--expected-snapshot",
                status["snapshot"]["snapshot_digest"],
            ],
            cwd=project,
        )["data"]
        status = _run_json(
            cli,
            ["--root", str(project), "--json", "status", "portable-smoke"],
            cwd=project,
        )["data"]
        if status["snapshot"]["snapshot_digest"] != approved["after_snapshot"]["snapshot_digest"]:
            raise AssertionError("approved snapshot is not reproducible")
        task = status["tasks"][0]
        _run_json(
            cli,
            [
                "--root",
                str(project),
                "--json",
                "complete-task",
                "portable-smoke",
                "1",
                "--expected-task-digest",
                task["task_digest"],
                "--expected-snapshot",
                status["snapshot"]["snapshot_digest"],
            ],
            cwd=project,
        )
        completed = _run_json(
            cli,
            ["--root", str(project), "--json", "status", "portable-smoke"],
            cwd=project,
        )["data"]
        if completed["completed_count"] != completed["task_count"]:
            raise AssertionError("installed lifecycle did not complete its task")

        before_doctor = _tree_identity(project)
        doctor = _run_json(
            cli,
            ["--root", str(project), "--json", "doctor"],
            cwd=project,
        )["data"]
        if _tree_identity(project) != before_doctor:
            raise AssertionError("readonly doctor changed project bytes")
        if (
            not doctor["healthy"]
            or Path(doctor["environment"]["install_path"]) != installed.resolve()
        ):
            raise AssertionError("doctor did not identify the installed package")

        _run_json(
            cli,
            [
                "--root",
                str(project),
                "--json",
                "archive",
                "portable-smoke",
                "--expected-snapshot",
                completed["snapshot"]["snapshot_digest"],
                "--summary",
                "Portable clean-install lifecycle smoke.",
            ],
            cwd=project,
        )
        terminal = _run_json(
            cli,
            ["--root", str(project), "--json", "doctor"],
            cwd=project,
        )["data"]
        if not terminal["healthy"] or (project / "sdd/portable-smoke").exists():
            raise AssertionError("archive lifecycle did not reach a healthy terminal state")

        if any(
            path.name == "__pycache__" or path.suffix == ".pyc"
            for path in installed.rglob("*")
        ):
            raise AssertionError("installed lifecycle created package residue")
        shutil.rmtree(installed)
        if installed.exists() or any(host_root.iterdir()):
            raise AssertionError("uninstall left files in the host Skill root")


def main() -> int:
    run_smoke()
    print("full-lifecycle-smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
