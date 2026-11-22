# 程式碼產生計畫：U2 `u2-iac-ui`

Brownfield。畫面寫在既有 `frontend/`，不寫進 record 目錄，不另開頂層 `/iac` 主路徑。本單元不改 U1 的閘、PBT 核心或 OpenAPI 產生義務。

品質目標是輸入，不調降：D1 請求 timeout ≥ 90s；session／scan／rewrite 的客戶端 timeout 大於 2s；download 大於 5s；切圖或卸載必須 `abort()`，過期回應不寫入 state；殼不為 D1 預熱而擋住既有首屏。達不到就在 `code-summary.md` 寫出缺口，不改門檻、不把測試改成恆真。

## 故事對應

| 步驟 | 對應 |
|---|---|
| 1 | 入口與殼：US1.1、US1.2；路由仍是 `/workspace` |
| 4 | W1 選圖與切圖清空：US1.2、US1.3 |
| 5 | W2 生成：US2.1、US2.3 |
| 6 | W3 掃描：US3.1、US3.2 |
| 7 | W4 改寫清單：US4.1、US4.2 |
| 8 | W5 下載確認與複製：US5.1 |
| 9 | 團隊規則 C：Coming Soon 換成真畫面後的 Playwright |

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

Testing Contract 的 methodology 是 `custom`。順序是：同一變更裡同時交出畫面與 Playwright。不改寫成逐層 TDD 的 Red／Green。資料庫層省略：本單元不碰資料庫。純函式 PBT 省略：generator／scanner／redactor 屬於 `u1-iac-api`。

## 實作步驟

- [x] Step 1 — 殼與入口。在 `frontend/src/pages/WorkspacePage.tsx` 把「生成 IaC 代碼」的 Coming Soon 改成可進入的工作區，無權時 `data-testid="iac-entry"` 為 disabled 並顯示說明。工作區留在 `/workspace`，不新增頂層 `/iac` 路由。步驟可自由點選；footer 只做導覽。互動控制項補上規格裡的 test id。資料抓取沿用既有兩層：純抓取函式不碰 state，呼叫端在 `.then`／`.catch`／`.finally` 更新 state。新元件放 `frontend/src/` 既有頁面語彙，檔名不得含 path part `secrets`。
- [x] Step 2 — 確認既有測試 runner。在 `frontend/` 確認 `npx playwright test` 仍是 `package.json` 的 `test:e2e` 入口，project 為 `chromium`。本單元指令（寫入 `unit-test-instructions.md`）：`npx playwright test tests/e2e/iac-workspace.spec.ts --project=chromium`。不新增 vitest／jest。
- [x] Step 3 — 遵守 custom ordering。畫面與 Playwright 同一批完成，不把 e2e 留到下一個 PR，也不拆成先寫失敗測試再寫畫面的逐層循環。
- [x] Step 4 — 進入與選圖。Aside 帶活躍圖、`iac-diagram-select`、`iac-diagram-upload`。無圖時主區阻擋並提供回到 Workspace 的 CTA，且不能觸發 D1。切圖時顯示清空提示、清掉本機檢視，進行中的回應不寫回。
- [x] Step 5 — 生成步驟。`iac-file-tree` 與 `iac-hcl-preview` 顯示草稿。`iac-run-d1` 只在有 D1 edit 且有圖時可點。執行時 busy，並顯示 `iac-agent-status`。POST `/api/iac/generate` 必帶 `diagram_id`。失敗顯示 `error.code` 對應文案與重試，並保留先前成功預覽。403 顯示缺權說明。D1 使用 `AbortController`，timeout ≥ 90s。
- [x] Step 6 — 掃描步驟。可自由打開。沒有草稿時顯示空態，且 `iac-run-d2` disabled。POST `/api/iac/scan` 之後，`iac-findings` 以文字標出嚴重度，不單靠顏色。HIGH／CRITICAL 不阻止進入改寫步驟。此路徑 timeout 大於 2s。
- [x] Step 7 — 改寫步驟。可自由打開。沒有成功掃描報告時，執行鈕 disabled 並附說明。POST `/api/iac/secrets/rewrite` 的結果放在 `iac-rewrite-list`，畫面不展示明文。timeout 大於 2s。不把 HCL、改寫前後正文或完整 fetch body 寫進 `console.log`。
- [x] Step 8 — 下載與複製。沒有草稿時 `iac-download` disabled。最新成功掃描含 HIGH／CRITICAL 時，先開 `iac-download-confirm`（dialog、Esc 與取消都不下載，關閉後焦點回到觸發控制項）。確認後才 GET `/api/iac/download`，用 blob 與物件 URL，完成或卸載時 revoke。`iac-copy` 複製目前檔。畫面上沒有 apply 或 destroy。download timeout 大於 5s。
- [x] Step 9 — Playwright。新增 `frontend/tests/e2e/iac-workspace.spec.ts`，以 `page.route` stub `/api/iac/*`，不斷言真實 LLM。至少 8 則：無權入口 disabled、有權進入殼、無圖阻擋、生成成功出現檔案樹與預覽、生成失敗保留舊預覽、掃描空態與嚴重度文字、改寫清單不含注入明文、HIGH 下載確認的取消與確認。每則斷言 test id 與可見文字，不寫「成功」。
- [x] Step 10 — 文件與追溯。撰寫 `code-summary.md`、`source-manifest.json`、`traceability.json`。manifest 列出本單元新增或修改的每個應用程式路徑。追溯的 `OK` target 必須是已存在的檔案。80% 行覆蓋率維持 80；本 repo 前端沒有 coverage 閘，缺口寫進摘要，不把門檻改成 0。

## 測試檔（必做，不延到 Build and Test）

- [x] `frontend/tests/e2e/iac-workspace.spec.ts`
- [x] Test configuration：不新增 runner 設定檔；沿用 `frontend/playwright.config.ts`（見 Step 2）

## 明確不做

- 後端閘、PBT、OpenAPI dump、Checkov、新 Postgres 表。
- 頂層 `/iac` 主路由、apply／destroy 按鈕。
- vitest、jest、前端 unit 測試框架。
- CI 上的 IaC scan job。
- 把 90s、2s、5s 或 80% 改小來讓步驟通過。
