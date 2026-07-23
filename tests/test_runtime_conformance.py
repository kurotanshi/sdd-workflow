from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run-runtime-conformance"


class RuntimeConformanceRunnerTests(unittest.TestCase):
    def run_runner(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNNER), *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_list_json_exposes_versioned_case_to_rule_inventory(self) -> None:
        result = self.run_runner("--list", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        document = json.loads(result.stdout)
        self.assertTrue(document["ok"])
        self.assertEqual(document["output_version"], 1)
        self.assertEqual(document["manifest_version"], 1)
        self.assertEqual(document["registry_version"], 1)
        cases = {case["case_id"]: case for case in document["cases"]}
        self.assertEqual(
            cases["approval.fail-closed"]["rules"],
            ["SDD-APPROVAL-001"],
        )
        self.assertIn("archive.authority", cases)
        self.assertIn("cli.public-contract", cases)
        self.assertIn("package.install-smoke", cases)

    def test_rule_filter_executes_only_mapped_cases(self) -> None:
        result = self.run_runner(
            "--rule",
            "SDD-APPROVAL-001",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertTrue(document["ok"])
        self.assertEqual(document["selected_rules"], ["SDD-APPROVAL-001"])
        self.assertEqual(document["selected_cases"], ["approval.fail-closed"])
        self.assertEqual(len(document["results"]), 1)
        self.assertTrue(document["results"][0]["passed"])
        self.assertIn(
            "tests.test_approval",
            document["results"][0]["argv"],
        )

    def test_unknown_rule_is_stable_usage_error(self) -> None:
        result = self.run_runner("--rule", "SDD-NOT-A-RULE", "--json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "")
        document = json.loads(result.stdout)
        self.assertFalse(document["ok"])
        self.assertEqual(document["errors"][0]["code"], "ERROR_UNKNOWN_RULE")

    def test_case_and_rule_filters_intersect(self) -> None:
        result = self.run_runner(
            "--rule",
            "SDD-ARCHIVE-001",
            "--case",
            "archive.authority",
            "--list",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(
            [case["case_id"] for case in document["cases"]],
            ["archive.authority"],
        )


if __name__ == "__main__":
    unittest.main()
