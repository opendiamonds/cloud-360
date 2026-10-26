# Code Generation Plan — `U10 session-store`

> 方法論與順序由下方 `## Testing Contract` 的 JSON 決定，該區塊由
> `bun .claude/tools/aidlc-testing-posture.ts render --unit session-store` 產生，
> **未經任何編輯**。本計畫的步驟順序即該契約 `plan_profile.steps` 的對應。

## 一、本單元要做什麼（一句話）

把 `SessionContext` 實作出來：單一 Redis key 之下的 Hash，持有**至多三段**對話
（`shared`／`workspace`／`assessment`），每段各自帶訊息歷程與三層作業對象；
追加與分段切換以 Lua 原子完成；TTL 24 小時、每次互動續期。

**本單元零對外端點、零 schema 變更、零前端面。**

## 二、交付物清單（20 個檔：9 新、11 改）

### 新增（9）

| # | 檔案 | 角色 |
|---|---|---|
| 1 | `backend/services/session_types.py` | 純資料形狀：段識別封閉集合、訊息、段、session；**零 I/O、零 Redis import**。含 `BR3.4` 修剪的**參考實作**（PBT 標的，非生產載體） |
| 2 | `backend/services/session_errors.py` | `SessionBackendUnavailable`（帶 `reason` 原因碼）、**`SessionMessageTooLong`**（`OPEN-N10-6` 新增）、三個原因碼常數 |
| 3 | `backend/services/redis_gateway.py` | 連線池、逾時、`[D2]`=A 的重試、Lua 載入、**三種原因碼分類**。不認識 `BrainSession` 語意 |
| 4 | `backend/services/session_store.py` | `K-09` 的五個方法；委派 `K-07` 做作業對象授權 |
| 5 | `backend/services/session_scripts/append_message.lua` | 追加＋`BR3.4` 修剪＋續期，原子 |
| 6 | `backend/services/session_scripts/switch_to_isolated.lua` | 建段＋複製作業對象＋改 `pageModes`，原子（`reliability-design.md` §三 第 3 列的 `EC3` 要求） |
| 7 | `backend/tests/test_session_types.py` | PBT（`hypothesis`）＋段識別封閉集合 |
| 8 | `backend/tests/test_session_contract.py` | 靜態契約斷言（不判權、不取身分、無 router、日誌白名單、Lua 為修剪唯一生產載體） |
| 9 | `backend/tests/test_session_store_behaviour.py` | 以**手寫 in-memory Redis 替身**驗五個方法的行為與授權委派 |

### 修改（11）

| # | 檔案 | 變更 | 為什麼是 blocking |
|---|---|---|---|
| 10 | `backend/requirements.txt` | 新增 Redis 客戶端 | `NFR8.41`；實讀確認目前**無任何** Redis 客戶端 |
| 11 | `backend/.env.example` | 新增 `BRAIN_SESSION_HISTORY_MAX`（**無值**，註明必填） | `project.md ## Mandated` 環境契約 |
| 12 | `deploy/.env.example` | 同上 | 同上 |
| 13 | `deploy/render-env.sh` | 寫入該變數 | 同上；`validate_env_contract.py` 會擋 |
| 14 | `deploy/docker-compose.deploy.yml` | `maxmemory-policy` → `noeviction`；backend 傳入新變數 | `[N3]`=A（`NFR4.50`）＋ `NFR8.40` |
| 15 | `deploy/docker-compose.test.yml` | backend 傳入新變數（內嵌含預設，CI 契約要的形狀） | `NFR8.40` |
| 16 | `docker-compose.yml`（repo 根，本機 dev） | 若它起 backend，傳入新變數 | 三環境一致 |
| 17 | `.github/workflows/deploy.yml` | 部署後還原驗證步驟（`[I1]`=B） | `NFR4.64` |
| 18 | **`LOCAL-DEV.md`** | 同步新環境變數與 Redis 的本機前置條件 | **`project.md ## Mandated` blocking**：異動任一 `.env.example` 或 `render-env.sh` 時必須同步 |
| 19 | `DEPLOY.md` | 記載 `noeviction` 的理由與還原驗證步驟 | 部署必知行為變更 |
| 20 | `backend/main.py` | **只在必要時**：啟動時驗證 `BRAIN_SESSION_HISTORY_MAX` 存在（`BR3.5` 大聲失敗） | `BR3.5`／`NFR8.40` |

