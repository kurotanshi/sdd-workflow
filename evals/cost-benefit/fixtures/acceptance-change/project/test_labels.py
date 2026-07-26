import unittest

from labels import clean_labels


class LabelTests(unittest.TestCase):
    def test_clean_labels(self) -> None:
        self.assertEqual(clean_labels([" alpha ", "", " beta"]), ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
