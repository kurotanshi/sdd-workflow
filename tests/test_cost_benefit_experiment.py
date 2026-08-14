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


FAKE_ACCEPTANCE_HOST = """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

if "--version" in sys.argv:
    print("fake-host 1.0")
    raise SystemExit(0)

prompt = sys.argv[-1]
root = Path.cwd()
if "Acceptance feedback" in prompt:
    (root / "plan.md").write_text("revised plan\\n", encoding="utf-8")
    if os.environ.get("FAKE_REVISION_MUTATE") == "1":
        labels = root / "labels.py"
        labels.write_text(
            labels.read_text(encoding="utf-8") + "# revision mutation\\n",
            encoding="utf-8",
        )
elif "approved" in prompt.lower():
    labels = root / "labels.py"
    labels.write_text(
        labels.read_text(encoding="utf-8") + "# approved change\\n",
        encoding="utf-8",
    )
else:
    (root / "plan.md").write_text("initial plan\\n", encoding="utf-8")

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


FAKE_SDD_HOST = """#!/usr/bin/env python3
import json
import sys

if "--version" in sys.argv:
    print("fake-host 1.0")
    raise SystemExit(0)

print(json.dumps({
    "type": "item.started",
    "item": {
        "id": "item_1",
        "type": "command_execution",
        "command": "python3 skills/sdd-workflow/scripts/discover-runtime.py",
    },
}))
print(json.dumps({
    "type": "turn.completed",
    "model": "fake-model",
    "usage": {
        "input_tokens": 1,
        "cached_input_tokens": 0,
        "output_tokens": 1,
    },
}))
"""


FAKE_ENV_HOST = """#!/usr/bin/env python3
import json
import os
import sys

if "--version" in sys.argv:
    print("fake-host 1.0")
    raise SystemExit(0)

