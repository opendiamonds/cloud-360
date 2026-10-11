# Code Generation Plan — `U15 memory-page-ui`

> 本計畫把四站設計（functional-design、nfr-requirements、nfr-design、
> infrastructure-design）落成程式，**並一併處置三站審查帶下來、經使用者裁決併入
> 本計畫的修正**（§二）。方法論依下方 Testing Contract 為 `test-after`。

## 一、交付範圍

| # | 交付 | 位置 | 類型 |
|---|---|---|---|
| 1 | 記憶頁 `/memory`（三區檢視 ＋ 逐則刪除） | `frontend/src/pages/MemoryPage.tsx`、`frontend/src/components/memory/` | 新建 |
| 2 | 記憶域非元件模組 | `frontend/src/memory/memoryApi.ts`、`memoryPaging.ts`、`memoryEntry.ts`、`memoryLabels.ts` | 新建 |
| 3 | 路由與 Sidebar 項 | `frontend/src/App.tsx`、`frontend/src/components/Sidebar.tsx` | 修改 |
| 4 | 記憶 API 的「已核准」檢查 | `backend/services/hierarchy_facade.py`、`memory_facade.py`、`memory_errors.py` 或 `memory_types.py`、`memory_router.py` | 修改（`U8` 既有程式，跨單元） |
| 5 | OpenAPI 與前端型別同步 | `openapi.json`、`frontend/src/types/api.d.ts` | 重新產生 |
| 6 | 後端測試 | `backend/tests/test_memory_pending_authz.py` | 新建 |
| 7 | 前端 e2e | `frontend/tests/e2e/memory-page.spec.ts` | 新建 |

**零新依賴、零新環境變數、零 schema 變更、零管線改動**（`infrastructure-specification.md §一`、`cicd-pipeline.md §一`）。

## 二、併入本計畫的審查修正（使用者裁決：帶進 code-generation）

| 來源 | 問題 | 本計畫的處置 | 落在哪一步 |
|---|---|---|---|
| functional-design `R-01`；nfr-design `R-01`／`R-02` | 就地移除 ＋ offset 分頁會漏列；刪空第一頁誤顯示 `empty`；補償重抓的競態以 effect 的 `cancelled` flag 管不到 | 情節記憶區刪除後背景重抓目前頁，**以 `useRef` 序號比對防亂序**（照 `AdminPage.tsx:124-131` 的 `requestSeq` 真正機制，不用 `cancelled` flag）；重抓失敗時**就地顯示**「清單同步失敗，畫面可能不是最新的」並經 `LiveRegion` 播報（照 `AdminPage.tsx:128-130`），不靜默 | Step 8 |
| nfr-design `R-03` | `BR34.4` 字面「不發任何重抓」；`BR34.6` 與背景重抓可能連退兩頁 | **單一頁次調整者**：刪除後只由背景重抓的回應決定頁次（回應為空且 `page > 1` 才退一頁），本地 `filter` 後**不**立即套用 `BR34.6`；頁次已被使用者改動時（序號不符）丟棄該回應。`BR34.4` 的偏離記入 `code-summary.md` | Step 8 |
| nfr-design `R-04` | 補償重抓沒有驗證 | e2e 以 `page.route` 模擬會位移 offset 的伺服器，含「重抓中翻頁」「刪空頁」「重抓失敗」三情境 | Step 10 案例 6–8 |
| nfr-design `R-06`；nfr-requirements `R-08` | 滿 200 則的區刪除一則後標題變成錯的精確數 | 區塊記住「首次回應是否滿載」；滿載過的區刪除後仍顯示「N+ 則」 | Step 7 `zoneCountLabel` |
| functional-design `R-03` | `/me` 失敗時 `user.id` 永遠 `undefined`，頁面無限轉圈 | `useAuth().isLoading` 為 false 且 `user.id` 仍非 number 時，顯示錯誤態與重新整理提示，不轉圈 | Step 8 |
| functional-design `R-02` | INV-3 的捷徑：`U14` 需匯入 `canSeeMemoryEntry` | **實查**：`construction/entry-page-ui/` 目錄**不存在**（`U14` 尚未施工），故本單元先落地 `memoryEntry.ts`，`U14` 屆時匯入。本單元不在 `/brain` 掛捷徑 | Step 7 |
| nfr-requirements `R-01`（Major）；nfr-design `R-05` | 待核准帳號可呼叫記憶 API，讀到他人 `platform` 記憶 | **落點在 facade，不在 router**：`memory_router.py:8-12` 宣告「本層不做任何授權判定」且 `tests/test_memory_contract.py:288` 的 `C3` 機械斷言它；`services/intent_routing.py` 同進程直呼 facade，router 層 dependency 管不到。做法見 Step 3 | Step 3–6 |
| nfr-requirements `R-05` | `SEC-U15-2` 的後端斷言已存在 | 引用 `backend/tests/test_memory_authz.py` 的 `test_A5_…`／`test_A7_…`，不重寫 | Step 4 |

