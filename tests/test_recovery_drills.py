from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/baseline/valid-simple"
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import main  # noqa: E402
from sdd_core.atomic_write import atomic_replace_bytes  # noqa: E402


def invoke(root: Path, *arguments: str) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(
        ["--root", str(root), "--json", *arguments],
        stdout=stdout,
        stderr=stderr,
        cwd=root,
    )
    if stderr.getvalue():
        raise AssertionError(f"unexpected JSON-mode stderr: {stderr.getvalue()}")
    return code, json.loads(stdout.getvalue())


def prepare_complete(root: Path, short_name: str = "recovery-item") -> dict[str, object]:
    target = root / "sdd" / short_name
    target.parent.mkdir(parents=True)
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
    status = invoke(root, "status", short_name)[1]["data"]
    approved = invoke(
        root,
        "approve",
        short_name,
        "--expected-snapshot",
        status["snapshot"]["snapshot_digest"],  # type: ignore[index]
    )
    if approved[0] != 0:
        raise AssertionError(approved)
    status = invoke(root, "status", short_name)[1]["data"]
    pending = next(
        task for task in status["tasks"] if not task["completed"]  # type: ignore[index]
    )
    completed = invoke(
        root,
        "complete-task",
        short_name,
        str(pending["ordinal"]),
        "--expected-task-digest",
        pending["task_digest"],
        "--expected-snapshot",
        status["snapshot"]["snapshot_digest"],  # type: ignore[index]
    )
    if completed[0] != 0:
        raise AssertionError(completed)
    return invoke(root, "status", short_name)[1]["data"]  # type: ignore[return-value]


