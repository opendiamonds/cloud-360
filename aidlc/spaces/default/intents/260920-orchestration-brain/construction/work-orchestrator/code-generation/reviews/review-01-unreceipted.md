# 審查紀錄（無收據）— `U12 work-orchestrator` code-generation iteration 1

> **審查有效、收據缺失。** 審查員依 brief 只跑本單元 8 個測試模組（`PYTHONDONTWRITEBYTECODE=1 python3 -B`），
> 但其中的 hypothesis 測試在 `backend/.hypothesis/unicode_data/15.1.0/` 建立了快取檔，使工作區來源指紋在
> `REVIEW_REQUESTED`（2026-10-12）之後改變；`REVIEW_COMPLETED` 兩次被拒（「workspace source changed after
> REVIEW_REQUESTED iteration 1」），刪除該快取檔後仍被拒。本站審查額度為 1，無法重新送審。
> 此為 `project.md ## Mandated` 已記載的同類死結（`source-fingerprint-includes-caches`）。依該條，**不得**為取得收據
> 而補記一次 `REVIEW_REQUESTED`。使用者 2026-10-12 裁決：存成本紀錄，修正後完成本站。
>
> | audit 事件 | 狀態 |
> |---|---|
> | `REVIEW_REQUESTED` iteration 1 | 已記錄 |
> | `REVIEW_COMPLETED` iteration 1（NOT-READY） | **缺**（引擎拒收） |
>
> 以下為審查員原文，未改動。

### 審查原文

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-12T07:13:51Z
**Iteration:** 1

### Findings

