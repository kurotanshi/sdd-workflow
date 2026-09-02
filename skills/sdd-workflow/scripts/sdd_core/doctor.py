"""Evidence-bound, read-only workflow diagnostics."""

from __future__ import annotations

import os
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .active_metadata import ActiveMetadataError, parse_active_metadata
from .approval import (
    ApprovalManifestError,
    approval_manifest_sha256,
    compare_approval_manifests,
    parse_approval_manifest,
    project_approval_manifest,
)
from .archive_index import validate_archive_index
from .archive_model import load_archive_records
from .archive_recovery import recovery_action_for_archive_diagnostic
from .discovery import list_active_proposal_paths
from .managed_state import ManagedStateError, compare_attested_state
from .parser_v1 import parse_with_schema
from .parser_v1 import SUPPORTED_SCHEMA_VERSIONS, select_schema_from_document
from .runtime_discovery import RuntimeDiscoveryError, load_identity
from .runtime_identity import PACKAGE_ROOT, SKILL_FILE, runtime_handshake
from .scanner import scan_tasks
from .version import ENGINE_VERSION, engine_generation
from .recovery_protocol import RECOVERY_AREA_NAME, inspect_recovery_state


@dataclass(frozen=True, slots=True)
class DoctorFinding:
    code: str
    action: str
    path: str
    message: str
    differences: tuple[dict[str, Any], ...] = ()

    @property
    def sort_key(self) -> tuple[str, str]:
        return (self.path, self.code)

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "action": self.action,
            "path": self.path,
            "message": self.message,
        }
        if self.differences:
            value["differences"] = list(self.differences)
        return value


