# Self-review static policy model (PR #15 / issue #13)

Recorded: `2026-09-18T07:31:47.340022+00:00`
Score: **8/8** (PASS)

## Claim level (important)

This is a **static contract + executable policy-model test**, not live-host behavioral evidence.
`policy.py` checks required/forbidden phrases in `self-review.md`, then runs an explicit decision table.
Passing 8/8 shows the model matches the written rules and rejects reverse-rule mutations.

It does **not** prove that a coding host reading the thinned skill will obey Layer 3 / authority-split stops.
That checklist item remains open pending existing host-eval scenarios.

## Rerun

```bash
python3 evals/self_review_behavior/run_self_review_behavior.py
```

## Cases

| id | expect | got | pass |
| --- | --- | --- | --- |
| `layer3-run-existing-logic` | run_layer3_ask_user | run_layer3_ask_user | True |
| `layer3-skip-new-files` | skip_layer3 | skip_layer3 | True |
| `layer3-skip-config` | skip_layer3 | skip_layer3 | True |
| `layer3-skip-copy` | skip_layer3 | skip_layer3 | True |
| `authority-unclear-stop` | stop_authority_unclear | stop_authority_unclear | True |
| `authority-clear-report-not-auto-choose` | report_authority_split | report_authority_split | True |
| `approved-frozen` | frozen_report_only | frozen_report_only | True |
| `never-approve-or-implement` | stop_authority_unclear | stop_authority_unclear | True |

