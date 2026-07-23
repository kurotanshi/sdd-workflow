# SDD Workflow Core Protocol v1.0

Protocol identifier: `sdd-protocol-1.0`

Status: stable normative contract

Normative language: RFC 2119 / RFC 8174

## 1. Purpose and conformance

This document specifies the stable v1 observable protocol shared by SDD
artifact producers, runtimes, Agent adapters, and conformance tools. It is
written so an independent implementation can be evaluated without reading the
reference Python implementation.

The v1 freeze covers authority, lifecycle, approval, attestation, transaction
commit points, recovery classification, compatibility negotiation, and trust
boundaries. Schema v3, locking or leases, Web UI, external-platform
integration, and multi-Agent orchestration are explicitly outside this
contract.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**, and
**OPTIONAL** in this document are to be interpreted as described in RFC 2119
and RFC 8174 when, and only when, they appear in all capitals.

An implementation claiming conformance:

1. MUST name the protocol identifier above;
2. MUST state which artifact schemas, CLI output versions, metadata versions,
   and capabilities it implements;
3. MUST pass every conformance-kit case applicable to that claim; and
4. MUST NOT use partial conformance to imply compatibility with an untested
   runtime, Agent host, or installation channel.

The reference runtime is one conforming implementation. Its source code is not
part of this protocol.

## 2. Roles and trust boundaries

| Role | Responsibility | Not trusted to decide |
| --- | --- | --- |
| Human | Supplies intent, resolves ambiguity, explicitly approves scope, and accepts handoff | Machine state integrity |
| Agent adapter | Maps human turns to protocol phases, invokes the runtime, consumes structured results, and explains required action | Parsing, snapshots, state transitions, or authorship attribution |
| Runtime | Discovers and parses artifacts, projects canonical state, validates compare-and-swap inputs, and performs managed transitions | Whether implementation work semantically satisfies a task |
| Artifact store | Persists project-local proposal and machine artifacts | Atomicity across multiple files |
| Conformance kit | Tests declared observable behavior | Formal support for a real Agent host |

All local files are potentially mutable by actors outside this protocol.
Hashes, metadata, timestamps, and writer identifiers are evidence, not identity
or authorship. An implementation MUST NOT claim which person or tool made an
edit unless that identity is established by a separate authenticated system.

## 3. Artifact model

An active proposal bundle has this logical layout:

```text
<project-root>/sdd/<short-name>/
├── proposal.md
├── tasks.md
└── .sdd/
    ├── metadata.json
    └── approval-manifest.json
```

The `.sdd` directory is optional for an unmanaged draft and REQUIRED once a
proposal enters a managed approval lifecycle. A conforming runtime:

- MUST contain discovery and every resolved proposal path within the selected
  project root;
- MUST reject symlinks or non-regular files at authority-bearing paths;
- MUST read text artifacts as strict UTF-8;
- MUST preserve raw bytes when a read or validation fails; and
- MUST treat unknown future schema or machine-envelope versions as
  unsupported rather than guessing their meaning.

`<short-name>` is a stable proposal identifier. Discovery order, diagnostics,
canonical task order, and conformance results MUST be deterministic for the
same input bytes and declared version support.

## 4. Canonical projection and task identity

A parser adapter converts a supported proposal bundle into one canonical
proposal containing, at minimum:

- short name;
- lifecycle status;
- change type, when the selected schema defines it;
- ordered scope items;
- ordered acceptance conditions;
- ordered task text and completion markers; and
- namespaced extensions with an explicit approval-relevance policy.

Canonicalization MUST NOT normalize away semantically observable text or
invent missing fields. Each task identity is the lowercase SHA-256 of the
canonical task text encoded as UTF-8, without Unicode normalization. The task
ordinal and completion marker are excluded from that digest.

The raw proposal and task bytes form snapshot version 1. A snapshot digest is
an optimistic concurrency token; it is not lifecycle authority and MUST NOT
be used as proof of user approval.

### SDD-PROJ-001 — deterministic canonical projection

The same bundle bytes and supported schema generation MUST produce the same
canonical projection, ordered task identities, snapshot fields, and
diagnostic ordering.

### SDD-DISC-001 — deterministic and contained discovery

