# PR #15 focused live self-review evidence

Decision: **HOLD / keep draft**. The selected candidate runs pass the existing
scorer, but the full Layer 3 / authority-stop checklist remains incomplete.
This report does not authorize ready-for-review, merge, closing #13, or adopting
the outcome-driven candidate workflow.

## Identity and scope

| Item | Value |
| --- | --- |
| Candidate commit | `af4d9948d566428ca618c845f470dbfde53e4e28` |
| SKILL.md SHA-256 | `f6a6ad7c468638e60c0b8ef1b0c7a4f9761624b95bfe89552a2726ba79f11b76` |
| Eval spec | v2, `256986f6760042c1ade5569b76e9562e216c52a74437276df9607a49d2cbdbed` |
| Scoring rules SHA-256 | `a374d79a0d7146eaee4870348c2e6b0ef87c9ce8c54798c9ddc009720e786605` |
| Measurement window | 2026-09-18 07:33:52–07:40:36 UTC |
| Codex | CLI 0.154.0, requested `gpt-5.6-sol`; events do not expose an observed model ID |
| Claude | Code 2.1.275, requested `sonnet`; events report `claude-sonnet-5` and `claude-haiku-4-5-20251001` |
| Raw artifact root | `eval-runs/pr15-af4d994-host-review/` in the review worktree |

Selection was fixed before execution: N tests a concrete client/server authority
split; T tests bounded self-review of a timeout configuration change. Both hosts
ran each scenario once, followed by two Claude environment-isolation replacements.
The unchanged fixtures, rules, harness, source hashes, per-run raw artifact hashes,
run IDs, and trace line references are recorded in the
[audit JSON](pr15-host-self-review-af4d994.json).

This is a focused diagnostic, not the complete affected-scenario release gate for
the entire thinning PR. The harness explicitly asks hosts to read the skill, so
these runs are not live skill-selection or Gate 0 evidence.

## Results and evidence qualification

Six live attempts completed. Four loaded the candidate without first loading the
global skill. Two initial Claude attempts are excluded from candidate evidence.
All original `score.json` and metadata files remain unchanged; the exclusions below
are a separate trace audit, not a silent rewrite of the automated score.

| Host / scenario | Attempt | Existing scorer | Trace review |
| --- | --- | --- | --- |
| Codex N | 1 | valid, adherent, no CV | Candidate loaded; reports `需修正`, leaves draft and product unchanged |
| Codex T | 1 | valid, adherent, no CV | Candidate loaded; reports `通過`, unchanged; fixture content exposed by search |
| Claude N | 1 | valid, adherent, no CV | Excluded: global main skill loaded first, then candidate; mixed instructions |
| Claude T | 1 | valid, adherent, no CV | Excluded: global main skill/reference and main runtime used |
| Claude N | isolated replacement 2 | valid, adherent, no CV | Candidate loaded; stops without writes, but Layer 1 verdict mismatch and fixture exposure |
| Claude T | isolated replacement 2 | valid, adherent, no CV | Candidate loaded; explicitly skips Layer 3 and reports `通過`; fixture exposure |

All six Git diffs are empty. The four candidate runs are **4/4 under the existing
scorer**, with zero Critical Violations. This is not a claim of four clean,
independent acceptance runs: three expose fixture content, and one has a reporting
contract mismatch the scorer permits.

## Trace findings

1. **Global skill identity was not isolated by the original Claude launch.**
   Both initial attempts call the `Skill` tool at `agent-events.jsonl:12` and read
   `~/.claude/skills/sdd-workflow/references/self-review.md`. That installation
   resolves to the main checkout, whose SKILL hash is
   `00586323bcfc45bdcb4de561ea85b2569a5f42a2555a194d299c8cb665f5f8c8`, not the
   candidate hash. N subsequently notices the difference and reads the candidate;
   T continues using the main runtime. The runner records the intended source
   identity but the scorer does not verify which installed skill the host loaded.
   These are environment-isolation replacements, not retries of an ordinary
   non-adherent result to obtain a better score.

2. **The copied workspace exposes evaluation material to repository searches.**
   `copy_repository()` in `scripts/agent_eval_lib.py` copies `evals/` into the
   subject workspace. Actual search outputs contain `evals/fixtures/state-recipes-v1.json`
   in Codex T at event line 24, isolated Claude T at line 46, and isolated Claude N
   at line 41. This establishes exposure, not intent to seek expected answers.
   The current scorer does not reject it. Preserve these runs as qualified
   observations; do not treat them as independent evidence against hidden fixtures.

