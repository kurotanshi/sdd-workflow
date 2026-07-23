from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE = ROOT / "conformance"
RUNNER = ROOT / "scripts/run-adapter-conformance"
sys.path.insert(0, str(CONFORMANCE))

from hermetic_adapter import (  # noqa: E402
    DESCRIPTOR,
    AdapterDecision,
    HermeticPolicyAdapter,
    evaluate,
)


class HermeticAdapterTests(unittest.TestCase):
    def run_adapter(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNNER), *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_descriptor_is_test_only_and_claims_no_agent_host(self) -> None:
        self.assertEqual(DESCRIPTOR["implementation_kind"], "hermetic-test")
        self.assertEqual(DESCRIPTOR["supported_hosts"], [])
        self.assertEqual(DESCRIPTOR["adapter_contract_version"], 1)

    def test_all_applicable_scenarios_pass(self) -> None:
        result = self.run_adapter("--json")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stderr, "")
        document = json.loads(result.stdout)
        self.assertTrue(document["ok"])
        self.assertEqual(len(document["selected_scenarios"]), 10)
        self.assertTrue(all(item["passed"] for item in document["results"]))
        self.assertEqual(document["adapter"]["supported_hosts"], [])

    def test_policy_is_not_keyed_by_scenario_id(self) -> None:
        source = (CONFORMANCE / "hermetic_adapter.py").read_text(encoding="utf-8")
        scenarios = json.loads(
            (CONFORMANCE / "adapter-scenarios-v1.json").read_text(encoding="utf-8")
        )
        for case in scenarios["scenarios"]:
            self.assertNotIn(case["id"], source)

    def test_requirement_change_wording_still_routes_to_revision(self) -> None:
        decision = HermeticPolicyAdapter().decide(
            "approved-one-task-complete",
            ["需求變更：驗收結果需要支援 IPv6"],
        )
        self.assertIn("begin-revision", decision.actions)
        self.assertIn("handoff-for-reapproval", decision.actions)
        self.assertNotIn("complete-task", decision.actions)

    def test_evaluator_rejects_a_prohibited_trace(self) -> None:
        case = {
            "id": "adapter.synthetic",
            "required_actions": ["status"],
            "prohibited_actions": ["approve"],
            "expected_handoff": "human",
        }
        result = evaluate(
            case,
            AdapterDecision(("status", "approve"), "human"),
        )
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["differences"][0]["path"],
            "/prohibited_actions",
        )


if __name__ == "__main__":
    unittest.main()
