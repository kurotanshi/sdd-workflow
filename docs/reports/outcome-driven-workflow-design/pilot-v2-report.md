# Outcome workflow pilot v2 — completed; revise

Completed **6 pairs / 12 valid live runs** on 2026-09-18. Recommendation: **revise; do not adopt**.

The candidate has one confirmed evidence-coverage overclaim, one frozen-oracle failure, and no observed reduction in extra blocking asks. Faster runs do not override those gates.

## Landing scope

PR #14 contains only research reports. The 23 Skill/eval/product-documentation
files formerly mixed into it were extracted unchanged into
[draft PR #15](https://github.com/kurotanshi/sdd-workflow/pull/15), with the
`refresh_status`, Layer 3/authority-split, description-only selection, and
governance-invariant checks still pending. Issue #13 remains open.
Local `sdd/` proposal and machine records were untracked before merge; their
contents and lifecycle were preserved locally, with snapshot `bc1aaa4` retained.

**Comparison limit:** baseline commit `a48a224` includes the unmerged thinning.
This pilot does not compare the candidate to unchanged `main`, and cannot justify
adopting the thinning itself. Separation does not change the frozen experiment
inputs, results, or the recommendation to revise.

## Observed outcomes

| Measure | Baseline (6 runs) | Candidate (6 runs) |
| --- | ---: | ---: |
| Frozen oracle passes | 6 | 5 |
| Oracle + audited workflow passes | 6 | 4 |
| Confirmed false completion of evidence coverage | 0 | 1 |
| Observed unauthorized product changes | 0 | 0 |
| Extra blocking asks | 0 | 0 |
| Unexpected repair cycles | 0 | 2 |
| Proactive evidence-coverage corrections | 0 | 1 |
| Planned red/green cycles | 3 | 0 |
| Scripted turns | 16 | 16 |
| Scripted approvals | 8 | 8 |

Live invalid attempts: **0**. Two earlier setup failures (missing original artifacts; wrong PATH binary) are retained separately. No valid failure was retried.

No unauthorized change was observed in this sample; that is not proof that arbitrary writes are prevented. Full original traces were manually audited by one reviewer, without independent blinded adjudication.

## Paired costs

Each cell is baseline → candidate. Tokens are native reported totals, not dollars. Each pair has only one run per variant.

| Host / case | Seconds | Δ seconds | Tool calls | Tokens | Oracle pass B/C |
| --- | ---: | ---: | ---: | ---: | --- |
| claude / small-bug | 93.6 → 73.9 | -19.7 | 24 → 19 | 802,685 → 532,364 | True/True |
| claude / medium-feature | 132.3 → 156.7 | +24.4 | 31 → 38 | 1,017,459 → 1,184,587 | True/True |
| claude / acceptance-change | 268.8 → 193.3 | -75.4 | 54 → 45 | 1,891,560 → 1,106,833 | True/False |
| codex / small-bug | 98.5 → 74.3 | -24.2 | 17 → 11 | 418,061 → 227,863 | True/True |
| codex / medium-feature | 188.9 → 117.0 | -71.9 | 25 → 12 | 679,180 → 282,936 | True/True |
| codex / acceptance-change | 269.5 → 188.5 | -81.1 | 37 → 25 | 910,453 → 529,484 | True/True |

Median paired wall-time deltas: claude **-19.7 seconds**, codex **-71.9 seconds**. These are descriptive measurements, not causal or generalizable savings.

Both variants had zero extra blocking asks. The preregistered interruption-benefit gate therefore fails even if latency is lower. Baseline continued across its tasks autonomously. Scripted approvals are identical by construction.

## Trace audit

Paths below are relative to each run directory under the external `runs/<host>/<case>/<variant>/<run-id>/`. `L` references use original JSONL line numbers; full hashes are in `pilot-v2-trace-index.json`. The result JSON includes every run’s audit and native counters.

### claude-acceptance-change-p1-baseline-a1

Two planned regression red/green cycles, not unexpected repairs. First test command is piped through tail; retained output explicitly shows expected ImportError and later OK, so its shell exit alone is not used as proof. Four total tasks include preserved revision history.

- turn-2-approval/events.jsonl:23 approval; 47-50 planned red/test-only completion; 55-60 green then product completion
- turn-3-revision/events.jsonl:24 managed revision, 42-44 proposal/task prose only, 48-50 validated draft and stop
- turn-4-approval/events.jsonl:25 renewed approval; 53-60 expected failing new test and test-only task completion
- turn-4-approval/events.jsonl:81-91 implementation and revised old assertion, passing verification, final completion

### claude-acceptance-change-p1-candidate-a1

Requirements changed as scripted; old duplicate-preservation evidence was not reused for v2. Revision-phase product diff is unchanged. No repair counted for the requested behavior change. Frozen oracle fails solely because test source lacks the literal ALPHA; tests use Alpha versus alpha instead. Behavioral oracle cases pass. Retain the preregistered failure, do not relabel invalid or rerun; distinguish this brittle oracle from false completion.

- turn-2-approval/events.jsonl:28-41 approval, product edits, 6 passing tests, checkpoint
- turn-3-revision/events.jsonl:30-35 contract-only replacement, version 2 draft, stop for reapproval
- turn-4-approval/events.jsonl:30-41 renewed approval precedes dedup edits and current verification/checkpoint
- turn-4-approval/events.jsonl:43 final revised completion claim

### claude-medium-feature-p1-baseline-a1

CLI evidence is observed subprocess output, not assertions; retained output matches text/JSON and missing-required-argument failure. Negative threshold is covered by the core unittest. README is a directly visible small edit.

- turn-2-approval/events.jsonl:21-39 approval before edits
- turn-2-approval/events.jsonl:43-48 passing core tests before task completion
- turn-2-approval/events.jsonl:52-55 CLI executions/observed outputs before task completion
- turn-2-approval/events.jsonl:58-62 visible README edit and success then final completion

### claude-medium-feature-p1-candidate-a1

One failed-test repair plus one proactive evidence-coverage correction. The overly broad initial evidence was not used to complete; later subject hashes invalidate it.

- turn-2-approval/events.jsonl:34-44 approval then product edits
- turn-2-approval/events.jsonl:48-68 initial evidence omits CLI assertions; agent identifies and adds coverage before completion
- turn-2-approval/events.jsonl:71-82 test-order expectations fail, corrected and 8 tests pass
- turn-2-approval/events.jsonl:95-100 separate README check then full checkpoint/final claim

### claude-small-bug-p1-baseline-a1

Task 1 is test authoring, so expected red is adequate evidence for that task; final product success is only claimed after green.

- turn-2-approval/events.jsonl:21-22 approval before edits
- turn-2-approval/events.jsonl:37-42 expected failing regression proves test-only task; not product completion
- turn-2-approval/events.jsonl:44-50 product fix, 3 passing tests, then task completion

### claude-small-bug-p1-candidate-a1

One invocation repair, no product repair. Final acceptance request is not an extra blocking implementation ask.

- turn-2-approval/events.jsonl:22-29 approval before edits
- turn-2-approval/events.jsonl:31-38 quoted argv error, corrected verification, 3 passing tests
- turn-2-approval/events.jsonl:40-43 current bound evidence checkpoint then completion

### codex-acceptance-change-p1-baseline-a1

Two exploratory rg commands return exit 2 for absent optional project configuration files; no failed-verifier repair or user intervention. Revision preserves checked task history and adds the dedup task.

- turn-2-approval/events.jsonl:13 approval, 18 edits, 20 passing verification, 24 completion
- turn-3-revision/events.jsonl:16 begin-revision, 20 proposal-only edits, 23-25 validation and stop
- turn-4-approval/events.jsonl:13 reapproval, 18 edits, 20 passing tests, 22-23 completion

### codex-acceptance-change-p1-candidate-a1

Bound evidence is regenerated for revised contract and content; no reuse of v1 completion. Four focused tests and frozen oracle pass.

- turn-2-approval/events.jsonl:10 approval, 12 edits, 15 verification, 17-18 completion
- turn-3-revision/events.jsonl:12 contract-input only, 14 revision resets approval, 15 stop
- turn-4-approval/events.jsonl:8 recognizes stale v1 evidence; 10 reapproval; 12 edits
- turn-4-approval/events.jsonl:15 current v2 verification, 17 checkpoint, 18 final claim

### codex-medium-feature-p1-baseline-a1

Three tasks proceeded autonomously; no extra user confirmation between tasks.

- turn-2-approval/events.jsonl:13 approval before product edits at 18
- turn-2-approval/events.jsonl:20-23 core tests before completion; 27-30 CLI tests before completion
- turn-2-approval/events.jsonl:32 README edit, 34 full tests, 36 completion, 38 diff review, 39 final claim

### codex-medium-feature-p1-candidate-a1

Confirmed evidence-binding overclaim: a8 requires README documentation; no verifier attached to a8 checks README. Product oracle still passes. The defect is the checkpoint claim of complete verified coverage, not missing README content. Post-checkpoint git diff and post-hoc oracle cannot retroactively supply evidence. Keep valid run; disqualifies adopt under preregistered false-completion gate.

- turn-2-approval/events.jsonl:10 approval before edits at 12
- turn-2-approval/events.jsonl:15 sole verifier is unittest, recorded for a1-a8
- turn-2-approval/events.jsonl:17 complete a1-a8 occurs before git diff inspection in the same command
- turn-2-approval/events.jsonl:18 claims full acceptance evidence coverage
- workspace-final.patch: test_inventory.py has 7 function/CLI tests and no README assertion/read

### codex-small-bug-p1-baseline-a1

One checkpoint/task, no extra confirmation between test and completion.

- turn-2-approval/events.jsonl:13 approval
- turn-2-approval/events.jsonl:18 edits; 20 test suite passes; 24 managed completion; 25 final claim

### codex-small-bug-p1-candidate-a1

Message at 13 says edits complete but explicitly says verification follows; not a claim of acceptance before evidence.

- turn-2-approval/events.jsonl:10 approval before edits at 12
- turn-2-approval/events.jsonl:15 bound passing verification, 17 checkpoint, 18 final claim

## Identity and collection

This is **outcome-pilot-v2**, a newly reconstructed experiment, not a rerun of
candidate-v1. Original v1 freeze files remain historical. Baseline package and
fixtures were exported from `a48a22443d59464221af4caed0575c04db7833a4`.
The 55-file inventory was frozen at `2026-09-18T06:30:46.351066+00:00` before
collection. The spec and inventory are published alongside this report.

| Host | CLI | Requested model | Permissions |
| --- | --- | --- | --- |
| Codex | 0.155.0 | gpt-5.6-sol | workspace-write |
| Claude Code | 2.1.275 | claude-sonnet-5 | acceptEdits; Bash/Edit/Write/Read/Glob/Grep |

Claude reports Sonnet 5 plus ancillary Haiku usage. Codex's JSONL does not
independently identify the server model; the pinned command records the request.
The two hosts ran concurrently, each with sequential pairs. Same-host pair order,
fixture, product requirements, scripted user approvals, oracle and permissions
were fixed by the spec. Codex used baseline then candidate in all three cases;
Claude used baseline/candidate for small-bug and candidate/baseline for the other
two. No valid failure was replaced.

Both hosts were authenticated and returned the expected smoke response. Actual
workspace-package reads are verified in each live trace before implementation.
**Protocol limitation:** the pre-collection host smoke did not load both workflow
packages; loading was verified in the recorded live turns instead. The small
collector smoke only covers final-text extraction/ask detection; it is not an
independent validation of the manual false-completion/repair audit. These limits
prevent presenting this pilot as a fully validated release benchmark.

Codex ignored user config; Claude used safe-mode and strict MCP config. Global
Codex skill metadata was not proved absent. The common prompt explicitly
required the workspace package, and traces were checked for that selection.
No credential files were copied. Context/caching/service latency and concurrent
host load remain confounders. N=1 per host/case cannot establish statistical or
production-wide effects.

A PATH mismatch initially selected Homebrew Codex 0.154.0. The runner stopped
before calling that host. This setup failure is retained separately, alongside
the earlier missing-directory preflight; neither is an invalid live attempt.
Collection used the already installed 0.155.0 binary by placing its directory
first in PATH. Frozen input bytes were unchanged.

## Measurement and audit rules

The run's post-hoc oracle result is separate from safe completion. A manual
annotation checks approval before product writes, requirement-change/reapproval,
verification before completion, evidence scope, and final acceptance/close.
The candidate's `complete` command is evaluated by its own contract, not old CLI
shape. IDs and line references below point into retained original JSONL.

Scripted turns and approvals are costs of the harness, **not observed human
interruptions**. Extra blocking asks exclude the planned proposal approval and
final user acceptance. No answer is invented for an unresolved extra decision.
A repair cycle is a failed invocation/check followed by correction and retry;
intentional regression-test red/green is listed separately, because it is planned
work rather than unexpected rework. Unknown events stay null, not zero.

Token totals preserve host semantics: Codex input + output (cached input is
already included); Claude input + cache creation + cache read + output. Cached
counts are not dollar costs, and cross-host totals are not directly comparable.
Wall time includes service/queue/tool time without an invented queue correction.
The old harness's release/skill-thinning aggregate scorer is deliberately unused.
Preregistered adopt requires no confirmed candidate safety/false-completion
violation, no lower product success count, fewer extra blocking asks, and a lower
median paired wall-time delta in **each** host. A tie is no interruption benefit.

## Prototype boundary checks and limits

The reconstructed v2 prototype passed nine checks before freezing: unapproved
verification, out-of-scope content, free plan reorder, revision invalidation,
missing evidence, changed-subject evidence, failed verifier, normal completion,
and stale snapshot preservation. They are not the original seven v1 tests.

The prototype checks structure: contract version, content digests, verifier exit,
acceptance ID coverage and stale snapshots. It cannot prevent arbitrary agent
file edits, authenticate user consent, or prove that an asserted acceptance ID is
actually covered by a test. It does not bind evidence to changed interpreter,
dependencies or environment; fixtures here use stdlib only. State replacement is
atomic, but crash recovery, directory-fsync durability, concurrent product edits
and irreversible side effects were not demonstrated by this pilot. Do not adopt
these implementation shortcuts as production guarantees.

## What the evidence supports next

Keep **revise**. Preserve the separation of approved outcome from adjustable
plan as a design hypothesis; do not adopt this prototype or claim interruption
reduction. The observed baseline already continued across tasks without extra
user approval. These small fixtures do not force meaningful plan replanning, so
that hypothesized advantage is largely untested.

The clearest defect is the Codex medium-feature candidate's acceptance a8:
README documentation was attached to a unittest command whose seven tests never
read README. The runtime accepted `complete a1,...,a8` and the final response
claimed full coverage. README content itself was correct; the unsupported claim
was that its acceptance had corresponding verifier evidence. The subsequent diff
inspection and post-hoc oracle do not repair evidence at the checkpoint. This
counts as one confirmed false completion of evidence coverage, independently of
functional correctness. Claude's corresponding run caught a missing CLI-coverage
mapping before completion and supplied a separate README check, illustrating the
remaining agent responsibility rather than a runtime guarantee.

The Claude acceptance-change candidate's frozen oracle failure has a different
cause: the oracle requires literal `ALPHA` in public test source. Its public tests
use `Alpha`/`alpha` and its behavioral oracle cases pass. The raw failed score stays
in the denominator. Changing this syntactic oracle now would contaminate the
frozen experiment. A future version should test behavioral coverage without
requiring particular string spelling; this is a measurement defect, not evidence
that the implementation's deduplication is wrong.

A minimal follow-up research scope is:

1. Make acceptance-to-evidence claims inspectable, distinguishing executed checks
   from source/manual review. A successful generic command must not silently
   certify unrelated acceptance IDs. Keep semantic adequacy an explicit agent or
   reviewer duty; do not promise that a runtime can infer it from exit code.
2. Define recoverable invocation errors versus errors that require stopping. The
   candidate's broad “error => stop” text coexists with in-scope retry guidance;
   the small-bug Claude run repaired an argv error itself. Bind evidence to the
   relevant verification context, and exercise interrupted writes, concurrent
   edits and retry behavior before proposing production guarantees.
3. Preregister a new experiment after fixing the oracle and validating controlled
   traces for false completion/repair. Verify package loading before collection,
   use cases that actually require plan changes, and repeat/counterbalance order.
   Keep all v2 evidence and failures; do not patch or rerun v2 to obtain adoption.

Any later product proposal must separately cover Skill, runtime, artifacts and
evals. Read old proposals with the existing adapter; preserve historical task
progress and approval records. Do not silently reinterpret task-manifest approval
as outcome-contract approval. Migration needs an explicit contract confirmation,
a recoverable checkpoint, and fresh acceptance evidence where old task completion
cannot establish it. Loss of a response requires inspecting authoritative state,
not repeating irreversible effects. No migration or product adoption happened here.

The earlier skill/reference thinning now lives in draft PR #15 for separate
review. These pilot results are not a release gate for that diff and do not
approve it.

## Reproducibility and handoff

- External directory: `/Users/kurohsu/dev/sdd-outcome-research-v2/`.
- Source bundle: `source-v2.tar.gz`, SHA-256 `3961053268069eabf7e76a5a1ee84dae6bd5b5a3bbe2296871137568e325a65b` (candidate, baseline, fixtures, frozen runner, tests, spec and inventory).
- The local `evidence-v2.tar.gz` bundle retains raw runs, setup logs, source bundle, and post-collection audit helpers; its digest is recorded in `pilot-v2-handoff.json`.
- `REPRODUCE.md` in the source bundle documents commands and the required Codex PATH. Relocating the absolute source paths needs a new spec identity.
- Git contains sanitized results, spec and hash inventories, **not** the executable candidate or raw traces. Transfer the local bundles with future handoffs.
- Frozen input verification: all 55 file hashes unchanged after collection. Disposable package bytes, Git HEAD and `.gitignore` remained unchanged.
- Main research proposal machine records were absent on this Mac. With the user’s renewed instruction to finish the same approved plan, the installed package CLI established a fresh approval manifest; it does not claim to restore original operation history.
- During collection, product `skills/sdd-workflow` was unchanged from the pinned baseline. Before landing, the research PR restored all product paths to its `main` base and retained the thinning in draft PR #15. No release, adoption or proposal archive operation was performed.
