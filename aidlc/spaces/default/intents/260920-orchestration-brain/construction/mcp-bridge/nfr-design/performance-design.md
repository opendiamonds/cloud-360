# 效能設計 — `U21 mcp-bridge`

> 承接 `../nfr-requirements/performance-requirements.md` 的 `NFR21.1`–`NFR21.3`。本站的工作是把「判準」變成「做法」：每一條寫出它落在
> 哪個模組、哪個時點、以什麼結構承載，以及哪一個檢查會在被改壞時失敗。模組名稱一律以 `logical-components.md` §一 的元件表為準。
> 本站未執行任何程式；凡依賴外部套件行為者標明取得方式。標「靜態讀」者，是讀另一個 clone 的 virtualenv 內已安裝套件原始碼
> （`uvicorn 0.52.3`、`httpx 0.28.1`、`mcp 1.29.0`），**不等於** code-generation 最後釘選的版本，由 code-generation 第一步複核。

## 一、逾時的兩層結構（`NFR21.1`）

httpx 的 `Timeout` 只限制**每一次**連線、讀、寫，「每 2 秒送 1 位元組」的 backend 可使它無限延長，所以整體上限必須另包一層。
兩層各自負責一件事：

| 層 | 設定 | 擋什麼 | 落點 |
|---|---|---|---|
| httpx 的分項逾時 | `httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=3.0)` | 連線建立 3 秒（`BR75.1`）；單次讀寫卡死 | `executor.build_backend_client` 建立共用 client 時設定一次 |
| 整體上限 | `asyncio.timeout(OVERALL_TIMEOUT_S)`（10 秒）包住「送出＋逐塊讀取本體」整段 | 滴流 backend（`NFR21.1` ②）；任何讀寫分項都沒超時、但總時間超過的情形 | `executor.exchange` |

```text
async def exchange(client, call, credential, limits) -> ExchangeResult:   # executor.py
    request = client.build_request(call.method, call.path, json=call.body,
                                   headers={"Authorization": credential.raw})
    try:
        async with asyncio.timeout(limits.overall_timeout_s):
            response = await client.send(request, stream=True)
            try:
                body = await read_bounded(response, limits.max_response_bytes)  # 見 scalability-design §三
            finally:
                await response.aclose()
    except Exception as exc:                       # 只在此處歸類，見 reliability-design §一
        failure = classify_transport_error(exc)
        return failure if failure is not None else InternalFailure()
    return body
```

- `pool=3.0`：連線池上限與並行閘相同（§四），正常情況下取連線不會等待；設 3 秒是防禦值，超過即歸類為 `timeout`。
- `asyncio.timeout` 拋出的 `TimeoutError` 由 `classify_transport_error` 歸為 `TransportFailure.TIMEOUT`（`reliability-design.md` §一）。
- 判準的三案（靜默、滴流、關閉埠）以 `asyncio.start_server` 在測試內構造，兩條依賴路線的拓樸都是真實 TCP，構造方式相同
  （`reliability-design.md` §六）。突變：拿掉 `asyncio.timeout` 那一層 → ② 紅燈。

## 二、事件迴圈不阻塞（`NFR21.2`）

| 可能阻塞的來源 | 處置 |
|---|---|
| 讀設定檔 | 只在 `startup.load_and_validate`（啟動時、uvicorn 起來之前）；`open(` 在 `backend/mcp_bridge/` 內只出現在 `startup.py`，grep 逐筆判讀 |
| 對 backend 的 HTTP | 只用 `httpx.AsyncClient`；同步 `httpx.Client(`、`requests`、`time.sleep` 的 grep 皆 0 |
| JSON 解碼 | 在事件迴圈內以 `json.loads` 解碼，大小有上界：請求 ≤ 65536 位元組（`NFR21.20`）、回應 ≤ 1048576 位元組（`NFR21.22`）。1 MiB 的解碼是毫秒級（**估計，未量測**），不另開執行緒；若 `build-and-test` 量到單次解碼佔附加時間的主要部分，再移到 `asyncio.to_thread` |
| log 輸出 | `StreamHandler` 寫 stderr，與 backend 既有做法相同；每次工具呼叫恰一行（`NFR21.34`） |

