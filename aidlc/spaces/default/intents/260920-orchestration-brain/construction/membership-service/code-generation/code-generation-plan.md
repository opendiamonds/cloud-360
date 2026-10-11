# Code Generation 計畫 — `U19 membership-service`

> 本單元是 `service`，`L` size，`embedded`（同一 FastAPI process）。
> 上游設計已全部交付並通過審查：`functional-design`（29 條 `BR`）、
> `nfr-requirements`（29 條 `NFR12.x`）、`nfr-design`（六份）、
> `infrastructure-design`（四份）。本計畫**不重新決定**任何已定案的事，
> 只把它們排成可執行、可勾選、可追溯的步驟。

## 一、本單元要交付什麼

| 類別 | 內容 |
|---|---|
| 新模組 | `MembershipFacade`（授權唯一入口）、`membership_router`（HTTP）、`select_successor`（純函式）、自動改選流程、回填腳本 |
| 改既有 | `backend/models.py`（兩個 ORM model）、`schema_rbac.sql` 的 `J)` 區塊（`cause` 欄）、`backend/scripts/verify_meta_schema.sql`（新斷言）、`user_router.py` 的停用端點（前置檢查 ＋ 顯式 409）、`.github/workflows/ci.yml`（新 job）、`openapi.json`、`frontend/src/types/api.d.ts`、`DEPLOY.md`、`LOCAL-DEV.md` |
| 新測試根 | `backend/tests_pg/`（真實 PostgreSQL 的併發測試；`[ID1]`=A） |
| **不做** | 成員頁畫面（`U24`）、需求欄位讀寫（`U20`／`K-17`）、三張表的建表 DDL（`U18`／`K-15`，本單元只回補 `cause` 一欄） |

## 二、上游約束清單（實作時逐條對照，不得重新解釋）

| 來源 | 條數 | 最危險的幾條 |
|---|---|---|
| `rules.md` 的 `BR1.1`–`BR6.4` | 29 | `BR4.1`（`select_successor` 純函式——違反它會讓 ADR-0006 的 PBT **失去作用對象**）、`BR5.5`（橫幅查詢漏 `cause` 過濾 ⇒ 每次人工改角色都彈錯誤文案的橫幅）、`BR6.2`（漏宣告 409 **不會有任何東西變紅**） |
| `nfr-requirements` 的 `NFR12.1`–`NFR12.29` | 29 | `NFR12.1`（鎖父 `projects` 列）、`NFR12.5`（不改 `SessionLocal`）、`NFR12.18`（建專案與建立者成員列同交易）、`NFR12.24`／`NFR12.25`（回填必須在任何消費端上線前） |
| `K-16`（`contract-summary.md:1611`） | 7 個公開方法 | `resolve_project_role` 回 `None` 即**非成員**（`BR1.6`）；拒絕 raise 領域例外**不是** `HTTPException`（`BR1.5`） |
| ADR-0006 四面向 | 4 | IAM（本單元的核心）、audit logging（稽核列 ＋ 結構化 log 兩個載體）；encryption 本單元無落點；network exposure 有落點但不新增監聽埠 |
| `[FD1]`=A／`[FD2]`=A／`[FD3]`=A／`[N1]`=A／`[N2]`=A／`[N3]`=C／`[ND1]`=A／`[ID1]`=A | 8 | 全部已定案，實作不得偏離 |

### 2.1 三件「違反後 CI 全綠」的事（本單元的靜默失敗面）

1. **漏宣告 409**（`BR6.2`）：FastAPI 不從 `raise HTTPException` 推導狀態碼，故 spec 與前端型別都「正確地」少了它，兩道漂移閘門一致通過。
2. **ORM 與 DDL 的約束／索引不一致**（`infrastructure-specification.md §四之二`）：既有 `T25` 只比對欄位名；約束名、索引名、partial 條件、外鍵有無都在它射程外。
3. **併發守門被繞過**（`[N1]`=A）：`with_for_update()` 在 SQLite dialect 下被**靜默丟棄**（編譯出的 SQL 無鎖子句、無錯誤、無警告），故跑在既有測試路徑上的併發測試驗證的是空氣。

