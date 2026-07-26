# sdd-workflow

> 版本 v1.0.1 ｜ [English](./README.en.md)

給 Claude Code、Codex 等 coding agent 使用的
**SDD（Spec-Driven Development，規格驅動開發）Skill**。

它把「先確認要做什麼，再允許 Agent 改程式」變成可持續、可恢復的工作流程：
範圍、任務、驗收條件、核准與進度都保存在專案內。這個 repo 的產品是完整的
Skill package，不是 protocol、SDK 或 developer kit。

## Skill 的目標

- 在任何產品程式碼變更前，先建立可審查的 proposal 與 task checklist。
- 只有明確核准的 proposal 才能進入實作；每次只完成並驗證一條 task。
- 需求改變時停止實作、留下修訂紀錄，並等待重新核准。
- 讓跨 session、交接、失敗重試與最後歸檔都能從專案中的權威狀態恢復。
- 狀態不一致或證據不足時 fail closed，不猜測、不靜默修復。

## 適合使用

- 需求需要先確認範圍與驗收條件，再允許 Agent 改碼。
- 變更包含多個可獨立驗證的步驟。
- 工作可能跨 session、Agent 交接或 context recovery。
- 實作或驗收期間可能改需求，需要保留修訂與重新核准紀錄。

## 通常不需要

- 唯讀問答、程式碼解釋、探索或一般研究。
- 你已明確要求直接完成的單一、低風險小修改。
- Git／程式碼 rollback、緊急復原或部署操作；這些不屬於 SDD proposal state。
- 沒有指向 SDD 提案的一般「取消」。

## 安裝

需求：CPython 3.11 以上；macOS 與 Linux 為支援平台，Windows 為 best effort。
必須安裝完整的 `skills/sdd-workflow/` 目錄，不能只複製 `SKILL.md`。

### Codex

在 Codex 對話中使用內建 installer：

```text
$skill-installer install skills/sdd-workflow from the GitHub repo kurotanshi/sdd-workflow into ~/.agents/skills
```

安裝位置是 `~/.agents/skills/sdd-workflow/`。若下一個 turn 未載入，請重新啟動
Codex。

### Claude Code

請 Claude Code 安裝完整 package：

```text
Install skills/sdd-workflow from https://github.com/kurotanshi/sdd-workflow into ~/.claude/skills/sdd-workflow
```

安裝位置是 `~/.claude/skills/sdd-workflow/`。若未載入，請開新 session。
手動安裝、驗證、更新與移除方式見
[`docs/install-methods.md`](./docs/install-methods.md)。

## 第一次 workflow

1. 建立提案：

   ```text
   $sdd-workflow 提案 幫我的專案新增健康檢查 API
   ```

   Claude Code 使用 `/sdd-workflow 提案 …`。Agent 會建立
   `sdd/<短名稱>/proposal.md` 與 `tasks.md`，驗證後停下，不修改產品程式碼。

2. 審閱提案後回覆 `開始實作`。Agent 會核准目前版本，逐條實作、驗證並更新
   task 進度。只說 `實作` 不會自動核准 draft。

3. 需求改變時直接說明新需求。Agent 會停止改碼、修訂 proposal，等待新的
   `開始實作`。

4. 所有 task 完成且你驗收後，回覆 `歸檔 <短名稱>`。提案會移至
   `sdd/archive/`。

可重播完整案例：`python3 examples/sample-web-api/run-walkthrough.py`

## 工作方式與安全邊界

| 階段 | 你的動作 | Agent 的邊界 |
| --- | --- | --- |
| 提案 | `提案` | 寫 proposal 與 tasks，驗證後停下，不改產品碼 |
| 核准／實作 | `開始實作` / `實作` | 只對已核准 proposal 逐條實作與驗證 |
| 修訂 | 說明需求變更 | 停止改碼，更新 proposal，等待重新核准 |
| 歸檔 | `歸檔 <短名稱>` | 只在可靠 task 全數完成且使用者驗收後歸檔 |
| 放棄 | `放棄` / `取消提案`，再 `確認放棄 <短名稱>` | 先顯示唯讀 preflight；不復原程式碼或 Git |

可用 `$sdd-workflow` 或 `/sdd-workflow` 明確啟動流程。Skill 不會因一般的
「分析」或「取消」自動擴張觸發範圍。

單獨說「取消」只會先詢問你是要復原程式碼/Git，還是放棄 SDD proposal。
Source-control rollback 是另一項操作，不會連帶修改 proposal state。

bundled CLI 是 proposal 狀態、task 進度、snapshot、metadata、archive 與 INDEX
的權威。不要手動改 status、checkbox、`.sdd` metadata、archive 目錄或
`INDEX.md`。遇到錯誤時依穩定的 `code` 與 `action` 處理；不要用猜測或重跑
掩蓋不一致。

## v1.0.1

這個 patch release 保持 proposal schema v1/v2、JSON output v1 與既有 Skill
流程相容，並修正：

- 已完成部分 task 後，合法修訂新增或移除尾端待辦 task 可重新核准。
- reapproval 在 manifest／metadata 寫入中斷後可安全重試。
- 可讀但不可變更的 legacy proposal 不再讓 mutation 指令誤報成功；它會以
  穩定錯誤停止且不寫入。

從舊版更新時請替換完整 package，不要混合不同版本的檔案。

## 文件

- 安裝、更新與移除：[`docs/install-methods.md`](./docs/install-methods.md)
- 團隊交接與 worktree：[`docs/team-operations.md`](./docs/team-operations.md)
- 診斷與恢復：[`docs/troubleshooting.md`](./docs/troubleshooting.md)
- 版本紀錄：[`CHANGELOG.md`](./CHANGELOG.md)
- 貢獻與測試：[`CONTRIBUTING.md`](./CONTRIBUTING.md)

Skill 的單一維護來源是
[`skills/sdd-workflow/`](./skills/sdd-workflow/)；安裝副本不是第二份來源。

## 致謝

本 repo / Skill 受到 @kaochenlong 在 2026 AI 年會分享的
[SimpleSDD](https://gist.github.com/kaochenlong/27ade9a6218244c2584777fa276d1214)
啟發。

## License

MIT（見 [LICENSE](./LICENSE)）
