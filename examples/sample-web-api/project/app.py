"""Dependency-free sample API before the proposal is implemented."""

from __future__ import annotations

from typing import Any


def handle(path: str) -> tuple[int, dict[str, str], dict[str, Any]]:
    return 404, {"content-type": "application/json"}, {"error": "not found"}
