"""Evidence-bound, read-only workflow diagnostics."""

from __future__ import annotations

import os
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
from .discovery import list_active_proposal_paths
from .managed_state import ManagedStateError, compare_attested_state
from .parser_v1 import parse_with_schema
from .scanner import scan_tasks
from .version import ENGINE_VERSION, engine_generation


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
                "inspect_archive_state",
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
