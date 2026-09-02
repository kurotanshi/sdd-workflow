"""Read-only and transition entry points for active artifact recovery."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Mapping

from .discovery import ProposalPaths
from .recovery_projection import (
    RecoveryIssue,
    RecoveryProjection,
    RecoverySupplement,
    plan_recovery_projection,
)
from .recovery_protocol import (
    RecoveryArtifact,
    RecoveryProtocolResult,
    execute_staged_recovery,
    find_recovery_operation,
    resume_staged_recovery,
)
from .parser_v1 import parse_with_schema
from .scanner import scan_tasks
from .transitions import TransitionError


@dataclass(frozen=True, slots=True)
class ActiveRepairResult:
    outcome: str
    projection: RecoveryProjection
    protocol: RecoveryProtocolResult | None = None


def preflight_proposal_repair(
    paths: ProposalPaths,
    *,
    supplement: RecoverySupplement | None = None,
) -> RecoveryProjection:
    """Inspect an active proposal without writing any artifact."""

    machine = paths.directory / ".sdd"
    protected = tuple(
        path
        for path in (
            machine / "metadata.json",
            machine / "approval-manifest.json",
        )
        if path.exists() or path.is_symlink()
    )
    if machine.is_symlink() or protected:
        source = (
            ("proposal.md", _digest(paths.proposal)),
            ("tasks.md", _digest(paths.tasks)),
        )
        return RecoveryProjection(
            target="active",
            disposition="blocked",
            encoding=None,
            source_digests=source,
            candidate_digests=(),
            required_inputs=(),
            changes=(),
            evidence=(),
            issues=(
                RecoveryIssue(
                    "ERROR_MACHINE_METADATA_INVALID",
                    "inspect_machine_metadata",
                    "Active approval or attestation artifacts prevent format recovery",
                    "metadata",
                ),
            ),
        )
    return plan_recovery_projection(
        target="active",
        short_name=paths.directory.name,
        proposal_bytes=paths.proposal.read_bytes(),
        tasks_bytes=paths.tasks.read_bytes(),
        supplement=supplement,
    )


def execute_proposal_repair(
    paths: ProposalPaths,
    *,
    supplement: RecoverySupplement,
    expected_source_digests: Mapping[str, str],
    expected_candidate_digests: Mapping[str, str],
) -> ActiveRepairResult:
    """Apply or resume a digest-confirmed active proposal reconstruction."""

    projection = preflight_proposal_repair(paths, supplement=supplement)
    if projection.issues:
        issue = projection.issues[0]
        raise TransitionError(issue.code, issue.action, issue.message)
    target_identity = f"active:{paths.directory.name}"
    operation_id = find_recovery_operation(
        paths.directory,
        kind="repair-proposal-format",
        target_identity=target_identity,
        source_digests=expected_source_digests,
        candidate_digests=expected_candidate_digests,
    )
    if operation_id is not None:
        protocol = resume_staged_recovery(
            paths.directory,
            operation_id,
            validate_candidates=_validate_active_candidates,
        )
        return ActiveRepairResult(protocol.outcome, projection, protocol)
    if projection.disposition == "no-op":
        return ActiveRepairResult("NO_OP", projection)
    if projection.required_inputs:
        raise TransitionError(
            "ERROR_RECOVERY_INPUT_REQUIRED",
            "provide_recovery_input",
            "Recovery requires explicit non-derived values",
            data={"required_inputs": list(projection.required_inputs)},
        )
    if not projection.applicable:
        raise TransitionError(
            "ERROR_RECOVERY_NOT_APPLICABLE",
            "rerun_repair_preflight",
            "Recovery preflight did not produce an applicable candidate",
        )
    if (
        dict(projection.source_digests) != dict(expected_source_digests)
        or dict(projection.candidate_digests) != dict(expected_candidate_digests)
    ):
        raise TransitionError(
            "ERROR_RECOVERY_EVIDENCE_MISMATCH",
            "rerun_repair_preflight",
            "Confirmed source or candidate digests differ from the current projection",
        )
    assert projection.proposal_candidate is not None
    assert projection.tasks_candidate is not None
    protocol = execute_staged_recovery(
        paths.directory,
        kind="repair-proposal-format",
        target_identity=target_identity,
        artifacts=(
            RecoveryArtifact(
                "proposal.md",
                paths.proposal.read_bytes(),
                projection.proposal_candidate,
            ),
            RecoveryArtifact(
                "tasks.md",
                paths.tasks.read_bytes(),
                projection.tasks_candidate,
            ),
        ),
        validate_candidates=_validate_active_candidates,
    )
    return ActiveRepairResult(protocol.outcome, projection, protocol)


def _validate_active_candidates(candidates: Mapping[str, bytes]) -> None:
    try:
        proposal_text = candidates["proposal.md"].decode("utf-8", errors="strict")
        tasks_text = candidates["tasks.md"].decode("utf-8", errors="strict")
    except (KeyError, UnicodeDecodeError) as error:
        raise TransitionError(
            "ERROR_RECOVERY_CANDIDATE_INVALID",
            "report_internal_error",
            "Active recovery candidates are incomplete or not UTF-8",
        ) from error
    task_scan = scan_tasks(tasks_text)
    outcome = parse_with_schema(
        short_name=_candidate_title(proposal_text),
        proposal_text=proposal_text,
        task_scan=task_scan,
    )
    if (
        outcome.model is None
        or outcome.model.status != "draft"
        or not outcome.mutation_safe
        or any(item.severity.value == "error" for item in outcome.diagnostics)
    ):
        raise TransitionError(
            "ERROR_RECOVERY_CANDIDATE_INVALID",
            "report_internal_error",
            "Active recovery candidate does not validate as a mutation-safe v2 draft",
        )


def _candidate_title(proposal_text: str) -> str:
    titles = [line[2:] for line in proposal_text.splitlines() if line.startswith("# ")]
    if len(titles) != 1:
        raise TransitionError(
            "ERROR_RECOVERY_CANDIDATE_INVALID",
            "report_internal_error",
            "Active recovery candidate title is ambiguous",
        )
    return titles[0]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
