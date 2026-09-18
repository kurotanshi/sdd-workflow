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

PR #14 lands only this research-report directory. The proposal, task status and
CLI-created machine records remain local under `sdd/outcome-driven-workflow-design/`;
they were untracked before merge without changing their contents or lifecycle.
The temporary snapshot remains available at commit `bc1aaa4`.

The 23 Skill/eval/product-documentation files were extracted unchanged into
[draft PR #15](https://github.com/kurotanshi/sdd-workflow/pull/15).
[Issue #13](https://github.com/kurotanshi/sdd-workflow/issues/13) remains open
pending its separate governance and selection-eval checklist. This research
does not adopt the candidate workflow or approve the thinning diff.

The pilot baseline is pinned to `a48a224`, which includes that unmerged thinning;
it is **not** the unchanged `main` package. The measurements must not be presented
as candidate-versus-main results. Frozen inputs and observed results are retained.
