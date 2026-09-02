# Proposal authoring reference

Read this file completely before creating, revising, or inspecting the
repository for an SDD proposal.

## New proposal

Intake, before authoring:

- Identify implicit assumptions and missing information that could
  materially change the requested behavior, scope, impact, or acceptance
  conditions.
- A requested implementation approach is not automatically the desired
  outcome; when the difference would change the proposal, treat it as
  material ambiguity.
- On material ambiguity, briefly state the decision-relevant assumptions or
  gaps and ask exactly one most-critical question; do not create the draft
  before the answer.
- Otherwise create the draft directly, marking safely deferable uncertainty
  in the proposal. Never emit a fixed analysis report or force a question
  when the answer cannot change the proposal.

Conditional implementation-readiness review:

- Run this review only for cross-module, high-risk, stateful, migration,
  deployment, or external/irreversible side-effect changes. For a small,
  low-risk proposal with sufficient information, skip the review and author
  the draft directly.
- When the review applies, before drafting, make one bounded discovery pass for
  decision-relevant repository evidence using this closed discovery sequence;
  targeted filename and reference searches are the only allowed expansion:
  1. Read the user-named targets first.
  2. For each still-missing category—applicable project guidance and
     requirements, architecture decisions, configuration, the affected core
     flow and callers, and tests—search that category separately using only a
     targeted filename or reference search. Do not combine missing categories
     into one search. After each search, read every decision-relevant match
     before moving to the next category; a search-result listing is not
     inspected evidence. A file not named by the user is not evidence that no
     applicable guidance or configuration exists.
  3. Stop as soon as every category has enough decision evidence; do not scan
     the repository aimlessly. Do not list the repository root, use repo-wide
     globs, or run content searches without an explicit file, path, or include
     scope. Treat a filename, path, or search context as sufficient to exclude
     an unrelated candidate; never list its directory or open it merely to
     confirm or prove it is unrelated.
  Do not modify product code or turn intake into a standalone review report.
- When the review applies, check requirement completeness; consistency among
  the proposal, tasks, and acceptance conditions; repository feasibility;
  state, failure, retry, and recovery boundaries; and whether acceptance can
  be verified.
- Use that evidence to test whether the current or requested technical approach
  satisfies the desired outcome and whether a simpler, more secure, or more
  maintainable alternative would change the proposal's behavior, scope,
  impact, or acceptance conditions. Such an alternative is material ambiguity
  and follows the existing one-question rule. When no proposal-changing
  alternative is evidenced, author the final direction directly without a
  separate architecture or security review report.
- A blocking gap that would change the proposal follows the existing material
  ambiguity rule before artifacts are created. Record safely deferable
  uncertainty in the draft. Do not emit fixed `READY`, `READY WITH
  NON-BLOCKING FINDINGS`, or `BLOCKED` verdicts.
- For stateful or external-side-effect changes, use the existing `## 要改什麼`,
  tasks, and acceptance conditions to identify the source of truth, commit point, retry/recovery behavior,
  and effects that must not repeat. Use `## 影響範圍`
  only for file estimates and presentation details. Do not add schema fields,
  metadata, or another artifact.
- A full repository, architecture, or security review that the user wants
  tracked and archived through SDD is a bounded `研究` proposal whose report is
  the deliverable. A one-off read-only review need not enter SDD, and neither
  case expands `自審提案` beyond reviewing an existing proposal.

Compact examples for triggered reviews:

- Migration: name the authoritative old/new data, the cutover commit point,
  how an interrupted run resumes, and any transformation that must not repeat.
- External API: name the local authoritative record, when a remote result is
  committed locally, how ambiguous responses are recovered, and calls such as
  charging that must not repeat.
- Message publication: name the event/outbox authority, the publication commit
  point, stable identity used for retry, and event creation that must not repeat.
- Deployment: name the desired-release authority, the traffic-switch commit
  point, retry/rollback boundary, and irreversible migration that must not repeat.

