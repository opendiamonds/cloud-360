# 可靠性設計 — `U13 brain-gateway`

> 承接 `../nfr-requirements/reliability-requirements.md` 的 `NFR13.23`–`NFR13.33`，並把帶入清單第 1、2、3、4、5、8、9、11、13、16
> 項中屬於「做法」的部分定成設計。對照 `work-orchestrator/nfr-design/reviews/review-01.md` 的四類缺陷，本檔逐一處置：
> 收尾不借用會被關閉的資源（§五）、非冪等寫入的「結果未知」（§四）、時間注入涵蓋**全部**計時路徑（§一）、檢查寫成會失敗的
> 形式（各節的突變靶）。

## 〇、不採用的模式

| 不採用 | 理由 |
|---|---|
| 對 Redis 寫入自行重試 | 冪等寫入已由 `RedisGateway` 重試（`redis_gateway.py:375`）；非冪等的 `append_message` 重試可能重複寫入（§四） |
| 伺服器端補送、緩衝、重播 | `BR63.5`；重連由快照收斂 |
| 熔斷 Redis 或 DB | Redis／DB 失敗已由 `[GW3]`=A 的逐輪 `error` 呈現；它們是本單元的必要依賴，熔斷只會把「慢」換成「全拒」 |
| 半開期間多個並行探測 | 冷載期間每個探測都會付滿等待上限；單一探測者即可判定恢復（§三） |

## 一、時間注入：`GatewayTiming`（帶入項 9）

```text
@dataclass(frozen=True)
class GatewayTiming:
    monotonic: Callable[[], float]                          = time.monotonic
    sleep:     Callable[[float], Awaitable[None]]           = asyncio.sleep
    wait_for:  Callable[[Awaitable[T], float], Awaitable[T]] = asyncio.wait_for
```

`BrainGateway`（`logical-components.md` §一）的建構子收 `timing: GatewayTiming = GatewayTiming()`，往下傳給
`ConnectionRegistry`、`RateLimiter`、`MemoryWorker`、`BreakerState` 的呼叫端與 handler。**全部計時路徑**逐一列舉（寫成表是為了
讓「漏一條」可被機械核對，對照 `review-01` R-03 的教訓）：

| 計時 | 數值（模組常數） | 走哪個注入點 |
|---|---|---|
| hello 等待 | `HELLO_WAIT_SEC = 10.0` | `timing.wait_for(websocket.receive_text(), …)` |
| 背景重驗週期 | `REVALIDATE_INTERVAL_SEC = 60.0` | `while True: await timing.sleep(…)` |
| 頻率滑動窗 | `RATE_WINDOW_SEC = 60.0` | `timing.monotonic()` 時間戳進 deque |
| 記憶熔斷開啟期 | `BREAKER_OPEN_SEC = 30.0` | `timing.monotonic()` 比較 `open_until` |
| 預取等待 | `PREFETCH_WAIT_SEC`（現值 3.0） | `timing.wait_for(fut, …)` |
| episodic 等待 | `EPISODIC_WAIT_SEC`（§三） | `timing.wait_for(fut, …)` |
| 單次送出 | `SEND_TIMEOUT_SEC = 10.0` | `timing.wait_for(ws.send_text(…), …)` |
| 逐輪計時 log | — | `timing.monotonic()`（`observability-design.md` §二） |

**不經注入點的計時一律禁止**：本單元模組內 `time.monotonic`、`time.time`、`asyncio.sleep`、`asyncio.wait_for` 只允許出現在
`GatewayTiming` 的預設值；以 AST 檢查（`Attribute` 節點 `time.monotonic` 等的出現位置）鎖住，新增一處直呼即紅燈。

**測試替身**（code-generation 新增於 `backend/tests/`）：`FakeTiming`——`monotonic` 回傳可推進的浮點；`sleep(s)` 推進後
`await asyncio.sleep(0)`（與既有 `FakeClock.sleep` 同形，`tests/work_orchestrator_fakes.py:93-96`）；`wait_for(aw, t)` 記錄 `t`
並把 `aw` 包成 task，若測試對該次呼叫呼叫 `expire()` 則取消該 task、推進 `t` 秒並拋 `TimeoutError`，否則照常 `await`。
於是 60 秒重驗、滑動窗、30 秒熔斷、3／15 秒逾時、10 秒 hello 皆可在毫秒內驗證（`NFR13.11` ③、`NFR13.20`、`NFR13.25`、
`NFR13.3` ②）。

## 二、依賴不可用（`NFR13.23`）

