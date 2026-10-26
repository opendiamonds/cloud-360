# Code Generation Plan — `U12 work-orchestrator`

> 本計畫把四站設計（functional-design 修訂 2、nfr-requirements、nfr-design、infrastructure-design）落成程式，
> **並一併處置三次審查帶下來、經使用者 2026-10-12 三次裁決帶進程式產生的 26 項殘留**（§二）。
> 方法論依下方 Testing Contract 為 `test-after`。

## 一、交付範圍

| # | 交付 | 位置 | 類型 |
|---|---|---|---|
| 1 | 兩支 Lua 腳本（建項、比對後以補丁合併寫入） | `backend/services/session_scripts/put_work_item.lua`、`update_work_item.lua` | 新建 |
| 2 | Lua 的 Python 參考實作（供替身與一致性測試） | `backend/services/session_types.py` 增 `ref_put_work_item`、`ref_update_work_item` | 修改（`U10` 跨單元） |
| 3 | 工作項儲存方法 | `backend/services/session_store.py` 增 `load_work_items`、`put_work_item`、`update_work_item` | 修改（`U10` 跨單元） |
| 4 | 系統下的圖 | `backend/services/hierarchy_facade.py` 增 `list_diagrams_of_system` | 修改（`U7` 跨單元） |
| 5 | 純函式與句型 | `backend/services/work_orchestrator_rules.py`：`transition`、`plan_waits`、`side_effect_on_stop`、`on_dependency_stopped`、目標圖判定、`PHRASES` 常數表 | 新建 |
| 6 | 呼叫既有能力 | `backend/services/work_orchestrator_capabilities.py`：`CapabilityClient`（ASGITransport 帶使用者 token；A1／A3 收齊 SSE 後解析；C1 列表、快照） | 新建 |
| 7 | 編排器 | `backend/services/work_orchestrator.py`：`WorkOrchestrator`（`dispatch`／`correct`／`list_items`、`_run`、`_finish_persist`、`_recover`、`_advance`、`_emit`） | 新建 |
| 8 | 測試 | `backend/tests/test_work_orchestrator_*.py`；`backend/tests_redis/test_work_item_lua.py`（opt-in，需真 Redis） | 新建 |
| 9 | 文件與追溯 | `code-summary.md`、`traceability.json`、`source-manifest.json` | 新建 |

**零新依賴、零新環境變數、零新 HTTP 端點、零 DDL。** 不觸發 `schema_rbac.sql`／`DEPLOY.md` 同步。
`U10`／`U7` 的三處跨單元修改與本單元同一次合併（`infrastructure-design` 第二節：不得拆分）。

## 二、併入本計畫的審查殘留（使用者裁決：帶進 code-generation）

來源縮寫：FD＝functional-design `review-03`；NR＝nfr-requirements `review-01`；ND＝nfr-design `review-01`。編號為帶入清單序號。

