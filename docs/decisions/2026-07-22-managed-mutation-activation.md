# Managed mutation activation

## Date
2026-07-22

## Versions
- Engine: `0.4.0` candidate
- Skill: managed-mutation candidate built from the v0.3 readonly path
- Environment: Codex CLI `0.145.0`, Claude Code `2.1.217`, CPython 3.11+, macOS arm64

## Question and gate
Decide whether the formal Skill may switch approve/revision, task completion, and terminal transitions from prose edits to the v0.4 command group. The gate requires both tools, in fresh sessions, to use the command-owned state path, preserve the approval boundary, stop on errors, and leave machine evidence that `doctor` can validate. A failed path keeps the complete group inactive; the repository does not ship a hybrid workflow.

## Evaluated scenarios
- Approve a synthetic draft, implement one task, validate it, and complete it with snapshot and task identity.
- Revise an approved proposal, invalidate its approval through `begin-revision`, edit only proposal semantics, and stop in draft for renewed approval.
- Archive an approved proposal with all tasks complete, commit the directory move, rebuild INDEX, and validate the result with `doctor`.
- Exercise stale snapshot, task identity, attestation drift, pre/post commit interruption, and terminal retry outcomes through the deterministic unit and failure-injection matrix.

## Observed evidence
- Fresh Codex CLI `0.145.0` sessions called `status`, `approve`, `complete-task`, `begin-revision`, and `archive`. The implementation fixture finished 1/1, the revision fixture stopped in draft with invalidated approval evidence, and the archived fixture had no doctor findings.
- Fresh Claude Code `2.1.217` sessions produced the same managed implementation, revision, and archive states. The implementation metadata records `complete-task`; the revision metadata records `begin-revision`; terminal metadata records the committed `archive` operation and its source snapshot. Post-archive `doctor` returned `healthy: true`.
- Both tools preserved the one-task implementation file as exactly `managed-pilot` plus one trailing newline. Neither fresh revision session implemented the revised proposal before renewed approval.
- Automated terminal tests cover summary transport, dry-run byte/mode/mtime invariance, collision versus committed retry, `COMMITTED_DERIVED_ARTIFACT_STALE`, and injected failures before and after metadata, status, move, and INDEX replacement.
- `F-20260722-05` records one harness invocation mistake. It occurred before a prompt reached Claude Code and did not exercise or bypass the workflow; the corrected invocation completed without workflow intervention.

Raw session transcripts and temporary repository paths are intentionally not retained. The observations above were checked against synthetic artifacts and operation evidence during the gate.

## Rejected alternatives
- Activate only approve/task completion while retaining prose archive: normal terminal work would then look like out-of-band drift and make the milestone internally incoherent.
- Keep all v0.4 commands experimental despite the passing gate: this would preserve the repeated mutation/verification cost in `F-20260722-04` without adding evidence.
- Claim that attestation proves which actor changed a file: attestation only compares managed state and cannot identify an author or intent.

## Decision
`GO` for the coherent v0.4 managed mutation group: approve/revision, task completion, archive, and abandon become the formal Skill paths together. The CLI remains non-interactive and the Skill remains responsible for semantic approval, implementation, validation, summaries, and stopping on machine actions.

## Rollback boundary
Pinning `v0.3.0` is safe only for proposals that have no v0.4 machine metadata. A managed in-flight proposal must be completed or abandoned with the v0.4 engine before pinning, or await an explicit migration decision; deleting `.sdd` metadata is not a supported downgrade. Roll back or open a new decision if fresh-session checks show repeated command bypass, material completion-rate regression, or an unrecoverable machine-state failure not covered by `doctor`.

## Follow-up
- Keep managed mutation scenarios in the release acceptance matrix for every behavior-generation change.
- Record new command friction in `docs/friction-log.md`; do not add `recover` or locking without repeated evidence and a separate decision.

## Sensitive-data review
- [x] No full user transcript is stored by default.
- [x] Project names, repository paths, source snippets, credentials, personal data, and customer data are removed or replaced with stable neutral labels.
- [x] Commands and links contain only information safe to retain in this repository.
- [x] When raw evidence cannot be safely retained, the record contains a de-identified summary and a minimal synthetic reproduction instead.
