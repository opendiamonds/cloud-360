# 觀測設計 — `U21 mcp-bridge`

> 承接 `../nfr-requirements/observability-requirements.md` 的 `NFR21.33`–`NFR21.36`，並以設計收斂 nfr-requirements 審查的 `R-06`
> （tool 欄未正規化；413／503 在 log 中零紀錄）與 functional-design 的 `OPEN-MB21-9`（指派本站的關聯鍵）。「靜態讀」的定義見
> `performance-design.md` 檔頭。

## 一、logger 與單行格式（`NFR21.33`）

`observability.configure_logging()`（不 import `mcp`，`reliability-design.md` §6.1）是 bridge 進程唯一的 logging 設定點，正式啟動
（`cli.main`）與測試呼叫同一支：

| 對象 | 層級 | 理由 |
|---|---|---|
| 根 logger | WARNING；掛一個寫 stderr 的 handler，formatter 為 `BridgeFormatter` | 第三方套件只有 WARNING 以上會出現 |
| `cloud360.mcp_bridge` | INFO | 本單元**唯一**的 logger 名稱（`team.md ## Code Style`；`getLogger` 引數 grep 只有此名） |
| `httpx`、`mcp` | WARNING | `NFR21.33` 原文；httpx 在 INFO 會記含 `system_id` 的請求 URL |
| `mcp.server.lowlevel.server` | **ERROR** | 靜讀 `mcp 1.29.0` 的 `server.py:494`：對未列出的工具名以 WARNING 記下呼叫端傳來的**原值**（可含換行，`R-06` 的注入面）。ERROR 仍滿足 `NFR21.33` 的「WARNING 以上」 |
| uvicorn | `log_config=None` 啟動，使 uvicorn 不覆寫上述設定；`access_log=False`（§五） | |

**`BridgeFormatter` 的單行保證**：格式化完成的整行文字中，`\r`、`\n` 一律替換為字面 `\\r`、`\\n`——不論來源是本單元或第三方 logger，
每一筆紀錄恰為一行。這是結構性防線；§二 的欄位正規化是第二層（使本單元自己的欄位根本不含呼叫端字串）。第二退路下測試讀子進程 stderr
時，「一筆紀錄＝一行」使計數斷言與第一順位相同（`reliability-design.md` §6.2）。

本單元自己的紀錄格式為 `<事件名> key=value …`，鍵依固定順序輸出，值只來自封閉集合或整數：

| 事件 | 層級 | 欄位（固定順序） |
|---|---|---|
| `tool_call` | INFO | `tool`、`agent`、`outcome`、`http_status`（整數或 `null`）、`duration_ms`（非負整數） |
| `request_rejected` | WARNING | `reason`（`over_concurrency`／`body_too_large`）、`http_status`（503／413） |
| `startup` | INFO | `port`（實際綁定的埠）、`tools`（載入的工具數） |
| `startup_failed` | ERROR | `subject`（違規的工具名或 agent 名，以 `json.dumps(…, ensure_ascii=True)` 輸出，保證單行且非 ASCII 可讀） |

同一組欄位另以 `extra` 附在 `LogRecord` 上，第一順位的測試可直接斷言鍵集合（`NFR21.34` 判準原文）；第二退路以解析文字行斷言同一集合。

## 二、每次 `tools/call` 恰一行（`NFR21.34`；帶入項 `R-06` 第 1 點、functional-design `R-19`）

- **產生點**：`dispatch.run_tool_call`（不 import `mcp`）在自己的 `finally` 中寫出恰一行 `tool_call`；`app.py` 只把它回傳的
  `ToolOutcome` 轉成 `CallToolResult`、自己不記 log。所有分支——本地拒絕、backend 各狀態、`ResponseTooLarge`、未預期例外——都經同一個
  `finally`，故「恰一行」由結構保證，且可在主直譯器以替身驗證（`NFR21.29` 單元層，`reliability-design.md` §3.3）。
- **`agent` 正規化**：已登錄名、`undeclared`、`unregistered`（`BR77.1` 原文）。
- **`tool` 正規化（`R-06` 第 1 點）**：只取 `tool_specs` 中已宣告的名稱；其餘一律記為 `unknown`。呼叫端可控的工具名**從不**原值進入本單元的 log。
- **未知工具的 `outcome`**：記為 `invalid_argument`。依據：MCP 規格對未知工具的協定錯誤碼是 JSON-RPC `-32602`（Invalid params），
  與 `invalid_argument` 同義；這使 `outcome` 仍落在 `BR77.1`「`ok` 或 `BR76.1` 的錯誤碼」的已核可集合內，不新增值。對 agent 的回應
  依 `BR76.3` 應為協定錯誤、訊息為固定字串、不回顯工具名。**但**靜讀 `mcp 1.29.0` 的 `server.py:589-590`，低階 server 的工具函式
  拋出的任何例外都被轉成 `isError` 結果（`UrlElicitationRequiredError` 除外），工具函式**無法**產生協定錯誤——SDK 自己會不會先擋未知工具，取決於版本。
  所釘版本若同樣如此，未知工具改以 `BR76.1` 形狀的 `invalid_argument` 結果回傳（固定訊息、不回顯）；這是版本所迫、與 `BR76.3` 字面的
  落差，列 `OPEN-MB21-17` 由 code-generation 實測後寫進 code-summary（`logical-components.md` §七）。
