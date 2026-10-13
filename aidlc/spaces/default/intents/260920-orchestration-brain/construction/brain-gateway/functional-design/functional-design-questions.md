# Functional Design 問題檔 — `U13 brain-gateway`

> 單元類型 **`service`**（`unit-of-work.md`，M），產出 `entities.md`、`rules.md`、`functional-spec.md`、
> `traceability.json` 四份。Depth `Minimal`。本單元的大部分形狀已由契約 `K-12` 與上游各單元的交接義務釘死，
> 故只出三題；每一題都是「預設錯了會造成真實重工或安全缺口」的事。

## 一、上游已定案、本站不重問

| 事項 | 定案 | 出處 |
|---|---|---|
| 端點 | `/api/brain/ws`，掛在 `/api/` 之下 | `K-12`（`contract-summary.md:869`、`:874`）；`[RA:FR8.3]` |
| 握手認證 | token 走 `Sec-WebSocket-Protocol`（`bearer.<jwt>`，以第一個 `.` 切分），不得放 query string；`get_user_from_token(record=True)` | `K-12` `:878`、`:883`；`brain_ws_contract.WsSubprotocol`；`[RA:FR8.4]`／`FR8.5` |
| 關閉碼 | 4401 認證失敗／4403 無 `K1`／4400 版本不相容／1011 內部錯誤 | `K-12` `:989-992` |
| 版本協商 | `hello {v}` → `ready`；不相容以 4400 關閉 | `K-12` `:949-950` |
| session 與多連線 | 一個使用者一個大腦 session；同一 key 多條連線並存，`work_target`／`sharing_mode`／`work_items` 推給全部存活連線；連線登錄在行程內（單一後端行程假設） | `K-12` `:887-938` |
| 終止語意 | 每輪恰一個終止事件；零內容 → `error(EMPTY_RESPONSE)`；prompt_guard 命中為有效回覆，以 `done` 結束 | `K-12` `:961-974`；`intent_routing_errors.PlatformSelfModificationRefused` |
| 非冪等 | `user_message` 不得自動重送；重連為新的一輪 | `K-12` `:976-987` |
| 自然語言回覆的來源 | 不新增 LLM 呼叫：編排層固定句型、A1 文字照轉 | `U12` 的 `[WO1]`=A |
| 單一實例 | `IntentRouter`、`WorkOrchestrator` 各一個行程一個實例，由本單元建立 | `U11` code-summary `:254`；`U12` code-summary §七 |
| episodic 記憶 | 每輪結束由本單元寫一筆 `kind=episodic` | `U8` `規則 7.1`；`U8` 的 `[FD4]`=B |
| DEMO 檔 | `backend/services/brain_router.py`（DEMO SCOPE）整支取代 | 該檔 `:27` |

**`AC8.1.1` 的判定方式**（揭露，非提問）：既然回覆來源不新增 LLM（`[WO1]`=A），「畫面在整段產生完成之前就出現第一個字」
以 `stories.md:392-398` 自己指定的**順序性質**驗證（第一個 `token` 早於最後一個 `token`、早於 `done`），落點
`TestClient.websocket_connect`。A1 的說明文字因 ASGI 傳輸緩衝而在產圖結束後才一次轉送（`U12` 的 `BR58.3`）。

## 二、本單元承載的故事

`unit-of-work-story-map.md` 指派 **`US7.1`**（推播，Should）、**`US8.1`**（串流與 WebSocket，Must）。

## 三、問題

### GW1. 握手時伺服器回送哪一個子協定？（安全）

瀏覽器規定：客戶端在 `Sec-WebSocket-Protocol` 提供子協定時，伺服器**必須**從中選一個回送，否則連線被拒。
DEMO 檔的做法是回送 `bearer.<jwt>` 本身（`brain_router.py:275`）——這會把 token 寫進**回應標頭**，而回應標頭
比請求標頭更常被反向代理、Cloudflare 與瀏覽器開發工具記錄。

A) **客戶端同時提供兩個子協定：`cloud360.brain.v1` 與 `bearer.<jwt>`，伺服器只回送 `cloud360.brain.v1`**（建議）：
   token 只出現在請求標頭、不被回送。代價：`U2` 已交付的 `WsSubprotocol` 要追認「另帶一個固定的協定名」，
   `U14` 前端建立連線時要帶兩個值（`new WebSocket(url, ["cloud360.brain.v1", "bearer." + token])`）。
B) **照 DEMO 回送 `bearer.<jwt>`**：不改契約，但 token 出現在回應標頭。
C) **改為握手後首則訊息帶 token**：token 完全不在標頭，但連線在認證前就已 accept（`US8` DoD 點名的 pre-accept
   暴露面），且違反 `K-12` 已定的標頭方案，要回改契約。

[Answer]: A <!-- 2026-10-12T08:10:00Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### GW2. 每輪結束寫 episodic 記憶失敗時，這一輪算不算失敗？

`U8` 的 `規則 7.1` 指派本單元在每輪結束寫一筆 episodic 記憶；`U8` 的 `nfr-design` 把「寫入失敗時對話是否因此失敗」交給本單元決定。
寫入需要呼叫嵌入模型（`MemoryFacade.write` 先取向量），可能因 Ollama 不可用而失敗。

A) **不算失敗：先送 `done`，記憶寫入在之後背景執行，失敗只記 WARNING**（建議）：使用者看到的回覆不受記憶層影響，
   也不讓嵌入呼叫拖慢 `done`。代價：該輪不會被記住，使用者不會被告知。
