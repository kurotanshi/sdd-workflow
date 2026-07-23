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
        ├── scripts/                # deterministic readonly CLI 與 Python core
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

## CI 與團隊並行

受保護 branch 使用五個穩定且可獨立設為 required 的 check：`unit`、`fixtures`、`package-validation`、`docs-consistency`、`install-smoke`。其中 unit 與 install matrix 覆蓋 macOS／Linux 和最低／最新 Python；release package、Claude/Codex 安裝目的地與 dev-link 都在隔離暫存目錄驗證。新增或改名 check 時，必須同步 `.github/workflows/ci.yml`、`tests/test_ci_contract.py` 與 `tests/docs_consistency.py`。

一個 proposal 同一時間只能有一位 owner。獨立變更使用不同 short name；實作檔案可能重疊時，使用不同 Git worktree。交接前停止 mutation 並提供最新狀態，接手者必須重新執行 `status`，不得沿用交接訊息裡的 snapshot。Archive directories 是 authority；若並行歸檔令 `INDEX.md` 暫時 stale，依序執行 `validate-index`、`rebuild-index`、`doctor`，不要手動合併 INDEX。完整契約見 [`docs/team-operations.md`](./docs/team-operations.md)。

## 驗收責任（互動測試由人執行）

自動化只能涵蓋**靜態與 hermetic** 檢查（skill 結構、frontmatter、文件、dev-link 行為）。

**跨工具的實際流程驗收必須由人在各自的全新互動 session 操作**，不能只靠 agent 自動跑過：

- Claude Code：新 session 用 `/sdd-workflow 提案 …` 走完 提案 → 批准 → 實作 → 歸檔；另在獨立 session 用自然語言確認會自動選用 skill 並停在等確認。
- Codex：新 session 用 `$sdd-workflow 提案 …` 走完相同三階段；另確認自然語言 implicit invocation。
- Skill 變更後可能需要開新對話／重啟才會載入；不要把「沒載入」誤判為「通過」。

### fresh-session 人工驗收矩陣

「靜態檢查可證明」指可從 `SKILL.md`／文件文字或 fixture 模擬直接證明的部分；「fresh-session 互動驗收」是必須由人在全新 session 實際操作確認的行為。**靜態檢查通過不代表互動行為通過**，兩欄都要滿足。

| 驗收項目 | 靜態檢查可證明 | fresh-session 互動驗收 |
| --- | --- | --- |
| 提案建立 | 範本含 `## 狀態` 且值為 `draft` | 建立後停下等核准，不修改產品程式碼 |
| 核准語意 | CLI transition tests 與 Skill command rule | `draft` 只說「實作」會詢問；「開始實作」以 snapshot 呼叫 `approve` 並驗證 manifest、metadata 與 `approved` |
| 缺檔防呆 | 規則文字存在 | 缺目錄或任一 artifact 時要求先提案、不動程式碼 |
| 修訂 | 規則文字存在 | 保留已勾任務、未勾任務最多 10 條、重設 `draft` 重新等核准；實質改變目標時建議另開新變更 |
| deterministic read 與 managed mutation path | `SKILL.md` 只定義 CLI orchestration；parser、transition 與 failure-injection tests 可重現結果 | agent 不自行解析 artifact，也不直接改既有 status、checkbox、metadata、archive location 或 INDEX；嚴格錯誤在 mutation 前停止，只有放棄 preflight 降級計數 |
| 放棄 preflight | `abandon-preflight` fixtures 驗證警告、計數與 snapshot | 「放棄」／「取消提案」只回報 CLI 進度、警告與兩個 hash 後停止；狀態、目錄與 INDEX 均未變 |
| 確認放棄 | CLI terminal tests、snapshot 比對與 Skill rule | 一字不差的「確認放棄 <短名稱>」才重跑 preflight；執行環境比對 transcript 與最新 JSON 內的兩個 hash，不目視比對；相符時呼叫 `abandon`，不符時重新確認 |
| 「取消」語意 | 規則文字存在 | 單獨輸入「取消」或指涉不明時先詢問要復原程式碼還是放棄提案，不直接執行任一種；明確指向程式碼的取消當一般復原請求處理——先確認範圍，絕不觸碰提案；未指名階段的選單列「取消提案」，不出現單獨的「取消」選項 |
| 完成歸檔 | terminal transition 與 failure-injection tests | `archive` 驗證 snapshot/manifest/attestation，directory move 是 commit point，完成後由 archive records 全量重建 INDEX |
| 共用終止程序 | SKILL.md 僅有一份 Terminal result procedure，CLI 共用 transaction engine | `archive` 與 `abandon` 共享 staging、move、retry 與 INDEX rebuild；move 後 INDEX 失敗不反向搬移 |
| Managed-state drift | attestation/doctor tests | 正常正文修改不造成 drift；status、checkbox 或 metadata 不符回報 `OUT_OF_BAND_DRIFT`，不得宣稱辨識修改者 |
| Schema v2 | Schema v2 fixtures、common-model 與 research archive tests | 新提案含明確 version；六種類型可讀；研究結論可歸檔重建；v1/legacy 不 migration，future version fail closed |
| 團隊／worktree 邊界 | CI contract、install matrix、worktree 與 concurrency tests | 同 proposal 維持單一 owner；不同 short name／worktree 不互相污染；stale INDEX 可偵測並重建 |
| git 行為 | 規則文字存在 | 全程未經使用者要求不建立 commit |

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
- 兩邊都可用繁中「提案／開始實作／實作／歸檔／放棄」自然觸發；執行放棄需再回覆一字不差的「確認放棄 <短名稱>」，單獨「取消」只會先詢問目標。

安裝、更新、移除指令依安裝通路而不同，見 README；不要混用某一通路的路徑或 ownership 假設。
