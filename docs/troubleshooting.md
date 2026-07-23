# Portable runtime troubleshooting

Status: v0.8 distribution and discovery guide

Always diagnose the exact package selected by the Agent. Do not run an `sdd`
found on `PATH`, copy a runtime between Skill directories, or delete proposal
metadata to make an older runtime accept it.

## First checks

Run these commands from the installed Skill directory:

```text
python3 <installed-skill>/scripts/discover-runtime.py
python3 <installed-skill>/scripts/sdd.py --json --handshake
python3 <installed-skill>/scripts/sdd.py --root <project> --json doctor
```

The discovery result and handshake must identify the same `sdd-workflow`
package, compatible `0.6` engine generation, schema interval `1..2`, and all
required capabilities. `doctor` reports values it cannot prove as `unknown`.

## Discovery failures

| Code | Meaning | Remediation |
| --- | --- | --- |
| `RUNTIME_NOT_FOUND` | The selected source has no regular `sdd.py`. | Reinstall the complete directory or correct one explicit absolute pin. |
| `RUNTIME_AMBIGUOUS` | One explicit source names multiple distinct runtime files. | Remove the ambiguity; never select first, newest, or highest version. |
| `RUNTIME_HANDSHAKE_FAILED` | The candidate did not return one successful JSON handshake. | Repair or reinstall that exact package; do not try PATH fallback. |
| `RUNTIME_INCOMPATIBLE` | Distribution, output/handshake version, engine generation, schema interval, capability set, identity manifest, or Skill hash does not match. | Replace the complete distribution as one unit. |
| `RUNTIME_SKILL_VERSION_SKEW` | `doctor` observed Skill bytes that differ from the package identity manifest. | Reinstall the complete distribution; do not overwrite only one file. |

## Host loads the wrong or no Skill

1. Compare the host-reported `SKILL.md` path with
   [`install-methods.md`](./install-methods.md).
2. For current Codex local discovery, use a user or repo `.agents/skills`
   root. Treat an old `.codex/skills` copy as migration-only.
3. For Claude Code, use `~/.claude/skills` or a project `.claude/skills`
   root.
4. A third-party installer proves only its installed layout. Confirm the host
   actually scans that destination.
5. Remove or migrate stale same-name copies instead of relying on precedence.
   Then refresh/restart the host when its own documentation requires it.

## Project command fails after handshake

A successful handshake proves only distribution compatibility. Follow the
command's stable `errors[].action` for project schema, approval, snapshot,
metadata, archive, or INDEX failures. Do not treat engine version, Agent model,
file timestamps, or a fresh `status` as authority to bypass a narrower
artifact gate.
