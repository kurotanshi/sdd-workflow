---
name: sdd-workflow
description: "Manage software changes through a proposal-first SDD workflow: create or revise a scoped proposal and checklist, wait for explicit approval before implementation, execute one task at a time with progress reports, and archive completed or abandoned work. Use only when the user explicitly invokes sdd-workflow or refers to an SDD proposal with 提案, 自審提案, 開始實作, 實作, 歸檔, 放棄, 取消提案, or 確認放棄. Generic cancellation without an explicit SDD proposal target is outside this skill. Source-control or code rollback is outside SDD: confirm its exact scope before changing files and never alter proposal state because of it."
---

# SDD Workflow

Enforce `提案 → 實作 → 歸檔`, including managed revision and abandonment.

## Invariants

- State the plan before implementation. Never modify implementation files unless canonical proposal status is `approved`.
- Phase words act only as explicit commands targeting this workflow or a proposal. Narrative mentions do nothing; unclear intent requires a question.
- `開始實作` explicitly approves a `draft`. Plain `實作` continues only an `approved` proposal; otherwise ask for approval and stop.
- Requirement changes during implementation or acceptance enter managed revision and require new `開始實作`.
- Run package-local discovery once before the first SDD CLI command in a session. Zero, ambiguous, failed, or incompatible discovery must fail closed. Never substitute a runtime from `PATH`, another checkout, or another Agent's Skill root.
- The bundled CLI is the only authority for discovery, parsing, validation, canonical status, tasks, acceptance, snapshots, diagnostics, managed fields, terminal moves, and INDEX. If it fails, fail closed and never fall back to prose parsing.
- Never directly edit lifecycle status, checkbox markers, machine metadata, archive paths, or INDEX. Direct prose edits are limited to new draft authoring, authorized revision prose, and an approved research conclusion.
- Work on and verify one canonical task at a time. Do not invent requirements, combine unrelated changes, or mark a task complete merely because code was written.
- Abandonment requires read-only preflight followed by exact `確認放棄 <short-name>`. It retains implementation and Git work.
- Source-control rollback is outside SDD. Confirm its exact scope and never change proposal state because of it.
- Do not create Git commits unless requested.

## Phase selection

- `提案`: create a draft or revise the named proposal; do not implement.
- `自審提案 [short-name]`: review an existing proposal; never approve or implement. Match this explicit command before its `提案` substring.
- `開始實作`: approve a draft, verify `approved`, then implement tasks.
- `實作`: continue an approved proposal only.
- `歸檔`: archive only after user acceptance and reliable full completion.
- `放棄 [short-name]` or `取消提案`: run abandonment preflight and stop.
- `確認放棄 <short-name>`: abandon only after matching successful preflight evidence in this conversation.

A bare or ambiguous cancellation such as `取消剛才的變更` requires one question distinguishing code/Git restoration from proposal abandonment; run nothing first. Explicit code rollback still requires exact-scope confirmation and never changes proposal state. Never offer a bare `取消` as a phase-menu option.

When invoked without a phase, ask for `提案`, `自審提案`, `開始實作`, `實作`, `歸檔`, `放棄`, or `取消提案`. If no short name is given, use `list --state active`; continue automatically only when exactly one active candidate exists. With two or more candidates, stop and request the short name—even if only one appears approved; never choose by status or modify a candidate first.

## CLI contract

`<skill-dir>` is this skill directory. Use its runtime only:

```text
python3 <skill-dir>/scripts/discover-runtime.py
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json list --state active
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json validate <short-name>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json status <short-name>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json approve <short-name> --expected-snapshot <digest>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json begin-revision <short-name> --expected-snapshot <digest>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json complete-task <short-name> <ordinal> --expected-task-digest <digest> --expected-snapshot <digest>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json abandon-preflight <short-name>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json archive <short-name> --expected-snapshot <digest> --summary <single-line>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json abandon <short-name> --expected-snapshot <digest> --summary <single-line>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json doctor
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json rebuild-index [--directory <name> --summary <single-line>]
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json repair-proposal-format <short-name> [--type <type> --scope <text> --acceptance <text>]
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json repair-archive-record <directory-name> [--terminal-status <status> --summary <single-line> --expected-proposal-sha256 <digest> --expected-tasks-sha256 <digest>]
```

Execute discovery and every CLI call as one unwrapped, noninteractive command. Continue only when discovery returns `ok: true`, source `package-local`, and distribution `sdd-workflow`. Consume complete JSON even on nonzero exit; branch on `ok`, then stable `errors[].code` and binding `errors[].action`, never message prose.

`status` is authoritative for ordered tasks, completion, acceptance, compatibility, and snapshot. `validate` is the strict format gate; only `abandon-preflight` may report unreliable task counts. Before handling any CLI error, abandonment, archive recovery, or doctor finding, read [`references/runtime-recovery.md`](./references/runtime-recovery.md) fully and follow it without improvised edits or retries.

