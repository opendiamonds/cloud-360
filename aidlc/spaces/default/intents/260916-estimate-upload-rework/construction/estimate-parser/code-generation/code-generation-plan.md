# Code Generation Plan — estimate-parser（U1）

> Unit: `estimate-parser` · kind: **library**  
> 上游：FD（functional-spec／entities／rules）、NFR Q1–Q6=A；`security-requirements.md`／`tech-stack-decisions.md`  
> 測試策略：Standard · methodology：**test-after**（見下方 Testing Contract）

## 前置事實（不重做）

| 項 | 狀態 |
|---|---|
| 模組路徑 | `backend/cost/estimate_parser.py`、`estimate_validator.py`（＋同套件讀取器） |
| 公開 API | `parse(file_bytes, filename?) → ParseResult`；`validate(parse_result) → MechanicalCheckResult` |
| NFR3.1 | 列 ≤ 50_000；CSV UTF-8 bytes ≤ 32 MiB；XLSX ZIP `file_size` 加總 ≤ 32 MiB |
| NFR3.2 | 例外訊息無絕對路徑／traceback；回傳結構無堆疊 |
| NFR4.1 | ≥3 條 Hypothesis PBT |
| NFR6.1／FR9.6 | 邊界腳本改掃 parser／validator／讀取器 |
| Tech | 標準庫 `csv`；**`openpyxl==3.1.5`** |

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

> library：Data model／Repository／API／Frontend 層標為 N/A（無對應檔案）；執行時跳過那些 checkbox，不改 methodology。重點在 Business logic 與單元測試。

## 追溯（計畫步驟 ↔ 需求）

| 步驟 | FR／NFR／BR | 說明 |
|---|---|---|
| Step 1 | tech-stack Q5 | 釘 `openpyxl==3.1.5` |
| Step 2 | FR2.1–2.3、BR1.*、BR2.*、BR3.1、NFR3.* | `parse`＋讀取器＋資源上限 |
| Step 3 | FR4.*、BR4.* | `validate` |
| Step 4 | FR9.6、BR2.3、BR9.1、NFR6.1 | 邊界腳本多路徑 |
| Step 5 | FR2.4、NFR4.1 | 測試＋PBT |
| Step 6 | C5 | contract／unittest 綠；交付物 |

---

## Step 1 — 依賴（Environment）

- [x] `backend/requirements.txt` 新增 `openpyxl==3.1.5`
- [x] 本機／CI 可 `import openpyxl`（不改 Dockerfile 額外步驟）

## Step 2 — `parse` 與讀取器（Business logic）

- [x] 新增 `backend/cost/estimate_parser.py`：公開 `parse(file_bytes: bytes, filename: str | None = None) -> ParseResult`
- [x] 格式嗅探：副檔名／內容 → `csv`｜`xlsx`（BR1.1）
- [x] 雲別判定 BR1.2；無法對應 → ambiguous＋空 lines（BR3.1）
- [x] AWS／GCP CSV 讀取器（標準庫）；Azure XLSX（openpyxl）
- [x] 列正規化 BR2.1／BR2.2（unidentifiable 保留 rawText）
- [x] 資源上限 NFR3.1；超出 → ambiguous／空 lines，不 raise
- [x] 例外訊息遵守 NFR3.2
- [x] **禁止** import httpx／requests／sqlalchemy／fastapi

## Step 3 — `validate`（Business logic）

- [x] 新增 `backend/cost/estimate_validator.py`：`validate(parse_result) -> MechanicalCheckResult`
- [x] 實作 BR4.1–BR4.4（幣別多數決、負數量、0.5% 對帳、跳過條件）
- [x] 確定性：同輸入同輸出

## Step 4 — CI 邊界腳本（Environment）

- [x] 改寫 `scripts/validate_cost_calculator_boundary.py`：掃 `estimate_parser.py`、`estimate_validator.py` 及 parser 直接 import 的同套件讀取器（若拆檔）
- [x] 目標缺失或禁 import → 非 0；確認 `ci.yml`／repo-contract 仍呼叫此腳本（不刪除）

## Step 5 — 測試（test-after；Standard）

見 `unit-test-instructions.md`。摘要：

- [x] `backend/tests/test_estimate_parser.py`（example + ≥3 PBT）
- [x] `backend/tests/test_estimate_validator.py`（BR4 案例 + PBT）
- [x] 指令：`cd backend && python3 -m unittest tests.test_estimate_parser tests.test_estimate_validator -v`

## Step 6 — 驗證與交付物

- [x] `python3 scripts/validate_repo_contract.py` → 0
- [x] `python3 scripts/validate_cost_calculator_boundary.py` → 0
- [x] 上列 unittest → 綠
- [x] `source-manifest.json`、`code-summary.md`、`traceability.json`

## 不做

- HTTP／上傳／DB／LLM（U2／U7）
- 憑證管線（U4 已完成）
- 查價客戶端（U5）
- TCMS 手寫案（Q6=A → tcms-test-cases）
- pandas／numpy

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