三者各有對應步驟，見下方 Step 10、Step 4、Step 13。

## 三、本單元承接的上游未決項（實作時必須處置，不得當成已解決）

| id | 內容 | 本計畫的處置步驟 |
|---|---|---|
| `OPEN-ND19-5`（blocking） | `U7` 的 `hierarchy_service.create_project`（`:98`）**自己 `db.commit()`**（`:118`），故天真的 `[ND1]`=A 實作是兩個交易，失敗時留下零成員專案——正是 `[ND1]` 要消除的狀態 | Step 9a：交易邊界歸 `U19`；`U7` 的 service 層新增一個**不 commit** 的變體供組合使用 |
| `OPEN-ND19-6` | 鎖等待 WARN 的門檻值未定 | Step 7d：定為模組層常數（**不是**環境變數） |
| `OPEN-N19-4` | 回填腳本是否與 `U18` 的 DDL 腳本合併 | Step 12：**不合併**（`U18` 的腳本目前純 DDL、無資料寫入，而那是它能單一交易並自我終檢的前提） |
| `OPEN-ID19-1` | 兩條建表路徑不等價（`create_all` 建的表無 COMMENT） | Step 4：ORM 逐條對齊 ＋ 擴充一致性測試；COMMENT 差異如實留為已知限制 |
| `OPEN-ID19-2`（blocking） | 回填與第一個消費端之間是**手動步驟邊** | Step 12 ＋ Step 14：`DEPLOY.md §2.2.10` 寫明順序；交接 `delivery-planning` |
| `OPEN-ID19-3` | `LOCAL-DEV.md` 缺本單元引入的隱性本機前置條件 | Step 14b |
| `OPEN-ID19-7` | 四個 log 事件名無機械保護 | Step 7d：定為模組層常數 |

### 3.1 `infrastructure-design` 審查留下的兩項 Minor（**本計畫不改那兩份已凍結的檔案**）

`infrastructure-design` 以 READY 收尾（0 Critical／0 Major／2 Minor），而該 stage 只有一輪審查額度，引擎逐字回覆「Do not ask the reviewer again; include the findings in the approval summary for the human」。兩項都是**用詞精確度**而非設計缺陷：

- **`R-01`**：`cicd-pipeline.md §五之三` 與 `infrastructure-specification.md §五之一` 用「本站實查」描述 `assert_can_deactivate` 在零成員列時的行為，而該函式**尚未落地**——結論由已發布的 `HAVING count(*) = 1` 查詢形狀推導而得（審查已獨立複核推導正確），但「實查」一詞宣稱了未發生的執行。
- **`R-02`**：「覆蓋面不可能靜默消失」一句在首次出現時缺限定詞；`ut` 目前**無任何必要狀態檢查**，故紅燈不擋合併（`OPEN-ID19-6`）。

**本計畫的處置**：兩項隨本 stage 的關卡呈現給使用者，**不就地編輯那兩份檔案**（編輯會使該 stage 的 READY 收據失效而無審查額度可補）。Step 14 的 `code-summary.md` 逐字記載它們仍為開放。

## 四、測試義務（來自 Testing Contract ＋ `team.md` 的 A／B／C 規則 ＋ ADR-0006）

Testing Contract 解析結果為 **`methodology: test-after`**、**`test_strategy: standard`**（每元件 5–8 個測試 ＋ 關鍵邊界的整合測試），scope floor 為「既有測試套件維持綠燈、不另加新測試底線」。故下方步驟一律**先實作該層、再寫並跑該層的測試**，而非 TDD 的 Red-first。

