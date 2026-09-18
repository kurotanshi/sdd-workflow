# Outcome-driven workflow research artifacts

Task 5 is complete: **6 pairs / 12 valid Codex + Claude live runs**.
Recommendation: **revise; do not adopt**. See the
[pilot v2 report](pilot-v2-report.md) for paired costs, trace audit, evidence
coverage failure, oracle limitation and follow-up scope.

- [Frozen specification](pilot-v2-spec.json) and [55-file inventory](pilot-v2-freeze.json)
- [Per-run results and audit](pilot-v2-results.json) and [raw artifact hashes](pilot-v2-trace-index.json)
- [Local source/evidence bundle handoff](pilot-v2-handoff.json)
- [Runbook and historical setup status](dual_host_pilot.md)

The rebuilt external harness is `/Users/kurohsu/dev/sdd-outcome-research-v2/`.
The original `/workspace/sdd-outcome-research/` was unavailable on this Mac;
v2 has a new identity and does not claim to reproduce the missing v1 prototype.
Original v1 design notes, freezes and the [06:24 UTC preflight](resume-preflight-2026-09-18.md)
remain historical records. Raw traces and executable candidate code stay outside Git.
Transfer the local bundles when handing this research to another machine.

The research proposal and task status are tracked on this temporary branch under
`sdd/outcome-driven-workflow-design/`, including fresh machine records established
through the supported CLI. Product `skills/sdd-workflow` was unchanged by this
continuation. PR #14's earlier Skill/eval thinning changes require separate review;
these research results do not approve that diff or qualify a release.
