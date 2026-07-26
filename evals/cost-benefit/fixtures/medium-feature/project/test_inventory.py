import json
import tempfile
import unittest
from pathlib import Path

from inventory import load_items


class InventoryTests(unittest.TestCase):
    def test_load_items(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.json"
            path.write_text(
                json.dumps([{"sku": "B-2", "stock": 4}]),
                encoding="utf-8",
            )
            self.assertEqual(load_items(path), [{"sku": "B-2", "stock": 4}])


if __name__ == "__main__":
    unittest.main()
