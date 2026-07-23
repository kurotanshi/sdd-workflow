from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.agent_eval_lib import (
    build_eval_prompt,
    copy_repository,
    extract_trace,
    load_scenario,
    materialize_state,
)


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run-agent-eval"


class AgentEvalRunnerTests(unittest.TestCase):
    def test_explicit_abandon_prompt_contains_prior_preflight_evidence(self) -> None:
        scenario, recipes, _ = load_scenario("K-explicit-abandon")
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            copy_repository(workspace)
            materialize_state(workspace, "K-explicit-abandon", recipes)
            prompt, context = build_eval_prompt(workspace, scenario)
        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(context["kind"], "successful_abandon_preflight")
        self.assertRegex(context["proposal_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(context["tasks_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn(context["proposal_sha256"], prompt)
        self.assertIn(context["tasks_sha256"], prompt)
        self.assertIn("Current user request:\n確認放棄 pilot-change", prompt)

    def test_trace_classifier_ignores_skill_text_and_deduplicates_tool_lifecycle(
        self,
    ) -> None:
        events = [
            {
                "type": "item.completed",
                "item": {
                    "id": "skill-read",
                    "type": "command_execution",
                    "command": "sed -n '1,240p' skills/sdd-workflow/SKILL.md",
                    "aggregated_output": "sdd.py status approve complete-task",
                },
            },
            {
                "type": "item.started",
                "item": {
                    "id": "status-call",
                    "type": "command_execution",
                    "command": "python3 skills/sdd-workflow/scripts/sdd.py --json status pilot",
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "id": "status-call",
                    "type": "command_execution",
                    "command": "python3 skills/sdd-workflow/scripts/sdd.py --json status pilot",
                    "aggregated_output": '{"ok":true}',
                },
            },
        ]
        stdout = "\n".join(json.dumps(event) for event in events)
        _, cli_events, _, _ = extract_trace(stdout)
        self.assertEqual(len(cli_events), 1)
        self.assertEqual(cli_events[0]["type"], "item.completed")

    def make_fake_codex(self, directory: Path) -> Path:
        executable = directory / "fake-codex"
        executable.write_text(
            """#!/usr/bin/env python3
import json
import sys

if "--version" in sys.argv:
    print("fake-codex 1.2.3")
    raise SystemExit(0)

print(json.dumps({
    "type": "item.completed",
    "item": {
        "type": "command_execution",
        "command": "python3 skills/sdd-workflow/scripts/sdd.py --root . --json status pilot-change",
        "aggregated_output": "{\\"command\\":\\"status\\",\\"ok\\":true}"
    }
}))
print(json.dumps({
    "type": "item.completed",
    "item": {
        "type": "agent_message",
        "text": "The proposal is draft. Do you explicitly approve it?"
    }
}))
""",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        return executable

    def test_fake_codex_run_collects_complete_versioned_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            executable = self.make_fake_codex(temporary)
            artifact_root = temporary / "artifacts"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--agent",
                    "codex",
                    "--scenario",
                    "B-approval-boundary",
                    "--model",
                    "fake-model-1",
                    "--run-id",
                    "test-run-001",
                    "--agent-executable",
                    str(executable),
                    "--artifact-root",
                    str(artifact_root),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            document = json.loads(result.stdout)
            self.assertTrue(document["ok"])
            run = Path(document["artifact_directory"])
            required = {
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
            }
            self.assertLessEqual(required, {path.name for path in run.iterdir()})

            metadata = json.loads((run / "run-metadata.json").read_text())
            self.assertEqual(metadata["agent"], "codex")
            self.assertEqual(metadata["requested_model"], "fake-model-1")
            self.assertEqual(metadata["host_version"], "fake-codex 1.2.3")
            self.assertEqual(metadata["scenario_version"], 1)
            self.assertEqual(metadata["scorer_version"], 1)
            self.assertEqual(metadata["permission_mode"], "workspace-write")
            self.assertRegex(metadata["skill_commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(metadata["skill_sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("engine_version", metadata["runtime"])
            self.assertIsNotNone(metadata["execution_finished_at"])

            self.assertIn(
                "command_execution",
                (run / "tool-calls.jsonl").read_text(),
            )
            self.assertIn(
                "sdd.py",
                (run / "cli-outputs.jsonl").read_text(),
            )
            self.assertIn(
                "explicitly approve",
                (run / "transcript.md").read_text(),
            )
            final_state = json.loads((run / "final-state.json").read_text())
            self.assertEqual(final_state["agent_exit_code"], 0)
            self.assertFalse(final_state["timed_out"])

    def test_unknown_scenario_fails_without_creating_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            executable = self.make_fake_codex(temporary)
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--agent",
                    "codex",
                    "--scenario",
                    "Z-unknown",
                    "--model",
                    "fake-model-1",
                    "--agent-executable",
                    str(executable),
                    "--artifact-root",
                    str(temporary / "artifacts"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(json.loads(result.stdout)["ok"])

    def test_claude_prepare_only_records_stream_and_permission_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            executable = self.make_fake_codex(temporary)
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--agent",
                    "claude",
                    "--scenario",
                    "A-plan-only",
                    "--model",
                    "fake-claude-model-1",
                    "--run-id",
                    "test-claude-prepare",
                    "--agent-executable",
                    str(executable),
                    "--artifact-root",
                    str(temporary / "artifacts"),
                    "--prepare-only",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            run = Path(json.loads(result.stdout)["artifact_directory"])
            metadata = json.loads((run / "run-metadata.json").read_text())
            self.assertEqual(metadata["agent"], "claude")
            self.assertEqual(metadata["permission_mode"], "acceptEdits")
            self.assertIn("-p", metadata["host_command"])
            self.assertIn("stream-json", metadata["host_command"])
            self.assertTrue(metadata["prepare_only"])


if __name__ == "__main__":
    unittest.main()
