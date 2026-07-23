# Test responsibility map

Status: v0.6 release-baseline classification

This document classifies the current flat `tests/` layout by primary
responsibility. A test may exercise adjacent layers, but it has one primary
category here so release and conformance failures can be routed consistently.
The files do not need to move into category directories.

| Category | Primary responsibility | Current unittest modules |
| --- | --- | --- |
| `unit` | Version-independent models, scanners, snapshot primitives, deterministic ordering, and summary transport | `test_model.py`, `test_scanner.py`, `test_snapshot.py`, `test_ordering.py`, `test_summary_input.py` |
| `parser` | Proposal discovery, legacy/v1/v2 parsing, canonical projection, and schema diagnostics | `test_parser.py`, `test_schema_v2.py`, `test_discovery.py` |
| `transition` | Approval, revision, task completion, and abandonment preflight rules before terminal commit | `test_approval.py`, `test_complete_task.py`, `test_preflight.py` |
| `transaction` | Atomic replacement, staged operation evidence, terminal commit points, partial failure, and safe retry | `test_atomic_write.py`, `test_transition_failures.py`, `test_terminal_validation.py` |
| `compatibility` | Engine/artifact version axes, legacy archive adaptation, and unknown-version behavior | `test_compatibility.py`, `test_archive_model.py` |
| `concurrency` | Stale snapshot rejection and concurrent archive/INDEX convergence | `test_concurrency.py` |
| `packaging` | Runtime launch/discovery, installed channel layouts, release baseline, CI shape, and classification contract | `test_runtime.py`, `test_runtime_discovery.py`, `test_install_channels.py`, `test_install_smoke.py`, `test_ci_contract.py`, `test_release_baseline.py`, `test_testing_contract.py` |
| `integration` | Public CLI envelopes, Agent-eval fixtures/runner/scorer/usage/publication checks and conformance contracts, quickstart/docs navigation, first-workflow usability and sample-repository walkthroughs, composition examples, Skill reduction and opt-in team evidence, and end-to-end archive, doctor, and team workflow behavior | `test_agent_eval_spec.py`, `test_agent_eval_runner.py`, `test_agent_eval_scoring.py`, `test_agent_eval_usage.py`, `test_agent_scenarios.py`, `test_adapter_contract.py`, `test_public_eval_report.py`, `test_cli.py`, `test_cli_snapshots.py`, `test_conformance_manifest.py`, `test_conformance_kit.py`, `test_composition_example.py`, `test_first_workflow_usability.py`, `test_hermetic_adapter.py`, `test_protocol_draft.py`, `test_quickstart_docs.py`, `test_sample_web_api.py`, `test_skill_reduction.py`, `test_team_evidence_contract.py`, `test_runtime_conformance.py`, `test_archive_cli.py`, `test_doctor.py`, `test_team_workflow.py` |

## Supporting contract checks and tools

| Responsibility | Files |
| --- | --- |
| Installed-package and layout smoke | `install_smoke.py`, `package_validation.py` |
| Clean install-to-uninstall lifecycle | `full_lifecycle_smoke.py` |
| Documentation and trigger consistency | `docs_consistency.py`, `trigger-contract.sh` |
| Fixture maintenance | `dump_fixture_models.py`, `fixtures/` |

## Release routing

- The `unit` required check runs the complete `test_*.py` suite on Ubuntu and
  macOS for the minimum and current Python generations.
- The `fixtures` check gives parser/schema/archive fixture failures a stable,
  independently required signal.
- `package-validation`, `docs-consistency`, and `install-smoke` retain their
  dedicated required check names.
- Later protocol conformance manifests should reference these modules and
  individual test IDs; they should not copy the same tests into a second tree.

The workflow and action runtime policy are documented in
[`ci.md`](./ci.md).
