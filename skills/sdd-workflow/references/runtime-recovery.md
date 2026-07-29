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
