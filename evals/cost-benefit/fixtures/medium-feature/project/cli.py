from __future__ import annotations

import argparse

from inventory import load_items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory")
    arguments = parser.parse_args()
    for item in load_items(arguments.inventory):
        print(f"{item['sku']}\t{item['stock']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
