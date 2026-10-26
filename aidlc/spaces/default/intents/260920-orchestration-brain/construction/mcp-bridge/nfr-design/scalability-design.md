# 擴展設計 — `U21 mcp-bridge`

> 承接 `../nfr-requirements/scalability-requirements.md` 的 `NFR21.20`–`NFR21.24`，並以設計收斂 nfr-requirements 審查的 `R-01`
> （並行上限）、`R-05`（算式）、`R-08` 第 3 點（回應過大的映射）、`R-09` 第 1 點（頻率後果揭露）。「靜態讀」的定義見
> `performance-design.md` 檔頭。

## 一、並行閘：在 bridge 自己的 ASGI 層計「進行中請求」（`NFR21.21`；帶入項 `R-01`）

### 1.1 為何不用 uvicorn 的 `limit_concurrency`

審查以本機 uvicorn 原始碼證實（`R-01`）：`limit_concurrency` 的判定式是「已開啟的**連線**數或 task 數 ≥ 上限」，閒置的 keep-alive
連線也算；超額回應在進入 app 之前產生，`/healthz` 與 `/mcp` 共用同一個額度。三個後果（判準不可構造、16 條閒置連線即可鎖死 bridge、
backend 變慢時 healthcheck 失敗使容器被標為 unhealthy）都來自「計數單位是連線」。且 `backend/requirements.txt:10` 的 `uvicorn`
未釘版本，依賴其內部判定式等於依賴一個會漂的行為。**本設計不設定 `limit_concurrency`**（保持 uvicorn 預設的不限制），
計數改由 bridge 自己做。

### 1.2 設計

`guards.ConcurrencyGate` 是一個 ASGI 中介層，狀態為**該應用實例**持有的一個整數（`create_app` 建立時產生，不是模組全域，
使 `NFR21.23` 的兩個實例互不影響）：

```text
class ConcurrencyGate:                      # guards.py；只在事件迴圈執行緒存取，無鎖、無 await 於判定與遞增之間
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/mcp":
            return await self.inner(scope, receive, send)        # /healthz 與其他路徑不計數
        if self.in_flight >= self.limit:
            log_rejected(reason="over_concurrency", http_status=503)  # observability §三
            return await send_fixed(send, 503, BUSY_BODY, retry_after="1")
        self.in_flight += 1
        try:
            await self.inner(scope, receive, send)
        finally:
            self.in_flight -= 1
```

- **計數單位**：進入 `/mcp` 的 HTTP 請求，從中介層收到請求到內層應用回傳（回應已送完）為止。閒置連線不計——連線生命週期與計數無關，
  判準不需要關閉連線即可構造（解掉 `R-01` 第 1 點）。
- **計哪些方法**：全部 `/mcp` 請求（`initialize`、`tools/list`、`tools/call`、通知），**偏離審查建議的「只計 `tools/call`」**。理由：
  (1) `NFR21.21` 已核可字面是「同時處理中的 **HTTP 請求**上限」，全部計數是逐字讀法；(2) 只計 `tools/call` 需要在 SDK 之前多一個
  JSON-RPC 解析器（含 batch 陣列的判讀），那是第二份協定解析、且是 SDK 之外的攻擊面；(3) `initialize`／`tools/list` 不呼叫 backend，
  佔用時間為毫秒級（**估計**），飽和時它們拿到 503 由 client 重試即可。**請下一輪審查針對此偏離檢查**。
- **不排隊**：判定與遞增之間沒有 `await`，單執行緒事件迴圈下不需要鎖；超額立即回 503（`NFR21.21` 字面）。
- **在本體上限之前**：閘門排在 `BodyLimit` 之外（`security-design.md` §二 的層序），慢速上傳的請求也佔用名額——它確實佔用了記憶體與連線。
- **uvicorn 的連線面**：不限制連線數；閒置連線由 uvicorn 預設 `timeout_keep_alive=5` 秒關閉（靜讀 `uvicorn/config.py:229`）。
  bridge 只在 `internal` 網段（`NFR21.16`），連線洪水的來源只可能是同網段容器，屬 `[G2]`=A 已接受的信任邊界。

### 1.3 判準（取代 `NFR21.21` 原判準的構造方式；二元條件不變）

