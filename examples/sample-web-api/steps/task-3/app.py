"""Dependency-free sample API after the revised scope is implemented."""

from __future__ import annotations

from typing import Any


SERVICE_VERSION = "1.0.0"


def handle(path: str) -> tuple[int, dict[str, str], dict[str, Any]]:
    headers = {"content-type": "application/json"}
    if path == "/health":
        return 200, headers, {
            "status": "ok",
            "version": SERVICE_VERSION,
        }
    return 404, headers, {"error": "not found"}
