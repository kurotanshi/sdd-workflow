# Self-review reference

Adversarial review of an authored proposal, run only on explicit `自審提案`.
Read this file fully before reviewing. This review never approves, never
implements, and never changes lifecycle status.

## Scope by canonical status

- `draft`: pending scope is not approved yet, so the draft may be corrected in
  place - prose gaps such as an omission in 影響範圍, an unstated exception case,
  a weak acceptance condition or a wrong description of current behavior, and
  the unchecked part of the task list when the review finds it genuinely
  defective: adding, removing, splitting, reordering, or rewording unchecked
  tasks. A `draft` reached through `begin-revision` can already carry checked
  tasks; their text and order are implementation history and stay exactly in
  place, exactly as `SKILL.md` 修訂 requires. Stay within the limit of ten
  unchecked tasks, then rerun `validate` and `status`. Every task-level edit is
  itemised in the report; silent restructuring is the thing being prevented, not
  the editing itself. Choosing between conflicting proposals is still the user's
  call - report it, never act on it.
- `approved`: prose is frozen. Report only, and state that applying any change
  requires `提案` to enter managed revision.
- Any other status: the proposal cannot be reviewed. Report the canonical status
  and stop, with no verdict line - none of the verdict tokens applies.

## Evidence rules

- Every finding names a concrete location: `path:line`, a command output, or a
  canonical task ordinal. A finding that cannot name one is dropped, not softened.
- Finding nothing is a correct and expected outcome. Never manufacture findings
  to justify the review. `無發現` is per-layer wording only, as in
  `設計取向：無發現`; the one-line verdict always uses a verdict token defined
  under Reporting, never `無發現`.
- Edit a draft only for a concrete, evidence-backed defect. Never add a generic
  non-goal, risk disclaimer, or statement that null, error, concurrency, or an
  unaffected area does not change merely to demonstrate coverage. If there is
  no defect, report `通過` without writing the proposal.
- Never claim a caller, behavior, or conflict that was not actually inspected.

## Layer 0 - foundation (always)

Verify the proposal's description of current behavior was actually checked
against the code, not recalled. Open every file, function, and setting the
proposal names.

A wrong premise invalidates every later layer. When the described current
behavior does not match reality, stop here: skip layers 1-3 and the conditional
checks, report the verdict `需修正` with the mismatch, and say plainly that the
later layers were not run because the premise is wrong. This early stop is the
one exception to the `always` layers, and it is never reported as `通過`.

## Layer 1 - correctness (always)

1. Related code and regression: grep every caller of each function, field, or
   setting being changed; decide for each whether it must change too. Missing
   ones belong in 影響範圍.
2. Rule authority: inspect whether the proposed change decides one rule in a
   second place, makes a client reimplement a rule already enforced by a server,
   or persists state that can be derived from an existing authority. Two
   locations are enough for this authority-split check; it is separate from the
   Layer 3 threshold for general code duplication. A finding requires concrete
   repository locations and the resulting behavioral or state divergence. When
   the evidence proves a split but cannot establish which location should remain
   authoritative, report the unresolved finding and stop rather than choosing.
   Similar code alone is not a finding when it neither decides the same rule nor
   persists derived state.
3. Existing data and state: when a field, format, stored value, or setting shape
   changes, state what happens to data that already exists. Grep finds code, not
   data, so this is checked separately.
4. Exception paths: for each task, state the empty, error, and concurrent cases.
   A low-frequency case may be excluded, but the exclusion is written down.
5. Falsifiable acceptance: every task maps to acceptance that can be judged true
   or false. "應該正常運作" is not acceptance.
6. Existing tests: identify tests whose assertions the new behavior invalidates.

## Layer 2 - SDD process (always)

1. Independently verifiable tasks: after each task the system is usable, not
   half-migrated.
2. Task granularity: a task that is really several changes cannot be verified
   once; split it.
3. Cross-proposal conflict: run `list --state active` and compare scope with
   other drafts and in-progress proposals. Overlapping or opposite logic means
   one of them should be abandoned or merged, and that is the user's call.
4. Scope purity: the proposal contains nothing the user did not ask for. This
   bites on work that changes how modules relate - new files, moved
   responsibility, a new abstraction layer, an altered call graph - and on
   unrelated feature work or logging. Local hygiene inside code the change
   already touches is not a scope violation: renaming a local, deleting dead
   code, extracting a short helper within one function, formatting. Report the
   former, leave the latter alone.

## Layer 3 - design direction (gated)

Entry gate: run this layer ONLY when the change modifies existing logic in
existing files. Pure new files, pure configuration additions, and pure copy
changes skip it entirely.

A recorded decision (a line beginning `設計取向：` in the proposal prose) closes
THAT question only, not this layer. Compare each new finding against every
recorded line: report it when it concerns different code or a different
tradeoff, and stay silent only when it is the same question already settled.
Skipping a genuinely new architectural problem costs more than asking twice.

Threshold: report only what will break again. A finding must satisfy one of:

- the approach forces the same detour again for the next request of this kind;
- the approach makes existing behavior untestable or unrecoverable.

Never report "不夠乾淨", "不符合 SOLID", or a named pattern as a finding on its
own. Those hold for almost any code and carry no information.

