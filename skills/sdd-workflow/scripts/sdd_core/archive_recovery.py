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
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class RepairResult:
    preflight: RepairPreflight
    repaired: tuple[str, ...]
    operation_id: str
    index_rebuilt: bool
    index_sha256: str | None
    diagnostics: tuple[ArchiveDiagnostic, ...]


def preflight_archive_repair(archive_root: Path, directory_name: str) -> RepairPreflight:
    directory, identity = validate_repairable_target(archive_root, directory_name)
    archive_date, short_name, name_status = identity
    expected_terminal = name_status or "completed"
    proposal_bytes = (directory / "proposal.md").read_bytes()
    tasks_bytes = (directory / "tasks.md").read_bytes()
    current_status = _parse_status(short_name, proposal_bytes, tasks_bytes)
    missing: list[str] = []
    if current_status not in TERMINAL_STATUSES:
        missing.append("terminal_status")
    if not _has_machine_evidence(directory):
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
    )


def execute_archive_repair(
    archive_root: Path,
    directory_name: str,
    *,
    terminal_status: str,
    summary: str,
    expected_proposal_sha256: str,
    expected_tasks_sha256: str,
    now_utc: datetime | None = None,
) -> RepairResult:
    preflight = preflight_archive_repair(archive_root, directory_name)
    if (
        preflight.proposal_sha256 != expected_proposal_sha256
        or preflight.tasks_sha256 != expected_tasks_sha256
    ):
        raise TransitionError(
            "ERROR_RECOVERY_EVIDENCE_MISMATCH",
            "rerun_repair_preflight",
            "Archived artifact bytes differ from the confirmed evidence digests",
        )
    if terminal_status != preflight.expected_terminal_status:
        raise TransitionError(
            "ERROR_RECOVERY_STATUS_MISMATCH",
            "inspect_archive_state",
            "Provided terminal status disagrees with the archive directory name",
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
    archive_root: Path, directory_name: str
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
    if _directory_has_terminal_metadata(directory):
        raise TransitionError(
            "ERROR_RECOVERY_NOT_APPLICABLE",
            "inspect_archive_state",
            "Archive directory already carries managed terminal evidence",
        )
    return directory, identity


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
