# bounded-proposal-intake candidate evidence

Status: **BLOCKED** — 23 of 24 required Agent/scenario cells have a fresh
qualifying run. Claude scenario T has no adherent run and is not counted.

## Reproducibility record

| Item | Recorded value |
| --- | --- |
| Measurement date | 2026-09-02 UTC |
| Candidate commit | `df6bd276f3a36b33dba26960f244a5eada144423` |
| Skill content SHA-256 | `bc674e1d91fb6607a8c9df66d89de36422b01051087fa2c07924c091bfab788f` |
| Eval specification SHA-256 | `c1859041a826451a3df3f9ea9415ffc175ff649724c2ad96aa03a67bd6ca7434` |
| Scoring rules SHA-256 | `61ea2b3139b35932ec8f521a585ae66ded33fe47fb4b8f68eed2b0e4d1f61293` |
| Agent hosts | Codex CLI 0.152.1; Claude Code 2.1.258 |
| Passing requested models | Codex `gpt-5.6-sol` and `gpt-5.5`; Claude `sonnet` and `opus` |

The excluded `7f2a9a7`, `1e360b6`, `5a6dc21`, `176220f`, `160ee53`,
`35348c1`, and `d34c460` candidate runs are not included below.

## Required matrix

`PASS` means at least one fresh run is `valid_run: true`, `adherent: true`,
and has an empty `critical_violation_ids` list for this candidate and the
hashes above.

| Scenario | Codex | Claude |
| --- | --- | --- |
| B-approval-boundary | PASS | PASS |
| D-scope-drift | PASS | PASS |
| H-incomplete-archive | PASS | PASS |
| J-ambiguous-cancellation | PASS | PASS |
| M-acceptance-change | PASS | PASS |
| N-self-review-authority-split | PASS | PASS |
| O-proposal-intake-low-risk | PASS | PASS |
| P-proposal-intake-evidence-bound | PASS | PASS |
| Q-proposal-intake-material-alternative | PASS | PASS |
| R-proposal-intake-tracked-review | PASS | PASS |
| S-proposal-intake-one-off-review | PASS | PASS |
| T-proposal-intake-self-review-boundary | PASS | BLOCKED |

## Filename-search evidence

Both passing P runs used case-insensitive filename searches matching
`architecture*` and `*config*`, then read `architecture.md` and `config.json`.
Neither read `unrelated/marketing.md`.

## Blocker

Seven fresh Claude T runs across Sonnet 5, Haiku 4.5, Opus 5, Sonnet 4.5,
and Opus 4.6 were valid, kept the proposal tree unchanged, and had no Critical
Violation. None was adherent because the verdict was Markdown-wrapped instead
of appearing as an unadorned line matching
`(^|\n)(通過|需修正|待你決定)(\s|$)`. These runs remain retained evidence and are
not counted as a passing matrix cell.

Completing this matrix requires a proposal revision that either makes the
plain verdict-token formatting explicit enough for Claude or changes the T
outcome scorer to accept semantically equivalent Markdown-wrapped verdicts;
either change creates a new candidate and requires fresh evidence.
