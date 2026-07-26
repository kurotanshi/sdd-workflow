# Team operation

Use one active operator for a proposal at a time. This is a cooperative rule:
the Skill rejects stale snapshots, but it does not provide a distributed lock.

## Parallel work

- Use a different proposal short name for each independent change.
- Use a separate Git worktree when implementation files may overlap.
- Never copy one active proposal directory between worktrees or merge
  `.sdd` machine metadata by hand.

## Handoff

The current operator stops mutation and reports:

- the proposal short name;
- the latest task completed and its validation result;
- any unresolved warning or diagnostic;
- the worktree containing the proposal and implementation.

The receiving operator opens that worktree and reruns the Skill's status
check. It must not reuse an old snapshot from the handoff message.

## Conflicts and archives

Resolve source-control conflicts before continuing proposal mutation. If two
worktrees contain different state for the same short name, stop and decide
which history is authoritative; do not combine their metadata.

Archive directories contain completed or abandoned proposal records.
`INDEX.md` is derived. If it is stale, preserve the archive directories and
let the bundled diagnostics validate and rebuild the index. Never append or merge index rows manually.

## Problem reports

Share only reviewed, de-identified evidence:

- Agent host, OS, Python version, and installed Skill path;
- proposal short name, command, stable error code/action, and whether a
  mutation reported success;
- latest validation result and relevant worktree layout.

Do not attach credentials, proprietary proposal text, complete metadata, or
full Agent transcripts by default. Maintainer test and evidence policy is
linked from [`CONTRIBUTING.md`](../CONTRIBUTING.md).