| # | 義務 | 來源 | 落點步驟 |
|---|---|---|---|
| 1 | allow/deny 雙向 `TestClient`（有權 → 2xx、無權 → 403） | `team.md` 規則 A ＋ B 交叉 | Step 10 |
| 2 | 新端點的 status code ＋ `response_model` 欄位集合斷言 | `team.md` 規則 B | Step 10 |
| 3 | 停用端點的 409：狀態碼 ＋ `LastAdminGuardReport` 欄位集合 | `team.md` B ＋ `BR6.2` | Step 10 |
| 4 | 既有兩道保護不得削弱（`:654`／`:676` 的條件與位置） | `BR6.3` | Step 10 |
| 5 | **PBT：`select_successor` 的排列不變性**（blocking） | ADR-0006 ＋ `BR4.1`／`BR4.2` | Step 8 |
| 6 | 聚合查詢 ↔ 逐專案判定的等價測試 | `[N3]`=C／`NFR12.12` | Step 6 |
| 7 | 併發守門三條斷言（真實 PostgreSQL） | `[N1]`=A ＋ `[ID1]`=A | Step 13 |
| 8 | ORM ↔ DDL 一致性擴充（欄位名以外三項） | `team.md`「單一真實來源」 | Step 4 |
| 9 | 前端 e2e（規則 C） | `team.md` 規則 C | **不適用本單元**：成員頁是 `U24`；實測 `frontend/src` 對 `projects` 命中數為 **0**，本單元無前端面 |

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

## 五、實作步驟（依 Testing Contract 的 `plan_profile.steps` 排序；test-after）

### Step 1 — 骨架與例外型別

- [x] 新增 `backend/services/membership_errors.py`：`MembershipForbidden(story_id, action, project_id)`、`MembershipNotFound`、`MissingGlobalPermission`、`LastAdminGuard(projects)`。**全部是領域例外，不得繼承 `HTTPException`**（`BR1.5`）。
- [x] 新增 `backend/services/membership_types.py`：`ProjectRole`（封閉列舉 `project_admin`／`member`，**不含 `project_owner`**）、`MemberSnapshot`（`user_id`／`joined_at`／`role` 三欄，刻意只含挑選所需）、`MemberView`（`user_id`／`display_name`／`role`／`joined_at`）、`LastAdminGuardReport`（`projects: list[{project_id, name}]`）。
- [x] logger：`logging.getLogger("cloud360.membership")`（`team.md` 的新模組一律 `"cloud360.<module>"`）。
- 追溯：`BR1.5`、`BR4.1`、`entities.md` 的四個值物件。

### Step 2 — 驗證測試執行器並記錄本單元的指令

- [x] 確認既有 `python -m unittest discover -s tests -v` 可跑（本單元不引入新測試框架）。
- [x] 確認 `backend/tests_pg/` 這個**新測試根**的指令可跑（需真實 PostgreSQL）。
- [x] 把兩條**本單元專屬**指令寫進 `unit-test-instructions.md`（不得使用 `python -m unittest` 這種全套命令）。
- 追溯：Testing Contract 的 `runner_step`；`runner_ready_before_first_test: true`。

### Step 3 — 資料模型：實作

- [x] `backend/models.py` 新增 `ProjectMember` 與 `ReselectionEvent`，**逐條對齊 `schema_rbac.sql` 的 `J)` 區塊**（完整清單見 `infrastructure-specification.md §四之二` 的十一列表）。三項最容易寫錯的：
  - `ReselectionEvent.project_id` **不得宣告 `ForeignKey`**（`[ND1]`=A：稽核須在專案被刪後存活）；
  - `ix_reselection_events_unack` 必須帶 `postgresql_where` ＋ `sqlite_where`（partial；形狀照既有 `uq_projects_default_per_owner`）；
  - `previous_role`／`new_role` **不得加 `CheckConstraint`**（封閉列舉由應用層 `BR5.4` 承載）。
