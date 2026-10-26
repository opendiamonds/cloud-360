# Code Generation Plan — `U20 requirement-field-service`

> 本計畫把四站設計（functional-design、nfr-requirements、nfr-design、
> infrastructure-design）落成程式，**並一併處置四站審查帶下來、經使用者裁決帶進
> 程式產生的殘留**（§二）。方法論依下方 Testing Contract 為 `test-after`。

## 一、交付範圍

| # | 交付 | 位置 | 類型 |
|---|---|---|---|
| 1 | 欄位定義常數（兩組七欄） | `backend/services/requirement_field_definitions.py` | 新建 |
| 2 | 例外與檢視型別 | `backend/services/requirement_field_errors.py`、`requirement_field_types.py` | 新建 |
| 3 | 資料存取（一次讀取、upsert、條件式清空） | `backend/services/requirement_field_service.py` | 新建 |
| 4 | 唯一授權入口 | `backend/services/requirement_field_facade.py` | 新建 |
| 5 | HTTP router（三個路由） | `backend/services/requirement_field_router.py`；`backend/main.py` 掛 `/api/requirements` | 新建／修改 |
| 6 | ORM 模型 | `backend/models.py` 新增 `SystemRequirementField` | 修改 |
| 7 | 資料表收斂（`updated_on_behalf_of` → `VARCHAR(64)`、去外鍵） | `schema_rbac.sql` 的 `J)` 區塊；`backend/scripts/run_meta_schema_migration.py`；`backend/scripts/verify_meta_schema.sql` | 修改 |
| 8 | CI 收斂驗證 | `.github/workflows/ci.yml` 的 `memory-schema` job；`backend/scripts/ci/downgrade_requirement_fields.sql`、`seed_requirement_field_fixture.sql` | 修改／新建 |
| 9 | 部署文件（blocking 同步） | `DEPLOY.md` 2.2.9 | 修改 |
| 10 | OpenAPI 與前端型別 | `openapi.json`、`frontend/src/types/api.d.ts` | 重新產生 |
| 11 | 測試 | `backend/tests/test_requirement_field_*.py`；`backend/tests_pg/test_requirement_field_pg.py` | 新建 |

**零新依賴、零新環境變數、零前端程式。** 觸發 `project.md ## Mandated` 的 `schema_rbac.sql` ＋
`DEPLOY.md` blocking 同步（第 7、9 項同一個 commit）。

## 二、併入本計畫的審查殘留（使用者裁決：帶進 code-generation）

