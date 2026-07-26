# Public surface inventory

Status: complete
Baseline date: 2026-07-24

## Entry evidence and guardrails

Gate 0 is complete. [`cost-benefit.md`](./cost-benefit.md) records 36/36 valid
measured runs against frozen source commit
`21fb26bc329743202a19bdd969e049b04c2481c2`, the pre-registered thresholds,
the corrected safety audit, and the Gate 2 eligibility decision. The focused
experiment tests and the full 249-test suite passed after collection.

This positioning stage may change documentation, navigation, release
communication, and tests that enforce those public statements. It must not
change:

- `skills/sdd-workflow/` behavior or bundled runtime mechanics;
- proposal schema or JSON output behavior;
- the frozen Gate 0 spec, fixtures, runner, raw results, or conclusions; or
- existing Agent scenario behavior.

Any runtime simplification is reserved for the separate Gate 2 decision and a
candidate-specific proposal.

## Baseline inventory

The inventory below is exhaustive for the documentation and contract surface
at the Gate 1 baseline. The sets do not overlap.

### Root documents

- User and repository entry files: `README.md`, `README.en.md`, `LICENSE`,
  `CHANGELOG.md`.
- Contributor and Agent context: `CONTRIBUTING.md`, `CONTRIBUTING.en.md`,
  `CLAUDE.md`.
- Planning input: `ROADMAP.md`.

### Documentation

- Root-level docs: `README.md`, `adapter-authoring-guide.md`, `agent-eval.md`,
  `approval-manifest.md`, `architecture.md`, `archive-model.md`, `ci.md`,
  `cli-contract.md`, `compatibility.md`, `conformance.md`, `cost-benefit.md`,
  `doctor-diagnostics.md`, `friction-log.md`, `install-methods.md`,
  `managed-state.md`, `migration-v1.md`, `non-goals-v1.md`,
  `protocol-draft.md`, `public-surface-inventory.md`, `recovery-drills.md`,
  `release-baseline-v0.6.md`, `release-baseline-v1.0.md`,
  `release-checklist.md`, `rollback-v1.md`, `runtime.md`, `schema-v2.md`,
  `security-trust-model.md`, `team-evidence.md`, `team-operations.md`,
  `testing.md`, `transaction-protocol.md`, and `troubleshooting.md`.
- Category indexes: `compatibility/README.md`, `concepts/README.md`,
  `design/README.md`, `operations/README.md`, `troubleshooting/README.md`.
- Frozen protocol-era contracts: `protocol/agent-adapter-contract.md`,
  `protocol/core-v1.md`, `protocol/runtime-cli-v1.md`, and
  `protocol/versioning-policy-v1.md`.
- Decision records: the nine files in `decisions/`, including `TEMPLATE.md`.
- Historical reports: `reports/v0.10-controlled-team-trial.md`,
  `reports/v1.0-conformance.md`, and `reports/v1.0-release-gate.md`.
- Usability evidence: `usability/first-workflow-15-minute.md`.

This accounts for all 54 Markdown files under `docs/` at baseline.

### Contract and regression artifacts

The seven files under `conformance/` are
`adapter-scenarios-v1.json`, `expected-envelopes-v1.json`,
`hermetic_adapter.py`, `install-channels-v1.json`,
`kit-manifest-v1.json`, `protocol-rules-v1.json`, and
`runtime-manifest-v1.json`.

Related executable entrypoints are `scripts/run-adapter-conformance`,
`scripts/run-conformance-kit`, and `scripts/run-runtime-conformance`.
Release and validation entrypoints include `scripts/build-release-package.py`,
`scripts/run-recovery-drills`, the `.github/workflows/` definitions, and the
repository validation scripts under `tests/`.

### Version and release concepts found

The public and maintainer surface currently names all of the following as
independent concepts:

- repository/Skill release (`v1.0.1`);
- engine/runtime version and engine generation;
- frozen protocol identifier (`sdd-protocol-1.0`);
- proposal schema version/range;
- CLI JSON output version;
- handshake, discovery, snapshot, approval, archive, terminal, canonical
  model, managed attestation, and adapter contract versions;
- conformance registry, kit, scenario, expectation, install-matrix, and
  manifest versions.

Release identity is repeated across both READMEs, `CHANGELOG.md`, compatibility
and release-baseline docs, protocol contracts, runtime identity, conformance
manifests, trigger/docs checks, package tests, and release reports.

