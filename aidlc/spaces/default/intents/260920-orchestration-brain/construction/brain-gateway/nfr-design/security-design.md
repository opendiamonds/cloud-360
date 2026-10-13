# 安全設計 — `U13 brain-gateway`

> 承接 `../nfr-requirements/security-requirements.md` 的 `NFR13.7`–`NFR13.16`。本站對這十條的工作是把「判準」變成「做法」：
> 每一條寫出它落在哪個函式、在哪個時點、以什麼資料結構承載，以及哪一個檢查會在被改壞時失敗。

## 一、token 的生命週期（`NFR13.7`、`NFR13.8`、`NFR13.15`）

| 時點 | 位置 | 規則 |
|---|---|---|
| 取得 | `websocket.headers.get("sec-websocket-protocol")` → `parse_subprotocol_offer` | **唯一**取得途徑；handler 不讀 `websocket.query_params`、不讀 `websocket.url`（AST 檢查：本單元模組無 `query_params` 屬性存取、無 `.url` 存取） |
| 持有 | `Connection.token: str`（實例屬性） | 不放進 `Connection` 的 `__repr__`（`@dataclass(repr=False)` 的欄位或自訂 `__repr__` 排除）；不傳給 sink 以外的物件；`dispatch(bearer_token=…)` 是唯一往外傳的出口（`U12` 需要它帶使用者 token 呼叫既有端點） |
| 回應 | `websocket.accept(subprotocol="cloud360.brain.v1")` | 回送值為模組常數 `PROTOCOL_NAME`，不以任何變數拼接；突變靶為 DEMO 寫法 `accept(subprotocol=f"bearer.{token}")`（`brain_router.py:275`） |
| 釋放 | handler 結束 | `Connection` 隨 `finally` 移出登錄後無引用 |

例外訊息不得進 log：本單元所有 `except` 只記 `type(exc).__name__`，**不**記 `str(exc)`／`repr(exc)`／`exc_info`——
`EmbeddingProviderUnavailable` 的 `detail` 含提供者端點、`HTTPException` 的 `detail` 可能含使用者輸入。

## 二、accept 之前完成認證（`NFR13.9`、`NFR13.10`）

```text
def _auth_once(token: str, *, record: bool) -> AuthResult:      # 在 to_thread 內
    db = SessionLocal()
    try:
        user = get_user_from_token(token, db, record=record)     # HTTPException → AuthResult.UNAUTHENTICATED
        if not user_can(db, user.role, "K1", "view",
                        authorization_status=user.authorization_status): return AuthResult.FORBIDDEN
        return AuthResult.ok(user.id, mint_principal(user))
    finally:
        db.close()
```

- `AuthResult` 是一個三態的值物件（`ok`／`UNAUTHENTICATED`／`FORBIDDEN`），handler 依它決定 4401／4403；**其他例外**原樣拋出，
  握手時對應 1011、訊息路徑對應 `error(INTERNAL_ERROR)` 且不關閉（`NFR13.11` ④）。
- 握手中 `accept` 之前只做：佔位、解析標頭、認證、每 key 佔位。沒有 `receive_*`、沒有 `SessionStore` 呼叫——`NFR13.9` 的
  替身斷言（`load`／`list_items`／`append_message` 皆 0 次、登錄為空）即是這個順序的機械形式。
- 停用帳號：`get_user_from_token` 對 `is_active=False` 拋 `HTTPException(403)`（`auth.py:75-77`）；`_auth_once` 把**任何** `HTTPException`（401 或 403）一律對應為 `UNAUTHENTICATED` → 4401（`BR61.4`，不以 HTTP 狀態碼區分）；`authorization_status`
  未核准者由 `user_can` 的 `K1` 判定拒絕 → 4403（依 `NFR13.10` 的四案）。四案的測試資料走 `tests/helpers.py` 的 SQLite，
  `_auth_once` 的 `SessionLocal` 由 `BrainGateway` 建構參數 `session_factory`（預設 `database.SessionLocal`）注入，使測試能把
  它換成測試 DB 的工廠——否則測試改的 `is_active` 對正式 engine 不可見（對照 `work-orchestrator` `review-01` R-05）。

## 三、重驗（`NFR13.11`）

- 每則客戶端訊息（hello 除外）：通過大小與頻率檢查後 `await to_thread(_auth_once, conn.token, record=True)`，以結果**取代**
  `conn.principal`；該輪後續全部呼叫使用新的 principal。
- 背景：ready 後 `conn.revalidate_task = _spawn(_revalidate_loop(conn))`：
  `while True: await timing.sleep(60); r = await to_thread(_auth_once, conn.token, record=False)`；`UNAUTHENTICATED` →
  `close(4401)`、`FORBIDDEN` → `close(4403)`（皆先同步 `unregister`，使關閉前不再收到扇出）；其他例外 → WARNING（類別名）、下一週期再試。
- 背景 task 在 handler `finally` 中 `cancel()`；它不持有 DB session（每次在 thread 內自開自關）。
- 撤權外洩窗：有訊息往來 ≤ 一則訊息；閒置 ≤ 60 秒（`FakeTiming.sleep` 推進驗證）。

## 四、輸入面（`NFR13.12`、`NFR13.13`）

