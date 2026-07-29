"""Regression coverage for supported archive-evidence recovery.

Reproduces the 2026-07-26 incident class: an archive directory missing
terminal status and `.sdd/` evidence blocks the derived INDEX rebuild of
every subsequent archive, and the only exit used to be manual edits that
the workflow forbids.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import main  # noqa: E402


ACTIVE_PROPOSAL_TEMPLATE = """---
schema_version: 2
---
# {short_name}
## 狀態
draft
## 類型
新功能
## 為什麼做
Reproduce the archive-evidence recovery scenario.
## 要改什麼
- Complete one synthetic task.
## 影響範圍
- Temporary test project only.
"""

ACTIVE_TASKS = """# Tasks

- [ ] Complete the synthetic task.

## 驗收條件

- 情境：the synthetic proposal archives cleanly.
"""

ARCHIVED_PROPOSAL_TEMPLATE = """---
schema_version: 2
---
# {short_name}
## 狀態
{status}
## 類型
新功能
## 為什麼做
Simulate a manual move that lost terminal evidence.
## 要改什麼
- Already implemented before the manual move.
## 影響範圍
- Archived directory without terminal status or machine evidence.
"""

DEVIANT_TASKS = """# Tasks

- [x] Implemented before the manual move.

## 驗收條件

- 情境：historical work preserved verbatim.
"""

INDEX_HEADER = "# SDD Archive\n\n"


def invoke(root: Path, *arguments: str) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(
        ["--root", str(root), "--json", *arguments],
        stdout=stdout,
        stderr=stderr,
        cwd=root,
    )
    assert stderr.getvalue() == ""
    return code, json.loads(stdout.getvalue())


def create_archived_directory(root: Path, name: str, short_name: str, status: str) -> None:
    directory = root / "sdd/archive" / name
    directory.mkdir(parents=True)
    (directory / "proposal.md").write_text(
        ARCHIVED_PROPOSAL_TEMPLATE.format(short_name=short_name, status=status),
        encoding="utf-8",
    )
    (directory / "tasks.md").write_text(DEVIANT_TASKS, encoding="utf-8")


def create_project(root: Path) -> None:
    archive = root / "sdd/archive"
    archive.mkdir(parents=True)
    (archive / "INDEX.md").write_text(INDEX_HEADER, encoding="utf-8")
    create_archived_directory(root, "2025-01-05-deviant", "deviant", "approved")


def create_active_proposal(root: Path, short_name: str) -> None:
    directory = root / "sdd" / short_name
    directory.mkdir(parents=True)
    (directory / "proposal.md").write_text(
        ACTIVE_PROPOSAL_TEMPLATE.format(short_name=short_name), encoding="utf-8"
    )
    (directory / "tasks.md").write_text(ACTIVE_TASKS, encoding="utf-8")


def archive_proposal(
    root: Path, short_name: str, summary: str
) -> tuple[int, dict[str, object]]:
    create_active_proposal(root, short_name)
    _, status = invoke(root, "status", short_name)
    invoke(
        root,
        "approve",
        short_name,
        "--expected-snapshot",
        status["data"]["snapshot"]["snapshot_digest"],
    )
    _, status = invoke(root, "status", short_name)
    invoke(
        root,
        "complete-task",
        short_name,
        "1",
        "--expected-task-digest",
        status["data"]["tasks"][0]["task_digest"],
        "--expected-snapshot",
        status["data"]["snapshot"]["snapshot_digest"],
    )
    _, status = invoke(root, "status", short_name)
    return invoke(
        root,
        "archive",
        short_name,
        "--expected-snapshot",
        status["data"]["snapshot"]["snapshot_digest"],
        "--summary",
        summary,
    )


def evidence_sha256(root: Path, name: str) -> tuple[str, str]:
    directory = root / "sdd/archive" / name
    return (
        hashlib.sha256((directory / "proposal.md").read_bytes()).hexdigest(),
        hashlib.sha256((directory / "tasks.md").read_bytes()).hexdigest(),
    )


class DeviantArchiveBlocksIndexTests(unittest.TestCase):
    def test_one_deviation_blocks_every_subsequent_archive_index_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_project(root)

            first_code, first = invoke(root, "rebuild-index")
            self.assertEqual(first_code, 1)
            self.assertEqual(first["errors"][0]["code"], "ARCHIVE_RECORD_MISMATCH")

            for short_name in ("first-change", "second-change"):
                code, envelope = archive_proposal(
                    root, short_name, f"Synthetic archive of {short_name}."
                )
                self.assertEqual(code, 1, envelope)
                self.assertEqual(
                    envelope["errors"][0]["code"], "COMMITTED_DERIVED_ARTIFACT_STALE"
                )
                self.assertTrue(envelope["data"]["committed"])
                self.assertFalse((root / "sdd" / short_name).exists())
                self.assertTrue(Path(root / envelope["data"]["destination"]).is_dir())
                self.assertEqual(
                    (root / "sdd/archive/INDEX.md").read_text(encoding="utf-8"),
                    INDEX_HEADER,
                )


class SupportedRecoveryTests(unittest.TestCase):
    def test_recovery_repairs_records_and_unblocks_future_archives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_project(root)
            code, envelope = archive_proposal(
                root, "first-change", "Synthetic archive of first-change."
            )
            self.assertEqual(code, 1, envelope)

            proposal_sha256, tasks_sha256 = evidence_sha256(root, "2025-01-05-deviant")
            code, preflight = invoke(
                root, "repair-archive-record", "2025-01-05-deviant"
            )
            self.assertEqual(code, 0, preflight)
            evidence = preflight["data"]["evidence"]
            self.assertEqual(evidence["proposal_sha256"], proposal_sha256)
            self.assertEqual(evidence["tasks_sha256"], tasks_sha256)
            self.assertIn("terminal_status", preflight["data"]["missing"])

            code, repaired = invoke(
                root,
                "repair-archive-record",
                "2025-01-05-deviant",
                "--terminal-status",
                "completed",
                "--summary",
                "Recovered after a manual move lost terminal evidence.",
                "--expected-proposal-sha256",
                proposal_sha256,
                "--expected-tasks-sha256",
                tasks_sha256,
            )
            self.assertEqual(code, 0, repaired)
            deviant = root / "sdd/archive/2025-01-05-deviant"
            self.assertTrue(deviant.is_dir())
            self.assertIn(
                "completed", (deviant / "proposal.md").read_text(encoding="utf-8")
            )

            code, rebuilt = invoke(root, "rebuild-index")
            self.assertEqual(code, 0, rebuilt)
            index = (root / "sdd/archive/INDEX.md").read_text(encoding="utf-8")
            self.assertIn(
                "deviant | completed | Recovered after a manual move lost terminal evidence.",
                index,
            )
            self.assertIn("first-change | completed |", index)

            code, validation = invoke(root, "validate-index")
            self.assertEqual(code, 0, validation)
            code, doctor = invoke(root, "doctor")
            self.assertEqual(code, 0, doctor)
            self.assertTrue(doctor["data"]["healthy"])

            code, envelope = archive_proposal(
                root, "third-change", "Synthetic archive of third-change."
            )
            self.assertEqual(code, 0, envelope)
            self.assertEqual(envelope["data"]["result"], "APPLIED")
            self.assertIn(
                "third-change | completed |",
                (root / "sdd/archive/INDEX.md").read_text(encoding="utf-8"),
            )


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class FailClosedTests(unittest.TestCase):
    def test_preflight_is_read_only_and_execute_fails_closed_on_evidence_mismatch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_project(root)
            before = tree_bytes(root)

            code, preflight = invoke(
                root, "repair-archive-record", "2025-01-05-deviant"
            )
            self.assertEqual(code, 0, preflight)
            self.assertEqual(tree_bytes(root), before)

            code, mismatch = invoke(
                root,
                "repair-archive-record",
                "2025-01-05-deviant",
                "--terminal-status",
                "completed",
                "--summary",
                "Attempt with stale evidence.",
                "--expected-proposal-sha256",
                "0" * 64,
                "--expected-tasks-sha256",
                preflight["data"]["evidence"]["tasks_sha256"],
            )
            self.assertEqual(code, 1, mismatch)
            self.assertEqual(
                mismatch["errors"][0]["code"], "ERROR_RECOVERY_EVIDENCE_MISMATCH"
            )
            self.assertEqual(
                mismatch["errors"][0]["action"], "rerun_repair_preflight"
            )
            self.assertEqual(tree_bytes(root), before)

    def test_execute_fails_closed_when_status_disagrees_with_directory_suffix(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_project(root)
            before = tree_bytes(root)
            proposal_sha256, tasks_sha256 = evidence_sha256(root, "2025-01-05-deviant")

            code, rejected = invoke(
                root,
                "repair-archive-record",
                "2025-01-05-deviant",
                "--terminal-status",
                "abandoned",
                "--summary",
                "Wrong terminal status for an unsuffixed directory.",
                "--expected-proposal-sha256",
                proposal_sha256,
                "--expected-tasks-sha256",
                tasks_sha256,
            )
            self.assertEqual(code, 1, rejected)
            self.assertEqual(
                rejected["errors"][0]["code"], "ERROR_RECOVERY_STATUS_MISMATCH"
            )
            self.assertEqual(tree_bytes(root), before)

    def test_execute_never_changes_an_existing_terminal_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            archive.mkdir(parents=True)
            (archive / "INDEX.md").write_text(INDEX_HEADER, encoding="utf-8")
            create_archived_directory(root, "2025-01-07-flipped", "flipped", "abandoned")
            before = tree_bytes(root)
            proposal_sha256, tasks_sha256 = evidence_sha256(root, "2025-01-07-flipped")

            code, rejected = invoke(
                root,
                "repair-archive-record",
                "2025-01-07-flipped",
                "--terminal-status",
                "completed",
                "--summary",
                "Attempt to rewrite an existing terminal status.",
                "--expected-proposal-sha256",
                proposal_sha256,
                "--expected-tasks-sha256",
                tasks_sha256,
            )
            self.assertEqual(code, 1, rejected)
            self.assertEqual(
                rejected["errors"][0]["code"], "ERROR_RECOVERY_STATUS_MISMATCH"
            )
            self.assertEqual(tree_bytes(root), before)

    def test_execute_without_summary_is_a_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_project(root)
            before = tree_bytes(root)
            proposal_sha256, tasks_sha256 = evidence_sha256(root, "2025-01-05-deviant")

            code, rejected = invoke(
                root,
                "repair-archive-record",
                "2025-01-05-deviant",
                "--terminal-status",
                "completed",
                "--expected-proposal-sha256",
                proposal_sha256,
                "--expected-tasks-sha256",
                tasks_sha256,
            )
            self.assertEqual(code, 2, rejected)
            self.assertEqual(rejected["errors"][0]["code"], "ERROR_USAGE")
            self.assertEqual(tree_bytes(root), before)

    def test_repair_fills_only_missing_fields_and_never_moves_the_directory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            archive.mkdir(parents=True)
            (archive / "INDEX.md").write_text(INDEX_HEADER, encoding="utf-8")
            create_archived_directory(root, "2025-01-06-orphan", "orphan", "completed")
            proposal_before = (
                archive / "2025-01-06-orphan/proposal.md"
            ).read_bytes()
            proposal_sha256, tasks_sha256 = evidence_sha256(root, "2025-01-06-orphan")

            code, preflight = invoke(root, "repair-archive-record", "2025-01-06-orphan")
            self.assertEqual(code, 0, preflight)
            self.assertEqual(
                preflight["data"]["missing"], ["machine_evidence", "index_row"]
            )

            code, repaired = invoke(
                root,
                "repair-archive-record",
                "2025-01-06-orphan",
                "--terminal-status",
                "completed",
                "--summary",
                "Backfilled machine evidence only.",
                "--expected-proposal-sha256",
                proposal_sha256,
                "--expected-tasks-sha256",
                tasks_sha256,
            )
            self.assertEqual(code, 0, repaired)
            self.assertEqual(repaired["data"]["repaired"], ["machine_evidence"])
            self.assertEqual(
                (archive / "2025-01-06-orphan/proposal.md").read_bytes(),
                proposal_before,
            )
            self.assertTrue((archive / "2025-01-06-orphan").is_dir())
            self.assertFalse((root / "sdd/orphan").exists())
            self.assertIn(
                "orphan | completed | Backfilled machine evidence only.",
                (archive / "INDEX.md").read_text(encoding="utf-8"),
            )


class RebuildIndexProvidedSummaryTests(unittest.TestCase):
    def test_provided_summary_completes_rebuild_when_only_summary_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            archive.mkdir(parents=True)
            (archive / "INDEX.md").write_text(INDEX_HEADER, encoding="utf-8")
            create_archived_directory(root, "2025-01-06-orphan", "orphan", "completed")

            code, blocked = invoke(root, "rebuild-index")
            self.assertEqual(code, 1)
            self.assertEqual(blocked["errors"][0]["code"], "UNKNOWN_STATE")

            code, rebuilt = invoke(
                root,
                "rebuild-index",
                "--directory",
                "2025-01-06-orphan",
                "--summary",
                "Backfilled summary for the orphan record.",
            )
            self.assertEqual(code, 0, rebuilt)
            index = (archive / "INDEX.md").read_text(encoding="utf-8")
            self.assertIn(
                "2025-01-06 | orphan | completed | Backfilled summary for the orphan record.",
                index,
            )

            code, again = invoke(root, "rebuild-index")
            self.assertEqual(code, 0, again)
            self.assertFalse(again["data"]["changed"])

    def test_provided_summary_is_rejected_when_summary_is_not_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            archive.mkdir(parents=True)
            create_archived_directory(root, "2025-01-06-orphan", "orphan", "completed")
            (archive / "INDEX.md").write_text(
                INDEX_HEADER + "- 2025-01-06 | orphan | completed | Existing summary.\n",
                encoding="utf-8",
            )
            before = (archive / "INDEX.md").read_bytes()

            code, rejected = invoke(
                root,
                "rebuild-index",
                "--directory",
                "2025-01-06-orphan",
                "--summary",
                "Conflicting summary.",
            )
            self.assertEqual(code, 1, rejected)
            self.assertEqual(
                rejected["errors"][0]["code"], "ERROR_RECOVERY_SUMMARY_UNEXPECTED"
            )
            self.assertEqual((archive / "INDEX.md").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
