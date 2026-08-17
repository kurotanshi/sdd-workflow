# Cut Gate 2 folded package verification

## Date

2026-08-17

## Question and design

Decide whether to keep a complete Skill package that verifies its manifest,
script digests, Skill digest, and resolved runtime root before importing the
CLI, then includes verified runtime evidence in CLI output v2. The candidate
removes the separate discovery command from each fresh Skill phase while
leaving `discover-runtime.py` and discovery envelope versioning unchanged.

The comparison is `paired-cost-v6`: frozen `skill-v4` baseline versus the
folded-verification `skill-v5` candidate on Codex CLI `0.147.0` and Claude Code
`2.1.233`. It is a Skill-vs-Skill non-inferiority experiment. v4's control
overhead remains the separate Gate 0 record and was not remeasured.

## Evidence integrity

- All 18 randomized pairs and 36 slots are valid and completed on attempt 1.
- Specification SHA-256:
  `9a0178c42ce3fea3e62c830c72f89b926e9abb0501fa801303f2fb1960f970da`.
- Runner SHA-256:
  `0f2a24d9716f1f4b891f50bb1136c25bc9ccf28b7bfb174349aa7957a1fd13af`.
- Baseline and candidate package tree SHA-256:
  `4645d55f869e90da4e0eb1e12240cd08bec47d2a168e3b77dad9a661c9703c6c`
  and `2b228c4c6dec1d266c9eeae3d0e6d23b339b1f6ee01a9dcaaea620693159479c`.
- The detailed cell and phase tables are in
  [`docs/cost-benefit.md`](../cost-benefit.md); raw evidence and aggregate
  summary remain under `eval-runs/cost-benefit-v6/` and
  `eval-runs/cost-benefit-v6-summary.json`.

`paired-cost-v5` is explicitly excluded. Its 18 Claude slots were revoked-token
HTTP 401 host failures that an incomplete classifier initially accepted. The
classifier correction has an exact regression test, and the corrected
collection received a new experiment identity rather than reusing v5.

## Registered conditions

| Condition | Observation | Result |
| --- | --- | --- |
| Failure-injection equivalence | package/bootstrap tests passed before measurement | pass |
| Candidate Critical Violations | `0/18` | pass |
| Candidate task success not below baseline | `14/18` versus `14/18` | pass |
| Every Skill phase has exactly one fewer runtime invocation | three Claude phases were `0`; one Codex phase was `-2` | fail |
| Every cell token and wall median is at most baseline +10% | Claude token exceeded in two cells; Claude medium-feature wall exceeded | fail |
| Tool-call median decreases in at least four of six cells | decreased in `3/6` | fail |

The candidate therefore fails the registered keep rule even though safety and
task success are non-inferior. The one removed discovery call did not produce a
stable one-call phase reduction across both hosts, and the Claude cost
regressions exceed the allowed noise bound.

## Decision

**CUT folded package verification.** Revert the candidate runtime identity,
bootstrap, CLI output v2, discovery compatibility, and `SKILL.md` hot-path
changes as one unit. Retain the existing output v1 and separate package-local
discovery design.

The experiment runner's corrected host-environment classifier, frozen v5/v6
specifications, aggregate/raw evidence, and this decision are retained. They
do not alter runtime behavior.

## Sensitive-data review

- [x] No credentials or authentication tokens are retained.
- [x] The revoked-token failure is recorded only as a typed, de-identified
  host-environment condition.
- [x] No full user transcript, customer data, or personal source content is
  included in this record.
- [x] Commands, hashes, and artifact locations are safe to retain in the
  repository.
