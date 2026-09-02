"""Explicitly confirmed repair for archive directories missing terminal evidence.

The repair path never moves directories, never guesses summaries, and never
changes an existing correct record. It fills the missing terminal status in
the archived proposal (the lifecycle authority) and records the maintainer's
confirmed summary as machine recovery evidence, so the derived INDEX can be
rebuilt without the summary having to come from an existing INDEX row.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from .archive_index import rebuild_archive_index
from .archive_model import (
    ArchiveDiagnostic,
    RECOVERY_EVIDENCE_VERSION,
    _directory_has_terminal_metadata,
    _directory_identity,
    load_archive_records,
    load_recovery_evidence,
    parse_legacy_index,
)
from .atomic_write import atomic_replace_bytes
from .parser_v1 import parse_with_schema
from .scanner import scan_tasks
from .recovery_projection import (
    RecoveryIssue,
    RecoveryProjection,
    RecoverySupplement,
    plan_recovery_projection,
)
from .recovery_protocol import (
    RecoveryArtifact,
    execute_staged_recovery,
    find_recovery_operation,
    resume_staged_recovery,
)
from .transitions import TransitionError, replace_status
from .version import ENGINE_VERSION


TERMINAL_STATUSES = frozenset({"completed", "abandoned"})


@dataclass(frozen=True, slots=True)
class RepairPreflight:
    directory_name: str
    short_name: str
    archive_date: str
    expected_terminal_status: str
    current_status: str | None
    missing: tuple[str, ...]
    proposal_sha256: str
    tasks_sha256: str
    projection: RecoveryProjection
    reconstruction_required: bool
    recovery_timestamp: str | None


@dataclass(frozen=True, slots=True)
class RepairResult:
    preflight: RepairPreflight
    repaired: tuple[str, ...]
    operation_id: str
    index_rebuilt: bool
    index_sha256: str | None
    diagnostics: tuple[ArchiveDiagnostic, ...]
    outcome: str = "APPLIED"
    committed: bool = True


def preflight_archive_repair(
    archive_root: Path,
    directory_name: str,
    *,
    supplement: RecoverySupplement | None = None,
    now_utc: datetime | None = None,
) -> RepairPreflight:
    directory, identity = validate_repairable_target(
        archive_root, directory_name, allow_managed=True
    )
    archive_date, short_name, name_status = identity
    expected_terminal = name_status or "completed"
    proposal_bytes = (directory / "proposal.md").read_bytes()
    tasks_bytes = (directory / "tasks.md").read_bytes()
    machine_path = directory / ".sdd/metadata.json"
    metadata_bytes = (
        machine_path.read_bytes()
        if machine_path.is_file() and not machine_path.is_symlink()
        else None
    )
    provided = RecoverySupplement() if supplement is None else supplement
    index_summaries = _matching_index_summaries(
        archive_root, archive_date, short_name, expected_terminal
    )
    index_summary = index_summaries[0] if len(index_summaries) == 1 else None
    try:
        recovery_evidence = load_recovery_evidence(directory)
    except ValueError:
        recovery_evidence = None
    recovery_summary = (
        str(recovery_evidence["summary"])
        if recovery_evidence is not None
        else None
    )
    authoritative_summary = (
        recovery_summary if recovery_summary is not None else index_summary
    )
    effective = RecoverySupplement(
        change_type=provided.change_type,
        scope=provided.scope,
        acceptance_conditions=provided.acceptance_conditions,
        summary=(
            provided.summary
            if provided.summary is not None
            else authoritative_summary
        ),
    )
    projection = plan_recovery_projection(
        target="archive",
        short_name=short_name,
        proposal_bytes=proposal_bytes,
        tasks_bytes=tasks_bytes,
        expected_status=expected_terminal,
        archive_date=archive_date,
        metadata_bytes=metadata_bytes,
        supplement=effective,
    )
    format_reconstruction_required = _requires_reconstruction(
        short_name, proposal_bytes, tasks_bytes
    )
    if (
        not format_reconstruction_required
        and projection.encoding != "recovery-v1"
        and not projection.issues
        and not projection.required_inputs
    ):
        projection = replace(
            projection,
            disposition="no-op",
            encoding=None,
            candidate_digests=(),
            required_inputs=(),
            changes=(),
            issues=(),
            proposal_candidate=None,
            tasks_candidate=None,
            metadata_candidate=None,
        )
    if len(index_summaries) > 1:
        projection = _blocked_projection(
            projection,
            RecoveryIssue(
                "ERROR_RECOVERY_EVIDENCE_AMBIGUOUS",
                "inspect_archive_state",
                "Multiple legacy INDEX summaries match the archive record",
                "summary",
            ),
        )
    elif (
        authoritative_summary is not None
        and provided.summary is not None
        and provided.summary.strip() != authoritative_summary
    ):
        projection = _blocked_projection(
            projection,
            RecoveryIssue(
                "ERROR_RECOVERY_INPUT_CONFLICT",
                "inspect_archive_state",
                "Explicit summary must not override existing archive authority",
                "summary",
            ),
        )
    current_status = _parse_status(short_name, proposal_bytes, tasks_bytes)
    reconstruction_required = projection.applicable and (
        projection.encoding == "recovery-v1"
        or format_reconstruction_required
    )
    recovery_timestamp: str | None = None
    if reconstruction_required and effective.summary is not None:
        recovery_timestamp = _recovery_timestamp(now_utc)
        operation_id = _repair_operation_id(
            directory_name=directory_name,
            terminal_status=expected_terminal,
            summary=effective.summary,
            expected_proposal_sha256=hashlib.sha256(proposal_bytes).hexdigest(),
            expected_tasks_sha256=hashlib.sha256(tasks_bytes).hexdigest(),
        )
        metadata_candidate = _recovery_metadata_bytes(
            archive_date=archive_date,
            short_name=short_name,
            terminal_status=expected_terminal,
            summary=effective.summary,
            timestamp=recovery_timestamp,
            operation_id=operation_id,
            proposal_sha256=hashlib.sha256(proposal_bytes).hexdigest(),
            tasks_sha256=hashlib.sha256(tasks_bytes).hexdigest(),
            reconstruction_digests=dict(projection.candidate_digests),
        )
        projection = replace(
            projection,
            candidate_digests=tuple(
                sorted(
                    (
                        *projection.candidate_digests,
                        (".sdd/metadata.json", hashlib.sha256(metadata_candidate).hexdigest()),
                    )
                )
            ),
            metadata_candidate=metadata_candidate,
            changes=tuple(
                (*projection.changes, (".sdd/metadata.json", "recovery_evidence"))
            ),
        )
    missing: list[str] = []
    if current_status not in TERMINAL_STATUSES:
        missing.append("terminal_status")
    if not _has_machine_evidence(directory) and not _directory_has_terminal_metadata(
        directory
    ):
        missing.append("machine_evidence")
    if not _has_index_row(archive_root, archive_date, short_name, expected_terminal):
        missing.append("index_row")
    return RepairPreflight(
        directory_name=directory_name,
        short_name=short_name,
        archive_date=archive_date,
        expected_terminal_status=expected_terminal,
        current_status=current_status,
        missing=tuple(missing),
        proposal_sha256=hashlib.sha256(proposal_bytes).hexdigest(),
        tasks_sha256=hashlib.sha256(tasks_bytes).hexdigest(),
        projection=projection,
        reconstruction_required=reconstruction_required,
        recovery_timestamp=recovery_timestamp,
    )


def execute_archive_repair(
    archive_root: Path,
    directory_name: str,
    *,
    terminal_status: str,
    summary: str,
    expected_proposal_sha256: str,
    expected_tasks_sha256: str,
    expected_metadata_sha256: str | None = None,
    expected_candidate_digests: dict[str, str] | None = None,
    recovery_timestamp: str | None = None,
    supplement: RecoverySupplement | None = None,
    now_utc: datetime | None = None,
) -> RepairResult:
    supplied = RecoverySupplement(summary=summary) if supplement is None else replace(
        supplement, summary=summary
    )
    timestamp_moment = now_utc
    if recovery_timestamp is not None:
        try:
            timestamp_moment = datetime.fromisoformat(
                recovery_timestamp.replace("Z", "+00:00")
            )
        except ValueError as error:
            raise TransitionError(
                "ERROR_RECOVERY_EVIDENCE_MISMATCH",
                "rerun_repair_preflight",
                "Recovery timestamp is not valid RFC 3339 UTC seconds",
            ) from error
    preflight = preflight_archive_repair(
        archive_root,
        directory_name,
        supplement=supplied,
        now_utc=timestamp_moment,
    )
    if terminal_status != preflight.expected_terminal_status:
        raise TransitionError(
            "ERROR_RECOVERY_STATUS_MISMATCH",
            "inspect_archive_state",
            "Provided terminal status disagrees with the archive directory name",
        )
    target_directory = archive_root / directory_name
    if (
        preflight.proposal_sha256 != expected_proposal_sha256
        or preflight.tasks_sha256 != expected_tasks_sha256
    ) and (
        expected_candidate_digests is None
        or _directory_has_terminal_metadata(target_directory)
    ):
        raise TransitionError(
            "ERROR_RECOVERY_EVIDENCE_MISMATCH",
            "rerun_repair_preflight",
            "Archived artifact bytes differ from the confirmed evidence digests",
        )
    if _directory_has_terminal_metadata(target_directory):
        machine_issues = tuple(
            issue
            for issue in preflight.projection.issues
            if issue.action == "inspect_machine_metadata"
        )
        if machine_issues:
            issue = machine_issues[0]
            raise TransitionError(issue.code, issue.action, issue.message)
        scan = load_archive_records(archive_root)
        if scan.diagnostics:
            return RepairResult(
                preflight,
                (),
                "",
                False,
                None,
                scan.diagnostics,
                outcome="NO_OP",
                committed=False,
            )
        _, changed, digest = rebuild_archive_index(archive_root, scan.records)
        refreshed = preflight_archive_repair(
            archive_root,
            directory_name,
            supplement=supplied,
            now_utc=timestamp_moment,
        )
        return RepairResult(
            refreshed,
            ("index_row",) if changed else (),
            "",
            True,
            digest,
            (),
            outcome="NO_OP",
            committed=False,
        )
    if preflight.projection.issues:
        issue = preflight.projection.issues[0]
        raise TransitionError(issue.code, issue.action, issue.message)
    if preflight.projection.required_inputs:
        raise TransitionError(
            "ERROR_RECOVERY_INPUT_REQUIRED",
            "provide_recovery_input",
            "Archive recovery requires explicit non-derived values",
            data={"required_inputs": list(preflight.projection.required_inputs)},
        )
    if expected_candidate_digests is not None:
        target = archive_root / directory_name
        operation_id = find_recovery_operation(
            target,
            kind="repair-archive-record",
            target_identity=f"archive:{directory_name}",
            source_digests={
                "proposal.md": expected_proposal_sha256,
                "tasks.md": expected_tasks_sha256,
                **(
                    {".sdd/metadata.json": expected_metadata_sha256}
                    if expected_metadata_sha256 is not None
                    else {}
                ),
            },
            candidate_digests=expected_candidate_digests,
        )
        if operation_id is not None:
            protocol = resume_staged_recovery(
                target,
                operation_id,
                validate_candidates=lambda values: _validate_archive_candidates(
                    preflight.short_name, terminal_status, values
                ),
            )
            return _finish_archive_reconstruction(
                archive_root,
                directory_name,
                protocol.operation_id,
                protocol.outcome,
                tuple(protocol.applied),
                supplied,
                timestamp_moment,
            )
    source_digest_map = dict(preflight.projection.source_digests)
    if (
        ".sdd/metadata.json" in source_digest_map
        and expected_metadata_sha256 is None
        and preflight.reconstruction_required
    ):
        raise TransitionError(
            "ERROR_RECOVERY_EVIDENCE_MISMATCH",
            "rerun_repair_preflight",
            "Existing metadata bytes require an explicit source digest confirmation",
        )
    if (
        expected_metadata_sha256 is not None
        and source_digest_map.get(".sdd/metadata.json") != expected_metadata_sha256
    ):
        raise TransitionError(
            "ERROR_RECOVERY_EVIDENCE_MISMATCH",
            "rerun_repair_preflight",
            "Archived metadata bytes differ from the confirmed evidence digest",
        )
    if (
        preflight.proposal_sha256 != expected_proposal_sha256
        or preflight.tasks_sha256 != expected_tasks_sha256
    ):
        raise TransitionError(
            "ERROR_RECOVERY_EVIDENCE_MISMATCH",
            "rerun_repair_preflight",
            "Archived artifact bytes differ from the confirmed evidence digests",
        )
    if not preflight.missing and preflight.projection.disposition == "no-op":
        evidence = load_recovery_evidence(archive_root / directory_name)
        operation = evidence.get("operation", {}) if evidence is not None else {}
        return RepairResult(
            preflight,
            (),
            str(operation.get("operation_id", "")),
            True,
            _index_sha256(archive_root),
            (),
            outcome="ALREADY_APPLIED",
        )
    if preflight.reconstruction_required:
        return _execute_archive_reconstruction(
            archive_root,
            preflight,
            terminal_status=terminal_status,
            summary=summary,
            expected_candidate_digests=expected_candidate_digests,
            recovery_timestamp=recovery_timestamp,
        )
    current_status = preflight.current_status
    if current_status is None:
        raise TransitionError(
            "ERROR_RECOVERY_TARGET_INVALID",
            "inspect_archive_state",
            "Archived proposal is unreadable and cannot be repaired",
        )
    if current_status in TERMINAL_STATUSES and current_status != terminal_status:
        raise TransitionError(
            "ERROR_RECOVERY_STATUS_MISMATCH",
            "inspect_archive_state",
            "Existing terminal status disagrees with the requested repair",
        )
    moment = datetime.now(timezone.utc) if now_utc is None else now_utc
    if moment.tzinfo is None:
        raise ValueError("recovery timestamp must be timezone-aware")
    timestamp = (
        moment.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    directory = archive_root / directory_name
    machine = directory / ".sdd"
    if machine.is_symlink() or (machine.exists() and not machine.is_dir()):
        raise TransitionError(
            "ERROR_MACHINE_METADATA_INVALID",
            "inspect_machine_metadata",
            "Recovery metadata directory is unsafe",
        )
    repaired: list[str] = []
    if "terminal_status" in preflight.missing:
        atomic_replace_bytes(
            directory / "proposal.md",
            replace_status(
                (directory / "proposal.md").read_bytes(), current_status, terminal_status
            ),
        )
        repaired.append("terminal_status")
    operation_id = _repair_operation_id(
        directory_name=directory_name,
        terminal_status=terminal_status,
        summary=summary,
        expected_proposal_sha256=expected_proposal_sha256,
        expected_tasks_sha256=expected_tasks_sha256,
    )
    metadata = {
        "metadata_version": 1,
        "writer": {"engine": "sdd-workflow", "version": ENGINE_VERSION},
        "last_operation": {"kind": "repair-archive-record", "operation_id": operation_id},
        "recovery": {
            "recovery_version": RECOVERY_EVIDENCE_VERSION,
            "archive_date": preflight.archive_date,
            "short_name": preflight.short_name,
            "terminal_status": terminal_status,
            "summary": summary,
            "timestamp": timestamp,
            "confirmed_evidence": {
                "proposal_sha256": expected_proposal_sha256,
                "tasks_sha256": expected_tasks_sha256,
            },
            "operation": {"kind": "repair-archive-record", "operation_id": operation_id},
        },
    }
    machine.mkdir(mode=0o700, exist_ok=True)
    atomic_replace_bytes(
        machine / "metadata.json",
        (json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
            "utf-8"
        ),
    )
    repaired.append("machine_evidence")
    scan = load_archive_records(archive_root)
    if scan.diagnostics:
        return RepairResult(
            preflight, tuple(repaired), operation_id, False, None, scan.diagnostics
        )
    _, _, digest = rebuild_archive_index(archive_root, scan.records)
    return RepairResult(preflight, tuple(repaired), operation_id, True, digest, ())


def validate_repairable_target(
    archive_root: Path, directory_name: str, *, allow_managed: bool = False
) -> tuple[Path, tuple[str, str, str | None]]:
    if archive_root.is_symlink() or not archive_root.is_dir():
        raise TransitionError(
            "ERROR_RECOVERY_TARGET_INVALID",
            "inspect_archive_state",
            f"Archive root is not a safe directory: {archive_root}",
        )
    identity = (
        _directory_identity(directory_name)
        if "/" not in directory_name and "\\" not in directory_name
        else None
    )
    if identity is None:
        raise TransitionError(
            "ERROR_RECOVERY_TARGET_INVALID",
            "inspect_archive_state",
            f"Archive directory name is unsupported: {directory_name}",
        )
    directory = archive_root / directory_name
    if directory.is_symlink() or not directory.is_dir():
        raise TransitionError(
            "ERROR_RECOVERY_TARGET_INVALID",
            "inspect_archive_state",
            f"Archive directory is unavailable: {directory_name}",
        )
    proposal = directory / "proposal.md"
    tasks = directory / "tasks.md"
    if (
        not proposal.is_file()
        or not tasks.is_file()
        or proposal.is_symlink()
        or tasks.is_symlink()
    ):
        raise TransitionError(
            "ERROR_RECOVERY_TARGET_INVALID",
            "inspect_archive_state",
            "Archive artifacts are missing or unsafe",
        )
    if _directory_has_terminal_metadata(directory) and not allow_managed:
        raise TransitionError(
            "ERROR_RECOVERY_NOT_APPLICABLE",
            "inspect_archive_state",
            "Archive directory already carries managed terminal evidence",
        )
    return directory, identity


def _execute_archive_reconstruction(
    archive_root: Path,
    preflight: RepairPreflight,
    *,
    terminal_status: str,
    summary: str,
    expected_candidate_digests: dict[str, str] | None,
    recovery_timestamp: str | None,
) -> RepairResult:
    projection = preflight.projection
    if projection.issues:
        issue = projection.issues[0]
        raise TransitionError(issue.code, issue.action, issue.message)
    if projection.required_inputs:
        raise TransitionError(
            "ERROR_RECOVERY_INPUT_REQUIRED",
            "provide_recovery_input",
            "Archive reconstruction requires explicit non-derived values",
            data={"required_inputs": list(projection.required_inputs)},
        )
    if recovery_timestamp != preflight.recovery_timestamp:
        raise TransitionError(
            "ERROR_RECOVERY_EVIDENCE_MISMATCH",
            "rerun_repair_preflight",
            "Confirmed recovery timestamp differs from the preflight candidate",
        )
    if expected_candidate_digests is None or (
        dict(projection.candidate_digests) != expected_candidate_digests
    ):
        raise TransitionError(
            "ERROR_RECOVERY_EVIDENCE_MISMATCH",
            "rerun_repair_preflight",
            "Confirmed archive candidate digests differ from the preflight projection",
        )
    assert projection.proposal_candidate is not None
    assert projection.tasks_candidate is not None
    assert projection.metadata_candidate is not None
    target = archive_root / preflight.directory_name
    metadata_path = target / ".sdd/metadata.json"
    metadata_original = (
        metadata_path.read_bytes()
        if metadata_path.is_file() and not metadata_path.is_symlink()
        else None
    )
    operation_id = _repair_operation_id(
        directory_name=preflight.directory_name,
        terminal_status=terminal_status,
        summary=summary,
        expected_proposal_sha256=preflight.proposal_sha256,
        expected_tasks_sha256=preflight.tasks_sha256,
    )
    protocol = execute_staged_recovery(
        target,
        kind="repair-archive-record",
        target_identity=f"archive:{preflight.directory_name}",
        operation_id=operation_id,
        artifacts=(
            RecoveryArtifact(
                "proposal.md",
                (target / "proposal.md").read_bytes(),
                projection.proposal_candidate,
            ),
            RecoveryArtifact(
                "tasks.md",
                (target / "tasks.md").read_bytes(),
                projection.tasks_candidate,
            ),
            RecoveryArtifact(
                ".sdd/metadata.json",
                metadata_original,
                projection.metadata_candidate,
            ),
        ),
        validate_candidates=lambda values: _validate_archive_candidates(
            preflight.short_name, terminal_status, values
        ),
    )
    return _finish_archive_reconstruction(
        archive_root,
        preflight.directory_name,
        protocol.operation_id,
        protocol.outcome,
        tuple(protocol.applied),
        RecoverySupplement(summary=summary),
        datetime.fromisoformat(recovery_timestamp.replace("Z", "+00:00")),
    )


def _finish_archive_reconstruction(
    archive_root: Path,
    directory_name: str,
    operation_id: str,
    outcome: str,
    repaired: tuple[str, ...],
    supplement: RecoverySupplement,
    now_utc: datetime | None,
) -> RepairResult:
    scan = load_archive_records(archive_root)
    if scan.diagnostics:
        preflight = preflight_archive_repair(
            archive_root,
            directory_name,
            supplement=supplement,
            now_utc=now_utc,
        )
        return RepairResult(
            preflight,
            repaired,
            operation_id,
            False,
            None,
            scan.diagnostics,
            outcome=outcome,
        )
    _, _, digest = rebuild_archive_index(archive_root, scan.records)
    preflight = preflight_archive_repair(
        archive_root,
        directory_name,
        supplement=supplement,
        now_utc=now_utc,
    )
    return RepairResult(
        preflight,
        repaired,
        operation_id,
        True,
        digest,
        (),
        outcome=outcome,
    )


def _validate_archive_candidates(
    short_name: str, terminal_status: str, candidates: dict[str, bytes]
) -> None:
    try:
        proposal = candidates["proposal.md"].decode("utf-8", errors="strict")
        tasks = candidates["tasks.md"].decode("utf-8", errors="strict")
        metadata = json.loads(
            candidates[".sdd/metadata.json"].decode("utf-8", errors="strict")
        )
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TransitionError(
            "ERROR_RECOVERY_CANDIDATE_INVALID",
            "report_internal_error",
            "Archive recovery candidates are incomplete or invalid",
        ) from error
    outcome = parse_with_schema(
        short_name=short_name,
        proposal_text=proposal,
        task_scan=scan_tasks(tasks),
    )
    if (
        outcome.model is None
        or outcome.model.status != terminal_status
        or any(item.severity.value == "error" for item in outcome.diagnostics)
        or not outcome.task_counts_reliable
        or not isinstance(metadata, dict)
        or "recovery" not in metadata
        or "terminal" in metadata
    ):
        raise TransitionError(
            "ERROR_RECOVERY_CANDIDATE_INVALID",
            "report_internal_error",
            "Archive recovery candidates fail strict terminal validation",
        )


def _requires_reconstruction(
    short_name: str, proposal_bytes: bytes, tasks_bytes: bytes
) -> bool:
    try:
        proposal = proposal_bytes.decode("utf-8", errors="strict")
        tasks = tasks_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return True
    scan = scan_tasks(tasks)
    outcome = parse_with_schema(
        short_name=short_name,
        proposal_text=proposal,
        task_scan=scan,
    )
    return (
        outcome.model is None
        or outcome.model.status is None
        or not scan.counts_reliable
        or any(item.severity.value == "error" for item in outcome.diagnostics)
    )


def _recovery_timestamp(now_utc: datetime | None) -> str:
    moment = datetime.now(timezone.utc) if now_utc is None else now_utc
    if moment.tzinfo is None:
        raise ValueError("recovery timestamp must be timezone-aware")
    return (
        moment.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _recovery_metadata_bytes(
    *,
    archive_date: str,
    short_name: str,
    terminal_status: str,
    summary: str,
    timestamp: str,
    operation_id: str,
    proposal_sha256: str,
    tasks_sha256: str,
    reconstruction_digests: dict[str, str],
) -> bytes:
    value = {
        "metadata_version": 1,
        "writer": {"engine": "sdd-workflow", "version": ENGINE_VERSION},
        "last_operation": {
            "kind": "repair-archive-record",
            "operation_id": operation_id,
        },
        "recovery": {
            "recovery_version": RECOVERY_EVIDENCE_VERSION,
            "archive_date": archive_date,
            "short_name": short_name,
            "terminal_status": terminal_status,
            "summary": summary,
            "timestamp": timestamp,
            "confirmed_evidence": {
                "proposal_sha256": proposal_sha256,
                "tasks_sha256": tasks_sha256,
            },
            "operation": {
                "kind": "repair-archive-record",
                "operation_id": operation_id,
            },
        },
        "reconstruction": {
            "protocol_version": 1,
            "candidate_digests": reconstruction_digests,
        },
    }
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _index_sha256(archive_root: Path) -> str | None:
    path = archive_root / "INDEX.md"
    if path.is_symlink() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recovery_action_for_archive_diagnostic(
    archive_root: Path, diagnostic: ArchiveDiagnostic
) -> str:
    """Route a record diagnostic to recovery only when preflight recognizes it."""

    prefix = "sdd/archive/"
    if not diagnostic.path.startswith(prefix):
        return "inspect_archive_state"
    directory_name = diagnostic.path[len(prefix) :].split("/", 1)[0].split(":", 1)[0]
    try:
        preflight = preflight_archive_repair(archive_root, directory_name)
    except (OSError, UnicodeDecodeError, TransitionError):
        return "inspect_archive_state"
    projection = preflight.projection
    if projection.applicable or projection.required_inputs:
        return "repair_archive_record"
    return "inspect_archive_state"


def _parse_status(short_name: str, proposal_bytes: bytes, tasks_bytes: bytes) -> str | None:
    try:
        proposal_text = proposal_bytes.decode("utf-8")
        tasks_text = tasks_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None
    outcome = parse_with_schema(
        short_name=short_name,
        proposal_text=proposal_text,
        task_scan=scan_tasks(tasks_text),
    )
    return None if outcome.model is None else outcome.model.status


def _has_machine_evidence(directory: Path) -> bool:
    try:
        return load_recovery_evidence(directory) is not None
    except ValueError:
        return False


def _has_index_row(
    archive_root: Path, archive_date: str, short_name: str, status: str
) -> bool:
    index_path = archive_root / "INDEX.md"
    if index_path.is_symlink() or not index_path.is_file():
        return False
    rows, _ = parse_legacy_index(
        index_path.read_text(encoding="utf-8"), path="sdd/archive/INDEX.md"
    )
    return any(row[:3] == (archive_date, short_name, status) for row in rows)


def _matching_index_summaries(
    archive_root: Path, archive_date: str, short_name: str, status: str
) -> tuple[str, ...]:
    index_path = archive_root / "INDEX.md"
    if index_path.is_symlink() or not index_path.is_file():
        return ()
    rows, diagnostics = parse_legacy_index(
        index_path.read_text(encoding="utf-8"), path="sdd/archive/INDEX.md"
    )
    if diagnostics:
        return ()
    return tuple(
        row[3] for row in rows if row[:3] == (archive_date, short_name, status)
    )


def _blocked_projection(
    projection: RecoveryProjection, issue: RecoveryIssue
) -> RecoveryProjection:
    return replace(
        projection,
        disposition="blocked",
        candidate_digests=(),
        required_inputs=(),
        changes=(),
        issues=(issue,),
        proposal_candidate=None,
        tasks_candidate=None,
        metadata_candidate=None,
    )


def _repair_operation_id(
    *,
    directory_name: str,
    terminal_status: str,
    summary: str,
    expected_proposal_sha256: str,
    expected_tasks_sha256: str,
) -> str:
    payload = json.dumps(
        {
            "kind": "repair-archive-record",
            "directory_name": directory_name,
            "terminal_status": terminal_status,
            "summary_utf8_sha256": hashlib.sha256(summary.encode("utf-8")).hexdigest(),
            "confirmed_evidence": {
                "proposal_sha256": expected_proposal_sha256,
                "tasks_sha256": expected_tasks_sha256,
            },
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
