# 技術選型 — `U13 brain-gateway`

## 〇、零新套件

全部沿用既有技術棧（`project.md ## Tech Stack`、`team.md ## Testing Posture`）：

| 層 | 選擇 | 依據 |
|---|---|---|
| WebSocket 端點 | FastAPI `APIRouter.websocket("/ws")`，`main.py` 以 `prefix="/api/brain"` 掛載 | `BR61.1`；FR8.3 |
| 同步呼叫離開迴圈 | `asyncio.to_thread`（第 1–9 項）；嵌入工作走 `concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="brain-memory")` ＋ `asyncio.wait_for` | `BR67.5`、`BR67.12`；`NFR13.4`、`NFR13.5` |
| 記憶預取傳遞 | `contextvars.ContextVar`（依 task 隔離） | `BR67.10` |
| 送出序列化 | 每連線一把 `asyncio.Lock` | `BR63.4` |
| 頻率限制 | 行程內滑動窗（每 session key、每連線各一個 `collections.deque` 時間戳），**不用** Redis。契約端點三問：寫＝每則入站訊框；讀＝`NFR13.20` 的檢查；清＝每次檢查時剔除窗外時間戳，連線關閉時刪除其 deque、該 key 的最後一條連線移出登錄時刪除 key 的 deque（與 `BR63.1`「集合為空即刪鍵」同一時點） | 單一行程假設下行程內即正確；用 Redis 會把每則訊息多一次往返加進 `NFR13.1(a)` 的預算 |
| 訊息形狀 | 一律以 `brain_ws_contract` 的 Pydantic 模型建構與驗證 | `BR65.4`；承接 `NFR5` |
| 測試 | `unittest` ＋ `hypothesis` ＋ `starlette.testclient.TestClient.websocket_connect`；Redis 用既有 `FakeRedis`／`WorkItemFakeRedis`、時鐘用 `FakeClock`；**非 pytest** | `team.md ## Testing Posture`；`requirements.txt` 已含 `httpx`（`:11`）、`hypothesis`（`:30`）、`redis`（`:49`） |

## 一、決定

