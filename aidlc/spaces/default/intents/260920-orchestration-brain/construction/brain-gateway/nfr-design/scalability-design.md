# 擴展設計 — `U13 brain-gateway`

> 承接 `../nfr-requirements/scalability-requirements.md` 的 `NFR13.17`–`NFR13.22`，並把帶入清單第 7、17 項定成設計（第 17 項的
> 「關閉最舊連線」與已核可的 `[GWN1]`=A 衝突，**出題待使用者裁決**，見 `nfr-design-questions.md` 的 `[GWND1]`；本檔先依
> `[GWN1]`=A 的字面設計，並寫明各選項對本檔的差異）。全部數值為模組常數（`NFR13.44`）。

## 一、連線佔位：握手一開始即計數（`NFR13.17`、`NFR13.18`；帶入項 7）

### 1.1 資料結構（`ConnectionRegistry`，只在事件迴圈執行緒存取，無鎖）

```text
class ConnectionRegistry:
    MAX_TOTAL   = 200
    MAX_PER_KEY = 10
    _total_slots: int                          # 握手中 ＋ 已登錄（loading／ready）的連線數
    _key_slots:   dict[str, int]               # 每個 session key：已通過認證、尚未釋放的連線數
    _by_key:      dict[str, list[Connection]]  # 已登錄連線，依登錄先後（扇出與 [GWND1] 用）

    def try_reserve_total(self) -> bool        # 同步：_total_slots < 200 → +1、True；否則 False
    def release_total(self) -> None            # 同步：-1
    def try_reserve_key(self, key) -> bool     # 同步：_key_slots.get(key,0) < 10 → +1、True
    def release_key(self, key) -> None         # 同步：-1；為 0 即 del（同時刪該 key 的頻率窗，§三）
    def register(self, conn) / unregister(self, conn)   # 同步；unregister 冪等（以 conn.registered 旗標）
```

**原子性的依據**：上列方法都是不含 `await` 的同步函式，在單執行緒事件迴圈上呼叫時不可能被其他協程插入，故「讀計數 →
比較 → 加一」為原子。這同時是單一行程假設（`reliability-design.md` §九）的一部分。

### 1.2 handler 中的佔位與釋放時機

```text
async def brain_ws(websocket):
    gw = getattr(websocket.app.state, "brain_gateway", None)   # 同步；None → accept → close(1011)、記 ERROR、return（無 registry 可佔）
    registry = gw.registry
    if not registry.try_reserve_total():            # ← 第一個可能拒絕的敘述，之前無任何 await
        log refuse(reason="global_limit"); await websocket.close(); return   # 未 accept（HTTP 403）
    key_reserved: str | None = None
    try:
        offer = parse_subprotocol_offer(header)     # 純函式
        …無協定名 → close()（未 accept）; return
        auth = await to_thread(_auth_once, …)        # 期間本連線已佔全域位
        …認證失敗 → accept → 4401 ／ K1 假 → accept → 4403; return
        key = session_key_for(auth.user_id)
        if not registry.try_reserve_key(key):        # ← 認證之後、accept 之前，同步
            log refuse(reason="per_key_limit"); await websocket.close(); return
        key_reserved = key
        await websocket.accept(subprotocol="cloud360.brain.v1")
        …hello → register(conn, phase=LOADING) → load → ready → drain → 接收迴圈
    finally:                                         # 任何結束路徑（含例外、取消、客戶端斷線）
        registry.unregister(conn)  若已登錄
        if key_reserved: registry.release_key(key_reserved)
        registry.release_total()
```

- 全域佔位涵蓋「正在認證」的握手：一波同時湧入的握手在各自 `await to_thread` 之前就已計數，第 201 個在付出任何 DB 成本之前
  被拒（`NFR13.17`）。
- 每 key 佔位在認證之後才可能（key 由 user id 推導），但在 `accept` 之前；同一使用者 11 條同時握手，各自在認證回傳後依序
  執行同步的 `try_reserve_key`，恰 10 條成功。
- 釋放只在 `finally`，故握手失敗、hello 逾時、載入 1011、送出失敗後 handler 結束、行程關閉取消，皆釋放。

### 1.3 測試：併發而非循序（帶入項 7）

