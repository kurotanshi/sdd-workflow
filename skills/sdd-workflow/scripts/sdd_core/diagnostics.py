"""Internal diagnostic value objects shared by parser adapters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A source-addressable parser finding.

    Generation and precedence rules live with the scanner. This type only fixes
    the canonical shape and deterministic sort key.
    """

    path: str
    line: int
    column: int
    code: str
    severity: Severity
    message: str

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("diagnostic path must not be empty")
        if self.line < 1 or self.column < 1:
            raise ValueError("diagnostic line and column are one-based")
        if not self.code:
            raise ValueError("diagnostic code must not be empty")

    @property
    def sort_key(self) -> tuple[str, int, int, str]:
        normalized = PurePosixPath(self.path.replace("\\", "/")).as_posix()
        return (normalized, self.line, self.column, self.code)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
        }
