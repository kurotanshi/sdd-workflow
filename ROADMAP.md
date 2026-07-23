# Roadmap

本 roadmap 的目標，是把 sdd-workflow 從以自然語言規則為主的 workflow skill，逐步提升為由可測試、可重現的程式核心支撐，同時保留目前輕量、跨 agent、Git-friendly 的特性。

```text
穩定現有規格
  → deterministic read-only core
  → deterministic state transitions
  → proposal schema 擴充
  → CI 與多人協作成熟化
```

## 原則

- Skill 負責理解使用者意圖、維持核准邊界與溝通進度。
- Script 負責格式解析、狀態驗證、檔案寫入與狀態轉移。
- Script 負責 deterministic discovery；Skill 負責 proposal 的語意消歧，CLI 不自行猜測、不互動詢問、不讀取 stdin。
- 先忠實移植現有語意，再獨立進行 schema 升級。
- Parser 一律先轉換成版本無關的 canonical model；status 與 transition logic 不直接操作 Markdown AST 或原始文字。
- 自動化驗證靜態與 hermetic 行為；跨工具的 agent 遵循度仍由 fresh-session 人工驗收。
- 保持向後相容，既有 proposal 與 archive 不得因工具升級而無法讀取。
- Script 不判斷任務在語意上是否真正完成，只驗證 artifact 結構、snapshot 與狀態轉移條件。
- Script 無法阻止 agent 或使用者直接修改 artifact；它只提供唯一受支援的 mutation 路徑，並在保存有足夠 machine evidence 時偵測 out-of-band drift。Diagnostic 不得宣稱能辨識修改者身分或證明 agent 刻意繞過。
- Snapshot CAS 只防止 stale caller context 與 time-of-check／time-of-use 間的覆寫，不防惡意修改、直接寫入，或 agent 取得新 snapshot 後繞過原核准語意；approval invariant 與 managed-state attestation 分別處理後兩者。
- 每次 Skill 將既有行為切換到新的 script path，都必須先完成對應 pilot、保存 go／no-go decision record，並定義 rollback boundary；parser、active mutation、task completion 與 terminal transition 都適用，不能把 v0.3.0 adoption gate 視為一次性程序。
- 每個 milestone 內的中間 repository state 都必須 coherent。Proposal 可以分開實作與歸檔，但 command 已存在不代表 Skill 已啟用；若相依路徑尚未完整，command 維持 experimental／未被正式 Skill 呼叫，不以暫時豁免 invariant 製造 hybrid 特例。

## 設計取捨

本 roadmap 對 review 建議採以下處理，不視為無條件承諾：

- 採納：versioned parser、canonical model、discovery／disambiguation 分工、legacy compatibility matrix、stable JSON/error contract、全 mutating snapshot CAS、versioned Approval Manifest、derived INDEX、dry-run 與 doctor。
- 採納：先交付 characterization parser，再以 readonly CLI pilot 蒐集採用證據；正式把 Skill 切換成 script-only parsing path 前必須有 go／no-go decision record。既有 mutation 在 v0.4.0 前仍依目前 Skill procedure 執行。
- 調整：approved plan protection 以保存完整、versioned Approval Manifest 並做結構比較為 correctness mechanism；digest 只作為該 artifact 的識別與傳輸 token，不另行 canonicalize Markdown。
- 調整：CLI 對外只承諾最小 JSON envelope、stable error code／action 與 stdout／stderr 邊界；deterministic ordering 與 error precedence 先作為有測試的 implementation invariant，不預先升格為永久 compatibility promise。
- 調整：characterization corpus 放在 v0.3.0 第一個交付，不追加入已核准且接近完成的 v0.2.3；baseline 仍以 v0.2.3 release tag 為準。
- 調整：不把 `spike` 當橫切面 label；Schema v2 先以主要類型 `研究` 表達，沿用相同 completed／archive lifecycle，避免同時引入第二套狀態機。
- 調整：v0.5.0 先交付 Schema v2 管線與類型擴充；explicit impacts 與 required-section matrix 改為有真實大型變更案例後才啟動的 follow-up。
- 延後：`recover` command 等 doctor 累積真實 failure cases 後再設計，避免自動修復錯誤狀態。
- 延後：lock 只在 derived INDEX、snapshot CAS 與 concurrency tests 仍證明有競爭缺口時加入，不預先導入 stale-lock lifecycle。
- 不採納：不要求所有 mutation 都天然 idempotent，也不假設每種磁碟狀態都有唯一根因；每個 command 必須定義 safe retry behavior，只有 evidence 足以辨識相同操作時才回報 `ALREADY_APPLIED`，其餘使用 conflict、ambiguous 或 partial-state diagnostic。
- 調整：v0.3.0 是可長期維持的 stable plateau；v0.4.0 只有在真實使用證明 stale context、直接 mutation、terminal inconsistency 或協作摩擦值得額外複雜度時才啟動，不因 roadmap 已列出就自動開工。

## 里程碑總覽

| 里程碑 | 優先級 | 核心成果 | 完成條件 |
| --- | --- | --- | --- |
| v0.2.3 規格穩定化 | Released | prose baseline release | release tag 與雙語文件完成；fresh-session 結果尚無 repository evidence |
| v0.2.4 Trigger patch | Now | 縮窄 skill trigger、校正文件狀態 | 不引入 parser 或 workflow schema 變更 |
| v0.3.0 Deterministic Core | P0 | characterization parser、readonly CLI pilot、runtime baseline | 格式判斷可重現，且 script-only parsing adoption 有 go／no-go evidence |
| v0.4.0 Transaction Engine | Evidence-triggered P1 | Approval Manifest、managed transitions、derived INDEX、retry protocol | entry evidence 與各 path activation gate 通過，partial state 有安全處理方式 |
| v0.5.0 Proposal Schema v2 | P1 | Schema v2 pipeline、類型擴充、extension rules | 新舊 parser adapter 共用 canonical model |
| v0.6.0 Team Readiness | P2 | 完整 CI、安裝矩陣、協作與 concurrency tests | Required checks 完整，多 agent 行為有明確規則 |

