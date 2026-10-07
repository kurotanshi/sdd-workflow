# Proposal authoring reference

Read this file completely before creating, revising, or inspecting a repository for an SDD proposal. After phase selection it is the first repository read; only runtime discovery may precede it. Do not inspect evaluation harnesses or fixtures to learn the scenario. Treat a code-formatted filename in the request as a user-named target.

## New proposal

Before authoring, identify assumptions or missing information that could materially change behavior, scope, impact, or acceptance. A requested implementation is not necessarily the desired outcome. Existing behavior the user asks to preserve is an approval-relevant baseline, not missing implementation to invent. If local evidence exposes no named implementation, preserve current observable behavior or configuration as-is; never reinterpret `preserve` as adding behavior. Ask only when the missing choice changes the requested outcome or acceptance. Overlap with an existing command is not by itself material ambiguity when the user names a new interface and observable checks; preserve that interface and record the smallest distinction supported by evidence. If an existing authority already enforces the requested rule, duplicating it in a caller is material ambiguity.

When material ambiguity exists, briefly state the decision evidence or gap and ask exactly one most-critical question using one interrogative sentence and one question mark. Options may follow as declarative statements. Do not draft before the answer. Otherwise draft directly; do not force a question or emit a fixed analysis/readiness report.

### Evidence for higher-risk changes

For cross-module, high-risk, stateful, migration, deployment, or external/irreversible-side-effect changes, gather enough decision evidence before drafting. Start with user-named targets, then inspect only the relevant project guidance, architecture, configuration, affected core flow and callers, and tests needed to judge:

Before drafting, account for each applicable category with separate targeted evidence: guidance, `architecture*`, `*config*`, core flow/callers, and test imports/references. A catch-all glob cannot replace any category.

- requirement and artifact consistency;
- repository feasibility and the existing rule authority;
- state, failure, safety, retry/recovery, and verification boundaries;
- whether a simpler, safer, or more maintainable direction would materially change the proposal.

Use this closed discovery sequence:

1. Read user-named targets first.
2. For each still-missing applicable category, search separately by targeted filename or reference and read only decision-relevant matches. Architecture searches must match `architecture*`; configuration searches must match `*config*`. Search test files for imports or references to user-named modules and relevant entry points, not only by guessed filenames. A listing is not evidence.
3. Do not draft until every applicable category has a decision-relevant match read or a scoped search found no match. Then stop. Never list the repository root, use a repository-wide glob or content search, inspect unrelated files, or search broadly to prove something absent; keep unknown internals as scoped uncertainty.

Complete the applicable categories before deciding that ambiguity remains. A request to make an observable outcome happen establishes that the outcome is unmet; apparent calls do not override that premise. If repair mechanics leave outcome and acceptance unchanged, draft the smallest supported defect and fix instead of asking the user to identify the defect or choose the algorithm. If material ambiguity remains, authority is unclear, or safety evidence is insufficient, stop and apply the one-question rule rather than choosing for the user. Small low-risk work with sufficient information skips this review.

Evidence gathering is read-only. During proposal intake, never run `pwd`, `ls`, `find .`, `tree`, an unscoped Glob/Grep, application code, or an experiment that relies on cleanup afterward in the project workspace. Target explicit paths or scoped patterns. If an empirical check is indispensable, isolate it in a disposable directory outside the project.

For stateful or external effects, use `## 要改什麼`, tasks, and acceptance to identify the source of truth, commit point, retry/recovery behavior, and effects that must not repeat. Do not add metadata or a second planning artifact. A full review that needs tracked output is a bounded `研究` proposal; a one-off read-only review need not enter SDD, and neither expands `自審提案` into a repository audit.

## Artifact contract

1. Choose a unique lowercase English hyphen-case short name. Never overwrite `sdd/<short-name>/`; ask whether to revise it or choose another name.
2. Classify the change as exactly one of `新功能`, `修 bug`, `重構`, `維運`, `文件`, or `研究`. Research asks a bounded evidence question and follows the normal lifecycle.
3. Create `proposal.md` as Schema v2 beginning at byte zero:

   ```text
   ---
   schema_version: 2
   ---
   ```

4. Use `# <short-name>`, then exactly `## 狀態` (`draft`), `## 類型`, `## 為什麼做`, `## 要改什麼`, and `## 影響範圍`. A research draft ends at an empty `## 結論`; placeholder text is not a conclusion, and intake never performs the review.
5. In plain language state the problem and requested behavior. Put approval-relevant changed and unchanged behavior, interfaces, data contracts, and meaningful exclusions in `## 要改什麼`; one verifiable sentence is enough when risk is low, and no placeholder is needed when no baseline matters. Keep likely files and presentation details in `## 影響範圍`, marking uncertain paths as estimates. A bug fix includes reproduction and regression validation when reasonable.
6. Create `tasks.md` with a heading, then one first-column top-level `- [ ] ` line per task. Do not use checkbox subtasks or other lists in the task region.
7. Make each task one independently verifiable behavior change with a specific check or observable result. Use at most ten tasks.
8. Add `## 驗收條件` after the tasks, followed by plain-language observable scenarios.

Order cross-file tasks by dependency and prefer vertical slices that leave the system usable after each item. Use a horizontal prerequisite only when it cannot yet form a usable slice. Do not impose a fixed file count or create another planning artifact.

The CLI alone parses, validates, and counts artifacts. Never reproduce parser rules or normalize managed text manually.

## Revision

- Edit only user-authorized semantic prose in an authorized draft/revision state.
- Never edit lifecycle status, checkbox markers, machine metadata, archive paths, or INDEX.
- Preserve checked task text and order as implementation history.
- Revise or remove an unchecked task only when superseded; append new work without reusing old task identity.
- Keep at most ten unchecked tasks. A materially different goal becomes another proposal.
- Acceptance changes revise scope, affected tasks, acceptance, and impact; then validate and stop for reapproval.

## Worked example

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
空白 email 送出會令後端回 500。

## 要改什麼
送出前驗證 email；錯誤時顯示「請輸入有效的 email」。保持後端 API 不變。

## 影響範圍
可能檔案：`src/pages/login.tsx`（預估）。
```

`tasks.md`:

```text
# fix-login-empty-email 任務

- [ ] 新增空白 email 不送出並顯示錯誤的回歸測試
- [ ] 實作送出前驗證並讓測試通過

## 驗收條件
- 情境：空白 email 不送出並顯示「請輸入有效的 email」
- 情境：合法 email 維持原有送出行為
```
