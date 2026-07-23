# Installation methods and package loading

Status: v0.8 portable-runtime channel matrix, checked 2026-07-23

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
| Codex | Current user Skills live under `~/.agents/skills`; repository Skills use `.agents/skills`. Codex follows symlinked Skill directories. | Complete copy, the built-in Skill installer, or complete directory symlink is supported. |
| Legacy Codex | Earlier repository guidance used `~/.codex/skills`. | The package remains runnable there, but current host loading is not guaranteed. Move/reinstall it into a current native root and verify in Codex. |
| Manual copy | Copy the complete directory into a host-native Skill root. | Supported; partial copies are rejected. |
| Native installer | An installer may select the native destination and copy the complete directory. | Supported when the installed bytes pass discovery/handshake. Installer provenance remains `unknown` unless independently recorded. |
| Third-party installer | A manager may place a complete package in a shared Agent Skills directory. | Conditional: validate package discovery, then separately prove the target host scans that directory. |
| Development link | `scripts/link-dev.sh` links the complete source directory into explicitly selected Claude/Codex roots. | Development-only; collision-safe linking and unlinking are tested. |

Current location and live-reload semantics were checked against the
[Claude Code Skills documentation](https://code.claude.com/docs/en/slash-commands)
and the [OpenAI Codex Skills manual](https://learn.chatgpt.com/docs/build-skills).
The third-party layout claim is limited to the package manager's own
[`npx skills` documentation](https://www.skills.sh/docs/cli); it is not treated
as evidence that a particular host scans the resulting directory.

## Legacy and incomplete layouts

`SKILL.md`-only copies predate the bundled runtime contract and are not
portable. Runtime-only copies are also invalid because the semantic adapter and
runtime cannot be upgraded independently. Discovery fails closed when the
identity manifest, runtime, required capabilities, or pinned Skill hash is
missing or inconsistent.

The old `~/.codex/skills` path is a migration source, not a second current
Codex destination. No runtime code scans it or silently falls back to it.

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
