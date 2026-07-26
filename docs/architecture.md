# Architecture and machine-metadata contract

Status: v0.4 Proposal A contract  
Decision date: 2026-07-22

## Responsibility boundary

- The Skill owns user intent, explicit approval, ambiguity resolution, command orchestration, and communication.
- The Python core owns artifact parsing, structural validation, canonical projection, snapshot checks, supported state transitions, and machine diagnostics.
- Scripts never decide whether implementation semantics satisfy a task. Agents never recreate structural parsing or state-transition rules in prose.
- A command can make supported mutation auditable and safer; it cannot prevent a user or another tool from editing files directly and cannot identify who made a change.

## Artifact authority

| Artifact or field | Authority | Meaning |
| --- | --- | --- |
| `proposal.md` `## 狀態` | Authoritative lifecycle state | The only source for `draft`, `approved`, `completed`, or `abandoned`. Metadata must not duplicate an independently writable status. |
| `tasks.md` checkbox markers | Authoritative task completion | The only source for current completion state. Approval projection includes task text but excludes markers. |
| Approval Manifest | Authoritative approved semantic baseline | The complete semantic value the user approved. It is compared structurally with a fresh projection; it does not replace current Markdown. |
| Active metadata | Authoritative machine evidence | Records metadata format, writer signal, approval-manifest identity/state, revision authorization, and operation evidence. It does not make semantic or lifecycle fields authoritative. |
| Snapshot manifest | Optimistic concurrency token | Identifies raw bytes observed by a caller. It is returned, not stored as a replacement authority for the artifacts. |

When two authorities disagree, no timestamp or writer version chooses a winner. The command fails with a typed mismatch and requires the remediation defined below.

## Storage layout

Machine-managed active artifacts live inside the proposal directory so a later terminal directory move carries them with the proposal:

```text
sdd/<short-name>/
├── proposal.md
├── tasks.md
└── .sdd/
    ├── metadata.json
    └── approval-manifest.json
```

- `.sdd/` and both files must be regular project-local paths. A symlink at any component fails closed before content is read or written.
- `.sdd/metadata.json` is the common machine envelope. Features add versioned fields to it instead of inventing unrelated sidecars.
- `.sdd/approval-manifest.json` stores the full Approval Manifest separately because it is a reviewable semantic artifact and has its own projection version.
- Both files use UTF-8 JSON with a trailing LF. Serialization is deterministic for reproducible fixtures and identity hashes, but correctness uses parsed structural comparison, never JSON key order.
- No v0.4 command adds an explicit proposal schema marker to an otherwise unversioned v1 Markdown artifact.
- Draft proposals may have no `.sdd/` directory. An approved proposal without a valid manifest is `legacy_unattested`, not silently repaired or treated as historically attested.
- `approve <short> --expected-snapshot <digest> --establish-manifest` is the only Proposal A baseline-establishment path. It accepts only a mutation-safe v1 proposal already in `approved`, treats the flag as the caller's explicit reconfirmation, writes a new manifest/envelope, and leaves the Markdown bytes—including an absent schema declaration—unchanged. Ordinary `approve` never adopts an already-approved proposal.

## Active metadata envelope

The first envelope is intentionally small:

```json
{
  "metadata_version": 1,
  "writer": {
    "engine": "sdd-workflow",
    "version": "1.0.1"
  },
  "approval": {
    "state": "active",
    "approval_model_version": 1,
    "manifest_sha256": "<64 lowercase hex>"
  },
  "revision": null,
  "last_operation": {
    "kind": "approve",
    "operation_id": "<opaque evidence token>"
  }
}
```

- `writer` is diagnostic provenance only. A newer or older writer string never overrides a supported format version and never proves who edited an artifact.
- `approval.state` is `active` or `invalidated`. It describes whether the manifest can authorize approved content; it does not duplicate proposal status.
- `revision` is absent/null outside an authorized revision or contains the Proposal A versioned revision marker. A direct Markdown status edit cannot create or clear this authorization.
- The Proposal A revision marker contains `revision_version: 1`, a `pending` or `open` phase, the approved-state source snapshot, and the field-level Approval Manifest differences observed when revision began. `pending` is staged before the status commit; `open` is finalized after it.
- `last_operation` is evidence for retry classification. It is not sufficient by itself to claim `ALREADY_APPLIED`; the command must also verify the authoritative artifacts and matching operation inputs.
- Unknown top-level fields are retained by writers when safe. An unknown field declared or conservatively classified as authority/approval relevant blocks mutation instead of being silently dropped.

## Version axes

