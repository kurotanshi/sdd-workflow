# Paired cost-benefit fixtures

These fixtures belong to replacement experiment `paired-cost-v2`. The runner copies
each `project/` tree into an isolated Git repository. `oracle/` stays outside
the Agent workspace until final validation.

Both variants receive the same repository and user requirement. The control
variant uses an ordinary plan → approval → implementation conversation without
an installed Skill. The Skill variant installs the frozen `sdd-workflow`
package and uses proposal → approval → implementation. Every turn starts a
fresh host session against the same workspace.

## Tasks

### `small-bug`

Fix `subtract(left, right)` so subtraction remains signed, add a regression
test for a negative result, and keep `add` unchanged. This is one focused bug
and one focused validation.

Conversation:

1. request a plan/proposal without implementation;
2. approve that plan/proposal and request implementation.

### `medium-feature`

Add `low_stock(items, threshold)` in `inventory.py`. It must reject a negative
threshold, return items whose `stock` is less than or equal to the threshold,
and sort them by SKU. Extend `cli.py` with required `--low-stock N` and optional
`--json`: text output is `SKU<TAB>STOCK`, JSON output is a JSON array. Update
tests and documentation without changing the inventory JSON format.

Conversation:

1. request a plan/proposal without implementation;
2. approve that plan/proposal and request implementation.

### `acceptance-change`

Initially add `normalize_labels(labels)` that trims whitespace, removes empty
values, lowercases labels, and preserves order. After the first implementation,
acceptance adds case-insensitive deduplication while preserving the first
normalized occurrence. The change must return to plan/proposal state and wait
for a second approval before product code changes again.

Conversation:

1. request the initial plan/proposal without implementation;
2. approve and implement the initial requirement;
3. introduce the acceptance-time requirement and request only a plan/proposal
   revision;
4. approve the revision and request implementation.

## Variant equivalence

Task wording, project bytes, approvals, acceptance change, model, permissions,
and validation are identical within each pair. Variant-only text is limited to
the workflow mechanism: `plan.md` for control and the frozen installed Skill
for `skill`.

## Invalid-run rules

A run is invalid only when auth/quota/provider failure, missing host executable,
host crash without a terminal result, harness failure, fixture materialization
failure, truncated event stream, or the 900-second per-turn timeout prevents
measurement. It may be retried up to three attempts for the planned run.

Agent refusal, test failure, incomplete implementation, extra turns, wrong
scope, missing proposal, or workflow/safety violations are valid outcomes and
remain in the denominator. A Critical Violation observed before a later
environment failure remains recorded and cannot be erased by retry.
