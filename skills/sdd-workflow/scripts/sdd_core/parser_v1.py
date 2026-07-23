"""Schema dispatch and the strict v1 proposal adapter."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .diagnostics import Diagnostic, Severity
from .model import (
    ApprovalRelevance,
    CANONICAL_SECTION_APPROVAL_POLICY,
    CanonicalProposal,
    CanonicalSection,
    ParseOutcome,
    TaskScanResult,
)


SUPPORTED_SCHEMA_VERSIONS = (1, 2)
ACTIVE_STATUSES = frozenset({"draft", "approved"})
TERMINAL_STATUSES = frozenset({"completed", "abandoned"})
VALID_STATUSES = ACTIVE_STATUSES | TERMINAL_STATUSES
VALID_CHANGE_TYPES = frozenset({"新功能", "修 bug", "重構"})

_SECTION_DEFINITIONS = (
    ("status", "狀態", CANONICAL_SECTION_APPROVAL_POLICY["status"]),
    ("change_type", "類型", CANONICAL_SECTION_APPROVAL_POLICY["change_type"]),
    ("why", "為什麼做", CANONICAL_SECTION_APPROVAL_POLICY["why"]),
    ("changes", "要改什麼", CANONICAL_SECTION_APPROVAL_POLICY["changes"]),
    ("impact", "影響範圍", CANONICAL_SECTION_APPROVAL_POLICY["impact"]),
)

_AUTO_SCHEMA = object()
_SCHEMA_ENTRY = re.compile(r"^schema_version: ([0-9]+)$")


@dataclass(frozen=True, slots=True)
class SchemaSelection:
    version: int | None
    declared: bool
    diagnostic: Diagnostic | None

    @property
    def supported(self) -> bool:
        return self.version in SUPPORTED_SCHEMA_VERSIONS and self.diagnostic is None


def detect_schema_version(
    explicit_version: object,
    *,
    path: str = "proposal.md",
) -> SchemaSelection:
    """Select an adapter without choosing an artifact encoding for schema v2."""

    if explicit_version is None:
        return SchemaSelection(version=1, declared=False, diagnostic=None)
    if type(explicit_version) is int and explicit_version in SUPPORTED_SCHEMA_VERSIONS:
        return SchemaSelection(version=explicit_version, declared=True, diagnostic=None)
    diagnostic = Diagnostic(
        path=path,
        line=1,
        column=1,
        code="ERROR_UNSUPPORTED_SCHEMA_VERSION",
        severity=Severity.ERROR,
        message=f"Unsupported explicit schema version: {explicit_version!r}",
    )
    return SchemaSelection(version=None, declared=True, diagnostic=diagnostic)


def parse_with_schema(
    *,
    short_name: str,
    proposal_text: str,
    task_scan: TaskScanResult | None,
    explicit_schema_version: object = _AUTO_SCHEMA,
    proposal_path: str = "proposal.md",
) -> ParseOutcome:
    if explicit_schema_version is _AUTO_SCHEMA:
        selection = select_schema_from_document(proposal_text, path=proposal_path)
    else:
        selection = detect_schema_version(explicit_schema_version, path=proposal_path)
    if not selection.supported:
        diagnostics = (selection.diagnostic,) if selection.diagnostic else ()
        return ParseOutcome(
            adapter=None,
            readable=False,
            mutation_safe=False,
            task_counts_reliable=False,
            abandonment_readable=False,
            model=None,
            diagnostics=diagnostics,
        )
    assert task_scan is not None
    if selection.version == 2:
        from .parser_v2 import parse_v2

        return parse_v2(
            short_name=short_name,
            proposal_text=proposal_text,
            task_scan=task_scan,
            proposal_path=proposal_path,
        )
    outcome = parse_v1(
        short_name=short_name,
        proposal_text=proposal_text,
        task_scan=task_scan,
        schema_version_declared=selection.declared,
        proposal_path=proposal_path,
    )
    if not selection.declared and missing_v1_sections(proposal_text):
        from .parser_legacy import parse_legacy

        return parse_legacy(
            short_name=short_name,
            proposal_text=proposal_text,
            task_scan=task_scan,
            proposal_path=proposal_path,
        )
    return outcome


def select_schema_from_document(
    proposal_text: str,
    *,
    path: str = "proposal.md",
) -> SchemaSelection:
    encoded_version, metadata_diagnostic = _frontmatter_schema_version(
        proposal_text,
        path=path,
    )
    if metadata_diagnostic is not None:
        return SchemaSelection(
            version=None,
            declared=True,
            diagnostic=metadata_diagnostic,
        )
    return detect_schema_version(encoded_version, path=path)


def _frontmatter_schema_version(
    proposal_text: str,
    *,
    path: str,
) -> tuple[object | None, Diagnostic | None]:
    lines = proposal_text.splitlines()
    if not lines or lines[0] != "---":
        return None, None
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return None, _schema_metadata_error(
            path,
            1,
            "ERROR_INVALID_SCHEMA_METADATA",
            "Schema frontmatter has no closing delimiter",
        )
    entries = lines[1:closing]
    if len(entries) != 1:
        line = 2 if entries else 1
        unknown = next(
            (
                value
                for value in entries
                if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:", value)
                and not value.startswith("schema_version:")
            ),
            None,
        )
        if unknown is not None:
            return None, _schema_metadata_error(
                path,
                lines.index(unknown, 1, closing) + 1,
                "ERROR_UNKNOWN_SCHEMA_FIELD",
                f"Unsupported schema frontmatter field: {unknown!r}",
            )
        return None, _schema_metadata_error(
            path,
            line,
            "ERROR_INVALID_SCHEMA_METADATA",
            "Schema frontmatter must contain exactly one schema_version entry",
        )
    match = _SCHEMA_ENTRY.fullmatch(entries[0])
    if match is None:
        code = (
            "ERROR_UNKNOWN_SCHEMA_FIELD"
            if not entries[0].startswith("schema_version:")
            else "ERROR_INVALID_SCHEMA_METADATA"
        )
        return None, _schema_metadata_error(
            path,
            2,
            code,
            f"Invalid schema frontmatter entry: {entries[0]!r}",
        )
    return int(match.group(1)), None


def _schema_metadata_error(
    path: str,
    line: int,
    code: str,
    message: str,
) -> Diagnostic:
    return Diagnostic(
        path=path,
        line=line,
        column=1,
        code=code,
        severity=Severity.ERROR,
        message=message,
    )


def parse_v1(
    *,
    short_name: str,
    proposal_text: str,
    task_scan: TaskScanResult,
    schema_version_declared: bool,
    proposal_path: str = "proposal.md",
) -> ParseOutcome:
    lines = proposal_text.splitlines()
    raw_sections = _collect_sections(lines)
    diagnostics: list[Diagnostic] = list(task_scan.diagnostics)
    sections: list[CanonicalSection] = []

    for key, heading, relevance in _SECTION_DEFINITIONS:
        match = raw_sections.get(heading)
        if match is None:
            diagnostics.append(
                Diagnostic(
                    path=proposal_path,
                    line=1,
                    column=1,
                    code="ERROR_REQUIRED_SECTION_MISSING",
                    severity=Severity.ERROR,
                    message=f"Missing required proposal section: ## {heading}",
                )
            )
            continue
        _, body = match
        sections.append(
            CanonicalSection(
                key=key,
                heading=heading,
                body=tuple(body),
                approval_relevance=relevance,
                semantic_items=_semantic_section_items(body),
            )
        )

    status, status_line = _single_value(raw_sections.get("狀態"))
    change_type, change_type_line = _single_value(raw_sections.get("類型"))
    if status is not None and status not in VALID_STATUSES:
        diagnostics.append(
            Diagnostic(
                path=proposal_path,
                line=status_line,
                column=1,
                code="ERROR_INVALID_STATUS",
                severity=Severity.ERROR,
                message=f"Unsupported proposal status: {status}",
            )
        )
    if change_type is not None and change_type not in VALID_CHANGE_TYPES:
        diagnostics.append(
            Diagnostic(
                path=proposal_path,
                line=change_type_line,
                column=1,
                code="ERROR_INVALID_CHANGE_TYPE",
                severity=Severity.ERROR,
                message=f"Unsupported proposal change type: {change_type}",
            )
        )

    ordered_diagnostics = tuple(sorted(diagnostics, key=lambda item: item.sort_key))
    model = CanonicalProposal(
        schema_version=1,
        schema_version_declared=schema_version_declared,
        short_name=short_name,
        status=status,
        change_type=change_type,
        sections=tuple(sections),
        tasks=task_scan.tasks,
        acceptance_conditions=task_scan.acceptance_conditions,
        diagnostics=ordered_diagnostics,
    )
    has_errors = any(item.severity is Severity.ERROR for item in ordered_diagnostics)
    mutation_safe = (
        not has_errors
        and task_scan.counts_reliable
        and status in ACTIVE_STATUSES
        and change_type in VALID_CHANGE_TYPES
    )
    return ParseOutcome(
        adapter="v1",
        readable=True,
        mutation_safe=mutation_safe,
        task_counts_reliable=task_scan.counts_reliable,
        abandonment_readable=True,
        model=model,
        diagnostics=ordered_diagnostics,
    )


def missing_v1_sections(proposal_text: str) -> tuple[str, ...]:
    present = _collect_sections(proposal_text.splitlines())
    return tuple(heading for _, heading, _ in _SECTION_DEFINITIONS if heading not in present)


def _collect_sections(lines: Iterable[str]) -> dict[str, tuple[int, list[str]]]:
    sections: dict[str, tuple[int, list[str]]] = {}
    current_heading: str | None = None
    for line_number, line in enumerate(lines, start=1):
        if line.startswith("## ") and len(line) > 3:
            current_heading = line[3:]
            sections.setdefault(current_heading, (line_number, []))
        elif current_heading is not None:
            sections[current_heading][1].append(line)
    return sections


def _single_value(section: tuple[int, list[str]] | None) -> tuple[str | None, int]:
    if section is None:
        return None, 1
    heading_line, body = section
    for offset, line in enumerate(body, start=1):
        value = line.strip()
        if value:
            return value, heading_line + offset
    return None, heading_line


def _semantic_section_items(body: Iterable[str]) -> tuple[str, ...]:
    """Translate v1 section container syntax into ordered semantic text."""

    items: list[str] = []
    for raw_line in body:
        value = raw_line.strip()
        if not value:
            continue
        if value.startswith("- "):
            value = value[2:]
        items.append(value)
    return tuple(items)