- [x] `schema_rbac.sql` 的 `J)` 區塊：`reselection_events` 加 `cause VARCHAR(32) NOT NULL` ＋ `CHECK (cause IN ('auto_reselection','manual_role_change'))`（兩個值由 `[FD3]`=A 定案，非未決事項）＋ COMMENT。**直接寫進 `CREATE TABLE`，不需 `ALTER TABLE`**——既有環境尚未跑過 `U18` 的腳本，這個便宜只在腳本尚未執行時成立。
- [x] `backend/scripts/verify_meta_schema.sql`：新增 `cause` 的存在性 ＋ CHECK 斷言。
- [x] **`project.md` 的 blocking 同步**：`DEPLOY.md §2.2.9` 的 `reselection_events` 由「8 欄」改「9 欄」並補該欄語意（只寫 `## 中文版` 半部，沿用 `U18`／`U5` 的既有處置）。
- 追溯：`K-15`、`[FD3]`=A、`BR5.3`、`entities.md`。

### Step 4 — 資料模型：測試（實作後）

- [x] 擴充 `T25` 形狀的一致性測試（新檔或擴充 `test_hierarchy_service.py` 的既有測試），對兩張新表加三項**二元可判**的斷言：
  - `ReselectionEvent.__table__.foreign_keys` 為**空集合**；
  - 兩張表的約束與索引**名稱集合**與 `schema_rbac.sql` 的 `J)` 區塊宣告相等；
  - `ix_reselection_events_unack` 的 `dialect_options` 含 `where` 條件。
- [x] 欄位名集合一致性（沿用 `T25` 既有形狀，涵蓋 `cause`）。
- [x] **已知限制如實記載**：`create_all` 建出的表沒有 COMMENT，而 `verify_meta_schema.sql` 的 12 條斷言只有 `P12` 碰 COMMENT 且只驗 `system_requirement_fields`——兩條建表路徑在 COMMENT 上不等價，影響限本機（`OPEN-ID19-1`）。
- 追溯：`team.md`「單一真實來源」、`OPEN-ID19-1`。

### Step 5 — 資料存取層：實作

- [x] `resolve_project_role` 的查詢：`WHERE project_id = ? AND user_id = ?`，覆蓋者是既有 `uq_project_members_project_user`。**不新增索引**（`performance-design.md §二之二` 的判準）。
- [x] `list_members` 的查詢（含 `display_name`，需 join `users`）。
- [x] **單專案判定函式** `admin_count_after(project_id, 假設的變更) >= 1`——`BR2.1` 的唯一謂詞。
- [x] **聚合版** `assert_can_deactivate`：一次 `GROUP BY project_id HAVING count(*) = 1`，找出該使用者獨任管理者的全部專案（`[N3]`=C）。**不取鎖**（`NFR12.3`：它是跨專案唯讀掃描，取鎖會讓一次停用鎖住該使用者的全部專案）。
- [x] **取鎖輔助函式**：`SELECT ... FOR UPDATE` 鎖父 `projects` 列；多專案時**一律按 `projects.id` 遞增**逐一取鎖（`security-design.md §一之二`）。**不得用 `WHERE id IN (...) FOR UPDATE`**——它的取鎖順序由執行計畫決定、不保證。
- [x] **不改 `backend/database.py`**（`NFR12.5`；判準是該檔 diff 為空）。
- 追溯：`NFR12.1`–`NFR12.3`、`NFR12.8`、`NFR12.10`、`NFR12.11`、`NFR12.13`、`BR2.1`、`BR2.3`。

### Step 6 — 資料存取層：測試（實作後）

- [x] `resolve_project_role`：查得／查無（`None`）兩側。
- [x] `list_members`：欄位集合與排序。
- [x] **等價測試**（`NFR12.12`／`[N3]`=C）：對隨機成員集合比對「聚合查詢的結果」與「逐專案呼叫單專案判定函式的結果」是否相同。它需要資料庫，**故不是 PBT 的作用對象**——與 `select_successor` 不同。可在既有 SQLite 路徑執行（`GROUP BY ... HAVING` 在 SQLite 可用，且**不需要鎖**）。
- 追溯：`NFR12.12`、`BR1.6`、`BR2.1`。

### Step 7 — 業務邏輯：實作

