# 效能設計 — `U13 brain-gateway`

> 承接 `../nfr-requirements/performance-requirements.md` 的 `NFR13.1`–`NFR13.6`，並把帶入清單（`../carried-review-items.md`）
> 第 5、14、15 項中屬於「做法」的部分定成設計。時間來源一律為 `GatewayTiming`（定義見 `reliability-design.md` §一），本檔不另
> 直呼 `time.monotonic`／`asyncio.sleep`／`asyncio.wait_for`。撰寫時間 2026-10-13T00:00:25Z（`date -u`）。

## 一、交接膠水的預算：各段獨立判定（`NFR13.1`；帶入項 14）

| 段 | 預算（P50） | 起點 → 終點（皆以 `GatewayTiming.monotonic()` 取值） |
|---|---|---|
| (a) 分類前 | 400 ms | 收到訊框（`receive_text` 回傳）→ 呼叫 `classify` 之前 |
| `U11` classify | 800 ms | `classify` 呼叫前 → 回傳（`U11` 的 `NFR3.60`，非本站） |
| (b) 分類後 | 300 ms | `classify` 回傳 → 該輪第一則內容 token 或 `clarify` 送出（`send_text` 回傳） |

**表述更正（帶入項 14）**：三段**各自**是一個獨立的 P50 預算，各自以 `NFR13.35` 的 log 欄位統計、各自判定通過與否。
上游 `performance-requirements.md` 的「400＋800＋300＋500＝2000」只用來說明**預算如何分配**，**不**主張「三段 P50 各自達標
則端到端 P50 ≤ 2000 ms」——P50 不可相加（三個分佈的中位數之和不等於和的中位數）。端到端 `NFR3` 仍由 `build-and-test`
以端到端量測直接判定。**本站無法判定 `NFR13.1` 是否達成**：本 repo 沒有延遲量測機制（`requirements.md` 的 `N-3` 尚未
存在），量測落點為 `build-and-test`；本站只保證量測原料（`NFR13.35`）的欄位與歸因正確。上游 NFR 檔的字面回補留給
code-generation（列 `code-summary.md` 的取代關係表）。

## 二、「先送、後做」的結構（`NFR13.2`）

- `GatewaySink.emit_in_turn(turn_id, tokens)`：檢查 `TurnLedger.allows("token")` 為真 → 對每則 token 立即
  `await conn.send(...)`（經 `scalability-design.md` §四的送出路徑）→ `ledger.content("token")`。**不**累積到 `dispatch` 回傳才送。
- episodic 寫入：送出 `done` 的 `await` 回傳之後，以 `self._spawn(self._write_episodic(...))` 建背景 task，handler 不 `await`
  它即繼續讀下一個訊框。`_spawn` 把 task 放入 `self._bg_tasks: set[asyncio.Task]`，`add_done_callback` 移除並取回例外
  （避免「Task exception was never retrieved」與被 GC 回收）。背景 task **不持有**連線物件、websocket 或 handler 的 DB session；
  它只帶入值：`principal`、`content` 字串、`turn_id`（見 `reliability-design.md` §五）。

## 三、離開事件迴圈的呼叫一覽（`NFR13.4`、`NFR13.5`）

### 3.1 本單元觸發的全部 I/O

