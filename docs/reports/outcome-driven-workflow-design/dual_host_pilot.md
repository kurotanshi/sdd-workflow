# Dual-host pilot runbook

## Intended matrix
Hosts: Codex, Claude  
Cases: small-bug, medium-feature, acceptance-change  
Workflows: baseline prompt + candidate prompt  
Total: 6 pairs / 12 valid runs

## One-click runner (external research dir)
Research harness lives outside the product package:

`/workspace/sdd-outcome-research/pilot/scripts/run_dual_host_pilot.py`

```bash
export PATH="/workspace/sdd-outcome-research/agent-tools/node_modules/.bin:$PATH"

# Preflight + materialize + dry-run (no live agent calls)
python3 /workspace/sdd-outcome-research/pilot/scripts/run_dual_host_pilot.py \
  --preflight --materialize --dry-run

# Live 12 runs (requires authenticated Codex + Claude)
python3 /workspace/sdd-outcome-research/pilot/scripts/run_dual_host_pilot.py \
  --preflight --materialize --execute
```

Auth options:
- Codex: `OPENAI_API_KEY` / `CODEX_API_KEY`, or `codex login`
- Claude: `ANTHROPIC_API_KEY`, or `claude auth login`

## Preflight
1. Confirm baseline freeze `docs/reports/.../baseline-freeze-v1.json` (and research copy under `sdd-outcome-research/baseline/`)
2. Confirm candidate freeze + prompt hashes
3. Verify each host CLI is present and authenticated; record versions
4. Materialize 12 fixture workspaces under `sdd-outcome-research/pilot/workspaces/`

## Per run
1. Apply only scripted approvals shared across both workflows
2. Collect transcript/tool traces under `sdd-outcome-research/pilot/runs/`
3. Run fixture oracle after the agent stops
4. Run `adapters/trace_collector.py` then `adapters/scorer.py`
5. Keep valid failures; retry only setup failures (max 3)

## Original research-machine status (2026-09-18)
- CLIs installed locally: Codex 0.155.0, Claude Code 2.1.276
- Prompt hashes match freeze (`baseline` / `candidate`)
- Dry-run matrix of 12 cells succeeded (commands + prompts written; no live agent)
- Live pilot still blocked until both hosts are authenticated

## Receiving-machine preflight (2026-09-18, 06:24 UTC)

The macOS machine now has authenticated Codex and Claude CLIs. The original
`/workspace/sdd-outcome-research/` directory is absent, however, and the runner,
prototype, prompts and adapters were not committed. No live runs were started.
Restore those files before using the commands above; their hashes alone cannot
recreate the frozen experiment. The local proposal also lacks its machine
approval baseline, which must be recovered before marking task 5 complete.

See [the resumption preflight](resume-preflight-2026-09-18.md) for observed
versions, the setup failure, and the conditions for resuming. The decision
remains **revise**, with **0/12 valid live runs**.
