# Bundled CLI and JSON output

Status: internal command reference; JSON output version is public compatibility
Output version: `1`

`skills/sdd-workflow/scripts/sdd.py` is a non-interactive adapter from project artifacts to the deterministic core. It never prompts, reads a selection from stdin, or chooses among multiple active proposals. Read and managed-mutation commands are the formal v0.4 Skill path.

## Global syntax

```text
sdd.py [--root PATH] [--json] --version
sdd.py [--root PATH] [--json] validate SHORT_NAME
sdd.py [--root PATH] [--json] validate --all
sdd.py [--root PATH] [--json] list --state active
sdd.py [--root PATH] [--json] status SHORT_NAME
sdd.py [--root PATH] [--json] abandon-preflight SHORT_NAME
sdd.py [--root PATH] [--json] approve SHORT_NAME --expected-snapshot DIGEST [--establish-manifest]
sdd.py [--root PATH] [--json] begin-revision SHORT_NAME --expected-snapshot DIGEST
sdd.py [--root PATH] [--json] complete-task SHORT_NAME TASK_NUMBER --expected-task-digest DIGEST --expected-snapshot DIGEST
sdd.py [--root PATH] [--json] rebuild-index [--directory NAME --summary TEXT]
sdd.py [--root PATH] [--json] validate-index
sdd.py [--root PATH] [--json] doctor
sdd.py [--root PATH] [--json] repair-proposal-format SHORT_NAME [--type TYPE --scope TEXT --acceptance TEXT] [--apply --expected-proposal-sha256 DIGEST --expected-tasks-sha256 DIGEST --expected-candidate-proposal-sha256 DIGEST --expected-candidate-tasks-sha256 DIGEST] [--restore-operation OPERATION_ID]
sdd.py [--root PATH] [--json] repair-archive-record NAME [--terminal-status STATUS --summary TEXT --expected-proposal-sha256 DIGEST --expected-tasks-sha256 DIGEST]
sdd.py [--root PATH] [--json] archive SHORT_NAME --expected-snapshot DIGEST (--summary TEXT | --summary-file PATH) [--dry-run]
sdd.py [--root PATH] [--json] abandon SHORT_NAME --expected-snapshot DIGEST (--summary TEXT | --summary-file PATH) [--dry-run]
```

- `--root` is optional. Root resolution is explicit root, Git worktree root, upward search, then fail.
- `--json` selects the versioned machine envelope. It is global and precedes the command.
- `validate` requires exactly one of `SHORT_NAME` or `--all`.
- `list` requires `--state active`; v0.3 defines no other state query.
- `status` and `abandon-preflight` require exactly one short name.
- No command accepts stdin data or an interactive choice.
- Full canonical models and a public `parse` command are intentionally absent.
- Existing proposal status, task completion, metadata, archive location, and INDEX changes use these commands exclusively. Proposal creation and authorized revision prose remain agent-authored.

## Exit behavior

| Exit | Meaning |
| --- | --- |
| `0` | Command completed with no blocking error. Warnings may be present. |
| `1` | A discovery, security, artifact, schema, or validation error was reported. |
| `2` | Command-line usage is invalid. |
| `70` | An unexpected internal failure was caught; no traceback is printed by default. |

JSON mode uses the same exit status as human mode. A nonzero exit does not make the JSON document optional.

## Human output

- Successful command results go to stdout.
- Warnings and errors go to stderr as `CODE: message` with source location when available.
- Human wording and layout are not compatibility contracts.
- `list` prints sorted candidate short names and never selects one.
- `validate` prints a valid summary for each checked candidate; format errors are written to stderr and make the command exit `1`.
- `status` prints short name, adapter, status, type, completed/total tasks, count reliability, and snapshot digest.
- `abandon-preflight` prints progress, the non-revert warning, and separate labeled 64-character lowercase SHA-256 values for `proposal.md` and `tasks.md`. Task-format diagnostics degrade counts to unreliable warnings instead of blocking preflight. Structural, path, or unsupported-schema failures remain blocking.
- `--version` prints engine version and the supported schema range.
- Lifecycle command output ends with labeled `current state`, `next action`, `blocked reason`, `required user action`, and `authoritative path` fields. Successful guidance is written to stdout; blocking guidance accompanies errors on stderr. A committed terminal transition remains reported as completed/abandoned when only the derived INDEX is stale.
- Guidance is derived from the same command result but is not a machine contract. Automation continues to use `--json`, stable `code`/`action`, and the versioned envelope.

