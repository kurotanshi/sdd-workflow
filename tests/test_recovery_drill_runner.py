from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.recovery_drill_runner import (
    DEFAULT_MANIFEST,
    DrillRunnerError,
    load_manifest,
    run_drills,
)


class RecoveryDrillRunnerTests(unittest.TestCase):
    def test_manifest_reuses_required_regression_layers(self) -> None:
        manifest = load_manifest(DEFAULT_MANIFEST)
        selectors = {
            selector
            for drill in manifest["drills"]
            for selector in drill["selectors"]
        }
        for required in (
            "tests.test_transition_failures",
            "tests.test_atomic_write",
            "tests.test_archive_cli",
            "tests.test_doctor",
            "tests.test_concurrency",
            "tests.test_compatibility",
        ):
            with self.subTest(required=required):
                self.assertIn(required, selectors)

    def test_selected_drill_runs_in_isolation(self) -> None:
        result = run_drills(
            selected_ids=["atomic-write.no-partial"],
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"], {"requested": 1, "passed": 1, "failed": 0})
        self.assertGreater(result["results"][0]["test_count"], 0)

    def test_unknown_drill_fails_closed(self) -> None:
        with self.assertRaisesRegex(DrillRunnerError, "unknown drill ID"):
            run_drills(selected_ids=["unknown"])

    def test_unsafe_selector_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "manifest_version": 1,
                        "drills": [
                            {
                                "id": "unsafe",
                                "selectors": ["tests.test_ok; touch unexpected"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DrillRunnerError, "unsafe selector"):
                load_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
