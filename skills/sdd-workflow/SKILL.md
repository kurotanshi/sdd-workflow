---
name: sdd-workflow
description: "Manage software changes through a proposal-first SDD workflow: create or revise a scoped proposal and checklist, wait for explicit approval before implementation, execute one task at a time with progress reports, and archive completed or abandoned work. Use only when the user explicitly invokes sdd-workflow or refers to an SDD proposal with 提案, 自審提案, 開始實作, 實作, 歸檔, 放棄, 取消提案, or 確認放棄. Generic cancellation without an explicit SDD proposal target is outside this skill. Source-control or code rollback is outside SDD: confirm its exact scope before changing files and never alter proposal state because of it."
---

# SDD Workflow

Enforce `提案 → 實作 → 歸檔`, including explicit revision and abandonment.

## Non-negotiable rules

- State the plan before implementation. Never modify implementation files unless canonical proposal status is `approved`.
- A phase word acts only as an explicit command targeting this workflow or a proposal. Narrative mentions do nothing; unclear intent requires a question.
- `開始實作` explicitly approves a `draft`. Plain `實作` continues only `approved`; for draft or missing status, ask for approval and stop.
- Requirement changes during implementation or acceptance always enter managed revision and require new `開始實作`; never hide new scope in task completion.
- Run package-local discovery once before the first SDD CLI command in a session. Zero, ambiguous, failed, or incompatible discovery stops; never search `PATH`, another checkout, or another Agent's Skill root, because a runtime from elsewhere can apply a different contract to the same artifacts.
- The bundled CLI is the only authority for discovery, parsing, validation, canonical status/tasks/acceptance, snapshots, diagnostics, managed fields, terminal moves, and INDEX. If unavailable, fail closed and do not fall back to prose parsing, because prose parsing cannot reproduce the canonical rules and drifts silently.
- Never directly edit lifecycle status, checkbox markers, machine metadata, archive paths, or INDEX. Direct prose access is limited to new draft authoring, explicitly authorized revision prose, and an approved research conclusion.
- Work on and verify one canonical task at a time. Do not invent requirements, combine unrelated changes, or mark completion merely because code was written.
- Abandonment is read-only preflight followed by exact `確認放棄 <short-name>`. It never reverts implementation or Git changes, so abandoning a proposal can never destroy work.
- Source-control rollback is outside SDD. Confirm its exact scope and never change proposal state because of it.
- Do not create Git commits unless requested.

## Phase selection

- `提案`: create a new draft or explicitly revise the named proposal; no implementation.
- `自審提案`, `自審提案 <short-name>`: adversarial review of an existing proposal; never approves and never implements. Selecting this phase requires the user to be issuing it as a phase command, not merely mentioning the term inside a descriptive, quoted, or documentation request such as `在 README 說明「自審提案」`. Once that holds, `自審提案` takes precedence over its substring `提案`, which must never match inside it. Never author or create a proposal on `自審提案`.
- `開始實作`: approve a draft with the CLI, verify `approved`, then implement one task at a time.
- `實作`: continue an approved proposal only.
- `歸檔`: archive only after user acceptance and reliable full task completion.
- `放棄`, `放棄 <short-name>`, `取消提案`: run abandonment preflight and stop.
- `確認放棄 <short-name>`: abandon only when this conversation contains a matching successful preflight.
- A bare `取消`, or a cancellation request whose target is unclear—including `取消剛才的變更`, `算了`, `先不要`, or `不用了`—requires one question naming both choices: restore code/Git, or abandon the SDD proposal. Run no command first. Explicit code rollback such as `取消剛才的程式碼修改` is outside SDD and still requires exact-scope confirmation.

If invoked without a phase, ask for `提案`, `自審提案`, `開始實作`, `實作`, `歸檔`, `放棄`, or `取消提案`. Never offer a bare `取消` as a menu option. If no short name is given, use `list --state active`; continue automatically only for exactly one active candidate, never an archive directory.

