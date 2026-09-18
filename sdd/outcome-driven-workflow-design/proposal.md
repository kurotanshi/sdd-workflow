---
schema_version: 2
---
# outcome-driven-workflow-design

## 狀態
approved

## 類型
研究

## 為什麼做
Issue #13（https://github.com/kurotanshi/sdd-workflow/issues/13）原先聚焦 Skill 瘦身與完成證據。使用者已明確允許重新設計流程，不要求沿用現有架構。本研究要回答：將「核准成果與邊界」和「Agent 可調整的施工計畫」分開，以可驗證 checkpoint 推進，能否減少不必要的中斷與執行成本，同時維持範圍控制及完成判定的可信度？

目前 `approval.py::project_approval_manifest()` 把 task 文字與順序納入核准基線，`complete-task` 以 task digest、snapshot 與核准狀態判定可否更新進度；它不檢查產品測試是否通過。主 Skill 則規定逐條 task 執行。這些是待比較的現況，不預先視為新流程必須沿用的設計。

專案已有成本對照工具及小修、跨檔功能、中途改需求三類 fixtures，也有 approved 的 `simplify-skill-release-evals` 提案（建立本提案時完成 3／4 條）。本研究另行探索流程，不改寫該提案、未提交工作或其發版驗證。研究產出供後續改版決策使用，不以主文件達到 5 KB 或保留既有命令作成功標準。

