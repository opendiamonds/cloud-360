# Unit Test Instructions — `U12 work-orchestrator`

## 一、框架與設定

- 後端：Python 內建 `unittest` ＋ `unittest.mock` ＋ `hypothesis`（純函式 `@given` 與 `RuleBasedStateMachine`），**不是 pytest**。
- 非同步測試：`unittest.IsolatedAsyncioTestCase`。
- Redis：既有替身（`tests/test_session_store_behaviour.py` 的形狀；Lua 以 `session_types` 的參考實作模擬）。**替身證明不了真實原子性**——
  它是單執行緒 Python 物件。真實原子性由 `backend/tests_redis/`（opt-in，`REDIS_URL` 未設定即 skip 並印原因）承擔，
  **不在 CI**（`ci.yml` 的 backend job 沒有 Redis 服務）。
- 資料庫：`backend/tests/helpers.py` 的 in-memory SQLite；`WorkOrchestrator` 以建構子注入的 `session_factory` 指向它。
- 既有能力：授權測試經**真實 app**（`ASGITransport(app=main.app)`＋測試 DB 覆寫 `get_db`）；流程測試以替身 app 一次回傳完整 SSE 本體。
- 時間：建構子注入 `clock` 與 `sleep`，測試以可推進的時鐘與立即返回的 `sleep` 控制，不依賴第三方假時鐘工具。
- 前端：本單元無前端程式，不跑 Playwright。

## 二、本單元的執行指令（皆限定本單元的檔案）

在 `backend/` 目錄：

```bash
# 測試執行器就緒檢查（Step 2）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_session_store_behaviour -v

# 本單元測試（Step 4／6／8）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_work_orchestrator_store tests.test_work_orchestrator_capabilities tests.test_work_orchestrator_rules tests.test_work_orchestrator_model tests.test_work_orchestrator_flow tests.test_work_orchestrator_boundaries tests.test_work_orchestrator_authz -v

# 既有受影響的兄弟測試（U10、U7 跨單元修改後須仍綠）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_session_store_behaviour tests.test_session_types tests.test_session_contract tests.test_hierarchy_service -v

# Lua 真實原子性（opt-in；需 REDIS_URL）
REDIS_URL=redis://localhost:6379/15 PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests_redis.test_work_item_lua -v

# OpenAPI 漂移（Step 9；本單元不應改變 openapi.json）
python3 scripts/dump_openapi.py --check
```

## 三、測試清單與數量（standard：每元件 5–8 個；PBT 依 ADR-0006）

| 檔案 | 元件 | 案例 |
|---|---|---|
| `test_work_orchestrator_store.py` | `SessionStore` 擴充、Lua 參考實作、`list_diagrams_of_system` | ① 建項成功 ② 欄位已存在即拒絕 ③ key 不存在即拒絕且不建 key（`NFR12.18`）④ 比對 status 與 `dispatchStage` 不符即拒絕 ⑤ 補丁只改指定欄位，`estimateSetId` 保留 ⑥ 補丁值 null 即設 null、空陣列保留 ⑦ TTL 不變 ⑧ `list_diagrams_of_system` 擁有者／非擁有者／零張 |
| `test_work_orchestrator_capabilities.py` | `CapabilityClient` | ① A1 有 xml 取最後一份 ② A1 error 與無 xml ③ A3 complete 與 error、結束無 complete ④ 401／403／5xx 對應 ⑤ 估價表翻頁找到即停 ⑥ 快照 generating 且 `started_at` 逾 5 分鐘判逾時 ⑦ 例外與 log 不含 token（`NFR12.6`）⑧ 完整本體一次回傳即可判定（`NFR12.29`） |
| `test_work_orchestrator_rules.py` | 純函式（PBT） | `transition` 不離開終態、不產生五值以外狀態；`plan_waits` 只有成本或檢視等待、對象為之前的架構設計、無循環；`side_effect_on_stop` 成本與 not_dispatched 恆 none、`persisting` 為「可能已存回…」；`on_dependency_stopped` 成本 proceed、檢視 skip；`PHRASES` 每個句型一案 |
| `test_work_orchestrator_model.py` | 比對後寫入（stateful PBT） | `RuleBasedStateMachine`，不變量 (a)–(e)（`../nfr-design/scalability-design.md` 第三節），規則含寫 `estimateSetId` |
| `test_work_orchestrator_flow.py` | `WorkOrchestrator` | ① 先回覆後執行（能力永不返回，`dispatch` 1 秒內回傳且已送建立訊息）② facade 在非事件迴圈執行緒 ③ 輪詢 ≤ 180 次後逾時 ④ 等待與 `BR53.4` 分流（成本開始、檢視已停掉＋說明）⑤ `correct` 與背景推進交錯（`sideEffect` 不為 none）⑥ 在途存檔四列（含逾時後 PUT 才成功）⑦ 復原掃描兩步、兩個併發掃描只啟動一次 ⑧ 寫入結果未知（連線錯誤）重讀確認、sink 失敗不擴散、不重試、停用判定兩案、token 與原句不入 log 與 Redis、所有訊息通過契約模型 |
| `test_work_orchestrator_boundaries.py` | 邊界 | AST 禁止 import 清單（含 `main`、`importlib`）；對外只經 `ASGITransport`；不 import LLM 模組（`NFR12.5`） |
| `test_work_orchestrator_authz.py` | 授權（真實 app） | A1 有權限 → `request_sent`；無權限 → `BR51.3` 句型；token 過期 → `BR51.6` 句型；C1 有／無權限各一 |
| `tests_redis/test_work_item_lua.py` | Lua（opt-in） | 與參考實作同一組案例比對結果 |

## 四、突變驗證（每項：套用 → 確認紅 → 還原 → 確認綠）

執行突變時設 `HYPOTHESIS_NO_SHRINK=1`（測試設定檔讀它以關閉 shrinking，避免長時間卡住）。

| 突變 | 預期紅燈 |
|---|---|
| Lua 只比對 status（不比對 `dispatchStage`） | 模型測試不變量 (a)；流程 ⑤ |
| Lua 改為整個物件覆寫（非補丁合併） | 模型測試不變量 (c)；store ⑤ |
| `_advance` 不看寫入結果即啟動 | 流程 ⑦ 的「只啟動一次」 |
| `_finish_persist` 不用 shield（或共用 `_run` 的 client） | 流程 ⑥ |
| 先送請求後記 `request_sent` | 流程 ⑤ 或「寫入失敗即不送」案例 |
| Authorization 改為固定管理者 token | authz 無權限案例 |
| 停用判定改為沿用握手快照 | 流程 ⑧ 的「PUT 後停用」案例 |
| `BR53.4` 改為一律照常開始 | 流程 ④ 的檢視案例 |
| log 帶入 `requestText` | 「原句不入 log」案例 |

結果記入 `code-summary.md`。

## 五、覆蓋率

repo 無覆蓋率量測機制（`team.md`）；以上列每個元件 5–8 個案例、四個純函式的 PBT、stateful 模型測試與突變驗證作為實際門檻，不宣稱百分比。

## 六、Mock 與測試資料

- 身分：測試建立 `User` 並以 `mint_principal` 鑄造；授權測試以真實登入流程取得 token 或以既有測試樣板簽發 JWT，**不 mock `user_can`**。
- 圖、系統、專案：經 `HierarchyFacade`／`MembershipFacade` 建立，不直接插表。
- 唯一標記字串：token、使用者原句、例外訊息各用 `uuid4()` 產生，斷言 log、Redis 與 sink 輸出不含它。
