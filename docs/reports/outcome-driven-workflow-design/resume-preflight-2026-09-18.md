# Pilot resumption preflight — 2026-09-18

Historical setup snapshot. The user subsequently authorized reconstruction;
[pilot v2 completed 12 valid live runs](pilot-v2-report.md). The observations
below are retained rather than rewritten as if the original files were recovered.

Observed at 06:24 UTC on the receiving macOS machine, after fast-forwarding
`research/outcome-driven-workflow-design` to
`b77a19798d482d20e61467ac41edf7bed1ec54f9` and inspecting PR #14.

**Result: setup failure before any live pilot run. Recommendation: revise.**

## Observations

| Check | Observed result |
| --- | --- |
| Codex CLI | `codex-cli 0.155.0` |
| `codex login status` | Authenticated using ChatGPT |
| Claude CLI | `2.1.275 (Claude Code)` |
| `claude auth status` | `loggedIn: true`; account identifiers omitted |
| `/workspace/sdd-outcome-research/` | Absent on this machine |
| Frozen prototype, runner, prompts and adapters | Not present in the checked-out Git tree; no matching runner or collector found in the scoped local development/temp search |
| Proposal status | CLI reports `approved`, 5/6 tasks complete; task 5 remains unchecked |
| Proposal machine approval baseline | Absent; CLI `doctor` reports `ERROR_APPROVAL_MANIFEST_REQUIRED`, action `establish_approval_manifest` |
| Product package | No difference between `a48a224` and `b77a197` under `skills/sdd-workflow/` |

Authentication status is a local credential check, not proof that a coding
request or package-loading probe succeeded. No model request was made here.
This is one setup preflight failure, not twelve invalid runs: **0 live attempts,
0 valid runs, 0 completed pairs**. Cost, interruption and safety outcomes remain
unmeasured; absent observations are not zero-valued metrics.

## What must be restored

The original research machine must supply the frozen `candidate_proto/`,
`adapters/`, baseline/candidate prompt files, inventories identifying how tree
hashes were computed, and `pilot/scripts/run_dual_host_pilot.py` plus its inputs.
Git contains their reported hashes and design notes, not the executable files.
The seven boundary tests recorded in the earlier report were not rerun here.

Restore the proposal's matching `.sdd/` machine state separately, if available.
The two tracked Markdown files do not carry the approval manifest or operation
evidence. If those records are unavailable, use a supported CLI recovery with
explicit authorization; do not synthesize metadata or change task checkboxes.

## Resume conditions

1. Locate the original artifacts and verify their contents against the recorded
   inventories and hashes. Do not substitute a recreated implementation under
   the `candidate-v1` identity.
2. Record a new execution specification for this machine before collection:
   the platform differs from the original Linux host and Claude is `2.1.275`,
   while the handoff records `2.1.276`. Pin requested models, permissions,
   prompts, collector/scorer identity and pair order; verify actual package
   loading. Preserve the original freeze files as historical evidence.
3. Run the recovered runner's preflight/materialization/dry-run, then the
   6-pair live pilot. Retain valid failures and apply the existing invalid-run
   policy without counting this preflight as a per-slot attempt.
4. Use live evidence to revisit the recommendation. Until then, retain
   **revise**, leave task 5 incomplete and do not adopt the candidate workflow.

If the original files cannot be recovered, a reconstructed candidate needs a
new candidate identity, new reproducibility checks and a new freeze. It cannot
claim to reproduce the previously reported prototype or its seven tests.
