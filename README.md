# sdd-workflow

> 版本 v1.0.0 ｜ [English](./README.en.md)

一份讓 Claude Code、Codex 等 coding agent 共用的
**SDD（Spec-Driven Development，規格驅動開發）Skill**。

它解決一個常見問題：Agent 很容易在需求還沒說清楚時就開始改程式。
sdd-workflow 會先把範圍、任務與驗收條件寫成可版控的提案，等你明確核准，
再一次實作一條任務；規格變更時回到修訂與重新核准，不把新需求偷偷塞進驗收。

## 安裝

必須安裝完整的 `skills/sdd-workflow/` 目錄，不能只複製 `SKILL.md`。

### Codex

在 Codex 對話中使用內建 installer：

```text
$skill-installer install skills/sdd-workflow from the GitHub repo kurotanshi/sdd-workflow into ~/.agents/skills
```

目前使用者層路徑是 `~/.agents/skills/sdd-workflow/`；請保留指令中的目的地，
因為部分 installer 版本仍可能使用舊的預設路徑。Codex 通常會自動偵測新
Skill；若下一個 turn 未出現，再重新啟動 Codex。

### Claude Code

請 Claude Code 安裝完整 package：

```text
Install skills/sdd-workflow from https://github.com/kurotanshi/sdd-workflow into ~/.claude/skills/sdd-workflow
```

目前使用者層路徑是 `~/.claude/skills/sdd-workflow/`。Claude Code 通常會
自動偵測安裝或更新；若 Skill 未出現，再開新 session。手動安裝、第三方
Skills CLI、驗證、更新與移除方式見
[`docs/install-methods.md`](./docs/install-methods.md)。

## 第一次 workflow

在要修改的專案中開啟 Agent，依序進行：

1. 建立提案：

   ```text
   $sdd-workflow 提案 幫我的專案新增健康檢查 API
   ```

   Claude Code 使用 `/sdd-workflow 提案 …`。Agent 會建立
   `sdd/<短名稱>/proposal.md` 與 `tasks.md`，顯示 canonical 範圍與驗收條件，
   然後停下；這一步不改產品程式碼。

2. 看完提案後回覆 `開始實作`。這是對目前 canonical proposal 的明確核准。
   Agent 之後一次實作、驗證並完成一條 task。

3. 若實作或驗收時需求改變，直接說明新需求。Agent 會停止、執行受管
   revision、更新提案，再停下等待新的 `開始實作`。

4. 所有 task 完成且你驗收後，回覆 `歸檔`。提案會移至
   `sdd/archive/`；目前 runtime 建立的 managed archive records 可用來重建
   `INDEX.md`。

完整可重播案例在 [`examples/sample-web-api/`](./examples/sample-web-api/)：

```text
python3 examples/sample-web-api/run-walkthrough.py
```

它會實際示範 approval、task、scope drift、revision/reapproval、archive 與
INDEX rebuild，且只在暫存目錄執行。

## 工作方式與安全邊界

| 階段 | 明確觸發 | 保證 |
| --- | --- | --- |
| 提案 | `提案` | 建立 `draft` 規格，驗證後停下，不寫產品程式碼 |
| 實作 | `開始實作` / `實作` | 前者核准 draft；後者只繼續 approved proposal；每次一條 task |
| 修訂 | 說明需求變更 | 使舊核准失效，保留完成紀錄，回到 draft 等待重新核准 |
| 歸檔 | `歸檔` | 僅在可靠 task 全數完成時建立 completed archive |
| 放棄 | `放棄` / `取消提案` → `確認放棄 <短名稱>` | 先唯讀 preflight，再以相同 snapshot 執行；不復原程式碼或 Git |

Runtime 是 parsing、snapshot、managed transition 與 diagnostics 的唯一權威；
Agent 不會自行解析或直接修改 status、checkbox、machine metadata、archive
位置或 INDEX。找不到相容 runtime、狀態模糊或 evidence 不一致時一律 fail
closed，交回明確的人類動作。

單獨說「取消」只會先詢問你是要復原程式碼/Git，還是放棄 SDD proposal。
Source-control rollback 不會連帶修改 proposal state。

## 進階文件

| 主題 | 從這裡開始 |
| --- | --- |
| Concepts：protocol、approval、schema、archive authority | [`docs/concepts/`](./docs/concepts/) |
| Operations：日常操作、team handoff、runtime、release | [`docs/operations/`](./docs/operations/) |
| Compatibility：OS/Python/Agent、安裝與版本組合 | [`docs/compatibility/`](./docs/compatibility/) |
| Design：architecture、transaction、attestation、ADR | [`docs/design/`](./docs/design/) |
| Troubleshooting：doctor、安裝、recovery | [`docs/troubleshooting/`](./docs/troubleshooting/) |

Protocol 作者與 adapter 作者可直接閱讀
[`docs/protocol-draft.md`](./docs/protocol-draft.md)、
[`Agent Adapter Contract`](./docs/protocol/agent-adapter-contract.md) 與
[`docs/conformance.md`](./docs/conformance.md)。

這個 repo **唯一維護的 Skill 來源**是
[`skills/sdd-workflow/SKILL.md`](./skills/sdd-workflow/SKILL.md)；安裝副本是可
重新產生的 package artifact，不是第二份流程來源。

歷史工程規劃與設計取捨見 [`ROADMAP.md`](./ROADMAP.md)；目前 v1.0 的完成
狀態與驗證證據見
[`v1.0 release gate`](./docs/reports/v1.0-release-gate.md)。

## 本機開發

一般使用者不需要這一段。修改本 repo 的 contributor 可用 symlink 測試：

```text
scripts/link-dev.sh
scripts/link-dev.sh --claude-only
scripts/link-dev.sh --codex-only
scripts/link-dev.sh --unlink
```

預設目的地為 `~/.claude/skills/` 與 `~/.agents/skills/`；既有目的地不會被
覆寫。完整測試、conformance 與 release gate 見
[`docs/operations/`](./docs/operations/)。

## 致謝

本 repo / Skill 受到 @kaochenlong 在 2026 AI 年會分享的
[SimpleSDD](https://gist.github.com/kaochenlong/27ade9a6218244c2584777fa276d1214)
啟發。

## License

MIT（見 [LICENSE](./LICENSE)）
