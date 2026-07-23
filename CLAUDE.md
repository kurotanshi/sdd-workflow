# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A cross-tool **Agent Skill** package: a Spec-Driven Development (SDD) workflow (`提案 → 實作 → 歸檔`, with revision and abandonment paths) shared by Claude Code (`/sdd-workflow`) and Codex (`$sdd-workflow`). It has two layers: the skill instructions (`skills/sdd-workflow/SKILL.md`) and a standard-library-only Python deterministic core (`skills/sdd-workflow/scripts/sdd_core/`) with its tests. There is no separate end-user application.

## Commands

All tests are stdlib `unittest`, run from the repo root, Python ≥ 3.11 required. Always set `PYTHONDONTWRITEBYTECODE=1` (installed skills may be symlinked back to this tree; never deposit bytecode in the package).

```bash
# Full unit suite (what CI's `unit` check runs)
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'

# One module / one test
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_parser
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_parser.ClassName.test_name

# Standalone CI checks (not part of unittest discovery)
PYTHONDONTWRITEBYTECODE=1 python3 tests/package_validation.py   # installable-package validation
PYTHONDONTWRITEBYTECODE=1 python3 tests/docs_consistency.py     # duplicated contract facts across docs
sh tests/trigger-contract.sh                                    # trigger-word contract
PYTHONDONTWRITEBYTECODE=1 python3 tests/install_smoke.py        # checkout + installed-package smoke

# Run the deterministic CLI directly
skills/sdd-workflow/scripts/sdd --json --root <project-root> status <short-name>

# Build a deterministic release tarball (refuses to overwrite)
python3 scripts/build-release-package.py

# Dev-link the canonical skill into local tools for live editing (author tool, not an installer)
scripts/link-dev.sh                # link into both Claude Code and Codex
scripts/link-dev.sh --claude-only  # or --codex-only
scripts/link-dev.sh --unlink       # remove links created by this repo
```

`link-dev.sh` only creates a symlink when the destination does not exist, and only removes symlinks that resolve to this repo; target dirs are overridable via `CLAUDE_SKILLS_DIR` / `CODEX_SKILLS_DIR` (used for hermetic testing).

Validate skill structure/frontmatter before a PR (requires Codex skill-creator locally):

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/sdd-workflow
```

## Single source of truth (most important rule)

**All workflow behavior lives in exactly one file: `skills/sdd-workflow/SKILL.md`.**

- Copies installed to `~/.claude/skills/`, `~/.codex/skills/`, or `~/.agents/skills/` are regenerable install artifacts, never a second source. Never edit only an installed copy.
- Do not create per-tool command/prompt variants (e.g. Claude slash commands, Codex prompts). Cross-tool differences appear only in invocation syntax documented in the READMEs, never in workflow rules. Earlier `commands/{propose,implement,archive}.md` and a public `install.sh` were deliberately removed for this reason (see CHANGELOG).
- `skills/sdd-workflow/agents/openai.yaml` carries Codex UI/invocation metadata only (`display_name`, `short_description`, `default_prompt`); it must never carry workflow rules. The `default_prompt` must mention the skill as `$sdd-workflow`.
- The skill folder stays clean: only `SKILL.md`, `agents/openai.yaml`, and `scripts/` (the deterministic core). User-facing docs (README, CHANGELOG, install instructions) live at the repo root, never inside the skill folder.

## Architecture

### Responsibility boundary (Skill vs Python core)

- The Skill (`SKILL.md`) owns user intent, explicit approval, ambiguity resolution, command orchestration, and communication.
- The Python core owns artifact parsing, structural validation, canonical projection, snapshot checks, supported state transitions, and machine diagnostics.
- Agents never recreate structural parsing or state-transition rules in prose; scripts never decide whether implementation semantics satisfy a task. There is no Markdown-parsing fallback — if the CLI fails, the workflow stops.

### Deterministic core (`skills/sdd-workflow/scripts/`)

- `sdd` (sh wrapper) → `sdd.py` (entry, enforces Python ≥ 3.11) → `sdd_core/cli.py`. Subcommands: `validate`, `list --state active`, `status`, `abandon-preflight`, `approve`, `begin-revision`, `complete-task`, `rebuild-index`, `validate-index`, `doctor`, `archive`, `abandon`. `--json` selects the versioned JSON envelope agents consume; errors are typed codes with a stable remediation `action`, and strict diagnostics fail closed **before** any mutation (only abandonment preflight degrades malformed task counts).
- Parsing: `parser_legacy.py` / `parser_v1.py` / `parser_v2.py` behind `model.py` (canonical model). Schema v2 has six explicit proposal types; v1/legacy artifacts are read without migration; unknown future versions fail closed.
- Mutation: `transitions.py` (approve / begin-revision / complete-task) and `terminal_transitions.py` (archive / abandon, sharing one transaction engine where the directory move is the commit point). Managed commands are the only paths that touch existing status, checkboxes, metadata, archive locations, or `INDEX.md`.
- Concurrency: `snapshot.py` produces raw-byte digests used as optimistic concurrency tokens; mutating commands require `--expected-snapshot` and fail with `ERROR_SNAPSHOT_MISMATCH` → `refresh_status` on drift.
- Authority model (when authorities disagree, commands fail with a typed mismatch — never pick a winner by timestamp or writer version): `proposal.md ## 狀態` is the only lifecycle authority (`draft`/`approved`/`completed`/`abandoned`); `tasks.md` checkboxes are the only completion authority; `.sdd/approval-manifest.json` is the approved semantic baseline; `.sdd/metadata.json` is machine evidence. `atomic_write.py` is the shared single-file atomic writer (temp file + fsync + `os.replace`, rejects symlinks).