| 案 | 構造 | 斷言 |
|---|---|---|
| ① 超額 | 以 `--max-concurrency 2`（第一順位為 `create_app(limits=BridgeLimits(max_concurrency=2))`）啟動；記錄包裝以 `asyncio.Event` 屏障扣住前兩個 `tools/call` 的 backend 請求 | 第三個並發 `/mcp` 請求收到 503、帶 `Retry-After`；記錄包裝仍只有 2 筆；`cloud360.mcp_bridge` 恰多一筆 `request_rejected reason=over_concurrency` |
| ② 放行後恢復 | 放行屏障、等前兩個完成，**同一組 client 連線不關閉** | 第四個請求成功（解掉 `R-01` 第 1 點：連線仍開著也不影響） |
| ③ 健康檢查豁免 | 預設上限 16：以屏障扣住 16 個 `tools/call` | `/healthz` 回 200；第 17 個 `/mcp` 請求回 503（`R-01` (b) 要求的新增案） |
| ④ 預設值 | 參數解析器不給 `--max-concurrency` | 值為 16 |
| ⑤ 實例獨立 | 兩個實例 X、Y 各以上限 2 建立，以屏障扣住 X 的兩個請求 | 對 Y 的請求成功（不受 X 的計數影響） |

突變：把 `ConcurrencyGate` 套在整個應用（含 `/healthz`）→ ③ 紅燈；把計數器改成模組全域 → ⑤ 紅燈。第二退路下 ⑤ 以兩個子進程構造
（`reliability-design.md` §6.2）。

### 1.4 揭露（`R-01` (c)，於核可關卡呈現）

超額回應是 **HTTP 503**，本體為固定 JSON `{"error":"busy"}`，**不是** `BR76.1` 形狀的工具結果——它發生在 MCP 協定層之外，
MCP client 看到的是 HTTP 錯誤而非 `isError` 結果。維持 503 是 `NFR21.21` 的已核可字面；改成工具結果需在 `BR76.1` 封閉表新增一列。
與 nfr-requirements 原文的差別只有兩處：產生者由 uvicorn 改為 bridge；並且**會**記一行 WARNING（原文的 uvicorn 503 不經 bridge log，`R-06` 第 2 點）。

## 二、請求本體上限（`NFR21.20`；算式更正見 §2.2）

### 2.1 設計：先緩衝、後交付

`guards.BodyLimit` 在呼叫內層之前**完整讀取**本體到記憶體，邊讀邊計：`Content-Length` > 65536 → 立即 413；無 `Content-Length` 或 chunked
→ 累計超過 65536 即停止讀取、回 413。讀完未超量者，以一個重播用的 `receive` 交給內層（SDK）。這保證超量本體**從未交給 SDK 解析**、
也不會「SDK 已讀一半才發現超量」。413 回應記一行 `request_rejected reason=body_too_large`（`observability-design.md` §三）。
突變：只檢查 `Content-Length` → chunked 案紅燈（`NFR21.20` ③）。

### 2.2 算式更正（帶入項 `R-05`；以 shell 整數運算與 `bc` 實算）

| 項 | 原文 | 更正 | 說明 |
|---|---|---|---|
| `value` 每字元最壞位元組 | 6（`\uXXXX`） | **12** | `MAX_VALUE_LENGTH = 2000` 計的是字元（`requirement_field_definitions.py:36`，facade 以 `len()` 判定），一個非基本多文種平面字元在 JSON 中可被寫成兩個代理項跳脫，共 12 位元組 |
| 合法請求最壞值 | 12000 | **24876**（＋JSON-RPC 外殼） | `2000×12＋18×6`（`system_id`）`＋2×64×6`（`agent_group`、`field`，pattern 驗證在解碼之後，故跳脫寫法也合法）＝24876；外殼以 1024 位元組**估計**（未實算）→ 約 25900 |
| 餘裕 | 「5 倍以上」 | **約 2.5 倍** | 65536／25900 ≈ 2.53（不含外殼為 2.63）。結論不變：65536 足夠，不調整上限 |

## 三、回應本體上限（`NFR21.22`；帶入項 `R-08` 第 3 點）

### 3.1 設計：串流讀取、超量即停

`executor.read_bounded(response, limit)`：先看 `Content-Length`，> 1048576 即不讀本體；否則以 `aiter_bytes()` 逐塊累加，累計超過 limit
即停止並回 `ResponseTooLarge`。整段在 `asyncio.timeout(10)` 之內（`performance-design.md` §一），故串流 2 MiB 的慢速回應也在 11 秒內結束。