## v0.2.3：規格穩定化（已發布）

`review-fixes-v023` 已發布為 v0.2.3：

- 放棄流程使用機器比對 snapshot hash。
- 抽出共用 terminal archive procedure。
- 修正 phase 選項中的裸 `取消`。
- 同步 README、CONTRIBUTING、CLAUDE.md 與 CHANGELOG。
- 定義 Claude Code 與 Codex fresh-session 驗收矩陣。

Repository 目前沒有保存兩個工具實際 fresh-session PASS 的結果，因此 roadmap 不把 release tag 等同於互動驗收證據。若既有驗收確實完成，應補 decision／acceptance record；否則狀態維持「已發布、互動驗收證據未記錄」。這個版本仍是後續 script 化的 prose baseline。Characterization fixtures 不回填已發布版本；v0.3.0 的第一項工作依 v0.2.3 release tag 建立 baseline corpus。

## v0.2.4：Trigger patch

在 deterministic core 前先交付不依賴新架構的小修正：

- 縮窄 skill frontmatter description，移除裸 `取消` 造成的過廣自動觸發；裸 `取消` 的消歧規則仍保留在 Skill 內供已明確進入 workflow 的對話使用。
- 同步中英文 README、CHANGELOG 與版本資訊，並由 README 連結本 roadmap。
- 不加入 parser、metadata、runtime dependency 或其他 workflow schema 變更。

## v0.3.0：Versioned deterministic read-only core

v0.3.0 維持一個 release milestone，但拆成三份依序核准的 proposal。Parser 建置本身不需要先證明 prose 已造成特定次數的事故；把 Skill 的讀取／解析正式切換成 script-only path 則必須通過 adoption gate。Status、checkbox 與 terminal mutation 在 v0.4.0 command 上線前仍依現行 Skill procedure 執行，不得把 v0.3.0 描述成完整 script-managed workflow。

### Proposal A：`add-parser-characterization`

#### 預計結構

```text
skills/sdd-workflow/
├── SKILL.md
├── agents/openai.yaml
└── scripts/
    ├── sdd.py
    └── sdd_core/
        ├── __init__.py
        ├── cli.py
        ├── diagnostics.py
        ├── discovery.py
        ├── model.py
        ├── parser_legacy.py
        ├── parser_v1.py
        └── snapshot.py

tests/
├── fixtures/baseline/
│   ├── MANIFEST.json
│   ├── valid-simple/
│   ├── valid-nested-acceptance/
│   ├── invalid-checkbox/
│   ├── invalid-list-item/
│   ├── ambiguous-active/
│   ├── abandon-snapshot/
│   └── completed-terminal/
├── test_scanner.py
└── test_parser.py
```

Fixture manifest 記錄 fixture 名稱、來源規則、expected outcome、對應的 v0.2.3 normative section 與 baseline release tag。

#### Parser architecture

```text
讀取原始 bytes
  ↓
偵測 schema version
  ↓
parse_v1 / parse_legacy
  ↓
Canonical Proposal Model
  ↓
validate / list / status / preflight
```

Canonical model 至少包含 schema version、short name、status、change type、sections、tasks、acceptance conditions 與 diagnostics。未來只增加 parser adapter，不讓 transaction engine 理解各版本 Markdown 差異。Canonical model 是內部 architecture contract；v0.3.0 不提供公開 `parse` command，以免把完整 model 意外升格為外部 CLI API。

#### Legacy compatibility contract

| 文件類型 | 讀取 | 驗證 | 修改 |
| --- | --- | --- | --- |
| 無版本、符合 v1 | 是 | 是 | 是；普通 mutation 不自動改寫 schema version |
| 無版本、部分 legacy 格式 | 是 | compatibility warning | 否，回報 `ERROR_LEGACY_MUTATION_UNSUPPORTED` |
| 明確 schema version 1 | 是 | 是 | 是 |
| 明確 schema version 2 | v0.5.0 起支援 | v0.5.0 起支援 | v0.5.0 起支援 |
| 未知 future version | 否 | fail closed | 否 |

核心規則：absence means v1；unknown version means unsupported；never guess a future schema。Read compatibility 不代表 mutation compatibility，建立 machine metadata 也不等同 schema migration。

### Proposal B：`add-readonly-cli-contract`

#### CLI 範圍

```text
sdd.py validate <short-name>
sdd.py validate --all
sdd.py list --state active --json
sdd.py status <short-name>
sdd.py status <short-name> --json
sdd.py abandon-preflight <short-name>
sdd.py --version
```

- `list` 只回傳 deterministic candidates，不自行選擇 proposal；候選的語意消歧仍由 Skill 處理。
- CLI 不提供互動 prompt，也不從 stdin 取得選擇。
- Project root discovery 順序固定為：explicit `--root` → Git worktree root → upward search → fail。
- Short name 必須符合 `^[a-z0-9][a-z0-9-]*$`，禁止 `..`、`/`、`\\`；resolve 後必須仍位於 project-local `sdd/` 下。
- Proposal directory 預設不允許 symlink；若 proposal 定案允許特定 symlink，必須以安全測試證明 resolve 後仍在 project-local `sdd/` 下。

