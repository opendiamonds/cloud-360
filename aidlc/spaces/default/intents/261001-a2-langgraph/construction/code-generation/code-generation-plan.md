# Code Generation Plan — A3 Assessment → LangGraph

> Intent `261001-a2-langgraph` · zero-Unit refactor · test-after · Minimal  
> Record: `construction/code-generation/`（stage-level）

## Testing Contract

```json
{
  "version": 1,
  "methodology": "test-after",
  "source": "fallback",
  "ordering": "Implement each testable layer, then write and run that layer's tests.",
  "scope": "refactor",
  "test_strategy": "minimal",
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
    "strategy": "minimal",
    "strategy_volume": [
      "One verifiable test per requirement at the narrowest effective level.",
      "At least one happy-path unit test per component.",
      "Unit tests are the default; a bugfix/security scope floor may require an integration or E2E regression when that is the narrowest level that reproduces the defect."
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
  "input_sha256": "sha256:34eaa5f2115297ad83b888ae0a23f03a42b520033c6c1ccb07e80768043b98da",
  "contract_sha256": "sha256:c26ecd89821206b864abe436997aafc83fe51552a90181338e9843bdf866cdc1"
}
```

## 追溯（FR／BR → 步驟）

| 步驟 | 覆蓋 |
|---|---|
| 0 FD 缺口修補 | R-01／R-02／R-03（BR3.2／BR3.3、retry 狀態機） |
| 1 依賴 | NFR3、langgraph_runtime 前置 |
| 2 Review graph | FR1／FR2／FR3、BR1.1–1.3、BR2.1、BR3.1–3.2 |
| 3 Lens graph | FR1、BR1.1–1.2、BR2.3、BR3.1–3.2 |
| 4 測試 | FR5、BR5.1 |
| 5 SDK／CLI 退場 | FR4、BR4.1 |
| 6 文件／manifest | NFR1.2／BR3.3、source-manifest |

## Step 1 — 專案結構與設定骨架

- [x] 確認不改前端 `AssessmentPage`／路由（BR2.2）
- [x] 在 `backend/requirements.txt` 補上 `langchain-openai`（`langgraph_runtime.openrouter_chat_model` 已依賴；目前未 pin）
- [x] 不新增 OpenAPI 路徑；不改 `review_router` 對外 URL

## Step 2 — 驗證既有測試 runner

- [x] 確認指令可跑：`cd backend && python3 -m unittest tests.test_langgraph_runtime tests.test_review_agent tests.test_wa_lens_engine -v`
- [x] 將本 unit 精確指令寫入 `unit-test-instructions.md`（完成後擴充含新測檔）

## Step 3 — Data model／Repository

- [x] N/A：本輪不改 DB schema／repository（僅執行期邏輯實體）

## Step 4 — Business logic — Review graph（實作）

- [x] 以獨立 compiled graph 重寫 `backend/services/review_agent.py`：`run_review_agent` 對外簽名不變（`AsyncIterator[str]`）
- [x] 經 `langgraph_runtime.openrouter_chat_model(model=get_review_model_name())`；預設 `google/gemini-3.7-flash`（BR1.3）；不得經 `ClaudeSDKClient`
- [x] 串流產出字串增量（token／messages stream 或等價），供 orchestrator 映射 `suggestion_delta`（BR2.1）
- [x] 硬失敗上拋；不得靜默空字串成功（BR3.1）
- [x] 錯誤路徑不得洩漏 API key／token（BR3.2）
- [x] 保留 `fallback_suggestions_from_findings`、prompt 載入等非 SDK helper
- [x] Logger 維持 `cloud360.*`（BR3.3）

## Step 5 — Business logic — Review 測試（test-after）

- [x] 擴充／新增 `backend/tests/test_review_agent.py`（或專檔）：mock LLM／runtime，斷言經 `langgraph_runtime`／`openrouter_chat_model` 且**不** import `claude_agent_sdk`（BR5.1）
- [x] 至少覆蓋：串流增量為 str；無 auth／runtime 失敗時行為與現況相容（上拋或既有 fallback 語意）
- [x] 執行 unit-scoped 指令並綠燈

## Step 6 — Business logic — Lens graph（實作）

- [x] 重寫 `answer_lens_with_agent`（`wa_lens_engine.py`）：獨立 compiled Lens graph；structured output／tool 節點產出 `dict[str, list[str]]`，形狀與 orchestrator 相容（BR2.3）
- [x] 經 `langgraph_runtime`；模型 `get_model_name()`／OpenRouter；不得 MCP `emit_lens_answers`／SDK
- [x] 保留 deterministic helpers（`load_lens`、`score_answers`、heuristic fallback）
- [x] 硬失敗上拋；secret 不進可見錯誤（BR3.1／BR3.2）；logger `cloud360.*`（BR3.3）

## Step 7 — Business logic — Lens 測試（test-after）

- [x] 擴充／新增測檔：mock LLM，斷言 Lens 經 `langgraph_runtime` 且不 import SDK（BR5.1）
- [x] 驗證結構化答案可被 `score_answers`／既有路徑消費；無效 schema → 失敗非假成功
- [x] 執行 unit-scoped 指令並綠燈

## Step 8 — API／endpoint

- [x] 確認 `review_orchestrator`／`review_router`／`wa_collab_orchestrator` **無需**改公開事件契約；僅因 agent 內部替換而冒煙（可選輕量 mock 測試，非新 URL）
- [x] N/A 前端行為層（BR2.2 凍結）

## Step 9 — SDK／Dockerfile 退場（FR4）

- [x] `rg ClaudeSDKClient|claude_agent_sdk backend/` → 應用程式執行期零命中（測試 mock 字串除外）
- [x] 通過後：`backend/Dockerfile` 移除 Node／`@anthropic-ai/claude-code` 安裝；更新過時註解
- [x] 同步 `DEPLOY.md`／`LOCAL-DEV.md` 中與映像 CLI 相關、且因本輪退場而失效的敘述（若有）

## Step 10 — FD 設計缺口修補（審查 R-01～R-03）

- [x] `rules.md` 新增 BR3.2（secret 遮罩）、BR3.3（logger `cloud360.*`）
- [x] `functional-spec.md` 補 retry 狀態轉換（`complete|failed --[retry]--> suggestions`）
- [x] 更新 FD `traceability.json` 對應 NFR2.1／NFR1.2

## Step 11 — 文件與追溯交付

- [x] 寫 `code-summary.md`、`traceability.json`（本 stage）、`source-manifest.json`
- [x] 既有 suite 綠燈：`cd backend && python3 -m unittest discover -s tests -v`（或至少本 unit 指令 + 既有相關測檔）

## 不做

- 不改 A1 Design agent、C1 cost_advice（已 LangGraph）
- 不改 Assessment 前端行為／API URL
- 不新增 production secrets／prod 路徑
