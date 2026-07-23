from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import main  # noqa: E402


HASH_LINE = re.compile(r"^(proposal\.md|tasks\.md) sha256: ([0-9a-f]{64})$", re.MULTILINE)


def invoke(root: Path, *, json_mode: bool) -> tuple[int, str, str]:
    arguments = ["--root", str(root)]
    if json_mode:
        arguments.append("--json")
    arguments.extend(("abandon-preflight", "abandon-snapshot"))
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(arguments, stdout=stdout, stderr=stderr, cwd=root)
    return exit_code, stdout.getvalue(), stderr.getvalue()


class AbandonmentPreflightTests(unittest.TestCase):
    def make_project(self, directory: str) -> Path:
        root = Path(directory)
        target = root / "sdd/abandon-snapshot"
        target.parent.mkdir(parents=True)
        shutil.copytree(ROOT / "tests/fixtures/baseline/abandon-snapshot", target)
        return root

    def test_human_preflight_prints_both_raw_hashes_and_does_not_mutate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            proposal = root / "sdd/abandon-snapshot/proposal.md"
            tasks = root / "sdd/abandon-snapshot/tasks.md"
            before = (proposal.read_bytes(), tasks.read_bytes())

            exit_code, stdout, stderr = invoke(root, json_mode=False)

            self.assertEqual(exit_code, 0)
            hashes = dict(HASH_LINE.findall(stdout))
            self.assertEqual(set(hashes), {"proposal.md", "tasks.md"})
            self.assertIn("(unreliable)", stdout)
            self.assertIn("will not be reverted", stdout)
            self.assertIn("reply exactly: 確認放棄 abandon-snapshot", stdout)
            self.assertIn("ERROR_INVALID_TASK_CHECKBOX", stderr)
            self.assertEqual((proposal.read_bytes(), tasks.read_bytes()), before)

    def test_json_preflight_degrades_task_error_and_contains_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            exit_code, stdout, stderr = invoke(root, json_mode=True)

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr, "")
            envelope = json.loads(stdout)
            self.assertTrue(envelope["ok"])
            self.assertEqual(envelope["errors"], [])
            self.assertEqual(
                [item["code"] for item in envelope["warnings"]],
                ["ERROR_INVALID_TASK_CHECKBOX"],
            )
            self.assertFalse(envelope["data"]["task_counts_reliable"])
            self.assertFalse(envelope["data"]["working_tree_reverted"])
            snapshot = envelope["data"]["snapshot"]
            for key in ("proposal_sha256", "tasks_sha256", "snapshot_digest"):
                self.assertRegex(snapshot[key], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