### Linked enforcement

| Surface | Direct enforcement or consumer |
| --- | --- |
| README pair and navigation | `tests/test_quickstart_docs.py`, `tests/docs_consistency.py`, `tests/trigger-contract.sh` |
| Contributor/CI statements | `tests/test_ci_contract.py`, `tests/docs_consistency.py`, `.github/workflows/ci.yml` |
| Protocol and runtime contracts | `tests/test_protocol_draft.py`, `tests/test_runtime.py`, `tests/test_adapter_contract.py`, `tests/test_compatibility.py` |
| Conformance registry/manifests | `tests/test_conformance_manifest.py`, `tests/test_conformance_kit.py`, `tests/test_runtime_conformance.py`, `tests/test_hermetic_adapter.py`, `tests/test_agent_scenarios.py` |
| Release/version statements | `tests/test_release_baseline.py`, `tests/test_install_channels.py`, `tests/install_smoke.py`, `tests/package_validation.py`, `tests/docs_consistency.py`, `tests/trigger-contract.sh` |
| Recovery/team evidence | `tests/test_recovery_drills.py`, `tests/test_recovery_drill_runner.py`, `tests/test_team_evidence_contract.py`, `tests/test_team_lock_decision.py`, `tests/test_team_workflow.py` |
| Eval and usability records | Agent-eval test modules, `tests/test_first_workflow_usability.py`, and `tests/test_cost_benefit_experiment.py` |

No item is removed or reclassified by this inventory step.

## Necessity classification

Each baseline item belongs to exactly one class:

- **user-required**: needed to install, decide whether to use, operate, or
  troubleshoot the Skill;
- **maintainer-required**: needed to build, test, release, diagnose, or safely
  change the Skill package, but not part of the user journey;
- **historical evidence**: retained for traceability or regression provenance;
  it is not a normative public contract and must not be linked as current
  product guidance.

### Root classification

| Class | Paths |
| --- | --- |
| user-required | `README.md`, `README.en.md`, `LICENSE`, `CHANGELOG.md` |
| maintainer-required | `CONTRIBUTING.md`, `CONTRIBUTING.en.md`, `CLAUDE.md` |
| historical evidence | `ROADMAP.md` |

### Documentation classification

| Class | Paths |
| --- | --- |
| user-required | `install-methods.md`, `team-operations.md`, `troubleshooting.md`, `troubleshooting/README.md` |
| maintainer-required | `README.md`, `agent-eval.md`, `approval-manifest.md`, `architecture.md`, `archive-model.md`, `ci.md`, `cli-contract.md`, `compatibility.md`, `cost-benefit.md`, `doctor-diagnostics.md`, `managed-state.md`, `public-surface-inventory.md`, `recovery-drills.md`, `release-checklist.md`, `runtime.md`, `schema-v2.md`, `security-trust-model.md`, `team-evidence.md`, `testing.md`, `transaction-protocol.md`, `usability/first-workflow-15-minute.md`, `compatibility/README.md`, `concepts/README.md`, `design/README.md`, `operations/README.md` |
| historical evidence | `adapter-authoring-guide.md`, `conformance.md`, `friction-log.md`, `migration-v1.md`, `non-goals-v1.md`, `protocol-draft.md`, `release-baseline-v0.6.md`, `release-baseline-v1.0.md`, `rollback-v1.md`, all four files in `protocol/`, all nine files in `decisions/`, and all three files in `reports/` |

The three documentation rows contain 4, 25, and 25 files respectively, for
the complete 54-file baseline.

### Contract, regression, and release classification

| Class | Paths |
| --- | --- |
| maintainer-required | `conformance/adapter-scenarios-v1.json`, `conformance/expected-envelopes-v1.json`, `conformance/hermetic_adapter.py`, `conformance/install-channels-v1.json`, `conformance/runtime-manifest-v1.json`, `scripts/run-adapter-conformance`, `scripts/run-runtime-conformance`, `scripts/build-release-package.py`, `.github/workflows/`, and their tests |
| historical evidence | `conformance/kit-manifest-v1.json`, `conformance/protocol-rules-v1.json`, and `scripts/run-conformance-kit` |

