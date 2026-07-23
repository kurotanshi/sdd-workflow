"""Engine release identity and diagnostic-only generation comparison."""

from __future__ import annotations

import re


ENGINE_VERSION = "0.6.0"
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def parse_engine_version(value: str) -> tuple[int, int, int] | None:
    match = _SEMVER.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def engine_generation(value: str) -> tuple[int, int] | None:
    parsed = parse_engine_version(value)
    return None if parsed is None else parsed[:2]
