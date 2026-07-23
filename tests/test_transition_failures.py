from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import main  # noqa: E402
from sdd_core.atomic_write import atomic_replace_bytes as real_atomic_replace_bytes  # noqa: E402


def invoke(arguments: list[str], root: Path) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(arguments, stdout=stdout, stderr=stderr, cwd=root)
    assert stderr.getvalue() == ""
    return code, json.loads(stdout.getvalue())


def status_snapshot(root: Path) -> str:
    code, result = invoke(
        ["--root", str(root), "--json", "status", "valid-simple"], root
    )
    assert code == 0
    return result["data"]["snapshot"]["snapshot_digest"]  # type: ignore[index]


def copy_fixture(root: Path) -> Path:
    target = root / "sdd/valid-simple"
    target.parent.mkdir(parents=True)
    shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
    return target


def fail_atomic_call(call_number: int):
    calls = 0

    def injected(path: Path, data: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == call_number:
            raise OSError(f"injected atomic failure {call_number}")
        real_atomic_replace_bytes(path, data)

    return injected


class TransitionFailureTests(unittest.TestCase):
    def test_approve_retry_recovers_manifest_only_stage(self) -> None:
        self._approve_retry_after_failure(2)

    def test_approve_retry_recovers_metadata_stage_before_status_commit(self) -> None:
        self._approve_retry_after_failure(3)

    def _approve_retry_after_failure(self, failure_call: int) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = copy_fixture(root)
            expected = status_snapshot(root)
            arguments = [
                "--root", str(root), "--json", "approve", "valid-simple",
                "--expected-snapshot", expected,
            ]
            with mock.patch(
                "sdd_core.transitions.atomic_replace_bytes",
                side_effect=fail_atomic_call(failure_call),
            ):
                failed, result = invoke(arguments, root)
            self.assertEqual(failed, 70)
            self.assertEqual(result["errors"][0]["code"], "ERROR_INTERNAL")  # type: ignore[index]
            self.assertIn("\ndraft\n", (target / "proposal.md").read_text())

            retried, result = invoke(arguments, root)
            self.assertEqual(retried, 0, result)
            self.assertIn("\napproved\n", (target / "proposal.md").read_text())
            self.assertTrue((target / ".sdd/approval-manifest.json").is_file())
            self.assertTrue((target / ".sdd/metadata.json").is_file())

    def test_begin_revision_retry_recovers_before_status_commit(self) -> None:
        self._revision_retry_after_failure(2)

    def test_begin_revision_retry_finalizes_after_status_commit(self) -> None:
        self._revision_retry_after_failure(3)

    def _revision_retry_after_failure(self, failure_call: int) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = copy_fixture(root)
            draft_snapshot = status_snapshot(root)
            approve_args = [
                "--root", str(root), "--json", "approve", "valid-simple",
                "--expected-snapshot", draft_snapshot,
            ]
            self.assertEqual(invoke(approve_args, root)[0], 0)
            proposal = target / "proposal.md"
            proposal.write_text(
                proposal.read_text().replace("Add deterministic parsing.", "Changed scope.")
            )
            expected = status_snapshot(root)
            arguments = [
                "--root", str(root), "--json", "begin-revision", "valid-simple",
                "--expected-snapshot", expected,
            ]
            with mock.patch(
                "sdd_core.transitions.atomic_replace_bytes",
                side_effect=fail_atomic_call(failure_call),
            ):
                failed, result = invoke(arguments, root)
            self.assertEqual(failed, 70)
            self.assertEqual(result["errors"][0]["code"], "ERROR_INTERNAL")  # type: ignore[index]

            retried, result = invoke(arguments, root)
            self.assertEqual(retried, 0, result)
            self.assertIn("\ndraft\n", proposal.read_text())
            metadata = json.loads((target / ".sdd/metadata.json").read_text())
            self.assertEqual(metadata["revision"]["phase"], "open")

    def test_managed_mutation_group_is_activated_coherently(self) -> None:
        skill = (ROOT / "skills/sdd-workflow/SKILL.md").read_text(encoding="utf-8")
        for command in (
            "--expected-snapshot",
            "begin-revision",
            "complete-task",
            "archive <short-name>",
            "abandon <short-name>",
        ):
            self.assertIn(command, skill)
        self.assertIn("Never edit these managed fields directly", skill)

    def test_complete_task_retry_finishes_staged_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = copy_fixture(root)
            draft_snapshot = status_snapshot(root)
            self.assertEqual(invoke([
                "--root", str(root), "--json", "approve", "valid-simple",
                "--expected-snapshot", draft_snapshot,
            ], root)[0], 0)
            status = invoke(
                ["--root", str(root), "--json", "status", "valid-simple"], root
            )[1]["data"]
            task = status["tasks"][1]  # type: ignore[index]
            arguments = [
                "--root", str(root), "--json", "complete-task", "valid-simple", "2",
                "--expected-task-digest", task["task_digest"],  # type: ignore[index]
                "--expected-snapshot", status["snapshot"]["snapshot_digest"],  # type: ignore[index]
            ]
            with mock.patch(
                "sdd_core.transitions.atomic_replace_bytes",
                side_effect=fail_atomic_call(2),
            ):
                failed, _ = invoke(arguments, root)
            self.assertEqual(failed, 70)
            self.assertIn("- [ ] Preserve one pending task", (target / "tasks.md").read_text())
            retried, result = invoke(arguments, root)
            self.assertEqual(retried, 0, result)
            self.assertEqual(result["data"]["result"], "APPLIED")
            self.assertIn("- [x] Preserve one pending task", (target / "tasks.md").read_text())

    def test_terminal_retry_matrix_across_pre_move_failure_points(self) -> None:
        for failure_kind in ("metadata", "status", "move"):
            with self.subTest(failure_kind=failure_kind):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    target = copy_fixture(root)
                    status = invoke(
                        ["--root", str(root), "--json", "status", "valid-simple"], root
                    )[1]["data"]
                    self.assertEqual(invoke([
                        "--root", str(root), "--json", "approve", "valid-simple",
                        "--expected-snapshot", status["snapshot"]["snapshot_digest"],
                    ], root)[0], 0)
                    status = invoke(
                        ["--root", str(root), "--json", "status", "valid-simple"], root
                    )[1]["data"]
                    task = status["tasks"][1]
                    self.assertEqual(invoke([
                        "--root", str(root), "--json", "complete-task", "valid-simple", "2",
                        "--expected-task-digest", task["task_digest"],
                        "--expected-snapshot", status["snapshot"]["snapshot_digest"],
                    ], root)[0], 0)
                    status = invoke(
                        ["--root", str(root), "--json", "status", "valid-simple"], root
                    )[1]["data"]
                    arguments = [
                        "--root", str(root), "--json", "archive", "valid-simple",
                        "--expected-snapshot", status["snapshot"]["snapshot_digest"],
                        "--summary", "failure matrix",
                    ]
                    if failure_kind == "move":
                        patcher = mock.patch(
                            "sdd_core.terminal_transitions.os.rename",
                            side_effect=OSError("injected move failure"),
                        )
                    else:
                        call = 1 if failure_kind == "metadata" else 2
                        patcher = mock.patch(
                            "sdd_core.terminal_transitions.atomic_replace_bytes",
                            side_effect=fail_atomic_call(call),
                        )
                    with patcher:
                        failed, _ = invoke(arguments, root)
                    self.assertEqual(failed, 70)
                    doctor = invoke(
                        ["--root", str(root), "--json", "doctor"], root
                    )[1]
                    doctor_codes = {
                        item["code"] for item in doctor["data"]["findings"]
                    }
                    if failure_kind == "metadata":
                        self.assertNotIn("PARTIAL_TRANSITION_DETECTED", doctor_codes)
                    else:
                        self.assertIn("PARTIAL_TRANSITION_DETECTED", doctor_codes)
                    if failure_kind == "move":
                        self.assertIn("STATUS_LOCATION_MISMATCH", doctor_codes)
                    retried, result = invoke(arguments, root)
                    self.assertEqual(retried, 0, result)
                    self.assertTrue(result["data"]["committed"])
                    self.assertFalse(target.exists())

    def test_terminal_index_failure_before_and_after_replace_never_moves_back(self) -> None:
        for failure_after_replace in (False, True):
            with self.subTest(failure_after_replace=failure_after_replace):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    target = copy_fixture(root)
                    status = invoke(
                        ["--root", str(root), "--json", "status", "valid-simple"], root
                    )[1]["data"]
                    self.assertEqual(invoke([
                        "--root", str(root), "--json", "approve", "valid-simple",
                        "--expected-snapshot", status["snapshot"]["snapshot_digest"],
                    ], root)[0], 0)
                    status = invoke(
                        ["--root", str(root), "--json", "status", "valid-simple"], root
                    )[1]["data"]
                    task = status["tasks"][1]
                    self.assertEqual(invoke([
                        "--root", str(root), "--json", "complete-task", "valid-simple", "2",
                        "--expected-task-digest", task["task_digest"],
                        "--expected-snapshot", status["snapshot"]["snapshot_digest"],
                    ], root)[0], 0)
                    status = invoke(
                        ["--root", str(root), "--json", "status", "valid-simple"], root
                    )[1]["data"]
                    arguments = [
                        "--root", str(root), "--json", "archive", "valid-simple",
                        "--expected-snapshot", status["snapshot"]["snapshot_digest"],
                        "--summary", "index failure",
                    ]
                    from sdd_core.archive_index import rebuild_archive_index as real_rebuild

                    def injected(archive_root, records):
                        if failure_after_replace:
                            real_rebuild(archive_root, records)
                        raise OSError("injected index failure")

                    with mock.patch(
                        "sdd_core.terminal_transitions.rebuild_archive_index",
                        side_effect=injected,
                    ):
                        code, result = invoke(arguments, root)
                    self.assertEqual(code, 1)
                    self.assertEqual(
                        result["errors"][0]["code"],
                        "COMMITTED_DERIVED_ARTIFACT_STALE",
                    )
                    destination = Path(result["data"]["destination"])
                    self.assertTrue(destination.is_dir())
                    self.assertFalse(target.exists())
                    doctor = invoke(
                        ["--root", str(root), "--json", "doctor"], root
                    )[1]
                    doctor_codes = {
                        item["code"] for item in doctor["data"]["findings"]
                    }
                    if failure_after_replace:
                        self.assertNotIn("ERROR_INDEX_STALE", doctor_codes)
                    else:
                        self.assertIn("ERROR_INDEX_STALE", doctor_codes)
                    retry_code, retry = invoke(arguments, root)
                    if failure_after_replace:
                        self.assertEqual(retry_code, 0, retry)
                        self.assertEqual(retry["data"]["result"], "ALREADY_APPLIED")
                    else:
                        self.assertEqual(retry_code, 1)
                        self.assertEqual(
                            retry["errors"][0]["code"],
                            "COMMITTED_DERIVED_ARTIFACT_STALE",
                        )


if __name__ == "__main__":
    unittest.main()
