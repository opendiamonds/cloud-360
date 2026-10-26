# 實作計畫 — `U7 hierarchy-service`

> 本計畫涵蓋 29 條業務規則（`rules.md`）、8 個工作流程（`functional-spec.md`
> `W1`–`W8`）、5 個 HTTP path 與 5 項可驗證 NFR（`NFR4.1`／`NFR5.1`／`NFR5.2`／
> `NFR7.1`／`NFR8.1`）。**本單元不擁有 DDL**——三張表與 `user_diagrams.system_id`
> 全部由已交付的 `U4 hierarchy-data` 提供（`schema_rbac.sql:327`–`:420`）。

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
> 其 `plan_profile.testable_layers` 含 `Frontend behavior` 一層，
> **本單元不適用**（零前端，畫面屬 `U23`／`U16`）——理由見
> `unit-test-instructions.md` §四「不寫的測試」。
> `applicable_notes` 的 project 層逐字要求 PBT 為 hard constraint，
> 本單元判為 **N/A（非豁免）**：適用對象為 IaC generator、
> cost calculator／估價表解析器、agent routing，而
> `unit-of-work.md` 全檔對 `U7` 無 PBT 指派、`:448` 只指派給 `U19` 的挑選函式；
> 且本單元**無純函式計算層**（`logical-components.md` §一）。

## 一、開工前的實地查證（已完成，結論影響計畫）

| 查證項 | 結果 | 對計畫的影響 |
|---|---|---|
| 三張表是否有 ORM model | **沒有**。`backend/models.py` 無 `Project`／`System`／`DiagramChangeRecord` 類別 | 必須新增，見 §二 的決定 1 |
| `UserDiagram` 是否有 `system_id` 屬性 | **沒有**（`models.py:91-105` 只有 `id`／`user_id`／`title`／`xml_data`／`updated_at`） | 必須補上映射，否則 `W5` 的系統條件與 `BR6.3` 讀不到該欄 |
| `U4` 用什麼存取資料 | raw `text()`（`hierarchy_migration.py:469-472`），且該檔 `:462` 註明是刻意選擇 | 遷移維持 raw SQL，本單元不改它 |
| router 註冊形狀 | `app.include_router(x_router, prefix="/api/...")`（`main.py:60-69`，9 個既有 router） | 沿用，prefix 為 `/api/hierarchy` |
| 三表的刪除語意 | `systems.project_id` 與 `user_diagrams.system_id` 皆 **ON DELETE RESTRICT**；`diagram_change_records.diagram_id` 為 **CASCADE** | 與 `BR4.3`／`BR4.4`／`BR5.5` 一致，**資料庫會替服務層擋一半**，但錯誤訊息無意義，故服務層仍須先檢查（`BR4.3`／`BR4.4` 要求附數量） |
| DDL 是否需變更 | **不需要**。新增的 ORM model 全部對應**既有**欄位 | **`project.md` 的 `schema_rbac.sql` ＋ `DEPLOY.md` blocking 同步規則不觸發**（無新增／刪除／更名表或欄位、無索引或約束變更、無 seed 語意變更） |

## 二、三個需要你知道的實作決定

### 決定 1：新增 ORM model，而非在服務層寫 raw SQL

**選擇 ORM model**（加進 `backend/models.py`），理由三項：

1. **測試可行性**。`backend/tests/helpers.py` 在任何 DB import 前把 `psycopg2`
   換成 `MagicMock()` 並改走 in-memory SQLite，而 SQLite 的表是由 ORM metadata
   建出來的——**走 raw SQL 的程式在那個測試環境裡沒有表可查**。
   `team.md` 的 B 規則要求 `TestClient` 測試，故 ORM 是唯一能被測的路徑。
2. **三層形狀**。`team.md` 要求新模組走 router → service → 純函式，
   而 service 層以 ORM 查詢才能保持「不碰 SQL 字串」的分層。
3. **`U4` 用 raw SQL 的理由不適用於本單元**。`hierarchy_migration.py:462`
   註明它刻意走 `text()`，因為它只寫 `system_id` 一個欄位且需要
   `WHERE ... IS NULL` 的批次語意；本單元是逐列 CRUD，無此需求。

**代價（如實記載）**：ORM model 的欄位定義與 `schema_rbac.sql` 的 DDL 成為**兩份
物化**。`team.md` 的「單一真實來源」規則要求此時必須有鎖住一致性的測試——
故計畫內含一支 **schema 對齊測試**（見 §四 的 `T9`），比對 ORM metadata 與
`schema_rbac.sql` 的欄位集合。沒有那支測試，這個決定不合規。

