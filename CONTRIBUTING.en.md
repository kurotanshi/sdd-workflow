# Contributing to sdd-workflow

> [繁體中文](./CONTRIBUTING.md)

Thanks for contributing! This document explains the maintenance rules of this repo.

## Single source of truth: the canonical skill

**All workflow behavior may only be changed in one file: [`skills/sdd-workflow/SKILL.md`](./skills/sdd-workflow/SKILL.md).**

- The three phases (提案 / 實作 / 歸檔), revision/abandonment paths, state transitions, artifact formats, and progress-reporting rules all live there.
- Copies installed into `~/.claude/skills/`, `~/.codex/skills/`, or `~/.agents/skills/` are **reproducible install artifacts**, never a second source of truth. **Never** edit only the copy inside a tool's directory — that causes divergence.
- Do not add per-tool command/prompt variants. Cross-tool differences appear only in *how the skill is invoked* (the trigger-syntax table in the README), never in workflow rules.

## Repo layout

```
sdd-workflow/
├── README.md / README.en.md    # Bilingual user documentation
├── CONTRIBUTING.md / CONTRIBUTING.en.md
├── CHANGELOG.md
├── LICENSE
├── scripts/
│   └── link-dev.sh             # Author dev-link tool (not a general install path)
└── skills/
    └── sdd-workflow/           # ← canonical skill, the only source of workflow rules
        ├── SKILL.md
        └── agents/
            └── openai.yaml     # Codex UI/invocation metadata only, no workflow rules
```

### Keep the skill folder clean

`skills/sdd-workflow/` contains **only** `SKILL.md` and `agents/openai.yaml` (plus `scripts/`, `references/`, `assets/` only if the skill itself truly needs them). Do **not** put `README.md`, `CHANGELOG.md`, install instructions, etc. inside the skill folder — user-facing documents always live at the **repo root**. This follows the Agent Skills convention (a skill ships only what the agent needs to perform the task).

`agents/openai.yaml` carries metadata only (`display_name`, `short_description`, `default_prompt`). The `default_prompt` must mention the skill as `$sdd-workflow`.

## Local development flow

1. Edit `skills/sdd-workflow/SKILL.md` (or its metadata).
2. Use the dev-link so edits take effect live:

   ```bash
   scripts/link-dev.sh                # or --claude-only / --codex-only
   scripts/link-dev.sh --unlink       # when done
   ```

   - It only creates a symlink to this repo when the destination does not exist; it stops and touches nothing when a file / directory / other symlink is already there.
   - Target directories can be overridden with `CLAUDE_SKILLS_DIR` / `CODEX_SKILLS_DIR` (for hermetic testing or a verified Codex skill root).
3. Before opening a PR, run the authoritative frontmatter/naming check (if Codex skill-creator is available in your environment):

   ```bash
   python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/sdd-workflow
   ```

## Acceptance responsibility (interactive testing is done by a human)

Automation can only cover **static and hermetic** checks (skill structure, frontmatter, docs, dev-link behavior).

**Actual cross-tool workflow acceptance must be performed by a human in fresh interactive sessions of each tool** — it cannot be replaced by an agent run:

- Claude Code: in a fresh session, run `/sdd-workflow 提案 …` through the full 提案 → approval → 實作 → 歸檔 flow; in a separate session, confirm natural-language input automatically selects the skill and stops to wait for approval.
- Codex: in a fresh session, run `$sdd-workflow 提案 …` through the same three phases; also confirm natural-language implicit invocation.
- A skill change may require a new conversation/restart to load; never mistake "not loaded" for "passed".

Verify at least these behaviors in each tool:

- A new proposal persists `draft` and stops. Saying only `實作` for a `draft` asks for approval; `開始實作` persists `approved`.
- An implementation request with no active proposal or a missing `proposal.md` / `tasks.md` stops without changing product code.
- A revision preserves checked tasks, appends new numbers, resets to `draft`, and waits for approval again.
- Completed archive checks only task checkboxes before the acceptance criteria, obtains the date from the execution environment, persists `completed`, and appends an `archive/INDEX.md` summary.
- `放棄` / `取消` creates an `-abandoned` archive with `abandoned` status and an INDEX summary.
- The workflow creates no git commit unless the user asks.

### Optional: Codex sub-agent assisted acceptance

Codex can spawn sub-agents to help with **non-interactive** acceptance. This suits noisy, parallelizable checks that you want out of the main thread — document/command verification, static validation, hermetic dev-link tests, repo structure scans. It cannot replace fresh Codex TUI acceptance, because sub-agents inherit the current session, sandbox, and workspace — they are not a brand-new interactive Codex CLI session.

In the main Codex thread, explicitly ask sub-agents to do read-heavy or hermetic checks only, and aggregate after all of them report back:

```text
Spawn 4 sub-agents to help accept the current repo, without modifying any files. Each sub-agent reports findings, evidence, and residual risks.

1. Docs/commands acceptance: verify the install, update, remove, and validator commands in README.md / README.en.md / CONTRIBUTING.md against current CLI help, and call out any GitHub-publication prerequisites that cannot be proven locally.
2. Skill structure acceptance: check that skills/sdd-workflow/ contains only SKILL.md and agents/openai.yaml, that openai.yaml carries metadata only, and that no legacy commands/prompts/install.sh remain in the repo.
3. Dev-link acceptance: in a temporary directory, exercise scripts/link-dev.sh with CLAUDE_SKILLS_DIR / CODEX_SKILLS_DIR — link, only-flags, unlink, existing-destination conflicts, and idempotency.
4. Codex loading boundary acceptance: check whether the currently installed Codex skill matches the repo's canonical skill, and list explicitly what still must be verified manually in a fresh Codex session.

After all 4 sub-agents finish, aggregate into PASS / FAIL / BLOCKED and list the remaining acceptance steps that require a human.
```

Sub-agents can help determine:

- whether the skill package in the repo is valid;
- whether the commands in the docs are supported by the current tools;
- whether `scripts/link-dev.sh` operates safely in a temporary directory;
- whether an installed copy has diverged from the repo's canonical skill.

Sub-agents cannot prove:

- that a fresh Codex session will actually load the newly installed skill;
- that `$sdd-workflow` appears in the interactive picker or can be invoked correctly from a fresh TUI;
- that the interactive `提案 → 實作 → 歸檔` flow has been fully exercised in a real Codex session.

So the final step is still a human running, in a fresh Codex session:

```text
$sdd-workflow 提案 建立一個測試文字檔
```

Confirm it stops at the proposal waiting for approval, then reply `開始實作`, verify the artifacts, and finally reply `歸檔`. In another independent session, test natural-language triggering, e.g.:

```text
提案：建立一個測試文字檔
```

## Trigger syntax differences (reminder)

- Claude Code: `/sdd-workflow`
- Codex: `$sdd-workflow`
- Both accept the Traditional Chinese natural triggers 提案 / 開始實作 / 實作 / 歸檔 / 放棄 / 取消.

Install, update, and remove commands differ per channel — see the README; never mix one channel's paths or ownership assumptions into another.
