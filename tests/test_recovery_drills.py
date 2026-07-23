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
FIXTURE = ROOT / "tests/fixtures/baseline/valid-simple"
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import main  # noqa: E402


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
