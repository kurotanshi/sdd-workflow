# Description-only skill selection (PR #15 / issue #13)

Recorded: `2026-09-18T07:22:56.491684+00:00`
Score: **8/8** (PASS)

## Method
Rerunnable runner: `python3 evals/description_only_selection/run_description_only_selection.py`
Router receives **only** `description[:160]` as `description_view`. It never opens the remainder of SKILL.md.
Counterexample coverage: replacing the first 200 description chars with `x` makes the 8-case runner fail; garbage-only views cannot invoke.

## Truncated view (160 chars)

```
Explicit SDD only (sdd-workflow / 提案|自審提案|開始實作|實作|歸檔|放棄|確認放棄). Not generic cancel or git/code rollback. Proposal-first: scoped checklist, wait for approval, one
```

## Cases

| id | expect | predicted | pass | utterance |
| --- | --- | --- | --- | --- |
| `pos-explicit-skill` | True | True | True | 用 sdd-workflow 開提案 |
| `pos-proposal` | True | True | True | 提案：限制登入重試 |
| `pos-self-review` | True | True | True | 自審提案 login-retry |
| `pos-start-impl` | True | True | True | 開始實作 login-retry |
| `pos-confirm-abandon` | True | True | True | 確認放棄 login-retry |
| `neg-generic-cancel` | False | False | True | 取消剛才的變更 |
| `neg-git-rollback` | False | False | True | 把程式碼 rollback 到昨天 |
| `neg-unrelated` | False | False | True | 今天天氣如何 |