## Deterministic command contract

`<skill-dir>` is the directory containing this file. The bundled CLI is
`python3 <skill-dir>/scripts/sdd.py`:

```text
python3 <skill-dir>/scripts/discover-runtime.py
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json list --state active
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json validate <short-name>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json status <short-name>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json abandon-preflight <short-name>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json approve <short-name> --expected-snapshot <digest>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json begin-revision <short-name> --expected-snapshot <digest>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json complete-task <short-name> <ordinal> --expected-task-digest <digest> --expected-snapshot <digest>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json archive <short-name> --expected-snapshot <digest> --summary <single-line>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json abandon <short-name> --expected-snapshot <digest> --summary <single-line>
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json doctor
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json rebuild-index [--directory <name> --summary <single-line>]
python3 <skill-dir>/scripts/sdd.py --root <project-root> --json repair-archive-record <directory-name> [--terminal-status <status> --summary <single-line> --expected-proposal-sha256 <digest> --expected-tasks-sha256 <digest>]
```

- Execute discovery and each CLI command as one unwrapped, noninteractive call: no pipe, redirect, chaining, or exit-code helper.
- Continue discovery only when JSON says `ok: true`, source `package-local`, and handshake distribution `sdd-workflow`; use that same resolved package runtime.
- Consume the complete JSON even on nonzero exit. Branch on `ok`, then stable `errors[].code` and `errors[].action`, never message prose.
- `status` is authoritative for ordered tasks, completion, acceptance, compatibility, and snapshot. `validate` is the strict format gate; `abandon-preflight` alone permits unreliable task-format counts.
- Any error action is binding. Read [`references/runtime-recovery.md`](./references/runtime-recovery.md) fully before handling an error, abandonment, archive recovery, or doctor finding. Do not improvise repair or retry.
- Before the first mutation in an implementation sequence, obtain fresh successful `status`. A successful `approve` or `complete-task` result then supplies the canonical `after_state`, exact next snapshot, and `next_task` for the next mutation in that sequence. `refresh_status` never preserves mutation intent automatically.

## 提案

Before authoring, revising, or any repository inspection for a proposal, read
[`references/proposal-authoring.md`](./references/proposal-authoring.md) fully.

1. Inspect enough project context to describe current behavior and likely files; do not implement. When the reference's high-risk review gate applies, use this closed discovery sequence before authoring:
   - Read the user-named targets first.
   - For each still-missing category—applicable project guidance, architecture decisions, configuration, affected core flow and callers, and tests—search that category separately using only a targeted filename or reference search. Do not combine missing categories into one search. After each search, read every decision-relevant match before moving to the next category; a search-result listing is not inspected evidence.
   - Stop as soon as every category has enough decision evidence. Do not list the repository root, use repo-wide globs, or run content searches without an explicit file, path, or include scope. Treat a filename, path, or search context as sufficient to exclude an unrelated candidate; never list its directory or open it merely to confirm or prove it is unrelated.
2. Author the Schema v2 draft and top-level task checklist exactly as the reference requires.
3. Run `validate`, then `status`. On success report canonical short name, type, behavior, task count, and acceptance scenarios.
4. Stop for explicit approval. Never implement in the proposal turn.

Material ambiguity requires a focused question before authoring.

## 自審提案

Optional on-demand review. Never automatic; run only on explicit `自審提案`.

Before reviewing, read [`references/self-review.md`](./references/self-review.md) fully.

1. Run `status`. Report canonical state before reviewing.
2. Run the review layers defined in the reference. Every finding needs a concrete location; drop findings that cannot name one.
3. `draft`: correct prose gaps and a genuinely defective task list in place, then rerun `validate` and `status`; itemise every task-level edit and give the task count before and after. Never resolve a conflict between proposals; report that for the user to decide. `approved`: never edit prose, report only and state that applying anything requires `提案`.
4. Report the verdict in chat as the reference requires, then stop. Never call `approve` and never implement.

