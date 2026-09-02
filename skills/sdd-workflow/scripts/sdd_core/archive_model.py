"""Canonical archive records and read-only legacy compatibility adapter."""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .discovery import SHORT_NAME_PATTERN
from .parser_v1 import parse_with_schema
from .scanner import scan_tasks
from .summary_input import fold_summary_for_index


ARCHIVE_MODEL_VERSION = 1
RECOVERY_EVIDENCE_VERSION = 1
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DIRECTORY = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@dataclass(frozen=True, slots=True)
class ArchiveRecord:
    directory_name: str
    short_name: str
    archive_date: str
    terminal_status: str
    summary: str
    source: str
    research_conclusion: tuple[str, ...] | None = None
    archive_model_version: int = ARCHIVE_MODEL_VERSION

    def __post_init__(self) -> None:
        if self.archive_model_version != ARCHIVE_MODEL_VERSION:
            raise ValueError("unsupported archive model version")
        if not _DATE.fullmatch(self.archive_date):
            raise ValueError("archive_date must be YYYY-MM-DD")
        if not SHORT_NAME_PATTERN.fullmatch(self.short_name):
            raise ValueError("invalid archive short_name")
        if self.terminal_status not in {"completed", "abandoned"}:
            raise ValueError("invalid terminal status")
        if not self.summary or "\n" in self.summary or "\r" in self.summary:
            raise ValueError("archive summary must be a non-empty single line")
        if self.source not in {"managed", "legacy"}:
            raise ValueError("invalid archive source")
        if self.research_conclusion is not None and not all(
            isinstance(item, str) and item for item in self.research_conclusion
        ):
            raise ValueError("research conclusion must contain non-empty strings")

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_model_version": self.archive_model_version,
            "directory_name": self.directory_name,
            "short_name": self.short_name,
            "archive_date": self.archive_date,
            "terminal_status": self.terminal_status,
            "summary": self.summary,
            "source": self.source,
            "research_conclusion": (
                None
                if self.research_conclusion is None
                else list(self.research_conclusion)
            ),
        }

    @property
    def sort_key(self) -> tuple[str, str, str, str]:
        return (
            self.archive_date,
            self.short_name,
            self.terminal_status,
            self.directory_name,
        )


@dataclass(frozen=True, slots=True)
class ArchiveDiagnostic:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}

    @property
    def sort_key(self) -> tuple[str, str]:
        return (self.path, self.code)


@dataclass(frozen=True, slots=True)
class ArchiveScan:
    records: tuple[ArchiveRecord, ...]
    diagnostics: tuple[ArchiveDiagnostic, ...]


