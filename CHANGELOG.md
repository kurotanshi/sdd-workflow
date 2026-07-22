# Changelog

本專案的所有重要變更都記錄在此檔。格式參考 [Keep a Changelog](https://keepachangelog.com/)，版本遵循 [SemVer](https://semver.org/)。

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
