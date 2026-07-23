---
name: sdd-workflow
description: "Manage software changes through a proposal-first SDD workflow: create or revise a scoped proposal and checklist, wait for explicit approval before implementation, execute one task at a time with progress reports, and archive completed or abandoned work. Use only when the user explicitly invokes sdd-workflow or refers to an SDD proposal with 提案, 開始實作, 實作, 歸檔, 放棄, 取消提案, or 確認放棄. Generic cancellation without an explicit SDD proposal target is outside this skill. Source-control or code rollback is outside SDD: confirm its exact scope before changing files and never alter proposal state because of it."
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
- Use the bundled CLI as the only supported way to discover, parse, validate, count, or snapshot proposal artifacts. If it cannot run, fail closed; never reconstruct its parser in prose.
- Before the first SDD CLI command in a session, run the bundled runtime discovery command once and require its JSON result to select the package-local compatible runtime. Never search `PATH`, the repository, or another Agent's Skill root; zero, ambiguous, failed, or incompatible discovery stops the workflow.
- Once a proposal exists, use the bundled CLI as the only supported way to change status, task completion, machine metadata, archive location, or archive INDEX. Never edit these managed fields directly.
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
- `確認放棄 <short-name>`: execute abandonment only when a preflight snapshot from the current conversation matches.
- A bare `取消`, or a cancellation request whose target is unclear—including `取消剛才的變更` and colloquial phrases such as `算了`, `先不要`, or `不用了`: ask one explicit question that names both choices, such as `你要回復最近的程式碼／Git 變更，還是放棄目前的 SDD 提案？`; never run a CLI or do either action before the answer. A cancellation request that explicitly targets code, such as `取消剛才的程式碼修改`, is an ordinary revert request outside this workflow: confirm the exact revert scope with the user before changing anything, and never touch the proposal status, artifacts, or archive because of it.

If the user invokes this skill or describes a change without naming a phase, ask them to choose `提案`, `開始實作`, `實作`, `歸檔`, `放棄`, or `取消提案`. Never offer a bare `取消` as a menu option — it is defined above as ambiguous and would only trigger another clarification round. Do not start coding from an ordinary feature request.

Keep the current change name in context across turns. If a phase request does not identify it, use `list --state active` below. Continue automatically only when its JSON contains exactly one candidate; otherwise ask the user for the short name. Never select a directory under `sdd/archive/`.

## Deterministic command contract

`<runtime-discovery>` means `python3 <skill-dir>/scripts/discover-runtime.py`. `<sdd-cli>` means `python3 <skill-dir>/scripts/sdd.py`, where `<skill-dir>` is the directory containing this `SKILL.md`. Run discovery once per session, then run project commands from the user's project with an explicit project root:

```text
<runtime-discovery>
<sdd-cli> --root <project-root> --json list --state active
<sdd-cli> --root <project-root> --json validate <short-name>
<sdd-cli> --root <project-root> --json status <short-name>
<sdd-cli> --root <project-root> --json abandon-preflight <short-name>
<sdd-cli> --root <project-root> --json approve <short-name> --expected-snapshot <digest>
<sdd-cli> --root <project-root> --json begin-revision <short-name> --expected-snapshot <digest>
<sdd-cli> --root <project-root> --json complete-task <short-name> <task-number> --expected-task-digest <digest> --expected-snapshot <digest>
<sdd-cli> --root <project-root> --json archive <short-name> --expected-snapshot <digest> --summary <single-line>
<sdd-cli> --root <project-root> --json abandon <short-name> --expected-snapshot <digest> --summary <single-line>
<sdd-cli> --root <project-root> --json doctor
<sdd-cli> --root <project-root> --json rebuild-index
```

