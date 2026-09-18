# Self-review behavioral gate (PR #15 / issue #13)

Recorded: `2026-09-18T07:22:56.549966+00:00`
Score: **8/8** (PASS)

## Method
Rerunnable runner: `python3 evals/self_review_behavior/run_self_review_behavior.py`
Executable policy in `evals/self_review_behavior/policy.py` decides Layer 3 run/skip and authority stop/report.
Conformance fails if required phrases are removed or reversed (e.g. auto-choose authority and continue).

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

## Counterexample

Reversing the authority-split rule to auto-choose authority makes `assert_conformance` fail, even if older string-presence anchors remain.
