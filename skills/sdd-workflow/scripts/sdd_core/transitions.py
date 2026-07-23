"""Experimental active proposal state transitions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path

from .active_metadata import ActiveMetadata, parse_active_metadata, serialize_active_metadata
from .approval import (
    APPROVAL_MODEL_VERSION,
    ApprovalDifference,
    approval_manifest_sha256,
    compare_approval_manifests,
    parse_approval_manifest,
    project_approval_manifest,
    serialize_approval_manifest,
)
from .atomic_write import atomic_replace_bytes
from .discovery import ProposalPaths
from .model import CanonicalProposal
from .managed_state import compare_attested_state, create_attestation
from .snapshot import SnapshotManifest, build_snapshot
from .task_identity import task_digest


class TransitionError(RuntimeError):
    def __init__(
        self,
        code: str,
        action: str,
        message: str,
        *,
        data: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.action = action
        self.message = message
        self.data = {} if data is None else data


@dataclass(frozen=True, slots=True)
class TransitionResult:
    before_snapshot: SnapshotManifest
    after_snapshot: SnapshotManifest
    operation_id: str
    applied: bool
    differences: tuple[ApprovalDifference, ...] = ()
    result: str = "APPLIED"


@dataclass(frozen=True, slots=True)
class CompleteTaskValidation:
    task_ordinal: int
    task_text: str
    task_digest: str
    metadata: ActiveMetadata


def approve_proposal(
    paths: ProposalPaths,
    model: CanonicalProposal,
    current_snapshot: SnapshotManifest,
    expected_snapshot: str,
    *,
    establish_manifest: bool = False,
) -> TransitionResult:
    _require_expected_snapshot(current_snapshot, expected_snapshot)
    expected_status = "approved" if establish_manifest else "draft"
    if model.status != expected_status:
        raise TransitionError(
            "ERROR_INVALID_SOURCE_STATE",
            "refresh_status",
            f"approve requires {expected_status} status, found: {model.status!r}",
        )

    manifest = project_approval_manifest(model)
    manifest_bytes = serialize_approval_manifest(manifest)
    manifest_sha = approval_manifest_sha256(manifest_bytes)
    operation_kind = "establish-manifest" if establish_manifest else "approve"
    operation_id = _operation_id(operation_kind, expected_snapshot, manifest_sha)
    metadata = ActiveMetadata(
        approval_state="active",
        approval_model_version=APPROVAL_MODEL_VERSION,
        manifest_sha256=manifest_sha,
        operation_kind=operation_kind,
        operation_id=operation_id,
    )
    approved_model = model if model.status == "approved" else replace(model, status="approved")
    metadata = replace(metadata, attestation=create_attestation(approved_model, metadata))
    metadata_bytes = serialize_active_metadata(metadata)
    machine_dir = _prepare_machine_directory(paths.directory)
    manifest_path = machine_dir / "approval-manifest.json"
    metadata_path = machine_dir / "metadata.json"
    _prepare_approval_targets(
        model,
        manifest_path,
        metadata_path,
        manifest_bytes,
        metadata_bytes,
        establish_manifest=establish_manifest,
    )

    atomic_replace_bytes(manifest_path, manifest_bytes)
    atomic_replace_bytes(metadata_path, metadata_bytes)
    if not establish_manifest:
        proposal_bytes = paths.proposal.read_bytes()
        updated_proposal = replace_status(proposal_bytes, "draft", "approved")
        atomic_replace_bytes(paths.proposal, updated_proposal)

    after_proposal = paths.proposal.read_bytes()
    after_tasks = paths.tasks.read_bytes()
    after = build_snapshot(after_proposal, after_tasks)
    if parse_approval_manifest(manifest_path.read_bytes()) != manifest:
        raise TransitionError(
            "ERROR_METADATA_STATE_MISMATCH",
            "inspect_machine_metadata",
            "Stored Approval Manifest did not validate after approve",
        )
    if parse_active_metadata(metadata_path.read_bytes()) != metadata:
        raise TransitionError(
            "ERROR_METADATA_STATE_MISMATCH",
            "inspect_machine_metadata",
            "Stored active metadata did not validate after approve",
        )
    return TransitionResult(current_snapshot, after, operation_id, True)


def begin_revision(
    paths: ProposalPaths,
    model: CanonicalProposal,
    current_snapshot: SnapshotManifest,
    expected_snapshot: str,
) -> TransitionResult:
    machine_dir, manifest_path, metadata_path = _require_machine_files(paths.directory)
    manifest_bytes = manifest_path.read_bytes()
    manifest = parse_approval_manifest(manifest_bytes)
    metadata = parse_active_metadata(metadata_path.read_bytes())
    _require_manifest_identity(metadata, manifest_bytes)
    current_manifest = project_approval_manifest(
        model, approval_model_version=manifest.approval_model_version
    )
    differences = compare_approval_manifests(manifest, current_manifest)
    differences_value = [item.to_dict() for item in differences]
    operation_id = _revision_operation_id(
        expected_snapshot, metadata.manifest_sha256, differences_value
    )

    if model.status == "draft":
        return _resume_committed_revision(
            paths,
            model,
            current_snapshot,
            expected_snapshot,
            metadata,
            operation_id,
            differences,
            metadata_path,
        )
    _require_expected_snapshot(current_snapshot, expected_snapshot)
    if model.status != "approved":
        raise TransitionError(
            "ERROR_INVALID_SOURCE_STATE",
            "refresh_status",
            f"begin-revision requires approved status, found: {model.status!r}",
        )
    if metadata.approval_state == "active":
        if metadata.revision is not None:
            raise _metadata_mismatch("Active approval cannot contain a revision marker")
        if metadata.attestation is None:
            raise _metadata_mismatch("Active approval lacks managed-state attestation")
        drift = compare_attested_state(metadata.attestation, model, metadata)
        if drift:
            raise TransitionError(
                "OUT_OF_BAND_DRIFT",
                "inspect_managed_state_drift",
                "Current managed fields differ from the last attested state; the editor or cause is unknown",
                data={"differences": [item.to_dict() for item in drift]},
            )
    elif not _matching_revision(metadata, operation_id, expected_snapshot, "pending"):
        raise _metadata_mismatch("Approval metadata is not active or a matching pending revision")

    marker = _revision_marker("pending", expected_snapshot, differences_value)
    pending = ActiveMetadata(
        approval_state="invalidated",
        approval_model_version=metadata.approval_model_version,
        manifest_sha256=metadata.manifest_sha256,
        operation_kind="begin-revision",
        operation_id=operation_id,
        revision=marker,
        attestation=metadata.attestation,
    )
    atomic_replace_bytes(metadata_path, serialize_active_metadata(pending))
    updated_proposal = replace_status(paths.proposal.read_bytes(), "approved", "draft")
    atomic_replace_bytes(paths.proposal, updated_proposal)
    opened = _opened_revision_metadata(pending, replace(model, status="draft"))
    atomic_replace_bytes(metadata_path, serialize_active_metadata(opened))
    after = build_snapshot(paths.proposal.read_bytes(), paths.tasks.read_bytes())
    return TransitionResult(current_snapshot, after, operation_id, True, differences)


def validate_complete_task(
    paths: ProposalPaths,
    model: CanonicalProposal,
    current_snapshot: SnapshotManifest,
    expected_snapshot: str,
    task_number: int,
    expected_task_digest: str,
) -> CompleteTaskValidation:
    """Validate complete-task inputs without changing any artifact."""

    _require_expected_snapshot(current_snapshot, expected_snapshot)
    _, manifest_path, metadata_path = _require_machine_files(paths.directory)
    manifest_bytes = manifest_path.read_bytes()
    manifest = parse_approval_manifest(manifest_bytes)
    metadata = parse_active_metadata(metadata_path.read_bytes())
    _require_manifest_identity(metadata, manifest_bytes)
    if metadata.approval_state != "active" or metadata.revision is not None:
        raise _metadata_mismatch("complete-task requires active approval metadata")
    if metadata.attestation is None:
        raise TransitionError(
            "ERROR_MANAGED_STATE_ATTESTATION_REQUIRED",
            "establish_managed_state_attestation",
            "Approved proposal has no managed-state attestation",
        )
    drift = compare_attested_state(metadata.attestation, model, metadata)
    if drift:
        raise TransitionError(
            "OUT_OF_BAND_DRIFT",
            "inspect_managed_state_drift",
            "Current managed fields differ from the last attested state; the editor or cause is unknown",
            data={"differences": [item.to_dict() for item in drift]},
        )
    if model.status != "approved":
        raise TransitionError(
            "ERROR_INVALID_SOURCE_STATE",
            "refresh_status",
            f"complete-task requires approved status, found: {model.status!r}",
        )
    if type(task_number) is not int or task_number < 1 or task_number > len(model.tasks):
        raise TransitionError(
            "ERROR_TASK_NOT_FOUND",
            "refresh_status",
            f"Task ordinal is outside the current proposal: {task_number!r}",
        )
    task = model.tasks[task_number - 1]
    current_digest = task_digest(task.text)
    if current_digest != expected_task_digest:
        raise TransitionError(
            "ERROR_TASK_IDENTITY_MISMATCH",
            "refresh_status",
            "Expected task digest does not match the current canonical task text",
            data={
                "task_number": task_number,
                "current_task_digest": current_digest,
            },
        )
    current_manifest = project_approval_manifest(
        model, approval_model_version=manifest.approval_model_version
    )
    differences = compare_approval_manifests(manifest, current_manifest)
    if differences:
        raise TransitionError(
            "ERROR_APPROVED_PLAN_CHANGED",
            "begin_revision",
            "Current approval-relevant content differs from the Approval Manifest",
            data={"differences": [item.to_dict() for item in differences]},
        )
    return CompleteTaskValidation(
        task_ordinal=task.ordinal,
        task_text=task.text,
        task_digest=current_digest,
        metadata=metadata,
    )


def complete_task(
    paths: ProposalPaths,
    model: CanonicalProposal,
    current_snapshot: SnapshotManifest,
    expected_snapshot: str,
    task_number: int,
    expected_task_digest: str,
) -> TransitionResult:
    operation_id = _complete_task_operation_id(
        expected_snapshot, task_number, expected_task_digest
    )
    retry = _retry_complete_task_if_proven(
        paths,
        model,
        current_snapshot,
        expected_snapshot,
        task_number,
        expected_task_digest,
        operation_id,
    )
    if retry is not None:
        return retry
    validation = validate_complete_task(
        paths,
        model,
        current_snapshot,
        expected_snapshot,
        task_number,
        expected_task_digest,
    )
    task = model.tasks[task_number - 1]
    if task.completed:
        raise TransitionError(
            "ERROR_TASK_ALREADY_COMPLETED",
            "refresh_status",
            f"Task {task_number} is already completed without matching retry evidence",
        )
    after_tasks = tuple(
        replace(item, completed=True) if item.ordinal == task_number else item
        for item in model.tasks
    )
    after_model = replace(model, tasks=after_tasks)
    metadata = ActiveMetadata(
        approval_state=validation.metadata.approval_state,
        approval_model_version=validation.metadata.approval_model_version,
        manifest_sha256=validation.metadata.manifest_sha256,
        operation_kind="complete-task",
        operation_id=operation_id,
        revision=validation.metadata.revision,
    )
    metadata = replace(metadata, attestation=create_attestation(after_model, metadata))
    metadata_path = paths.directory / ".sdd/metadata.json"
    atomic_replace_bytes(metadata_path, serialize_active_metadata(metadata))
    updated_tasks = replace_task_completion(
        paths.tasks.read_bytes(), task.source_line, expected_task_digest
    )
    atomic_replace_bytes(paths.tasks, updated_tasks)
    after = build_snapshot(paths.proposal.read_bytes(), paths.tasks.read_bytes())
    return TransitionResult(current_snapshot, after, operation_id, True)


def _retry_complete_task_if_proven(
    paths: ProposalPaths,
    model: CanonicalProposal,
    current_snapshot: SnapshotManifest,
    expected_snapshot: str,
    task_number: int,
    expected_task_digest: str,
    operation_id: str,
) -> TransitionResult | None:
    machine = paths.directory / ".sdd"
    metadata_path = machine / "metadata.json"
    manifest_path = machine / "approval-manifest.json"
    if not metadata_path.is_file() or metadata_path.is_symlink():
        return None
    metadata = parse_active_metadata(metadata_path.read_bytes())
    if metadata.operation_kind != "complete-task" or metadata.operation_id != operation_id:
        return None
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise _retry_conflict("Matching operation evidence lacks a valid Approval Manifest")
    manifest_bytes = manifest_path.read_bytes()
    manifest = parse_approval_manifest(manifest_bytes)
    _require_manifest_identity(metadata, manifest_bytes)
    if metadata.approval_state != "active" or metadata.revision is not None:
        raise _retry_conflict("Matching operation evidence is not in active approval state")
    if model.status != "approved" or not (1 <= task_number <= len(model.tasks)):
        raise _retry_conflict("Current status or task ordinal does not match retry evidence")
    task = model.tasks[task_number - 1]
    if task_digest(task.text) != expected_task_digest:
        raise _retry_conflict("Current task text does not match retry evidence")
    approval_differences = compare_approval_manifests(
        manifest,
        project_approval_manifest(
            model, approval_model_version=manifest.approval_model_version
        ),
    )
    if approval_differences:
        raise _retry_conflict("Approval-relevant content changed after the operation")
    if metadata.attestation is None:
        raise _retry_conflict("Matching operation evidence lacks an attestation")

    if not task.completed:
        if current_snapshot.snapshot_digest != expected_snapshot:
            raise _retry_conflict("Uncommitted retry no longer matches its source snapshot")
        after_model = replace(
            model,
            tasks=tuple(
                replace(item, completed=True) if item.ordinal == task_number else item
                for item in model.tasks
            ),
        )
        drift = compare_attested_state(metadata.attestation, after_model, metadata)
        if drift:
            raise _retry_conflict(
                "Staged attestation does not match the intended task completion",
                differences=drift,
            )
        atomic_replace_bytes(
            paths.tasks,
            replace_task_completion(
                paths.tasks.read_bytes(), task.source_line, expected_task_digest
            ),
        )
        after = build_snapshot(paths.proposal.read_bytes(), paths.tasks.read_bytes())
        return TransitionResult(current_snapshot, after, operation_id, True)

    drift = compare_attested_state(metadata.attestation, model, metadata)
    if drift:
        raise _retry_conflict(
            "Committed retry does not match its stored attestation", differences=drift
        )
    before_tasks = replace_task_uncompletion(
        paths.tasks.read_bytes(), task.source_line, expected_task_digest
    )
    reconstructed = build_snapshot(paths.proposal.read_bytes(), before_tasks)
    if reconstructed.snapshot_digest != expected_snapshot:
        raise _retry_conflict("Committed retry cannot reconstruct its exact source snapshot")
    return TransitionResult(
        reconstructed,
        current_snapshot,
        operation_id,
        False,
        result="ALREADY_APPLIED",
    )


def replace_task_completion(data: bytes, source_line: int, expected_digest: str) -> bytes:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise TransitionError(
            "ERROR_ARTIFACT_ENCODING", "fix_artifact_format", "tasks.md is not UTF-8"
        ) from error
    lines = text.splitlines(keepends=True)
    if source_line < 1 or source_line > len(lines):
        raise TransitionError(
            "ERROR_TASK_IDENTITY_MISMATCH", "refresh_status", "Task source line is unavailable"
        )
    line = lines[source_line - 1]
    ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
    content = line[: len(line) - len(ending) if ending else len(line)]
    if not content.startswith("- [ ] ") or task_digest(content[6:]) != expected_digest:
        raise TransitionError(
            "ERROR_TASK_IDENTITY_MISMATCH",
            "refresh_status",
            "Task source line no longer matches the expected incomplete task",
        )
    lines[source_line - 1] = f"- [x] {content[6:]}{ending}"
    return "".join(lines).encode("utf-8")


def replace_task_uncompletion(data: bytes, source_line: int, expected_digest: str) -> bytes:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise _retry_conflict("tasks.md is not valid UTF-8") from error
    lines = text.splitlines(keepends=True)
    if source_line < 1 or source_line > len(lines):
        raise _retry_conflict("Completed task source line is unavailable")
    line = lines[source_line - 1]
    ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
    content = line[: len(line) - len(ending) if ending else len(line)]
    if not content.startswith("- [x] ") or task_digest(content[6:]) != expected_digest:
        raise _retry_conflict("Completed task line does not match retry evidence")
    lines[source_line - 1] = f"- [ ] {content[6:]}{ending}"
    return "".join(lines).encode("utf-8")


def _retry_conflict(
    message: str, *, differences: tuple[ApprovalDifference, ...] = ()
) -> TransitionError:
    data: dict[str, object] = {}
    if differences:
        data["differences"] = [item.to_dict() for item in differences]
    return TransitionError(
        "ERROR_TASK_RETRY_CONFLICT",
        "inspect_managed_state_drift",
        message,
        data=data,
    )


def replace_status(data: bytes, expected: str, target: str) -> bytes:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise TransitionError(
            "ERROR_ARTIFACT_ENCODING", "fix_artifact_format", "proposal.md is not UTF-8"
        ) from error
    lines = text.splitlines(keepends=True)
    heading_indices = [
        index for index, line in enumerate(lines) if line.rstrip("\r\n") == "## 狀態"
    ]
    if len(heading_indices) != 1:
        raise TransitionError(
            "ERROR_STATUS_FIELD_AMBIGUOUS",
            "fix_artifact_format",
            "proposal.md must contain exactly one ## 狀態 section",
        )
    start = heading_indices[0] + 1
    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    values = [index for index in range(start, end) if lines[index].strip()]
    if len(values) != 1 or lines[values[0]].strip() != expected:
        raise TransitionError(
            "ERROR_INVALID_SOURCE_STATE",
            "refresh_status",
            f"Expected a single {expected!r} status value",
        )
    index = values[0]
    line = lines[index]
    ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
    prefix_length = len(line) - len(line.lstrip(" \t"))
    prefix = line[:prefix_length]
    content = line[prefix_length : len(line) - len(ending) if ending else len(line)]
    trailing_length = len(content) - len(content.rstrip(" \t"))
    trailing = content[len(content) - trailing_length :] if trailing_length else ""
    lines[index] = f"{prefix}{target}{trailing}{ending}"
    return "".join(lines).encode("utf-8")


def _require_expected_snapshot(current: SnapshotManifest, expected: str) -> None:
    if current.snapshot_digest != expected:
        raise TransitionError(
            "ERROR_SNAPSHOT_MISMATCH",
            "refresh_status",
            "Expected snapshot does not match current proposal artifacts",
        )


def _prepare_machine_directory(proposal_directory: Path) -> Path:
    machine = proposal_directory / ".sdd"
    if machine.is_symlink() or (machine.exists() and not machine.is_dir()):
        raise TransitionError(
            "ERROR_MACHINE_METADATA_INVALID",
            "inspect_machine_metadata",
            f"Machine metadata path must be a regular directory: {machine}",
        )
    machine.mkdir(mode=0o700, exist_ok=True)
    return machine


def _require_machine_files(proposal_directory: Path) -> tuple[Path, Path, Path]:
    machine = proposal_directory / ".sdd"
    manifest = machine / "approval-manifest.json"
    metadata = machine / "metadata.json"
    if machine.is_symlink() or not machine.is_dir():
        raise TransitionError(
            "ERROR_APPROVAL_MANIFEST_REQUIRED",
            "establish_approval_manifest",
            "Approved proposal has no machine approval baseline",
        )
    for path in (manifest, metadata):
        if path.is_symlink() or not path.is_file():
            raise TransitionError(
                "ERROR_APPROVAL_MANIFEST_REQUIRED",
                "establish_approval_manifest",
                "Approved proposal has no valid machine approval baseline",
            )
    return machine, manifest, metadata


def _require_manifest_identity(metadata: ActiveMetadata, manifest_bytes: bytes) -> None:
    if metadata.approval_model_version != APPROVAL_MODEL_VERSION:
        raise TransitionError(
            "ERROR_UNSUPPORTED_APPROVAL_MODEL_VERSION",
            "use_supported_engine",
            f"Unsupported approval model version: {metadata.approval_model_version!r}",
        )
    if approval_manifest_sha256(manifest_bytes) != metadata.manifest_sha256:
        raise TransitionError(
            "ERROR_APPROVAL_MANIFEST_IDENTITY_MISMATCH",
            "inspect_machine_metadata",
            "Approval Manifest bytes do not match active metadata identity",
        )


def _revision_marker(
    phase: str, source_snapshot: str, differences: list[dict[str, object]]
) -> dict[str, object]:
    return {
        "revision_version": 1,
        "phase": phase,
        "source_snapshot": source_snapshot,
        "differences": differences,
    }


def _opened_revision_metadata(
    metadata: ActiveMetadata, model: CanonicalProposal
) -> ActiveMetadata:
    assert metadata.revision is not None
    revision = dict(metadata.revision)
    revision["phase"] = "open"
    opened = ActiveMetadata(
        approval_state="invalidated",
        approval_model_version=metadata.approval_model_version,
        manifest_sha256=metadata.manifest_sha256,
        operation_kind="begin-revision",
        operation_id=metadata.operation_id,
        revision=revision,
    )
    return replace(opened, attestation=create_attestation(model, opened))


def _matching_revision(
    metadata: ActiveMetadata, operation_id: str, source_snapshot: str, phase: str
) -> bool:
    revision = metadata.revision
    return bool(
        metadata.approval_state == "invalidated"
        and metadata.operation_kind == "begin-revision"
        and metadata.operation_id == operation_id
        and isinstance(revision, dict)
        and revision.get("revision_version") == 1
        and revision.get("phase") == phase
        and revision.get("source_snapshot") == source_snapshot
    )


def _resume_committed_revision(
    paths: ProposalPaths,
    model: CanonicalProposal,
    current_snapshot: SnapshotManifest,
    expected_snapshot: str,
    metadata: ActiveMetadata,
    operation_id: str,
    differences: tuple[ApprovalDifference, ...],
    metadata_path: Path,
) -> TransitionResult:
    source_bytes = replace_status(paths.proposal.read_bytes(), "draft", "approved")
    source_snapshot = build_snapshot(source_bytes, paths.tasks.read_bytes())
    if source_snapshot.snapshot_digest != expected_snapshot:
        _require_expected_snapshot(current_snapshot, expected_snapshot)
    if _matching_revision(metadata, operation_id, expected_snapshot, "pending"):
        atomic_replace_bytes(
            metadata_path,
            serialize_active_metadata(_opened_revision_metadata(metadata, model)),
        )
        return TransitionResult(source_snapshot, current_snapshot, operation_id, True, differences)
    if _matching_revision(metadata, operation_id, expected_snapshot, "open"):
        return TransitionResult(source_snapshot, current_snapshot, operation_id, False, differences)
    raise _metadata_mismatch("Draft status lacks a matching revision authorization")


def _metadata_mismatch(message: str) -> TransitionError:
    return TransitionError(
        "ERROR_METADATA_STATE_MISMATCH", "inspect_machine_metadata", message
    )


def _prepare_approval_targets(
    model: CanonicalProposal,
    manifest_path: Path,
    metadata_path: Path,
    new_manifest_bytes: bytes,
    new_metadata_bytes: bytes,
    *,
    establish_manifest: bool,
) -> None:
    for path, label in (
        (manifest_path, "Approval Manifest"),
        (metadata_path, "active metadata"),
    ):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise TransitionError(
                "ERROR_MACHINE_METADATA_INVALID",
                "inspect_machine_metadata",
                f"{label} path must be a regular file: {path}",
            )
    existing = manifest_path.exists() or metadata_path.exists()
    if not existing:
        return
    if not manifest_path.is_file() or not metadata_path.is_file():
        if manifest_path.exists() and manifest_path.read_bytes() != new_manifest_bytes:
            raise _metadata_mismatch("Staged Approval Manifest does not match this operation")
        if metadata_path.exists() and metadata_path.read_bytes() != new_metadata_bytes:
            raise _metadata_mismatch("Staged metadata does not match this operation")
        return
    if (
        manifest_path.read_bytes() == new_manifest_bytes
        and metadata_path.read_bytes() == new_metadata_bytes
    ):
        return
    if establish_manifest:
        raise _metadata_mismatch("Baseline establishment cannot replace existing metadata")
    old_manifest_bytes = manifest_path.read_bytes()
    old_metadata = parse_active_metadata(metadata_path.read_bytes())
    _require_manifest_identity(old_metadata, old_manifest_bytes)
    if (
        old_metadata.approval_state != "invalidated"
        or not isinstance(old_metadata.revision, dict)
        or old_metadata.revision.get("phase") != "open"
        or old_metadata.attestation is None
    ):
        raise _metadata_mismatch("Existing metadata is not an authorized open revision")
    drift = compare_attested_state(old_metadata.attestation, model, old_metadata)
    if drift:
        raise TransitionError(
            "OUT_OF_BAND_DRIFT",
            "inspect_managed_state_drift",
            "Draft managed fields differ from the authorized revision state",
            data={"differences": [item.to_dict() for item in drift]},
        )


def _operation_id(kind: str, expected_snapshot: str, manifest_sha: str) -> str:
    payload = json.dumps(
        {
            "kind": kind,
            "expected_snapshot": expected_snapshot,
            "manifest_sha256": manifest_sha,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _revision_operation_id(
    expected_snapshot: str,
    manifest_sha: str,
    differences: list[dict[str, object]],
) -> str:
    payload = json.dumps(
        {
            "kind": "begin-revision",
            "expected_snapshot": expected_snapshot,
            "manifest_sha256": manifest_sha,
            "differences": differences,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _complete_task_operation_id(
    expected_snapshot: str, task_number: int, expected_digest: str
) -> str:
    payload = json.dumps(
        {
            "kind": "complete-task",
            "expected_snapshot": expected_snapshot,
            "task_number": task_number,
            "task_digest": expected_digest,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()
