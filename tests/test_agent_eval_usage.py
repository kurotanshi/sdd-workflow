from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.agent_eval_usage import UsageSummaryError, summarize_usage


class AgentEvalUsageTests(unittest.TestCase):
    def write_json(self, path: Path, value: object) -> None:
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")

    def make_run(
        self,
        root: Path,
        agent: str,
        *,
        valid: bool = True,
        terminal: bool = True,
    ) -> None:
        run = root / agent / "scenario" / f"{agent}-run"
        run.mkdir(parents=True)
        self.write_json(run / "score.json", {"valid_run": valid})
        self.write_json(run / "run-metadata.json", {"agent": agent})
        if agent == "codex":
            events = [
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 60,
                        "cache_write_input_tokens": 5,
                        "output_tokens": 20,
                    },
                }
            ]
        else:
            events = [
                {
                    "type": "result",
                    "usage": {
                        "input_tokens": 10,
                        "cache_read_input_tokens": 70,
                        "cache_creation_input_tokens": 20,
                        "output_tokens": 30,
                    },
                }
            ]
        if not terminal:
            events = [{"type": "assistant"}]
        (run / "agent-events.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in events),
            encoding="utf-8",
        )

    def test_normalizes_codex_and_claude_terminal_usage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_run(root, "codex")
            self.make_run(root, "claude")
            summary = summarize_usage(root)
        self.assertEqual(summary["valid_runs"], 2)
        self.assertTrue(summary["diagnostic_only"])
        codex = summary["by_agent"]["codex"]["metrics"]
        claude = summary["by_agent"]["claude"]["metrics"]
        self.assertEqual(codex["context_input_tokens"]["sum"], 100)
        self.assertEqual(codex["total_tokens"]["sum"], 120)
        self.assertEqual(claude["context_input_tokens"]["sum"], 100)
        self.assertEqual(claude["total_tokens"]["sum"], 130)

    def test_excludes_invalid_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_run(root, "codex", valid=False, terminal=False)
            self.make_run(root, "claude")
            summary = summarize_usage(root)
        self.assertEqual(summary["valid_runs"], 1)
        self.assertEqual(set(summary["by_agent"]), {"claude"})

    def test_missing_terminal_usage_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_run(root, "codex", terminal=False)
            with self.assertRaisesRegex(UsageSummaryError, "terminal usage"):
                summarize_usage(root)


if __name__ == "__main__":
    unittest.main()
