from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.team_evidence_trial import PRIVACY, run_trial


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "evals/team-evidence-spec-v1.json"
SCHEMA = ROOT / "evals/schema/team-evidence-v1.schema.json"
DOC = ROOT / "docs/team-evidence.md"
TRIAL = ROOT / "evals/team-trials/v010-controlled-trial-v1.json"


class TeamEvidenceContractTests(unittest.TestCase):
    def test_metric_definitions_have_explicit_denominators(self) -> None:
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        expected = {
            "multi_operator_proposals",
            "concurrent_mutation_attempts",
            "snapshot_stale_results",
            "short_name_conflicts",
            "index_conflicts",
            "worktree_isolation_runs",
            "recovery_interventions",
            "workflow_bypass_observations",
        }
        self.assertEqual(set(spec["metric_definitions"]), expected)
        for name, definition in spec["metric_definitions"].items():
            with self.subTest(name=name):
                self.assertTrue(definition["numerator"])
                self.assertTrue(definition["denominator"])
                self.assertTrue(definition["unit"])

    def test_privacy_defaults_fail_closed(self) -> None:
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        privacy = spec["privacy_defaults"]
        self.assertEqual(privacy["collection_mode"], "manual_opt_in")
        self.assertFalse(privacy["default_telemetry_enabled"])
        self.assertFalse(privacy["uploads_enabled"])
        self.assertFalse(privacy["contains_direct_identifiers"])
        self.assertFalse(privacy["contains_proposal_content"])
        self.assertFalse(privacy["contains_raw_transcripts"])
        self.assertEqual(privacy["raw_retention_days"], 0)

        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        properties = schema["properties"]["privacy"]["properties"]
        for key, expected in privacy.items():
            with self.subTest(key=key):
                self.assertEqual(properties[key]["const"], expected)

    def test_document_discloses_collection_and_zero_denominator_rules(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for fact in (
            "manual and opt-in",
            "enable no telemetry or upload path",
            "proposal, task, source, metadata, or customer content",
            "prompts, raw Agent transcripts",
            "default retention of zero days",
            "A zero denominator is reported as `0/0`",
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, text)

    def test_controlled_trial_is_reproducible_and_aggregate_only(self) -> None:
        report = run_trial()
        self.assertEqual(report["sample"]["operators"], 2)
        self.assertEqual(report["sample"]["proposals"], 2)
        self.assertEqual(report["privacy"], PRIVACY)
        self.assertEqual(set(report["metrics"]), set(
            json.loads(SPEC.read_text(encoding="utf-8"))["metric_definitions"]
        ))
        for metric in report["metrics"].values():
            self.assertLessEqual(metric["numerator"], metric["denominator"])

    def test_versioned_trial_records_every_metric_and_observation_period(self) -> None:
        report = json.loads(TRIAL.read_text(encoding="utf-8"))
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.assertEqual(report["evidence_version"], 1)
        self.assertEqual(set(report["metrics"]), set(spec["metric_definitions"]))
        self.assertEqual(report["privacy"], spec["privacy_defaults"])
        self.assertLess(
            report["observation_period"]["started_at"],
            report["observation_period"]["finished_at"],
        )
        self.assertEqual(report["friction_entry_ids"], [])


if __name__ == "__main__":
    unittest.main()
