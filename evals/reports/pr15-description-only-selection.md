# Description-only selection smoke (PR #15 / issue #13)

Recorded: `2026-09-18T07:31:47.339789+00:00`
Score: **8/8** (PASS)

## Claim level (important)

This is a **truncated-view polarity/keyword smoke test**, not a live multi-skill host selection bakeoff.
It proves:
- the router sees only `description[:160]`
- positive SDD triggers in that view still route in
- outside-polarity cues reject generic cancel / rollback / `放棄剛才的變更`
- reversing outside→use-for breaks negative cases
- garbage/`x` views cannot invoke

It does **not** prove Codex/Claude/Cursor skill routing behavior in a real host.

## Rerun

```bash
python3 evals/description_only_selection/run_description_only_selection.py
```

## Truncated view (160)

```
Explicit SDD only (sdd-workflow / 提案|自審提案|開始實作|實作|歸檔|放棄|取消提案|確認放棄). Outside: generic cancel & git/code rollback. Proposal-first: checklist, approval, one task, 
```

## Cases

| id | expect | predicted | pass | utterance |
| --- | --- | --- | --- | --- |
| `pos-explicit-skill` | True | True | True | 用 sdd-workflow 開提案 |
| `pos-proposal` | True | True | True | 提案：限制登入重試 |
| `pos-self-review` | True | True | True | 自審提案 login-retry |
| `pos-start-impl` | True | True | True | 開始實作 login-retry |
| `pos-cancel-proposal` | True | True | True | 取消提案 login-retry |
| `neg-generic-cancel` | False | False | True | 取消剛才的變更 |
| `neg-abandon-just-now` | False | False | True | 放棄剛才的變更 |
| `neg-git-rollback` | False | False | True | 把程式碼 rollback 到昨天 |

