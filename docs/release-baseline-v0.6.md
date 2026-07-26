# v0.6 release baseline

Status: historical snapshot recorded 2026-07-23 for regression comparison

This document is an index of immutable release facts and canonical contract
sources. It is not a second protocol specification. When a summary here and a
linked contract differ, the linked contract governs.

## Release identity

| Item | Baseline |
| --- | --- |
| Release tag | `v0.6.0` |
| Release commit | `863f7691ffd96ce49a058ed87f5f8889b73946fc` |
| Engine version | `0.6.0` |
| CLI output version | `1` |
| Proposal schemas | implicit/explicit `1`, explicit `2` |
| Minimum Python | CPython `3.11` |

The machine version envelope is:

```json
{"command":"version","data":{"engine_version":"0.6.0","maximum_schema_version":2,"minimum_schema_version":1},"errors":[],"ok":true,"output_version":1,"warnings":[]}
```

An eval claiming this baseline must check out the exact release commit or an
artifact proven to contain the same package bytes. A branch name, moving major
tag, engine writer string, or current Agent/model label is not an immutable
baseline identity.

## Public CLI contract

The public commands are:

```text
version
validate
list
status
abandon-preflight
approve
begin-revision
complete-task
rebuild-index
validate-index
doctor
archive
abandon
```

[`cli-contract.md`](./cli-contract.md) owns the stdout/stderr, JSON envelope,
exit-code, stable code/action, and noninteractive behavior. The versioned
command inventory and representative exit `0`, `1`, and `2` JSON documents are
fixed by [`tests/fixtures/cli-output-v1.json`](../tests/fixtures/cli-output-v1.json)
and `tests/test_cli_snapshots.py`.

## Artifact and schema fixtures

- `tests/fixtures/baseline/MANIFEST.json` inventories legacy and Schema v1
  characterization cases and their source rule IDs.
- `tests/fixtures/schema-v2/MANIFEST.json` inventories Schema v2 types,
  research output, strict frontmatter, and unknown future-version behavior.
- `tests/fixtures/snapshot-v1.json` fixes raw-byte snapshot serialization and
  digest identity.
- `tests/fixtures/archive/` fixes legacy archive adaptation and derived INDEX
  ordering behavior.

[`schema-v2.md`](./schema-v2.md) owns the authoring and parsing contract.
[`compatibility.md`](./compatibility.md) owns read/mutation compatibility and
unknown-version behavior.

## Version axes

The v0.6 compatibility generation records:

| Axis | Version |
| --- | --- |
| Engine/release | `0.6.0` |
| CLI output | `1` |
| Proposal schema | `1`, `2` |
| Canonical model | `1` |
| Snapshot | `1` |
| Active metadata | `1` |
| Approval model | `1` |
| Managed attestation | `1` |
| Archive model | `1` |
| Terminal metadata | `1` |

These values select independent compatibility contracts; the engine version
does not override any artifact format. Normative behavior and remediation live
in [`compatibility.md`](./compatibility.md).

## Skill trigger and adapter baseline

The canonical adapter source is
[`skills/sdd-workflow/SKILL.md`](../skills/sdd-workflow/SKILL.md). Its explicit
phase vocabulary is `提案`, `開始實作`, `實作`, `歸檔`, `放棄`, `取消提案`, and
`確認放棄`; a bare `取消` is ambiguous, and an explicit source-control/code
rollback remains outside SDD. `tests/trigger-contract.sh` prevents the
frontmatter, phase menu, README, and cancellation boundary from drifting.

The v0.4 managed-mutation activation record observed Codex CLI `0.145.0` and
Claude Code `2.1.217` on CPython 3.11+ and macOS arm64. That dated record proves
the activation decision only; it does not identify future host/model versions.
See
[`2026-07-22-managed-mutation-activation.md`](./decisions/2026-07-22-managed-mutation-activation.md)
and
[`2026-07-22-team-readiness-entry.md`](./decisions/2026-07-22-team-readiness-entry.md).

## Package and environment baseline

The installable package root is `skills/sdd-workflow/`:

```text
skills/sdd-workflow/
├── SKILL.md
├── agents/openai.yaml
└── scripts/
    ├── sdd
    ├── sdd.py
    └── sdd_core/
```

`tests/package_validation.py` is the machine-readable required-file and
forbidden-file manifest. `scripts/build-release-package.py` constructs release
archives from that validated package. [`runtime.md`](./runtime.md) owns the
platform contract: macOS and Linux are supported, Windows is best effort, and
the core uses only the Python standard library. [`ci.md`](./ci.md) records the
Node 24 action and runner baseline. [`testing.md`](./testing.md) maps current
tests to release responsibilities.

## Authority, trust, and recovery sources

- [`architecture.md`](./architecture.md): artifact/field authority, machine
  metadata, compatibility axes, and individual-file atomicity.
- [`approval-manifest.md`](./approval-manifest.md): approved semantic
  projection and invalidation.
- [`managed-state.md`](./managed-state.md): attestation and managed drift.
- [`transaction-protocol.md`](./transaction-protocol.md): commit points,
  failure classes, safe retry, and activation boundaries.
- [`archive-model.md`](./archive-model.md): terminal archive authority and
  derived INDEX.
- [`doctor-diagnostics.md`](./doctor-diagnostics.md): evidence thresholds and
  manual-only remediation.
- [`team-operations.md`](./team-operations.md): one-owner boundary, worktrees,
  handoff, and INDEX recovery.

The runtime is a cooperative change-control mechanism, not an authorization
sandbox. The linked documents define what can be detected and recovered; this
baseline does not broaden those guarantees.

## Reproduction checklist

From an exact baseline checkout:

```text
python3 skills/sdd-workflow/scripts/sdd.py --json --version
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tests/package_validation.py
python3 tests/docs_consistency.py
sh tests/trigger-contract.sh
python3 tests/install_smoke.py
```

An eval report must additionally record OS, Python, Agent host/model and host
version, Skill commit, runtime version, scenario/scorer version, permission
mode, supported sampling controls, and execution date.

## Rebaseline policy

`v0.6.0` and its release commit are immutable. A later patch may link this
baseline but must not rewrite its release identity or historical evidence.
Behavioral, package, fixture, or JSON-contract changes require a new exact
release identity and explicit comparison notes before an eval adopts them.
