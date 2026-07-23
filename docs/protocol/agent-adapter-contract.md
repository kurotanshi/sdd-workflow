# Agent Adapter Contract v1

Status: normative for `sdd-protocol-draft-0`

An Agent adapter translates human conversation into SDD protocol operations.
It is not a parser, state-transition engine, source-control manager, or
authority for user approval. This contract is independent of any particular
Agent vendor, model, prompt format, or tool-call transport.

## Declared adapter capability

An adapter claiming version 1 conformance MUST declare:

- adapter contract version `1`;
- the SDD phase triggers it recognizes;
- the runtime handshake versions and capabilities it requires;
- whether it supports proposal authoring, implementation, revision, archive,
  and abandonment;
- the conformance scenarios it has executed; and
- the exact Agent hosts, if any, for which support is claimed.

A hermetic or scripted adapter MUST identify itself as a test implementation.
Passing its tests MUST NOT be presented as support for a real Agent host.

## Runtime discovery

At the first SDD operation in a session, the adapter MUST invoke the
package-local discovery bootstrap supplied with the installed Skill. It MUST
consume the returned JSON and continue only when:

- `ok` is `true`;
- `runtime.source` is `package-local`;
- the handshake distribution is `sdd-workflow`;
- the handshake version is supported;
- the schema interval and required capabilities cover the requested operation;
  and
- the Skill identity agrees with the package identity.

The adapter MUST use the resolved runtime path returned by discovery for the
session. It MUST NOT search `PATH`, guess another package directory, choose
between distinct candidates, or silently downgrade after a discovery or
handshake failure.

## Noninteractive invocation

Every runtime command MUST be one noninteractive invocation with an explicit
project root, `--json`, a command, and an explicit short name whenever the
command requires one. The adapter MUST NOT wrap a lifecycle mutation in shell
pipelines, output filters, exit-code rewriting, or automatic retries.

The adapter MUST wait for process completion and consume exactly one JSON
document. It MUST reject:

- an unsupported `output_version`;
- extra non-JSON stdout;
- JSON-mode progress or diagnostics on stderr;
- a missing `ok`, `warnings`, `errors`, or `data` field; and
- a process exit class inconsistent with the envelope.

The adapter branches on `ok`, `errors[].code`, and `errors[].action`. Message
text is presentation only and MUST NOT decide a mutation.

## Phase and approval mapping

| Human intent | Canonical adapter behavior |
| --- | --- |
| `提案` with a scoped change | Author a draft, validate, report canonical scope, then stop |
| `開始實作` for a draft | Treat as explicit approval, run `approve` with the fresh snapshot, verify `approved`, then implement |
| `實作` for an approved proposal | Continue one unchecked canonical task |
| `實作` for a draft | Ask whether the user approves; do not approve or implement |
| Requirement change during implementation or acceptance | Stop, run `begin-revision`, edit only the agreed scope, validate, and stop for `開始實作` |
| `歸檔` with all tasks complete | Archive with the fresh snapshot and a bounded summary |
| Explicit proposal abandonment | Run preflight, present non-revert evidence, require the exact confirmation, then abandon |
| Source-control rollback request | Confirm exact Git scope and keep SDD lifecycle state unchanged |

Approval is valid only for the canonical Approval Manifest. A generic
implementation request, prior approval of different bytes, successful task
work, or user silence MUST NOT be interpreted as approval.

## Ambiguity and proposal selection

The adapter MUST ask the human to choose when:

- several active proposals are candidates;
- a phase-triggered request does not identify which proposal;
- an implementation request targets a draft without explicit approval;
- a cancellation request could mean Git rollback or SDD abandonment;
- a requested semantic edit exceeds the authorized revision; or
- the runtime action is `select_project_root`, `choose_short_name`,
  `create_or_select_proposal`, or another human-choice action.

While waiting, the adapter MUST NOT mutate artifacts, Git state, proposal
status, completion markers, archive paths, or the archive index.

## Mutation boundary

The adapter MAY author new draft prose and MAY edit explicitly authorized
semantic prose while a managed revision is open. It MUST use the runtime as the
only writer for:

- lifecycle status;
- task completion markers;
- approval and attestation metadata;
- terminal metadata;
- archive directory moves; and
- archive index rebuild.

Before each mutation the adapter MUST obtain a fresh successful `status` and
use the exact snapshot, ordinal, and task digest returned for that operation.
It MUST implement and verify one canonical task at a time.

## Error actions and human handoff

The adapter MAY continue automatically only after a successful envelope or a
documented, evidence-backed `ALREADY_APPLIED` result. These actions are binding
handoff or stop boundaries:

| Action | Required behavior |
| --- | --- |
| `refresh_status` | Rerun read-only status, explain stale evidence, and wait for renewed intent before mutation |
| `select_project_root`, `choose_short_name`, `create_or_select_proposal` | Ask the human for the missing choice |
| `begin_revision`, `begin_revision_and_reapprove` | Enter the explicit revision flow; never patch scope opportunistically |
| `establish_approval_manifest` | Require explicit reconfirmation of the canonical plan |
| `inspect_project_path`, `inspect_machine_metadata`, `inspect_managed_state_drift`, `inspect_archive_state` | Stop mutation and present observable evidence |
| `use_supported_engine`, `upgrade_or_recreate_proposal`, `fix_artifact_format` | Stop and describe the compatible remediation |
| `rebuild_index` | Rebuild only when terminal evidence or doctor proves the archive bundle committed and only INDEX is stale |
| `report_internal_error` | Stop and preserve the failure evidence |

An adapter response at a handoff MUST state:

1. current canonical state, if known;
2. authoritative proposal or archive path, if known;
3. blocked reason using observable evidence;
4. next permitted protocol action; and
5. the exact required human action: a user choice or confirmation.

It MUST NOT claim an actor, cause, approval, repair, or successful mutation that
the runtime result does not prove.

## Terminal safety

Archive requires reliable task counts and every task complete. Abandonment is a
two-turn operation: read-only preflight followed by the exact requested
confirmation. Neither operation reverts source files or Git history.

If a terminal directory move commits but INDEX maintenance fails, the adapter
MUST report the terminal bundle as authoritative and MAY run `rebuild-index`
only when the returned action identifies that recovery. It MUST NOT move the
bundle back to active state.

## Conformance

`conformance/adapter-scenarios-v1.json` is the versioned observable inventory.
An adapter claim MUST list the applicable scenario IDs and preserve the
required and prohibited action traces. Test-only scenarios may use a hermetic
runtime and deterministic turns; real-host support additionally requires the
Agent evaluation defined by the release policy.

The authoring procedure and a minimal implementation outline are in
[`adapter-authoring-guide.md`](../adapter-authoring-guide.md).
