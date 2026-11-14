# 擴展需求 — `U13 brain-gateway`

## 〇、本單元的擴展面

本單元沒有自己的持久化儲存（session 在 `U10` 的 Redis key、記憶在 `U8`），也沒有新進程。真實的擴展面是**對外的
WebSocket 面**：連線數、訊框大小、訊息頻率——`OPEN-GW13-13`（`functional-spec.md:407`）把這三者標為「未設限」並指派本站，
`session-store` 也明寫「限流屬 `U13`」（`session-store/nfr-design/reliability-design.md:27`）。本站在此**定數字並附理由**。

**單一行程假設**（`A-1`，`functional-spec.md:440`）：以下所有上限都是**每行程**的值；本 repo 部署只有一個行程
（`backend/Dockerfile:30` 的 `uvicorn` 指令無 `--workers`），其守門見 `NFR13.33`。

## 一、連線數（`OPEN-GW13-13` 第一項）

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR13.17`** | 每行程的登錄連線數（載入中＋就緒）上限 **200**；已達上限時，新的握手在**認證之前**即拒絕升級（不 accept，`close()`，真實環境為 HTTP 403），不付任何 DB 成本；記 INFO 計數 | 以替身把登錄計數設為 200：第 201 個握手未 accept，且認證替身呼叫 0 次；降回 199 後下一個握手正常收到 `ready`。**限制**：未 accept 的形狀在 `TestClient` 下為關閉碼 1000（見 `NFR13.8` 的限制） |
| **`NFR13.18`** | **（`[GWN1]`=A，使用者 2026-10-12 定案）** 同一 session key 的登錄連線數上限 **10**；超過時在認證之後、accept 之前拒絕升級，不影響該使用者既有的連線 | 同一使用者先建 10 條連線，第 11 條未 accept、前 10 條仍可收發；關掉其中一條後第 11 次重試收到 `ready` |

**數值理由**：
- **200**：不是容量估計而是保護上界。每條就緒連線的固定成本是每 60 秒一次 `to_thread` 認證（`BR62.6`）——200 條即約
  每秒 3.3 次 DB session（`python3 -c "print(200/60)"` 實算 3.33），遠低於既有端點的負載；載入中的連線另有至多 256 則的
  暫存佇列（`NFR13.22`）。上界的作用是讓一個失控的客戶端（重連迴圈）無法讓行程記憶體與 `to_thread` 預設池無限成長。
- **10**（若採用）：`K-12` 規定入口頁、`/workspace`、`/assessment` 三處**皆持有一條連線**（`contract-summary.md:911-913`），
  10 容得下三頁各開三個分頁再加一條重連重疊；它防的是「單一使用者的重連迴圈吃光 200 條全域額度、把其他人擋在外面」。
- **拒絕形狀選「不 accept」而非新的關閉碼**：新關閉碼是契約增量（`K-12` 的關閉碼清單），須進 `ADR-0020`；本站不擴大
  `ADR-0020`。代價是客戶端分辨不出「額滿」與「協定錯誤」（兩者皆為連線失敗）——**`U14` 的重連必須是有上限的退避**，
  否則額滿時會形成重試風暴。此為對 `U14` 的配合事項，列入 `functional-spec.md` §十一之四的同一清單（由 `U14` 承接）。
- **與上游的關係**：`U10` 的 `NFR2.41` 逐字為「同一 session key 的並存連線數**不設上限**」（`session-store/nfr-requirements/scalability-requirements.md:41`），
  而 `K-12` 的 `multiple_allowed` 只要求「允許多條並存」（`contract-summary.md:919-920`）。`NFR13.18` 與前者字面牴觸、與後者相容——
  **這是改寫已核可上游字面的決定，只有使用者能做**，故出成 `[GWN1]`（問題檔）；使用者選 A，偏離 `NFR2.41` 字面於此揭露，U10 的檔案不回改。`NFR13.17` 是每行程的全域上限，
  不以 session key 為單位，與 `NFR2.41` 不牴觸。

## 二、訊框大小（`OPEN-GW13-13` 第三項）

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR13.19`** | 入站單一訊框上限 **65536 位元組**，在 **JSON 解析之前**以應用層檢查；超過 → 不解析、不處理，以新 turnId 送 `error(INVALID_REQUEST, "訊息太長，請縮短後再送出")`（沿用 `BR67.1` 對 `SessionMessageTooLong` 的同一句），連線保留。**不改** uvicorn 的全域 `ws_max_size` | ① 送 65537 位元組的文字訊框：收到上述 error，`json.loads` 替身（或 `WsUnvalidatedEnvelope` 驗證）未被呼叫、`classify` 0 次；送 65536 位元組以內的合法 `user_message`（4000 字）照常處理。② `backend/Dockerfile` 的 `CMD` 不含 `--ws-max-size`（grep） |

