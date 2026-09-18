# Acceptance 證據與最小持久狀態

## 證據最低欄位
- acceptance_id
- kind / verifier
- result
- subject_digests（受驗檔案內容）
- contract_id + contract_version
- 可選：command、exit_code、stdout hash

證據必須能追溯到：成果契約、受驗內容、驗證條件。

## 狀態與權威

| 狀態 | 權威 | Commit point | 備註 |
|---|---|---|---|
| contract.json | 使用者核准事件 | approve / reapprove | 唯讀直到下一次核准 |
| plan.json | Agent | set_plan / reorder | 不得單獨改變契約 |
| evidence/*.json | Agent 寫入；runtime 結構檢查 | record_evidence | 語意正確性仍有 Agent 責任 |
| progress.json | runtime | complete_checkpoint / close_out / block | completed_checkpoints 只能追加 |

## 異常處理
- 缺證據完成 → runtime 拒絕
- 需求未變但受驗內容變 → digest 不一致，舊證據失效
- session 恢復 → 以磁碟狀態為準，不靠對話記憶覆蓋
- 寫入中斷 → 單一 JSON 檔 atomic replace；半寫入檔視為無效
- 回應遺失 → 以 progress/evidence 是否已提交判定；未提交可重試同一 checkpoint
- 並行修改 → 以檔案 digest 與 contract version 衝突檢測；不靠時間戳定權威

## Runtime 強制 vs Agent 責任
Runtime 強制：未核准、越 scope、缺證據、digest 過期、契約版本不符、計畫綁錯契約。
Agent 責任：verifier 是否真的跑對、請示是否必要、自然語言是否誠實。
