from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/sdd-workflow/scripts"
STABLE_CONTRACT = ROOT / "docs/protocol/runtime-cli-v1.md"


class RuntimeContractTests(unittest.TestCase):
    def test_stable_v1_contract_covers_the_public_runtime_boundary(self) -> None:
        contract = STABLE_CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Contract version: `1`", contract)
        self.assertIn("Protocol: `sdd-protocol-1.0`", contract)
        for heading in (
            "## 2. Command selectors and arguments",
            "## 3. Exit classes",
            "## 4. JSON output contract",
            "## 5. Stable error actions",
            "## 7. Package-local discovery",
            "## 8. Runtime handshake",
            "## 9. Noninteractive and retry behavior",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, contract)
        for command in (
            "validate",
            "list",
            "status",
            "abandon-preflight",
            "approve",
            "begin-revision",
            "complete-task",
            "rebuild-index",
            "validate-index",
            "doctor",
            "archive",
            "abandon",
        ):
            with self.subTest(command=command):
                self.assertIn(
                    f"sdd.py [--root PATH] [--json] {command}",
                    contract,
                )
        for field in (
            "`output_version`",
            "`errors[].code`",
            "`errors[].action`",
            "`runtime_identity_sha256`",
            "`skill_sha256`",
        ):
            with self.subTest(field=field):
                self.assertIn(field, contract)

    def test_platform_matrix_is_explicit(self) -> None:
        contract = (ROOT / "docs/runtime.md").read_text()
        self.assertIn("| macOS | Supported |", contract)
        self.assertIn("| Linux | Supported |", contract)
        self.assertIn("| Windows | Best effort |", contract)
        self.assertIn("v0.4 transaction proposals", contract)
        self.assertIn("cannot fail or satisfy the required matrix", contract)

    def test_current_runtime_reports_version(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "sdd.py"), "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("sdd-workflow 1.0.0", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_launcher_fails_closed_when_python_is_missing(self) -> None:
        environment = dict(os.environ)
        environment["PATH"] = "/definitely-not-a-real-bin-directory"
        result = subprocess.run(
            ["/bin/sh", str(SCRIPTS / "sdd"), "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("ERROR_PYTHON_NOT_FOUND", result.stderr)
        self.assertIn("Python 3.11 or newer", result.stderr)
        self.assertIn("do not fall back to prose parsing", result.stderr)


if __name__ == "__main__":
    unittest.main()