### 刻意**不**動的四項（作為可驗證面）

| 不動 | 驗證方式 |
|---|---|
| `openapi.json` 與 `frontend/src/types/api.d.ts` | **本單元零 HTTP 端點**（`BR5.3`）。Step 11.2 斷言兩者 diff 為空；`dump_openapi.py --check` 須仍然通過 |
| `schema_rbac.sql`／`DEPLOY.md` 的表清單 | 本單元零 schema 變更，故 `project.md` 的 schema 同步 blocking 規則**不觸發**（`DEPLOY.md` 只加部署行為說明，不加表） |
| `backend/database.py` | diff 必須為空 |
| 任何既有 router／service | 本單元不改任何既有模組的行為 |

## 三、承接自上游、本站必須關掉的七項

| 來源 | 內容 | 本計畫的落點 |
|---|---|---|
| `nfr-requirements` 審查 `R-01`（Major） | `EC6` 逐字禁止 `BrainSession` **任何欄位**入 log，與 `NFR4.61`／`NFR4.63` 要求記 `sessionKey` 直接衝突 | Step 5.3：日誌白名單**以單一建構函式**實作，允許 `sessionKey`；`security-design.md` §一 已定操作性規則為 `BR3.6`（識別碼不是內容）。Step 11.1 斷言白名單不接受任意 `kwargs` |
| `nfr-requirements` 審查 `R-02`（Major） | `SessionMessage.text` 無長度上界，使 `NFR4.41` 的「可計算硬上界」不成立 | Step 4.2：`append_message` 入口檢查長度，超限 raise **`SessionMessageTooLong`**；Step 2.1 新增該例外型別 |
| `nfr-design` 審查 `R-02`（Major） | 上條的「可辨識錯誤」在 `K-09` 的凍結介面裡**沒有型別可承載**（只有 `SessionBackendUnavailable`） | 同上。`OQ-N4` 逐字授權改 `public_interface`，故新增例外型別在授權內 |
| `infrastructure-design` 審查 `R-01`（**Critical**） | 部署後驗證「等 healthcheck 轉綠」，而本單元已定該 healthcheck 不可信（AOF 載入中會通過） | Step 9.2：等待條件改為**以 app ACL 身分實際讀回 fixture 的某一欄位成功**，附重試上限與逾時；**不得**使用 healthcheck |
| `infrastructure-design` 審查 `R-02`（Major） | 「反正 stack 已重啟過」的緩解在多數部署上為假——`deploy.yml` 用 `up -d --build --remove-orphans`，**無 `--force-recreate`**，不會動到未變更的 Redis | Step 9.3：不寫假緩解。改為**明確宣告**該步驟會中斷當下使用者的 session，並把它放在部署序列**最後**（既有檢查全部通過之後），使中斷發生在服務已確認可用之後 |
| `infrastructure-design` 審查 `R-03`（Minor） | `NFR8.42` 從追溯表消失 | Step 12.1：本站 `traceability.json` 以**上游的 `traceability.json` ∪ markdown** 為 id 來源，不只掃 markdown |
| `nfr-design` 審查 `R-01`（Major） | `tech-stack-decisions.md:59` 寫「儲存結構留 `code-generation` 決定」，而 `nfr-design` 的 `[D1]`=A 已決定 | 本計畫**不重新決定**：結構＝Hash ＋ Lua，已定。Step 1.3 在 `code-summary.md` 記錄該對齊 |

## 四、實作步驟（對應 `plan_profile.steps` 的 `test-after` 順序）

### Step 1 — 專案結構與設定骨架

- [x] 1.1 建立 `backend/services/session_scripts/` 目錄（Lua 腳本的落點）
- [x] 1.2 `backend/requirements.txt` 新增 Redis 客戶端；在該行上方加註解說明**為何不用 `==` 精確釘選**（該檔檔頭逐字：精確釘選的理由是 OpenAPI 輸出的位元決定性，而本依賴不影響 OpenAPI）
- [x] 1.3 在 `code-summary.md` 記錄 `nfr-design` 審查 `R-01` 的對齊：儲存結構已於 `nfr-design` 定案，本站不重決