## 要改什麼
- 設計取向：以穩定的成果契約承載使用者核准，以可調整的施工計畫支援 Agent 自主執行，以 acceptance 對應的證據支援完成判定；既有 task、CLI、schema、metadata 與 archive 結構都可以被替換。正式產品改版與資料遷移在研究結論之後另立提案，因為本次先要驗證流程與必要狀態，而不是先承諾一套架構。
- 先凍結現行流程基準與共同實驗條件：記錄確切 commit、工作樹或套件內容雜湊、相關未提交差異、Agent host／model、權限、fixtures、共同 prompts 與量測定義。既有提案若仍在進行，以獨立唯讀快照作基準，不把後續工作樹變動混入同一比較；歷史成本報告只作背景，不直接和新模型的結果混算。候選套件及 workflow prompts 待原型完成後、正式收集前另行凍結，連同實驗 adapter／scorer 內容雜湊一併記錄；收集後改動任一實驗輸入必須另編版本，舊結果保留但不得混算。
- 設計「釐清成果與驗收 → 核准範圍 → 自主執行 checkpoint → 提出驗收證據 → 使用者驗收與結案」流程。明確界定對外行為、acceptance、重要限制及具有實質影響的風險變更何時使核准失效；施工順序、搜尋方法、內部步驟拆合在成果契約不變時可調整，不逐次要求使用者批准。Agent 不能藉重新描述施工計畫擴張授權，無法判定是否越界時須提出具體決策問題。
- 定義 checkpoint 的可驗證成果、acceptance 對應、完成證據、失敗處理與繼續條件。一個 checkpoint 可以涵蓋多個相依修改，粒度依回饋速度與變更風險決定；範圍內完成驗證後預設自動前進，不把每個 checkpoint 變成新的人工關卡。未完成、測試失敗或必要證據無法取得時不得宣告完成；沒有專案宣告的品質指令仍須有 acceptance 證據，且不得虛構新的全專案品質要求。
- 定義最少必要的持久狀態與責任分工：成果契約及核准版本、可調整計畫、證據引用、進度／結案狀態各自由誰決定、何時寫入，以及跨 session 如何恢復。證據須能追溯到 acceptance、受驗的程式／產物內容及相關驗證條件，而非僅有成果契約版本；即使需求未變，受驗內容、測試或必要環境改變後仍須重新判定證據是否適用，不得直接沿用舊成功結果。對每個持久狀態轉換指出權威、commit point、重試方式與不得重複的副作用；涵蓋證據失效、寫入中斷、回應遺失、並行修改及證據不足。區分 Agent 對證據語意的判斷與 runtime 能強制檢查的結構條件，不把一句完成報告或一次 exit code 宣稱為完整品質保證。
- 在專案外的可丟棄目錄製作最小流程原型，先用既有工具或輕量指令驗證，再決定是否需要不同 runtime。可在隔離副本修改候選 Skill、必要腳本或實驗 adapter；不得把新行為直接套到目前產品套件、已安裝 Skill 或真實 proposal。至少留下一個可執行的邊界檢查，涵蓋未核准執行、範圍變更未重新核准、缺證據／受驗內容已改卻完成，以及施工計畫合理調整，逐項記錄期望與實際結果，並標明哪些阻擋是程式保證、哪些仍依賴 Agent 遵守。凍結候選前以可控 trace 確認 collector 能辨識額外請示、失敗後修正與錯誤完成；確認兩個 host 實際載入各自指定的套件，記錄共同的其他 Skill／宿主指令，無法確認時列為 setup failure，不聲稱目錄分開即代表宿主上下文隔離。
- 用相同的小修、跨檔功能、中途改需求三類案例，比較凍結的現行流程與候選流程。Codex、Claude 各跑每類一組有效配對，合計 6 pairs／12 valid runs，作探索性 pilot；兩邊使用相同需求、驗收 oracle、專案輸入、每個 host 對應的 model、權限與使用者核准，只讓 workflow 指引不同。移除候選 prompt 中強迫遵守舊 task／CLI 程序的條款，但保留相同使用者授權邊界。沿用既有 harness 中適用的隔離、紀錄與結果收集能力；舊流程專屬 scorer 不得直接當成新流程失敗條件，也不得放寬共同產品驗收來美化結果。
- 正式 pilot 前登記配對順序、成本指標、改善／退化門檻與停止條件；記錄驗收成功、未授權變更、錯誤完成、返工、非必要人工介入、turns、tool calls、tokens 與牆鐘時間。既有 harness 的 turn_count 與 confirmation_turns 來自預定 turn_sequence，僅作腳本成本，不能用來主張人工介入減少；另由 transcript／工具 trace 逐項記錄預定核准以外的阻斷式請示與修正循環，附定位及事前定義的分類。無法判定的事件列為未知，不補成零；額外請示若無事前允許的共同回覆規則，不猜答案、不視為默許，也不讓下一個預定核准跨過尚未解決的決策。Collector 必須能依兩種流程各自的產物位置辨識計畫、進度與結案，不能只看舊 sdd/archive 路徑；產品 oracle 通過與 Agent 在當時是否有有效證據支撐完成宣告分開計分，harness 事後跑測試不補足 Agent 漏做的驗證。有效失敗保留在分母；只有 host／環境無效可重試，每個 slot 最多 3 次嘗試，Critical 事件不可被重試抹除。安全違規使候選不具採用資格；環境阻塞則如實記錄並保留尚未完成的量測任務。12 runs 只支持探索性判斷，不宣稱統計顯著或完成 release gate。
- 將觀察、流程設計、原型與 pilot 證據位置、限制、推薦或否決理由寫入本提案的 `## 結論`。列出後續 runtime／artifact 的保留、刪除或替換建議、Skill 與 eval 的同步範圍，以及舊 proposal 的讀取、核准效力、進度保存與遷移／恢復策略。可以建議 breaking change，但必須明列相容性代價；不預設 zero schema break，也不以破壞相容性作為目標。本研究的完成條件是完成約定設計、檢查及有效 pilot，並如實報告；候選未達安全、行為或效益門檻時，否決候選仍可完成研究，不要求修改候選或替換失敗 run 直到通過。環境阻塞造成的證據缺漏不能算完成。

