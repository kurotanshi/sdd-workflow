from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
SNAPSHOT = FIXTURES / "cli-output-v1.json"
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import build_parser, main  # noqa: E402


def invoke(arguments: list[str], *, cwd: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(arguments, stdout=stdout, stderr=stderr, cwd=cwd)
    return exit_code, stdout.getvalue(), stderr.getvalue()


class CliSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    def test_public_command_inventory_matches_snapshot(self) -> None:
        parser = build_parser()
        subparsers = next(
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        actual = ["version", *subparsers.choices.keys()]
        self.assertEqual(actual, self.fixture["public_commands"])

    def test_representative_json_envelopes_match_snapshot(self) -> None:
        self.assertEqual(self.fixture["fixture_version"], 1)
        for case in self.fixture["cases"]:
            with self.subTest(case=case["id"]):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / "sdd").mkdir()
                    setup_fixture = case.get("setup_fixture")
                    if setup_fixture is not None:
                        destination = root / "sdd" / Path(setup_fixture).name
                        shutil.copytree(FIXTURES / setup_fixture, destination)
                    arguments = [
                        str(root) if item == "{root}" else item
                        for item in case["argv"]
                    ]
                    exit_code, stdout, stderr = invoke(arguments, cwd=root)
                    self.assertEqual(exit_code, case["exit_code"])
                    self.assertEqual(stderr, "")
                    decoder = json.JSONDecoder()
                    envelope, end = decoder.raw_decode(stdout)
                    self.assertEqual(stdout[end:], "\n")
                    self.assertEqual(
                        envelope["output_version"], self.fixture["output_version"]
                    )
                    self.assertEqual(envelope, case["envelope"])


if __name__ == "__main__":
    unittest.main()