| Axis | v1 value | Compatibility role |
| --- | --- | --- |
| Engine version | `1.0.1` | Diagnostic/release identity; not an artifact compatibility decision. |
| CLI output version | `1` | Selects the external JSON envelope contract. |
| Proposal schema version | implicit/explicit `1` | Selects the Markdown parser adapter; unknown explicit versions fail before parsing. |
| Canonical model version | `1` internal | Defines parser output consumed by projections; not exposed as a public parse API. |
| Snapshot version | `1` | Selects raw-byte CAS manifest serialization. |
| Active metadata version | `1` | Selects `.sdd/metadata.json` decoding and mutation compatibility. |
| Approval model version | `1` | Selects the semantic projection and structural comparison rules stored with each manifest. |

Compatibility is decided by the narrowest relevant version. Unknown metadata or approval-model versions fail closed with `ERROR_UNSUPPORTED_METADATA_VERSION` or `ERROR_UNSUPPORTED_APPROVAL_MODEL_VERSION` and action `use_supported_engine`. They are never inferred from the engine writer string.

## Mismatch and remediation rules

| Observed state | Code | Stable action | Rule |
| --- | --- | --- | --- |
| Caller snapshot differs from current raw bytes | `ERROR_SNAPSHOT_MISMATCH` | `refresh_status` | Do not retry mutation automatically. A fresh status does not preserve semantic approval by itself. |
| Current approval projection differs from active manifest | `ERROR_APPROVED_PLAN_CHANGED` | `begin_revision` | Return field-level structural differences. Completion-marker-only changes are excluded. |
| Approved proposal has no valid manifest/metadata | `ERROR_APPROVAL_MANIFEST_REQUIRED` | `establish_approval_manifest` | Classify as `legacy_unattested`; require explicit user reconfirmation. |
| Proposal status and metadata phase cannot form a supported state | `ERROR_METADATA_STATE_MISMATCH` | `inspect_machine_metadata` | Markdown status remains lifecycle authority; do not rewrite either side automatically. |
| Manifest identity in metadata differs from manifest bytes | `ERROR_APPROVAL_MANIFEST_IDENTITY_MISMATCH` | `inspect_machine_metadata` | Do not accept either value by timestamp or writer version. |
| Unsupported metadata or projection version | version-specific code above | `use_supported_engine` | Fail before mutation and preserve bytes. |
| Machine path is missing during initial draft | none | none | Valid unmanaged draft; `approve` may create the first envelope. |
| Machine path is malformed, non-regular, or a symlink | `ERROR_MACHINE_METADATA_INVALID` or path diagnostic | `inspect_machine_metadata` / `inspect_project_path` | Fail before artifact mutation. |

An unversioned but structurally valid v1 proposal stays unversioned after ordinary mutation. Establishing metadata records the parser/projection versions used by the engine without rewriting Markdown schema syntax.

## Multi-file transition boundary

Proposal A cannot make several files atomically visible as one filesystem transaction. Each command therefore defines one authoritative commit point and leaves enough staged operation evidence to classify a retry:

- `approve`: manifest and metadata are prepared first; the `proposal.md` status replacement to `approved` is the authoritative commit point. Draft status with staged approval files is not approved and must be diagnosed/cleaned safely.
- `begin-revision`: a pending revision operation is recorded first; the `proposal.md` status replacement to `draft` is the authoritative commit point. Metadata finalization is retryable from matching operation evidence.
- Individual file replacement is atomic on supported filesystems and uses the shared writer contract. Cross-file rollback is never described as ACID.

The command's result returns an after snapshot only after the committed state has been re-read and validated.

Proposal B's managed-state projection and attestation envelope are defined in [`managed-state.md`](./managed-state.md). That contract narrows drift evidence to parsed managed fields and does not expand attestation to whole-file bytes.

Proposal C's terminal metadata and canonical archive authority are defined in [`archive-model.md`](./archive-model.md). Archive directories and archived proposal status are authoritative; `INDEX.md` is derived except for preserving otherwise unavailable legacy summaries through the compatibility adapter.

The evidence thresholds and manual-only remediation for doctor findings are defined in [`doctor-diagnostics.md`](./doctor-diagnostics.md).

Terminal staging, the directory-move commit point, retry evidence, and activation/downgrade boundaries are defined in [`transaction-protocol.md`](./transaction-protocol.md). Version axes are centralized in [`compatibility.md`](./compatibility.md).

## Individual-file atomic writer

- The shared writer creates a uniquely named temporary file in the target directory, writes bytes, flushes the Python stream, and calls `fsync()` on the file before replacement.
- It preserves an existing target's permission bits; a new machine file starts at mode `0600` independent of the process umask.
- It rejects symlink or non-regular targets and a symlink/non-directory parent, then uses `os.replace()` for the individual-file commit point.
- Any failure before or during replacement removes the temporary file. A failed replacement leaves the prior target bytes intact. This contract does not claim a cross-file transaction or directory-entry durability after power loss.
