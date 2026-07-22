---
name: sdd-workflow
description: "Manage software changes through a proposal-first SDD workflow: create or revise a scoped proposal and checklist, wait for explicit approval before implementation, execute one task at a time with progress reports, and archive completed or abandoned work. Use when the user says 提案, 開始實作, 實作, 歸檔, 放棄, or 取消, or otherwise asks to run the sdd-workflow for a project change."
---

# SDD Workflow

Use this skill to enforce the project workflow `提案 → 實作 → 歸檔`, including revision and abandonment paths.

## Non-negotiable rules

- State what will be done before writing implementation code.
- Do not modify implementation files unless the active proposal status is `approved`.
- Treat `開始實作` as explicit approval of a `draft` proposal. If the user says only `實作` for a `draft` or statusless proposal, ask for approval and stop; do not infer approval.
- Do not invent requirements, add unrequested features, or over-design.
- Ask when the specification, target, or expected behavior is unclear; do not guess.
- Work on one task at a time and report each completed task briefly.
- Keep scope to the current request. Do not combine unrelated features or fixes in one workflow.
- Treat `sdd/` as project-local and resolve it relative to the current working directory.
- Do not create git commits unless the user asks. When asked to commit, prefer a message that includes the short name and task number, such as `feat(add-health-check): task 2 - register route`.

## Phase selection

Interpret the user's explicit phase word as follows:

- `提案`: create or revise a proposal for the described change; do not write implementation code.
- `開始實作`: explicitly approve a `draft` proposal, persist the approval, then implement one unchecked task at a time.
- `實作`: continue an `approved` proposal. For a `draft` or statusless proposal, ask whether the user approves it and do not implement in the same turn.
- `歸檔`: archive an implementation that the user has accepted.
- `放棄` or `取消`: archive an active proposal as abandoned without implementing remaining tasks.

If the user invokes this skill or describes a change without naming a phase, ask them to choose `提案`, `開始實作`, `實作`, `歸檔`, `放棄`, or `取消`. Do not start coding from an ordinary feature request.

Keep the current change name in context across turns. If an implementation, archive, or abandonment request does not identify it, inspect `sdd/` for active directories containing `proposal.md` and `tasks.md`. Continue automatically only when exactly one active change is unambiguous; otherwise ask the user for the short name. Never use a directory under `sdd/archive/` as an active change.

## Phase 1: 提案

When the user says `提案` and describes a requirement:

1. Inspect the current project enough to understand existing behavior and likely files. Do not modify implementation files.
2. Choose a short English name in lowercase hyphen-case, such as `add-todo` or `fix-login`. Before creating files, check whether `sdd/<short-name>/` already exists. Do not overwrite an existing proposal; ask whether to revise it or choose another name.
3. Classify the change as exactly one of `新功能`, `修 bug`, or `重構`. Treat this classification as human-readable metadata for proposal reports and archive lookup, not as a separate workflow.
4. Create `sdd/<short-name>/proposal.md` with these sections:

   ```markdown
   # <short name>

   ## 狀態
   draft

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

   Always create a new proposal with status `draft`. Explain the problem, requested behavior, and likely new or changed files in plain language. Mark uncertain file paths as estimates rather than presenting guesses as facts. For `修 bug`, include a reproduction task and regression validation when the behavior can reasonably be reproduced.
5. Create `sdd/<short-name>/tasks.md` with a top-to-bottom checklist. Every implementation task must start with `- [ ]` and represent one independently verifiable behavior change with a specific test or observable result. Keep the checklist to at most 10 tasks. Do not hide a large task by making its wording vague or combining unrelated outcomes. If the request cannot reasonably fit within 10 independently verifiable tasks, tell the user to split the request into smaller changes before implementation.
6. Append `## 驗收條件` to `tasks.md`. Describe observable outcomes as plain-language scenarios, for example:

   ```markdown
   ## 驗收條件
   - 情境：當使用者點擊「新增」按鈕，就把輸入框的文字加到清單最下面
   - 情境：當輸入框是空的就按新增，就不新增，並提示「請先輸入內容」
   ```

7. Re-read both files. Show the user the short name, classification, key behavior changes, task count, and acceptance scenarios. Then stop and wait for explicit approval. Do not implement anything in the same turn.

If requirements are materially ambiguous, ask a focused question before creating the proposal. If the request is too large, explain why and ask the user to split it; do not silently expand the scope or begin implementation.

## Proposal revisions

Use this path when the user asks to revise an active proposal, or when implementation has stopped because the agreed specification must change:

1. Stop implementation and read the current `proposal.md` and `tasks.md` completely.
2. Revise the proposal, affected acceptance conditions, and impact scope to reflect only the agreed amendment.
3. Preserve every checked task exactly as implementation history: do not uncheck, rewrite, delete, or renumber it. Revise or remove an unchecked task only when the amendment explicitly supersedes it. Append new work as concrete tasks using the next unused task numbers, without reusing old numbers. Keep the complete checklist at no more than 10 tasks; if that is not possible, split the amendment into another change.
4. Change `## 狀態` to `draft`, then re-read both files and report the revised behavior, retained completed tasks, and new or superseded unchecked tasks.
5. Stop and wait for `開始實作`. Do not resume implementation in the revision turn, even if the proposal had previously been `approved`.

