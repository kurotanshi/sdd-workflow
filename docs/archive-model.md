# Canonical archive record v1

Status: v0.4 Proposal C contract  
Archive model version: `1`

## Authority and source hierarchy

An archive directory under `sdd/archive/` is authoritative evidence that an artifact set is located in the archive. Its archived `proposal.md` status remains authoritative for `completed` or `abandoned`; neither `INDEX.md` nor metadata may override it.

`sdd/archive/INDEX.md` is a derived rendering and is never authoritative for managed records. For a legacy directory without terminal metadata, the accepted summary sources are, in order: valid recovery evidence in its `.sdd/metadata.json` (authoritative when present), or its unique matching legacy INDEX row. Reading that row is compatibility, not promotion of the entire INDEX to authority. An explicitly provided `rebuild-index --directory NAME --summary TEXT` summary is accepted only when the directory has neither source.

New terminal transitions extend the proposal-local `.sdd/metadata.json` envelope with a `terminal` object. Moving the whole directory carries this evidence into the archive; no second summary sidecar is invented.

## Terminal metadata v1

```json
{
  "terminal": {
    "terminal_metadata_version": 1,
    "archive_date": "2026-07-22",
    "short_name": "add-feature",
    "source_status": "approved",
    "terminal_status": "completed",
    "timestamp": "2026-07-22T12:34:56Z",
    "summary": "Single-line user-approved summary",
    "destination_directory": "2026-07-22-add-feature",
    "source_snapshot": {
      "snapshot_version": 1,
      "proposal_sha256": "<64 lowercase hex>",
      "tasks_sha256": "<64 lowercase hex>",
      "snapshot_digest": "<64 lowercase hex>"
    },
    "operation": {
      "kind": "archive",
      "operation_id": "<opaque evidence token>"
    }
  }
}
```

- `short_name` is copied from the validated active proposal identity.
- `source_status` records the validated pre-transition lifecycle state so an interrupted pre-move retry can reconstruct the source snapshot.
- `terminal_status` is exactly `completed` or `abandoned` and must equal archived `proposal.md`.
- `archive_date` is the execution environment's local `YYYY-MM-DD` and determines the managed archive directory prefix.
- `timestamp` is an independent UTC RFC 3339 instant with trailing `Z`; its UTC calendar date may differ from `archive_date` near local midnight.
- `summary` is caller-supplied UTF-8 text validated by the terminal command. It is not derived from proposal prose.
- `destination_directory` is the exact direct-child name validated before staging and must equal the archive directory after commit.
- `source_snapshot` is the exact raw-byte snapshot accepted immediately before the terminal transition.
- `operation` is terminal retry evidence. It does not supersede directory/status authority and cannot alone prove a commit.
- Unknown terminal fields or versions fail closed. Terminal metadata is immutable after a committed move except through a future explicit migration protocol.

## Recovery evidence v1

`repair-archive-record` records maintainer-confirmed evidence for a legacy directory that lost its terminal records; it never counterfeits a `terminal` object:

```json
{
  "recovery": {
    "recovery_version": 1,
    "archive_date": "2026-07-24",
    "short_name": "refocus-skill-roadmap",
    "terminal_status": "completed",
    "summary": "Explicitly confirmed single-line summary",
    "timestamp": "2026-07-29T04:05:06Z",
    "confirmed_evidence": {
      "proposal_sha256": "<64 lowercase hex>",
      "tasks_sha256": "<64 lowercase hex>"
    },
    "operation": {
      "kind": "repair-archive-record",
      "operation_id": "<64 lowercase hex>"
    }
  }
}
```

- A directory with recovery evidence remains a `legacy` record; the block only supplies the summary that has no INDEX-row source and audits the confirmed repair.
- `confirmed_evidence` holds the pre-repair raw-byte digests printed by the read-only preflight and confirmed at execution; they are the repair's optimistic concurrency token.
- `archive_date`, `short_name`, and `terminal_status` must agree with the directory name and the archived proposal status; disagreement or any malformed field is `ARCHIVE_RECORD_MISMATCH`, never a silent fallback to another source.

## Canonical record

Every readable archive adapter produces:

```json
{
  "archive_model_version": 1,
  "directory_name": "2026-07-22-add-feature",
  "short_name": "add-feature",
  "archive_date": "2026-07-22",
  "terminal_status": "completed",
  "summary": "Single-line user-approved summary",
  "source": "managed"
}
```

| Field | Rule |
| --- | --- |
| `archive_model_version` | Exactly `1`; selects rendering/validation behavior. |
| `directory_name` | Exact direct child name under `sdd/archive/`; never a symlink. |
| `short_name` | Valid lowercase hyphen-case. Managed records use terminal metadata and verify the directory name. Legacy records parse the unambiguous date/status envelope and verify artifact identity where possible. |
| `archive_date` | `YYYY-MM-DD`. Managed source is terminal metadata's local execution date cross-checked with the directory prefix; legacy source is the directory/INDEX date when they agree. |
| `terminal_status` | `completed` or `abandoned`; must match archived proposal status. |
| `summary` | Managed terminal summary, confirmed recovery-evidence summary, or the exact decoded legacy INDEX summary. Missing legacy summary is an error, never replaced with proposal text or an empty invention. |
| `source` | `managed` or `legacy`; diagnostic provenance, not an INDEX column. |

The minimal INDEX row is deterministically rendered from `archive_date`, `short_name`, `terminal_status`, and escaped `summary`, sorted by `(archive_date, short_name, terminal_status, directory_name)`. Canonical records do not include INDEX line numbers, task counts, writer strings, Markdown formatting, or filesystem timestamps.

## Directory naming and mismatches

- Completed managed directory: `YYYY-MM-DD-<short-name>`.
- Abandoned managed directory: `YYYY-MM-DD-<short-name>-abandoned`.
- A direct child that cannot be safely adapted remains an archive diagnostic; it is never silently omitted from a successful rebuild.
- Directory/metadata short-name, date, status, or proposal-status disagreement is `ARCHIVE_RECORD_MISMATCH` with an evidence-only field diff.
- Multiple legacy INDEX rows matching one directory, one row matching multiple directories, or an unparsable escaped row is `AMBIGUOUS_STATE`; the adapter does not select by order or timestamp.
- Missing summary evidence is `UNKNOWN_STATE`. Supported remediation is the explicitly confirmed `repair-archive-record` path, or `rebuild-index --directory NAME --summary TEXT` when only the summary is missing; there is still no automatic recovery, and manual archive edits remain unsupported.
