---
name: sdd-workflow
description: "Manage software changes through a proposal-first SDD workflow: create or revise a scoped proposal and checklist, wait for explicit approval before implementation, execute one task at a time with progress reports, and archive completed or abandoned work. Use when the user says 提案, 開始實作, 實作, 歸檔, 放棄, 取消, or 確認放棄, or otherwise asks to run the sdd-workflow for a project change."
---

# SDD Workflow

Use this skill to enforce the project workflow `提案 → 實作 → 歸檔`, including revision and abandonment paths.

## Non-negotiable rules

- State what will be done before writing implementation code.
- Act on a phase word only when the user states it as a command whose target is this workflow or a specific proposal. A phase word inside descriptive or narrative text never starts a phase; when intent is unclear, ask.
- Do not modify implementation files unless the active proposal status is `approved`.
- Abandonment is a two-step operation: a read-only preflight, then an exact `確認放棄 <short-name>` confirmation. Never change proposal status, move directories, or update the archive index during preflight or on an ambiguous cancellation request.
- Abandonment never reverts implementation code or git changes. Revert working-tree changes only as a separate operation that the user explicitly requests and whose scope the user confirms.
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
- `放棄`, `放棄 <short-name>`, or `取消提案`: run the abandonment preflight for the resolved active proposal. Preflight is read-only; never archive in the same turn.
- `確認放棄 <short-name>`: execute abandonment, only when a preflight snapshot from the current conversation matches (see Abandonment execution).
- A bare `取消`, or a cancellation request whose target is unclear: ask whether the user wants to revert recent code changes or abandon the active proposal; never do either directly. A cancellation request that explicitly targets code, such as `取消剛才的程式碼修改`, is an ordinary revert request outside this workflow: confirm the exact revert scope with the user before changing anything, and never touch the proposal status, artifacts, or archive because of it.

If the user invokes this skill or describes a change without naming a phase, ask them to choose `提案`, `開始實作`, `實作`, `歸檔`, `放棄`, or `取消提案`. Never offer a bare `取消` as a menu option — it is defined above as ambiguous and would only trigger another clarification round. Do not start coding from an ordinary feature request.

Keep the current change name in context across turns. If an implementation, archive, or abandonment request does not identify it, inspect `sdd/` for active directories containing `proposal.md` and `tasks.md`. Continue automatically only when exactly one active change is unambiguous; otherwise ask the user for the short name. Never use a directory under `sdd/archive/` as an active change.

## Task checklist format and scanner

Every operation that reads or counts tasks — Phase 1 creation, Phase 2 implementation, proposal revisions, the abandonment preflight, and the Phase 3 completion check — must apply these shared rules and no other counting method:

- Scan region: from the start of `tasks.md` up to, but not including, the first `## 驗收條件` heading. Lines at or after that heading never affect task counting.
- Valid task line: begins at the first column with exactly `- [ ] ` or `- [x] ` followed by the task text. Tasks form one top-level list; checkbox subtasks are not allowed.
- Checkbox-like line: any line in the scan region that begins with optional leading whitespace, then a list marker — `-`, `*`, `+`, or an ordered-list marker such as `1.` or `1)` — then optional whitespace, then `[`, any run of characters other than `]` (including none), and `]`. This includes indented or nested checkboxes and variants such as `- [X]`, `* [ ]`, `-[ ]`, `- [xx]`, `- []`, and `1. [ ]`.
- Other list items: the scan region may contain only valid task lines, blank lines, and non-list text. Any other line that begins with optional leading whitespace and a list marker — including an item whose text starts with a markdown link, such as `- [參考文件](https://example.com)` — is not allowed, even when it is not checkbox-like.
- Every checkbox-like line or other list item that is not a valid task line is a format error. Report each offending line number and stop the current operation. Never proceed by skipping or silently ignoring such lines. Single exception: the abandonment preflight never stops on format errors — it continues in degraded mode as specified in its own section, because a broken checklist must never lock the user out of abandoning a proposal. Phase 1, Phase 2, proposal revisions, and the Phase 3 completion check always stay strict.

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
5. Create `sdd/<short-name>/tasks.md` with a top-to-bottom checklist. Every implementation task must be a valid task line under the shared task scanner: it starts at the first column with `- [ ] `, stays in one top-level list, and has no checkbox subtasks. Each task represents one independently verifiable behavior change with a specific test or observable result. Keep the checklist to at most 10 tasks. Do not hide a large task by making its wording vague or combining unrelated outcomes. If the request cannot reasonably fit within 10 independently verifiable tasks, tell the user to split the request into smaller changes before implementation.
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
3. Preserve every checked task exactly as implementation history: do not uncheck, rewrite, delete, or renumber it. Revise or remove an unchecked task only when the amendment explicitly supersedes it. Append new work as concrete tasks using the next unused task numbers, without reusing old numbers. Checked tasks are history and never count against the quota: after a revision, keep at most 10 unchecked tasks. If the amendment cannot fit within 10 unchecked tasks, or it materially changes the proposal's goal, do not stretch the revision; ask the user to handle it as a new change instead. The revised checklist must pass the shared task scanner.
4. Change `## 狀態` to `draft`, then re-read both files and report the revised behavior, retained completed tasks, and new or superseded unchecked tasks.
5. Stop and wait for `開始實作`. Do not resume implementation in the revision turn, even if the proposal had previously been `approved`.

