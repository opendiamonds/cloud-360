# 程式碼產生計畫：U1 `u1-iac-api`

Brownfield。應用程式碼寫在 repo 既有的 `backend/`，不寫進 record 目錄，不複製 `*_modified` 檔。本單元不實作 U2 React。

品質目標是輸入，不調降：`POST /generate` p95＜60s、硬逾時 90s；`/session`、`/scan`、`/secrets/rewrite` p95＜2s；`/download` p95＜5s；每進程 generate in-flight ≤2，超出回 429；槽 ≤16 MiB；log 白名單不含 HCL 全文、prompt、JWT。達不到就在 `code-summary.md` 寫出缺口，不改門檻、不把測試改成恆真。

## 故事對應

| 步驟 | 對應 |
|---|---|
| 1 | Unit 邊界：`backend/iac/`、`/api/iac`、無新表 |
| 2 | 測試 runner 既有 `unittest` |
| 4 | US2.2、US2.3、BR1.8、BR1.9（generator）；US3.1、BR1.3（scanner 報告形狀）；US4.1、US5.2、BR1.6、BR1.7（redactor） |
| 5 | BR1.1–BR1.5、BR1.10–BR1.13、US6.1、NFR4.1 |
| 6 | 圖 API 只存 `diagram_id`；agent 走 `langgraph_runtime`，可 stub |
| 7 | OpenAPI drift；Checkov 釘版進既有 backend image；無 CI scan job；無 apply |
| 8 | traceability、source-manifest、code-summary |

## Testing Contract