- [x] **7a `select_successor`（純函式）**：簽章只接受 `list[MemberSnapshot]`；**不得注入 session、不得讀任何外部狀態**（`BR4.1`）。排序鍵 `(joined_at, user_id)` 取最小者（`BR4.2`），形狀沿用 `backend/cost/estimate_readers.py:247-251` 的 `best_clouds`。
- [x] **7b `MembershipFacade` 的七個公開方法**（`K-16` 的 `public_interface`）：`resolve_project_role`／`list_members`／`invite_member`／`remove_member`／`change_role`／`assert_can_deactivate`／`select_successor`。每個方法第一個參數為 `principal`，`project_id` 為**具名參數**（`BR1.4`）。授權判定**先於任何讀寫**，失敗即中止（`BR1.5` 的 `hard_rule`）。
  - `invite_member`：**非冪等**（`BR3.3`）；全域權限前置檢查不過 → `MissingGlobalPermission`，且**整個操作在單一交易內**故被拒時不留半套狀態（`BR3.2`／`AC12.5.3`）。
  - `remove_member`：對已非成員**回成功**（`BR3.4`／`[FD2]`=A）。
  - `change_role`：可有**多位** `project_admin`，指定第二位**不得覆寫**第一位（`BR3.5`）；成功時寫稽核列。
  - 三條減少管理者的路徑（停用／自我降級／自我移出）共用**同一個**守門判定，且位於三者**共同上游**（`BR2.1`）。**不另立「至少一位成員」的謂詞**（`BR2.2`）。
- [x] **7c 自動改選流程**：觸發條件是 `project_owner` 的**帳號被停用**（`BR4.4`），在停用**成功之後**才跑。**逐專案獨立交易**，各自取鎖、各自釋放（`scalability-design.md §二`；`BR4.3` 的冪等性使逐專案獨立安全）。冪等：該專案已有 `project_admin`（排除被停用的 owner）則**不執行、不寫事件**（`BR4.3`）。
- [x] **7d 稽核與結構化 log**：
  - 稽核列寫 `ReselectionEvent`，五個事實齊備（`BR5.1`）；**不得只用 `logger.info`**（`BR5.2`）。
  - `cause` 區分兩種來源（`BR5.3`）；`previous_owner_user_id` 在兩種 `cause` 下指不同的人且**這是刻意的**（`BR5.4`）。
  - `acknowledged_at` **只對 `auto_reselection` 有意義**；橫幅查詢**必須同時過濾 `cause = 'auto_reselection'` 與 `acknowledged_at IS NULL`**（`BR5.5`——漏掉 `cause` 過濾會讓每次人工改角色都彈一則文案錯誤的橫幅）。
  - 四個 log 事件名定為**模組層常數**：`membership.denied`（WARN）／`membership.lock_wait`（WARN）／`membership.reselected`（INFO）／`membership.reselect_skipped`（INFO）。欄位見 `observability-design.md §一`；**不得含 token／session／授權標頭**（`NFR12.26`）。
  - 鎖等待門檻：**模組層常數**，不是環境變數（`OPEN-ND19-6`）。
- 追溯：`BR2.1`–`BR2.3`、`BR3.2`–`BR3.6`、`BR4.1`–`BR4.4`、`BR5.1`–`BR5.6`、`NFR12.6`／`NFR12.7`／`NFR12.26`–`NFR12.29`、`AC12.1.1`–`AC12.2.4`、`AC12.4.1`–`AC12.4.4`、`AC12.6.1`–`AC12.6.3`。

### Step 8 — 業務邏輯：測試（實作後）