### Step 2 — 驗證測試執行器並記錄單元範圍指令

- [x] 2.1 確認 `python -m unittest` 可執行；記錄本單元的**三個**精確指令於 `unit-test-instructions.md`（不得用 `python -m unittest` 裸跑全套）
- [x] 2.2 新增 `backend/services/session_errors.py`：`SessionBackendUnavailable(reason=...)`、`SessionMessageTooLong`、三個原因碼常數 `REDIS_UNREACHABLE`／`REDIS_OOM`／`REDIS_COMMAND_ERROR`

### Step 3 — 資料模型／資料庫行為：實作

- [x] 3.1 `session_types.py`：`SegmentId` 封閉集合（`EC4`）、`SessionMessage`、`ConversationSegment`、`BrainSession`、`PageScope`
- [x] 3.2 `session_types.py`：`trim_history(messages, cap)` **參考實作**——`BR3.4` 的語意（丟最舊、保序、已達上限時不動）。**檔案層註解明記它不是生產載體**，生產載體是 Lua（`performance-design.md` 的唯一載體原則）
- [x] 3.3 序列化／反序列化：Hash 欄位 ↔ 型別。欄位前綴 `seg:`／`tgt:`／`meta`（`OPEN-N10-7` 的命名空間）

### Step 4 — 資料模型／資料庫行為：寫測試並跑

- [x] 4.1 `test_session_types.py`：`@given` PBT 三條 property——①輸出長度 ≤ cap；②輸出是輸入的後綴；③輸入長度 ≤ cap 時輸出等於輸入
- [x] 4.2 `test_session_types.py`：段識別封閉集合的拒絕測試；序列化往返（round-trip）測試
- [x] 4.3 跑 `python -m unittest tests.test_session_types -v`，綠燈

### Step 5 — 儲存層（`redis_gateway`）：實作

- [ ] 5.1 連線池：`min 5 / max 20`、`idle timeout 10m`、`max lifetime 30m`（`performance-design.md` 的算式）
- [x] 5.2 逾時：連線 2s、指令 1s；冪等方法重試至多 2 次、指數退避**含抖動**；`append_message` **不重試**
- [x] 5.3 **原因碼分類**：連線層例外 → `REDIS_UNREACHABLE`；回覆以 `OOM ` 開頭 → `REDIS_OOM`；其餘指令錯誤 → `REDIS_COMMAND_ERROR`。全部包成 `SessionBackendUnavailable(reason=...)`
- [x] 5.4 **日誌建構函式**：固定欄位白名單 `sessionKey`／`segmentId`／`method`／`reason`／`elapsedMs`／`droppedCount`／`attempt`，**不接受任意 `kwargs`**（`NFR4.63`；`EC6` 對齊見 §三）
- [x] 5.5 Lua 腳本載入與 `EVALSHA` 快取；`NOSCRIPT` 時回退 `EVAL`

### Step 6 — 儲存層：寫測試並跑

- [x] 6.1 手寫 in-memory Redis 替身（支援 `HGET`／`HSET`／`HGETALL`／`EXPIRE`／`TTL`／`EVAL`），置於 `backend/tests/` 內
- [x] 6.2 原因碼分類的三個案例（含 `OOM ` 前綴字串）
- [x] 6.3 重試行為：冪等方法重試、`append_message` 不重試
- [x] 6.4 跑 `python -m unittest tests.test_session_store_behaviour -v`

### Step 7 — 商業邏輯（`session_store` ＋ Lua）：實作

- [x] 7.1 `load`／`touch`：`BR1.6`（不存在回 `None`）、`BR1.3`（續期）
- [x] 7.2 `append_message(session_key, segment_id, role, text)`：**帶段識別**（`BR3.1`）；入口檢查長度（`OPEN-N10-6`）；走 `append_message.lua`
- [x] 7.3 `set_sharing_mode(session_key, scope, mode)`：入口頁拒絕（`BR2.2`）；切 isolated 走 `switch_to_isolated.lua`（建段＋複製＋改模式，原子）；切回 shared 只改 `pageModes`（`BR2.5`，不刪段）
- [x] 7.4 `set_work_target(session_key, segment_id, principal, …)`：先呼叫 `K-07` 的 `HierarchyFacade.resolve_work_target`，例外**原樣上傳**（`BR4.6`）；寫解析結果含 `null`（`BR4.5`）
- [x] 7.5 `append_message.lua`：解碼→追加→修剪到 cap→編碼寫回→`EXPIRE`
- [x] 7.6 `switch_to_isolated.lua`：段不存在則建立並逐欄複製 `tgt:shared`→`tgt:<P>`；寫 `pageModes[P]=isolated`；`EXPIRE`