```json
{
  "version": 1,
  "methodology": "custom",
  "source": "team",
  "ordering": "同一 PR 合併前必須齊備 A／B／C 變更範圍義務，以及已 Affirm 之純函式核心（IaC generator、scanner、redactor）所需的 PBT／突變測試；不得把測試留到後續 PR。",
  "scope": "feature",
  "test_strategy": "standard",
  "project_type": "brownfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. Specific\nmethodology — TDD, BDD, ATDD, or classic test-after — is captured by the\ntesting-strategy stage when it ships.\n\nUntil then, our default per scope is:\n- `mvp`, `enterprise`, `feature`, `infra` → tests written alongside\n  code; minimum 80% line coverage; tests run in CI before merge.\n- `bugfix`, `security-patch` → regression test for the specific\n  bug/vulnerability; existing test suite must remain green.\n- `poc`, `refactor`, `workshop` → existing test suite remains green;\n  no new test floor required.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "- **Methodology**: custom\n- **Ordering**: 同一 PR 合併前必須齊備 A／B／C 變更範圍義務，以及已 Affirm 之純函式核心（IaC generator、scanner、redactor）所需的 PBT／突變測試；不得把測試留到後續 PR。\n\n\n### 既成事實\n\n- **Backend 測試框架**為 Python 內建 `unittest` + `hypothesis` + `unittest.mock`，**未使用 pytest**。CI 以 `python -m unittest discover -s tests -v` 執行（`ci.yml`）。測試 DB 策略見 `backend/tests/helpers.py`：在任何 DB import 前 `sys.modules.setdefault(\"psycopg2\", MagicMock())`，改走 in-memory SQLite，每 session `ensure_role_permissions_seeded(db, force=True)`。規模：`backend/tests/` **本輪覆核（HEAD `0bffc82`）41 個 `test_*.py`**（含 cost／estimate／pricing／langgraph 等；前版「21 個／HEAD `c3de2c8`」已過時）。\n- **Frontend e2e** 為 Playwright（chromium 單一 project），涵蓋登入與 RBAC 可視性；`ui-regression` gh-aw workflow 每 PR 對短生命週期 stack 執行並回報 Kiwi TCMS。**這是真閘門**：`post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`；容忍 `stats.flaky`，`retries: 1`。HEAD 現有 e2e 涵蓋登入、RBAC 與 Admin 等；**本輪覆核：仍無 Story D／IaC 頁 e2e**（D 柱無專屬頁面，僅 Workspace Coming Soon stub）。成本頁現況留待 C 柱既有規則，不在本 intent 覆寫。\n- **Frontend 完全沒有 unit／component 測試框架**：`frontend/package.json` 的 `devDependencies` 只有 `@playwright/test`，無 vitest、無 jest、無 `@testing-library/*`；`scripts` 只有 `test:e2e`。前端的唯一自動化驗證層就是 Playwright e2e。\n- **Property-based testing**：本輪覆核（HEAD `0bffc82`）至少 12 個測試檔含 `@given`（約 19 處），仍集中於純函式模組，屬自發良好實踐。`project.md` ADR-0006 點名的三個 hard-constraint 落點（**IaC generator**、cost calculator、agent routing）中，**IaC generator 在本 repo 仍無對應實作模組**，故該約束對 Story D 現況為 N/A（非豁免、非違反）。**本 intent 一旦落地 IaC generator 純函式核心，ADR-0006 PBT 約束隨即由 N/A 轉為 blocking。**本輪另 Affirm（Q5=B）：**scanner 與／或 redactor 亦列為 PBT 核心**。\n- **HTTP 層 TestClient 現況**：`backend/tests/test_user_list_endpoint.py` 用 `starlette.testclient.TestClient` 測 `/api/auth/list` 分頁欄位（樣板在 `tests/helpers.py`）。樣板仍在 `tests/helpers.py`；本輪覆核另有 `test_estimate_intake_api.py`、`test_me_endpoint.py` 等 TestClient 使用例。**無任何 D1／D2／D3／IaC router 可測**（OpenAPI 零 IaC 條目）。\n- **Story D／IaC 測試完全缺席（本輪焦點）**：無 `test_*iac*`／`test_*terraform*`；`backend/tests/` 對 D1／D2／D3 業務端點 0 命中；`test_rbac.py` 未將 D 柱 allow／deny 當 Story D 落地義務覆蓋。C 柱測試現況已由後續 intent 推進，本檔不覆寫其效力。\n- **完全沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）。`org.md` 宣告的「最低 80% line coverage」目前**既無法量測也無法強制，是宣告而非閘門**。\n- **既有授權測試皆在 service 層**：`test_rbac.py`、`test_j5_authz.py`、`test_review_authz.py` 皆非 HTTP 層測試。\n\n### 本輪新增規則（Q4 定案：A + B + C，D 不採）\n\n依據：本 intent 的六道現有 CI 閘門（`repo-contract`、frontend lint、`tsc -b`、backend import smoke、backend `unittest`、`ui-regression`）逐一查證後，**對「後端漏欄位、序列化成 null、前端渲染成空白」這條失敗路徑全部無效**——不是覆蓋率不足的程度問題，是這條變更路徑上沒有任何自動化斷言存在的有無問題。三項零新依賴的測試底線本輪起生效：\n\n- **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 `role_permissions` 預設值變更，必須有測試同時驗證「該角色能做到」與「其他角色做不到」。零新依賴，直接擴充既有 `test_rbac.py`／`test_j5_authz.py` 形狀。C1 的 RBAC seed 種子已存在（`FinOps_Analyst` 與 C1 相關欄位）；若本 intent 改動 C1 預設值（例如讓架構師 edit 時數），屬 seed 變更，須 A 規則測試。\n- **B — 新增或修改 HTTP 端點需 `TestClient` 測試**：斷言其 status code 與 `response_model` 的欄位集合。採用成本為零——`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，`starlette.testclient.TestClient` 前置條件已滿足；新測試檔放進 `backend/tests/` 即被現有 `python -m unittest discover -s tests` 撿到；`get_db`（`database.py:31`）與 `get_current_user`（`services/auth.py:39`）為穩定的模組層函式，可用 `app.dependency_overrides` 覆寫；以 `TestClient(app)` 直接使用不觸發 `@app.on_event(\"startup\")` 的 `init_db()`，不需要真實 DB。C1 若新增 `/api/cost*` 端點，須依 B 規則補 TestClient 測試，且 CI 的 OpenAPI drift 檢查會要求同步更新 `openapi.json`。\n- **C — 前端資料形狀變更需 e2e 斷言**：例如本次 Admin 表格加欄，須新增至少一個 Playwright case 斷言表頭出現該欄位、且至少一列顯示值或既定的「從未」佔位。用既有 Playwright，不需新依賴，且是目前**唯一**能碰到前端頁面的自動化層。C1 若新建 Cost 頁，資料形狀為全新，須 C 規則 e2e 斷言。\n- **D（不採用）— 引入前端 unit／component 測試框架**：需新增依賴（Vitest 或類似），成本明顯較高，且屬獨立的工具鏈決策，不由本次加欄 feature 夾帶。C 項的 e2e 斷言已覆蓋本 intent 的加欄驗證需求。\n\n- **Q3 定案（A）— C1 HTTP 消費者的最小授權測試義務**：即使 `role_permissions` seed 資料未修改（C1 種子已存在於 `rbac_seed_data.py`），第一個 C1 HTTP 端點落地時仍須補 allow/deny 雙向 TestClient 測試——「具 C1 權限的角色應收到 2xx」與「無 C1 權限的角色應收到 403」兩個案例缺一不可。此為 A 規則與 B 規則的交叉要求，適用於本 intent 新增的任何 `/api/cost*` 端點。\n\n### 80% 覆蓋率門檻的定位\n\n**維持 `org.md` 原文，不在本檔弱化或改寫其宣稱**（把「80% 是目標不是閘門」寫進 `team.md` 會構成 `team.md` 弱化 `org.md` 的矛盾，屬 §13 learning admission 應擋下的形狀）。如實記載目前無法量測、無法強制的現況（見上），並以上述 A/B/C 三項變更範圍內、二元可判、零工具成本的規則作為現階段的實際門檻。導入 `coverage.py` 量測工具列為待補承載機制（見 `discovered-rules.md`）。\n\n---\n\n### Story D 本輪定案（`261105-d-iac-generation`，訪談 Q2–Q6／Q8）\n\n- **既有 A／B／C 對新模組的一般效力（已定案）**：改 D 種子 → A；新增／修改 `/api/iac*`（或等價）→ B；真 UI／資料形狀取代 Coming Soon → C。\n- **Q2 定案（A）— D 柱第一個 HTTP 消費者的最小授權測試**：D1／D2／D3 **任一**故事的第一個 HTTP 消費者落地時，即使 `role_permissions` seed 未改，仍強制 allow／deny 雙向 TestClient（有權 → 2xx、無權 → 403）。此為 A／B 交叉要求，對齊 C1 Q3 形狀；**codekb 若寫「D 已比照 team.md Q3」不可信——該 Q3 僅鎖定 C1。**\n- **Q3 定案（A）— D2 掃描自動化落點**：本 intent 只要求 unittest 測「編排＋報告形狀」（工具／CLI 可 stub）；**不**新增 CI IaC scan job；工具品牌不預填進 Mandated。\n- **Q4 定案（A）— D3 Secret 測試最低線**：D3 落地時強制負向測試＋redaction 突變驗證（注入明文樣式 → 輸出／log／artifact 不得出現該明文；拿掉遮罩 → 測試應紅）；contract 掃描作用域擴大另排、不阻塞本條。\n- **Q5／Q6 交叉 — 決定性核心先於 LLM**：每個故事先有可離線斷言的決定性核心（D1 generator 含 PBT；D2 報告形狀／scanner；D3 redactor）；LLM 編排進手動／TCMS「只能手動」桶。\n- **Q8 定案（A）**：Methodology＝`custom`；Ordering＝同 PR 齊備 A／B／C 與已 Affirm 核心之 PBT／突變義務（見節首）。\n\n\n---"
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
      "Meet an 80% line-coverage floor.",
      "Run the selected tests in CI before merge."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "custom",
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
      "Custom ordering - 同一 PR 合併前必須齊備 A／B／C 變更範圍義務，以及已 Affirm 之純函式核心（IaC generator、scanner、redactor）所需的 PBT／突變測試；不得把測試留到後續 PR。",
      "Implementation and tests - preserve that exact ordering; do not convert it to layer-local TDD.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:d06ac6dc9bf4828b8e1ba07db78cc3f37a0860123ef09faf4f286690938b4d54",
  "contract_sha256": "sha256:42eb5622ff2b532bbad41c230d3ef86a823ebbca9fb6e690145aa4c50af6c7b7"
}
```

## 方法

Testing Contract 的 methodology 是 `custom`。順序是：同一變更裡同時交出實作與 A／B／C、以及 generator／scanner／redactor 的 PBT 與 redactor 突變測試。不改寫成逐層 TDD 的 Red／Green。資料庫層省略：本單元不新增表。前端層省略：UI 屬於 `u2-iac-ui`。

## 實作步驟

- [x] Step 1 — 套件骨架。新增 `backend/iac/`：router、session service、generator／scanner／redactor 純函式、agent port。在既有 FastAPI app 掛上 `/api/iac`。logger 使用 `cloud360.iac`。純函式層不得 import `httpx`、DB session、`HTTPException`。不新增 path part 名為 `secrets` 的路徑。
- [x] Step 2 — 確認既有測試 runner。在 `backend/` 確認 `python -m unittest` 仍是 CI 所用入口。本單元指令（已寫入 `unit-test-instructions.md`）：`python -m unittest tests.test_iac_generator tests.test_iac_scanner tests.test_iac_redactor tests.test_iac_session tests.test_iac_http -v`。不新增 vitest／jest／pytest 設定檔；既有 `unittest` 就是 Test configuration。
- [x] Step 3 — 遵守 custom ordering。測試與實作同一批完成，不把 PBT、突變或 TestClient 留到下一個 PR，也不拆成先寫失敗測試再寫實作的逐層循環。
- [x] Step 4 — 行程內 session 與三個純函式核心，連同測試一起完成。鍵為 `(userId, diagramId)`。generate 失敗保留同圖的既有成功草稿。scan／download 沒有成功草稿回 `missing_draft`。rewrite 需要成功草稿與成功掃描；省略 `report_id` 時用最新成功報告；舊報告回 `stale_report_id`。切圖作廢舊產物。generator 對非主要雲不靜默丟棄。redactor 改寫後的 JSON、log 抽樣與 zip 不得再含注入的明文樣式。scanner 產出報告形狀（允許零 finding、`maxSeverity=NONE`）；Checkov 以可 stub 的子行程呼叫，缺 CLI 時 D2 失敗。測試檔：`test_iac_generator.py`（6 + Hypothesis）、`test_iac_scanner.py`（6 + Hypothesis）、`test_iac_redactor.py`（6 + Hypothesis，並記錄拿掉遮罩後變紅）、`test_iac_session.py`（8，含 16 MiB 與 generate 併發 2）。
- [x] Step 5 — HTTP 與授權，連同 TestClient 一起完成。`POST /generate` 要 D1 edit；`POST /scan` 要 D2 edit；`POST /secrets/rewrite` 要 D3 edit；`GET /session` 要 D1 view；`GET /download` 要 D1 edit。無權 403，不是 404。缺 `diagram_id` 為 422 `missing_diagram_id`。無產物的 session 回 200 且欄位 null。download 不因 HIGH／CRITICAL 拒絕。執行類 POST 不自動重試；逾時 504。第 3 個 in-flight generate 回 429。`test_iac_http.py` 8 則，含 US6.1 成對 403／2xx，並斷言 status 與回應欄位集合。
- [x] Step 6 — Agent 接線。D1／D2／D3 經既有 `langgraph_runtime` 與 OpenRouter，測試以 stub 取代。不新增 Claude-SDK-only 路徑。不代使用者 apply、destroy，也不寫雲端 Secret Manager。讀圖只使用既有公開 API 的 `diagram_id`。
- [x] Step 7 — 環境與建置。更新 `openapi.json`（`backend/scripts/dump_openapi.py`），讓 CI drift 通過。Checkov 釘版裝進既有 backend image，不新增 CI 掃描 job，不新增 compose 服務，不改三環境的 `.env` 契約，除非 LLM 金鑰已有既有鍵。無 Dockerfile 以外的部署 IaC。
- [x] Step 8 — 文件與追溯。撰寫 `code-summary.md`、`source-manifest.json`、`traceability.json`。manifest 列出本單元新增或修改的每個應用程式路徑。追溯覆蓋本單元被指派的 AC、NFR、BR；`OK` 的 target 必須是已存在的檔案。

## 測試檔（必做，不延到 Build and Test）

- [x] `backend/tests/test_iac_generator.py`
- [x] `backend/tests/test_iac_scanner.py`
- [x] `backend/tests/test_iac_redactor.py`
- [x] `backend/tests/test_iac_session.py`
- [x] `backend/tests/test_iac_http.py`
- [x] Test configuration：不新增 runner 設定檔；沿用 `backend/` 的 `unittest`（見 Step 2）

## 明確不做

- React、Playwright、Coming Soon 替換（U2）。
- 新 Postgres 表、`schema_rbac.sql` 變更（本輪不改 D1／D2／D3 seed 時不觸發 schema 同步；若實作時發現必須改 seed，先停下來）。
- 雲端 apply／destroy、Secret Manager 寫入。
- CI 上的 IaC scan job。
- 把 80% 覆蓋率改成 0 或跳過測試來讓步驟通過。
