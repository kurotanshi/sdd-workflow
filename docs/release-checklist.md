# Release checklist

Status: current v1.x release gate

Use an exact candidate commit and record every command result with the release
handoff. Do not publish a moving branch as release evidence.

## Candidate integrity

- [ ] Confirm the candidate commit and version are exact.
- [ ] Confirm the worktree contains no unrelated tracked or untracked files.
- [ ] Run the complete unit/integration suite and package, documentation,
  trigger, and install-smoke validations.
- [ ] Run `python3 tests/full_lifecycle_smoke.py` and require install,
  discovery, handshake, proposal lifecycle, readonly diagnostics, uninstall,
  and no-residue checks to pass.
- [ ] Run `python3 <candidate-skill>/scripts/discover-runtime.py`; confirm the
  identity manifest, Skill hash, engine generation, schema interval, and
  required capabilities agree.
- [ ] Compare `conformance/install-channels-v1.json`, README install paths,
  `docs/install-methods.md`, and package validation for the same complete
  distribution contract.
- [ ] Review compatibility, schema, CLI, and package changes for an explicit
  version decision.

## Deterministic conformance

- [ ] Run `scripts/run-runtime-conformance --json`.
- [ ] Require every selected case to pass; preserve the manifest and registry
  versions in the release handoff.

## Agent-eval matrix

Select every scenario whose interaction boundary the candidate can affect. The
release handoff must list those scenario IDs, explain the selection, and record
the exact candidate commit, Skill SHA-256, per-Agent requested models, and eval
spec version/SHA-256 from `evals/eval-spec-v2.json`. Do not infer this list with an automatic diff classifier
or maintain a second eval configuration.

- [ ] Run the selected two-Agent release matrix (repeat `--scenario`):

  ```text
  scripts/run-agent-eval-matrix \
    --artifact-root eval-runs/<candidate> \
    --scenario <affected-scenario-id> \
    --codex-model <exact-model> \
    --claude-model <exact-model-or-alias>
  ```

- [ ] Score and summarize the retained artifacts:

  ```text
  scripts/summarize-agent-eval \
    --artifact-root eval-runs/<candidate> \
    --scenario <affected-scenario-id> \
    --skill-commit <exact-commit> \
    --skill-sha256 <exact-skill-sha256> \
    --codex-model <exact-model> \
    --claude-model <exact-model-or-alias> \
    --json-output eval-runs/<candidate>/summary.json \
    --markdown-output eval-runs/<candidate>/summary.md
  ```

- [ ] Require every selected Agent/scenario cell to contain one valid adherent
  run, with no valid non-adherent run, exhausted invalid cell, identity
  mismatch, or Critical Violation. Aggregate adherence is diagnostic-only and
  cannot make a failed cell pass.
- [ ] Classify every valid failure and invalid attempt. Do not replace a valid
  non-adherent run or erase a Critical Violation through retry.
- [ ] Use `--full-benchmark` only for an explicitly requested three-run full
  matrix (`20 × 2 × 3 = 120` slots). Record it separately from release evidence.

The in-progress v1.4.0 matrix remains historical v1 evidence and completes
under its original policy. Do not modify, rescore, replace, or rerun its raw
artifacts as v2 evidence.

## Publication review

- [ ] Write only the aggregate, anonymized report under `evals/reports/`.
- [ ] Run `scripts/check-public-eval-report`.
- [ ] Manually inspect the staged report for secrets, credentials, absolute
  user paths, personal identifiers, prompts, transcripts, event payloads, and
  raw command output.
- [ ] Confirm the report records the scenario-selection rationale, exact
  candidate and per-Agent model identity, runtime/spec/scorer identity,
  measurement dates, selected matrix, diagnostic aggregate adherence, identity
  mismatches, failure classifications, and release-gate decision.
- [ ] Confirm no file under `eval-runs/` is staged or committed.

## Recovery and examples

- [ ] Run `scripts/run-recovery-drills` and require every versioned drill group
  to pass.
- [ ] Run the example repository walkthrough and the security-review
  composition example from clean temporary projects.
- [ ] Confirm Schema v3, locking/leases, Web UI, external-platform integration,
  and multi-Agent orchestration are absent from the release scope.

## Release identity

- [ ] Confirm Core protocol, runtime/CLI, and Agent adapter contracts identify
  their stable v1 versions.
- [ ] Confirm runtime `--version`, handshake, package identity, README,
  compatibility matrix, CLI fixtures, and tests all report the exact candidate
  release and the same candidate-declared engine generation.
- [ ] Review `CHANGELOG.md`, migration, rollback, security/trust, and non-goals
  documents against the candidate bytes.
- [ ] Record the final candidate commit in the release handoff. Tagging,
  pushing, and publication remain separate explicitly authorized actions.