The historical registry and kit remain available to reproduce the v1.0
release evidence. Internal regression consumers may read them, but the project
does not invite independent implementations to claim current protocol
conformance.

## Baseline counts

Counts are fixed before changing the READMEs.

A **public product commitment** is an independently advertised, versioned, or
compatibility-governed surface that a user or third-party implementer could
reasonably expect this repository to support. Repeated mentions of the same
surface count once. The baseline has **9**:

1. installable Skill and repository release;
2. frozen core protocol;
3. runtime/CLI protocol contract;
4. Agent adapter contract;
5. independent public conformance kit;
6. proposal artifact schema;
7. JSON output envelope;
8. multi-axis protocol compatibility/deprecation policy;
9. protocol migration and rollback policy.

A **synchronization-bearing source** is a file currently presented or enforced
as a source of truth for at least one of those commitments. Generated raw run
artifacts and historical reports are excluded. The baseline has **21**:

- `skills/sdd-workflow/SKILL.md` and
  `skills/sdd-workflow/runtime-identity.json`;
- `README.md`, `README.en.md`, and `CHANGELOG.md`;
- `docs/README.md`, `docs/protocol-draft.md`, all four files in
  `docs/protocol/`, `docs/compatibility.md`, `docs/schema-v2.md`,
  `docs/cli-contract.md`, `docs/release-baseline-v1.0.md`, and
  `docs/conformance.md`;
- `conformance/protocol-rules-v1.json`,
  `conformance/runtime-manifest-v1.json`, and
  `conformance/kit-manifest-v1.json`;
- `tests/docs_consistency.py` and `tests/trigger-contract.sh`.

Gate 1 succeeds only if the final public commitment count is lower than 9 and
the synchronization-bearing source count is lower than 21. Reclassifying or
renaming a file without removing its current normative obligation does not
reduce either count.

## Version and retention decision

Current external communication is limited to:

1. the installable Skill release;
2. proposal artifact schema compatibility; and
3. bundled CLI JSON output compatibility.

Runtime engine, discovery, handshake, snapshot, approval, attestation, archive,
terminal, adapter, registry, and manifest versions remain implementation
metadata where the current code needs them. They are not separate release
tracks and are not linked from the user journey.

No historical document, regression fixture, runner, or test was deleted in
Gate 1. The old protocol, adapter, versioning, and conformance sources contain
unique v1.0 evidence and are still consumed by regression tests. Their public
normative obligation was removed by:

- removing them from README and user-support navigation;
- marking their documents as frozen historical evidence;
- describing conformance assets as internal regression/reproduction inputs;
  and
- changing tests that called them current public contracts into frozen-evidence
  checks.

This preserves executable safety evidence without treating its directory or
version names as current products.

## Final counts and validation

Using the baseline definitions above:

| Measure | Before | After | Change |
| --- | ---: | ---: | ---: |
| Public product commitments | 9 | 3 | -6 (-66.7%) |
| Synchronization-bearing sources | 21 | 14 | -7 (-33.3%) |

The 14 remaining synchronization-bearing sources are:

- `skills/sdd-workflow/SKILL.md` and
  `skills/sdd-workflow/runtime-identity.json`;
- `README.md`, `README.en.md`, and `CHANGELOG.md`;
- `CONTRIBUTING.md` and `CONTRIBUTING.en.md`;
- `docs/README.md`, `docs/public-surface-inventory.md`,
  `docs/compatibility.md`, `docs/schema-v2.md`, and `docs/cli-contract.md`;
- `tests/docs_consistency.py` and `tests/trigger-contract.sh`.

The count includes the new contributor scope and this decision record rather
than hiding newly created synchronization obligations. Historical protocol,
adapter, release-policy, and conformance files no longer count because they
are explicitly non-normative, absent from the user journey, and tested only as
frozen evidence.

Validation completed on 2026-07-24:

- all repository-local Markdown links checked in the user and maintainer
  documentation set;
- `docs-consistency` and `trigger-contract` passed;
- all 249 unittest cases passed;
- package validation, macOS install smoke, and full lifecycle smoke passed;
- `skills/sdd-workflow/` has no worktree diff; and
- the Gate 0 experiment spec, runner, entrypoint, and fixture identities remain
  frozen.

No Skill rule, runtime mechanic, proposal schema, JSON behavior, or existing
Agent scenario was changed in Gate 1.
