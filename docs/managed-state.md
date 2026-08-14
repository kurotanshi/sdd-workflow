# Managed-state attestation v1

Status: v0.4 Proposal B contract  
Attestation version: `1`

## Purpose and boundary

Managed-state attestation is structural evidence of the last state committed by a supported command. It detects that current managed fields differ from that baseline; it cannot identify the editor, infer intent, or distinguish a person from an agent or interrupted tool.

The three integrity layers remain independent:

| Layer | Input | Mismatch action |
| --- | --- | --- |
| Snapshot CAS | Raw `proposal.md` and `tasks.md` bytes observed by the caller | `refresh_status` |
| Approval Manifest | Approval-relevant semantic projection, including task text | `begin_revision` |
| Managed-state attestation | Parsed lifecycle/progress and machine-managed metadata | `inspect_managed_state_drift` |

Attestation never includes entire Markdown bytes, ordinary prose, task text, acceptance text, headings, source lines, whitespace, or file timestamps. An edit excluded from both the Approval Manifest and managed-state projection requires a fresh snapshot but does not create managed-state drift.

## Storage and envelope

The attestation is the required top-level `attestation` field in `.sdd/metadata.json` once Proposal B manages an approved proposal:

```json
{
  "attestation": {
    "attestation_version": 1,
    "projection": {
      "status": "approved",
      "tasks": [
        {"ordinal": 1, "completed": false}
      ],
      "metadata": {
        "metadata_version": 1,
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
    },
    "projection_sha256": "<64 lowercase hex>"
  }
}
```

The stored projection is the correctness baseline. `projection_sha256` is a raw identity/check token over its deterministic UTF-8 JSON serialization and never replaces structural comparison.

## Versioned projection

Managed-state projection v1 contains exactly:

- the canonical proposal `status`;
- one ordered task entry per canonical task, containing only its one-based `ordinal` and `completed` boolean;
- active metadata's `metadata_version`, `approval`, `revision`, and `last_operation` values.

The projection deliberately excludes:

- `writer`, because it is diagnostic provenance rather than authoritative state;
- the `attestation` field itself, preventing recursive serialization;
- task text/digest, which belong to task identity and Approval Manifest checks;
- proposal schema/canonical model versions, raw snapshots, paths, timestamps, and non-managed extensions.

Unknown metadata fields are not silently excluded. The v1 reader blocks mutation unless a later metadata version explicitly classifies them, because an unknown field may be machine-managed authority.

## Update and comparison rules

1. A mutating command validates the caller snapshot, Approval Manifest, current metadata, and current projection against the stored attestation before changing managed fields.
2. It computes the intended after-state metadata (excluding attestation), status, and completion markers, then stores an attestation of that after-state as part of the same operation protocol.
3. `status`, `validate`, `list`, preflight, and other read-only commands never create, replace, or refresh an attestation.
4. Structural differences use deterministic JSON Pointer paths such as `/status`, `/tasks/1/completed`, or `/metadata/approval/state`.
5. Any unexplained difference returns `OUT_OF_BAND_DRIFT` with stable action `inspect_managed_state_drift`. The diagnostic states only the observed field differences.
6. An initial unmanaged draft needs no attestation. `approve` or explicit baseline establishment creates the first one. An authorized `begin-revision` updates it to the committed draft/revision-marker projection; directly editing approved status to draft leaves the approved attestation unchanged and is drift.
7. Missing attestation on a pre-v0.4 approved artifact is a transitional unattested state, not proof of drift or approval history. It must use the explicit baseline-establishment path before `complete-task`.

## Commit and retry boundary

Attestation records the intended after projection, while authoritative Markdown status/checkboxes remain the commit points. Operation evidence must be sufficient to distinguish a matching interrupted write from unrelated drift before returning `ALREADY_APPLIED` or finalizing metadata. If the observed state admits multiple explanations, fail closed as conflict/ambiguous state; never rebuild attestation from current files merely because a caller reran `status`.

### `complete-task` retry matrix

| Observed state for the same operation ID and inputs | Result |
| --- | --- |
| Metadata/after-attestation staged; exact source snapshot and incomplete target remain | Finish the checkbox commit and return `APPLIED`. |
| Target checkbox completed; current projection matches attestation; replacing only that marker reconstructs the exact source snapshot | Return success with `ALREADY_APPLIED` and do not rewrite files. |
| Caller uses an old snapshot but matching operation evidence is absent | `ERROR_SNAPSHOT_MISMATCH` / `refresh_status`; do not retry automatically. |
| Target is already completed under different/insufficient operation evidence | Managed drift or `ERROR_TASK_ALREADY_COMPLETED`; never claim idempotent success. |
| Proposal/task text, another artifact byte, status, metadata, or Manifest changed so the exact source cannot be reconstructed | `ERROR_TASK_RETRY_CONFLICT` / `inspect_managed_state_drift`. |

Validation precedence is: proven same-operation retry; otherwise snapshot CAS, metadata/Manifest identity and attestation, approved source state, ordinal/task digest, then Approval Manifest semantic equality. A read-only status call never upgrades weak evidence into a proven retry.

After a successful `approve` or `complete-task`, the JSON result projects the committed canonical state as `after_state` and its first incomplete task as `next_task`. This removes a separate read-only status process between task completions without changing any integrity layer: the next mutation still requires and revalidates the exact returned snapshot, ordinal, and task digest. A lost response is retried with the identical original inputs so the operation ID can prove `ALREADY_APPLIED`; a new status must not replace those inputs for retry.
