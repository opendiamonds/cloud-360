# Code Generation Plan — `object-picker-ui`（U16，`kind: ui`）

<!-- Stage: code-generation（Construction 3.5）· Unit: object-picker-ui · Record: 260920-orchestration-brain -->

## 一、範圍

交付 `ContextBar` 內的「切換對象」選單：列出可選的專案與系統、選定即送出 `set_work_target`、在選單內就地建立專案與系統。承載 `US9.2`（`AC9.2.1`、`AC9.2.2`；`AC9.2.3` 依 `F-01` 讀為 **Deferred**，只交付畫面面）。

**零後端、零 DDL、零 seed、零環境變數、零 secret、零 workflow 檔變更、零新依賴。**

## 二、綁定的上游（全部必讀；衝突時以「更正附錄」為準，三份附錄之間以較晚者為準）

| 檔案 | 編號 |
|---|---|
| `../functional-design/functional-spec.md`、`rules.md`、`frontend-components.md` | W1–W6、`BR11`–`BR15`（22 條）、元件與 testid |
| `../functional-design/functional-spec-corrections.md` | `F-01`–`F-08` |
| `../nfr-requirements/*.md` ＋ `nfr-requirements-corrections.md` | `NFR2.160`、`NFR5.160`、`NFR8.160`、`NFR11.160`、`OPN-01`–`OPN-26`；`N-01`–`N-07`（含 `OPN1`=A） |
| `../nfr-design/*.md` ＋ `nfr-design-corrections.md` | 設計與突變 M1–M11；`D-01`–`D-07`（突變增為 M1–M16） |
| `../infrastructure-design/*.md` | 不新增 CI job；三個共用檔的揭露 |

**被附錄取代、實作時不得照原文做的上游內容**（逐條列出以免誤用）：

| 原文 | 取代者 |
|---|---|
| `frontend-components.md` §五之一 `fetchPickerGroups`（一次抓全部、扇出） | `N-02`、`logical-components.md` §一：`fetchProjects`／`fetchSystems` 兩個單一抓取；展開才抓、搜尋時補抓 |
| `frontend-components.md` §四之二「建立成功但 `setWorkTarget` 回 false → 重抓清單」 | `D-03`：不重抓，顯示 `switchError` |
| `frontend-components.md` §八「播報一律 `announce()`」、`BR15.4` | `F-04`：開啟中寫選單內播報區，關閉後才寫頁面 `LiveRegion` |
| `frontend-components.md` §十之一「清單失敗：第二個 `listSystems` 500 → 整體 error」 | `F-05`：只影響該群組 |
| `frontend-components.md` §十之一末句「本單元不擴充 `a11y.spec.ts`」 | `N-06`／`OPN-23`：新增兩個掃描點 |
| `BR12.3`「`user.id` 未決時維持 loading」 | `F-03`／`N-01`／`D-04`：衍生 `identity`，`refreshMe` 一次後轉 failed |
| `performance-design.md` §一之二「冪等讀 state 的 `idle`」 | `D-01`：同步 ref 登記簿 |
| `performance-design.md` §五的備案（卸載清理關閉） | `D-05`：刪除，只用依前值調整 state |

## 三、帶入事項的處置

| 事項 | 處置 |
|---|---|
| `OPEN-OP16-4`：重開 `U14` 的 `ContextBar.tsx` | 只加鈕、`pickerOpen`、衍生可見性、`<section>` 的 `tabIndex={-1}` 與 ref、斷線處置、改寫 `:20` 註解；不動五態判定與名稱節點。跑全部既有 brain e2e |
| `OPN-23`：重開 `U17` 的 `a11y.spec.ts` | 只新增兩個掃描點（選單 `default`、建立表單錯誤態），用既有 `scan()`／`isolate()`；`a11y-baseline.json` 維持空。跑 `U17` 全部 22 個 test |
| `N-03`／`D-06`：修改共用 `frontend/eslint.config.js` | 末端新增一個區塊（選單檔案集合），展開 `WS_SUBPROTOCOL_RESTRICTIONS`；既有兩區塊一行不動 |
| 選單檔案集合（`N-03`） | 元件一律以 `ObjectPicker` 開頭：`ObjectPicker.tsx`、`ObjectPickerGroup.tsx`、`ObjectPickerCreateForm.tsx`（`frontend-components.md` 的 `ObjectCreateForm` 改名，使其落入 lint 集合） |
| `D-05` 播報重複字串 | `announce('')` 後以 `setTimeout(…, 0)` 再送文字 |
| `AC9.2.3` | 依 `F-01` 讀為 Deferred；字面裁決交關卡 `G-2` |

