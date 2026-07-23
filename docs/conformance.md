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
- `conformance/kit-manifest-v1.json` packages the public rule registry,
  reference manifest, fixture manifests, expected envelopes, reference
  runtime, and implementation-neutral runner.
- `conformance/expected-envelopes-v1.json` expresses stable expected fields as
  JSON Pointer assertions. It deliberately does not require diagnostic message
  prose or JSON object key order to match.
- `scripts/run-conformance-kit` runs those public cases against the reference
  runtime or a candidate selected with `--runtime`.

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

## Public implementation-neutral kit

An adapter or runtime author can inspect the versioned inventory and exercise
the reference runtime without starting an Agent:

```text
scripts/run-conformance-kit --list --json
scripts/run-conformance-kit --json
```

To evaluate another executable implementation:

```text
scripts/run-conformance-kit --runtime /absolute/path/to/sdd-runtime --json
```

Python candidates may be passed as a `.py` file and are invoked with the
current Python interpreter; any other candidate must be executable. Each case
runs in a fresh temporary project populated from a declared fixture. The
runner requires the expected exit class, exactly one JSON document on stdout,
empty stderr in JSON mode, and every versioned JSON Pointer assertion.

The public envelope cases cover version negotiation, deterministic status,
unsafe identity rejection, unknown-schema fail-closed behavior, and invalid
invocation. The reference-runtime manifest remains the deeper executable
evidence for transaction, recovery, archive, concurrency, packaging, and
documentation rules. Passing either suite does not add a supported Agent host
or installation channel.
