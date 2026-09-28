# Code Generation Plan — legacy-cost-retirement（U3）

> Unit: `legacy-cost-retirement` · kind: **service**（退場）  
> 上游：FD（Q1=A、Q2=A、Q3=C、Q4–Q6=A）、NFR Q1–Q6=A  
> 測試策略：Standard · methodology：**test-after**（見下方 Testing Contract）  
> **合併閘門**：須與 U8 同批（程序檢查清單）；本計畫可先實作，**不得單獨合進 `ut`／部署**

## 前置事實（不重做）

| 項 | 狀態 |
|---|---|
| HTTP | 移除舊 `cost_router`／diagrams 等；不新增 v1 stub |
| 四表 | rename → `archive_*`，保留 ≥90 天；應用零讀寫 |
| Calculator | 刪 runner／spike；移除 Python `playwright` |
| 保留 | pricing_sdk／client／config／YAML 等 U5 存活集 |
| e2e | 刪／改舊 cost 段（`$86.40`／diagrams） |
| DROP | 另開 chore；本 unit 只 rename＋DEPLOY 記到期 |

## Testing Contract

```json
{
  "version": 1,
  "methodology": "test-after",
  "source": "fallback",
  "ordering": "Implement each testable layer, then write and run that layer's tests.",
  "scope": "c1-estimate-upload-rework",
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
  "input_sha256": "sha256:87df1f81158277f635903b8ee162db69bdcf5c7214ef3b6c2c0cca36106d1019",
  "contract_sha256": "sha256:b133bc796b1a0c526e9100d77dc5b870c0ae09a139b5646ace840a60e7ac3576"
}
```

> 退場型 service：重點在刪除／rename／契約綠；Data model 層＝schema rename；API 層＝移除舊路由；Frontend e2e＝刪舊斷言。

## 追溯（計畫步驟 ↔ 需求）

| 步驟 | FR／BR／NFR | 說明 |
|---|---|---|
| Step 1 | FR9.1、BR9.1 | 移除舊 HTTP |
| Step 2 | FR9.2、BR9.2、Q3=C | archive_* rename 雙軌＋DEPLOY |
| Step 3 | FR9.3、BR9.3 | Calculator＋playwright |
| Step 4 | FR9.4–9.5、BR9.4、FR9.7–9.11 | 存活集護欄、工具鏈、e2e、OpenAPI |
| Step 5 | FR9.8、Q4=A | 舊 env 減項；contract 綠 |
| Step 6 | BR9.5、Q3=A | 交付物＋U8 同批檢查清單 |

---

## Step 1 — 移除舊 HTTP（API）

- [x] `main.py` 取消 `cost_router` 掛載
- [x] 刪除／清空僅服務舊 diagrams 路徑的 router／service／agent 模組（保留 U5 存活集）
- [x] 刪除或改寫 `backend/tests/test_cost_api*.py` 等依賴舊 API 的測試
- [x] 同 PR 重產 `openapi.json`＋前端型別（FR9.10）

## Step 2 — 表 rename（Data model）

- [x] `database.py::_ensure_cost_schema`：四表 `ALTER TABLE … RENAME TO archive_*`（或等價遷移）
- [x] `schema_rbac.sql` 同步
- [x] 移除應用 ORM／查詢對 live 表名的依賴；**不**新增 archive ORM
- [x] `DEPLOY.md`：表對照改 archive_*；記載保留到期日（≥90 天）

## Step 3 — Calculator 與相依

- [x] 刪 `azure_calculator_runner`／`gcp_calculator_*`／相關 spike／fixtures 若僅服務 Calculator
- [x] `requirements.txt` 移除 Python `playwright` 與相關註解
- [x] 刪／改依賴 Calculator 的 unittest（含 live 測試）

## Step 4 — 工具鏈、e2e、orphan

- [x] 修正或刪除 `scripts/warm_aws_pricing_cache.py`
- [x] 處理 `backend/prompts/cost_pricing_agent_system.md` orphan
- [x] `frontend/tests/e2e/regression.spec.ts`：移除／改寫 cost diagrams／`$86.40` 段（U8 未就緒則 skip／刪）
- [x] 確認 `validate_cost_calculator_boundary.py` 仍指向 U1 parser（不得回退）

## Step 5 — 環境變數減項

- [x] 自 `backend/.env.example`、`deploy/.env.example`、`render-env.sh`、compose、deploy.yml 等移除舊 stub／calculator 變數讀取（U4 目錄價憑證保留）
- [x] `python3 scripts/validate_env_contract.py` → 0

## Step 6 — 驗證與交付物

- [x] `python3 scripts/validate_repo_contract.py` → 0
- [x] `cd backend && PYTHONPATH=. python3 -m unittest discover -s tests -v` → 綠（刪改後）
- [x] source-manifest／code-summary／traceability
- [x] **PR 檢查清單**：明示「須與 U8 同批合併／部署」；本 unit 單獨不合 `ut`

## 不做

- 不新增 `/api/cost/v1`（U2）
- 不實作 U8 UI／不單獨部署
- 不 DROP `archive_*`（chore／operation）
- 不刪 U5 存活集；不引入 Alembic
- 不手寫 TCMS（Q6=A）

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-19T20:15:00Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|

### Summary
Code-generation READY after floor reset; empty findings.