| 來源 | 問題 | 本計畫的處置 | 步驟 |
|---|---|---|---|
| FD `review-02` R-01；NFR `review-01` 帶入；ND R-06 | 收斂若無條件轉型清值，重跑會清掉代寫溯源 | `DO $$` 區塊：僅當欄位為 `integer` 才轉型（`USING NULL`，並 `RAISE NOTICE` 被清掉的非空值筆數）；僅當外鍵存在才移除，名稱以 `pg_constraint.conkey` 比對該欄查得；設 `lock_timeout`；catalog 查詢一律加 `public` schema 限定 | Step 3 |
| FD R-02；ID R-02、R-03、R-04、R-05 | 舊定義資料庫的收斂從未被驗；CASCADE 未被驗；遷移腳本無欄位級後條件 | `run_meta_schema_migration.py` 新增欄位級後條件（型別為 `character varying`、該欄無外鍵、`updated_by` 外鍵仍在）並同步其成功輸出；`memory-schema` job 新增步驟 0／A–E（setup-python ＋ pip、舊定義、跑腳本、寫入 fixture 並 `COMMIT`、重跑、**先刪 system 斷言 CASCADE**、清除），值斷言用 `DO … RAISE EXCEPTION`，所有 `psql` 帶 `-v ON_ERROR_STOP=1`，`DATABASE_URL` 為 `postgresql+psycopg://` 形式；在 `ci.yml` 註解寫明此為對 `concurrency` job 註解所述取捨的有意違反與理由 | Step 3、4 |
| ID R-01 | ORM 模型會讓啟動時 `create_all` 在表不存在時建表 | **沿用 `U19` 對兄弟表的先例（`OPEN-ID19-1`）**：不掛 `before_create` 守門（掛了會讓後端在未遷移的資料庫上**整個起不來**，影響面遠大於本單元）；改為讓 ORM 宣告與 DDL 等價的唯一鍵、CHECK、外鍵與 `VARCHAR(64)`，使 `create_all` 建出的表功能等價、只缺 COMMENT（遷移腳本的 `COMMENT ON` 之後補上）；`DEPLOY.md` 2.2.9 照此如實描述，**不寫**「表不存在時 500」 | Step 3、12 |
| FD R-04；ND R-01 | 框架 422 回顯輸入且早於授權 | router 不讓框架驗證本體或 `system_id`：`PUT` 讀原始本體、`system_id` 以字串接收，**授權通過後**才由 facade 解析與驗證（非整數 `system_id` → 404；本體非 JSON、缺 `value`、型別錯、含未知欄位如 `updated_by` → `RequirementFieldValidationError` → 422）。錯誤 `detail` 沿用既有 router 的**固定字串**形狀（含定址欄位、不含值）；三路由一致宣告 403／404／422 | Step 9 |
| NFR R-06（使用者 2026-10-12 裁決） | 本體帶 `updated_by` | 422（同上一列的未知欄位處理） | Step 9、10 |
| NFR R-01；ND R-03 | 授權矩陣漏列 | 十二列矩陣：`security-design.md` 的九列 ＋「屬於**別的**專案的成員」「`project_admin` 且有 `K4.edit` 的正向寫入」「`Platform_Admin` 非成員」 | Step 10 |
| NFR R-08 | 併發清空兩者皆寫入 | 單一條件式 `UPDATE … WHERE value IS NOT NULL`，0 列時再讀現況 | Step 5 |
| NFR R-02；ND R-07 | upsert 的計數判準；`session.bind` | 單一敘述 ＋ `RETURNING`；方言取自 `session.get_bind().dialect.name` | Step 5 |
| ID R-07 | PostgreSQL 方言的 upsert 從未在 CI 執行 | 新增 `backend/tests_pg/test_requirement_field_pg.py`（由既有 `concurrency` job 執行）：PG 上的 upsert、條件式清空、兩個併發清空只生效一次 | Step 6 |
| FD R-06 | 第四種列的 FieldView 溯源欄位 | `never_filled`（含第四種列）一律回 null 的 `updatedAt`／`updatedBy`／`updatedOnBehalfOf`／`clearedAt` | Step 7 |
| ND R-04 | SQLite `now()` 秒級精度使「時間不變」測試不會紅 | 寫入與清空的時間戳由 Python 產生並傳入，測試可注入固定時鐘 | Step 5 |
| ND R-07 | StaticPool 下「另一 session 重讀」不成立 | 回滾測試改為：mock commit 拋錯後，斷言 session 已 rollback，並在同一連線上重新查詢——rollback 之後的讀取即為已提交狀態——值與 `filledState` 與呼叫前相同 | Step 8 |
| FD R-03；R-07 | 契約追認清單補項 | 寫入 `code-summary.md` 的交接（`K-17` 的 `own_responsibility`／`anti_double_check` 字面、`unfilled_count` 命名、`K-16` 矛盾句） | Step 12 |
| FD R-05 | 自檢 5 殘留舊數字 33 | `code-summary.md` 揭露（實為 37），不回改已凍結的設計檔 | Step 12 |
| FD R-03（BR42.5 的限度）；ID R-06 | 代寫路徑省略標示仍會清值；上線確認方法 | 交接 `U21`／`U13`；`DEPLOY.md` 上線確認改為查 `information_schema` 的 `data_type` | Step 12 |

## 三、步驟（`test-after`：逐層實作後補該層測試）

- [x] **Step 1 — 結構骨架**：建 `backend/scripts/ci/` 目錄（若不存在）；不建任何空檔。
- [x] **Step 2 — 驗證執行器並記錄本單元指令**：執行 `unit-test-instructions.md §二` 的指令，確認 `unittest` 可載入既有 `tests.test_membership_data`。`tests_pg` 依既有慣例在缺 `DATABASE_URL` 時**大聲失敗**（`tests_pg/__init__.py` 的 `require_pg_url`，刻意不退回 SQLite），故本機無 PostgreSQL 時不執行它，由 CI 的 `concurrency` job 執行；本機若有 PostgreSQL 則以該 job 的同一指令執行。
- [x] **Step 3 — 資料模型：實作**
  - `schema_rbac.sql` 的 `J)` 區塊：`updated_on_behalf_of` 改為 `VARCHAR(64)`、無外鍵；改寫該欄 COMMENT；在建表敘述之後加條件式收斂 `DO $$` 區塊（§二 第一列）。
  - `backend/models.py` 新增 `SystemRequirementField`：欄位、三欄唯一鍵、`ck_system_requirement_fields_cleared_has_null_value`、兩條外鍵（`system_id` CASCADE、`updated_by`）與 `VARCHAR(64)` 的 `updated_on_behalf_of`，與 DDL 等價；不掛 `before_create` 守門（§二 第三列）。
  - `run_meta_schema_migration.py`：欄位級後條件與成功輸出。
  - `verify_meta_schema.sql`：欄位級斷言（型別、該欄無外鍵、`updated_by` 外鍵仍在）。
  - `backend/scripts/ci/downgrade_requirement_fields.sql`、`seed_requirement_field_fixture.sql`。
  - `.github/workflows/ci.yml` 的 `memory-schema` job：步驟 0／A–E（§二 第二列）。
