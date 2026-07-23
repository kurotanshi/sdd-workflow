"""Stable identity tokens for canonical task text."""

from __future__ import annotations

import hashlib


def task_digest(canonical_text: str) -> str:
    """Hash parser-owned canonical text without Unicode normalization."""

    if not isinstance(canonical_text, str) or not canonical_text:
        raise ValueError("canonical task text must be a non-empty string")
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()

