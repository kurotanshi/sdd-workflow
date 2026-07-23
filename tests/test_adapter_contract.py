from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/protocol/agent-adapter-contract.md"
GUIDE = ROOT / "docs/adapter-authoring-guide.md"
SCENARIOS = ROOT / "conformance/adapter-scenarios-v1.json"


class AdapterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = CONTRACT.read_text(encoding="utf-8")
        cls.guide = GUIDE.read_text(encoding="utf-8")
        cls.scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))

    def test_contract_covers_required_boundaries(self) -> None:
        for heading in (
            "## Runtime discovery",
            "## Noninteractive invocation",
            "## Phase and approval mapping",
            "## Ambiguity and proposal selection",
            "## Mutation boundary",
            "## Error actions and human handoff",
            "## Terminal safety",
            "## Conformance",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.contract)
        for term in (
            "package-local",
            "errors[].code",
            "errors[].action",
            "acceptance",
            "begin-revision",
            "required human action",
        ):
            with self.subTest(term=term):
                self.assertIn(term, self.contract)

    def test_scenario_inventory_is_versioned_and_complete(self) -> None:
        self.assertEqual(self.scenarios["scenario_version"], 1)
        self.assertEqual(self.scenarios["adapter_contract_version"], 1)
        self.assertEqual(
            self.scenarios["protocol_version"],
            "sdd-protocol-1.0",
        )
        cases = self.scenarios["scenarios"]
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 10)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["turns"])
                self.assertTrue(case["required_actions"])
                self.assertTrue(case["prohibited_actions"])
                self.assertTrue(case["expected_handoff"])

    def test_acceptance_change_requires_revision_and_reapproval(self) -> None:
        case = next(
            case
            for case in self.scenarios["scenarios"]
            if case["id"] == "adapter.acceptance-requirement-change"
        )
        self.assertIn("begin-revision", case["required_actions"])
        self.assertIn("handoff-for-reapproval", case["required_actions"])
        self.assertIn("complete-task", case["prohibited_actions"])
        self.assertEqual(case["expected_handoff"], "explicit-reapproval")

    def test_test_adapter_cannot_become_a_host_support_claim(self) -> None:
        self.assertIn(
            "A hermetic or scripted adapter MUST identify itself as a test "
            "implementation.",
            self.contract,
        )
        self.assertIn(
            'Use `implementation_kind: "hermetic-test"` for a scripted adapter.',
            self.guide,
        )
        self.assertIn(
            "Hermetic success proves contract logic only.",
            self.guide,
        )


if __name__ == "__main__":
    unittest.main()
