"""Validate that public Agent-eval reports contain no raw or sensitive data."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REPORT_ROOT = ROOT / "evals/reports"

UNSAFE_PATTERNS = {
    "absolute macOS user path": re.compile(r"/Users/[^\s)`>\"]+"),
    "absolute Linux user path": re.compile(r"/home/[^\s)`>\"]+"),
    "absolute Windows user path": re.compile(
        r"[A-Za-z]:\\Users\\[^\s)`>\"]+",
        re.IGNORECASE,
    ),
    "email address": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        re.IGNORECASE,
    ),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "GitHub token": re.compile(
        r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"
        r"|\bgithub_pat_[A-Za-z0-9_]{20,}\b",
        re.IGNORECASE,
    ),
    "Anthropic secret": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Bearer credential": re.compile(
        r"\bauthorization\s*:\s*bearer\s+\S+",
        re.IGNORECASE,
    ),
    "private key": re.compile(
        r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----",
        re.IGNORECASE,
    ),
    "raw trace identifier": re.compile(
        r"""["']?(?:session_id|request_id|tool_use_id)["']?\s*:""",
        re.IGNORECASE,
    ),
}

REQUIRED_SUMMARY_FACTS = (
    "Release gate: **PASS**",
    "77/78",
    "98.7%",
    "Critical Violations: **0**",
    "Secret scan: PASS",
    "Anonymization review: PASS",
    "Manual review: PASS",
)


class PublicReportError(ValueError):
    """Raised when a public report is unsafe or incomplete."""


def validate_text(text: str, *, source: str) -> None:
    for label, pattern in UNSAFE_PATTERNS.items():
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            raise PublicReportError(f"{source}:{line}: {label}")


def validate_report_directory(report_root: Path = PUBLIC_REPORT_ROOT) -> list[Path]:
    if not report_root.is_dir():
        raise PublicReportError(f"missing public report directory: {report_root}")
    reports = sorted(
        path
        for path in report_root.rglob("*")
        if path.is_file() and path.suffix in {".md", ".json"}
    )
    if not reports:
        raise PublicReportError(f"no public reports found under {report_root}")

    for path in reports:
        if path.is_symlink():
            raise PublicReportError(f"public report cannot be a symlink: {path}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise PublicReportError(f"public report must be UTF-8: {path}") from error
        validate_text(text, source=path.relative_to(report_root).as_posix())

    summaries = [
        path for path in reports if path.name.endswith("-agent-eval-summary.md")
    ]
    if not summaries:
        raise PublicReportError("missing versioned Agent-eval summary report")
    for path in summaries:
        text = path.read_text(encoding="utf-8")
        missing = [fact for fact in REQUIRED_SUMMARY_FACTS if fact not in text]
        if missing:
            raise PublicReportError(
                f"{path.name}: missing publication facts: {', '.join(missing)}"
            )
    return reports
