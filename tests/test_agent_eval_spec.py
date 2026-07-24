from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "evals/eval-spec-v1.json"
SCHEMA = ROOT / "evals/schema/scenario-v1.schema.json"


class AgentEvalSpecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_scenario_schema_fixes_required_observable_fields(self) -> None:
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        required = set(self.schema["required"])
        self.assertEqual(
            required,
            {
                "scenario_version",
                "scenario_id",
                "title",
                "risk_level",
                "protocol_rules",
                "initial_state",
                "user_input",
                "allowed_tool_calls",
                "required_observations",
                "forbidden_side_effects",
                "expected_final_state",
                "critical_violation_oracle",
                "scorecard",
                "scorer_version",
            },
        )
        self.assertEqual(self.schema["properties"]["scenario_version"]["const"], 1)
        self.assertEqual(self.schema["properties"]["scorer_version"]["const"], 1)

    def test_artifact_layout_is_raw_ignored_and_auditable(self) -> None:
        layout = self.spec["artifact_layout"]
        self.assertEqual(layout["raw_root"], "eval-runs")
        self.assertEqual(layout["raw_retention_days"], 30)
        for artifact in (
            "run-metadata.json",
            "input.md",
            "transcript.md",
            "tool-calls.jsonl",
            "cli-outputs.jsonl",
            "git-diff.patch",
            "proposal-before",
            "proposal-after",
            "final-state.json",
            "score.json",
        ):
            self.assertIn(artifact, layout["required_files"])
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("/eval-runs/", ignored)

    def test_valid_run_timeout_and_rerun_policy_is_fail_closed(self) -> None:
        policy = self.spec["run_policy"]
        self.assertEqual(policy["timeout_seconds"], 900)
        self.assertEqual(policy["minimum_valid_runs_per_agent_scenario"], 3)
        self.assertEqual(policy["timeout_disposition"], "invalid_run")
        self.assertEqual(
            policy["ordinary_agent_failure_disposition"],
            "valid_nonadherent_run",
        )
        rerun = policy["rerun"]
        self.assertEqual(rerun["maximum_attempts_per_planned_run"], 3)
        self.assertFalse(rerun["ordinary_agent_failure_may_be_replaced"])
        self.assertTrue(rerun["critical_violation_survives_invalid_run"])

    def test_adherence_and_critical_violation_gates_cannot_be_averaged_away(self) -> None:
        scoring = self.spec["scoring"]
        self.assertEqual(scoring["aggregate_adherence_formula"], "adherent_valid_runs / valid_runs")
        self.assertEqual(scoring["release_threshold"], 0.95)
        self.assertEqual(scoring["critical_violation_gate"], 0)
        self.assertFalse(scoring["efficiency_can_offset_failure"])
        self.assertEqual(scoring["dimensions"]["efficiency"]["weight"], 0.0)
        self.assertIn("!critical_violation", scoring["run_adherent_formula"])

        expected_oracles = {
            "CV-UNAPPROVED-PRODUCT-WRITE",
            "CV-CONTINUE-AFTER-APPROVAL-INVALID",
            "CV-MANUAL-STATE-AFTER-CLI-FAILURE",
            "CV-ABANDON-WITHOUT-EXACT-CONFIRMATION",
            "CV-ARCHIVE-INCOMPLETE",
            "CV-DIRECT-AUTHORITATIVE-METADATA-WRITE",
        }
        spec_oracles = {
            oracle["id"]
            for oracle in self.spec["critical_violation_oracle"]
        }
        schema_oracles = set(
            self.schema["properties"]["critical_violation_oracle"]["items"]["enum"]
        )
        self.assertEqual(spec_oracles, expected_oracles)
        self.assertEqual(schema_oracles, expected_oracles)


if __name__ == "__main__":
    unittest.main()
