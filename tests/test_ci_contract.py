from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


class CiContractTests(unittest.TestCase):
    def test_five_required_check_names_are_stable_jobs(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        required = {
            "unit",
            "fixtures",
            "package-validation",
            "docs-consistency",
            "install-smoke",
        }
        job_ids = set(re.findall(r"^  ([a-z][a-z0-9-]*):$", text, re.MULTILINE))
        self.assertTrue(required <= job_ids)
        for name in required:
            block = re.search(
                rf"^  {re.escape(name)}:\n(?P<body>(?:    .*\n|\n)*)",
                text,
                re.MULTILINE,
            )
            self.assertIsNotNone(block, name)
            self.assertIn(f"    name: {name}\n", block.group("body"))

    def test_required_checks_keep_their_distinct_contract_commands(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        for command in (
            "python -m unittest discover",
            "tests.test_schema_v2",
            "python tests/package_validation.py",
            "python tests/docs_consistency.py",
            "sh tests/trigger-contract.sh",
            "python tests/install_smoke.py",
        ):
            self.assertIn(command, text)
        self.assertIn("needs: unit-matrix", text)
        self.assertIn("needs: install-smoke-matrix", text)


if __name__ == "__main__":
    unittest.main()