A design-direction finding is a question for the user, never a decision this skill makes.

## 修訂

1. Stop implementation and run `status`; continue only when mutation-safe.
2. If approved, call `begin-revision` with that snapshot before editing prose. An already authorized draft may be edited directly.
3. Change only the agreed semantics. Preserve checked task text/order as history; keep at most 10 unchecked tasks and use a new proposal when the goal materially changes.
4. Run `validate` and `status`, report retained completed work and revised pending scope, then stop for new `開始實作`.

Never edit status or checkbox markers during revision.

## 實作

1. Run fresh `status`. Errors stop according to their binding action. Treat it as the current canonical state.
2. Approval gate: `approved` continues; draft plus `開始實作` calls `approve` and requires its successful `after_state`; draft plus plain `實作` asks for approval and stops.
3. Select the intended unchecked task from the current canonical state and its acceptance conditions. Before editing, load the minimum context packet: the current task and acceptance conditions, target files, related tests, and one existing similar pattern. If no similar pattern exists, say so and continue; do not load unrelated history or create a context artifact. When correctness depends on a framework, library, SDK, or tool version, identify the version from project dependency evidence and consult the applicable official documentation before choosing the pattern.
4. Validate proportionally. Cite the official source for version-dependent decisions; if a necessary source cannot be verified, stop and report a blocker rather than claiming verification. Apply only a Definition of Done or quality command explicitly declared for the project in scoped instructions, contributor guidance, or CI documentation and relevant to this change. An existing script alone is not a declaration; conflicting declarations stop with an ambiguity report; no declaration means do not invent a new gate. A specification gap or changed outcome stops for a decision/revision.
5. Compare the result with exact task wording and acceptance. For research, write only observed output under `## 結論` and require a non-empty canonical conclusion before final completion.
6. Call `complete-task` with the current ordinal, task digest, and snapshot. Require `APPLIED` or evidence-backed `ALREADY_APPLIED`.
7. Require its `after_state` to prove only the intended task completed, then report `第 N 條完成` plus validation. Use that state and `next_task` for the next task without another `status`; if the response was lost, retry once with the same inputs so operation evidence can return `ALREADY_APPLIED`.
8. At full completion report `全部完成` and request acceptance; do not archive without `歸檔`.

## 放棄

Preflight:

1. Read the recovery reference, run `abandon-preflight`, and stop on structural/runtime errors.
2. Report canonical progress; label unreliable counts and warning locations.
3. State that code and Git are retained. Print labeled `proposal_sha256` and `tasks_sha256`.
4. Ask for exact `確認放棄 <short-name>` and stop without mutation.

Execution requires both printed 64-character hashes from a successful preflight for the same short name in this conversation. Rerun preflight and machine-compare each transcript hash with its corresponding fresh field. Any missing/different evidence stops for a new confirmation. On a match, call `abandon` with the fresh snapshot and a concise summary.

## 歸檔 and terminal results

1. Run `status`; require at least one task, reliable counts, and every task complete.
2. Call `archive` with the fresh snapshot and concise summary.
3. `APPLIED` and `ALREADY_APPLIED` succeed. `COMMITTED_DERIVED_ARTIFACT_STALE` means the terminal move committed: never move it back; follow the reference's INDEX recovery. Other results stop by action.
4. Never manipulate archive directories or INDEX directly. Use `doctor` for ambiguous evidence.
5. Report `歸檔完成`, or `已放棄` plus retained-work/count warnings, and the summary.

## Reporting

Write all user-facing workflow output—reports, questions, and error explanations—in Traditional Chinese, matching the built-in trigger words and report tokens. Keep reports short: current canonical state, completed task and validation, blocker, next permitted action, and exact user action. Never infer an actor, cause, approval, or path that the runtime did not prove.
