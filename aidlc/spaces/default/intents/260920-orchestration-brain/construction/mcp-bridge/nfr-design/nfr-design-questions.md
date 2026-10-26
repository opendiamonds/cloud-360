# NFR Design 問題檔 — `U21 mcp-bridge`

> 撰寫時間 2026-10-14T23:11:16Z（`date -u` 取值）。**本站出題數為 0。**
>
> 本站的兩項主要工作是把 nfr-requirements 審查的 `R-01`（並行上限誤用 uvicorn `limit_concurrency`）與 `R-02`（獨立 virtualenv 退路下
> 測試不可執行）以**設計**收斂，其餘帶入項（`../carried-review-items.md` 的 functional-design `R-11`–`R-21` 與 nfr-requirements `R-01`–`R-10`）
> 有設計落點者一併收斂。逐項查過之後，每一個設計選擇都落在下列三種之一：(1) 使用者已核可的帶入項「Required action」本身就指定了方向；
> (2) 已核可的規則或需求字面只容許一種做法；(3) 是可隨時改的常數或模組內部結構，預設錯了是一行或一個函式的修改，**不構成重工、也不改寫
> 任何已核可字面**。依派工，只有「預設錯了會造成真實重工或改寫已核可字面」者才出題，故 0 題。先例：`U12`、`U15`、`U20` 同站皆 0 題；
> `U13` 同站 1 題，是因為帶入項的轉述與已核可的 `[GWN1]`=A 字面直接衝突——本站逐項查過，**沒有任何帶入項與已核可作答衝突**（見下表）。

## 〇、不重問的事（已定案，附出處）

| 事項 | 定案處 |
|---|---|
| 並行上限的計數單位與實作層：「進行中請求」、在 bridge 自己的 ASGI 層計數、`/healthz` 豁免 | nfr-requirements `R-01` 的 Required action (a)；使用者 2026-10-14T23:02:07Z 裁決「核可，帶進寫程式」（`../carried-review-items.md:26`） |
| 第二退路下的可構造拓樸（backend 在主直譯器以真實 TCP 起、bridge 在 venv 子進程、測試 client 改用手寫的最小 JSON-RPC client） | nfr-requirements `R-02` 的 Required action 第一個選項；functional-design `R-11` 的 Required action (1)–(4)（含「把 `BR78.1` 的最小 client 與 `BR78.2` 的拓樸一併改寫」）；兩者皆經使用者裁決帶入 |
| `OPEN-MB21-13`（明文 JWT 於 `internal` 網段） | 使用者 2026-10-14T23:02:07Z 經選單確認**接受**，沿用 `[G2]`=A（`../carried-review-items.md:25`）；本站不重開 |
| `OPEN-MB21-14`（成功讀取不新增帶身分的紀錄） | `[MBN1]`=A（`../nfr-requirements/nfr-requirements-questions.md` 的 `[MBN1]` 作答列） |
| 逾時 3／10 秒、不重試、無狀態、零環境變數、log 欄位白名單 | `BR71.1`、`BR71.2`、`BR75.1`、`BR77.1`；`NFR21.1`、`NFR21.17`、`NFR21.27` |
| 依賴退路順序（第一順位 → 較舊版本 → 獨立 virtualenv → 升 FastAPI 須另開題） | `functional-spec.md` §十二 第 1 步；本站不改順序，只讓第二退路可測 |

## 一、刻意不出成題目的設計選擇（附「為何預設錯了不構成重工、不改寫已核可字面」）

