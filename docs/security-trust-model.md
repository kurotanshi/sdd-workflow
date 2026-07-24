# Security and trust model

Status: stable v1 contract

Protocol: `sdd-protocol-1.0`

SDD Workflow is a cooperative local change-control protocol. It reduces
accidental state corruption, stale writes, approval confusion, and unsafe
automatic recovery. It is not an operating-system sandbox, identity provider,
access-control service, secrets manager, or defense against an actor that can
rewrite the whole workspace.

## Protected assets

The protocol protects the integrity and interpretation of:

- proposal identity, scope, acceptance conditions, and ordered tasks;
- lifecycle status and task completion;
- explicit approval and revision authorization;
- transaction evidence, snapshots, and managed-state attestation;
- terminal archive bundles and their derived index;
- runtime/Skill package identity and version negotiation; and
- bounded conformance/evaluation evidence intended for publication.

Source code, Git history, credentials, Agent transcripts, and external service
state are not made authoritative by SDD metadata.

## Trust boundaries

| Boundary | Trusted for | Not trusted for |
| --- | --- | --- |
| Human | Intent, proposal selection, explicit approval, abandonment confirmation | Machine-state integrity or authorship proof |
| Agent adapter | Intent routing, runtime invocation, result explanation, implementation work | Parsing authority, lifecycle writes, user identity, automatic repair |
| Reference runtime | Contained parsing, canonical projection, CAS checks, managed transitions | Semantic quality of implementation or truth of user intent |
| Project filesystem | Persisting observed bytes | Atomic multi-file transactions, identity, provenance, exclusive access |
| Git | Source history when explicitly used | SDD lifecycle authority or automatic rollback permission |
| Agent host/model | Tool transport and generated work | Stable protocol compliance without versioned eval evidence |
| Conformance/eval tooling | Evidence for declared cases | Security certification or support for an untested host/model |

Hashes, timestamps, writer strings, process IDs, host labels, and model names
are evidence fields. They MUST NOT be interpreted as authenticated identity or
proof of authorship.

## Threats and controls

| Threat | Required control |
| --- | --- |
| Path escape, unsafe symlink, or non-regular authority file | Resolve within the selected root and fail before reading or writing protocol authority. |
| Malformed UTF-8, schema, metadata, or JSON | Strict decoding and version dispatch; never guess or parse prose as fallback. |
| Stale or concurrent mutation | Exact snapshot/task identity CAS and evidence-backed retry; converge or fail stale. |
| Approval substitution | Structural Approval Manifest comparison and explicit reapproval after semantic revision. |
| Direct managed-state edits | Attestation comparison, doctor diagnostics, and human inspection; never silently bless drift. |
| Partial multi-file transition | One documented authoritative commit point plus staged operation evidence and bounded recovery. |
| Runtime substitution or mixed package | Package-local discovery, identity/Skill hashes, capability and version handshake, no PATH fallback. |
| Ambiguous proposal or cancellation | Human selection/confirmation before mutation; source-control rollback remains separate. |
| Untrusted proposal content | Treat Markdown as data; never execute proposal text or interpolate it into a shell command. |
| Sensitive evidence disclosure | Keep raw runs local; publish only reviewed aggregate reports without prompts, transcripts, credentials, personal data, or absolute user paths. |
| Resource abuse through external input | Bound summary/config reads, subprocess timeouts, deterministic case limits, and no stdin-driven interaction. |

## File and process guarantees

The runtime SHOULD create machine artifacts with owner-only permissions where
the platform supports them. It MUST use individual-file atomic replacement at
documented commit points, but it does not claim ACID behavior across files or
process isolation between writers.

The cooperative concurrency model has no lock, lease, authenticated owner, or
INDEX compare-and-swap. M4 recovery evidence supports stale rejection and
deterministic repair; it does not justify stronger ownership claims. The v1
release therefore keeps the recorded no-lock decision.

## Secrets and privacy

Proposal and task content may contain project-sensitive information. Runtime
JSON, `.sdd` metadata, failure artifacts, Git diffs, and Agent traces MUST be
reviewed before sharing. Public reports MUST NOT include:

- credentials, tokens, cookies, or private keys;
- raw prompts, responses, tool events, or transcripts;
- absolute user paths or machine identifiers;
- customer, project, or personal identifiers; or
- source artifacts not explicitly approved for publication.

Redaction MUST preserve denominators, classifications, versions, and release
decisions. A report that cannot retain those facts safely must remain private.

## Residual risks and response

An actor with write access to all project and package files can replace both
data and integrity evidence. A compromised Agent host can misstate user intent
or implementation quality. A malicious dependency or interpreter is outside
the standard-library package trust claim. Filesystem and kernel failures can
violate assumptions below the runtime.

On unexplained authority drift, package mismatch, unsupported version, or
ambiguous recovery evidence:

1. stop mutation;
2. preserve bounded diagnostics;
3. run read-only `status` and `doctor` with the intended root/runtime;
4. identify the authoritative artifact and compatible engine;
5. require human direction for any semantic choice; and
6. use forward recovery or a documented backup, never deletion-based repair.

Vulnerability reports should contain the minimum reproducer, affected
contract/version, stable error code/action, and redacted evidence. Do not
attach raw project artifacts or Agent transcripts by default.
