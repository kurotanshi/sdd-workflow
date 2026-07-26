# Skill-only Roadmap

Status: strategy reset after v1.0
Scope: `sdd-workflow` is an installable Agent Skill, not a developer kit

## Product decision

The repository has one product: the package under `skills/sdd-workflow/`.
`SKILL.md` defines the Agent workflow; references, scripts, fixtures, and evals
exist only to make that Skill usable and maintainable. They are not separate
protocol, SDK, platform, or third-party conformance products.

Future work is decision-gated, not precommitted to versions or dates. A gate
may close with no product change.

## Current baseline

The reset starts from the current `main` behavior and evidence:

- the main `SKILL.md` is 9,901 bytes with two on-demand references;
- the package-local Python runtime is about 6,165 lines;
- the complete suite contains 240 passing tests;
- the v0.9 reduction cut the main Skill by about 46% without reducing measured
  Agent adherence;
- the v1.0 matrix recorded 76/78 adherent runs and zero Critical Violations;
- existing usage evidence does not isolate the Skill's ceremony cost, because
  earlier comparisons used different repository snapshots.

The Skill already implements one-task-at-a-time automatic progression and a
proposal summary handoff. These are current behavior, not roadmap features.

## Assessment of the proposed direction

### Adopt

- Make the Skill the only public product and keep one canonical package source.
- Freeze natural-language trigger expansion.
- Preserve the existing runtime until a paired cost comparison exists.
- Measure value and ceremony against a no-Skill baseline before runtime cuts;
  retain a small high-risk cross-Agent regression set.
- Require real demand before adding modes, adapters, schemas, or references.

### Amend

- Treat 5 KB for `SKILL.md` and two references as review targets, not blind
  deletion instructions.
- Measure complexity through Agent round trips and synchronized contract
  surfaces as well as source lines.
- Classify documents by need before changing them; churn is not simplification.
- Separate measurement, positioning, runtime, and UX gates.

### Defer

- Defer exploration, adapters, English schema aliases, semantic review,
  type-specific authoring, and another reporting reference.
- Do not rewrite proven safety behavior for a line target or advertise a
  protocol, developer kit, or third-party conformance program.

## Complexity budget

Every roadmap item is labeled before work starts:

- **Reduce** removes a product promise, required step, synchronization surface,
  or recurring maintenance obligation.
- **Fix** corrects behavior or usability without expanding the supported scope.
- **Measure** produces evidence for a named decision and adds no product
  capability.
- **Add** expands a trigger, mode, adapter, schema, command, reference, public
  guarantee, or supported environment.

Additions need a real requester, unmet need, expected benefit, owner, and
regression evidence. Release numbering or existing code is not demand.

### Public product surface

- one product and canonical source: `skills/sdd-workflow/`;
- one main `SKILL.md`, targeting at most 5 KB;
- at most two on-demand references;
- one user-facing workflow and no independent protocol or developer-kit
  compatibility promise;
- only Skill release, proposal artifact schema, and JSON output version are
  first-class version concepts; lower-level metadata versions are internal
  diagnostics.

Exceed a target only when safety or usability evidence justifies it.

### Agent execution cost

Track turns, tool calls per task, total tokens, and wall time on the normal
workflow. Hidden digests and internal code do not count as simplification when
the Agent still performs the same round trips. Numerical keep-or-cut thresholds
must be registered before each comparison.

### Maintainer synchronization cost

For every behavior change, record which Skill rules, runtime paths, fixtures,
scorers, and public documents must move together. Prefer designs that reduce
this required set. Moving files, renaming conformance assets, or hiding a
concept from README does not count as reduced maintenance unless the old
obligation and its synchronization checks are actually removed.

### Internal implementation

Internal stdlib-only scripts and regression tests may remain as large as needed
to preserve proven behavior. Runtime line count is diagnostic, not a release
gate, until cost evidence identifies a specific low-value path. New internal
machinery is still an addition and must pass the same demand gate.

## Gate 0 — freeze and paired cost-benefit baseline

This gate runs before any Skill behavior, runtime, public-positioning, or eval
matrix change. Pin the exact repository commit, Skill bytes, Agent host/model
versions, permissions, prompts, fixtures, and cache interpretation used by
both variants.

### Comparison design

Use three representative tasks:

1. a small bug fix with one focused validation;
2. a medium feature spanning multiple files;
3. an acceptance-time requirement change that tests scope-drift handling.

Run each task with Codex and Claude Code in two variants: ordinary coding
without `sdd-workflow`, and the current complete Skill package. Use isolated
copies of the same repository snapshot, equivalent prompts, fresh sessions,
and three valid paired runs per Agent/task/variant. Randomize variant order
within each pair and retain failures in the denominator unless the host or test
environment itself is invalid.

Do not change `SKILL.md`, runtime code, proposal format, or scenario wording
after collection starts. A changed input starts a new experiment version.

### Measurements

For every run, record:

- task and acceptance success;
- any implementation before explicit approval;
- hidden or unapproved scope changes;
- premature archive or unsafe abandonment;
- turns and user confirmations;
- total tool calls and tool calls per completed task;
- input, cache, and output tokens using each host's documented semantics;
- total wall time, with host queue or outage time identified separately;
- which predefined failure, if any, the Skill stopped or made recoverable.

Publish aggregate results and limitations in `docs/cost-benefit.md`. Raw
transcripts and project content stay outside the repository unless separately
reviewed for publication.

### Pre-registered decision thresholds

The current runtime is acceptable when all of the following hold:

- the Skill variant has zero Critical Violations;
- its task-success count is not lower than the paired no-Skill variant;
- median additional tool calls are at most four per completed task;
- median total-token overhead is at most 40%;
- median wall-time overhead, excluding identified host queue time, is at most
  35% in at least two of the three task types for each Agent.

Runtime simplification becomes eligible only when a cost threshold is exceeded
for both Agents in at least two task types. A single-host or single-task
regression triggers diagnosis, not architecture removal. Observed prevented
errors are reported as benefit evidence but are never manufactured by changing
the control prompt.

Crossing a threshold authorizes a separate runtime decision; it does not
preselect what to remove. Passing the gate closes runtime reduction with a
documented no-op result.

## Gate 1 — public-positioning convergence

Enter only after Gate 0 inputs and results are frozen. This gate changes what
the project promises, not Skill behavior or runtime mechanics.

Inventory each root document, `docs/` page, conformance claim, version concept,
release artifact, and linked test under exactly one primary need:

1. **User-required** — needed to decide when to use the Skill, install it, run
   the happy path, or recover from a likely failure.
2. **Maintainer-required** — needed to preserve a safety invariant or explain
   an implementation decision that active code still depends on.
3. **Historical evidence** — useful for audit or prior results but no longer a
   current product promise.

Keep user-required material discoverable from README. Mark maintainer material
as internal and link it from contributing guidance, not the user journey.
Preserve historical evidence without presenting it as normative support.
Remove a document or test only when its obligation is gone or another canonical
source fully owns it.

The user-facing result must describe an SDD Skill, include “use when” and
“usually unnecessary when” guidance, and communicate only Skill release,
proposal artifact schema, and JSON output version. It must not invite third
parties to implement against a frozen protocol or advertise a standalone
conformance kit.

Renaming `conformance/`, moving `docs/protocol/`, or merging release records is
optional and earns no completion credit by itself. Gate 1 closes only when the
number of public promises and synchronized sources is demonstrably smaller,
links and regression checks pass, and runtime behavior remains unchanged.

## Gate 2 — conditional runtime decision

Enter only if Gate 0 exceeds a cost threshold for both Agents in at least two
task types. Otherwise close this gate as a no-op and retain the tested runtime.

For an eligible result, test the smallest change first:

1. reduce high-frequency round trips by combining fresh-state checks with the
   mutation that needs them;
2. simplify optimistic locking only if stale-context rejection remains
   equivalent;
3. consider handshake capability matrices, attestation, or multi-axis
   compatibility metadata only when measurement ties them to material Agent or
   maintainer cost.

Do not begin with a parser rewrite, archive-model change, or line-count target.
Measure every candidate separately, rerun its focused regression tests and the
paired cost cases, and keep it only when it reduces the registered cost without
weakening these invariants:

- product code is not changed before explicit proposal approval;
- requirement or acceptance changes invalidate approval until reapproved;
- only the canonical current task advances, and only after validation;
- incomplete work is not archived, and terminal moves cannot target the wrong
  proposal or silently reverse;
- abandonment requires the exact confirmation and never rolls back source
  control or product code;
- stale or concurrent mutation fails before overwriting newer state.

If no candidate passes both cost and safety checks, document the evidence and
close Gate 2 without a runtime change.

## Gate 3 — demand-driven refinements

After the baseline and positioning work, each refinement needs a separate
proposal and remains a Fix rather than a bundled release:

- test whether bare `實作` on a draft should ask one approval question instead
  of stopping; it must not silently approve;
- add authoring limits of 1–3 rationale paragraphs, 3–7 tasks, and 3–8
  observable acceptance scenarios only if usability evidence shows they help;
- after behavioral changes, run one fresh pass on approval boundary (B), scope
  drift (D), ambiguous cancellation (J), incomplete archive (H), and
  acceptance-time change (M) in both Claude Code and Codex; reserve the full
  matrix for major host changes or identified risk;
- add fresh-session or context-compression cases only when field evidence shows
  a recovery gap not covered by the existing cross-session scenario.

Use the existing authoring reference; do not add a reporting reference. Current
automatic one-task progression and proposal-summary handoff remain baseline
behavior, not candidates.

## Demand-only backlog

Exploration mode, additional Agent adapters, English schema aliases, semantic
review, type-specific guidance, and a reporting reference have no scheduled
version. Each requires a named requester and the addition-gate evidence.
Exploration, if ever justified, accepts only explicit
`$sdd-workflow 分析`; it must never expand natural-language triggers.
