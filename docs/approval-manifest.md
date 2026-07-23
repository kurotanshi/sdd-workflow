# Approval Manifest v1

Status: v0.4 Proposal A contract  
Approval model version: `1`

## Purpose

The Approval Manifest is the complete parsed semantic value approved by the user. A command builds it from the canonical proposal model, stores the full JSON, and later compares parsed structures. Its optional raw-byte SHA-256 is only an identity token; correctness never depends on hashing or canonicalizing Markdown.

## Schema

```json
{
  "approval_model_version": 1,
  "short_name": "add-feature",
  "change_type": "新功能",
  "scope": [
    "Add the requested behavior."
  ],
  "acceptance_conditions": [
    "情境：the observable result is present"
  ],
  "tasks": [
    {
      "text": "Implement the approved behavior"
    }
  ],
  "extensions": {}
}
```

| Field | Type | Approval relevance | Projection rule |
| --- | --- | --- | --- |
| `approval_model_version` | integer, exactly `1` | Projection selector, not user semantics | Written by the engine and used to choose comparison rules. |
| `short_name` | non-empty string | Relevant | Preserve the canonical proposal identity exactly. |
| `change_type` | string or null | Relevant | Preserve the parsed v1 value; approval never translates labels between languages. |
| `scope` | ordered array of strings | Relevant | Project semantic items from canonical section key `changes` (`## 要改什麼`). The parser adapter removes Markdown container syntax; this layer never edits Markdown text. |
| `acceptance_conditions` | ordered array of strings | Relevant | Preserve canonical text and order. |
| `tasks` | ordered array of objects containing only `text` | Relevant | Preserve canonical task text and order; omit ordinal, source line, digest, and completion marker. |
| `extensions` | object keyed by namespace | Relevant by explicit declaration | Include only extensions declared `relevant`, preserving their JSON-compatible value. Sort keys only during deterministic file serialization. |

All seven top-level keys are required. Unknown top-level keys in a stored v1 manifest are rejected with `ERROR_APPROVAL_MANIFEST_INVALID`; they are not silently ignored during comparison.

## Explicit exclusions

The following canonical fields are intentionally absent:

| Canonical input | Reason for exclusion |
| --- | --- |
| canonical model version and whether schema was declared | Parser mechanics, not approved behavior. The manifest has its own projection version. |
| raw `schema_version` field | The top-level compatibility selector is not copied directly. Schema v2 projects `{"schema_version": 2}` through the approval-relevant `sdd.schema` extension, so v1 and v2 approval identities cannot be interchanged. |
| proposal `status` | Lifecycle state is authoritative in `proposal.md`, not semantic approval content. |
| task `completed`, ordinal, and source line | Runtime progress and source location; task array order and text carry approved identity. |
| `## 為什麼做` (`why`) | Background/rationale may be clarified without changing approved scope. |
| `## 影響範圍` (`impact`) | File/path estimates and presentation metadata are not the behavior contract. |
| section heading spelling or Markdown list marker | Parser-adapter syntax; never input to the manifest algorithm. |
| diagnostics and mutation-safety flags | Current validation state, not user-approved semantics. |
| extensions declared `excluded` | Runtime or presentation data with an explicit non-approval policy. |
| active metadata, writer version, timestamps, snapshot, operation IDs | Concurrency/audit evidence, not semantic scope. |

Changing an excluded value alone must produce an equal Approval Manifest. Exclusion does not make invalid Markdown mutable: parser or metadata diagnostics may still block a command independently.

### Schema v2 extension policy

| Namespace | Approval relevance | Manifest behavior |
| --- | --- | --- |
| `sdd.schema` | Relevant | Stored as `{"schema_version": 2}` in `extensions`; a schema boundary changes approval identity. |
| `sdd.research.conclusion` | Excluded | Not stored. A research conclusion is validated terminal output, not part of the question/scope authorization. |

The approval model version remains `1`: its existing namespace-keyed extension envelope already represents the v2 additions without changing top-level fields. Adapter code owns namespace creation and must declare relevance in `CANONICAL_EXTENSION_APPROVAL_POLICY`. Stored extension values are preserved and compared structurally; an engine that cannot reproduce a relevant namespace cannot claim manifest equality.

## Semantic projection rules

1. Require a readable, mutation-safe canonical model and a supported approval model version.
2. Preserve Unicode code points exactly as emitted by the parser. Do not apply NFC/NFD normalization, case folding, locale translation, or whitespace normalization in the manifest layer.
3. Let each parser adapter convert its source syntax into semantic scope items, task text, and acceptance-condition text. Approval projection never knows heading depth, bullet marker, checkbox spacing, line ending, BOM, or indentation.
4. Preserve order for `scope`, `acceptance_conditions`, and `tasks`; order changes are approval-relevant.
5. Represent relevant extensions as a namespace-keyed object. A canonical extension that lacks an explicit relevance declaration, cannot be represented as JSON, or conflicts with another namespace blocks projection.
6. Serialize the stored file as UTF-8, `ensure_ascii=false`, sorted object keys, two-space indentation, and one trailing LF. This deterministic representation supports fixtures and raw identity; parsed structural equality remains authoritative.

## Comparison and diff

- Parse the stored manifest strictly, verify all required fields and types, then project the current canonical model using the stored `approval_model_version`.
- Compare JSON data structures recursively. Object key order is irrelevant; array order and string code points are relevant.
- Equality returns no semantic change even if the source Markdown bytes, excluded sections, status, or task markers differ.
- Inequality returns `ERROR_APPROVED_PLAN_CHANGED` with action `begin_revision` and a deterministic list of field-level differences.
- A difference path uses JSON Pointer escaping and identifies additions, removals, or replacements, for example `/tasks/1/text` or `/scope/0`.
- The diff reports values from parsed structures; it never emits a Markdown patch or silently adopts current content.

## Field-policy completeness

Every `CanonicalProposal` field, every nested semantic field, and every extension must have an explicit `relevant` or `excluded` policy. Tests compare the dataclass field inventory against that policy table. Adding a field without deciding its approval effect is a test failure and blocks release.
