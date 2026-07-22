# sdd-workflow

> Version v0.1.0 ｜ [繁體中文](./README.md)

A cross-agent **SDD (Spec-Driven Development)** skill. One idea: **before writing any code, state clearly what will be done, get it approved, then build.**

Every request is split into three phases, with revision and abandonment paths. The workflow stops wherever approval is required:

| Phase | Trigger | What it does |
| --- | --- | --- |
| 1. Propose | `提案` | Pick a short name and type, produce `proposal.md` and `tasks.md` with status `draft`, then **stop and wait — no code yet**; use the same trigger to revise a proposal |
| 2. Implement | `開始實作` / `實作` | `開始實作` approves a `draft` as `approved`; `實作` only continues an approved proposal. Then implement, validate, check off, and report one task at a time |
| 3. Archive | `歸檔` | After acceptance and full task completion, obtain the system date, archive as `completed`, and update `sdd/archive/INDEX.md` |
| Abandon | `放棄` / `取消` | Mark the active proposal `abandoned`, move it to an archive directory with an `-abandoned` suffix, and update the index |

All artifacts are plain text under your project's `sdd/` directory, version-controlled with git.

The **single maintained source** of the workflow is [`skills/sdd-workflow/SKILL.md`](./skills/sdd-workflow/SKILL.md). Copies installed into each tool are reproducible install artifacts, not a second source of truth.

> The trigger words (`提案` / `開始實作` / `實作` / `歸檔` / `放棄` / `取消`) are intentionally Traditional Chinese, and so is the workflow's user-facing output. The skill instructions themselves are written in English for cross-tool maintainability.

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
    Note over User, Files: Other paths: revision resets draft; abandonment archives as abandoned and updates INDEX.md

    Note over User, Agent: 2. Implement Phase
    User->>Agent: "開始實作" (Approve and start)
    Agent->>Files: Persist approved status and re-read it
    loop Execute tasks one by one
        Agent->>Files: Implement the first unchecked task in tasks.md
        Agent->>Agent: Run tests/validation
        Agent->>Files: Check off task ( [ ] -> [x] )
        Agent->>User: Report "Task N completed"
    end
    Agent->>User: All tasks completed, request verification

    Note over User, Agent: 3. Archive Phase
    User->>Agent: "歸檔" (Archive)
    Agent->>Files: Verify all tasks are checked
    Agent->>Files: Get system date, mark completed, and move to archive
    Agent->>Files: Append one line to sdd/archive/INDEX.md
    Agent->>User: Report "Archive complete" with one-line summary
```

### Directory Structure

```text
Project Root/
└── sdd/
    ├── <short-name>/         # Active change proposal (e.g., sdd/add-health-check/)
    │   ├── proposal.md       # Status, type, rationale, and impact area
    │   └── tasks.md          # Up to 10 independently verifiable tasks plus acceptance criteria
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

## Usage

Trigger syntax for both tools:

| Tool | Explicit trigger | Natural-language trigger |
| --- | --- | --- |
| [Claude Code](https://claude.com/claude-code) (Anthropic) | `/sdd-workflow 提案 …` | Say `提案: …` / `開始實作` / `實作` / `歸檔` / `放棄` / `取消` |
| [Codex](https://github.com/openai/codex) (OpenAI/GPT) | `$sdd-workflow 提案 …` | Say `提案: …` / `開始實作` / `實作` / `歸檔` / `放棄` / `取消` |

Explicit syntax is preferred (clear and predictable); natural-language triggering is a convenience that relies on the model selecting the skill from its description. If your tool does not automatically pick the skill, use the explicit syntax.

The normal workflow has three steps:

1. **Propose**: the agent creates `proposal.md` and `tasks.md` with status `draft`. Each task represents one independently verifiable behavior change, with at most 10 tasks in the full checklist. The agent then stops for approval without changing product code.
2. **Implement**: after reviewing the proposal, reply with `開始實作`. The agent persists `approved`, re-reads it, then completes one task at a time. If a proposal is still `draft` and you say only `實作`, the agent asks for approval instead of changing code. If the specification must change, it stops, preserves completed history, revises the artifacts, resets to `draft`, and waits for approval again.
3. **Archive**: after accepting the result, reply with `歸檔`. The agent counts only task checkboxes before the acceptance criteria, requires at least one and all completed, obtains the date from the execution environment, marks the proposal `completed`, moves it to `sdd/archive/<date>-<short-name>/`, and appends its summary to `INDEX.md`.

For an active proposal that will not proceed, reply with `放棄` or `取消`. The agent marks it `abandoned`, moves it to `sdd/archive/<date>-<short-name>-abandoned/`, and records it in the same `INDEX.md`. The workflow does not create git commits unless you ask.

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