#### 最小 JSON compatibility contract

- 所有 JSON output 包含 `output_version`、`command`、`ok`、`warnings` 與 `errors`。
- Error 保證 machine-readable `code`，並可提供穩定的 `action`；message、語言、排版與 `suggested_command` 不是相容性契約。
- `--json` stdout 只能輸出單一合法 JSON document；human-readable error 寫入 stderr，stack trace 預設隱藏。
- Diagnostic 在適用時包含 path、line 與 column。
- `--version` 回報 engine version 與支援的 schema version range。

Proposal candidates、tasks 與 diagnostics 仍必須 deterministic，不得依賴 filesystem enumeration order；ordering 與多重錯誤 precedence 以 tests 固定為 implementation invariant，但 v0.3.0 不承諾它們永遠是外部 compatibility contract。一般 fixture 比較 parsed JSON；只有真正參與 hash 或持久化的 canonical artifact 比較 bytes。

#### Snapshot contract

`status` 與 preflight 產生 versioned snapshot manifest：

```json
{
  "snapshot_version": 1,
  "proposal_sha256": "...",
  "tasks_sha256": "...",
  "snapshot_digest": "..."
}
```

- SHA-256 針對檔案原始 bytes，不正規化換行、編碼、BOM 或尾端空白。
- Snapshot manifest 的持久化／hash serialization 必須版本化並以 fixtures 固定。
- Snapshot 預留加入其他 artifact 的能力，不擴充每個 mutating command 的 hash 參數數量。
- Snapshot CAS 的 remediation 固定為重新讀取 `status`；若 proposal semantic content 已改變，取得新 snapshot 不代表原核准仍有效。
- v0.3.0 的 abandonment execution 仍由 prose-era procedure 執行，因此 `abandon-preflight` 的 human output 必須明列 `proposal.md` 與 `tasks.md` 兩個 64 位小寫 SHA-256，維持 v0.2.x transcript confirmation contract；JSON 可額外提供 versioned snapshot manifest，但不得只輸出 composite digest 而讓既有確認流程無法取得兩個 expected hash。

### Proposal C：`add-runtime-packaging-baseline`

- 選定並測試最低 Python 3 版本，README 與 CHANGELOG 顯著標示 v0.3.0 引入必要 runtime dependency，且在 `0.x` 階段屬 breaking minor change。
- 第一級支援平台為 macOS 與 Linux；Proposal C 必須把 Windows 明確定案為 supported 或 best effort，並由該決定約束 v0.4 fsync／rename／replacement test matrix，不把平台等級繼續留成後續未決問題。
- repository checkout 與安裝後都能執行 `sdd.py --version`；skill package 內相對路徑正確，Python 缺失或版本過舊時回報可操作錯誤。
- 建立 macOS／Linux 基本 install smoke、parser fixtures、package validation 與核心中英文文件／CLI 指令一致性檢查。
- Mutation 專屬的 fsync、mode preservation、directory rename 與 open-file replacement 測試留到 v0.4.0。
- Script 無法執行時 fail closed，不提供 prose parser fallback，以免形成第二套解析邏輯。

#### Adoption gate 與 rollback

正式把 SKILL.md 切換為 read-only script path 前，使用 v0.2.3 fixtures 與代表性 workflow scenarios 在 Claude Code、Codex fresh sessions 執行 pilot，記錄：

- agent 是否穩定呼叫 CLI，而非自行重做 parser；
- parser 與既有 prose 判斷是否出現 divergence；
- CLI 失敗時是否確實 fail closed；
- 額外 tool call 是否造成明顯遵循或完成率下降；
- 需要多少人工介入與 remediation。

不硬訂必須先發生幾次 production bug，但 release 前必須保存 go／no-go decision record。Pilot 失敗時延後 Skill 的 parsing-path 切換並修正 CLI／指令，不在同一版本加入 prose parser fallback。v0.3.0 的回滾方式是 pin 或重新安裝最新的 v0.2.x prose-only release；v0.3.0 不修改 artifact schema，因此回滾不需資料 migration。

#### Evidence records

Proposal C 建立所有 evidence-gated decision 共用的輕量紀錄位置：

```text
docs/
├── decisions/
│   └── YYYY-MM-DD-<decision>.md
└── friction-log.md
```

- Decision record 至少包含日期、engine／skill version、evaluated scenarios、observed evidence、rejected alternatives、decision 與 rollback boundary。
- Friction log 每筆包含日期、版本、scenario、observed friction／failure、severity、可選 evidence link 與 disposition。
- 不預設保存完整使用者 transcript；若 evidence 含專案內容、個資或敏感資訊，只記錄去識別摘要與可安全保存的重現案例。
- Adoption、recover、lock、Schema v2 與 impact metadata 的 gate 都引用這些持久紀錄，不以未記錄的個人印象視為充分 evidence。

### SKILL.md 瘦身

- Proposal A/B 完成後，移除已由 script 承擔的 scanner grammar、hash 計算與 JSON 判讀細節。
- Skill 只保留使用者意圖、proposal 消歧、核准邊界、CLI 呼叫時機、error action 與溝通規則。
- 不使用行數作 KPI；完成標準是規則不重複、失敗時 fail closed，且 fresh-session 行為不退化。

### v0.3.0 完成門檻

- 依 v0.2.3 release tag 建立 characterization corpus；既有 scanner prose 中每個 normative 合法與非法例都有 fixture input 與 expected JSON result。
- Parser adapter output 符合相同 canonical model，status logic 不直接操作 Markdown AST 或原始文字。
- Legacy compatibility、最小 JSON contract、deterministic implementation invariants、root discovery、path safety、snapshot 與 runtime failure 都有測試。
- macOS／Linux 基本 install smoke 通過。
- Adoption gate 有書面結果，且 Skill 已移除由 read-only script 承擔的重複規則。

