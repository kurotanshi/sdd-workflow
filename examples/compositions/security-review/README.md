# Security Review composition

This is a minimal upper-level workflow that uses SDD Workflow as its complete
change-control and lifecycle primitive.

The Security Review layer owns only domain framing:

- formulate the bounded security question;
- choose review tasks and acceptance conditions;
- perform the review work; and
- record findings in the Schema v2 research conclusion.

It does not add a security-review status, approval flag, finding database,
sidecar, transition, or archive format. Draft, approval, progress, conclusion,
terminal state, and recovery use the existing SDD protocol artifacts and
commands.

## Example flow

The project template under `project/` asks whether an authentication boundary
is safe to release. An upper-level Agent would:

1. present the generated research proposal;
2. hand explicit approval to `sdd-workflow`;
3. execute each review task through the normal one-task loop;
4. write observed findings under the existing `## 結論` field;
5. archive through the standard terminal transition; and
6. use `doctor` for the final repository health check.

Run the executable proof:

```text
python3 examples/compositions/security-review/run-smoke.py
```

The smoke test copies the template into a temporary directory, executes that
entire flow with the public runtime, and verifies that the terminal bundle
contains only standard SDD artifacts. It does not invoke an Agent and makes no
Agent-host support claim.