| # | 來源 | 問題 | 本計畫的處置 | 步驟 |
|---|---|---|---|---|
| 1、11、18、23 | FD R-10；NR R-05；ND R-01、R-06 | 在途存檔被 `correct` 或逾時取消後遺失結果與變更紀錄 | `_finish_persist` 以 `asyncio.shield` 包住，**自建獨立的 `AsyncClient`**（不共用 `_run` 的）、自有最外層 `except` 與 PUT 逾時上限（60 秒）；依 `reliability-design.md` 第二節的四列對照收尾，含「已被逾時判失敗後 PUT 才成功」 | 7、8 |
| 2 | FD R-11 | 兩個復原掃描同時推進同一孤兒，重複啟動 | 所有推進共用 `_advance`：只有寫入回 True 才建 task、送訊息 | 7、8 |
| 3、12 | FD R-12；NR R-06 | 先送後記，`sideEffect` 誤報 none | 每個請求前先以比對後寫入記下 `request_sent`／`persisting`，成功才送 | 7、8 |
| 4、7、24 | FD R-13；NR R-01；ND R-07 | 過期值覆寫 `estimateSetId`；重試語意；補丁細節 | Lua 收**補丁**、腳本內合併；補丁中值為 JSON `null` 即設為 null，未出現的欄位不動；以 `cjson.decode_array_with_array_mt` 保留空陣列；`eval_script(..., idempotent=False)`（傳輸層不重送）；`correct` 的比對失敗重讀重算上限 5 次，超過即記 WARNING 並回現況 | 1、2、3 |
| 19 | ND R-02 | 非冪等寫入遇連線錯誤時結果未知 | `_advance` 第三分支：捕捉 `SessionBackendUnavailable` → 重讀該項，若已是目標狀態與 `dispatchStage` 視為成功；讀不到則不做副作用、記 WARNING | 7、8 |
| 5、10 | FD R-14；NR R-04 | 停用判定與存回後失敗的矛盾；測試分辨不出有無重鑄 | `_call_facade` 自寫停用判定（`mint_principal` 不查 `is_active`）；存回前停用 → 失敗；存回後 → 依 `BR51.4`／`BR51.5` 的 violation_behaviour。測試在「PUT 成功後、寫變更紀錄前」停用 | 7、8 |
| 6、8 | FD R-15；NR R-02 | 欄位清理、`sideEffect` 對照、句型 | 推進為處理中的補丁同時寫 `deadlineAt`、清 `waitingOn`／`dependsOn`；離開處理中的補丁含 `deadlineAt=null`；`side_effect_on_stop` 為唯一對照（`persisting` → 「可能已存回架構圖〈名稱〉」），`BR55.1`／`BR56.6`／`BR56.7` 三處皆呼叫它；`PHRASES` 收齊 `BR58.1` 全部句型含「〈label〉沒有執行：前一項〈label〉已停掉」，每個句型一案 | 5、6、7、8 |
| 9 | NR R-03 | Lua 原子性在替身上驗不到 | `tests_redis/test_work_item_lua.py`：以 `REDIS_URL` 連真 Redis，未設定即 skip 並印原因；對兩支腳本與參考實作跑同一組案例比對。**不是 CI 閘門**（`ci.yml` backend job 無 Redis），在 `code-summary.md` 如實揭露 | 3、4 |
| 13、20 | NR R-07；ND R-03 | 時鐘不可控、`wait_for` 用另一個時鐘 | 建構子注入 `clock` 與 `sleep`；三種能力的牆鐘上限一律以 `clock() >= deadlineAt` 自行判定（每次 await 能力呼叫以 `sleep` 切片輪詢完成與否），不用 `asyncio.wait_for`；輪詢計數規則：每次快照 GET 計一次 | 7、8 |
| 14、21 | NR R-08；ND R-04 | import 檢查可被繞過 | `test_work_orchestrator_boundaries.py`：以 `ast` 掃本單元三個模組的 `import`／`from … import`，禁止清單含 `main`、`cost.estimate_intake_service`、`cost.advice_orchestrator`、`services.design_agent`、`services.review_orchestrator`、`services.collab_router`、`services.llm_provider`，並禁止 `importlib`／`__import__`；另以 patch `httpx.AsyncClient.send` 斷言所有請求的 transport 皆為 `ASGITransport` | 8 |
| 15 | NR R-09 | `requestText` 靜態加密承接 | 不實作加密（併入上游 `OQ-3`）；`code-summary.md` 交接表寫明承接鏈 `nfr-design`（CONDITIONAL）→ `infrastructure-design` → `code-generation` | 9 |
| 16 | NR R-10 | 契約承接只測 sink | 生產路徑：`_emit` 對每則訊息先以 `brain_ws_contract` 對應模型 `model_validate` 再交給 sink；測試以會拒絕非模型輸入的 sink 驗證 | 7、8 |
| 17 | NR R-11 | 邊界案例 | token 出現在例外訊息的案例；401／403 不重試、輪詢 404 的案例 | 8 |
| 22 | ND R-05 | `SessionLocal` 不可注入；`list_diagrams_of_system` 未交付 | 建構子注入 `session_factory`（預設 `database.SessionLocal`）；交付 #4 | 3、7 |
| 25 | ND R-08 | 對 functional-design 的偏離未揭露 | `code-summary.md` 揭露：`BR55.7` 延伸至逾時失敗項；重啟後 `persisting` 孤兒無法補寫變更紀錄（圖可能已改而無紀錄）的稽核缺口 | 9 |
| 26 | ND R-09 | traceability 落點 | 本站 `traceability.json` 以 `NFR12.x` 對到實際測試檔；帶入項 7–17 的落點即本表 | 9 |
| — | FD／NR 回報 | functional-design 文字待回補 | `code-summary.md` 列 `OPEN-WO12-9` 的三處文字回補；`OPEN-WO12-6`／`OPEN-WO12-7`（`AC10.2.4`、`AC1.3.2`、`AC5.1.3`）交使用者裁決 | 9 |

