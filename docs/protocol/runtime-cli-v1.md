# SDD Reference Runtime and CLI Contract v1

Contract version: `1`

Protocol: `sdd-protocol-1.0`

Status: stable normative contract

This document freezes the observable v1 boundary of the reference runtime,
its noninteractive command-line interface, and package-local discovery. Python
module names, internal functions, human presentation wording, and JSON object
key order are implementation details.

## 1. Runtime identity

The reference distribution MUST identify itself as `sdd-workflow`. Its engine
release MUST be strict `MAJOR.MINOR.PATCH` Semantic Versioning. The engine
release identifies implementation code; it MUST NOT override narrower
proposal, metadata, handshake, or JSON format versions.

The package root MUST contain:

- `SKILL.md`;
- `runtime-identity.json`;
- `scripts/discover-runtime.py`;
- `scripts/sdd.py`; and
- every runtime module imported by `scripts/sdd.py`.

The minimum supported interpreter is CPython 3.11. The reference runtime uses
only the Python standard library.

## 2. Command selectors and arguments

Exactly one command selector is REQUIRED per invocation:

```text
sdd.py [--root PATH] [--json] --version
sdd.py [--root PATH] [--json] --handshake
sdd.py [--root PATH] [--json] validate SHORT_NAME
sdd.py [--root PATH] [--json] validate --all
sdd.py [--root PATH] [--json] list --state active
sdd.py [--root PATH] [--json] status SHORT_NAME
sdd.py [--root PATH] [--json] abandon-preflight SHORT_NAME
sdd.py [--root PATH] [--json] approve SHORT_NAME --expected-snapshot DIGEST [--establish-manifest]
sdd.py [--root PATH] [--json] begin-revision SHORT_NAME --expected-snapshot DIGEST
sdd.py [--root PATH] [--json] complete-task SHORT_NAME TASK_NUMBER --expected-task-digest DIGEST --expected-snapshot DIGEST
sdd.py [--root PATH] [--json] rebuild-index
sdd.py [--root PATH] [--json] validate-index
sdd.py [--root PATH] [--json] doctor
sdd.py [--root PATH] [--json] archive SHORT_NAME --expected-snapshot DIGEST (--summary TEXT | --summary-file PATH) [--dry-run]
sdd.py [--root PATH] [--json] abandon SHORT_NAME --expected-snapshot DIGEST (--summary TEXT | --summary-file PATH) [--dry-run]
```

`--root` selects the project authority boundary. When omitted, resolution is
the Git worktree root, then deterministic upward search, then failure. A
runtime MUST NOT select an unrelated project.

`SHORT_NAME`, task ordinal, digest, and snapshot arguments are exact protocol
inputs. Mutation commands MUST reject stale or mismatched inputs rather than
refreshing them. `--summary` and `--summary-file` are mutually exclusive;
stdin is not a summary source.

`validate` requires exactly one target. `list` accepts only the `active` state.
No v1 command prompts, reads a choice from stdin, starts an editor, searches
`PATH` for another runtime, or retries a mutation automatically.

## 3. Exit classes

| Exit | Stable class |
| --- | --- |
| `0` | The command completed without a blocking error. |
| `1` | Discovery, security, artifact, schema, validation, compatibility, or managed-transition failure. |
| `2` | Invalid command-line usage. |
| `70` | Caught unexpected internal failure. |

JSON and human modes MUST use the same exit class. A nonzero exit MUST still
emit a complete JSON document when `--json` was requested. The runtime MUST
not expose an uncaught traceback as the JSON contract.

## 4. JSON output contract

JSON mode MUST write exactly one UTF-8 JSON document followed by one line feed
to stdout and MUST write no progress or diagnostic text to stderr:

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

The stable top-level fields are `output_version`, `command`, `ok`, `warnings`,
`errors`, and `data`. Every diagnostic MUST contain `code`, `action`,
`message`, and `severity`; `path`, `line`, and `column` are optional evidence.
Warnings and errors MUST use deterministic order.

Consumers MUST branch on `output_version`, `ok`, `errors[].code`, and
`errors[].action`. Human message wording, suggested commands, object key
order, and additive non-authority presentation fields are not decision
contracts.

`tests/fixtures/cli-output-v1.json` is the executable regression fixture for
the command inventory and representative exit `0`, `1`, and `2` envelopes.

## 5. Stable error actions

The v1 action vocabulary binds a failure to the next permitted class of
behavior:

| Action | Required consumer behavior |
| --- | --- |
| `select_project_root`, `choose_short_name`, `create_or_select_proposal` | Obtain the missing human choice. |
| `fix_command_arguments`, `fix_artifact_format` | Correct the named input; do not mutate proposal state first. |
| `refresh_status` | Read fresh state and do not reuse the rejected snapshot. |
| `begin_revision`, `begin_revision_and_reapprove` | Enter the explicit revision lifecycle. |
| `establish_approval_manifest` | Obtain explicit reconfirmation of the canonical plan. |
| `inspect_project_path`, `inspect_machine_metadata`, `inspect_managed_state_drift`, `inspect_archive_state` | Stop mutation and inspect the evidence-bearing authority. |
| `use_supported_engine`, `upgrade_or_recreate_proposal` | Use a compatible format path; never delete a version marker to force downgrade. |
| `rebuild_index` | Rebuild only the derived archive index from authoritative terminal bundles. |
| `report_internal_error` | Stop and preserve bounded failure evidence. |

The stable code-to-action catalog is defined in
[`cli-contract.md`](../cli-contract.md). A patch release MAY add a new code for
a newly distinguished failure only when its action remains safe for v1
consumers. Changing the action of an existing code is a breaking contract
change.

## 6. Human output

Human mode MAY improve wording and layout. Success is written to stdout;
blocking diagnostics are written to stderr. Lifecycle output MUST label:

1. current state;
2. next action;
3. blocked reason;
4. required user action; and
5. authoritative path.

Human output MUST NOT be parsed to decide a mutation. It does not replace the
JSON contract.

## 7. Package-local discovery

An adapter MUST start the first SDD operation in a session by running the
installed package's `scripts/discover-runtime.py`. Default discovery has
exactly one candidate: that same package's `scripts/sdd.py`. It MUST NOT search
`PATH`, choose the newest candidate, combine files from packages, or silently
fall back after failure.

Discovery output version 1 contains:

```json
{
  "discovery_version": 1,
  "ok": true,
  "error": null,
  "runtime": {
    "source": "package-local",
    "installed_path": "/absolute/path/to/scripts/sdd.py",
    "resolved_path": "/absolute/path/to/scripts/sdd.py",
    "handshake": {}
  }
}
```

Distinct candidates are `RUNTIME_AMBIGUOUS`; no candidate is
`RUNTIME_NOT_FOUND`; an unexecutable or malformed probe is
`RUNTIME_HANDSHAKE_FAILED`; incompatible identity or versions are
`RUNTIME_INCOMPATIBLE`. Discovery failures are fail-closed.

## 8. Runtime handshake

Discovery probes the candidate using one unwrapped invocation:

```text
<interpreter> <resolved-runtime> --json --handshake
```

Handshake v1 uses the ordinary CLI envelope with `command: "handshake"`. Its
`data` MUST contain:

- `distribution_id`;
- `engine_version` and `engine_generation`;
- `handshake_version`;
- `cli_output_version`;
- `minimum_schema_version` and `maximum_schema_version`;
- sorted, unique `capabilities`;
- versioned `artifact_versions`;
- `runtime_identity_sha256`; and
- `skill_sha256`.

The identity manifest and handshake MUST agree on distribution, engine
generation, CLI output, handshake, schema coverage, required capabilities,
identity bytes, and Skill bytes. Discovery MUST reject partial agreement. A
successful handshake proves package compatibility, not user approval, Agent
compliance, or project mutation safety.

## 9. Noninteractive and retry behavior

Each adapter operation MUST execute as one command invocation and consume the
complete result before choosing another operation. Shell pipelines, output
filters, exit-code rewriting, background mutation, and interactive prompts are
outside the v1 contract.

Read-only commands MUST remain byte-readonly. A mutating caller MUST first
obtain fresh status and pass the exact snapshot and task identity required by
the command. `ALREADY_APPLIED` is permitted only when durable operation
evidence proves the same original inputs committed. Otherwise a changed
snapshot or authority MUST fail stale.

## 10. Compatibility and evolution

Runtime/CLI contract version `1`, CLI output version `1`, discovery version
`1`, and handshake version `1` are independent axes. Support for one does not
imply support for another.

Additive data fields and new diagnostics are compatible when existing
consumers can ignore them without weakening a stop boundary. Removing or
renaming a public command, changing argument meaning, exit class, JSON
compatibility field, existing code/action binding, discovery selection, or
handshake requirement needs a major protocol/runtime contract version and
corresponding migration and rollback guidance.