Discovery MUST be deterministic, remain within the selected project root, and
fail when the target is missing, ambiguous, unsafe, or structurally
incomplete. A list operation MAY report several candidates but MUST NOT select
one on behalf of the caller.

## 5. Authority

Authority is divided by field; no timestamp, writer version, or file order
overrides it.

| Authority | Authoritative meaning |
| --- | --- |
| `proposal.md` lifecycle field | Current `draft`, `approved`, `completed`, or `abandoned` state |
| `tasks.md` top-level checkbox markers | Current task completion |
| Approval Manifest | Exact approval-relevant semantic baseline |
| Active metadata | Approval state, revision authorization, operation evidence, and managed-state attestation |
| Snapshot | Raw bytes observed by a particular caller |
| Archived terminal bundle | Completed or abandoned proposal history |
| Archive `INDEX.md` | Derived lookup view; never primary terminal history |

When two authorities cannot form a supported state, the runtime MUST fail
closed with a stable diagnostic and MUST NOT choose a winner heuristically.
Read-only commands MUST NOT refresh approval, attest current bytes, or repair
history as a side effect.

## 6. Approval and attestation

Approval uses two separate integrity projections:

1. The Approval Manifest records approval-relevant semantics: identity, change
   type, ordered scope, acceptance conditions, task text, and explicitly
   relevant extensions. Completion markers and implementation results are
   excluded.
2. Managed-state attestation records lifecycle status, ordered completion
   booleans, and machine-managed metadata. Ordinary prose, task text, whole
   file bytes, timestamps, and writer provenance are excluded.

Both projections are structurally compared. A serialized SHA-256 MAY identify
an envelope but MUST NOT replace parsed comparison.

### SDD-APPROVAL-001 — approval and attestation fail closed

A missing, stale, unsupported, or mismatched manifest, snapshot, task
identity, revision authorization, or managed-state attestation MUST stop a
mutation. An approved legacy proposal without a managed baseline MUST require
explicit reconfirmation; it MUST NOT be silently adopted.

Approval-relevant edits require the following sequence:

1. observe an attested approved state;
2. begin a managed revision using the exact observed snapshot;
3. commit the state to `draft` and invalidate the prior approval;
4. edit the authorized semantics;
5. validate and present the revised canonical scope; and
6. obtain new explicit approval before implementation continues.

Changing only completion markers through `complete-task` does not invalidate
the Approval Manifest because it does not change the approved plan.

## 7. Lifecycle and managed transitions

The lifecycle states and permitted managed transitions are:

```text
draft --approve--> approved
approved --begin-revision--> draft
approved --complete-task--> approved
approved --archive (all tasks complete)--> completed archive
draft|approved --abandon (confirmed)--> abandoned archive
```

There is no protocol transition from a terminal archive back to active state.
Restoration or source-control rollback is a separate user-authorized operation
and MUST NOT silently change SDD proposal state.

### SDD-TRANS-001 — managed transition boundary

Approval, revision, task completion, archive, and abandonment MUST use their
defined source states, exact compare-and-swap inputs, and managed command.
Adapters MUST NOT edit lifecycle fields, checkbox markers, machine metadata,
archive locations, or the archive index directly.

Every mutating command MUST validate, in the precedence defined for that
transition:

- supported artifact and machine-envelope versions;
- expected raw snapshot;
- approval baseline and managed attestation;
- allowed lifecycle source state;
- exact task identity or terminal eligibility; and
- transition-specific confirmation or summary inputs.

## 8. Transaction and recovery protocol

The protocol assumes atomic replacement of one regular file but does not claim
an ACID transaction across files. Each multi-file transition therefore has one
authoritative commit point and durable operation evidence sufficient to
classify a retry.

| Transition | Authoritative commit point |
| --- | --- |
| Approve | Lifecycle field becomes `approved` |
| Begin revision | Lifecycle field becomes `draft` |
| Complete task | Exact top-level checkbox becomes complete |
| Archive/abandon | Active directory is moved to its terminal archive path |
| Rebuild index | Derived `INDEX.md` replacement |

### SDD-TXN-001 — atomic commit points