### Stable plateau

v0.3.0 是 intentional stable plateau：即使沒有證據支持進入 v0.4.0，專案也可以長期停留在「script 負責 deterministic read／parse，現行 Skill procedure 負責 mutation」的模式。這已消除主要的 task counting 與格式判斷不確定性，同時避免在低頻、單人使用情境預付 transaction metadata、attestation 與 recovery protocol 的維護成本。

## v0.4.0：Deterministic state transitions

v0.4.0 維持一個 milestone，但預期至少拆成四份 proposal。實際建立 proposal 時仍受十條未完成任務上限約束；若任一份無法以十條內的獨立驗證工作完成，繼續拆分，不用籠統 task 壓縮。

### Entry criteria

v0.4.0 不因 v0.3.0 完成而自動啟動。至少要有持久 evidence 顯示一項以上問題反覆出現，且預期收益足以支付 machine metadata 與額外 command orchestration 的成本：

- stale caller context 或錯誤 task identity 造成實際 mutation 風險；
- agent／其他工具直接修改 status、checkbox 或 terminal artifact，且事後難以辨識；
- archive／INDEX partial transition 或多人協作摩擦已出現；
- 使用頻率足以讓 deterministic mutation 明顯降低人工驗證成本；
- v0.3 adoption evidence 顯示 agent 能穩定遵循 script path，沒有因 tool-call 負擔反覆繞過。

Entry decision 保存於 `docs/decisions/`；不以 roadmap 完整性本身視為開工理由。

### 分階段 architecture decisions

不以單一巨型 ADR 阻塞全部 v0.4.0。每項決策跟著第一個消費它的 proposal 定案：

| 時機 | 必須定案的內容 |
| --- | --- |
| Proposal A 前／內 | artifact authority、metadata storage、必要 version axes、Approval Manifest 與 legacy approved adoption |
| Proposal B | managed-state projection、attestation update rules、drift classification 與 remediation action |
| Proposal C | archive record authority、legacy adapter、doctor diagnostic evidence boundary |
| Proposal D／正式 activation 前 | terminal operation evidence、hybrid activation boundary、upgrade／downgrade 與 rollback policy |

共通預設是 v1 status 仍由 `proposal.md` authoritative，task completion 仍由 `tasks.md` authoritative；machine metadata 保存 attestation 與 operation records，不因普通 mutation 自動把無版本 v1 改寫成明確 schema v1。若 metadata 複製 status，相關 decision 必須定義 mismatch diagnostic，不得留下未定義的雙重權威。

### 三層保護模型

| 機制 | 覆蓋內容 | 保護目標 |
| --- | --- | --- |
| Snapshot CAS | 相關 artifact 原始 bytes | `status`／preflight 後至 mutation 前的 stale write |
| Approval Manifest | 明確標為 approval-relevant 的 semantic projection | 核准後的 scope、task text 與 acceptance integrity |
| Managed-state attestation | status、checkbox 與 machine-managed metadata 的 parsed projection | 受支援 command 外的 managed-state drift |

Attestation 不涵蓋整份 Markdown raw bytes。非 approval-relevant、非 machine-managed 的正文可自由編輯；下一次 mutation 仍須以新 `status` 取得 raw-byte snapshot。正文欄位是否 approval-relevant 由 Approval Manifest contract 明訂，例如背景補充可以排除，會改變 scope 或驗收判斷的描述則必須納入。三層保護各自回報不同 error code／action，不以「重跑 status」處理所有 mismatch。

### 完整狀態機

每條合法狀態邊有唯一 command；agent 不直接修改既有 status：

```text
draft → approved               approve
approved → draft               begin-revision
approved → completed           archive
draft → abandoned              abandon
approved → abandoned           abandon
```

- `complete-task` 只接受 `approved`。
- 新 proposal 的初始 `draft` 建立不是狀態轉移；一旦 proposal 存在，後續 status 只能由 command 改變。
- `archive` 只接受 `approved` 且 tasks 全部完成。
- `completed` 與 `abandoned` 是終態，不允許轉回 active。
- Statusless legacy proposal 只有明訂的 abandonment path；其他 mutation fail closed。

### Proposal A：`add-machine-metadata-and-approval-manifest`

```text
sdd.py approve <short-name> --expected-snapshot <digest>
sdd.py begin-revision <short-name> --expected-snapshot <digest>
```

#### Approval Manifest

`approve` 由 canonical model 投影出 versioned Approval Manifest，保存完整 JSON artifact：

```json
{
  "approval_model_version": 1,
  "short_name": "add-feature",
  "change_type": "feature",
  "description": "...",
  "acceptance_conditions": ["..."],
  "tasks": [{"text": "..."}]
}
```

- Manifest 包含使用者核准的 scope、change description、acceptance conditions、task 文字，以及未來明確標為 approval-relevant 的 non-goals、risk、migration 等欄位。
- Manifest 排除 status、checkbox 完成狀態與 completion metadata；task completion 改變不會改變核准內容。
- 後續 command 讀取已保存 JSON，將目前 Markdown 依該 proposal 保存的 `approval_model_version` 投影後做資料結構比較，mismatch 回傳欄位級 diff 與 `ERROR_APPROVED_PLAN_CHANGED`。
- 不對 Markdown 做獨立的 whitespace、換行或 Unicode canonicalization。Parser 決定語法差異如何映射到 semantic fields；Unicode code points 預設原樣保留。
- `approval_manifest_sha256` 如有需要，只對已保存 Approval Manifest 的原始 bytes 計算，作為 artifact identity／transport token，不取代結構比較。
- 每個 canonical model 欄位與 extension 必須宣告是否 approval-relevant；未知且可能影響 scope 的欄位不得被靜默排除。
- `begin-revision` 使目前 manifest 失效；是否保存為 audit history 由 proposal 明訂，失效 manifest 不得繼續授權修改後的內容。

