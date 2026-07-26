# Agent adapter authoring guide

Status: historical v1.0 implementation evidence; not a current public adapter SDK

This guide records how the v1.0 protocol experiment integrated an Agent without
importing the reference Python implementation. To reproduce that historical
work, read the former
[`Agent Adapter Contract`](./protocol/agent-adapter-contract.md), the public
[`protocol draft`](./protocol-draft.md), and the
[`conformance kit`](./conformance.md). New third-party adapter support is not a
current product commitment.

## 1. Declare the boundary

Record an adapter descriptor in your own package:

```json
{
  "adapter_contract_version": 1,
  "implementation_kind": "agent-host",
  "supported_hosts": ["your-exact-host-and-version"],
  "required_handshake_version": 1,
  "required_capabilities": [
    "approval-manifest-v1",
    "managed-transitions-v1",
    "terminal-transitions-v1"
  ],
  "scenario_claims": []
}
```

Use `implementation_kind: "hermetic-test"` for a scripted adapter. Do not add a
host to `supported_hosts` until it has passed the Agent-eval release gate.

## 2. Discover once per SDD session

Invoke the bootstrap by absolute path inside the installed package:

```text
python3 <skill-package>/scripts/discover-runtime.py
```

Validate `ok`, `runtime.source`, the distribution identity, Skill hash,
handshake version, schema interval, and capabilities. Store only the returned
resolved runtime path for the current session. A failure is a handoff; it is
not permission to try `sdd`, another checkout, or a global executable.

## 3. Model the conversation as phases

Keep a small adapter-owned session record containing only orchestration state:

```text
project root chosen?
proposal short name chosen?
requested phase
discovered runtime path
pending human question, if any
```

Do not copy lifecycle state, task completion, approval state, snapshots, or
machine metadata into adapter authority. Refresh those values from `status`.

Recommended dispatch:

```text
proposal request     -> author draft -> validate -> status -> handoff
開始實作 + draft     -> status -> approve -> status -> task loop
實作 + approved      -> status -> one task -> verify -> complete-task
requirement change  -> status -> begin-revision -> edit -> validate -> handoff
archive request      -> status -> archive -> doctor if recovery is reported
abandon request      -> abandon-preflight -> exact-confirmation handoff
```

## 4. Consume JSON defensively

Run one command, capture stdout and stderr separately, then:

1. require process completion;
2. parse all stdout as one JSON object;
3. validate `output_version`;
4. validate the envelope fields;
5. compare process exit class with `ok`;
6. branch on stable `code` and `action`; and
7. retain the raw result privately only as long as needed for diagnostics.

Never scrape a message for a short name, snapshot, task number, or remediation.
Do not publish raw results: they may contain local paths or operational
evidence.

## 5. Preserve the approval boundary

For a draft, only the adapter's explicit start trigger may call `approve`.
Before implementation, report the canonical scope, task count, and acceptance
conditions so the approval is informed.

During implementation, compare every new user request with the selected
canonical task and acceptance conditions:

- clarification within approved scope may continue;
- a changed outcome, new constraint, removed condition, or new task is a
  requirement change;
- on requirement change, stop work and begin revision before editing the plan;
- after revision, always stop for a new explicit `開始實作`.

This rule also applies during acceptance. “It works, but make it support X”
cannot be converted into a completed task or an undocumented follow-up.

## 6. Implement one task

For each task:

1. call fresh `status`;
2. select the first intended unchecked canonical task;
3. report that exact task;
4. modify only implementation files in its scope;
5. run the smallest relevant validation, then regression validation;
6. compare the result with the exact task and acceptance conditions;
7. call `complete-task` with the fresh snapshot, ordinal, and task digest; and
8. call `status` again to prove only the intended task changed.

Stop immediately when a user turn supersedes the task or the runtime returns a
binding action.

## 7. Hand off clearly

Use a stable presentation shape:

```text
Current state: draft
Authoritative path: <project>/sdd/add-feature
Blocked reason: approval is not explicit
Next permitted action: approve the canonical proposal
Required user action: say 開始實作 add-feature, or revise the proposal
```

Omit values the runtime cannot prove. Use “unknown” where the protocol defines
it; never fill a gap from a likely directory, previous turn, model guess, or
writer string.

## 8. Test the adapter

Run the public runtime envelope kit first:

```text
scripts/run-conformance-kit --runtime /absolute/path/to/runtime --json
```

Then execute every applicable entry in
`conformance/adapter-scenarios-v1.json`. Record:

- adapter descriptor and exact version;
- scenario ID;
- deterministic initial state;
- user turns;
- runtime command trace;
- adapter decision trace;
- required and prohibited actions;
- final handoff; and
- pass/fail reason.

Finally, run the real-host Agent evaluation before making a support claim.
Hermetic success proves contract logic only.

The repository's test-only reference policy can be exercised with:

```text
scripts/run-adapter-conformance --json
```

It uses `implementation_kind: "hermetic-test"` and has an empty
`supported_hosts` list. Its result demonstrates the action/handoff contract,
not Claude Code, Codex, or any other Agent integration.
