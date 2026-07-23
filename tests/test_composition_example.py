from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/compositions/security-review"
MANIFEST = EXAMPLE / "composition.json"
SMOKE = EXAMPLE / "run-smoke.py"


class SecurityReviewCompositionTests(unittest.TestCase):
    def test_manifest_declares_no_protocol_extension_or_domain_state(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["composition_version"], 1)
        self.assertEqual(manifest["lower_level_protocol"], "sdd-protocol-draft-0")
        self.assertEqual(manifest["state_model"], "sdd-protocol-only")
        self.assertEqual(manifest["core_extensions"], [])
        self.assertEqual(
            set(manifest["persistent_artifacts"]),
            {
                "proposal.md",
                "tasks.md",
                ".sdd/approval-manifest.json",
                ".sdd/metadata.json",
            },
        )

    def test_smoke_completes_with_standard_sdd_primitives_only(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SMOKE)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        result = json.loads(completed.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["state_model"], "sdd-protocol-only")
        self.assertEqual(result["completed_tasks"], 3)
        self.assertEqual(result["terminal_status"], "completed")
        self.assertTrue(result["doctor_healthy"])

    def test_example_explains_composition_boundary(self) -> None:
        readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "It does not add a security-review status, approval flag",
            readme,
        )
        self.assertIn("standard SDD artifacts", readme)
        self.assertIn("does not invoke an Agent", readme)


if __name__ == "__main__":
    unittest.main()
