# v1.0 release baseline

Status: release candidate prepared 2026-07-23

The final release handoff records the exact candidate commit. Tagging, pushing,
and publication are not implied by this document.

## Release identity

| Item | v1.0 contract |
| --- | --- |
| Release target | `v1.0.0` |
| Engine version | `1.0.0` |
| Core protocol | `1.0.0` / `sdd-protocol-1.0` |
| Runtime/CLI contract | `1.0.0` |
| Agent adapter contract | `1.0.0` |
| CLI output | `1` |
| Runtime discovery / handshake | `1` / `1` |
| Proposal schemas | implicit/explicit `1`, explicit `2` |
| Minimum Python | CPython `3.11` |

The machine version envelope is:

```json
{"command":"version","data":{"engine_version":"1.0.0","maximum_schema_version":2,"minimum_schema_version":1},"errors":[],"ok":true,"output_version":1,"warnings":[]}
```

The v0.6 baseline and commit remain immutable in
[`release-baseline-v0.6.md`](./release-baseline-v0.6.md).

## Stable contracts

- [`protocol/core-v1.md`](./protocol/core-v1.md) defines authority, lifecycle,
  approval, attestation, transactions, recovery, compatibility, and trust.
- [`protocol/runtime-cli-v1.md`](./protocol/runtime-cli-v1.md) defines public
  commands, arguments, exit classes, JSON, discovery, and handshake.
- [`protocol/agent-adapter-contract.md`](./protocol/agent-adapter-contract.md)
  defines phase triggers, approval wording, ambiguity, managed mutation, and
  human handoff.
- [`protocol/versioning-policy-v1.md`](./protocol/versioning-policy-v1.md)
  defines Semantic Versioning, deprecation, schema evolution, migration, and
  rollback.

## Format freeze

v1.0 does not add Schema v3 or a new machine-envelope generation. Canonical
model, snapshot, active metadata, approval, attestation, archive, and terminal
metadata remain at version `1`; proposals remain Schema v1/v2. Engine identity
does not override these narrower compatibility axes.

The public command inventory and representative exit `0`, `1`, and `2` JSON
documents remain fixed by
[`tests/fixtures/cli-output-v1.json`](../tests/fixtures/cli-output-v1.json).

## Release evidence

- Runtime conformance: 18/18 cases passed.
- Public conformance kit: 5/5 cases passed.
- Agent evaluation: 76/78 adherent (97.4%), Critical Violations 0.
- Hermetic adapter: 10/10 applicable scenarios passed.
- Acceptance-time requirement change: 6/6 real-Agent runs passed.
- Recovery, installation, examples, package, documentation, and trigger gates
  are required by [`release-checklist.md`](./release-checklist.md).

Evidence details are recorded in
[`reports/v1.0-conformance.md`](./reports/v1.0-conformance.md) and
[`../evals/reports/v1.0-agent-eval-summary.md`](../evals/reports/v1.0-agent-eval-summary.md).

## Security, migration, and rollback

The security and trust boundary is
[`security-trust-model.md`](./security-trust-model.md); explicit exclusions are
[`non-goals-v1.md`](./non-goals-v1.md). Upgrade from v0.6.0 follows
[`migration-v1.md`](./migration-v1.md). Direct rollback is permitted only
under the format checks in [`rollback-v1.md`](./rollback-v1.md).

## Reproduction

```text
python3 skills/sdd-workflow/scripts/sdd.py --json --version
python3 -m unittest discover -s tests -p 'test_*.py' -v
scripts/run-runtime-conformance
scripts/run-conformance-kit --json
scripts/run-adapter-conformance --json
scripts/run-recovery-drills
python3 tests/package_validation.py
python3 tests/docs_consistency.py
sh tests/trigger-contract.sh
python3 tests/install_smoke.py --expect-platform macos
python3 tests/full_lifecycle_smoke.py
python3 examples/sample-web-api/run-walkthrough.py
python3 examples/compositions/security-review/run-smoke.py
```

Raw Agent runs remain ignored and retention-limited. Only aggregate,
publication-reviewed reports are committed.
