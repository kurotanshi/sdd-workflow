# Keep Gate 2 Candidate A

## Date

2026-08-14

## Versions

- Engine: `1.1.1` (compatible generation `1.1`)
- Skill: frozen commit `64c6a7af46995a9c65180f93d7ae8b4f02ebed4d`
- Experiment: `paired-cost-v4`, 36 valid measured runs
- Environment: Codex CLI `0.147.0` with `gpt-5.6-sol`; Claude Code
  `2.1.232` with `sonnet`; macOS Darwin 24.6.0 arm64; Python `3.13.0`

## Question and gate

Decide whether to keep Candidate A: successful `approve` and `complete-task`
results include canonical after-state, the next snapshot, and the next pending
task so the Skill can chain active mutations without a separate `status` call.
Snapshot and task-digest inputs remain required.

The frozen keep rule requires every item below to pass:

1. locking-equivalence and retry regressions pass;
2. Skill Critical Violations are zero;
3. Skill task successes are at least the v3 Skill baseline of `14/18`;
4. median Skill runtime invocations and tool calls per completed task are both
   below v3; and
5. at least one registered cell-level cost metric decreases in at least four
   of the six Agent/task cells.

The v4 Skill-control gap is recorded for Gate 0 but is not a Candidate A cut
condition because that gap existed before the candidate.

## Evaluated scenarios

- `approve` and `complete-task` after-state equality with an immediate
  canonical `status` result.
- Chained snapshot use, concurrent-change rejection before mutation, and
  unchanged operation identity / `ALREADY_APPLIED` retry behavior.
- Two isolated host Agents across `small-bug`, `medium-feature`, and
  `acceptance-change`, three randomized pairs per cell.
- Per-phase runtime, tool-call, token, and wall-time comparison against the
  frozen `paired-cost-v3` baseline.

## Observed evidence

The detailed frozen identities, phase table, task outcomes, and raw-artifact
locations are in [`docs/cost-benefit.md`](../cost-benefit.md). The registered
inputs are in
[`evals/cost-benefit/experiment-v4.json`](../../evals/cost-benefit/experiment-v4.json).

| Pre-registered condition | Observation | Result |
| --- | --- | --- |
| Locking and retry regressions | after-state/status equality, stale snapshot, operation identity, and lost-response retry tests pass | pass |
| Skill Critical Violations | `0/18` Skill runs | pass |
| Skill task success | `16/18`, versus required `14/18` | pass |
| Runtime invocations per completed task | median `5 → 3`; all six cells decreased | pass |
| Tool calls per completed task | median `9.25 → 7`; all six cells decreased | pass |
| Registered cell-level costs | extra calls decreased in `6/6` cells, token overhead in `5/6`, wall overhead in `4/6` | pass |

All 18 pairs and 36 variant slots were valid on attempt 1. The independent
four-run smoke matrix also passed with zero Critical Violations. Frozen Skill,
runtime, runner, fixture, and specification hashes matched after collection.

Contrary evidence is retained: absolute v4 Skill-control overhead still
exceeds every Gate 0 limit in all six cells, so the aggregate summary remains
`runtime_acceptable: false`. Task-success asymmetry also remains concentrated
in `acceptance-change` (Claude control `0/3`; Codex Skill `1/3`). These facts
block no Candidate A criterion but remain material to the overall runtime
decision.

## Rejected alternatives

- **Cut Candidate A:** rejected because every pre-registered cut condition
  passed; cutting after observing the result would replace the registered rule
  with a stricter post hoc control comparison.
- **Remove or relax snapshot inputs:** rejected and not evaluated. Candidate A
  preserves stale-context rejection and retry identity; the experiment does
  not justify a weaker mutation boundary.
- **Combine discovery simplification:** rejected for this decision. Candidate
  B changes a different trust boundary and requires its own isolated proposal
  and measurement.

## Decision

**KEEP Candidate A.** Retain the self-describing `approve` and
`complete-task` results and the Skill's chained-snapshot implementation loop.
The candidate lowers the measured approval hot-path cost without weakening the
tested locking and retry behavior, while safety and Skill task success meet the
registered non-regression floors.

This is a candidate-level decision, not a Gate 0 runtime-acceptability finding.
The remaining Skill-control gap stays open for separate roadmap decisions.

## Rollback boundary

Candidate A's runtime, tests, Skill, and contract-document changes are frozen
together at commit `64c6a7af46995a9c65180f93d7ae8b4f02ebed4d`. Revert that unit only if a
future regression violates after-state equality, stale-write rejection,
operation identity, or lost-response retry behavior. Measurement artifacts and
this decision record remain evidence and do not roll back with runtime code.

## Follow-up

- Keep Gate 0 reporting separate from Candidate A's passed non-regression
  rule.
- Evaluate any discovery-round-trip candidate independently; do not bundle it
  with snapshot or transition changes.
- Re-run a frozen paired experiment if host/model versions or scenario inputs
  change before using these numbers for another decision.

## Sensitive-data review

- [x] No full user transcript is stored by default.
- [x] Project names, repository paths, source snippets, credentials, personal
  data, and customer data are removed or replaced with stable neutral labels.
- [x] Commands and links contain only information safe to retain in this
  repository.
- [x] When raw evidence cannot be safely retained, the record contains a
  de-identified summary and a minimal synthetic reproduction instead.
