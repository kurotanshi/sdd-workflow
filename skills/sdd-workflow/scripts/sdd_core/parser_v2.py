"""Strict Schema v2 adapter into the shared canonical proposal model."""

from __future__ import annotations

from .diagnostics import Diagnostic, Severity
from .model import (
    ApprovalRelevance,
    CANONICAL_EXTENSION_APPROVAL_POLICY,
    CanonicalExtension,
    CanonicalProposal,
    CanonicalSection,
    ParseOutcome,
    TaskScanResult,
)
from .parser_v1 import (
    ACTIVE_STATUSES,
    _collect_sections,
    _semantic_section_items,
    _single_value,
    parse_v1,
)


_V2_BASE_HEADINGS = frozenset({"狀態", "類型", "為什麼做", "要改什麼", "影響範圍"})
_V2_HEADINGS = _V2_BASE_HEADINGS | {"結論"}
VALID_V2_CHANGE_TYPES = frozenset(
    {"新功能", "修 bug", "重構", "維運", "文件", "研究"}
)


def parse_v2(
    *,
    short_name: str,
    proposal_text: str,
    task_scan: TaskScanResult,
    proposal_path: str = "proposal.md",
) -> ParseOutcome:
    """Parse minimal v2 while keeping all workflow logic schema-independent."""

    strict_v1 = parse_v1(
        short_name=short_name,
        proposal_text=proposal_text,
        task_scan=task_scan,
        schema_version_declared=True,
        proposal_path=proposal_path,
    )
    assert strict_v1.model is not None
    diagnostics = [
        item
        for item in strict_v1.diagnostics
        if item.code != "ERROR_INVALID_CHANGE_TYPE"
    ]
    sections = _collect_sections(proposal_text.splitlines())
    change_type, change_type_line = _single_value(sections.get("類型"))
    if change_type is not None and change_type not in VALID_V2_CHANGE_TYPES:
        diagnostics.append(
            Diagnostic(
                path=proposal_path,
                line=change_type_line,
                column=1,
                code="ERROR_INVALID_CHANGE_TYPE",
                severity=Severity.ERROR,
                message=f"Unsupported Schema v2 change type: {change_type}",
            )
        )
    for heading, (line, _) in sections.items():
        if heading not in _V2_HEADINGS:
            diagnostics.append(
                Diagnostic(
                    path=proposal_path,
                    line=line,
                    column=1,
                    code="ERROR_UNKNOWN_SCHEMA_FIELD",
                    severity=Severity.ERROR,
                    message=f"Unsupported Schema v2 section: ## {heading}",
                )
            )

    source = strict_v1.model
    canonical_sections = list(source.sections)
    extensions = [
        CanonicalExtension(
            "sdd.schema",
            {"schema_version": 2},
            CANONICAL_EXTENSION_APPROVAL_POLICY["sdd.schema"],
        )
    ]
    conclusion_section = sections.get("結論")
    conclusion_items: tuple[str, ...] = ()
    if change_type == "研究":
        if conclusion_section is None:
            diagnostics.append(
                Diagnostic(
                    path=proposal_path,
                    line=1,
                    column=1,
                    code="ERROR_REQUIRED_SECTION_MISSING",
                    severity=Severity.ERROR,
                    message="Schema v2 research requires section: ## 結論",
                )
            )
        else:
            _, conclusion_body = conclusion_section
            conclusion_items = _semantic_section_items(conclusion_body)
            canonical_sections.append(
                CanonicalSection(
                    key="conclusion",
                    heading="結論",
                    body=tuple(conclusion_body),
                    approval_relevance=CANONICAL_EXTENSION_APPROVAL_POLICY[
                        "sdd.research.conclusion"
                    ],
                    semantic_items=conclusion_items,
                )
            )
        if source.status == "completed" and not conclusion_items:
            diagnostics.append(
                Diagnostic(
                    path=proposal_path,
                    line=conclusion_section[0] if conclusion_section else 1,
                    column=1,
                    code="ERROR_RESEARCH_CONCLUSION_REQUIRED",
                    severity=Severity.ERROR,
                    message="Completed research requires a non-empty conclusion",
                )
            )
        extensions.append(
            CanonicalExtension(
                "sdd.research.conclusion",
                {"items": list(conclusion_items)},
                CANONICAL_EXTENSION_APPROVAL_POLICY["sdd.research.conclusion"],
            )
        )
    elif conclusion_section is not None:
        diagnostics.append(
            Diagnostic(
                path=proposal_path,
                line=conclusion_section[0],
                column=1,
                code="ERROR_INVALID_TYPE_SECTION",
                severity=Severity.ERROR,
                message="Only Schema v2 research may contain ## 結論",
            )
        )

    ordered = tuple(sorted(diagnostics, key=lambda item: item.sort_key))
    model = CanonicalProposal(
        schema_version=2,
        schema_version_declared=True,
        short_name=source.short_name,
        status=source.status,
        change_type=source.change_type,
        sections=tuple(canonical_sections),
        tasks=source.tasks,
        acceptance_conditions=source.acceptance_conditions,
        diagnostics=ordered,
        extensions=tuple(extensions),
    )
    has_errors = any(item.severity is Severity.ERROR for item in ordered)
    return ParseOutcome(
        adapter="v2",
        readable=True,
        mutation_safe=(
            not has_errors
            and task_scan.counts_reliable
            and model.status in ACTIVE_STATUSES
            and model.change_type in VALID_V2_CHANGE_TYPES
        ),
        task_counts_reliable=task_scan.counts_reliable,
        abandonment_readable=True,
        model=model,
        diagnostics=ordered,
    )
