"""Versioned active-proposal machine metadata."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .version import ENGINE_VERSION


METADATA_VERSION = 1
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BASE_FIELDS = frozenset({"metadata_version", "writer", "approval", "revision", "last_operation"})


class ActiveMetadataError(ValueError):
    def __init__(self, code: str, action: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.action = action
        self.message = message


@dataclass(frozen=True, slots=True)
class ActiveMetadata:
    approval_state: str
    approval_model_version: int
    manifest_sha256: str
    operation_kind: str
    operation_id: str
    revision: dict[str, Any] | None = None
    writer_version: str = ENGINE_VERSION
    metadata_version: int = METADATA_VERSION
    attestation: dict[str, Any] | None = None
    terminal: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.metadata_version != METADATA_VERSION:
            raise ActiveMetadataError(
                "ERROR_UNSUPPORTED_METADATA_VERSION",
                "use_supported_engine",
                f"Unsupported metadata version: {self.metadata_version!r}",
            )
        if self.approval_state not in {"active", "invalidated"}:
            raise _invalid(f"Unsupported approval state: {self.approval_state!r}")
        if type(self.approval_model_version) is not int:
            raise _invalid("approval_model_version must be an integer")
        if not _SHA256.fullmatch(self.manifest_sha256):
            raise _invalid("manifest_sha256 must be lowercase SHA-256 hex")
        if not self.operation_kind or not self.operation_id:
            raise _invalid("last_operation kind and operation_id must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        value = {
            "metadata_version": self.metadata_version,
            "writer": {"engine": "sdd-workflow", "version": self.writer_version},
            "approval": {
                "state": self.approval_state,
                "approval_model_version": self.approval_model_version,
                "manifest_sha256": self.manifest_sha256,
            },
            "revision": self.revision,
            "last_operation": {
                "kind": self.operation_kind,
                "operation_id": self.operation_id,
            },
        }
        if self.attestation is not None:
            value["attestation"] = self.attestation
        if self.terminal is not None:
            value["terminal"] = self.terminal
        return value


def serialize_active_metadata(metadata: ActiveMetadata) -> bytes:
    return (
        json.dumps(metadata.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def parse_active_metadata(data: bytes | str) -> ActiveMetadata:
    try:
        text = data.decode("utf-8", errors="strict") if isinstance(data, bytes) else data
        value = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _invalid(f"Active metadata is not valid UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise _invalid("Active metadata root must be an object")
    optional = set(value) - _BASE_FIELDS
    if not set(value).issuperset(_BASE_FIELDS) or not optional.issubset({"attestation", "terminal"}):
        raise _invalid("Active metadata fields are missing or unsupported")
    version = value["metadata_version"]
    if type(version) is not int or version != METADATA_VERSION:
        raise ActiveMetadataError(
            "ERROR_UNSUPPORTED_METADATA_VERSION",
            "use_supported_engine",
            f"Unsupported metadata version: {version!r}",
        )
    writer = value["writer"]
    approval = value["approval"]
    operation = value["last_operation"]
    if not isinstance(writer, dict) or set(writer) != {"engine", "version"}:
        raise _invalid("writer must contain engine and version")
    if writer["engine"] != "sdd-workflow" or not isinstance(writer["version"], str):
        raise _invalid("writer values are invalid")
    if not isinstance(approval, dict) or set(approval) != {
        "state", "approval_model_version", "manifest_sha256"
    }:
        raise _invalid("approval metadata fields are invalid")
    if not isinstance(operation, dict) or set(operation) != {"kind", "operation_id"}:
        raise _invalid("last_operation fields are invalid")
    revision = value["revision"]
    if revision is not None and not isinstance(revision, dict):
        raise _invalid("revision must be an object or null")
    return ActiveMetadata(
        metadata_version=version,
        writer_version=writer["version"],
        approval_state=approval["state"],
        approval_model_version=approval["approval_model_version"],
        manifest_sha256=approval["manifest_sha256"],
        operation_kind=operation["kind"],
        operation_id=operation["operation_id"],
        revision=revision,
        attestation=value.get("attestation"),
        terminal=value.get("terminal"),
    )


def _invalid(message: str) -> ActiveMetadataError:
    return ActiveMetadataError(
        "ERROR_MACHINE_METADATA_INVALID", "inspect_machine_metadata", message
    )