- [x] **PBT（blocking，ADR-0006）**：`select_successor` 的**排列不變性**——對同一組成員的任意排列，輸出必須相同。以 `hypothesis` 的 `@given` 撰寫（repo 已有 13 個 `@given` 的先例）。**可失敗的性質是排列不變性**，不是「同一組輸入選出同一人」（後者對純函式恆真，是恆真斷言）。
- [x] 守門：三條路徑各自命中與各自放行（`BR2.1`）。
- [x] `invite_member` 的非冪等（`BR3.3`）、`remove_member` 的冪等（`BR3.4`）。
- [x] **多位管理者**：指定第二位後**兩位都能執行管理動作**（`AC12.2.4`／`BR3.5`——這個 Then 子句是為了讓「覆寫第一位」成為可觸發的紅燈）。
- [x] 稽核列的五個事實齊備 ＋ `cause` 正確 ＋ `previous_owner_user_id` 在兩種 `cause` 下的語意（`BR5.1`／`BR5.3`／`BR5.4`）。
- [x] **橫幅查詢的 `cause` 過濾**（`BR5.5`）：人工角色變更**不得**產生橫幅。
- [x] 自動改選的冪等（`BR4.3`）：重跑不產生第二筆事件。
- 追溯：同 Step 7，加 `NFR12.12` 以外的全部業務面 AC。

### Step 9 — API／端點：實作

- [x] **9a `create_project_with_owner`（`[ND1]`=A）**：`MembershipFacade` 新增此方法，先呼叫 `U7` 的 `HierarchyFacade.create_project` 建專案、再寫建立者成員列，**兩者同一交易**（`NFR12.18`／`BR3.1`）。**`OPEN-ND19-5` 的 blocking 前置**：`U7` 的 `hierarchy_service.create_project`（`:98`）在 `:118` 自己 `db.commit()`，故須為它新增一個**不 commit 的變體**供組合使用；交易邊界歸 `U19`。建立路徑**不取鎖**（專案尚不存在，無併發對手）。建立專案的 HTTP 入口改走 `U19`（或 `U7` 的 router 退化為薄委派）。
- [x] **9b `membership_router`**：成員清單／邀請／移出／改角色／橫幅確認的端點。掛在既有 `/api/` 之下，**不新增監聽埠**。全域層仍由既有 `require_story_action` 承載（`BR1.2`，**本元件不重新實作它**）；router 層把領域例外轉 HTTP（`MembershipForbidden` → 403、`LastAdminGuard` → 409）。
- [x] **9c 既有停用端點的擴充**（`BR6.1`）：在 `user_router.py:682` 的 `target_user.is_active = request.is_active` **之前**呼叫 `assert_can_deactivate`；命中回 **409** 並列出那些專案。**三道檢查都必須在 `:682` 之前**，且既有兩道（自我停用守門 `:654`、最後一位可編輯角色的全域管理員守門 `:676`）**照原樣保留**（`BR6.3`）。
- [x] **9d 顯式宣告 409**（`BR6.2`）：`responses={409: {"model": LastAdminGuardReport}}`。**這是本單元唯一「違反後 CI 全綠」的規則**。
- [x] **9e 兩道漂移閘門**：重 dump `openapi.json`（`backend/scripts/dump_openapi.py`）＋ 重跑前端型別產生器並 commit `frontend/src/types/api.d.ts`。兩者**在不同 job 且並行**，各自獨立紅燈。
- 追溯：`BR1.2`、`BR3.1`、`BR6.1`–`BR6.3`、`NFR12.18`、`AC12.3.1`–`AC12.3.3`、`AC12.5.1`–`AC12.5.3`、`K-16` 的 `existing_endpoint_extension`。

### Step 10 — API／端點：測試（實作後）

