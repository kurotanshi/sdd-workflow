# Demand-driven refinement intake

Status: complete; no refinements scheduled
Date: 2026-07-24

## Entry evidence

- Gate 0 published 36/36 valid paired results and fixed cost/safety thresholds.
- Gate 1 reduced the public surface to one Skill product and three public
  version concepts.
- Gate 2 retained the current runtime, rejected unsupported simplification
  claims, and separated the measured reapproval bug into its own Fix draft.

Gate 3 does not modify the Skill, runtime, references, schema, trigger
description, or eval matrix.

## Intake requirement

A refinement can be scheduled only when one evidence record contains all five
fields:

| Field | Required evidence |
| --- | --- |
| requester | A named real user or team that encountered the gap |
| unmet need | An observed task they could not complete or completed with material friction |
| expected benefit | A specific user-visible outcome, not a file or mode to add |
| owner | A maintainer accountable for implementation and removal |
| regression evidence | A reproducible failing case plus the minimum cross-Agent scenarios |

An idea in a roadmap, review, or model-generated recommendation is not a named
request. Missing any field keeps the item in demand-only backlog. Different
behavior changes require separate intake records and separate Fix proposals.

## Candidate checks

| Candidate | Evidence found | Intake result |
| --- | --- | --- |
| Ask before approving a draft after plain `實作` | Already required in `SKILL.md`, README, scenario B, and fresh-session adoption evidence; no unmet behavior remains | not a new feature |
| Authoring limits (1–3 reason paragraphs, 3–7 tasks, 3–8 scenarios) | Current authoring reference requires independently verifiable tasks, observable acceptance, and at most 10 pending tasks; friction log and usability evidence contain no named user blocked by length | backlog; no requester or failing case |
| Fresh-session/context-compression recovery | Scenario G already verifies authoritative fresh-session resume. No retained friction entry, named requester, or reproducible context-compression failure exists | backlog; fresh-session behavior exists, compression gap unproven |

None of the three has all five intake fields. The first is existing behavior;
the other two are design suggestions without field demand.

## Demand-only backlog

| Item | No-op reason | Reopen only when |
| --- | --- | --- |
| Numeric authoring limits | No named user, failed proposal, or measured quality gain | A named user supplies an over/under-sized proposal failure and owner |
| Context-compression recovery | No reproducible failure beyond the already-covered fresh-session resume | A retained compression reproduction fails authoritative resume |
| Exploration/analysis mode | Agents already inspect code; broad “analysis” language risks false triggers | A named user needs an SDD-specific artifact and accepts explicit invocation only |
| Additional Agent adapters | Claude Code and Codex are the supported evidence set | A named host user and maintainer owner provide a loading/test environment |
| English schema aliases | No user report that the Traditional Chinese artifact headings block use | A named user supplies affected artifacts and migration expectations |
| Semantic proposal review | No agreed failure definition or deterministic acceptance evidence | Repeated named-user proposal defects share one observable pattern |
| Type-specific authoring guidance | No type-specific failure sample | A named user supplies a failing type and expected authoring outcome |
| Separate reporting reference | Existing Skill reporting rules have no recorded gap | A named user shows repeated inconsistent handoffs not covered by current rules |

Backlog presence is not a release promise. No Skill, reference, schema, mode,
or test matrix is added for these items.

## Proposal creation result

No Gate 3 candidate passes intake, so Gate 3 creates no Fix proposal. The
separate `fix-authorized-revision-reapproval` draft came from a measured Gate 0
correctness failure and the Gate 2 safety analysis; it is not evidence that a
Gate 3 UX or authoring request exists.

## Regression responsibility

Any future behavioral refinement that passes intake must include one fresh
pass for scenarios B, D, J, H, and M on both Claude Code and Codex. A complete
13-scenario matrix is reserved for a major host change or a risk that the five
scenarios do not cover.

The existing `fix-authorized-revision-reapproval` draft now carries this
minimum cross-Agent responsibility in addition to deterministic invariant
tests. No Gate 3 backlog item receives tests before it passes intake.

## Existing behavior audit

Two proposed “improvements” are already canonical behavior:

- Proposal step 3 requires reporting the canonical short name, type, behavior,
  task count, and acceptance scenarios after validation.
- Implementation step 7 requires reporting each completed task and validation,
  then repeating one task at a time until full completion or a defined stop.

Neither is added to a roadmap or proposal. A future formatting example would
still need a named inconsistency report; it would not create the underlying
summary or progression behavior.

## Trigger freeze

- The canonical `SKILL.md` SHA-256 remains
  `3ecc09d8130dabd4ed48c74a342e528b0523404ececd22f4fc5caa23646c2e83`.
- `tests/trigger-contract.sh` passes, and `skills/sdd-workflow/` has no diff.
- No natural-language trigger was added or widened in Gate 3.
- If an exploration mode ever passes demand intake, it may be invoked only as
  explicit `$sdd-workflow 分析`; the word `分析` alone must never trigger it.
- Every demand-only backlog item still requires a named requester and the
  other four intake fields before scheduling.

## Final decision

Gate 3 closes as a no-op. It schedules zero refinement proposals, retains
eight demand-only backlog items, and records two suggestions as behavior that
already exists. The Gate 2 `fix-authorized-revision-reapproval` draft remains
a separate measured correctness fix, not a Gate 3 refinement.

No Skill, runtime, reference, artifact schema, trigger description, or eval
matrix changed for Gate 3.