Managed writes MUST stage required evidence before their authoritative write,
MUST use an atomic individual-file replacement where specified, and MUST NOT
report success until the committed state has been re-read and validated.

### SDD-RETRY-001 — evidence-backed safe retry

A retry MUST compare the current authoritative state with the original
operation identifier and exact inputs. It MAY return `ALREADY_APPLIED` only
when those facts prove the same operation committed. Otherwise it MUST reject
stale or conflicting state without rewriting it.

### SDD-CONC-001 — concurrent updates converge or fail stale

Concurrent writers MUST either commit independent authoritative state safely
or reject stale state. A writer MUST NOT overwrite an intervening operation,
infer that a changed snapshot is harmless, or regenerate attestation from
unexplained current bytes.

Recovery tools MUST distinguish:

- a pre-commit staged operation that can be safely finalized;
- a post-commit operation whose derived metadata can be safely completed;
- a proven already-applied operation;
- observable out-of-band drift; and
- ambiguous evidence requiring human inspection.

Ambiguity always selects the last two outcomes, never automatic repair.

## 9. Terminal authority and archive index

A terminal transition records the summary and machine evidence, changes the
lifecycle state, and moves the complete proposal directory to a deterministic
archive path. The committed terminal bundle remains authoritative even if
derived index maintenance fails.

### SDD-ARCHIVE-001 — archive bundle remains authoritative

An implementation MUST reconstruct `INDEX.md` only from unambiguous canonical
archive records. It MUST NOT invent a summary, status, completion count, or
history from prose. If index replacement fails after the directory move, the
terminal operation remains committed and the result MUST identify index
rebuild as the only pending recovery action.

## 10. Compatibility and version negotiation

The protocol has independent version axes:

| Axis | v1 value or range |
| --- | --- |
| Protocol identifier | `sdd-protocol-1.0` |
| Proposal schema | `1..2` |
| CLI output | `1` |
| Canonical model | `1` |
| Snapshot | `1` |
| Active metadata | `1` |
| Approval model | `1` |
| Managed attestation | `1` |
| Archive model | `1` |
| Terminal metadata | `1` |
| Runtime handshake | `1` |

An implementation MUST choose compatibility using the narrowest relevant
axis. Engine release strings are diagnostic identity and MUST NOT override an
unsupported artifact or envelope version.

### SDD-COMPAT-001 — explicit compatibility generations

Supported legacy, Schema v1, and Schema v2 inputs MUST retain their documented
behavior. An explicit unknown schema or machine-envelope version MUST fail
before its semantic or authority-bearing content is used. Mutation of a
read-only legacy input MUST require migration or recreation unless an
explicitly specified adoption transition applies.

## 11. Runtime discovery and CLI contract

An installable distribution provides a package-local runtime identity and
handshake. An adapter MUST discover the runtime using the distribution's
documented deterministic mechanism. It MUST NOT silently fall back to a
same-named executable on `PATH` or choose between multiple distinct compatible
candidates.

Machine consumers invoke one command noninteractively. JSON mode emits exactly
one UTF-8 JSON document plus a trailing line feed on stdout and no progress
text on stderr:

```json
{
  "output_version": 1,
  "command": "status",
  "ok": true,
  "warnings": [],
  "errors": [],
  "data": {}
}
```

### SDD-CLI-001 — stable public CLI contract

Public commands MUST preserve the versioned envelope, stdout/stderr
separation, exit classes, and stable error `code` and `action` semantics.
Consumers MUST branch on `ok`, `errors[].code`, and `errors[].action`; they
MUST NOT parse human messages to decide a mutation.

### SDD-DIAG-001 — evidence-bounded diagnostics

Validation and doctor diagnostics MUST report only observable facts. Unknown
Agent environment, installation source, package source, actor, or causal
history MUST be represented as unknown or omitted, never inferred. Read-only
diagnostics MUST NOT modify proposal or archive state.

## 12. Agent adapter contract

An Agent adapter is a policy and orchestration layer, not a second runtime.
It MUST:

- recognize the explicit proposal, approval, implementation, revision,
  archive, and abandonment triggers it claims to support;
- preserve the difference between `開始實作` (explicit approval of a draft)
  and a generic request that lacks approval;