## 四、步驟

依 Testing Contract 的 `test-after`：每一層先實作、再寫並跑該層的測試。本單元**沒有資料模型、資料存取、API 層**（零後端），`plan_profile` 中這三層不適用。純函式層（`objectPickerModel`）屬「Business logic」，但前端無 unit 框架（`team.md` D 不採），其測試以 e2e 承擔，在 Step 7 一併寫並跑。

- [x] **Step 1 — 讀上游並複驗前提（不動程式）**：讀第二節全部檔案；確認 `ContextBar.tsx:20`／`:22`、`brainSession.ts:56-57`、`useBrainConnection.ts:337`、`projectsApi.ts:85-104`、`objectCreateAction.ts:51-86`、`fanoutQueue.ts:49`、`AuthContext.tsx:79-84`、`LiveRegion.tsx:51`、`eslint.config.js:54-97`、`a11y.spec.ts:177-181`／`:711` 與設計檔所述一致。任一不符即停下回報。記下 `N-05` 的三個比較基準（`git hash-object ws-contract.json`、`frontend/package.json` 依賴鍵、`git hash-object frontend/tests/e2e/a11y-baseline.json`）。
- [x] **Step 2 — 驗證測試執行器並記錄單元專屬指令**：依 `unit-test-instructions.md` 以 `npm run build` ＋ `npx vite preview --port 4173 --strictPort` ＋ `BASE_URL=http://localhost:4173` 跑一次既有 `entry-page.spec.ts`，確認攔截層與假大腦可用（不需 Docker）。記錄結果。
- [x] **Step 3 — 純函式層實作（Business logic）**：`frontend/src/brain/objectPickerModel.ts`：`isOwnedByMe`、`rowKey`、`currentRowKey`、`targetIdsForProject`、`targetIdsForSystem`（`String()` 轉換集中於此，`OPN-21`）、`normalize`（NFKC＋trim＋小寫）、`filterGroups`（子字串比對、不用 `RegExp`）。不碰 state、不碰 `fetch`。
- [x] **Step 4 — 純抓取層實作**：`frontend/src/brain/objectPickerData.ts`：`fetchProjects(token)`、`fetchSystems(token, projectId)`，包 `listProjects`／`listSystems`，不碰 state、零主控台。
- [x] **Step 5 — 前端行為實作：`ObjectPicker` 與子元件**：`ObjectPicker.tsx`（dialog、焦點陷阱、搜尋、選單內播報區 `brain-object-picker-live`、`mountedRef`、冪等登記簿 ref（`D-01`）、`expanded`、`backfillStarted`、搜尋補抓佇列與卸載 `cancel()`、衍生 `identity`（`D-04`）、`switchError`、`reloadKey` 只由專案清單重試遞增（`D-03`））；`ObjectPickerGroup.tsx`（專案列、展開鈕 `aria-expanded`／`aria-controls`、系統清單四態、非擁有者說明、「+ 新增系統」）；`ObjectPickerCreateForm.tsx`（`useRef` 單發鎖、經 `objectCreateAction`）。testid 依 `frontend-components.md` §九，另加 `brain-object-expand-{projectId}`、`brain-object-group-retry-{projectId}`、`brain-object-identity-error`、`brain-object-backfill-status`。手機寬度以 `md:` 斷點切換全寬。
- [x] **Step 6 — 前端行為實作：`ContextBar` 擴充**：鈕（`brain-context-switch-object`）、`pickerOpen`、`pickerVisible = pickerOpen && status === 'ready'`、依前值調整 state 清 `pickerOpen`（`D-05`）、斷線時焦點移到 `<section>` 並播報（只在原本可見時）、改寫 `:20` 註解。
- [x] **Step 7 — 前端行為測試：寫並跑 `object-picker.spec.ts`**：沿用 `entry-page.spec.ts` 的假大腦（`routeWebSocket` ＋ `wsFrames.ts` 建構器）與 `page.route`。至少涵蓋：`frontend-components.md` §十之一的 11 列（依第二節取代表修正）、`N-01` 兩情境、`N-02` 的 30 專案請求計數與搜尋命中、`D-01` 的展開與補抓競態、`OPN-02` 晚到回應、`D-02` 的同任務雙送出、`OPN-05`／`D-05` 斷線（含連續兩次）、`OPN-13` 惡意名稱、`OPN-14` 特殊字元、`OPN-15` 主控台計數與儲存鍵、`OPN-21` 字串 id 與「目前」、`NFR2.160` 回推前不變、`NFR11.160` pathname 序列（三頁）、`OPN-16` 404 文案、全形搜尋。請求計數類一律對 preview 執行。跑綠。
- [x] **Step 8 — lint 區塊（Environment/build configuration）**：依 `security-design.md` §一 ＋ `D-06` 在 `frontend/eslint.config.js` 末端新增區塊；`npm run lint` 0 errors、warning 數不增。
- [x] **Step 9 — 無障礙掃描點**：`a11y.spec.ts` 新增兩個掃描點（`logical-components.md` §二），樁化全部 `/api/hierarchy`；跑 `U17` 全部 test 綠，`a11y-baseline.json` 不變。若掃出選單違規，在本單元修（只改選單檔案的無障礙屬性）；選單以外的違規停下回報。
- [x] **Step 10 — 回歸**：跑 `entry-page.spec.ts`、`entry-page-live.spec.ts` 與其他既有 brain 相關 spec 全綠（`OPEN-OP16-4`）。
- [x] **Step 11 — 突變驗證（M1–M16）**：依 `security-design.md` §六 ＋ `D-02`／`D-07`／`D-01` 逐一套用 → 確認紅在預期的檢查（lint 或 e2e） → 還原 → 確認綠。**M9 必須實際看到紅燈**，看不到就改測法（`D-02`）。每條結果記錄。
- [x] **Step 12 — 環境與建置檢查**：`npm run build`（含 `tsc -b`）；`N-05` 三個比較基準完工後重取並比對相同；`python3 scripts/validate_repo_contract.py`、`python3 scripts/validate_env_contract.py` 通過；`git diff --stat` 中 `backend/`、`deploy/`、`.github/` 零變更。
- [x] **Step 13 — 規格註解（`test-case-authoring.md` §4.4）**：`object-picker.spec.ts` 每個 `test()` 前加 `@purpose`／`@given`／`@step`／`@pass`／`@ui`／`@story`（`US9.2`）／`@note`；`@ui` 只用 `App.tsx` 實有路由（`/`、`/workspace`、`/assessment`）；**不寫 `@api`**（全部攔截，寫了是假端點）。`describe` 名稱定為 `U16 object picker`，合併後不得再改。
- [x] **Step 14 — 文件與追溯**：`code-summary.md`（第三節各事項結果、三個重開檔的改動清單、`D-05` 採用寫法的 lint 實證、突變結果、比較基準、關卡事項 `G-1`–`G-6`）、`traceability.json`、`source-manifest.json`。

