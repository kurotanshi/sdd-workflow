# Dual-host pilot runbook (blocked in current environment)

## Intended matrix
Hosts: Codex, Claude  
Cases: small-bug, medium-feature, acceptance-change  
Workflows: baseline prompt + candidate prompt  
Total: 6 pairs / 12 valid runs

## Preflight
1. Confirm baseline freeze `baseline/baseline-freeze-v1.json`
2. Confirm candidate freeze `freeze/candidate-freeze-v1.json`
3. Verify each host loads the intended package/prompt (record hashes)
4. Materialize fixture project copies outside product git state

## Per run
1. Apply only scripted approvals shared across both workflows
2. Collect transcript/tool traces under an external run directory
3. Run fixture oracle after the agent stops
4. Run `adapters/trace_collector.py` then `adapters/scorer.py`
5. Keep valid failures; retry only setup failures (max 3)

## Current blocker
This machine has no authenticated Codex/Claude coding-host session for the paired agent pilot. Boundary checks and collector/scorer simulations were executed instead.
