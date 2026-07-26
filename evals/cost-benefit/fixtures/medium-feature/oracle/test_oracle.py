import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from inventory import low_stock


class MediumFeatureOracleTests(unittest.TestCase):
    def test_low_stock_filters_and_sorts(self) -> None:
        items = [
            {"sku": "B-2", "stock": 2},
            {"sku": "A-1", "stock": 1},
            {"sku": "C-3", "stock": 5},
        ]
        self.assertEqual(
            low_stock(items, 2),
            [{"sku": "A-1", "stock": 1}, {"sku": "B-2", "stock": 2}],
        )

    def test_low_stock_rejects_negative_threshold(self) -> None:
        with self.assertRaises(ValueError):
            low_stock([], -1)

    def test_cli_text_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.json"
            path.write_text(
                json.dumps(
                    [
                        {"sku": "B-2", "stock": 2},
                        {"sku": "A-1", "stock": 1},
                        {"sku": "C-3", "stock": 5},
                    ]
                ),
                encoding="utf-8",
            )
            text = subprocess.run(
                [sys.executable, "cli.py", str(path), "--low-stock", "2"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(text.returncode, 0, text.stderr)
            self.assertEqual(text.stdout, "A-1\t1\nB-2\t2\n")

            json_output = subprocess.run(
                [
                    sys.executable,
                    "cli.py",
                    str(path),
                    "--low-stock",
                    "2",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(json_output.returncode, 0, json_output.stderr)
            self.assertEqual(
                json.loads(json_output.stdout),
                [{"sku": "A-1", "stock": 1}, {"sku": "B-2", "stock": 2}],
            )

    def test_documentation_and_public_tests_cover_feature(self) -> None:
        readme = Path("README.md").read_text(encoding="utf-8")
        tests = Path("test_inventory.py").read_text(encoding="utf-8")
        self.assertIn("--low-stock", readme)
        self.assertIn("--json", readme)
        self.assertIn("low_stock", tests)


if __name__ == "__main__":
    unittest.main()
