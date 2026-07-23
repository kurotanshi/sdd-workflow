"""Versioned raw-byte snapshot manifests."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any


SNAPSHOT_VERSION = 1
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class SnapshotManifest:
    proposal_sha256: str
    tasks_sha256: str
    snapshot_digest: str
    snapshot_version: int = SNAPSHOT_VERSION

    def __post_init__(self) -> None:
        if self.snapshot_version != SNAPSHOT_VERSION:
            raise ValueError(f"unsupported snapshot version: {self.snapshot_version}")
        for value in (
            self.proposal_sha256,
            self.tasks_sha256,
            self.snapshot_digest,
        ):
            if not _SHA256.fullmatch(value):
                raise ValueError("snapshot hashes must be lowercase SHA-256 hex")

    def payload(self) -> dict[str, Any]:
        return {
            "snapshot_version": self.snapshot_version,
            "proposal_sha256": self.proposal_sha256,
            "tasks_sha256": self.tasks_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "snapshot_digest": self.snapshot_digest}


def build_snapshot(proposal_bytes: bytes, tasks_bytes: bytes) -> SnapshotManifest:
    proposal_sha256 = hashlib.sha256(proposal_bytes).hexdigest()
    tasks_sha256 = hashlib.sha256(tasks_bytes).hexdigest()
    payload = _canonical_payload(proposal_sha256, tasks_sha256)
    return SnapshotManifest(
        proposal_sha256=proposal_sha256,
        tasks_sha256=tasks_sha256,
        snapshot_digest=hashlib.sha256(payload).hexdigest(),
    )


def canonical_snapshot_payload(manifest: SnapshotManifest) -> bytes:
    """Return the exact v1 composite-digest preimage."""

    return _canonical_payload(manifest.proposal_sha256, manifest.tasks_sha256)


def _canonical_payload(proposal_sha256: str, tasks_sha256: str) -> bytes:
    return json.dumps(
        {
            "snapshot_version": SNAPSHOT_VERSION,
            "proposal_sha256": proposal_sha256,
            "tasks_sha256": tasks_sha256,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
