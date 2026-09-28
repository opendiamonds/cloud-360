# Code Generation Plan — credential-pipeline（U4／B3）

> Unit: `credential-pipeline` · kind: **packaging** · 無執行期業務邏輯  
> 上游：NFR Q1–Q5=A；`security-requirements.md`／`tech-stack-decisions.md`；ADR-0018（**已 Accepted**）  
> 測試策略：Standard · methodology：**test-after**（見下方 Testing Contract）

## 前置事實（不重做）

| 項 | 狀態 |
|---|---|
| ADR-0018 | 已成文並 Accepted（`inception/decisions/0018-catalog-price-api-credentials.md`）；`project.md`／`team.md` 已加註 |
| NFR Q5=A | 「code-gen 開頭先寫 ADR」→ **改為確認既有 ADR 完整＋關閉 OQ7**（手法已由 NFR Q1=A＋審閱 R-01 定案） |
| GCP 管線 | `GCP_BILLING_API_KEY` 已在 `deploy.yml`／`render-env.sh`／compose |
| AWS 密鑰 | **尚未**注入；`render-env.sh` 註解仍寫「No AWS account credentials」 |
| R-01 Major | 本計畫 Step 2 必須寫入具體 regex（見 NFR9.1 修訂意圖） |

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

> packaging：Data model／Repository／API／Frontend 層標為 N/A（無對應檔案）；執行時跳過那些 checkbox，不改 methodology。


## 追溯（計畫步驟 ↔ 需求）

| 步驟 | FR／NFR | 說明 |
|---|---|---|
| Step 1 | ADR-0018 §6、OQ7、NFR9.1 | 確認 ADR；定案 regex |
| Step 2–3 | FR11.2、NFR9.1、ADR-0018 §6 | contract 值樣式＋測試／突變 |
| Step 4 | FR11.1、FR5.8、FR5.9、NFR9.2 | AWS 憑證傳遞重建 |
| Step 5 | FR11.3、FR11.4、NFR8.1、NFR9.3 | 文件 |
| Step 6 | C5、FR9.8 增側 | 雙 contract 綠燈 |

---

## Step 1 — 確認 ADR-0018 與關閉 OQ7

- [x] 確認 `0018-catalog-price-api-credentials.md` Status=Accepted；`project.md`／`team.md` 已含 ADR-0018 加註（若缺則補，不重寫整份 ADR）
- [x] 於 ADR §6／Assumptions 將 OQ7 標為 **Closed**：手法＝NFR Q1=A 值樣式（下列 regex）
- [x] **具體偵測條件（R-01）**寫入實作與 ADR／NFR 交叉引用：
  - AWS：`AWS_SECRET_ACCESS_KEY\s*=\s*([A-Za-z0-9/+=]{40})`
  - GCP：`GCP_BILLING_API_KEY\s*=\s*(AIza[0-9A-Za-z\-_]{35})`
  - 維持 `BEGIN PRIVATE KEY` 字串禁令
  - 空值／僅變數名 → 通過

## Step 2 — 修正 `scripts/validate_repo_contract.py`（Business logic）

- [x] 自 `FORBIDDEN_CONTENT_PATTERNS` **移除**對變數名 `AWS_SECRET_ACCESS_KEY` 的裸字串攔截（保留 `BEGIN PRIVATE KEY`；檢視 `AZURE_`／`GOOGLE_` 條是否仍適當）
- [x] 新增值樣式檢查（或擴充 `validate_no_obvious_secrets`）：套用 Step 1 的兩條 regex
- [x] 註解載明：放行變數名、攔密鑰形賦值；對照 ADR-0018 §6／NFR9.1

## Step 3 — 測試（test-after；Standard 5–8 案例）

見 `unit-test-instructions.md`。摘要：

- [x] 新增 `backend/tests/test_repo_contract_secret_patterns.py`（CI discover 路徑）
- [x] 以暫存 git repo + patch `ROOT` 測：變數名通過、40 字元假 AWS secret 賦值失敗、`AIza…` 假 GCP key 失敗、空值通過、`BEGIN PRIVATE KEY` 仍失敗
- [x] **突變驗證**：暫時還原「裸字串禁變數名」邏輯，確認「僅變數名」案例變紅；再還原修正
- [x] 指令：`cd backend && python -m unittest tests.test_repo_contract_secret_patterns -v`

## Step 4 — 重建 AWS 憑證傳遞（Environment／deploy）

- [x] `.github/workflows/deploy.yml`：deploy 與 rollback 的 `render-env.sh` env 增加 `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`（自 GitHub Secrets）
- [x] `deploy/render-env.sh`：刪除／改寫「No AWS account credentials」註解；寫入兩變數（可空）；`$` 檢查迴圈納入 `AWS_SECRET_ACCESS_KEY`（與 GCP 同）
- [x] `deploy/docker-compose.deploy.yml`：backend 服務傳入 `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`；更新註解指向 ADR-0018
- [x] 確認 `docker-compose.test.yml`／CI **不**注入真密鑰（NFR8.1／Q2=A）
- [x] 範本：`backend/.env.example`、`deploy/.env.example` 保留註解變數名、值空

## Step 5 — 文件（Documentation）

- [x] `DEPLOY.md`：Secrets 清單、最小權限（`pricing:GetProducts` 等）、缺憑證可啟動
- [x] `LOCAL-DEV.md`：本機可不設 AWS／GCP 密鑰；禁止把真金鑰寫進版控檔
- [x] 文件明文：log／錯誤不得含 secret **值**（NFR9.3）

## Step 6 — 驗證與交付物

- [x] `python3 scripts/validate_repo_contract.py` → 0
- [x] `python3 scripts/validate_env_contract.py` → 0
- [x] `cd backend && python -m unittest tests.test_repo_contract_secret_patterns -v` → 綠
- [x] `cd backend && python -m unittest discover -s tests -v` → 本 unit 相關綠；全套 346 中 2 FAIL 於既有 `test_pricing_azure`（與本變更無關，見 code-summary）
- [x] 寫 `source-manifest.json`（本 unit 觸及的所有應用／腳本／文件路徑）
- [x] 寫 `code-summary.md`、`traceability.json`

## 不做

- 不實作 U5 查價客戶端／降級／遮罩
- 不引入 Vault
- 不放寬帳單類 API
- 不強制本機持有雲端憑證
- 不在本 unit 改 `pricing_client`／`pricing_sdk` 行為（屬 U5）

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
