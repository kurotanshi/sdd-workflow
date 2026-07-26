# Maintainer documentation map

The user journey lives in the root README. User-facing supporting documents
are limited to installation, team operation, and troubleshooting:

- [`install-methods.md`](./install-methods.md)
- [`team-operations.md`](./team-operations.md)
- [`troubleshooting.md`](./troubleshooting.md)

Everything else under `docs/` supports maintenance, regression, or historical
traceability for the installable Skill:

- [`concepts/`](./concepts/) — internal artifact and authority models
- [`operations/`](./operations/) — testing, evaluation, CI, and release work
- [`compatibility/`](./compatibility/) — package and format compatibility
- [`design/`](./design/) — runtime architecture and decisions

The project does not publish a protocol, adapter SDK, or third-party
conformance program. Protocol-era files and v1.0 reports remain reproducible
historical evidence, not current normative product contracts. Their exact
classification and retention reason are recorded in
[`public-surface-inventory.md`](./public-surface-inventory.md).
