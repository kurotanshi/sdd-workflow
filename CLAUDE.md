# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A cross-tool **Agent Skill** package: a Spec-Driven Development (SDD) workflow (`提案 → 實作 → 歸檔`) shared by Claude Code (`/sdd-workflow`) and Codex (`$sdd-workflow`). There is no application code, build system, or test suite — the deliverables are the skill itself and its documentation.

## Single source of truth (most important rule)

**All workflow behavior lives in exactly one file: `skills/sdd-workflow/SKILL.md`.**

- Copies installed to `~/.claude/skills/`, `~/.codex/skills/`, or `~/.agents/skills/` are regenerable install artifacts, never a second source. Never edit only an installed copy.
- Do not create per-tool command/prompt variants (e.g. Claude slash commands, Codex prompts). Cross-tool differences appear only in invocation syntax documented in the READMEs, never in workflow rules. Earlier `commands/{propose,implement,archive}.md` and a public `install.sh` were deliberately removed for this reason (see CHANGELOG).
- `skills/sdd-workflow/agents/openai.yaml` carries Codex UI/invocation metadata only (`display_name`, `short_description`, `default_prompt`); it must never carry workflow rules. The `default_prompt` must mention the skill as `$sdd-workflow`.
- The skill folder stays clean: only `SKILL.md` and `agents/openai.yaml` (plus `scripts/`/`references/`/`assets/` only if the skill itself needs them). User-facing docs (README, CHANGELOG, install instructions) live at the repo root, never inside the skill folder.

## Language conventions

- The skill body (`SKILL.md` instructions) is written in **English** for cross-tool maintainability.
- Trigger words (`提案`, `實作`/`開始實作`, `歸檔`) and all user-facing output of the workflow stay in **Traditional Chinese**.
- `README.md` (zh-TW) and `README.en.md` are a bilingual pair — keep them in sync when changing either.

## Commands

Dev-link the canonical skill into local tools for live editing (author tool, not an installer):

```bash
scripts/link-dev.sh                # link into both Claude Code and Codex
scripts/link-dev.sh --claude-only  # or --codex-only
scripts/link-dev.sh --unlink       # remove links created by this repo
```

The script only creates a symlink when the destination does not exist, and only removes symlinks that resolve to this repo; target dirs are overridable via `CLAUDE_SKILLS_DIR` / `CODEX_SKILLS_DIR` (used for hermetic testing).

Validate skill structure/frontmatter before a PR (requires Codex skill-creator locally):

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/sdd-workflow
```

## Verification model

Automation can only cover static and hermetic checks (skill structure, frontmatter, docs, link-dev.sh behavior). **Actual workflow acceptance must be done by a human in fresh interactive sessions** of each tool — a skill change may require a new session to load, and "not loaded" must not be mistaken for "passed". See CONTRIBUTING.md for the full acceptance checklist.

## Repo's own `sdd/` directory

This repo dogfoods its own workflow: `sdd/archive/` holds completed change proposals (e.g. `sdd/archive/2026-07-22-shareable-v1/`). Active changes would live at `sdd/<short-name>/` with `proposal.md` + `tasks.md`. Never treat archived directories as active changes, and never delete or merge archive contents silently.
