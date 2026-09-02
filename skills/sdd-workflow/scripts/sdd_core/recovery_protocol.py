"""Recoverable multi-file replacement protocol for artifact reconstruction.

The protocol does not claim cross-file atomicity.  It saves private source and
candidate copies before touching authoritative files, records progress after
each single-file atomic replacement, and makes an interrupted operation
resumable or restorable while the target still matches recovery evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .atomic_write import atomic_replace_bytes
from .transitions import TransitionError


RECOVERY_PROTOCOL_VERSION = 1
RECOVERY_AREA_NAME = ".sdd-recovery"
_OPERATION_ID = re.compile(r"^[0-9a-f]{64}$")
_RELATIVE_ARTIFACT = re.compile(
    r"^(?:proposal\.md|tasks\.md|INDEX\.md|\.sdd/metadata\.json)$"
)


@dataclass(frozen=True, slots=True)
class RecoveryArtifact:
    relative_path: str
    original_bytes: bytes | None
    candidate_bytes: bytes

    def __post_init__(self) -> None:
        if not _RELATIVE_ARTIFACT.fullmatch(self.relative_path):
            raise ValueError(f"unsupported recovery artifact: {self.relative_path!r}")


@dataclass(frozen=True, slots=True)
class RecoveryProtocolResult:
    operation_id: str
    state: str
    outcome: str
    applied: tuple[str, ...]
    final_digests: tuple[tuple[str, str], ...]
    recovery_directory: Path

    def redacted_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "state": self.state,
            "outcome": self.outcome,
            "applied": list(self.applied),
            "final_digests": dict(self.final_digests),
            "recovery_directory": self.recovery_directory.as_posix(),
        }


def recovery_operation_id(
    *, kind: str, target_identity: str, artifacts: tuple[RecoveryArtifact, ...]
) -> str:
    payload = {
        "protocol_version": RECOVERY_PROTOCOL_VERSION,
        "kind": kind,
        "target_identity": target_identity,
        "artifacts": [
            {
                "path": item.relative_path,
                "original_sha256": (
                    None if item.original_bytes is None else _sha256(item.original_bytes)
                ),
                "candidate_sha256": _sha256(item.candidate_bytes),
            }
            for item in sorted(artifacts, key=lambda value: value.relative_path)
        ],
    }
    return _sha256(_json_bytes(payload))


def execute_staged_recovery(
    target: Path,
    *,
    kind: str,
    target_identity: str,
    artifacts: tuple[RecoveryArtifact, ...],
    validate_candidates: Callable[[Mapping[str, bytes]], None] | None = None,
    operation_id: str | None = None,
) -> RecoveryProtocolResult:
    """Stage source/candidate bytes, then finish or resume their installation."""

    ordered = _validate_artifacts(artifacts)
    if operation_id is None:
        operation_id = recovery_operation_id(
            kind=kind, target_identity=target_identity, artifacts=ordered
        )
    elif not _OPERATION_ID.fullmatch(operation_id):
        raise ValueError("recovery operation id must be lowercase SHA-256 hex")
    operation_directory = _operation_directory(target, operation_id)
    manifest = _stage_or_load(
        target,
        operation_directory,
        kind=kind,
        target_identity=target_identity,
        operation_id=operation_id,
        artifacts=ordered,
    )
    _require_manifest_matches(
        operation_directory, manifest, kind, target_identity, operation_id, ordered
    )
    if validate_candidates is not None:
        validate_candidates(
            {item.relative_path: item.candidate_bytes for item in ordered}
        )

    state = manifest["state"]
    if state == "restored":
        raise TransitionError(
            "ERROR_RECOVERY_OPERATION_RESTORED",
            "rerun_repair_preflight",
            "A restored recovery operation cannot be applied again",
        )
    if state == "committed":
        _require_current_candidates(target, ordered)
        return _result(operation_directory, manifest, "ALREADY_APPLIED")
    if state not in {"staged", "applying"}:
        raise _invalid_state("Recovery manifest state is unsupported")

    manifest["state"] = "applying"
    _write_manifest(operation_directory, manifest)
    applied = set(manifest["applied"])
    for item in ordered:
        path = _artifact_path(target, item.relative_path)
        current = _read_current(path)
        if current == item.candidate_bytes:
            applied.add(item.relative_path)
        elif current == item.original_bytes:
            _ensure_private_parent(target, path.parent)
            atomic_replace_bytes(path, item.candidate_bytes)
            applied.add(item.relative_path)
        else:
            raise TransitionError(
                "ERROR_RECOVERY_RETRY_CONFLICT",
                "rerun_repair_preflight",
                f"Artifact bytes no longer match source or candidate: {item.relative_path}",
            )
        manifest["applied"] = sorted(applied)
        _write_manifest(operation_directory, manifest)

    _require_current_candidates(target, ordered)
    manifest["state"] = "committed"
    manifest["final_digests"] = {
        item.relative_path: _sha256(item.candidate_bytes) for item in ordered
    }
    _write_manifest(operation_directory, manifest)
    return _result(operation_directory, manifest, "APPLIED")


def restore_staged_recovery(
    target: Path, operation_id: str
) -> RecoveryProtocolResult:
    """Restore exact source bytes unless later lifecycle mutation is observable."""

    if not _OPERATION_ID.fullmatch(operation_id):
        raise _invalid_state("Recovery operation id is invalid")
    operation_directory = _operation_directory(target, operation_id)
    manifest = _load_manifest(operation_directory)
    artifacts = _artifacts_from_private_copies(operation_directory, manifest)
    if manifest.get("operation_id") != operation_id:
        raise _invalid_state("Recovery operation identity does not match its directory")
    if manifest["state"] == "restored":
        _require_current_originals(target, artifacts)
        return _result(operation_directory, manifest, "ALREADY_RESTORED")
    if manifest["state"] not in {"staged", "applying", "committed", "restoring"}:
        raise _invalid_state("Recovery manifest cannot be restored from this state")

    # Validate every path first.  This prevents an automatic rollback after a
    # later approval, task completion, or terminal transition changed a file.
    for item in artifacts:
        current = _read_current(_artifact_path(target, item.relative_path))
        if current not in {item.original_bytes, item.candidate_bytes}:
            raise TransitionError(
                "ERROR_RECOVERY_RESTORE_UNSAFE",
                "inspect_lifecycle_state",
                "Later lifecycle mutation prevents automatic recovery restore",
            )

    manifest["state"] = "restoring"
    _write_manifest(operation_directory, manifest)
    restored = set(manifest["restored"])
    for item in reversed(artifacts):
        path = _artifact_path(target, item.relative_path)
        current = _read_current(path)
        if current == item.original_bytes:
            restored.add(item.relative_path)
        elif item.original_bytes is None:
            if current != item.candidate_bytes:
                raise _restore_conflict(item.relative_path)
            path.unlink()
            restored.add(item.relative_path)
        elif current == item.candidate_bytes:
            atomic_replace_bytes(path, item.original_bytes)
            restored.add(item.relative_path)
        else:
            raise _restore_conflict(item.relative_path)
        manifest["restored"] = sorted(restored)
        _write_manifest(operation_directory, manifest)

    for relative in sorted(
        manifest["created_directories"], key=lambda value: value.count("/"), reverse=True
    ):
        directory = _created_directory_path(target, relative)
        try:
            directory.rmdir()
        except OSError:
            pass
    _require_current_originals(target, artifacts)
    manifest["state"] = "restored"
    _write_manifest(operation_directory, manifest)
    return _result(operation_directory, manifest, "RESTORED")


def find_recovery_operation(
    target: Path,
    *,
    kind: str,
    target_identity: str,
    source_digests: Mapping[str, str | None],
    candidate_digests: Mapping[str, str],
) -> str | None:
    """Find one staged operation matching a previously confirmed digest set."""

    area = target / RECOVERY_AREA_NAME
    if area.is_symlink() or not area.is_dir():
        return None
    matches: list[str] = []
    for directory in sorted(area.iterdir(), key=lambda item: item.name):
        if directory.is_symlink() or not directory.is_dir():
            continue
        try:
            manifest = _load_manifest(directory)
        except TransitionError:
            continue
        if (
            manifest["kind"] != kind
            or manifest["target_identity"] != target_identity
        ):
            continue
        entries = manifest["artifacts"]
        assert isinstance(entries, list)
        original = {
            str(entry["path"]): entry["original_sha256"]
            for entry in entries
            if isinstance(entry, dict)
        }
        candidate = {
            str(entry["path"]): str(entry["candidate_sha256"])
            for entry in entries
            if isinstance(entry, dict)
        }
        if (
            all(original.get(key) == value for key, value in source_digests.items())
            and all(candidate.get(key) == value for key, value in candidate_digests.items())
            and set(candidate_digests).issubset(candidate)
        ):
            matches.append(str(manifest["operation_id"]))
    if len(matches) > 1:
        raise _invalid_state("Multiple recovery operations match the confirmed digests")
    return matches[0] if matches else None


def resume_staged_recovery(
    target: Path,
    operation_id: str,
    *,
    validate_candidates: Callable[[Mapping[str, bytes]], None] | None = None,
) -> RecoveryProtocolResult:
    """Resume a known operation using only its private, digest-verified copies."""

    if not _OPERATION_ID.fullmatch(operation_id):
        raise _invalid_state("Recovery operation id is invalid")
    operation_directory = _operation_directory(target, operation_id)
    manifest = _load_manifest(operation_directory)
    artifacts = _artifacts_from_private_copies(operation_directory, manifest)
    return execute_staged_recovery(
        target,
        kind=str(manifest["kind"]),
        target_identity=str(manifest["target_identity"]),
        artifacts=artifacts,
        validate_candidates=validate_candidates,
        operation_id=operation_id,
    )


def inspect_recovery_state(target: Path) -> tuple[dict[str, object], ...]:
    """Return redacted operation receipts for diagnostics."""

    area = target / RECOVERY_AREA_NAME
    if area.is_symlink() or not area.is_dir():
        return ()
    results: list[dict[str, object]] = []
    for directory in sorted(area.iterdir(), key=lambda item: item.name):
        if not directory.is_dir() or directory.is_symlink():
            continue
        try:
            manifest = _load_manifest(directory)
            results.append(
                {
                    "operation_id": manifest["operation_id"],
                    "kind": manifest["kind"],
                    "state": manifest["state"],
                    "applied": list(manifest["applied"]),
                }
            )
        except TransitionError:
            results.append(
                {
                    "operation_id": directory.name,
                    "kind": "unknown",
                    "state": "invalid",
                    "applied": [],
                }
            )
    return tuple(results)


def _validate_artifacts(
    artifacts: tuple[RecoveryArtifact, ...]
) -> tuple[RecoveryArtifact, ...]:
    if not artifacts:
        raise ValueError("recovery operation requires at least one artifact")
    ordered = tuple(sorted(artifacts, key=lambda item: item.relative_path))
    paths = [item.relative_path for item in ordered]
    if len(paths) != len(set(paths)):
        raise ValueError("recovery artifact paths must be unique")
    return ordered


def _stage_or_load(
    target: Path,
    operation_directory: Path,
    *,
    kind: str,
    target_identity: str,
    operation_id: str,
    artifacts: tuple[RecoveryArtifact, ...],
) -> dict[str, object]:
    _require_target(target)
    area = target / RECOVERY_AREA_NAME
    if area.is_symlink() or (area.exists() and not area.is_dir()):
        raise _invalid_state("Recovery area is unsafe")
    if operation_directory.exists() or operation_directory.is_symlink():
        return _load_manifest(operation_directory)
    for item in artifacts:
        current = _read_current(_artifact_path(target, item.relative_path))
        if current != item.original_bytes:
            raise TransitionError(
                "ERROR_RECOVERY_EVIDENCE_MISMATCH",
                "rerun_repair_preflight",
                f"Artifact bytes changed before recovery staging: {item.relative_path}",
            )
    area.mkdir(mode=0o700, exist_ok=True)
    os.chmod(area, 0o700)
    operation_directory.mkdir(mode=0o700)
    os.chmod(operation_directory, 0o700)
    copies = operation_directory / "copies"
    copies.mkdir(mode=0o700)
    os.chmod(copies, 0o700)
    entries: list[dict[str, object]] = []
    for index, item in enumerate(artifacts):
        original_slot = f"copies/{index:03d}.original"
        candidate_slot = f"copies/{index:03d}.candidate"
        if item.original_bytes is not None:
            atomic_replace_bytes(operation_directory / original_slot, item.original_bytes)
            os.chmod(operation_directory / original_slot, 0o600)
        atomic_replace_bytes(operation_directory / candidate_slot, item.candidate_bytes)
        os.chmod(operation_directory / candidate_slot, 0o600)
        entries.append(
            {
                "path": item.relative_path,
                "original_exists": item.original_bytes is not None,
                "original_sha256": (
                    None if item.original_bytes is None else _sha256(item.original_bytes)
                ),
                "candidate_sha256": _sha256(item.candidate_bytes),
                "original_slot": original_slot,
                "candidate_slot": candidate_slot,
            }
        )
    created_directories = sorted(
        {
            str(Path(item.relative_path).parent)
            for item in artifacts
            if item.original_bytes is None
            and Path(item.relative_path).parent != Path(".")
            and not (target / Path(item.relative_path).parent).exists()
        }
    )
    manifest: dict[str, object] = {
        "protocol_version": RECOVERY_PROTOCOL_VERSION,
        "kind": kind,
        "target_identity": target_identity,
        "operation_id": operation_id,
        "state": "staged",
        "artifacts": entries,
        "applied": [],
        "restored": [],
        "created_directories": created_directories,
        "final_digests": {},
    }
    _write_manifest(operation_directory, manifest)
    return manifest


def _load_manifest(operation_directory: Path) -> dict[str, object]:
    if operation_directory.is_symlink() or not operation_directory.is_dir():
        raise _invalid_state("Recovery operation directory is unavailable")
    manifest_path = operation_directory / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise _invalid_state("Recovery manifest is unavailable")
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _invalid_state(f"Recovery manifest is unreadable: {error}") from error
    required = {
        "protocol_version",
        "kind",
        "target_identity",
        "operation_id",
        "state",
        "artifacts",
        "applied",
        "restored",
        "created_directories",
        "final_digests",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise _invalid_state("Recovery manifest fields are unsupported")
    if value["protocol_version"] != RECOVERY_PROTOCOL_VERSION:
        raise _invalid_state("Recovery protocol version is unsupported")
    if (
        not isinstance(value["kind"], str)
        or not value["kind"]
        or not isinstance(value["target_identity"], str)
        or not value["target_identity"]
        or not isinstance(value["operation_id"], str)
        or not _OPERATION_ID.fullmatch(value["operation_id"])
        or value["state"]
        not in {"staged", "applying", "committed", "restoring", "restored"}
    ):
        raise _invalid_state("Recovery manifest identity or state is invalid")
    entries = value["artifacts"]
    if not isinstance(entries, list) or not entries:
        raise _invalid_state("Recovery artifact manifest is invalid")
    expected_entry_fields = {
        "path",
        "original_exists",
        "original_sha256",
        "candidate_sha256",
        "original_slot",
        "candidate_slot",
    }
    artifact_paths: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != expected_entry_fields:
            raise _invalid_state("Recovery artifact entry fields are invalid")
        path = entry["path"]
        original_digest = entry["original_sha256"]
        candidate_digest = entry["candidate_sha256"]
        if (
            not isinstance(path, str)
            or not _RELATIVE_ARTIFACT.fullmatch(path)
            or type(entry["original_exists"]) is not bool
            or (
                entry["original_exists"]
                and (
                    not isinstance(original_digest, str)
                    or not _OPERATION_ID.fullmatch(original_digest)
                )
            )
            or (not entry["original_exists"] and original_digest is not None)
            or not isinstance(candidate_digest, str)
            or not _OPERATION_ID.fullmatch(candidate_digest)
            or entry["original_slot"] != f"copies/{index:03d}.original"
            or entry["candidate_slot"] != f"copies/{index:03d}.candidate"
        ):
            raise _invalid_state("Recovery artifact entry values are invalid")
        artifact_paths.append(path)
    if len(artifact_paths) != len(set(artifact_paths)):
        raise _invalid_state("Recovery artifact paths are duplicated")
    for field in ("applied", "restored", "created_directories"):
        if not isinstance(value[field], list) or not all(
            isinstance(item, str) for item in value[field]
        ):
            raise _invalid_state(f"Recovery manifest {field} is invalid")
    if (
        not set(value["applied"]).issubset(artifact_paths)
        or not set(value["restored"]).issubset(artifact_paths)
        or not set(value["created_directories"]).issubset({".sdd"})
        or not isinstance(value["final_digests"], dict)
        or not set(value["final_digests"]).issubset(artifact_paths)
    ):
        raise _invalid_state("Recovery manifest progress evidence is invalid")
    if operation_directory.stat().st_mode & 0o077 or manifest_path.stat().st_mode & 0o077:
        raise _invalid_state("Recovery operation permissions are not private")
    return value


def _require_manifest_matches(
    operation_directory: Path,
    manifest: dict[str, object],
    kind: str,
    target_identity: str,
    operation_id: str,
    artifacts: tuple[RecoveryArtifact, ...],
) -> None:
    if (
        manifest["kind"] != kind
        or manifest["target_identity"] != target_identity
        or manifest["operation_id"] != operation_id
    ):
        raise _invalid_state("Recovery manifest identity conflicts with the request")
    entries = manifest["artifacts"]
    assert isinstance(entries, list)
    expected = [
        (
            item.relative_path,
            None if item.original_bytes is None else _sha256(item.original_bytes),
            _sha256(item.candidate_bytes),
        )
        for item in artifacts
    ]
    actual = [
        (entry.get("path"), entry.get("original_sha256"), entry.get("candidate_sha256"))
        for entry in entries
        if isinstance(entry, dict)
    ]
    if actual != expected:
        raise _invalid_state("Recovery manifest evidence conflicts with the request")
    _verify_private_copies(operation_directory, manifest)


def _verify_private_copies(
    operation_directory: Path, manifest: dict[str, object]
) -> None:
    copies = operation_directory / "copies"
    if copies.is_symlink() or not copies.is_dir() or copies.stat().st_mode & 0o077:
        raise _invalid_state("Recovery copies directory is unsafe")
    for entry in manifest["artifacts"]:
        if not isinstance(entry, dict):
            raise _invalid_state("Recovery artifact entry is invalid")
        candidate = operation_directory / str(entry["candidate_slot"])
        if _read_private(candidate, str(entry["candidate_sha256"])) is None:
            raise _invalid_state("Recovery candidate copy is invalid")
        if entry["original_exists"]:
            original = operation_directory / str(entry["original_slot"])
            if _read_private(original, str(entry["original_sha256"])) is None:
                raise _invalid_state("Recovery original copy is invalid")


def _artifacts_from_private_copies(
    operation_directory: Path, manifest: dict[str, object]
) -> tuple[RecoveryArtifact, ...]:
    _verify_private_copies(operation_directory, manifest)
    artifacts: list[RecoveryArtifact] = []
    for entry in manifest["artifacts"]:
        if not isinstance(entry, dict) or not _RELATIVE_ARTIFACT.fullmatch(
            str(entry.get("path", ""))
        ):
            raise _invalid_state("Recovery artifact entry is invalid")
        original = None
        if entry["original_exists"]:
            original = (operation_directory / str(entry["original_slot"])).read_bytes()
        candidate = (operation_directory / str(entry["candidate_slot"])).read_bytes()
        artifacts.append(RecoveryArtifact(str(entry["path"]), original, candidate))
    return tuple(artifacts)


def _write_manifest(operation_directory: Path, manifest: dict[str, object]) -> None:
    path = operation_directory / "manifest.json"
    atomic_replace_bytes(path, _json_bytes(manifest))
    os.chmod(path, 0o600)


def _require_target(target: Path) -> None:
    if target.is_symlink() or not target.is_dir():
        raise _invalid_state("Recovery target is not a safe directory")


def _operation_directory(target: Path, operation_id: str) -> Path:
    area = target / RECOVERY_AREA_NAME
    if area.is_symlink() or (area.exists() and not area.is_dir()):
        raise _invalid_state("Recovery area is unsafe")
    return area / operation_id


def _artifact_path(target: Path, relative_path: str) -> Path:
    if not _RELATIVE_ARTIFACT.fullmatch(relative_path):
        raise _invalid_state("Recovery artifact path is unsupported")
    path = target.joinpath(*relative_path.split("/"))
    if path == target or target not in path.parents:
        raise _invalid_state("Recovery artifact path escapes its target")
    if path.parent != target and (
        path.parent.is_symlink()
        or (path.parent.exists() and not path.parent.is_dir())
    ):
        raise _invalid_state("Recovery artifact parent is unsafe")
    return path


def _created_directory_path(target: Path, relative_path: str) -> Path:
    if relative_path != ".sdd":
        raise _invalid_state("Recovery-created directory path is unsupported")
    return target / ".sdd"


def _ensure_private_parent(target: Path, parent: Path) -> None:
    if parent == target:
        return
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise _invalid_state("Recovery artifact parent is unsafe")
    if not parent.exists():
        parent.mkdir(mode=0o700)
        os.chmod(parent, 0o700)


def _read_current(path: Path) -> bytes | None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise _invalid_state(f"Recovery artifact is unsafe: {path.name}")
    return path.read_bytes() if path.is_file() else None


def _read_private(path: Path, expected_sha256: str) -> bytes | None:
    if path.is_symlink() or not path.is_file():
        return None
    data = path.read_bytes()
    if _sha256(data) != expected_sha256:
        return None
    if path.stat().st_mode & 0o077:
        return None
    return data


def _require_current_candidates(
    target: Path, artifacts: tuple[RecoveryArtifact, ...]
) -> None:
    for item in artifacts:
        if _read_current(_artifact_path(target, item.relative_path)) != item.candidate_bytes:
            raise TransitionError(
                "ERROR_RECOVERY_RETRY_CONFLICT",
                "rerun_repair_preflight",
                "Committed recovery evidence does not match authoritative bytes",
            )


def _require_current_originals(
    target: Path, artifacts: tuple[RecoveryArtifact, ...]
) -> None:
    for item in artifacts:
        if _read_current(_artifact_path(target, item.relative_path)) != item.original_bytes:
            raise _restore_conflict(item.relative_path)


def _result(
    operation_directory: Path, manifest: dict[str, object], outcome: str
) -> RecoveryProtocolResult:
    final = manifest["final_digests"]
    assert isinstance(final, dict)
    return RecoveryProtocolResult(
        operation_id=str(manifest["operation_id"]),
        state=str(manifest["state"]),
        outcome=outcome,
        applied=tuple(str(item) for item in manifest["applied"]),
        final_digests=tuple(sorted((str(key), str(value)) for key, value in final.items())),
        recovery_directory=operation_directory,
    )


def _restore_conflict(path: str) -> TransitionError:
    return TransitionError(
        "ERROR_RECOVERY_RESTORE_UNSAFE",
        "inspect_lifecycle_state",
        f"Artifact cannot be restored from recovery evidence: {path}",
    )


def _invalid_state(message: str) -> TransitionError:
    return TransitionError(
        "ERROR_RECOVERY_STAGED_STATE_INVALID",
        "inspect_recovery_state",
        message,
    )


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