- [x] **allow/deny 雙向 `TestClient`**：具權限 → 2xx、無權限 → 403，**缺一不可**（`team.md` 規則 A ＋ B 交叉）。
- [x] 新端點的 status code ＋ `response_model` 欄位集合（規則 B）。
- [x] **409 的形狀**：狀態碼 ＋ `LastAdminGuardReport` 的欄位集合（含專案名稱——只給 id 的話畫面無法告知使用者是哪個專案）。
- [x] **`BR6.3` 的三道檢查**：以測試逐一鎖住既有兩道的條件與位置，以及新守門在寫入之前。**沒有這些測試，拿掉這道檢查不會有任何東西變紅**（`logical-components.md §二之二` 把它列為本單元最危險的失效模式）。
- [x] `create_project_with_owner`：成功後必然存在一列 `(project_id, 建立者, project_admin)`；**部分失敗不得留下零成員專案**（`NFR12.18` 的二元判準）。
- [x] 測試檔第一行（或任何應用模組 import 之前）須先匯入 `tests.helpers`——它負責把 `backend/`、`backend/services/` 插進 `sys.path`（**任何環境都必要**），並在 `psycopg` 未安裝時裝 stub（CI 裝了它，故 CI 只走 `sys.path` 那一半）。
- 追溯：`AC12.1.1`–`AC12.1.3`、`AC12.3.1`–`AC12.3.3`、`AC12.5.1`–`AC12.5.3`、`BR6.1`–`BR6.3`。

### Step 11 — 前端行為：**不適用（genuinely inapplicable，附理由）**

成員頁是 `U24 member-pages-ui`，不是本單元。實測 `frontend/src` 對 `projects` 的命中數為 **0**，故本單元沒有前端消費端。`team.md` 規則 C（前端資料形狀變更需 e2e 斷言）的義務隨成員頁落在 `U24`。

**唯一的前端觸點是 Step 9e 的產生型別檔**，而它是建置產物而非行為。

### Step 12 — 既有專案的回填腳本

- [x] 新增 `backend/scripts/backfill_project_members.py`，沿用 `U18` 的 `[P1]`=A 形狀：獨立腳本、單一交易、**大聲失敗（非零碼）**、不動啟動路徑。
- [x] 內容：對每個 `projects` 列，若該專案無任何 `project_members` 列，則插入一列 `(project_id, owner_user_id, 'project_admin', now())`。
- [x] **冪等**：以「無任何成員列」為條件，故重跑安全。
- [x] **自我終檢**：commit 前斷言「`projects` 中無成員列的專案數為 0」；不為 0 即 rollback ＋ 非零碼。
- [x] **不與 `U18` 的 `run_meta_schema_migration.py` 合併**（`OPEN-N19-4` 定案）：`U18` 的腳本目前純 DDL、無資料寫入，而那是它能單一交易並自我終檢的前提。
- [x] 順序前置：必須在 `U18` 的腳本**之後**（表要先存在），且在**任何消費端上線之前**（`NFR12.25`）。
- 追溯：`NFR12.24`、`NFR12.25`、`OPEN-ID19-2`。

### Step 13 — 環境／建置設定（`[ID1]`=A）

- [x] **新增 `concurrency` job** 於 `.github/workflows/ci.yml`：`needs: gate`、`if: needs.gate.outputs.is_sync != 'true'`（沿用五個既有 job 的同一條件）、自帶 `pgvector/pgvector:pg18` service container、`setup-python@v5`（`python-version: '3.12'`、`cache: pip`、`cache-dependency-path: backend/requirements.txt`）、`psql -f schema_rbac.sql` 一次、**明確的 `timeout-minutes`**。
- [x] job 層 env `DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5432/cloud360`；測試從 `os.environ["DATABASE_URL"]` 讀它，**缺值即大聲失敗，不得退回 SQLite 預設**（退回 SQLite 會讓整個 job 綠燈而鎖從未存在）。
- [x] **新測試根 `backend/tests_pg/`**（含 `__init__.py`，其 docstring 寫明兩個測試根的分工與**為何**真實 PG 測試不能放回 `backend/tests/`）。隔離是**結構性**的：既有 `discover -s tests` 看不到它，故不需任何 env guard。
- [x] 併發測試的三條斷言（順序以 **barrier** 釘住，**不得用 `sleep`**）：
  1. `FOR UPDATE` 真的存在——兩個並行交易對同一專案的成員變更被序列化，守門不被繞過；
  2. 不同專案**不**互相阻塞（`NFR12.13`）；
  3. `assert_can_deactivate` **不**取鎖（`NFR12.3`）。