1. Choose a unique lowercase English hyphen-case short name. Never overwrite an existing `sdd/<short-name>/`; ask whether to revise it or choose another name.
2. Classify as exactly one of `新功能`, `修 bug`, `重構`, `維運`, `文件`, or `研究`. `研究` asks a bounded evidence question and uses the normal lifecycle.
3. Create `proposal.md` as Schema v2 beginning at byte zero:

   ```text
   ---
   schema_version: 2
   ---
   ```

4. Use `# <short-name>`, then exactly these level-two sections:
   `## 狀態` (`draft`), `## 類型`, `## 為什麼做`, `## 要改什麼`, and
   `## 影響範圍`. Research also requires an initially empty `## 結論`.
5. Explain the problem, requested behavior/question, and likely files in plain language. In the approval-relevant `## 要改什麼`, state any decision-relevant behavior, interface, or data contract that must remain unchanged, plus meaningful out-of-scope boundaries. Scale this to the risk: one verifiable sentence is enough for a small change, and when no such baseline affects the decision, add no placeholder. Keep file estimates and presentation details in `## 影響範圍`; do not add a heading, schema field, template, or artifact for these baselines. Mark uncertain file paths as estimates. A bug fix should include reproduction and regression validation when reasonable.
6. Create `tasks.md` with a heading, then one first-column top-level line per task using the exact incomplete marker `- [ ] `. Do not use checkbox subtasks or other list items in the task region.
7. Each task is one independently verifiable behavior change with a specific test or observable result. A new proposal has at most 10 tasks.
8. After the tasks, add `## 驗收條件` and plain-language observable scenarios.

For cross-file or cross-module work, order tasks by dependency and prefer
vertical slices that leave the system usable and independently verifiable after
each task. A horizontal prerequisite is acceptable only when the proposal
states why it cannot form a usable slice yet. Do not impose a fixed file-count
limit or create another planning artifact; small, obvious changes may keep a
short proposal.

The CLI alone decides whether the artifact is valid or how tasks are counted.
Do not reproduce parser rules or normalize text manually.

## Revision

- Edit only user-authorized semantic prose while the proposal is in an authorized draft/revision state.
- Never edit lifecycle status, checkbox markers, `.sdd` metadata, archive paths, or INDEX.
- Preserve every checked task exactly in place as implementation history.
- Revise/remove an unchecked task only when explicitly superseded; append new work without reusing an old task identity.
- Keep at most 10 unchecked tasks. A materially different goal becomes a separate proposal.
- Acceptance-time changes are ordinary scope changes: revise proposal scope, affected tasks, acceptance conditions, and impact, then validate and stop for reapproval.

## Worked example

A complete, minimal, valid pair. Copied verbatim into `sdd/fix-login-empty-email/`,
both files pass `validate` and `status` unchanged. The CLI remains the format
authority; this example illustrates the rules above, it does not replace them.

`proposal.md`:

```text
---
schema_version: 2
---
# fix-login-empty-email

## 狀態
draft

## 類型
修 bug

## 為什麼做
登入表單允許空白 email 送出，後端回 500。重現：在登入頁留空 email 按送出。預期應在前端擋下並顯示錯誤訊息。

## 要改什麼
在送出前驗證 email 非空且格式正確；錯誤時顯示「請輸入有效的 email」。保持後端 API 不變。

## 影響範圍
- 僅登入頁前端驗證。可能檔案：`src/pages/login.tsx`（預估）。
- 新增回歸測試防止再發。
```

`tasks.md`:

```text
# fix-login-empty-email 任務

- [ ] 新增失敗回歸測試：空白 email 送出應被前端擋下並顯示錯誤訊息
- [ ] 實作送出前 email 驗證，讓回歸測試通過

## 驗收條件
- 情境：登入頁留空 email 按送出，表單不送出並顯示「請輸入有效的 email」
- 情境：輸入合法 email 可正常送出，行為與修復前相同
```
