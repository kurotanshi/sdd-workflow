# sdd-workflow

> Version v0.6.0 ｜ [繁體中文](./README.md)

A cross-agent **SDD (Spec-Driven Development)** skill. One idea: **before writing any code, state clearly what will be done, get it approved, then build.**

Every request is split into three phases, with revision and abandonment paths. The workflow stops wherever approval is required:

| Phase | Trigger | What it does |
| --- | --- | --- |
| 1. Propose | `提案` | Pick a short name and type, produce `proposal.md` and `tasks.md` with status `draft`, then **stop and wait — no code yet**; use the same trigger to revise a proposal |
| 2. Implement | `開始實作` / `實作` | `開始實作` asks the CLI to approve a `draft`; `實作` only continues an approved proposal. Each task is implemented and validated before the CLI records completion |
| 3. Archive | `歸檔` | After acceptance and full task completion, the CLI stages terminal state, commits the directory move, and rebuilds `sdd/archive/INDEX.md` |
| Abandon | `放棄` / `取消提案` → `確認放棄 <short-name>` | Run the bundled CLI's read-only preflight first: report progress, warn that working-tree code is not reverted, and print its snapshot hashes; format errors in `tasks.md` only make counts unreliable. After an exact `確認放棄 <short-name>`, rerun preflight and machine-compare snapshots before the CLI archives as `abandoned` and rebuilds the index; a bare `取消` only asks what to cancel |

All artifacts are plain text under your project's `sdd/` directory, version-controlled with git.

The **single maintained source** of the workflow is [`skills/sdd-workflow/SKILL.md`](./skills/sdd-workflow/SKILL.md). Copies installed into each tool are reproducible install artifacts, not a second source of truth.

The staged engineering plan and design trade-offs for the deterministic parser, transaction engine, and later schema work are documented in [`ROADMAP.md`](./ROADMAP.md).

> The direct trigger words (`提案` / `開始實作` / `實作` / `歸檔` / `放棄` / `取消提案` / `確認放棄 <short-name>`) are intentionally Traditional Chinese, and so is the workflow's user-facing output. A standalone `取消` (without a target) is not a direct Skill trigger; the cancellation disambiguation rule applies only after the user explicitly refers to an SDD proposal or has entered the workflow. An explicit code-revert request stays outside SDD, but its exact scope must be confirmed before changing files and it must never alter proposal state. The skill instructions themselves are written in English for cross-tool maintainability.

## Install and get started

> [!IMPORTANT]
> **Post-installation note**: After installing or updating the skill, you usually need to **start a fresh conversation session** (e.g., restart Claude Code) for it to be loaded; in an already-open session the agent may not recognize the newly installed skill. Exception: when installed via Codex's built-in skill-installer, the skill becomes available on the **next turn** of the same conversation.

Pick the path for your tool. Each channel's installer manages its own destination; this repo does not ship its own end-user installer.

### Codex

Ask Codex's built-in skill-installer to install from this repo:

```text
$skill-installer install skills/sdd-workflow from the GitHub repo kurotanshi/sdd-workflow
```

This runs `install-skill-from-github.py --repo kurotanshi/sdd-workflow --path skills/sdd-workflow`, installs into `~/.codex/skills/sdd-workflow/`, and becomes available on the **next turn**. (Manual install: copy the whole `skills/sdd-workflow/` folder to `~/.codex/skills/sdd-workflow`.)

Verify in a fresh Codex conversation:

```text
$sdd-workflow 提案 Add a health-check API to my project
```

### Claude Code

Claude Code has no built-in "install a skill from GitHub" command; the fastest way is to ask it to install the skill itself:

```text
Install skills/sdd-workflow from https://github.com/kurotanshi/sdd-workflow into ~/.claude/skills/sdd-workflow
```

If you'd rather not let the agent run commands, install manually:

```bash
rm -rf /tmp/sdd-workflow
git clone https://github.com/kurotanshi/sdd-workflow.git /tmp/sdd-workflow
mkdir -p ~/.claude/skills
cp -R /tmp/sdd-workflow/skills/sdd-workflow ~/.claude/skills/sdd-workflow
```