## Phase 2: 實作

When the user says `實作` or `開始實作`:

1. Resolve the active short name, then verify that `sdd/<short-name>/` exists and contains both `proposal.md` and `tasks.md`. If the directory or either file is missing, stop and tell the user to run `提案`; do not create missing artifacts or modify implementation files.
2. Read `proposal.md` and `tasks.md` completely before changing code. Read the value under `## 狀態`; a missing status is an unapproved legacy proposal, never implicit approval.
3. Apply the approval gate:
   - If the status is `approved`, continue.
   - If the status is `draft` or missing and the user said only `實作`, ask whether they approve the proposal and stop without modifying implementation files.
   - If the status is `draft` or missing and the user said `開始實作`, change or insert `## 狀態` as `approved`, then re-read `proposal.md` and verify the persisted value before continuing.
   - If the status has any other value, stop and report it; do not infer that implementation is allowed.
4. Read the acceptance conditions and identify the first unchecked task from top to bottom. Work on only that task. Before implementing it, inspect the project for existing components, utilities, patterns, tests, or configuration that can be reused.
5. Make the smallest change that satisfies that task. Do not implement later tasks in advance and do not add unrequested behavior.
6. Validate the task proportionally: run the relevant tests, type checks, lint, build, or a focused manual check when available. If validation exposes a specification gap or a wrong direction, stop and tell the user what is unclear; do not rewrite the proposal or force a solution.
7. Before checking off the task, re-read its exact wording and the relevant acceptance conditions. Only when the result satisfies both should you change its marker from `- [ ]` to `- [x]`.
8. Re-read `tasks.md` after the edit and verify that the intended line is actually `- [x]`. Report briefly, using the task number, for example `第 1 條完成`.
9. Continue with the next unchecked task one at a time, reporting after each task. If the user gives a new instruction, follow it instead of continuing automatically.
10. When every task is checked, report `全部完成` and ask the user to verify the acceptance conditions. Do not archive until the user confirms acceptance and says `歸檔`.

Never mark a task complete merely because code was written. A task is complete only after its wording and acceptance conditions have been checked and the relevant validation has passed or its limitation has been reported.

## Abandonment: 放棄 / 取消

When the user says `放棄` or `取消`:

1. Resolve the active short name and verify that its directory contains `proposal.md` and `tasks.md`. Read both files completely; if either artifact is missing, stop and report the problem.
2. Obtain the real local date from the current execution environment in `YYYY-MM-DD` format. On POSIX systems run `date +%F`; otherwise use an equivalent system command. Never infer the date from model knowledge or conversation context.
3. Use `sdd/archive/YYYY-MM-DD-<short-name>-abandoned/` as the destination. Create `sdd/archive/` if necessary. If the destination exists, stop and ask; never overwrite, merge, or delete archive contents silently.
4. Change the proposal status to `abandoned` and re-read `proposal.md` to verify it before moving the whole active directory.
5. Create `sdd/archive/INDEX.md` with the heading `# SDD Archive` if it does not exist, preserving existing content. Append one lookup line in this format, using a factual one-sentence summary derived from the proposal:

   ```markdown
   - YYYY-MM-DD | <short-name> | abandoned | <summary>
   ```

6. Verify that the source directory is gone, the destination contains `proposal.md` and `tasks.md` with status `abandoned`, and `INDEX.md` contains the appended line. Report `已放棄` with the summary.

## Phase 3: 歸檔

When the user confirms acceptance and says `歸檔`:

1. Read `sdd/<short-name>/proposal.md` and `sdd/<short-name>/tasks.md` completely. For completion, inspect only the task area from the start of `tasks.md` to, but not including, the first `## 驗收條件` heading. Count only lines that begin exactly with `- [ ]` or `- [x]`.
2. Require at least one counted task and require every counted task to be `- [x]`. If there are no counted tasks or any are unchecked, report the problem and unchecked task number(s), then stop without archiving. Checkboxes under acceptance conditions do not affect completion.
3. Obtain the real local date from the current execution environment in `YYYY-MM-DD` format. On POSIX systems run `date +%F`; otherwise use an equivalent system command. Never infer the date from model knowledge or conversation context.
4. Use `sdd/archive/YYYY-MM-DD-<short-name>/` as the destination. Create `sdd/archive/` if necessary. If the destination exists, stop and ask; never overwrite, merge, or delete archive contents silently.
5. Change the proposal status to `completed` and re-read `proposal.md` to verify it before moving the whole active directory.
6. Create `sdd/archive/INDEX.md` with the heading `# SDD Archive` if it does not exist, preserving existing content. Append one lookup line in this format, using a factual one-sentence summary derived from the proposal:

   ```markdown
   - YYYY-MM-DD | <short-name> | completed | <summary>
   ```

7. Verify that the source directory is gone, the destination contains `proposal.md` and `tasks.md` with status `completed`, and `INDEX.md` contains the appended line.
8. Report `歸檔完成` and include the same one-sentence summary for future lookup.

## Progress reporting

Keep reports short and concrete. At proposal completion, show the plan and wait. During implementation, report only the completed task, validation result, and any blocker before moving to the next task. When blocked by missing requirements, surface the exact decision needed and pause.
