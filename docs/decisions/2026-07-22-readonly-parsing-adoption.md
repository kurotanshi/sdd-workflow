# Adopt the v0.3 readonly parsing path

## Date
2026-07-22

## Versions
- Engine: `0.3.0`
- Skill: v0.3 candidate based on repository commit `5facfaca4c1e339d69fb2c14ac26c33062c5596f`
- Environment: Codex CLI `0.145.0`; Claude Code `2.1.217`; macOS `15.7.3` arm64; pilot host Python `3.13.0`

## Question and gate
May the canonical `SKILL.md` switch its readonly proposal discovery, validation, status, and abandonment-preflight paths from prose parsing to the bundled v0.3 CLI?

Success required fresh Codex and Claude Code sessions to invoke the CLI instead of opening proposal artifacts, reproduce reachable fixture outcomes, stop without prose fallback after an execution or validation failure, preserve all fixture bytes, and require no repeated operator guidance. Failure of any core condition would produce `NO-GO`; the script would remain internal until another pilot.

## Evaluated scenarios

| Scenario | Expected behavior |
| --- | --- |
| Valid status | Run `status --json`; report `draft` and 1/2 tasks from CLI data. |
| Strict malformed-task validation | Run `validate --json`; stop on `ERROR_INVALID_TASK_CHECKBOX` / `fix_artifact_format` without reading Markdown. |
| Degraded abandonment preflight | Run `abandon-preflight --json`; keep preflight available, label 1/2 counts unreliable, preserve both artifact hashes, state that working-tree code is not reverted, and request the exact confirmation phrase. |
| CLI unavailable to the agent | Stop and ask for execution permission; never substitute prose parsing. |
| Unknown schema characterization case | Determine whether the manifest-only injected version is a valid public-CLI pilot case. |

## Observed evidence

- Codex ran four fresh sessions. Each session loaded the selected Skill once and issued one CLI call. The reachable status, strict validation, and degraded preflight cases matched the fixture expectations; there were no direct reads of `proposal.md` or `tasks.md`.
- Claude Code ran fresh sessions for the same three reachable paths. Each successful session issued one Bash CLI call and did not read proposal artifacts. Status and preflight returned the same canonical fields and hashes as Codex.
- Both tools reported the three `ERROR_INVALID_TASK_CHECKBOX` / `fix_artifact_format` pairs from strict validation and stopped without fallback.
- In Claude Code `dontAsk` mode, one strict-validation attempt appended `; echo EXIT=$?`, which the permission policy rejected. A later canonical-Skill check also rejected direct execution of the POSIX launcher. Claude stopped without reading artifacts in both cases. Skill orchestration was therefore standardized on the same entry point as one unwrapped `python3 <skill-dir>/scripts/sdd.py` call; the launcher remains a user/install-smoke convenience. This intervention is recorded as `F-20260722-02`.
- Codex's read-only sandbox emitted pyenv temporary-file warnings before otherwise valid JSON. The agent still consumed the JSON correctly; this is recorded as `F-20260722-03` for monitoring.
- The `future-schema` fixture carries version `99` only as an injected characterization-manifest input. Because v0.3 intentionally does not define schema metadata encoding in artifacts, the public CLI correctly treated its Markdown as unversioned v1. The pilot replaced this unreachable failure scenario with malformed-task validation; see `F-20260722-01`.
- `cmp` confirmed that all four copied fixture pairs remained byte-identical after the pilot.
- No reachable parser result diverged from the v0.2.3 characterization expectations. No session used a second parsing path. The ordinary cost was one CLI execution per readonly operation; Codex also performed its standard one-time Skill load.
- After switching the canonical Skill, fresh Codex and Claude Code sessions received only the ordinary `實作 valid-simple` request. Each loaded the actual Skill, issued exactly one canonical `status` call, made no artifact read, and stopped at the `draft` approval gate with no mutation. The first Claude direct-launcher attempt reproduced `F-20260722-02`; after the documented `python3 .../sdd.py` invocation adjustment, the same `dontAsk` harness passed without a permission denial.

The record retains only de-identified result summaries and reproducible fixture names. Full transcripts and session identifiers are intentionally not stored.

## Rejected alternatives
- Keep prose parsing as a fallback: rejected because it creates two competing implementations and invalidates fail-closed behavior.
- Delay all adoption until mutation commands exist: rejected because the reachable readonly paths were stable and independently useful, while v0.3 is intentionally a script-read/prose-write plateau.
- Treat unknown-schema injection as a public CLI acceptance case in v0.3: rejected because no artifact encoding exists until the schema proposal defines one.
- Require zero tool calls: rejected because one deterministic CLI call is the mechanism under evaluation; no evidence showed a completion-rate regression at this level.

## Decision
`GO` for the v0.3 readonly paths only: candidate discovery, validation, status/counting, implementation prechecks, archive completion checks, and abandonment preflight may switch to bundled CLI orchestration. Active and terminal mutation remain on the current prose procedure until separately gated v0.4 commands exist.

The Skill must direct agents to execute each JSON CLI command as one unwrapped `python3 <skill-dir>/scripts/sdd.py` tool call, consume JSON even when the process exits nonzero, branch on `ok` and `errors[].code/action`, and fail closed when execution itself is unavailable. It must not retain a duplicate scanner or hash implementation.

## Rollback boundary
If post-adoption evidence shows repeated direct artifact parsing, permission friction that blocks ordinary use, or materially lower completion, pin or reinstall prose-only `v0.2.4` and record a new decision. v0.3 readonly commands write no proposal schema or machine metadata, so this rollback requires no artifact migration. It does not authorize rollback of implementation code or proposal state.

## Follow-up
- The canonical `SKILL.md` is switched and slimmed; fresh-session post-switch status/approval-gate checks passed in both tools.
- Monitor `F-20260722-02` and `F-20260722-03`; reopen the gate if either repeats outside the pilot harness.
- Do not start v0.4 solely because this adoption passed; v0.4 still requires its own entry evidence and path-specific activation gates.

## Sensitive-data review
- [x] No full user transcript is stored by default.
- [x] Project names, repository paths, source snippets, credentials, personal data, and customer data are removed or replaced with stable neutral labels.
- [x] Commands and links contain only information safe to retain in this repository.
- [x] When raw evidence cannot be safely retained, the record contains a de-identified summary and a minimal synthetic reproduction instead.
