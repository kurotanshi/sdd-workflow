# Installation methods and package loading

Status: v1.0 installation contract, checked 2026-07-24

The supported unit is the complete `sdd-workflow/` directory. A channel is
runtime-compatible only when `SKILL.md`, `runtime-identity.json`, host metadata,
and all scripts remain together. Host discovery and package integrity are
separate gates: a complete copy in a directory the host does not scan is not
an installed Skill.

The machine-readable contract is
[`conformance/install-channels-v1.json`](../conformance/install-channels-v1.json).

## Current host paths

| Channel | Current loading contract | SDD support |
| --- | --- | --- |
| Claude Code | Personal Skills live under `~/.claude/skills/<name>/`; project Skills live under `.claude/skills/<name>/`. Supporting files may live beside `SKILL.md`. | Complete copy or complete directory symlink is supported. |
| Codex | Current user Skills live under `~/.agents/skills`; repository Skills use `.agents/skills`. Codex follows symlinked Skill directories. | Complete copy, built-in Skill installer with an explicit native destination, or complete directory symlink is supported. |
| Legacy Codex | Earlier repository guidance used `~/.codex/skills`. | The package remains runnable there, but current host loading is not guaranteed. Move/reinstall it into a current native root and verify in Codex. |
| Manual copy | Copy the complete directory into a host-native Skill root. | Supported; partial copies are rejected. |
| Native installer | An installer may select the native destination and copy the complete directory. | Supported when the installed bytes pass discovery/handshake. Installer provenance remains `unknown` unless independently recorded. |
| Third-party installer | A manager may place a complete package in a shared Agent Skills directory. | Conditional: validate package discovery, then separately prove the target host scans that directory. |
| Development link | `scripts/link-dev.sh` links the complete source directory into explicitly selected Claude/Codex roots. | Development-only; collision-safe linking and unlinking are tested. |

Current location and live-reload semantics were checked against the
[Claude Code Skills documentation](https://code.claude.com/docs/en/skills)
and the [OpenAI Codex Skills manual](https://learn.chatgpt.com/docs/build-skills).
The third-party layout claim is limited to the package manager's own
[`npx skills` documentation](https://www.skills.sh/docs/cli); it is not treated
as evidence that a particular host scans the resulting directory.

## Recommended installation

For Codex, ask the built-in installer to copy the repository subdirectory into
the current user Skill root explicitly:

```text
$skill-installer install skills/sdd-workflow from the GitHub repo kurotanshi/sdd-workflow into ~/.agents/skills
```

Do not infer host loading from a successful download alone. Some bundled
installer generations still default to `$CODEX_HOME/skills` (normally
`~/.codex/skills`), while the current Codex user loading contract is
`~/.agents/skills`. Confirm the resulting directory and loaded `SKILL.md`.

For Claude Code, request the complete package at its personal Skill root:

```text
Install skills/sdd-workflow from https://github.com/kurotanshi/sdd-workflow into ~/.claude/skills/sdd-workflow
```

Both hosts normally detect Skill additions and `SKILL.md` changes
automatically. Restart the host when the Skill does not appear; a newly created
top-level Claude Code Skills directory may require a new session before it is
watched.

For a manual installation, download or clone a release, then copy the complete
`skills/sdd-workflow/` directory into an empty host-native destination. Never
merge individual files into an existing installation. A third-party manager is
acceptable only when it preserves the complete directory and the target host is
separately shown to scan its destination.

## Legacy and incomplete layouts

`SKILL.md`-only copies predate the bundled runtime contract and are not
portable. Runtime-only copies are also invalid because the semantic adapter and
runtime cannot be upgraded independently. Discovery fails closed when the
identity manifest, runtime, required capabilities, or pinned Skill hash is
missing or inconsistent.

The old `~/.codex/skills` path is a migration source, not a second current
Codex destination. No runtime code scans it or silently falls back to it.

## Updates and removal

Treat an update as complete-package replacement:

1. Obtain the new package in a separate staging directory.
2. Run the discovery and handshake checks below against the staged package.
3. Preserve or remove the old package as one complete directory; do not merge
   releases or overwrite selected files.
4. Put the new complete directory at the same host-native destination.
5. Confirm the host loaded that exact `SKILL.md`, then run the checks again.

An installer may refuse to update when the destination already exists. That is
a collision guard, not permission to merge package contents. If rollback may
be needed, keep the old complete package outside every host-scanned Skill root
and follow [`rollback-v1.md`](./rollback-v1.md).

To remove the Skill, first identify the exact loaded directory, close sessions
that may still hold its instructions, and remove only that complete
`sdd-workflow/` directory. Repeat for each host root where it was installed.
Removal does not delete project `sdd/` artifacts, implementation changes, or
Git history.

## Verification

For the installed package selected by the host:

```text
python3 <installed-skill>/scripts/discover-runtime.py
python3 <installed-skill>/scripts/sdd.py --json --handshake
```

Both results must identify `sdd-workflow`, engine generation `1.0`, handshake
version `1`, schema range `1..2`, and all required capabilities. Then invoke
the Skill in the host and confirm the loaded `SKILL.md` path is the same
package. A package handshake alone cannot prove host loading.