### 決定 2：為 `UserDiagram` 補 `system_id` 映射（既有 model 的加法改動）

`W5` 的系統條件篩選與 `BR6.3` 的可見性判定都要讀 `user_diagrams` 的欄位。
該欄**在 DDL 中已存在**（`schema_rbac.sql:373`），缺的只是 ORM 映射。

**這是純加法**：三條建圖路徑（`collab_router.py:517`、`review_router.py:131`／
`:327`）不傳該參數，故行為完全不變——它們仍留 `NULL`，`OPEN-H11` 依然成立。
補映射只是讓**讀取端**能取到它。

**不做的事**：不改那三條建圖路徑。`team.md` 明訂修改既有 router 不得夾帶重構，
且那兩支目前沒有 HTTP 層測試保護。`OPEN-H11` 維持開啟並指向擁有建圖路徑的單元。

### 決定 3：`Principal` 以模組私有 sentinel 實作「不可偽造」（`BR1.4`）

`BR1.4` 要求 principal 只能由授權入口鑄造，使「拿不到 principal 就呼叫不了
facade」成為型別層事實。Python 沒有 package-private，故用標準做法：

```python
_MINT = object()                      # 模組私有，不匯出

@dataclass(frozen=True)
class Principal:
    user_id: int
    role: str
    def __post_init__(self) -> None: ...   # 由 _mint 設定後即不可變

def _mint(user_id: int, role: str) -> Principal: ...   # 僅本模組可呼叫
```

`Principal` 的建構子要求 `_MINT` sentinel，外部模組拿不到它。
**誠實的限制**：這擋得住「誤用」，擋不住刻意的 `module._MINT` 存取——
Python 沒有真正的封裝。`BR1.4` 的 `violation_behaviour` 已如實記載這一點，
本計畫不升級該宣稱。

## 三、要寫的檔案

| # | 檔案 | 動作 | 內容 | 承載規則 |
|---|---|---|---|---|
| 1 | `backend/models.py` | **改**（加法） | 新增 `Project`／`System`／`DiagramChangeRecord` 三個 model；為 `UserDiagram` 補 `system_id` 映射 | 實體形狀對應 `entities.md` |
| 2 | `backend/services/hierarchy_facade.py` | **新** | `Principal` ＋ `_mint`；`HierarchyFacade` 的 8 個方法；4 個例外型別 | `BR1.1`–`BR1.5`、`BR6.1`／`BR6.4`／`BR6.5`、`BR2.4` |
| 3 | `backend/services/hierarchy_service.py` | **新** | DB 讀寫；名稱檢查、刪除前置、列範圍過濾 | `BR2.x`／`BR3.x`／`BR4.x`／`BR5.x`／`BR6.3` |
| 4 | `backend/services/hierarchy_router.py` | **新** | 5 個 path；取身分 → 呼叫 facade → 轉譯例外；**顯式宣告 409** | `W1`／`W2`／`W5`／`W6`／`W7`、`BR6.6`、`NFR5.2` |
| 5 | `backend/main.py` | **改**（一行） | `app.include_router(hierarchy_router, prefix="/api/hierarchy")` | — |
| 6 | `backend/tests/test_hierarchy_service.py` | **新** | 見 `unit-test-instructions.md` | 全部 |
| 7 | `backend/openapi.json` | **重 dump** | `python3 backend/scripts/dump_openapi.py` | `NFR5.1`／`NFR5.2` |

**不動的檔案**（逐一列出，避免事後爭議）：`schema_rbac.sql`、`DEPLOY.md`、
`LOCAL-DEV.md`、`deploy/` 全部、任一 `.env.example`、`render-env.sh`、
`.github/workflows/` 全部、`collab_router.py`、`review_router.py`、
`hierarchy_migration.py`、`services/rbac.py`、`rbac_seed_data.py`。
→ 這同時是 `NFR8.1` 的判準（diff 不含部署設定）。

## 四、facade 的 8 個方法與其規則落點

