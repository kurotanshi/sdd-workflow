# First-workflow 15-minute usability check

Status: v0.9 bounded acceptance protocol

## Claim

A first-time, Agent-assisted user can complete one small SDD workflow within
15 minutes without reading the transaction protocol. This check deliberately
separates install success from first-workflow usability.

The v0.9 evidence is a single automated first-time-path proxy. It proves that
the documented happy path is complete, hermetic, and comfortably inside the
budget; it does not estimate a human population success rate or comprehension
time. A later moderated human sample can use the same boundaries and valid-run
rules without changing the claim.

## Persona

Persona ID: `agent-assisted-developer-first-sdd-workflow-v1`

- A developer who can open a repository, review a diff, and run a test.
- Comfortable asking a coding Agent for a small change.
- Has never used `sdd-workflow` and has not read its protocol, transaction,
  schema, or recovery design documents.
- Uses only the README first-workflow section and the Agent's handoff.

## Timer and task boundaries

Start point:
`package-installed-clean-repository-readme-quickstart-open`.

At time zero, the complete Skill package is installed and available, a clean
repository is open, and the README quickstart is visible. Installation,
account authorization, model queueing, and repository cloning are excluded;
they have separate compatibility and install gates.

End point:
`one-task-change-tested-accepted-and-archived`.

The timer stops only when:

1. one draft proposal exists and validates;
2. explicit approval precedes product implementation;
3. the product test passes and the one canonical task is complete;
4. acceptance is checked;
5. the proposal is archived, the archive INDEX validates, and doctor is
   healthy.

The threshold is 900 elapsed seconds. Pauses caused by the test facilitator do
not invalidate a run but remain in elapsed time. A run is invalid only for
external host outage or corrupted test setup; user confusion, wrong phase,
failed tests, unsafe mutation, timeout, or incomplete archive are task
failures and remain in the denominator.

## Sample size and result

Planned v0.9 sample: 1 complete automated proxy run. Observed: 1 valid run,
1 task success, 1 within 15 minutes.

The versioned aggregate record is
[`evals/usability/first-workflow-sample-v1.json`](../../evals/usability/first-workflow-sample-v1.json).
Replay it with:

```text
python3 examples/first-workflow/run.py
```

Release interpretation: **PASS with bounded evidence**. The executable path
meets the 15-minute target and requires no transaction-protocol read. Because
the sample has no human participant, the result is not evidence of a 100%
human success rate. Before making a population-level usability claim, collect
moderated first-time human runs and publish their numerator, denominator,
timing distribution, invalid-run reasons, and uncovered environments.
