# Changelog

本專案的所有重要變更都記錄在此檔。格式參考 [Keep a Changelog](https://keepachangelog.com/)，版本遵循 [SemVer](https://semver.org/)。

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
