## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

前次 review-01 提出的四項 Major（R-01 至 R-04）在凍結的 nfr-design 產出中全部仍然存在，沒有 corrections 檔取代它們。已落地的程式（work_orchestrator.py 檔頭說明與 `_cas`、`_finish_persist`、test_work_orchestrator_boundaries.py 的 ast 檢查）已改採正確做法，所以這四項是「設計文件與程式矛盾，程式這一邊才對」。照字面讀 nfr-design 的人會實作出會出錯的版本。Critical 0、Major 4、Minor 3。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/work-orchestrator/nfr-design/security-design.md 第二節；reliability-design.md 第二節 | 前次 review-01 R-01 已提。security-design 仍規定「每次 `_run` 建一個 AsyncClient，用完即關」，reliability-design 要求 `_finish_persist` 在外層 `_run` 被取消後照常跑完，卻沒說 PUT 用哪個 client。照字面實作時，`_run` 被取消會先關閉 client，在途 PUT 失敗，變更紀錄遺失。程式已改為 `_finish_persist` 自建獨立 CapabilityClient（work_orchestrator.py 檔頭「在途存檔」段），程式是對的，設計是舊的。 | 以 corrections 檔或修訂，明寫 `_finish_persist` 自建並自行關閉 client，token 以參數傳入；測試替身須使用真的 AsyncClient＋ASGITransport。 | New |
| R-02 | Major | construction/work-orchestrator/nfr-design/scalability-design.md 第二節；reliability-design.md 第一節 | 前次 R-02 已提。`_advance` 只描述 `ok` 為真與假兩種結果。Lua 設為 `idempotent=False` 時，連線錯誤會拋 `SessionBackendUnavailable`，此時寫入可能已生效，設計沒有第三種「結果未知」。程式的 `_cas`（work_orchestrator.py 約 390-412 行）已實作重讀確認，並在讀不到時不做副作用，程式是對的，設計缺這一段。 | 把「捕捉例外、重讀、比對補丁欄位、重讀也失敗則不送請求」寫進 scalability-design 第二節與 reliability-design 第一節。 | New |
| R-03 | Major | construction/work-orchestrator/nfr-design/performance-design.md 第二節；reliability-design.md | 前次 R-03 已提。設計只把輪詢迴圈做成可注入時間，沒說背景執行（A1／A3）的牆鐘逾時如何注入；BR56.6 的 `asyncio.wait_for` 用事件迴圈的單調時鐘，NFR12.19 的假時鐘測試無法成立。NFR12.3 的 180 次計法也未寫明。程式已改為 `_run` 看門迴圈以 sleep 切片比對 `clock() >= deadlineAt`，並明寫「每次快照 GET 計一次輪詢」，程式是對的，設計缺這一段。 | 把看門迴圈的逾時機制與輪詢次數計法寫入 performance-design 與 reliability-design，並標明取代 BR56.6 的 `wait_for`。 | New |
| R-04 | Major | construction/work-orchestrator/nfr-design/security-design.md 第三節；performance-design.md 第三節 | 前次 R-04 已提。「走訪 `__dict__` 與 `sys.modules` 差集」的 import 圖檢查不可實作：`from x import f` 不會出現，同一個測試行程內差集恆為空，所以檢查恆真。禁止清單也沒有 `main`（BR51.1）。程式的 test_work_orchestrator_boundaries.py 已改用 `ast` 解析 Import／ImportFrom，設計未同步。 | 設計改為 ast 解析、補 `main`，並補上出站請求只能走 ASGITransport 的行為判準。 | New |
| R-05 | Minor | construction/work-orchestrator/nfr-design/logical-components.md 第一節；security-design.md 第四節 | 前次 R-05 已提。設計未讓 session 工廠可注入，且把 `HierarchyFacade.list_diagrams_of_system` 當成未交付的 U7 擴充。現況：該方法已存在於 hierarchy_facade.py:481，程式也已有 `session_factory` 建構參數（work_orchestrator.py:193）。這兩點的程式已解，只剩設計文字過期。 | 更新 logical-components 的依賴說明，並在 security-design 第四節註明 `session_factory` 可注入。 | New |
| R-06 | Minor | construction/work-orchestrator/nfr-design/reliability-design.md 第二、五節 | 前次 R-06 已提。`_finish_persist` 另成 task 後，`_run` 的最外層 `except` 不再涵蓋它，設計沒有說它自帶例外處理，也沒有指定 PUT 的 httpx timeout。程式已有自有最外層例外處理與 60 秒 PUT 上限，設計未記。 | 把「自帶 try／except、PUT 上限 60 秒」寫進 reliability-design。 | New |
| R-07 | Minor | construction/work-orchestrator/nfr-design/traceability.json；logical-components.md 第四節 OPEN-WO12-9 | 前次 R-07、R-08、R-09 已提而未處置：NFR12.19 的追溯目標仍指向 reliability-design（實際內容應在 performance-design）；NFR12.27、NFR12.29 在 logical-components 沒有設計內容；OPEN-WO12-9 未揭露「失敗且 PUT 為 2xx 仍寫變更紀錄」這項對 BR55.7 的偏離，也未記載 persisting 孤兒在重啟後永遠沒有變更紀錄的 ADR-0006 稽核殘餘風險。 | 修正追溯目標，補 NFR12.27／12.29 的做法，在 OPEN-WO12-9 增列偏離與殘餘風險。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀 nfr-design 全部 7 份產出與 reviews/review-01.md | 前次四項 Major 的原文仍在凍結產出中，無 corrections 檔 | R-01 至 R-04 未處置 |
| 讀 backend/services/work_orchestrator.py（檔頭、`_cas`、`_finish_persist`） | 程式已採用修正後做法 | 設計與程式矛盾，程式正確 |
| grep `list_diagrams_of_system` 於 backend/services | hierarchy_facade.py:481 已存在 | R-05 的未交付依賴已消除 |
| 檢視 tests/test_work_orchestrator_boundaries.py | 已用 `ast.Import`／`ast.ImportFrom` | 程式側已解 R-04 |
| 測試、lint | 未執行（brief 禁止產生快取） | 本站為設計文件審查 |