## JSON output

Every JSON-mode result writes exactly one UTF-8 JSON document plus a trailing newline to stdout and writes nothing to stderr:

```json
{
  "output_version": 1,
  "command": "status",
  "ok": true,
  "warnings": [],
  "errors": [],
  "data": {}
}
```

Only `output_version`, `command`, `ok`, `warnings`, `errors`, error `code`, and error `action` are compatibility fields in v0.3. Messages, suggested commands, key order, and presentation fields may evolve. Candidate, task, and diagnostic ordering are nevertheless deterministic implementation invariants covered by tests. Additive command-data projections may remain on output version `1` when they do not change mutation inputs, authority, or error behavior; unknown fields remain ignorable.

Diagnostic objects may also include `message`, `path`, `line`, `column`, and `severity`. A missing value is omitted rather than encoded as an invented location.

## Command data

### `--version`

Human output contains `sdd-workflow <engine-version> (schema 1..2)`. JSON data contains `engine_version`, `minimum_schema_version`, and `maximum_schema_version`.

### `validate`

Data contains a sorted `results` array. Each result contains `short_name`, `valid`, `adapter`, and diagnostic arrays. `--all` validates every complete active candidate; an incomplete directory is not silently promoted to a candidate.

### `list --state active`

Data contains `state: "active"` and a sorted `candidates` array. Each candidate contains its short name and parsed summary when readable. Multiple candidates are a successful list result, not an ambiguity error.

### `status`

Data contains the canonical summary fields needed by the Skill: short name, adapter, status, change type, ordered tasks, completed and total counts, count reliability, compatibility flags, and the snapshot manifest. Each task includes its one-based `ordinal`, exact scanner `source_text`, parser-owned `canonical_text`, compatibility alias `text`, `completed` state, source line, and `task_digest`. The digest is lowercase SHA-256 of the canonical text's UTF-8 bytes without Unicode normalization; ordinal and completion are intentionally excluded. Schema v2 research also exposes `research_conclusion` as an ordered string array. Other arbitrary canonical extensions remain internal. For an approved proposal with a managed approval baseline, `status` also checks manifest identity, attested managed fields, and approval-relevant semantic equality. Observable drift returns a nonzero envelope with field-level `differences` before implementation can start; this readonly check never refreshes metadata.

### `abandon-preflight`

Data contains the same ordered progress fields as `status`, a `working_tree_reverted: false` assertion, and the snapshot manifest with both raw artifact hashes. Task syntax errors move to `warnings` and set `task_counts_reliable: false`; no artifact is repaired.

### Managed active transitions

Read compatibility never authorizes mutation. When a readable legacy proposal
has `mutation_safe: false`, `approve`, `begin-revision`, `complete-task`,
`archive`, and `abandon` all exit nonzero without writing and return
`ERROR_LEGACY_MUTATION_UNSUPPORTED` with action
`upgrade_or_recreate_proposal` except that `archive` routes a registered
format to `repair_proposal_format`. Existing parser warnings remain in the same
envelope. A mutation command must never return a successful parse-only result
when no transition was attempted.

`approve` requires a mutation-safe draft plus its exact current snapshot. It stores the Approval Manifest and metadata before committing the status change, then returns before/after snapshots, operation evidence, `after_state`, and `next_task`. `--establish-manifest` instead requires an already-approved unattested v1 proposal, represents explicit caller reconfirmation, and does not change the Markdown bytes.

