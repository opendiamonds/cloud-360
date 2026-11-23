# Code Generation Plan — 讓大腦直接建立新的架構圖

## Summary

- Builds: 架構圖草稿狀態（U1）、大腦新建架構圖流程與四種可點選反問（U2）、前端草稿標示與手動存檔轉正式（U3）
- Touches: `backend/services/{collab_router,hierarchy_service,hierarchy_facade,hierarchy_migration,work_orchestrator*,brain_gateway*,brain_ws_contract,intent_routing_decisions,review_router,agent_router,user_router}.py`、新增 `backend/services/brain_diagram_creation.py`、`backend/cost/estimate_intake_router.py`、`schema_rbac.sql`、`DEPLOY.md`、`frontend/src/{projects,components/projects,components/brain,pages/WorkspacePage.tsx}`、`openapi.json` 與產生的前端型別
- Tests: 約 45 個後端測試（unittest＋TestClient＋hypothesis PBT）與 3 個 Playwright e2e 案例

> 來源：`inception/contract-design/contract-summary.md`（修訂 2，C1～C7）、`inception/units-generation/unit-of-work.md`（修訂 1）、`inception/domain-design/decisions.md`（ADR-001～009）、`inception/requirements-analysis/requirements.md`（修訂 2）。本計畫只有一份（引擎以 stage 層級執行），以 U1 → U2 → U3 的單元分段；**三個單元同一批合入 `ut`**（C2 的 `finalize` 與 C6 的新反問都需要 U3 才完整）。
> 追溯以 FR 為鍵（本 intent 沒有 user-stories 站）。分支：`danniel/feat/brain-create-diagram`，自 `origin/ut` 開出。

## Testing Contract

```json
{
  "version": 1,
  "methodology": "test-after",
  "source": "fallback",
  "ordering": "Implement each testable layer, then write and run that layer's tests.",
  "scope": "bugfix",
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
      "Include a targeted regression for the bug or vulnerability.",
      "Keep the existing test suite green."
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
  "input_sha256": "sha256:aef99ad6fb618544581679a6ee06a93014b5527f291df595cb0f99d2034327ac",
  "contract_sha256": "sha256:6405825cd8e861eaedf6dfa972b5b3d7d3f9e62e78a92c2886782f60ced07bef"
}
```

## Steps

### 準備

- [ ] **Step 1 — 分支與結構**：自 `origin/ut` 開 `danniel/feat/brain-create-diagram`（`team.md` 命名）；新增空模組 `backend/services/brain_diagram_creation.py`（ADR-001）。
- [ ] **Step 2 — 驗證測試執行器**：確認 `cd backend && python -m unittest tests.test_diagram_system_attach -v` 可執行且綠燈、`cd frontend && npx playwright test --list` 可列出案例；把各單元的精確指令寫進 `unit-test-instructions.md`。

### U1 diagram-drafts