### Step 8 — 商業邏輯：寫測試並跑

- [x] 8.1 五個方法的 happy path
- [x] 8.2 **授權委派**：`K-07` raise `HierarchyForbidden` 時 `set_work_target` 原樣上傳且**不落地**
- [x] 8.3 **逐段驗證**（`BR4.7`）：對**第二段**（非 `shared`）也跑一次 allow/deny
- [x] 8.4 `BR2.2`：入口頁切換被拒
- [x] 8.5 `BR2.5`：切回 shared 後該段仍在；再切 isolated **回到同一段**（`[S2]`=A 的重入）
- [x] 8.6 `BR3.2`：讀取某段只得到該段訊息（`AC3.1.2`／`AC6.1.3`）
- [x] 8.7 `OPEN-N10-6`：超長訊息 raise `SessionMessageTooLong`，**不是** `SessionBackendUnavailable`
- [x] 8.8 `BR3.5`：上限參數缺值時啟動失敗

### Step 9 — API／端點層

**本單元零 HTTP 端點**（`BR5.3`）。本層改為**部署驗證**：

- [x] 9.1 `deploy.yml` 新增部署後步驟：寫 fixture session（三段、各有訊息與不同作業對象、`pageModes` 一鍵 isolated）→ 記錄五項基準與剩餘 TTL
- [x] 9.2 `docker compose restart redis` → **等待條件為「以 app ACL 身分實際讀回 fixture 的某一欄位成功」**，附重試上限與總逾時；**不使用 healthcheck**（審查 `R-01` Critical）
- [ ] 9.3 逐項比對五項；`NFR4.57` 的 TTL 斷言為**區間**（< 原值且 > 原值 − 寬限）；步驟置於部署序列**最後**，並在步驟說明中**明確宣告**它會中斷當下使用者的 session（審查 `R-02`：不寫假緩解）
- [x] 9.4 失敗時讓 deploy job 失敗以觸發既有 rollback；**不得** `logger.warning` 帶過
- [x] 9.5 刪除 fixture session

### Step 10 — 前端行為

**不適用。** 本單元零前端面（`unit-of-work.md` 的 kind 為 `service`）。消費端
`U14`／`U16` 為獨立單元。**不產生任何前端檔案。**

### Step 11 — 環境／建置設定

- [x] 11.1 `BRAIN_SESSION_HISTORY_MAX`（值 **200**）寫進 `render-env.sh`、兩份 `.env.example`、`deploy` 與 `test` 兩份 compose、repo 根 `docker-compose.yml`（若它起 backend）
- [x] 11.2 `deploy/docker-compose.deploy.yml` 的 `maxmemory-policy` → `noeviction`
- [x] 11.3 `LOCAL-DEV.md` 同步（**blocking**）：新環境變數、Redis 為本機硬依賴
- [x] 11.4 `DEPLOY.md` 記載 `noeviction` 的理由與還原驗證步驟
- [x] 11.5 跑 `python3 scripts/validate_repo_contract.py` 與 `python3 scripts/validate_env_contract.py`

### Step 12 — 文件與追溯

- [x] 12.1 `traceability.json`：id 來源為上游 `traceability.json` **∪** markdown（審查 `R-03`）
- [x] 12.2 `code-summary.md`：交付物、刻意不動的四項與其驗證、承接未關的項目
- [x] 12.3 `source-manifest.json`：**只含** `stage`／`unit`／`version`／`writes` 四個欄位（多一個欄位會讓 `REVIEW_REQUESTED` 被拒）
- [x] 12.4 全套回歸：`python -m unittest discover -s tests -v` 綠燈；`dump_openapi.py --check` 通過；`backend/database.py`、`openapi.json`、`api.d.ts` diff 為空