**數值理由**：最大的合法客戶端訊框是 4000 字的 `user_message`（`session_store.py:113` 的 `DEFAULT_MESSAGE_MAX_CHARS`）。即使
每個字都被 JSON 跳脫成 `\uXXXX`（6 位元組），本文為 4000 × 6 ＝ 24000 位元組（`python3 -c "print(4000*6)"`），加上信封
不到 1 KiB；65536 為其 2.7 倍以上的餘裕（`python3 -c "print(round(65536/24000,2))"` 得 2.73）。**為何不改全域
`ws_max_size`**：同一行程的 `collab_router` WebSocket 會收整張架構圖 XML，上限 `MAX_DIAGRAM_XML_CHARS = 2 * 1024 * 1024`
（`collab_router.py:33`），把全域上限降到 64 KiB 會打壞協作。**殘留（揭露）**：uvicorn 仍會在交給應用之前把單一訊框緩衝到
預設的 16 MiB；真正的位元組上界屬部署層，列入 `OPEN-GW13-13` 的 `infrastructure-design` 一半（若該站被 skip，轉
`build-and-test`，判定 skip 者須重新提交使用者）。

## 三、訊息頻率（`OPEN-GW13-13` 第二項）

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR13.20`** | (a) 同一 session key 的 `user_message` 在任意 60 秒滑動窗內至多 **20** 則；(b) 同一連線的全部客戶端訊框在任意 60 秒滑動窗內至多 **120** 則。超過 → 不處理該則（不重驗、不分類、不寫歷程），以新 turnId 送 `error(INVALID_REQUEST, "訊息太頻繁，請稍候再送出")`，連線保留。檢查位於訊框大小之後、**重驗之前**（洪水不轉成 DB 負載） | 以假時鐘：① 同一使用者的兩條連線合計送第 21 則 `user_message` → 收到上述 error，`classify` 與認證替身皆未因第 21 則被呼叫；推進 60 秒後第 22 則正常處理。② 單一連線 60 秒內送第 121 個 `set_sharing_mode` → 收到 error 且 `set_sharing_mode` 替身未被呼叫 |

**數值理由**：20 則／分鐘＝平均每 3 秒一句，高於人在入口頁打字交辦的實際節奏，卻把**每位使用者每分鐘的計費分類呼叫**
封頂在 20 次（`NFR9`「盡量省」）；以 session key 計是因為以連線計會被多開分頁放大。120 則／分鐘（每秒 2 則）給點選類訊息
（切換對象、共享模式、反問選擇、更正）足夠空間，作用是擋住失控的客戶端迴圈。**連帶效果**：episodic 記憶的寫入速率因此
每位使用者至多 20 筆／分鐘，回應 `memory-service` 對「列數由 `U13` 每輪寫入決定、會持續成長」的關切
（`memory-service/nfr-requirements/scalability-requirements.md:32`）。**新句型的位置**：「訊息太頻繁，請稍候再送出」是
`BR67.1` 封閉表的**新增一列**（code 沿用既有的 `INVALID_REQUEST`，`brain_ws_contract.py:303` 的四值之一，**不是契約增量**），
由 code-generation 寫入 `BR67.1` 對應的實作表與 `NFR13.14` 的封閉表測試。

## 四、每輪與載入期的工作量上界

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR13.21`** | 對象目錄每輪至多 1＋50 次 facade 查詢、同一 DB session、不快取（`BR64.12`）。**專案數超過 50 時不得回「找不到系統」的不實句型**：此時目錄只含專案名稱、不含系統名稱（`BR64.12`），故 referent 或原句**零筆相符**時，回「專案太多，請先在脈絡列選定專案」＋ `done`，取代 `BR64.11` (b) 的「找不到名為…」句型（帶入項 4）；多筆相符仍走 `BR64.11` (a)；當前段已選專案時，`BR64.9` 第 1 步照常比對該專案的系統 | ① 51 個專案的替身、脈絡列未選定、referent 為某系統名：`list_systems` 被呼叫 0 次、`list_projects` 1 次；收到的 token 文字恰為「專案太多，請先在脈絡列選定專案」，**不含**「找不到」。② 同樣 51 個專案但已選定某專案、referent 為該專案下唯一的系統名：`set_work_target` 被呼叫 1 次並交辦。③ 50 個專案：`list_systems` 被呼叫 50 次。**附帶**：`traceability.json`（functional-design）的 `AC1.1.5` 註記須列出「專案數 ≤ 50 或已選定專案」為主情境的成立條件——由 code-generation 一併更新 |
| **`NFR13.22`** | 載入中連線的暫存佇列上限 **256** 則；第 257 則 → 以 1011 關閉該連線、移出登錄，**不丟棄單則**（`BR63.6`） | 在 `load` 替身內注入 257 次 `emit_session`：該連線收到 1011、登錄中無此連線；注入 256 次則收到 `ready` 並恰收到 256 則暫存訊息 |

## 五、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 多行程擴展（Redis pub/sub 扇出） | 單一行程假設是 `K-12` 的已核可前提（`contract-summary.md` 的 `fanout_mechanism_and_its_assumption`）；改多行程是新的架構決定，不在單元層做。本站只以 `NFR13.33` 守住假設不被無聲打破 |
| 每連線的送出佇列上限 | 送出以 `asyncio.Lock` 序列化、失敗即移除（`BR63.4`），慢客戶端只拖慢自己那條；伺服器發起的訊息量由 `U12` 的工作項數決定，無上游數據顯示需要上限 |
| 頻率與連線上限做成環境變數 | 見 `tech-stack-decisions.md` 的 `NFR13.44`：模組常數，避免新增 `NFR8` 的三處同步義務 |