- Execute discovery and each CLI invocation as one unwrapped tool call. Do not add pipes, redirects, command chaining, or an exit-code helper.
- Consume the discovery JSON first. Continue only when `ok` is true, `runtime.source` is `package-local`, and the handshake identifies `sdd-workflow`; use the returned installed runtime path only as evidence that it is the same package-local `scripts/sdd.py`. A discovery failure is binding and never falls back to another candidate.
- Consume the JSON document even when the process exits nonzero. Branch on `ok`, then `errors[].code` and `errors[].action`; never branch on message wording.
- If the launcher, Python runtime, or tool permission is unavailable, stop and report the execution problem. Do not open the artifacts and do not fall back to prose parsing.
- Never read raw artifacts to derive status, task order or counts, acceptance conditions, diagnostics, compatibility, snapshots, or managed-state evidence. Direct artifact access is allowed only when creating a new proposal, editing user-authorized semantic prose during an explicit revision, or recording the conclusion body of an approved Schema v2 research proposal; never use it to mutate managed fields.
- `list` discovers candidates but never selects among multiple entries. `status` is the source for status, ordered tasks, source lines, completion, acceptance conditions, compatibility, and snapshot. `validate` is the strict structural gate. `abandon-preflight` is the only degraded task-format path.
- Common error actions are binding: `select_project_root` or `choose_short_name` requires user input; `create_or_select_proposal` stops mutation; `inspect_project_path`, `inspect_machine_metadata`, `inspect_managed_state_drift`, `inspect_archive_state`, `use_supported_engine`, `upgrade_or_recreate_proposal`, `fix_artifact_format`, and `report_internal_error` stop and report their evidence. `refresh_status` means rerun `status` and stop for renewed intent, not retry a mutation automatically. `begin_revision` or `begin_revision_and_reapprove` requires the explicit revision flow. `rebuild_index` may run only when the terminal result says the directory move committed or doctor reports only a rebuildable stale INDEX.

New or revised `tasks.md` content must use one first-column top-level line per task with the exact marker `- [ ] `, no checkbox subtasks, and a `## 驗收條件` section after the tasks. This is an authoring contract; the CLI alone decides whether an artifact is valid and how it is counted.

## Phase 1: 提案

When the user says `提案` and describes a requirement:

1. Inspect the current project enough to understand existing behavior and likely files. Do not modify implementation files.
2. Choose a short English name in lowercase hyphen-case, such as `add-todo` or `fix-login`. Before creating files, check whether `sdd/<short-name>/` already exists. Do not overwrite an existing directory; ask whether to revise it or choose another name.
3. Classify the change as exactly one of `新功能`, `修 bug`, `重構`, `維運`, `文件`, or `研究`. Use `研究` for a bounded evidence question whose deliverable is a conclusion, while retaining the normal lifecycle. Do not invent labels, impact taxonomies, or type-specific required sections. Treat the classification as human-readable metadata for proposal reports and archive lookup, not as a separate workflow.
4. Create `sdd/<short-name>/proposal.md` as Schema v2, starting with the exact frontmatter `---`, `schema_version: 2`, `---`, then these sections and status `draft`: `# <short name>`, `## 狀態`, `## 類型`, `## 為什麼做`, `## 要改什麼`, and `## 影響範圍`. For `研究`, also add `## 結論`, initially empty. Explain the problem, requested behavior or research question, and likely files in plain language; mark uncertain paths as estimates. For `修 bug`, include a reproduction task and regression validation when reasonable.
5. Create `sdd/<short-name>/tasks.md` with a top-to-bottom checklist following the authoring contract. Each task represents one independently verifiable behavior change with a specific test or observable result. Keep at most 10 tasks; if that is not reasonable, ask the user to split the change.
6. Add plain-language scenarios under `## 驗收條件`.
7. Run strict `validate`, then `status`. If either fails, report its code/action and stop without implementing. From the canonical result, show the short name, classification, key behavior changes, task count, and acceptance scenarios. Stop and wait for explicit approval; never implement in this turn.

If requirements are materially ambiguous, ask a focused question before creating the proposal. Do not silently expand scope.

## Proposal revisions

1. Stop implementation and run `status`. Continue only when it succeeds and reports `mutation_safe: true`. If status is `approved`, call `begin-revision` with that exact snapshot before editing prose; if status is already an authorized `draft`, continue. Any error/action stops the revision.
2. Revise the proposal, affected acceptance conditions, and impact scope to reflect only the agreed amendment. Never edit status or checkbox markers.
3. Preserve every checked task exactly as implementation history: do not rewrite, delete, or renumber it. Revise or remove an unchecked task only when explicitly superseded. Append new work without reusing prior task identity. Keep at most 10 unchecked tasks; if the amendment cannot fit or materially changes the goal, ask for a new change.
4. Run strict `validate` and `status`. Report the canonical revised behavior, retained completed tasks, and changed unchecked tasks.
5. Stop and wait for `開始實作`; do not resume implementation in the revision turn.

## Phase 2: 實作

1. Resolve the active short name and run `status` before changing code. Missing artifacts, invalid format, unsafe legacy compatibility, or any other error stops the phase according to its code/action; never repair or create artifacts implicitly.
2. Apply the approval gate to the canonical status; missing status is never implicit approval:
   - `approved`: continue.
   - `draft` or missing with only `實作`: ask whether the user approves and stop.
   - `draft` with `開始實作`: call `approve` with the status snapshot, then use its after snapshot/result and verify with `status` before continuing.
   - Any other status: stop and report it.