| # | 呼叫 | I/O 種類 | 在迴圈上？ | 移開方式 | 等待上限 |
|---|---|---|---|---|---|
| 1 | `get_user_from_token(record=True)` ＋ `user_can(K1)` ＋ `mint_principal`（握手） | PostgreSQL | 否 | `asyncio.to_thread(_auth_once, token, record=True)`；`_auth_once` 內 `db = SessionLocal()`，`finally: db.close()` | 無（DB 驅動自身逾時；未設本單元上限） |
| 2 | 同上（每則訊息，`record=True`） | PostgreSQL | 否 | 同上 | 同上 |
| 3 | 同上（60 秒背景重驗，`record=False`） | PostgreSQL | 否 | 同上 | 同上 |
| 4 | `SessionStore.load` | Redis | 否 | `to_thread` | `redis_gateway.py:93` `COMMAND_TIMEOUT_SECONDS=1.0`，冪等重試 `MAX_RETRIES=2`（`:99`），重試睡眠為執行緒內 `time.sleep`，最壞約 3.3 秒 |
| 5 | `SessionStore.append_message` | Redis（Lua，`idempotent=False`，`session_store.py:275`） | 否 | `to_thread` | 單次 1 秒、不重試 |
| 6 | `SessionStore.set_sharing_mode` | Redis（`idempotent=True`，`:339`） | 否 | `to_thread` | 同 #4 |
| 7 | `SessionStore.set_work_target`（內含 `hierarchy_facade` 轉接器開 DB session） | Redis ＋ PostgreSQL | 否 | `to_thread` | 同 #4 |
| 8 | `SessionStore.load_work_items` | Redis | 否 | `to_thread` | 同 #4 |
| 9 | `HierarchyFacade.list_projects` ＋ 每專案 `list_systems` | PostgreSQL | 否 | **一次** `to_thread(_build_catalog, principal, selected_project_id)`，同一 DB session | 無 |
| 10 | `MemoryFacade.search`（預取，內含嵌入） | PostgreSQL ＋ 嵌入（Ollama HTTP／`fastembed` 行程內） | 否 | `MemoryWorker`（專用執行器，§3.2） | `PREFETCH_WAIT_SEC`（現值 3.0，依 §四定值） |
| 11 | `MemoryFacade.write(episodic)` | PostgreSQL ＋ 嵌入 | 否 | `MemoryWorker` | `EPISODIC_WAIT_SEC = embedding_port.EMBEDDING_TIMEOUT_SEC + 5.0`（見 `reliability-design.md` §三） |
| 12 | `IntentRouter.classify` | LLM HTTP（`U11` 內部，async） | 在迴圈上但為 `await` | 不需移開（非同步 I/O） | `U11` 自身 |
| 13 | `WorkOrchestrator.dispatch`／`correct`／`list_items` | `U12` 內部 | `U12` 對 `SessionStore` 的同步呼叫**在迴圈上** | **不包裝**（具名殘留 `OPEN-GW13-4`，最壞約 3.3 秒） | `U12` 自身 |
| 14 | `websocket.send_text`／`receive_text` | 網路 | 是（async） | 不需移開 | 送出 `SEND_TIMEOUT_SEC=10.0`（`scalability-design.md` §四）；接收見 hello 10 秒，其餘不設 |

`_auth_once`、`_build_catalog`、`_session_call` 三個 thread 函式是本單元唯一的同步執行體；handler 與 sink 內不出現任何同步
I/O 呼叫。**判準的機械形式**（`NFR13.4`）：測試把 #1–#9 的替身包成「記錄 `threading.get_ident()`」，走完需求檔指定的全路徑，
九類皆非迴圈執行緒；突變（把 #4 改為直呼）→ 紅燈。

### 3.2 `MemoryWorker`：在途上限以實際執行緒完成計數（`NFR13.5`；帶入項 5、15）

```text
class MemoryWorker:
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="brain-memory")
    _slots    = threading.BoundedSemaphore(4)     # 跨執行緒：迴圈取、工作執行緒放
    _breaker  : BreakerState（僅迴圈執行緒讀寫，見 reliability-design.md §三）

    async def run(self, fn, *, wait_sec, purpose) -> Outcome:
        if breaker 為 open（且非半開探測者）: return Outcome.BREAKER_OPEN        # 不取位
        if not self._slots.acquire(blocking=False): return Outcome.BUSY_SKIPPED  # 不排隊、不開熔斷
        def _job():
            try:     return fn()            # fn 內自開 DB session、finally 關閉
            finally: self._slots.release()  # ← 位子在「執行緒實際結束」時才歸還
        fut = loop.run_in_executor(self._executor, _job)
        try:     result = await timing.wait_for(fut, wait_sec)
        except BaseException as exc: return breaker.on_failure(exc)  # 分類見 reliability-design.md §三
        breaker.on_success(); return Outcome.OK(result)
```

