# Workflow friction log

This append-only log is the common evidence source for adoption, recover, lock, Schema v2, impact metadata, and other evidence-gated decisions. Record observed behavior, not an inferred author or motive. A decision record under `docs/decisions/` must cite relevant entry IDs; memory or an unrecorded report is not sufficient evidence.

## Recording rules

- Add one entry per independently observable friction or failure and keep its stable ID when updating the disposition.
- Store no full user transcript by default. Remove or replace project names, repository paths, source content, credentials, personal data, and customer data with neutral labels.
- Prefer a minimal synthetic reproduction. If raw evidence cannot be retained safely, record only a de-identified summary and whether a maintainer privately verified it.
- Do not claim that a script diagnostic identifies who changed an artifact or why it changed.
- Severity is one of `low`, `medium`, `high`, or `critical`. Disposition is one of `open`, `monitor`, `accepted`, `mitigated`, `rejected`, or `superseded`.

## Entry template

### F-YYYYMMDD-NN: <short summary>

- Date: `YYYY-MM-DD`
- Versions: engine `<version or n/a>`; skill `<version or commit>`; environment `<tool/runtime/OS>`
- Scenario: `<what the operator or agent attempted>`
- Observed friction or failure: `<observable result without attributing intent>`
- Severity: `<low|medium|high|critical>`
- Evidence: `<safe repository link, reproducible command, de-identified summary, or none>`
- Manual intervention: `<none or the action needed to continue>`
- Disposition: `<open|monitor|accepted|mitigated|rejected|superseded>`
- Related decision: `<docs/decisions/... or pending>`

## Entries

<!-- Append new entries below this line. Do not place sensitive raw transcripts here. -->

### F-20260722-01: Manifest-injected schema version is not a public CLI scenario

- Date: `2026-07-22`
- Versions: engine `0.3.0`; skill `v0.3 candidate`; environment `Codex CLI 0.145.0 / macOS arm64`
- Scenario: Ask a fresh agent to validate the characterization fixture whose manifest injects schema version `99`.
- Observed friction or failure: The copied Markdown has no encoded version, so the public CLI correctly parsed it as unversioned v1 instead of producing the internal dispatch error expected by the injected unit-test input.
- Severity: `low`
- Evidence: `tests/fixtures/baseline/MANIFEST.json` and `docs/decisions/2026-07-22-readonly-parsing-adoption.md`
- Manual intervention: Replace the public-CLI fail-closed pilot case with the reachable malformed-task fixture.
- Disposition: `mitigated`
- Related decision: `docs/decisions/2026-07-22-readonly-parsing-adoption.md`

### F-20260722-02: Shell wrapper caused a Claude Code permission denial

- Date: `2026-07-22`
- Versions: engine `0.3.0`; skill `v0.3 candidate`; environment `Claude Code 2.1.217 / dontAsk / macOS arm64`
- Scenario: Validate a malformed checklist whose CLI result intentionally exits `1` with a JSON error envelope.
- Observed friction or failure: The agent appended `; echo EXIT=$?` to one requested command and the harness denied the compound invocation. The first canonical-Skill retest later showed the same permission class rejecting direct execution of the package launcher. Both attempts stopped without prose fallback.
- Severity: `medium`
- Evidence: de-identified pilot summary in `docs/decisions/2026-07-22-readonly-parsing-adoption.md`
- Manual intervention: Retry the pilot once with an explicit single command. Then standardize Skill orchestration on the same bundled entry point as `python3 <skill-dir>/scripts/sdd.py`, which the permission harness already allowed, while retaining the POSIX launcher for user/install smoke.
- Disposition: `mitigated`
- Related decision: `docs/decisions/2026-07-22-readonly-parsing-adoption.md`

### F-20260722-03: Read-only Codex sandbox emitted pyenv stderr noise

- Date: `2026-07-22`
- Versions: engine `0.3.0`; skill `v0.3 candidate`; environment `Codex CLI 0.145.0 / read-only sandbox / macOS arm64`
- Scenario: Execute `status --json` through the script shebang in a fresh read-only Codex session.
- Observed friction or failure: Host pyenv printed temporary-file warnings before the valid JSON result. The CLI exited successfully and the agent reported the canonical result correctly.
- Severity: `low`
- Evidence: de-identified pilot summary in `docs/decisions/2026-07-22-readonly-parsing-adoption.md`
- Manual intervention: none
- Disposition: `monitor`
- Related decision: `docs/decisions/2026-07-22-readonly-parsing-adoption.md`