## 三、步驟（`test-after`：逐層實作後補該層測試）

- [x] **Step 1 — 結構骨架**：建 `frontend/src/memory/`、`frontend/src/components/memory/` 目錄；不建任何空檔。
- [x] **Step 2 — 驗證執行器並記錄本單元指令**：執行 `unit-test-instructions.md §二` 的兩條指令，確認後端 `unittest` 可載入既有 `tests.test_memory_authz`、Playwright `--list` 對尚不存在的 spec 回報 0 個測試而非設定錯誤。
- [x] **Step 3 — 後端業務邏輯：已核准檢查（facade 層）**
  - `hierarchy_facade.Principal` 新增欄位 `is_approved: bool`（預設 `True`，置於 `_mint_token` 之後以保持既有位置參數不變）；`mint_principal(user)` 以 `services.rbac.user_is_approved(user)` 填入——**沿用既有判定，不另寫一份**（`team.md` 單一真實來源）。先確認 `hierarchy_facade` import `rbac` 不形成循環；若形成，改為在 `rbac` 之外的既有共用位置取用同一函式，並記入 `code-summary.md`。
  - `MemoryFacade` 新增 `_authorize_approved(principal)`，在 `write`／`search`／`list_records`／`delete`／`widen_scope`／`list_audit_events` 六個公開方法的**第一行**呼叫；不通過時 `memory_service.log_denied(...)` 後 raise `MemoryForbidden(reason=<新增的 pending 理由常數>)`。判定先於任何取列，故不形成存在性 oracle。
  - `HierarchyFacade` **不改**（避免擴大範圍；專案頁的同類缺口另記為交接事項）。
- [x] **Step 4 — 後端業務邏輯測試**：新建 `backend/tests/test_memory_pending_authz.py`（`unittest` ＋ `TestClient` ＋ SQLite，沿用 `test_memory_authz.py` 的 `MemoryAuthzTestBase` 形狀）：
  - pending 帳號對 `GET /records`、`POST /records`、`DELETE /records/{id}`、`PUT /records/{id}/scope`、`GET /audit-events` 皆 **403**；
  - 同一情境改為 approved 帳號 → 對應 2xx（`team.md` A＋B 雙向）；
  - 同進程：以 pending 使用者鑄造的 principal 直呼 `MemoryFacade.list_records` → raise `MemoryForbidden`（覆蓋 `intent_routing.py` 的路徑）；
  - pending 帳號刪除**不存在**的 id 也是 403（證明判定先於取列）；
  - `mint_principal` 對 `authorization_status` 為 `pending`／`rejected`／`approved` 的三個 `User` 給出正確的 `is_approved`。
  - 執行並確認既有 `tests.test_memory_authz`、`tests.test_memory_contract` 仍全綠（`C3` 不得因本步驟而紅）。
