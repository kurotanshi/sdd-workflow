# Troubleshooting sdd-workflow

Always diagnose the exact Skill package loaded by the Agent. Do not run an
unrelated `sdd` from `PATH`, copy scripts between Skill installations, or
delete proposal metadata to make an error disappear.

## Skill is missing

1. Confirm the complete package exists at
   `~/.agents/skills/sdd-workflow/` for Codex or
   `~/.claude/skills/sdd-workflow/` for Claude Code.
2. Confirm the directory includes `SKILL.md`, `scripts/`, and `references/`.
3. Restart the Agent or open a fresh session.
4. Follow [`install-methods.md`](./install-methods.md) if multiple or partial
   copies exist.

## Verify the loaded package

From that installed package:

```text
python3 scripts/discover-runtime.py
python3 scripts/sdd.py --json --version
```

Discovery must select the same package and report `ok: true`. If it does not,
replace the complete installation rather than individual files.

## Proposal command stops

Read the stable error `code` and `action` reported by the Skill. Preserve the
proposal and follow that action. Do not manually edit lifecycle status,
checkboxes, `.sdd` metadata, archive directories, or `INDEX.md`.

Common outcomes:

| Observation | Safe response |
| --- | --- |
| proposal or tasks file is missing/malformed | return to `提案` or repair the author-authored draft; do not implement |
| proposal is still a draft | use `開始實作` only after reviewing it |
| snapshot is stale | rerun status, review what changed, then renew the intended action |
| package/runtime mismatch | reinstall the complete Skill package |
| archive index is stale | preserve archive directories and use the bundled validation/rebuild path |
| evidence is ambiguous | stop mutation and retain the diagnostic for a maintainer |

## Known v1.0.0 revision blocker

When partially completed work is revised by appending new pending tasks,
reapproval may stop with:

```text
OUT_OF_BAND_DRIFT
action: inspect_managed_state_drift
```

Do not bypass approval, delete metadata, or edit the task checkboxes. Preserve
the proposal and diagnostic. Continue the product change only after a
maintainer-provided fix or a separately approved replacement proposal gives a
safe path.

## Cancel, abandon, or roll back

- `放棄` or `取消提案` starts a read-only proposal preflight. It does not revert
  implementation or Git state.
- Exact `確認放棄 <short-name>` is required for proposal abandonment.
- A standalone `取消` asks whether you mean proposal abandonment or code/Git
  rollback.
- Source-control rollback is separate from SDD. Confirm its exact files or
  commits before changing anything, and never alter proposal state as a side
  effect.

## Ask for help

Report the Agent host, installed Skill path, proposal short name, stable error
code/action, and whether any mutation reported success. Share the smallest
de-identified evidence needed to reproduce the problem.