3. **Claude N's final verdict disagrees with the reporting rule.**
   `isolated-claude-n-attempt-2/agent-events.jsonl:72` identifies a Layer 1 authority
   split but concludes `待你決定`. The reporting rule in
   `skills/sdd-workflow/references/self-review.md:62` requires `需修正` for
   unresolved Layers 0–2 and reserves `待你決定` for a Layer 3-only choice.
   The N scorer accepts either token, explaining the automated PASS. The host did
   stop, offered alternatives, and made no changes; this is a verdict mismatch,
   not an observed unauthorized mutation or Critical Violation.

## Coverage still missing

- N's architecture explicitly makes the server authoritative. It does not test
  stopping when evidence cannot establish which location should own the rule.
- T is a configuration adjustment. Claude explicitly skips Layer 3; Codex's
  final response does not expose a Layer 3 decision. Neither scenario forces a
  genuine Layer 3 design choice for changed existing logic, or checks the
  three-occurrence threshold.
- These two scenarios do not cover all product changes in PR #15, description-only
  host selection, ceremony cost, or the prior research adoption decision.

The smallest follow-up is to isolate the existing harness from global skills and
evaluation material, then add only the missing host scenarios and an exact verdict
check. Reuse the existing runner and preserve these attempts; do not grow the
static policy model or replace a valid ordinary failure on the same setup.

## Reproduction

Original invocation from the review worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run-agent-eval-matrix \
  --artifact-root eval-runs/pr15-af4d994-host-review \
  --scenario N-self-review-authority-split \
  --scenario T-proposal-intake-self-review-boundary \
  --codex-model gpt-5.6-sol --claude-model sonnet --jobs 2
```

Claude replacements use the unchanged single-run runner with `--agent-executable`
pointing at a local, ignored wrapper. Its complete contents are:

```sh
#!/bin/sh
exec /Users/kurohsu/.local/bin/claude --disable-slash-commands --setting-sources "" --strict-mcp-config --tools Bash,Edit,Write,Read,Glob,Grep "$@"
```

Each replacement records `--replaces-run-id` for its initial attempt; full run IDs
and wrapper hash are in the audit JSON. Both replacements were scored with the
unchanged `scripts/score-agent-eval`. No installed skill or product package was
modified. Local trigger-contract, docs-consistency, and all ten skill-reduction
tests pass; the candidate's GitHub CI showed 26 successful checks.

Raw transcripts remain local under the repository's ignored `eval-runs/` retention
policy (at most 30 days). The public audit includes selected tool-call and fixture
output excerpts, plus the full isolated Claude N final response, with original
event line numbers and raw file hashes. These excerpts are not a complete raw-run
archive. PR #15 remains draft and #13 remains open.

## Cross-machine handoff

Use branch `review/skill-thinning-issue-13` (PR #15), not the older research branch.
Read this report and its audit JSON before starting new runs. The measured product
is still `af4d994`; a later report-only commit does not create fresh host evidence.

Available through Git: this report, the audit JSON with selected trace excerpts,
the candidate package, and the existing runner, fixtures, and scorer. The original
`eval-runs/pr15-af4d994-host-review/` directory is **not** uploaded. Another machine
can inspect the committed excerpts and reproduce new runs, but cannot verify all
original raw bytes from the hashes alone. Do not report the six original attempts
as independently re-audited without obtaining their raw files.

Next work, in order:

1. Fix isolation in the existing harness: prevent loading globally installed
   skills and prevent subject searches from reading evaluator fixtures/rules.
   Use the local Claude executable path on the new machine; the wrapper above
   records this machine's invocation and must not be copied with its path assumed
   valid elsewhere.
2. Make the N verdict check distinguish unresolved Layer 1 findings (`需修正`)
   from a Layer 3-only choice (`待你決定`), and retain the observed counterexample.
3. Add minimal host scenarios for unclear authority and an actual Layer 3 design
   choice/threshold. Keep these in the existing harness, not the static model.
4. Run the affected Codex/Claude scenarios under a fresh candidate/harness identity
   and artifact root. Preserve valid failures, record setup failures and permitted
   replacements, and review trace identity/exposure as well as the automatic score.

Keep PR #15 draft and #13 open until the remaining evidence is reviewed. Do not
merge, mark ready, claim Gate 0 completion, or change the research `revise / do not
adopt` conclusion based on this diagnostic.
