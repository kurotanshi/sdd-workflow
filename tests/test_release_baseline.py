from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORIC_BASELINE = ROOT / "docs/release-baseline-v0.6.md"
CURRENT_BASELINE = ROOT / "docs/release-baseline-v1.0.md"
CI_POLICY = ROOT / "docs/ci.md"
CLI_FIXTURE = ROOT / "tests/fixtures/cli-output-v1.json"


class ReleaseBaselineTests(unittest.TestCase):
    def test_v06_release_identity_remains_immutable(self) -> None:
        document = HISTORIC_BASELINE.read_text(encoding="utf-8")
        self.assertIn("`v0.6.0`", document)
        self.assertIn("`863f7691ffd96ce49a058ed87f5f8889b73946fc`", document)

    def test_v10_historical_identity_and_current_envelope_are_exact(self) -> None:
        document = CURRENT_BASELINE.read_text(encoding="utf-8")
        self.assertIn("historical release-candidate snapshot", document)
        self.assertIn("`v1.0.0`", document)
        self.assertIn("`sdd-protocol-1.0`", document)
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "skills/sdd-workflow/scripts/sdd.py"),
                "--json",
                "--version",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["output_version"], 1)
        self.assertEqual(envelope["data"]["engine_version"], "1.0.3")
        self.assertEqual(envelope["data"]["minimum_schema_version"], 1)
        self.assertEqual(envelope["data"]["maximum_schema_version"], 2)

    def test_baseline_indexes_commands_fixtures_and_contract_sources(self) -> None:
        document = HISTORIC_BASELINE.read_text(encoding="utf-8")
        fixture = json.loads(CLI_FIXTURE.read_text(encoding="utf-8"))
        for command in fixture["public_commands"]:
            with self.subTest(command=command):
                self.assertIn(f"\n{command}\n", document)
        for reference in (
            "tests/fixtures/cli-output-v1.json",
            "tests/fixtures/baseline/MANIFEST.json",
            "tests/fixtures/schema-v2/MANIFEST.json",
            "tests/fixtures/snapshot-v1.json",
            "architecture.md",
            "compatibility.md",
            "transaction-protocol.md",
            "2026-07-22-managed-mutation-activation.md",
            "tests/package_validation.py",
        ):
            with self.subTest(reference=reference):
                self.assertIn(reference, document)

        current = CURRENT_BASELINE.read_text(encoding="utf-8")
        for reference in (
            "protocol/core-v1.md",
            "protocol/runtime-cli-v1.md",
            "protocol/agent-adapter-contract.md",
            "protocol/versioning-policy-v1.md",
            "tests/fixtures/cli-output-v1.json",
            "reports/v1.0-conformance.md",
            "v1.0-agent-eval-summary.md",
            "security-trust-model.md",
            "non-goals-v1.md",
            "migration-v1.md",
            "rollback-v1.md",
        ):
            with self.subTest(current_reference=reference):
                self.assertIn(reference, current)

    def test_ci_policy_records_reproducible_matrix_and_hosted_gate(self) -> None:
        document = CI_POLICY.read_text(encoding="utf-8")
        for fact in (
            "macOS 15.7.3 arm64",
            "python:3.11-slim@sha256:",
            "python:3.13-slim@sha256:",
            "Git installed",
            "GitHub-hosted run",
            "runtime-deprecation",
            "exact head SHA",
            "run URL",
            "green run from an earlier action generation is",
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, document)


if __name__ == "__main__":
    unittest.main()