## 五、交付檔案

| 檔案 | 動作 |
|---|---|
| `frontend/src/brain/objectPickerModel.ts`、`objectPickerData.ts` | 新 |
| `frontend/src/components/brain/ObjectPicker.tsx`、`ObjectPickerGroup.tsx`、`ObjectPickerCreateForm.tsx` | 新 |
| `frontend/src/components/brain/ContextBar.tsx` | 改（`U14` 的檔） |
| `frontend/eslint.config.js` | 改（共用設定，末端加區塊） |
| `frontend/tests/e2e/object-picker.spec.ts` | 新 |
| `frontend/tests/e2e/a11y.spec.ts` | 改（`U17` 的檔，加兩個掃描點） |

## 六、ADR-0006 四面向與 PBT

沿用 `security-design.md` §七、§八：IAM 適用（呈現層，伺服器仍是授權點）；Encryption、Network exposure、Audit logging 不適用；PBT 不適用（三個純函式以 e2e 例子驗證）。

## 七、揭露（核可前請看）

1. **會修改三個不屬本單元的檔**：`U14` 的 `ContextBar.tsx`、`U17` 的 `a11y.spec.ts`、共用的 `eslint.config.js`（範圍見第三節）。
2. **多處上游設計被更正附錄取代**（第二節第二張表）；實作照附錄，不照原文。
3. **`AC9.2.3` 讀為 Deferred**：只交付畫面面；字面與 `U7` 實作的矛盾交關卡（`G-2`）。
4. **斷線時清 `pickerOpen` 的寫法**依審查讀規則原始碼的結論採「依前值調整 state」；仍以 `npm run lint` 實證並記錄。
5. **e2e 只能在本機以 `vite preview` 跑**（無 Docker）；全部走攔截層。
6. **關卡事項**：`G-1` `CreateConfirmCard` 不實作；`G-2` `AC9.2.3` 字面；`G-3` 刪除路徑不存在；`G-4` 新建圖無系統歸屬；`G-5` 成員選不了非自有專案；`G-6` 被移出的建立者看到「請稍後再試」。

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
