# SDD v1 Versioning and Deprecation Policy

Policy version: `1.0.0`

Applies from release: `v1.0.0`

Status: frozen v1.0 historical evidence; not a current deprecation policy

This policy classifies changes to the Core protocol, reference runtime, Agent
adapter contract, schemas, machine envelopes, and conformance assets. It uses
Semantic Versioning for release contracts while preserving independent integer
versions for wire and artifact formats.

## 1. Independent version axes

| Axis | v1.0 value | Version rule |
| --- | --- | --- |
| Core protocol | `1.0.0` / identifier `sdd-protocol-1.0` | Semantic Versioning; identifier carries major/minor. |
| Reference runtime engine | `1.0.0` | Semantic Versioning. |
| Runtime/CLI contract | `1.0.0` | Semantic Versioning. |
| Agent adapter contract | `1.0.0` | Semantic Versioning. |
| Proposal schema | `1`, `2` | Monotonic integer format version. |
| CLI JSON output | `1` | Monotonic integer wire version. |
| Runtime discovery | `1` | Monotonic integer wire version. |
| Runtime handshake | `1` | Monotonic integer wire version. |
| Canonical and machine envelopes | individually `1` | Independent monotonic integer versions. |
| Conformance manifests and fixtures | individually `1` | Independent monotonic integer versions. |

An engine version MUST NOT imply support for an artifact or wire version.
Every implementation MUST declare the narrowest applicable axes and fail
closed on an unsupported explicit version.

## 2. Semantic Versioning classification

After `v1.0.0`, release versions are `MAJOR.MINOR.PATCH`:

- PATCH fixes behavior to match the existing contract, clarifies prose
  without changing obligations, adds tests for an existing rule, or adds
  optional diagnostic/presentation data that v1 consumers may ignore.
- MINOR adds backward-compatible optional capability, command, diagnostic
  code, proposal type, or schema support without changing existing authority,
  stop boundaries, defaults, or required consumer behavior.
- MAJOR removes or renames a public command; changes existing argument
  meaning, exit class, JSON compatibility field, code/action binding,
  authority, lifecycle, approval semantics, task identity, commit point,
  recovery classification, discovery selection, handshake requirement,
  adapter trigger authority, or supported existing schema behavior.

A bug fix that makes previously accepted unsafe or invalid state fail closed
MAY be PATCH when the state was already prohibited by the normative contract.
The release notes MUST cite the governing clause and identify the observable
change. If the prior contract allowed the behavior, the change is MAJOR.

Pre-release identifiers MAY be used for release candidates. A pre-release MUST
NOT be advertised as the supported v1 stable line or used to rewrite stable
artifact versions.

## 3. Deprecation policy

Deprecation is documentation and diagnostics, not silent behavior change.

1. A stable v1 surface MAY be deprecated only in a MINOR release.
2. The release notes MUST name the exact command, field, capability, schema,
   or installation path; replacement; migration; rollback; and earliest
   removal major.
3. The deprecated surface MUST remain functional for the rest of the current
   major line unless continued support would violate an already normative
   safety rule.
4. Removal or incompatible reinterpretation requires the next MAJOR release.
5. A warning MUST use a stable diagnostic code when machine consumers need to
   distinguish the deprecation. Human prose alone is not a migration API.

Security response MAY shorten notice, but it MUST still publish bounded
impact, migration, rollback, and compatibility evidence. It MUST NOT silently
adopt, delete, or rewrite project artifacts.

## 4. Proposal schema support

The v1 runtime supports implicit/explicit Schema v1 and explicit Schema v2.
New proposals use Schema v2. Existing supported proposals MUST NOT be rewritten
merely because a newer engine is installed.

A new proposal schema:

- uses a new integer and strict dispatch before semantic parsing;
- documents authority and approval relevance for every new field;
- includes read, mutation, archive, unknown-version, migration, and rollback
  fixtures;
- MUST NOT change the meaning of Schema v1 or v2 bytes; and
- is a MINOR engine capability only when support is additive and the default
  authoring format remains unchanged.

Changing the default authoring schema requires an explicit release decision
and migration/rollback guide. Removing supported Schema v1 or v2, or changing
its canonical meaning, requires a MAJOR release.

Unknown explicit schemas MUST fail before their authority-bearing content is
used. Removing a schema marker, machine envelope, or approval evidence to force
an older parser is never a supported downgrade.

## 5. Wire and machine-envelope support

CLI output, discovery, handshake, metadata, approval, attestation, snapshot,
archive, terminal, and conformance versions evolve independently.

An additive field MAY retain its integer version only when the owning contract
declares it ignorable and it cannot affect authority, approval, mutation,
security, or stop behavior. Otherwise the format receives a new integer
version. Writers MUST emit one declared version; readers MUST reject versions
they do not support.

A release adding a new envelope version MUST state whether it dual-reads the
previous version. It MUST NOT claim downgrade support merely because an older
reader can inspect unrelated Markdown.

## 6. Migration release gate

Every change that introduces a schema, envelope, default, or breaking contract
MUST ship with:

- a source/target compatibility matrix;
- preconditions and a read-only preflight;
- exact authority-bearing artifacts changed;
- atomic commit point and interruption recovery;
- validation and conformance evidence;
- whether the migration is automatic, explicit, or recreate-only;
- backup and sensitive-data guidance; and
- a rollback classification.

Migration MUST require explicit user intent when it changes approval-relevant
semantics or machine-managed authority. A migration tool MUST use versioned
structured results and evidence-backed retries. No migration may infer user
approval from successful conversion.

## 7. Rollback policy

Each release MUST identify:

- the last compatible engine line;
- artifacts written or upgraded by the release;
- whether active proposals can continue on the prior engine;
- a safe point before mutation;
- post-commit recovery when rollback is no longer direct; and
- the source-control scope, which remains separate from SDD lifecycle state.

Rollback is one of:

| Class | Meaning |
| --- | --- |
| `direct` | Prior engine can read and mutate every artifact; pinning is sufficient. |
| `finish-or-abandon` | Prior engine cannot manage in-flight state; complete or abandon with the current compatible engine first. |
| `restore-backup` | A committed format migration requires restoring an explicit pre-migration backup. |
| `forward-recovery` | Authority committed and must be repaired or finalized by a compatible current/newer engine. |

Deleting `.sdd`, editing lifecycle fields, removing version markers, moving a
terminal bundle back to active state, or rewriting Git history MUST NOT be
presented as protocol rollback.

## 8. Release evidence

A stable release candidate MUST pass the versioned protocol conformance suite,
CLI JSON regression fixtures, applicable adapter conformance, supported
install matrix, recovery drills, examples, and the declared Agent evaluation
gate. Release notes MUST separately list Added, Changed, Deprecated, Removed,
Security, Migration, and Rollback sections when applicable; an empty section
may state `None`.
