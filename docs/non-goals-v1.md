# v1 non-goals

Status: stable scope boundary for `sdd-protocol-1.0`

The v1 release stabilizes evidence-backed proposal lifecycle and Agent
handoff. The following capabilities are deliberately not part of v1 and MUST
NOT be inferred from current artifacts, diagnostics, or conformance results.

## Excluded product capabilities

- Schema v3 or a generic user-extensible proposal schema.
- Locking, leases, enforced proposal ownership, or INDEX-level compare-and-swap.
- Web UI, dashboard, server, daemon, or background watcher.
- GitHub, Jira, Linear, Slack, CI-provider, database, or other external-platform
  integration as protocol authority.
- Multi-Agent scheduling, orchestration, consensus, leader election, or merge
  of concurrent proposal state.
- Automatic source-control commit, push, pull request, merge, revert, or branch
  policy.
- Remote state storage, synchronization, telemetry, analytics, or hosted
  control plane.

## Excluded security guarantees

- Authenticated human, Agent, host, or writer identity.
- Access control, process isolation, filesystem sandboxing, encryption, secret
  storage, or tamper resistance against a workspace-wide writer.
- Formal verification, security certification, or proof that generated code
  satisfies acceptance conditions.
- Transactional atomicity across multiple files or distributed systems.

## Excluded compatibility claims

- Windows support beyond the documented best-effort Python path.
- Agent hosts, models, installation roots, or package managers absent from the
  current compatibility matrix and eval report.
- Backward mutation through engines that do not support present artifact and
  machine-envelope versions.
- Forward compatibility by ignoring unknown schemas, fields, capabilities, or
  protocol versions.

## Excluded workflow behavior

- Inferring approval from silence, generic implementation language, passing
  tests, or acceptance of output.
- Selecting among multiple proposals or ambiguous cancellation scopes for the
  human.
- Editing managed lifecycle fields, checkbox markers, metadata, archive moves,
  or INDEX outside the runtime.
- Treating Git rollback as SDD abandonment or restoring a terminal proposal to
  active state.
- Automatically repairing ambiguous evidence or attributing an out-of-band
  edit to a person or tool.

An excluded capability requires its own evidence-backed proposal, version
decision, security analysis, migration/rollback plan, and conformance changes.
It cannot enter v1 through a patch release or documentation implication.
