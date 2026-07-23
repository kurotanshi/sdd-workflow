from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/sample-web-api"
RUNNER = EXAMPLE / "run-walkthrough.py"


class SampleWebApiTests(unittest.TestCase):
    def test_walkthrough_replays_drift_revision_archive_and_recovery(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(RUNNER)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        result = json.loads(completed.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["drift_code"], "ERROR_APPROVED_PLAN_CHANGED")
        self.assertEqual(result["retained_completed_tasks"], 1)
        self.assertEqual(result["final_task_count"], 3)
        self.assertTrue(result["archive_committed"])
        self.assertTrue(result["index_rebuilt"])
        self.assertTrue(result["doctor_healthy"])
        self.assertGreaterEqual(result["git_commit_count"], 9)

    def test_documented_stages_match_machine_walkthrough(self) -> None:
        manifest = json.loads(
            (EXAMPLE / "walkthrough.json").read_text(encoding="utf-8")
        )
        readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
        self.assertEqual(manifest["walkthrough_version"], 1)
        self.assertEqual(len(manifest["stages"]), 12)
        for ordinal in range(1, 13):
            self.assertIn(f"{ordinal}.", readme)


if __name__ == "__main__":
    unittest.main()