- [x] **Step 4 — 資料模型：測試**：新建 `backend/tests/test_requirement_field_data.py`（比照 `test_membership_data.py`）：ORM 與 `schema_rbac.sql` `J)` 區塊的欄位集合、可空性、唯一鍵、CHECK 一致；SQLite 上 CHECK 擋下「有值且已清空」。PostgreSQL 側的收斂與 CASCADE 由 CI `memory-schema` job 驗（本機無 PostgreSQL 時記為未在本機執行）。
- [x] **Step 5 — 資料存取：實作** `requirement_field_service.py`：一次讀取；依方言的 `INSERT … ON CONFLICT DO UPDATE … RETURNING`；條件式清空 `UPDATE … WHERE value IS NOT NULL RETURNING`，0 列時讀現況；時間戳由呼叫端傳入。
- [x] **Step 6 — 資料存取：測試**：`backend/tests/test_requirement_field_service.py`（SQLite）：upsert 重複寫入列數為 1、列已存在時走首寫路徑不拋 `IntegrityError`、條件式清空對從未填過／已清空／第四種列皆為 no-op、查詢計數（`before_cursor_execute`）；另建 `backend/tests_pg/test_requirement_field_pg.py`（PostgreSQL）：PG 方言 upsert、條件式清空、兩個併發清空只生效一次。另加 SQLite 版本 ≥ 3.35 的守衛測試。
- [x] **Step 7 — 業務邏輯：實作**：`requirement_field_definitions.py`（兩組七欄、組標題、欄位標籤、填寫提示）、`requirement_field_errors.py`、`requirement_field_types.py`、`requirement_field_facade.py`（`BR41`–`BR46` 全部；log 事件依 `observability-design.md`；logger `"cloud360.requirement_fields"`）。
- [x] **Step 8 — 業務邏輯：測試**：`backend/tests/test_requirement_field_facade.py`：三態推導（含第四種列回 null 溯源）、計數同源、定義外保留列不顯示不計數、空值寫入即清空、代寫路徑空值被拒、代寫標示不授權、同進程（`U13` 路徑）的待核准與全域層拒絕、拒絕 log 欄位與「log 不含值」、no-op 不記 INFO、依賴非預期例外不放行、回滾後值不變。
- [x] **Step 9 — API：實作**：`requirement_field_router.py`（GET／PUT／DELETE；原始本體授權後解析；固定字串 `detail`；三路由宣告 403／404／422）；`main.py` 掛 `/api/requirements`；重新產生 `openapi.json`（`backend/scripts/dump_openapi.py`）與 `frontend/src/types/api.d.ts`（前端 `gen:types`）。
- [x] **Step 10 — API：測試**：`backend/tests/test_requirement_field_http.py`（`TestClient`）：十二列 allow／deny 矩陣、回應欄位集合（`team.md` 規則 B）、四類 422（錯綁別組、超長值、未宣告代寫組、本體帶 `updated_by`）不回顯唯一標記字串、非整數 `system_id` → 404、`raise_server_exceptions=False` 下的 500 案例；突變驗證（拿掉成員判定 → 「非成員有 `K4.edit`」列紅；拿掉全域 `edit` → 只有 view 的寫入列紅；拿掉待核准檢查 → 待核准列紅），結果記入 `code-summary.md`。`dump_openapi.py --check` 通過。
- [x] **Step 11 — 環境／建置設定**：零新環境變數；`python3 scripts/validate_env_contract.py`、`python3 scripts/validate_repo_contract.py` 通過；前端 `npm run check:types` 通過。
- [x] **Step 12 — 文件與追溯**：`DEPLOY.md` 2.2.9（欄位說明、收斂敘述的重跑行為、部署順序與 `create_all` 的實際行為、上線確認改查 `information_schema`）；`code-summary.md`（§二 的交接與揭露）；`source-manifest.json`；`traceability.json`。