- **全域**：以 `MAX_TOTAL` 注入為 3 的 registry（建構子參數，預設 200），認證替身在 `threading.Event` 上阻塞；以 4 條執行緒
  同時 `TestClient.websocket_connect`，待 3 條進入認證替身後檢查：第 4 條未 accept、認證替身被呼叫恰 3 次；釋放 Event 後 3 條
  皆收到 `ready`；關閉全部後 `_total_slots == 0`。
- **每 key**：`MAX_PER_KEY` 注入為 2，同一使用者 3 條同時握手、認證替身同步放行：恰 2 條 `ready`、1 條未 accept；關閉一條後
  重試成功。
- **洩漏**：各失敗路徑（4401、4403、4400、hello 逾時、載入 1011、送出失敗）各一案後，`_total_slots` 與 `_key_slots` 歸零。
- 突變靶：把 `try_reserve_total` 移到 `accept` 之後 → 全域併發案紅燈（認證替身被呼叫 4 次）。

### 1.4 已斷線未清的登錄（帶入項 17 的前半）

本設計下「已斷線但仍在登錄」只有一種成因：TCP 半開（客戶端消失、伺服器未收到關閉）。uvicorn 的 WebSocket keepalive 會在
`ws_ping_interval`＋`ws_ping_timeout` 內偵測並使 `receive_text` 拋出，handler 的 `finally` 即釋放佔位。本機 uvicorn 0.52.1 的
預設值實讀為 20.0 與 20.0 秒，故上界約 40 秒（`python3 -c "print(20+20)"`）；`backend/Dockerfile:30` 的 `CMD` 未覆寫這兩個值。
送出失敗的連線另以 `conn.dead` 立即移出登錄（`reliability-design.md` §八）。後端無法更早偵測：starlette 的 WebSocket 介面不提供
ping 結果，故不另做「清理過期登錄」的掃描（掃描也分不出殘留與活著的連線）。

**殘留窗口的後果（`nfr-requirements` `review-01` R-11 原文指出）**：開著 N 個分頁的使用者遇到一次網路抖動，N 條舊登錄在約 40 秒內
仍佔位、N 個分頁同時重連，被擋的分頁數為 `max(0, 2N−10)`（N＝6 → 2、N＝8 → 6、N＝10 → 10；`python3` 實算）。依 `[GWND1]` 的
建議案 A，這由 `U14` 的重試義務承接：退避重試至少持續 60 秒才放棄（大於約 40 秒的窗口），舊登錄釋放後自動連上。

### 1.5 `[GWND1]` 各選項對本節的差異

| 選項 | 本節變更 |
|---|---|
| A（依 `[GWN1]`=A） | 本節無變更；`U14` 增加「退避重試至少持續 60 秒」的配合事項（§1.4） |
| B（關閉最舊的一條） | `try_reserve_key` 失敗時改為：取 `_by_key[key][0]`（最舊），`await` 以既有關閉碼關閉之、等其 handler `finally` 釋放後再佔位；需新增「等待釋放」的 `asyncio.Event`，佔位不再是單一同步步驟 |
| C（B ＋ 新關閉碼） | 同 B，關閉碼改用新增的「被取代」碼；契約增量進 `ADR-0020`，`U14` 收到該碼不重連 |
| D（上限提高為 20） | `MAX_PER_KEY = 20`；其餘不變 |

## 二、訊框大小（`NFR13.19`）

接收一律 `raw = await websocket.receive_text()`（本端點只收文字訊框；收到二進位訊框時 starlette 拋例外 → 依 `BR67.1`
`INVALID_REQUEST`）。下一行即 `if len(raw.encode("utf-8")) > MAX_FRAME_BYTES (65536)`：不呼叫 `json.loads`、不重驗，以新 turnId
送 `error(INVALID_REQUEST, "訊息太長，請縮短後再送出")`，記 INFO 計數。uvicorn 全域 `ws_max_size` 不改（理由見需求檔）。

## 三、訊息頻率：行程內滑動窗（`NFR13.20`）