- [ ] **Step 3 — 資料模型（實作）**：`models.py` 的 `UserDiagram` 加 `status`（`draft`／`ready`，非空、預設 `ready`）；`hierarchy_migration._ensure_hierarchy_schema()` 以 `ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'ready'` ＋ CHECK 補欄位；`schema_rbac.sql` 同步 DDL 與 COMMENT；`DEPLOY.md` 更新欄位表與升級說明（blocking 同步）。〔FR6.1、FR6.5、C3〕
- [ ] **Step 4 — 資料模型（測試）**：遷移在已有資料的 SQLite 上執行後既有圖皆為 `ready`；重跑遷移冪等；非法值被 CHECK 擋下。〔FR6.5〕
- [ ] **Step 5 — 資料存取（實作）**：`hierarchy_service.list_diagrams_of_system` 與 facade 加必填 keyword-only `include_drafts`，回傳 `(diagram_id, title, diagram_status, updated_at)`、依 `updated_at` 降冪再 `id` 降冪；現行呼叫端 `work_orchestrator.py:967` 改為 `include_drafts=True` 並解構四元組；同步 `tests/test_work_orchestrator_store.py:416-426`、`tests/work_orchestrator_fakes.py:336` 與相關斷言；刪除系統（`hierarchy_service.py:212`）、清除預設專案（`user_router.py:438`）、刪除使用者（`user_router.py:651`）三處直接查詢確認不排除草稿；`record_diagram_change` 的 docstring 依 C5 修訂 K-07 並寫明出處。〔FR6.4b、FR6.4c、C5〕
- [ ] **Step 6 — 資料存取（測試）**：不傳 `include_drafts` → `TypeError`；`True`／`False` 各自包含／排除草稿；排序（含同時間 tie-break）；系統下只有草稿時刪除系統被拒；預設專案下只有草稿時不被清除。〔FR6.4b、FR6.4c〕
- [ ] **Step 7 — API（實作）**：`collab_router` 的建圖接受 `as_draft`、存檔接受 `finalize`（預設 false；只把草稿轉正式，不碰已正式的圖）；四支端點補 `response_model`（`DiagramCreated`／`DiagramSaved`／`MyDiagramItem`／`DiagramDetail`，欄位逐一照 C1～C3 的清單）並回 `diagram_status`；分享草稿回 409；定義常數 `DRAFT_REJECTED_DETAIL`，評核（`review_router.py:104`、`:176`）、WA 共編（`agent_router.py:167`）、估價綁圖（`estimate_intake_router.py:116`，**僅當**圖存在、屬於呼叫者且為草稿）共用。〔FR6.1、FR6.2、FR6.4a、C1～C4〕
- [ ] **Step 8 — API（測試）**：TestClient 斷言四支端點的鍵集合等於契約清單（含既有測試 `test_diagram_system_attach.py:108` 改為加入 `diagram_status`）；`as_draft` 建立草稿、不傳則正式；`finalize` true／false／對正式圖無作用；四個 409 入口各一案且資料不變；估價綁他人的圖或不存在的圖維持現況（原樣存入、不回 409）；`require_arch_action("edit")` allow／deny 雙向（NFR5）。〔FR6.2、FR6.4a、NFR5〕
- [ ] **Step 9 — 變更紀錄（實作＋測試）**：facade `record_diagram_change` 以 C5 的摘要「經大腦建立「<名稱>」」與標籤「大腦建立架構圖」寫入；測試斷言寫入一列、`source=brain_orchestration`、摘要非空。〔FR7.1〕

### U2 brain-create-flow

- [ ] **Step 10 — 純函式（實作）**：`brain_diagram_creation.py` 新增 `decide(p, t, target_kind, has_diagrams, has_drafts)`（FR2.2 判定表＋FR6.3a 優先序）與 `make_title(text, system_name, existing_titles)`（指令詞清單、30 個可見字元、去控制字元、空主題退回「<系統名> 架構圖」、重名加「（n）」）；不讀 DB、不連外、不拋 `HTTPException`。〔FR2.1～FR2.4、FR5.1～FR5.4、FR6.3a〕
- [ ] **Step 11 — 純函式（測試，PBT）**：hypothesis 鎖住 FR2.3 四項性質（互斥、不明一定反問、對 p 單調、決定性）與取名性質（長度上限、不含控制字元、不切斷組合字元、與既有名稱不重複）；另以例子測試判定表每一格與 FR6.3a 的優先序。〔FR2.3、FR5、ADR-0006 PBT〕
- [ ] **Step 12 — 路由與 I/O（實作）**：`intent_routing_decisions.build_questions` 加 `wants_new_diagram` 題，併入同一次請求、結果留在行程內；路由觀測事件加判定類別（不含原文與圖名）；`CapabilityClient.create_diagram`（固定 `as_draft=true`）與 `put_diagram(finalize=...)`；`CapabilityError.draft_rejected`、`PHRASES["draft_rejected"]` 與 `failure_for_status` 的 409 分支；工作編排產圖存回時傳 `finalize=True`；BrainDiagramCreation 的 I/O 函式（建草稿、寫變更紀錄，失敗只記 log）。〔FR2.2、FR1.1、FR6.2、FR6.4a、FR7.1、NFR2、NFR4、C4、C7〕
- [ ] **Step 13 — 路由與 I/O（測試）**：路由請求只發一次且帶新題；`draft_rejected` 只在 409 且 detail 等於常數時為 true，回應內容不被保存；`PHRASES["draft_rejected"] == DRAFT_REJECTED_DETAIL`；建圖逾時不重試且不交辦；產圖成功後圖轉正式、失敗則維持草稿。〔FR6.2、FR6.3、C4、C5 錯誤表〕
- [ ] **Step 14 — 閘道（實作）**：`brain_ws_contract.py` 的 `ClarifyPayload.kind` 加四個值、`ClarifyCandidate` 加選填 `systemId`／`diagramId`／`action`；重跑 `dump_ws_contract`；閘道新建流程：`user_can_arch(edit)` 預檢 → 判定 → 建草稿 → `TargetRef.diagram_id` 經 `_set_target_confirmed` 切換 → 交辦；`_reread_target` 比對加入 `diagram_id`；四種反問的候選（上限 10＋新建、排序依 C6）存入 `PendingClarify`，點選時先比對候選集合（`brain_gateway.py:1672`）再經 HierarchyService 重新驗證；名下沒有系統時回覆專案頁路徑。〔FR1.1～FR1.5、FR3.1～FR3.6、FR4.1、FR4.3、FR6.3a、C6、C7〕
- [ ] **Step 15 — 閘道（測試）**：只有系統沒有圖 → 建一張草稿、作業對象切到它、工作項完成後轉正式（FR1.5）；同一工作項重試、復原掃描、再說一次接著畫皆不建第二張（NFR3 三案）；無架構編輯權 → 不建、回說明（NFR5 deny）；四種反問各一案（含點選失效的候選被拒並重列）；`_reread_target` 對圖目標的比對；候選超過 10 筆只列 10 筆並附說明。〔FR1.4、FR1.5、FR3、FR4.1、NFR3、NFR5〕