`approve` 與 `begin-revision` 使用 snapshot CAS，成功後回傳新 snapshot。Individual-file atomic replacement、mode preservation 與 fsync 行為在本 proposal 建立共用基礎。

#### In-flight adoption

- `draft` v1 proposal 可照常驗證與 approve；approve 建立第一份 Approval Manifest，不進行 schema migration。
- 已是 `approved`、但沒有 Approval Manifest 的 proposal 標記為 `legacy_unattested`，不得直接 complete task。Skill 必須要求使用者重新確認目前 proposal；確認後由明確的 `approve --establish-manifest` 或等價專用 command 建立 baseline，具體 syntax 在 Proposal A 定案。
- 建立 baseline 不得偽造原始核准時間，也不得宣稱能證明歷史 task completion 都由 script 執行。
- Legacy archive 維持 read-only compatibility，不因安裝 v0.4 原地寫入 metadata。

### Proposal B：`script-task-completion`

```text
sdd.py complete-task <short-name> <task-number> \
  --expected-task-digest <digest> \
  --expected-snapshot <digest>
```

- `status --json` 為每條 task 回傳文件序號、原文、完成狀態與由 task canonical text 計算的 task digest。
- `complete-task` 同時驗證 ordinal、task digest、snapshot、Approval Manifest 與 managed-state attestation，避免勾選錯誤目標或接受 out-of-band drift。
- Schema v2 是否引入永久 task ID 延後決定；v0.4.0 不改現有 task Markdown 格式。
- Approved proposal 保存最後一次 script committed managed-state projection 的 attestation，只涵蓋 status、task completion markers 與 machine-managed metadata，不涵蓋整份檔案 bytes 或一般正文。`status` 是唯讀，不能刷新或覆蓋 attestation；目前 managed projection 與 attested state 不符時，command fail closed，doctor 回報 `OUT_OF_BAND_DRIFT` 或更精確的 evidence-based code。
- Diagnostic 只能證明目前 managed projection 不同於最後 attested state，不能判斷是 agent、使用者、其他工具或 interrupted command 所修改。
- Initial draft，或由 `begin-revision` command 正式進入並帶有 revision marker 的 draft，允許人工編輯；直接把 approved status 改成 draft 不會清除既有 attestation，仍回報 drift。重新 approve 時建立新的 attested baseline。
- Drift error 的 stable `action` 是 `inspect_managed_state_drift`，建議先執行 `doctor` 並檢查欄位級差異；不得以 `refresh_status`、自動採用目前狀態或隱式重建 attestation 洗掉 evidence。具體人工修復步驟由 Proposal B 的 failure cases 定案，自動 recover 仍不在本版本範圍。

### Proposal C：`add-archive-model-and-index-tools`

```text
sdd.py rebuild-index
sdd.py validate-index
sdd.py doctor
```

- Archive directory 是 authoritative state；`archive/INDEX.md` 是可重建的 derived artifact。
- 定義 versioned canonical archive record 與 legacy archive adapter。Adapter 結合 archive artifacts 與 legacy INDEX，保留無法從 proposal/tasks 重建的既有 summary。
- `rebuild-index` 不得自行 migration 或改寫 legacy archive，也不得從自然語言 proposal 猜測等價摘要。
- `validate-index` 比對 INDEX 與 canonical archive records。
- `doctor` 檢查 active／archive 同名、status-location mismatch、INDEX stale、temporary file、terminal status 位於 active、Approval Manifest mismatch、attested-state drift，以及可辨識的 partial transition。
- Doctor 允許回報 `AMBIGUOUS_STATE`／`UNKNOWN_STATE`；相同磁碟狀態可能有多個成因，不虛構唯一 root cause。
- v0.4.0 只提供診斷與明確人工修復步驟；自動 `recover` 延後到有真實 failure cases。

### Proposal D：`script-terminal-transitions`

```text
sdd.py archive <short-name> --expected-snapshot <digest> \
  (--summary "single-line summary" | --summary-file <path>)
sdd.py abandon <short-name> --expected-snapshot <digest> \
  (--summary "single-line summary" | --summary-file <path>)
```

- `--summary` 與 `--summary-file` 互斥。`--summary` 只接受單行，遇 CR／LF 直接回報 stable validation error；`--summary-file` 以 UTF-8 strict mode 讀取並允許多行，不支援 stdin，另定義大小上限、空值、NUL 與 file-read error code。
- Metadata 保存 summary 原文；INDEX renderer 將多行 summary 以固定規則摺疊成單行，再處理 `|` 與反斜線 escaping。摺疊規則與 fixtures 在 Proposal D 定案，不由 shell quoting 或 Markdown renderer 隱式決定。
- Terminal metadata 至少包含 metadata version、short name、terminal status、UTC RFC 3339 timestamp、summary、來源 snapshot 與足以辨識 committed retry 的 operation evidence。
- Archive directory 名稱沿用執行環境本地 `YYYY-MM-DD`，不得從 UTC timestamp 推導而改變既有語意。
- Directory move 是 authoritative commit point。Move 完成後從 archive records 重建 INDEX；INDEX rebuild 失敗不反向搬移已 committed archive，回報 `COMMITTED_DERIVED_ARTIFACT_STALE` 並建議 `rebuild-index`。
- Destination collision 與「相同 terminal operation 已 committed」只有在 metadata evidence 足以區分時才分別回報；證據不足時維持 collision 或 ambiguous state，不猜測。

