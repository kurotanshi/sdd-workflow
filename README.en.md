# sdd-workflow

> Version v1.0.0 ｜ [繁體中文](./README.md)

An **SDD (Spec-Driven Development) Skill** for coding agents such as Claude
Code and Codex.

It requires the Agent to write version-controlled scope, tasks, and acceptance
conditions before changing code, wait for explicit approval, and then
implement and validate one task at a time. The product in this repository is a
Skill package, not a protocol, SDK, or developer kit.

## Good fits

- Review scope and acceptance conditions before the Agent may change code.
- Manage multiple verifiable steps across sessions, handoffs, or context recovery.
- Record requirement changes during implementation or acceptance.
- Keep the proposal, task progress, and final archive under version control.

## Usually unnecessary

- Read-only questions, code explanations, exploration, or general research.
- A single low-risk edit that you explicitly asked the Agent to perform directly.
- Git/code rollback, emergency recovery, or deployment; these are outside SDD proposal state.
- Generic cancellation that does not target an SDD proposal.

You can still invoke `$sdd-workflow` or `/sdd-workflow` explicitly. The Skill
does not expand its natural-language trigger surface for generic “analysis” or
“cancel” requests.

## Install

Install the complete `skills/sdd-workflow/` directory, not only `SKILL.md`.
Bundled scripts and references are internal parts of the Skill.

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

1. Create a proposal in the project you want to change:

   ```text
   $sdd-workflow 提案 Add a health-check API to my project
   ```

   Claude Code uses `/sdd-workflow 提案 …`. The Agent creates
   `sdd/<short-name>/proposal.md` and `tasks.md`, validates them, and stops
   without changing product code.

2. Review the proposal, then reply `開始實作`. The Agent approves the current
   proposal and implements, validates, and completes tasks in order. If a
   proposal is still a draft, plain `實作` asks whether you intend to approve
   it.

3. State any changed requirement. The Agent stops implementation, revises the
   proposal, and waits for a new `開始實作`.

4. After every task is complete and you accept the result, reply `歸檔`. The
   proposal moves under `sdd/archive/`.

Replayable example:

```text
python3 examples/sample-web-api/run-walkthrough.py
```

## Workflow and safety boundaries

| Phase | Your action | Agent boundary |
| --- | --- | --- |
| Propose | `提案` | Write and validate the proposal and tasks, then stop without product-code changes |
| Implement | `開始實作` / `實作` | Implement and validate tasks only for an approved proposal |
| Revise | State the requirement change | Stop code changes, update the proposal, and wait for reapproval |
| Archive | `歸檔` | Archive only after reliable task state is fully complete |
| Abandon | `放棄` / `取消提案`, then `確認放棄 <short-name>` | Show a read-only preflight first; never revert code or Git |

A standalone `取消` only asks whether you mean a code/Git rollback or SDD
proposal abandonment. Source-control rollback never changes proposal state.

If the Skill reports inconsistent proposal state, runtime, or evidence, stop
and follow the specific action it provides. Do not manually edit status,
checkboxes, metadata, or archive directories.

Known limitation: in v1.0.0, reapproval may stop with `OUT_OF_BAND_DRIFT` after
a revision appends pending tasks to partially completed work. Do not bypass
approval or repair managed state by hand; preserve the evidence and see
[`docs/troubleshooting.md`](./docs/troubleshooting.md).

## More help

- Installation and updates: [`docs/install-methods.md`](./docs/install-methods.md)
- Team handoff and worktrees: [`docs/team-operations.md`](./docs/team-operations.md)
- Diagnostics and recovery: [`docs/troubleshooting.md`](./docs/troubleshooting.md)
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