def diagnose_project(project_root: Path) -> tuple[DoctorFinding, ...]:
    findings: list[DoctorFinding] = []
    archive_root = project_root / "sdd/archive"
    archive_scan = load_archive_records(archive_root)
    for diagnostic in archive_scan.diagnostics:
        findings.append(
            DoctorFinding(
                diagnostic.code,
                recovery_action_for_archive_diagnostic(archive_root, diagnostic),
                diagnostic.path,
                diagnostic.message,
            )
        )
    if not archive_scan.diagnostics:
        for difference in validate_archive_index(archive_root, archive_scan.records):
            findings.append(
                DoctorFinding(
                    "ERROR_INDEX_STALE",
                    "rebuild_index",
                    "sdd/archive/INDEX.md",
                    "Derived INDEX differs from canonical archive records",
                    (difference.to_dict(),),
                )
            )

    active = list_active_proposal_paths(project_root)
    archived_names = {record.short_name for record in archive_scan.records}
    for paths in active:
        relative = f"sdd/{paths.directory.name}"
        findings.extend(_recovery_state_findings(paths.directory, relative))
        if paths.directory.name in archived_names:
            findings.append(
                DoctorFinding(
                    "ACTIVE_ARCHIVE_COLLISION",
                    "inspect_archive_state",
                    relative,
                    "The same short name exists in active and archive locations",
                )
            )

        proposal_bytes = paths.proposal.read_bytes()
        tasks_bytes = paths.tasks.read_bytes()
        outcome = parse_with_schema(
            short_name=paths.directory.name,
            proposal_text=proposal_bytes.decode("utf-8", errors="strict"),
            task_scan=scan_tasks(tasks_bytes.decode("utf-8", errors="strict")),
        )
        if outcome.model is None:
            continue
        model = outcome.model
        if model.status in {"completed", "abandoned"}:
            findings.append(
                DoctorFinding(
                    "STATUS_LOCATION_MISMATCH",
                    "inspect_archive_state",
                    f"{relative}/proposal.md",
                    f"Terminal status {model.status!r} remains in active location",
                )
            )
        machine = paths.directory / ".sdd"
        manifest_path = machine / "approval-manifest.json"
        metadata_path = machine / "metadata.json"
        present = (manifest_path.is_file(), metadata_path.is_file())
        if present == (False, False):
            if model.status == "approved":
                findings.append(
                    DoctorFinding(
                        "ERROR_APPROVAL_MANIFEST_REQUIRED",
                        "establish_approval_manifest",
                        relative,
                        "Approved proposal has no machine approval baseline",
                    )
                )
            continue
        if present[0] != present[1] or manifest_path.is_symlink() or metadata_path.is_symlink():
            findings.append(
                DoctorFinding(
                    "PARTIAL_TRANSITION_DETECTED",
                    "inspect_machine_metadata",
                    relative,
                    "Only part of the machine approval artifact set is present or safe",
                )
            )
            continue
        try:
            manifest_bytes = manifest_path.read_bytes()
            manifest = parse_approval_manifest(manifest_bytes)
            metadata = parse_active_metadata(metadata_path.read_bytes())
            writer_generation = engine_generation(metadata.writer_version)
            current_generation = engine_generation(ENGINE_VERSION)
            if writer_generation is None:
                findings.append(
                    DoctorFinding(
                        "ENGINE_VERSION_UNKNOWN",
                        "inspect_engine_version",
                        relative,
                        f"Metadata writer version is not strict SemVer: {metadata.writer_version!r}",
                    )
                )
            elif current_generation is not None and writer_generation > current_generation:
                findings.append(
                    DoctorFinding(
                        "ENGINE_VERSION_SKEW",
                        "use_compatible_engine",
                        relative,
                        (
                            f"Metadata writer generation {metadata.writer_version} is newer "
                            f"than current engine {ENGINE_VERSION}"
                        ),
                    )
                )
            if metadata.terminal is not None:
                findings.append(
                    DoctorFinding(
                        "PARTIAL_TRANSITION_DETECTED",
                        "inspect_machine_metadata",
                        relative,
                        "Terminal metadata is staged while the proposal remains active",
                    )
                )
            if approval_manifest_sha256(manifest_bytes) != metadata.manifest_sha256:
                findings.append(
                    DoctorFinding(
                        "ERROR_APPROVAL_MANIFEST_IDENTITY_MISMATCH",
                        "inspect_machine_metadata",
                        relative,
                        "Approval Manifest identity differs from metadata",
                    )
                )
                continue
            current_manifest = project_approval_manifest(
                model, approval_model_version=manifest.approval_model_version
            )
            semantic = compare_approval_manifests(manifest, current_manifest)
            if metadata.approval_state == "active" and semantic:
                findings.append(
                    DoctorFinding(
                        "ERROR_APPROVED_PLAN_CHANGED",
                        "begin_revision",
                        relative,
                        "Approval-relevant content differs from the active Manifest",
                        tuple(item.to_dict() for item in semantic),
                    )
                )
            if metadata.attestation is not None:
                drift = compare_attested_state(metadata.attestation, model, metadata)
                if drift:
                    findings.append(
                        DoctorFinding(
                            "OUT_OF_BAND_DRIFT",
                            "inspect_managed_state_drift",
                            relative,
                            "Managed fields differ from attestation; editor and cause are unknown",
                            tuple(item.to_dict() for item in drift),
                        )
                    )
        except (ApprovalManifestError, ActiveMetadataError, ManagedStateError, OSError) as error:
            findings.append(
                DoctorFinding(
                    getattr(error, "code", "UNKNOWN_STATE"),
                    getattr(error, "action", "inspect_machine_metadata"),
                    relative,
                    str(error),
                )
            )

    if archive_root.is_dir() and not archive_root.is_symlink():
        for directory in sorted(archive_root.iterdir(), key=lambda item: item.name):
            if directory.is_dir() and not directory.is_symlink():
                findings.extend(
                    _recovery_state_findings(
                        directory, f"sdd/archive/{directory.name}"
                    )
                )

    sdd_root = project_root / "sdd"
    for directory, directory_names, file_names in os.walk(sdd_root, followlinks=False):
        directory_names[:] = sorted(directory_names)
        for name in sorted(file_names):
            if name.startswith(".") and name.endswith(".tmp"):
                path = Path(directory) / name
                findings.append(
                    DoctorFinding(
                        "TEMPORARY_FILE_PRESENT",
                        "inspect_machine_metadata",
                        path.relative_to(project_root).as_posix(),
                        "A transaction-shaped temporary file remains; its cause is unknown",
                    )
                )
    return tuple(sorted(findings, key=lambda item: item.sort_key))


