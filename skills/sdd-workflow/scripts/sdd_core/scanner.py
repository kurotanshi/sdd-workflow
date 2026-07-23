"""Deterministic v1 task scanner characterized from the v0.2.3 prose rules."""

from __future__ import annotations

import re

from .diagnostics import Diagnostic, Severity
from .model import CanonicalTask, TaskScanResult


ACCEPTANCE_HEADING = "## 驗收條件"
_VALID_TASK = re.compile(r"^- \[([ x])\] (.+)$")
_CHECKBOX_LIKE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s*\[[^]]*\](?:\s|$)")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])")


def scan_tasks(tasks_text: str, *, path: str = "tasks.md") -> TaskScanResult:
    lines = tasks_text.splitlines()
    try:
        boundary_index = lines.index(ACCEPTANCE_HEADING)
    except ValueError:
        boundary_index = len(lines)

    tasks: list[CanonicalTask] = []
    diagnostics: list[Diagnostic] = []
    for line_number, line in enumerate(lines[:boundary_index], start=1):
        valid = _VALID_TASK.match(line)
        if valid:
            tasks.append(
                CanonicalTask(
                    ordinal=len(tasks) + 1,
                    text=valid.group(2),
                    completed=valid.group(1) == "x",
                    source_line=line_number,
                    source_text=line,
                )
            )
            continue
        if _CHECKBOX_LIKE.match(line):
            diagnostics.append(
                _task_diagnostic(
                    path=path,
                    line_number=line_number,
                    line=line,
                    code="ERROR_INVALID_TASK_CHECKBOX",
                    message="Checkbox-like list item is not a valid top-level task",
                )
            )
        elif _LIST_ITEM.match(line):
            diagnostics.append(
                _task_diagnostic(
                    path=path,
                    line_number=line_number,
                    line=line,
                    code="ERROR_INVALID_TASK_LIST_ITEM",
                    message="Non-task list item is not allowed in the task scan region",
                )
            )

    acceptance_conditions = tuple(
        line[2:]
        for line in lines[boundary_index + 1 :]
        if line.startswith("- ") and len(line) > 2
    )
    ordered = tuple(sorted(diagnostics, key=lambda item: item.sort_key))
    return TaskScanResult(
        tasks=tuple(tasks),
        acceptance_conditions=acceptance_conditions,
        diagnostics=ordered,
        counts_reliable=not ordered,
    )


def _task_diagnostic(
    *,
    path: str,
    line_number: int,
    line: str,
    code: str,
    message: str,
) -> Diagnostic:
    column = len(line) - len(line.lstrip()) + 1
    return Diagnostic(
        path=path,
        line=line_number,
        column=column,
        code=code,
        severity=Severity.ERROR,
        message=message,
    )