### U3 draft-ui

- [ ] **Step 16 — 前端（實作）**：`npm run gen:types` 更新 `src/types/api.d.ts`；`MyDiagram` 改由產生型別推導；專案頁「系統的架構圖」、工作區歷史清單、切換對象選單標示「草稿」並加 `data-testid`；`OverviewTab.tsx` 的 `attachedCount` 排除草稿；工作區「儲存架構圖」按鈕送 `finalize: true`，自動存檔與評核前寫回不送；`ClarifyCandidates.tsx` 依四種新 kind 呈現提示文字與按鈕（點選只送 `candidateId`）；遵守 lint 結構約束（資料抓取拆兩層、不就地修改）。〔FR6.2、FR6.4、FR6.4a、FR3.4〕
- [ ] **Step 17 — 前端（測試）**：Playwright 三案——草稿在專案頁清單標示「草稿」且不計入計數；在工作區按「儲存架構圖」後標示消失；大腦送出 `pick_system` 反問時候選可點選並繼續。`npm run lint` 與 `npm run build`（含 `tsc -b`）綠燈。〔FR6.4、FR6.4a、FR6.2、FR3.4、NFR5〕

### 收尾

- [ ] **Step 18 — 建置與契約**：`python backend/scripts/dump_openapi.py` 重產 `openapi.json` 並以 `--check` 確認；`dump_ws_contract --check`；`python3 scripts/validate_repo_contract.py`、`python3 scripts/validate_env_contract.py`；完整後端測試 `cd backend && python -m unittest discover -s tests` 全綠（既有測試保持綠燈）。
- [ ] **Step 19 — 文件與追溯**：`LOCAL-DEV.md`（若動到 `database.py` 啟動補丁）；`code-summary.md` 與 `traceability.json`；commit 與 PR 標題依 ADR-0010 用中文 type。

### 修訂 1（核可關卡要求修改，2026-11-19）

> 來源：審查 `construction/brain-create-flow/code-generation/reviews/review-01.md`（整體）、`review-02.md`（brain-create-flow）、`construction/diagram-drafts/code-generation/reviews/review-01.md`、`construction/draft-ui/code-generation/reviews/review-01.md`。使用者裁決：Major 二採「backend 啟動時只補該欄位」；作業對象是草稿時再說「畫一張」維持「接著畫同一張」（偏差 #2 接受）。

