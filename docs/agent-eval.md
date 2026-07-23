# Agent evaluation contract

Status: eval specification, scenario schema, and scorer version 1

Agent evaluation measures whether an adapter follows the SDD workflow under
non-deterministic execution. It is deliberately separate from deterministic
runtime conformance.

The machine-readable contract is
`evals/eval-spec-v1.json`; scenario fixtures conform to
`evals/schema/scenario-v1.schema.json`. Both are immutable version 1 inputs to
a run. A report must name their versions rather than relying on a moving
branch or an unqualified "current" Agent.

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

A valid run has complete pinned metadata, matching scenario/scorer versions,
input and trace artifacts, a final-state projection, no harness/environment
failure, and a terminal Agent response before the 900-second timeout.

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

The v0.7 gate requires at least 90% aggregate adherence and exactly zero
Critical Violations. Reports always include the numerator, denominator,
invalid-run count, version matrix, and measurement dates.

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
commit and SHA-256, runtime version, scenario/scorer versions, platform, and
UTC timestamps. Use `--replaces-run-id` only under the versioned retry policy.

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
  --json-output eval-summary.json \
  --markdown-output eval-summary.md
```

The summary reports the Agent/scenario valid-run matrix, adherence numerator
and denominator, invalid runs, failed dimensions, and Critical Violations.
The release gate is conjunctive: the minimum matrix, 90% adherence, and zero
Critical Violations must all pass. Efficiency is always diagnostic-only.

Run or resume the minimum two-Agent matrix with:

```text
scripts/run-agent-eval-matrix \
  --artifact-root eval-runs/v07-baseline \
  --codex-model gpt-5.6-sol \
  --claude-model sonnet
```

The matrix runner counts existing valid runs, retries only invalid
harness/environment attempts under the versioned three-attempt limit, scores
each new artifact immediately, and never replaces a valid non-adherent run.