## Phase 2: 實作

When the user says `實作` or `開始實作`:

1. Resolve the active short name, then verify that `sdd/<short-name>/` exists and contains both `proposal.md` and `tasks.md`. If the directory or either file is missing, stop and tell the user to run `提案`; do not create missing artifacts or modify implementation files.
2. Read `proposal.md` and `tasks.md` completely before changing code. Read the value under `## 狀態`; a missing status is an unapproved legacy proposal, never implicit approval.
3. Run the shared task scanner on `tasks.md`. On any format error, report the offending line numbers and stop before the approval gate: do not change or insert `## 狀態`, and do not modify implementation files.
4. Apply the approval gate:
   - If the status is `approved`, continue.
   - If the status is `draft` or missing and the user said only `實作`, ask whether they approve the proposal and stop without modifying implementation files.
   - If the status is `draft` or missing and the user said `開始實作`, change or insert `## 狀態` as `approved`, then re-read `proposal.md` and verify the persisted value before continuing.
   - If the status has any other value, stop and report it; do not infer that implementation is allowed.
5. Read the acceptance conditions and identify the first unchecked task from top to bottom. Work on only that task. Before implementing it, inspect the project for existing components, utilities, patterns, tests, or configuration that can be reused.
6. Make the smallest change that satisfies that task. Do not implement later tasks in advance and do not add unrequested behavior.
7. Validate the task proportionally: run the relevant tests, type checks, lint, build, or a focused manual check when available. If validation exposes a specification gap or a wrong direction, stop and tell the user what is unclear; do not rewrite the proposal or force a solution.
8. Before checking off the task, re-read its exact wording and the relevant acceptance conditions. Only when the result satisfies both should you change its marker from `- [ ]` to `- [x]`.
9. Re-read `tasks.md` after the edit and verify that the intended line is actually `- [x]`. Report briefly, using the task number, for example `第 1 條完成`.
10. Continue with the next unchecked task one at a time, reporting after each task. If the user gives a new instruction, follow it instead of continuing automatically.
11. When every task is checked, report `全部完成` and ask the user to verify the acceptance conditions. Do not archive until the user confirms acceptance and says `歸檔`.

Never mark a task complete merely because code was written. A task is complete only after its wording and acceptance conditions have been checked and the relevant validation has passed or its limitation has been reported.

## Abandonment preflight: 放棄 / 取消提案

When the user says `放棄`, `放棄 <short-name>`, or `取消提案`:

1. Resolve the active short name and verify that its directory contains `proposal.md` and `tasks.md`. Read both files completely; if either artifact is missing, stop and report the problem.
2. Run the shared task scanner on `tasks.md`. On any format error, do not stop: report each offending line number, state that the task counts and the completed-task list are unreliable (`任務計數不可靠`), and continue the preflight in degraded mode. This is the single documented exception to the shared scanner's stop rule — a broken checklist must never lock the user out of abandonment, and the preflight snapshot does not depend on scanner results. Never repair or edit `tasks.md` during preflight.
3. Report the short name, the current `## 狀態` value, the number of completed and uncompleted tasks, and the list of completed tasks; in degraded mode derive them best-effort and label both as unreliable. State explicitly that abandonment archives only the SDD artifacts: implementation code and git changes made for completed tasks stay in the working tree and will not be reverted.
4. Compute a SHA-256 content hash of `proposal.md` and of `tasks.md` from the current execution environment. On POSIX systems run `shasum -a 256` or `sha256sum`; otherwise use an equivalent system command. Print both hash values in the preflight report, each labeled with its file name: the printed values are the preflight snapshot, and they must appear as report text so they persist in the transcript rather than only in tool-output memory. Do not write any confirmation file and do not modify any artifact.
5. Ask the user to reply exactly `確認放棄 <short-name>` with the real short name and no angle brackets, for example `確認放棄 add-todo`, then stop. The preflight never changes the proposal status, moves a directory, or updates `sdd/archive/INDEX.md`.