#### Terminal failure protocol

```text
prepare
→ stage metadata/status
→ commit directory move
→ rebuild derived INDEX
→ finish
```

Proposal D 必須以 failure injection tests 模擬 metadata write、status write、directory move、INDEX replace 前後的中斷，列出磁碟狀態、authoritative commit 是否發生、command retry 結果與 doctor diagnostic。

Transaction marker 不是預設硬需求；只有 failure matrix 證明現有 artifact 無法辨識必要 phase 時才加入。若採 marker，必須版本化並定義建立、更新、搬移、清除及殘留行為。

### Implementation 與 Skill activation boundary

- Proposal A–D 可以分開實作、測試與歸檔，但正式 Skill 在相依 mutation paths 完整前維持 v0.3 stable plateau 行為；尚未啟用的 command 標為 experimental，不成為唯一受支援路徑。
- 不得先啟用 `complete-task` attestation、同時讓正式 terminal path 繼續以 prose 直接修改 status／搬移目錄，因為正常歸檔會被誤判為 out-of-band drift。
- 預設在 A–D、doctor 與 terminal failure protocol 都完成後一次啟用 managed mutation group。若要提早啟用其中一條 path，該 proposal 必須提供完整、經測試的 compatibility bridge，且不得暫時關閉 attestation 或降低 fail-closed 保證。
- Command implementation merge 與 user-facing activation 是兩個不同 decision；release note、SKILL.md 與 `--version` 必須能辨識目前啟用的 behavior generation。

### v0.4.0 activation gate

正式切換每條 Skill behavior path 前，都以 fresh Claude Code／Codex sessions 執行 pilot；可以在同一 decision record 中批次評估相依 paths，但結果必須分別涵蓋 approve／revision、task completion 與 terminal transition：

- agent 是否使用 command 而非直接編輯 managed fields；
- 每條 task 的總 tool calls、失敗重試率與人工介入是否可接受；
- snapshot、task digest 或 attestation mismatch 時是否遵循 stable `action`，而非無腦 refresh／retry；
- partial terminal failure 是否能依 diagnostic 安全停下或重建 INDEX；
- rollback 到 activation 前 Skill path 是否有明確邊界，且不需刪除 metadata 偽裝降級。

只有 gate 通過才修改正式 SKILL.md。失敗時保留已實作 command 供測試或後續改良，不啟用混合路徑，並把結果記入 decision／friction records。

### 所有 mutating commands 的共同契約

- 支援 `--dry-run` 與 `--json`，回報 `would_change`，不得修改 artifact content、directory entries、symlink target、mode 或 mtime；atime／ctime 不作跨平台契約。
- 所有既有 proposal 的 mutation 要求 caller 提供 `--expected-snapshot`，不隱式採用 command 當下的新 snapshot。
- 修改前重新驗證 schema、proposal、tasks、snapshot、Approval Manifest 與適用的 managed-state attestation。`begin-revision` 是 Approval Manifest equality 的明確例外：若 approved semantic content 已先被修改，它仍可在 snapshot 與 managed-state attestation 有效時記錄欄位 diff、失效舊 manifest 並正式進入 draft；其他 mutation 不得用此例外接受未重新核准的內容。
- 成功 JSON 回傳 `before_snapshot`、`after_snapshot`、`changes`、`warnings` 與 `errors`；舊 snapshot 成功後失效。
- `--dry-run` 回傳 `before_snapshot`、`predicted_changes` 與 `after_snapshot: null`；不預測含時間資料的 terminal after snapshot。
- Individual file 使用同目錄 temporary file、完整寫入、flush、視平台支援 fsync、保留 mode，最後以 `os.replace()` 原子替換。
- 不宣稱多檔案或跨目錄 transition 具備 ACID；採 individual-file atomic replacement 與可診斷的 multi-artifact protocol。
- 每個 command 定義 authoritative commit point、成功後重跑、舊 snapshot 重跑、partial completion 與 evidence 不足時的 safe retry behavior。
- `APPLIED`、`ALREADY_APPLIED`、`NO_CHANGE` 是 operation outcome；conflict、partial、ambiguous 與 validation failure 是 error category，不混成單一平面狀態列舉。
- Snapshot mismatch 的 `action` 是 `refresh_status`，但不得自動重試 mutation；Approval Manifest mismatch 的 `action` 是 `begin_revision_and_reapprove`。

### SKILL.md 與 downgrade

v0.4.0 managed mutation activation gate 通過後，Skill 才移除直接修改 status、checkbox、archive move 與 INDEX 的程序，只保留 command orchestration、核准語意與 error action。Agent 是否遵循這條規則仍由 fresh-session 驗收；script 與 doctor 只能降低錯誤或偵測有 evidence 的 drift。

Downgrade 到任何 pre-v0.4 workflow 不支援繼續 mutation 已有 v0.4 machine metadata 的 active proposal，因為舊 Skill 會繞過 attestation。較舊 engine 最多依 compatibility matrix 做唯讀檢查。支援的 rollback 是先完成／放棄現有 proposal，或使用明確、另行設計的 downgrade procedure；不得以刪除 metadata 假裝安全降級。

## v0.5.0：Proposal Schema v2

### Entry criteria

Schema v2 不只由版本時程啟動。開始 proposal 前，v0.4 transaction engine 必須已處理一批真實 active／archived proposals，並留下具體 evidence 說明：