- 信封兩步驗證沿用 `brain_ws_contract`：`WsUnvalidatedEnvelope` 之後把**原始 dict** 交給 `WsClientEnvelope.model_validate`
  （`extra="forbid"`），故 `userId`、`turnId` 等多餘欄位必然 `ValidationError` → `error(INVALID_REQUEST)`。
- `prompt_guard`：`BR64.5`，於 `load`、預取、`classify`、`append_message` 之前呼叫；命中即以 `REFUSAL_MESSAGE` 送 token ＋
  `done`，該輪 `TurnLedger` 標記 `guard`，不寫歷程、不寫 episodic。`classify` 拋 `PlatformSelfModificationRefused` 時走同一
  結束路徑（縱深第二層）。

## 五、輸出面（`NFR13.14`）

- `error_for(exc) -> (code, message)` 為純函式，message 只取自模組常數 `ERROR_MESSAGES: Mapping[str, str]`（`BR67.1` 的封閉表
  加本站新增的「訊息太頻繁，請稍候再送出」；`NFR13.20`）。未列出的例外一律 `("INTERNAL_ERROR", ERROR_MESSAGES["internal"])`。
- 關閉原因為模組常數 `CLOSE_REASONS = {4401: "credentials-expired-or-invalid", 4403: "forbidden", 1011: "internal-error"}`
  與 4400 的 `f"expected=1 received={n}"`——其中 `n` 只能是 `int` 或字面 `"invalid"`（由 `BR61.8` 的判定函式回傳），**不**
  拼接客戶端字串。測試列舉 `CLOSE_REASONS` 全部值與 4400 的兩種形狀：`isascii()` 且 `len(encode()) ≤ 123`。

## 六、邊界檢查寫成會失敗的形式（`NFR13.16`；對照 `review-01` R-04）

字串 grep 對 `from x import f` 與別名無效，對「不在本模組 import、但經他模組間接呼叫」也無效。改為三種檢查：

1. **AST 直接 import 檢查**：以 `ast.parse` 讀 `brain_gateway.py`、`brain_gateway_rules.py`，走訪全部 `Import`／`ImportFrom`
   （含函式內），模組名與禁止清單比對：`services.hierarchy_service`、`services.memory_service`、`services.membership_service`、
   `services.membership_facade`、`services.requirement_field_facade`、`services.requirement_field_service`、
   `services.progress_channel`、`services.llm_provider`、`openai`、`langchain*`、`langgraph*`、`main`。另斷言兩模組內
   `importlib`、`__import__` 的出現次數為 0（防動態 import 繞過）。
2. **AST 名稱檢查**：兩模組內不得出現 `Name`／`Attribute` 為 `request_key`、`query_params`、`execute`（直寫 SQL 的 session 方法）、
   `text`（`sqlalchemy.text`）的節點；以字面 `"type"` 為鍵的 `Dict` 節點數為 0（訊息必經契約模型，`NFR13.40`）。
3. **行為檢查**（見 `performance-design.md` §五）：一輪完整交辦期間任何出站連線使測試失敗。

**為何不做「完整 import 閉包」檢查**：本單元合法依賴 `IntentRouter`（`U11`）與 `MemoryFacade`（`U8`），它們本身會載入
`llm_provider` 與 `memory_service`；閉包檢查必然紅燈，換成「排除合法依賴」又會把檢查削成恆真。故直接 import ＋ 行為檢查。

突變靶：在 `brain_gateway.py` 的某個函式內加 `from services.memory_service import search_memories` → 檢查 1 紅燈；把一則訊息
改成手組 `{"type": "token", …}` → 檢查 2 紅燈。

## 七、靜態加密（上游 `OQ-3` 在本單元的落點）

`OQ-3`（`requirements.md:784`）指派 `nfr-design`。本單元**不新增任何持久化落點**：使用者文字只以行程記憶體暫存
（`PendingClarify.utterance`、載入期 `pending`），落地處為 `U10` 的 Redis 歷程與 `U8` 的 `memory_records`，其加密由各自
單元的 nfr-design／`infrastructure-design` 決定。本站判定：`OQ-3` 在 `U13` 的部分**結案為不適用（無新落點）**，非豁免。

## 八、ADR-0006 四面向（逐格對照上游，無一格相反）

逐格對照 `../nfr-requirements/security-requirements.md` §五（四格皆「適用」）與 `functional-spec.md` §七（四格皆「適用」）：

| 面向 | 判定 | 本站的做法落點 |
|---|---|---|
| IAM | **適用** | §二 accept 前認證與三態結果；§三逐則與 60 秒重驗；§四身分只來自連線；§六 只經 facade 的 AST 檢查 |
| Encryption | **適用** | 傳輸：token 只在子協定標頭、不回送（§一）；tunnel 內明文 ws 與既有 SSE 同形，不新增。靜態：§七（本單元無新落點） |
| Network exposure | **適用** | 本 intent 唯一新增的對外面；`scalability-design.md` 的連線佔位（§一）、訊框（§二）、頻率（§三）、送出逾時（§四）；殘留 `OPEN-GW13-6`（cloudflared／nginx 透傳子協定未實測）不變 |
| Audit logging | **適用** | 逐則 `record=True`、背景 `record=False`（§三）；`observability-design.md` 的連線生命週期與拒絕 log；log 禁令（§一） |