### Normative docs and fixtures

- `docs/` holds the normative contracts (`architecture.md`, `cli-contract.md`, `schema-v2.md`, `transaction-protocol.md`, `archive-model.md`, `managed-state.md`, `doctor-diagnostics.md`, `compatibility.md`, `team-operations.md`); `docs/decisions/` holds dated decision records. Behavior changes must keep code, docs, and fixtures aligned — `tests/docs_consistency.py` enforces duplicated facts.
- `tests/fixtures/baseline/` and `tests/fixtures/schema-v2/` are governed by their `MANIFEST.json` files and `tests/fixtures/baseline/NORMATIVE_RULES.md`; fixture `sdd/` directories are tracked (the root `.gitignore` anchors `sdd/` to the repo root only).
- Tests must be hermetic: CI checkouts have no repo-root `sdd/` directory, so never depend on it.

### CI contract

Protected branches require five stable checks: `unit`, `fixtures`, `package-validation`, `docs-consistency`, `install-smoke` (unit and install matrices cover macOS/Linux × Python 3.11/latest). Adding or renaming a check requires synchronized updates to `.github/workflows/ci.yml`, `tests/test_ci_contract.py`, and `tests/docs_consistency.py`.

## Language conventions

- The skill body (`SKILL.md` instructions), code, and `docs/` contracts are written in **English** for cross-tool maintainability.
- Trigger words (`提案`, `開始實作`, `實作`, `歸檔`, `放棄`, `取消提案`, `確認放棄 <short-name>`) and all user-facing output of the workflow stay in **Traditional Chinese**. Generic cancellation without an explicit SDD proposal target is outside the skill-selection boundary.
- `README.md` (zh-TW) / `README.en.md` and `CONTRIBUTING.md` / `CONTRIBUTING.en.md` are bilingual pairs — keep them in sync when changing either.

## Verification model

Automation covers parser fixtures, CLI behavior, package/runtime checks, docs consistency, and other hermetic rules. **Actual workflow acceptance must still be done by a human in fresh interactive sessions** of each tool — a skill change may require a new session to load, and "not loaded" must not be mistaken for "passed". Acceptance must confirm that structure decisions come from the bundled JSON CLI with no Markdown fallback; new proposals use explicit Schema v2 and its six types; research conclusions remain output while reconstructing from archives; `approve`, `begin-revision`, `complete-task`, `archive`, and `abandon` are the only existing-proposal managed mutation paths; strict diagnostics stop before mutation; abandonment preflight alone degrades malformed task counts; terminal paths share one result procedure and preserve the move commit point; cancellation remains unambiguous; code is never auto-reverted; and no commit is created without a request. See CONTRIBUTING.md for the full matrix.

## Repo's own `sdd/` directory

This repo dogfoods its own workflow, but its `sdd/` directory is **local-only**: it is gitignored and was removed from git history on 2026-07-22 — never commit or push it. Active changes live at `sdd/<short-name>/` with `proposal.md` + `tasks.md` (plus machine-managed `.sdd/`); `proposal.md` persists `draft` or `approved`. Locally, `sdd/archive/` holds completed directories, `-abandoned` directories, and `INDEX.md`; archived proposals persist the terminal status `completed` or `abandoned`. Never treat archived directories as active changes, and never overwrite, delete, or merge archive contents silently.
