# Runtime simplification decision

Status: complete; runtime simplification no-op
Date: 2026-07-24

## Evidence integrity

The decision uses the pre-registered `paired-cost-v2` experiment in
[`docs/cost-benefit.md`](../cost-benefit.md).

- 36/36 planned results exist, are valid, and completed on attempt 1.
- Every result records source commit
  `21fb26bc329743202a19bdd969e049b04c2481c2`.
- Every result records spec SHA-256
  `abd4f2e29409722786b8803129014a49f412b527ef4d79e5bbccd8b6b62606f5`.
- Runner and entrypoint hashes remain
  `55c68cc300ba43df5530be0ba232c74f0ad08de46e834fc1480840bf69ffde2b`
  and
  `ab0af5de13ce3458a8cc9a3a8e7c4da690471547abced2886bd938a8e691118a`.
- The small-bug, medium-feature, and acceptance-change fixture hashes remain
  `3ac1755430a8224c60771a6c50374acac5a232da7b459d33c3098e7ff7983414`,
  `97fc93d1a5abc37c28bca3206be7bf865ad00942afbc12a49462a6f29156317f`,
  and
  `4a56dc9f28853fe62855bc94b189a160a1c94bda1204ac1e03f0576696841a0f`.
- Gate 1 changed documentation and related assertions only.
  `skills/sdd-workflow/` has no worktree diff.

The v1 invalid-classifier artifacts remain excluded. Gate 2 does not change
the registered thresholds, recalculate invalidity, or substitute later Agent
runs.

## Entry decision

The pre-registered entry condition is: at least one cost limit must be
exceeded by both Agents in at least two task types.

| Task | Claude Code | Codex | Jointly over budget |
| --- | --- | --- | --- |
| small bug | yes | yes | yes |
| medium feature | no | yes | no |
| acceptance change | yes | yes | yes |

`small-bug` and `acceptance-change` satisfy the joint condition. Gate 2 is
therefore **open**. The result permits evaluation of a smaller runtime path; it
does not authorize a rewrite or weaken an approval boundary.

## Cost-to-path diagnosis

### High-frequency round trips

Across three Skill replicates per cell, the traces contain:

| Agent/task | discovery | list | status | approve | complete-task | begin-revision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Claude/small bug | 6 | 5 | 15 | 3 | 6 | 0 |
| Codex/small bug | 12 | 12 | 34 | 6 | 6 | 0 |
| Claude/acceptance change | 12 | 11 | 26 | 6 | 6 | 3 |
| Codex/acceptance change | 24 | 24 | 66 | 12 | 12 | 6 |

The exact counts include Agent retries of read-only commands, so they are
diagnostic rather than a required sequence. They nevertheless match the paired
cost result: +18 to +34 median tool calls in the two jointly over-budget task
types.

The concrete sources are:

- package discovery at the start of each fresh host turn;
- `list` followed by `status` to select and inspect the only proposal;
- another fresh `status` before every mutation to obtain snapshot/task
  identity;
- separate `approve`, `complete-task`, and post-mutation `status` processes;
  and
- repeated parsing and JSON transport at every process boundary.

The safety reason for fresh evidence is valid. The cost is the number of Agent
round trips needed to obtain and then immediately consume that evidence.

### Revision/reapproval blocker

All six Skill acceptance-change runs followed the revision boundary without
editing product code, then failed reapproval with:

```text
OUT_OF_BAND_DRIFT
action: inspect_managed_state_drift
```

The path is `sdd_core.transitions.approve_proposal` through
`_prepare_approval_targets`. An open revision carries the prior attestation;
reapproval compares that attestation with the intentionally revised canonical
model and classifies newly appended pending tasks as unauthorized drift. The
runtime therefore cannot distinguish the authorized revision delta from an
out-of-band managed-field edit.

This is not only ceremony cost. It explains the Skill's 0/6
acceptance-change completions and is the highest-priority correctness path.

### Optimistic locking and metadata

Snapshot comparison itself remains useful: it rejects stale caller context at
low implementation cost. The measured overhead comes from acquiring a fresh
snapshot in a separate status call before each mutation, not from hashing
bytes. A candidate should therefore combine evidence acquisition and mutation
without removing stale-context rejection.

Discovery handshake/capability metadata contributes repeated process and
prompt work but did not independently cause a measured task failure.
Approval/attestation metadata did cause the revision blocker above. Other
multi-axis metadata has no isolated cost attribution in this experiment and
must not be removed merely because it has a protocol-era name.

## Safety invariants and regression map

