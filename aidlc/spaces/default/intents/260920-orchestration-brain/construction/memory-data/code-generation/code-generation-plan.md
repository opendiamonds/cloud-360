# 實作計畫 — `U5 memory-data`

> 本單元是 `spec`：交付 **記憶獨立 schema ＋ grant 邊界 ＋ pgvector `vector(1024)`
> ＋ `embeddingModel` 欄位**。**沒有應用程式碼、沒有端點、沒有畫面。**
> 涵蓋 13 條規則（`BR1.1`–`BR4.3`）＋ 3 項本單元 NFR（`NFR6.1`／`NFR6.2`／`NFR7.2`）。

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

> **本區塊由 `aidlc-testing-posture.ts render` 產生，未經手改。**
> 其 `testable_layers` 列了五層，而本單元**只落在第一層**
> （Data model / database behavior）——`Repository`／`Business logic`／
> `API`／`Frontend` 四層對本單元皆無承載對象（零程式碼、零端點、零畫面）。
> `applicable_notes` 的 project 層要求 PBT 為 hard constraint，本單元判 **N/A
> （非豁免）**：適用對象為 IaC generator、估價表解析器、agent routing，
> 而本單元**沒有任何函式**可施加 property。

## 一、開工前的實地查證（已完成，其中一項推翻了上游的未決前提）

| 查證項 | 結果 | 影響 |
|---|---|---|
| **`OPEN-N5-3`：PG image 是否含 pgvector** | **已解決，且已就緒。** `deploy/docker-compose.deploy.yml:40` 與 `docker-compose.test.yml:51` **皆為 `pgvector/pgvector:pg18`**；該檔 `:36-39` 的註解逐字「PG 18 + pgvector. The `vector` type must exist before any table declaring a `vector(1024)` column is created」 | **不需換 image、不需改部署設定**。`U1 brain-infra` 已處理。`OPEN-N5-3` 由本站關閉 |
| `schema_rbac.sql` 的執行方式 | `:55` 掛載為 `/docker-entrypoint-initdb.d/01-schema_rbac.sql:ro`，**僅在空 volume 執行** | 既有環境的建立路徑仍是 `OPEN-M5`，本站**不自行決定** |
| 既有 `schema_rbac.sql` 的分區慣例 | 以 `-- ###...` 區塊分段並標註擁有單元（如「H) U4 hierarchy-data」） | 新增區塊沿用同形狀 |
| `N-2` 是否已存在 | `ci.yml` **無任何 PostgreSQL service container**——`N-2` 為全新交付物 | 本站必須新建它 |

## 二、要寫的檔案

| # | 檔案 | 動作 | 內容 | 規則 |
|---|---|---|---|---|
| 1 | `schema_rbac.sql` | **改**（新增一個區塊） | `CREATE SCHEMA IF NOT EXISTS memory`；`memory_records` ＋ `memory_audit_events` 兩表；四條 CHECK；**`occurredAt` 索引**；grant；COMMENT | `BR1.1`／`BR1.3`／`BR2.x`／`BR3.x`／`BR4.1`、`NFR7.2` |
| 2 | `DEPLOY.md` | **改** | 更新「這支 SQL 會建立的表／欄位」表；補 `psql` 驗證指令；**載明主機磁碟加密狀態**（`NFR6.1`） | `project.md` blocking |
| 3 | `.github/workflows/ci.yml` | **改**（新增一個 job） | `N-2`：`pgvector/pgvector:pg18` service container ＋ 套用 `schema_rbac.sql` ＋ 執行 SQL 斷言 | `NFR6`、契約 `K-05` `verification` |
| 4 | `backend/scripts/verify_memory_schema.sql` | **新** | `N-2` 執行的斷言腳本（純 SQL，無 Python） | 見 `unit-test-instructions.md` |

**不動的檔案**：`backend/models.py`（本單元**不建 ORM model**——理由見 §三）、
`backend/services/` 全部、`deploy/` 全部（image 已就緒，零新變數）、
任一 `.env.example`、`render-env.sh`、`schema.sql`、`openapi.json`、
`backend/tests/` 全部（SQLite 無 schema 概念，見 §三）。

## 三、兩個與 `U7` 相反的決定

### 決定 1：**不建 ORM model**

`U7` 建了 ORM model，理由是 `tests/helpers.py` 的 in-memory SQLite 由 ORM
metadata 建表，故 ORM 是唯一可被 `TestClient` 測到的路徑。

**本單元恰恰相反**：契約 `K-05` 的 `verification.why_not_existing_tests` 逐字
說明 **SQLite 沒有 schema 概念**，所以那條路徑對本契約**根本不可用**。
建 ORM model 不會讓它變得可測，只會：

- 把兩張表放進 `Base.metadata`，使 `create_all()` 在**每個**既有測試中
  嘗試建立它們（SQLite 會把 `memory.memory_records` 當成一個**含點的表名**
  而非 schema 限定名）；
- 重演 `U7` 踩過的洞——**改變建表的權威**，而這次沒有任何好處。

讀寫記憶屬 `U8 memory-service`（契約 `K-08`）；**它**可以在需要時建 model。

### 決定 2：**驗證完全靠 `N-2`，不碰 `backend/tests/`**

本單元**不新增任何 Python 測試**。斷言寫成純 SQL（檔案 4），
由 `N-2` 對真實 PostgreSQL 執行。這是契約指定的載體，不是退讓。

## 四、`N-2` 這個 CI job 的形狀

```yaml
memory-schema:            # N-2
  runs-on: ubuntu-latest
  services:
    postgres:
      image: pgvector/pgvector:pg18   # 與部署同一個 image
      env: { POSTGRES_PASSWORD: ..., POSTGRES_DB: ... }
      options: --health-cmd pg_isready ...
  steps:
    - 套用 schema_rbac.sql
    - 再套用一次（驗 BR1.3 可重跑）
    - 執行 verify_memory_schema.sql，任一斷言失敗即 exit 1
```

**兩次套用是刻意的**：`BR1.3` 要求可重跑，而「可重跑」只有實際跑兩次才驗得到。

## 五、完成判準（二元）

- [ ] `N-2` job 綠燈，且**兩次**套用 `schema_rbac.sql` 皆成功（`BR1.3`）
- [ ] `verify_memory_schema.sql` 的全部斷言通過
- [ ] `python3 scripts/validate_repo_contract.py` 綠燈
- [ ] `python3 scripts/validate_env_contract.py` 綠燈（本單元零新變數）
- [ ] `cd backend && python3 -m unittest discover -s tests` **無迴歸**
      （基線 497；本單元不新增 Python 測試，故應維持 497）
- [ ] `DEPLOY.md` 含兩張新表、`psql` 驗證指令與主機加密狀態（`NFR6.1`）
- [ ] `git diff --stat` 不含 §二「不動的檔案」清單中的任何一項
