# Code Generation Plan — `a11y-gate`（U17，`kind: packaging`）

<!-- Stage: code-generation（Construction 3.5）· Unit: a11y-gate · Record: 260920-orchestration-brain -->

## 一、範圍

交付 `@axe-core/playwright` devDependency 與一支 `frontend/tests/e2e/a11y.spec.ts`（21 個 `test()`：18 個掃描點、1 個手機寬度檢查、2 個基準清單檢查）加上 `frontend/tests/e2e/a11y-baseline.json`。違規即讓 `ui-regression` 變紅（`[DM:D6]`=A）。

**本單元沒有使用者故事**（`unit-of-work-story-map.md:122`、`:129`）：它承載的是 `requirements.md` 回補項 **N-9**（無障礙自動掃描機制）。可追溯的上游是 `AC-A11Y.1`／`AC-A11Y.2`（`stories.md:652-653`，`[R7]` WCAG 2.1 AA）與契約 `K-13`／`K-14`／`K-19`／`K-20` 對 `U17` 課的 `test-target` 義務。

## 二、綁定的上游（全部必讀；衝突時以「更正附錄」為準）

| 檔案 | 編號 |
|---|---|
| `../nfr-requirements/security-requirements.md` | `A11Y-S1`–`A11Y-S10` |
| `../nfr-requirements/security-requirements-corrections.md` | `C-01`–`C-08`（取代 S5／S7 的驗證條件、補 S9 規則 5、掃描面 14→18） |
| `../nfr-requirements/tech-stack-decisions.md` | `T-1`–`T-6` |
| `../nfr-design/security-design.md` | 四層結構、突變 `M1`–`M10`、開放項 `OPEN-ND24-1`／`OPEN-MP15-4` |
| `../nfr-design/security-design-corrections.md` | `D-01`–`D-08`（include 目標、逐點互動與定位器、寫檔時機、WebSocket 事前兜底、突變 `M11`／`M12`） |
| `../infrastructure-design/*.md` | 不改 `ui-regression`、不改 `playwright.config.ts`（`D-03` 備案除外）、證據留存缺口 |

## 三、帶入事項的處置（逐條）

| 事項 | 處置 |
|---|---|
| `UG-5`／`H-1`：`/admin/*` 是否納入掃描的重審 | **維持不掃**（`[DM:D11]`=A）。重審依據：§27 的錯誤態渲染在 `AdminPage` 版面內，`include()` 限縮仍會掃到同子樹的既存問題（`accessibility-checklist.md` 修訂 1 更正段），而 `AdminPage.tsx:104`／`:299-302` 的既存違規不在本 intent 範圍。§27 維持人工驗證 |
| `H-2`：`ui-regression` 時間預算 | Step 13 以本機實測 `a11y.spec.ts` 耗時並記入 `code-summary.md`；整體預算交 `build-and-test` |
| `H-3`／`C-06`：`[人工]` 項目 | `AC-A11Y.2` 由 Step 9 自動化；其餘（O-1、O-12、R-4、landmark／標題層級、`OPEN-ND24-1`）交 `build-and-test` ＋ `tcms-test-cases` |
| `H-4`：上游無 `NFRx.y` | `traceability.json` 以 `A11Y-S*`／`C-*`／`D-*` 為上游 id；sensor 的「no NFRx.y」照實保留 |
| `D-07`：契約 `brain-*` 前綴落差 | 不改契約、不改程式 id；記入 `code-summary.md` 交 `build-and-test` |
| 證據留存缺口（`monitoring-design.md`） | 不改 `ui-regression`；記入 `code-summary.md` 交 `build-and-test` |

## 四、掃到違規時的處置原則（本計畫最重要的一條，核可前請看）

第一次實跑（Step 10）一定會有結果。三類各自的處置：

1. **落在本 intent 新元件內**（根節點清單見 `C-03` 規則 1）：**在本單元修掉**。修改範圍限於無障礙屬性與語意標記（`aria-*`、`role`、`alt`、`<label>`、標題層級、對比色的 Tailwind class），**不改行為、不改 test-id、不改版面結構**。這會改到 `U14`／`U15`／`U23`／`U24` 已交付的元件檔，屬重開已交付單元；每一處都列進 `code-summary.md`。**若單一元件需要結構性改動，或新元件違規總數超過 10 筆，停下來回報**，不在本單元硬修。
2. **落在頁殼既有節點、且規則不屬 `C-03` 規則 5 的交界類**：列入 `a11y-baseline.json`，每筆附 `reason`。取不到穩定選擇器者依 `D-04` 停下回報。
3. **交界類規則**（`landmark-*`、`region`、`heading-order` 等，若在選定規則集內真的會執行）：一律停下回報，不進基準、不自行修頁殼。