## 三、步驟（`test-after`：逐層實作後補該層測試）

- [x] **Step 1 — 結構骨架**：建 `backend/tests_redis/`（含 `__init__.py`，說明 opt-in 與 skip 條件）；不建空的實作檔。
- [x] **Step 2 — 驗證執行器並記錄本單元指令**：執行 `unit-test-instructions.md §二` 的就緒檢查（以既有 `tests.test_session_store_behaviour` 確認 `unittest` 與 Redis 替身可載入）。
- [x] **Step 3 — 資料模型：實作**：交付 #1、#2、#3（Lua 與參考實作、`SessionStore` 三方法，key 不存在即拒絕、不改 TTL）；#4（`list_diagrams_of_system`：`_authorize(view)` ＋ `assert_system_owned_by`，回 `(diagram_id, title)` 清單）。
- [x] **Step 4 — 資料模型：測試**：`test_work_orchestrator_store.py`（替身）：建項成功與重複拒絕、key 不存在拒絕且不建 key、比對 status 與 `dispatchStage`、補丁只改指定欄位（`estimateSetId` 不被清）、null 語意、空陣列保留、TTL 不變；`list_diagrams_of_system` 的擁有者、非擁有者、零張三案。`tests_redis/test_work_item_lua.py`（opt-in）。
- [x] **Step 5 — 資料存取（能力呼叫）：實作**：交付 #6。每次呼叫新建 `AsyncClient(transport=ASGITransport(app))`；SSE 本體解析（A1 `message`／`xml`／`error`；A3 `complete`／`error`）；C1 列表翻頁與快照；例外只保留類別名與狀態碼。
- [x] **Step 6 — 資料存取：測試**：`test_work_orchestrator_capabilities.py`：以一次回傳完整 SSE 本體的替身 app 驗 A1／A3 成功與各失敗（`NFR12.29`）；401／403／5xx 對應；翻頁找到即停（`NFR12.4`）；快照 `generating` 且 `started_at` 逾 5 分鐘判逾時；token 不出現在例外與 log。
- [x] **Step 7 — 業務邏輯：實作**：交付 #5、#7，涵蓋 `BR51`–`BR58` 與 §二 全部處置；logger `"cloud360.work_orchestrator"`，log 形狀依 `observability-design.md`。
- [x] **Step 8 — 業務邏輯：測試**：
  - `test_work_orchestrator_rules.py`：四個純函式的 `@given` 性質（`NFR12.28`），每個 `PHRASES` 句型一案。
  - `test_work_orchestrator_model.py`：`RuleBasedStateMachine`，規則含「背景推進 `dispatchStage`」「寫 `estimateSetId`」「`correct`」「復原掃描」「被等待者轉終態」，不變量 (a)–(e)（`scalability-design.md` 第三節）。
  - `test_work_orchestrator_flow.py`：交辦先回覆（`NFR12.1`）、`to_thread`（`NFR12.2`）、輪詢上限（`NFR12.3`）、等待與 `BR53.4` 分流、`correct` 與背景交錯、在途存檔四列、逾時、復原掃描兩步與併發只啟動一次（`NFR12.13`）、寫入結果未知、sink 失敗、不重試、停用判定兩案、token 與原句不入 log 與 Redis。
  - `test_work_orchestrator_boundaries.py`：§二 第 14、21 項。
  - `test_work_orchestrator_authz.py`：經真實 app（ASGITransport＋測試 DB）的 allow／deny 雙向：A1 有／無權限、C1 有／無權限、token 過期（`NFR12.7`）。
- [x] **Step 9 — API**：本單元**無 HTTP 端點**（入口為 `U13` 的 WebSocket），`openapi.json` 不變；以 `dump_openapi.py --check` 確認未漂移。Frontend 層無程式，省略。
- [x] **Step 10 — 突變驗證**：依 `unit-test-instructions.md §四` 逐項套用 → 確認紅 → 還原 → 確認綠，結果記入 `code-summary.md`。hypothesis 測試在突變執行時以環境變數關閉 shrinking（避免長時間卡住）。
- [x] **Step 11 — 環境／建置設定**：零新環境變數；`python3 scripts/validate_env_contract.py`、`python3 scripts/validate_repo_contract.py` 通過。
- [x] **Step 12 — 文件與追溯**：`code-summary.md`（§二 的揭露與交接、`OPEN-WO12-6`／`-7`／`-9`、`tests_redis` 不在 CI）；`source-manifest.json`；`traceability.json`。

