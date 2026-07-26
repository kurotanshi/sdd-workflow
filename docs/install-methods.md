# Install, update, and remove the Skill

Install the complete `skills/sdd-workflow/` directory. A `SKILL.md`-only copy
is incomplete because the bundled scripts and references are part of the
Skill.

## Codex

Ask the built-in installer to use the current user Skill root:

```text
$skill-installer install skills/sdd-workflow from the GitHub repo kurotanshi/sdd-workflow into ~/.agents/skills
```

The expected result is `~/.agents/skills/sdd-workflow/`. If Codex does not load
it on the next turn, restart Codex. An older copy under `~/.codex/skills/` does
not prove that the current host loaded it.

## Claude Code

Ask Claude Code to copy the complete package:

```text
Install skills/sdd-workflow from https://github.com/kurotanshi/sdd-workflow into ~/.claude/skills/sdd-workflow
```

The expected result is `~/.claude/skills/sdd-workflow/`. Start a fresh session
if it does not appear.

## Manual copy

Copy the complete directory into an empty host-native Skill location. Do not
merge selected files into an existing installation. A third-party Skill
manager is usable only when it preserves the complete directory and the target
Agent actually scans its destination.

Repository contributors may use `scripts/link-dev.sh`; it is a development
tool, not the normal installation path.

## Verify

From the installed directory, run:

```text
python3 scripts/discover-runtime.py
python3 scripts/sdd.py --json --version
```

Discovery must report `ok: true`, source `package-local`, and distribution
`sdd-workflow`. The version command must return one successful JSON object.
Then start a fresh Agent session and explicitly invoke `$sdd-workflow` or
`/sdd-workflow`.

## Update

1. Stage the new complete package outside every Agent-scanned Skill root.
2. Verify the staged package.
3. Replace the installed directory as one unit; do not merge files from two
   releases.
4. Restart the Agent if needed and verify the loaded copy again.

## Remove

Identify the exact loaded `sdd-workflow/` directory, close sessions that may
still cache it, and remove only that directory. Repeat for each host where it
was installed.

Removing the Skill does not delete project `sdd/` artifacts, implementation
changes, or Git history. See [`troubleshooting.md`](./troubleshooting.md) when
the loaded path or package state is unclear.
