# Contributing to sdd-workflow

> [繁體中文](./CONTRIBUTING.md)

Thanks for contributing! This document explains the maintenance rules of this repo.

## The only product: the canonical Skill package

**This repository maintains one product:
[`skills/sdd-workflow/`](./skills/sdd-workflow/).**

- `SKILL.md` is the sole source for Agent behavior boundaries and trigger
  rules. Bundled scripts and references are internal Skill implementation, not
  a separate protocol or developer kit.
- The deterministic runtime may enforce parsing, mutation, and archive safety.
  A behavior change must check Skill prose, runtime, and regression together;
  changing only one does not redefine the complete workflow.
- Copies installed into `~/.claude/skills/`, `~/.codex/skills/`, or `~/.agents/skills/` are **reproducible install artifacts**, never a second source of truth. **Never** edit only the copy inside a tool's directory — that causes divergence.
- Do not add per-tool command/prompt variants. Cross-tool differences appear only in *how the skill is invoked* (the trigger-syntax table in the README), never in workflow rules.

## Scope and complexity budget

- Label every roadmap item before implementation as subtract, fix, measure, or
  add. An addition needs a named requester and unmet need; otherwise it stays
  in the backlog.
- Communicate only Skill release, proposal artifact schema, and JSON output
  version externally. Handshake, attestation, and manifest versions are
  internal implementation details when retained.
- Do not create a third-party adapter program, public conformance kit, protocol
  freeze, deprecation policy, development framework, or general orchestration
  platform.
- Do not add natural-language triggers, schemas, Agent adapters, references, or
  recovery mechanisms without field evidence and a separate proposal.
- Prefer removing duplicate promises, consolidating synchronization sources,
  and reusing tests. Renaming files or hiding details does not reduce
  complexity.

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
        ├── scripts/                # internal deterministic Skill runtime
        ├── references/             # operation detail loaded on demand
        └── agents/
            └── openai.yaml     # Codex UI/invocation metadata only, no workflow rules
