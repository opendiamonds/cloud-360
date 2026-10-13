# 觀測設計 — `U13 brain-gateway`

> 承接 `../nfr-requirements/observability-requirements.md` 的 `NFR13.34`–`NFR13.38`，並結案 `OPEN-GW13-8`（指派本站）。

## 一、logger 與格式（`NFR13.34`）

- `logger = logging.getLogger("cloud360.brain_gateway")`，`brain_gateway.py` 與 `brain_gateway_rules.py` 共用（後者只在
  `is_transient_memory_failure` 等純函式**不**記 log，故實際上只有前者寫 log；共用名稱是為了日後不出現第二個名稱）。
- 所有紀錄以固定的 `%s` 格式字串輸出，事件名在前、`key=value` 在後；**只有** `BR67.3` 的允許欄位能出現在引數裡。為讓這件事
  可被機械檢查，本單元只經一個出口：

```text
_ALLOWED = frozenset({"connId","sessionKey","turnId","type","code","closeCode","reason","exc",
                      "elapsedMs","preClassifyMs","classifyMs","toFirstContentMs","outcome","prefetch","count","skipped"})
def _log(level, event, **fields):
    assert fields.keys() <= _ALLOWED        # 測試期即失敗；正式環境 python -O 時略過，仍由 AST 檢查把關
    logger.log(level, "%s " + " ".join(f"{k}=%s" for k in fields), event, *fields.values())
```

AST 檢查：本單元模組內 `logger.` 的直接呼叫數為 0（全部經 `_log`）。

## 二、逐輪計時（`NFR13.35`；`NFR13.1` 的量測原料）

每個使用者輪次一個 `TurnTimer`（handler 區域變數），時間全部取自 `timing.monotonic()`：

| 欄位 | 計算 |
|---|---|
| `preClassifyMs` | `t_classify_start − t_received`（`receive_text` 回傳時刻） |
| `classifyMs` | `t_classify_end − t_classify_start`；攔截輪次為 `null` |
| `toFirstContentMs` | `t_first_content − t_classify_end`；`t_first_content` 由 sink 的 `emit_in_turn` 或 handler 的 token／`clarify` 送出在**第一次** `send` 回傳後寫入；攔截或無內容為 `null` |
| `outcome` | `done`／`error:<code>`／`clarify`／`ended_silent`／`guard` |
| `prefetch` | `MemoryWorker.run` 的 `Outcome`：`hit`（有結果）／`empty`（成功但 0 筆）／`failed`／`breaker_open`／`busy_skipped` |

輪次結束（終止事件送出、或 `ended_silent`）時 `_log(INFO, "turn_end", turnId=…, …)` 恰一筆。`clarify` 之後該輪未結束：
`outcome=clarify` 的紀錄在送出 `clarify` 時寫一筆，使用者選定後的續輪以同一 `turnId` 再寫一筆 `turn_end`（`build-and-test`
統計時以 `turnId` 去重）。毫秒值為 `int(round(差值 * 1000))`。

## 三、連線、拒絕與熔斷（`NFR13.36`、`NFR13.37`）

| 事件 | 等級 | 欄位 |
|---|---|---|
| `ws_refused`（未 accept） | INFO | `reason` ∈ {`no_protocol`, `global_limit`, `per_key_limit`} |
| `ws_accepted` | INFO | `connId` |
| `ws_ready` | INFO | `connId`, `sessionKey` |
| `ws_closed` | INFO | `connId`, `sessionKey`（認證前關閉時為空）, `closeCode` |
| `frame_rejected` | INFO | `connId`, `reason` ∈ {`too_large`, `rate_conn`, `rate_key`}, `count`（該連線累計） |
| `memory_breaker_open` | WARNING | `exc`（觸發的例外類別名） |
| `memory_breaker_close` | INFO | `skipped`（開啟期間跳過次數） |
| `episodic_write_failed` | WARNING | `turnId`, `exc` |
| `memory_busy` | INFO | `count`（行程累計；每 100 次記一筆，避免洗版） |

熔斷開啟期間與執行器滿的跳過**不逐則**記 WARNING：前者累計在 `BreakerState.skipped`，於關閉時隨 `memory_breaker_close` 輸出；
後者每 100 次輸出一筆 INFO。`connId` 為 `secrets.token_urlsafe(8)`，不含使用者資訊。

**揭露**：本機預設 `EMBEDDING_PROVIDER=fulltext` 下，`MemoryFacade.write` 必拋設定錯誤（`memory_facade.py:230`），它不開熔斷
（`reliability-design.md` §3.1），故本機每個有交辦的輪次都會產生一筆 `episodic_write_failed` WARNING——這是 `NFR13.24` ③ 的
字面要求（每次失敗一筆），在本機會顯得吵。列 `logical-components.md` §四 `OPEN-GW13-18`。

## 四、關聯鍵（`NFR13.38`；結案 `OPEN-GW13-8`）

- `turnId` 由 `secrets.token_urlsafe(16)` 鑄造，傳入 `classify(..., turn_id=T)` 與 `dispatch(..., turn_id=T)`，並出現在本輪
  本 logger 的每一筆紀錄。
- 預取：`MemoryWorker.run` 前後各記一筆 DEBUG `prefetch_start`／`prefetch_end`（`turnId`、`elapsedMs`、`prefetch`）。
  `MemoryFacade.search` 自身的 log 由 `U8` 擁有、無 `turnId` 欄位；本單元**不**改 `U8` 的 logger、不加全域 logging filter
  （會影響整個行程的 log 管線）。關聯方式為：同一行程內 `prefetch_start` 與 `prefetch_end` 之間、同一工作執行緒名稱
  （`brain-memory_N`，若 log 格式含 `threadName`）的 `U8` 紀錄屬於該 `turnId`。**`OPEN-GW13-8` 在本站結案**：本單元這一半已
  承接；`U8` 的 log 不帶 `turnId` 列為接受的殘留，若日後需要，由 `U8` 的修訂在 `search` 增加可選的關聯參數。