print(json.dumps({
    "type": "item.completed",
    "item": {
        "id": "probe",
        "type": "command_execution",
        "probe": os.environ.get("FAKE_ISOLATION_PROBE", "missing"),
    },
}))
print(json.dumps({
    "type": "turn.completed",
    "model": "fake-model",
    "usage": {
        "input_tokens": 1,
        "cached_input_tokens": 0,
        "output_tokens": 1,
    },
}))
"""


class CostBenefitExperimentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = experiment.read_json(experiment.SPEC_PATH)
        self.spec_sha256 = experiment.sha256_file(experiment.SPEC_PATH)

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

    def make_fake_host(self, directory: Path, source: str = FAKE_HOST) -> Path:
        executable = directory / "fake-host"
        executable.write_text(source, encoding="utf-8")
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
        return executable

    def run_fake(
        self,
        directory: Path,
        *,
        preapproval: bool = False,
        task: str = "small-bug",
        host_source: str = FAKE_HOST,
        environment: dict[str, str] | None = None,
        spec_path: Path | None = None,
    ) -> dict:
        executable = self.make_fake_host(directory, host_source)
        artifact_root = directory / "artifacts"
        arguments = argparse.Namespace(
            spec=spec_path or experiment.SPEC_PATH,
            agent="codex",
            task=task,
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
        if environment is None:
            environment = {"FAKE_PREAPPROVAL": "1"} if preapproval else {}
        with mock.patch.dict(os.environ, environment, clear=False):
            code, _ = experiment.execute_one(arguments)
        self.assertEqual(code, 0)
        return json.loads(
            (
                artifact_root
                / f"codex/{task}/control/fake-run/result.json"
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
        self.assertEqual(result["turns"][0]["runtime_invocations"], 0)
        self.assertEqual(result["turns"][0]["unidentified_command_events"], 0)

    def test_preapproval_product_change_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_fake(Path(directory), preapproval=True)
        self.assertEqual(
            result["safety"]["critical_violations"][0]["kind"],
            "product-change-before-approval",
        )

    def test_unchanged_product_patch_during_revision_is_not_critical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_fake(
                Path(directory),
                task="acceptance-change",
                host_source=FAKE_ACCEPTANCE_HOST,
            )
        self.assertTrue(result["valid"])
        self.assertEqual(result["safety"]["critical_violations"], [])

    def test_product_mutation_during_revision_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_fake(
                Path(directory),
                task="acceptance-change",
                host_source=FAKE_ACCEPTANCE_HOST,
                environment={"FAKE_REVISION_MUTATE": "1"},
            )
        kinds = [
            violation["kind"]
            for violation in result["safety"]["critical_violations"]
        ]
        self.assertIn(
            "product-change-after-requirement-change-before-reapproval",
            kinds,
        )
        self.assertNotIn("product-change-before-approval", kinds)

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
            "experiment_id": self.spec["experiment_id"],
            "spec_sha256": self.spec_sha256,
            "host_isolation": {},
            "host_version": "fake-host 1.0",
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
        summary = experiment.aggregate_results(
            results, self.spec, expected_spec_sha256=self.spec_sha256
        )
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
        summary = experiment.aggregate_results(
            [invalid], self.spec, expected_spec_sha256=self.spec_sha256
        )
        self.assertEqual(summary["invalid_result_count"], 1)
        self.assertEqual(len(summary["invalid_runs"]), 1)
        self.assertEqual(summary["pairs"], [])

    def test_experiment_v3_spec_is_frozen_and_isolated(self) -> None:
        spec_path = ROOT / "evals/cost-benefit/experiment-v3.json"
        freeze_path = ROOT / "eval-runs/cost-benefit-v3-freeze.json"
        spec = experiment.read_json(spec_path)
        freeze = experiment.read_json(freeze_path)
        v2 = self.spec

        self.assertNotEqual(spec["experiment_id"], v2["experiment_id"])
        self.assertEqual(spec["artifact_root"], "eval-runs/cost-benefit-v3")
        self.assertNotEqual(
            ROOT / spec["artifact_root"], experiment.DEFAULT_ARTIFACT_ROOT
        )
        self.assertNotEqual(
            spec["smoke_artifact_root"], spec["artifact_root"]
        )

        frozen = spec["frozen"]
        self.assertEqual(
            frozen["runner_module_sha256"],
            experiment.sha256_file(ROOT / frozen["runner_module"]),
        )
        self.assertEqual(
            frozen["runtime_entrypoint_tree_sha256"],
            experiment.tree_sha256(ROOT / frozen["runtime_entrypoint"]),
        )
        skill_file = ROOT / spec["source"]["skill_path"] / "SKILL.md"
        self.assertEqual(
            spec["source"]["skill_sha256"],
            experiment.sha256_file(skill_file),
        )
        self.assertEqual(
            spec["source"]["skill_bytes"], skill_file.stat().st_size
        )
        for task in spec["tasks"].values():
            self.assertEqual(
                experiment.tree_sha256(ROOT / task["fixture"]),
                task["fixture_sha256"],
            )

        self.assertEqual(
            freeze["spec_sha256"], experiment.sha256_file(spec_path)
        )
        self.assertEqual(freeze["experiment_id"], spec["experiment_id"])
        self.assertEqual(
            freeze["frozen_hashes"]["runner_module_sha256"],
            frozen["runner_module_sha256"],
        )
        self.assertEqual(
            freeze["frozen_hashes"]["runtime_entrypoint_tree_sha256"],
            frozen["runtime_entrypoint_tree_sha256"],
        )
        self.assertEqual(
            freeze["frozen_hashes"]["skill_sha256"],
            spec["source"]["skill_sha256"],
        )

        self.assertEqual(spec["prompts"], v2["prompts"])
        self.assertEqual(spec["thresholds"], v2["thresholds"])
        for task_id, task in spec["tasks"].items():
            self.assertEqual(
                task["requirement"], v2["tasks"][task_id]["requirement"]
            )
            self.assertEqual(
                task.get("acceptance_change"),
                v2["tasks"][task_id].get("acceptance_change"),
            )
            self.assertEqual(
                task["turn_sequence"], v2["tasks"][task_id]["turn_sequence"]
            )

        for agent in spec["agents"].values():
            self.assertTrue(agent["isolation_environment"])
            self.assertIn("HOME", agent["isolation_environment"])
        self.assertEqual(spec["agents"]["codex"]["host_version"], "0.147.0")
        self.assertEqual(spec["agents"]["claude"]["host_version"], "2.1.232")

    def test_runtime_invocation_counting_for_both_hosts(self) -> None:
        codex_events = [
            {
                "type": "item.completed",
                "item": {
                    "id": "a",
                    "type": "command_execution",
                    "command": (
                        "python3 skills/sdd-workflow/scripts/sdd.py"
                        " --json status demo"
                    ),
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "id": "b",
                    "type": "command_execution",
                    "command": "ls -la",
                },
            },
            {
                "type": "item.completed",
                "item": {"id": "c", "type": "command_execution"},
            },
        ]
        claude_events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "d",
                            "name": "Bash",
                            "input": {
                                "command": (
                                    "python3 scripts/discover-runtime.py"
                                )
                            },
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "e",
                            "name": "Write",
                            "input": {},
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "id": "f", "name": "Bash"}
                    ]
                },
            },
        ]
        self.assertEqual(
            experiment.runtime_invocations(codex_events), (1, 1)
        )
        self.assertEqual(
            experiment.runtime_invocations(claude_events), (1, 1)
        )

    def test_summary_reports_per_phase_metrics(self) -> None:
        result = self.synthetic_result(
            agent="codex",
            task="acceptance-change",
            replicate=1,
            variant="skill",
            calls=10,
            tokens=100,
            wall=10,
        )
        result["turns"] = [
            {
                "turn": 1,
                "kind": "initial",
                "tool_calls": 2,
                "tokens": {"total_tokens": 10},
                "wall_seconds": 1.0,
                "runtime_invocations": 1,
                "unidentified_command_events": 0,
            },
            {
                "turn": 2,
                "kind": "approval",
                "tool_calls": 5,
                "tokens": {"total_tokens": 50},
                "wall_seconds": 3.0,
                "runtime_invocations": 2,
                "unidentified_command_events": 1,
            },
            {
                "turn": 3,
                "kind": "revision",
                "tool_calls": 1,
                "tokens": {"total_tokens": 5},
                "wall_seconds": 0.5,
                "runtime_invocations": 0,
                "unidentified_command_events": 0,
            },
            {
                "turn": 4,
                "kind": "approval",
                "tool_calls": 4,
                "tokens": {"total_tokens": 40},
                "wall_seconds": 2.0,
                "runtime_invocations": 3,
                "unidentified_command_events": 0,
            },
        ]
        summary = experiment.aggregate_results(
            [result], self.spec, expected_spec_sha256=self.spec_sha256
        )
        phases = {
            row["phase"]: row
            for row in summary["phases"]
            if row["agent"] == "codex"
            and row["task"] == "acceptance-change"
            and row["variant"] == "skill"
        }
        self.assertIn("turn-2-approval", phases)
        self.assertIn("turn-4-approval", phases)
        self.assertEqual(
            phases["turn-2-approval"]["median_runtime_invocations"], 2
        )
        self.assertEqual(
            phases["turn-4-approval"]["median_runtime_invocations"], 3
        )
        self.assertEqual(
            phases["turn-2-approval"]["unidentified_command_events"], 1
        )
        self.assertEqual(phases["turn-2-approval"]["median_tool_calls"], 5)
        self.assertEqual(
            phases["turn-4-approval"]["median_total_tokens"], 40
        )

    def test_workspace_is_created_outside_repository_ancestry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_fake(root)
            self.assertFalse((root / "artifacts/.workspaces").exists())
        self.assertTrue(result["valid"])

    def test_workspace_inside_repository_is_setup_failure(self) -> None:
        inside = ROOT / "eval-runs" / ".test-workspace"
        with mock.patch.object(
            experiment.tempfile, "mkdtemp", return_value=str(inside)
        ):
            with self.assertRaises(experiment.ExperimentError):
                experiment.create_workspace("codex", "small-bug", "control")

    def test_control_sdd_invocation_is_setup_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = self.make_fake_host(root, FAKE_SDD_HOST)
            arguments = argparse.Namespace(
                spec=experiment.SPEC_PATH,
                agent="codex",
                task="small-bug",
                variant="control",
                run_id="fake-run",
                pair_id="fake-pair",
                replicate=1,
                attempt=1,
                variant_order=["control", "skill"],
                artifact_root=root / "artifacts",
                timeout_seconds=30,
                agent_executable=str(executable),
                keep_workspace=False,
            )
            with self.assertRaises(experiment.ExperimentError):
                experiment.execute_one(arguments)

    def test_isolation_environment_is_applied_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = json.loads(
                experiment.SPEC_PATH.read_text(encoding="utf-8")
            )
            spec["agents"]["codex"]["isolation_environment"] = {
                "FAKE_ISOLATION_PROBE": "isolated"
            }
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            result = self.run_fake(
                root, host_source=FAKE_ENV_HOST, spec_path=spec_path
            )
            events = (
                root
                / "artifacts/codex/small-bug/control/fake-run/"
                "turn-1-initial/events.jsonl"
            ).read_text(encoding="utf-8")
        self.assertEqual(
            result["host_isolation"], {"FAKE_ISOLATION_PROBE": "isolated"}
        )
        self.assertIn("isolated", events)

    def test_aggregation_rejects_inconsistent_pair_host_baseline(self) -> None:
        control = self.synthetic_result(
            agent="codex",
            task="small-bug",
            replicate=1,
            variant="control",
            calls=1,
            tokens=1,
            wall=1,
        )
        skill = self.synthetic_result(
            agent="codex",
            task="small-bug",
            replicate=1,
            variant="skill",
            calls=1,
            tokens=1,
            wall=1,
        )
        skill["host_isolation"] = {"CODEX_HOME": "/different"}
        with self.assertRaises(experiment.ExperimentError):
            experiment.aggregate_results(
                [control, skill],
                self.spec,
                expected_spec_sha256=self.spec_sha256,
            )

    def test_runner_spec_is_parameterizable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = json.loads(
                experiment.SPEC_PATH.read_text(encoding="utf-8")
            )
            spec["experiment_id"] = "cost-benefit-test"
            spec_path = root / "experiment-test.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            result = self.run_fake(root, spec_path=spec_path)
            expected_hash = experiment.sha256_file(spec_path)
        self.assertEqual(result["experiment_id"], "cost-benefit-test")
        self.assertEqual(result["spec_sha256"], expected_hash)

    def test_aggregation_rejects_foreign_results(self) -> None:
        foreign = self.synthetic_result(
            agent="codex",
            task="small-bug",
            replicate=1,
            variant="control",
            calls=1,
            tokens=1,
            wall=1,
        )
        foreign["experiment_id"] = "cost-benefit-v0"
        with self.assertRaises(experiment.ExperimentError):
            experiment.aggregate_results(
                [foreign], self.spec, expected_spec_sha256=self.spec_sha256
            )
        stale = self.synthetic_result(
            agent="codex",
            task="small-bug",
            replicate=1,
            variant="control",
            calls=1,
            tokens=1,
            wall=1,
        )
        stale["spec_sha256"] = "0" * 64
        with self.assertRaises(experiment.ExperimentError):
            experiment.aggregate_results(
                [stale], self.spec, expected_spec_sha256=self.spec_sha256
            )


if __name__ == "__main__":
    unittest.main()
