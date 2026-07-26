import unittest
from pathlib import Path

from labels import clean_labels, normalize_labels


class AcceptanceChangeOracleTests(unittest.TestCase):
    def test_normalize_labels_uses_final_acceptance_rule(self) -> None:
        self.assertEqual(
            normalize_labels([" Alpha ", "beta", "ALPHA", "", " Beta ", "gamma"]),
            ["alpha", "beta", "gamma"],
        )

    def test_existing_clean_labels_is_unchanged(self) -> None:
        self.assertEqual(clean_labels([" alpha ", "", " beta"]), ["alpha", "beta"])

    def test_public_tests_cover_final_acceptance(self) -> None:
        tests = Path("test_labels.py").read_text(encoding="utf-8")
        self.assertIn("normalize_labels", tests)
        self.assertIn("ALPHA", tests)


if __name__ == "__main__":
    unittest.main()