- [x] **Step 5 — API 層：回應宣告**：`memory_router.py` 的 `DELETE` 加入 `FORBIDDEN_RESPONSE`；更新該檔頭「`DELETE` 沒有 403」一節，寫明新的 403 來自**身分**（未核准）而非**列**（非擁有者仍收斂為 404），故 `[D1]`=A 的反列舉理由不受影響。其餘四條路由已宣告 403 或依需要補上。重新產生 `openapi.json`（`backend/scripts/dump_openapi.py`）與 `frontend/src/types/api.d.ts`（前端 `gen:types`）。
- [x] **Step 6 — API 層測試**：`python3 backend/scripts/dump_openapi.py --check` 通過；前端型別檢查通過；Step 4 的 `TestClient` 案例覆蓋回應碼。
- [x] **Step 7 — 前端非元件模組**：
  - `memoryApi.ts`：`fetchMemoryRecords(kind, offset, limit)`、`deleteMemoryRecord(id)`（204→`'deleted'`、404→`'already-gone'`、其餘拋例外）；`apiUrl()` ＋ 手寫 `Bearer`；型別取自 `api.d.ts`。
  - `memoryPaging.ts`：`EPISODIC_PAGE_SIZE = 20`、`FULL_ZONE_LIMIT = 200`、`computeEpisodicPage`、`pageAfterEmptyRefetch`、`zoneCountLabel(n, wasFull)`（滿載過即 `N+`）。
  - `memoryEntry.ts`：`canSeeMemoryEntry(auth)`（已登入）。
  - `memoryLabels.ts`：kind → 區標題、kind → test id 片段（`procedure`→`procedural`）、可見範圍 → 文字。
- [x] **Step 8 — 前端元件與頁面**：`MemoryPage`、`MemoryZone`、`MemoryItem`、`DeleteConfirmRow`、`EpisodicPager`；`App.tsx` 新增 `/memory`（`ProtectedRoute`、不包 `CapabilityRoute`）；`Sidebar.tsx` 於 `:209-216` DEMO SCOPE 區塊**之後**新增「我的記憶」（`data-testid="sidebar-memory-link"`，以 `canSeeMemoryEntry` 判定）。實作 §二 的五項修正；遵守 `frontend-components.md` 全部規格（三區固定、`empty`／`error` 可區分、就地確認列、`canDelete` 只決定控件、不過濾、不落地、console 不含內容、文字節點渲染、無 `dangerouslySetInnerHTML`）。
- [x] **Step 9 — 前端靜態檢查**：`npm run lint`（0 error）、`npm run build`（含 `tsc -b`）。另以 `grep` 確認本單元新增檔案中 `localStorage`／`sessionStorage`／`IndexedDB`／`dangerouslySetInnerHTML` 命中為 0。
- [x] **Step 10 — 前端行為測試**：新建 `frontend/tests/e2e/memory-page.spec.ts`（`describe` 固定為 `U15 memory page`），案例見 `unit-test-instructions.md §四`，執行並全綠；每支案例做一次**突變驗證**（把對應修正改回錯的行為、確認紅燈、還原複驗），結果記入 `code-summary.md`。
- [x] **Step 11 — 環境／建置設定**：無新增（驗證 `python3 scripts/validate_env_contract.py` 與 `python3 scripts/validate_repo_contract.py` 通過）。
- [x] **Step 12 — 文件與追溯**：`code-summary.md`（含 `BR34.4` 偏離、跨單元改動 `U8`、`HierarchyFacade` 同類缺口交接）、`source-manifest.json`、`traceability.json`。

## 四、步驟 ↔ 故事追溯

| 故事／AC | 步驟 |
|---|---|
| `US4.2` `AC4.2.1`（要求刪除） | Step 7、8、10 |
| `US4.4` `AC4.4.1`（檢視擁有者欄位） | Step 8、10 |
| `US4.4` `AC4.4.3`（檢視可見範圍） | Step 8、10 |
| `US4.4`（擁有者與可見範圍的伺服器端判定；pending 缺口） | Step 3–6 |
| INV-3（`interaction-spec.md:33`） | Step 7、8 |

## 五、方法論與 contract 基線的對應

Testing Contract 的 14 步基線中，**Data model** 與 **Repository** 兩層本單元無改動（零 schema、`memory_service` 不改），故省略；**Business logic**（Step 3–4）、**API**（Step 5–6）、**Frontend**（Step 7–10）三層依序「實作 → 測試」。方法論未改。

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
