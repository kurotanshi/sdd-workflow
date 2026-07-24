from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "docs/decisions/2026-07-23-v010-lock-lease.md"
PLAYBOOK = ROOT / "docs/team-operations.md"
TRIAL = ROOT / "evals/team-trials/v010-controlled-trial-v1.json"


class TeamLockDecisionTests(unittest.TestCase):
    def test_no_go_decision_matches_quantitative_trial(self) -> None:
        decision = DECISION.read_text(encoding="utf-8")
        trial = json.loads(TRIAL.read_text(encoding="utf-8"))
        metrics = trial["metrics"]
        expected = {
            "0/6 mutation attempts": (
                metrics["concurrent_mutation_attempts"]["numerator"],
                metrics["concurrent_mutation_attempts"]["denominator"],
            ),
            "1/3 terminal or INDEX events": (
                metrics["index_conflicts"]["numerator"],
                metrics["index_conflicts"]["denominator"],
            ),
            "1/1 incidents": (
                metrics["recovery_interventions"]["numerator"],
                metrics["recovery_interventions"]["denominator"],
            ),
            "0/6 lifecycle operations": (
                metrics["workflow_bypass_observations"]["numerator"],
                metrics["workflow_bypass_observations"]["denominator"],
            ),
        }
        for text, (numerator, denominator) in expected.items():
            with self.subTest(text=text):
                self.assertIn(text, decision)
                self.assertIn(f"{numerator}/{denominator}", text)
        self.assertIn("**NO-GO** for lock, lease, enforced ownership", decision)
        self.assertIn("requires a new SDD proposal", decision)

    def test_playbook_separates_coordination_presentation_and_locking(self) -> None:
        playbook = PLAYBOOK.read_text(encoding="utf-8")
        for heading in (
            "## Cooperative coordination",
            "## Presentation-only ownership",
            "## Locking and leases",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, playbook)
        self.assertIn("does not grant mutation authority", playbook)
        self.assertIn("does not implement a lock or lease", playbook)
        self.assertIn("2026-07-23-v010-lock-lease.md", playbook)


if __name__ == "__main__":
    unittest.main()
