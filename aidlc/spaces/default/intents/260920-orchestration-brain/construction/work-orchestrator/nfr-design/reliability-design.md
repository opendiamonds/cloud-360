# 可靠性設計 — `U12 work-orchestrator`

> 承接 `NFR12.16`–`NFR12.23`，並把 functional-design `review-03` 與 nfr-requirements `review-01` 帶入的可靠性項目定成做法。

## 〇、不採用的模式

| 不採用 | 理由 |
|---|---|
| 自動重試、熔斷器 | `BR56.4` 不重試；呼叫在同一行程內，熔斷沒有意義 |
| 持久化任務佇列 | 新增依賴與進程；重啟由復原掃描處理（`NFR12.17`） |
| 重啟後自動續跑 | 已送出請求的結果未知，續跑可能重複建立 A3 檢視或覆寫圖 |

## 一、步驟順序：先記錄、再送出（`NFR12.21`；帶入項 3、12）

每個有副作用的請求前先以比對後寫入記下要進入的 dispatchStage，成功才送：

| 步驟 | 先寫（預期 → 新） | 再做 |
|---|---|---|
| A1 產圖 | not_dispatched → request_sent | POST A1 |
| 存回 | request_sent → persisting | PUT |
| A3 檢視 | not_dispatched → request_sent | POST A3 |

寫入回 False（被停掉或被搶先）即中止，不送請求。

## 二、在途存檔的收尾（`NFR12.20`；帶入項 1、11）

PUT 與其後的收尾（寫變更紀錄、更新 sideEffect／dispatchStage）包成協程 `_finish_persist`，以
`asyncio.shield(self._spawn(_finish_persist(...)))` 執行：外層 `_run` 被 `correct` 取消或被牆鐘上限取消時，收尾協程照常
跑完。收尾依當下儲存狀態分流：

| PUT 結果 | 當下 status | 收尾 |
|---|---|---|
| 2xx | 處理中 | persisting → result_persisted；寫變更紀錄；完成 |
| 2xx | 已停掉（被 correct） | 寫變更紀錄；sideEffect「已存回架構圖〈名稱〉」；dispatchStage → result_persisted；status 不變（`BR55.7`） |
| 2xx | 失敗（被牆鐘上限或復原掃描判逾時） | 同上一列：圖已改寫，稽核必須如實；status 維持失敗，sideEffect 改為「已存回架構圖〈名稱〉」 |
| 非 2xx | 任一 | sideEffect 依 status：處理中 → 失敗；已停掉／失敗 → sideEffect 改 none |

收尾的每次寫入預期 `dispatchStage=persisting`，故只會成功一次。

## 三、sideEffect 對照統一（帶入項 6、8）

`side_effect_on_stop(capability, dispatch_stage)` 是唯一的對照函式，`BR55.1`（停掉）、`BR56.6`（逾時）、`BR56.7`（逾期掃描）
三處都呼叫它；`persisting` 一律為「可能已存回架構圖〈名稱〉」。functional-design 的 `BR56.7` 文字「其他 → unknown」以本函式為準
（回報 functional-design 下一次修訂）。

## 四、復原掃描（`NFR12.16`–`NFR12.18`）

`_recover(session_key)`：`load_work_items` 一次 → 依序 (1) 逾期 (2) 孤兒等待，每次推進經 `_advance`（`scalability-design.md`
第二節）。推進為處理中時同一個補丁寫 `deadlineAt=clock()+上限`、清 `waitingOn`／`dependsOn`；離開處理中的每個補丁都含
`deadlineAt=null`。

## 五、sink 與失敗隔離（`NFR12.22`、`NFR12.23`）

- `_emit(...)` 包住所有 sink 呼叫：`except Exception` → WARNING log（類別名），不再拋出。
- `_run` 最外層 `except Exception` → 工作項失敗「〈能力名稱〉暫時無法使用」＋ERROR log（類別名），確保 task 不留下未處理例外。
- 輪詢：連續失敗計數器只在非 401／403／404 的錯誤遞增，成功即歸零；401／403 即依 `BR51.6`／`BR51.3` 失敗、404 依 `BR57.4`。
