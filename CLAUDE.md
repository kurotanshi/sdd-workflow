# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A cross-tool **Agent Skill** package: a Spec-Driven Development (SDD) workflow (`提案 → 實作 → 歸檔`, with revision and abandonment paths) shared by Claude Code (`/sdd-workflow`) and Codex (`$sdd-workflow`). The package includes a standard-library Python deterministic core and its tests; there is no separate end-user application.

## Single source of truth (most important rule)

**All workflow behavior lives in exactly one file: `skills/sdd-workflow/SKILL.md`.**

- Copies installed to `~/.claude/skills/`, `~/.codex/skills/`, or `~/.agents/skills/` are regenerable install artifacts, never a second source. Never edit only an installed copy.
- Do not create per-tool command/prompt variants (e.g. Claude slash commands, Codex prompts). Cross-tool differences appear only in invocation syntax documented in the READMEs, never in workflow rules. Earlier `commands/{propose,implement,archive}.md` and a public `install.sh` were deliberately removed for this reason (see CHANGELOG).
- `skills/sdd-workflow/agents/openai.yaml` carries Codex UI/invocation metadata only (`display_name`, `short_description`, `default_prompt`); it must never carry workflow rules. The `default_prompt` must mention the skill as `$sdd-workflow`.
- The skill folder stays clean: only `SKILL.md` and `agents/openai.yaml` (plus `scripts/`/`references/`/`assets/` only if the skill itself needs them). User-facing docs (README, CHANGELOG, install instructions) live at the repo root, never inside the skill folder.

## Language conventions

- The skill body (`SKILL.md` instructions) is written in **English** for cross-tool maintainability.
- Trigger words (`提案`, `開始實作`, `實作`, `歸檔`, `放棄`, `取消提案`, `確認放棄 <short-name>`) and all user-facing output of the workflow stay in **Traditional Chinese**. Generic cancellation without an explicit SDD proposal target is outside the skill-selection boundary.
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

Automation covers parser fixtures, CLI behavior, package/runtime checks, docs consistency, and other hermetic rules. **Actual workflow acceptance must still be done by a human in fresh interactive sessions** of each tool — a skill change may require a new session to load, and "not loaded" must not be mistaken for "passed". Acceptance must confirm that structure decisions come from the bundled JSON CLI with no Markdown fallback; new proposals use explicit Schema v2 and its six types; research conclusions remain output while reconstructing from archives; `approve`, `begin-revision`, `complete-task`, `archive`, and `abandon` are the only existing-proposal managed mutation paths; strict diagnostics stop before mutation; abandonment preflight alone degrades malformed task counts; terminal paths share one result procedure and preserve the move commit point; cancellation remains unambiguous; code is never auto-reverted; and no commit is created without a request. See CONTRIBUTING.md for the full matrix.

## Repo's own `sdd/` directory

This repo dogfoods its own workflow, but its `sdd/` directory is **local-only**: it is gitignored and was removed from git history on 2026-07-22 — never commit or push it. Active changes live at `sdd/<short-name>/` with `proposal.md` + `tasks.md`; `proposal.md` persists `draft` or `approved`. Locally, `sdd/archive/` holds completed directories, `-abandoned` directories, and `INDEX.md`; archived proposals persist the terminal status `completed` or `abandoned`. Never treat archived directories as active changes, and never overwrite, delete, or merge archive contents silently.
