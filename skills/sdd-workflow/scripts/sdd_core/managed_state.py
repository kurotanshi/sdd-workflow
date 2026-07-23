"""Versioned projection and attestation of parsed machine-managed state."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .active_metadata import ActiveMetadata
from .approval import ApprovalDifference
from .model import CanonicalProposal


ATTESTATION_VERSION = 1
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ManagedStateError(ValueError):
    def __init__(self, code: str, action: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.action = action
        self.message = message


def project_managed_state(
    model: CanonicalProposal, metadata: ActiveMetadata
) -> dict[str, Any]:
    metadata_value = metadata.to_dict()
    metadata_value.pop("writer")
    metadata_value.pop("attestation", None)
    return {
        "status": model.status,
        "tasks": [
            {"ordinal": task.ordinal, "completed": task.completed}
            for task in model.tasks
        ],
        "metadata": metadata_value,
    }


def create_attestation(
    model: CanonicalProposal, metadata: ActiveMetadata
) -> dict[str, Any]:
    projection = project_managed_state(model, metadata)
    return {
        "attestation_version": ATTESTATION_VERSION,
        "projection": projection,
        "projection_sha256": _projection_sha256(projection),
    }


def validate_attestation(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "attestation_version", "projection", "projection_sha256"
    }:
        raise _invalid("Attestation fields are missing or unsupported")
    version = value["attestation_version"]
    if type(version) is not int or version != ATTESTATION_VERSION:
        raise ManagedStateError(
            "ERROR_UNSUPPORTED_ATTESTATION_VERSION",
            "use_supported_engine",
            f"Unsupported attestation version: {version!r}",
        )
    projection = value["projection"]
    if not isinstance(projection, dict) or set(projection) != {"status", "tasks", "metadata"}:
        raise _invalid("Attestation projection fields are invalid")
    digest = value["projection_sha256"]
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise _invalid("Attestation projection digest is invalid")
    if digest != _projection_sha256(projection):
        raise _invalid("Attestation projection digest does not match stored projection")
    return _json_copy(projection)


def compare_attested_state(
    attestation: object,
    model: CanonicalProposal,
    metadata: ActiveMetadata,
) -> tuple[ApprovalDifference, ...]:
    stored = validate_attestation(attestation)
    current = project_managed_state(model, metadata)
    differences: list[ApprovalDifference] = []
    _diff(stored, current, "", differences)
    return tuple(differences)


def _projection_sha256(projection: dict[str, Any]) -> str:
    data = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _diff(approved: Any, current: Any, path: str, output: list[ApprovalDifference]) -> None:
    if type(approved) is not type(current):
        output.append(ApprovalDifference(path or "", "changed", approved, current))
        return
    if isinstance(approved, dict):
        for key in sorted(set(approved) | set(current)):
            child = f"{path}/{str(key).replace('~', '~0').replace('/', '~1')}"
            if key not in approved:
                output.append(ApprovalDifference(child, "added", current=current[key]))
            elif key not in current:
                output.append(ApprovalDifference(child, "removed", approved=approved[key]))
            else:
                _diff(approved[key], current[key], child, output)
        return
    if isinstance(approved, list):
        shared = min(len(approved), len(current))
        for index in range(shared):
            _diff(approved[index], current[index], f"{path}/{index}", output)
        for index in range(shared, len(approved)):
            output.append(ApprovalDifference(f"{path}/{index}", "removed", approved=approved[index]))
        for index in range(shared, len(current)):
            output.append(ApprovalDifference(f"{path}/{index}", "added", current=current[index]))
        return
    if approved != current:
        output.append(ApprovalDifference(path or "", "changed", approved, current))


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _invalid(message: str) -> ManagedStateError:
    return ManagedStateError(
        "ERROR_MANAGED_STATE_ATTESTATION_INVALID",
        "inspect_managed_state_drift",
        message,
    )