## 四、步驟 ↔ 故事追溯

| 故事／AC | 步驟 |
|---|---|
| `US11.2` `AC11.2.1`（未填以資料決定） | Step 7、8 |
| `US11.2` `AC11.2.2`（錯綁別組即拒、組標題與欄位集合） | Step 7、8、10 |
| `US11.2` `AC11.2.3`（失敗不留半套） | Step 5、8 |
| `US11.3` `AC11.3.1`–`AC11.3.3`（計數同源） | Step 5–8、10 |
| 代寫溯源（`[FD1]`=A，`BR47`） | Step 3、4、6 |

## 五、方法論與 contract 基線的對應

Testing Contract 的 14 步基線中，**Frontend** 層本單元無程式（畫面屬 `U23`），故省略；
**Data model**（Step 3–4）、**Repository**（Step 5–6）、**Business logic**（Step 7–8）、
**API**（Step 9–10）四層依序「實作 → 測試」。方法論未改。

## 六、code-generation Request Changes（2026-10-20）的對照結果

使用者對整站送出 Request Changes，要求修正 `construction/functional-design/merge-blockers.md` 的 19 項，各在所屬單元修正並附測試。逐項對照「單元」欄：**19 項中沒有一項劃給 `requirement-field-service`**，全文對 `requirement-field-service`／`U20`／`K4` 亦零命中（唯一含 `requirements` 字樣的第 8 項指的是 `requirements.md` 的稽核主體要求，劃給 `mcp-bridge`）。

前序單元的修正對本單元的影響：`hierarchy-service` 為 `HierarchyFacade._authorize` 補上待核准檢查（第 3 項相關的缺口）——本單元的授權自 Step 7 起即自行判定待核准（Step 8 的「同進程（`U13` 路徑）的待核准與全域層拒絕」案例鎖住它），不依賴該修正，但兩者現在同形。

因此本計畫**不新增步驟**，本輪只重新查驗既有步驟（Step 1–12）並以 `backend/.venv` 重跑本單元測試（`test_requirement_field_facade`、`test_requirement_field_http`）與 `dump_openapi.py --check`。

## 七、合併前必修第 24 項（2026-10-26 使用者裁決：先修再重審）

**來源**：`construction/functional-design/merge-blockers.md` 第 24 項（code-generation 重做時 review-03 R-01 Major ＋ `DEPLOY.md` 矛盾）。上方第六節「沒有合併前必修劃給本單元」已因第 24 項而過時，保留原文作為歷史紀錄。

- [x] **Step 13 — 業務邏輯：實作 NUL 拒絕**：`_write_authorized` 對含 NUL（`\u0000`）的值拋 `RequirementFieldValidationError`；於 `requirement_field_errors.py` 登錄一則新的固定訊息（不回顯值），router 照既有轉譯回 422。
- [x] **Step 14 — 測試**：`test_requirement_field_http.py`（`TestClient`＋SQLite）新增 NUL 值 → 422 且 `detail` 為該固定訊息的案例；`tests_pg/test_requirement_field_pg.py` 新增真實 PostgreSQL 上 NUL 值不再拋 `DataError`／回 500 的案例。
- [x] **Step 15 — 突變驗證**（只在暫存區副本做）：拿掉 NUL 檢查 → Step 14 兩案皆紅。結果記入 `code-summary.md`。
- [x] **Step 16 — 文件**：把 `DEPLOY.md` 約第 730–732 行改成與同檔 U20 小節（約第 842 行：`create_all` 建表、只缺 COMMENT 與收斂）一致，只改該段。
- [x] **Step 17 — 回歸與收尾**：完整後端套件、`tests_pg`（本機一次性 PostgreSQL 17，綁 127.0.0.1，用完即刪）、`dump_openapi.py --check`、`validate_repo_contract.py`、`validate_env_contract.py` 全綠；`traceability.json` 只更正變為不實的註記；`code-summary.md` 追加第 24 項處置段。
- 追溯：`merge-blockers.md` #24；review-03 R-01；`BR41`–`BR46` 的輸入驗證。

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