- **為何以執行緒完成計數而非 `wait_for` 逾時**（帶入項 15）：`wait_for` 逾時只取消 asyncio 端的包裝 future，執行緒內的嵌入
  仍跑到它自己的 httpx 逾時為止。若在 `wait_for` 逾時時歸還位子，第 5 件工作會被送進執行器的**內部佇列**排隊——正是需求
  要禁止的。`BoundedSemaphore.release()` 寫在 `_job` 的 `finally`，故「同時在途」等於「實際佔用中的執行緒數」，恆 ≤ 4；
  `max_workers=4` 與號誌同為 4，執行器內部佇列恆為空。
- `acquire(blocking=False)` 在迴圈執行緒上呼叫，為非阻塞、微秒級；不是 `await`，不讓出。
- **判準**：① 替身記錄執行緒名稱，#10、#11 以 `brain-memory` 開頭、#1–#9 皆否；② 4 個「等待測試釋放的 `threading.Event`」
  的嵌入替身佔滿位子，其中**已讓 `wait_for` 逾時**的 2 件仍未釋放：第 5 則訊息的預取回 `BUSY_SKIPPED`，熔斷狀態不因此開啟
  （`BUSY_SKIPPED` 不經 `on_failure`）；同時 `load` 與重驗在 1 秒內完成。釋放 Event 後下一則取得位子。第 ② 案的「已逾時仍
  佔位」是帶入項 15 的突變靶：把 `release()` 移到 `except TimeoutError` 分支 → 紅燈。

## 四、預取等待上限的定值程序（`NFR13.3`；帶入項 5 的「依實測調整」）

`PREFETCH_WAIT_SEC` 為模組常數，**程式碼現值 3.0**，由 code-generation 依下列程序定值並寫進 `code-summary.md`：

1. 量測腳本（只在本機手動執行，不進 CI）：對選定的嵌入提供者，以新行程呼叫 `MemoryFacade.search` 1 次（冷載）後，再連續
   30 次（暖機），記錄每次耗時（`time.perf_counter`）。
2. 選定值 = `min(3.0, max(0.5, round(暖機 P95 × 1.5, 1)))` 秒；冷載首呼叫超過選定值時，接受該輪預取逾時（熔斷因此開啟 30 秒，
   見 `reliability-design.md` §三的成本揭露）。
3. 表格欄位：提供者、樣本數、暖機 P50／P95、冷載首呼叫、選定值與算式。缺表即 `NFR13.3` ① 未通過。
4. 部署主機的 Ollama 若無法於 code-generation 量測，以本機 `fastembed`（或 `stub`）的數字暫定、在 code-summary 明記「暫定」，
   Ollama 實測轉 `build-and-test`。

## 五、計費下游之前的四道檢查（`NFR13.6`）

接收迴圈每個訊框的處理順序固定為：① 訊框大小（`len(raw.encode())`，`NFR13.19`）→ ② 頻率窗（`NFR13.20`）→ ③ 重驗
（#2）→ ④ 兩步信封驗證 → ⑤ 文字長度（`BR64.3`）→ ⑥ `prompt_guard`（`BR64.5`）→ 之後才可能呼叫 `classify`。①②⑤⑥ 為
純函式或行程內資料結構，無 I/O。

**「不新增 LLM 呼叫」的檢查形式**（不寫成不會失敗的 grep，見 `security-design.md` §六）：
- AST 檢查本單元兩個模組的 `Import`／`ImportFrom`（含函式內）不含 `services.llm_provider`、`openai`、`langchain*`、`langgraph*`；
- 行為檢查：在一輪完整交辦期間（`classify`、`dispatch` 為替身），以 `unittest.mock.patch` 讓 `httpx.AsyncClient.send`、
  `httpx.Client.send` 與 `socket.create_connection` 一被呼叫即使測試失敗——本單元自身不得產生任何出站連線。四類違規
  （超大訊框、超頻、超長、攔截命中）各一案，`classify` 替身呼叫 0 次。
