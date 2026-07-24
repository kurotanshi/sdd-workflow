"""Dependency-free sample API with the first approved task implemented."""

from __future__ import annotations

from typing import Any


def handle(path: str) -> tuple[int, dict[str, str], dict[str, Any]]:
    headers = {"content-type": "application/json"}
    if path == "/health":
        return 200, headers, {"status": "ok"}
    return 404, headers, {"error": "not found"}
