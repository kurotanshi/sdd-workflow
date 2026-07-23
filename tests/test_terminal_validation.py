from __future__ import annotations

import io
import json
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import load_archive_records  # noqa: E402
from sdd_core.cli import main  # noqa: E402


def invoke(root: Path, arguments: list[str]) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(["--root", str(root), "--json", *arguments], stdout=stdout, stderr=stderr, cwd=root)
    assert stderr.getvalue() == ""
    return code, json.loads(stdout.getvalue())


def tree_state(root: Path) -> dict[str, tuple[bytes, int, int]]:
    state: dict[str, tuple[bytes, int, int]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            info = path.stat()
            state[path.relative_to(root).as_posix()] = (
                path.read_bytes(), stat.S_IMODE(info.st_mode), info.st_mtime_ns
            )
    return state


class TerminalValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.target = self.root / "sdd/valid-simple"
        self.target.parent.mkdir(parents=True)
        shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", self.target)
        status = invoke(self.root, ["status", "valid-simple"])[1]["data"]
        self.assertEqual(invoke(self.root, [
            "approve", "valid-simple", "--expected-snapshot",
            status["snapshot"]["snapshot_digest"],
        ])[0], 0)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def complete_pending(self) -> dict[str, object]:
        status = invoke(self.root, ["status", "valid-simple"])[1]["data"]
        task = status["tasks"][1]
        code, _ = invoke(self.root, [
            "complete-task", "valid-simple", "2",
            "--expected-task-digest", task["task_digest"],
            "--expected-snapshot", status["snapshot"]["snapshot_digest"],
        ])
        self.assertEqual(code, 0)
        return invoke(self.root, ["status", "valid-simple"])[1]["data"]

    def test_archive_dry_run_validates_and_preserves_tree_metadata(self) -> None:
        status = self.complete_pending()
        before = tree_state(self.root)
        code, result = invoke(self.root, [
            "archive", "valid-simple",
            "--expected-snapshot", status["snapshot"]["snapshot_digest"],
            "--summary", "ready | safe", "--dry-run",
        ])
        self.assertEqual(code, 0, result)
        self.assertTrue(result["data"]["would_change"])
        self.assertIsNone(result["data"]["after_snapshot"])
        self.assertEqual(tree_state(self.root), before)
        self.assertTrue(self.target.is_dir())

    def test_archive_rejects_incomplete_stale_and_destination_collision(self) -> None:
        status = invoke(self.root, ["status", "valid-simple"])[1]["data"]
        incomplete = invoke(self.root, [
            "archive", "valid-simple", "--expected-snapshot",
            status["snapshot"]["snapshot_digest"], "--summary", "not done", "--dry-run",
        ])[1]
        self.assertEqual(incomplete["errors"][0]["code"], "ERROR_ARCHIVE_TASKS_INCOMPLETE")
        status = self.complete_pending()
        stale = invoke(self.root, [
            "archive", "valid-simple", "--expected-snapshot", "0" * 64,
            "--summary", "done", "--dry-run",
        ])[1]
        self.assertEqual(stale["errors"][0]["code"], "ERROR_SNAPSHOT_MISMATCH")
        import datetime
        destination = self.root / "sdd/archive" / f"{datetime.date.today().isoformat()}-valid-simple"
        destination.mkdir(parents=True)
        collision = invoke(self.root, [
            "archive", "valid-simple", "--expected-snapshot",
            status["snapshot"]["snapshot_digest"], "--summary", "done", "--dry-run",
        ])[1]
        self.assertEqual(collision["errors"][0]["code"], "ERROR_ARCHIVE_DESTINATION_COLLISION")

    def test_abandon_initial_draft_dry_run_preserves_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/draft-item"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            proposal = target / "proposal.md"
            proposal.write_text(proposal.read_text().replace("valid-simple", "draft-item", 1))
            tasks = target / "tasks.md"
            tasks.write_text(tasks.read_text().replace("valid-simple", "draft-item", 1))
            status = invoke(root, ["status", "draft-item"])[1]["data"]
            before = tree_state(root)
            code, result = invoke(root, [
                "abandon", "draft-item", "--expected-snapshot",
                status["snapshot"]["snapshot_digest"],
                "--summary", "stopped", "--dry-run",
            ])
            self.assertEqual(code, 0, result)
            self.assertEqual(tree_state(root), before)
            self.assertIn("-abandoned", result["data"]["destination"])

    def test_abandon_direct_draft_bypass_is_drift_but_revision_draft_is_valid(self) -> None:
        proposal = self.target / "proposal.md"
        proposal.write_text(proposal.read_text().replace("approved", "draft", 1))
        status = invoke(self.root, ["status", "valid-simple"])[1]["data"]
        bypass = invoke(self.root, [
            "abandon", "valid-simple", "--expected-snapshot",
            status["snapshot"]["snapshot_digest"],
            "--summary", "stop", "--dry-run",
        ])[1]
        self.assertEqual(bypass["errors"][0]["code"], "OUT_OF_BAND_DRIFT")

        proposal.write_text(proposal.read_text().replace("draft", "approved", 1))
        approved = invoke(self.root, ["status", "valid-simple"])[1]["data"]
        revision = invoke(self.root, [
            "begin-revision", "valid-simple", "--expected-snapshot",
            approved["snapshot"]["snapshot_digest"],
        ])
        self.assertEqual(revision[0], 0, revision)
        status = invoke(self.root, ["status", "valid-simple"])[1]["data"]
        valid = invoke(self.root, [
            "abandon", "valid-simple", "--expected-snapshot",
            status["snapshot"]["snapshot_digest"],
            "--summary", "authorized stop", "--dry-run",
        ])
        self.assertEqual(valid[0], 0, valid)

    def test_archive_commits_move_metadata_status_and_index(self) -> None:
        status = self.complete_pending()
        code, result = invoke(self.root, [
            "archive", "valid-simple", "--expected-snapshot",
            status["snapshot"]["snapshot_digest"], "--summary", "done | verified",
        ])
        self.assertEqual(code, 0, result)
        self.assertFalse(self.target.exists())
        destination = Path(result["data"]["destination"])
        self.assertTrue(destination.is_dir())
        self.assertIn("\ncompleted\n", (destination / "proposal.md").read_text())
        metadata = json.loads((destination / ".sdd/metadata.json").read_text())
        self.assertEqual(metadata["terminal"]["summary"], "done | verified")
        self.assertEqual(metadata["terminal"]["destination_directory"], destination.name)
        self.assertIn("done \\| verified", (destination.parent / "INDEX.md").read_text())
        retry_code, retry = invoke(self.root, [
            "archive", "valid-simple", "--expected-snapshot",
            status["snapshot"]["snapshot_digest"], "--summary", "done | verified",
        ])
        self.assertEqual(retry_code, 0, retry)
        self.assertFalse(retry["data"]["applied"])
        self.assertEqual(retry["data"]["result"], "ALREADY_APPLIED")

        ambiguous = invoke(self.root, [
            "archive", "valid-simple", "--expected-snapshot",
            status["snapshot"]["snapshot_digest"], "--summary", "different",
        ])[1]
        self.assertEqual(ambiguous["errors"][0]["code"], "AMBIGUOUS_STATE")

    def test_committed_retry_reports_stale_index_without_moving_back(self) -> None:
        status = self.complete_pending()
        arguments = [
            "archive", "valid-simple", "--expected-snapshot",
            status["snapshot"]["snapshot_digest"], "--summary", "done",
        ]
        first = invoke(self.root, arguments)[1]
        destination = Path(first["data"]["destination"])
        (destination.parent / "INDEX.md").unlink()
        code, retry = invoke(self.root, arguments)
        self.assertEqual(code, 1)
        self.assertEqual(retry["errors"][0]["code"], "COMMITTED_DERIVED_ARTIFACT_STALE")
        self.assertTrue(retry["data"]["committed"])
        self.assertTrue(destination.is_dir())
        self.assertFalse(self.target.exists())

    def test_abandon_multiline_summary_preserves_original_and_folds_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/draft-item"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            (target / "proposal.md").write_text(
                (target / "proposal.md").read_text().replace("valid-simple", "draft-item", 1)
            )
            (target / "tasks.md").write_text(
                (target / "tasks.md").read_text().replace("valid-simple", "draft-item", 1)
            )
            summary = root / "summary.txt"
            summary.write_bytes("first\r\nsecond | line\n".encode())
            status = invoke(root, ["status", "draft-item"])[1]["data"]
            code, result = invoke(root, [
                "abandon", "draft-item", "--expected-snapshot",
                status["snapshot"]["snapshot_digest"], "--summary-file", str(summary),
            ])
            self.assertEqual(code, 0, result)
            destination = Path(result["data"]["destination"])
            metadata = json.loads((destination / ".sdd/metadata.json").read_text())
            self.assertEqual(metadata["terminal"]["summary"], "first\r\nsecond | line\n")
            index = (destination.parent / "INDEX.md").read_text()
            self.assertIn("first ⏎ second \\| line ⏎ ", index)
            retry_code, retry = invoke(root, [
                "abandon", "draft-item", "--expected-snapshot",
                status["snapshot"]["snapshot_digest"], "--summary-file", str(summary),
            ])
            self.assertEqual(retry_code, 0, retry)
            self.assertEqual(retry["data"]["result"], "ALREADY_APPLIED")

    def test_terminal_stale_snapshot_without_operation_evidence_fails_closed(self) -> None:
        self.complete_pending()
        code, result = invoke(self.root, [
            "archive", "valid-simple", "--expected-snapshot", "0" * 64,
            "--summary", "stale", "--dry-run",
        ])
        self.assertEqual(code, 1)
        self.assertEqual(result["errors"][0]["code"], "ERROR_SNAPSHOT_MISMATCH")
        self.assertEqual(result["errors"][0]["action"], "refresh_status")
        self.assertTrue(self.target.is_dir())

    def test_completed_research_archives_and_reconstructs_conclusion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/research-item"
            target.mkdir(parents=True)
            (target / "proposal.md").write_text(
                "---\n"
                "schema_version: 2\n"
                "---\n"
                "# research-item\n\n"
                "## 狀態\n"
                "draft\n\n"
                "## 類型\n"
                "研究\n\n"
                "## 為什麼做\n"
                "Answer an evidence-gated question.\n\n"
                "## 要改什麼\n"
                "- Evaluate the question.\n\n"
                "## 影響範圍\n"
                "- Decision record only.\n\n"
                "## 結論\n",
                encoding="utf-8",
            )
            (target / "tasks.md").write_text(
                "# research-item 任務\n\n"
                "- [ ] Evaluate the evidence\n\n"
                "## 驗收條件\n"
                "- 情境：the conclusion answers the question\n",
                encoding="utf-8",
            )
            draft = invoke(root, ["status", "research-item"])[1]["data"]
            approved_code, _ = invoke(root, [
                "approve", "research-item", "--expected-snapshot",
                draft["snapshot"]["snapshot_digest"],
            ])
            self.assertEqual(approved_code, 0)

            proposal = target / "proposal.md"
            proposal.write_text(
                proposal.read_text(encoding="utf-8") + "- Use the managed v2 path.\n",
                encoding="utf-8",
            )
            active = invoke(root, ["status", "research-item"])[1]["data"]
            task = active["tasks"][0]
            completed_code, _ = invoke(root, [
                "complete-task", "research-item", "1",
                "--expected-task-digest", task["task_digest"],
                "--expected-snapshot", active["snapshot"]["snapshot_digest"],
            ])
            self.assertEqual(completed_code, 0)
            completed = invoke(root, ["status", "research-item"])[1]["data"]
            archive_code, archive_result = invoke(root, [
                "archive", "research-item", "--expected-snapshot",
                completed["snapshot"]["snapshot_digest"],
                "--summary", "research answered",
            ])
            self.assertEqual(archive_code, 0, archive_result)
            scan = load_archive_records(root / "sdd/archive")
            self.assertEqual(scan.diagnostics, ())
            record = next(item for item in scan.records if item.short_name == "research-item")
            self.assertEqual(record.research_conclusion, ("Use the managed v2 path.",))


if __name__ == "__main__":
    unittest.main()