- [x] **Step 20 — 啟動時補欄位（Major）**：新增只補 `user_diagrams.status` 的啟動補丁（比照 `_ensure_last_activity_schema` 的形狀：可重跑、欄位已在即不動、只碰這一欄，不跑整套階層遷移）；`DEPLOY.md` 改寫該欄位的升級說明（不再要求手動跑 `run_hierarchy_migration.py`），回復段補「舊版 backend 看不到草稿狀態、不會擋 409」的提醒；同步 `LOCAL-DEV.md`。測試：已有資料的 SQLite 上啟動補丁執行後既有圖皆為 `ready`、重跑冪等。〔FR6.5〕
- [x] **Step 21 — 建草稿逾時（Major）**：`_create_and_dispatch` 的建圖呼叫加上逾時（沿用閘道既有的逾時工具與設定方式），逾時視為「結果不明」：不重試、不交辦、回覆契約 C5 錯誤表的文字；測試以會卡住的替身斷言逾時後連線仍可處理下一則訊息。〔契約 C5 錯誤表〕
- [x] **Step 22 — 意圖反問後保留機率**：`_on_select` 重建 `IntentDecision` 時帶回 `new_diagram_probability`；測試：系統無圖、意圖反問選定後說要修改 → 走 FR2.4 而非新建。〔FR2.4〕
- [x] **Step 23 — 403 文字分流**：建圖端點回 403 時，只有缺架構編輯權才用「需要架構編輯權」文字；K2 或擁有權的 403 用對應的既有文字；測試兩種 403。〔FR4.1〕
- [x] **Step 24 — 測試強度**：改寫兩條不可能失敗的性質測試（互斥、決定性），使其在 `decide` 被改壞時會紅燈並做突變驗證；新增 `build_brain_gateway` 注入 `diagram_client_factory` 的接線測試。〔FR2.3、FR1.1〕
- [x] **Step 25 — 名稱長度**：`make_title` 另以 code point 上限保證不超過端點的 200 字元限制（含 ZWJ／組合字元輸入）；PBT 補此性質。〔FR5.3〕
- [x] **Step 26 — 前端草稿標示補漏**：`SystemDiagrams` 的「把架構圖掛到…」下拉標示「（草稿）」；評核頁下拉標示草稿，發起評核被 409 拒絕時顯示 `detail` 文字而非原始 JSON；工作區 `Diagram` 介面與 e2e `DiagramStub` 改由產生型別推導；新反問依 kind 提供 `aria-label`，動作型反問的回絕按鈕改為「都不要」；Playwright 補掛圖下拉與評核頁兩個斷言。〔FR6.4、FR6.4a〕
- [x] **Step 27 — 追溯與重測**：`draft-ui` 追溯補 `FR6.2`、`FR6.4a`、`FR3.4`；各單元 `code-summary.md` 補修訂 1 的改動；後端全套、lint、build、契約 `--check`、Playwright 重跑。

## 追溯（FR → Step）

| FR | Step |
|---|---|
| FR1.1～FR1.5 | 12、14、15 |
| FR2.1～FR2.4 | 10、11、12 |
| FR3.1～FR3.6 | 14、15、16、17 |
| FR4.1～FR4.3 | 8、14、15 |
| FR5.1～FR5.4 | 10、11 |
| FR6.1、FR6.5 | 3、4、7 |
| FR6.2 | 7、8、12、13、16、17 |
| FR6.3、FR6.3a、FR6.3b | 10、13、14、15 |
| FR6.4、FR6.4a | 7、8、16、17 |
| FR6.4b、FR6.4c | 5、6 |
| FR7.1 | 9、12 |
| NFR1、NFR2 | build-and-test 量測（本站只確保不多一次模型往返，Step 12、13） |
| NFR3、NFR5 | 8、15、17 |
| NFR4 | 12 |

## 風險與注意

- `response_model` 會靜默丟掉未列的鍵：以 Step 8 的鍵集合斷言把關。
- `list_diagrams_of_system` 回傳形狀變更是唯一的破壞性改動，呼叫端與替身在 Step 5 一併修改。
- NFR1（判定準確率重測）與 NFR2（首字回應 P50）需要真實模型與部署環境，排在 build-and-test，不在本站。