- 握手內（ready 之前）：`load`／`list_items` 任何例外 → `registry.unregister(conn)`（同步、無 `await`，連同丟棄
  `conn.pending`）→ `close(1011, "internal-error")`。
- ready 之後：`SessionBackendUnavailable` → `error_for` 回 `(INTERNAL_ERROR, "工作階段暫時無法存取，請稍後再試")`，送 `error`
  結束該輪；不關閉、不動登錄；接收迴圈繼續。

## 三、記憶熔斷（`NFR13.25`；帶入項 5、8）

### 3.1 會開啟熔斷的例外（純函式 `is_transient_memory_failure(exc) -> bool`，置於 `brain_gateway_rules.py`）

沿 `exc`、`exc.__cause__`、`exc.__context__` 鏈往下走（深度上限 5，防循環），任一節點符合即回 `True`：

| 節點型別 | 來源 |
|---|---|
| `TimeoutError`（Python 3.11 起 `asyncio.TimeoutError` 即此型別） | 本單元 `wait_for` 的等待上限 |
| `httpx.TimeoutException` 及其子類 | Ollama 的 httpx 逾時，被包成 `EmbeddingProviderUnavailable`（`embedding_port.py:614-618` 的 `raise … from exc`） |
| `httpx.NetworkError` 及其子類（`ConnectError`、`ReadError`、`WriteError`、`CloseError`） | 同上，連線類 |
| `ConnectionError` 及其子類 | 行程內或 socket 層的連線錯誤 |

**不開啟**（只使該次失敗）：`EmbeddingProviderUnavailable` 鏈上**沒有**上表節點者——包括 `EMBEDDING_PROVIDER=fulltext` 時
`_require_port` 拋的設定錯誤（`memory_facade.py:230`，無 `__cause__`）、維度不符（`embedding_port.py:528`／`:538`）、
`fastembed` 未安裝、HTTP 狀態錯誤（提供者有回應即非連線問題）；以及 `MemoryForbidden`、`MemoryInvalidInput` 等。
**理由**：本機預設 `fulltext`（`backend/.env.example:120`），若「任何 `EmbeddingProviderUnavailable` 都開熔斷」，本機的熔斷會
永遠開著；而這些失敗都是立即失敗，不會讓使用者多等，熔斷沒有收益。`httpx` 在 `brain_gateway_rules.py` 內以函式內 import
取型別（與 `embedding_port.py:603` 的作法同形），不新增依賴。

### 3.2 狀態機（純資料，迴圈執行緒獨佔，無鎖）

```text
@dataclass
class BreakerState:
    open_until: float | None = None   # None ＝ 關閉
    probing:    bool         = False  # 半開時是否已有探測者
    skipped:    int          = 0      # 開啟期間跳過次數（observability 用）

admit(now) -> "run" | "probe" | "skip":
    open_until is None            → "run"
    now < open_until              → skipped += 1; "skip"
    not probing                   → probing = True; "probe"
    else                          → skipped += 1; "skip"
on_success()        : 若 open_until 非 None → 記 INFO（含 skipped）；open_until=None, probing=False, skipped=0
on_failure(exc, now): probing=False；is_transient_memory_failure(exc) → open_until = now + 30（由關閉轉開時記 WARNING，含例外類別名）
```

- 鍵為**全域**（每行程一個 `BreakerState`），理由見 `NFR13.25`。
- `BUSY_SKIPPED`（執行器滿）不呼叫 `on_failure`（`performance-design.md` §3.2）。
- 狀態轉移是純函式，以 `hypothesis.stateful` 驗：不變量 (i) `skip` 只在 `open_until` 非 None 時發生；(ii) 半開期間至多一個
  探測者；(iii) 非暫時性例外永不使 `open_until` 由 None 轉為非 None。

### 3.3 寫入路徑等待上限的落差（帶入項 8）

functional-design 把 episodic 等待定為 15 秒、「大於嵌入逾時 10 秒」。實際上嵌入逾時可由 `EMBEDDING_TIMEOUT_SEC` 覆寫
（`embedding_port.py:277`），且 httpx 的 `timeout=10` 是**每一階段**（connect／read／write／pool）各 10 秒而非總時長。故：

- `EPISODIC_WAIT_SEC = embedding_port.EMBEDDING_TIMEOUT_SEC + 5.0`，於 `BrainGateway` 建構時讀取該**模組常數**（不讀環境變數，
  `NFR13.44` ① 不受影響）；預設值即 15.0，與 functional-design 一致。
- 兩種逾時都會被認出：嵌入自身逾時 → `EmbeddingProviderUnavailable` 鏈上有 `httpx.TimeoutException`；本單元等待上限先到 →
  `TimeoutError`。兩者皆開熔斷。