## Abandonment execution: 確認放棄

When the user says `確認放棄 <short-name>`:

1. Execute only when all of the following hold: the current conversation contains a preflight snapshot — the hash values printed in a preflight report — for the same proposal; the short name in the confirmation matches that snapshot exactly; and both files pass the machine hash verification below. Take both expected values verbatim from the snapshot text in the transcript. Before any substitution, verify that each expected value matches `^[0-9a-f]{64}$` — exactly 64 lowercase hexadecimal characters; if either value does not, treat the conversation as having no valid snapshot: run no comparison, re-run the preflight, and stop. Only then let the execution environment perform the comparison: on POSIX systems substitute each expected value into a shell equality test such as `[ "<expected-hash>" = "$(shasum -a 256 <file> | cut -d' ' -f1)" ]` (or the `sha256sum` equivalent) and act only on its exit code; on other systems use an equivalent machine string-equality check. Never compare hex strings by eye, never substitute a freshly recomputed value for the expected snapshot side, and treat a failed or unavailable comparison command as a mismatch.
2. If the user says only `確認放棄` without a name, the name does not match, the current conversation has no preflight snapshot for that proposal — including any new session — either snapshot value fails the `^[0-9a-f]{64}$` format check, or the machine verification reports a mismatch for either file, do not execute. Run the preflight again and stop. Never reuse a stale confirmation and never persist confirmation state to a file.
3. Run the Terminal archive procedure with the abandonment execution parameters from its table.

## Terminal archive procedure

Abandonment execution and Phase 3 archiving both finish through this single procedure. Never re-implement its steps separately, and never start it before every precondition check in the calling section has passed. The behavior differences between the two paths are selected only through this table; the final report contents referenced here are defined immediately below it:

| Parameter | Abandonment execution | Phase 3: 歸檔 |
| --- | --- | --- |
| terminal status | `abandoned` | `completed` |
| destination | `sdd/archive/YYYY-MM-DD-<short-name>-abandoned/` | `sdd/archive/YYYY-MM-DD-<short-name>/` |
| final report | `已放棄` report, defined below | `歸檔完成` report, defined below |

Final report definitions:

- `已放棄` report: report `已放棄` with the summary, list the completed tasks again — when the preflight ran in degraded mode, repeat that the task counts and the completed-task list are unreliable — and repeat that their implementation code and git changes remain in the working tree and were not reverted. Never revert automatically; a revert is a separate operation that needs an explicit user request and a confirmed scope.
- `歸檔完成` report: report `歸檔完成` and include the same one-sentence summary for future lookup.

Steps:

1. Obtain the real local date from the current execution environment in `YYYY-MM-DD` format. On POSIX systems run `date +%F`; otherwise use an equivalent system command. Never infer the date from model knowledge or conversation context.
2. Resolve the destination from the parameter table. Create `sdd/archive/` if necessary. If the destination exists, stop and ask; never overwrite, merge, or delete archive contents silently.
3. Change the proposal status to the terminal status and re-read `proposal.md` to verify the persisted value.
4. Move the whole active directory to the destination. Verify the move succeeded — the source directory is gone and the destination contains `proposal.md` and `tasks.md` with the terminal status — before touching the archive index.
5. Only after the verified move, create `sdd/archive/INDEX.md` with the heading `# SDD Archive` if it does not exist, preserving existing content. Append one lookup line in this format, using the terminal status and a factual one-sentence summary derived from the proposal:

   ```markdown
   - YYYY-MM-DD | <short-name> | <terminal-status> | <summary>
   ```

6. Verify that `INDEX.md` contains the appended line, then give the final report from the parameter table.

## Phase 3: 歸檔

When the user confirms acceptance and says `歸檔`:

1. Read `sdd/<short-name>/proposal.md` and `sdd/<short-name>/tasks.md` completely. Run the shared task scanner on `tasks.md`. On any format error, report the offending line numbers and stop without archiving; never proceed by ignoring the problem lines.
2. Require at least one valid task line and require every valid task line to be `- [x]`. If there are no valid tasks or any are unchecked, report the problem and the unchecked task number(s), then stop without archiving. Checkboxes under acceptance conditions never affect completion.
3. Run the Terminal archive procedure with the Phase 3 parameters from its table.

## Progress reporting

Keep reports short and concrete. At proposal completion, show the plan and wait. During implementation, report only the completed task, validation result, and any blocker before moving to the next task. When blocked by missing requirements, surface the exact decision needed and pause.
