"""Read-compatible adapter for unversioned, partially structured proposals."""

from __future__ import annotations

from .diagnostics import Diagnostic, Severity
from .model import CanonicalProposal, ParseOutcome, TaskScanResult
from .parser_v1 import missing_v1_sections, parse_v1


LEGACY_MUTATION_BLOCK_CODE = "ERROR_LEGACY_MUTATION_UNSUPPORTED"


def parse_legacy(
    *,
    short_name: str,
    proposal_text: str,
    task_scan: TaskScanResult,
    proposal_path: str = "proposal.md",
) -> ParseOutcome:
    """Preserve known v1-shaped fields without claiming mutation safety."""

    strict = parse_v1(
        short_name=short_name,
        proposal_text=proposal_text,
        task_scan=task_scan,
        schema_version_declared=False,
        proposal_path=proposal_path,
    )
    assert strict.model is not None

    diagnostics = [
        item
        for item in strict.diagnostics
        if item.code != "ERROR_REQUIRED_SECTION_MISSING"
    ]
    for heading in missing_v1_sections(proposal_text):
        if heading == "狀態":
            code = "WARNING_LEGACY_STATUS_MISSING"
            message = "Legacy proposal has no status; approval must not be inferred"
        else:
            code = "WARNING_LEGACY_SECTION_MISSING"
            message = f"Legacy proposal is missing v1 section: ## {heading}"
        diagnostics.append(
            Diagnostic(
                path=proposal_path,
                line=1,
                column=1,
                code=code,
                severity=Severity.WARNING,
                message=message,
            )
        )

    ordered = tuple(sorted(diagnostics, key=lambda item: item.sort_key))
    source = strict.model
    model = CanonicalProposal(
        schema_version=source.schema_version,
        schema_version_declared=False,
        short_name=source.short_name,
        status=source.status,
        change_type=source.change_type,
        sections=source.sections,
        tasks=source.tasks,
        acceptance_conditions=source.acceptance_conditions,
        diagnostics=ordered,
        extensions=source.extensions,
    )
    return ParseOutcome(
        adapter="legacy",
        readable=True,
        mutation_safe=False,
        task_counts_reliable=task_scan.counts_reliable,
        abandonment_readable=True,
        model=model,
        diagnostics=ordered,
        mutation_block_code=LEGACY_MUTATION_BLOCK_CODE,
    )
