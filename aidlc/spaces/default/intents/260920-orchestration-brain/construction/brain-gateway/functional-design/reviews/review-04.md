## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

brain-gateway 的功能設計整體自洽：實體、規則、工作流程與 traceability 互相對得上，ADR-0006 四面向在 functional-spec §七有落點，AC1.1.5、AC7.1.x、AC8.1.2 至 AC8.1.4 有承載規則，AC8.1.1 誠實標為 Deferred。主要問題不在設計內部，而在凍結的設計與已落地程式已經分歧：前次 review-03 提出的 1 項 Major 與 5 項 Minor 發生在產出最後修改（2026-10-13 06:45）之後，凍結產出中全部仍在，而程式在若干處已採較安全的作法或因後續 ADR 而改變行為。Critical 0、Major 2、Minor 5，依規則判 READY（Major 不超過 2）。下游實作者應以程式為準處理 R-01 與 R-02，不可照凍結的 BR64.13 與 BR64.12 字面重做。新發現來源分類：既存漏審 0、前次已提且仍留在凍結產出 6（R-01、R-03 至 R-07）、設計與程式分歧 2（R-01、R-02，其中 R-01 同時是前次已提）。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/brain-gateway/functional-design/rules.md > BR64.13 logic 與 BR64.8 kind=intent 分支；functional-spec.md > GW-W3、D-10、OPEN-GW13-5；程式 backend/services/brain_gateway.py:1403-1415 | 前次 review-03 R-01 已提：BR64.13 規定反問選定意圖後以原句子字串掃描目錄（名稱長度 2 以上），恰一個命中即走 BR64.9 直接 set_work_target 並交辦。兩字通用詞（例如專案名為「測試」）會靜默改掉作業對象；巢狀名稱（系統「訂單」與「訂單系統」）會把使用者逐字講出的完整名稱誤判為多個對象。凍結產出至今未處置（產出 mtime 早於 review-03）。設計與程式矛盾：程式 _resolve_and_dispatch 在 scan 命中時一律改走 _clarify_target，並註明「不靜默改動作業對象」，與 BR64.13「恰一個對象走 BR64.9 更新路徑」相反。程式那一邊是對的，因為它守住 BR64.8 與 BR64.11 要防的「工作項建在使用者沒指的對象上」。凍結的設計文字因此成為會誤導下游的過期規格；且低信心路徑（掃描）與高信心路徑（referent 精確相符）的行為差異沒有理由說明。 | 以修正檔（corrections）取代 BR64.13 的恰一個命中行為為「命中一律對象反問確認」，保留巢狀名稱只取最長命中的處理或明文列為已知限制；GW-W3、D-10、OPEN-GW13-5 同步。補測試：原句含兩字通用詞且恰為專案名、巢狀名稱，斷言走對象反問而非靜默切換。 | New |
| R-02 | Major | construction/brain-gateway/functional-design/rules.md > BR64.12 logic 末段；functional-spec.md > OPEN-GW13-16、§六 F-26；traceability.json > AC1.1.5 note；entities.md > TargetCatalog；程式 backend/services/brain_gateway.py:1348-1378 | 設計主張對象目錄只含「使用者為擁有者的專案」，並以「K-07 的 resolve_work_target 目前也不允許成員設為作業對象，故一致」為理由（OPEN-GW13-16）。程式 _build_catalog 已改為 list_projects 與 list_systems 都帶 project_visible=membership_facade.project_visibility(principal)，且 _HierarchyResolver.resolve_work_target（brain_gateway.py:600-610）同樣帶成員可見性，即目錄範圍已是成員可見而非擁有者專屬，OPEN-GW13-16 的前提不再成立，AC1.1.5 的 note 與 TargetCatalog 的描述也隨之過期。程式那一邊是對的（授權範圍由後續 U23 可見性守門決定，且目錄與 resolve_work_target 範圍仍保持一致）。凍結設計的範圍敘述會讓下游或測試作者以擁有者範圍寫斷言，與落地行為牴觸；另 IAM 面向的判定表（functional-spec §七）仍寫擁有者範圍。 | 以修正檔更正 BR64.12、OPEN-GW13-16、entities.md 的 TargetCatalog、traceability AC1.1.5 note 與 §七 IAM 格：目錄範圍＝經 U23 成員可見性過濾後的專案與系統，且與 resolve_work_target 同範圍；同時註記該範圍變動的來源 ADR。 | New |
| R-03 | Minor | construction/brain-gateway/functional-design/rules.md > BR63.2 排序保證、BR63.6；functional-spec.md > GW-W1 步驟 9 | 前次 review-03 R-03 已提：排序保證只在「暫存佇列送完後才改 phase 為 ready」且「送佇列期間新到的訊息不遺失」時成立，但規則只寫「依序送出暫存佇列，最後把 phase 改為 ready」。送出是 await，期間另一協程的扇出仍看到 phase=loading 並附加到佇列（deliver 的判斷與附加之間無 await，brain_gateway.py:694-705，這一半成立）；若實作對佇列取快照再迭代，或迭代結束到改 phase 之間有 await，新增的訊息會遺失，客戶端停在舊狀態。測試只涵蓋 load 與 list_items 之間注入，未涵蓋送出期間注入。 | 寫明：持續從佇列頭取出直到為空，最後一次空檢查與 phase 改為 ready 之間不得有 await；補一個送出期間注入 emit_session 的測試，斷言客戶端最後收到的狀態為最新。 | New |
| R-04 | Minor | construction/brain-gateway/functional-design/rules.md > BR64.12 專案上限分支、BR64.11 (b)；traceability.json > AC1.1.5；程式 backend/services/brain_gateway.py:1411-1412、1435 | 前次 review-03 R-04 已提：專案數超過 50 時目錄不含系統名稱，設計只記 INFO 計數，使用者收到 BR64.11 (b) 的「找不到名為 X 的系統或專案」，這句話不實（系統存在，只是沒掃描）。程式已另加 TOO_MANY_PROJECTS_MESSAGE 並在已選專案時仍載入該專案的系統（:1369-1377），所以設計與程式分歧，程式較好，但設計文字仍寫「不比對系統名稱」。traceability 的 AC1.1.5 未列出超過 50 個專案或 referent 與名稱不逐字相同使 AC 不成立的條件。 | 修正檔補上固定句型 TOO_MANY_PROJECTS_MESSAGE 與「已選專案仍載入其系統」兩點；traceability 的 AC1.1.5 note 補上使 AC 失效的兩項條件。 | New |
| R-05 | Minor | construction/brain-gateway/functional-design/rules.md > BR67.12 熔斷與等待上限；BR67.10 | 前次 review-03 R-05 已提：熔斷器全域，任一次預取或寫入例外即開 30 秒，包括只屬於單一輸入的失敗（過長內容導致嵌入被提供者拒絕），一位使用者可讓全體使用者的記憶預取停 30 秒，而 U11 自承記憶降級可能改變分類結果。預取等待 3 秒低於 Ollama 冷載的合理耗時，一次冷載即觸發熔斷。執行器工作佇列未設上限。 | 熔斷只計入逾時與提供者不可用類例外；說明 3 秒與冷載的關係或調整；為執行器佇列加上限或在逾時時取消尚未開始的工作。 | New |
| R-06 | Minor | construction/brain-gateway/functional-design/rules.md > BR67.11 第 1 點；functional-spec.md > GW-W7 | 前次 review-03 R-06 已提：規格稱「本單元不新增環境變數，故無 LOCAL-DEV.md 同步義務」，但 REDIS_URL、REDIS_USER、REDIS_PASSWORD 從此成為後端啟動必要條件（缺值 KeyError 使整個後端拒絕啟動）。現況：LOCAL-DEV.md 第 22-26 行已把這三個變數列為啟動必要並說明缺值拒絕啟動，所以落地的文件沒問題，但凍結設計的免同步說法仍在，與已落地的文件矛盾。 | 修正檔更正 GW-W7 與 BR67.11 的說法，註記 LOCAL-DEV.md 的更新是 code-generation 的交付條件且已完成。 | New |
| R-07 | Minor | construction/brain-gateway/functional-design/functional-spec.md > 七 PBT 性質五；rules.md > BR64.13 與 BR64.9 | 前次 review-03 R-02 已提：性質五要求「目錄中任一長度 2 以上的名稱，若是原句子字串則其對象在結果內」，BR64.13 卻規定同專案下系統命中時專案名的命中不另計，兩者同時命中時性質不成立，照字面寫成 property-based 測試會紅燈。BR64.9 對「專案與其自己的系統同名」計為兩筆而走對象反問，BR64.13 對同樣情況去重為一個對象，兩條規則給出相反結論；BR64.9 的「去空白」是去頭尾還是去除全部空白未定。此項會隨 R-01 的修正檔一併重寫，但性質五是 ADR-0006 PBT 約束的承載點，須在修正檔明確。 | 把去重規則寫進性質五的前提或結果定義；統一 BR64.9 與 BR64.13 對「專案與其系統同名」的處置；寫明去空白的語意。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 產出時序比對 | 產出 mtime 為 2026-10-13 06:45，review-03 為 07:30 | review-03 的全部發現（Major 1、Minor 5）都發生在最後一次產出修改之後，凍結產出中全部仍在，故本次逐項重列為 R-01 與 R-03 至 R-07 |
| 設計對程式抽查 | 2 處分歧 | brain_gateway.py:1403-1415（掃描命中一律反問）與 :1348-1378（成員可見性目錄）與凍結的 BR64.13、BR64.12 矛盾，程式較安全或較新；對應 R-01、R-02 |
| LOCAL-DEV.md 抽查 | 已更新 | 第 22-26 行已記載三個 REDIS 變數與啟動拒絕語意；凍結設計的免同步說法已過期，對應 R-06 |
| 契約端點三問 | 無孤兒 | entities.md 的每個實體都有寫讀清（摘要表）；GatewaySink、MemoryPrefetch、TargetCatalog、MemoryExecutor 皆有擁有者與呼叫者；OPEN-GW13-12 具名列出 K-16、K-17、K-18 的 consumed_by 不實，屬契約追認而非本單元缺口 |
| ADR-0006 四面向 | 有落點 | functional-spec §七逐項列出（Network exposure 格已確認；IAM 格的目錄範圍敘述過期，見 R-02）；audit 面向以 log 禁令與 BR67.x 承載 |
| 兄弟單元與測試 | 未執行 | 依派工指示不開啟其他單元、不跑測試；U11、U12 的整合點僅以已落地程式的公開行為核對 |