| id | 決定 | 二元判準 |
|---|---|---|
| **`NFR13.39`** | 本單元**不新增任何套件**（無 `fakeredis`、無 `pytest`、無限流套件、無 WebSocket 客戶端套件） | `git diff` 下 `backend/requirements.txt` 與 `frontend/package.json` 的 dependencies 區段無新增行 |
| **`NFR13.40`** | 本單元送出的每一則訊息先通過 `brain_ws_contract` 對應模型的驗證；驗證失敗不送（`BR65.4`）——契約閘門只比對型別定義，手組 dict 會讓閘門對本單元無效（承接 `NFR5`） | 測試的送出替身對收到的每則訊息做 `WsEnvelope.model_validate`：走完 `NFR13.4` 的全路徑，全部通過；本單元模組內不出現以字面 `"type":` 組訊息的 dict（grep 為 0） |
| **`NFR13.41`** | （承接 `NFR5`）契約增量 C-1～C-7（`functional-spec.md` §十一，`:459-467`）依序落地：六個模型加欄位且每欄有 `description`；`dump_ws_contract.py` 的 `CLIENT_FIELD_WHITELIST` 同步；重產 `ws-contract.json` 與 `frontend/src/types/ws-contract.d.ts`；`test_ws_contract.py` 改五處並新增 `protocolName` 負向案例（§十一之二第 5 點）。**前置關卡**：`ADR-0020` 取得使用者核可之前，依賴它的規則（`BR61.2` 協定名部分、`BR62.5`、`BR63.2` 兩則狀態訊息、`BR63.3`、`BR66.1`、`BR66.2`）不得合併（`OPEN-GW13-1`） | ① CI 的 `python scripts/dump_ws_contract.py --check`（`ci.yml:300`）與 `npm run check:ws-types`（`ci.yml:219`）皆綠；② `backend/tests/test_ws_contract.py` 與 `test_dump_ws_contract.py` 全綠；③ `inception/decisions/` 下存在 `0020-*.md` 且其核可紀錄早於含 C-1～C-7 的 commit；④ 突變驗證：只改模型不重產 `ws-contract.json` → ① 紅燈 |
| **`NFR13.42`** | 五個純函式的 property-based 測試（`functional-spec.md` §七，`:357-369`）：性質一 `parse_subprotocol_offer`、性質二 `session_key_for`、性質三 `TurnLedger`、性質四 `resolve_segment`、性質五 `scan_targets_in_utterance`（**以 `NFR13.28` 改寫後的版本**）；`error_for` 與 `match_referent` 以 example-based 覆蓋。**定位**：ADR-0006 的 PBT hard constraint 落點是 agent routing（`U11`），本單元判 N/A（非豁免）；本條是本站對單元的要求，不是 hard constraint 的承接 | 五個函式各有至少一個 `@given` 測試；性質五的三條（a）（b）（c）各自獨立斷言；突變驗證見 `NFR13.28` ① |
| **`NFR13.43`** | （帶入項 6；`project.md ## Mandated` 的 `LOCAL-DEV.md` 同步）本單元使 `REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD` 成為**後端啟動的必要條件**（`NFR13.32`），而 `LOCAL-DEV.md:23` 目前把 Redis 寫成「session 相關功能不可用」的降級依賴——在本單元合併後這句為假。同一 PR 必須：① 改寫 `LOCAL-DEV.md:23` 的 Redis 列為「後端啟動本身（U13 起）」的必要條件，並寫明三個變數缺值或 `REDIS_USER=default` 即拒絕啟動、Redis 暫時不可達**不**阻止啟動而在入口頁握手時以 1011 呈現；② 於同表「後端啟動本身」各列（`:24-25`）之後補上 U13 的啟動拒絕條件；③ 同檔 `:79` 的註解「沒有它，大腦編排的 session 相關功能不可用」同為降級敘述，一併改寫 | ① `LOCAL-DEV.md` 內「session 相關功能不可用」的出現次數為 0，且含 `REDIS_USER=default` 字串；② 該 PR 的 diff 同時含 `backend/main.py` 與 `LOCAL-DEV.md` |
| **`NFR13.44`** | 本站定的數值（`NFR13.17` 200、`NFR13.18` 10、`NFR13.19` 65536、`NFR13.20` 20／120、`NFR13.22` 256，以及 functional-design 的 10 秒 hello、60 秒重驗、3／15 秒等待、30 秒熔斷、4 條執行緒）一律為**模組常數**，**不新增環境變數**——避免 `NFR8` 的三處同步義務（`render-env.sh`、`deploy/.env.example`、`backend/.env.example`）與 `validate_env_contract.py` 的記載要求；日後若任一值需要可調，同一 PR 依 `NFR8` 同步三處並更新 `LOCAL-DEV.md` | ① 本單元模組讀取的環境變數名稱集合 ⊆ {`REDIS_URL`, `REDIS_USER`, `REDIS_PASSWORD`}（grep `os.environ`／`os.getenv` 的引數；這三個是既有變數，startup 建立 Redis client 時讀取，見 `functional-spec.md:201`）；② `python3 scripts/validate_env_contract.py` 綠 |

## 二、刻意不採用

| 不採用 | 理由 |
|---|---|
| 調低 uvicorn 全域 `--ws-max-size` | 會打壞 `collab_router` 的架構圖 XML 傳輸（`collab_router.py:33` 上限 2 MiB）；改以應用層檢查（`NFR13.19`） |
| 以 Redis 實作頻率限制或連線計數 | 單一行程假設下多一次往返而無收益；多行程時扇出本身已失效（`NFR13.33`），限流跨行程一致也救不了 |
| 為 WebSocket 新增關閉碼（如額滿 4429、訊框過大 1009） | 新關閉碼是契約增量，須擴大 `ADR-0020`；以「不 accept」與既有 `INVALID_REQUEST` 句型承載（`NFR13.17`、`NFR13.19`），代價已於 `scalability-requirements.md` 揭露 |
| `pytest`、`fakeredis` | `team.md`：backend 測試為 `unittest`；既有 `FakeRedis` 已涵蓋本單元需要的指令 |