### 3.2 映射（解掉 `R-08` 第 3 點「是否經 `map_outcome`、`retryable` 為何」）

執行層的結果統一為一個封閉聯集 `ExchangeResult = Received(status, body) | TransportFailure(kind) | ResponseTooLarge | InternalFailure`
（`reliability-design.md` §一），**全部**經純函式 `map_outcome` 映射，`BR76.1` 的封閉表因此只有一個實作點。
`ResponseTooLarge` → `internal_error`、`retryable: false`（`BR76.1` 的「其他」列；重試不會讓回應變小）。

### 3.3 算式（`R-05` 對回應端的質疑）

原文 `7 × 2000 × 6 = 84000` **維持**，但理由更正：審查指出 FastAPI 以 UTF-8 輸出、每字元至多 4 位元組（7×2000×4＝56000）；
然而 JSON 編碼器對**控制字元**仍輸出 `\u00XX` 六位元組跳脫，backend 是否允許 `value` 含控制字元本站未查證，故取 6 為保守上界。
1048576／84000 ≈ 12.48 倍，結論不變。

## 四、無狀態與多實例（`NFR21.23`）

| 狀態 | 位置 | 跨請求？ |
|---|---|---|
| 並行計數 | `ConcurrencyGate` 實例屬性（每個 `create_app` 一份） | 是，但只是計數、不含身分；兩個實例互不共享 |
| 使用者 token、agent 宣告 | `guards` 模組的 `ContextVar`，於每個請求設定、`finally` 重設 | 否（`NFR21.28`） |
| cookie | 共用 httpx client 的 jar，政策為**拒收一切**（`security-design.md` §一） | 否（jar 永遠為空） |
| 工具宣告、登錄表 | 啟動時載入的不可變值（`tuple`／`MappingProxyType`） | 唯讀 |

不需 session affinity；`Mcp-Session-Id` 在無狀態模式下不產生（靜讀 `mcp/server/streamable_http_manager.py:58` 的 `stateless` 說明），
`NFR21.23` 的「下一次請求不帶它也成功」為判準。

## 五、數值的單一來源（`NFR21.24`）

`limits.py` 定義五個具名常數（`CONNECT_TIMEOUT_S = 3.0`、`OVERALL_TIMEOUT_S = 10.0`、`MAX_REQUEST_BODY_BYTES = 65536`、
`DEFAULT_MAX_CONCURRENCY = 16`、`MAX_RESPONSE_BODY_BYTES = 1048576`）與不可變資料類別 `BridgeLimits`（預設值取自上列常數）。
`cli.parse_args` 的 `--max-concurrency` 預設值引用 `DEFAULT_MAX_CONCURRENCY`；其他模組只經 `BridgeLimits` 取值。判準：五個常數名
各自 grep，定義列恰 1。

## 六、最壞記憶體上界（交接 `infrastructure-design` 定記憶體上限，`NFR21.32`；該站為 CONDITIONAL，若被 skip 轉 `code-generation`）

緩衝上界＝並行上限 ×（請求緩衝＋回應緩衝）＝ 16 ×（65536＋1048576）＝ **17825792 位元組（17 MiB）**（shell 實算）。
另加 Python 直譯器、`mcp` SDK、`httpx` 的常駐量（**未量測**）。`infrastructure-design` 設 compose 記憶體上限時，此 17 MiB 是本單元
可由設計保證的**請求相關**上界，常駐量須於部署後以 `docker stats` 量測並回寫 `DEPLOY.md`（「未量測」標記，`functional-spec.md` H-1）。

## 七、請求頻率：後果揭露（帶入項 `R-09` 第 1 點，於核可關卡呈現）

`OPEN-MB21-10` 的頻率部分維持 nfr-requirements 的關閉理由（bridge 不知使用者是誰；以 agent 為單位可被自報繞過）。**補上使用者會遇到的後果**：
持有有效 token 的呼叫端，在並行 16 之內可以**不限速率**地反覆呼叫 `write_requirement_field`——每一次都是一次 DB 寫入與 `updated_at`
變動；並行閘只限制「同時幾個」，不限制「每秒幾個」，本設計修正 `R-01` 之後仍是如此。本版沒有任何實際 client（`OPEN-MB21-1`），
正式環境的此類流量目前為 0；大腦 client 落地時（後續 intent）再評估以 token 雜湊為單位的頻率限制。
