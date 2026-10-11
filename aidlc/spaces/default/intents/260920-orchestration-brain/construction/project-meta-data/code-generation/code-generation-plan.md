# Code Generation 計畫 — `U18 project-meta-data`

## 〇、本單元交付什麼

`spec` 單元：**三張新表的 DDL** ＋ 兩份部署資產的 blocking 同步
＋ `[P1]`=A 定案的獨立遷移腳本（涵蓋 `U5` ＋ `U18`）＋ 真實 PostgreSQL 的 CI 斷言。

**零應用程式碼、零端點、零畫面、零 ORM model。**

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

**本單元適用哪些層**：`plan_profile.testable_layers` 五層中只有
**Data model / database behavior** 適用。Repository／Business logic／API／Frontend
四層在本單元**不存在**（零程式碼、零端點、零畫面），故 `steps` 的對應條目省略。
`methodology` 為 `test-after`，順序照 contract：**先實作該層，再寫並執行該層的測試**。

## 二、實作步驟（依序；每步完成後勾選）

- [x] **Step 1 — 驗證既有測試執行器並記下本單元的確切指令**
      （contract 要求 runner readiness 先於第一個可執行測試步驟；brownfield
      只需驗證不需 bootstrap）。本單元的驗證載體**不是** Python 測試，
      而是對真實 PostgreSQL 執行的純 SQL 斷言，故指令形式為 `psql -f`。
      確切指令記入 `unit-test-instructions.md`。

- [x] **Step 2 — Data model 實作（1/3）：`schema_rbac.sql` 新增 `J) U18 project-meta-data` 區塊**
      三張表 ＋ 索引 ＋ CHECK ＋ 外鍵 ＋ COMMENT，全部 `IF NOT EXISTS`（`BR2.1`）。
      形狀逐一沿用 `U5` 的 `I)` 區塊與 `U4` 的 `H)` 區塊（見 §三的對照表）。

- [x] **Step 3 — Data model 實作（2/3）：`backend/scripts/run_meta_schema_migration.py`**
      `[P1]`=A 的落地：**一支腳本建 `U5` ＋ `U18` 的全部新物件**
      （`memory` schema ＋ 兩張表 ＋ 三張 public 表及其索引／約束／COMMENT／grant）。
      `NFR8.2`–`NFR8.4`：單一交易、自我終檢、非零碼結束、**不動 `database.py`**。

- [x] **Step 4 — Data model 實作（3/3）：`DEPLOY.md` blocking 同步**
      `BR3.3` 的第一次觸發（`K-03` 的 seed 語意變更另算一次，**不可互相替代**）：
      表清單加三張表、`psql` 驗證指令、腳本執行步驟（`NFR8.5`）。

- [x] **Step 5 — Data model 測試（test-after）：`backend/scripts/verify_meta_schema.sql`**
      純 SQL 斷言，結構類 ＋ 行為類分開（形狀沿用 `verify_memory_schema.sql`）。
      斷言清單與突變表見 `unit-test-instructions.md`。

- [x] **Step 6 — CI 接線：擴充既有 `memory-schema` job**
      在既有的「套用兩次 `schema_rbac.sql`」之後加一個步驟執行本單元的斷言檔。
      **刻意不改 job 的 `id` 與 `name:`**，理由見 §四之二（check name 風險）。

- [x] **Step 7 — 突變驗證**：逐條把 DDL 改錯、確認對應斷言紅燈、還原複驗。
      每一項突變都要先確認 **DDL 真的改變了**（`U5` 的 `M1` 踩過「突變本身是 no-op」）。

- [x] **Step 8 — 文件與追溯**：`code-summary.md`、`source-manifest.json`、
      `traceability.json`；並在 summary **逐項揭露**三處上游缺口（§五）。

## 三、三張表的 DDL 形狀（逐欄，含每個決定的來源）

### 3.1 `project_members`

| 欄 | 型別／約束 | 來源 |
|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | repo 慣例（`U4` 的 `projects`／`systems` 皆 `id SERIAL PRIMARY KEY`） |
| `project_id` | `INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE` | `[ND1]`=A |
| `user_id` | `INTEGER NOT NULL REFERENCES users (id)`（**無 `ON DELETE` 子句**） | `[ND1]`=A ＋ `U5` 先例（`memory_audit_events.actor_user_id` 同形）；COMMENT 寫明承接 `OQ-H1` |
| `role` | `VARCHAR(32) NOT NULL` ＋ CHECK `IN ('project_admin','member')` | `K-16` 的 `ProjectRole` |
| `joined_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | `BR1.1`（**不得可為 null**） |
| `invited_by` | `INTEGER REFERENCES users (id)`（可為空） | `entities.md` |

約束與索引：`UNIQUE (project_id, user_id)`（`entity_constraints`）；
`CREATE INDEX ix_project_members_user_id` **不建**，理由見 §四之三。

### 3.2 `reselection_events` — 形狀一對一對照 `U5` 的 `memory_audit_events`

| 欄 | 型別／約束 | 對照 `U5` |
|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | 同 |
| `project_id` | `INTEGER NOT NULL`（**無外鍵**） | 同 `memory_id INTEGER NOT NULL`（刻意無外鍵） |
| `promoted_user_id` | `INTEGER NOT NULL REFERENCES users (id)` | 同 `actor_user_id`（有 FK、無 `ON DELETE`） |
| `previous_owner_user_id` | `INTEGER REFERENCES users (id)`（可為空） | — |
| `previous_role` | `VARCHAR(32)` | 同 `previous_scope` |
| `new_role` | `VARCHAR(32) NOT NULL` | 同 `new_scope` |
| `occurred_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 同 `occurred_at` |
| `acknowledged_at` | `TIMESTAMPTZ`（可為空） | — （`BR1.2`：以**事件**為鍵） |

