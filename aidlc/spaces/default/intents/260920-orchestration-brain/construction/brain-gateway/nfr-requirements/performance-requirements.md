# 效能需求 — `U13 brain-gateway`

> **本站引入新的 parent id `NFR13`**（比照 `U12` 的 `NFR12`；全 record 以 `grep -rhoE "NFR13\.[0-9]+"` 實查 0 命中，無碰撞）。
> 上游 `requirements.md` 的 `NFR1`–`NFR11` 逐條判定見 `traceability.json` 的 `coverage`；本單元專屬、可驗證的需求一律另立
> `NFR13.x`，不硬掛到不相干的 parent 之下。功能面的正式來源是本單元 functional-design（`rules.md` 的 `BR61.1`–`BR67.12`，
> 53 條）與帶入清單 `carried-review-items.md`（`review-03` 的 6 項，對照見 `reliability-requirements.md` 第三節）。
>
> **判準的共同前提**：凡寫「替身」者，指 `backend/tests/` 既有形狀的測試替身——Redis 用 `FakeRedis`
> （`tests/test_session_store_behaviour.py:83`）或 `WorkItemFakeRedis`（`tests/work_orchestrator_fakes.py:31`），時鐘用
> `FakeClock`（`tests/work_orchestrator_fakes.py:80`）；WebSocket 用 `TestClient(app).websocket_connect(...)`（starlette 0.46.2
> 實測可讀 `accepted_subprotocol` 與 `extra_headers`、可接到關閉碼）。**只在替身上驗得到的性質逐條註明限制。**

## 〇、本單元的效能面

本單元零新進程、零新監聽埠（embedded，`functional-spec.md:22`）。它對延遲的影響只有兩處：**一則 `user_message` 從收到到
第一則內容送出的「交接膠水」時間**，以及**本單元的同步 I/O 是否卡住同一行程的其他連線**。分類本身（`U11`）、交辦內部
（`U12`）與能力耗時都不在本單元控制內。

## 一、交接膠水時間的預算分配（承接 `NFR3`；`OPEN-GW13-9`；`intent-router` `performance-requirements.md:87`）

`U11` 把 `NFR3` 的 2000 ms 切成「`classify` 800 ms ＋ 下游首字 1200 ms」，並把「`U13` 解包／授權 → `U12` 建項 → 分派」這段
**列為未分配、指派本站**（`intent-router/nfr-requirements/performance-requirements.md:84-88`）。本站的分配基於一個已查證的
事實：**在本單元的交辦路徑上，該輪第一則內容 token 是 `U12` 在 `dispatch` 內、呼叫任何能力之前送出的固定建立訊息**
（`U12` 的 `NFR12.1`：不等待能力即回傳；`U12` 經 `emit_in_turn` 送出，`functional-spec.md:57`）。故 `U11` 宣告的「下游能力首字
1200 ms」在本路徑上**整段就是交接膠水 ＋ `U12` 的 `dispatch` 前段**，不存在另一個「能力首字」。

```
NFR3 的端到端預算                                   P50 ≤ 2000 ms（送出 → WS 收到第一則內容）
  ├─ U13 分類前（重驗 → 攔截 → load → 記憶預取）      P50 ≤  400 ms   ← NFR13.1(a)，本站定
  ├─ U11 classify                                     P50 ≤  800 ms   ← NFR3.60（U11 已定）
  ├─ U13 分類後到第一則內容（寫歷程 → 目錄／對象 →
  │    重讀 → U12 dispatch 送出第一則 token）          P50 ≤  300 ms   ← NFR13.1(b)，本站定
  └─ 保留（量測變異與未歸因的排程延遲）                       500 ms   ← 刻意不分配
```

算式：400 ＋ 800 ＋ 300 ＋ 500 ＝ 2000（`python3 -c "print(400+800+300+500)"` 實算）。

**為何分類前拿 400 ms**：此段有一個本單元無法壓縮的成本——記憶預取（`BR67.10`）要呼叫嵌入（部署為 Ollama、本機為
`fastembed`，`LOCAL-DEV.md:26`），其餘三步（一次 `to_thread` 的認證三連、`prompt_guard` 純函式、一次 Redis `load`）皆為
同主機毫秒級。**為何分類後只拿 300 ms**：此段全是同主機的 Redis／PostgreSQL 往返（`append_message`、至多 1＋50 次 facade
查詢、`set_work_target`、重讀、`U12` 的 Lua 寫入），無外部呼叫。**為何保留 500 ms 不分配**：兩段的數值都是**預算不是預測**
（同 `U11` 的立場，`intent-router` `performance-requirements.md:63`），嵌入延遲在本 repo 從未量測；保留額是讓首次實測若
其中一段略超、端到端仍可判讀，而不是逼人立刻改寫門檻。

