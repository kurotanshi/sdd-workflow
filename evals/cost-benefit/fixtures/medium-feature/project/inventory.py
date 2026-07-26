from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class Item(TypedDict):
    sku: str
    stock: int


def load_items(path: str | Path) -> list[Item]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return [{"sku": str(item["sku"]), "stock": int(item["stock"])} for item in value]