`begin-revision` requires an attested approved proposal and its exact current snapshot. It records field-level semantic differences, invalidates the prior approval, commits status `draft`, and returns the after snapshot. A retry with identical inputs may finalize or recognize the same revision operation; it never adopts unrelated current bytes.

`complete-task` validates approved status, task ordinal and digest, raw snapshot, Approval Manifest, and managed-state attestation. It stages the intended after attestation and atomically replaces the exact incomplete checkbox as the authoritative commit point. Successful `approve` and `complete-task` results contain `after_state`, exactly the data a status command projects for the committed state, plus `next_task`, the first incomplete task object from that state or `null`. The existing `after_snapshot` remains unchanged and equals `after_state.snapshot`; callers may feed that snapshot and `next_task.task_digest` directly into the next `complete-task`. `begin-revision`, `archive`, and `abandon` results do not add these fields.

`rebuild-index` adapts every direct archive directory to a canonical record and fails without writing when any record is unknown, ambiguous, or mismatched. Otherwise it deterministically renders all records and atomically replaces `INDEX.md` only when bytes differ. It never writes a legacy archive directory or derives a missing summary from prose. `--directory` and `--summary` are accepted only together: the explicitly provided summary applies to exactly that directory and only when it has no summary source at all; a directory that already has an authoritative summary returns `ERROR_RECOVERY_SUMMARY_UNEXPECTED` without writing.

`validate-index` performs the same read-only adaptation and compares the derived rendering with current `INDEX.md`. A missing, unsafe, non-UTF-8, reordered, or otherwise different INDEX returns `ERROR_INDEX_STALE`, action `rebuild_index`, and deterministic `/lines/<index>` differences without changing bytes.

`doctor` is read-only and reports evidence-bound findings for active/archive collisions, lifecycle/location mismatch, stale INDEX, transaction-shaped temporary files, incomplete private recovery operations, partial machine artifacts, Approval Manifest mismatch, and managed-state drift. `RECOVERY_STAGED_STATE` exposes only operation identity/state and routes to `resume_or_restore_recovery`; committed/restored receipts are not findings. A finding describes observed state and remediation action; it never identifies the editor, invents a unique cause, or repairs files.

`repair-proposal-format` is a dedicated active recovery command, not a parser fallback. Preflight returns a redacted `projection` with registered encoding, source/candidate digests, required explicit inputs, evidence-source hashes, and field-level changes; it never returns source or candidate bodies. Only top-level non-empty checkbox deviations with blank/`x`/`X` state and registered list markers are normalizable. Apply requires all four Markdown digests from the same projection and installs only a strictly validated Schema v2 `draft` through the staged recovery protocol. Existing approval/attestation artifacts block recovery with `inspect_machine_metadata`. The result does not carry approval and therefore requires the ordinary approval/task/acceptance gates. `--restore-operation` restores exact private originals only while no later lifecycle mutation is observable.

`repair-archive-record` targets one direct archive directory. Without execution flags it is a read-only preflight: data reports identity, terminal-state evidence, missing fields, raw artifact digests, and the same redacted recovery projection. The original evidence-repair flags remain supported for readable records. When `reconstruction_required` is true, apply additionally requires candidate proposal/tasks/metadata digests and the reported `recovery_timestamp`; an existing metadata source also requires `--expected-metadata-sha256`. The staged operation reconstructs registered Markdown or recovery-v1 JSON, keeps the directory and terminal status, writes recovery evidence without a managed `terminal` object, and rebuilds INDEX. It never derives missing semantics, never reruns historical project tests, and never rewrites already-valid Markdown merely because recovery JSON needs repair. Valid managed records are evidence-backed `NO_OP`; an exact reconstruction retry is `ALREADY_APPLIED`.

`archive` and `abandon` accept exactly one summary source. Inline `--summary` rejects CR/LF; `--summary-file` reads at most 65,536 bytes as strict UTF-8, allows multiple lines, and rejects stdin (`-`), empty/whitespace-only content, and NUL. Metadata preserves the decoded source exactly. INDEX display normalizes CRLF/CR to LF, replaces each LF with ` ⏎ `, then applies backslash/pipe escaping.

