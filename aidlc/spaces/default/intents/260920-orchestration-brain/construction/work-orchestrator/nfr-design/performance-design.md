# 效能設計 — `U12 work-orchestrator`

> 承接 `../nfr-requirements/performance-requirements.md` 的 `NFR12.1`–`NFR12.5`。

## 一、先回覆、後執行（`NFR12.1`、`NFR12.2`）

- `dispatch` 的同步部分只做：復原掃描 → 建立工作項（`put_work_item`）→ 推送 `work_items` → 以本輪 turnId 送建立／
  等待訊息 → 對處理中項目 `asyncio.create_task(_run(item))` → 回傳。任何對既有能力的 `await` 都只出現在 `_run` 內。
- task 參考存在 `WorkOrchestrator._tasks: dict[str, asyncio.Task]`（以 workItemId 為鍵），task 結束時以
  `add_done_callback` 移除，避免持有已結束的 task。
- 同步 facade 呼叫一律包成 `await asyncio.to_thread(_call_facade, …)`；`_call_facade` 內自開 `SessionLocal()`、
  `finally` 關閉（`BR51.7`）。測試以替身在被呼叫時記錄 `threading.get_ident()`，與事件迴圈執行緒比對（`NFR12.2`）。

## 二、背景負擔（`NFR12.3`、`NFR12.4`）

- 成本輪詢迴圈：`while True: snapshot = await get(); …; await self._sleep(2)`。`_sleep` 與 `clock` 皆由建構子注入
  （預設 `asyncio.sleep` 與 `datetime.now(timezone.utc)`），測試注入可控版本（帶入項 13）。上界由牆鐘上限保證：
  `deadlineAt` 由同一個 `clock` 算出，迴圈每圈先比對 `clock() >= deadlineAt` 即判逾時，不另依賴 `wait_for` 的單調時鐘。
- 估價表搜尋：`page=1` 起逐頁 GET，`page_size=50`（C1 上限），找到第一份 `diagram_id ∈ 目標圖集合` 即 `break`。

## 三、不呼叫 LLM（`NFR12.5`）

- 本單元模組只依賴 `httpx`、`asyncio`、`session_store`、`hierarchy_facade`、`memory_facade`、`brain_ws_contract`、
  `intent_routing_types`。檢查方式見 `security-design.md` 第三節的 import 圖檢查（帶入項 14），不只 grep 字串。
