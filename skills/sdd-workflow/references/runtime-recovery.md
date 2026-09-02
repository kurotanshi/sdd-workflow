# Runtime error and recovery reference

Read this file completely before handling any runtime error, abandonment,
terminal recovery, or doctor finding.

## Binding actions

| Action | Required behavior |
| --- | --- |
| `select_project_root`, `choose_short_name` | Ask the user for the missing choice |
| `create_or_select_proposal` | Stop; do not implicitly create/repair artifacts |
| `refresh_status` | Rerun readonly status, explain stale evidence, and stop for renewed intent |
| `begin_revision`, `begin_revision_and_reapprove` | Use the explicit revision flow |
| `establish_approval_manifest` | Require explicit canonical-plan reconfirmation |
| `inspect_project_path`, `inspect_machine_metadata`, `inspect_managed_state_drift`, `inspect_archive_state` | Stop mutation and report observable evidence |
| `use_supported_engine`, `upgrade_or_recreate_proposal`, `fix_artifact_format` | Stop and describe the compatible remediation |
| `rebuild_index` | Run only after terminal evidence or doctor proves only derived INDEX is stale |
| `rerun_repair_preflight` | Rerun the readonly repair preflight and confirm its fresh evidence digests |
| `repair_proposal_format` | Run active reconstruction preflight; never edit Markdown directly |
| `repair_archive_record` | Run archive reconstruction preflight for the named directory |
| `provide_recovery_input` | Ask only for the listed non-derived values; never infer them |
| `resume_or_restore_recovery` | Report the operation ID and ask whether to resume the same evidence or explicitly restore |
| `inspect_recovery_state`, `inspect_lifecycle_state` | Stop automatic recovery; preserve private evidence and report the observed conflict |
| `report_internal_error` | Stop and retain failure evidence |

Unavailable launcher/Python/tool permission also stops. Do not open raw artifacts
to reconstruct status and do not fall back to another runtime.

## Abandonment evidence

Preflight is readonly. It may degrade task-format problems into unreliable
counts but structural, path, or schema errors remain blocking. Its report must:

- name the canonical proposal and progress;
- warn that implementation and Git changes are retained;
- print labeled `snapshot.proposal_sha256` and `snapshot.tasks_sha256`; and
- request exact `確認放棄 <short-name>`.

Execution requires those same two hashes in the current conversation. Rerun
preflight, compare both pairs as exact strings in the execution environment,
and use only the matching fresh snapshot digest. Never compare visually,
substitute a fresh expected value, reuse another short name/session, or persist
confirmation in a file.

## Terminal result procedure

| Result | Meaning and action |
| --- | --- |
| `APPLIED` | Terminal bundle committed; report success |
| `ALREADY_APPLIED` | Matching operation evidence proves prior commit; report success |
| `COMMITTED_DERIVED_ARTIFACT_STALE` | Archive move committed; do not move it back; run `rebuild-index`, validate, then report |
| Any other error | Stop according to stable action |

Archive directories are terminal authority; INDEX is derived. Never create,
move, merge, overwrite, delete, or edit an archive directory or INDEX directly.
Use `doctor` when evidence is ambiguous or partial. It reports observations,
not actor or cause, and does not authorize repair unless its action proves the
documented recovery.

## Archive record recovery

When `rebuild-index` or a terminal result is blocked because an archive
directory lacks terminal records (missing terminal status, machine evidence,
or INDEX row), the only supported repair is `repair-archive-record`; manual
edits stay forbidden:

1. Run the readonly preflight `repair-archive-record <directory-name>`. Report
   its `missing` list and print both labeled `evidence` digests.
2. Stop for explicit user confirmation of the terminal status and a single-line
   summary. Never infer either from prose or history.
3. Execute with `--terminal-status`, `--summary`, and both
   `--expected-proposal-sha256` / `--expected-tasks-sha256` digests from the
   same preflight. Digest drift, a status that disagrees with the directory
   suffix, or an existing different terminal status fails closed without
   writing; follow the returned action.
4. When only the summary is missing, `rebuild-index --directory <name>
   --summary <text>` completes the derived INDEX the same way.

Repair fills only missing fields and never moves directories. Rerun
`validate-index` and `doctor` afterwards and report the result.

## Legacy format reconstruction

The normal parser never falls back to tolerant reconstruction. Use the
following procedure only when a stable action names the recovery command.

For active proposals:

1. Run `repair-proposal-format <short-name>` without `--apply`. Optional
   `--type`, `--scope`, and repeated `--acceptance` values may supply only
   fields listed in `projection.required_inputs`; they must not override
   existing evidence.
2. A `no-op` disposition succeeds without writing. A blocked registered
   format with required inputs stops for exactly those values. Any issue or
   unregistered format follows its action and is not guessed.
3. For `ready`, report the four source/candidate Markdown digests and stop for
   explicit confirmation. Apply only with `--apply` plus matching
   `--expected-proposal-sha256`, `--expected-tasks-sha256`,
   `--expected-candidate-proposal-sha256`, and
   `--expected-candidate-tasks-sha256`.
4. Require `committed: true`. The result is a Schema v2 draft and is not
   approved; wait for a new `開始實作` before implementation.

For archived records, first run `repair-archive-record <directory-name>` with
any required `--type`, `--scope`, repeated `--acceptance`, and
`--recovery-summary` inputs. Reconstruction apply uses the ordinary terminal
status, summary, and source Markdown digests plus all candidate digests and the
reported `recovery_timestamp`. If an original metadata file exists, also
confirm its `source_digests[".sdd/metadata.json"]` with
`--expected-metadata-sha256`. The operation stays in place, writes a
recovery-only JSON record, and rebuilds INDEX. It never creates managed
`terminal` evidence and never runs or requests the archived proposal's old
project tests.

Both apply paths store raw originals and candidates below target-local
`.sdd-recovery/<operation-id>/` with private permissions. Reports expose
digests and structured fields, not bodies. `RECOVERY_STAGED_STATE` means a
prior apply did not commit: repeat the same confirmed operation to resume, or
use `--restore-operation <operation-id>` explicitly. Restore is rejected once
current bytes prove a later lifecycle mutation. Do not delete recovery copies
or manufacture a replacement receipt.