```

### Keep the skill folder clean

`skills/sdd-workflow/` contains **only** `SKILL.md` and `agents/openai.yaml` (plus `scripts/`, `references/`, `assets/` only if the skill itself truly needs them). Do **not** put `README.md`, `CHANGELOG.md`, install instructions, etc. inside the skill folder — user-facing documents always live at the **repo root**. This follows the Agent Skills convention (a skill ships only what the agent needs to perform the task).

`agents/openai.yaml` carries metadata only (`display_name`, `short_description`, `default_prompt`). The `default_prompt` must mention the skill as `$sdd-workflow`.

## Local development flow

1. Edit `skills/sdd-workflow/SKILL.md` (or its metadata).
2. After any byte change to `SKILL.md` (whitespace included), refresh
   `skill_sha256` in `skills/sdd-workflow/runtime-identity.json` to match.
   Otherwise `package-validation` fails with "runtime identity does not match
   SKILL.md bytes" and several discovery/install-channel unit tests turn red
   with it:

   ```bash
   shasum -a 256 skills/sdd-workflow/SKILL.md
   # Put the printed hash into skill_sha256 in runtime-identity.json, then verify:
   PYTHONDONTWRITEBYTECODE=1 python3 tests/package_validation.py
   ```

3. Use the dev-link so edits take effect live:

   ```bash
   scripts/link-dev.sh                # or --claude-only / --codex-only
   scripts/link-dev.sh --unlink       # when done
   ```

   - It only creates a symlink to this repo when the destination does not exist; it stops and touches nothing when a file / directory / other symlink is already there.
   - Target directories can be overridden with `CLAUDE_SKILLS_DIR` / `CODEX_SKILLS_DIR` (for hermetic testing or a verified Codex skill root).
4. Before opening a PR, run the authoritative frontmatter/naming check (if Codex skill-creator is available in your environment):

   ```bash
   python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/sdd-workflow
   ```

## CI and team concurrency

Protected branches use five stable checks that can be required independently: `unit`, `fixtures`, `package-validation`, `docs-consistency`, and `install-smoke`. The unit and install matrices cover macOS/Linux and minimum/latest Python; release packages, Claude/Codex destinations, and dev links are verified in isolated temporary directories. Any check addition or rename must update `.github/workflows/ci.yml`, `tests/test_ci_contract.py`, and `tests/docs_consistency.py` together.

One proposal has one owner at a time. Independent changes use distinct short names and separate Git worktrees when implementation files may overlap. The current owner stops mutation before handoff and provides the latest status; the receiver must rerun `status` and never reuse the handed-off snapshot. Archive directories are authoritative. If concurrent terminal work leaves `INDEX.md` stale, run `validate-index`, `rebuild-index`, then `doctor`; never merge INDEX manually. See [`docs/team-operations.md`](./docs/team-operations.md) for the complete contract.

## Acceptance responsibility (interactive testing is done by a human)

Automation can only cover **static and hermetic** checks (skill structure, frontmatter, docs, dev-link behavior).

**Actual cross-tool workflow acceptance must be performed by a human in fresh interactive sessions of each tool** — it cannot be replaced by an agent run:

- Claude Code: in a fresh session, run `/sdd-workflow 提案 …` through the full 提案 → approval → 實作 → 歸檔 flow; in a separate session, confirm natural-language input automatically selects the skill and stops to wait for approval.
- Codex: in a fresh session, run `$sdd-workflow 提案 …` through the same three phases; also confirm natural-language implicit invocation.
- A skill change may require a new conversation/restart to load; never mistake "not loaded" for "passed".

### Fresh-session acceptance matrix

"Statically provable" means the rule can be proven from the text of `SKILL.md`/docs or a fixture simulation; "fresh-session interactive acceptance" is behavior a human must confirm by operating a brand-new session. **Passing the static column never implies the interactive column passed** — both are required.

| Item | Statically provable | Fresh-session interactive acceptance |
| --- | --- | --- |
| Proposal creation | Template contains `## 狀態` with value `draft` | Stops for approval after creation; no product code touched |
| Proposal intake | Authoring reference states the conditional intake rules (anchored by `tests/test_skill_reduction.py`) | On material ambiguity the agent briefly states the decision-relevant assumptions or gaps, asks exactly one most-critical question, and does not draft before the answer; with sufficient information it drafts directly, marking deferable uncertainty, without a fixed analysis report; a requested implementation approach whose difference from the desired outcome would change the proposal is clarified as material ambiguity |
| Approval semantics | CLI transition tests and Skill command rule | `實作` on a `draft` asks; `開始實作` calls `approve` with the snapshot and verifies manifest, metadata, and `approved` |
| Missing-artifact guard | Rule text present | Missing directory or artifact demands `提案` first; no code changes |
| Revision | Rule text present | Preserves checked tasks, keeps at most 10 unchecked tasks, resets `draft` and waits again; a goal-changing amendment is redirected to a new change |
| Deterministic read and managed mutation path | `SKILL.md` defines only CLI orchestration; parser, transition, and failure-injection tests reproduce outcomes | The agent never parses artifacts or directly edits existing status, checkbox, metadata, archive location, or INDEX; strict errors stop before mutation, while only abandonment preflight degrades counts |
| Abandonment preflight | `abandon-preflight` fixtures verify warnings, counts, and snapshot | `放棄` / `取消提案` reports only CLI progress, warning, and both hashes before stopping; status, directory, and INDEX remain unchanged |
| Abandonment confirmation | CLI terminal tests, snapshot comparison, and Skill rule | Only exact `確認放棄 <short-name>` reruns preflight; the environment compares both transcript and current JSON hashes without eyeballing, calls `abandon` only on a match, and requires a new confirmation otherwise |
| Standalone `取消` | Rule text present | A standalone `取消` or unclear cancellation always asks whether to revert code or abandon the proposal; never does either directly; the no-phase menu offers `取消提案`, never a standalone `取消` |
| Completed archive | Terminal transition and failure-injection tests | `archive` validates snapshot/manifest/attestation, treats the directory move as the commit point, then rebuilds INDEX from all archive records |
| Shared terminal procedure | SKILL.md has exactly one Terminal result procedure; the CLI uses one transaction engine | `archive` and `abandon` share staging, move, retry, and INDEX rebuild; an INDEX failure after move never moves the directory back |
| Managed-state drift | Attestation and doctor tests | Ordinary prose edits do not cause drift; status, checkbox, or metadata mismatch reports `OUT_OF_BAND_DRIFT` without claiming who changed it |
| Schema v2 | Schema v2 fixtures, common-model, and research archive tests | New proposals declare a version; all six types parse; research conclusions reconstruct from archives; v1/legacy remain unmigrated and future versions fail closed |
| Team/worktree boundary | CI contract, install matrix, worktree, and concurrency tests | One owner per proposal; distinct short names/worktrees do not contaminate each other; stale INDEX is detected and rebuilt |
| Git behavior | Rule text present | No commit is created unless the user asks |
| Output language | `SKILL.md` Reporting section states the rule | All user-facing reports, questions, and error explanations stay in Traditional Chinese; report tokens (第 N 條完成 / 全部完成 / 歸檔完成 / 已放棄) unchanged |

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
- Both accept the Traditional Chinese natural triggers 提案 / 開始實作 / 實作 / 歸檔 / 放棄; executing abandonment additionally requires the exact reply `確認放棄 <short-name>`, and a bare `取消` only asks what to cancel.

Install, update, and remove commands differ per channel — see the README; never mix one channel's paths or ownership assumptions into another.