### F-20260722-04: Repeated prose mutation requires separate edit and verification steps

- Date: `2026-07-22`
- Versions: engine `0.3.0`; skill `v0.2.4→v0.3.0 dogfood`; environment `sequential implementation of four repository proposals`
- Scenario: Complete the first four roadmap proposals under the supported prose-mutation workflow while validating every task transition.
- Observed friction or failure: The four canonical checklists contain 29 completed tasks (5 + 8 + 8 + 8). Every completion required a direct checkbox edit plus a separate re-read or canonical `status` verification; proposal approval likewise remained a separate direct status edit. No incorrect task was observed, but the repeated two-step mutation/verification cost is now material and cannot provide snapshot CAS by construction.
- Severity: `medium`
- Evidence: canonical `status` output for `narrow-skill-trigger-v024`, `add-parser-characterization`, `add-readonly-cli-contract`, and `add-runtime-packaging-baseline`; de-identified maintainer verification recorded in `docs/decisions/2026-07-22-v04-entry-reassessment.md`
- Manual intervention: 29 explicit marker edits and their verification reads across the four real proposal executions.
- Disposition: `accepted`
- Related decision: `docs/decisions/2026-07-22-v04-entry-reassessment.md`

### F-20260722-05: Claude pilot launcher option preceded the print prompt

- Date: `2026-07-22`
- Versions: engine `0.4.0 candidate`; skill `v0.4 managed-mutation candidate`; environment `Claude Code 2.1.217 / bypassPermissions / macOS arm64`
- Scenario: Start the fresh-session managed-mutation implementation pilot with a print prompt and an additional allowed directory.
- Observed friction or failure: The first harness invocation placed `--add-dir` before the positional print prompt, so Claude Code reported that no prompt was supplied and performed no workflow action.
- Severity: `low`
- Evidence: de-identified pilot summary in `docs/decisions/2026-07-22-managed-mutation-activation.md`
- Manual intervention: Correct the launcher argument order and start a new stateless session; no proposal artifact required repair.
- Disposition: `mitigated`
- Related decision: `docs/decisions/2026-07-22-managed-mutation-activation.md`

### F-20260722-06: Operational proposals require imprecise v1 types

- Date: `2026-07-22`
- Versions: engine `0.4.0`; skill `v0.4.0`; environment `ten repository roadmap proposals`
- Scenario: Classify runtime/package hardening and team-operation/CI work using the v1 primary type vocabulary.
- Observed friction or failure: Runtime packaging work is recorded as `新功能` and team readiness as `重構`; neither value describes the proposal's primary intent as precisely as `維運`.
- Severity: `low`
- Evidence: `sdd/add-runtime-packaging-baseline/proposal.md`, `sdd/harden-team-workflow/proposal.md`, and `docs/decisions/2026-07-22-schema-v2-entry.md`
- Manual intervention: Reviewers must infer the actual change class from scope text instead of the type field.
- Disposition: `accepted`
- Related decision: `docs/decisions/2026-07-22-schema-v2-entry.md`

### F-20260722-07: Research conclusions live outside proposal lifecycle

- Date: `2026-07-22`
- Versions: engine `0.4.0`; skill `v0.4.0`; environment `four repository decision records`
- Scenario: Use evidence-gated investigations for readonly adoption, v0.4 entry, and managed-mutation activation.
- Observed friction or failure: The v1 proposal artifact has neither a research type nor a canonical conclusion location, so the question and result must live in a separate decision format and cannot be reconstructed as one terminal proposal record.
- Severity: `medium`
- Evidence: `docs/decisions/2026-07-22-readonly-parsing-adoption.md`, `docs/decisions/2026-07-22-v04-entry.md`, `docs/decisions/2026-07-22-v04-entry-reassessment.md`, `docs/decisions/2026-07-22-managed-mutation-activation.md`
- Manual intervention: Maintain separate proposal-like decision documents and link them manually from evidence logs.
- Disposition: `accepted`
- Related decision: `docs/decisions/2026-07-22-schema-v2-entry.md`