- perform package-local discovery once per SDD session and consume the
  handshake before invoking lifecycle commands;
- execute each runtime invocation as one noninteractive call;
- consume the complete JSON result before deciding what to do next;
- stop on binding error actions and request human input where required;
- implement one canonical task at a time and verify it before marking it
  complete;
- treat acceptance-time requirement changes as revision and reapproval, not
  task completion;
- keep source-control rollback outside SDD lifecycle state; and
- explain current state, authoritative path, blocked reason, next action, and
  required human action without inventing evidence.

### SDD-ADAPTER-001 — Agent adapter phase boundary

Adapters MUST preserve explicit phase triggers, approval gates, CLI-only
managed mutation, ambiguity handling, human handoff, and separation of SDD
state from source-control operations. A hermetic adapter used by the
conformance kit MUST be labelled as a test implementation, not a supported
real Agent host.

## 13. Packaging

### SDD-PKG-001 — portable validated package

The installable package MUST contain its declared Skill, runtime, identity,
and supporting runtime modules; MUST exclude generated caches and
repository-only user documentation; and MUST run on every OS and Python
generation in its declared support matrix. An installer is conforming only
when it preserves the complete package boundary.

### SDD-DOC-001 — duplicated contract facts remain consistent

Duplicated public version, command, runtime, installation, and workflow facts
MUST agree with their named canonical source. Documentation checks SHOULD
detect drift before publication.

## 14. Conformance kit

### SDD-CONF-001 — versioned conformance mapping

The public conformance kit MUST contain a versioned rule registry, case
manifest, fixtures or test selectors, expected machine envelopes where
required, and a deterministic runner. Every executable reference-runtime test
MUST map to at least one registered rule, and every registered rule MUST have
executable evidence.

Case results MUST identify their rule IDs and applicability. The runner MUST
distinguish pass, conformance failure, invalid invocation, and inapplicable
cases. Passing the kit demonstrates only the declared protocol surface; it
does not certify security, implementation quality, or an untested Agent host.

## 15. Security and threat model

The protocol is designed to reduce accidental state corruption and confused
deputy behavior in a local workspace. It does not provide process isolation,
cryptographic user identity, authorization outside the selected project, or
protection from an actor able to rewrite all project files.

A conforming implementation:

- MUST validate containment before reading or writing authority-bearing paths;
- MUST fail closed on symlinks, unsupported versions, invalid UTF-8, malformed
  envelopes, ambiguous discovery, stale snapshots, and inconsistent managed
  evidence;
- MUST use bounded input reads for external summary or configuration files;
- MUST NOT execute content from proposal Markdown;
- MUST NOT expose secrets, prompts, transcripts, absolute user paths, or raw
  Agent events in public conformance or evaluation reports;
- SHOULD create new machine artifacts with owner-only permissions where the
  platform supports them; and
- SHOULD document residual risks and manual recovery boundaries.

An adapter MUST treat runtime output as untrusted structured input until the
envelope version and required fields are validated. A runtime MUST treat the
adapter's claimed user intent as an instruction to validate, not as permission
to bypass state or integrity checks.

## 16. Evolution

The v1 line may add optional diagnostics and presentation fields without
changing CLI output version 1. A change to compatibility fields, authority,
canonical approval semantics, transition commit points, or mandatory adapter
behavior requires an explicit protocol/version decision, a Semantic Versioning
classification, migration and rollback guidance, and updated conformance
evidence.

New canonical extensions MUST use a collision-resistant namespace and declare
their approval relevance. Unknown approval-relevant or authority-bearing
extensions MUST block mutation until supported. An implementation MUST NOT
silently downgrade a proposal, envelope, or capability claim.

Detailed schemas and recovery matrices remain in the linked design documents:
[`architecture.md`](../architecture.md),
[`Agent Adapter Contract`](./agent-adapter-contract.md),
[`approval-manifest.md`](../approval-manifest.md),
[`managed-state.md`](../managed-state.md),
[`transaction-protocol.md`](../transaction-protocol.md),
[`archive-model.md`](../archive-model.md),
[`schema-v2.md`](../schema-v2.md),
[`cli-contract.md`](../cli-contract.md), and
[`compatibility.md`](../compatibility.md).