- 預取的 3 秒（或 §四 定值）遠小於嵌入逾時，故預取路徑幾乎只會以 `TimeoutError` 開熔斷——這是熔斷曾因「只認
  `asyncio.TimeoutError`」而在寫入路徑永不開啟的原因（`nfr-requirements` `review-01` R-02）。

**測試替身拋實際例外**：替身以 `raise EmbeddingProviderUnavailable("ollama", detail="…") from httpx.ReadTimeout("…")` 構造
（真例外型別、真 `__cause__`）；另一案 `from None` 的設定錯誤不開熔斷。**替身限制（揭露）**：替身不經真 httpx 與 Ollama，
無法驗證 Ollama 冷載時實際拋出的是 `ReadTimeout` 還是 `ConnectError`——兩者皆在 §3.1 表內，故結論不受影響；真實型別在
`build-and-test` 的部署 stack 上以 log 的例外類別名複核。

## 四、非冪等寫入與「結果未知」

| 呼叫 | 傳輸層 | `SessionBackendUnavailable` 時寫入是否可能已生效 | 處置 |
|---|---|---|---|
| `append_message`（使用者，`BR64.6` 第 6 步） | `idempotent=False` | 可能 | **不重試**（重試可能重複一則使用者訊息）；依 `[GW3]` 送 `error(INTERNAL_ERROR)` 結束該輪，不交辦。歷程可能多出一則無回覆的使用者訊息——揭露、接受（下一輪分類只是多看到一句） |
| `append_message`（回覆，`BR64.10`） | 同上 | 可能 | **不重試**；記 WARNING、照常送 `done`（`BR64.10`）。可能缺一則回覆，接受 |
| `set_sharing_mode`／`set_work_target` | `idempotent=True`（`session_store.py:339`、`:404`），閘道已重試 2 次 | 可能（較早一次嘗試已生效、回應遺失） | **重讀確認**：捕捉後做一次 `to_thread load`；讀到的值等於欲寫入值 → 視為成功（扇出、繼續原流程，含 referent 路徑的交辦）；不等或重讀也失敗 → 送 `error(INTERNAL_ERROR)`、**不交辦**。重讀失敗時客戶端狀態可能與 Redis 不一致，由下一次扇出或重連快照收斂（`BR63.2`） |
| `load`／`load_work_items` | 讀取 | 無寫入 | `[GW3]` |

判準（code-generation 補測）：`set_work_target` 替身「實際寫入替身 Redis 後拋 `SessionBackendUnavailable`」：客戶端收到
`work_target` 扇出且 `dispatch` 替身恰被呼叫 1 次；替身「未寫入即拋」：收到 `error`，`dispatch` 0 次。

## 五、episodic 背景寫入的資源擁有權（`NFR13.24`；對照 `review-01` R-01、R-06）

- 背景 task `_write_episodic(principal, content, turn_id)` 只持有**值**；DB session 在 `MemoryWorker` 的工作執行緒內由
  `fn` 自開、`finally` 關閉——不借用 handler 的任何 session，也不持有 websocket。連線在 `done` 之後關閉不影響它。
- task 最外層 `try/except BaseException`：`CancelledError`（行程關閉）→ 重拋；其他 → 依 `Outcome` 記一筆 WARNING（例外類別名、
  `turnId`），不送任何訊息。`_bg_tasks` 的 done callback 取回例外，事件迴圈不留未處理例外。
- 不寫的 6 類輪次以 `TurnLedger` 的結束狀態與一個 `dispatched: bool` 旗標判定：只有 `finish() == "done"` 且 `dispatched` 且
  非伺服器發起的輪次才 `_spawn`；熔斷開啟或執行器滿 → `MemoryWorker.run` 回 `BREAKER_OPEN`／`BUSY_SKIPPED`，只計數
  （`observability-design.md` §三），不逐則 WARNING。

## 六、載入期暫存佇列的送出：取空到 ready 之間無 `await`（`NFR13.26`；帶入項 3）

```text
# handler 內，ready 與快照都已送出之後
while conn.pending:                  # ← 判斷「已空」
    msg = conn.pending.popleft()
    await conn.send_direct(msg)      # 讓出：其間新到的扇出因 phase 仍為 LOADING 而 append 到 pending 尾端
conn.phase = Phase.READY             # ← 緊接在 while 判斷為假之後，中間無任何 await
conn.revalidate_task = self._spawn(self._revalidate_loop(conn))
```

