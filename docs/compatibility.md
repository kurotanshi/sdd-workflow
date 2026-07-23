# Compatibility axes

Status: v0.8 portable-distribution contract over the v0.6 engine

| Axis | Current version | Consumer | Unknown version behavior |
| --- | --- | --- | --- |
| Engine/release | `0.6.0` active | Human diagnostics/activation records | Never overrides artifact formats. |
| CLI output | `1` | Skill and test consumers | Consumer must refuse unsupported envelopes. |
| Proposal schema | implicit/explicit `1`, explicit `2` | Markdown parser adapter | Fail before task parsing; never guess future schema. |
| Canonical model | `1` | Internal projections | Engine upgrade required. |
| Snapshot | `1` | CAS and terminal source evidence | Fail closed. |
| Active metadata | `1` | Active/terminal transition engine | `ERROR_UNSUPPORTED_METADATA_VERSION`. |
| Approval model | `1` | Approval Manifest projection | `ERROR_UNSUPPORTED_APPROVAL_MODEL_VERSION`. |
| Managed attestation | `1` | Drift comparison | `ERROR_UNSUPPORTED_ATTESTATION_VERSION`. |
| Archive model | `1` | INDEX renderer/validator | Fail record adaptation. |
| Terminal metadata | `1` | Terminal retry/archive adapter | Fail closed; never reinterpret collision as committed retry. |

Read compatibility is not mutation compatibility. An absent proposal schema selects v1; an absent machine envelope can mean an initial draft or an explicitly diagnosed unattested legacy proposal, never an inferred future format. Version writer strings are diagnostic signals only.

## Upgrade and downgrade matrix

| Artifact / engine pairing | Read | Mutation | Required action |
| --- | --- | --- | --- |
| v1 or readable legacy with v0.6 | Yes | v1 when mutation-safe; legacy no | Establish a manifest explicitly for unattested approved v1; recreate/upgrade legacy before mutation. |
| Schema v2 with v0.6 | Yes | Yes when all format and state versions are supported | Normal managed command path. |
| Schema v2 with a v1-only engine | No | No | Upgrade the engine; never remove frontmatter to force fallback. |
| v0.4/v0.5 metadata with v0.6 | Yes | Yes when metadata/approval/attestation versions remain supported | Writer version is preserved as provenance until the next successful write. |
| Supported formats with a newer writer generation | Format-dependent | Format-dependent; never inferred from writer alone | `doctor` reports `ENGINE_VERSION_SKEW`; collect `--version` and use a compatible engine when behavior is uncertain. |
| Unknown proposal/metadata/approval/attestation version | No for the affected operation | No | `use_supported_engine`; no prose fallback or deletion-based downgrade. |

Supported downgrade is read-only and format-bound. A pre-v0.5 engine may read only the schemas and envelopes it explicitly supports. An in-flight managed proposal must be completed or abandoned with a compatible engine before pinning an older workflow; deleting `.sdd` or a schema marker is never downgrade.

## Portable environment matrix

| Axis | Supported | Conditional / best effort | Fail-closed or unsupported behavior |
| --- | --- | --- | --- |
| OS | macOS and Linux/Ubuntu, with required filesystem and clean-install tests | Windows is best effort through `sdd.py`; the POSIX launcher and release gate do not claim Windows support | An unsupported launcher/platform never authorizes a prose parser fallback. |
| Python | CPython 3.11 and the current CI Python generation | A later CPython is accepted only while the complete suite and handshake pass | Python below 3.11 returns `ERROR_PYTHON_VERSION`; missing `python3` returns `ERROR_PYTHON_NOT_FOUND`. |
| Agent host | Claude Code Skills and Codex Skills when the host loads one complete package from its documented root | Other Agent Skills hosts and third-party managers are conditional on proving both host loading and package handshake | A complete package in an unscanned directory is not treated as installed. |
| Agent model | Model identity is not a runtime compatibility axis; evaluated model/host pairs are recorded in each Agent-eval report | A changed model or host generation requires affected scenarios to be rerun | No model label can override a failed runtime handshake, approval gate, or Critical Violation. |
| Proposal schema | implicit/explicit v1 and explicit v2 | readable legacy artifacts are read-only when the adapter marks mutation unsafe | Unknown or malformed explicit versions fail before tasks are parsed. |
| Distribution | One complete `sdd-workflow` package with matching Skill hash and required capabilities | A complete directory symlink is supported where the host follows it | Partial/mixed copies, multiple distinct candidates, PATH discovery, and silent fallback are unsupported. |

Installation-channel locations and host-loading limits are fixed in
[`install-methods.md`](./install-methods.md) and
`conformance/install-channels-v1.json`.

## Skill/runtime combinations

| Skill package / runtime | Discovery | Project mutation | Required action |
| --- | --- | --- | --- |
| Package-local runtime, identity manifest, Skill hash, engine generation, schema interval, and capabilities all match | Accepted | Allowed subject to ordinary project/status gates | Normal command path. |
| Same file exposed through duplicate symlink aliases | Deduplicated by resolved file identity | Same as the one resolved candidate | Record installed and resolved paths. |
| Multiple distinct candidates in one explicit discovery source | `RUNTIME_AMBIGUOUS` | No | Select one complete package; do not choose newest or first. |
| Explicit candidate missing or invalid | `RUNTIME_NOT_FOUND` or `RUNTIME_HANDSHAKE_FAILED` | No | Repair the exact pin; no fallback to bundled or PATH runtime. |
| Wrong distribution, handshake/output version, engine generation, schema interval, or capability set | `RUNTIME_INCOMPATIBLE` | No | Install a compatible complete distribution. |
| Installed `SKILL.md` bytes differ from `runtime-identity.json` | `RUNTIME_INCOMPATIBLE`; `doctor` reports `RUNTIME_SKILL_VERSION_SKEW` when directly inspected | No | Reinstall the complete distribution; never choose either file by timestamp. |
| Compatible runtime with proposal/metadata version outside its declared artifact support | Runtime handshake may pass, affected project command fails its narrower format gate | No for the affected artifact | Use an engine that explicitly supports the artifact; never delete version markers. |

The runtime handshake proves package compatibility, not Agent compliance.
Agent host/model behavior remains covered by the versioned Agent-eval matrix.

## Problem reports

Include the exact `sdd.py --json --version` envelope, OS, Python version, command name, stable error code/action, proposal schema version, and `doctor --json` findings. Do not attach source artifacts, machine metadata, or full transcripts unless they have been reviewed for secrets and project/customer data.

The behavior-generation boundary remains separate from implementation. The v0.4 command group became active only after `docs/decisions/2026-07-22-managed-mutation-activation.md` recorded a coherent cross-tool `GO`. Schema v2 became the authoring default only after `docs/decisions/2026-07-22-schema-v2-entry.md` recorded evidence for types and research output; release docs, `SKILL.md`, and `--version` switched together.
