# Cut single-status authoring

## Date

2026-08-18

## Question and design

Decide whether Agent proposal and revision authoring should replace
`validate → status` with one strict `status`. The candidate retained the
public `validate` command and all runtime, schema, parser, approval, and
mutation contracts.

The comparison is `paired-cost-v7`: frozen v1.1.3 package baseline versus the
single-status candidate on Codex CLI `0.147.0` and Claude Code `2.1.234`. It is
a Skill-vs-Skill non-inferiority experiment using the existing three scenarios
and three replicates per Agent/task cell.

## Evidence integrity

- All 18 randomized pairs and 36 slots were valid on attempt 1; no valid
  failures were replaced.
- All command events were attributable, and candidate Critical Violations were
  `0/18`.
- Specification SHA-256:
  `dce516ad09e8e4055e8a209b125e538fa849498247a776b9d1f1c3aaea766011`.
- Runner SHA-256:
  `eb2f3ae9021e2f50e75692aa02aa530d9cc1b92b56f6a3c04987d0cc0e937849`.
- Baseline and candidate package tree SHA-256:
  `f92d4d54e01dba0c66500d9ff383f936ee282430788eb961efd37701308d9d99`
  and `01cbc92d8b1b36c84c9d52f66650ff50093b5e849b70eb40fa1255c87064e288`.
- Detailed cell and phase evidence is in
  [`docs/cost-benefit.md`](../cost-benefit.md); raw evidence and aggregate
  summary remain under `eval-runs/cost-benefit-v7/` and
  `eval-runs/cost-benefit-v7-summary.json`.

Claude could not authenticate in isolated temporary homes. Both Claude arms
therefore used the same authenticated current-user context, with an explicit
prompt requiring the workspace Skill. This limitation was frozen before
formal collection; no credentials were copied or modified.

## Registered conditions

| Condition | Observation | Result |
| --- | --- | --- |
| CLI strict diagnostic and read equivalence | deterministic fixture tests passed | pass |
| Candidate Critical Violations | `0/18` | pass |
| Candidate task success not below baseline | `15/18` versus `14/18` | pass |
| Every proposal/revision phase has exactly one fewer runtime invocation | three Claude phases were delta `0` | fail |
| Candidate proposal/revision median `validate` calls | `0` in every registered phase | pass |
| Every cell token and wall median is at most baseline +10% | all six cells passed both limits | pass |
| Tool-call median decreases in at least four of six cells | decreased in `4/6` | pass |

The exact phase-delta condition is binding. Claude reduced `small-bug`
proposal authoring from three runtime calls to two, but its `medium-feature`
proposal and both `acceptance-change` authoring phases remained unchanged.
The baseline did not consistently execute the redundant `validate` call, so
removing that instruction did not produce the registered deterministic saving.

## Decision

**CUT single-status authoring.** Restore the v1.1.3 Skill and documentation
behavior that explicitly runs `validate` before the authoritative `status`
read. Keep the public CLI unchanged.

Retain the CLI equivalence regression, experiment harness command accounting
and environment classifier improvements, frozen v7 specification, aggregate
and raw evidence, and this decision. They do not alter production authoring
behavior.

## Sensitive-data review

- [x] No credentials or authentication tokens are retained.
- [x] No isolated-home credential copy or mutation was performed.
- [x] No full user transcript, customer data, or personal source content is
  included in this record.
- [x] Commands, hashes, aggregate metrics, and artifact locations are safe to
  retain in the repository.
