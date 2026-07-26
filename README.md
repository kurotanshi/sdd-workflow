# sdd-workflow

> 版本 v1.0.0 ｜ [English](./README.en.md)

一份給 Claude Code、Codex 等 coding agent 使用的
**SDD（Spec-Driven Development，規格驅動開發）Skill**。

它要求 Agent 在改程式前先把範圍、任務與驗收條件寫成可版控提案，取得明確
核准後逐項實作與驗證。這個 repo 的產品是 Skill package，不是 protocol、
SDK 或 developer kit。

## 適合使用

- 需求需要先確認範圍與驗收條件，再允許 Agent 改碼。
- 變更包含多個可驗證步驟，可能跨 session、交接或中途恢復。
- 實作或驗收期間可能改需求，需要留下修訂與重新核准紀錄。
- 你希望 proposal、task 進度與最後歸檔可以一起進版控。

## 通常不需要

- 唯讀問答、程式碼解釋、探索或一般研究。
- 你已明確要求直接完成的單一、低風險小修改。
- Git／程式碼 rollback、緊急復原或部署操作；這些不屬於 SDD proposal state。
- 沒有指向 SDD 提案的一般「取消」。

你仍可用 `$sdd-workflow` 或 `/sdd-workflow` 明確要求採用流程；Skill 不會因
一般的「分析」或「取消」自然語言自動擴張觸發面。

## 安裝

請安裝完整的 `skills/sdd-workflow/` 目錄，不能只複製 `SKILL.md`；bundled
scripts 與 references 是 Skill 的內部組成。

### Codex

在 Codex 對話中使用內建 installer：

```text
$skill-installer install skills/sdd-workflow from the GitHub repo kurotanshi/sdd-workflow into ~/.agents/skills
```

安裝位置是 `~/.agents/skills/sdd-workflow/`。若下一個 turn 未載入 Skill，
請重新啟動 Codex。

### Claude Code

請 Claude Code 安裝完整 package：

```text
Install skills/sdd-workflow from https://github.com/kurotanshi/sdd-workflow into ~/.claude/skills/sdd-workflow
```

安裝位置是 `~/.claude/skills/sdd-workflow/`。若未載入，請開新 session。
手動安裝、驗證、更新與移除方式見
[`docs/install-methods.md`](./docs/install-methods.md)。

## 第一次 workflow

1. 在要修改的專案中建立提案：

   ```text
   $sdd-workflow 提案 幫我的專案新增健康檢查 API
   ```

   Claude Code 使用 `/sdd-workflow 提案 …`。Agent 會建立
   `sdd/<短名稱>/proposal.md` 與 `tasks.md`，驗證內容後停下，不改產品程式碼。

2. 看完提案後回覆 `開始實作`。Agent 會核准目前提案，依序實作、驗證並完成
   task。草稿狀態只說 `實作` 時，Agent 會先詢問是否要核准。

3. 需求改變時直接提出新需求。Agent 會停止實作、修訂提案，再等待新的
   `開始實作`。

4. 所有 task 完成且你驗收後，回覆 `歸檔`。提案會移至 `sdd/archive/`。

可重播案例：

```text
python3 examples/sample-web-api/run-walkthrough.py
```

## 工作方式與安全邊界

| 階段 | 你的動作 | Agent 的邊界 |
| --- | --- | --- |
| 提案 | `提案` | 寫 proposal 與 tasks，驗證後停下，不改產品碼 |
| 實作 | `開始實作` / `實作` | 只對已核准提案逐條實作與驗證 |
| 修訂 | 說明需求變更 | 停止改碼，更新提案，等待重新核准 |
| 歸檔 | `歸檔` | 只在可靠 task 全數完成後歸檔 |
| 放棄 | `放棄` / `取消提案`，再 `確認放棄 <短名稱>` | 先顯示唯讀 preflight；不復原程式碼或 Git |

單獨說「取消」只會先詢問你是要復原程式碼/Git，還是放棄 SDD proposal。
Source-control rollback 不會連帶修改 proposal state。

若 Skill 回報 proposal state、runtime 或 evidence 不一致，請停止並依它提供的
明確動作處理；不要手動改 status、checkbox、metadata 或 archive 目錄。

已知限制：v1.0.0 在「已完成部分 task 後，修訂並新增待辦 task」的重新核准
可能以 `OUT_OF_BAND_DRIFT` 停止。這時不要繞過核准或手動修復，請保留現場並
參考 [`docs/troubleshooting.md`](./docs/troubleshooting.md)。

## 需要更多協助

- 安裝與更新：[`docs/install-methods.md`](./docs/install-methods.md)
- 團隊交接與 worktree：[`docs/team-operations.md`](./docs/team-operations.md)
- 診斷與恢復：[`docs/troubleshooting.md`](./docs/troubleshooting.md)
- 貢獻與測試：[`CONTRIBUTING.md`](./CONTRIBUTING.md)

Skill 的單一維護來源是
[`skills/sdd-workflow/`](./skills/sdd-workflow/)；安裝副本不是第二份來源。

## 致謝

本 repo / Skill 受到 @kaochenlong 在 2026 AI 年會分享的
[SimpleSDD](https://gist.github.com/kaochenlong/27ade9a6218244c2584777fa276d1214)
啟發。

## License

MIT（見 [LICENSE](./LICENSE)）