Before the first mutation in an implementation sequence, obtain fresh successful `status`. A successful `approve` or `complete-task` result then supplies the canonical `after_state`, exact next snapshot, and `next_task` for the next mutation in that sequence. `refresh_status` never preserves mutation intent automatically. If a response is lost, retry once with identical inputs to obtain `ALREADY_APPLIED` evidence.

## 提案

Before creating, revising, or inspecting a repository for a proposal, read [`references/proposal-authoring.md`](./references/proposal-authoring.md) fully; only runtime discovery may precede that read.

Inspect the minimum project context needed by that reference, author Schema v2 `proposal.md` and `tasks.md`, then run `validate` and `status`. On success report canonical short name, type, behavior, task count, and acceptance scenarios. Stop for explicit approval. Material ambiguity requires one focused question before authoring.

A research draft ends at an empty `## 結論`: never add placeholder text or perform the review during intake.

For higher-risk changes, do not draft until user targets plus relevant guidance, architecture, configuration, callers, and tests are read or a scoped search proves a category absent. Never inspect eval fixtures or run application code in the project workspace.
Use only targeted paths and searches: never `pwd`, `ls`, `find`, `tree`, or a root-wide glob; search tests by imports or references to the target modules, not guessed test filenames.
A generic `*` search satisfies nothing. Search `architecture*`, `*config*`, callers, and test imports/references separately, read each match, then draft.
Do not open a file merely to decide whether it is relevant; ignore search results outside those named evidence categories, including unrelated directories.

## 自審提案

Run only on explicit `自審提案`. Read [`references/self-review.md`](./references/self-review.md) fully, run `status`, and apply its evidence layers and report contract.

For a `draft`, correct only concrete evidence-backed prose or unchecked-task defects, then rerun `validate` and `status`; itemize every task edit and counts before/after. Never resolve conflicting proposals for the user. For `approved`, prose is frozen: report findings and require `提案` for changes. Never call `approve` and never implement.
An authority split is a conflicting design decision: never rewrite it or return `通過`; name the authoritative and duplicate locations, explain drift, and ask the user to choose a direction.

## Revision

Stop implementation and run `status`. If approved, call `begin-revision` with its snapshot before editing prose. Change only agreed semantics, preserve checked task text and order, keep at most ten unchecked tasks, and use a new proposal for a materially different goal. Run `validate` and `status`, report retained completion and revised scope, then stop for new `開始實作`.

## Implementation

1. Run fresh `status`; continue only from `approved`, or approve a draft when the command is `開始實作` and require successful `after_state`.
2. Select the next unchecked canonical task and its acceptance conditions. Inspect the target files, related tests, and enough existing project patterns to make the smallest in-scope change. Consult applicable official documentation only when correctness depends on a versioned tool or dependency.
3. Validate proportionally using relevant project-declared quality commands. A script's existence alone does not declare a gate. Conflicting declarations, missing necessary external evidence, a specification gap, or a changed outcome stop for a decision or revision.
4. Compare the result with the exact task and acceptance. For research, write only observed output under `## 結論` and require a non-empty canonical conclusion.
5. Call `complete-task` with current ordinal, task digest, and snapshot. Require `APPLIED` or evidence-backed `ALREADY_APPLIED`, and verify from `after_state` that only the intended task completed.
6. Report `第 N 條完成` and validation, then use `next_task` and the returned snapshot for the next item. At full completion report `全部完成` and request acceptance; do not archive yet.

## Abandonment

Read the recovery reference, run `abandon-preflight`, and report canonical progress, warnings, whether counts are reliable, retained code/Git work, and labeled `proposal_sha256` and `tasks_sha256`. Ask for exact `確認放棄 <short-name>` and stop.

Confirmation is valid only when both 64-character hashes from that successful preflight appear in this conversation. Rerun preflight and machine-compare each transcript hash with its fresh counterpart. Missing or changed evidence requires new confirmation; matching evidence permits `abandon` with the fresh snapshot.

## Archive and terminal results

Run `status`; require at least one task, reliable counts, and all tasks complete. Call `archive` with its snapshot and a concise summary. `APPLIED` and `ALREADY_APPLIED` succeed. `COMMITTED_DERIVED_ARTIFACT_STALE` means the terminal move committed; never move it back, and recover INDEX through the recovery reference. Other errors follow their binding action. Never manipulate archive directories or INDEX directly.

## Reporting

Write all user-facing workflow reports, questions, and error explanations in Traditional Chinese. Keep them short and evidence-based: canonical state, completed task and validation, blocker, next permitted action, and exact user action. Preserve the lifecycle report tokens `第 N 條完成`, `全部完成`, `歸檔完成`, and `已放棄`. Never infer an actor, cause, approval, or path the runtime did not prove.
