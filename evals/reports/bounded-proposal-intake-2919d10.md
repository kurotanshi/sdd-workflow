# bounded-proposal-intake candidate evidence

Status: **PASS** — the scoped T outcome acceptance is satisfied on both hosts.

## Reproducibility record

| Item | Recorded value |
| --- | --- |
| Measurement date | 2026-09-03 UTC |
| Candidate commit | `2919d105fd96493acf0984504978290dbd20b534` |
| Skill content SHA-256 | `c3c393b495b429e8c3ef3ca81fdb7eb2f94971cc2c3bab90ff1cf7a1882ec2a1` |
| Eval specification SHA-256 | `c1859041a826451a3df3f9ea9415ffc175ff649724c2ad96aa03a67bd6ca7434` |
| Scoring rules SHA-256 | `37c90b51f7729d8520469c57c91eeb30baa445fb54b933a734e69b6af3042b32` |

## Scoped acceptance

| Host | Fresh run | Valid | Outcome | Verdict |
| --- | --- | --- | --- | --- |
| Codex 0.153.0 (`gpt-5.6-sol`) | `2919d10-codex-T-1` | PASS | PASS (1/1) | `通過` |
| Claude Code 2.1.259 (`opus`) | `2919d10-claude-T-1` | PASS | PASS (1/1) | `**通過**` |

Both runs use candidate `2919d10` and have `valid_run: true`; their
`self-review-verdict` checks pass under the recorded scoring rules. Raw
artifacts are retained under `eval-runs/bounded-proposal-intake-2919d10/`.

This acceptance covers only the T outcome scorer change. Other dimensions and
other scenarios are not gates for this task and were not rerun. Earlier
candidate runs are not counted.