| # | 設計選擇（本站預設） | 不出題的理由 |
|---|---|---|
| 1 | 超過並行上限時維持回 **HTTP 503**（不改成 `BR76.1` 形狀的工具結果），由 bridge 的 ASGI 層產生並記一行 WARNING | `NFR21.21` 已核可字面就是「回 HTTP 503，不排隊」；改成工具結果需在 `BR76.1` 封閉表新增一列（改寫已核可規則），反而要出題。本站只把「由 uvicorn」換成「由 bridge 的 ASGI 層」，這是 `R-01` 已核可的修正方向。`R-01` (c) 要求揭露「503 不是 `BR76.1` 形狀」，於 `scalability-design.md` §1.4 揭露 |
| 2 | 並行閘計數**全部** `/mcp` HTTP 請求（含 `initialize`、`tools/list`），不只 `tools/call` | `NFR21.21` 已核可字面是「同時處理中的 **HTTP 請求**上限」——全部 `/mcp` 請求才是逐字讀法；審查建議的「只計 `tools/call`」需要在 SDK 之前多一個 JSON-RPC 解析器（含 batch 形狀），本站**偏離審查建議**並在 `scalability-design.md` §1.2 寫明理由。改為只計 `tools/call` 是閘門判定函式的一處修改，不是重工 |
| 3 | 第二退路下的測試 client 用手寫的最小 JSON-RPC client，另加一案在 venv 內以官方 SDK client 做互通煙霧測試 | functional-design `R-11` (4) 已核可「把 `BR78.1` 的最小 client 與 `BR78.2` 的拓樸一併改寫」；第一順位下 `BR78.1` 原樣適用，字面不變 |
| 4 | `R-12` 擇 (a)：啟動也載入 `allowlist.json` 作為白名單相等檢查的獨立參考集合 | 已核可的 `functional-spec.md` 2.5 簽名就是 `validate_tool_specs(specs, allowlist)`；(a) 是唯一與該簽名一致的選項，(b) 反而要改簽名。`NFR21.6` 已把擇定權交給實作並要求寫進 code-summary |
| 5 | `R-14` 擇 (a)：產生器 PBT 每個類別各自一個 `@given` | `NFR21.39` 列出的三個可接受形式之一；結構保證決定性，改選 (b)／(c) 是測試檔的局部修改 |
| 6 | `R-20` 第 2 點擇 (b)：httpx client 使用「拒收一切 cookie」政策的 cookie jar | `NFR21.14` 已把擇定權交給實作；兩案的判準相同；(a)（見 `Set-Cookie` 即失敗）會讓 backend 日後任何一個 cookie 使全部工具呼叫失敗，本站以此理由擇 (b) |
| 7 | `OPEN-MB21-9`（bridge 與 backend log 的關聯鍵）：本版**不設**，依時間對照 | 加關聯鍵要在 `BR77.1` 的欄位白名單加欄、在 `BR73.2` 的轉送標頭集合加一個標頭、並改 backend 的 log——三者都改寫已核可字面；**不加**則字面全部不變，日後要加是純增量（新欄位、新標頭），不重工既有程式。理由與後果寫在 `observability-design.md` §六，於核可關卡揭露 |
| 8 | compose `stop_grace_period: 15s`（大於單次呼叫上限 10 秒加判定餘裕） | `R-09` (2) 的 Required action 二擇一之一；是 compose 的一個鍵，屬 `infrastructure-design` 交接，改值是一行 diff |
| 9 | `mcp.server.lowlevel.server` logger 設為 ERROR、formatter 一律把 CR／LF 跳脫成單行 | `NFR21.33` 的字面是「`httpx` 與 `mcp` 的 logger 設為 WARNING **以上**」，ERROR 滿足；理由是該 SDK 版本會以 WARNING 原樣記下呼叫端傳來的未知工具名（`observability-design.md` §二） |
| 10 | 調整 `functional-spec.md` 2.5 的模組配置（`configure_logging` 移出 `app.py`，另立不 import `mcp` 的 `guards`／`dispatch`／`startup`／`cli` 模組） | 規則（`BR78.3` 的「唯一組裝點」、`NFR21.40` 的純函式禁令）全部保留；模組配置是 functional-design 的表格而非規則，移動的目的正是讓第二退路可測（`R-02`）。取代關係逐條列於 `logical-components.md` §六 |

## 二、問題

（無。理由見檔頭與第一節。）
