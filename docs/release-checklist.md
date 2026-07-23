# Release checklist

Status: v0.7 conformance and Agent-eval release gate

Use an exact candidate commit and record every command result with the release
handoff. Do not publish a moving branch as release evidence.

## Candidate integrity

- [ ] Confirm the candidate commit and version are exact.
- [ ] Confirm the worktree contains no unrelated tracked or untracked files.
- [ ] Run the complete unit/integration suite and package, documentation,
  trigger, and install-smoke validations.
- [ ] Review compatibility, schema, CLI, and package changes for an explicit
  version decision.

## Deterministic conformance

- [ ] Run `scripts/run-runtime-conformance --json`.
- [ ] Require every selected case to pass; preserve the manifest and registry
  versions in the release handoff.

## Agent-eval matrix

- [ ] Run or resume the two-Agent matrix:

  ```text
  scripts/run-agent-eval-matrix \
    --artifact-root eval-runs/<candidate> \
    --codex-model <exact-model> \
    --claude-model <exact-model-or-alias>
  ```

- [ ] Score and summarize the retained artifacts:

  ```text
  scripts/summarize-agent-eval \
    --artifact-root eval-runs/<candidate> \
    --json-output eval-runs/<candidate>/summary.json \
    --markdown-output eval-runs/<candidate>/summary.md
  ```

- [ ] Require three valid runs for every Agent/scenario cell, at least 90%
  aggregate adherence, and exactly zero Critical Violations.
- [ ] Classify every valid failure and invalid attempt. Do not replace a valid
  non-adherent run or erase a Critical Violation through retry.

## Publication review

- [ ] Write only the aggregate, anonymized report under `evals/reports/`.
- [ ] Run `scripts/check-public-eval-report`.
- [ ] Manually inspect the staged report for secrets, credentials, absolute
  user paths, personal identifiers, prompts, transcripts, event payloads, and
  raw command output.
- [ ] Confirm the report records the model/host/runtime/spec/scorer/Skill
  identity, measurement dates, matrix denominator, failure classifications,
  and release-gate decision.
- [ ] Confirm no file under `eval-runs/` is staged or committed.
