# Contributing to sdd-workflow

> [English](./CONTRIBUTING.en.md)

感謝貢獻！這份文件說明這個 repo 的維護規則。

## 唯一產品：canonical Skill package

**本 repo 只維護一個產品：
[`skills/sdd-workflow/`](./skills/sdd-workflow/)。**

- `SKILL.md` 是 Agent 行為邊界與觸發規則的唯一來源；bundled scripts 與
  references 是 Skill 的內部實作，不是另一套 protocol 或 developer kit。
- deterministic runtime 可以強制執行 parser、mutation 與 archive 安全性；
  修改行為時必須同步檢查 Skill prose、runtime 與 regression，不得宣稱只改其中一份就能改變完整流程。
- 安裝到 `~/.claude/skills/`、`~/.codex/skills/`、`~/.agents/skills/` 的副本都是**可重新產生的安裝產物**，不是第二份來源。**絕對不要**只改某個工具目錄裡的副本——那會造成分歧。
- 不要為了單一工具再開 command／prompt 變體。跨工具差異只反映在「怎麼呼叫」（README 的觸發語法表），不反映在流程規則。

## Scope 與複雜度預算

- 每個 roadmap 項目在動工前標成「減（Reduce）、修（Fix）、量（Measure）、加（Add）」；「加」必須記錄具名
  requester 與未滿足需求，否則留在 backlog。
- 對外只溝通 Skill release、proposal artifact schema、JSON output version。
  handshake、attestation、manifest 等若保留，都是內部實作細節。
- 不建立第三方 adapter 計畫、公開 conformance kit、protocol freeze、
  deprecation policy、開發框架或通用 orchestration platform。
- 不增加自然語言 trigger、schema、Agent adapter、reference 或 recovery
  機制，除非有 field evidence 與獨立提案。
- 優先刪除重複承諾、合併同步來源與重用既有測試；檔案改名或把細節藏起來不算降低複雜度。

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
        ├── scripts/                # Skill 內部 deterministic runtime
        ├── references/             # 按需載入的操作細節
        └── agents/
            └── openai.yaml     # 只放 Codex UI／invocation metadata，不承載流程規則