| ID | Severity | Status | Location | Finding | Required action |
|---|---|---|---|---|---|
| R-01 | Major | New | backend/services/work_orchestrator.py:945-960 (`_fail_item` 的 timeout 分支) 與 :867-868、:211 附近的 `_execute` | 「成本分析逾時」這條最常見的路徑會取消自己。`_poll_advice` 於快照判為 timeout（`failed` 且 `timed_out`、或 `generating` 且 `started_at` 超過 5 分鐘）或輪詢迴圈搶先到 deadline 時，會在 `_execute` 的內層 task 裡拋出 `_Failed(..., "timeout")`。`_fail_item` 在比對後寫入成功之後，對 category 為 timeout 的失敗取消 `self._tasks[item_id]`。該 task 是外層 `_run`，而不是 `asyncio.current_task()`（目前是內層 `_execute` task）。`_run` 收到取消後會再取消內層，所以 `_fail_item` 剩下的工作會在第一個真正讓出事件迴圈的 await 被截斷：work_items 推送、「沒有完成：成本分析逾時」訊息、`_advance_dependents` 都不會做。狀態在 Redis 已寫成失敗，使用者畫面卻停在處理中，要等下一次 dispatch／correct／list 才會補上。實測：把 `RecordingSink` 的三個 emit 方法各加一次 `await asyncio.sleep(0)`（真實 WebSocket sink 一定會讓出），再跑 `CostPollingTest.test_polling_is_bounded_and_ends_in_cost_timeout` 的情境，結果 status=失敗，但 `sink.turns == []` 且 `sink.session` 只有一筆「處理中」。只有 `_run` 看門迴圈那條路徑不受影響（它在 `_run` task 自己內執行）。 | 讓 `_fail_item` 的取消判斷排除所有屬於本條執行鏈的 task：不要在 `_Failed` 路徑取消 `_run`（內層本來就會結束），只在 `_recover` 這類外部呼叫者才取消；或把取消延到所有副作用完成之後。補一個回歸測試：sink 在每個 emit 讓出一次，斷言 timeout 之後推送、失敗訊息與等待者推進都有發生。 |
| R-02 | Major | New | backend/tests/work_orchestrator_fakes.py:99-130（`RecordingSink`）與 backend/tests/test_work_orchestrator_flow.py 全檔 | 測試替身掩蓋了 R-01 這整類缺陷。`RecordingSink.emit_*` 雖宣告為 async，卻從不真正讓出事件迴圈，所以所有「先取消後完成」「部分完成後被取消」的交錯在 33 個流程案例中都不可能出現。code-summary 的突變表（M1–M9）也沒有一項涵蓋取消時機。測試的自我信心被高估：全部 88 案在本機皆綠，卻藏著 R-01。 | 把 `RecordingSink` 預設改為每次 emit 先 `await asyncio.sleep(0)`（或提供兩種 sink 並讓流程測試以讓出版本再跑一遍），並新增至少一個以取消為主題的突變：把 `_fail_item` 的取消條件改成無條件，確認測試轉紅。 |
| R-03 | Minor | New | backend/services/work_orchestrator.py:100-112（`_run` 看門迴圈） | `_run` 在啟動時只讀一次 `deadlineAt`，之後即使項目已經因 `_complete` 的比對後寫入轉為完成（`deadlineAt` 已清為 null），只要內層 task 還在做收尾（寫記憶、推送、送完成訊息、推進等待者），時鐘越過舊 deadline 就會取消內層。此時 `current["status"]` 已不是處理中，所以不會補任何失敗，但完成訊息或等待者推進可能被截斷。窗口很窄（收尾通常不到一秒），但後果與 R-01 同形。 | 完成或失敗的比對後寫入成功後，看門迴圈不應再取消內層；例如讓內層在寫入成功後以 shield 完成收尾，或讓看門迴圈每圈重讀 `deadlineAt`／status 後再決定是否取消。 |
| R-04 | Minor | New | backend/tests/test_work_orchestrator_boundaries.py（`test_logger_name`） | 該測試只在原始碼含 `getLogger` 時才斷言 logger 名稱，`work_orchestrator_capabilities.py` 沒有 `getLogger` 時等於空轉。另 `model_dump()` 後再 `model_validate` 的二次驗證（work_orchestrator.py `_emit`）只驗證剛驗證過的實例，不增加保證。這兩處是無害的虛設檢查。 | 讓 `test_logger_name` 對 `work_orchestrator.py` 無條件斷言；`_emit` 的二次驗證可保留，但在註解標明它不是額外的契約防線。 |
| R-05 | Minor | New | backend/services/work_orchestrator.py（所有 `self._store.*` 呼叫）與 backend/services/redis_gateway.py:306（`sleep=time.sleep`） | `SessionStore` 是同步 API，`WorkOrchestrator` 在事件迴圈上直接呼叫（`load_work_items` 為冪等讀取，連線錯誤時閘道會以 `time.sleep` 退避重試）。Redis 抖動時，同一進程的所有 WebSocket 連線會被阻塞。functional-design／nfr-design 只要求 facade 呼叫走 `to_thread`，沒有涵蓋 store，所以不算違反計畫，但 code-summary 也未揭露這個取捨。 | 在 code-summary 的偏離與揭露補一行，說明 store 呼叫在事件迴圈上同步執行及其風險，並交由 `U13`／`build-and-test` 決定是否包 `to_thread`。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest`（本單元 7 個模組加 `tests.test_redis_gateway_noscript`） | `Ran 88 tests ... OK` | 本單元測試全綠；與 code-summary 的 85 案加 F1 的 3 案一致。 |
| 讓出式 sink 重跑（暫存於 scratchpad，未改動任何受審檔） | `CostPollingTest.test_polling_is_bounded_and_ends_in_cost_timeout` 轉紅，status 為失敗但無推送與失敗訊息 | 證實 R-01。其餘三個紅燈是我停用 logging 造成的人為結果，與缺陷無關。 |
| 26 項帶入處置抽查 | 在途存檔 shield 與獨立 client、`_advance` 寫入成功才啟動、先記錄再送出、Lua 補丁合併與 null 與空陣列、停用判定、注入時鐘、AST import 檢查、訊息經契約模型驗證，皆在程式中找到對應實作，且測試覆蓋 | 除 R-01 外，帶入處置為真實實作，不只是測試名稱對上。 |
| 跨單元修改 diff | `session_store.py`、`session_types.py`、`hierarchy_facade.py`、`hierarchy_service.py`、`redis_gateway.py` 皆只新增（`git diff --stat` 無刪除行，唯一的 `-1` 是無關的 `aidlc-state`／audit 檔） | 只新增、未改既有語意。F1 的 `isinstance(exc, types.noscript)` 先判型別、保留字串前綴退路，向後相容；`list_diagrams_of_system` 先授權再依擁有者範圍過濾，符合 `BR6.1`。 |
| 安全抽查 | log 只記 workItemId、能力、狀態、stage 與例外類別名；`CapabilityError` 不帶 `str(exc)`；token 只在 `_Ctx` 與 client 標頭；授權測試走真實 `main.app` 與 SQLite，不 mock `user_can` | 未發現 token 或原句外洩路徑；未發現未揭露的 import 邊界違反。 |

### Summary

Critical 0、Major 2、Minor 3。26 項帶入處置整體為真實實作，跨單元修改只新增，F1 修正正確且向後相容，安全與授權邊界站得住。阻擋點是 R-01：成本逾時這條常見路徑，`_fail_item` 會取消自己的外層 task，讓真實（會讓出的）sink 收不到失敗推送與訊息，也不會推進等待者；R-02 指出測試替身從不讓出事件迴圈，所以 88 案全綠卻看不見這個缺陷。修掉取消邏輯並補上讓出式 sink 的回歸測試後即可重審。偏離清單 D1–D11 與開放項大致完整，唯獨 R-05（store 在事件迴圈上同步呼叫）未揭露。