B) **算失敗：寫入成功才送 `done`，失敗送 `error(INTERNAL_ERROR)`**：記憶完整性優先，但 Ollama 一出問題整個大腦都無法回覆。
C) **不算失敗，但送一則提示「這輪對話沒有被記住」**：誠實，但每次嵌入層抖動都會打擾使用者。

[Answer]: A <!-- 2026-10-12T08:10:00Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### GW3. Redis 不可用時怎麼呈現？

`U10` 遇到 Redis 不可達一律拋 `SessionBackendUnavailable`、不降級，並把「怎麼呈現」交給本單元
（`session-store/nfr-requirements/reliability-requirements.md:64`）。

A) **握手階段遇到 → 以 1011 關閉；連線已建立後遇到 → 該輪送 `error(INTERNAL_ERROR)`，連線保留**（建議）：
   Redis 短暫抖動時使用者只失去那一輪，不必重新連線；握手時連 session 都讀不到則無法提供服務，只能關閉。
B) **任何時候遇到都以 1011 關閉連線**：行為單純，但 Redis 抖動一次所有連線都會被踢掉並同時重連。
C) **降級成行程內暫存繼續服務**：違反 `[RA:NFR4]`（狀態不得放行程記憶體）與 `U10` 的「不降級」，不建議。

[Answer]: A <!-- 2026-10-12T08:10:00Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### GW4. 使用者訊息怎麼表明它來自哪一頁？（產出時發現，追加）

`user_message` 的 payload 只有 `text`（`brain_ws_contract.py`）。本單元分不出訊息來自哪一頁，就無法依 `U10` W2 選擇該頁的段，
所有訊息都會落進共用段，`[RA:FR3.2]`（各頁獨立對話）失效。

A) **在 `user_message` 增加 `page` 欄位（`entry`／`workspace`／`assessment`），本單元據此選段**（建議）：屬 `U2` 已交付契約的增量，列入 `OPEN-GW13-1` 追認；`U14` 送訊息時帶上。
B) **每條連線在 `hello` 宣告頁面**：訊息不帶欄位，但同一分頁切換頁面須重連，同樣要改契約。
C) **本輪只用共用段**：不改契約，但 `FR3.2` 不成立，須標 Deferred 並回報上游。

[Answer]: A <!-- 2026-10-12T15:25:21Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

## Revision 1（2026-10-12T15:44:17Z，依 `reviews/review-01.md`）

審查判定 NOT-READY（Major 4、Minor 8）。本段只記修訂來源與裁決，**既有四題的作答與選項本文不改寫**。

| 審查項 | 裁決來源 | 處置 |
|---|---|---|
| R-02（`AC8.1.1`） | 使用者裁決：標 `Deferred` 並回報上游；不新增任何 LLM 呼叫；傳輸層保留逐則送出 | `traceability.json` 改 `Deferred`；`functional-spec.md` `OPEN-GW13-15`（改寫 AC 或追加串流 LLM 回覆，交使用者裁決） |
| R-01 | 使用者指定方向：referent 無法唯一解析時不得交辦給舊對象，改走反問或以固定句型請使用者指定 | 新增 `BR64.11` |
| R-03 | 使用者指定方向：本單元擁有注入 `U11` 的記憶轉接器，以 `to_thread` 預取 | 新增 `BR67.10`；更正 `OPEN-GW13-4` |
| R-04 | 使用者指定方向：契約增量逐欄定義並列入契約追認 | `functional-spec.md` §十一；`OPEN-GW13-1` |
| R-05～R-12 | 使用者指定：依各列 Required action 處置；R-10 的三個 `consumed_by` 列為契約追認並更正 H-24 | `functional-spec.md` §十二 逐項對照 |

`[GW4]`=A（`page` 欄位）在修訂前已作答，本輪將其逐欄定義為契約增量 C-2（`functional-spec.md` §十一）。
規則數 44 → 49（新增 `BR62.6`、`BR64.11`、`BR65.5`、`BR67.10`、`BR67.11`）。

## Revision 2（2026-10-12T22:45:18Z，依 `reviews/review-02.md`）

審查判定 NOT-READY（Major 2、Minor 5）。使用者裁決：重開、修進設計再審。本段只記修訂來源，**既有四題的作答與選項本文不改寫**，本輪未新增提問、未新增 LLM 呼叫。

| 審查項 | 使用者指定的方向 | 處置 |
|---|---|---|
| R-01 | 未選定時系統名稱須能在使用者可見的全部專案中解析，不得繞過 facade；AC1.1.5 依實際覆蓋判定 | 新增 `BR64.12`；改寫 `BR64.9`；`traceability.json` 納入 `AC1.1.5` |
| R-02 | 反問選定後曾有指涉但未解析時不得帶舊對象交辦 | 新增 `BR64.13`（以原句掃描對象）；改寫 `BR64.8` |
| R-03 | 握手期先登錄再讀取，寫明順序與理由 | 新增 `BR63.6`；改寫 `BR63.1`、`BR63.2` |
| R-04 | 列出 `test_ws_contract.py` 須同步修改的行 | `functional-spec.md` §十一之二 第 5 點 |
| R-05 | 多意圖反問形狀、`ClarifyPayload` 鑑別欄位、與 episodic 的關係 | 改寫 `BR64.11`、`BR67.7`；契約增量 C-7 |
| R-06 | startup 順序含 `configure_intent_routing_env` 之後；Redis client 設定來源與失敗語意；A-6 定案 | 改寫 `BR67.11`；A-6 改為已確認事實 |
| R-07 | 預取改用專用有界執行器並寫明上限與逾時 | 新增 `BR67.12`；改寫 `BR67.10` |

規則數 49 → 53（新增 `BR63.6`、`BR64.12`、`BR64.13`、`BR67.12`）。逐項對應見 `functional-spec.md` §十三。
