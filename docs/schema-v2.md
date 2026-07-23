# Proposal Schema v2

Status: accepted format contract for v0.5

## Encoding and dispatch

A Schema v2 `proposal.md` begins at byte zero with this UTF-8 frontmatter envelope:

```yaml
---
schema_version: 2
---
```

The envelope is deliberately a strict YAML-compatible subset implemented without a YAML dependency:

- `---` delimiter lines and the key name are exact; LF and CRLF are both accepted by text decoding.
- The value is an unquoted base-10 integer. Booleans, strings, comments, duplicate keys, blank entries, and nested values are invalid.
- `schema_version` is the only recognized frontmatter key. An unknown key fails closed with `ERROR_UNKNOWN_SCHEMA_FIELD`; a malformed envelope uses `ERROR_INVALID_SCHEMA_METADATA`.
- An absent envelope continues to select unversioned v1 and its legacy fallback. An explicit supported `schema_version: 1` selects strict v1. An unknown integer version fails before task parsing with `ERROR_UNSUPPORTED_SCHEMA_VERSION`.
- Frontmatter is format metadata, not a Markdown section. Parser adapters strip it before collecting headings; transaction logic receives only the canonical model.

New proposals authored by the v0.5 Skill use version `2`. Existing v1 and legacy artifacts are not rewritten or migrated in place.

## Fields and allowed values

All v2 proposals retain the v1 headings and lifecycle statuses:

| Field | Encoding | Allowed/required values |
| --- | --- | --- |
| Schema version | frontmatter `schema_version` | integer `2` |
| Status | `## 狀態` single value | `draft`, `approved`, `completed`, `abandoned` |
| Primary type | `## 類型` single value | `新功能`, `修 bug`, `重構`, `維運`, `文件`, `研究` |
| Why | `## 為什麼做` | existing semantic prose |
| Scope | `## 要改什麼` | existing ordered semantic items |
| Impact area | `## 影響範圍` | existing presentation prose; not an impact taxonomy |
| Conclusion | `## 結論` | present only for `研究`; may be empty while active or abandoned, but a completed research proposal requires at least one nonblank semantic item |

The five v1 headings remain required for every v2 type. `## 結論` is additionally required for research and rejected for other types. V2 rejects unknown level-two headings so that unmodelled semantics cannot silently bypass approval policy. Level-three or deeper content remains part of its containing known section.

No label, explicit-impact vocabulary, or type-specific required-section matrix is part of Schema v2.

## Canonical extensions

V2 reuses `CanonicalProposal` and adds only namespaced adapter extensions:

| Namespace | Value | Approval policy | Reason |
| --- | --- | --- | --- |
| `sdd.schema` | `{"schema_version": 2}` | approval-relevant | Prevents v1 and v2 approval identities from being silently interchanged while keeping the Approval Manifest envelope compatible. |
| `sdd.research.conclusion` | `{"items": [...]}` | presentation-only | The conclusion is an implementation/research result, analogous to completion output; it must not invalidate the question and plan that authorized the work. |

The conclusion also appears as a canonical section with key `conclusion` and excluded approval relevance so archive/read consumers can render it without understanding Markdown.

Adapter namespaces are code-owned. User-authored frontmatter cannot create arbitrary extensions. Stored relevant extension values are preserved and compared structurally; an engine that cannot reproduce one cannot claim Approval Manifest equality. No adapter may add an extension without an explicit approval policy and fixtures.

## Archive behavior

Active and terminal transitions continue to consume only `CanonicalProposal`; they do not branch on Markdown headings or parser adapter. A completed research transition fails validation when its canonical conclusion is empty. The proposal, terminal metadata, and canonical archive adapter together preserve the question, acceptance conditions, and conclusion. Abandoned research may retain an empty conclusion because abandonment must not be blocked by unfinished research.
