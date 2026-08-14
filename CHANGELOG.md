# Changelog

本專案的所有重要變更都記錄在此檔。格式參考 [Keep a Changelog](https://keepachangelog.com/)，版本遵循 [SemVer](https://semver.org/)。

## v1.1.1 — 2026-08-14

### Changed
- `references/proposal-authoring.md`：新增「Intake, before authoring」條件式需求澄清規則——寫草案前辨識可能實質改變 requested behavior、scope、impact 或 acceptance conditions 的假設與缺口；使用者指定的實作方式不自動等同期望成果；重大歧義時簡述決策相關缺口、只問一個最關鍵的問題，收到回答前不建草案；資訊足夠時直接建立草案並標示可延後的不確定性，不輸出固定分析報告。`SKILL.md` 既有「Material ambiguity requires a focused question before authoring.」維持為主流程摘要；觸發詞、核准閘門、managed 命令面與 lifecycle 均不變。
- `CONTRIBUTING.md`／`CONTRIBUTING.en.md`：fresh-session 驗收矩陣新增「提案 intake」檢查列。
- Engine release 更新為 `1.1.1`；engine generation 維持 `1.1`，proposal schema v1/v2、JSON output v1 與 machine envelopes 均不變。

### Validation
- 變更源自已歸檔提案 `refine-proposal-clarification`（文件，1/1 task，TDD 錨點測試先行）。
- `tests/test_skill_reduction.py` 新增條件式 intake 雙路徑錨點測試；270 筆 unit/integration、package-validation、docs-consistency、trigger-contract 與 install-smoke（macOS）全數通過。

## v1.1.0 — 2026-07-29

### Added
- 新增公開指令 `repair-archive-record`：對缺少終端證據的封存目錄提供受支援、需明確確認的復原路徑。唯讀 preflight 回報缺漏（終端狀態、機器證據、INDEX 列）並印出封存 `proposal.md`／`tasks.md` 原始位元組的具名 SHA-256 證據摘要；執行需同時帶回兩個證據摘要、明確終端狀態與單行摘要。復原只補缺漏欄位（以 managed status writer 補終端狀態、寫入 `recovery` 機器證據承載摘要），永不搬回目錄、不猜測摘要、不改動既有正確記錄；證據不符或終端狀態與目錄名稱後綴不一致時 fail closed（新錯誤碼 `ERROR_RECOVERY_TARGET_INVALID`、`ERROR_RECOVERY_NOT_APPLICABLE`、`ERROR_RECOVERY_EVIDENCE_MISMATCH`、`ERROR_RECOVERY_STATUS_MISMATCH`；binding action 新增 `rerun_repair_preflight`）。
- `rebuild-index` 新增 `--directory <name> --summary <text>`：僅在該目錄完全沒有摘要來源時接受明確提供的摘要，解除「摘要必須來自既有 INDEX 列」的循環依賴；目錄已有權威摘要時回 `ERROR_RECOVERY_SUMMARY_UNEXPECTED` 且不寫入。
- Archive model 新增 recovery evidence v1：legacy 目錄的摘要來源依序為有效 recovery 證據（權威）→ 唯一匹配的 INDEX 列；malformed recovery 證據 fail closed。

### Fixed
- 修正一筆缺少終端證據的歷史封存目錄會無限期阻塞後續每次歸檔的衍生 INDEX 重建（`COMMITTED_DERIVED_ARTIFACT_STALE`），而復原規則禁止手動編輯封存目錄與 INDEX、工具卻沒有任何受支援復原路徑的問題（2026-07-26 實際阻塞事故）。

### Changed
- Engine release 更新為 `1.1.0`，engine generation 由 `1.0` 進為 `1.1`（`runtime-identity.json` 的 `compatible_engine_generation` 同步）；proposal schema v1/v2、JSON output v1、既有指令與 machine envelopes 均不變，屬向後相容新增（versioning policy §2 MINOR：adds backward-compatible optional command / diagnostic code）。
- 同步 `SKILL.md` 指令契約清單、`references/runtime-recovery.md`（新增 Archive record recovery 程序）、`docs/cli-contract.md`、`docs/archive-model.md` 與 `docs/doctor-diagnostics.md`。

### Validation
- 新增 `tests/test_archive_recovery.py` 9 筆回歸（阻塞案例重現、復原解除阻塞、僅缺摘要重建、全部 fail-closed 不變量含 preflight 唯讀與永不搬回）；269 筆 unit/integration、package-validation、docs-consistency、trigger-contract 與 install-smoke（macOS）全數通過。

## v1.0.3 — 2026-07-29

### Changed
- `SKILL.md`：新增明文輸出語言規則（使用者面向回報、提問與錯誤說明為繁體中文），並為 package-local discovery、CLI fail-closed 與放棄不回退三條規則補上動機；規則語義、觸發詞、回報詞元與 managed 命令面不變。
- `references/proposal-authoring.md`：新增可逐字複製的完整 worked example（proposal.md＋tasks.md，Schema v2）；docs-consistency 以現行 parser 驗證內嵌範例，防止範例與格式規則漂移。
- `CONTRIBUTING.md`／`CONTRIBUTING.en.md`：文件化「SKILL.md 變更須同步刷新 `runtime-identity.json` 的 `skill_sha256`」維護流程，並在 fresh-session 驗收矩陣加入「輸出語言」檢查項。
- Engine release 更新為 `1.0.3`；engine generation 維持 `1.0`，proposal schema v1/v2、JSON output v1 與 machine envelopes 均不變。

### Validation
- 變更源自已歸檔研究 `prompting-best-practices-audit`（對照官方 Claude prompting best practices：0 衝突、3 緊張，均為澄清型缺口）。
- 260 筆 unit/integration、package-validation、docs-consistency、trigger-contract 與 install-smoke（macOS）全數通過；觸發詞與回報詞元不變由 trigger contract 證明。

## v1.0.2 — 2026-07-27

### Changed
- 重寫中英文 README 的產品定位：SDD 不只用於大型或跨 session 工作，而是協助 AI Agent 以可審查規格、明確核准與逐項驗證，正確完成大多數可驗收的變更任務。
- 明確列出新功能、修 bug、重構、維運、文件與有界研究等適用類型，並保留純問答、無界探索、rollback、部署與一般取消的邊界。
- 說明小型任務可以使用精簡 proposal，但不會跳過核准、逐條驗證與驗收歸檔；CPython 3.11 是 bundled state-management CLI 的執行環境，日常操作仍透過 Agent 對話完成。
- 新增 README 定位回歸契約。Engine release 更新為 `1.0.2`；Skill 觸發、proposal lifecycle、engine generation `1.0`、proposal schema v1/v2、JSON output v1 與 machine envelopes 均不變。

## v1.0.1 — 2026-07-27

### Fixed
- 修正 authorized revision 在已完成部分 task 後新增或移除尾端待辦 task 時，重新核准被誤判為 `OUT_OF_BAND_DRIFT`；status、machine metadata 與已完成 task 的未授權變更仍然 fail closed。
- 修正 reapproval 在 Approval Manifest 或 metadata 寫入中斷後無法安全重試；相同 operation 可恢復，後續竄改仍會被拒絕。
- 修正可讀但不可變更的 legacy proposal 對 `approve`、`begin-revision`、`complete-task`、`archive`、`abandon` 誤報成功；現在回傳 `ERROR_LEGACY_MUTATION_UNSUPPORTED`／`upgrade_or_recreate_proposal` 且不寫入。

### Changed
- 重寫中英文 README，明確說明 Skill 目標、適用情境、安裝需求、完整 workflow、使用方式與安全邊界。
- Engine release 更新為 `1.0.1`；engine generation 維持 `1.0`，proposal schema v1/v2、JSON output v1 與所有 machine-envelope versions 不變。

### Validation
- `SKILL.md`、觸發規則與 Agent orchestration 未變；沿用 v1.0.0 的完整 78-run Agent adherence gate，並納入兩項修正的 focused cross-Agent evidence。
- 發布候選版本必須通過完整 unit/integration、runtime conformance、recovery drills、package/install/full-lifecycle、examples、documentation 與 trigger gates。

## v1.0.0 — 2026-07-23

### Added
- 凍結 `sdd-protocol-1.0` 的 Core protocol、Reference runtime／CLI 與 Agent adapter 三組穩定契約。
- 新增 v1 Semantic Versioning／deprecation policy、security/trust model、non-goals、v0.6→v1 migration 與 rollback guides。
- 新增公開 conformance kit、portable runtime discovery／handshake、sample repository、上層 composition example、team evidence 與 10 組 recovery drill groups。

### Changed
- Engine release 更新為 `1.0.0`、package-compatible generation 更新為 `1.0`；proposal schema 仍為 v1/v2，CLI、handshake 與所有 machine envelopes 維持既有版本。
- Agent release gate 提高為至少 95% adherence 且 Critical Violation 必須為零；v1 候選矩陣為 76/78（97.4%）、Critical 0，驗收期需求變更情境為 6/6。
- Skill 保留精簡 adapter，managed lifecycle mutation 持續只由 package-local runtime 執行。

### Deprecated
- None.

### Removed
- None.

### Security
- 明確限制本系統為 cooperative local change control，不提供 authenticated identity、process isolation、access control 或 workspace-wide tamper resistance。
- Public eval reports 僅保留 aggregate evidence；raw prompts、transcripts、event payloads、credentials、個資與絕對使用者路徑不得發布。

### Migration
- 從 v0.6.0 替換完整 package 後重新執行 discovery、handshake、status、doctor 與 index validation；本 release 不重寫 proposal 或 machine envelopes。

### Rollback
- 在只存在 v0.6 支援的 Schema v1/v2 與 version-1 envelopes、且無 partial transition 時，可完整 package 直接 pin 回 v0.6.0；不得刪除 `.sdd`、版本標記或改動 SDD lifecycle。

## v0.6.0 — 2026-07-22

### Added
- 新增五個可獨立設為 required 的 CI checks：`unit`、`fixtures`、`package-validation`、`docs-consistency`、`install-smoke`，並保留 macOS／Linux、最低／最新 Python 的 unit 與 install matrices。
- 新增 deterministic release-package builder，以及 Claude Code、Codex、dev-link、release archive 的 hermetic installation smoke matrix。
- 新增 engine version-skew diagnostics、upgrade/read-only downgrade matrix、問題回報欄位與 team/worktree ownership contract。
- 新增 concurrent archive、parallel INDEX rebuild、stale-scan overwrite 與 worktree isolation regression tests。

### Changed
- Engine version 更新為 `0.6.0`；artifact compatibility 仍由 proposal schema 與各 machine-envelope version 決定，不由 writer version 單獨決定。
- 團隊操作明訂同一 proposal 同時只有一位 owner；獨立工作使用不同 short name，實作樹可能互相干擾時搭配不同 Git worktree。

### Decision
- Contention matrix 未觀察到 authoritative archive data loss、不可恢復狀態或無法由 `validate-index`／`rebuild-index` 修復的 derived-state corruption，因此 v0.6.0 不加入 speculative lock 或 INDEX-level CAS。

### Rollback
- CI、安裝測試與團隊指引不改變 artifact formats，可獨立回退。已由 v0.4+ 管理的 proposal 仍須依 [`docs/compatibility.md`](./docs/compatibility.md) 使用相容 engine 完成或放棄。

## v0.5.0 — 2026-07-22

### Added
- 新增明確 `schema_version: 2` frontmatter、strict `parse_v2` adapter 與 Schema v2 fixture corpus；future/unknown metadata 在 task parsing 前 fail closed。
- 新增 `維運`、`文件`、`研究` 三種 primary type；研究沿用既有 lifecycle，並以 canonical `## 結論` 保存與重建研究輸出。
- 新增 Schema v2 entry decision 與 evidence records；實際案例支持類型／研究結論，但不支持 impacts、labels 或 type-specific required-section matrix。

### Changed
- 新提案預設寫入 Schema v2；既有 unversioned/explicit v1 與 legacy artifacts 繼續透過原 adapter 讀取，不原地 migration。
- Approval Manifest 透過 approval-relevant `sdd.schema` extension 區分 v1/v2 identity；研究結論為 presentation/output extension，不因產出答案而失效原核准。
- Engine version 更新為 `0.5.0`，支援 proposal schema `1..2`。

### Rollback
- Schema v2 proposal 必須由支援 v2 的 engine 讀取與 mutation；移除 schema marker 不是降級。既有 v1 proposals 可繼續由 v0.5 engine 管理。

## v0.4.0 — 2026-07-22

### Added
- 新增 versioned active metadata、Approval Manifest、managed-state attestation 與欄位級 approval diff；approval identity 由保存的 canonical JSON manifest 定義，digest 只作 identity token。
- 新增 `approve`、`begin-revision` 與 `complete-task`，以 snapshot CAS、task identity、atomic replacement 與 evidence-backed retry 管理 active transitions。
- 新增 canonical archive model、全量 deterministic INDEX renderer、`rebuild-index`、`validate-index` 與 evidence-bound `doctor` diagnostics。
- 新增 `archive`／`abandon`、互斥的 `--summary`／`--summary-file`、terminal operation evidence、directory-move commit point、partial-failure injection 與 safe retry matrix。

### Changed
- Cross-tool activation gate 通過後，正式 Skill 的既有 status、checkbox、metadata、archive move 與 INDEX mutation 統一由 CLI 執行；agent 仍負責核准語意、程式實作、驗證、摘要與錯誤溝通。
- Archive INDEX 改為由所有 archive records 全量重建的 derived artifact，不再 append-only 修改。
- Attestation 只涵蓋 machine-managed state；approval-relevant semantics 由 Approval Manifest 比對，其餘正文不被誤當 managed drift。

### Breaking
- v0.4 metadata 一旦建立，進行中的 proposal 不得由 v0.3 prose mutation path 接手。刪除 `.sdd` metadata 不是受支援的降級或 recovery。

### Rollback
- 沒有 v0.4 metadata 的 proposal 可 pin 回 readonly plateau `v0.3.0`。已有 metadata 的進行中 proposal 必須先以 v0.4 完成或放棄，或等待明確 migration decision。
- Activation evidence 與 rollback triggers 見 `docs/decisions/2026-07-22-managed-mutation-activation.md`。

## v0.3.0 — 2026-07-22

### Added
- 新增以 v0.2.3 release 行為為 baseline 的 characterization corpus、version-dispatched parser、canonical proposal model 與 deterministic diagnostics。
- 新增 `validate`、`list`、`status` 與 `abandon-preflight` readonly CLI，包含 stable machine error code、JSON envelope、project root/path/symlink 安全邊界與 raw-byte snapshot manifest。
- 新增 macOS/Linux 的 checkout 與 installed-package smoke tests，以及 parser fixtures、package validation 與核心文件一致性 CI。

### Changed
- 必要 runtime 調整為 CPython 3.11 以上；macOS 與 Linux 為 supported，Windows 為 best effort。Runtime 缺失或版本過舊時 fail closed，不得回退到 prose parser。
- Adoption gate 通過後，Skill 的 readonly parsing path 由內附 script 擔任，`SKILL.md` 只保留意圖、核准、command orchestration、error action 與溝通邏輯。

### Breaking
- 本專案仍處於 `0.x`，但 v0.3.0 是 breaking minor：安裝環境必須提供 CPython 3.11+，readonly workflow 不再保證無 Python 的 copy-only 行為。

### Rollback
- 若 parsing-path pilot 發現額外 tool call 導致 agent 遵循度退化，pin 回最新 prose-only release `v0.2.4`。v0.3 readonly plateau 不寫入 proposal schema 或 machine metadata，因此不需要 data migration。

## v0.2.4 — 2026-07-22

### Fixed
- 縮窄 `SKILL.md` frontmatter description：自然語言直接觸發詞改列明確的 `取消提案`，並明訂未指向 SDD proposal 的裸 `取消` 不得選用此 Skill；code-revert request 維持 workflow 外操作，但 frontmatter 同時攜帶「改檔前確認精確範圍、不得改動 proposal state」的安全邊界。

### Added
- 新增 `tests/trigger-contract.sh` regression check，驗證 frontmatter trigger、裸取消消歧、code-revert 範例與 phase menu 規則不互相漂移。
- 中英文 README 更新至 v0.2.4，加入 `ROADMAP.md` 入口並同步 direct-trigger 說明；`CLAUDE.md` 的工具層 trigger 清單也只列明確的 `取消提案`，避免啟動上下文重新擴張 selector 邊界。

### Notes
- 本 patch 不加入 deterministic parser、machine metadata、proposal schema 變更或必要 Python runtime；這些工作仍依 ROADMAP 的獨立 proposal 與 adoption gate 推進。

## v0.2.3 — 2026-07-22

### Fixed
- 放棄不再被 `tasks.md` 格式錯誤鎖死：abandonment preflight 成為共用 task scanner 停止規則的唯一例外——格式錯誤時回報行號、標明任務計數與已完成清單不可靠，仍照常計算並印出 hash snapshot、允許進入 `確認放棄 <短名稱>` 流程；實作（approval gate 前）、修訂與歸檔維持嚴格擋下。降級情況下，確認放棄執行後的回報同步標明計數與清單不可靠。
- 確認放棄的 hash 比對改由機器執行：把 transcript 中的 snapshot 值逐一代入系統指令做等值判斷（POSIX 例如 `[ "<expected-hash>" = "$(shasum -a 256 <file> | cut -d' ' -f1)" ]`），agent 只依比對結果／exit code 行動；代入前先驗證每個 snapshot 值符合 `^[0-9a-f]{64}$`（64 位小寫十六進位），格式不符視為無有效 snapshot、不執行比對直接重跑 preflight；禁止目視比對 hex 字串、禁止以現場重算值取代 expected snapshot，比對指令失敗或不可用一律視為不符。
- Phase selection 未指名階段的選項清單改列 `取消提案`，移除會觸發再次反問的裸 `取消`。

### Changed
- 抽出共用 Terminal archive procedure：放棄執行與完成歸檔在各自前置檢查通過後，走同一份參數化程序（終態字串、目錄後綴、最終回報文字等行為差異僅由參數表選擇，回報內容定義於表下方），消除兩份幾乎相同步驟未來只修一邊的 drift 風險（v0.2.1 的 INDEX 順序修正曾需兩處各修一次）。
- 中英 README（版本 v0.2.3）、中英 CONTRIBUTING 驗收矩陣與 CLAUDE.md 驗證模型同步以上變更；驗收矩陣新增「共用歸檔程序」項目。

## v0.2.2 — 2026-07-22

### Changed
- 放棄 preflight 必須把兩份檔案的 SHA-256 hash 直接列在回報中：印出的值即為 preflight snapshot，成為 transcript 裡的持久文字，避免長對話 context 壓縮後 snapshot 只存在於工具輸出記憶而遺失（遺失時仍安全回退為重跑 preflight）。
- Task scanner 明文化任務區清單規則：掃描區內只允許合法任務行、空行與非清單文字，其他清單項——包含以 Markdown 連結開頭的項目（如 `- [參考](https://…)`）——一律視為格式錯誤，回報行號並停止。把原本 checkbox-like 判定誤傷連結清單項的隱性副作用改為 documented 規則。
- 放寬「取消」語意：明確指向程式碼的取消請求（如「取消剛才的程式碼修改」）直接視為 workflow 之外的一般復原請求——先確認範圍才執行、絕不觸碰提案；只有裸「取消」或指涉不明時才反問要復原程式碼還是放棄提案。
- 中英 README 與 CONTRIBUTING 驗收矩陣同步以上三項。

## v0.2.1 — 2026-07-22

### Fixed
- 放棄改為兩階段安全操作：`放棄`／`放棄 <短名稱>`／`取消提案` 只執行唯讀 preflight（回報短名稱、狀態與任務進度、警告工作區程式碼不會復原、以系統指令計算 SHA-256 hash snapshot 留在對話中）；只有一字不差的 `確認放棄 <短名稱>` 且重新計算的 hash 未變，才標記 `abandoned`、搬移目錄並更新 INDEX。裸 `取消` 一律先詢問要復原程式碼還是放棄提案。
- 觸發防呆：階段詞必須是指向 SDD workflow 或特定提案的明確指令，描述性文字不啟動任何 phase。
- 共用 task scanner 補上完成度漏洞：Phase 1、Phase 2、修訂、abandonment preflight 與歸檔只認行首頂層 `- [ ] `／`- [x] `；checkbox-like 判定涵蓋 `-`/`*`/`+` 與有序清單 marker、任意方括號內容，掃描區域內縮排、巢狀、`- [X]`、`* [ ]`、`-[ ]`、`- [xx]`、`- []`、`1. [ ]` 等行都是格式錯誤，回報行號並停止（修正巢狀或變體 checkbox 可無聲通過完成度檢查的問題）。Phase 2 在 approval gate 之前即執行 scanner，格式錯誤不會寫入 `approved`。
- 放棄執行與完成歸檔固定步驟順序為「狀態驗證 → 搬移整個活動目錄並驗證 → 才追加 INDEX → 最終驗證」，修正 v0.2.0 以來 INDEX 可能先於搬移寫入、留下不一致狀態的缺口。

### Changed
- 放棄流程明確永不自動 revert 工作區程式碼；復原是需另行明確要求並確認範圍的獨立操作。
- 修訂配額改為「未勾任務最多 10 條」；已勾任務為歷史紀錄不占配額，修訂實質改變原目標時要求另開新變更。
- 中英 README、CONTRIBUTING 與 `CLAUDE.md` 同步兩階段放棄、scanner 與修訂配額規則；CONTRIBUTING 的驗收清單改為 fresh-session 人工驗收矩陣，明確區分靜態可證明與需人工互動驗證的項目。

## v0.2.0 — 2026-07-22

### Added
- 提案持久化狀態：新提案以 `draft` 建立，明確核准後寫入 `approved`，歸檔時寫入 `completed` 或 `abandoned`。
- 提案修訂與放棄路徑：修訂保留已完成任務並重新等待核准；`放棄`／`取消` 會建立帶 `-abandoned` 後綴的歷史紀錄。
- `sdd/archive/INDEX.md`：完成或放棄歸檔時追加日期、短名稱、終態與單句摘要。
- Phase 2 缺少活動目錄、`proposal.md` 或 `tasks.md` 時的停止防呆，以及舊提案缺少狀態時的未核准處理。
- Git 行為規則：未經使用者要求不自動 commit；被要求時建議 message 對應短名稱與任務編號。

### Changed
- 收緊核准語意：`開始實作` 可核准 `draft`；單獨的 `實作` 只會繼續 `approved`，否則先詢問確認。
- 任務粒度從約一小時改為一個可獨立驗證的行為改變，仍維持最多 10 條。
- 歸檔日期必須由目前執行環境取得；完成度只計算 `## 驗收條件` 前的 task checkbox，且空 checklist 不視為完成。
- 中英 README、CONTRIBUTING 與 repo 維護規範同步新的狀態、修訂、放棄、歸檔索引與驗收規則。

## v0.1.0 — 2026-07-22

首個版本：把個人用的 SDD 三階段指令收斂成一份跨工具、可分享的 canonical Agent Skill。

### Added
- Canonical skill `skills/sdd-workflow/SKILL.md`：單一流程來源，涵蓋 提案 → 實作 → 歸檔 三階段（無候選消歧、逐條進度回報、re-read 驗證、標準提案區段）。
- `skills/sdd-workflow/agents/openai.yaml`：Codex UI／invocation metadata（僅 metadata，不承載流程規則）。
- `scripts/link-dev.sh`：作者／貢獻者專用的 dev-link 工具（雙工具、`--claude-only`／`--codex-only`／`--unlink`／`--help`、`CLAUDE_SKILLS_DIR`／`CODEX_SKILLS_DIR` 覆寫、idempotent、衝突時停止）。
- 中英雙語 README（`README.md` / `README.en.md`）：三種安裝通路（Codex 原生 skill-installer、第三方 skills.sh CLI、手動複製）、各通路更新／移除方式、兩工具觸發語法。
- `CONTRIBUTING.md`：明訂所有流程行為只能改 canonical `SKILL.md`、安裝副本不是來源、skill 資料夾保持乾淨、互動驗收責任。

### Changed
- 跨工具整合改採 **Agent Skills 開放格式的單一 skill**，供 Claude Code（`/sdd-workflow`）與 Codex（`$sdd-workflow`）共用；顯式語法為首選，繁中自然語言觸發為便利功能。

### Removed
- 移除初期的 `commands/{propose,implement,archive}.md`（Claude 專屬 slash commands）與需要 frontmatter 剝除的公開 `install.sh`。原因：Codex 自訂 prompts 已 deprecated 且 `/archive` 撞內建指令；commands + prompts 會讓同一套流程存在多份而分歧。

### Notes
- 觸發詞與對使用者的輸出維持繁中；skill 指令本體為英文，利於跨工具維護。
- 對外散布採各工具生態原生的 copy／installer 模型；symlink 僅作為作者 dev loop，使用前需在各工具新 session 驗證載入。