## 五、突變驗證（六項，每項須實際看到紅燈再還原）

| # | 突變 | 預期紅燈 |
|---|---|---|
| M1 | `trim_history` 改成丟最新而非最舊 | PBT property ②（輸出是輸入的後綴） |
| M2 | `append_message` 省略段識別、預設寫 `shared` | `BR3.1` 的拒絕測試 ＋ `BR3.2` 的段隔離測試 |
| M3 | `set_work_target` 寫入呼叫方傳入的原始識別碼而非 `K-07` 解析結果 | 授權委派測試（`HierarchyForbidden` 後仍落地） |
| M4 | `switch_to_isolated` 改回三次獨立寫入（非 Lua） | **須確認此突變在替身下可偵測**；若不可，如實記為替身的限制而非測試缺口 |
| M5 | 長度檢查移除 | `OPEN-N10-6` 的 `SessionMessageTooLong` 測試 |
| M6 | 日誌建構函式改為接受 `**kwargs` | `NFR4.63` 的白名單靜態斷言 |

**M4 的誠實限定**：in-memory 替身能否區分「一次 Lua」與「三次寫入」取決於替身的
實作粒度。若不能，**記為替身的限制**——真正的原子性只能在真實 Redis 上驗，
而那是 `[I1]`=B 的部署後步驟的範圍。不得為了讓 M4 有紅燈而偽造一個斷言。

## 六、本計畫**無法**在 CI 驗證的三項（如實記載）

| 項目 | 為什麼 | 真正的驗證點 |
|---|---|---|
| Lua 腳本的實際行為 | CI 的測試 stack 有 Redis，但 backend 測試走 in-memory SQLite 且**不連 Redis**；新增一個連 Redis 的 CI job 已於 `[I1]` 否決 | 部署後驗證（`[I1]`=B）＋ staging 實跑 |
| `noeviction` 的 OOM 行為 | 需要把 Redis 灌到 256MB | 不驗。`NFR4.60` 的使用率訊號是它的替代偵測面 |
| 重啟還原五項 | CI 測試 stack 無 AOF、無 volume（實讀確認） | `[I1]`=B 的部署後步驟 |

**三項都不是「忘了測」，是測不到。** 把它們列出來，使下游不會把「CI 全綠」
讀成「這三件事已驗證」。
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

## 七、方法論適用說明（`test-after`，`standard`）

上方的 `## Testing Contract` 由
`bun .claude/tools/aidlc-testing-posture.ts render --unit session-store` 產生，
**未經任何編輯**。

| 契約項 | 本計畫的落實 |
|---|---|
| `methodology: test-after` | 每層先實作再測：Step 3 → Step 4；Step 5 → Step 6；Step 7 → Step 8 |
| `runner_ready_before_first_test: true` | Step 2.1 在任何測試步驟之前確認執行器並記錄三個單元範圍指令 |
| `testable_layers` 的 `Data model / database behavior` | Step 3（`session_types`）＋ Step 4 |
| `testable_layers` 的 `Repository / data access` | Step 5（`redis_gateway`）＋ Step 6 |
| `testable_layers` 的 `Business logic` | Step 7（`session_store` ＋ Lua）＋ Step 8 |
| `testable_layers` 的 `API / endpoint` | **本單元零 HTTP 端點**（`BR5.3`）。該層改以 Step 9 的部署後驗證承載——那是本單元唯一真的會執行的端到端驗證 |
| `testable_layers` 的 `Frontend behavior` | **不適用**：本單元零前端面，kind 為 `service`。消費端 `U14`／`U16` 是獨立單元 |
| `test_strategy: standard`（每元件 5–8 測試 ＋ 關鍵邊界的整合測試） | `session_types` 約 5 條（含 3 個 PBT property）、`redis_gateway` 約 6 條、`session_store` 約 8 條、靜態契約約 5 條 |
| `scope_floor`：既有測試須維持綠燈 | Step 12.4 |
| `project.md` 的 PBT hard constraint | **N/A（非豁免）**——ADR-0006 點名的三個落點（IaC generator、cost calculator、agent routing）皆不是本單元。但 `BR3.4` 的修剪是天然的純函式 PBT 標的，Step 4.1 **仍然做**，屬 `team.md` 記載的自發良好實踐 |