## 四、步驟 ↔ 故事追溯

| 故事／AC | 步驟 |
|---|---|
| `AC1.1.1`、`AC5.1.1`（一個意圖一個工作項、標示能力） | 7、8 |
| `AC1.1.2`（狀態轉換） | 5、8 |
| `AC1.1.4`、`AC10.1.1`（目標圖與估價表解析） | 3、5、7、8 |
| `AC1.3.1`、`AC1.3.3`（逐項更正、`sideEffect`、請使用者再說一次） | 7、8 |
| `AC5.1.2`（等待中） | 7、8 |
| `AC10.1.2`、`AC10.1.3`、`AC10.2.1`、`AC10.2.2`（成本輪詢、卡片、逾時與失敗可分辨） | 5、6、7、8 |
| `AC10.1.5`（權限不足） | 6、8 |
| `AC10.2.3`（先回覆後執行） | 7、8 |
| `AC1.3.2`、`AC5.1.3` | 行為依 `BR53.4` 實作（Step 7、8）；AC 字面為 Deferred，交使用者裁決（`OPEN-WO12-7`） |
| `AC10.2.4` | Deferred，交使用者裁決（`OPEN-WO12-6`）；本計畫不另造稽核事件 |

## 五、方法論與 contract 基線的對應

Testing Contract 的 14 步基線中：**Data model**（Step 3–4，Redis 工作項與 Lua）、**Repository / data access**
（Step 5–6，對既有能力的呼叫）、**Business logic**（Step 7–8）依序「實作 → 測試」；**API** 層本單元無端點
（Step 9 只做漂移確認）；**Frontend** 層無程式，省略。方法論未改。

## 六、code-generation Request Changes（2026-10-20）：合併前必修第 18 項的工作項那一半

使用者對整站送出 Request Changes，要求修正 `construction/functional-design/merge-blockers.md` 的 19 項。劃給本單元的是**第 18 項**（與 `session-store` 共有）。`session-store` 已在 2026-10-23 處理對話那一半，每段上限 200 KB；該列逐字寫明「**不在本上界內**：同 key 的 `U12` 工作項集合（`OPEN-N10-3`），`work-orchestrator` 那一半的容量未由本項處理」。

**實測現況（以唯讀查證取得）**：
- `put_work_item.lua` 只檢查 key 是否存在、欄位是否已存在，**沒有任何筆數上限**，全 `backend/services` 也沒有刪除 `wi:*` 欄位的路徑。
- 每則請求最多產生 3 筆（`work_orchestrator_rules.CAPABILITY_NAMES` 三種能力）。每筆最大約 7.5 KB：`requestText` 上限 2000 字（`REQUEST_TEXT_MAX_CHARS`），`ensure_ascii=False` 下中文約 6 KB，其他欄位約 1.5 KB。
- 工作階段 TTL 會隨使用者互動續期（`session_store.py` 的 `touch` 與各寫入方法），所以活躍的工作階段裡，工作項會無上限累積。
- 容量帳：`maxmemory 256mb` 的 80% ≈ 214.7 MB，除以 300 個工作階段 ≈ 699 KiB／個；扣掉對話最壞值 3 × 200 KiB = 600 KiB，剩約 **99 KiB** 給工作項。

**使用者裁決**（本站問題檔 `[WO-MB18]`）：**限筆數＋完成後瘦身**。
- 同時進行中（處理中＋等待中）最多 **5 筆**。
- 已結束（完成、失敗、已停掉）只保留最近 **20 筆**。
- 轉為已結束時，`requestText` 截成 **200 字**（`CHANGE_SUMMARY_MAX_CHARS`，變更摘要本來就只取這個長度）。
- 最壞值：5 × 7.5 KiB + 20 × 約 2.1 KiB ≈ **80 KiB**，低於 99 KiB，300 個工作階段的承諾成立。

