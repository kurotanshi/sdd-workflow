# v0.2.3 parser characterization rules

Baseline release: `v0.2.3`  
Baseline commit: `5facfaca4c1e339d69fb2c14ac26c33062c5596f`  
Normative source: `skills/sdd-workflow/SKILL.md` at that tag

This inventory identifies observable prose-era behavior that parser fixtures must preserve. Rule IDs are stable test references; quoted field names and markers are syntax, while the descriptions below are paraphrases of the tagged source.

| Rule ID | Normative section | Characterized behavior |
| --- | --- | --- |
| `DISCOVERY-001` | Phase selection | An active candidate is a direct child of `sdd/`, excludes `sdd/archive/`, and contains both `proposal.md` and `tasks.md`. |
| `DISCOVERY-002` | Phase selection | Zero candidates is missing, one is unambiguous, and more than one is ambiguous; filesystem enumeration order must not choose a winner. |
| `PROPOSAL-001` | Phase 1, step 4 | A v1 proposal uses the headings `## 狀態`, `## 類型`, `## 為什麼做`, `## 要改什麼`, and `## 影響範圍` under a short-name title. |
| `PROPOSAL-002` | Phase 1 / Phase 2 | Recognized active status values are `draft` and `approved`; missing status is legacy and never implies approval. |
| `PROPOSAL-003` | Terminal archive procedure | Recognized terminal status values are `completed` and `abandoned`. |
| `PROPOSAL-004` | Phase 1, step 3 | Recognized v1 change types are `新功能`, `修 bug`, and `重構`. |
| `TASK-001` | Task checklist format and scanner | The task scan region starts at line 1 and ends immediately before the first exact `## 驗收條件` heading. |
| `TASK-002` | Task checklist format and scanner | A valid task begins in column 1 with exactly `- [ ] ` or `- [x] ` and has non-empty task text. |
| `TASK-003` | Task checklist format and scanner | Valid task order is document order; checked and unchecked counts derive only from valid task lines in the scan region. |
| `TASK-004` | Task checklist format and scanner | Any other checkbox-like list line is invalid, including indentation, alternate list markers, ordered markers, missing spaces, `[X]`, `[xx]`, and `[]`. |
| `TASK-005` | Task checklist format and scanner | Any other list item in the scan region is invalid, including a Markdown link list item that is not a task. |
| `TASK-006` | Task checklist format and scanner | Blank lines and non-list text are permitted in the scan region and do not affect task counts. |
| `TASK-007` | Task checklist format and scanner | Every invalid list line is diagnosed; strict consumers stop rather than silently skipping it. |
| `TASK-008` | Phase 1, step 5 / Proposal revisions | New proposals allow at most 10 tasks; revisions allow at most 10 unchecked tasks because checked tasks are retained history. |
| `ACCEPTANCE-001` | Phase 1, step 6 | Content after `## 驗收條件` is acceptance content and checkbox/list syntax there never contributes to task counts or task-format diagnostics. |
| `LEGACY-001` | Phase 2, step 2 | A proposal without `## 狀態` remains readable as legacy but is unapproved for mutation. |
| `LEGACY-002` | Task scanner / Abandonment preflight | Malformed task syntax remains readable for abandonment; counts are best-effort and explicitly unreliable instead of blocking preflight. |
| `TERMINAL-001` | Phase 3 / Terminal archive procedure | Completed and abandoned proposals remain readable with their terminal status and task history. |

## Parser-era compatibility additions

The following rules are not claims about v0.2.3 syntax. They are architecture constraints introduced by `ROADMAP.md` for adapting that baseline safely.

| Rule ID | Roadmap section | Required behavior |
| --- | --- | --- |
| `SCHEMA-001` | Parser architecture / Legacy compatibility contract | No explicit version means the parser first attempts schema v1. |
| `SCHEMA-002` | Legacy compatibility contract | An explicit schema version `1` uses the v1 adapter. |
| `SCHEMA-003` | Legacy compatibility contract | An unknown explicit future version fails closed and is never guessed. |
| `LEGACY-003` | Legacy compatibility contract | A partially compatible unversioned document may be read with warnings but is not mutation-safe. |
| `MODEL-001` | Parser architecture | All adapters produce one version-independent model containing schema version, short name, status, change type, sections, tasks, acceptance conditions, and diagnostics. |
| `MODEL-002` | Parser architecture | Approval relevance is extension metadata on canonical fields; it is not inferred later from Markdown syntax. |
| `API-001` | Parser architecture | The canonical model is internal in v0.3.0; no public `parse` command is added. |

## Evidence boundary

Fixtures characterize syntax and deterministic parser output. They do not prove agent compliance, semantic completion, filesystem atomicity, approval integrity, or mutation safety; those belong to later proposals and fresh-session acceptance.
