from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import cost_benefit_experiment as experiment


FAKE_HOST = """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

if "--version" in sys.argv:
    print("fake-host 1.0")
    raise SystemExit(0)

prompt = sys.argv[-1]
root = Path.cwd()
if "plan.md" in prompt and "approved" not in prompt.lower():
    (root / "plan.md").write_text("signed subtraction plan\\n", encoding="utf-8")
    if os.environ.get("FAKE_PREAPPROVAL") == "1":
        calculator = root / "calculator.py"
        calculator.write_text(
            calculator.read_text(encoding="utf-8").replace(
                "return abs(left - right)", "return left - right"
            ),
            encoding="utf-8",
        )
elif "approved" in prompt.lower():
    calculator = root / "calculator.py"
    calculator.write_text(
        calculator.read_text(encoding="utf-8").replace(
            "return abs(left - right)", "return left - right"
        ),
        encoding="utf-8",
    )
    tests = root / "test_calculator.py"
    tests.write_text(
        tests.read_text(encoding="utf-8")
        + "\\n\\nclass SignedRegressionTests(unittest.TestCase):\\n"
        + "    def test_negative_result(self) -> None:\\n"
        + "        self.assertEqual(subtract(3, 7), -4)\\n",
        encoding="utf-8",
    )

print(json.dumps({
    "type": "item.completed",
    "item": {"id": "tool-1", "type": "file_change"},
}))
print(json.dumps({
    "type": "turn.completed",
    "model": "fake-model",
    "usage": {
        "input_tokens": 10,
        "cached_input_tokens": 2,
        "output_tokens": 3,
    },
}))
"""


class CostBenefitExperimentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = experiment.read_json(experiment.SPEC_PATH)

    def test_fixture_hashes_match_specification(self) -> None:
        for task in self.spec["tasks"].values():
            self.assertEqual(
                experiment.tree_sha256(ROOT / task["fixture"]),
                task["fixture_sha256"],
            )

    def test_prompts_expand_to_real_newlines(self) -> None:
        task = self.spec["tasks"]["small-bug"]
        prompt = experiment.prompt_for(self.spec, task, "control", "initial")
        self.assertIn("\n" + task["requirement"] + "\n\n", prompt)
        self.assertNotIn("\\n", prompt)

    def test_variant_order_is_stable(self) -> None:
        first = experiment.order_for(self.spec, "codex", "small-bug", 1)
        self.assertEqual(
            first,
            experiment.order_for(self.spec, "codex", "small-bug", 1),
        )
        self.assertEqual(sorted(first), ["control", "skill"])

    def test_tool_and_token_parsing_for_both_hosts(self) -> None:
        codex_events = [
            {
                "type": "item.completed",
                "item": {"id": "a", "type": "command_execution"},
            },
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 20,
                    "cached_input_tokens": 5,
                    "output_tokens": 4,
                },
            },
        ]
        claude_events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "id": "b", "name": "Write"}
                    ]
                },
            },
            {
                "type": "result",
                "usage": {
                    "input_tokens": 3,
                    "cache_creation_input_tokens": 7,
                    "cache_read_input_tokens": 11,
                    "output_tokens": 5,
                },
            },
        ]
        self.assertEqual(experiment.tool_usage(codex_events)[0], 1)
        self.assertEqual(experiment.tool_usage(claude_events)[0], 1)
        self.assertEqual(
            experiment.token_usage(codex_events, "codex")["total_tokens"],
            24,
        )
        self.assertEqual(
            experiment.token_usage(claude_events, "claude")["total_tokens"],
            26,
        )

    def test_invalid_run_classification(self) -> None:
        self.assertEqual(
            experiment.classify_invalid(
                returncode=124,
                timed_out=True,
                stdout="",
                stderr="",
                events=[],
            ),
            "turn-timeout",
        )
        self.assertIsNone(
            experiment.classify_invalid(
                returncode=1,
                timed_out=False,
                stdout='{"type":"result","text":"agent failed"}\n',
                stderr="",
                events=[{"type": "result", "text": "agent failed"}],
            )
        )
        self.assertIsNone(
            experiment.classify_invalid(
                returncode=0,
                timed_out=False,
                stdout='{"type":"system","plugins":["order-quota-doc"]}\n',
                stderr="",
                events=[{"type": "system", "plugins": ["order-quota-doc"]}],
            )
        )
        self.assertEqual(
            experiment.classify_invalid(
                returncode=1,
                timed_out=False,
                stdout='{"type":"result","is_error":true,"result":"Quota exceeded"}\n',
                stderr="",
                events=[
                    {
                        "type": "result",
                        "is_error": True,
                        "result": "Quota exceeded",
                    }
                ],
            ),
            "host-environment:quota",
        )

    def make_fake_host(self, directory: Path) -> Path:
        executable = directory / "fake-host"
        executable.write_text(FAKE_HOST, encoding="utf-8")
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
        return executable

    def run_fake(self, directory: Path, *, preapproval: bool = False) -> dict:
        executable = self.make_fake_host(directory)
        artifact_root = directory / "artifacts"
        arguments = argparse.Namespace(
            agent="codex",
            task="small-bug",
            variant="control",
            run_id="fake-run",
            pair_id="fake-pair",
            replicate=1,
            attempt=1,
            variant_order=["control", "skill"],
            artifact_root=artifact_root,
            timeout_seconds=30,
            agent_executable=str(executable),
            keep_workspace=False,
        )
        environment = {"FAKE_PREAPPROVAL": "1"} if preapproval else {}
        with mock.patch.dict(os.environ, environment, clear=False):
            code, _ = experiment.execute_one(arguments)
        self.assertEqual(code, 0)
        return json.loads(
            (
                artifact_root
                / "codex/small-bug/control/fake-run/result.json"
            ).read_text(encoding="utf-8")
        )

    def test_fake_host_completes_valid_control_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_fake(root)
            self.assertTrue(
                (
                    root
                    / "artifacts/codex/small-bug/control/fake-run/"
                    "proposal-final/sdd"
                ).is_dir()
            )
        self.assertTrue(result["valid"])
        self.assertTrue(result["task_success"])
        self.assertEqual(result["metrics"]["turn_count"], 2)
        self.assertEqual(result["metrics"]["tool_calls"], 2)
        self.assertEqual(result["metrics"]["tokens"]["total_tokens"], 26)
        self.assertEqual(result["safety"]["critical_violations"], [])

    def test_preapproval_product_change_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_fake(Path(directory), preapproval=True)
        self.assertEqual(
            result["safety"]["critical_violations"][0]["kind"],
            "product-change-before-approval",
        )

    def synthetic_result(
        self,
        *,
        agent: str,
        task: str,
        replicate: int,
        variant: str,
        calls: int,
        tokens: int,
        wall: float,
        valid: bool = True,
    ) -> dict:
        return {
            "valid": valid,
            "invalid_reason": None if valid else "turn-timeout",
            "run_id": f"{agent}-{task}-{replicate}-{variant}",
            "agent": agent,
            "task": task,
            "pair_id": f"{agent}-{task}-p{replicate}",
            "replicate": replicate,
            "attempt": 1,
            "variant": variant,
            "task_success": True,
            "metrics": {
                "tool_calls": calls,
                "tokens": {"total_tokens": tokens},
                "adjusted_wall_seconds": wall,
            },
            "safety": {"critical_violations": []},
        }

    def test_aggregation_is_paired_and_applies_gate2_rule(self) -> None:
        results = []
        for agent in self.spec["agents"]:
            for task in self.spec["task_order"]:
                for replicate in range(1, 4):
                    results.append(
                        self.synthetic_result(
                            agent=agent,
                            task=task,
                            replicate=replicate,
                            variant="control",
                            calls=10,
                            tokens=100,
                            wall=10,
                        )
                    )
                    expensive = task != "acceptance-change"
                    results.append(
                        self.synthetic_result(
                            agent=agent,
                            task=task,
                            replicate=replicate,
                            variant="skill",
                            calls=15 if expensive else 12,
                            tokens=150 if expensive else 120,
                            wall=15 if expensive else 12,
                        )
                    )
        summary = experiment.aggregate_results(results, self.spec)
        self.assertTrue(summary["complete"])
        self.assertEqual(
            summary["decision"]["jointly_exceeded_task_types"],
            ["small-bug", "medium-feature"],
        )
        self.assertTrue(summary["decision"]["gate2_eligible"])
        self.assertFalse(summary["decision"]["runtime_acceptable"])

    def test_invalid_attempt_is_retained_but_not_paired(self) -> None:
        invalid = self.synthetic_result(
            agent="codex",
            task="small-bug",
            replicate=1,
            variant="control",
            calls=0,
            tokens=0,
            wall=0,
            valid=False,
        )
        summary = experiment.aggregate_results([invalid], self.spec)
        self.assertEqual(summary["invalid_result_count"], 1)
        self.assertEqual(len(summary["invalid_runs"]), 1)
        self.assertEqual(summary["pairs"], [])


if __name__ == "__main__":
    unittest.main()