3. Use the canonical acceptance conditions and first unchecked task in source order. Work on only that task, first inspecting reusable project patterns.
4. Make the smallest change that satisfies the task; do not implement later work early.
5. Validate proportionally. If validation exposes a specification gap or wrong direction, stop and report the required decision.
6. Before completion, compare the result against the task's exact canonical wording and acceptance conditions. Only then call `complete-task` with its canonical ordinal, `task_digest`, and the exact snapshot from the status used to select it.
   For `研究`, write observed results only under `## 結論`; before completing the final task, rerun `status` and require a non-empty canonical `research_conclusion`. This conclusion is output, not a scope revision, and no other approved prose may be changed through this exception.
7. Require `APPLIED` or evidence-backed `ALREADY_APPLIED`, then rerun `status` and verify that the intended task alone became complete. Report `第 N 條完成` with the validation result.
8. Continue one task at a time, rerunning `status` before each mutation. Follow any new user instruction instead of continuing automatically.
9. When the canonical result reports every task complete, report `全部完成` and ask the user to verify acceptance. Do not archive until the user says `歸檔`.

Never mark a task complete merely because code was written.

## Abandonment preflight: 放棄 / 取消提案

1. Resolve the active short name and run `abandon-preflight` as one readonly CLI call. Structural, path, schema, or runtime errors stop according to their code/action. Task-format diagnostics appear as warnings and never lock the user out of abandonment.
2. Report the canonical short name, status, completed and total counts, and completed-task list. When `task_counts_reliable` is false, label the counts and completed-task list `任務計數不可靠` and report warning locations without repairing anything.
3. State that abandonment archives only SDD artifacts; implementation code and git changes remain in the working tree and are not reverted.
4. Print `snapshot.proposal_sha256` and `snapshot.tasks_sha256`, labeled with their artifact names, in the user-facing report so the transcript retains the snapshot. Do not calculate replacement values, write confirmation state, or modify artifacts.
5. Ask for exactly `確認放棄 <short-name>`, using the real name, then stop. Preflight never changes status, moves a directory, or updates `INDEX.md`.

## Abandonment execution: 確認放棄

1. Execute only when the current conversation contains both hashes printed by a successful preflight for the same exact short name. Run a fresh `abandon-preflight`, then use an execution-environment string comparison between each transcript hash and its corresponding fresh JSON field. Act only on the comparison result; never compare long values visually and never replace the expected side with a fresh value.
2. If the name is missing or differs, the transcript lacks either valid 64-character lowercase hexadecimal value, the new preflight fails, or either comparison differs, do not execute. Report the evidence, present the new preflight if available, and stop for a new exact confirmation. Never reuse stale confirmation or persist it to a file.
3. Create a concise single-line summary, then call `abandon` with the freshly verified `snapshot.snapshot_digest` and summary. Require `APPLIED`, `ALREADY_APPLIED`, or the committed-stale handling below.

## Terminal result procedure

Both terminal paths use this one procedure after their own preconditions pass:

| Parameter | Abandonment execution | Phase 3: 歸檔 |
| --- | --- | --- |
| terminal status | `abandoned` | `completed` |
| destination | `sdd/archive/YYYY-MM-DD-<short-name>-abandoned/` | `sdd/archive/YYYY-MM-DD-<short-name>/` |
| final report | `已放棄` plus summary, retained work warning, and completed tasks | `歸檔完成` plus summary |

1. Branch on the terminal command's machine result. `APPLIED` and `ALREADY_APPLIED` are success. `COMMITTED_DERIVED_ARTIFACT_STALE` means the authoritative move succeeded: do not move it back; inspect diagnostics and run `rebuild-index`, then verify it. Other errors stop according to their stable action.
2. Never create, move, merge, overwrite, delete, or edit an archive directory or INDEX directly. Use `doctor` for ambiguous/partial evidence and report the required manual decision.
3. Give the selected final report. For abandonment, repeat unreliable-count warnings when applicable and never revert implementation code.

## Phase 3: 歸檔

1. Run `status` and stop on any error according to its code/action; do not inspect artifacts as fallback.
2. Require at least one canonical task and require every task complete. Otherwise report the canonical unchecked task numbers and stop.
3. Create a concise single-line summary and call `archive` with the current status snapshot. Handle its result through the Terminal result procedure.

## Progress reporting

Keep reports short and concrete. At proposal completion, show the plan and wait. During implementation, report only the completed task, validation result, and blockers. When a requirement is missing, surface the exact decision and pause.