Both directions share ONE slot, and at most one finding is reported:

- compromise: bending around a framework limit where refactoring first is the
  cheaper total path;
- over-engineering: abstraction, indirection, or configuration the request does
  not need;
- duplication: extraction is proposed only at three or more existing
  occurrences, never two.

The output is options with costs, never a decision. Report two to four options,
never more; each states its task count and what it touches. Options must differ
in outcome, not in style - collapse variations of the same approach into one. If
more than four plausible approaches exist, report the widest-spread three and say
outright that narrower variants were dropped.

Once the user picks, record the decision as a single line beginning `設計取向：`
inside the existing `## 要改什麼` section. Never add a `## 設計取向` section or any
other new level-two heading: Schema v2 permits exactly the sections listed in
[`proposal-authoring.md`](./proposal-authoring.md), and an extra one fails
`validate`. Write the line directly for a `draft`; for an `approved` proposal it
belongs in the next `提案` revision. Rerun `validate` after writing it.

Write that line as a scope boundary in positive terms, never as a record of the
deliberation. State the approach this proposal takes, where the alternative goes
instead, and the reason - not what was considered and rejected:

```text
設計取向：於現有框架內繞道實作，重構另案處理（原因：時程）
```

Not `原本考慮先重構…評估後決定不重構…`. The proposal states the final direction
only; the deliberation lives in this conversation and in Git, never in the prose.

The line exists because refactoring and extraction are agent defaults that fire
without being asked. A purely positive spec cannot suppress a default it never
mentions, and a later reader needs the reason to keep an intentionally plain
approach from being "fixed". That is the whole job of the line - it is a
constraint, not history.

The same rule governs every correction this review makes: edit the prose to its
final state. Never leave a struck-through claim, a "改為", or any trace that the
draft once said something else.

### How far the line reaches

It constrains architectural direction, not tidiness. Two tests decide whether
something falls under it:

1. Does the work change how modules relate to each other - new files, moved
   responsibility, a new abstraction layer, an altered call graph? If yes it is
   constrained. Local hygiene inside code already being touched is not.
2. Can the acceptance conditions of the task at hand verify the work? Cleanup
   that no acceptance condition covers is an unverified change riding along, and
   that - not untidiness - is the actual risk. Small and uncovered is fine when
   stated; uncovered and reaching into another module is what gets reported.

The line binds that one proposal only. It never becomes a project-wide rule, is
never carried into another proposal, and never belongs in CLAUDE.md. The user
may change direction at any time through ordinary `提案` revision.

## Conditional checks (only on a match)

- Security: the change touches input, permissions, secrets, or external data.
- Reversibility: the change deletes data, alters a schema, or changes production
  configuration. State whether it can be undone.
- Performance: the change adds queries or loops over data that grows.
- New dependency: the change adds a package or alters build/CI.

## Reporting

Write the report in Traditional Chinese, in chat, and make it self-contained.
Never answer with a pointer such as "細節在文件裡" or "請看提案" - the chat report
carries the finding itself, enough for the user to discuss it without opening
anything.

Report in this order:

1. Verdict, one line, decided by what is still unresolved after the in-place
   corrections this review already made: `通過` (nothing unresolved anywhere),
   `需修正` (an unresolved finding from layers 0-2 or from the conditional
   checks), or `待你決定` (only a layer 3 option question is left, everything
   else resolved or clean). A finding corrected in place is resolved and never
   forces `需修正` on its own; it is still itemised under point 2, so the user
   sees what changed. An unresolved conditional finding is never downgraded to a
   footnote under `通過`: those risks are low-frequency and high-loss, which is
   the entire reason the checks exist. The Layer 0 early stop is the one
   exception to resolution: a wrong premise is always `需修正`, never corrected
   into `通過` here.
2. Each finding: location, what is wrong, and what it causes. For a `draft`,
   state which ones were already corrected and which still need a decision. List
   every task-level edit one by one - added, removed, split, reordered, reworded
   - with the task count before and after, so the user re-reads the list before
   `開始實作` knowing exactly what moved. Say so plainly when the task list was
   not touched.
3. A layer 3 finding, in this shape:

```text
設計取向發現
位置：<path:line>
問題：<what breaks again, concretely>
選項 A｜<name>：<task count>，<cost>
選項 B｜<name>：<task count>，<cost>
（選項 C、D 依實際方向數列出，最多四個）
需要你選一個方向
```

The two rows above are the minimum, not the shape. List as many options as the
approaches genuinely differ, within the two-to-four bound.

4. Closing line: the exact next action available to the user - `開始實作` when
   the verdict is `通過`, `提案` to revise, or answering the option question.

Offer to expand on any finding. Asking about a finding, and answering the
design-direction option question, are both normal continuations of this phase,
not new ones. Answer a question directly and stay stopped. Never treat either as
a fresh `提案`.

When the user picks an option, honour the status rule above. For a `draft`, write
the `設計取向：` line, rerun `validate` and `status`, report what was written, and
only then stop. For an `approved` proposal the prose stays frozen: report the
chosen direction and the exact line to be written, and state that it lands in the
next `提案` revision. Never edit approved prose here.
