# Terminal transaction protocol v1

Status: v0.4 Proposal D contract

## Commit model

`archive` and `abandon` are multi-artifact protocols, not ACID transactions. Each individual file uses the shared atomic writer; the directory move from `sdd/<short-name>/` to its final direct child under `sdd/archive/` is the sole authoritative terminal commit point.

```text
validate inputs and destination
→ stage terminal metadata with intended after-state attestation
→ atomically replace proposal status
→ atomically rename the proposal directory (authoritative commit)
→ rebuild the complete derived INDEX
→ report result
```

- Before the move, the proposal is still active even if staged metadata/status indicates a pending terminal transition. `doctor` reports the observable partial state and command retry may continue only when operation evidence and exact inputs agree.
- After the move, the archive is committed. Failure to rebuild INDEX never moves the directory back and returns `COMMITTED_DERIVED_ARTIFACT_STALE` with action `rebuild_index`.
- The terminal metadata travels inside `.sdd/metadata.json`; it contains `terminal_metadata_version: 1`, local `archive_date`, short name, terminal status, UTC timestamp, original summary, source snapshot, destination directory name, and operation evidence.
- `archive_date` comes from the execution environment's local calendar date and determines the directory prefix. UTC RFC 3339 `timestamp` is independent audit evidence and may have a different calendar date near midnight.
- The operation ID is derived from command kind, short name, terminal status, exact source snapshot, destination, and validated summary bytes. It contains no secret and is evidence only.

## Preconditions

`archive` accepts only attested `approved` proposals with at least one task and all tasks completed. It validates snapshot CAS, Approval Manifest equality, managed-state attestation, destination absence, and summary input before any write.

`abandon` accepts `draft` or `approved`. An approved proposal requires the same active Manifest/attestation checks as other mutations. An authorized revision draft requires its revision metadata/attestation. An initial unmanaged draft may establish terminal metadata directly because it has no claimed approval baseline. Legacy/statusless proposals retain only the separately documented compatibility path and are not silently promoted to managed mutation.

Both commands support `--dry-run`. Dry run executes all deterministic validations and returns `would_change`, `before_snapshot`, `predicted_changes`, and `after_snapshot: null`; it does not choose a timestamp, write a file, create a directory, change mode/mtime, or move an entry.

## Retry evidence

- Destination absent plus exact matching staged metadata and pre-move status may resume toward the same move.
- Destination present and source absent is `ALREADY_APPLIED` only when terminal metadata, operation ID, directory name, terminal status, source snapshot, and summary all match the requested operation.
- Destination present with source present is a collision/ambiguous state; no merge, overwrite, suffix increment, or automatic deletion occurs.
- Source absent with insufficient/malformed terminal evidence is `AMBIGUOUS_STATE`, not success.
- A stale source snapshot without matching staged/committed operation evidence is `ERROR_SNAPSHOT_MISMATCH`; acquiring a fresh status does not authorize an automatic retry.

## Failure-injection matrix

| Injected point | Authoritative commit? | Expected retry | Expected doctor evidence |
| --- | --- | --- | --- |
| Before terminal metadata replace | No | Revalidate unchanged source; retry normally. | No terminal partial solely from the failed write; an empty newly created `.sdd/` is not fabricated history. |
| After metadata, before status | No | Matching operation may finish status then move. | `PARTIAL_TRANSITION_DETECTED` for terminal metadata in active location. |
| After status, before directory move | No | Reconstruct exact source snapshot, then move. | `PARTIAL_TRANSITION_DETECTED` plus `STATUS_LOCATION_MISMATCH`. |
| After move, before INDEX replace | Yes | Never move back; return/retain `COMMITTED_DERIVED_ARTIFACT_STALE`. | `ERROR_INDEX_STALE`; archive record remains readable. |
| After INDEX replace, before success response | Yes | Matching retry returns `ALREADY_APPLIED` when INDEX validates. | No stale finding merely because the prior response was lost. |

## Terminal result and remediation matrix

| Situation | Result/code | Caller behavior |
| --- | --- | --- |
| First archive/abandon commits and INDEX rebuilds | `APPLIED` | Use returned destination/after snapshot; do not reuse the source snapshot for another mutation. |
| Exact successful operation is repeated | `ALREADY_APPLIED` | Treat as success; no files are rewritten. |
| Move committed but INDEX is missing/stale/unrebuildable | `COMMITTED_DERIVED_ARTIFACT_STALE` / `rebuild_index` | Preserve the archive, inspect record diagnostics, then run `rebuild-index`; never retry by restoring/moving the source. |
| Snapshot is stale and no matching staged/committed evidence exists | `ERROR_SNAPSHOT_MISMATCH` / `refresh_status` | Read current status and stop for renewed intent; do not automatically invoke terminal mutation. |
| Destination exists while source still exists | `ERROR_ARCHIVE_DESTINATION_COLLISION` or `AMBIGUOUS_STATE` / `inspect_archive_state` | Inspect both directories; never overwrite, merge, delete, or increment a suffix automatically. |
| Source is missing and same-name archive evidence does not exactly match snapshot/summary/operation | `AMBIGUOUS_STATE` / `inspect_archive_state` | Require human inspection; do not claim the requested operation committed. |
| Pre-move metadata/status is partially staged with exact matching operation evidence | Resume and return `APPLIED` | Continue only the remaining defined steps; mismatched evidence is ambiguous/drift. |

These rules are identical for `archive` and `abandon`; only source-state/task preconditions, terminal status, and destination suffix differ.

## Artifact reconstruction staged protocol v1

Legacy reconstruction is a separate multi-file protocol and likewise makes no
ACID claim:

```text
confirm source/candidate digests
→ save private originals, candidates, identity, and staged receipt
→ strictly validate every candidate
→ atomically replace each authoritative file and record progress
→ verify final digests
→ mark receipt committed
→ rebuild derived INDEX when the target is archived
```

The target-local `.sdd-recovery/<operation-id>/` and its `copies/` directory
use mode `0700`; copied bytes and the manifest use `0600`. Normal active and
archive discovery never treats this area as proposal authority. Reports expose
only digests, operation state, and structured field changes.

A retry accepts each file only when it equals the saved original or candidate;
anything else is `ERROR_RECOVERY_RETRY_CONFLICT`. Replacement before receipt
update is recoverable because retry recognizes the candidate digest and records
the completed step. Success requires all candidate digests plus a committed
receipt. Exact repeats return `ALREADY_APPLIED`.

Explicit restore performs an all-path safety check before changing anything,
then restores saved originals and removes only files the operation proved it
created. It is resumable after partial restore. A later approval, task
completion, terminal mutation, or any unrelated byte value produces
`ERROR_RECOVERY_RESTORE_UNSAFE`; automatic rollback is then forbidden and the
private evidence remains for inspection.

## Upgrade, activation, and downgrade

Implementation availability does not activate a Skill path. Until the managed-mutation pilot passes for approve/revision, complete-task, archive, and abandon together, `SKILL.md` remains on its coherent v0.3 script-read/prose-write path.

After activation, proposals carrying v0.4 metadata must use the managed command group. A pre-v0.4 Skill may read compatible Markdown but must not mutate such proposals. Supported rollback is to pin the prior Skill only for proposals with no v0.4 metadata, or first finish/abandon managed in-flight proposals under the current engine. Deleting metadata is not downgrade, recovery, or proof of a prose-era state.
