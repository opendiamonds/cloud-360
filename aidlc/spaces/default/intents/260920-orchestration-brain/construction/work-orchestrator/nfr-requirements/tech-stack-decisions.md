# 技術選型 — `U12 work-orchestrator`

## 〇、零新套件

全部沿用既有技術棧（`codekb/chiton/technology-stack.md`、`team.md`）：

| 層 | 選擇 | 依據 |
|---|---|---|
| 對既有能力的呼叫 | `httpx.AsyncClient` ＋ `ASGITransport(app=…)` | `BR51.1`；`httpx` 已在 `requirements.txt:11` |
| 工作項儲存 | `U10` 的 `SessionStore` 新增三個方法；兩支 Lua 腳本 `put_work_item.lua`、`update_work_item.lua` 放 `backend/services/session_scripts/`，經 `RedisGateway.eval_script` 執行 | `BR52.4`／`BR52.7`；與既有 `append_message.lua`、`switch_to_isolated.lua` 同處 |
| 背景執行 | `asyncio` task ＋ `asyncio.wait_for`；在途存檔的收尾以 `asyncio.shield` 保護（帶入項 1） | `BR56.6`、`NFR12.20` |
| 同步 facade | `asyncio.to_thread` ＋ 每次呼叫自開 `SessionLocal` | `BR51.7`、`NFR12.2` |
| WebSocket 訊息形狀 | 一律以 `brain_ws_contract` 的 Pydantic 模型（`WorkItem`、`WorkItemsPayload`、`TokenPayload`、`CostCardPayload`）建構 | 承接 `NFR5`：契約是前後端的單一來源，本單元不手寫訊息 dict（`NFR12.27`） |
| 測試 | `unittest` ＋ `hypothesis`（純函式 PBT 與 stateful 模型測試）＋ 經真實 app 的同進程呼叫；**非 pytest** | `team.md ## Testing Posture`；ADR-0006 PBT hard constraint |

## 一、決定

| id | 決定 | 理由 |
|---|---|---|
| **`NFR12.27`** | 本單元送出的每則訊息都先通過 `brain_ws_contract` 對應模型的驗證（承接 `NFR5`） | 契約閘門只比對型別定義；若本單元繞過模型手組 dict，閘門對它無效 |
| **`NFR12.28`** | PBT 落點為四個不讀 IO 的純函式：`transition`、`plan_waits`、`side_effect_on_stop`、`on_dependency_stopped`，加上 `NFR12.12` 的 stateful 模型測試 | ADR-0006 點名 agent routing；functional-spec 第七節 |
| **`NFR12.29`** | 以一個測試鎖住「ASGI 傳輸收齊才交回」這個假設對本單元無害：A1／A3 的判定以完整回應本體進行，不依賴中途事件 | `httpx` 在 `requirements.txt` 未釘版（`review-02` R-02 的附註）；若未來版本改為真串流，本單元的判定仍須正確 |

**判準**：`NFR12.27` — 測試替身 sink 對每則收到的訊息做 `model_validate`，全部通過；`NFR12.28` — 四個函式各有 `@given` 測試，`NFR12.12` 有 `RuleBasedStateMachine`；`NFR12.29` — 以一次性回傳完整 SSE 本體的替身跑 A1／A3 成功與失敗各一案，判定正確。

## 二、刻意不採用

| 不採用 | 理由 |
|---|---|
| 讀 C1 的 `/advice/stream` | ASGI 傳輸緩衝，中途事件收不到；改輪詢快照（`BR57.1`） |
| 任務佇列（Celery、RQ 等） | 新增依賴與新進程；每項有牆鐘上限、重啟由復原掃描處理，不需要持久化佇列 |
| 釘選 `httpx` 版本 | 屬全專案依賴政策（`team.md`：多數套件未 pin），不由單一單元決定；以 `NFR12.29` 的測試降低風險 |