- [x] **Step 13 — 資料模型：實作**
  - 新常數 `work_orchestrator_rules.MAX_ACTIVE_WORK_ITEMS = 5`、`MAX_TERMINAL_WORK_ITEMS = 20`（模組常數，非環境變數）。
  - **`put_work_item.lua`**：新增 `ARGV[3]`（進行中上限）。腳本內以 `HGETALL` 解碼 `wi:*`，計算 `status` 不屬於三種終態的筆數；已達上限即回 **`-1`**，不寫入。key 不存在或欄位已存在仍回 `0`。
  - **`update_work_item.lua`**：新增 `ARGV`（已結束保留數）。補丁使該項**由非終態轉為終態**時，腳本依 `createdAt`（同值再以欄位名，決定性）刪除超出 20 筆的最舊終態欄位（`HDEL`）。只刪終態項，不碰進行中項。
  - **參考實作**：`ref_put_work_item`／`ref_update_work_item` 同語意更新。
  - **`SessionStore`**：`put_work_item` 改回三值：已寫入／已到期或重複／已達上限，形狀由實作決定，但呼叫端必須能區分第三種。
  - **`requestText` 截斷**：在 Python 端做（`WorkOrchestrator` 送出轉終態的補丁時一併帶 `"requestText": text[:CHANGE_SUMMARY_MAX_CHARS]`），**不在 Lua 以位元組截斷**，避免切壞 UTF-8。
- [x] **Step 14 — 資料模型：測試**
  - `test_work_orchestrator_store.py`（替身）：第 6 筆進行中被拒且不寫入、終態項不計入上限、轉終態後超過 20 筆刪最舊、進行中項永不被刪、同 `createdAt` 的刪除順序決定性、key 不存在仍回原值。
  - `tests_redis/test_work_item_lua.py`（opt-in）：Lua 與參考實作逐案比對上述案例。
  - 以 `hypothesis` 加一條性質：任意交辦與轉終態序列後，進行中 ≤ 5 且終態 ≤ 20。
- [x] **Step 15 — 業務邏輯：實作**
  - `dispatch` 在寫入任何一筆**之前**，先以 `load_work_items` 計算「現有進行中＋本批筆數」，超過 5 即丟新例外 `WorkCapacityExceeded`，**整批不寫**，避免一則請求只建了一半。
  - 若預檢通過後 Lua 仍回「已達上限」（同一工作階段的併發交辦），把本批已寫入的項以補丁轉為 `失敗`，`failureReason` 為固定字串；再丟 `WorkCapacityExceeded`。
  - 所有轉終態的補丁帶截斷後的 `requestText`。
  - **跨單元（`U13 brain-gateway`）**：`brain_gateway_rules.error_for` 把 `WorkCapacityExceeded` 對應到既有代碼 `INVALID_REQUEST`（**不改 WS 契約**的 `code` 列舉）。訊息為固定字串「目前進行中的工作已達 5 項，請等其中一項完成後再交辦。」，經 `brain_gateway.py:1521` 既有的 `_fail_turn_exc` 送出。
- [x] **Step 16 — 業務邏輯：測試**
  - `test_work_orchestrator_flow.py`：已有 4 筆進行中時交辦 2 個意圖 → 整批拒絕、Redis 無新欄位、回 `WorkCapacityExceeded`；併發交辦下 Lua 回上限 → 已寫入的同批項轉 `失敗`；轉終態後 `requestText` 長度 ≤ 200。
  - 閘道測試：`WorkCapacityExceeded` → `INVALID_REQUEST`，加上固定訊息。
  - 突變驗證（記入 `code-summary.md`），每項都要讓對應測試轉紅：
    - 拿掉 Lua 的上限檢查；
    - 拿掉 `dispatch` 的預檢；
    - 拿掉終態刪除；
    - 刪除改成刪進行中項；
    - 拿掉 `requestText` 截斷。
- [ ] **Step 17 — 文件與追溯**
  - **容量說明**：`DEPLOY.md` 與 `LOCAL-DEV.md` 的 Redis 容量段、`deploy/.env.example` 與 `backend/.env.example` 的容量註解改寫為「對話 600 KiB＋工作項 80 KiB／工作階段」，300 個工作階段 ≈ 199 MiB ≈ 78%。
  - **合併前必修清單**：`merge-blockers.md` 第 18 列標為已修正。
  - **其他文件**：`code-summary.md` 新增一節；`traceability.json` 與 `source-manifest.json` 更新。
  - **驗證**：`validate_env_contract.py` 與 `validate_repo_contract.py` 通過，`dump_openapi.py --check` 不漂移。

**不在本次範圍**：`requestText` 靜態加密（§二 第 15 項，仍併入上游 `OQ-3`）；前端工作清單如何顯示「只保留最近 20 筆」（工作清單由 `U14` 消費，本次只在 `code-summary.md` 交接）。