```

### skill 資料夾要保持乾淨

`skills/sdd-workflow/` 內**只放** `SKILL.md` 與 `agents/openai.yaml`（以及 skill 真的需要的 `scripts/`、`references/`、`assets/`）。**不要**在 skill 資料夾內放 `README.md`、`CHANGELOG.md`、安裝說明等——那些對外文件一律放在 **repo 根目錄**。這是 Agent Skills 的慣例（skill 只裝 agent 執行任務所需的內容）。

`agents/openai.yaml` 只放 metadata（`display_name`、`short_description`、`default_prompt`）。`default_prompt` 需以 `$sdd-workflow` 形式提及 skill 名稱。

## 本機開發流程

1. 改 `skills/sdd-workflow/SKILL.md`（或其 metadata）。
2. 只要 `SKILL.md` 有任何 byte 變更（含空白），就同步刷新
   `skills/sdd-workflow/runtime-identity.json` 的 `skill_sha256`，否則
   `package-validation` 會以「runtime identity does not match SKILL.md bytes」
   失敗，且多筆 discovery／install-channel 單元測試會一起變紅：

   ```bash
   shasum -a 256 skills/sdd-workflow/SKILL.md
   # 把輸出的 hash 填回 runtime-identity.json 的 skill_sha256，然後驗證：
   PYTHONDONTWRITEBYTECODE=1 python3 tests/package_validation.py
   ```

3. 用 dev-link 讓改動即時生效：

   ```bash
   scripts/link-dev.sh                # 或 --claude-only / --codex-only
   scripts/link-dev.sh --unlink       # 收工
   ```

   - 只在目的地不存在時建立指向本 repo 的 symlink；遇到既有檔案／目錄／其他 symlink 會停止不動。
   - 目標目錄可用 `CLAUDE_SKILLS_DIR`、`CODEX_SKILLS_DIR` 覆寫（hermetic 測試或指定已驗證的 Codex skill root）。
4. 送 PR 前建議跑 frontmatter／命名的權威檢查（若你的環境有 Codex skill-creator）：

   ```bash
   python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/sdd-workflow
   ```

## CI 與團隊並行

受保護 branch 使用五個穩定且可獨立設為 required 的 check：`unit`、`fixtures`、`package-validation`、`docs-consistency`、`install-smoke`。其中 unit 與 install matrix 覆蓋 macOS／Linux 和最低／最新 Python；release package、Claude/Codex 安裝目的地與 dev-link 都在隔離暫存目錄驗證。新增或改名 check 時，必須同步 `.github/workflows/ci.yml`、`tests/test_ci_contract.py` 與 `tests/docs_consistency.py`。

一個 proposal 同一時間只能有一位 owner。獨立變更使用不同 short name；實作檔案可能重疊時，使用不同 Git worktree。交接前停止 mutation 並提供最新狀態，接手者必須重新執行 `status`，不得沿用交接訊息裡的 snapshot。Archive directories 是 authority；若並行歸檔令 `INDEX.md` 暫時 stale，依序執行 `validate-index`、`rebuild-index`、`doctor`，不要手動合併 INDEX。完整契約見 [`docs/team-operations.md`](./docs/team-operations.md)。

## 驗收責任（隔離 runner）

靜態／hermetic tests 與隔離 non-interactive Agent runs 共同構成本變更的完整驗收證據；不需要任何人工 host session。Agent 行為由版本化 runner 證據判定，不再要求人重跑完整 workflow。

### 隔離 non-interactive 行為驗收

使用既有 `scripts/run-agent-eval` 與 `scripts/score-agent-eval`。Runner 會建立暫存 Git repository；Codex 使用 `exec --ephemeral`，Claude Code 使用 `-p --no-session-persistence`。每個 run 必須保留 `run-metadata.json`、input、transcript、tool／CLI trace、Git diff、proposal before／after、final state 與 `score.json`。

變更契約的必要矩陣為兩個 hosts 各跑一次下列六個 scenarios，共 12 個隔離 runs：

- `N-self-review-authority-split`
- `B-approval-boundary`
- `D-scope-drift`
- `J-ambiguous-cancellation`
- `H-incomplete-archive`
- `M-acceptance-change`

每個 run 只有在 `valid_run: true`、`adherent: true` 且 `critical_violation_ids` 為空時才通過。無效 run 必須依 runner 的 replacement metadata 重跑，不能以人工判讀補成通過。

### 行為契約參考矩陣

「靜態檢查可證明」指可從 `SKILL.md`、文件文字或 fixture 直接證明；「隔離行為驗收條件」由對應的版本化 scenario 與 scorer 判定。兩欄都要滿足。

| 驗收項目 | 靜態檢查可證明 | 隔離行為驗收條件 |
| --- | --- | --- |
| 提案建立 | 範本含 `## 狀態` 且值為 `draft` | 建立後停下等核准，不修改產品程式碼 |
| 提案 intake | authoring reference 含條件式 intake 與 readiness 規則（`tests/test_skill_reduction.py` 錨點防漂移） | 重大歧義時先簡述決策相關假設或缺口、只問一個最關鍵問題，收到回答前不建草案；小型低風險且資訊足夠時直接建立草案，不輸出固定分析或 readiness verdict；跨模組、高風險、狀態型、migration、部署或外部副作用變更才唯讀檢查與決策相關的專案規範、目前變更、核心 flow、caller、設定與測試，並檢查需求完整性、artifact 一致性、repository feasibility、失敗／重試／復原邊界與可驗證性；若更簡單、安全或易維護的替代方向會改變 proposal 的行為、範圍、影響或驗收條件，依重大歧義規則澄清，否則直接寫出最終方向；在既有 proposal、tasks 與 acceptance 中記錄 source of truth、commit point、retry／recovery 與不可重複副作用；需追蹤歸檔的完整 review 使用有界 `研究` proposal，一次性唯讀 review 不強制進入 SDD，`自審提案` 不擴張成 repository audit |
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
| 輸出語言 | `SKILL.md` Reporting 節含明文規則 | 全程使用者面向回報、提問與錯誤說明為繁體中文；回報詞元（第 N 條完成／全部完成／歸檔完成／已放棄）不變 |

## 觸發語法差異（提醒）

- Claude Code：`/sdd-workflow`
- Codex：`$sdd-workflow`
- 兩邊都可用繁中「提案／開始實作／實作／歸檔／放棄」自然觸發；執行放棄需再回覆一字不差的「確認放棄 <短名稱>」，單獨「取消」只會先詢問目標。

安裝、更新、移除指令依安裝通路而不同，見 README；不要混用某一通路的路徑或 ownership 假設。