def load_legacy_archive_records(
    archive_root: Path,
    provided_summaries: dict[str, str] | None = None,
) -> ArchiveScan:
    """Adapt legacy directories without writing or inferring missing summaries.

    ``provided_summaries`` maps a directory name to an explicitly provided
    summary that is used only when that directory has no summary source at
    all; it never overrides an existing INDEX row or recovery evidence.
    """

    provided = {} if provided_summaries is None else dict(provided_summaries)
    index_path = archive_root / "INDEX.md"
    index_rows, index_diagnostics = parse_legacy_index(
        index_path.read_text(encoding="utf-8") if index_path.is_file() else "",
        path="sdd/archive/INDEX.md",
    )
    records: list[ArchiveRecord] = []
    diagnostics = list(index_diagnostics)
    rows_by_key: dict[tuple[str, str, str], list[str]] = {}
    for date, short_name, status, summary in index_rows:
        rows_by_key.setdefault((date, short_name, status), []).append(summary)

    if archive_root.is_symlink() or not archive_root.is_dir():
        return ArchiveScan(
            (),
            (ArchiveDiagnostic("UNKNOWN_STATE", "sdd/archive", "Archive directory is unavailable"),),
        )
    for directory in sorted(archive_root.iterdir(), key=lambda item: item.name):
        if directory.name == "INDEX.md" or not directory.is_dir():
            continue
        relative = f"sdd/archive/{directory.name}"
        if directory.is_symlink():
            diagnostics.append(
                ArchiveDiagnostic("UNKNOWN_STATE", relative, "Archive symlinks are unsupported")
            )
            continue
        identity = _directory_identity(directory.name)
        if identity is None:
            diagnostics.append(
                ArchiveDiagnostic("UNKNOWN_STATE", relative, "Archive directory name is unsupported")
            )
            continue
        date, short_name, name_status = identity
        proposal = directory / "proposal.md"
        tasks = directory / "tasks.md"
        if not proposal.is_file() or not tasks.is_file() or proposal.is_symlink() or tasks.is_symlink():
            diagnostics.append(
                ArchiveDiagnostic("UNKNOWN_STATE", relative, "Archive artifacts are missing or unsafe")
            )
            continue
        try:
            outcome = parse_with_schema(
                short_name=short_name,
                proposal_text=proposal.read_text(encoding="utf-8"),
                task_scan=scan_tasks(tasks.read_text(encoding="utf-8")),
            )
        except (OSError, UnicodeDecodeError) as error:
            diagnostics.append(ArchiveDiagnostic("UNKNOWN_STATE", relative, str(error)))
            continue
        if (
            outcome.model is None
            or not outcome.task_counts_reliable
            or any(item.severity.value == "error" for item in outcome.diagnostics)
        ):
            diagnostics.append(
                ArchiveDiagnostic(
                    "ARCHIVE_RECORD_MISMATCH",
                    relative,
                    "Archived proposal artifacts fail strict format validation",
                )
            )
            continue
        status = outcome.model.status if outcome.model is not None else None
        if status not in {"completed", "abandoned"}:
            diagnostics.append(
                ArchiveDiagnostic(
                    "ARCHIVE_RECORD_MISMATCH",
                    relative,
                    f"Archived proposal status is not terminal: {status!r}",
                )
            )
            continue
        if name_status is not None and name_status != status:
            diagnostics.append(
                ArchiveDiagnostic(
                    "ARCHIVE_RECORD_MISMATCH",
                    relative,
                    "Directory suffix and proposal terminal status disagree",
                )
            )
            continue
        try:
            recovery = load_recovery_evidence(directory)
        except ValueError as error:
            diagnostics.append(
                ArchiveDiagnostic("ARCHIVE_RECORD_MISMATCH", relative, str(error))
            )
            continue
        if recovery is not None:
            if (
                recovery["archive_date"] != date
                or recovery["short_name"] != short_name
                or recovery["terminal_status"] != status
            ):
                diagnostics.append(
                    ArchiveDiagnostic(
                        "ARCHIVE_RECORD_MISMATCH",
                        relative,
                        "Recovery evidence disagrees with the archived artifacts",
                    )
                )
                continue
            summary = fold_summary_for_index(recovery["summary"])
        else:
            summaries = rows_by_key.get((date, short_name, status), [])
            if len(summaries) == 1:
                summary = summaries[0]
            elif not summaries and directory.name in provided:
                summary = fold_summary_for_index(provided[directory.name])
            else:
                code = "UNKNOWN_STATE" if not summaries else "AMBIGUOUS_STATE"
                diagnostics.append(
                    ArchiveDiagnostic(
                        code,
                        relative,
                        "Legacy summary is missing" if not summaries else "Multiple legacy summaries match",
                    )
                )
                continue
        records.append(
            ArchiveRecord(
                directory_name=directory.name,
                short_name=short_name,
                archive_date=date,
                terminal_status=status,
                summary=summary,
                source="legacy",
                research_conclusion=_research_conclusion(outcome.model),
            )
        )
    return ArchiveScan(
        tuple(sorted(records, key=lambda item: item.sort_key)),
        tuple(sorted(diagnostics, key=lambda item: item.sort_key)),
    )


