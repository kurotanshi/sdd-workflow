"""Read-only identity and capability handshake for the packaged runtime."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .active_metadata import METADATA_VERSION
from .approval import APPROVAL_MODEL_VERSION
from .archive_model import ARCHIVE_MODEL_VERSION
from .managed_state import ATTESTATION_VERSION
from .model import CANONICAL_MODEL_VERSION
from .parser_v1 import SUPPORTED_SCHEMA_VERSIONS
from .snapshot import SNAPSHOT_VERSION
from .version import ENGINE_VERSION, engine_generation


DISTRIBUTION_ID = "sdd-workflow"
HANDSHAKE_VERSION = 1
CLI_OUTPUT_VERSION = 1
TERMINAL_METADATA_VERSION = 1
CAPABILITIES = (
    "approval-manifest-v1",
    "archive-model-v1",
    "doctor-v1",
    "managed-attestation-v1",
    "managed-transitions-v1",
    "schema-v1",
    "schema-v2",
    "terminal-transitions-v1",
)

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
IDENTITY_MANIFEST = PACKAGE_ROOT / "runtime-identity.json"
SKILL_FILE = PACKAGE_ROOT / "SKILL.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_handshake() -> dict[str, Any]:
    generation = engine_generation(ENGINE_VERSION)
    if generation is None:
        raise RuntimeError("runtime engine version is not semantic")
    return {
        "handshake_version": HANDSHAKE_VERSION,
        "distribution_id": DISTRIBUTION_ID,
        "engine_version": ENGINE_VERSION,
        "engine_generation": ".".join(str(part) for part in generation),
        "cli_output_version": CLI_OUTPUT_VERSION,
        "minimum_schema_version": min(SUPPORTED_SCHEMA_VERSIONS),
        "maximum_schema_version": max(SUPPORTED_SCHEMA_VERSIONS),
        "capabilities": list(CAPABILITIES),
        "artifact_versions": {
            "active_metadata": METADATA_VERSION,
            "approval_model": APPROVAL_MODEL_VERSION,
            "archive_model": ARCHIVE_MODEL_VERSION,
            "canonical_model": CANONICAL_MODEL_VERSION,
            "managed_attestation": ATTESTATION_VERSION,
            "snapshot": SNAPSHOT_VERSION,
            "terminal_metadata": TERMINAL_METADATA_VERSION,
        },
        "runtime_identity_sha256": _sha256(IDENTITY_MANIFEST),
        "skill_sha256": _sha256(SKILL_FILE),
    }
