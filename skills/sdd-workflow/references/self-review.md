# Self-review reference

Run this adversarial review only on explicit `自審提案`. Read this file fully before reviewing. It never approves, implements, or changes lifecycle status.

## Canonical status

- `draft`: correct concrete evidence-backed prose gaps and genuinely defective unchecked tasks in place. Preserve checked task text and order, keep at most ten unchecked tasks, then run `validate` and `status`. Itemize every task-level edit and task counts before/after. Conflicting proposals remain the user's decision.
- `approved`: prose is frozen. Report findings only; applying one requires `提案` to enter managed revision.
- Any other status: report it and stop without a verdict token.

## Evidence rules

- Every finding names a concrete location: `path:line`, command output, or canonical task ordinal. Drop findings without one.
- An authority finding names both the authoritative implementation and each duplicate location; a role name alone is not a location.
- Do not inspect evaluation harnesses or fixtures to learn expected findings.
- Finding nothing is valid. Never manufacture a finding or add generic non-goals, risk disclaimers, unaffected cases, or null/error/concurrency prose merely to demonstrate coverage.
- Edit a draft only for a concrete defect. Never claim behavior, callers, or conflicts that were not inspected.

## Layer 0 — foundation

Check the proposal's claims about current behavior against every named file, function, and setting. If a premise is wrong, stop: report `需修正`, identify the mismatch, and state that later layers were not run. Do not silently correct a wrong premise into a passing review.

## Layer 1 — correctness

Inspect enough decision evidence for each item:

1. Related code and regression: find every caller of changed functions, fields, or settings and identify affected tests.
2. Rule authority: check whether the proposal decides one rule twice, makes a client reimplement a server rule, or stores state derivable from an existing authority. Similar code alone is not a finding. A finding needs concrete locations and resulting divergence; when evidence proves a split but cannot establish which location should remain authoritative, report it and stop rather than choosing.
3. Existing state: explain what happens to existing data, formats, stored values, or settings when their shape changes.
4. Failure boundaries: cover relevant empty, error, concurrent, retry, and recovery cases; explicitly exclude a low-frequency case when appropriate.
5. Falsifiable acceptance: map every task to an observable true/false outcome.

## Layer 2 — SDD process

Check that tasks are independently verifiable, correctly ordered, and leave the system usable. Split a task that cannot be validated once. Run `list --state active` and report overlapping proposals for the user to resolve. Reject unrequested behavior, responsibility moves, abstractions, call-graph changes, or unrelated logging; ordinary local cleanup inside already-touched code is not a scope violation.

## Layer 3 — design direction

Run this layer only when existing logic in existing files changes. Pure new files, configuration additions, and copy changes skip it.

Report at most one issue that would force the same detour on the next similar request or make behavior untestable or unrecoverable. Do not report style preferences, named patterns, or generic cleanliness. A duplication finding requires at least three existing occurrences; an authority split follows Layer 1 and needs only two.

Give two to four materially different options, each with task count and touched scope. Do not choose for the user. A prior `設計取向：` line closes only the same question.

After the user chooses, record one positive `設計取向：` scope boundary inside `## 要改什麼`, including the chosen approach, where the alternative belongs, and why. Never add a `## 設計取向` heading or deliberation history. Write directly only for a `draft`; an `approved` proposal requires managed revision. Run `validate` after writing.

The line constrains module relationships and unverified cross-module cleanup, not local tidiness. It applies only to that proposal and may change through ordinary revision.

## Conditional checks

Run only those that match:

- Security: inputs, permissions, secrets, or external data. Stop when safety evidence is insufficient.
- Reversibility: deleted data, schema changes, or production configuration; state how to undo it.
- Performance: new queries or loops over growing data.
- New dependency: package, build, or CI changes.

## Reporting

Write a self-contained Traditional Chinese report in chat:

1. One verdict: `通過` when nothing remains, `需修正` for unresolved Layers 0–2 or conditional findings, or `待你決定` when only a Layer 3 choice remains. Corrected draft findings are resolved but still itemized. Never downgrade an unresolved safety finding to a passing footnote.
2. For each finding, give location, defect, and consequence. Distinguish corrected items from decisions still needed. List every task addition, removal, split, reorder, or reword and counts before/after; say when tasks were untouched.
3. For a Layer 3 finding, show the problem and two to four named options with task counts and costs, ending `需要你選一個方向`.
4. End with the exact next action: `開始實作` after `通過`, `提案` for revision, or an answer to the option question.

Offer to expand on findings. A question about the report or an option answer continues self-review; answer it and remain stopped. Never call `approve` or implement.
