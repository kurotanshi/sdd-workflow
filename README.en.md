# sdd-workflow

> Version v0.1.0 ｜ [繁體中文](./README.md)

A cross-agent **SDD (Spec-Driven Development)** skill. One idea: **before writing any code, state clearly what will be done, get it approved, then build.**

Every request is split into three phases. Each phase stops and waits for your confirmation instead of running ahead:

| Phase | Trigger | What it does |
| --- | --- | --- |
| 1. Propose | `提案` | Pick a short name, classify the change (feature / bug fix / refactor), produce `sdd/<short-name>/proposal.md` and `tasks.md`, then **stop and wait — no code yet** |
| 2. Implement | `實作` / `開始實作` | Work the `tasks.md` checklist one item at a time, reporting after each; stop and ask if the spec turns out wrong |
| 3. Archive | `歸檔` | Once every item is checked, move `sdd/<short-name>/` to `sdd/archive/<date>-<short-name>/` |

All artifacts are plain text under your project's `sdd/` directory, version-controlled with git.

**The single maintained source of the workflow is [`skills/sdd-workflow/SKILL.md`](./skills/sdd-workflow/SKILL.md).** Copies installed into each tool are reproducible install artifacts, not a second source of truth.

> The trigger words above (`提案` / `實作` / `歸檔`) are intentionally Traditional Chinese, and so is the workflow's user-facing output. The skill instructions themselves are written in English for cross-tool maintainability.

## Supported tools and trigger syntax

| Tool | Explicit trigger | Natural-language trigger |
| --- | --- | --- |
| [Claude Code](https://claude.com/claude-code) (Anthropic) | `/sdd-workflow 提案 …` | Just say `提案: …` / `開始實作` / `歸檔` |
| [Codex](https://github.com/openai/codex) (OpenAI/GPT) | `$sdd-workflow 提案 …` | Just say `提案: …` / `開始實作` / `歸檔` |

Explicit syntax is preferred (clear and predictable); natural-language triggering is a convenience that relies on the model selecting the skill from its description.

## Usage

After installation, start from a **fresh conversation / session** with the explicit syntax so you can confirm the tool loaded the skill:

```text
# Claude Code
/sdd-workflow 提案 Create a test text file

# Codex
$sdd-workflow 提案 Create a test text file
```

The normal workflow has three steps:

1. **Propose**: the agent creates `sdd/<short-name>/proposal.md` and `sdd/<short-name>/tasks.md`, then stops for your approval. It should not change product code in this step.
2. **Implement**: after reviewing the proposal, explicitly reply with `開始實作` or `實作`. The agent works through `tasks.md` one item at a time, checks off each completed item, and reports progress. If the spec turns out wrong, it should stop and ask.
3. **Archive**: after you accept the result, reply with `歸檔`. The agent verifies every task is complete, then moves `sdd/<short-name>/` to `sdd/archive/<date>-<short-name>/`.

Natural-language triggering is also supported, for example `提案: Create a test text file`. If your tool does not automatically pick the skill, use the explicit syntax in the table above.

## Installation

Choose one of the channels below. Each channel's installer manages its own destination; this repo does not ship its own end-user installer.

### 1. Codex native (built-in skill-installer)

Ask Codex to install from this repo:

```
$skill-installer install kurotanshi/sdd-workflow path skills/sdd-workflow from GitHub
```

This runs `install-skill-from-github.py --repo kurotanshi/sdd-workflow --path skills/sdd-workflow`, installs into `~/.codex/skills/sdd-workflow/`, and becomes available on the **next turn**.

### 2. Cross-agent Skills CLI (third party)

[`npx skills`](https://skills.sh/) is a package manager for the open agent-skills ecosystem, targeting many agents at once:

```bash
npx skills add kurotanshi/sdd-workflow --skill sdd-workflow -g -y
```

`-g` installs at user level, `-y` skips prompts. The source is recorded in that tool's lock file.

> ⚠️ **This is a third-party tool (skills.sh), not an official OpenAI or Anthropic installer.** It places the skill in the shared `~/.agents/skills/`. **Verify your agent actually loads that directory** — different tools read different skill paths (e.g. Codex's own toolchain uses `~/.codex/skills`). If it isn't picked up, use channel 1 or 3.

### 3. Manual copy (fallback)

Copy the **entire `skills/sdd-workflow/` folder** (including `agents/`, not just `SKILL.md`) into your tool's user-level skills directory:

```bash
# Claude Code (v2.1.203+ also supports a symlinked skill)
cp -R skills/sdd-workflow ~/.claude/skills/sdd-workflow

# Codex
cp -R skills/sdd-workflow ~/.codex/skills/sdd-workflow
```

## Update and remove

| Channel | Update | Remove |
| --- | --- | --- |
| Codex skill-installer | Delete `${CODEX_HOME:-$HOME/.codex}/skills/sdd-workflow`, then reinstall (the installer aborts on an existing dir) | Delete `${CODEX_HOME:-$HOME/.codex}/skills/sdd-workflow` |
| Skills CLI (third party) | `npx skills update sdd-workflow -g -y` | `npx skills remove sdd-workflow -g -y` |
| Manual copy | Delete the old folder, then copy the full `skills/sdd-workflow/` folder again | Delete the folder you copied |

## Authors / contributors: local development

To **edit this repo's skill** and have changes take effect live, use the dev-link script to symlink the repo's canonical skill folder into a tool's skills directory (**this is an author tool, not an end-user install path**):

```bash
scripts/link-dev.sh                # link into Claude Code and Codex
scripts/link-dev.sh --claude-only  # Claude only
scripts/link-dev.sh --codex-only   # Codex only
scripts/link-dev.sh --unlink       # remove dev links this repo created
scripts/link-dev.sh --help
```

It only creates a symlink at a **non-existing** destination, and only removes a symlink that **resolves to this repo**; any other existing file / directory / symlink is left untouched. Override target dirs with `CLAUDE_SKILLS_DIR` / `CODEX_SKILLS_DIR` (for hermetic testing or a verified Codex skill root).

> Before relying on a symlinked skill, confirm it actually loads in a **fresh session** of both Claude Code and Codex.

## License

MIT (see [LICENSE](./LICENSE))
