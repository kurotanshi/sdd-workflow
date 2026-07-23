# sdd-workflow

> 版本 v0.6.0 ｜ [English](./README.en.md)

一份跨 AI coding agent 共用的 **SDD（Spec-Driven Development，規格驅動開發）** skill。核心理念一句話：**動手寫程式之前，先把要做什麼寫清楚、讓人確認，再開始做。**

它把每個需求切成三個階段，另有修訂與放棄路徑；需要核准的地方都會停下來等你確認：

| 階段 | 觸發詞 | 做什麼 |
| --- | --- | --- |
| 1. 提案 | `提案` | 取短名稱、判斷類型，產出狀態為 `draft` 的 `proposal.md` 與 `tasks.md`，然後**停下等確認，不寫程式**；修訂既有提案也使用這個觸發詞 |
| 2. 實作 | `開始實作`／`實作` | `開始實作` 由 CLI 把 `draft` 核准為 `approved`；`實作` 只會繼續已核准提案。之後逐條完成任務、驗證，再由 CLI 寫入完成狀態並回報 |
| 3. 歸檔 | `歸檔` | 驗收且任務全數完成後，由 CLI 原子地準備終態、搬移目錄並重建 `sdd/archive/INDEX.md` |
| 放棄 | `放棄`／`取消提案` → `確認放棄 <短名稱>` | 先由內附 CLI 執行唯讀 preflight：回報進度、警告工作區程式碼不會復原、把 snapshot hash 列在回報中；`tasks.md` 格式錯誤不會擋下放棄，只會標明任務計數不可靠。收到一字不差的 `確認放棄 <短名稱>` 後重跑 preflight 並以機器比對 snapshot，內容未變才由 CLI 歸檔為 `abandoned` 並重建索引；單獨說「取消」只會先詢問目標 |

產出物都是純文字，留在你的專案 `sdd/` 目錄，跟著 git 一起版控。

這個 repo **唯一維護的流程來源**是 [`skills/sdd-workflow/SKILL.md`](./skills/sdd-workflow/SKILL.md)。安裝到各工具的副本只是可重新產生的安裝產物，不是第二份來源。

Deterministic parser、transaction engine 與後續 schema 的分階段工程計畫及設計取捨，見 [`ROADMAP.md`](./ROADMAP.md)。

> 裸 `取消` 不是直接 Skill trigger；只有使用者明指 SDD proposal 或已明確進入 workflow 時，才套用 Skill 內的取消消歧規則。明確的 code-revert 請求屬於 workflow 外操作，但在改檔前仍必須確認精確範圍，且不得因此改動 proposal state。

## v0.6 Schema、runtime 與團隊契約

v0.6.0 必須有 **CPython 3.11 以上**；macOS 與 Linux 為支援平台，Windows 目前只提供 best-effort Python core。v0.3.0 引入 runtime 時是 `0.x` 的 **breaking minor**；此要求延續至今。新提案使用明確的 Schema v2，類型可為 `新功能`、`修 bug`、`重構`、`維運`、`文件` 或 `研究`；研究沿用相同 lifecycle，並以 `## 結論` 保存輸出。既有 v1/legacy artifacts 不會原地 migration。CLI 或 runtime 不可用時一律 fail closed，不回退到 agent 直接解析或修改 managed state。完整契約見 [`docs/schema-v2.md`](./docs/schema-v2.md)、[`docs/runtime.md`](./docs/runtime.md)、[`docs/cli-contract.md`](./docs/cli-contract.md) 與 [`docs/transaction-protocol.md`](./docs/transaction-protocol.md)。

安裝或升級後，先在 package 內執行 `skills/sdd-workflow/scripts/sdd.py --version`（安裝副本使用對應路徑）。v1 proposals 可繼續由 v0.6 engine 管理；Schema v2 proposal 不可交給只支援 v1 的 engine。已有 `.sdd` machine metadata 的進行中 proposal 必須以相容 engine 完成或放棄，刪除 metadata 或 schema marker 不構成受支援的降級。