### 覆蓋率門檻

`org.md` 宣告 80% line coverage；本 repo **無覆蓋率量測機制**（`team.md` 逐字
「既無法量測也無法強制，是宣告而非閘門」）。**本計畫不宣稱滿足該數字、也不弱化它**，
改以上表的測試條數 ＋ §五 的六項突變驗證作為實際門檻，並如實記載落差。

## 八、ADR-0006 四面向：本計畫的程式落點

逐格對照 `nfr-design/security-design.md §五` 與
`nfr-requirements/security-requirements.md`。**不改任何判定。**

| 面向 | 判定 | 本計畫的落點 |
|---|---|---|
| **IAM** | 適用（本單元最重的一格） | Step 7.4 的「解析在前、寫入解析結果」；Step 8.2／8.3 的 allow/deny **對第二段也跑一次**（`BR4.7` 是 `[S3]`=A 自己製造出來的授權面）；Step 11.1 不新增任何 story id |
| **Encryption** | 適用，無增量 | 不新增儲存體；憑證沿用 `U1` 的 ACL 路徑。**不寫「不適用」** |
| **Network exposure** | 適用，**零增量** | Step 11 不開任何埠；Step 12.4 斷言 `openapi.json` diff 為空（零新端點的機械證據） |
| **Audit logging** | 適用 | Step 5.4 的白名單建構函式；Step 11.1 的靜態斷言。**反向禁令**：對話內容不得入 log——本 repo 為 public、Actions log 公開可讀 |

**四面向皆適用，無不適用項。**

## 九、公開 repo 的輸出禁令

本單元持有**個人對話內容**，而本 repo 為 public、Actions log 公開可讀
（`project.md` 逐字「一次意外 echo 即等同公開發布」）。

| 禁令 | 落點 | 驗證 |
|---|---|---|
| 日誌不得含 `text`／整個段／整個 session | Step 5.4 的建構函式（**白名單，不是黑名單**） | Step 11.1 的靜態斷言 ＋ Step 8 的執行期字串比對 |
| Lua 的 `ARGV` 內容不得被記錄 | Step 5.5 的腳本呼叫處 | 同上 |
| 部署後驗證的 fixture 不得含真實樣貌的對話文字 | Step 9.1 | 人工核對；fixture 一律用 `fixture-` 前綴的無意義字串 |
| 錯誤訊息不得回傳他人 session 的任何欄位 | Step 2.2 的例外型別只帶 `reason`，不帶內容 | Step 8 的斷言 |

**第一條是本單元最容易出的錯**：`logger.warning(f"...{session}")` 在功能上完全
正常、測試也會綠，而它把整段對話寫進公開可讀的日誌。故 Step 5.4 把白名單做成
**建構函式的參數簽章**而非文件約定——簽章擋得住，文件擋不住。

## 十、合併前必修第 12、18 項（code-generation Request Changes 修訂，2026-10-23）

**來源**：`construction/functional-design/merge-blockers.md` 第 12 項（`nfr-design` review-02 R-01）與第 18 項（`infrastructure-design` work-orchestrator review-01 R-02；`nfr-requirements` session-store review-02 R-01）。第 18 項的單元欄為「session-store／work-orchestrator」，容量上界由本單元的修剪承載，故在本單元處理。使用者於 2026-10-23 裁決，兩題皆選建議項。

### Step 13 — 第 12 項：寫入與續期以 Redis 交易一次送出（裁決：MULTI／EXEC）

**缺陷**：首次建立 session（`_ensure_meta`，`session_store.py:528-543`：兩次 `HSET`）與 `set_work_target`（`:394-407`：`_ensure_meta` ＋ `HSET` ＋ `EXPIRE`）都是多個獨立指令；中途行程中止或 key 剛好過期，可能留下**無 TTL** 的 key，永不過期。