## 影響範圍
- 本次正式研究產物為 `sdd/outcome-driven-workflow-design/proposal.md` 的結論與同目錄 `tasks.md` 進度；維持此研究提案的現行 Schema v2 與核准流程，候選流程只作用於隔離測試案例。
- 主要參照 `skills/sdd-workflow/SKILL.md`、既有 references、`scripts/sdd_core/approval.py`、`transitions.py`、`terminal_transitions.py`、`snapshot.py`、`docs/architecture.md`、`docs/approval-manifest.md`、`docs/cost-benefit.md` 及相應測試。上述 runtime 路徑均相對於 `skills/sdd-workflow/`。
- 預計重用 `scripts/cost_benefit_experiment.py`、`evals/cost-benefit/fixtures/` 的適用能力與三類案例；候選套件、必要實驗 adapter、凍結 manifest 和 raw traces 存放於專案外研究目錄，確切位置與內容雜湊於執行時記錄。原始紀錄不提交 Git，不改寫歷史實驗或現行 release eval 規範。
- 後續產品實作的檔案範圍由研究決定，可能涉及 Skill、runtime、artifact schema、相容性、文件及測試；這些不是本研究已授權的正式產品修改。本次不更新 GitHub issue、不發版、不 commit，亦不調整 `simplify-skill-release-evals` 的 scope 或狀態。

## 結論

- 已凍結現行流程比較基準：commit `a48a22443d59464221af4caed0575c04db7833a4`、skills/sdd-workflow 內容雜湊、cost-benefit fixtures 雜湊、共同案例（small-bug／medium-feature／acceptance-change）、指標與事件分類；候選套件於原型後另凍為 candidate-v1。詳見 `docs/reports/outcome-driven-workflow-design/baseline-freeze-v1.json` 與外部研究目錄 `/workspace/sdd-outcome-research/baseline/`。
- 設計已將「使用者核准的成果契約」與「Agent 可調整施工計畫」分開；checkpoint 以 acceptance 對應證據推進。三類案例的輸入、授權、可調計畫、必要停點見 `docs/reports/outcome-driven-workflow-design/01-outcome-contract-and-checkpoints.md`。
- 最小持久狀態與異常恢復責任已定義：contract／plan／evidence／progress；證據需綁定契約版本與受驗內容 digest。需求未變但受驗內容或驗證條件改變時，不得沿用舊成功結果。見 `docs/reports/outcome-driven-workflow-design/02-evidence-and-durable-state.md`。
- 專案外最小候選原型與邊界檢查已完成且可重跑：7 項 unittest 全過，涵蓋未核准執行、範圍外修改、計畫重排無需重核准、契約變更需重核准、缺證據完成、證據過期、正常關閉。程式強制與 Agent 責任已在設計中標明。凍結雜湊見 `docs/reports/outcome-driven-workflow-design/candidate-freeze-v1.json`。
- 雙 host（Codex／Claude）12 valid runs 的正式 pilot **未完成**：本環境無已登入／可用的 Codex 或 Claude coding host，屬 setup failure，不是候選有效失敗。已提供 runbook、trace collector／scorer，以及模擬 trace 驗證「事後 oracle 通過不能抹除缺證據完成」。因此目前 **不能** 主張候選降低中斷或成本，也 **不能** 建議直接採用為正式產品流程。
- 建議決策：**修正後再研究（revise）**，不要 adopt，也不宜因環境阻塞而把候選判為否決。下一步最小正式工作：1) 在可用的 Codex+Claude 環境執行凍結條件下的 6 pairs／12 runs；2) 若 pilot 顯示 false completion／越權為零且額外阻斷請示有探索性改善，再另立產品改版提案，將成果契約／證據閘道接入 runtime，並處理舊 proposal 的 task-manifest 相容與遷移；3) 在那之前維持現行 sdd-workflow 產品行為不變。
- 舊 proposal 相容性預判：若未來改為成果契約核准，現有以 task 文字／順序入核准基線的 proposal 不能默認沿用同一核准效力，需遷移或重新核准；完成證據也需從「task digest 完成」升級為「acceptance+受驗內容」證據。此為後續產品提案範圍，不是本研究已授權的產品修改。
- 本研究未修改 `skills/sdd-workflow` 產品套件、未改 `simplify-skill-release-evals`、未發版；原始 live pilot traces 因未產生而未提交。
