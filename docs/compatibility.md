# Maintainer compatibility

Status: internal package and format support

The project communicates three version concepts outside the implementation:

| Public concept | Current support | Meaning |
| --- | --- | --- |
| Skill release | `v1.2.0` | Version of the installable Skill package |
| Proposal artifact schema | implicit/explicit `1`, explicit `2` | Format accepted for `proposal.md` and `tasks.md` |
| JSON output | `1` | Machine envelope emitted by the bundled CLI |

Discovery, handshake, snapshot, approval, attestation, archive, and manifest
versions may remain in machine data. They are internal compatibility details,
not independently released products or promises that users must compose.
Engine version is diagnostic package metadata and does not override proposal
schema or JSON output support.

Output version `1` permits the additive `after_state` and `next_task` command-data
fields on successful `approve` and `complete-task` results. Older consumers may
ignore them. They do not change mutation syntax, authority, error actions, or
snapshot/task-digest validation; newer consumers use the returned evidence as
the exact input to the next existing mutation.

## Environment support

| Axis | Supported | Conditional |
| --- | --- | --- |
| OS | macOS and Linux/Ubuntu | Windows is best effort through the Python entrypoint |
| Python | CPython 3.11 and current CI generations | A newer Python remains supported only while the suite passes |
| Agent host | Claude Code and Codex loading one complete Skill package | Other hosts require direct evidence that they load the complete directory |
| Proposal schema | implicit/explicit v1 and explicit v2 | readable legacy proposals may be read-only |

Model identity is an evaluation variable, not a runtime compatibility axis.
Agent host/model combinations are recorded in eval evidence and rerun when the
host changes materially.

## Complete-package rule

`SKILL.md`, bundled scripts, references, runtime identity, and host metadata
form one installable package. Partial copies, mixed releases, `PATH` fallback,
or selecting one of multiple distinct package candidates are unsupported.

Discovery failures stop before project mutation:

- `RUNTIME_NOT_FOUND`: reinstall or select the intended complete package;
- `RUNTIME_AMBIGUOUS`: remove the ambiguity instead of picking newest/first;
- `RUNTIME_HANDSHAKE_FAILED`: repair that exact package;
- `RUNTIME_INCOMPATIBLE` or `RUNTIME_SKILL_VERSION_SKEW`: replace the complete
  package rather than individual files.

See [`install-methods.md`](./install-methods.md) for user-facing package paths.

## Artifact handling

Read compatibility does not imply mutation compatibility. Unknown proposal
schema or machine metadata fails closed for the affected operation. Never
delete schema frontmatter or `.sdd` metadata to force an older interpretation.

Readable legacy proposals remain available to `status`, `list`, `validate`,
`abandon-preflight`, and `doctor`, including their existing format warnings.
They are not mutation-compatible: `approve`, `begin-revision`,
`complete-task`, `archive`, and `abandon` fail without writing, using
`ERROR_LEGACY_MUTATION_UNSUPPORTED` and action
`upgrade_or_recreate_proposal`. A successful read result is never evidence that
a requested lifecycle transition completed.

An upgrade replaces one complete Skill package. Existing project proposals
remain in place and are inspected with the new package before mutation. If a
downgrade is required, use a package that explicitly supports every artifact
present; otherwise finish or abandon the proposal with a compatible package
first.

The old multi-axis version/deprecation, migration, and rollback documents are
retained only as v1.0 release evidence. They are indexed in
[`public-surface-inventory.md`](./public-surface-inventory.md) and do not define
current public policy.

## Problem reports

Include the Skill release, proposal schema when known, JSON output version,
Agent host, OS, Python version, installed path, command, stable error
code/action, and reviewed diagnostic output. Do not attach proprietary
proposal content, machine metadata, or full transcripts by default.