def load_archive_records(
    archive_root: Path,
    provided_summaries: dict[str, str] | None = None,
) -> ArchiveScan:
    """Load managed records and legacy compatibility records together."""

    legacy = load_legacy_archive_records(archive_root, provided_summaries)
    legacy_by_directory = {record.directory_name: record for record in legacy.records}
    diagnostics = [
        item
        for item in legacy.diagnostics
        if not _directory_has_terminal_metadata(archive_root / _diagnostic_directory(item.path))
    ]
    records = [
        record
        for record in legacy.records
        if not _directory_has_terminal_metadata(archive_root / record.directory_name)
    ]
    if not archive_root.is_dir() or archive_root.is_symlink():
        return legacy
    for directory in sorted(archive_root.iterdir(), key=lambda item: item.name):
        if not directory.is_dir() or directory.is_symlink():
            continue
        metadata_path = directory / ".sdd/metadata.json"
        if not _directory_has_terminal_metadata(directory):
            continue
        try:
            record = _load_managed_record(directory, metadata_path)
        except (ValueError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            diagnostics.append(
                ArchiveDiagnostic(
                    "ARCHIVE_RECORD_MISMATCH",
                    f"sdd/archive/{directory.name}",
                    str(error),
                )
            )
        else:
            records.append(record)
            legacy_by_directory.pop(directory.name, None)
    return ArchiveScan(
        tuple(sorted(records, key=lambda item: item.sort_key)),
        tuple(sorted(diagnostics, key=lambda item: item.sort_key)),
    )


def load_recovery_evidence(directory: Path) -> dict[str, Any] | None:
    """Load explicitly confirmed recovery evidence, or None when absent.

    Raises ValueError when a recovery block exists but is malformed, so
    callers fail closed instead of guessing at partially written evidence.
    """

    path = directory / ".sdd/metadata.json"
    if path.is_symlink() or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or "recovery" not in value:
        return None
    recovery = value["recovery"]
    if not isinstance(recovery, dict):
        raise ValueError("recovery evidence must be an object")
    expected_fields = {
        "recovery_version", "archive_date", "short_name", "terminal_status",
        "summary", "timestamp", "confirmed_evidence", "operation",
    }
    if (
        set(recovery) != expected_fields
        or recovery["recovery_version"] != RECOVERY_EVIDENCE_VERSION
    ):
        raise ValueError("recovery evidence fields or version are unsupported")
    if not isinstance(recovery["archive_date"], str) or not _DATE.fullmatch(
        recovery["archive_date"]
    ):
        raise ValueError("recovery archive_date must be YYYY-MM-DD")
    if not isinstance(recovery["short_name"], str) or not SHORT_NAME_PATTERN.fullmatch(
        recovery["short_name"]
    ):
        raise ValueError("recovery short_name is invalid")
    if recovery["terminal_status"] not in {"completed", "abandoned"}:
        raise ValueError("recovery terminal status is invalid")
    summary = recovery["summary"]
    if (
        not isinstance(summary, str)
        or not summary.strip()
        or "\n" in summary
        or "\r" in summary
    ):
        raise ValueError("recovery summary must be a non-empty single line")
    if not isinstance(recovery["timestamp"], str) or not _TIMESTAMP.fullmatch(
        recovery["timestamp"]
    ):
        raise ValueError("recovery timestamp must be UTC RFC 3339 seconds")
    evidence = recovery["confirmed_evidence"]
    if (
        not isinstance(evidence, dict)
        or set(evidence) != {"proposal_sha256", "tasks_sha256"}
        or not all(
            isinstance(evidence[field], str) and _SHA256_HEX.fullmatch(evidence[field])
            for field in ("proposal_sha256", "tasks_sha256")
        )
    ):
        raise ValueError("recovery confirmed evidence is invalid")
    operation = recovery["operation"]
    if (
        not isinstance(operation, dict)
        or set(operation) != {"kind", "operation_id"}
        or operation["kind"] != "repair-archive-record"
        or not isinstance(operation["operation_id"], str)
        or not _SHA256_HEX.fullmatch(operation["operation_id"])
    ):
        raise ValueError("recovery operation evidence is invalid")
    return recovery


def _directory_has_terminal_metadata(directory: Path) -> bool:
    path = directory / ".sdd/metadata.json"
    if path.is_symlink() or not path.is_file():
        return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return isinstance(value, dict) and "terminal" in value


def _diagnostic_directory(path: str) -> str:
    prefix = "sdd/archive/"
    if not path.startswith(prefix):
        return ""
    return path[len(prefix) :].split("/", 1)[0]


def _load_managed_record(directory: Path, metadata_path: Path) -> ArchiveRecord:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or not isinstance(metadata.get("terminal"), dict):
        raise ValueError("managed archive lacks terminal metadata")
    terminal = metadata["terminal"]
    expected_fields = {
        "terminal_metadata_version", "archive_date", "short_name", "source_status", "terminal_status", "timestamp",
        "summary", "destination_directory", "source_snapshot", "operation",
    }
    if set(terminal) != expected_fields or terminal["terminal_metadata_version"] != 1:
        raise ValueError("terminal metadata fields or version are unsupported")
    short_name = terminal["short_name"]
    archive_date = terminal["archive_date"]
    status = terminal["terminal_status"]
    source_status = terminal["source_status"]
    timestamp = terminal["timestamp"]
    summary = terminal["summary"]
    destination_directory = terminal["destination_directory"]
    if not isinstance(timestamp, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp
    ):
        raise ValueError("terminal timestamp must be UTC RFC 3339 seconds")
    if not isinstance(archive_date, str) or not _DATE.fullmatch(archive_date):
        raise ValueError("terminal archive_date must be YYYY-MM-DD")
    if not isinstance(short_name, str) or not SHORT_NAME_PATTERN.fullmatch(short_name):
        raise ValueError("terminal short_name is invalid")
    if status not in {"completed", "abandoned"}:
        raise ValueError("terminal status is invalid")
    if source_status not in {"draft", "approved"}:
        raise ValueError("terminal source_status is invalid")
    expected_directory = f"{archive_date}-{short_name}"
    if status == "abandoned":
        expected_directory += "-abandoned"
    if directory.name != expected_directory:
        raise ValueError("directory name disagrees with terminal metadata")
    if destination_directory != expected_directory:
        raise ValueError("recorded destination disagrees with terminal metadata")
    if not isinstance(summary, str):
        raise ValueError("terminal summary is invalid")
    snapshot = terminal["source_snapshot"]
    operation = terminal["operation"]
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "snapshot_version", "proposal_sha256", "tasks_sha256", "snapshot_digest"
    }:
        raise ValueError("terminal source snapshot is invalid")
    if snapshot["snapshot_version"] != 1 or not all(
        isinstance(snapshot.get(field), str) and re.fullmatch(r"[0-9a-f]{64}", snapshot[field])
        for field in ("proposal_sha256", "tasks_sha256", "snapshot_digest")
    ):
        raise ValueError("terminal source snapshot values are invalid")
    if not isinstance(operation, dict) or set(operation) != {"kind", "operation_id"}:
        raise ValueError("terminal operation evidence is invalid")
    expected_kind = "archive" if status == "completed" else "abandon"
    if operation["kind"] != expected_kind or not isinstance(operation["operation_id"], str):
        raise ValueError("terminal operation evidence disagrees with status")
    proposal = directory / "proposal.md"
    tasks = directory / "tasks.md"
    if not proposal.is_file() or not tasks.is_file() or proposal.is_symlink() or tasks.is_symlink():
        raise ValueError("managed archive artifacts are missing or unsafe")
    outcome = parse_with_schema(
        short_name=short_name,
        proposal_text=proposal.read_text(encoding="utf-8"),
        task_scan=scan_tasks(tasks.read_text(encoding="utf-8")),
    )
    if (
        outcome.model is None
        or outcome.model.status != status
        or not outcome.task_counts_reliable
        or any(item.severity.value == "error" for item in outcome.diagnostics)
    ):
        raise ValueError("archived proposal status disagrees with terminal metadata")
    return ArchiveRecord(
        directory_name=directory.name,
        short_name=short_name,
        archive_date=archive_date,
        terminal_status=status,
        summary=fold_summary_for_index(summary),
        source="managed",
        research_conclusion=_research_conclusion(outcome.model),
    )


