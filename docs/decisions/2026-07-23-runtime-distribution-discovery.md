# Runtime distribution and discovery

## Date
2026-07-23

## Status
Accepted for the v0.8 portable-runtime implementation.

## Context

The Skill and deterministic Python core are one behavioral unit, but a copied
Skill, a package installed by a host, a development symlink, and an unrelated
`sdd` on `PATH` can expose different bytes. Selecting a runtime by command
name, current directory, newest timestamp, or highest version would make the
approval and mutation boundary depend on unobservable machine state.

The portable distribution needs a deterministic bootstrap that works outside
the source checkout and can prove which runtime it selected. It must also
distinguish release identity from the independently versioned protocol and
artifact formats.

## Decision

### Distribution unit

`skills/sdd-workflow/` is the indivisible release unit. It contains
`SKILL.md`, host metadata, the bootstrap/discovery entry point, the Python
runtime, and a machine-readable identity manifest. Installers copy or link the
whole directory to a host-specific Skill root; they do not install a separate
global `sdd` executable. A release archive has one top-level
`sdd-workflow/` directory and no external runtime dependency beyond a
supported `python3`.

### Discovery sources and precedence

Discovery has two modes:

1. An explicit absolute runtime path supplied by the caller is the sole
   candidate. It is intended for controlled testing, rollback, and a
   deliberately pinned deployment.
2. Without an explicit path, the only candidate is the package-local
   `scripts/sdd.py` resolved from the loaded `SKILL.md` package root.

The resolver never searches `PATH`, the current working directory, repository
parents, another host's Skill directory, or a "latest" installation. A source
that yields zero candidates is `RUNTIME_NOT_FOUND`; more than one distinct
candidate is `RUNTIME_AMBIGUOUS`. A symlink is allowed only when its resolved
target remains a regular file; identity reports both the installed and
resolved locations. Repeated aliases that resolve to the same file count as
one candidate.

There is no fallback between modes. If an explicit candidate is missing,
malformed, or incompatible, discovery fails instead of silently selecting the
bundled runtime.

### Identity and handshake

The runtime exposes a read-only versioned handshake before project discovery.
The response includes:

- distribution ID `sdd-workflow`;
- engine version and CLI output version;
- protocol handshake version;
- supported proposal-schema interval;
- supported metadata, approval, attestation, archive, terminal, and snapshot
  versions;
- a sorted capability list for the command groups the Skill depends on;
- installed path, resolved path, and discovery source when the resolver adds
  environment evidence.

The package identity manifest fixes the expected distribution ID, handshake
version, compatible engine generation, schema interval, and required
capabilities. Discovery accepts a candidate only when its handshake is valid
JSON, uses a supported handshake/output version, matches the distribution and
engine-generation contract, covers the required schema interval, and contains
every required capability. Unknown or absent required fields are
`RUNTIME_INCOMPATIBLE`; they are never inferred from the engine version.

The handshake is informational and read-only. It does not inspect a
repository, establish approval, or authorize mutation.

### Version axes

Engine/release, CLI output, protocol handshake, proposal schema, canonical
model, snapshot, active metadata, Approval Manifest, managed attestation,
archive, and terminal metadata remain separate axes. The distribution manifest
may constrain a compatible engine generation, but it cannot reinterpret an
unknown artifact version. Capability membership selects behavior; comparing
version strings alone does not.

### Upgrade, downgrade, and rollback

An upgrade installs a complete candidate beside the current package, verifies
its identity and handshake, then atomically changes the host-managed Skill
directory or symlink. The old complete package remains the rollback unit until
the new package passes clean-install lifecycle smoke. In-place mixing of files
from two releases is unsupported.

A downgrade uses the same whole-package switch and is permitted only when the
older handshake declares every required capability and every in-flight
artifact version. Managed proposals using a newer unsupported format must be
completed or abandoned with a compatible runtime first. Deleting metadata or
schema markers is never rollback.

Rollback is triggered by handshake failure, clean-install lifecycle failure,
or a repeated host-loading mismatch. Rollback changes the installed package;
it never rewrites proposal state.

### Failure contract

Bootstrap failures are stable, non-interactive, and fail closed:

| Code | Meaning | Required action |
| --- | --- | --- |
| `RUNTIME_NOT_FOUND` | The selected source produced no regular runtime file. | Reinstall or provide one exact absolute candidate. |
| `RUNTIME_AMBIGUOUS` | The selected source produced multiple distinct files. | Remove ambiguity and select one complete package. |
| `RUNTIME_HANDSHAKE_FAILED` | The candidate could not return a valid handshake. | Repair/reinstall the candidate; do not invoke project commands. |
| `RUNTIME_INCOMPATIBLE` | Identity, version axes, or required capabilities do not match. | Install a compatible complete distribution. |

These failures never authorize Markdown parsing, PATH lookup, a second
candidate, or a project mutation.

## Consequences

- Host integrations need only locate the loaded Skill directory; the package
  carries its runtime.
- Manual copy, release archive, host installer, third-party installer, and
  development link can share one identity/handshake test contract.
- A globally installed command may still exist for unrelated tools, but it is
  outside this Skill's discovery graph.
- Package validation and clean-environment smoke must reject incomplete or
  mixed distributions.

## Rejected alternatives

- Search `PATH` and select the first `sdd`: ordering is host state, not package
  identity, and can change without repository evidence.
- Select the highest engine version: release versions do not prove protocol or
  artifact compatibility.
- Fall back from an explicit candidate to the bundled runtime: a broken pin
  would become an unreported behavior change.
- Publish the core separately from the Skill: independent upgrades would make
  skew the default and complicate rollback.

## Validation gate

The decision is implemented only when hermetic tests cover zero, one,
duplicate-alias, multiple-distinct, malformed-handshake, wrong-distribution,
unsupported-version, and missing-capability candidates; clean-install smoke
must then complete discovery and the managed proposal lifecycle without
consulting `PATH`.

## Sensitive-data review

- [x] No transcript or user project content is stored.
- [x] Paths and identities are synthetic.
- [x] The decision contains no credentials or host-specific personal data.