## 五、步驟

依 Testing Contract 的 `test-after`：每一層先實作、再寫並跑該層的測試。本單元沒有資料模型、資料存取、API 層，`plan_profile` 中這三層不適用。

- [x] **Step 1 — 讀上游並複驗前提（不動程式）**：讀第二節全部檔案；以 `grep -rn` 逐一確認 `C-02`／`D-02` 表中的 test-id 與文字定位器仍存在於 `frontend/src`；確認 `playwright.config.ts` 仍為 `fullyParallel: false`、`workers: 1`、CI `retries: 1`；確認 `ReselectionBanner.tsx` 仍有 `data-slot="reselection-banner"`。任一不符即停下回報。
- [x] **Step 2 — 驗證測試執行器並記錄單元專屬指令**：依 `unit-test-instructions.md` 以 `npm run build` ＋ `npx vite preview --port 4173` ＋ `BASE_URL=http://localhost:4173` 起前端，跑一次既有 `memory-page.spec.ts` 確認攔截層可用（不需 Docker）。記錄結果。
- [x] **Step 3 — 加入 devDependency（`A11Y-S1`–`A11Y-S4`、`T-1`／`T-2`）**：以 `npm view @axe-core/playwright time versions peerDependencies license` 選定一個發布滿 14 天、peer 範圍涵蓋已安裝 `@playwright/test` 的版本；`npm install --save-dev @axe-core/playwright@<版本>`（caret 寫入）；確認 `package-lock.json` 兩個條目有 `integrity`；`npm audit` 過濾新套件樹，high／critical 即停；記錄版本、發布日、peer、授權、audit 結果。
- [x] **Step 4 — 實作隔離層（`C-01`、`D-05`）**：`a11y.spec.ts` 內的 `isolate(page)`：最先註冊 HTTP 兜底（`abort` ＋ 記錄）與 WebSocket 兜底（`routeWebSocket(/.*/)` ＋ 記錄 ＋ `close`），再註冊 `/api/brain/ws`、`/api/collab/ws/**` 的具體接管；token 用固定假值（`A11Y-S6`）。
- [x] **Step 5 — 實作狀態層（`A11Y-S10`、`C-04`、`C-07`、`D-01`、`D-02`）**：18 個 `stage*()`；資料形狀複製自四支既有 spec 的最小必要部分，不抽共用模組（`security-design.md` 第三節）；互動步驟依 `D-02` 表；第 18 點以 `include('[data-slot="reselection-banner"]')`。
- [x] **Step 6 — 實作就緒層（`A11Y-S7`、`C-02`、`D-02`）**：每點一份 `{ ready, absent }`；不以任何 axe 欄位當作「有掃到」的證據；使用 `include()` 的掃描點，就緒 test-id 以 include 根節點為範圍定位（`D-01` 通則）。
- [x] **Step 7 — 實作掃描層（`A11Y-S8`、`A11Y-S9`、`C-03`、`D-03`、`D-04`）**：`withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa'])`；違規節點重新定位為穩定選擇器（不得用 `nth-child`）；**先寫檔（實際看到的條目）再斷言**；附件只放 `violations` 與 `incomplete`。
- [x] **Step 8 — 實作基準清單的兩個檢查 test**：(a) 靜態檢查：規則 1（不得收新元件根節點）、規則 4（`reason` 非空）、規則 5（交界類規則 id 不得出現）、`M12`（每點 `ready` 至少一項）；(b) 過期檢查：檔案最末，讀回 18 個檔，檔數不足即失敗，全部掃描點都沒出現的條目判過期。
- [x] **Step 9 — 實作手機寬度檢查（`C-06`、`AC-A11Y.2`）**：375×812，入口頁就緒後斷言 `scrollWidth <= clientWidth`。
- [x] **Step 10 — 第一次實跑並依第四節處置結果**：以空的 `a11y-baseline.json` 跑全部 21 個 test；逐筆分類違規；修新元件（第四節第 1 類）、建立基準（第 2 類）、遇第 3 類或超量即停下回報。記下第一次實跑的**完整違規清單與筆數**（`A11Y-S9` 規則 3 的比對基準）。
- [x] **Step 11 — 跑測試並做突變驗證（`M1`–`M12`）**：全綠後逐一套用 `security-design.md` 第八節 `M1`–`M10` 與 `D-08` 的 `M11`／`M12`，每一道：套用 → 確認紅在預期的那一層 → 還原 → 確認綠；`M10` 以環境變數注入一次性失敗並設 `CI=1` 使 `retries: 1` 生效，驗證過期檢查不誤紅——若誤紅，依 `D-03` 備案改以 project `dependencies` 拆出過期檢查（會改 `playwright.config.ts`，記入 `code-summary.md`）。
- [x] **Step 12 — 規則分類實查（`D-06`）**：以 `axe.getRules(['wcag2a','wcag2aa','wcag21a','wcag21aa'])` 列出實際執行的規則，與 `C-03` 規則 5 清單交叉比對；不符時以實查為準，調整 Step 8(a) 的清單並記錄。
- [x] **Step 13 — 環境與建置檢查**：`npm run lint`（0 errors，warning 數不增）；`npm run build`（含 `tsc -b`）；`grep -rn "axe-core" frontend/src` 為 0、`dist/` 內 `axe` 為 0（`A11Y-S1`）；`python3 scripts/validate_repo_contract.py`、`python3 scripts/validate_env_contract.py` 通過；實測 `a11y.spec.ts` 總耗時（`H-2`）。
- [ ] **Step 14 — 規格註解（`test-case-authoring.md` §4.4）**：21 個 `test()` 前各加 `@purpose`／`@given`／`@step`／`@pass`／`@ui`／`@story`／`@note`；`@ui` 用 `App.tsx` 實有的路由；`@story` 寫 `N-9`（無故事單元）；**不寫 `@api`**（受測對象不打真實 API，寫了是假端點）。`describe` 名稱定為 `U17 a11y gate`，合併後不得再改。
- [x] **Step 15 — 文件與追溯**：`code-summary.md`（含第三節各帶入事項的結果、第四節的修改清單、Step 3 的版本資訊、Step 10 的完整初始違規清單、Step 11 的突變結果、Step 13 的耗時）、`traceability.json`、`source-manifest.json`。

