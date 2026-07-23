# Runtime conformance

Status: manifest and runner contract version 1

Runtime conformance is a deterministic reference-runtime gate. It is separate
from Agent evaluation: a runtime case executes repository tests or a contract
check and reports the protocol rules for which that case provides evidence.

## Versioned inputs

- `conformance/protocol-rules-v1.json` is the rule registry.
- `conformance/runtime-manifest-v1.json` maps executable cases to registered
  rules without copying existing tests into another tree.
- `scripts/run-runtime-conformance` executes manifest version 1 and emits
  output version 1.

Every `tests/test_*.py` module must appear in at least one manifest case, and
every registered rule must have at least one executable case. The manifest
also includes package validation, documentation consistency, trigger-contract,
and install-smoke commands. Command cases may use `{python}` and `{platform}`;
the runner resolves the latter only to the supported `macos` or `linux`
contract value.

## Usage

Run the complete manifest:

```text
scripts/run-runtime-conformance
```

List cases or produce one machine-readable result:

```text
scripts/run-runtime-conformance --list --json
scripts/run-runtime-conformance --json
```

Rerun only cases affected by a protocol rule or an exact case:

```text
scripts/run-runtime-conformance --rule SDD-APPROVAL-001
scripts/run-runtime-conformance --case archive.authority
```

`--rule` and `--case` are repeatable; when combined, their filters intersect.
Exit `0` means every selected case passed, exit `1` means at least one selected
case failed, and exit `2` means the manifest, selection, or invocation was
invalid. Each result names its case and rules, so a failure identifies the
affected contract directly.