團隊並行時，每個 proposal 同一時間只交由一位 owner；獨立工作使用不同 short name，修改可能互相干擾時再搭配不同 Git worktree。Archive directories 是 authoritative，`INDEX.md` 是可由 `validate-index`／`rebuild-index` 檢查與重建的 derived artifact。v0.6.0 的 contention tests 沒有發現 authoritative data loss，因此沒有預先加入 lock 或 INDEX CAS。完整交接、worktree、version-skew 與 stale INDEX 程序見 [`docs/team-operations.md`](./docs/team-operations.md) 與 [`docs/compatibility.md`](./docs/compatibility.md)。

## 工作流程

```mermaid
sequenceDiagram
    actor User as 使用者
    participant Agent as AI Coding Agent
    participant Files as sdd/ 目錄

    Note over User, Agent: 1. 提案階段 (Proposal Phase)
    User->>Agent: 「提案：幫專案新增 OOO 功能」
    Agent->>Files: 建立 draft proposal.md & tasks.md
    Agent->>User: 顯示提案規格、工作清單與驗收條件
    Note over Agent: 停下等待確認，不修改任何程式碼
    Note over User, Files: 其他路徑：修訂會重設 draft；放棄先 preflight，回覆「確認放棄 <短名稱>」才歸檔為 abandoned 並更新 INDEX.md

    Note over User, Agent: 2. 實作階段 (Implementation Phase)
    User->>Agent: 「開始實作」
    Agent->>Files: CLI approve 寫入 manifest、metadata 與 approved 狀態
    loop 逐條任務執行
        Agent->>Files: 檢查並實作 tasks.md 中第一條未勾選任務
        Agent->>Agent: 執行測試/驗證
        Agent->>Files: CLI complete-task 驗證 snapshot 後寫入 [x]
        Agent->>User: 回報「第 N 條完成」
    end
    Agent->>User: 全部完成，請使用者驗收

    Note over User, Agent: 3. 歸檔階段 (Archive Phase)
    User->>Agent: 「歸檔」
    Agent->>Files: 檢查 tasks.md 是否全數完成
    Agent->>Files: CLI archive 標記 completed 並移至 archive
    Agent->>Files: 從 archive records 全量重建 INDEX.md
    Agent->>User: 回報「歸檔完成」與單句變更摘要
```

### 目錄結構

```text
專案根目錄/
└── sdd/
    ├── <短名稱>/             # 活動中的變更提案 (例如: sdd/add-health-check/)
    │   ├── proposal.md       # Schema v2、狀態、類型、原因與影響範圍
    │   ├── tasks.md          # 頂層 checkbox 任務清單（新提案最多 10 條）與驗收條件
    │   └── .sdd/             # approval manifest、attestation 與 operation evidence
    └── archive/              # 已完成或放棄的歷史紀錄
        ├── INDEX.md          # 日期、短名稱、終態與單句摘要
        ├── YYYY-MM-DD-<短名稱>/
        │   ├── proposal.md   # 狀態為 completed
        │   └── tasks.md      # 任務皆為 [x] 狀態
        └── YYYY-MM-DD-<短名稱>-abandoned/
            ├── proposal.md   # 狀態為 abandoned
            └── tasks.md
```

### 產出物範本預覽

`sdd/<短名稱>/proposal.md` 範例：

```markdown
---
schema_version: 2
---
# add-health-check

## 狀態
draft

## 類型
新功能

## 為什麼做
為了讓監控系統能確認服務是否正常運作。

## 要改什麼
- 新增 `/api/health` 路由，回傳 JSON `{"status": "ok"}`。

## 影響範圍
- 新增：`src/routes/health.js`
- 修改：`src/app.js`
```

`sdd/<短名稱>/tasks.md` 範例：

```markdown
- [ ] 1. 新增健康檢查路由檔案，處理 GET /api/health
- [ ] 2. 在主程式 app.js 註冊該路由
- [ ] 3. 新增單元測試確保回傳 status ok

## 驗收條件
- 情境：當發送 GET 請求至 /api/health，應收到 200 狀態碼與 JSON `{"status": "ok"}`
```

## 安裝與上手

> [!IMPORTANT]
> **安裝後注意事項**：安裝或更新 Skill 後，通常需要**開新的對話 session**（例如重啟 Claude Code）才會載入；在已開啟的舊對話中輸入指令，Agent 可能無法辨識新安裝的 Skill。例外：用 Codex 內建 skill-installer 安裝時，同一對話的**下一個 turn** 就會生效。

依你使用的工具擇一安裝。各通路的目的地由該安裝工具自己管理，本 repo 不另外提供給一般使用者用的自製 installer。