class RecoveryDrillsTests(unittest.TestCase):
    def test_second_process_with_same_snapshot_stably_fails_stale(self) -> None:
        for attempt in range(3):
            with self.subTest(attempt=attempt):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    active = root / "sdd/recovery-item"
                    active.parent.mkdir(parents=True)
                    shutil.copytree(FIXTURE, active)
                    proposal = active / "proposal.md"
                    tasks = active / "tasks.md"
                    proposal.write_text(
                        proposal.read_text(encoding="utf-8").replace(
                            "valid-simple",
                            "recovery-item",
                            1,
                        ),
                        encoding="utf-8",
                    )
                    tasks.write_text(
                        tasks.read_text(encoding="utf-8").replace(
                            "valid-simple",
                            "recovery-item",
                            1,
                        ),
                        encoding="utf-8",
                    )
                    status = invoke(root, "status", "recovery-item")[1]["data"]
                    command = [
                        sys.executable,
                        str(ROOT / "skills/sdd-workflow/scripts/sdd.py"),
                        "--root",
                        str(root),
                        "--json",
                        "approve",
                        "recovery-item",
                        "--expected-snapshot",
                        status["snapshot"]["snapshot_digest"],  # type: ignore[index]
                    ]
                    environment = os.environ.copy()
                    environment["PYTHONDONTWRITEBYTECODE"] = "1"
                    first = subprocess.run(
                        command,
                        cwd=root,
                        env=environment,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    second = subprocess.run(
                        command,
                        cwd=root,
                        env=environment,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(first.returncode, 0, first.stdout)
                    self.assertEqual(first.stderr, "")
                    self.assertEqual(second.returncode, 1, second.stdout)
                    self.assertEqual(second.stderr, "")
                    stale = json.loads(second.stdout)
                    self.assertEqual(
                        stale["errors"][0]["code"],
                        "ERROR_SNAPSHOT_MISMATCH",
                    )
                    self.assertEqual(
                        stale["errors"][0]["action"],
                        "refresh_status",
                    )
                    final_code, final = invoke(root, "status", "recovery-item")
                    self.assertEqual(final_code, 0, final)
                    self.assertEqual(final["data"]["status"], "approved")  # type: ignore[index]
                    self.assertTrue((active / ".sdd/metadata.json").is_file())
                    self.assertTrue((active / ".sdd/approval-manifest.json").is_file())

    def test_atomic_metadata_replace_never_exposes_partial_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            machine = Path(directory) / ".sdd"
            machine.mkdir()
            metadata = machine / "metadata.json"
            metadata.write_text('{"state":"before"}\n', encoding="utf-8")
            with mock.patch(
                "sdd_core.atomic_write.os.replace",
                side_effect=OSError("injected metadata replace failure"),
            ):
                with self.assertRaises(OSError):
                    atomic_replace_bytes(metadata, b'{"state":"after"}\n')
            self.assertEqual(
                json.loads(metadata.read_text(encoding="utf-8")),
                {"state": "before"},
            )
            self.assertEqual(list(machine.glob(".metadata.json.*.tmp")), [])

    def test_precommit_metadata_failure_preserves_draft_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = root / "sdd/recovery-item"
            active.parent.mkdir(parents=True)
            shutil.copytree(FIXTURE, active)
            proposal = active / "proposal.md"
            tasks = active / "tasks.md"
            proposal.write_text(
                proposal.read_text(encoding="utf-8").replace(
                    "valid-simple",
                    "recovery-item",
                    1,
                ),
                encoding="utf-8",
            )
            tasks.write_text(
                tasks.read_text(encoding="utf-8").replace(
                    "valid-simple",
                    "recovery-item",
                    1,
                ),
                encoding="utf-8",
            )
            status = invoke(root, "status", "recovery-item")[1]["data"]
            calls = 0

            def fail_metadata(path: Path, data: bytes) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected metadata write failure")
                atomic_replace_bytes(path, data)

            arguments = (
                "approve",
                "recovery-item",
                "--expected-snapshot",
                status["snapshot"]["snapshot_digest"],  # type: ignore[index]
            )
            with mock.patch(
                "sdd_core.transitions.atomic_replace_bytes",
                side_effect=fail_metadata,
            ):
                code, failed = invoke(root, *arguments)
            self.assertEqual(code, 70)
            self.assertEqual(failed["errors"][0]["code"], "ERROR_INTERNAL")  # type: ignore[index]
            self.assertIn("\ndraft\n", proposal.read_text(encoding="utf-8"))
            manifest = active / ".sdd/approval-manifest.json"
            metadata = active / ".sdd/metadata.json"
            self.assertIsInstance(json.loads(manifest.read_text(encoding="utf-8")), dict)
            self.assertFalse(metadata.exists())
            self.assertEqual(list(active.rglob("*.tmp")), [])

            doctor_code, doctor = invoke(root, "doctor")
            self.assertEqual(doctor_code, 1)
            finding_codes = {
                finding["code"] for finding in doctor["data"]["findings"]  # type: ignore[index]
            }
            self.assertIn("PARTIAL_TRANSITION_DETECTED", finding_codes)

            retry_code, retry = invoke(root, *arguments)
            self.assertEqual(retry_code, 0, retry)
            self.assertIn("\napproved\n", proposal.read_text(encoding="utf-8"))
            self.assertIsInstance(json.loads(metadata.read_text(encoding="utf-8")), dict)

    def test_archive_commit_survives_index_failure_and_rebuilds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = root / "sdd/recovery-item"
            status = prepare_complete(root)
            with mock.patch(
                "sdd_core.terminal_transitions.rebuild_archive_index",
                side_effect=OSError("injected post-move INDEX failure"),
            ):
                code, archived = invoke(
                    root,
                    "archive",
                    "recovery-item",
                    "--expected-snapshot",
                    status["snapshot"]["snapshot_digest"],  # type: ignore[index]
                    "--summary",
                    "recovery drill",
                )
            self.assertEqual(code, 1, archived)
            self.assertEqual(
                archived["errors"][0]["code"],  # type: ignore[index]
                "COMMITTED_DERIVED_ARTIFACT_STALE",
            )
            self.assertTrue(archived["data"]["committed"])  # type: ignore[index]
            destination = Path(archived["data"]["destination"])  # type: ignore[index]
            self.assertTrue(destination.is_dir())
            self.assertFalse(active.exists())
            self.assertIn(
                "\ncompleted\n",
                (destination / "proposal.md").read_text(encoding="utf-8"),
            )

            doctor_code, doctor = invoke(root, "doctor")
            self.assertEqual(doctor_code, 1)
            finding_codes = {
                finding["code"] for finding in doctor["data"]["findings"]  # type: ignore[index]
            }
            self.assertIn("ERROR_INDEX_STALE", finding_codes)

            self.assertEqual(invoke(root, "rebuild-index")[0], 0)
            self.assertEqual(invoke(root, "validate-index")[0], 0)
            healed_code, healed = invoke(root, "doctor")
            self.assertEqual(healed_code, 0, healed)
            self.assertTrue(healed["data"]["healthy"])  # type: ignore[index]
            self.assertTrue(destination.is_dir())
            self.assertFalse(active.exists())


if __name__ == "__main__":
    unittest.main()
