"""Terminal transition validation and, later, commit orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime, timezone
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path

from .active_metadata import ActiveMetadata, parse_active_metadata
from .approval import (
    approval_manifest_sha256,
    compare_approval_manifests,
    parse_approval_manifest,
    project_approval_manifest,
)
from .discovery import ProposalPaths
from .managed_state import compare_attested_state
from .model import CanonicalProposal
from .snapshot import SnapshotManifest
from .summary_input import fold_summary_for_index
from .transitions import TransitionError
from .active_metadata import serialize_active_metadata
from .atomic_write import atomic_replace_bytes
from .managed_state import create_attestation
from .transitions import replace_status
from .snapshot import build_snapshot
from .archive_model import load_archive_records
from .archive_index import rebuild_archive_index
from .archive_index import validate_archive_index
from .version import ENGINE_VERSION


@dataclass(frozen=True, slots=True)
class TerminalValidation:
    command: str
    source_status: str
    terminal_status: str
    archive_date: str
    destination: Path
    summary: str
    index_summary: str
    before_snapshot: SnapshotManifest
    metadata: ActiveMetadata | None

    def predicted_changes(self) -> tuple[dict[str, str], ...]:
        return (
            {"kind": "write_terminal_metadata", "path": ".sdd/metadata.json"},
            {"kind": "replace_status", "value": self.terminal_status},
            {"kind": "move_directory", "destination": self.destination.as_posix()},
            {"kind": "rebuild_index", "path": "sdd/archive/INDEX.md"},
        )


@dataclass(frozen=True, slots=True)
class TerminalCommitResult:
    validation: TerminalValidation
    operation_id: str
    after_snapshot: SnapshotManifest
    destination: Path
    index_stale: bool
    index_diagnostics: tuple[dict[str, str], ...] = ()
    applied: bool = True
    outcome: str = "APPLIED"


def validate_archive(
    paths: ProposalPaths,
    model: CanonicalProposal,
    current_snapshot: SnapshotManifest,
    expected_snapshot: str,
    summary: str,
    *,
    local_date: date | None = None,
) -> TerminalValidation:
    _require_snapshot(current_snapshot, expected_snapshot)
    if model.status != "approved":
        raise TransitionError(
            "ERROR_INVALID_SOURCE_STATE",
            "refresh_status",
            f"archive requires approved status, found: {model.status!r}",
        )
    if not model.tasks:
        raise TransitionError(
            "ERROR_ARCHIVE_TASKS_REQUIRED",
            "complete_remaining_tasks",
            "archive requires at least one canonical task",
        )
    incomplete = [item.ordinal for item in model.tasks if not item.completed]
    if incomplete:
        raise TransitionError(
            "ERROR_ARCHIVE_TASKS_INCOMPLETE",
            "complete_remaining_tasks",
            "archive requires every canonical task to be complete",
            data={"incomplete_tasks": incomplete},
        )
    if model.change_type == "研究" and not _research_conclusion_items(model):
        raise TransitionError(
            "ERROR_RESEARCH_CONCLUSION_REQUIRED",
            "complete_research_conclusion",
            "archive requires a non-empty canonical research conclusion",
        )
    metadata = _validate_attested_approval(paths, model)
    archive_date = (date.today() if local_date is None else local_date).isoformat()
    destination = paths.sdd_root / "archive" / f"{archive_date}-{model.short_name}"
    _validate_destination(paths.sdd_root / "archive", destination)
    return TerminalValidation(
        command="archive",
        source_status="approved",
        terminal_status="completed",
        archive_date=archive_date,
        destination=destination,
        summary=summary,
        index_summary=fold_summary_for_index(summary),
        before_snapshot=current_snapshot,
        metadata=metadata,
    )


def _research_conclusion_items(model: CanonicalProposal) -> tuple[str, ...]:
    for extension in model.extensions:
        if extension.namespace != "sdd.research.conclusion":
            continue
        value = extension.value
        if isinstance(value, dict) and isinstance(value.get("items"), list):
            return tuple(
                item for item in value["items"] if isinstance(item, str) and item
            )
    return ()


def validate_abandon(
    paths: ProposalPaths,
    model: CanonicalProposal,
    current_snapshot: SnapshotManifest,
    expected_snapshot: str,
    summary: str,
    *,
    local_date: date | None = None,
) -> TerminalValidation:
    _require_snapshot(current_snapshot, expected_snapshot)
    if model.status not in {"draft", "approved"}:
        raise TransitionError(
            "ERROR_INVALID_SOURCE_STATE",
            "refresh_status",
            f"abandon requires draft or approved status, found: {model.status!r}",
        )
    metadata: ActiveMetadata | None
    if model.status == "approved":
        metadata = _validate_attested_approval(paths, model)
    else:
        metadata = _validate_draft_abandonment(paths, model)
    archive_date = (date.today() if local_date is None else local_date).isoformat()
    destination = (
        paths.sdd_root / "archive" / f"{archive_date}-{model.short_name}-abandoned"
    )
    _validate_destination(paths.sdd_root / "archive", destination)
    return TerminalValidation(
        command="abandon",
        source_status=model.status,
        terminal_status="abandoned",
        archive_date=archive_date,
        destination=destination,
        summary=summary,
        index_summary=fold_summary_for_index(summary),
        before_snapshot=current_snapshot,
        metadata=metadata,
    )


def commit_terminal_transition(
    paths: ProposalPaths,
    model: CanonicalProposal,
    validation: TerminalValidation,
    *,
    now_utc: datetime | None = None,
) -> TerminalCommitResult:
    moment = datetime.now(timezone.utc) if now_utc is None else now_utc
    if moment.tzinfo is None:
        raise ValueError("terminal timestamp must be timezone-aware")
    timestamp = moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    operation_id = _terminal_operation_id(validation)
    terminal = {
        "terminal_metadata_version": 1,
        "archive_date": validation.archive_date,
        "short_name": model.short_name,
        "source_status": model.status,
        "terminal_status": validation.terminal_status,
        "timestamp": timestamp,
        "summary": validation.summary,
        "destination_directory": validation.destination.name,
        "source_snapshot": validation.before_snapshot.to_dict(),
        "operation": {"kind": validation.command, "operation_id": operation_id},
    }
    after_model = replace(model, status=validation.terminal_status)
    if validation.metadata is None:
        metadata_value = {
            "metadata_version": 1,
            "writer": {"engine": "sdd-workflow", "version": ENGINE_VERSION},
            "last_operation": {"kind": validation.command, "operation_id": operation_id},
            "terminal": terminal,
        }
        metadata_bytes = (
            json.dumps(metadata_value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
    else:
        metadata = ActiveMetadata(
            approval_state=validation.metadata.approval_state,
            approval_model_version=validation.metadata.approval_model_version,
            manifest_sha256=validation.metadata.manifest_sha256,
            operation_kind=validation.command,
            operation_id=operation_id,
            revision=validation.metadata.revision,
            terminal=terminal,
        )
        metadata = replace(metadata, attestation=create_attestation(after_model, metadata))
        metadata_bytes = serialize_active_metadata(metadata)

    archive_root = validation.destination.parent
    if archive_root.is_symlink() or (archive_root.exists() and not archive_root.is_dir()):
        raise TransitionError(
            "ERROR_ARCHIVE_PATH_INVALID",
            "inspect_archive_state",
            f"Archive root is not a safe directory: {archive_root}",
        )
    archive_root.mkdir(mode=0o755, exist_ok=True)
    if validation.destination.exists() or validation.destination.is_symlink():
        raise TransitionError(
            "ERROR_ARCHIVE_DESTINATION_COLLISION",
            "inspect_archive_state",
            f"Archive destination already exists: {validation.destination}",
        )
    machine = paths.directory / ".sdd"
    if machine.is_symlink() or (machine.exists() and not machine.is_dir()):
        raise TransitionError(
            "ERROR_MACHINE_METADATA_INVALID",
            "inspect_machine_metadata",
            "Terminal metadata directory is unsafe",
        )
    machine.mkdir(mode=0o700, exist_ok=True)
    atomic_replace_bytes(machine / "metadata.json", metadata_bytes)
    atomic_replace_bytes(
        paths.proposal,
        replace_status(paths.proposal.read_bytes(), model.status or "", validation.terminal_status),
    )
    return _move_and_rebuild(paths.directory, validation, operation_id)


def _move_and_rebuild(
    source_directory: Path,
    validation: TerminalValidation,
    operation_id: str,
) -> TerminalCommitResult:
    archive_root = validation.destination.parent
    os.rename(source_directory, validation.destination)
    archived_proposal = validation.destination / "proposal.md"
    archived_tasks = validation.destination / "tasks.md"
    after_snapshot = build_snapshot(
        archived_proposal.read_bytes(), archived_tasks.read_bytes()
    )
    scan = load_archive_records(archive_root)
    diagnostics = tuple(item.to_dict() for item in scan.diagnostics)
    if diagnostics:
        return TerminalCommitResult(
            validation,
            operation_id,
            after_snapshot,
            validation.destination,
            True,
            diagnostics,
        )
    try:
        rebuild_archive_index(archive_root, scan.records)
    except OSError as error:
        return TerminalCommitResult(
            validation,
            operation_id,
            after_snapshot,
            validation.destination,
            True,
            ({"code": "ERROR_INDEX_REBUILD", "path": "sdd/archive/INDEX.md", "message": str(error)},),
        )
    return TerminalCommitResult(validation, operation_id, after_snapshot, validation.destination, False)


def resume_staged_terminal_transition(
    paths: ProposalPaths,
    model: CanonicalProposal,
    current_snapshot: SnapshotManifest,
    command: str,
    expected_snapshot: str,
    summary: str,
) -> TerminalCommitResult | None:
    metadata_path = paths.directory / ".sdd/metadata.json"
    if metadata_path.is_symlink() or not metadata_path.is_file():
        return None
    try:
        value = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    terminal = value.get("terminal") if isinstance(value, dict) else None
    if not isinstance(terminal, dict):
        return None
    operation = terminal.get("operation")
    source_snapshot = terminal.get("source_snapshot")
    expected_terminal = "completed" if command == "archive" else "abandoned"
    if (
        terminal.get("short_name") != model.short_name
        or terminal.get("terminal_status") != expected_terminal
        or terminal.get("summary") != summary
        or not isinstance(operation, dict)
        or operation.get("kind") != command
        or not isinstance(source_snapshot, dict)
        or source_snapshot.get("snapshot_digest") != expected_snapshot
    ):
        raise TransitionError(
            "AMBIGUOUS_STATE",
            "inspect_machine_metadata",
            "Staged terminal metadata does not prove the requested operation",
        )
    try:
        snapshot = SnapshotManifest(
            snapshot_version=source_snapshot["snapshot_version"],
            proposal_sha256=source_snapshot["proposal_sha256"],
            tasks_sha256=source_snapshot["tasks_sha256"],
            snapshot_digest=source_snapshot["snapshot_digest"],
        )
        destination = paths.sdd_root / "archive" / terminal["destination_directory"]
        validation = TerminalValidation(
            command=command,
            source_status=terminal["source_status"],
            terminal_status=terminal["terminal_status"],
            archive_date=terminal["archive_date"],
            destination=destination,
            summary=summary,
            index_summary=fold_summary_for_index(summary),
            before_snapshot=snapshot,
            metadata=None,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise TransitionError(
            "AMBIGUOUS_STATE",
            "inspect_machine_metadata",
            "Staged terminal metadata is incomplete",
        ) from error
    operation_id = _terminal_operation_id(validation)
    if operation.get("operation_id") != operation_id:
        raise TransitionError(
            "AMBIGUOUS_STATE",
            "inspect_machine_metadata",
            "Staged terminal operation identity does not match its inputs",
        )
    if destination.exists() or destination.is_symlink():
        raise TransitionError(
            "AMBIGUOUS_STATE",
            "inspect_archive_state",
            "Source and destination both exist for a staged terminal operation",
        )
    if model.status == validation.source_status:
        if current_snapshot.snapshot_digest != expected_snapshot:
            raise TransitionError(
                "ERROR_SNAPSHOT_MISMATCH", "refresh_status", "Staged source bytes changed"
            )
        atomic_replace_bytes(
            paths.proposal,
            replace_status(
                paths.proposal.read_bytes(), validation.source_status, validation.terminal_status
            ),
        )
    elif model.status == validation.terminal_status:
        source_proposal = replace_status(
            paths.proposal.read_bytes(), validation.terminal_status, validation.source_status
        )
        reconstructed = build_snapshot(source_proposal, paths.tasks.read_bytes())
        if reconstructed.snapshot_digest != expected_snapshot:
            raise TransitionError(
                "AMBIGUOUS_STATE",
                "inspect_machine_metadata",
                "Terminal status is staged but the exact source snapshot cannot be reconstructed",
            )
    else:
        raise TransitionError(
            "AMBIGUOUS_STATE",
            "inspect_machine_metadata",
            "Current status is incompatible with staged terminal evidence",
        )
    return _move_and_rebuild(paths.directory, validation, operation_id)


def find_committed_terminal_retry(
    project_root: Path,
    short_name: str,
    command: str,
    expected_snapshot: str,
    summary: str,
) -> TerminalCommitResult | None:
    sdd_root = project_root / "sdd"
    source = sdd_root / short_name
    if source.exists() or source.is_symlink():
        return None
    archive_root = sdd_root / "archive"
    if archive_root.is_symlink() or not archive_root.is_dir():
        return None
    candidates: list[tuple[Path, dict[str, object]]] = []
    for directory in sorted(archive_root.iterdir(), key=lambda item: item.name):
        metadata_path = directory / ".sdd/metadata.json"
        if directory.is_symlink() or not directory.is_dir() or not metadata_path.is_file():
            continue
        try:
            value = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        terminal = value.get("terminal") if isinstance(value, dict) else None
        if isinstance(terminal, dict) and terminal.get("short_name") == short_name:
            candidates.append((directory, terminal))
    if not candidates:
        return None
    matches: list[tuple[Path, dict[str, object]]] = []
    for directory, terminal in candidates:
        source_snapshot = terminal.get("source_snapshot")
        operation = terminal.get("operation")
        if (
            terminal.get("terminal_status")
            == ("completed" if command == "archive" else "abandoned")
            and terminal.get("summary") == summary
            and terminal.get("destination_directory") == directory.name
            and isinstance(source_snapshot, dict)
            and source_snapshot.get("snapshot_digest") == expected_snapshot
            and isinstance(operation, dict)
            and operation.get("kind") == command
        ):
            try:
                snapshot = SnapshotManifest(
                    snapshot_version=source_snapshot["snapshot_version"],
                    proposal_sha256=source_snapshot["proposal_sha256"],
                    tasks_sha256=source_snapshot["tasks_sha256"],
                    snapshot_digest=source_snapshot["snapshot_digest"],
                )
                validation = TerminalValidation(
                    command=command,
                    source_status=terminal["source_status"],
                    terminal_status=terminal["terminal_status"],
                    archive_date=terminal["archive_date"],
                    destination=directory,
                    summary=summary,
                    index_summary=fold_summary_for_index(summary),
                    before_snapshot=snapshot,
                    metadata=None,
                )
            except (KeyError, TypeError, ValueError):
                continue
            if operation.get("operation_id") == _terminal_operation_id(validation):
                matches.append((directory, terminal))
    if len(matches) != 1:
        raise TransitionError(
            "AMBIGUOUS_STATE",
            "inspect_archive_state",
            "Archived directories exist for this short name but do not uniquely prove the requested operation",
        )
    directory, terminal = matches[0]
    source_snapshot = terminal["source_snapshot"]
    snapshot = SnapshotManifest(
        snapshot_version=source_snapshot["snapshot_version"],
        proposal_sha256=source_snapshot["proposal_sha256"],
        tasks_sha256=source_snapshot["tasks_sha256"],
        snapshot_digest=source_snapshot["snapshot_digest"],
    )
    validation = TerminalValidation(
        command=command,
        source_status=terminal["source_status"],
        terminal_status=terminal["terminal_status"],
        archive_date=terminal["archive_date"],
        destination=directory,
        summary=summary,
        index_summary=fold_summary_for_index(summary),
        before_snapshot=snapshot,
        metadata=None,
    )
    after = build_snapshot(
        (directory / "proposal.md").read_bytes(), (directory / "tasks.md").read_bytes()
    )
    scan = load_archive_records(archive_root)
    diagnostics = [item.to_dict() for item in scan.diagnostics]
    if not diagnostics:
        differences = validate_archive_index(archive_root, scan.records)
        diagnostics.extend(
            {
                "code": "ERROR_INDEX_STALE",
                "path": "sdd/archive/INDEX.md",
                "message": str(item.to_dict()),
            }
            for item in differences
        )
    stale = bool(diagnostics)
    return TerminalCommitResult(
        validation=validation,
        operation_id=terminal["operation"]["operation_id"],
        after_snapshot=after,
        destination=directory,
        index_stale=stale,
        index_diagnostics=tuple(diagnostics),
        applied=False,
        outcome="COMMITTED_DERIVED_ARTIFACT_STALE" if stale else "ALREADY_APPLIED",
    )


def _terminal_operation_id(validation: TerminalValidation) -> str:
    payload = json.dumps(
        {
            "kind": validation.command,
            "terminal_status": validation.terminal_status,
            "source_status": validation.source_status,
            "source_snapshot": validation.before_snapshot.to_dict(),
            "destination_directory": validation.destination.name,
            "summary_utf8_sha256": hashlib.sha256(
                validation.summary.encode("utf-8")
            ).hexdigest(),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_draft_abandonment(
    paths: ProposalPaths, model: CanonicalProposal
) -> ActiveMetadata | None:
    machine = paths.directory / ".sdd"
    if not machine.exists():
        return None
    if machine.is_dir() and not any(machine.iterdir()):
        return None
    manifest_path = machine / "approval-manifest.json"
    metadata_path = machine / "metadata.json"
    if (
        machine.is_symlink()
        or not machine.is_dir()
        or manifest_path.is_symlink()
        or metadata_path.is_symlink()
        or not manifest_path.is_file()
        or not metadata_path.is_file()
    ):
        raise TransitionError(
            "PARTIAL_TRANSITION_DETECTED",
            "inspect_machine_metadata",
            "Draft machine approval artifacts are incomplete or unsafe",
        )
    manifest_bytes = manifest_path.read_bytes()
    metadata = parse_active_metadata(metadata_path.read_bytes())
    if approval_manifest_sha256(manifest_bytes) != metadata.manifest_sha256:
        raise TransitionError(
            "ERROR_APPROVAL_MANIFEST_IDENTITY_MISMATCH",
            "inspect_machine_metadata",
            "Approval Manifest identity differs from draft metadata",
        )
    if (
        metadata.approval_state != "invalidated"
        or not isinstance(metadata.revision, dict)
        or metadata.revision.get("phase") != "open"
        or metadata.attestation is None
    ):
        raise TransitionError(
            "OUT_OF_BAND_DRIFT",
            "inspect_managed_state_drift",
            "Draft status is not backed by an authorized open revision",
        )
    drift = compare_attested_state(metadata.attestation, model, metadata)
    if drift:
        raise TransitionError(
            "OUT_OF_BAND_DRIFT",
            "inspect_managed_state_drift",
            "Draft managed fields differ from revision attestation; editor and cause are unknown",
            data={"differences": [item.to_dict() for item in drift]},
        )
    return metadata


def _validate_attested_approval(
    paths: ProposalPaths, model: CanonicalProposal
) -> ActiveMetadata:
    machine = paths.directory / ".sdd"
    manifest_path = machine / "approval-manifest.json"
    metadata_path = machine / "metadata.json"
    if (
        machine.is_symlink()
        or not machine.is_dir()
        or manifest_path.is_symlink()
        or metadata_path.is_symlink()
        or not manifest_path.is_file()
        or not metadata_path.is_file()
    ):
        raise TransitionError(
            "ERROR_APPROVAL_MANIFEST_REQUIRED",
            "establish_approval_manifest",
            "Terminal mutation requires a valid machine approval baseline",
        )
    manifest_bytes = manifest_path.read_bytes()
    manifest = parse_approval_manifest(manifest_bytes)
    metadata = parse_active_metadata(metadata_path.read_bytes())
    if approval_manifest_sha256(manifest_bytes) != metadata.manifest_sha256:
        raise TransitionError(
            "ERROR_APPROVAL_MANIFEST_IDENTITY_MISMATCH",
            "inspect_machine_metadata",
            "Approval Manifest identity differs from metadata",
        )
    if metadata.approval_state != "active" or metadata.revision is not None:
        raise TransitionError(
            "ERROR_METADATA_STATE_MISMATCH",
            "inspect_machine_metadata",
            "Terminal mutation requires active approval metadata",
        )
    if metadata.attestation is None:
        raise TransitionError(
            "ERROR_MANAGED_STATE_ATTESTATION_REQUIRED",
            "establish_managed_state_attestation",
            "Terminal mutation requires managed-state attestation",
        )
    drift = compare_attested_state(metadata.attestation, model, metadata)
    if drift:
        raise TransitionError(
            "OUT_OF_BAND_DRIFT",
            "inspect_managed_state_drift",
            "Managed fields differ from attestation; editor and cause are unknown",
            data={"differences": [item.to_dict() for item in drift]},
        )
    semantic = compare_approval_manifests(
        manifest,
        project_approval_manifest(
            model, approval_model_version=manifest.approval_model_version
        ),
    )
    if semantic:
        raise TransitionError(
            "ERROR_APPROVED_PLAN_CHANGED",
            "begin_revision_and_reapprove",
            "Approval-relevant content differs from the active Manifest",
            data={"differences": [item.to_dict() for item in semantic]},
        )
    return metadata


def _require_snapshot(current: SnapshotManifest, expected: str) -> None:
    if current.snapshot_digest != expected:
        raise TransitionError(
            "ERROR_SNAPSHOT_MISMATCH",
            "refresh_status",
            "Expected snapshot does not match current proposal artifacts",
        )


def _validate_destination(archive_root: Path, destination: Path) -> None:
    if archive_root.is_symlink() or (archive_root.exists() and not archive_root.is_dir()):
        raise TransitionError(
            "ERROR_ARCHIVE_PATH_INVALID",
            "inspect_archive_state",
            f"Archive root is not a safe directory: {archive_root}",
        )
    if destination.is_symlink() or destination.exists():
        raise TransitionError(
            "ERROR_ARCHIVE_DESTINATION_COLLISION",
            "inspect_archive_state",
            f"Archive destination already exists: {destination}",
        )
