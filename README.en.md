# sdd-workflow

> Version v1.0.0 ｜ [繁體中文](./README.md)

A cross-agent **SDD (Spec-Driven Development) Skill** for coding agents such
as Claude Code and Codex.

It addresses a common failure mode: an Agent starts changing code before the
requirement is clear. sdd-workflow first writes the scope, tasks, and
acceptance conditions into a version-controlled proposal, waits for explicit
approval, and then implements one task at a time. A requirement change returns
to revision and reapproval instead of being smuggled into acceptance.

## Install

Install the complete `skills/sdd-workflow/` directory, not only `SKILL.md`.

### Codex

Use the built-in installer in a Codex conversation:

```text
$skill-installer install skills/sdd-workflow from the GitHub repo kurotanshi/sdd-workflow into ~/.agents/skills
```

The current user-level location is `~/.agents/skills/sdd-workflow/`. Keep the
destination in the request because some installer versions still use an older
default. Codex normally detects a new Skill automatically; restart Codex if it
does not appear on the next turn.

### Claude Code

Ask Claude Code to install the complete package:

```text
Install skills/sdd-workflow from https://github.com/kurotanshi/sdd-workflow into ~/.claude/skills/sdd-workflow
```

The current user-level location is `~/.claude/skills/sdd-workflow/`. Claude
Code normally detects installs and updates automatically; start a fresh
session if the Skill does not appear. Manual installation, the third-party
Skills CLI, verification, updates, and removal are covered in
[`docs/install-methods.md`](./docs/install-methods.md).

## Your first workflow

Open the Agent in the project you want to change, then:

1. Create a proposal:

   ```text
   $sdd-workflow 提案 Add a health-check API to my project
   ```

   Claude Code uses `/sdd-workflow 提案 …`. The Agent creates
   `sdd/<short-name>/proposal.md` and `tasks.md`, presents the canonical scope
   and acceptance conditions, and stops. It does not change product code.

2. After reviewing the proposal, reply with `開始實作`. This explicitly
   approves the current canonical proposal. The Agent then implements,
   validates, and completes one task at a time.

3. If the requirement changes during implementation or acceptance, state the
   new requirement. The Agent stops, begins a managed revision, updates the
   proposal, and stops again for a new `開始實作`.

4. Once every task is complete and you accept the result, reply with `歸檔`.
   The proposal moves under `sdd/archive/`. Managed archive records created by
   the current runtime can be used to rebuild `INDEX.md`.

The complete replayable example is under
[`examples/sample-web-api/`](./examples/sample-web-api/):

```text
python3 examples/sample-web-api/run-walkthrough.py
```

It exercises approval, tasks, scope drift, revision/reapproval, archive, and
INDEX rebuild entirely inside a temporary directory.

## Workflow and safety boundaries

| Phase | Explicit trigger | Guarantee |
| --- | --- | --- |
| Propose | `提案` | Create and validate a `draft`, then stop without product-code changes |
| Implement | `開始實作` / `實作` | The first approves a draft; the second only continues an approved proposal; one task at a time |
| Revise | State the requirement change | Invalidate prior approval, preserve completed history, and return to draft for reapproval |
| Archive | `歸檔` | Create a completed archive only when reliable task state is fully complete |
| Abandon | `放棄` / `取消提案` → `確認放棄 <short-name>` | Read-only preflight first, then mutate only with the same snapshot; never revert code or Git |

The runtime is the sole authority for parsing, snapshots, managed transitions,
and diagnostics. The Agent does not independently parse or directly edit
status, checkboxes, machine metadata, archive locations, or INDEX. A missing
compatible runtime, ambiguous state, or inconsistent evidence fails closed
and hands a specific action back to the human.

A standalone `取消` only asks whether you mean a code/Git rollback or SDD
proposal abandonment. Source-control rollback never changes proposal state.

## Advanced documentation

| Topic | Start here |
| --- | --- |
| Concepts: protocol, approval, schema, archive authority | [`docs/concepts/`](./docs/concepts/) |
| Operations: daily use, team handoff, runtime, release | [`docs/operations/`](./docs/operations/) |
| Compatibility: OS/Python/Agent, installation, version combinations | [`docs/compatibility/`](./docs/compatibility/) |
| Design: architecture, transactions, attestation, ADRs | [`docs/design/`](./docs/design/) |
| Troubleshooting: doctor, installation, recovery | [`docs/troubleshooting/`](./docs/troubleshooting/) |

Protocol and adapter authors can go directly to
[`docs/protocol-draft.md`](./docs/protocol-draft.md), the
[`Agent Adapter Contract`](./docs/protocol/agent-adapter-contract.md), and
[`docs/conformance.md`](./docs/conformance.md).

The **single maintained Skill source** is
[`skills/sdd-workflow/SKILL.md`](./skills/sdd-workflow/SKILL.md). Installed
copies are reproducible package artifacts, not a second workflow source.

Historical engineering plans and design trade-offs are documented in
[`ROADMAP.md`](./ROADMAP.md). The current v1.0 completion status and evidence
are recorded in the
[`v1.0 release gate`](./docs/reports/v1.0-release-gate.md).

## Local development

Regular users do not need this section. Contributors editing this repository
can test through symlinks:

```text
scripts/link-dev.sh
scripts/link-dev.sh --claude-only
scripts/link-dev.sh --codex-only
scripts/link-dev.sh --unlink
```

The default destinations are `~/.claude/skills/` and `~/.agents/skills/`.
Existing destinations are never overwritten. See
[`docs/operations/`](./docs/operations/) for the full test, conformance, and
release gates.

## Acknowledgements

This repository and Skill are inspired by
[SimpleSDD](https://gist.github.com/kaochenlong/27ade9a6218244c2584777fa276d1214),
shared by @kaochenlong at the 2026 AI conference.

## License

MIT (see [LICENSE](./LICENSE))