### Codex

在 Codex 對話中請內建的 skill-installer 從本 repo 安裝：

```text
$skill-installer 從 GitHub 安裝 kurotanshi/sdd-workflow 的 skills/sdd-workflow
```

底層等同 `install-skill-from-github.py --repo kurotanshi/sdd-workflow --path skills/sdd-workflow`，會裝進 `~/.codex/skills/sdd-workflow/`，並在**下一個 turn** 生效。（手動安裝：把整個 `skills/sdd-workflow/` 資料夾複製到 `~/.codex/skills/sdd-workflow`。）

開一個新的 Codex 對話驗證：

```text
$sdd-workflow 提案 幫我的專案加一個健康檢查 API
```

### Claude Code

Claude Code 沒有內建的「從 GitHub 裝 skill」指令，最快的方式是直接請它自己裝：

```text
幫我把 https://github.com/kurotanshi/sdd-workflow 的 skills/sdd-workflow 安裝到 ~/.claude/skills/sdd-workflow
```

不想讓 agent 動手，就手動安裝：

```bash
rm -rf /tmp/sdd-workflow
git clone https://github.com/kurotanshi/sdd-workflow.git /tmp/sdd-workflow
mkdir -p ~/.claude/skills
cp -R /tmp/sdd-workflow/skills/sdd-workflow ~/.claude/skills/sdd-workflow
```

> 要複製**整個 `skills/sdd-workflow/` 資料夾**（含 `agents/`，不是只複製 `SKILL.md`）。若 `~/.claude/skills/sdd-workflow` 已存在（重裝），請先刪掉舊資料夾。Claude Code v2.1.203+ 亦支援 symlinked skill。

開一個新的 Claude Code session 驗證：

```text
/sdd-workflow 提案 幫我的專案加一個健康檢查 API
```

### 其他通路：跨 agent Skills CLI（第三方）

