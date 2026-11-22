# 邏輯元件 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M）　Stage：`nfr-design`（3.3）
> 本檔橋接 NFR 設計決定與 Infrastructure Design：給出元件層視圖（服務邊界、
> 失效域、blast radius、隔離策略、共享資源）。
>
> **注意：`infrastructure-design` 對本單元不適用**——其 `produces_kinds` 為
> `[service, ui, packaging]`，本單元是 `library`。所以本檔的下游讀者是
> `code-generation`，不是基礎設施設計。

---

## §一 元件清單

本單元只有一個邏輯元件，**沒有服務邊界**（無進程、無 socket、無 port）。

| 元件 | 類型 | 執行位置 | 對外介面 |
|---|---|---|---|
| `ProgressChannelRegistry` | 行程內狀態容器（`library`） | 既有 FastAPI 行程內，與呼叫端同一個事件迴圈 | 四個同進程方法：`open`／`publish`／`drain`／`close`（`K-18` `public_interface`） |

內部結構（非獨立元件，列出以供 blast radius 分析）：

| 內部結構 | 角色 |
|---|---|
| `_channels: dict[str, _Channel]` | **唯一的共享可變狀態**。取代 `design_agent.py:31` 的模組層全域 |
| `_Channel.buffer: deque[ProgressEvent]` | 單一請求的事件 FIFO，有限上界（數值見 `S-1`） |
| `_admit(channel, event)` | 私有**同步**函式，臨界區段（`[Q1]`=A）。`await` 在其中是 `SyntaxError` |

---

## §二 失效域與 blast radius

這一節是本檔的實質內容，因為**本單元存在的理由就是把一個 blast radius 從「全部
使用者」縮到「一個請求」**。

| | 現狀（`_progress_queue` 模組層全域） | 本設計（per-key registry） |
|---|---|---|
| **失效域** | 整個行程的**所有併發請求** | **單一請求**（`U22-V1` 的互斥斷言即量測這一格） |
| 一個請求覆寫狀態的後果 | 另一個請求收到它的事件（跨帳號內容外洩） | 無——鍵不同即不同格子 |
| 一個請求結束的後果 | 另一個請求的通道變 `None`，其 `drain` 崩潰 | 無——`close(kB)` 不碰 `kA` |
| 一個請求的例外原文 | 經 `:103`／`:216` 送達使用者 | 只進 `logger.exception`（§二 單一出口） |
| 一個請求寫爆記憶體 | 無上界（`asyncio.Queue()`） | 該請求的 buffer 達上界後丟棄最舊的 `progress`；`xml`／`error` 永不丟 |

**仍然共享、無法由本單元隔離的**（如實記載）：

| 共享資源 | 誰共享 | 本單元的處置 |
|---|---|---|
| `_channels` dict 本身 | 全部併發請求 | 鍵隔離使**內容**不共享，但**容器**仍是一個。容器層的失效模式只剩一種：鍵洩漏導致無上界成長（`BR2.1`／`BR2.3` 的清除契約 ＋ `U22-V2` 的測試承擔） |
| 行程的記憶體總量 | 全部併發請求 ＋ 整個應用 | 單請求有上界（`BR4.1`），**但存活通道數沒有上界**——`[Q2]`（`functional-design`）的選項 D（存活通道數上界）未被採用。這是一個已知且被接受的殘餘面：若清除契約被違反，成長由存活請求數而非單請求決定 |
| 單一事件迴圈 | 全部協程 | `_admit` 為同步函式，故臨界區段不可被其他協程插入（`[Q1]`=A）。**這是本單元對「共享事件迴圈」這個資源的全部處置**——它不需要鎖，因為它不 `await`。`drain` 同樣是純同步的 `deque` 取出迴圈、無 I/O，這承載 `U22-V6`（不得成為首字延遲來源，`NFR3`） |

---

## §三 隔離策略

| 層 | 機制 | 強度 |
|---|---|---|
| 請求之間的事件隔離 | per-key dict，跨鍵取值需要一個不存在的操作 | **結構保證**（非檢查） |
| 臨界區段的原子性 | 私有同步 `def`，`await` 即 `SyntaxError` | **型別／語法保證**（非規則） |
| 例外原文不外洩 | 單一出口：原文只進 `logger.exception`，對外一律固定字串 | **控制流保證**，驗證為形狀級 grep（不依賴訊息文字） |
| 鍵的不可重用與不碰撞 | 密碼學安全隨機源（`SEC-1`） | **在呼叫端**，本單元只保證自己不鑄造（`U22-V5`）。缺口見 `S-5` |

三層保證的共同形狀：**都不靠人記得**。這是本站兩個決定（`[Q1]`、`[Q2]`）的選擇依據
——上一輪審查連續兩次指出「只取建議的一半」「靠人遵守」，本站刻意兩次都取結構。

---

## §四 對 `code-generation` 的元件層交接

| 項 | 內容 |
|---|---|
| 新檔 | `backend/services/progress_channel.py`（`U22-D1`） |
| 改檔 | `backend/services/design_agent.py`（五個退場符號 ＋ `:103`／`:216` 的固定字串）、`backend/services/wa_collab_orchestrator.py:79`、`backend/services/agent_router.py:125`、`backend/test_agent.py:41`（後三者為 `S-2` 的三個呼叫點） |
| 新測試 | `backend/tests/test_progress_channel.py`（`unittest` ＋ `IsolatedAsyncioTestCase`，`U22-D8`） |
| 零新依賴 | `collections.deque` ＋ `dict`，標準庫（`U22-D3`） |
| 零部署變更 | 無環境變數、無 compose 服務、無 schema（`SEC-4`）；compose 維持 6 個服務 |
| 無 IaC、無基礎設施 | 本單元無獨立執行期，故 `infrastructure-design` 對它 kind-vacuous |

**不在本單元的元件層決定**：SSE／WebSocket 的傳輸與重連（`U13`）、`thread_id` 的
分區語意與 `MemorySaver()` 單例（`FR13.4`，`functional-design` 的 `OQ-P2`）、
鍵的鑄造（`U13`／`U12`，`S-5`）。