## 六、交付檔案（預估）

| 檔案 | 動作 |
|---|---|
| `frontend/package.json`、`frontend/package-lock.json` | 改（新增一個 devDependency） |
| `frontend/tests/e2e/a11y.spec.ts` | 新 |
| `frontend/tests/e2e/a11y-baseline.json` | 新 |
| `frontend/src/**` 中 `U14`／`U15`／`U23`／`U24` 的元件 | **視 Step 10 結果**，只改無障礙屬性（第四節第 1 類） |
| `frontend/playwright.config.ts` | **預設不改**；僅在 Step 11 的 `M10` 實證失敗時依 `D-03` 備案改 |

零後端、零 DDL、零環境變數、零 secret、零 workflow 檔變更。

## 七、ADR-0006 四面向

沿用 `security-requirements.md` 的判定（四面向皆不適用，三個變形分別由隔離層、就緒層、掃描層附件承接）。PBT 不適用（固定狀態集合）。

## 八、揭露（核可前請看）

1. **會重開已交付單元**：若 Step 10 掃出新元件違規，本單元會改 `U14`／`U15`／`U23`／`U24` 的元件檔（限無障礙屬性）。上限與停損條件見第四節。
2. **`/admin/*` 維持不掃**（第三節 `UG-5`）。
3. **e2e 只能在本機以 `vite preview` 跑**：Docker 不在本機時，`ui-regression` 的真實 compose stack 跑不了；本單元的 spec 全部走攔截層，與 stack 的差異只在前端是否由 nginx 服務，不影響掃描結果。
4. **證據留存缺口不在本單元修**：`ui-regression` 沒有 artifact 上傳，綠燈時 axe 結果零留存。
5. **追溯 sensor 會報 no NFRx.y IDs**，原因是上游沒有無障礙 NFR，照實保留。

## 九、code-generation Request Changes（2026-10-20）：本單元無劃入的合併前必修項

使用者對整站送出 Request Changes，要求修正 `construction/functional-design/merge-blockers.md` 的 19 項。逐列核對該檔第 1–19 列的「單元」欄，**沒有任何一列劃給 `a11y-gate`**（`grep -c "a11y" merge-blockers.md` 為 1，唯一命中是第 2 列記載 `a11y.spec.ts` 作為 entry-page-ui 修正的回歸測試）。

但其他單元本輪的修正改到了本單元掃描的畫面：`entry-page-ui` 新增對話中的系統提示列與「這句沒有送達」狀態，`member-pages-ui` 的成員頁新增「查不到這個專案」狀態。因此本輪只做回歸驗證，不改程式。

- [x] **Step 16 — 回歸驗證**：以 `npm run build` ＋ `vite preview` 生產建置跑 `tests/e2e/a11y.spec.ts` 全部案例須全綠；`a11y-baseline.json` **不得新增條目**（新出現的違規屬第四節第 1 類，應修元件而非收進基準——若出現即停下回報，不在本單元擅改他單元元件）；過期檢查不得誤紅。結果記入 `code-summary.md` 新增一節；`source-manifest.json`、`traceability.json` 無變更則不動。

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
