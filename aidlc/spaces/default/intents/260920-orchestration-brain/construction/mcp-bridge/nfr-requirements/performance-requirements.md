# 效能需求 — `U21 mcp-bridge`

> 撰寫時間 2026-10-14T16:24:59Z（`date -u` 取值）。
>
> **本站引入新的 parent id `NFR21`**（比照 `U12` 的 `NFR12`、`U13` 的 `NFR13`；全 record 以 `grep -rhoE "NFR21\.[0-9]+"` 實查，
> 本站寫檔前為 0 命中，無碰撞）。上游 `requirements.md` 的 `NFR1`–`NFR11` 逐條判定見 `traceability.json` 的 `coverage`；本單元專屬、
> 可驗證的需求一律另立 `NFR21.x`，不硬掛到不相干的 parent 之下。功能面的正式來源是本單元 functional-design（`rules.md` 的
> `BR71.1`–`BR78.5`，45 條；`functional-spec.md` §十二 的必測清單 `T-1`–`T-8`）與帶入清單 `carried-review-items.md`（`review-02` 的
> 11 項，對照見 `security-requirements.md` 第七節）。本站的唯一一題 `[MBN1]`=A（`nfr-requirements-questions.md:74`，
> 2026-10-14T16:22:38Z 經選單作答）落在 `security-requirements.md` 第五節。
>
> **判準的共同前提**：凡寫「驗證拓樸」者，指 `BR78.2` 的拓樸——bridge 經 `BR78.3` 的 `create_app` 建立、以 uvicorn 起在
> `127.0.0.1` 的隨機埠，bridge 對 backend 的呼叫經 `httpx.ASGITransport` 直達真實的 FastAPI app（`backend/tests/helpers.py` 的
> SQLite 測試資料庫）；凡寫「記錄包裝」者，指 `BR78.4` 在 backend app 外包的一層只記 `(method, path, 標頭)` 的 ASGI 包裝。
> 凡需要**真實 TCP** 的判準（逾時、併發上限）逐條註明，因為 `ASGITransport` 不經網路、httpx 的逾時設定對它不生效。

## 〇、本單元的效能面

bridge 本版**沒有任何實際呼叫端**（`OPEN-MB21-1`，`[MB1]`=A），也不在大腦的首字路徑上（`NFR3` 的路徑不經 MCP），故本單元
對使用者可感延遲的影響目前為零。效能需求只管三件事：**一次工具呼叫最久卡多久**（逾時上限，直接決定日後 agent 的等待）、
**bridge 不得卡住自己的事件迴圈**（單一進程服務所有呼叫）、**bridge 自己多加的時間**（預算，不是預測）。

## 一、需求

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.1`** | 一次工具呼叫從送出 backend 請求到取得工具結果，**最久 10 秒**（整體上限，不是每次讀取的上限）；連線建立最久 3 秒（`BR75.1`、`BR76.1`、MB-W1 第 3 步）。逾時一律映射為 `backend_unavailable`、`retryable: true`。**注意**：httpx 的 `Timeout(10, connect=3)` 中的 10 秒是**每次讀取**的上限，不是整體上限——「每 2 秒送 1 位元組」的 backend 可以讓它無限延長；整體上限必須由執行層另以 `asyncio.timeout`／`wait_for` 包住整次 `send` 與本體讀取 | **真實 TCP**（bridge 的 `--backend-url` 指向測試內以 `asyncio.start_server` 起的本機 socket），三案：① 接受連線但永不回應 → 工具結果為 `backend_unavailable`、`retryable` 為真，自送出起算耗時 ≤ 11 秒；② 每 2 秒送 1 位元組、永不結束 → 同上，耗時 ≤ 11 秒（**這一案只有整體上限擋得住**）；③ 埠已關閉（連線拒絕）→ 同一錯誤碼，耗時 ≤ 1 秒。突變驗證：拿掉整體上限、只留 httpx 的 `Timeout` → ② 紅燈 |
| **`NFR21.2`** | 處理請求的路徑上**不得有阻塞式 I/O**：不得使用同步 HTTP client、`time.sleep`、同步檔案讀取；讀檔只發生在啟動時的具名載入函式（`R-17` 要求的 `load_and_validate`，MB-W1 第 2 步） | grep `backend/mcp_bridge/`：`requests`、`time.sleep`、`httpx.Client(`（同步版）的出現次數皆為 0；`open(` 只出現在啟動載入函式所在的模組與函式內（逐筆判讀，結果寫進 `code-generation` 的 code-summary） |
| **`NFR21.3`** | bridge 自身附加時間（同一 token、同一系統下，「經 MCP 工具呼叫」減「直接呼叫 backend GET」）**P50 ≤ 50 ms**。**這是預算，不是預測**：本 repo 沒有延遲量測機制，且本版無實際 client | `build-and-test` 在驗證拓樸上做 50 組成對呼叫（`AC11.4.1` 的「理由相同」測試已同時發出兩種呼叫，沿用之），計算差值的 P50 並寫進測試輸出。未達標時**不自動放寬**，由 `build-and-test` 的核可關卡裁決（接受實測值並記理由／改善後重測／判定預算設錯並重定）。限制：`ASGITransport` 不含 TCP 往返，正式環境的附加時間會多一次同主機 TCP 往返（compose `internal` 網段），本判準量不到那一段 |

## 二、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 吞吐量目標（每秒工具呼叫數） | 本版無實際 client（`OPEN-MB21-1`），沒有負載可預測；同時處理量的**上限**以 `scalability-requirements.md` 的 `NFR21.21` 約束，那是保護 backend 的數字而非服務目標 |
| 啟動時間目標 | 啟動不呼叫 backend（`BR71.4`），只載入兩份小 JSON；compose healthcheck 的 `start-period` 由 `infrastructure-design` 定（H-2），本站不另設 |
| `gen_mcp_tools.py --check` 的執行時間 | 純函式處理三個 operation，CI 時間不構成風險；漂移閘門的**正確性**見 `NFR21.31` |
| 快取 | bridge 不得持有跨請求狀態（`BR73.3`、`BR71.2` 無狀態）；需求欄位的讀取也不適合快取（授權隨請求的 token 而變） |
