from __future__ import annotations

import json
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/usability/first-workflow-15-minute.md"
RECORD = ROOT / "evals/usability/first-workflow-sample-v1.json"
RUNNER = ROOT / "examples/first-workflow/run.py"
SPEC = importlib.util.spec_from_file_location("first_workflow_run", RUNNER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load usability runner: {RUNNER}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
END_POINT = MODULE.END_POINT
PERSONA_ID = MODULE.PERSONA_ID
START_POINT = MODULE.START_POINT
run = MODULE.run


class FirstWorkflowUsabilityTests(unittest.TestCase):
    def test_hermetic_first_workflow_meets_bounded_acceptance(self) -> None:
        record = run()
        self.assertTrue(record["valid_run"])
        self.assertTrue(record["task_success"])
        self.assertTrue(record["within_budget"])
        self.assertFalse(record["transaction_protocol_read"])
        self.assertEqual(
            record["stages"],
            ["proposal", "approval", "implementation", "acceptance", "archive"],
        )
        self.assertTrue(record["doctor_healthy"])

    def test_versioned_record_uses_declared_boundaries(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        self.assertEqual(record["sample_count"], 1)
        self.assertEqual(record["valid_runs"], 1)
        self.assertEqual(record["task_successes"], 1)
        self.assertEqual(record["within_budget_runs"], 1)
        self.assertEqual(record["threshold_seconds"], 900)
        self.assertEqual(record["persona_id"], PERSONA_ID)
        self.assertEqual(record["start_point"], START_POINT)
        self.assertEqual(record["end_point"], END_POINT)
        self.assertEqual(record["human_participant_runs"], 0)
        self.assertEqual(record["decision"], "PASS_WITH_BOUNDED_EVIDENCE")

    def test_protocol_discloses_persona_scope_and_limitations(self) -> None:
        text = PROTOCOL.read_text(encoding="utf-8")
        for fact in (
            PERSONA_ID,
            START_POINT,
            END_POINT,
            "900 elapsed seconds",
            "1 complete automated proxy run",
            "no human participant",
            "not evidence of a 100%",
            "human success rate",
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, text)


if __name__ == "__main__":
    unittest.main()
