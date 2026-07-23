# Team readiness entry and contention gate

## Date
2026-07-22

## Versions
- Engine: `0.5.0`
- Skill: `v0.5.0`
- Environment: ten sequential roadmap proposals, Codex/Claude activation pilots, macOS/Linux CI baseline

## Question and gate
Decide which team-readiness work is justified and fix the evidence threshold for adding a lock or INDEX-level CAS. CI decomposition, install/package reproducibility, compatibility guidance, worktree boundaries, and concurrency tests may proceed when they reduce observed release or operator ambiguity. Serialization may proceed only if a reproducible contention test shows authoritative data loss, an unrecoverable state, or repeated derived-state corruption that `validate-index`/`rebuild-index` cannot safely resolve.

## Evaluated scenarios
- Repeated sequential execution of the first nine roadmap proposals and their release checks.
- Fresh Codex and Claude Code activation sessions using the same installable package.
- Existing terminal failure injection, stale INDEX detection, and deterministic rebuild behavior.
- Potential same-proposal and different-short-name operations in one repository or separate worktrees.

## Observed evidence
- The suite and packaging checks have grown across parser, transaction, archive, and schema milestones, but the current CI groups them under one matrix job. A failure cannot be selected as one of the five stable branch-protection check names from the roadmap.
- Fresh-tool pilots worked only after loading the canonical package path and version; install/version-skew diagnostics are therefore part of reproducible operation, not presentation polish.
- `F-20260722-04` records repeated workflow use, while the managed activation and Schema v2 decisions show the engine is now stateful enough that mixed generations need an explicit boundary.
- Snapshot CAS continues to protect a single proposal from stale-context writes.
- Two concurrent archives for different short names preserved both authoritative archive directories. One process may report `COMMITTED_DERIVED_ARTIFACT_STALE`, after which `validate-index` and `rebuild-index` restore the derived view without moving or rewriting authoritative artifacts.
- Six parallel `rebuild-index` processes completed through atomic replacement and converged on the same valid INDEX without leaving temporary files.
- A synthetic stale-scan overwrite was detected as `ERROR_INDEX_STALE`; both archive records remained readable and a deterministic rebuild repaired the INDEX.
- No contention test demonstrated authoritative data loss, an unrecoverable state, or repeated derived-state corruption that the existing validation and rebuild commands could not resolve.

## Rejected alternatives
- Add a repository-wide lock before contention tests: there is no evidence for its stale-owner lifecycle or maintenance cost.
- Treat one combined CI matrix job as five required checks: branch protection cannot independently identify or require those contracts.
- Promise same-proposal multi-agent safety from snapshot CAS alone: the supported ownership rule remains one agent per proposal until a separate mechanism proves otherwise.

## Decision
`GO` for decomposed CI checks, hermetic installation/package tests, version-skew and worktree guidance, and reproducible concurrency tests. `NO-GO` for a lock or INDEX-level CAS in v0.6.0: the contention threshold was not met. A temporarily stale but reconstructible INDEX is not by itself sufficient evidence for serialization. Re-evaluate only after a reproducible failure meets the fixed gate above.

## Rollback boundary
CI/check and documentation changes are reversible without artifact migration. Installation tests must not write user tool directories. If concurrency tests reveal authoritative loss, stop release and open the smallest serialization design with stale-owner/recovery tests; do not silently add an untested lock inside this proposal.

## Follow-up
- Record a friction entry only for a reproduced failure or material operator cost; a hypothetical race is not friction evidence.
- Keep the one-owner-per-proposal boundary; these tests do not authorize concurrent mutation of one proposal.
- Preserve the concurrent archive and rebuild scenarios as regression tests for future engine changes.

## Sensitive-data review
- [x] No full user transcript is stored by default.
- [x] Project names, repository paths, source snippets, credentials, personal data, and customer data are removed or replaced with stable neutral labels.
- [x] Commands and links contain only information safe to retain in this repository.
- [x] When raw evidence cannot be safely retained, the record contains a de-identified summary and a minimal synthetic reproduction instead.
