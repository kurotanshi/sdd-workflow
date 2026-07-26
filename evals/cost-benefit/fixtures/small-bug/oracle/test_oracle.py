import unittest
from pathlib import Path

from calculator import add, subtract


class SmallBugOracleTests(unittest.TestCase):
    def test_subtraction_keeps_sign(self) -> None:
        self.assertEqual(subtract(3, 7), -4)

    def test_add_is_unchanged(self) -> None:
        self.assertEqual(add(-2, 5), 3)

    def test_negative_regression_is_public(self) -> None:
        tests = Path("test_calculator.py").read_text(encoding="utf-8")
        self.assertIn("subtract(3, 7)", tests)
        self.assertIn("-4", tests)


if __name__ == "__main__":
    unittest.main()