**反問與攔截的輪次**：該輪沒有 `token` 而是 `clarify`（`BR64.8`）或固定拒絕句（`BR64.5`）。本站建議 `build-and-test` 把
`clarify` 訊框的送出時刻視為「第一則內容」；攔截輪次在分類前即結束，只計 (a) 段。此為量測定義的建議，最終定義落
`build-and-test`（與 `U11` 對輪詢型下游的處置同形，`intent-router` `performance-requirements.md:100-101`）。

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR13.1`** | (a) 分類前段 P50 ≤ 400 ms；(b) 分類後到第一則內容 P50 ≤ 300 ms。兩段皆以伺服器端計時、不含使用者網路往返（與 `NFR3` 的量測方式一致） | **量測落點 `build-and-test`**（`NFR3` 的量測機制是 `requirements.md:716` 的 `N-3`，尚未存在）：以 `NFR13.35` 的逐輪計時 log 統計兩段 P50，各自 ≤ 門檻為通過。未達標依 `NFR1` 的校正程序（`requirements.md:400-428`）裁決，不自動改寫門檻。**本站可先驗的部分**：`NFR13.35` 的欄位存在且歸因正確 |
| **`NFR13.2`** | 第一則內容不被任何「尾段工作」延後：`U12` 經 `emit_in_turn` 交來的每則 token **收到即送**（`BR65.2`），不等 `dispatch` 回傳；episodic 寫入在終止事件**之後**於背景進行（`BR67.7`，`[GW2]`=A） | 兩案：① `dispatch` 替身先呼叫 `emit_in_turn` 再等待一個不會自行設定的 `asyncio.Event`：客戶端在 1 秒內收到該 token（此時 `dispatch` 尚未回傳）；② `MemoryFacade.write` 替身睡 5 秒：客戶端在 1 秒內收到 `done`，且 `write` 仍被呼叫恰 1 次 |
| **`NFR13.3`** | 記憶預取的等待上限（現值 3000 ms，`BR67.12`）**依實測定值並寫明理由**（帶入項 5）：在 code-generation 量測嵌入的暖機 P50／P95 與冷載首呼叫耗時，取「≥ 暖機 P95 × 1.5」且「≤ 3000 ms」的值；冷載超過上限時接受該輪不帶記憶分類（`U11` 既有降級） | ① code-generation 的產出（`code-summary.md`）含一張量測表：嵌入提供者、樣本數、暖機 P50／P95、冷載首呼叫、選定值與算式；缺表即未通過。② 測試：嵌入替身睡「上限＋0.5 秒」，`classify` 替身在上限＋200 ms 內被呼叫，且收到的轉接器在 `search` 時拋例外（預取記為失敗）。**限制**：Ollama 只在部署 stack 存在（`LOCAL-DEV.md:26`）；code-generation 若無法在部署主機量測，以本機 `fastembed` 的數字暫定並把 Ollama 實測轉 `build-and-test`，在 code-summary 明記「暫定」 |

## 二、事件迴圈不得被同步阻塞（`BR67.5`）

本單元自己的同步呼叫**逐一列舉**（取自 `functional-spec.md:66-79` 的呼叫一覽，加上背景重驗），共 **11 個落點**：

| # | 呼叫 | 時機 | 執行方式 |
|---|---|---|---|
| 1 | `get_user_from_token(record=True)` ＋ `user_can(K1)` ＋ `mint_principal` | 握手 | `asyncio.to_thread`，同一 DB session（`BR61.4`） |
| 2 | 同上（`record=True`） | 每則客戶端訊息（hello 除外） | `to_thread`（`BR62.1`） |
| 3 | 同上（`record=False`） | 每 60 秒背景重驗 | `to_thread`（`BR62.6`） |
| 4 | `SessionStore.load` | 連線建立、分類前、交辦前重讀 | `to_thread` |
| 5 | `SessionStore.append_message` | 使用者訊息、本輪回覆、段已知的推播 | `to_thread`（`BR64.6`、`BR64.10`、`BR65.5`） |
| 6 | `SessionStore.set_sharing_mode` | `set_sharing_mode` 訊息 | `to_thread`（`BR66.2`） |
| 7 | `SessionStore.set_work_target` | `set_work_target`、referent 唯一相符、對象反問選定 | `to_thread`（`BR66.1`、`BR64.9`） |
| 8 | `SessionStore.load_work_items` | `correct_work_item` 之前 | `to_thread`（`BR66.3`） |
| 9 | `HierarchyFacade.list_projects` ＋ 每專案 `list_systems` | 對象目錄 | 一次 `to_thread`、同一 DB session（`BR64.12`） |
| 10 | `MemoryFacade.search` | 分類前預取 | **專用記憶執行器**，非 `to_thread`（`BR67.10`、`BR67.12`） |
| 11 | `MemoryFacade.write(episodic)` | `done` 之後 | **專用記憶執行器**（`BR67.7`、`BR67.12`） |

**具名殘留（不在本單元判準內）**：`U12` 對 `SessionStore` 的同步呼叫在事件迴圈上（`OPEN-GW13-4`，`functional-spec.md:398`），
本單元不包裝；其量測落 `build-and-test`。

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR13.4`** | 上表第 1–9 項一律在事件迴圈執行緒以外執行 | 每個同步替身記錄 `threading.get_ident()`；handler 內記錄事件迴圈執行緒 id。走完「握手 → 一則帶 referent 的交辦（觸發對象目錄） → `set_work_target` → `set_sharing_mode` → `correct_work_item` → 推進假時鐘 60 秒」：九類呼叫皆至少被記錄一次，且**全部**不等於迴圈執行緒 id。突變驗證：把第 4 項改為直呼 → 紅燈 |
| **`NFR13.5`** | 第 10、11 項只在專用執行器（`max_workers=4`、`thread_name_prefix="brain-memory"`）上執行；**同時在途至多 4 件、不排隊**——4 件皆在途時，新的預取立即記為失敗、新的 episodic 寫入立即跳過（記 WARNING 計數），兩者皆**不開啟熔斷**（帶入項 5 的「執行器佇列設上限，超出即跳過預取」）。認證、session 讀寫等仍走 `to_thread` 預設池，不被嵌入排擠（`BR67.12`） | ① 替身記錄執行緒名稱：第 10、11 項的名稱以 `brain-memory` 開頭，第 1–9 項皆否。② 以 4 個睡 10 秒的嵌入替身佔滿執行器，再送第 5 則訊息：其預取在 50 ms 內記為失敗（不等 3 秒）、熔斷狀態仍為關閉；同時進行的重驗與 `load` 在 1 秒內完成（`BR67.12` 的可驗證性） |
| **`NFR13.6`** | 本單元**不新增任何 LLM 呼叫**（`[WO1]`=A 的延伸；承接 `NFR9`）；會產生計費的唯一下游是 `U11.classify`，在它之前必須已完成：訊框大小（`NFR13.19`）、頻率（`NFR13.20`）、文字長度（`BR64.3`）、`prompt_guard`（`BR64.5`）四道檢查 | ① 本單元新增模組對 `llm_provider`、`openai`、`langchain`、`langgraph` 的 import 數為 0（grep）。② 四類違規各一案（超大訊框、超頻、超長、攔截命中）：`classify` 替身被呼叫 0 次 |

## 三、刻意不設的目標（附理由，不留空白）

| 不設 | 理由 |
|---|---|
| 單元層的絕對延遲單元測試（如「一輪 ≤ N ms」的計時斷言） | 計時斷言在 CI 共用 runner 上不穩定；本站以 `NFR13.2`、`NFR13.4`、`NFR13.5` 的**結構性**判準（不等待、離開迴圈、不排隊）保證不破壞預算，P50 的實測落 `build-and-test` |
| `U12` 的 `dispatch` 內部預算 | `U12` 已以 `NFR12.1` 承諾不等待能力；`dispatch` 前段的耗時併入 `NFR13.1(b)` 計量，不另切 |
| 吞吐量（每秒訊息數） | 訊息來源是人在頁面上打字與點選；上界由 `NFR13.20` 的頻率限制給出，無上游流量數據支撐吞吐目標 |
