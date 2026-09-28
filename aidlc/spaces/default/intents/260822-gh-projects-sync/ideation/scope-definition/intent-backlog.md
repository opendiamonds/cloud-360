# Intent Backlog — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: scope-definition（Ideation 1.4）· 來源標籤定義見 scope-definition-questions.md 的 ## Sources。
     本檔為 proto-Unit 清單；正式的 Unit 切分屬 units-generation（2.7），Bolt 切分屬 delivery-planning（2.8）。 -->

## 上游輸入

- **intent-statement**（`../intent-capture/intent-statement.md`）：三項成功指標是本 backlog 每一項的驗收方向。
- **feasibility-assessment**（`../feasibility/feasibility-assessment.md`）：RSK-7 決定了本清單的第一順位。
- **constraint-register**（`../feasibility/constraint-register.md`）：C-T7（不得以 repo 內程式承載）約束了每一項的實作形態。

## 優先序表達方式

全部十一項為 Must [Q2] [Q2b] [ADR-0013]，因此優先序不由分級表達，而由**依賴序**表達。本清單不做 WSJF／RICE 數值評分——單一決策者且依賴序已定時，相對分數沒有真實輸入（`project.md ## Corrections`）。

排序偏好為 risk-first [Q3]：最高不確定性的驗證排在最前，讓後續設計在已校準的前提上進行。

## Proto-Unit 清單（依依賴序）

| 序 | Proto-Unit | 內容 | 依賴 | 依賴性質 | 來源 |
| --- | --- | --- | --- | --- | --- |
| 0 | PU-0 憑證可行性實測 | 以最小可行呼叫確認應用程式鑄出的憑證是否真的帶組織層看板寫入權 | P-1、P-2（外部人工） | 技術依賴 | [Q3] [feas:RSK-7] |
| 1 | PU-1 綁定建立 | intent 誕生時自動開 issue、加入看板、設 In progress，並把編號寫回 intent 的紀錄 | PU-0 | 技術依賴 | [Q2] [intent:Q7] [feas:Q8] |
| 2 | PU-2 寫入前回讀確認 | 寫入前比對目標項目，不符即中止並開 issue | PU-0 | 技術依賴 | [Q2b] [feas:Q10] |
| 3 | PU-3 PR 觸發的狀態同步 | PR 開啟→In review、合併→Done；優先於推送 | PU-1、PU-2 | 技術依賴 | [Q2] [feas:Q2] [feas:Q9] |
| 4 | PU-4 推送觸發的狀態同步 | 讀已推送的進度紀錄，依對照表映射寫入；受 PU-3 的優先序約束 | PU-1、PU-2、PU-3 | **避免重工**（PU-3 先定下優先序機制，PU-4 沿用；反序會讓 PU-4 先實作一套之後要改的寫入邏輯） | [Q2] [feas:Q2] |
| 5 | PU-5 失敗通報 | 紅燈＋自動開 issue；對帳不一致亦視為失敗 | PU-1（需有可通報的對象） | 技術依賴 | [Q2b] [intent:Q9] |
| 6 | PU-6 排程對帳 | 低頻掃描並補齊差異，僅涵蓋已綁定項目 | PU-4、PU-5 | 技術依賴 | [Q2] [intent:Q6] [intent:Q12] |
| 7 | PU-7 細粒度進展外置 | 看板自訂欄位承載目前 stage；欄位由機制自動建立，不支援則退回人工 | PU-0、P-4 | 技術依賴 | [Q4] [Q9] |
| 8 | PU-8 驗證層 | 映射邏輯 dry-run 斷言 ＋ 對真實測試項目的端到端驗證 | PU-4（需有映射邏輯可斷言）、PU-1（需有可測項目） | 技術依賴 | [Q2b] [feas:Q6] |
| 9 | PU-9 README 指路文字 | 於 README 增加一段指向 Project #16 為需求清單正本的說明 | 無 | — | [intent:Q11] |
| 10 | PU-10 反向同步 | 定時把看板端的狀態變更（含人工拖動卡片）拉回，開 PR 更新 record；含防迴圈的內容雜湊比對、`[aidlc-sync]` 來源標記與狀態欄位單向三道防線 | PU-1、PU-4 | 技術依賴 | ADR-0013 決定 2 |

### 依賴性質的區分

依 `project.md ## Corrections`，排序約束須區分兩種性質，因為它們在依賴圖上長得一樣但可覆寫性不同：

- **技術依賴**（不可覆寫）：上表除 PU-4 外的所有依賴。缺了前項，後項在機制上無法運作。
- **避免重工**（可由下游在記明緩解方式的前提下覆寫）：僅 PU-4 對 PU-3 的依賴。PU-4 不需要等 PU-3 才能運作，但若先做 PU-4 並以「推送即寫入」的形狀完成，PU-3 引入優先序時會要求改寫該邏輯。

## 交付意向與 Bolt 切分的界線

- 使用者選擇一次做完全部、不分批 [Q1]。此為範圍層意向，**不決定 Bolt 數量**。
- PU-0 為 Must 但**不構成交付批次** [Q3]：它是 application-design 展開前的驗證動作，其產物是一個結論而非可部署的變更。
- PU-9 無任何依賴，可在任何時點併入。
- PU-10 對 PU-4 的依賴是**技術依賴不可覆寫**：ADR-0012 已推理過「沒有穩定的正向同步，反向同步沒有比對基準」，缺了正向寫入，反向拉回無從判斷差異是人為變更還是尚未同步。
- Bolt 切分、以及「十一項一次交付」與短生命週期分支實務的張力，由 delivery-planning（2.8）處理。

## Assumptions & Open Questions

- PU-7 的可行性取決於框架是否支援建立看板欄位，該能力未見於框架的安全輸出清單；不可行時依 [Q9] 退回人工建立，PU-7 的依賴會從 PU-0 改為一項外部人工前置。 [assumption]
- PU-0 的產物是一個結論而非程式碼，其在 Construction 中如何留下可追溯證據（例如寫入 record 或以測試形式固化）尚未定義。 [assumption]
- PU-4 對 PU-3 的「避免重工」依賴其重工成本未量化；下游若有理由反序，需自行評估該成本。 [assumption]
- PU-8 的端到端驗證需要一個真實的測試項目，該項目建立後是否長期保留在看板上尚未決定 [feas:Q6]。 [assumption]

## Revision 1（2026-08-23）

**觸發**：ADR-0013（修訂 ADR-0012）把反向同步從 Won't Have 移入範圍。詳見 `scope-document.md` 的 Revision 1 段與問題檔的 Revision 1 段。

**改動**：新增 **PU-10 反向同步**，依賴 PU-1（需有綁定才知道哪個項目對應哪個 intent）與 PU-4（需有穩定的正向同步作為比對基準），兩者皆為技術依賴。清單總數由 10 項更新為 11 項。

**未改動**：PU-0～PU-9 的內容、依賴與依賴性質皆不受影響；PU-4 對 PU-3 的「避免重工」標記維持不變。risk-first 的排序偏好仍成立，PU-0 仍為首位。

**未解事項**：PU-10 的驗證落點未定。PU-8 的驗證層（dry-run ＋ 真實測試項目端到端）是為正向路徑設計的，反向路徑的正確性判準（「該不該把這個看板變更寫回 record」）與正向不同型。指派 application-design 一併處理。
