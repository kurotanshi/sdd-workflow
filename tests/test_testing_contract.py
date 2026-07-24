from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
CLASSIFICATION = ROOT / "docs/testing.md"


class TestingContractTests(unittest.TestCase):
    def test_every_unittest_module_has_a_primary_classification(self) -> None:
        document = CLASSIFICATION.read_text(encoding="utf-8")
        modules = sorted(path.name for path in TESTS.glob("test_*.py"))
        self.assertGreater(len(modules), 0)
        for module in modules:
            with self.subTest(module=module):
                self.assertIn(f"`{module}`", document)

    def test_release_categories_are_explicit(self) -> None:
        document = CLASSIFICATION.read_text(encoding="utf-8")
        for category in (
            "unit",
            "parser",
            "transition",
            "transaction",
            "compatibility",
            "concurrency",
            "packaging",
            "integration",
        ):
            with self.subTest(category=category):
                self.assertIn(f"| `{category}` |", document)


if __name__ == "__main__":
    unittest.main()