## Stable error actions

| Condition | Code | Action |
| --- | --- | --- |
| No project root | `ERROR_PROJECT_ROOT_NOT_FOUND` | `select_project_root` |
| Invalid or missing short name | `ERROR_INVALID_SHORT_NAME` | `choose_short_name` |
| Missing proposal directory/artifact | `ERROR_PROPOSAL_NOT_FOUND` / `ERROR_ARTIFACT_MISSING` | `create_or_select_proposal` |
| Path escape or symlink | `ERROR_PATH_OUTSIDE_SDD` / `ERROR_SYMLINK_UNSUPPORTED` | `inspect_project_path` |
| Unknown schema | `ERROR_UNSUPPORTED_SCHEMA_VERSION` | `use_supported_engine` |
| Invalid/unknown schema metadata | `ERROR_INVALID_SCHEMA_METADATA` / `ERROR_UNKNOWN_SCHEMA_FIELD` | `fix_artifact_format` |
| Managed mutation attempted on a readable legacy proposal | `ERROR_LEGACY_MUTATION_UNSUPPORTED` | `upgrade_or_recreate_proposal` |
| Archive blocked by a registered active legacy format | parser/legacy diagnostic | `repair_proposal_format` |
| INDEX/doctor finds a registered recoverable archive format | archive diagnostic | `repair_archive_record` |
| Recovery lacks explicit type/scope/acceptance/summary | `ERROR_RECOVERY_INPUT_REQUIRED` | `provide_recovery_input` |
| Recovery receipt is incomplete | `RECOVERY_STAGED_STATE` | `resume_or_restore_recovery` |
| Recovery retry/restore conflicts with current lifecycle bytes | `ERROR_RECOVERY_RETRY_CONFLICT` / `ERROR_RECOVERY_RESTORE_UNSAFE` | `rerun_repair_preflight` / `inspect_lifecycle_state` |
| Artifact format invalid | parser diagnostic code | `fix_artifact_format` |
| Snapshot mismatch in a later mutation | `ERROR_SNAPSHOT_MISMATCH` | `refresh_status` |
| Task ordinal absent / task text identity changed | `ERROR_TASK_NOT_FOUND` / `ERROR_TASK_IDENTITY_MISMATCH` | `refresh_status` |
| Approved semantic content changed | `ERROR_APPROVED_PLAN_CHANGED` | `begin_revision` |
| Completed research lacks conclusion | `ERROR_RESEARCH_CONCLUSION_REQUIRED` | `complete_research_conclusion` |
| Parsed status/checkbox/metadata differs from attestation | `OUT_OF_BAND_DRIFT` | `inspect_managed_state_drift` |
| Matching retry evidence conflicts with current artifacts | `ERROR_TASK_RETRY_CONFLICT` | `inspect_managed_state_drift` |
| Approval metadata/Manifest missing or inconsistent | metadata-specific code | `establish_approval_manifest` / `inspect_machine_metadata` |
| Repair target missing, unsafe, unsupported, or unreadable | `ERROR_RECOVERY_TARGET_INVALID` | `inspect_archive_state` |
| Repair target already carries managed terminal evidence | `ERROR_RECOVERY_NOT_APPLICABLE` | `inspect_archive_state` |
| Archived bytes differ from confirmed evidence digests | `ERROR_RECOVERY_EVIDENCE_MISMATCH` | `rerun_repair_preflight` |
| Terminal status disagrees with directory suffix or existing status | `ERROR_RECOVERY_STATUS_MISMATCH` | `inspect_archive_state` |
| Provided summary targets a directory whose summary is not missing | `ERROR_RECOVERY_SUMMARY_UNEXPECTED` | `inspect_archive_state` |
| Invalid CLI syntax | `ERROR_USAGE` | `fix_command_arguments` |
| Unexpected failure | `ERROR_INTERNAL` | `report_internal_error` |

The CLI may add non-contract `suggested_command` text, but consumers branch on `code` and `action`, never on message prose.
