"""Deterministic derived archive INDEX rendering and replacement."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import hashlib
from dataclasses import dataclass
from typing import Any

from .archive_model import ArchiveRecord
from .atomic_write import atomic_replace_bytes


@dataclass(frozen=True, slots=True)
class IndexDifference:
    path: str
    kind: str
    expected: Any = None
    current: Any = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"path": self.path, "kind": self.kind}
        if self.kind != "added":
            value["expected"] = self.expected
        if self.kind != "removed":
            value["current"] = self.current
        return value


def render_archive_index(records: Iterable[ArchiveRecord]) -> bytes:
    ordered = sorted(records, key=lambda item: item.sort_key)
    directory_names = [item.directory_name for item in ordered]
    if len(directory_names) != len(set(directory_names)):
        raise ValueError("canonical archive records contain duplicate directories")
    rows = ["# SDD Archive", ""]
    rows.extend(
        "- "
        + " | ".join(
            (
                record.archive_date,
                record.short_name,
                record.terminal_status,
                _escape_field(record.summary),
            )
        )
        for record in ordered
    )
    return ("\n".join(rows) + "\n").encode("utf-8")


def replace_archive_index(archive_root: Path, records: Iterable[ArchiveRecord]) -> bytes:
    if archive_root.is_symlink() or not archive_root.is_dir():
        raise OSError(f"archive root must be a regular directory: {archive_root}")
    rendered = render_archive_index(records)
    atomic_replace_bytes(archive_root / "INDEX.md", rendered)
    return rendered


def rebuild_archive_index(
    archive_root: Path, records: Iterable[ArchiveRecord]
) -> tuple[bytes, bool, str]:
    rendered = render_archive_index(records)
    target = archive_root / "INDEX.md"
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise OSError(f"archive INDEX must be a regular file: {target}")
    changed = not target.exists() or target.read_bytes() != rendered
    if changed:
        replace_archive_index(archive_root, records)
    return rendered, changed, hashlib.sha256(rendered).hexdigest()


def validate_archive_index(
    archive_root: Path, records: Iterable[ArchiveRecord]
) -> tuple[IndexDifference, ...]:
    expected = render_archive_index(records)
    target = archive_root / "INDEX.md"
    if target.is_symlink() or (target.exists() and not target.is_file()):
        return (IndexDifference("/INDEX.md", "changed", "regular file", "unsafe path"),)
    if not target.exists():
        return (IndexDifference("/INDEX.md", "removed", expected=expected.decode("utf-8")),)
    try:
        current = target.read_bytes().decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return (IndexDifference("/INDEX.md", "changed", "UTF-8", "invalid encoding"),)
    expected_lines = expected.decode("utf-8").splitlines()
    current_lines = current.splitlines()
    differences: list[IndexDifference] = []
    shared = min(len(expected_lines), len(current_lines))
    for index in range(shared):
        if expected_lines[index] != current_lines[index]:
            differences.append(
                IndexDifference(
                    f"/lines/{index}", "changed", expected_lines[index], current_lines[index]
                )
            )
    for index in range(shared, len(expected_lines)):
        differences.append(
            IndexDifference(f"/lines/{index}", "removed", expected=expected_lines[index])
        )
    for index in range(shared, len(current_lines)):
        differences.append(
            IndexDifference(f"/lines/{index}", "added", current=current_lines[index])
        )
    return tuple(differences)


def _escape_field(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|")
