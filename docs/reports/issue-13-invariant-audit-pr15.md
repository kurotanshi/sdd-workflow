# Issue #13 invariant audit (PR #15)

Recorded: `2026-09-18T07:13:09.590732+00:00`

Line-by-line mapping of fail-closed governance invariants after skill thinning. Paths are relative to repo root.

| Invariant | File | Lines | Evidence snippet |
| --- | --- | --- | --- |
| Proposal before implementation / no impl without approval | `skills/sdd-workflow/SKILL.md` | 12 | - State the plan before implementation. Never modify implementation files unless canonical proposal status is `approved`. |
| Explicit 開始實作 approves draft | `skills/sdd-workflow/SKILL.md` | 14 | - `開始實作` explicitly approves a `draft`. Plain `實作` continues only an `approved` proposal; otherwise ask for approval and stop. |
| Managed revision on requirement change | `skills/sdd-workflow/SKILL.md` | 15 | - Requirement changes during implementation or acceptance enter managed revision and require new `開始實作`. |
| Package-local discovery fail-closed | `skills/sdd-workflow/SKILL.md` | 16 | - Run package-local discovery once before the first SDD CLI command in a session. Zero, ambiguous, failed, or incompatible discovery must fa |
| CLI sole authority / no prose fallback | `skills/sdd-workflow/SKILL.md` | 17 | - The bundled CLI is the only authority for discovery, parsing, validation, canonical status, tasks, acceptance, snapshots, diagnostics, man |
| No direct lifecycle/INDEX edits | `skills/sdd-workflow/SKILL.md` | 18 | - Never directly edit lifecycle status, checkbox markers, machine metadata, archive paths, or INDEX. Direct prose edits are limited to new d |
| One canonical task at a time | `skills/sdd-workflow/SKILL.md` | 19 | - Work on and verify one canonical task at a time. Do not invent requirements, combine unrelated changes, or mark a task complete merely bec |
| Abandon double confirm exact phrase | `skills/sdd-workflow/SKILL.md` | 20, 100 | - Abandonment requires read-only preflight followed by exact `確認放棄 <short-name>`. It retains implementation and Git work. |
| refresh_status does not keep mutation intent | `skills/sdd-workflow/SKILL.md` | 63 | Before the first mutation in an implementation sequence, obtain fresh successful `status`. A successful `approve` or `complete-task` result  |
| refresh_status recovery action table | `skills/sdd-workflow/references/runtime-recovery.md` | 12 | \| `refresh_status` \| Rerun readonly status, explain stale evidence, and stop for renewed intent \| |
| Self-review never approves/implements | `skills/sdd-workflow/references/self-review.md` | 67 | Offer to expand on findings. A question about the report or an option answer continues self-review; answer it and remain stopped. Never call |
| Layer 3 gated + user chooses | `skills/sdd-workflow/references/self-review.md` | 37 | ## Layer 3 — design direction |
| Authority split stops without choosing | `skills/sdd-workflow/references/self-review.md` | 28 | 2. Rule authority: check whether the proposal decides one rule twice, makes a client reimplement a server rule, or stores state derivable fr |
| Approved prose frozen | `skills/sdd-workflow/references/self-review.md` | 8 | - `approved`: prose is frozen. Report findings only; applying one requires `提案` to enter managed revision. |

## Tests locking these invariants

- `tests/test_skill_reduction.py` — budget, lifecycle anchors, `refresh_status`, Layer 3 / authority-split stop, description-only truncation gate
- Existing runtime suites (unchanged by this PR’s intent): transition/recovery tests still assert `refresh_status` actions on snapshot/identity mismatches

## Claim level

Static skill/reference line mapping only. Complements, but does not replace, live host-eval behavioral evidence for issue #13.

## Verdict

**PASS** — all listed invariants have explicit skill/reference anchors on this branch.
