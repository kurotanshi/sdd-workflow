---
name: sdd-workflow
description: "Manage software changes through a proposal-first SDD workflow: create a scoped proposal and checklist, wait for explicit approval before implementation, execute one task at a time with progress reports, and archive completed work. Use when the user says 提案, 實作, 開始實作, or 歸檔, or otherwise asks to run the sdd-workflow for a project change."
---

# SDD Workflow

Use this skill to enforce the project workflow `提案 → 實作 → 歸檔`.

## Non-negotiable rules

- State what will be done before writing implementation code.
- Do not modify implementation files before the user explicitly approves the proposal with `開始實作` (also accept `實作` when it is clearly intended as the implementation approval).
- Do not invent requirements, add unrequested features, or over-design.
- Ask when the specification, target, or expected behavior is unclear; do not guess.
- Work on one task at a time and report each completed task briefly.
- Keep scope to the current request. Do not combine unrelated features or fixes in one workflow.
- Treat `sdd/` as project-local and resolve it relative to the current working directory.

## Phase selection

Interpret the user's explicit phase word as follows:

- `提案`: create or revise a proposal for the described change; do not write implementation code.
- `實作` or `開始實作`: implement the approved proposal, one unchecked task at a time.
- `歸檔`: archive an implementation that the user has accepted.

If the user invokes this skill or describes a change without naming a phase, ask them to choose `提案`, `實作`, or `歸檔`. Do not start coding from an ordinary feature request.

Keep the current change name in context across turns. If an implementation or archive request does not identify it, inspect `sdd/` for active directories containing `proposal.md` and `tasks.md`. Continue automatically only when exactly one active change is unambiguous; otherwise ask the user for the short name. Never use a directory under `sdd/archive/` as an active change.

## Phase 1: 提案

When the user says `提案` and describes a requirement:

1. Inspect the current project enough to understand existing behavior and likely files. Do not modify implementation files.
2. Choose a short English name in lowercase hyphen-case, such as `add-todo` or `fix-login`. Before creating files, check whether `sdd/<short-name>/` already exists. Do not overwrite an existing proposal; ask whether to revise it or choose another name.
3. Classify the change as exactly one of `新功能`, `修 bug`, or `重構`.
4. Create `sdd/<short-name>/proposal.md` with these sections:

   ```markdown
   # <short name>

   ## 類型
   新功能

   ## 為什麼做
   ...

   ## 要改什麼
   - ...

   ## 影響範圍
   - 新增：...
   - 修改：...
   ```

   Explain the problem, requested behavior, and likely new or changed files in plain language. Mark uncertain file paths as estimates rather than presenting guesses as facts.
5. Create `sdd/<short-name>/tasks.md` with a top-to-bottom checklist. Every implementation task must start with `- [ ]`, be small enough to finish in about one hour, and be concrete enough to verify. Keep the checklist to at most 10 tasks. Do not hide a large task by making its wording vague. If the request cannot reasonably fit within 10 small tasks, tell the user to split the request into smaller changes before implementation.
6. Append `## 驗收條件` to `tasks.md`. Describe observable outcomes as plain-language scenarios, for example:

   ```markdown
   ## 驗收條件
   - 情境：當使用者點擊「新增」按鈕，就把輸入框的文字加到清單最下面
   - 情境：當輸入框是空的就按新增，就不新增，並提示「請先輸入內容」
   ```

7. Re-read both files. Show the user the short name, classification, key behavior changes, task count, and acceptance scenarios. Then stop and wait for explicit approval. Do not implement anything in the same turn.

If requirements are materially ambiguous, ask a focused question before creating the proposal. If the request is too large, explain why and ask the user to split it; do not silently expand the scope or begin implementation.

## Phase 2: 實作

When the user says `實作` or `開始實作`:

1. Read `sdd/<short-name>/proposal.md` and `sdd/<short-name>/tasks.md` completely before changing code.
2. Read the acceptance conditions and identify the first unchecked task from top to bottom. Work on only that task. Before implementing it, inspect the project for existing components, utilities, patterns, tests, or configuration that can be reused.
3. Make the smallest change that satisfies that task. Do not implement later tasks in advance and do not add unrequested behavior.
4. Validate the task proportionally: run the relevant tests, type checks, lint, build, or a focused manual check when available. If validation exposes a specification gap or a wrong direction, stop and tell the user what is unclear; do not rewrite the proposal or force a solution.
5. Before checking off the task, re-read its exact wording and the relevant acceptance conditions. Only when the result satisfies both should you change its marker from `- [ ]` to `- [x]`.
6. Re-read `tasks.md` after the edit and verify that the intended line is actually `- [x]`. Report briefly, using the task number, for example `第 1 條完成`.
7. Continue with the next unchecked task one at a time, reporting after each task. If the user gives a new instruction, follow it instead of continuing automatically.
8. When every task is checked, report `全部完成` and ask the user to verify the acceptance conditions. Do not archive until the user confirms acceptance and says `歸檔`.

Never mark a task complete merely because code was written. A task is complete only after its wording and acceptance conditions have been checked and the relevant validation has passed or its limitation has been reported.

## Phase 3: 歸檔

When the user confirms acceptance and says `歸檔`:

1. Read `sdd/<short-name>/tasks.md` and verify that every task checkbox is `- [x]`. If any task is unchecked, report the task number(s) and stop; do not archive.
2. Use the current local date in `YYYY-MM-DD` format and move the whole directory:

   ```text
   sdd/<short-name>/
   → sdd/archive/YYYY-MM-DD-<short-name>/
   ```

   Create `sdd/archive/` if necessary. If the destination already exists, stop and ask before overwriting or choosing a different date/name; never merge or delete archive contents silently.
3. Verify that the source directory is gone and the destination contains both proposal files.
4. Report `歸檔完成` and summarize the change in one sentence for future lookup.

## Progress reporting

Keep reports short and concrete. At proposal completion, show the plan and wait. During implementation, report only the completed task, validation result, and any blocker before moving to the next task. When blocked by missing requirements, surface the exact decision needed and pause.