索引：
- `ix_reselection_events_unack ON (promoted_user_id) WHERE acknowledged_at IS NULL`
  — partial，`security-design.md §四之二` 的設計；慣用法先例 `schema_rbac.sql:341`。
- `ix_reselection_events_project_id ON (project_id)` — 成員詳情頁的變更紀錄讀取端。

### 3.3 `system_requirement_fields`

| 欄 | 型別／約束 | 來源 |
|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | repo 慣例 |
| `system_id` | `INTEGER NOT NULL REFERENCES systems (id) ON DELETE CASCADE` | `[ND1]`=A |
| `agent_group` | `VARCHAR(64) NOT NULL` | `components.md:820`；`K-17` 的 `read_fields` 按它分組 |
| `field_key` | `VARCHAR(64) NOT NULL` | 同上；`K-17` 的 `UnknownFieldKey` 以它為基礎 |
| `value` | `TEXT`（**可為 NULL**） | `BR1.3`／`ADR-015` 的三態模型 |
| `cleared_at` | `TIMESTAMPTZ`（可為空） | `BR1.4` |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | `components.md:820` |
| `updated_by` | `INTEGER NOT NULL REFERENCES users (id)` | `components.md:820`；`K-17` 的 `clear_field` 逐字「記 `clearedAt` **與 `updatedBy`**」 |
| `updated_on_behalf_of` | `INTEGER REFERENCES users (id)`（可為空） | `BR1.5` |

約束：`UNIQUE (system_id, agent_group, field_key)`。
CHECK `ck_system_requirement_fields_cleared_has_null_value`：
`cleared_at IS NULL OR value IS NULL` — 鎖住三態模型的第三態
（「清空」必須 `value` 為 NULL **且** `cleared_at` 有值，`BR1.4`）。

**COMMENT 是 `BR2.2` 的強制項**，須寫明 `[UG:G9]`=A 的三件事：
欄位定義被移除後其值列**保留**、畫面不渲染該組、未填計數只算**當前已宣告**的欄位。

## 四、三個需要你知道的決定

### 4.1 本計畫會補上 `entities.md` 缺的九個欄位

`nfr-design` 查出 `entities.md` 比 `components.md:819`／`:820` 少**九個欄位**
（`ReselectionEvent` 5 個、`SystemRequirementField` 4 個；`ProjectMember` 0 個），
其中六個正是 `FR12.4b` 與 `ADR-015` 點名的稽核事實，而 `AC12.2.2` 的 Then
（「顯示**誰在何時把角色由什麼改為什麼**」）需要其中四個。

`nfr-design` 已把回補**指派**給本站（`OPEN-ND18-1`，severity `blocking-downstream`），
故本計畫依 `components.md` 的欄位清單建表。**不回改 `entities.md`**（已核可上游），
改以 `code-summary.md` 逐項揭露落差。

**不補的後果是具體的**：以 `entities.md` 的兩個欄位建表，成員詳情頁的變更紀錄
沒有任何內容可顯示，`AC12.2.2` 永遠紅燈——而這**不會被任何斷言抓到**，
因為斷言是依 `entities.md` 寫的。

### 4.2 CI job 不改名

Step 6 擴充既有的 `memory-schema` job（它已有 `pgvector/pgvector:pg18` service
與「套用兩次」的步驟），**不改 `id` 也不改 `name:`**。
理由：GitHub 的 check name 取自 job 的 `name:`，改它會改掉 check 名稱，
而 branch protection 的必要檢查若引用舊名就會變成「缺少必要檢查」。
代價是 job 名稱（`Memory schema (real PostgreSQL)`）比它實際涵蓋的範圍窄，
會以註解在 job 內說明。**若你希望改名（或另開獨立 job），請選 Request Changes。**

### 4.3 刻意不建 `project_members.user_id` 的索引

`security-design.md §四之三` 的設計：它成為缺口的兩個條件本輪都不成立
（① 以成員身分列出「我參與的專案」尚未存在——`hierarchy_facade.list_projects`
目前 owner-scoped，是 `[F8/R-02]` 的已核可結果；② 使用者硬刪除行為是 `OQ-H1`、
上游刻意未決）。不需要的索引有寫入成本，故不建，承接站 `U19`。

## 五、要在 `code-summary.md` 揭露的三處上游缺口

| # | 缺口 | 本站處置 |
|---|---|---|
| 1 | `entities.md` 少九個欄位 | DDL 依 `components.md` 建全欄；揭露落差（`OPEN-ND18-1`） |
| 2 | `rules.md` 的 `BR2.3` 寫「四條外鍵」，`[ND1]`=A 後實為三條 | DDL 建三條；揭露（`OPEN-ND18-2`） |
| 3 | **契約 `K-15` 的 `foreign_keys` 同樣列了第四條**（`reselection_events.project_id → projects.id`），而它是 `U19`／`U20` 讀的跨單元契約 | 揭露並指名：這是 `nfr-design` 的審查發現 `R-01`（Major），`nfr-design` 只對 `rules.md` 開了修訂指派而漏了 `K-15`。本站一併揭露，使兩處都在同一份 summary 內可見 |

第 3 項是 `nfr-design` 的 advisory 審查**明確指出而該站未能處置**的那一項
（該站的 review 收據已終結，改檔會使收據失效，故處置落到本站）。

## 六、選項

| 選項 | 內容 |
|---|---|
| **Approve Plan** | 八個步驟與三個決定如上，開始實作。 |
| **Request Changes** | 某項要改。常見的：§四之二 的 CI job 改名與否；§四之一 的九欄回補是否該改由上游先修 `entities.md`；§四之三 的索引是否現在就建。 |
