# 擴展設計 — `U12 work-orchestrator`

> 承接 `NFR12.12`–`NFR12.15`。

## 一、比對後寫入的 Lua 設計（`NFR12.12`；帶入項 4、7）

`update_work_item.lua`（KEYS[1]=工作階段 key；ARGV=workItemId、預期 status 清單 JSON、預期 dispatchStage、**欄位補丁** JSON）：

1. `EXISTS KEYS[1]` 為 0 → 回 `0`（不建 key；`NFR12.18`）。
2. `HGET` 該 `wi:<id>`；不存在 → 回 `0`。
3. 解碼後比對 `status ∈ 預期集合` 且 `dispatchStage == 預期值`；不符 → 回 `0`。
4. **在腳本內**把補丁合併到讀到的當前值（只覆寫補丁指定的欄位），`HSET` 回寫，回 `1`。

呼叫端傳的是**補丁**而非整個物件，故 `estimateSetId` 等未在補丁中的欄位不可能被過期值覆寫。腳本經
`RedisGateway.eval_script(..., idempotent=False)` 執行——比對後寫入不是冪等的，傳輸層不得自動重送（帶入項 7）。

`put_work_item.lua`：`EXISTS KEYS[1]` 為 0 → 回 `0`；`HSETNX` 該欄位；回其結果。同樣 `idempotent=False`。

## 二、寫入成功者才啟動（`NFR12.13`；帶入項 2）

所有「推進並啟動」的地方（`BR53.2`、`BR53.4`、`BR56.7` 的兩步）共用一個函式 `_advance(item, patch, then)`：
`ok = await update_work_item(...)`；**只有 `ok` 為真**才執行 `then`（建 task、送訊息）。`ok` 為假即重讀、不做副作用。

## 三、測試設計（`NFR12.12`；帶入項 7、9）

- **模型測試**：`hypothesis.stateful.RuleBasedStateMachine`，規則為「背景推進 dispatchStage」「寫 estimateSetId」
  「correct」「復原掃描」「被等待者轉終態」。不變量：(a) 請求已送出時停掉後 sideEffect ≠ none（成本除外）；
  (b) 終態不被改寫；(c) estimateSetId 一旦非 null 永不回到 null；(d) `status=處理中 ⇔ deadlineAt 非 null`；
  (e) `status=等待中 ⇔ dependsOn 非 null`。模型跑在 Lua 的 Python 參考實作上。
- **Lua 一致性**：repo 的 Redis 替身以參考實作模擬 Lua，驗不到真實原子性（`test_session_store_behaviour.py` 檔頭自述）。
  故另寫一支需要真 Redis 的整合測試（與 `backend/tests_pg/` 同性質：opt-in，以環境變數指向 Redis，未設定即 skip 並印出原因），
  對兩支腳本跑同一組案例，斷言與參考實作結果一致。**它不是 CI 閘門**：`ci.yml` 的 backend `unittest` 沒有 Redis 服務，
  `deploy/docker-compose.test.yml` 的 Redis 只供 `ui-regression` 的 Playwright stack 使用。真實原子性因此只由本機 opt-in
  測試與 code review 承擔——這個限制如實寫進 code-generation 的測試計畫，不宣稱已被 CI 鎖住。

## 四、背景執行數量（`NFR12.14`、`NFR12.15`）

不設 executor 與排隊；每條 task 受 `deadlineAt` 約束。實體不變量 (d)(e) 由模型測試承載，不靠 `transition`（帶入項 8）。
