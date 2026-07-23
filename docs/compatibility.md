# Compatibility axes

Status: v0.6 contract

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

## Problem reports

Include the exact `sdd.py --json --version` envelope, OS, Python version, command name, stable error code/action, proposal schema version, and `doctor --json` findings. Do not attach source artifacts, machine metadata, or full transcripts unless they have been reviewed for secrets and project/customer data.

The behavior-generation boundary remains separate from implementation. The v0.4 command group became active only after `docs/decisions/2026-07-22-managed-mutation-activation.md` recorded a coherent cross-tool `GO`. Schema v2 became the authoring default only after `docs/decisions/2026-07-22-schema-v2-entry.md` recorded evidence for types and research output; release docs, `SKILL.md`, and `--version` switched together.