- 哪些 v1 限制已造成反覆摩擦或無法表達的需求；
- 哪些新欄位需要進入 canonical model 與 Approval Manifest；
- 哪些資訊只是文件展示，不需要 script validation；
- parser adapter 與 approval-model versioning 已能在不修改 transaction engine 的情況下支援新 schema。

不硬訂 archive 數量；若沒有具體 v1 limitation evidence，延後 Schema v2，而不是為驗證架構抽象而製造格式變更。

### Schema pipeline 與分類

- 使用 v0.3.0 已定義的 schema version detection、canonical model 與 extension rules，以及 v0.4 staged architecture decisions 定義的 machine metadata policy，正式加入 `parse_v2` adapter。
- 主要類型擴充為：`新功能`、`修 bug`、`重構`、`維運`、`文件`、`研究`。
- 可選標籤：`效能`、`安全性`、`migration`、`dependency`；不把 `spike` 混入橫切面標籤。
- `研究`／spike 在 v0.5.0 仍使用相同 completed／archive lifecycle，但驗收可以是回答明確問題與產出研究結論，不要求一定修改 implementation。Schema v2 proposal 必須決定結論的 canonical 落點（例如 proposal 的 `## 結論` 或明確 artifact），確保 archive 不只保存問題而遺失答案。
- 新提案明確宣告 schema version，並由 `parse_v2` 轉成既有 canonical model；transaction engine 不依賴 Markdown schema version。
- Schema v2 的正式欄位名稱、允許值及 Markdown／frontmatter encoding 只在本 proposal 內定案，不由 v0.3.0 預先核准。

### Evidence-gated follow-up：explicit impacts

Explicit impacts 與 required-section matrix 不再是 v0.5.0 的必要交付。只有 archive 已累積足夠真實案例，證明大型變更反覆缺少 migration、相容性、安全性、部署或跨服務資訊時，才另開 `add-impact-metadata` proposal。

該 proposal 必須從具體 archive 案例推導 impact vocabulary、必要章節與 validation matrix，不沿用 roadmap 中預先猜測的欄位。責任邊界維持：Skill 根據需求提出 impacts，使用者在 proposal review 時核准，script 只依明確 metadata 驗證必要章節，不從自然語言自行推測 impact。未宣告對應 impact 時，不得產生空白條件式章節。

### 完成門檻

- 最小 Schema v2 proposal 只比 Schema v1 增加 schema metadata，不增加強制正文章節或空白 placeholder。
- `parse_v1`、`parse_legacy` 與 `parse_v2` 產生相容的 canonical model，既有 archive 不需原地 migration 即可讀取。
- 類型與研究 lifecycle 都有 deterministic fixtures，且不改變 completed／abandoned 終態語意。
- 每個新增欄位明訂是否 approval-relevant；研究 conclusion 在 terminal archive 中可重建、可讀取。
- 若尚未達到 impacts 的 entry criteria，v0.5.0 不實作 impact metadata 或 required-section matrix。

## v0.6.0：Team readiness

### CI 與靜態驗證

Required status checks 固定為：

```text
unit
fixtures
package-validation
docs-consistency
install-smoke
```

- `unit`：parser、canonical model、snapshot、Approval Manifest、transitions 與 doctor unit tests。
- `fixtures`：baseline、Schema v2、archive collision、snapshot mismatch、partial failure 與 concurrency fixtures。
- `package-validation`：frontmatter、skill package 與 CLI contract validation。
- `docs-consistency`：中英文文件的 command、版本、安全警告、runtime requirement 與 CLI `--help` 核對；一般說明文字不要求逐句鏡像，避免把翻譯形式本身變成無差別持續稅。
- `install-smoke`：`link-dev.sh` hermetic tests 與各支援安裝通路的 package smoke test。

### 平行 agent 與 worktree

短期先建立使用邊界：

> 同一 proposal 同一時間只由一個 agent 操作；平行修改使用不同 short-name 與獨立 worktree。

同一 repo 的所有 agent 必須使用相容的 workflow engine generation。混用 prose-era skill 與 script-managed skill 不受支援，因為舊 agent 可直接修改 checkbox、status 或 INDEX，繞過 snapshot CAS、Approval Manifest 與 attestation。

- `--version` 是問題回報與人工核對的必要資訊。
- Artifact 可記錄最低 writer／engine version 作為 compatibility signal，但不能宣稱它能完整偵測舊 agent 的直接寫入。
- `doctor` 只在 machine metadata 足以證明 version skew 時回報；不得把缺乏證據推論成安全保證。

v0.4.0 已用 derived INDEX 避免並行 archive 造成 authoritative archive data 遺失，並以 snapshot CAS 保護單一 proposal。但兩個並行 rebuild 仍可能讓 INDEX 暫時 stale，因此 v0.6.0 必須加入 concurrency tests 與 `validate-index` 檢查；只有實際證據顯示需要序列化時，才加入 lock 或 INDEX-level compare-and-swap。

可能的後續機制：

- Mutating command lock。
- 兩個 archive process 的 concurrency test。
- INDEX-level compare-and-swap。
- Lock stale-owner detection 與 recovery guidance。

## 建議的 SDD proposal 切分

每一項應作為獨立提案、獨立核准與獨立歸檔：

