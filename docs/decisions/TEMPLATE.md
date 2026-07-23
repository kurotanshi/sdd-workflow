# <decision title>

## Date
YYYY-MM-DD

## Versions
- Engine: `<engine version or not applicable>`
- Skill: `<skill version or commit>`
- Environment: `<tool, runtime, OS, and other decision-relevant versions>`

## Question and gate
State the decision being made, the activation or investment gate it controls, and the success and failure criteria that were fixed before evaluation.

## Evaluated scenarios
- `<scenario and expected behavior>`

## Observed evidence
- `<result, reproducible command or safe evidence link>`

Record both supporting and contradictory observations. Distinguish automated checks, fresh-session observations, and human judgement. Do not treat an unrecorded recollection as evidence.

## Rejected alternatives
- `<alternative and why the observed evidence does not justify it>`

## Decision
`GO`, `NO-GO`, `DEFER`, or another explicitly defined outcome, followed by its rationale and the behavior paths covered by the decision.

## Rollback boundary
State what can be reverted or pinned, which artifacts or metadata would require migration, and which condition triggers rollback or a new decision.

## Follow-up
- `<owner or trigger, action, and evidence needed>`

## Sensitive-data review
- [ ] No full user transcript is stored by default.
- [ ] Project names, repository paths, source snippets, credentials, personal data, and customer data are removed or replaced with stable neutral labels.
- [ ] Commands and links contain only information safe to retain in this repository.
- [ ] When raw evidence cannot be safely retained, the record contains a de-identified summary and a minimal synthetic reproduction instead.
