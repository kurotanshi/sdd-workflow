# Proposal authoring reference

Read this file completely before creating or revising an SDD proposal.

## New proposal

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
5. Explain the problem, requested behavior/question, and likely files in plain language. Mark uncertain file paths as estimates. A bug fix should include reproduction and regression validation when reasonable.
6. Create `tasks.md` with a heading, then one first-column top-level line per task using the exact incomplete marker `- [ ] `. Do not use checkbox subtasks or other list items in the task region.
7. Each task is one independently verifiable behavior change with a specific test or observable result. A new proposal has at most 10 tasks.
8. After the tasks, add `## 驗收條件` and plain-language observable scenarios.

The CLI alone decides whether the artifact is valid or how tasks are counted.
Do not reproduce parser rules or normalize text manually.

## Revision

- Edit only user-authorized semantic prose while the proposal is in an authorized draft/revision state.
- Never edit lifecycle status, checkbox markers, `.sdd` metadata, archive paths, or INDEX.
- Preserve every checked task exactly in place as implementation history.
- Revise/remove an unchecked task only when explicitly superseded; append new work without reusing an old task identity.
- Keep at most 10 unchecked tasks. A materially different goal becomes a separate proposal.
- Acceptance-time changes are ordinary scope changes: revise proposal scope, affected tasks, acceptance conditions, and impact, then validate and stop for reapproval.
