# 成果契約、施工計畫與 Checkpoint 設計

## 分開兩層授權

| 層級 | 誰決定 | 變更是否需使用者重核准 | 內容 |
|---|---|---|---|
| 成果契約 Outcome Contract | 使用者核准 | 是（成果／acceptance／範圍／重要風險變更） | 要達成什麼、如何驗收、可改哪些路徑、限制與重要風險 |
| 施工計畫 Execution Plan | Agent | 否（契約不變時） | 步驟順序、搜尋方法、內部拆合 |

Agent 不能靠改寫施工計畫擴張授權。無法判斷是否越界時必須提出具體決策問題並停止。

## Checkpoint

Checkpoint = 一組相依修改的可驗證成果切片，對應契約中的 outcomes + acceptance。

- 可涵蓋多檔修改
- 完成條件：每條 acceptance 都有有效證據，且證據綁定當下受驗內容 digest
- 範圍內驗證通過後預設自動前進，不把每個 checkpoint 變成新人工關卡
- 失敗／缺證據／受驗內容或驗證條件已變：不得宣告完成，也不得沿用舊成功結果

## 三類案例流程摘要

### small-bug
- 輸入：修復 `subtract` 符號、補回歸測試、不改 `add`
- 授權成果：正確減法行為 + 回歸測試
- 計畫可調：先測後改／先改後測、搜尋方式
- 必須停點：擴大到无关模組、改 `add` 行為、沒跑回歸卻宣稱完成

### medium-feature
- 輸入：`low_stock` + CLI + 文件／測試
- 授權成果：閾值行為、排序、CLI 文本／JSON、文件同步
- 計畫可調：實作順序（inventory→cli→docs）
- 必須停點：改 inventory JSON schema、新增未授權子命令、無測試證據完成

### acceptance-change
- 輸入：先做 normalize_labels，中途追加 case-insensitive dedupe
- 授權：第一次契約與第二次修訂契約分開核准
- 計畫可調：重構內部 helper
- 必須停點：未重核准就實作新 acceptance；用舊證據關閉新契約版本