[`npx skills`](https://skills.sh/) 是開放 agent skills 生態的套件管理器，可一次餵給多種 agent：

```bash
npx skills add kurotanshi/sdd-workflow --skill sdd-workflow -g -y
```

`-g` 裝在使用者層、`-y` 略過確認。安裝來源會記錄在該工具的 lock file。

> ⚠️ 這是第三方工具（skills.sh），不是 OpenAI 或 Anthropic 官方 installer。它把 skill 放進共用的 `~/.agents/skills/`。**請自行確認你的 agent 真的會載入該目錄**——不同工具讀取的 skill 路徑不同（例如 Codex 內建工具鏈使用 `~/.codex/skills`）；若沒被載入，請改用上方各工具的原生安裝方式。

## 使用方式

兩個工具的觸發語法：

| 工具 | 明確指令觸發 | 也可自然語言觸發 |
| --- | --- | --- |
| [Claude Code](https://claude.com/claude-code)（Anthropic） | `/sdd-workflow 提案 …` | 直接說「提案：…」／「開始實作」／「實作」／「歸檔」／「放棄」（執行放棄需再回覆「確認放棄 <短名稱>」） |
| [Codex](https://github.com/openai/codex)（OpenAI/GPT） | `$sdd-workflow 提案 …` | 直接說「提案：…」／「開始實作」／「實作」／「歸檔」／「放棄」（執行放棄需再回覆「確認放棄 <短名稱>」） |

明確指令是首選（可預期、不靠模型猜）；自然語言觸發是便利功能，靠模型依 skill 描述自動選用。若工具沒有自動選到 skill，請改用明確指令語法。

> Skill 指令本體為英文（利於跨工具維護），但**觸發詞與對你的輸出維持繁中**。

正常流程會分三步走：

1. **提案**：agent 建立狀態為 `draft` 的 `proposal.md` 與 `tasks.md`。每條任務都應對應一個可獨立驗證的行為改變，完整清單最多 10 條；任務 checkbox 一律置於行首、維持頂層清單，不使用 checkbox 子任務。建立後停下等待確認，不修改產品程式碼。
2. **實作**：看完提案後回覆「開始實作」，agent 會先把狀態寫成 `approved` 並重新讀取確認，再一次完成一條任務。若提案仍是 `draft` 而你只說「實作」，agent 會先詢問是否核准，不會直接動碼。發現規格不對時會停止，修訂提案、保留已完成紀錄並回到 `draft` 等待重新核准；已勾任務屬歷史紀錄不占配額，修訂後未勾任務最多 10 條，若修訂實質改變原目標會建議另開新變更。
3. **歸檔**：驗收完成後回覆「歸檔」。agent 只計算「驗收條件」之前、行首頂層的 task checkbox，確認至少一條且全部完成；若出現縮排、巢狀或 `- [X]` 等格式異常的 checkbox 行，或任務區內混入其他清單項——包含以 Markdown 連結開頭的項目，如 `- [參考](https://…)`——會指出行號並停止歸檔。通過後再由執行環境取得日期、標記為 `completed`、移到 `sdd/archive/<日期>-<短名稱>/`，並把摘要追加到 `INDEX.md`。

不再進行的活動提案可回覆「放棄」、「放棄 <短名稱>」或「取消提案」。agent 會先呼叫內附 CLI 執行**唯讀的 preflight**：回報狀態、進度與 snapshot，並明確提醒放棄只歸檔 `sdd/` 產出物，已寫入工作區的程式碼與 git 變更**不會自動復原**。`tasks.md` 格式錯誤不會擋下 preflight，但計數會明確標為不可靠。你回覆一字不差的「確認放棄 <短名稱>」後，agent 會重跑 CLI preflight，由執行環境機器比對對話中與最新的兩個 hash，不目視比對長字串。內容未變才會標記 `abandoned`、移至 `sdd/archive/<日期>-<短名稱>-abandoned/` 並更新 `INDEX.md`；名稱不符、snapshot 不符或跨 session 沒有 snapshot 時會重新 preflight。單獨說「取消」或指涉不明時只會先詢問目標；明確指向程式碼的取消屬於 workflow 外復原，要先確認範圍且不得改動提案。未經你要求，workflow 不會自行建立 git commit。

## 更新與移除

| 工具／通路 | 更新 | 移除 |
| --- | --- | --- |
| Codex | 先刪 `${CODEX_HOME:-$HOME/.codex}/skills/sdd-workflow` 再重裝（installer 遇既有目錄會中止） | 刪除 `${CODEX_HOME:-$HOME/.codex}/skills/sdd-workflow` |
| Claude Code | 先刪 `~/.claude/skills/sdd-workflow` 再重新安裝 | 刪除 `~/.claude/skills/sdd-workflow` |
| Skills CLI（第三方） | `npx skills update sdd-workflow -g -y` | `npx skills remove sdd-workflow -g -y` |

## 作者／貢獻者：本機開發

> 這一段只給要**修改這個 repo 的 skill 本身**的人看，一般使用者請用上方〈安裝與上手〉的方式。

一般安裝是「複製」：工具讀的是 `~/.claude/skills/` 或 `~/.codex/skills/` 裡的副本，你在 repo 改了 `SKILL.md`，副本不會跟著變，每次都要重新複製才能測試。

`scripts/link-dev.sh` 用 symlink 取代複製，讓工具的 skills 目錄直接指向本 repo 的 `skills/sdd-workflow/`。之後在 repo 的任何修改，開新 session 就會直接生效：

```bash
scripts/link-dev.sh                # link 進 Claude Code 與 Codex
scripts/link-dev.sh --claude-only  # 只 Claude
scripts/link-dev.sh --codex-only   # 只 Codex
scripts/link-dev.sh --unlink       # 收工時移除 symlink
scripts/link-dev.sh --help
```

`link-dev.sh` 是防呆的：目的地已有檔案／資料夾／別的 symlink 時一律停止不動（不會蓋掉你已安裝的版本）；`--unlink` 也只移除確定指向本 repo 的 symlink。目標目錄可用 `CLAUDE_SKILLS_DIR`、`CODEX_SKILLS_DIR` 環境變數覆寫（供 hermetic 測試或指定已驗證的 Codex skill root）。

> symlink 好之後，記得分別在 Claude Code 與 Codex 開**新 session** 確認 skill 真的有載入。

## 致謝

本 repo / skill 受到 @kaochenlong 在 2026 AI 年會分享的 [SimpleSDD](https://gist.github.com/kaochenlong/27ade9a6218244c2584777fa276d1214) 啟發。

## License

MIT（見 [LICENSE](./LICENSE)）
