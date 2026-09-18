# Description-only skill selection (PR #15 / issue #13)

Recorded: `2026-09-18T07:12:50.233891+00:00`
Score: **8/8** (PASS)

## Method
Deterministic description-only keyword router using only SKILL.md frontmatter description (and its 160-char truncation). No model call; validates that truncated description still retains explicit invoke vs out-of-scope boundaries required by issue #13.

## Truncation probe (160 chars)

```
Manage software changes through a proposal-first SDD workflow: create or revise a scoped proposal and checklist, wait for explicit approval before implementatio
```

- Retains SDD identity: `True`
- Retains approval gate wording: `False`
- Full description keeps generic-cancel out-of-scope: `True`
- Full description keeps VCS rollback out-of-scope: `True`

## Cases

| id | expect | predicted | pass | utterance |
| --- | --- | --- | --- | --- |
| `pos-explicit-invoke` | True | True | True | 用 sdd-workflow 幫我開一個提案 |
| `pos-zh-start` | True | True | True | 開始實作 login-rate-limit |
| `pos-zh-proposal` | True | True | True | 提案：把重試改成可設定 |
| `pos-self-review` | True | True | True | 自審提案 checkout-flow |
| `neg-generic-cancel` | False | False | True | 取消剛才的變更 |
| `neg-git-rollback` | False | False | True | 把程式碼 rollback 到昨天 |
| `neg-generic-implement` | False | False | True | 幫我改一下這個 bug |
| `neg-unrelated` | False | False | True | 今天天氣如何 |

## Note

This is an offline gate for description routing boundaries, not a live multi-skill host bakeoff. Live host selection remains a follow-up measurement under issue #13 Gate 0.
