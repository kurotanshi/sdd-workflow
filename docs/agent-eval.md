# Agent evaluation contract

Status: eval specification version 2; scenario schema and scorer version 1

Agent evaluation measures whether an adapter follows the SDD workflow under
non-deterministic execution. It is deliberately separate from deterministic
runtime conformance.

The active machine-readable contract is `evals/eval-spec-v2.json`; historical
v1 evidence remains bound to `evals/eval-spec-v1.json`. Scenario fixtures still
conform to `evals/schema/scenario-v1.schema.json`. Every run records the exact
eval-spec version and SHA-256; reports must not reinterpret or combine evidence
across spec identities.

## Artifact boundary

Raw runs use:

```text
eval-runs/<agent>/<scenario-id>/<run-id>/
```

Each run records metadata, input, transcript, tool and CLI traces, Git diff,
proposal state before and after execution, final-state projection, and score.
`eval-runs/` is ignored and retained for at most 30 days unless a controlled
artifact store has a shorter policy. Raw transcripts never become repository
fixtures automatically; public summaries live under `evals/reports/`.

## Valid runs and retries

A valid run has complete pinned metadata, matching eval-spec version/SHA-256
and scenario/scorer versions, input and trace artifacts, a final-state
projection, no harness/environment failure, and a terminal Agent response
before the 900-second timeout.

Timeout, harness failure, and environment failure are invalid and may be
retried up to three total attempts for one planned run. Each attempt gets a new
run ID and names the run it replaces. An ordinary Agent failure is a valid
non-adherent run and cannot be replaced. A Critical Violation observed before
an invalid-run condition remains release-blocking and cannot be erased by a
retry.

## Scoring and release gate

Outcome, process, and safety checks are binary fixture checklists. A valid run
is adherent only when all three dimensions pass and no Critical Violation
occurs. Efficiency is diagnostic and has zero release-gate weight; it cannot
offset another failure.

Aggregate adherence is:

```text
adherent valid runs / all valid runs
```

An affected-scenario release gate requires one valid adherent run in every
selected Codex/scenario and Claude/scenario cell. Any valid non-adherent run,
cell still invalid after replacements are exhausted, identity mismatch, or
Critical Violation fails the gate. Unselected scenarios are outside that
matrix and do not make it incomplete.

Aggregate adherence remains in reports as a diagnostic ratio only. Its former
95% threshold is not a v2 release gate and cannot offset a failed cell.

Full benchmark mode is separate and explicit: it plans three valid runs for
both Agents across all 20 scenarios (`20 × 2 × 3 = 120`). It is never selected
implicitly and is not labeled as release-gate evidence.

## Isolated runner

`scripts/run-agent-eval` prepares one scenario in a temporary Git repository,
invokes either Codex non-interactively (`codex exec --json`) or Claude Code in
print mode (`claude -p --output-format stream-json`), and collects the complete
artifact layout. Example:

```text
scripts/run-agent-eval \
  --agent codex \
  --scenario M-acceptance-change \
  --model gpt-5.6
```

Codex defaults to `workspace-write`; Claude Code defaults to `acceptEdits` with
an explicit Bash/Edit/Write/Read/Glob/Grep allowlist. Each run records the
permission mode, requested and observed model identities, host version, Skill
commit and SHA-256, runtime version, scenario/scorer versions, exact eval-spec
version and SHA-256, platform, and UTC timestamps. Use `--replaces-run-id` only
under the versioned retry policy.

## Scoring and aggregate summary

Score each completed raw run with the versioned rule registry:

```text
scripts/score-agent-eval \
  eval-runs/codex/M-acceptance-change/<run-id>
```

The scorer evaluates each fixture checklist against trace, Git, proposal, and
final-state evidence. It writes a complete `score.json`. A non-adherent run is
still a successfully scored result; scorer or artifact contract errors exit
with status 2.

Aggregate completed scores without copying raw transcripts into the report:

```text
scripts/summarize-agent-eval \
  --artifact-root eval-runs \
  --scenario M-acceptance-change \
  --skill-commit <exact-commit> \
  --skill-sha256 <exact-skill-sha256> \
  --codex-model <exact-model> \
  --claude-model <exact-model-or-alias> \
  --json-output eval-summary.json \
  --markdown-output eval-summary.md
```

Repeat `--scenario` for the exact affected selection used by the runner. The
summary reports only that selected matrix, plus diagnostic aggregate adherence,
invalid runs, failed dimensions, identity mismatches, and Critical Violations.
Artifacts with another Skill commit/SHA-256, per-Agent requested model, or eval
spec identity are classified and make the release gate fail; they never fill a
selected cell.

Run or resume the minimum two-Agent matrix with:

```text
scripts/run-agent-eval-matrix \
  --artifact-root eval-runs/v07-baseline \
  --scenario M-acceptance-change \
  --codex-model gpt-5.6-sol \
  --claude-model sonnet
```

The matrix runner counts existing valid runs, retries only invalid
harness/environment attempts under the versioned three-attempt limit, scores
each new artifact immediately, and never replaces a valid non-adherent run.
Selection must be explicit, non-empty, unique, and known before the artifact
root is created. Use `--dry-run` to inspect the plan, or `--full-benchmark` for
the separate 120-slot benchmark. No automatic diff classifier or second eval
configuration chooses scenarios; the release handoff records the rationale.

## v1 to v2 transition

The already-running v1.4.0 matrix completes under its original v1 policy and
remains historical baseline evidence. Do not modify, delete, rescore, replace,
or combine those raw artifacts with v2. Do not start another 120-run matrix for
transition validation; new release candidates use explicit v2 selection.