```text
class RateLimiter:                      # 迴圈執行緒獨佔，無鎖
    _per_key:  dict[str, deque[float]]  # user_message 的時間戳，上限 20
    _per_conn: dict[str, deque[float]]  # 全部訊框的時間戳，上限 120（以 connId 為鍵）
    def admit(self, key, conn_id, is_user_message, now) -> bool:
        d = _per_conn[conn_id]; while d and d[0] <= now - 60: d.popleft()
        if len(d) >= 120: return False
        if is_user_message:
            k = _per_key[key]; while k and k[0] <= now - 60: k.popleft()
            if len(k) >= 20: return False
            k.append(now)
        d.append(now); return True
```

- `now = timing.monotonic()`；`is_user_message` 由 `WsUnvalidatedEnvelope` 之前的最小判讀取得：`json.loads` 之後讀
  `type == "user_message"`（`json.loads` 在大小檢查之後才發生，故洪水的解析成本受 65536 位元組約束）。
- 檢查位置：大小之後、重驗之前（`performance-design.md` §五的順序）。被拒的訊框**不**計入窗（只有放行的才 `append`），否則
  持續超頻的客戶端會永遠鎖死自己。
- 清除端：連線結束時 `del _per_conn[conn_id]`；`release_key` 使該 key 計數歸 0 時 `del _per_key[key]`（`tech-stack-decisions.md`
  的契約端點三問）。
- `RateLimiter.admit` 為純資料結構操作（`now` 由參數傳入），以 `hypothesis` 驗：任一長度 60 秒的窗內放行的 `user_message`
  ≤ 20、全部訊框 ≤ 120。
- **與逐則處理（`BR64.4`）的交互（揭露）**：前一則處理完才讀下一則，故時間戳是「讀取時刻」而非「到達時刻」；排隊在 TCP／
  uvicorn 緩衝中的訊框在讀出時才計入。效果是限流量測的是本行程實際處理的速率，正是要保護的對象。

## 四、送出路徑（`BR63.4`、`NFR13.30`）

```text
class Connection:
    send_lock: asyncio.Lock
    async def send_direct(self, model) -> bool:       # 握手、快照、drain 用
        text = model.model_dump_json(by_alias=True)   # 經契約模型（NFR13.40）
        async with self.send_lock:
            try:   await timing.wait_for(self.ws.send_text(text), SEND_TIMEOUT_SEC); return True
            except BaseException as exc:
                if isinstance(exc, asyncio.CancelledError): raise
                registry.unregister(self); self.dead = True; log DEBUG(type(exc).__name__); return False
```

- `SEND_TIMEOUT_SEC = 10.0`：一個 TCP 送出緩衝塞滿的客戶端最多卡住**自己那一條**的送出 10 秒，之後被移出登錄；扇出迴圈對
  每條連線依序 `await`，故其他連線至多延遲 10 秒一次（而非無限期）。扇出採依序而非 `gather`，以保證同一連線上兩次扇出的
  先後與產生順序一致。
- 扇出 `emit_session` 先對 `_by_key[key]` 取**快照清單**再迭代（迭代中 `unregister` 不影響迭代）。

## 五、工作量上界（`NFR13.21`、`NFR13.22`）

- 對象目錄：見 `reliability-design.md` §7.5；每輪至多 1＋50 次 facade 查詢（超過 50 個專案且已選專案時為 1＋1），同一 DB
  session，不快取。
- 載入期暫存佇列：`collections.deque`（不設 `maxlen`，因為需要偵測溢位而非靜默丟最舊），上限 256 由 append 前的長度檢查
  實施，溢位處置見 `reliability-design.md` §六。

## 六、容量的算式（實算）

- 背景重驗負載：200 條就緒連線 ÷ 60 秒 ≈ 3.33 次 DB session／秒（`python3 -c "print(200/60)"`）。SQLAlchemy engine 以預設池
  建立（`backend/database.py:37` 的 `create_engine(db_url)` 未傳 `pool_size`，SQLAlchemy 預設 5＋overflow 10）；每次重驗為
  單一短交易，不構成瓶頸。
- 最壞記憶體：200 條 × 256 則暫存，每則上限為一則 `work_items`（大小由 `U12` 的工作項數決定，無上游上限）——此項未量化，
  列為 `logical-components.md` §四的開放項 `OPEN-GW13-19`。
