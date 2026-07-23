from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/sdd-workflow/scripts"


class RuntimeContractTests(unittest.TestCase):
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
        self.assertIn("sdd-workflow 0.6.0", result.stdout)
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