## Testing Contract

```json
{
  "version": 1,
  "methodology": "test-after",
  "source": "fallback",
  "ordering": "Implement each testable layer, then write and run that layer's tests.",
  "scope": "agent-orchestration-brain",
  "test_strategy": "standard",
  "project_type": "brownfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. Specific\nmethodology — TDD, BDD, ATDD, or classic test-after — is captured by the\ntesting-strategy stage when it ships.\n\nUntil then, our default per scope is:\n- `mvp`, `enterprise`, `feature`, `infra` → tests written alongside\n  code; minimum 80% line coverage; tests run in CI before merge.\n- `bugfix`, `security-patch` → regression test for the specific\n  bug/vulnerability; existing test suite must remain green.\n- `poc`, `refactor`, `workshop` → existing test suite remains green;\n  no new test floor required.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "### 既成事實\n\n- **Backend 測試框架**為 Python 內建 `unittest` + `hypothesis` + `unittest.mock`，**未使用 pytest**。CI 以 `python -m unittest discover -s tests -v` 執行（`ci.yml`）。測試 DB 策略見 `backend/tests/helpers.py`：在任何 DB import 前 `sys.modules.setdefault(\"psycopg2\", MagicMock())`，改走 in-memory SQLite，每 session `ensure_role_permissions_seeded(db, force=True)`。規模：`backend/tests/` 21 個測試檔（HEAD `c3de2c8`；2026-08-06 版「14 個」已過時）。\n- **Frontend e2e** 為 Playwright（chromium 單一 project），涵蓋登入與 RBAC 可視性；`ui-regression` gh-aw workflow 每 PR 對短生命週期 stack 執行並回報 Kiwi TCMS。**這是真閘門**：`post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`；容忍 `stats.flaky`，`retries: 1`。HEAD 現有 e2e 涵蓋 Admin 最後活動與分頁，**無成本頁 e2e**。\n- **Frontend 完全沒有 unit／component 測試框架**：`frontend/package.json` 的 `devDependencies` 只有 `@playwright/test`，無 vitest、無 jest、無 `@testing-library/*`；`scripts` 只有 `test:e2e`。前端的唯一自動化驗證層就是 Playwright e2e。\n- **Property-based testing**：7 個檔共 13 個 `@given`（HEAD `c3de2c8`；覆蓋 `test_design_agent`、`test_wa_rule_engine`、`test_diagram_builder`、`test_diagram_icons`、`test_collab`、`test_auth`、`test_activity`），皆落在純函式模組，屬自發良好實踐。`project.md` ADR-0006 點名的三個 hard-constraint 落點（IaC generator、cost calculator、agent routing）中，**cost calculator 在本 repo 尚無對應實作模組**，故該約束目前對 repo 現況為 N/A（非豁免、非違反）。本 intent 若新建 calculator 模組，ADR-0006 PBT 約束隨即由 N/A 轉為 blocking。\n- **HTTP 層 TestClient 現況**：`backend/tests/test_user_list_endpoint.py` 用 `starlette.testclient.TestClient` 測 `/api/auth/list` 分頁欄位（樣板在 `tests/helpers.py`）。此為現行唯一 TestClient 使用例；**無 cost router 可測**。\n- **C1 / pricing 測試完全缺席**：無 `test_cost*`；`'C1'`／`\"C1\"` 在 `backend/tests/` 0 命中；`test_rbac.py` 不覆蓋 C1／C2／C3。WA `COST-*` findings 連 example-based 測試都沒有。\n- **完全沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）。`org.md` 宣告的「最低 80% line coverage」目前**既無法量測也無法強制，是宣告而非閘門**。\n- **既有授權測試皆在 service 層**：`test_rbac.py`、`test_j5_authz.py`、`test_review_authz.py` 皆非 HTTP 層測試。\n\n### 本輪新增規則（Q4 定案：A + B + C，D 不採）\n\n依據：本 intent 的六道現有 CI 閘門（`repo-contract`、frontend lint、`tsc -b`、backend import smoke、backend `unittest`、`ui-regression`）逐一查證後，**對「後端漏欄位、序列化成 null、前端渲染成空白」這條失敗路徑全部無效**——不是覆蓋率不足的程度問題，是這條變更路徑上沒有任何自動化斷言存在的有無問題。三項零新依賴的測試底線本輪起生效：\n\n- **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 `role_permissions` 預設值變更，必須有測試同時驗證「該角色能做到」與「其他角色做不到」。零新依賴，直接擴充既有 `test_rbac.py`／`test_j5_authz.py` 形狀。C1 的 RBAC seed 種子已存在（`FinOps_Analyst` 與 C1 相關欄位）；若本 intent 改動 C1 預設值（例如讓架構師 edit 時數），屬 seed 變更，須 A 規則測試。\n- **B — 新增或修改 HTTP 端點需 `TestClient` 測試**：斷言其 status code 與 `response_model` 的欄位集合。採用成本為零——`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，`starlette.testclient.TestClient` 前置條件已滿足；新測試檔放進 `backend/tests/` 即被現有 `python -m unittest discover -s tests` 撿到；`get_db`（`database.py:31`）與 `get_current_user`（`services/auth.py:39`）為穩定的模組層函式，可用 `app.dependency_overrides` 覆寫；以 `TestClient(app)` 直接使用不觸發 `@app.on_event(\"startup\")` 的 `init_db()`，不需要真實 DB。C1 若新增 `/api/cost*` 端點，須依 B 規則補 TestClient 測試，且 CI 的 OpenAPI drift 檢查會要求同步更新 `openapi.json`。\n- **C — 前端資料形狀變更需 e2e 斷言**：例如本次 Admin 表格加欄，須新增至少一個 Playwright case 斷言表頭出現該欄位、且至少一列顯示值或既定的「從未」佔位。用既有 Playwright，不需新依賴，且是目前**唯一**能碰到前端頁面的自動化層。C1 若新建 Cost 頁，資料形狀為全新，須 C 規則 e2e 斷言。\n- **D（不採用）— 引入前端 unit／component 測試框架**：需新增依賴（Vitest 或類似），成本明顯較高，且屬獨立的工具鏈決策，不由本次加欄 feature 夾帶。C 項的 e2e 斷言已覆蓋本 intent 的加欄驗證需求。\n\n- **Q3 定案（A）— C1 HTTP 消費者的最小授權測試義務**：即使 `role_permissions` seed 資料未修改（C1 種子已存在於 `rbac_seed_data.py`），第一個 C1 HTTP 端點落地時仍須補 allow/deny 雙向 TestClient 測試——「具 C1 權限的角色應收到 2xx」與「無 C1 權限的角色應收到 403」兩個案例缺一不可。此為 A 規則與 B 規則的交叉要求，適用於本 intent 新增的任何 `/api/cost*` 端點。\n\n### 80% 覆蓋率門檻的定位\n\n**維持 `org.md` 原文，不在本檔弱化或改寫其宣稱**（把「80% 是目標不是閘門」寫進 `team.md` 會構成 `team.md` 弱化 `org.md` 的矛盾，屬 §13 learning admission 應擋下的形狀）。如實記載目前無法量測、無法強制的現況（見上），並以上述 A/B/C 三項變更範圍內、二元可判、零工具成本的規則作為現階段的實際門檻。導入 `coverage.py` 量測工具列為待補承載機制（見 `discovered-rules.md`）。\n\n---"
    },
    {
      "layer": "project",
      "text": "**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含 property-based 測試，不得只有 example-based：IaC generator、cost calculator、agent routing。其餘模組沿用 `org.md` 的預設門檻。"
    }
  ],
  "obligations": {
    "strategy": "standard",
    "strategy_volume": [
      "Five to eight tests per component.",
      "Unit tests plus integration tests for key boundaries.",
      "Add E2E, performance, or security tests when requirements demand them."
    ],
    "scope_floor": [
      "Keep the existing test suite green.",
      "This scope adds no extra new-test floor beyond the selected test strategy."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "test-after",
    "runner_step": "Verify the existing test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Verify the existing test runner/configuration and record the exact unit-scoped command.",
      "Data model / database behavior - implement.",
      "Data model / database behavior - write and run its tests after implementation.",
      "Repository / data access - implement.",
      "Repository / data access - write and run its tests after implementation.",
      "Business logic - implement.",
      "Business logic - write and run its tests after implementation.",
      "API / endpoint - implement.",
      "API / endpoint - write and run its tests after implementation.",
      "Frontend behavior - implement.",
      "Frontend behavior - write and run its tests after implementation.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:1aedc10dd7de9a19bd06fecb49cbcb5f27456db7ce4b18e81d500355d460bea6",
  "contract_sha256": "sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77"
}
```
