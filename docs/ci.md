# CI and action runtime policy

Status: v0.6 release-baseline policy

## Action runtime baseline

Repository workflows use:

- `actions/checkout@v6`
- `actions/setup-python@v6`

Both supported majors run on Node 24. A self-hosted runner must be GitHub Actions
Runner `v2.327.1` or newer. `actions/checkout@v6` additionally requires runner
`v2.329.0` or newer when authenticated Git commands run from a Docker container
action. GitHub-hosted runners are expected to satisfy these prerequisites; any
self-hosted runner owner must verify them before enabling this workflow.

The runner requirements come from the official
[`actions/checkout`](https://github.com/actions/checkout) and
[`actions/setup-python`](https://github.com/actions/setup-python) release
contracts.

## Pinning and updates

- First-party `actions/*` dependencies are pinned to supported major tags. This
  allows reviewed patch delivery within the selected compatibility generation
  while keeping the Node runtime boundary explicit.
- A major-tag change requires review of the action release notes, Node runtime,
  minimum runner version, permissions, and the complete Ubuntu/macOS test and
  install matrices.
- A future third-party action must be pinned to a full commit SHA after its
  source and permissions are reviewed. Floating branches and unversioned
  references are not allowed.
- `tests/test_ci_contract.py` fixes the selected majors and runner-policy facts.
  Intentional changes update the workflow, this policy, and the regression test
  together.

## Supported CI matrix

The release baseline exercises Ubuntu and macOS with CPython 3.11 and the
current `3.x` tool-cache release. The stable required check names remain
`unit`, `fixtures`, `package-validation`, `docs-consistency`, and
`install-smoke`.

The test environment must provide a `git` executable. The team-workflow
integration tests create temporary repositories and commits; a minimal Linux
container therefore needs Git installed before running the suite. GitHub-hosted
Ubuntu and macOS images provide it by default.

## 2026-07-23 local parity evidence

The v0.6 baseline work was reproduced on both supported operating-system
families before publishing the workflow change:

| Environment | Python | Validation |
| --- | --- | --- |
| macOS 15.7.3 arm64 | 3.11.15 | 128 unit/integration tests, package validation, docs consistency, trigger contract, and install smoke passed |
| macOS 15.7.3 arm64 | 3.13.0 | 128 unit/integration tests, package validation, docs consistency, trigger contract, and install smoke passed |
| `python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93` arm64, with Git installed | 3.11 | Same validation set passed |
| `python:3.13-slim@sha256:6771159cd4fa5d9bba1258caf0b82e6b73458c694d178ad97c5e925c2d0e1a91` arm64, with Git installed | 3.13 | Same validation set passed |

This local evidence establishes macOS/Linux behavior parity. It does not replace
the required GitHub-hosted run: the updated workflow must still complete there
without a runtime-deprecation annotation before the release-baseline task is
closed.

## GitHub-hosted release gate

The hosted evidence is valid only when all of the following are recorded
together:

1. The workflow run URL, run ID, event, head branch, and exact head SHA.
2. The workflow at that head SHA uses `actions/checkout@v6` and
   `actions/setup-python@v6`; a green run from an earlier action generation is
   not reusable.
3. Every Ubuntu/macOS and Python 3.11/3.x matrix cell succeeds, together with
   the five stable required checks.
4. The run summary, annotations, and action setup logs contain no Node runtime
   deprecation warning.

Record that evidence in the release handoff before completing the SDD task. If
the workflow is tested on a temporary branch, keep its exact run URL so the
result remains auditable after the branch is removed.