- [x] 失敗時須印出兩個執行緒各自卡在哪一步（barrier 前／取鎖中／已提交）——只印 `assertEqual` 失敗對診斷無用。
- [x] **不改 `deploy/`**：不動 `deploy.yml`、任一 compose、`nginx.conf`、`render-env.sh`、任一 `.env.example`。判準：`python3 scripts/validate_env_contract.py` 綠燈 ＋ 本單元 diff 不含上列路徑。
- 追溯：`NFR12.1`–`NFR12.4`、`NFR12.13`、`[ID1]`=A。

### Step 14 — 文件與追溯

- [x] **14a `DEPLOY.md`**：新增 §2.2.10（接在 `U18` 的 §2.2.9 之後，使三支腳本的順序在文件上也是順序），含回填腳本的執行步驟與 `psql` 驗證指令；§2.2.9 的欄位數 8→9。**只寫 `## 中文版` 半部。**
- [x] **14b `LOCAL-DEV.md`**（非 blocking，但該規則的存在理由觸發了——本單元是第一個在執行期真的讀寫那兩張表的程式）：既有本機資料庫需跑 `U18` 的腳本與本單元的回填；`backend/tests_pg/` 的本機執行指令；§四之二 的「後端先啟動過會得到無 COMMENT 的表」這個本機專屬陷阱。
- [x] **14c `source-manifest.json`**：列出本單元建立／修改／刪除的**每一個**應用程式碼路徑（含 shell、scaffolding、generator 寫的檔）。
- [x] **14d `traceability.json`**：枚舉 20 條 `AC12.x`、29 條 `NFR12.x`、29 條 `BRx.y`，每個 `OK` 的 target 必須是一個**存在的** workspace 相對路徑。
- [x] **14e `code-summary.md`**：檔案清單、關鍵實作決定、測試覆蓋摘要、與計畫的偏離，以及 §三之一 兩項仍開放的 Minor。

## 六、步驟 → 故事追溯

| Step | 故事／AC | 說明 |
|---|---|---|
| 1、2 | （基礎設施） | 例外型別、值物件、測試執行器 |
| 3、4 | `US12`（資料面） | 兩個 ORM model ＋ `cause` 回補 ＋ 一致性測試 |
| 5、6 | `AC12.1.3`、`AC12.3.1`–`.3` | per-project 判定與守門的查詢層 |
| 7、8 | `AC12.1.1`、`AC12.2.1`–`.4`、`AC12.4.1`–`.4`、`AC12.6.1`–`.3` | 成員生命週期、自動改選、稽核、橫幅 |
| 9、10 | `AC12.1.1`–`.3`、`AC12.5.1`–`.3` | HTTP 面 ＋ 既有端點擴充 |
| 11 | （`U24`） | 不適用，附理由 |
| 12 | `AC12.1.3` 的前提 | 既有專案的擁有者須先成為成員，否則被判為非成員 |
| 13 | `AC12.3.1`–`.3` 的併發面 | `[N1]`=A 選的機制唯一驗得到的地方 |
| 14 | （全部） | 文件、manifest、追溯 |

## 七、完成判準（全部二元可判）

1. `python3 scripts/validate_repo_contract.py` 綠燈；
2. `python3 scripts/validate_env_contract.py` 綠燈；
3. `backend/database.py` 的 diff **為空**（`NFR12.5`）；
4. 既有 `python -m unittest discover -s tests` 全綠（既有套件維持綠燈，scope floor）；
5. 新 `concurrency` job 的三條斷言綠燈，且**每條都做過突變驗證**（把鎖拿掉 → 斷言 1 必須紅燈）；
6. `select_successor` 的 PBT 綠燈，且突變驗證（把 tie-break 改成只按 `joined_at` → 必須紅燈）；
7. `backend/scripts/dump_openapi.py --check` 綠燈，且 `openapi.json` 含 `409` 在停用端點上；
8. 前端型別產生器無漂移；
9. `source-manifest.json` 涵蓋每一個變更路徑（未宣告的變更路徑會擋下 stage 完成）。