> Copy the **entire `skills/sdd-workflow/` folder** (including `agents/`, not just `SKILL.md`). If `~/.claude/skills/sdd-workflow` already exists (reinstall), delete the old folder first. Claude Code v2.1.203+ also supports a symlinked skill.

Verify in a fresh Claude Code session:

```text
/sdd-workflow 提案 Add a health-check API to my project
```

### Other channel: cross-agent Skills CLI (third party)

[`npx skills`](https://skills.sh/) is a package manager for the open agent-skills ecosystem, targeting many agents at once:

```bash
npx skills add kurotanshi/sdd-workflow --skill sdd-workflow -g -y
```

`-g` installs at user level, `-y` skips prompts. The source is recorded in that tool's lock file.

> ⚠️ This is a third-party tool (skills.sh), not an official OpenAI or Anthropic installer. It places the skill in the shared `~/.agents/skills/`. **Verify your agent actually loads that directory** — different tools read different skill paths (e.g. Codex's own toolchain uses `~/.codex/skills`). If it isn't picked up, use the native install path for your tool above.

## Workflow

```mermaid
sequenceDiagram
    actor User
    participant Agent as AI Coding Agent
    participant Files as sdd/ Directory

    Note over User, Agent: 1. Propose Phase
    User->>Agent: "提案: Add OOO feature"
    Agent->>Files: Create draft proposal.md & tasks.md
    Agent->>User: Display proposal spec, checklist, and acceptance criteria
    Note over Agent: Stop and wait — no code modification yet
    Note over User, Files: Other paths: revision resets draft. Abandonment runs a preflight and archives as abandoned only after "確認放棄 SHORT_NAME" and then updates INDEX.md

    Note over User, Agent: 2. Implement Phase
    User->>Agent: "開始實作" (Approve and start)
    Agent->>Files: CLI approve writes manifest, metadata, and approved status
    loop Execute tasks one by one
        Agent->>Files: Implement the first unchecked task in tasks.md
        Agent->>Agent: Run tests/validation
        Agent->>Files: CLI complete-task validates snapshot and writes [x]
        Agent->>User: Report "Task N completed"
    end
    Agent->>User: All tasks completed, request verification

    Note over User, Agent: 3. Archive Phase
    User->>Agent: "歸檔" (Archive)
    Agent->>Files: Verify all tasks are checked
    Agent->>Files: CLI archive marks completed and commits the move
    Agent->>Files: Rebuild INDEX.md from all archive records
    Agent->>User: Report "Archive complete" with one-line summary
```

### Directory Structure

```text
Project Root/
└── sdd/
    ├── <short-name>/         # Active change proposal (e.g., sdd/add-health-check/)
    │   ├── proposal.md       # Schema v2, status, type, rationale, and impact area
    │   ├── tasks.md          # Top-level checkbox task list (up to 10 for a new proposal) plus acceptance criteria
    │   └── .sdd/             # Approval manifest, attestation, and operation evidence
    └── archive/              # Completed and abandoned history
        ├── INDEX.md          # Date, short name, terminal status, and one-line summary
        ├── YYYY-MM-DD-<short-name>/
        │   ├── proposal.md   # Status: completed
        │   └── tasks.md      # All tasks checked ([x])
        └── YYYY-MM-DD-<short-name>-abandoned/
            ├── proposal.md   # Status: abandoned
            └── tasks.md
```

### Preview of Generated Artifacts

`sdd/<short-name>/proposal.md` Example:

```markdown
---
schema_version: 2
---
# add-health-check

## 狀態 (Status)
draft

## 類型 (Type)
新功能 (New Feature)

## 為什麼做 (Why)
為了讓監控系統能確認服務是否正常運作。
(Allow monitoring systems to verify service availability.)

## 要改什麼 (Scope of Changes)
- 新增 `/api/health` 路由，回傳 JSON `{"status": "ok"}`。

## 影響範圍 (Impact Area)
- 新增 (New): `src/routes/health.js`
- 修改 (Modified): `src/app.js`
```

`sdd/<short-name>/tasks.md` Example:

```markdown
- [ ] 1. Create health check route file handling GET /api/health
- [ ] 2. Register route in main app.js
- [ ] 3. Add unit test to verify status ok response

## 驗收條件 (Acceptance Criteria)
- 情境：當發送 GET 請求至 /api/health，應收到 200 狀態碼與 JSON `{"status": "ok"}`
  (Scenario: send a GET request to /api/health, expect a 200 status code and JSON `{"status": "ok"}`)
```

> In the real artifacts, headings and content are Traditional Chinese (per the skill's template, regardless of tool); the English in these two examples is added for readability only.

## Usage

Trigger syntax for both tools:

| Tool | Explicit trigger | Natural-language trigger |
| --- | --- | --- |
| [Claude Code](https://claude.com/claude-code) (Anthropic) | `/sdd-workflow 提案 …` | Say `提案: …` / `開始實作` / `實作` / `歸檔` / `放棄` (executing abandonment also needs `確認放棄 <short-name>`) |
| [Codex](https://github.com/openai/codex) (OpenAI/GPT) | `$sdd-workflow 提案 …` | Say `提案: …` / `開始實作` / `實作` / `歸檔` / `放棄` (executing abandonment also needs `確認放棄 <short-name>`) |

Explicit syntax is preferred (clear and predictable); natural-language triggering is a convenience that relies on the model selecting the skill from its description. If your tool does not automatically pick the skill, use the explicit syntax.

The normal workflow has three steps:

1. **Propose**: the agent creates `proposal.md` and `tasks.md` with status `draft`. Each task represents one independently verifiable behavior change, with at most 10 tasks in the full checklist; every task checkbox sits at the first column in one top-level list, with no checkbox subtasks. The agent then stops for approval without changing product code.
2. **Implement**: after reviewing the proposal, reply with `開始實作`. The agent persists `approved`, re-reads it, then completes one task at a time. If a proposal is still `draft` and you say only `實作`, the agent asks for approval instead of changing code. If the specification must change, it stops, preserves completed history, revises the artifacts, resets to `draft`, and waits for approval again; checked tasks are history and do not count against the quota, a revision keeps at most 10 unchecked tasks, and an amendment that materially changes the goal is redirected to a new change.
3. **Archive**: after accepting the result, reply with `歸檔`. The agent counts only first-column, top-level task checkboxes before the acceptance criteria and requires at least one with all completed; any malformed checkbox line — indented, nested, or variants like `- [X]` — stops the archive with its line number reported, and so does any other list item in the task region, including one that starts with a markdown link such as `- [參考](https://…)`. It then obtains the date from the execution environment, marks the proposal `completed`, moves it to `sdd/archive/<date>-<short-name>/`, and appends its summary to `INDEX.md`.

**Abandonment and Disambiguation Rules**:

- **Proposal Abandonment (Two-step process)**:
  1. **Request Abandonment**: Reply with `放棄`, `放棄 <short-name>`, or `取消提案`. The agent calls the bundled CLI for a **read-only preflight**: it reports status, progress, and snapshot hashes, and warns that implementation code and git changes in the working tree are **never reverted automatically**. Task-format errors do not block preflight, but counts are marked unreliable.
  2. **Confirm Abandonment**: After the exact phrase `確認放棄 <short-name>`, the agent reruns CLI preflight and has the execution environment **machine-compare** snapshot hashes. An unchanged snapshot permits `abandoned`, the move to `sdd/archive/<date>-<short-name>-abandoned/`, and the `INDEX.md` update. A mismatched snapshot or new session prompts for a fresh preflight.
- **Disambiguation and Revert Boundaries**:
  - **Standalone "取消"**: A standalone or unclear `取消` only asks which target you mean to prevent unintended actions.
  - **Code Revert**: An explicit code cancellation (e.g. "cancel recent code changes") remains a separately confirmed revert outside SDD and **never alters proposal state**.
  - **Git Commit**: The workflow creates no git commit unless requested.

## v0.6 schema, runtime, and team contract

- **System and Runtime Requirements**:
  - **Python Version**: Requires **CPython 3.11 or newer**. (The runtime introduced in v0.3.0 was a **breaking minor** within `0.x` and remains required).
  - **Supported Platforms**: macOS and Linux are fully supported; Windows currently receives a best-effort Python core.
- **Schema v2 and Proposal Specifications**:
  - **Proposal Types**: New proposals use explicit Schema v2 and may be classified as `新功能`, `修 bug`, `重構`, `維運`, `文件`, or `研究` (Research uses the same lifecycle and stores output under `## 結論`).
  - **Compatibility and Fail-Closed**: Existing v1/legacy artifacts are never migrated in place. A missing CLI or runtime fails closed and never falls back to direct parsing or managed-state edits. An in-flight proposal with `.sdd` machine metadata must finish or be abandoned under a compatible engine; deleting metadata or the schema marker is not a supported downgrade. See [`docs/schema-v2.md`](./docs/schema-v2.md), [`docs/runtime.md`](./docs/runtime.md), [`docs/cli-contract.md`](./docs/cli-contract.md), and [`docs/transaction-protocol.md`](./docs/transaction-protocol.md).
  - **Version Verification**: After installing or upgrading, run `skills/sdd-workflow/scripts/sdd.py --version` from the package, using the corresponding path in an installed copy.
- **Team Concurrency and Data Authority**:
  - **Owner Mechanism**: For team concurrency, one proposal has one owner at a time. Independent changes use different short names and, when implementation trees may interfere, separate Git worktrees.
  - **INDEX and Archive**: Archive directories are authoritative; `INDEX.md` is a derived artifact checked and reconstructed by `validate-index` / `rebuild-index`. The v0.6.0 contention tests found no authoritative data loss, so the release does not add a speculative lock or INDEX CAS. See [`docs/team-operations.md`](./docs/team-operations.md) and [`docs/compatibility.md`](./docs/compatibility.md) for handoff, worktree, version-skew, and stale-INDEX procedures.

## Update and remove

| Tool / channel | Update | Remove |
| --- | --- | --- |
| Codex | Delete `${CODEX_HOME:-$HOME/.codex}/skills/sdd-workflow`, then reinstall (the installer aborts on an existing dir) | Delete `${CODEX_HOME:-$HOME/.codex}/skills/sdd-workflow` |
| Claude Code | Delete `~/.claude/skills/sdd-workflow`, then reinstall | Delete `~/.claude/skills/sdd-workflow` |
| Skills CLI (third party) | `npx skills update sdd-workflow -g -y` | `npx skills remove sdd-workflow -g -y` |

## Authors / contributors: local development

> This section is only for people **editing this repo's skill itself**. Regular users should install via "Install and get started" above.

Normal installation is a **copy**: your tool reads the copy under `~/.claude/skills/` or `~/.codex/skills/`. Editing `SKILL.md` in this repo does not change that copy, so you would have to re-copy after every edit to test anything.

`scripts/link-dev.sh` replaces the copy with a symlink, pointing the tool's skills directory straight at this repo's `skills/sdd-workflow/`. From then on, any edit in the repo takes effect in the next fresh session:

```bash
scripts/link-dev.sh                # link into Claude Code and Codex
scripts/link-dev.sh --claude-only  # Claude only
scripts/link-dev.sh --codex-only   # Codex only
scripts/link-dev.sh --unlink       # remove the symlinks when done
scripts/link-dev.sh --help
```

The script is deliberately conservative: if the destination already holds a file / directory / other symlink, it stops and touches nothing (it will never overwrite an installed copy); `--unlink` only removes symlinks that provably resolve to this repo. Target directories can be overridden with the `CLAUDE_SKILLS_DIR` / `CODEX_SKILLS_DIR` environment variables (for hermetic testing or a verified Codex skill root).

> After linking, confirm the skill actually loads in a **fresh session** of both Claude Code and Codex.

## Acknowledgements

This repo / skill is inspired by [SimpleSDD](https://gist.github.com/kaochenlong/27ade9a6218244c2584777fa276d1214), shared by @kaochenlong at the 2026 AI conference.

## License

MIT (see [LICENSE](./LICENSE))
