from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "evals/team-evidence-spec-v1.json"
SCHEMA = ROOT / "evals/schema/team-evidence-v1.schema.json"
DOC = ROOT / "docs/team-evidence.md"


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


if __name__ == "__main__":
    unittest.main()