- 扇出端 `deliver(conn, msg)`：`if conn.phase is LOADING: append`（同步、無 `await`）`else: await conn.send(msg)`。
  phase 的讀取與 append 在同一個無 `await` 區段，故「判斷 loading → 附加」不會被 drain 迴圈插入。
- 由於 `while` 條件為假與 `phase = READY` 之間沒有讓出點，事件迴圈不可能在兩者之間執行任何扇出；改 ready 之後的扇出走
  直接送出，而 drain 的最後一次 `send_direct` 已回傳，故順序為「快照 → 原佇列 → 送出期間新到者 → ready 之後者」。
- 佇列上限（`NFR13.22`）：append 前 `len(conn.pending) >= 256` → 不 append，設 `conn.overflowed = True` 並同步
  `registry.unregister(conn)`；handler 在 `load`／`list_items` 回傳後與 drain 迴圈每次 `send_direct` 之後檢查旗標，為真即
  `close(1011)`。
- **判準與突變靶**：見 `NFR13.26`；突變為在 `while` 與 `phase = READY` 之間插入 `await asyncio.sleep(0)`，並在該讓出點注入
  一次 `emit_session` → 該則因 phase 仍為 LOADING 而附加到 pending，但 drain 迴圈已結束、之後再也沒有人讀 pending，
  訊息永久遺失 → 紅燈。

## 七、對象解析的正確性（`NFR13.27`、`NFR13.28`；帶入項 1、2、4、11、13）

### 7.1 名稱正規化（統一）

`norm(s) = s.strip().casefold()`；名稱 `len(norm(n)) < 2` 者不參與原句掃描（referent 比對不受此限）。`BR64.9` 與 `BR64.13`
共用同一個 `norm`。

### 7.2 `scan_targets_in_utterance(utterance, catalog) -> list[TargetRef]`（最長完整名稱）

1. `u = utterance.casefold()`（原句不 strip 內部、只 casefold）。
2. 對目錄中每個條目 `e`（專案或系統，帶 `project_id`、`system_id`、`norm_name`、目錄序 `ord`），以 `str.find` 迴圈取出 `u` 中
   **所有**出現區間 `[s, s+len)`（允許重疊）。
3. 一個出現區間 `o` **被支配**，若存在另一個條目的出現區間 `o2`，`len(o2) > len(o)` 且 `o2.s ≤ o.s` 且 `o.e ≤ o2.e`。
   **同名（`norm_name` 相等）的不同條目區間相同，互不支配**（帶入項 11）。
4. 條目 `e` 命中 ⇔ 它至少有一個**未被支配**的出現區間。
5. 所屬專案吸收：若某系統條目命中，其 `project_id` 的專案條目從命中集合移除（不論兩者是否同名；帶入項 2）。
6. 依 `(project_id, system_id)` 去重，依 `ord` 排序回傳。

複雜度上界：條目數 ≤ 50 個專案＋其系統、原句 ≤ 4000 字；`find` 迴圈為 O(條目數 × 原句長)，不需更巧的結構。

**處置**（`NFR13.27`）：結果非空 → **一律**送 `clarify{kind:"target"}`，候選即結果（含只有一個時）；結果為空 → 依當前作業對象
交辦。客戶端以 `candidateId: null` 回絕時依 `BR64.8` 該輪 `ended_silent`。高信心路徑（`BR64.9`）維持唯一相符即更新。

### 7.3 `match_referent` 與同名專案／系統（`NFR13.28`）

`BR64.9` 第 2 步的候選集合先套 7.2 第 5 步的同一個吸收規則：同一專案下若系統名相符，該專案的同名相符不另計。故「專案
『訂單』含系統『訂單』」→ 一筆（該系統）。不同專案下的同名對象仍為多筆 → `BR64.11` (a)。

### 7.4 PBT 性質五（可失敗版本，帶入項 2、11）

對任意原句 `u` 與目錄（`hypothesis` 生成，名稱字母表刻意小以製造包含關係）：
- (a) 結果中每個對象的 `norm_name` 是 `u.casefold()` 的子字串；
- (b) 目錄中長度 ≥ 2 的條目，若它有一個未被支配的出現區間、且它不是某個已命中系統的所屬專案，則它的對象在結果內；
- (c) 結果中每個對象都有一個出現區間，不被**名稱不同且較長**的任何條目的出現區間完全覆蓋。

突變靶：步驟 3–4 改回純子字串 → (c) 紅燈（「改訂單系統」使「訂單」入列）；拿掉步驟 5 → 同名專案與系統的 example 紅燈。

### 7.5 專案數超過 50（`NFR13.21`；帶入項 4、13）