| 方法 | 類別 | 列範圍 | 規則 |
|---|---|---|---|
| `create_project(principal, name)` | 寫 | 擁有者即請求者 | `BR2.1`／`BR2.3`／`BR3.1`／`BR3.2`、**不需 `BR6.5`**（見 `W1`） |
| `create_system(principal, project_id, name)` | 寫 | **`BR6.5`** | ＋`BR2.2`、`BR6.5` |
| `list_projects(principal)` | 列舉 | **`BR6.1`** | `BR6.1` |
| `list_systems(principal, project_id)` | 列舉 | **`BR6.1`** | `BR6.1` |
| `resolve_work_target(principal, *, project_id, system_id, diagram_id)` | 列舉（使用者路徑） | **`BR6.1`** | `BR1.2`（具名參數）／`BR2.4`（冪等可重試） |
| `delete_project(principal, project_id)` | 寫 | **`BR6.5`** | ＋`BR4.2`／`BR4.4` |
| `delete_system(principal, system_id)` | 寫 | **`BR6.5`** | ＋`BR4.2`／`BR4.3` |
| `record_diagram_change(principal, diagram_id, summary, label)` | 寫 | 圖的擁有者 | `BR5.2`／`BR5.3`／`BR5.4`／`BR5.6`／`BR2.4`（非冪等） |
| `list_diagram_changes(principal, *, label, system_id)` | 列舉 | **`BR6.3`** | `BR5.1`／`BR6.3`／`NFR7.1` |
| `project_exists(principal, project_id)`／`get_project_owner(...)`／`get_project_of_system(...)` | **判定支援型** | **不套列範圍（`BR6.4`）** | `BR6.4` 的三道約束 |

**`BR6.4` 的三道約束如何在程式中成立**：
(1) 同進程——這三個方法**不被任何 router handler 呼叫**（§三 的檔案 4 不 import 它們）；
(2) 最小欄位——回傳型別分別為 `bool`／`int`／`int`，**不回傳 model 物件**；
(3) 呼叫端自檢——以 docstring 明寫，且 `OPEN-H10` 記載本單元無法自驗這一項。

## 五、順序

1. 檔案 1（model）→ 2（facade 與例外）→ 3（service）→ 4（router）→ 5（註冊）
2. 檔案 6（測試）**與實作交錯**：每寫完一組規則即補其測試並跑綠
3. 檔案 7（重 dump `openapi.json`）＋ 顯式 409 宣告的核對
4. 突變驗證（見 `unit-test-instructions.md` §三）
5. 四支 validator ＋ 全套測試複跑

## 六、完成判準（二元，缺一不可）

- [x] `python -m unittest discover -s tests -v` 全綠，且**全套**無迴歸
- [x] `python3 scripts/validate_repo_contract.py` 綠燈
- [x] `python3 scripts/validate_env_contract.py` 綠燈（`NFR8.1`）
- [x] `python3 backend/scripts/dump_openapi.py --check` 綠燈（`NFR5.1`）
- [x] `openapi.json` 中五個 path 皆存在，且衝突端點的 responses 含 `409`（`NFR5.2`）
- [ ] 突變驗證逐項 RED，零存活
- [ ] `git diff --stat` 不含 §三「不動的檔案」清單中的任何一項（`NFR8.1`）

## 七、code-generation Request Changes（2026-10-20）的對照結果

使用者對整站送出 Request Changes，要求修正 `construction/functional-design/merge-blockers.md` 的 19 項，各在所屬單元修正並附測試。逐項對照該表「單元」欄：**19 項中沒有一項劃給 `hierarchy-service`**。以 §三 的檔案反查各項的修法落點：
- 第 14 項（成員頁以 403／404 洩漏專案是否存在）劃給 `project-pages-ui`，該頁的可見性判定在 U23 的路徑上，不在本單元 `hierarchy_router.py` 的五個 path；若 U23 修正時需要動本單元檔案，在 U23 的計畫中處理並註明。
- 第 3 項已在 `hierarchy-data` 修正，改的是 `user_router.py`，不觸及本單元檔案。

因此本計畫**不新增步驟**，本輪只重新查驗 §六 的七項完成判準並跑測試。**判準第 7 項的解讀**：它指的是本單元**自己的變更**（原 commit）不碰「不動的檔案」，以 `git show --stat <本單元 commit>` 判定；本輪工作樹另含其他單元修正必修項時對 `schema_rbac.sql`、`DEPLOY.md`、`LOCAL-DEV.md` 的改動，那些不屬本單元的 diff。完整套件一律以 `backend/.venv` 執行（本機系統 Python 的套件版本與 `requirements.txt` 不一致）。