- [x] `backend/services/redis_gateway.py`：新增一個以 `pipeline(transaction=True)`（MULTI／EXEC）送出「同一 key 的多個 `HSET` ＋ 一個 `EXPIRE`」的方法；沿用既有方法的錯誤分類、原因碼與日誌白名單（§九），不新增可記錄內容的參數。
- [x] `session_store.py`：`_ensure_meta` 的建立與 `set_work_target` 的寫入＋續期改走該方法，使「寫入」與「設定 TTL」同進同退。`append_message`／`set_sharing_mode` 若有同形狀的多指令寫入，一併改；已由 Lua 承載而原子者不動。
- [x] 測試：替身（`tests/` 的 Redis fake）支援 MULTI／EXEC 語意（未 EXEC 前不可見、EXEC 時全部生效）；斷言首次建立後 key 有 TTL；模擬 EXEC 之前連線中斷 → key 不存在（不會留下無 TTL 的半成品）；`set_work_target` 後 TTL 已續期。突變：把交易拆回逐條指令並在中間注入失敗 → 「無 TTL 半成品」案例紅。
- [x] 真實 Redis 的原子性屬 §六「無法在 CI 驗證」之列，據實記載；本機可用 scratchpad 臨時 `redis-server` 實測時記錄結果。

### Step 14 — 第 18 項：每段加 200 KB 位元組上限（裁決：每段對話大小上限）

**缺陷**：容量承諾（`deploy/.env.example:145-146`：300 個同時存活 session ≈ 90 MB）以「每則 500 B」的平均假設計算，而單則上限是 4000 字元（`DEFAULT_MESSAGE_MAX_CHARS`，`session_store.py:113`）；最壞每 session 約 3 段 × 200 則 × 4000 個中文字 ≈ 7 MB，`maxmemory 256mb`＋`noeviction` 下最壞約 35 個 session 即滿，滿後所有 session 寫入失敗。

- [x] 新增模組常數 `DEFAULT_SEGMENT_MAX_BYTES = 200 * 1024`（以 UTF-8 位元組計；刻意不做環境變數，理由同 `OPEN-ND19-6`：環境設定契約的三處同步成本不值得）。
- [x] `BR3.4` 修剪改為**兩個條件取較嚴者**：每段最多 `BRAIN_SESSION_HISTORY_MAX` 則，**且**整段序列化後 ≤ 200 KB；超過時從最舊的訊息開始丟，直到兩者都成立。純函式版（`session_types` 的修剪）與 Lua 生產載體**同一語意**，Lua 以位元組長度（`string.len`）判斷。
- [x] 單則訊息本身大於 200 KB 不可能發生（4000 字元 × 最多 4 位元組 = 16 KB），故不需「單則超限」分支；以斷言寫明此前提。
- [x] 容量算式改用最壞值：每 session 最壞 3 段 × 200 KB ≈ 600 KB；`maxmemory 256mb` 的 80% ≈ 204 MB ÷ 600 KB ≈ **340** 個 session，對得上 300 的承諾。更新 `deploy/.env.example:145-146` 的註解、`DEPLOY.md` 的 Redis 容量說明（含 `noeviction` 滿載的後果與 `MEMORY STATS` 觀察方式）、`deploy/docker-compose.deploy.yml` redis `command:` 旁的註解；**`maxmemory` 值與 `noeviction` 不變**。
- [x] 測試：PBT（`session_types` 的修剪）新增 property——任何輸入修剪後整段位元組數 ≤ 上限、則數 ≤ 上限、保留的是最新的那幾則且順序不變；行為測試以 4000 個中文字的訊息灌滿一段，斷言位元組上限生效而非則數上限。突變：拿掉位元組條件 → 新 property 與行為案例紅。
- [x] `validate_env_contract.py`、`validate_repo_contract.py` 綠（只改註解，未新增變數）。

### Step 15 — 驗證與紀錄

- [x] 本單元三個測試模組與完整套件（`backend/.venv`）全綠。
- [x] `merge-blockers.md` 第 12、18 列回填處置；`code-summary.md` append 本節紀錄（改動檔:行、測試、突變、容量重算、未驗項）；`source-manifest.json`、`traceability.json`（加 `MB-12`／`MB-18`）更新。`brain-infra` 的 `traceability.json`／計畫 Step 6 仍寫 `allkeys-lru` 的過期敘述，不屬本單元，於 `code-summary.md` 註明由 `brain-infra` 的記錄承接（該處已記載）。
- 追溯：`merge-blockers.md` #12／#18；`BR3.4`、`BR3.5`、`NFR4.40`、`NFR4.41`、`NFR4.50`。

## Plan Approval
