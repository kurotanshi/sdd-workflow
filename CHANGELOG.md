# Changelog

本專案的所有重要變更都記錄在此檔。格式參考 [Keep a Changelog](https://keepachangelog.com/)，版本遵循 [SemVer](https://semver.org/)。

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
- 新增 Schema v2 entry decision 與 evidence records；實際案例支持類型/研究結論，但不支持 impacts、labels 或 type-specific required-section matrix。

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
- 本專案仍處於 `0.x`，v0.3.0 但是 breaking minor：安裝環境必須提供 CPython 3.11+，readonly workflow 不再保證無 Python 的 copy-only 行為。

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
