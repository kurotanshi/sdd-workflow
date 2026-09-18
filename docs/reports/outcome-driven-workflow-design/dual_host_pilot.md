# Dual-host pilot runbook

## Current result: reconstructed v2 complete

The original external Linux directory was unavailable. With user authorization,
a new harness was frozen and executed under
`/Users/kurohsu/dev/sdd-outcome-research-v2/`. **6 pairs / 12 valid live runs**
are complete; the recommendation remains **revise** based on measured results.
See [the report](pilot-v2-report.md) and [bundle handoff](pilot-v2-handoff.json).

To inspect/resume the existing collection, use `REPRODUCE.md` in that directory
or its `source-v2.tar.gz`. The matrix runner skips all existing valid runs,
including failures. Do not remove a valid result or change frozen inputs to seek
a pass. A new experiment requires a new identity and output directory.

```sh
cd /Users/kurohsu/dev/sdd-outcome-research-v2
export PATH=/Users/kurohsu/.nvm/versions/node/v24.15.0/bin:$PATH
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/cost_benefit_experiment.py matrix --spec pilot-spec-v2.json --agents codex --artifact-root runs --keep-workspace
python3 scripts/cost_benefit_experiment.py matrix --spec pilot-spec-v2.json --agents claude --artifact-root runs --keep-workspace
python3 audit/summarize.py
```

Codex 0.155.0 and Claude 2.1.275 must match the spec. Homebrew Codex 0.154.0 is
not the pinned executable. The old aggregate `summarize` command is not used for
v2; its skill-thinning thresholds do not answer this research question.

The sections below preserve **historical v1 instructions and setup observations**;
their old 0/12 status is superseded by the v2 result above.

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