| Invariant | Existing evidence | Non-negotiable gap or candidate obligation |
| --- | --- | --- |
| Initial approval | `test_approval`, `test_complete_task`, adapter scenario B, trigger contract | No product mutation before explicit approval; any combined command must still prove approved canonical input |
| Revision and reapproval | `test_complete_task.test_authorized_revision_can_be_reapproved_with_new_attestation`, transition retry tests, acceptance-change scenario M | **Gap:** existing success test does not change approval-relevant fields. Add a pending task and changed acceptance, reapprove successfully, and reject unapproved edits |
| Canonical task identity | parser/schema/scanner tests and complete-task ordinal, digest, manifest, and attestation tests | A combined completion path must select one ordered canonical task and reject stale text, ordinal, or snapshot |
| Completed archive | terminal validation, archive CLI, transaction-failure, concurrency, and recovery-drill tests | Preserve full-completion gate, directory-move commit point, collision handling, and no reverse move after derived INDEX failure |
| Confirmed abandonment | preflight, terminal validation, transition-failure, trigger contract, and Agent scenario J tests | Preserve read-only preflight, exact user confirmation, fresh evidence, retained code/Git, and terminal retry semantics |
| Stale mutation rejection | complete-task stale-snapshot tests, terminal stale tests, transition failure injection, and concurrency tests | A lower-round-trip API must acquire and consume evidence atomically or reject a changed artifact before mutation |

The revision gap explains how 249 tests could pass while every measured Skill
acceptance-change run failed. It must be added before or with any candidate;
coverage count alone is not an acceptance argument.

## Candidate evaluation

Candidates are evaluated in the registered order.

### A. Self-describing existing mutation results

`approve` and `complete-task` already compute an after snapshot. Extend their
existing JSON results with the canonical after state and next pending task so
the Skill can treat a successful result as authoritative evidence instead of
immediately running another `status`. The returned snapshot remains the
expected input for a later mutation, which still rejects intervening changes.

This targets the measured high-frequency path without a new parser, command,
archive model, or lock. It is safe in principle only after tests prove all six
invariants and the Skill removes exactly the now-redundant reads.

### B. Fold package verification into the first CLI command

The package-local command could verify its own identity/capability envelope and
include that evidence in the first ordinary result, eliminating a separate
`discover-runtime.py` process per fresh host turn. This targets 2-turn and
4-turn workflows directly.

It changes the current discovery trust boundary and has no candidate-level
failure-injection design yet. Keep it behind candidate A; do not combine both
changes in one proposal.

### C. Simplify optimistic locking

Reject as a removal candidate. The current snapshot already consists of file
hash evidence, and stale rejection is covered by concurrency and terminal
tests. Replacing it with another file hash does not reduce a round trip.
Removing expected evidence would weaken stale-context safety.

### D. Remove protocol-era metadata

- Removing approval attestation is rejected because it protects managed fields
  and terminal state. Its revision comparison needs a correctness fix, not
  wholesale removal.
- Removing discovery capability/version fields has no isolated cost estimate
  in Gate 0.
- Removing handshake, manifest, or compatibility axes by name alone would
  reduce lines but has no measured task-level benefit.

These remain no-op unless a later experiment isolates a field's cost and
proves equivalent failure behavior.

Parser rewrite, archive-model change, and total-line targets are explicitly
not candidates.

## Savings and synchronization cost

The most favorable deterministic call estimate is:

| Workflow | Candidate A maximum | Candidate B maximum | Combined maximum |
| --- | ---: | ---: | ---: |
| two-turn, two-task small bug | 3 calls | 2 calls | 5 calls |
| four-turn, four-task acceptance change | 6 calls | 4 calls | 10 calls |

Candidate A counts one post-result status after each approval and task
completion. Candidate B counts one required discovery per host turn. The
estimate does not claim that token or wall-time savings are proportional.

Even the disallowed combined change leaves the measured median additional
calls above the registered limit:

| Cell | Measured extra calls | Best combined residual |
| --- | ---: | ---: |
| Claude/small bug | 25 | at least 20 |
| Codex/small bug | 18 | at least 13 |
| Claude/acceptance change | 34 | at least 24 |
| Codex/acceptance change | 23 | at least 13 |

Neither candidate can be shown to reach the `≤ 4` call threshold, and Gate 0
does not support a credible `≤ 40%` token or `≤ 35%` wall-time projection.

Candidate A would synchronize at least the Skill command rules, CLI result
projection, transition results, CLI documentation, and invariant tests.
Candidate B additionally changes discovery, runtime identity/handshake,
failure recovery, and package tests. Combining them would be a broad redesign,
not a minimum candidate.

The runtime simplification decision is therefore **no-op**: retain the current
runtime until a smaller experiment demonstrates a candidate that can meet cost
and safety conditions. This is distinct from the measured reapproval bug. That
bug has a direct correctness case and qualifies for its own Fix proposal
without claiming it simplifies the runtime.

## Final decision

- **Runtime simplification:** no-op. Keep the current implementation and do
  not start candidate A or B.
- **Correctness follow-up:** draft the independent
  `fix-authorized-revision-reapproval` proposal. Its scope is the demonstrated
  authorized-revision defect and missing regression only.
- **Excluded:** parser rewrite, archive-model change, snapshot removal,
  capability/attestation deletion, or a line-count target.

This Gate 2 stage modifies no file under `skills/sdd-workflow/`. The Fix
proposal remains a draft and needs explicit approval before implementation.