`dispatch`、`guards`、`executor` 三個模組內的函式全部是 `async def` 或純同步運算；不呼叫任何會等待 I/O 的同步函式。

## 三、附加時間的量測設計（`NFR21.3`；帶入項 nfr-requirements `R-07`）

**判準改寫為二元（`R-07` (1)）**：`build-and-test` 量出 P50 並與 50 ms 比較，**量測值與比較結果必須寫進該站的測試輸出**；
超過 50 ms 時，該站核可關卡**必須留有一筆裁決紀錄**（接受並記理由／改善後重測／判定預算設錯並重定）。二元條件是
「超過時，裁決紀錄存在與否」——不再是「由關卡裁決」這種沒有通過線的寫法。

**兩條路徑的不對稱（`R-07` (2)）——分段推導，不憑直覺**：以 `T` 表示一次同主機 TCP＋HTTP 往返，`B` 為 bridge 自身處理
（JSON-RPC 編解碼、驗證、組請求），`K` 為 backend 處理。

| 情境 | 經 MCP 的路徑 | 直接呼叫 backend | 差值 |
|---|---|---|---|
| 正式環境（未來的大腦 client） | `T`（client→bridge）＋`B`＋`T`（bridge→backend）＋`K` | `T`＋`K` | `T`＋`B` |
| 第一順位拓樸（同直譯器） | `T`（真實 uvicorn）＋`B`＋0（`ASGITransport`）＋`K` | 0（`ASGITransport`）＋`K` | `T`＋`B` |
| 第二退路拓樸（子進程） | `T`＋`B`＋`T`＋`K` | `T`＋`K` | `T`＋`B` |

三種情境的差值形狀相同，所以 nfr-requirements 原文的「量不到 TCP 往返一段」與審查的「預算被高估」**兩個方向的偏差在差值中都相消**。
剩下的偏差只有兩個，方向如下：(1) 測試 client 的 SDK 編解碼算進 `B`（正式環境的大腦 client 也有同等成本，**不偏**）；
(2) 第一順位下直接呼叫走 `ASGITransport`、經 MCP 的 bridge→backend 那一跳也走 `ASGITransport`，兩邊同形，**不偏**。
前提是「同主機 TCP 往返在兩條路徑上成本相同」——這是假設，`build-and-test` 若量到明顯偏差，以此表為起點拆解。

**抖動（`R-07` (3)）**：輸出除 P50 外另列 P25、P75 與 50 組差值的原始序列；同一 commit 連跑兩次，兩次 P50 相差超過 20% 時，
輸出標記為「不穩定」，裁決紀錄須引用兩次的值。20% 是本站定的判讀門檻（常數），不是預算。

**樣本來源**：沿用 `AC11.4.1`「理由相同」測試已同時發出兩種呼叫的形狀（`NFR21.3` 原文），由 `build-and-test` 擴充為 50 組成對呼叫。

## 四、連線池與並行閘對齊

| 參數 | 值 | 理由 |
|---|---|---|
| `httpx.Limits(max_connections=…)` | 等於 `max_concurrency`（預設 16） | 並行閘保證進行中請求 ≤ 16（`scalability-design.md` §一），對 backend 的請求不會超過它；池上限與之相等使「取連線」不需等待，`pool` 逾時只是防禦 |
| `max_keepalive_connections` | 等於 `max_concurrency` | 同主機長連線重用，省掉每次 TCP 建立 |
| `keepalive_expiry` | httpx 預設（**未改**） | backend 側的 uvicorn 預設 `timeout_keep_alive` 為 5 秒（靜讀 `uvicorn/config.py:229`），閒置連線由 backend 關閉後 httpx 重建，無需對齊 |

兩個數值都由 `BridgeLimits`（`logical-components.md` §一）單一來源推導，不另立常數（`NFR21.24`）。

## 五、刻意不設

沿用 `../nfr-requirements/performance-requirements.md` 第二節（吞吐量目標、啟動時間、`--check` 執行時間、快取），本站無新增理由。
另：**不**以執行緒池處理 JSON 解碼（理由見 §二），**不**做請求合併或批次（每次工具呼叫恰一次 backend 請求，`NFR21.27`）。
