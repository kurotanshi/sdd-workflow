# Release recovery drills

Status: v0.10 release validation contract

`recovery/drill-manifest-v1.json` groups existing failure-injection and
recovery tests into stable release drills. Run all groups with:

```text
python3 scripts/run-recovery-drills
```

Select one or more groups with repeated `--drill ID`. The runner accepts only
versioned manifest entries and safe `tests.test_*` unittest selectors. It
executes every group in a separate Python process with bytecode generation
disabled, then emits one JSON aggregate containing group IDs, selector/test
counts, and pass/fail results.

The v1 groups cover:

- transaction retry and terminal commit classification;
- atomic writer interruption behavior;
- archive authority and evidence-bounded doctor findings;
- committed archive authority across post-move INDEX failure and rebuild;
- concurrent archive/INDEX convergence; and
- compatibility and future-version fail-closed behavior.

The manifest reuses the canonical regression modules rather than copying
their logic into a second drill implementation. A drill failure is a release
failure. Passing drills prove only their observable scenarios; they do not
prove a unique failure cause, power-loss durability, distributed locking, or
the absence of untested states.
