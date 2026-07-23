# Schema v2 entry

## Date
2026-07-22

## Versions
- Engine: `0.4.0`
- Skill: `v0.4.0` managed-mutation path
- Environment: ten real roadmap proposals, four legacy archives, four evidence decisions, and the repository friction log

## Question and gate
Decide whether observed v1 limitations justify a minimal Schema v2. A `GO` requires repeated or structurally unavoidable information loss, a clear canonical/approval role for every new field, and evidence that parser adapters can absorb the format change without branching the transaction engine. It does not authorize speculative impacts, labels, or type-specific required-section matrices.

## Evaluated scenarios
- Classify packaging/runtime hardening and team-operation work with v1's three values: `新功能`, `修 bug`, and `重構`.
- Represent adoption, entry, and activation investigations as proposals whose terminal artifact preserves both the research question and conclusion.
- Pass v1 and a prospective explicitly versioned v2 model through the existing Approval Manifest and transaction contracts.
- Review archives and friction evidence for repeated missing impact metadata.

## Observed evidence
- `add-runtime-packaging-baseline` is recorded as `新功能`, while its work is runtime/package hardening; `harden-team-workflow` is recorded as `重構`, while its scope is team operations and CI. The v1 vocabulary forced both into an imprecise category (`F-20260722-06`).
- Four repository decisions now carry research-like questions and conclusions outside proposal artifacts. The three activation/entry investigations could not use the proposal lifecycle without either pretending to be implementation work or losing their conclusion at archive time (`F-20260722-07`).
- The v0.4 engine has processed active state, task completion, approval, and terminal synthetic pilots through one version-independent canonical model. Approval relevance is already explicit per field, so an adapter-only v2 remains testable without transaction-engine schema branches.
- Four legacy archives and all v1 roadmap proposals remain readable. No archive or friction entry demonstrates repeated missing migration/security/deployment/cross-service fields, so impacts have not met their independent gate.

## Rejected alternatives
- Keep overloading `新功能`/`重構`: this preserves bytes but loses useful primary classification in real operational work.
- Add only more type strings to v1: unversioned v1 readers would accept or misinterpret a format evolution without an explicit compatibility boundary.
- Add labels, impacts, or per-type mandatory sections now: current evidence does not identify a stable vocabulary or validation matrix.
- Give research a separate state machine: no evidence requires different draft/approved/completed/abandoned semantics.

## Decision
`GO` for a minimal Schema v2 containing explicit schema metadata, the six evidenced primary types, and a canonical research conclusion. Schema version and primary type are approval-relevant. The conclusion is presentation-only implementation/research output: completed research must contain it, but producing the answer does not invalidate the approved question, tasks, or acceptance conditions. Ordinary explanatory prose remains governed by the existing field policy. `NO-GO` for impacts, labels, or type-specific required sections.

## Rollback boundary
Existing v1 and legacy artifacts are never migrated in place. Before v2 becomes the default authoring path, both adapters and all v0.4 transitions must pass common-model fixtures. If transaction code requires a schema-version branch, or v1/archive reads regress, retain v2 fixtures as experimental and keep the Skill authoring v1. Once a v2 proposal is created, downgrade means using a v2-capable engine or an explicit migration—not removing its version marker.

## Follow-up
- Record concrete impact omissions in the friction log. Consider `add-impact-metadata` only after repeated cases establish vocabulary and required sections.
- Reassess whether optional labels are needed independently; this decision does not include them merely because the roadmap listed examples.

## Sensitive-data review
- [x] No full user transcript is stored by default.
- [x] Project names, repository paths, source snippets, credentials, personal data, and customer data are removed or replaced with stable neutral labels.
- [x] Commands and links contain only information safe to retain in this repository.
- [x] When raw evidence cannot be safely retained, the record contains a de-identified summary and a minimal synthetic reproduction instead.
