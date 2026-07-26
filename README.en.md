# sdd-workflow

> Version v1.0.1 ｜ [繁體中文](./README.md)

An **SDD (Spec-Driven Development) Skill** for coding agents such as Claude
Code and Codex.

It turns “agree on the change before the Agent edits code” into a durable,
recoverable workflow. Scope, tasks, acceptance conditions, approval, and
progress stay in the project. The product in this repository is a complete
Skill package, not a protocol, SDK, or developer kit.

## Skill goals

- Create a reviewable proposal and task checklist before any product-code change.
- Allow implementation only for an explicitly approved proposal, one verified task at a time.
- Stop implementation when requirements change, record the revision, and wait for reapproval.
- Recover authoritative state across sessions, handoffs, failed writes, and final archival.
- Fail closed when state or evidence is inconsistent instead of guessing or silently repairing it.

## Good fits

- Scope and acceptance conditions must be reviewed before the Agent may change code.
- The change contains multiple independently verifiable steps.
- Work may span sessions, Agent handoffs, or context recovery.
- Requirements may change during implementation or acceptance and need an approval record.

## Usually unnecessary

- Read-only questions, code explanations, exploration, or general research.
- A single low-risk edit that you explicitly asked the Agent to perform directly.
- Git/code rollback, emergency recovery, or deployment; these are outside SDD proposal state.
- Generic cancellation that does not target an SDD proposal.

## Install

Requirements: CPython 3.11 or newer; macOS and Linux are supported, while
Windows is best effort. Install the complete `skills/sdd-workflow/` directory,
not only `SKILL.md`.

### Codex

Use the built-in installer in a Codex conversation:

```text
$skill-installer install skills/sdd-workflow from the GitHub repo kurotanshi/sdd-workflow into ~/.agents/skills
```

The install location is `~/.agents/skills/sdd-workflow/`. Restart Codex if the
Skill does not appear on the next turn.

### Claude Code

Ask Claude Code to install the complete package:

```text
Install skills/sdd-workflow from https://github.com/kurotanshi/sdd-workflow into ~/.claude/skills/sdd-workflow
```

The install location is `~/.claude/skills/sdd-workflow/`. Start a fresh session
if the Skill does not appear. Manual installation, verification, updates, and
removal are covered in [`docs/install-methods.md`](./docs/install-methods.md).

## Your first workflow

1. Create a proposal:

   ```text
   $sdd-workflow 提案 Add a health-check API to my project
   ```

   Claude Code uses `/sdd-workflow 提案 …`. The Agent creates
   `sdd/<short-name>/proposal.md` and `tasks.md`, validates them, and stops
   without changing product code.

2. Review the proposal, then reply `開始實作`. The Agent approves that version
   and implements, validates, and updates tasks one at a time. Plain `實作`
   never approves a draft automatically.

3. State any changed requirement. The Agent stops code changes, revises the
   proposal, and waits for a new `開始實作`.

4. After every task is complete and you accept the result, reply
   `歸檔 <short-name>`. The proposal moves under `sdd/archive/`.

Replay the complete example with
`python3 examples/sample-web-api/run-walkthrough.py`.

## Workflow and safety boundaries

| Phase | Your action | Agent boundary |
| --- | --- | --- |
| Propose | `提案` | Write and validate the proposal and tasks, then stop without product-code changes |
| Approve/implement | `開始實作` / `實作` | Implement and validate tasks only for an approved proposal |
| Revise | State the requirement change | Stop code changes, update the proposal, and wait for reapproval |
| Archive | `歸檔 <short-name>` | Archive only after reliable task completion and user acceptance |
| Abandon | `放棄` / `取消提案`, then `確認放棄 <short-name>` | Show a read-only preflight first; never revert code or Git |

Invoke the workflow explicitly with `$sdd-workflow` or `/sdd-workflow`. The
Skill does not expand its trigger surface for generic “analysis” or “cancel”
requests.

A standalone `取消` only asks whether you mean a code/Git rollback or SDD
proposal abandonment. Source-control rollback is a separate operation and
never changes proposal state as a side effect.

The bundled CLI is authoritative for proposal state, task progress, snapshots,
metadata, archives, and INDEX. Do not manually edit status, checkboxes, `.sdd`
metadata, archive directories, or `INDEX.md`. Follow stable error `code` and
`action` values; never use guessing or repeated commands to hide inconsistent
state.

## v1.0.1

This patch release keeps proposal schemas v1/v2, JSON output v1, and the
existing Skill workflow compatible. It fixes:

- reapproval after an authorized revision appends or removes trailing pending tasks;
- safe reapproval retry after an interrupted manifest or metadata write; and
- false success from mutation commands on readable but non-mutation-compatible legacy proposals.

Replace the complete package when updating. Never mix files from different
releases.

## Documentation

- Install, update, and remove: [`docs/install-methods.md`](./docs/install-methods.md)
- Team handoff and worktrees: [`docs/team-operations.md`](./docs/team-operations.md)
- Diagnostics and recovery: [`docs/troubleshooting.md`](./docs/troubleshooting.md)
- Release history: [`CHANGELOG.md`](./CHANGELOG.md)
- Contributing and tests: [`CONTRIBUTING.en.md`](./CONTRIBUTING.en.md)

The single maintained source is
[`skills/sdd-workflow/`](./skills/sdd-workflow/). Installed copies are not a
second source of truth.

## Acknowledgements

This repository and Skill are inspired by
[SimpleSDD](https://gist.github.com/kaochenlong/27ade9a6218244c2584777fa276d1214),
shared by @kaochenlong at the 2026 AI conference.

## License

MIT (see [LICENSE](./LICENSE))