`_build_catalog(principal, selected_project_id)`：`projects = list_projects(principal)`；`len(projects) ≤ 50` → 對每個專案
`list_systems`；`> 50` → 目錄只含專案名稱，`truncated = True`，**另外**若 `selected_project_id` 非 None 則仍呼叫一次
`list_systems(selected_project_id)`（使 `BR64.9` 第 1 步照常成立）。

| 路徑 | `truncated` | 狀況 | 處置 |
|---|---|---|---|
| referent 非 null（句中確實指名） | 真 | 零筆相符 | token「專案太多，請先在脈絡列選定專案」＋ `done`（取代「找不到名為…」） |
| referent 非 null | 真 | 唯一／多筆相符 | 照 `BR64.9`／`BR64.11` (a) |
| referent 為 null（未指名） | 任意 | — | 不取目錄，依當前作業對象交辦（帶入項 13） |
| 原句掃描（意圖反問選定後） | 真 | 無命中 | 依當前作業對象交辦——掃描無法判定句中是否點名了系統，不得改送「專案太多」（帶入項 13 的「只在確實指名時」） |

## 八、輪次與送出隔離（`NFR13.29`、`NFR13.30`）

- `TurnLedger` 為純狀態機（`brain_gateway_rules.py`），handler 與 sink 送出輪次訊息前一律先問 `allows(kind)`。
- 送出失敗（`WebSocketDisconnect`、`RuntimeError`、`TimeoutError` 等任何例外）在 `Connection.send` 內捕捉：同步
  `registry.unregister(conn)`、`conn.dead = True`、記 DEBUG；**不向上拋**。接收迴圈每次 `receive_text` 前檢查 `conn.dead`，
  為真即結束 handler（其 `finally` 釋放佔位，`scalability-design.md` §一）。

## 九、重啟、啟動與部署假設（`NFR13.31`–`NFR13.33`；帶入項 16）

- **行程內狀態清單**（重啟即失）：`ConnectionRegistry`、每連線的 `pending`／`TurnLedger`／`PendingClarify`、`RateLimiter` 的
  deque、`BreakerState`、`_bg_tasks`。**沒有任何一項是會話狀態**；會話狀態只在 Redis（`NFR13.31`）。
- **啟動**（`BR67.11`、`NFR13.32`）：`build_brain_gateway(app)` 由 `main.py` 既有 startup hook 在 `configure_intent_routing_env()` 之後、
  `init_db()` 之前呼叫（`main.py:55-77`）；三個 Redis 變數以 `os.environ[...]` 取值（缺值即 `KeyError`、`REDIS_USER=default` 由
  `build_redis_client` 拋 `ValueError`，皆使啟動失敗），而 client 延遲連線，Redis 暫時不可達不阻止啟動、在握手時以 1011 呈現；
  `app.state` 無閘道元件時 handler 的第一個動作（同步讀 `app.state`）即發現，`accept` → `close(1011)` 並記 ERROR——此時沒有 registry 可佔位，
  故不佔位；新增 `@app.on_event("shutdown")`：取消 `_bg_tasks` 與各連線的重驗 task、
  `MemoryWorker._executor.shutdown(wait=False, cancel_futures=True)`。
- **單一行程守門**（`NFR13.33`＋帶入項 16），測試以文字／YAML 檢查，任一不成立即紅燈：
  1. `backend/Dockerfile` 的 `CMD`（`:30`）不含 `--workers`；檔內 `ENV` 不設 `WEB_CONCURRENCY`、`UVICORN_WORKERS`。
  2. `deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml` 以 `yaml.safe_load`（`PyYAML` 已在
     `backend/requirements.txt:32`）解析：`backend` 服務無 `command`，其 `environment` 不含上述兩個名稱。
  3. `deploy/.env.example`、`backend/.env.example`、`deploy/render-env.sh` 的文字不含上述兩個名稱。
  理由：uvicorn 的 `--workers` 預設取自 `$WEB_CONCURRENCY`（本機 uvicorn 0.52.1 的 `main.py` 說明文字實讀），且其 CLI 以
  `auto_envvar_prefix="UVICORN"` 讀 `UVICORN_WORKERS`——兩者都能在不改 `CMD` 的情況下讓行程數變多。**限制**：部署主機上
  手動設定的環境變數不在 repo 內，本檢查看不到；`build-and-test` 以 `ps` 確認 backend 容器內只有一個 uvicorn worker。
  本單元**不**在啟動時讀這兩個變數做執行期守門——那會違反 `NFR13.44` ① 的環境變數集合。
