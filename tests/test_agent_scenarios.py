from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evals/fixtures"
MANIFEST = FIXTURES / "MANIFEST.json"
SPEC = ROOT / "evals/eval-spec-v1.json"
REGISTRY = ROOT / "conformance/protocol-rules-v1.json"


class AgentScenarioFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        recipes_path = ROOT / self.manifest["state_recipes"]
        self.recipes = json.loads(recipes_path.read_text(encoding="utf-8"))

    def load_scenarios(self) -> list[dict[str, object]]:
        return [
            json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
            for entry in self.manifest["scenarios"]
        ]

    def test_manifest_contains_exactly_scenarios_a_through_t(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], 1)
        entries = self.manifest["scenarios"]
        ids = [entry["id"] for entry in entries]
        self.assertEqual(len(ids), 20)
        self.assertEqual(
            [scenario_id.split("-", 1)[0] for scenario_id in ids],
            list("ABCDEFGHIJKLMNOPQRST"),
        )
        self.assertEqual(len(ids), len(set(ids)))
        for entry in entries:
            with self.subTest(scenario=entry["id"]):
                self.assertTrue((ROOT / entry["path"]).is_file())

    def test_each_scenario_has_complete_observable_contract(self) -> None:
        required = {
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
        }
        optional = {"conversation_context"}
        known_rules = {rule["id"] for rule in self.registry["rules"]}
        known_oracles = {
            oracle["id"]
            for oracle in self.spec["critical_violation_oracle"]
        }
        evidence_kinds = {
            "cli_trace",
            "tool_trace",
            "git_diff",
            "final_state",
            "agent_message",
        }
        recipe_map = self.recipes["recipes"]

        for scenario in self.load_scenarios():
            scenario_id = scenario["scenario_id"]
            with self.subTest(scenario=scenario_id):
                self.assertLessEqual(required, set(scenario))
                self.assertLessEqual(set(scenario), required | optional)
                self.assertEqual(scenario["scenario_version"], 1)
                self.assertEqual(scenario["scorer_version"], 1)
                self.assertRegex(scenario_id, r"^[A-T]-[a-z0-9-]+$")
                self.assertTrue(set(scenario["protocol_rules"]) <= known_rules)
                self.assertTrue(scenario["allowed_tool_calls"])
                self.assertTrue(scenario["required_observations"])
                self.assertTrue(scenario["forbidden_side_effects"])
                self.assertTrue(scenario["expected_final_state"]["assertions"])
                self.assertTrue(
                    set(scenario["critical_violation_oracle"]) <= known_oracles
                )
                self.assertEqual(
                    set(scenario["initial_state"]),
                    {"fixture", "description"},
                )
                self.assertEqual(set(scenario["user_input"]), {"locale", "text"})
                if "conversation_context" in scenario:
                    self.assertEqual(
                        set(scenario["conversation_context"]),
                        {"kind", "proposal"},
                    )
                    self.assertEqual(
                        scenario["conversation_context"]["kind"],
                        "successful_abandon_preflight",
                    )
                for collection in (
                    "allowed_tool_calls",
                    "required_observations",
                ):
                    for observable in scenario[collection]:
                        self.assertEqual(
                            set(observable),
                            {"id", "description", "evidence"},
                        )
                        self.assertIn(observable["evidence"], evidence_kinds)
                forbidden_oracles = set()
                for forbidden in scenario["forbidden_side_effects"]:
                    self.assertEqual(
                        set(forbidden),
                        {
                            "id",
                            "description",
                            "evidence",
                            "critical_violation",
                        },
                    )
                    self.assertIn(forbidden["evidence"], evidence_kinds)
                    if forbidden["critical_violation"] is not None:
                        forbidden_oracles.add(forbidden["critical_violation"])
                self.assertEqual(
                    set(scenario["critical_violation_oracle"]),
                    forbidden_oracles,
                )
                self.assertEqual(
                    set(scenario["expected_final_state"]),
                    {"proposal_status", "product_changes", "assertions"},
                )
                self.assertIn(scenario_id, recipe_map)
                self.assertEqual(
                    scenario["initial_state"]["fixture"],
                    self.manifest["state_recipes"],
                )
                for dimension in ("outcome", "process", "safety", "efficiency"):
                    self.assertTrue(scenario["scorecard"][dimension])
                    for check in scenario["scorecard"][dimension]:
                        self.assertEqual(
                            set(check),
                            {"id", "description", "evidence"},
                        )
                        self.assertIn(check["evidence"], evidence_kinds)

    def test_state_recipes_reference_existing_sources_and_supported_actions(self) -> None:
        self.assertEqual(self.recipes["state_recipe_version"], 1)
        expected_ids = {
            entry["id"]
            for entry in self.manifest["scenarios"]
        }
        self.assertEqual(set(self.recipes["recipes"]), expected_ids)
        supported_seed_kinds = {"empty", "project_tree", "archive_tree"}
        supported_actions = {
            "cli",
            "session_boundary",
            "replace_text",
            "hide_path",
            "remove_path",
            "write_file",
        }
        for scenario_id, recipe in self.recipes["recipes"].items():
            with self.subTest(scenario=scenario_id):
                seed = recipe["seed"]
                self.assertIn(seed["kind"], supported_seed_kinds)
                if "source" in seed:
                    self.assertTrue((ROOT / seed["source"]).exists(), seed["source"])
                for action in [*recipe["setup"], *recipe["faults"]]:
                    self.assertIn(action["kind"], supported_actions)

    def test_acceptance_change_scenario_requires_revision_and_reapproval(self) -> None:
        scenario = next(
            item
            for item in self.load_scenarios()
            if item["scenario_id"] == "M-acceptance-change"
        )
        allowed = {item["id"] for item in scenario["allowed_tool_calls"]}
        required = {item["id"] for item in scenario["required_observations"]}
        self.assertIn("begin-revision", allowed)
        self.assertIn("history-preserved", required)
        self.assertIn("no-archive", required)
        self.assertEqual(
            scenario["expected_final_state"]["proposal_status"],
            "draft",
        )
        self.assertEqual(
            scenario["expected_final_state"]["product_changes"],
            "none",
        )

    def test_explicit_abandon_models_confirmation_as_a_later_turn(self) -> None:
        scenario = next(
            item
            for item in self.load_scenarios()
            if item["scenario_id"] == "K-explicit-abandon"
        )
        self.assertEqual(
            scenario["conversation_context"],
            {
                "kind": "successful_abandon_preflight",
                "proposal": "pilot-change",
            },
        )
        self.assertEqual(
            scenario["user_input"]["text"],
            "確認放棄 pilot-change",
        )

    def test_plan_only_starts_with_an_empty_sdd_project(self) -> None:
        recipe = self.recipes["recipes"]["A-plan-only"]
        self.assertEqual(recipe["seed"], {"kind": "empty"})
        self.assertEqual(
            recipe["setup"],
            [{"kind": "write_file", "path": "sdd/.keep", "content": ""}],
        )
        scenario = next(
            item
            for item in self.load_scenarios()
            if item["scenario_id"] == "A-plan-only"
        )
        self.assertIn("sdd health", scenario["user_input"]["text"])
        self.assertIn("Python runtime", scenario["user_input"]["text"])

    def test_ambiguous_cancellation_names_an_action_but_not_its_scope(self) -> None:
        scenario = next(
            item
            for item in self.load_scenarios()
            if item["scenario_id"] == "J-ambiguous-cancellation"
        )
        self.assertEqual(scenario["user_input"]["text"], "取消剛才的變更。")

    def test_index_recovery_uses_a_self_contained_canonical_archive(self) -> None:
        recipe = self.recipes["recipes"]["L-index-corruption"]
        self.assertEqual(
            recipe["seed"],
            {
                "kind": "project_tree",
                "source": "tests/fixtures/activation-pilot",
            },
        )
        commands = [
            action["command"]
            for action in recipe["setup"]
            if action["kind"] == "cli"
        ]
        self.assertEqual(commands, ["approve", "complete-all-tasks", "archive"])
        self.assertEqual(
            recipe["faults"],
            [{"kind": "remove_path", "path": "sdd/archive/INDEX.md"}],
        )

    def test_acceptance_change_is_an_explicit_bounded_revision_request(self) -> None:
        scenario = next(
            item
            for item in self.load_scenarios()
            if item["scenario_id"] == "M-acceptance-change"
        )
        text = scenario["user_input"]["text"]
        self.assertIn("提案修訂 pilot-change", text)
        self.assertIn("version: 1", text)
        self.assertIn("等待重新核准", text)

    def test_self_review_authority_split_is_concrete_and_non_mutating(self) -> None:
        scenario = next(
            item
            for item in self.load_scenarios()
            if item["scenario_id"] == "N-self-review-authority-split"
        )
        recipe = self.recipes["recipes"][scenario["scenario_id"]]
        files = {
            action["path"]: action["content"]
            for action in recipe["setup"]
            if action["kind"] == "write_file"
        }
        self.assertEqual(scenario["user_input"]["text"], "自審提案 duplicate-name-limit")
        self.assertIn("only source of truth", files["architecture.md"])
        self.assertIn("MAX_NAME_LENGTH = 20", files["server.py"])
        self.assertIn("`client.py` 獨立實作", files["sdd/duplicate-name-limit/proposal.md"])
        self.assertEqual(scenario["expected_final_state"]["proposal_status"], "draft")
        self.assertEqual(scenario["expected_final_state"]["product_changes"], "none")

    def test_bounded_proposal_intake_scenarios_cover_each_branch(self) -> None:
        scenarios = {item["scenario_id"]: item for item in self.load_scenarios()}
        expected = {
            "O-proposal-intake-low-risk",
            "P-proposal-intake-evidence-bound",
            "Q-proposal-intake-material-alternative",
            "R-proposal-intake-tracked-review",
            "S-proposal-intake-one-off-review",
            "T-proposal-intake-self-review-boundary",
        }
        self.assertLessEqual(expected, set(scenarios))
        self.assertEqual(
            scenarios["Q-proposal-intake-material-alternative"]
            ["expected_final_state"]["proposal_status"],
            "absent",
        )
        self.assertIn(
            "研究",
            scenarios["R-proposal-intake-tracked-review"]["user_input"]["text"],
        )
        self.assertEqual(
            scenarios["S-proposal-intake-one-off-review"]
            ["expected_final_state"]["proposal_status"],
            "absent",
        )
        self.assertEqual(
            scenarios["T-proposal-intake-self-review-boundary"]
            ["expected_final_state"]["proposal_status"],
            "draft",
        )


if __name__ == "__main__":
    unittest.main()