def _recovery_state_findings(
    target: Path, relative: str
) -> tuple[DoctorFinding, ...]:
    area = target / RECOVERY_AREA_NAME
    if (
        area.is_symlink()
        or (area.exists() and not area.is_dir())
        or (area.is_dir() and area.stat().st_mode & 0o077)
    ):
        return (
            DoctorFinding(
                "ERROR_RECOVERY_STAGED_STATE_INVALID",
                "inspect_recovery_state",
                f"{relative}/{RECOVERY_AREA_NAME}",
                "Recovery area is not a safe private directory",
            ),
        )
    findings: list[DoctorFinding] = []
    for operation in inspect_recovery_state(target):
        state = str(operation["state"])
        if state in {"staged", "applying", "restoring"}:
            findings.append(
                DoctorFinding(
                    "RECOVERY_STAGED_STATE",
                    "resume_or_restore_recovery",
                    f"{relative}/{RECOVERY_AREA_NAME}/{operation['operation_id']}",
                    f"Recovery operation is incomplete in state: {state}",
                )
            )
        elif state == "invalid":
            findings.append(
                DoctorFinding(
                    "ERROR_RECOVERY_STAGED_STATE_INVALID",
                    "inspect_recovery_state",
                    f"{relative}/{RECOVERY_AREA_NAME}/{operation['operation_id']}",
                    "Recovery operation evidence is invalid",
                )
            )
    return tuple(findings)


def diagnose_runtime_package() -> tuple[DoctorFinding, ...]:
    try:
        identity = load_identity(PACKAGE_ROOT)
        handshake = runtime_handshake()
    except (OSError, RuntimeError, RuntimeDiscoveryError) as error:
        return (
            DoctorFinding(
                getattr(error, "code", "RUNTIME_IDENTITY_UNKNOWN"),
                getattr(error, "action", "reinstall_runtime"),
                "runtime-package",
                str(error),
            ),
        )
    if identity["skill_sha256"] != handshake["skill_sha256"]:
        return (
            DoctorFinding(
                "RUNTIME_SKILL_VERSION_SKEW",
                "reinstall_complete_distribution",
                "runtime-package",
                "Installed Skill bytes differ from the runtime identity manifest",
            ),
        )
    return ()


def collect_environment_evidence(
    project_root: Path,
    findings: tuple[DoctorFinding, ...],
) -> dict[str, Any]:
    try:
        handshake = runtime_handshake()
        skill_sha256: str | None = hashlib.sha256(SKILL_FILE.read_bytes()).hexdigest()
        install_path: str | None = str(PACKAGE_ROOT)
    except OSError:
        handshake = {}
        skill_sha256 = None
        install_path = None

    observed_schemas: set[int] = set()
    schema_observation = "known"
    try:
        for paths in list_active_proposal_paths(project_root):
            selection = select_schema_from_document(
                paths.proposal.read_text(encoding="utf-8"),
                path=f"sdd/{paths.directory.name}/proposal.md",
            )
            if selection.version is None:
                schema_observation = "unknown"
            else:
                observed_schemas.add(selection.version)
    except (OSError, UnicodeDecodeError):
        schema_observation = "unknown"

    skew_codes = sorted(
        finding.code
        for finding in findings
        if finding.code in {"ENGINE_VERSION_SKEW", "RUNTIME_SKILL_VERSION_SKEW"}
    )
    return {
        "agent_environment": "unknown",
        "runtime": {
            "distribution_id": handshake.get("distribution_id", "unknown"),
            "engine_version": handshake.get("engine_version", "unknown"),
            "handshake_version": handshake.get("handshake_version", "unknown"),
            "capabilities": handshake.get("capabilities", "unknown"),
        },
        "skill": {
            "version": "unknown",
            "sha256": skill_sha256 if skill_sha256 is not None else "unknown",
        },
        "schema": {
            "runtime_supported": list(SUPPORTED_SCHEMA_VERSIONS),
            "repository_observation": schema_observation,
            "repository_observed_versions": sorted(observed_schemas),
        },
        "install_path": install_path if install_path is not None else "unknown",
        "package_source": "unknown",
        "discovery_source": "unknown",
        "version_skew": {
            "detected": bool(skew_codes),
            "codes": skew_codes,
        },
        "repository": {
            "health": "healthy" if not findings else "findings-present",
            "finding_count": len(findings),
        },
    }
