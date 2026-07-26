import unittest

from calculator import add, subtract


class CalculatorTests(unittest.TestCase):
    def test_add(self) -> None:
        self.assertEqual(add(2, 3), 5)

    def test_subtract_positive_result(self) -> None:
        self.assertEqual(subtract(7, 3), 4)


if __name__ == "__main__":
    unittest.main()
