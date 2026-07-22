# Contributing to sdd-workflow

> [English](./CONTRIBUTING.en.md)

感謝貢獻！這份文件說明這個 repo 的維護規則。

## 唯一的來源：canonical skill

**所有流程行為只能改一個檔案：[`skills/sdd-workflow/SKILL.md`](./skills/sdd-workflow/SKILL.md)。**

- 三階段（提案／實作／歸檔）、修訂／放棄路徑、狀態轉移、產出格式與進度回報方式，全部住在這裡。
- 安裝到 `~/.claude/skills/`、`~/.codex/skills/`、`~/.agents/skills/` 的副本都是**可重新產生的安裝產物**，不是第二份來源。**絕對不要**只改某個工具目錄裡的副本——那會造成分歧。
- 不要為了單一工具再開 command／prompt 變體。跨工具差異只反映在「怎麼呼叫」（README 的觸發語法表），不反映在流程規則。

## Repo 版面

```
sdd-workflow/
├── README.md / README.en.md    # 中英雙語使用說明
├── CONTRIBUTING.md / CONTRIBUTING.en.md
├── CHANGELOG.md
├── LICENSE
├── scripts/
│   └── link-dev.sh             # 作者 dev-link 工具（非一般安裝方式）
└── skills/
    └── sdd-workflow/           # ← canonical skill，唯一流程來源
        ├── SKILL.md
        └── agents/
            └── openai.yaml     # 只放 Codex UI／invocation metadata，不承載流程規則
```

### skill 資料夾要保持乾淨

`skills/sdd-workflow/` 內**只放** `SKILL.md` 與 `agents/openai.yaml`（以及 skill 真的需要的 `scripts/`、`references/`、`assets/`）。**不要**在 skill 資料夾內放 `README.md`、`CHANGELOG.md`、安裝說明等——那些對外文件一律放在 **repo 根目錄**。這是 Agent Skills 的慣例（skill 只裝 agent 執行任務所需的內容）。

`agents/openai.yaml` 只放 metadata（`display_name`、`short_description`、`default_prompt`）。`default_prompt` 需以 `$sdd-workflow` 形式提及 skill 名稱。

## 本機開發流程

1. 改 `skills/sdd-workflow/SKILL.md`（或其 metadata）。
2. 用 dev-link 讓改動即時生效：

   ```bash
   scripts/link-dev.sh                # 或 --claude-only / --codex-only
   scripts/link-dev.sh --unlink       # 收工
   ```

   - 只在目的地不存在時建立指向本 repo 的 symlink；遇到既有檔案／目錄／其他 symlink 會停止不動。
   - 目標目錄可用 `CLAUDE_SKILLS_DIR`、`CODEX_SKILLS_DIR` 覆寫（hermetic 測試或指定已驗證的 Codex skill root）。
3. 送 PR 前建議跑 frontmatter／命名的權威檢查（若你的環境有 Codex skill-creator）：

   ```bash
   python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/sdd-workflow
   ```

## 驗收責任（互動測試由人執行）

自動化只能涵蓋**靜態與 hermetic** 檢查（skill 結構、frontmatter、文件、dev-link 行為）。

**跨工具的實際流程驗收必須由人在各自的全新互動 session 操作**，不能只靠 agent 自動跑過：

- Claude Code：新 session 用 `/sdd-workflow 提案 …` 走完 提案 → 批准 → 實作 → 歸檔；另在獨立 session 用自然語言確認會自動選用 skill 並停在等確認。
- Codex：新 session 用 `$sdd-workflow 提案 …` 走完相同三階段；另確認自然語言 implicit invocation。
- Skill 變更後可能需要開新對話／重啟才會載入；不要把「沒載入」誤判為「通過」。

每個工具至少驗證以下行為：

- 新提案寫入 `draft` 並停下；對 `draft` 只說「實作」會詢問核准，「開始實作」才會持久化為 `approved`。
- 沒有活動提案或缺少 `proposal.md`／`tasks.md` 時要求實作會停止，不修改產品程式碼。
- 修訂會保留已勾任務、追加新編號、重設為 `draft` 並再次等待核准。
- 完成歸檔只掃描「驗收條件」前的 task checkbox，日期來自執行環境，終態為 `completed`，且 `archive/INDEX.md` 新增摘要。
- 「放棄」／「取消」會產生 `-abandoned` 歸檔、寫入 `abandoned` 狀態與 INDEX 摘要。
- 未經使用者要求不會建立 git commit。

### Codex 子代理輔助驗收（可選）

Codex 可以建立子代理協助跑**非互動式**驗收。這適合把 noisy、可並行的檢查移出主 thread，例如文件命令核對、靜態驗證、hermetic dev-link 測試、repo 結構掃描。它不適合取代 fresh Codex TUI 驗收，因為子代理繼承目前 session、sandbox 與 workspace，不是一個全新的互動式 Codex CLI session。

建議在主 Codex thread 明確要求子代理只做 read-heavy 或 hermetic 檢查，並等全部回報後再彙整：

```text
請建立 4 個子代理協助驗收目前 repo，但不要修改檔案。每個子代理回報 finding、證據與殘留風險即可。

1. 文件命令驗收：核對 README.md / README.en.md / CONTRIBUTING.md 內的 install、update、remove、validator 指令是否符合目前 CLI help，並指出不能在本機證明的 GitHub 發佈前提。
2. skill 結構驗收：檢查 skills/sdd-workflow/ 只含 SKILL.md 與 agents/openai.yaml，openai.yaml 只承載 metadata，repo 內沒有舊 commands/prompts/install.sh。
3. dev-link 驗收：在暫存目錄用 CLAUDE_SKILLS_DIR / CODEX_SKILLS_DIR 跑 scripts/link-dev.sh 的 link、only flag、unlink、既有目的地衝突與 idempotency 測試。
4. Codex 載入邊界驗收：檢查目前已安裝的 Codex skill 與 repo canonical skill 是否一致，並明確列出哪些事項仍必須由 fresh Codex session 手動確認。

等 4 個子代理都完成後，請彙整成 PASS / FAIL / BLOCKED，列出需要人工操作的剩餘驗收。
```

子代理可協助判斷：

- repo 內的 skill package 是否有效。
- 文件裡的命令是否能由目前工具支援。
- `scripts/link-dev.sh` 是否在暫存目錄安全運作。
- 已安裝副本與 repo canonical skill 是否分歧。

子代理不能證明：

- 新的 Codex session 一定會載入剛安裝的 skill。
- `$sdd-workflow` 會出現在互動式選單或能被 fresh TUI 正確呼叫。
- `提案 → 實作 → 歸檔` 的互動流程已在真實 Codex session 完整跑過。

因此最終仍要由人在 fresh Codex session 執行：

```text
$sdd-workflow 提案 建立一個測試文字檔
```

確認它停在提案等待批准後，再回覆「開始實作」，驗收產物，最後回覆「歸檔」。另開一個獨立 session 測自然語言觸發，例如：

```text
提案：建立一個測試文字檔
```

## 觸發語法差異（提醒）

- Claude Code：`/sdd-workflow`
- Codex：`$sdd-workflow`
- 兩邊都可用繁中「提案／開始實作／實作／歸檔／放棄／取消」自然觸發。

安裝、更新、移除指令依安裝通路而不同，見 README；不要混用某一通路的路徑或 ownership 假設。