1. `narrow-skill-trigger-v024`：縮窄 frontmatter trigger 並同步 patch 文件。
2. `add-parser-characterization`：baseline manifest、fixtures、versioned parser、canonical model 與 diagnostics。
3. `add-readonly-cli-contract`：validate、list、status、preflight、snapshot、最小 JSON contract 與 path safety。
4. `add-runtime-packaging-baseline`：Python contract、基本 install smoke、最低 CI、evidence records、adoption pilot 與 read-only Skill 瘦身。
5. `add-machine-metadata-and-approval-manifest`：authority／storage decisions、approve、begin-revision、Approval Manifest、in-flight adoption、CAS 與 atomic-write 基礎。
6. `script-task-completion`：task identity、complete-task、managed-state projection／attestation、drift action 與 retry behavior。
7. `add-archive-model-and-index-tools`：archive record、legacy adapter、rebuild-index、validate-index 與 doctor。
8. `script-terminal-transitions`：archive、abandon、summary file、commit point、failure injection、safe retry matrix 與 managed mutation activation gate。
9. `expand-proposal-schema`：entry criteria 通過後交付 Schema v2 pipeline、類型、研究 conclusion lifecycle 與 `parse_v2` adapter。
10. `harden-team-workflow`：完整 CI、installation matrix、worktree 指引與 concurrency tests。

上述清單是目前 dependency-based forecast，不是不可變的 proposal 數量。`add-impact-metadata` 是 evidence-gated candidate，不預先承諾版本。建立每份 proposal 時都要套用最多 10 條未完成任務的限制；若無法拆成 10 條以內的可獨立驗證工作，就繼續拆 proposal，不得用籠統 task 壓縮範圍。

## 文件演進

Roadmap 保留目標、milestone、entry／exit criteria、proposal dependency 與非目標。詳細契約在相關 proposal 落地時逐步移出，避免一次建立尚無實作證據的空泛文件：

```text
ROADMAP.md
docs/
├── architecture.md          # Skill／Script 邊界、canonical model、staged authority decisions
├── cli-contract.md          # public JSON／error／stdio contract
├── compatibility.md         # version axes、upgrade／downgrade matrix
├── transaction-protocol.md  # CAS、Approval Manifest、attestation、retry／failure matrix
├── friction-log.md          # evidence-gated follow-up 的去識別摩擦紀錄
└── decisions/
    └── YYYY-MM-DD-*.md      # adoption、entry、rollback 與其他 go／no-go records
```

Testing strategy 在測試形態穩定前保留於各 proposal 與 test suite；出現跨里程碑共用規則後才抽成獨立文件。

## 成功指標

- 同一 fixture 在不同 agent 與 session 得到相同的 task 數量與錯誤行號。
- Parser adapter 的 output 都符合相同 canonical model contract；transition tests 不依賴 Markdown schema version。
- Adoption、entry、recover、lock、Schema v2 與 impact decisions 都引用 repository 內的 decision／friction evidence，不依賴未記錄的個人印象。
- v0.3.0 的 script-only parsing 切換有 pilot evidence 與 go／no-go record；失敗不導入第二套 prose parser，也不宣稱 v0.4.0 前的 mutation 已由 script 管理。
- v0.3.0 可作為長期 stable plateau；沒有 v0.4 entry evidence 時不因 roadmap 順序自動啟動 transaction engine。
- v0.4.0 managed mutation activation 後，每條合法狀態邊都有唯一 command；Skill 不再指示 agent 直接修改既有 status、checkbox 或 INDEX，但 roadmap 不宣稱 script 能物理阻止直接寫入。
- v0.4 commands 的 implementation 與正式 Skill activation 分離；任何 user-facing path 切換都有 fresh-session gate，且中間 repository state 不會以正常 prose 行為製造 drift。
- 所有既有 proposal 的 mutating commands 都要求 snapshot CAS 並回傳 before／after snapshot；核准後的 scope、task 文字或驗收條件改變必定與 Approval Manifest 結構不符並提供可讀 diff。
- Approved／terminal 的 managed-state projection 若不同於最後 attestation，command fail closed 且 doctor 回報 evidence-based drift diagnostic，不推論修改者身分；一般正文 raw-byte 差異本身不構成 attestation drift。
- 每個 mutation 都定義 commit point 與 safe retry behavior；只有 evidence 足夠時回報 `ALREADY_APPLIED`。
- 所有 terminal transitions 都受 status、snapshot、Approval Manifest、attestation 與 destination collision 驗證；新 archive 的 INDEX 資料可由 archive artifacts 重建，legacy archive 透過 compatibility adapter 保留既有資訊。
- `--dry-run` 前後 artifact bytes、directory entries、symlink target、mode 與 mtime 不變；atime／ctime 不列入跨平台保證。
- 最小 Schema v2 proposal 只增加 schema metadata，不增加強制正文章節或空白 placeholder。
- Branch protection 要求 `unit`、`fixtures`、`package-validation`、`docs-consistency`、`install-smoke` 全數通過。
- Fresh-session 人工驗收負責確認 agent 是否呼叫 command、是否繞過受支援路徑與錯誤時是否 fail closed；parser 計算正確性由 fixtures／unit tests 負責。

## 非目標

- 不把 sdd-workflow 擴張為 Jira、Linear 或大型 RFC 平台。
- 不引入 daemon、database 或常駐服務。
- 不要求所有小型修改都使用 extended proposal sections。
- 不以自動化測試取代 Claude Code 與 Codex 的 fresh-session 人工驗收。
- 不嘗試由 script 判斷任務是否在語意上真正完成；script 只驗證狀態轉移與 artifact 結構。
- 不承諾跨 filesystem 或多檔案操作具備資料庫等級的 ACID transaction。
- 不把 `sdd.py` 發展成通用 Markdown parser 或通用專案管理 CLI。
- 不在缺乏實際 contention 或 recovery cases 前加入常駐 lock service 或自動修復引擎。
