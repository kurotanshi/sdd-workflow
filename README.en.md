# sdd-workflow

> Version v1.0.2 ｜ [繁體中文](./README.md)

An **SDD (Spec-Driven Development) Skill** for coding agents such as Claude Code and Codex.

Its goal is to help AI Agents complete most change tasks by turning the expected
outcome into a reviewable, testable specification before implementation.
Features, fixes, refactors, maintenance, and documentation use the same
framework, reducing wrong scope, missed acceptance, and stale requirements.

SDD is not limited to large projects. Small edits use concise proposals; complex
work describes more tasks and acceptance conditions. Both retain “agree first,
then implement and verify,” with state that can recover across sessions. This
repository contains a complete Skill package, not a protocol, SDK, or developer kit.

## Skill goals

- Define the goal, scope, and observable acceptance results so the Agent knows what completion means.
- Split work into independently verifiable tasks and implement only an explicitly approved proposal.
- Implement and verify one task at a time instead of producing a large batch that is difficult to review.
- Stop code changes when requirements change, revise the proposal, and wait for reapproval.
- Recover authoritative state across sessions, handoffs, failed writes, and archival.
- Fail closed when state or evidence is inconsistent instead of guessing or silently repairing it.

## Good fits

Most tasks that produce an observable project change fit the SDD framework,
including:

- adding a feature, API, CLI, configuration, or automation;
- fixing a reproducible bug and adding regression validation;
- refactoring code or architecture while preserving existing behavior;
- updating dependencies, CI, operations settings, documentation, or public guidance;
- researching a bounded question and recording an evidence-based conclusion; and
- work that benefits from cross-session recovery, Agent handoff, revisions, or traceable approval.

## Install

The bundled state-management CLI requires CPython 3.11 or newer. macOS and Linux
are supported; Windows is best effort. Everyday use remains Agent-driven, so you
do not operate the Python CLI yourself. Install the complete
`skills/sdd-workflow/` directory, not only `SKILL.md`.

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

1. Use `提案` to describe the result you want. Small changes fit too:

   ```text
   $sdd-workflow 提案 Fix the health-check API returning 500 when the database is offline
   ```

   Claude Code uses `/sdd-workflow 提案 …`. The Agent creates
   `sdd/<short-name>/proposal.md` and `tasks.md`, records the expected outcome
   and acceptance conditions, validates them, and stops without changing
   product code.

2. Review the proposal, then reply `開始實作`. The Agent approves that version,
   then implements and verifies one task at a time. Plain `實作` never approves a draft.

3. State changed requirements. The Agent revises the proposal and waits for a new `開始實作`.

4. Accept the completed result, then reply `歸檔 <short-name>` to move it under `sdd/archive/`.

Replay the example with `python3 examples/sample-web-api/run-walkthrough.py`.

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

## Task size and workflow

The amount of specification should match the task, but this Skill does not
skip safety boundaries merely because a change is small:

- Small edit: use a concise proposal, often with one task and a directly observable acceptance result.
- Typical feature or fix: split distinct outcomes into independently verifiable tasks.
- Cross-module or high-risk work: state the impact, regression validation, revision, and recovery considerations.

Every size follows `proposal → explicit approval → task-by-task implementation
and verification → user acceptance → archive`. This makes results easier to
check, but does not guarantee that an Agent never makes a mistake; acceptance
conditions and actual validation remain the evidence of completion.

## Usually unnecessary

- Read-only questions, code explanations, or status checks that do not change the project.
- Open-ended exploration without a bounded question and observable conclusion.
- Git/code rollback, emergency recovery, or deployment; these are outside SDD proposal state.
- Generic cancellation that does not target an SDD proposal.

## v1.0.2

This patch positions the Skill to help AI Agents use SDD for most observable
change tasks and clarifies small-task and bundled-Python-runtime usage. It does
not change Skill triggers, the proposal lifecycle, approval boundaries,
schemas, or JSON output.

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
