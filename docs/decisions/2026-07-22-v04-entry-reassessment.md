# Start the v0.4 transaction engine after dogfood reassessment

## Date
2026-07-22

## Versions
- Engine: `0.3.0`
- Skill: `v0.3.0` candidate based on commit `5facfaca4c1e339d69fb2c14ac26c33062c5596f`
- Environment: four sequential repository dogfood proposals, verified through the canonical readonly CLI

## Question and gate
Does newly quantified real workflow usage satisfy the v0.4 entry criterion after the earlier `DEFER` decision?

The applicable ROADMAP criterion is not a hypothetical stale-write failure. It is whether actual usage frequency makes deterministic mutation clearly reduce repeated manual verification cost, while v0.3 evidence shows agents can follow the CLI path.

## Evaluated scenarios
- Run canonical `status` for each of the four completed dogfood proposals and count completed tasks.
- Identify the minimum supported prose-mutation operations required by those completed markers.
- Verify that readonly adoption remained stable enough to justify building experimental mutation commands without activating a hybrid Skill path.

## Observed evidence
- `narrow-skill-trigger-v024` has 5/5 completed tasks.
- `add-parser-characterization`, `add-readonly-cli-contract`, and `add-runtime-packaging-baseline` each have 8/8 completed tasks.
- The corpus therefore contains 29 real task completions, not synthetic failure injection. Under the supported workflow each required one direct marker edit and one distinct verification read/status operation; direct proposal approval was another separate mutation.
- This repeated cost is structural: prose writes cannot combine expected-snapshot validation, the marker transition, and the after-state result in one authoritative operation.
- `docs/decisions/2026-07-22-readonly-parsing-adoption.md` shows both Codex and Claude Code consistently followed a single CLI read path after the permission-form adjustment. No repeated bypass or completion-rate regression was observed.
- No stale-write or wrong-task incident is claimed. Entry is justified solely by the ROADMAP's explicit high-frequency/manual-verification-cost criterion, recorded as `F-20260722-04`.

## Rejected alternatives
- Continue to defer until a damaging mutation occurs: rejected because the roadmap explicitly permits demonstrated usage cost as entry evidence; requiring an avoidable incident would change the approved gate.
- Activate all v0.4 mutation paths immediately: rejected because implementation merge and Skill activation remain separate path-specific decisions.
- Treat 29 tasks as 29 correctness failures: rejected; the evidence proves repeated operational cost only.

## Decision
`GO` for implementing the experimental v0.4 transaction proposals in dependency order, starting with `add-machine-metadata-and-approval-manifest`. This supersedes `docs/decisions/2026-07-22-v04-entry.md`.

This decision does not activate any new Skill mutation path. Each path still requires its own fresh-session pilot and activation decision after the dependent command set is coherent.

## Rollback boundary
Until a path-specific activation decision changes `SKILL.md`, experimental commands and metadata fixtures may be removed without changing the supported v0.3 workflow. Once a command writes metadata in a test or explicitly opted-in proposal, rollback must preserve or explicitly discard that proposal-local metadata; it must never silently reinterpret approval history.

## Follow-up
- Explicitly approve and implement `add-machine-metadata-and-approval-manifest`.
- Keep approve/revision commands experimental until task completion and terminal dependencies reach coherent activation points.
- Use new friction entries, not this entry decision alone, for recover, lock, Schema v2, or impact metadata gates.

## Sensitive-data review
- [x] No full user transcript is stored by default.
- [x] Project names, repository paths, source snippets, credentials, personal data, and customer data are removed or replaced with stable neutral labels.
- [x] Commands and links contain only information safe to retain in this repository.
- [x] When raw evidence cannot be safely retained, the record contains a de-identified summary and a minimal synthetic reproduction instead.
