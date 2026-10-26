# 擴展需求 — `U21 mcp-bridge`

> `NFR21` 的 parent id 理由與判準前提見 `performance-requirements.md` 檔頭。

## 〇、本單元的擴展面

`OPEN-MB21-10`（「bridge 無請求頻率、並發與本體大小上限」，`functional-spec.md:282`）指派本站。本版**沒有任何實際 client**
（`OPEN-MB21-1`），量不到真實負載，所以本站的數字一律是**保護性上限**——它們回答的不是「bridge 要服務多少量」，而是「一個失控的
呼叫端最多能對 backend 與本機記憶體造成多少壓力」。數字皆為模組常數或命令列參數的預設值（`BR71.1` 規定設定全走命令列），
改值是一行 diff，不觸發任何部署同步義務（`NFR21.24`）。逐條查過 `requirements.md` 的 `NFR1`–`NFR11` 與 `X-04`，無任何已核可文字
對 bridge 的上限有字面要求，故定值不牴觸上游；問題檔第一節第 1 項已寫明不出題的理由。

## 一、請求本體大小（`OPEN-MB21-10` 第三項）

**算式**：最大的合法請求是 `write_requirement_field`。`value` 上限 2000 字元（`requirement_field_definitions.py:36`
`MAX_VALUE_LENGTH = 2000`，由 backend 驗證）；最壞情況每字元以 JSON 的 `\uXXXX` 跳脫為 6 位元組，2000 × 6 = 12000 位元組；
`system_id` ≤ 18、`agent_group`／`field` ≤ 64，加上 JSON-RPC 外殼，合計遠低於 16384。取 **65536 位元組**，為最壞合法請求的 5 倍以上。

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.20`** | `/mcp` 的 HTTP 請求本體 **> 65536 位元組**即在 bridge 的 ASGI 層以 HTTP 413 拒絕，**不交給 SDK 解析**、不呼叫 backend；以 `Content-Length` 判定，無 `Content-Length` 或 chunked 時以累計讀取量判定 | 驗證拓樸三案：① 本體 65536 位元組的合法請求（`value` 以填充字串湊到上限之內的 JSON）→ 不因大小被拒（結果由後續規則決定）；② 65537 位元組、帶 `Content-Length` → 413，記錄包裝 0 筆；③ 同 ② 但以 chunked 送出、不帶 `Content-Length` → 413，0 筆。突變驗證：只檢查 `Content-Length` → ③ 紅燈 |

## 二、同時處理量（`OPEN-MB21-10` 第二項）

**算式與理由**：需求欄位的三條路由皆為同步 `def`（`requirement_field_router.py:146`、`:166`、`:196`），FastAPI 以執行緒池執行，
anyio 的預設上限為 40 條（**套件預設值，本站未實測**）。這 40 條由 backend 全部同步端點共用（含使用者正常開頁面）。bridge 的同時
處理上限取 **16**：即使 bridge 全滿，backend 仍至少有 24 條（60%）留給其他流量。

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.21`** | bridge 同時處理中的 HTTP 請求上限預設 **16**，以命令列參數 `--max-concurrency` 可調（預設值即 16；compose 的 `command` 不需列出）；超過者由 uvicorn 回 HTTP 503，不排隊 | **真實 TCP**：以 `--max-concurrency 2` 啟動 bridge（uvicorn 的 `limit_concurrency`），記錄包裝以屏障扣住前兩個請求，第三個並發請求收到 503；放行後第四個請求成功。另一個單元測試：參數解析器不給該參數時值為 16 |

## 三、backend 回應大小

**算式**：最大的成功回應是 `read_requirement_fields` 的 `FieldSetView`。目前宣告 7 個欄位鍵（`functional-spec.md` D-16），
每個值 ≤ 2000 字元、最壞 6 位元組／字元：7 × 2000 × 6 = 84000 位元組，加上每欄的中繼資料仍 < 128 KiB。取 **1 MiB**（1048576 位元組），
約為最壞值的 12 倍，為 `U20` 日後新增欄位留餘裕。

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.22`** | bridge 讀取 backend 回應本體 **> 1048576 位元組**即停止讀取，工具結果為 `internal_error`（`BR76.1` 的「其他」列）；不把部分本體交給 agent | 記錄包裝回 200，三案：① 本體 1048576 位元組以內的合法 JSON → 成功；② 1048577 位元組、帶 `Content-Length` → `internal_error`；③ 以串流送出 2 MiB、不帶 `Content-Length` → `internal_error`，且耗時 ≤ 11 秒（`NFR21.1`）。突變驗證：只依 `Content-Length` 判定 → ③ 紅燈 |

## 四、無狀態與水平擴展

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.23`** | bridge 不持有任何跨請求狀態（`BR71.2` 無狀態、`BR73.3`）：不需 session affinity，可同時跑多個實例 | 以 `create_app` 建兩個實例 X、Y（共用同一個 backend ASGI app），同一個測試 client 交替對 X、Y 發 10 次工具呼叫：全部成功，且不需任何 `Mcp-Session-Id` 之類的 session 標頭延續（若 SDK 回傳該標頭，下一次請求不帶它也成功）。`NFR21.7` 的身分隔離另行涵蓋並發面 |
| **`NFR21.24`** | 本站定的數值（`NFR21.1` 的 3／10 秒、`NFR21.20` 的 65536、`NFR21.21` 的 16、`NFR21.22` 的 1048576）一律為模組常數或命令列參數預設值，**不新增環境變數**（承接 `NFR8`、`BR71.1`） | 與 `NFR21.17` 同一組 grep；四個數值在 `backend/mcp_bridge/` 內各以具名常數定義恰一次（grep 常數名，定義列為 1） |

## 五、刻意不設的目標

| 不設 | 理由 |
|---|---|
| **請求頻率上限**（`OPEN-MB21-10` 第一項） | 頻率限制需要「以誰為單位」：bridge 不解碼 JWT、不知道使用者是誰（`BR73.5`，`[MBN1]`=A 亦未改變此點），以 agent 宣告為單位則可被自報繞過（`BR74.5`）；以 token 字串的雜湊為單位是可行的，但本版無實際 client，失控的情形只可能來自日後的大腦 client，屆時它與 bridge 同主機、同一個信任邊界。本版以 `NFR21.21` 的同時處理上限約束最壞壓力。**`OPEN-MB21-10` 的頻率部分以此理由關閉，於核可關卡揭露**；大腦 client 落地時（`OPEN-MB21-1` 的後續 intent）再評估 |
| 每位使用者的並發上限 | 同上，bridge 不知道使用者是誰 |
| 記憶體上限的數值 | 屬 compose（`functional-spec.md` §八 H-1：「暫定值＋`DEPLOY.md` 標記未量測」），由 `infrastructure-design` 定；本站只要求存在上限，見 `NFR21.32` |
| 自動擴展 | 單一主機、單一 compose 部署（ADR-0007）；`NFR21.23` 只保證「可以」多實例，不要求部署多實例 |
