# Team operation contract

Status: v0.6 team-readiness contract

## Cooperative coordination

One proposal has exactly one active agent/operator at a time. Snapshot CAS catches stale inputs but is not a lease, lock, or proof that another process is absent. Do not run two mutating commands for the same short name concurrently.

Parallel work uses both:

- a different short name for each independently scoped change; and
- a separate Git worktree for each agent when implementation files may overlap or working-tree isolation matters.

Before handing a proposal to another agent, the current owner stops all commands and reports the exact short name, `sdd.py --json --version` envelope, latest successful `status` snapshot, last completed task, validation result, and any doctor finding. The receiving owner reruns `status`; it never reuses the handed-off snapshot for mutation.

Do not copy an active proposal directory between worktrees, share one uncommitted `.sdd` envelope, or merge two versions of machine metadata by hand. Resolve source-control conflicts first, then rerun `status`/`doctor`. Machine metadata is an artifact, not a distributed coordination protocol.

## Presentation-only ownership

A team may coordinate in an external issue or handoff note, but the current
protocol has no owner field. A future versioned owner label would be
presentation-only unless a separately approved contract says otherwise: it
does not grant mutation authority, block a transition, prove exclusive use,
or replace a fresh status check.

Do not add an unversioned owner key to proposal or machine artifacts. Any
ownership extension requires a separate SDD proposal defining authority,
approval projection, unknown-version behavior, migration, and removal.

## Locking and leases

v0.10 does not implement a lock or lease. It has no timeout, heartbeat,
owner-death detection, remote coordinator, or stale-lease recovery. Snapshot
CAS rejects stale caller context but does not serialize callers that both
validated before either write.

The quantified decision is
[`decisions/2026-07-23-v010-lock-lease.md`](./decisions/2026-07-23-v010-lock-lease.md).
Until a separate approved proposal meets that gate, keep the cooperative
one-operator boundary and use distinct proposals/worktrees for parallel work.

## Worktrees and engine generation

Run the Skill and CLI from the intended worktree. Explicit `--root` is preferred for automation; otherwise discovery uses that worktree's Git root before upward search. Every agent operating one repository must use an engine that supports the proposal schema and every machine-envelope version present.

Different worktrees may carry different package installations only when their engine generations and artifact formats are compatible. A newer writer string is diagnostic evidence, not proof of incompatibility; use `doctor` and the matrix in [`compatibility.md`](./compatibility.md). Never resolve skew by deleting `.sdd` or schema frontmatter.

## Archive and derived INDEX

Archive directories are authoritative. `INDEX.md` is derived and may be temporarily stale after concurrent terminal work or source-control merges. Never merge or append INDEX rows manually:

1. preserve every non-colliding archive directory;
2. resolve any same-destination collision with human ownership/history evidence;
3. run `validate-index`;
4. run `rebuild-index` only when every archive record adapts without unknown/ambiguous diagnostics; and
5. rerun `doctor`.

A stale but rebuildable INDEX does not justify a global lock. Lock or INDEX CAS requires the contention evidence and decision in `docs/decisions/2026-07-22-team-readiness-entry.md`.

## Problem report checklist

Provide only reviewed, de-identified evidence:

- CLI JSON version envelope, OS, Python version, and installation path kind (Claude, Codex, dev link, or release package);
- command name, stable code/action, and whether the operation reported committed;
- proposal schema and machine-envelope versions;
- `doctor --json` and `validate-index --json` findings;
- worktree layout, short names involved, and whether ownership overlapped.

Do not attach credentials, proprietary proposal text, full metadata, or complete agent transcripts by default.

Aggregate team trials follow the opt-in, numerator/denominator, and retention
contract in [`team-evidence.md`](./team-evidence.md). Runtime and Skill use
does not enable collection automatically.