def _research_conclusion(model: Any) -> tuple[str, ...] | None:
    if model is None or model.change_type != "研究":
        return None
    for extension in model.extensions:
        if extension.namespace != "sdd.research.conclusion":
            continue
        value = extension.value
        if not isinstance(value, dict) or set(value) != {"items"}:
            raise ValueError("research conclusion extension is invalid")
        items = value["items"]
        if not isinstance(items, list) or not all(
            isinstance(item, str) and item for item in items
        ):
            raise ValueError("research conclusion items are invalid")
        return tuple(items)
    raise ValueError("research proposal lacks canonical conclusion")


def parse_legacy_index(
    text: str, *, path: str = "INDEX.md"
) -> tuple[tuple[tuple[str, str, str, str], ...], tuple[ArchiveDiagnostic, ...]]:
    rows: list[tuple[str, str, str, str]] = []
    diagnostics: list[ArchiveDiagnostic] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("- "):
            continue
        fields = _split_escaped_fields(line[2:])
        if len(fields) != 4:
            diagnostics.append(
                ArchiveDiagnostic(
                    "AMBIGUOUS_STATE",
                    f"{path}:{line_number}",
                    "Legacy INDEX row does not contain four fields",
                )
            )
            continue
        date, short_name, status, summary = (field.strip() for field in fields)
        if (
            not _DATE.fullmatch(date)
            or not SHORT_NAME_PATTERN.fullmatch(short_name)
            or status not in {"completed", "abandoned"}
            or not summary
        ):
            diagnostics.append(
                ArchiveDiagnostic(
                    "AMBIGUOUS_STATE",
                    f"{path}:{line_number}",
                    "Legacy INDEX row fields are invalid",
                )
            )
            continue
        rows.append((date, short_name, status, summary))
    return tuple(rows), tuple(sorted(diagnostics, key=lambda item: item.sort_key))


def _directory_identity(name: str) -> tuple[str, str, str | None] | None:
    match = _DIRECTORY.fullmatch(name)
    if match is None:
        return None
    date, remainder = match.groups()
    status = None
    short_name = remainder
    if remainder.endswith("-abandoned"):
        short_name = remainder[: -len("-abandoned")]
        status = "abandoned"
    if not SHORT_NAME_PATTERN.fullmatch(short_name):
        return None
    return date, short_name, status


def _split_escaped_fields(value: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    escaped = False
    for character in value:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "|":
            fields.append("".join(current))
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    fields.append("".join(current))
    return fields