- **SDK 預先驗證（functional-design `R-19`）**：靜讀 `mcp 1.29.0` 的 `server.py:498-537`：`call_tool(validate_input=True)` 為預設，
  會以 `jsonschema` 先驗證參數，失敗時回傳 `"Input validation error: {e.message}"`——`jsonschema` 的訊息**會引用不合格的值**，直接違反
  `NFR21.8` 的不回顯，且不經本單元的封閉表與 log。設計：**以 `validate_input=False` 註冊**，參數驗證一律由 `calls.validate_arguments`
  執行（`BR75.4`）；`tools/list` 仍公開完整的 `inputSchema`（`NFR21.4`）。所釘版本若無此開關，`NFR21.8` 的兩案（多餘參數、`pattern`
  不符）會紅燈，code-generation 須另找關閉方式後才能完成。
- 判準：`NFR21.34` 原文，另加兩案——`tools/call` 的工具名為 `"evil\nINJECTED"`：恰一行 `tool=unknown outcome=invalid_argument`，
  全部 log 文字不含 `INJECTED`；`X-Cloud360-Agent: "evil\nINJECTED"` 一案照原文。突變：`tool` 欄改寫原值 → 前一案紅燈；
  拿掉 `mcp.server.lowlevel.server` 的 ERROR 層級 → 前一案紅燈（SDK 的 WARNING 帶出 `INJECTED`，雖已被跳脫成單行，仍含該子字串）。

## 三、HTTP 層的拒絕也要留紀錄（帶入項 `R-06` 第 2 點）

413（`NFR21.20`）與 503（`NFR21.21`）都發生在 MCP 協定層之外、不屬於任何 `tools/call`，原需求下 bridge log 對它們零紀錄。設計：
`guards.BodyLimit` 與 `guards.ConcurrencyGate` 各在拒絕時記**恰一行** `request_rejected` WARNING，欄位只有 `reason` 與 `http_status`——
**不含**請求本體、標頭、來源位址、`Content-Length` 數值。判準：`NFR21.20` ②③ 與 `NFR21.21` ① 各斷言恰一筆 `request_rejected`，且全文
不含送出的標記字串。

濫用時的 log 量：每次拒絕一行；容器 log 由 `json_file_bounded` 限制總量（`NFR21.32`），不另設節流。

## 四、啟動紀錄（`NFR21.35`）

- 成功：uvicorn 綁定 socket 之後記一行 `startup port=<實際埠> tools=3`。記「實際埠」使第二退路的測試以 `--port` 指定埠時可交叉核對。
- 失敗：`cli.main` 捕捉 `StartupConfigError` 記一行 `startup_failed subject=<json 字串>`，回傳 1（`reliability-design.md` §五）。
  四份手改產物各恰一筆 ERROR，`subject` 的值以白名單比對（工具名或 agent 名）。

## 五、存取 log 關閉（`NFR21.36`）

`uvicorn.Config(..., access_log=False, log_config=None)`。判準照原文（5 次 `/healthz`，`uvicorn.access` 0 筆；第二退路為 stderr 中 0 行
存取紀錄）。

## 六、關聯鍵：本版不設（結案 `OPEN-MB21-9`）

`OPEN-MB21-9`（bridge log 與 backend log 只能依時間對照）由 functional-design 指派本站。**判定：本版不設關聯鍵，以時間對照**。理由：

1. 關聯鍵要有用，兩端都要記錄它：bridge 要在 `BR77.1` 的欄位白名單加一欄、在 `BR73.2` 的轉送標頭集合（只轉 `Authorization`、
   `Content-Type`、`Accept`）加一個請求 id 標頭，backend 也要記錄它——三處都改寫已核可字面，且 backend 的部分在本單元之外。
2. 只做 bridge 半邊（例如自己產生 id 寫進自己的 log）對「對照 backend」毫無幫助，還會改寫 `BR77.1`。
3. 本版沒有任何實際 client（`OPEN-MB21-1`），正式環境經 bridge 的流量為 0；日後要加是純增量（新欄位、新標頭），不重工既有程式。

**使用者會遇到的後果（於核可關卡揭露）**：追查某次經 MCP 的呼叫在 backend 端對應哪一筆時，只能依 `duration_ms` 與時間戳對照；
同一秒內有多次呼叫時無法一對一配對。承接：大腦 client 落地的後續 intent（與 `OPEN-MB21-1` 同批評估）。

## 七、刻意不設

| 不設 | 理由 |
|---|---|
| metrics、告警、儀表板 | repo 無 metrics 管線（`project.md ## Deployment`）；本版無實際 client，SLI 無量測母體。異常以 compose 健康狀態呈現（`NFR21.32`） |
| SLI／SLO | 同上；`reliability-requirements.md` 第五節的理由沿用 |
| 分散式追蹤 | 一跳（bridge → backend）且無上游 client |
| `/healthz`、`tools/list` 的逐次紀錄 | 免認證、無副作用；記錄只會被 healthcheck 洗版 |

`build-and-test` 的統計原料：`tool_call` 行的 `outcome` 計數與 `duration_ms` 分佈（`performance-design.md` §三 的附加時間另以成對呼叫量測），
`request_rejected` 行的 `reason` 計數。
