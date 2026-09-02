# Doctor diagnostic evidence contract

Status: v0.4 Proposal C contract

`doctor` is a read-only classifier of observable filesystem/artifact states. It never identifies an editor, assigns intent, chooses the most likely history, changes metadata, deletes temporary files, rebuilds INDEX, moves directories, or resumes a transaction.

## Evidence levels

| Code | Required evidence | What it does not claim | Stable action |
| --- | --- | --- | --- |
| `AMBIGUOUS_STATE` | Two or more incompatible interpretations are directly supported, such as duplicate legacy rows matching one directory. | Which record or operation is correct. | `inspect_archive_state` |
| `UNKNOWN_STATE` | Required evidence is absent/unreadable, such as a legacy archive summary with no unique INDEX source. | That an operation failed, or what the missing value should be. | `inspect_archive_state` |
| `PARTIAL_TRANSITION_DETECTED` | A defined artifact set/phase is only partly present, such as exactly one of metadata and Approval Manifest. | Which command created it, whether commit occurred, or whether deleting the remainder is safe. | `inspect_machine_metadata` |
| `OUT_OF_BAND_DRIFT` | Current parsed managed projection differs structurally from stored attestation. | Who edited it or whether the edit was manual, malicious, accidental, or interrupted. | `inspect_managed_state_drift` |
| `ERROR_INDEX_STALE` | Current INDEX bytes differ from deterministic rendering of complete canonical records. | That archive authority is damaged. | `rebuild_index` |
| `RECOVERY_STAGED_STATE` | A private recovery receipt is `staged`, `applying`, or `restoring`. | That any unrecorded step succeeded, or that rollback is still safe. | `resume_or_restore_recovery` |
| `ERROR_RECOVERY_STAGED_STATE_INVALID` | A recovery area/receipt is unsafe, unreadable, or violates its versioned structure. | Which bytes are authoritative or whether deletion is safe. | `inspect_recovery_state` |
| `ENGINE_VERSION_SKEW` | Parsed metadata names a strictly newer major/minor writer generation than the running engine. | That artifact format is incompatible, that the writer caused drift, or that timestamps decide authority. | `use_compatible_engine` |
| `ENGINE_VERSION_UNKNOWN` | Metadata writer is not strict `MAJOR.MINOR.PATCH` SemVer. | Which engine wrote it or whether its format is unsupported. | `inspect_engine_version` |
| `RUNTIME_SKILL_VERSION_SKEW` | The installed `SKILL.md` SHA-256 differs from the value fixed by the package identity manifest. | Which file was replaced, who replaced it, or whether either file should win. | `reinstall_complete_distribution` |

More specific evidence-based codes (`ACTIVE_ARCHIVE_COLLISION`, `STATUS_LOCATION_MISMATCH`, Manifest identity/semantic mismatch, unsupported version) take precedence over a generic unknown label when their predicates are proven.

## Manual remediation

- For `AMBIGUOUS_STATE`, inspect every named path/row, preserve a copy, and have a person select or correct the authoritative record. Rerun `doctor`; do not select the first/last entry automatically.
- For `UNKNOWN_STATE`, recover the missing fact from an external trusted source. A legacy archive directory missing terminal records has a supported path: the read-only `repair-archive-record` preflight plus explicitly confirmed execution, or `rebuild-index --directory NAME --summary TEXT` when only the summary is missing. Proposal prose is never a substitute for a missing legacy summary.
- For `PARTIAL_TRANSITION_DETECTED`, compare operation evidence, status/checkbox commit points, and all staged artifacts. Do not delete, complete, or roll back files solely from the generic diagnostic.
- For `OUT_OF_BAND_DRIFT`, inspect the JSON Pointer differences and the relevant command history. A fresh `status` does not refresh attestation; repair requires an explicit later protocol or a valid revision path.
- For `ERROR_INDEX_STALE`, run `rebuild-index` only after all archive records adapt without unknown/ambiguous/mismatch diagnostics.
- For `RECOVERY_STAGED_STATE`, use the reported operation ID with the same
  confirmed digest set to resume, or explicitly invoke the matching repair
  command's `--restore-operation`. Restore must stop if current bytes show a
  later lifecycle mutation. Never delete `.sdd-recovery` by hand.
- Committed and restored receipts are retained audit evidence and are not
  findings. Doctor output includes operation IDs/states, never stored source or
  candidate bodies.

Every finding reports paths and observed differences when available. Wording uses “differs,” “missing,” “multiple,” or “present”; it avoids “was modified by,” “caused by,” and other historical assertions unsupported by artifacts.

## Environment evidence

The JSON result also contains `data.environment`. Runtime identity,
capabilities, supported schemas, installed package path, Skill hash, version
skew, and repository health are reported only from files and runtime values
observed by the current process. Agent environment, Skill version, package
source, and discovery source are `unknown` unless a future version receives
verifiable provenance for them. `doctor` never guesses these values from a
home-directory name, current working directory, `PATH`, or a likely host
layout.
