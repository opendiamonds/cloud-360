# Code Summary — `U23 project-pages-ui`

> 撰寫時間 2026-10-16T17:11:44Z（`date -u` 取值）。依據為同目錄已核可的 `code-generation-plan.md`（15 步，Testing Contract：`test-after`，`contract_sha256` `1f0b6822…`）與 `unit-test-instructions.md`。
> 設計檔一律未回改；設計文字的更正與取代集中在 §九「設計文字回補表」。本單元**未 commit**。

## 一、結果摘要

| 項目 | 結果（取得方式） |
|---|---|
| 計畫步驟 | 15／15 完成；計畫檔的 42 個 `- [ ]` 已勾為 `- [x]`（只動任務標記） |
| 後端單元指令（`unit-test-instructions.md` §二「全單元」，3.12 venv，含 `mcp`） | `Ran 145 tests` → `OK` |
| 同上（全域 python3 3.13，去掉需 `mcp` 的 `tests.test_mcp_bridge_e2e`） | `Ran 130 tests` → `OK` |
| 後端全套 `python -m unittest discover -s tests`（3.12 venv） | `Ran 1157 tests` → `FAILED (failures=4)`；4 筆全是 `test_progress_channel_contract` 掃到 repo 根目錄下**非本單元、未納入版控**的 `.kilo/worktrees/secret-deposit/backend/services/*.py`（§十一 第 1 項） |
| 後端全套（全域 python3 3.13） | `Ran 1157 tests` → `FAILED (failures=32, skipped=1)`：28 筆為 `mcp` 未安裝的既知環境限制（`test_mcp_bridge_app` 10、`test_mcp_bridge_e2e` 16、`test_mcp_bridge_topology` 2），4 筆同上 `.kilo` |
| `python scripts/dump_openapi.py --check` | `規格檔與後端程式碼一致。` |
| 前端 `npm run lint` | `✖ 2 problems (0 errors, 2 warnings)`——與 Step 2 基準相同（`AssessmentPage.tsx:365`、`WorkspacePage.tsx:302`，皆既存） |
| 前端 `npm run build`（含 `tsc -b`） | `✓ built`（只有既存的 chunk 大小提示） |
| 前端 `npm run check:types` | `API 型別檔與規格檔一致。` |
| e2e `tests/e2e/project-pages.spec.ts` | **23 passed**（原 21 ＋ 審查修正 2）——對 `vite` dev server（`BASE_URL=http://localhost:5199`）與 production build 的 `vite preview`（`BASE_URL=http://localhost:5198`）各跑皆綠 |
| e2e 鄰近回歸（`member-pages` ＋ `memory-page` ＋ 本 spec，production build） | **48 passed** |
| 突變驗證 | 計畫 §五 的 **36／36** 道全部「套用 → 紅 → 還原 → 綠」；拆成 44 次實跑，0 存活（§六）；審查修正另加 `F11`、`F12` 兩道，亦紅後綠（§十四） |
| repo 根目錄 `validate_repo_contract.py`／`validate_env_contract.py` | 皆 `passed` |

## 二、Step 1 複驗紀錄（唯讀，與計畫一致，未停下）

| 計畫所述事實 | 實讀結果 |
|---|---|
| `deploy/docker-compose.deploy.yml` 服務鍵 `db`（`:35`）、`backend`（`:79`） | `:35` 為 `db:`、`:79` 為 `backend:` |
| 無 `container_name`、無 `${VAR:?}` | `grep -n container_name` 0 筆；`grep -c ":?"` 為 **0** |
| `backend/Dockerfile` `WORKDIR /app`（`:14`）、`COPY . .`（`:19`） | 相符。**漏查一項（審查 R-01）**：腳本自己以 `REPO_ROOT = BACKEND_DIR.parent` 讀 `schema_rbac.sql`（`run_meta_schema_migration.py:70-72`），容器內解析為 `/schema_rbac.sql`；backend 映像的 build context 只有 `backend/`（`docker-compose.deploy.yml:81`），compose 只把該檔掛給 `db`（`:55`）。初版部署步驟因此必然 exit 1，已於 §十四 修正 |
| `backend/.dockerignore` 不排除 `scripts/` | 內容只有 `.env`、`.env.*`、`!.env.example`、`__pycache__/`、`*.py[cod]`、`.pytest_cache/`、`.venv/`、`venv/` |
| `DEPLOY.md` 2.2.7（`:330`）、2.2.9（`:583`）、`:674` 的「7 個索引」、`:867` 的 owner-scoped 句、`:213-214` 的 `docker exec` 形式 | 全部相符（改前） |
| `schema_rbac.sql` `project_members` DDL 結束於 `:606`、`:608-615` 為「刻意不建」註解 | 相符 |
| `run_meta_schema_migration.py` 的 `EXPECTED_INDEXES` 實為 8 筆 | 相符（`:155-170`） |

## 三、Step 2 基準（改動前）

| 指令 | 結果 |
|---|---|
| `cd backend && PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_membership_data tests.test_hierarchy_service tests.test_membership_facade tests.test_membership_endpoints -v` | `Ran 54 tests` → `OK` |
| `cd frontend && npm run lint` | `✖ 2 problems (0 errors, 2 warnings)` |
| `cd frontend && npm run check:types` | `API 型別檔與規格檔一致。` |
| `cd frontend && npx playwright test tests/e2e/project-pages.spec.ts --list` | `Total: 0 tests in 0 files`（檔案尚不存在，非設定錯誤） |

## 四、逐步完成情況與檔案清單

| Step | 內容 | 狀態 | 驗證 |
|---|---|---|---|
| 1 | 結構骨架與事實複驗 | 完成 | §二 |
| 2 | 測試執行器基準 | 完成 | §三 |
| 3 | 索引：`schema_rbac.sql` 四處、`models.py`、遷移腳本兩處 | 完成 | `grep -c ix_project_members_user_id`：`schema_rbac.sql` 4、`backend/models.py` 2、`run_meta_schema_migration.py` 2 |
| 4 | `test_M3` 兩個點名斷言、新增 `test_M3b` | 完成 | `tests.test_membership_data` `Ran 9 tests` OK；`D1`–`D3` 皆紅後綠 |
| 5 | `hierarchy_service.list_projects_by_ids`、六處 f-string 改常數；`membership_service` 可見性唯一定義；兩個常數 | 完成 | `grep "import.*membership"` 對 `hierarchy_facade.py`／`hierarchy_service.py` 為 0；`grep -c "NOT EXISTS\|project_members\|ProjectMember"` 兩檔皆 0；`def _visible_project_ids_select` 恰 1 |
| 6 | `VisibilityPredicateTest` 7 案 | 完成 | `Ran 7 tests` OK；`M1`／`M2`／`M3`／`M6` 紅後綠 |
| 7 | `HierarchyFacade` 守門與兩個 unscoped 方法、`[PPD1]` actor log；`MembershipFacade` 三方法；`ALWAYS_VISIBLE`；15 處補參數；router 三支寫入 handler 注入判定（**自 Step 9 提前**，§十 D-1） | 完成 | 15 處逐筆：`test_hierarchy_service.py` 11（`:219`、`:231`、`:233`、`:323`、`:331`、`:346`、`:351`、`:359`、`:374`、`:387`、`:391`，以 `grep -A2` 計 11／11 帶 `project_visible=ALWAYS_VISIBLE`）、`test_work_orchestrator_store.py` 2、`test_requirement_field_facade.py` 1、`test_mcp_bridge_e2e.py` 1；**斷言、fixture、案例名稱皆未動** |
| 8 | 靜態鎖 5 條；跨單元回歸 | 完成 | `tests.test_project_visibility_static` `Ran 5 tests` OK；回歸（3.12 venv）`Ran 77 tests` OK；`BR87.7-M`、`G4`、`G5`、`G7`、`G8`、`G9` 紅後綠 |
| 9 | 兩支列舉 handler 改委派、docstring 改寫；重 dump `openapi.json`、重產 `api.d.ts` | 完成 | `git diff --stat openapi.json`：`2 insertions(+), 2 deletions(-)`，兩個 hunk（`@@ -4408`、`@@ -4522`）皆只有 `description` 行；路徑、`response_model`、狀態碼、`responses` 不變；`--check` 與 `check:types` 綠 |
| 10 | 端點測試 16 案、守門 22 案、語句數 2 案 | 完成 | `Ran 47 tests` OK；`T2b` 綠；`--check` 綠；§六 的 `M`／`G`／`N`／`L`／`Q` 全部紅後綠 |
| 11 | 前端 15 個新檔中的 14 個實作檔、`App.tsx`／`Sidebar.tsx` | 完成 | lint 0 errors（warnings 2，不高於基準）、build 綠、`check:types` 綠；grep 完成條件見 §四之一 |
| 12 | e2e 21 案 | 完成 | 21 passed；`F1`–`F10` 紅後綠 |
| 13 | 環境／建置零改動驗證 | 完成 | `git diff --stat` 對 `deploy/`、`*.env.example`、`.github/workflows/`、`backend/requirements.txt`、`backend/database.py`、`frontend/package.json`、`frontend/package-lock.json`、`LOCAL-DEV.md`、`schema.sql` 為空；新路徑無 `prod`／`production`／`secrets` path part；兩支 validator passed |
| 14 | `DEPLOY.md` 四處、腳本檔頭 | 完成 | `grep -c ix_project_members_user_id DEPLOY.md` 為 6；`grep -n "7 個索引" DEPLOY.md` 為 0；`owner-scoped` 殘留 2 處皆為**標明為歷史狀態**的敘述（`DEPLOY.md:921`、`backfill_project_members.py:21`） |
| 15 | 本檔、`traceability.json`、`source-manifest.json`；全單元重跑 | 完成 | §一 |

### 四之一、Step 11 的 grep 完成條件（逐筆判讀）

| 檢查 | 結果 |
|---|---|
| 本單元新增前端檔中 `owner_user_id`（`PPN-16`） | 3 筆，全在 `components/projects/SystemCreateAction.tsx`：兩筆 docstring、一筆渲染條件（`:31`） |
| `localStorage`／`sessionStorage`／`indexedDB`（`PPN-17`） | 0 |
| `console.`（`PPN-18`） | 0（`fanoutQueue.ts` 0）。初版兩檔的 docstring 寫出了該字面字串，已改寫為「主控台輸出」使 grep 為 0 |
| `createProject(`／`createSystem(` 的呼叫只在 `objectCreateAction.ts`（`BR82.1`） | 呼叫 2 筆皆在 `objectCreateAction.ts:79`／`:81`；另 2 筆為 `projectsApi.ts` 的函式定義 |
| `FANOUT_CONCURRENCY` 定義 | 恰 1 處（`fanoutQueue.ts:27`） |

### 四之二、修改與新增的應用程式檔（39 個，與 `source-manifest.json` 以 `diff` 比對完全一致）

**後端改檔（14）**：`backend/models.py`、`backend/scripts/run_meta_schema_migration.py`、`backend/scripts/backfill_project_members.py`（只改檔頭一句，不改行為）、`backend/services/hierarchy_facade.py`、`backend/services/hierarchy_router.py`、`backend/services/hierarchy_service.py`、`backend/services/membership_facade.py`、`backend/services/membership_service.py`、`backend/tests/helpers.py`、`backend/tests/test_membership_data.py`、`backend/tests/test_hierarchy_service.py`（`U7`）、`backend/tests/test_work_orchestrator_store.py`（`U12`）、`backend/tests/test_requirement_field_facade.py`（`U20`）、`backend/tests/test_mcp_bridge_e2e.py`（`U21`）。

**後端新檔（4）**：`backend/tests/test_project_visibility_queries.py`（9 案）、`backend/tests/test_project_visibility_static.py`（5 案）、`backend/tests/test_project_visibility_endpoints.py`（16 案）、`backend/tests/test_project_write_guard.py`（22 案）。

**schema、契約與文件（4）**：`schema_rbac.sql`、`openapi.json`、`frontend/src/types/api.d.ts`（`gen:types` 重產）、`DEPLOY.md`。

**前端改檔（2）**：`frontend/src/App.tsx`、`frontend/src/components/Sidebar.tsx`。

**前端新檔（15）**：`frontend/src/projects/{fanoutQueue,projectsApi,requirementsApi,objectCreateAction}.ts`、`frontend/src/pages/{ProjectsListPage,ProjectCreatePage,ProjectDetailPage}.tsx`、`frontend/src/components/projects/{ProjectTabs,OverviewTab,RecentChanges,RequirementsTab,RequirementField,SystemCreateAction,MemorySummaryTab}.tsx`、`frontend/tests/e2e/project-pages.spec.ts`。

`git diff --stat`（排除 `aidlc/`）：20 個既有檔 `608 insertions(+), 66 deletions(-)`。

### 四之三、關鍵實作決定

1. **可見性只有一份**：`membership_service._visible_project_ids_select(user_id)` 回傳一個 `UNION`（成員那一半 ∪ 擁有者且零成員列那一半），`visible_project_ids` 與 `is_project_visible` 都只由它組出；`MembershipFacade.list_visible_projects`／`list_visible_systems`／`project_visibility` 只呼叫這兩支。`hierarchy_facade.py`／`hierarchy_service.py` 不 import 任何 membership 符號。
2. **寫入守門以注入取得**：`HierarchyFacade` 三個寫入方法新增必填、無預設、keyword-only 的 `project_visible: Callable[[int], bool]`；順序為 `K2 edit` → （`delete_system` 先取所屬專案）→ 守門 → 既有擁有者檢查 → service（含 409）。`delete_system` 的守門拋**系統句**。
3. **固定訊息**：`PROJECT_NOT_FOUND_DETAIL = "查不到專案"`、`SYSTEM_NOT_FOUND_DETAIL = "查不到系統"` 定義於 `hierarchy_facade.py`（`HierarchyNotFound` 之後）並加入 `__all__`；`hierarchy_service.py` 六處帶 id 的 f-string 改用常數，架構圖那一句不改。
4. **openapi 漂移只限兩支列舉端點**：三支寫入 handler 的說明改寫成**程式註解**而非 docstring——docstring 即 operation description，改它會讓 `openapi.json` 多漂移三支。
5. **前端資料只有一份**：`ProjectDetailPage` 持有 `fieldsBySystem`、`lastGoodFields`（重讀失敗時仍要呈現欄位結構與草稿，`BR85.6`）與 `changesBySystem`；扇出佇列 `createFanoutQueue()` 每次 effect 建一個，cleanup 依序 `cancelled = true`、`queue.cancel()`；`tab` 不在依賴陣列。
6. **建立的唯一寫入路徑**：`objectCreateAction(token, kind, name, parentProjectId?)`；pending 期間的重複觸發以 `useRef` 判定（state 在同一事件迴圈內尚未生效）；按鈕以 `aria-disabled` 而非 `disabled` 保持可聚焦。

## 五、測試指令與結果

後端在 `backend/` 目錄執行；「venv」指 `/private/tmp/claude-501/-Users-jiangzhengdao-orca-workspaces-cloud-360-chiton/4d25ab9d-f000-4c33-b722-b68fcdd65f73/scratchpad/venv/bin/python`（`uv venv --python 3.12` 後 `uv pip install -r backend/requirements.txt`；**未**把 `mcp` 裝進全域 python）。

| 層 | 指令 | 結果 |
|---|---|---|
| Data model（Step 4） | `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_membership_data -v` | `Ran 9 tests` OK |
| Repository（Step 6） | `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_project_visibility_queries.VisibilityPredicateTest -v` | `Ran 7 tests` OK |
| Business logic（Step 8） | `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_project_visibility_static -v` | `Ran 5 tests` OK |
| 〃 跨單元回歸 | venv：`… -m unittest tests.test_hierarchy_service tests.test_work_orchestrator_store tests.test_requirement_field_facade tests.test_mcp_bridge_e2e tests.test_membership_facade -v` | `Ran 77 tests` OK（全域 3.13 下 `test_mcp_bridge_e2e` 16 筆 AssertionError，為既知 `mcp` 環境限制） |
| API（Step 10） | `… -m unittest tests.test_project_visibility_endpoints tests.test_project_write_guard tests.test_project_visibility_queries -v` | `Ran 47 tests` OK |
| 〃 | `… -m unittest tests.test_hierarchy_service -v`（含 `T2b`） | OK |
| 全單元（Step 15） | venv：`unit-test-instructions.md` §二 的「全單元」指令（11 個模組） | `Ran 145 tests` OK |
| 〃 | 全域 python3：同上去掉 `tests.test_mcp_bridge_e2e` | `Ran 130 tests` OK |
| 全套 | venv：`python -m unittest discover -s tests` | `Ran 1157`，failures=4（全為 `.kilo`，§十一） |
| 契約 | `python scripts/dump_openapi.py --check` | 一致 |
| 前端 | `npm run lint`／`npm run build`／`npm run check:types` | 0 errors 2 warnings／綠／一致 |
| e2e（dev server） | `npx vite --port 5199 --strictPort` 後 `BASE_URL=http://localhost:5199 npx playwright test tests/e2e/project-pages.spec.ts` | 21 passed |
| e2e（production build） | `npm run build && npx vite preview --port 5198 --strictPort` 後 `BASE_URL=http://localhost:5198 npx playwright test tests/e2e/member-pages.spec.ts tests/e2e/memory-page.spec.ts tests/e2e/project-pages.spec.ts` | 46 passed |

**e2e 執行環境（如實記載）**：本機未起 `deploy/docker-compose.test.yml` 的 nginx stack；本 spec 全部以 `page.route()` 攔截 API，故以 `vite` dev server 與 `vite preview`（production build）執行——`unit-test-instructions.md` §二 已列此為允許的替代方式。**附帶觀察**：在 dev server 上，`member-pages.spec.ts` 與 `memory-page.spec.ts` 有數案以「請求數不等」失敗；`main.tsx` 以 `<StrictMode>` 包覆，dev 模式下 effect 執行兩次，會使「恰 N 次請求」型斷言加倍。同兩支在 production build（CI 的 nginx 服務的也是 build 產物）下全綠。**審查修正 R-05 已驗證為 HEAD 既存**：在乾淨的 HEAD（`a898f31`）worktree 以 dev server 跑同兩支，結果為 `9 failed, 16 passed`，失敗的 9 案與本工作樹在 dev server 上的 9 案**逐案名稱相同**（§十四 R-05）。本單元未修改它們。

**新增測試數**：後端 53 案（`test_M3b` 1 ＋ queries 9 ＋ static 5 ＋ endpoints 16 ＋ write guard 22）；e2e 21 案。後端每案 docstring 帶 `@purpose`／`@story`，有 HTTP 端點者帶 `@api`；受測對象無 HTTP 端點者（靜態鎖、service 層謂詞、`test_M3b`、`E14b`）不寫 `@api`。e2e 每案帶 `@purpose`／`@api`／`@ui`／`@given`／`@step`／`@pass`／`@story`。新增檔中 `skipTest`／`skipIf`／`skipUnless`／`SkipTest` 為 0。

**覆蓋率**：repo 沒有量測機制（`team.md`），本單元不宣稱百分比。

## 六、突變驗證（計畫 §五 的 36 道，全部紅後綠）

執行方式：以 scratchpad 的輔助腳本對指定檔做**單一字串替換**、跑該層指令、記下失敗案例、以**記憶體中的原檔內容寫回**還原、再跑同一指令確認綠。還原**未**使用計畫所寫的 `git checkout -- <檔>`：被突變的檔案含本單元尚未 commit 的改動，`git checkout` 會連同實作一起抹掉（§十 D-9）。後端指令同 §五 各層（`M4` 另加 `tests.test_hierarchy_service` 以涵蓋 `T2b`）；前端 `F` 系列為 `BASE_URL=http://localhost:5199 npx playwright test tests/e2e/project-pages.spec.ts --reporter=line`（dev server 即時反映原始碼）。`G7` 為靜態 grep：`test "$(grep -c "NOT EXISTS\|project_members\|ProjectMember" services/hierarchy_service.py)" -eq 0`。

子變體：`M1`／`M2`／`M3`／`M6` 在 Step 6（service 層）與 Step 10（API 層，`-api` 後綴）各跑一次；`M5` 分 `M5a`（`list_projects_by_ids`）與 `M5b`（`list_systems_unscoped`）；`G3` 分 `G3a`（`delete_project`）與 `G3b`（`delete_system`）；`N1` 另加 `N1b`（service 層 `get_project_of_system` 的訊息）；`L1` 分 `L1a`／`L1b`。計數：`D` 3、`M` 6、`BR87.7-M` 1、`G` 9、`N` 3、`L` 1、`Q` 3、`F` 10 ＝ **36 道**；實跑 44 次，**44／44 紅後綠、0 存活**。`N2` 的紅燈是 `errors=3` 而非 failures：`MembershipForbidden` 不在 `hierarchy_router._translate` 的轉譯清單內，故以未轉譯的例外浮出（仍為紅燈，且正說明該突變不只改了狀態碼）。

| 代號 | 突變 | 改動檔 | 套用後 | 還原後 |
|---|---|---|---|---|
| `D1` | 只從 EXPECTED_INDEXES 刪該列、保留 BLOCK_SENTINELS['J'] | `backend/scripts/run_meta_schema_migration.py` | 紅（Ran 9 tests in 0.121s；FAILED (failures=1)）：`test_M3b_migration_script_verifies_the_user_id_index` | 綠（Ran 9 tests in 0.114s；OK） |
| `D2` | DDL 寫成 ON public.project_members | `schema_rbac.sql` | 紅（Ran 9 tests in 0.113s；FAILED (failures=1)）：`test_M3_constraint_and_index_names_match_the_ddl` | 綠（Ran 9 tests in 0.113s；OK） |
| `D3` | 只拿掉 ORM 的 Index | `backend/models.py` | 紅（Ran 9 tests in 0.118s；FAILED (failures=1)）：`test_M3_constraint_and_index_names_match_the_ddl` | 綠（Ran 9 tests in 0.113s；OK） |
| `M1` | 拿掉成員那一半（UNION 只剩擁有者半邊） | `backend/services/membership_service.py` | 紅（Ran 9 tests in 0.372s；FAILED (failures=5)）：`test_V1_owner_with_member_row_sees_project`、`test_V2_invited_member_sees_project`、`test_V3_member_of_another_project_does_not_see_target`、`test_V4_removed_owner_does_not_see_project`、`test_V7_visible_ids_are_ascending_and_union_both_halves` | 綠（Ran 9 tests in 0.371s；OK） |
| `M2` | 拿掉「零成員列」條件（退回擁有者 ∪ 成員） | `backend/services/membership_service.py` | 紅（Ran 9 tests in 0.364s；FAILED (failures=1)）：`test_V4_removed_owner_does_not_see_project` | 綠（Ran 9 tests in 0.376s；OK） |
| `M3` | 拿掉擁有者那一半 | `backend/services/membership_service.py` | 紅（Ran 9 tests in 0.365s；FAILED (failures=2)）：`test_V5_owner_of_zero_member_project_sees_it`、`test_V7_visible_ids_are_ascending_and_union_both_halves` | 綠（Ran 9 tests in 0.377s；OK） |
| `M6` | is_project_visible 的外層漏掉與目標專案的關聯（退化為「有任何可見專案」） | `backend/services/membership_service.py` | 紅（Ran 9 tests in 0.367s；FAILED (failures=1)）：`test_V3_member_of_another_project_does_not_see_target` | 綠（Ran 9 tests in 0.361s；OK） |
| `M1-api` | 拿掉成員那一半（UNION 只剩擁有者半邊） | `backend/services/membership_service.py` | 紅（Ran 47 tests in 2.089s；FAILED (failures=16)）：`test_E1_owner_with_member_row_lists_project`、`test_E2_invited_member_lists_project`、`test_E3_member_of_another_project_does_not_list_target`、`test_E6_owner_with_member_row_gets_200`、`test_E7_invited_member_gets_200`、`test_Q_system_list_statement_count_is_independent_of_S`、`test_V1_owner_with_member_row_sees_project`、`test_V2_invited_member_sees_project`、`test_V3_member_of_another_project_does_not_see_target`、`test_V4_removed_owner_does_not_see_project`、`test_V7_visible_ids_are_ascending_and_union_both_halves`、`test_a_create_system_owner_member_201`、`test_a_delete_project_owner_member_204`、`test_a_delete_system_owner_member_204`、`test_log_delete_project_records_actor`、`test_log_delete_system_records_actor` | 綠（Ran 47 tests in 2.149s；OK） |
| `M2-api` | 拿掉「零成員列」條件（退回擁有者 ∪ 成員） | `backend/services/membership_service.py` | 紅（Ran 47 tests in 2.153s；FAILED (failures=11)）：`test_E4_removed_owner_does_not_list_project`、`test_E9_removed_owner_gets_404`、`test_V4_removed_owner_does_not_see_project`、`test_b_create_system_removed_owner_404_no_change`、`test_b_delete_project_removed_owner_404_no_change`、`test_b_delete_system_removed_owner_404_no_change`、`test_e2_delete_system_with_diagram_removed_owner_404_not_409`、`test_e_delete_project_with_systems_removed_owner_404_not_409`、`test_g_create_system_missing_vs_invisible`、`test_g_delete_project_missing_vs_invisible`、`test_g_delete_system_missing_vs_invisible` | 綠（Ran 47 tests in 2.147s；OK） |
| `M3-api` | 拿掉擁有者那一半 | `backend/services/membership_service.py` | 紅（Ran 47 tests in 2.073s；FAILED (failures=7)）：`test_E10_owner_of_zero_member_project_gets_200`、`test_E5_owner_of_zero_member_project_lists_it`、`test_V5_owner_of_zero_member_project_sees_it`、`test_V7_visible_ids_are_ascending_and_union_both_halves`、`test_c_create_system_zero_member_owner_201`、`test_c_delete_project_zero_member_owner_204`、`test_c_delete_system_zero_member_owner_204` | 綠（Ran 47 tests in 2.100s；OK） |
| `M6-api` | is_project_visible 的外層漏掉與目標專案的關聯（退化為「有任何可見專案」） | `backend/services/membership_service.py` | 紅（Ran 47 tests in 2.089s；FAILED (failures=3)）：`test_E15_missing_and_invisible_project_are_byte_identical`、`test_E8_member_of_another_project_gets_404`、`test_V3_member_of_another_project_does_not_see_target` | 綠（Ran 47 tests in 2.139s；OK） |
| `M4` | 系統清單改經 _assert_project_exists | `backend/services/membership_facade.py` | 紅（Ran 75 tests in 2.982s；FAILED (failures=4)）：`test_E13_non_canonical_is_denied_system_list_of_existing_project`、`test_E14_non_canonical_is_denied_system_list_of_missing_project`、`test_E15_missing_and_invisible_project_are_byte_identical`、`test_T2b_non_canonical_role_is_denied_everywhere` | 綠（Ran 75 tests in 2.948s；OK） |
| `M5a` | 拿掉 list_projects_by_ids 第一行 K2 | `backend/services/hierarchy_facade.py` | 紅（Ran 47 tests in 2.094s；FAILED (failures=3)）：`test_E11_non_canonical_member_is_denied_project_list`、`test_E12_non_canonical_with_empty_visible_set_is_still_denied`、`test_E14b_list_systems_unscoped_itself_requires_K2` | 綠（Ran 47 tests in 2.162s；OK） |
| `M5b` | 拿掉 list_systems_unscoped 第一行 K2 | `backend/services/hierarchy_facade.py` | 紅（Ran 47 tests in 2.118s；FAILED (failures=1)）：`test_E14b_list_systems_unscoped_itself_requires_K2` | 綠（Ran 47 tests in 2.145s；OK） |
| `BR87.7-M` | hierarchy_router.py 直呼 list_systems_unscoped | `backend/services/hierarchy_router.py` | 紅（Ran 5 tests in 0.695s；FAILED (failures=1)）：`test_S1_unscoped_methods_called_only_by_membership_facade` | 綠（Ran 5 tests in 0.706s；OK） |
| `G1` | 拿掉守門（三個方法的 project_visible 判定） | `backend/services/hierarchy_facade.py` | 紅（Ran 47 tests in 2.116s；FAILED (failures=8)）：`test_b_create_system_removed_owner_404_no_change`、`test_b_delete_project_removed_owner_404_no_change`、`test_b_delete_system_removed_owner_404_no_change`、`test_e2_delete_system_with_diagram_removed_owner_404_not_409`、`test_e_delete_project_with_systems_removed_owner_404_not_409`、`test_g_create_system_missing_vs_invisible`、`test_g_delete_project_missing_vs_invisible`、`test_g_delete_system_missing_vs_invisible` | 綠（Ran 47 tests in 2.179s；OK） |
| `G2` | 守門移到 _authorize 之前（create_system） | `backend/services/hierarchy_facade.py` | 紅（Ran 47 tests in 2.137s；FAILED (failures=1)）：`test_f_create_system_developer_403_not_404` | 綠（Ran 47 tests in 2.109s；OK） |
| `G3a` | delete_project 的守門移到 service 呼叫之後 | `backend/services/hierarchy_facade.py` | 紅（Ran 47 tests in 2.152s；FAILED (failures=3)）：`test_b_delete_project_removed_owner_404_no_change`、`test_c_delete_project_zero_member_owner_204`、`test_e_delete_project_with_systems_removed_owner_404_not_409` | 綠（Ran 47 tests in 2.118s；OK） |
| `G3b` | delete_system 的守門移到 service 呼叫之後 | `backend/services/hierarchy_facade.py` | 紅（Ran 47 tests in 2.055s；FAILED (failures=2)）：`test_b_delete_system_removed_owner_404_no_change`、`test_e2_delete_system_with_diagram_removed_owner_404_not_409` | 綠（Ran 47 tests in 2.173s；OK） |
| `G4` | project_visible 預設 None 且為 None 時略過守門 | `backend/services/hierarchy_facade.py` | 紅（Ran 5 tests in 0.685s；FAILED (failures=1)）：`test_S2_project_visible_is_required_keyword_only` | 綠（Ran 5 tests in 0.681s；OK） |
| `G5` | router 改傳 lambda _pid: True | `backend/services/hierarchy_router.py` | 紅（Ran 5 tests in 0.645s；FAILED (failures=1)）：`test_S3_every_write_call_injects_project_visibility` | 綠（Ran 5 tests in 0.690s；OK） |
| `G6` | delete_system 的守門改拋專案句 | `backend/services/hierarchy_facade.py` | 紅（Ran 47 tests in 2.083s；FAILED (failures=1)）：`test_g_delete_system_missing_vs_invisible` | 綠（Ran 47 tests in 2.049s；OK） |
| `G7` | hierarchy_service 內另寫一份成員查詢（靜態 grep 檢查） | `backend/services/hierarchy_service.py` | 紅（exit 1，輸出 `FAILED grep>0`）：grep 計數大於 0 | 綠（exit 0） |
| `G8` | router 直呼 hierarchy_service.delete_project（模組屬性形式） | `backend/services/hierarchy_router.py` | 紅（Ran 5 tests in 0.690s；FAILED (failures=1)）：`test_S5_service_write_functions_called_only_from_hierarchy_facade` | 綠（Ran 5 tests in 0.691s；OK） |
| `G9` | from services.hierarchy_service import delete_project 後裸呼叫 | `backend/services/hierarchy_router.py` | 紅（Ran 5 tests in 0.683s；FAILED (failures=1)）：`test_S5_service_write_functions_called_only_from_hierarchy_facade` | 綠（Ran 5 tests in 0.683s；OK） |
| `N1` | create_system 守門的訊息改回 f"查不到專案 {project_id}" | `backend/services/hierarchy_facade.py` | 紅（Ran 47 tests in 2.101s；FAILED (failures=1)）：`test_g_create_system_missing_vs_invisible` | 綠（Ran 47 tests in 2.049s；OK） |
| `N1b` | service get_project_of_system 的訊息改回 f"查不到系統 {system_id}" | `backend/services/hierarchy_service.py` | 紅（Ran 47 tests in 2.115s；FAILED (failures=1)）：`test_g_delete_system_missing_vs_invisible` | 綠（Ran 47 tests in 2.038s；OK） |
| `N2` | 系統清單的「不可見」改拋 MembershipForbidden（403） | `backend/services/membership_facade.py` | 紅（Ran 47 tests in 2.128s；FAILED (errors=3)）：`test_E15_missing_and_invisible_project_are_byte_identical`、`test_E8_member_of_another_project_gets_404`、`test_E9_removed_owner_gets_404` | 綠（Ran 47 tests in 2.054s；OK） |
| `N3` | 系統清單的「不存在」改用帶 id 的訊息 | `backend/services/membership_facade.py` | 紅（Ran 47 tests in 2.114s；FAILED (failures=1)）：`test_E15_missing_and_invisible_project_are_byte_identical` | 綠（Ran 47 tests in 2.077s；OK） |
| `L1a` | 拿掉 delete_project 的 actor log | `backend/services/hierarchy_facade.py` | 紅（Ran 47 tests in 2.075s；FAILED (failures=1)）：`test_log_delete_project_records_actor` | 綠（Ran 47 tests in 2.034s；OK） |
| `L1b` | 拿掉 delete_system 的 actor log | `backend/services/hierarchy_facade.py` | 紅（Ran 47 tests in 2.154s；FAILED (failures=1)）：`test_log_delete_system_records_actor` | 綠（Ran 47 tests in 2.066s；OK） |
| `Q1` | list_visible_projects 改為對每個候選專案呼叫 is_project_visible | `backend/services/membership_facade.py` | 紅（Ran 47 tests in 2.219s；FAILED (failures=1)）：`test_Q_project_list_statement_count_is_independent_of_P` | 綠（Ran 47 tests in 2.168s；OK） |
| `Q2` | service list_projects_by_ids 改為逐 id 取（每 id 一條查詢） | `backend/services/hierarchy_service.py` | 紅（Ran 47 tests in 2.089s；FAILED (failures=1)）：`test_Q_project_list_statement_count_is_independent_of_P` | 綠（Ran 47 tests in 2.093s；OK） |
| `Q3` | 系統清單逐系統再查一次（逐系統查詢子物件） | `backend/services/membership_facade.py` | 紅（Ran 47 tests in 2.141s；FAILED (failures=1)）：`test_Q_system_list_statement_count_is_independent_of_S` | 綠（Ran 47 tests in 2.044s；OK） |
| `F1` | enqueue 直接執行（不受上限，等同全發） | `frontend/src/projects/fanoutQueue.ts` | 紅（3 failed；18 passed (28.7s)）：`fans out the detail page fields first and changes second with at most four in flight`、`fans out the list page with at most four requests in flight and no truncation`、`stops sending queued fan-out requests after leaving the page` | 綠（21 passed (22.4s)） |
| `F2` | 詳情頁兩段入列對調（先變更紀錄、後需求欄位） | `frontend/src/pages/ProjectDetailPage.tsx` | 紅（2 failed；19 passed (33.1s)）：`fans out the detail page fields first and changes second with at most four in flight`、`lists at most five recent changes with honest scope, ordering and partial failure` | 綠（21 passed (21.8s)） |
| `F3` | 清單扇出 slice(0, 4) | `frontend/src/pages/ProjectsListPage.tsx` | 紅（1 failed；20 passed (23.6s)）：`fans out the list page with at most four requests in flight and no truncation` | 綠（21 passed (22.4s)） |
| `F4` | 拿掉清單頁 cleanup 的 queue.cancel() | `frontend/src/pages/ProjectsListPage.tsx` | 紅（1 failed；20 passed (22.4s)）：`stops sending queued fan-out requests after leaving the page` | 綠（21 passed (22.3s)） |
| `F5` | 把 tab（searchParams）放進詳情頁 effect 依賴 | `frontend/src/pages/ProjectDetailPage.tsx` | 紅（2 failed；19 passed (53.1s)）：`keeps saved drafts when the reload fails and recovers on refresh`、`switches tabs by keyboard without history entries or requests` | 綠（21 passed (22.4s)） |
| `F6` | 建立系統成功後導航（離開詳情頁） | `frontend/src/pages/ProjectDetailPage.tsx` | 紅（1 failed；20 passed (32.2s)）：`shows the create-system action only to the owner and recounts systems after creating one` | 綠（21 passed (22.5s)） |
| `F7` | 失敗欄位的草稿被重讀結果覆蓋 | `frontend/src/components/projects/RequirementsTab.tsx` | 紅（1 failed；20 passed (32.6s)）：`keeps the failed field input and applies the reloaded value to the saved one` | 綠（21 passed (21.9s)） |
| `F8` | 重讀失敗時清除成功欄位草稿 | `frontend/src/components/projects/RequirementsTab.tsx` | 紅（1 failed；20 passed (32.9s)）：`keeps saved drafts when the reload fails and recovers on refresh` | 綠（21 passed (22.0s)） |
| `F9` | [儲存] 不看 can('K4','edit') | `frontend/src/components/projects/RequirementsTab.tsx` | 紅（1 failed；20 passed (32.6s)）：`allows editing with K4 edit and renders read-only without it` | 綠（21 passed (21.8s)） |
| `F10` | 更新者標題改取欄位所屬組的 legend | `frontend/src/components/projects/RequirementsTab.tsx` | 紅（1 failed；20 passed (32.8s)）：`shows the updater from the requesting group and degrades for unknown groups` | 綠（21 passed (22.0s)） |

## 七、帶入項 20 項的逐項落點（`../carried-review-items.md`）

| # | 站別 | ID | 落點（實作／測試／文件） | 狀態 |
|---|---|---|---|---|
| 1 | functional-design | R-01（Major，使用者裁決） | 守門：`hierarchy_facade.py` 三個寫入方法（必填 `project_visible`、順序見 §四之三 第 2 點）；注入：`hierarchy_router.py` 三處、`MembershipFacade.project_visibility`；測試：`test_project_write_guard.py` (a)–(g)、(e')（22 案）；突變 `G1`–`G9` 全紅後綠。**`OPEN-PP23-10` 於本單元關閉**：被移出的建立者對三條寫入路徑一律 404 且四表列數不變；`functional-spec.md` 的「本 intent 內無自然承接站」一句以使用者裁決為準。兩條級聯（刪專案刪全部成員列、刪系統刪需求欄位值）於 §十二 第 1 項重新揭露 | 完成 |
| 2 | functional-design | R-02 | `RecentChanges.tsx` 標示逐字「只含經大腦、已歸屬系統、且為你自己擁有之圖的變更」、空態逐字「沒有符合條件的變更紀錄」、部分失敗「部分變更無法取得」；e2e 'lists at most five recent changes…' 斷言三句；`traceability.json` 的 `BR86.2` note 補「未歸屬系統的圖（`OPEN-H11`）查不到」 | 完成 |
| 3 | functional-design | R-03 | ③ 構造為「另一專案的成員」（`VisibilityWorld.other_member`）；`V3`、`E3`、`E8`、`E15`；`M5a`／`M5b`（含可見集合為空的缺 `K2` 使用者 `E12`）與 `M6` 紅後綠 | 完成 |
| 4 | functional-design | R-04 | `ProjectDetailPage` 先入列全部端點 5、再入列全部端點 7；端點 1、進頁的端點 2、建立後重讀、儲存後重讀、`[重新整理]` 直接呼叫不經佇列；e2e 'fans out the detail page fields first…' 斷言順序與在途恰 4；`F2` 紅後綠 | 完成 |
| 5 | functional-design | R-05 | 紀錄：見 §九 第 8 列 | 紀錄 |
| 6 | nfr-requirements | R-01（Major，使用者裁決） | 兩常數（`hierarchy_facade.py`）、六處改常數（`hierarchy_service.py`）；逐位元比較四條路徑：系統清單 `E15`、建立系統／刪除專案／刪除系統 `test_g_*` 三案；`N1`、`N1b`、`N2`、`N3`、`G6` 紅後綠 | 完成 |
| 7 | nfr-requirements | R-02（Major，使用者裁決） | 索引沿用 `U18` 遷移路徑：`schema_rbac.sql` `J)`、`models.py`、`EXPECTED_INDEXES`（8 → 9）、`BLOCK_SENTINELS["J"]`；`DEPLOY.md` 2.2.9 計數改 9 並更正原本的 7、新增部署後步驟小節；`backend/database.py` 未動，`LOCAL-DEV.md` 同步不觸發；`D1`–`D3` 紅後綠 | 完成 |
| 8 | nfr-requirements | R-03 | 必填無預設 keyword-only；靜態鎖第 2 條（`kw_defaults` 為 `None`）、第 3 條（值必須是 `….project_visibility(...)` 呼叫）；`delete_system` 為「取所屬專案 → 守門 → 擁有者檢查」；`G4`、`G5` 紅後綠 | 完成 |
| 9 | nfr-requirements | R-04 | 守門早於擁有者檢查與一切 409；(e) `test_e_delete_project_with_systems_removed_owner_404_not_409`；`G3a` 紅後綠 | 完成 |
| 10 | nfr-requirements | R-05 | 紀錄：`fanoutQueue.ts` 檔頭照錄 `performance-design.md` §三 的定位（4 是經驗值、只限單人突發、不保護連線池；約 3 位使用者同時進入系統數多的專案即可耗盡 15 條連線）；§十二 第 9 項揭露 | 紀錄 |
| 11 | nfr-requirements | R-06 | `[PPD1]`=A：`delete_project`／`delete_system` 成功後記 `logger.info("刪除專案 project_id=%s actor_user_id=%s", …)`（系統同形），不記名稱；`assertLogs` 兩案、`L1a`／`L1b` 紅後綠。連帶刪除筆數不記（殘留，§十二 第 9 項）；上游「刪除不記稽核」更正見 §九 第 9 列 | 完成 |
| 12 | nfr-design | R-01（Major，使用者裁決：接受為殘留） | 不改 `U19`／`U20` 程式與測試。以實讀事實改寫 `security-design.md` §八 第 4 項，見 §九 第 4 列與 §八 Network exposure 格 | 紀錄 |
| 13 | nfr-design | R-02 | 靜態鎖第 5 條：`Attribute` 與 `Name` 兩種形式、`ImportFrom` 匯入三個名稱，皆只准在 `services/hierarchy_facade.py`；`G8`、`G9` 紅後綠 | 完成 |
| 14 | nfr-design | R-03 | (e') `test_e2_delete_system_with_diagram_removed_owner_404_not_409`（以 ORM 把一張 `user_diagrams` 指向該系統構造）；`G3` 對兩個方法各一次（`G3a`／`G3b`） | 完成 |
| 15 | nfr-design | R-04 | `schema_rbac.sql` 檔頭 J 區塊涵蓋說明補一行、檔尾 J 驗證註解補 `pg_indexes` 查詢與「應回 1 列」；`grep -c ix_project_members_user_id schema_rbac.sql` 為 4（DDL、改寫的說明註解、檔頭、檔尾） | 完成 |
| 16 | infrastructure-design | R-01（Major，使用者裁決） | `DEPLOY.md` 新小節：先列 2.2.7 前置；容器內 `docker compose -f deploy/docker-compose.deploy.yml exec backend python scripts/run_meta_schema_migration.py; echo "exit=$?"`（無 TTY 加 `-T`）；驗證 `docker exec -i <db-container> psql -U postgres -d cloud360 -c "…pg_indexes…"`（形式同 `DEPLOY.md` 2.1 的 A）；明寫不發布 5432、不以重跑整支 `schema_rbac.sql` 取代。服務名與工作目錄已於 Step 1 實讀（§二） | 完成 |
| 17 | infrastructure-design | R-02 | `test_M3b` 以 `ast.parse` ＋ `ast.literal_eval` 取 `EXPECTED_INDEXES` 的**值**比對三元組；`D1`（只刪 `EXPECTED_INDEXES` 一列、保留哨兵）使它紅 | 完成 |
| 18 | infrastructure-design | R-03 | 紀錄：§九 第 6 列 | 紀錄 |
| 19 | infrastructure-design | R-04 | 紀錄：§九 第 7 列 | 紀錄 |
| 20 | infrastructure-design | R-05 | `DEPLOY.md` 新小節第 1 步即 2.2.7 前置；第 6 步的三種資料庫狀態寫明 `create_all` 建表缺 COMMENT（`OPEN-ID19-1`）且仍須跑一次遷移腳本 | 完成 |

計數：20 項，0 項拒絕；程式／文件 15 項、只做紀錄 5 項（#5、#10、#12、#18、#19）。

## 八、blocking 同步確認與 ADR-0006

### 八之一、`project.md` 三條規則

| 規則 | 判定 | 完成證據 |
|---|---|---|
| schema ↔ deploy 同步（blocking） | **觸發**（新增索引） | `schema_rbac.sql`：DDL（`J)` 區塊、單行、無 schema 前綴、`IF NOT EXISTS`）、說明註解改寫、檔頭涵蓋清單、檔尾驗證註解；`DEPLOY.md`：2.2.9 表的 `project_members` 列補索引、結束碼說明 7 → 9（並更正 7 本身已錯）、新增部署後步驟小節（含 `psql` 驗證指令）、2.2.10 的 owner-scoped 句改寫 |
| `LOCAL-DEV.md` 同步 | **不觸發** | 未改 `backend/database.py` 的 schema 補丁、`deploy/nginx.conf`／`frontend/nginx.conf`、任一 `.env.example`、`render-env.sh`（`git diff --stat` 為空）——使用者裁決「不動啟動路徑」 |
| env contract | **不觸發**（零新變數） | `validate_env_contract.py` passed |

### 八之二、ADR-0006 四面向（逐格對照計畫 §六之二）

| 面向 | 計畫判定 | 實作後判定 | 證據 |
|---|---|---|---|
| IAM | 適用（擴充） | **相同** | 列舉放寬（`BR87`）＋ 寫入守門（三條路徑）＋ 固定訊息 ＋ 靜態鎖五條；`K2` 判定仍只在 `HierarchyFacade._authorize` 一份；allow／deny 雙向 `TestClient`（列舉 16 案、寫入 22 案） |
| Encryption | 相同（落點 `U21`） | **相同** | 零新傳輸、零新持久資料；新索引不含新資料；前端草稿不落地（`PPN-17` grep 為 0） |
| Network exposure | 相同（落點 `U21`） | **相同**，措辭依 nfr-design R-01 改寫：本單元會回 404 的四條路徑（系統清單、建立系統、刪除專案、刪除系統）「不存在 vs 不可見」以 `response.content` 逐位元證明相同；`U19` 成員清單（`membership_facade.py:207-221` 的 `list_members`：先 `_assert_project_exists`（`:114-137`）回 404「查不到專案 {id}」、再 `_require_project_role`（`:139`）回 403）與 `U20` 需求欄位端點（`requirement_field_facade.py:242-264` 的 `_authorize`：系統不存在回 `RequirementFieldNotFound`、非成員回 `RequirementFieldForbidden(reason="not_member")`）仍可由 404／403 區分專案或系統是否存在（不洩漏內容；使用者已接受為殘留） | 零新端點、零新埠；部署步驟明寫不發布 5432 |
| Audit logging | 適用（擴充，`[PPD1]`=A） | **相同** | 成功刪除記 `actor_user_id`（`assertLogs` 兩案）；連帶刪除筆數不記（殘留） |

**PBT**：不適用（非 IaC generator、cost calculator、agent routing）；可見性兩分支以五身分 ＋ 守門矩陣 example-based 窮舉，與計畫一致。

## 九、設計文字回補表（設計檔不回改，以本表為準）

| # | 設計檔位置 | 原文要點 | 本單元的事實／取代 | 依據 |
|---|---|---|---|---|
| 1 | `functional-design/rules.md` `BR87.6`、`functional-spec.md` §八 `OPEN-PP23-10` | 被移出的建立者在 API 層仍能建立系統、刪除專案與系統；「本 intent 內無自然承接站」 | **已取代**：三條寫入路徑加可見性守門，被移出者一律 404；`OPEN-PP23-10` 於本單元關閉。`BR87.6` 其餘範圍宣告（擁有者範圍的列舉方法不變、大腦對象目錄仍為擁有者範圍）仍成立 | functional-design R-01 使用者裁決（2026-10-15T22:46:22Z） |
| 2 | `[PP3]` 選項文字中的「零 schema 變更」 | 不改 schema | **已取代**：新增索引 `ix_project_members_user_id` | `[PPN1]`=A |
| 3 | `functional-design/rules.md` `BR86.2` 的標示與空態文字 | 「只含經大腦、且為你自己擁有之圖的變更」；「你擁有的圖尚無經大腦的變更」 | 以「只含經大腦、已歸屬系統、且為你自己擁有之圖的變更」與「沒有符合條件的變更紀錄」取代 | functional-design R-02 |
| 4 | `nfr-design/security-design.md` §八 第 4 項 | 「成員頁的 404 訊息仍含 id（`membership_facade.py:132-136`、`membership_service.py:194`／`:431`）」 | 實讀：`membership_facade.py` 的 `raise MembershipNotFound(f"查不到專案 {project_id}")` 在 `:133`、`:135`、`:137`；`membership_service.py` 在 `:194` 與 **`:495`**（`:431` 已因本單元在該檔新增可見性段落而下移——該處內容未變）。可區分性：`list_members`（`membership_facade.py:207-221`）先 404 後 403；`requirement_field_facade.py:242-264` 的 `_authorize` 不存在 404、非成員 403。兩處皆為使用者接受的殘留 | nfr-design R-01 |
| 5 | `security-design.md` §一之三「五條路徑各一案」 | 五條 | 實為**四**條會回 404 的路徑（專案清單只回 200／403，無 404 可比）；計畫 §二 #6 亦寫四條。本單元四案皆有 | 計畫 §二 #6 |
| 6 | `infrastructure-design/cicd-pipeline.md` §四 的 ✅ | 表示該閘門擋下 | 讀為「訊號（不擋合併）」——`ut` 無必要狀態檢查，CI 紅燈只是訊號 | infra R-03 |
| 7 | `cicd-pipeline.md` §三 第 5、6 列 | 第 5 列：表不存在時的後果；第 6 列：`U20` → `U23` → `U21` 的合併順序 | 第 5 列改述為「`create_all` 會連同索引建表，真實後果是缺 COMMENT 且需先跑 2.2.7」；第 6 列為 bolt-plan 的排序性質，已非現況（`763a45a` 的 `U21` 已早於本單元） | infra R-04 |
| 8 | `functional-spec.md` §十之一 第一個空表 | 空表 | 格式缺陷，以散文後的單一表格為準 | functional-design R-05 |
| 9 | `nfr-requirements/security-requirements.md` §五「刪除不記稽核」 | 刪除不記 | 更正為「改前已有 INFO log（含 id，`hierarchy_service.py` 的 `刪除專案 %s`／`刪除系統 %s`），只是沒有 actor」；`[PPD1]`=A 補上 actor（記在 facade 層 `cloud360.hierarchy_facade`） | nfr-design `security-design.md` §五之一、nfr-requirements R-06 |
| 10 | `nfr-requirements/performance-requirements.md` §二之一 | 4 由連線池「確認」 | 改讀為經驗值（`performance-design.md` §三） | nfr-requirements R-05 |
| 11 | `performance-design.md` §二之二 專案清單的語句序列 | `K2 view` → `UNION` → `IN` 查詢 | 實作為 `UNION` 先、`K2 view` 後（`list_projects_by_ids` 以 id 集合為參數）；被拒時結果丟棄、不回傳任何東西。語句數仍與 P 無關（`PPN-06` 綠） | §十 D-5 |
| 12 | `frontend-components.md` §三 `OverviewTab` 持有 `changes`／`changesStatus` | 總覽籤自行抓變更紀錄 | 改由 `ProjectDetailPage` 持有 `changesBySystem`：端點 7 必須與端點 5 共用同一個佇列並排在其後（functional-design R-04），只有頁面能決定入列順序 | §十 D-6 |
| 13 | `logical-components.md` §三 #8 的驗證指令 `psql "$DATABASE_URL" …` | 主機直連形式 | 依 infra R-01 使用者裁決改為容器內 `docker exec` 形式（`DEPLOY.md` 新小節） | infra R-01 |

## 十、偏離計畫之處（全部列出）

| # | 偏離 | 理由與影響 |
|---|---|---|
| D-1 | router 三支**寫入** handler 的注入（計畫 Step 9）提前到 Step 7 | 簽章改為必填後，router 不改即在執行期 `TypeError`；Step 8 的靜態鎖第 3 條也以 router 呼叫為斷言對象。兩支**列舉** handler 仍在 Step 9 |
| D-2 | `ALWAYS_VISIBLE` 寫成具名函式而非 `lambda` 指派 | 語意相同（恆真）；避免 lambda 指派的風格問題，並附 docstring |
| D-3 | `test_project_visibility_endpoints.py` 為 **16** 案（計畫 15） | 新增 `E14b`：`M5` 的第二變體（拿掉 `list_systems_unscoped` 的 `K2`）在 HTTP 層**不可能**變紅——`list_visible_systems` 第一步的 `project_exists` 已先判 `K2`。故以直接呼叫 facade 鎖住「`K2` 判定不假設呼叫端已檢查」，同案也對 `list_projects_by_ids(project_ids=[])` 斷言 403 |
| D-4 | 靜態鎖第 1 條另允許 `hierarchy_service.list_projects_by_ids(...)` 出現在 `HierarchyFacade` 內 | service 層有同名函式；該形式只准在 facade 內，否則等同直呼 service 層繞過 `K2` |
| D-5 | 專案清單的可見 id 查詢早於 `K2` 判定一條語句 | `list_projects_by_ids` 的簽章以 id 集合為參數（`BR87.3` 定名），故必須先算 id。缺 `K2` 者仍得 403 而非 200 `[]`（`E11`、`E12`），結果不外洩 |
| D-6 | `changesBySystem` 由 `ProjectDetailPage` 持有（設計寫 `OverviewTab`） | 見 §九 第 12 列 |
| D-7 | 只渲染目前籤的 tabpanel | 兩處 `SystemCreateAction` 不會同時掛載（`data-testid` 不重複）。初版的代價是需求籤未儲存的草稿在切籤時遺失；**審查修正 R-02 已消除**——輸入狀態上提到頁面（§十四） |
| D-8 | 新增 `lastGoodFields` state | `BR85.6` 要求重讀失敗時成功欄位保留送出值並標示，而此時 `fieldsBySystem` 該筆為 `'failed'`、沒有欄位結構可渲染 |
| D-9 | 突變還原以記憶體中的原檔寫回，而非 `git checkout -- <檔>` | 被突變的檔含本單元未 commit 的實作 |
| D-10 | 突變代號拆子變體（44 次實跑） | 見 §六；道數仍為 36 |
| D-11 | 新增設計表以外的 `data-testid` | `project-list-empty-create`、`project-list-row-count-<id>`、`project-list-row-systems-<id>`（含 `data-state`）、`project-list-open-<id>`、`project-list-skeleton`、`system-create-form`／`-name`／`-submit`／`-cancel`／`-error`、`requirements-unsaved-<g>-<k>`、`requirements-input-hint`、`project-recent-changes-scope`／`-empty`／`-partial`、`project-recent-change-<id>`、`project-detail-error`、三頁根節點。設計表列出的 testid 全部存在 |
| D-12 | e2e 以 `vite` dev server 與 `vite preview` 執行，未起 docker-compose 測試 stack | 見 §五 |
| D-13 | 三支寫入 handler 的 docstring 不改、改寫為程式註解 | 使 `openapi.json` 只漂移兩支（計畫 §七 第 2 點的揭露範圍）；初版曾改 docstring 造成五支漂移，已修正並重 dump |
| D-14 | `DEPLOY.md` 新小節放在 2.2.9 的最末（`U20` 欄位收斂小節之後、2.2.10 之前） | 2.2.9 已有兩個子小節，置於最末使「既有環境重跑同一支腳本」的步驟緊接在該腳本所有說明之後 |

## 十一、殘留與開放項

1. **後端全套的 4 筆失敗與本單元無關**：`test_progress_channel_contract.RunDesignAgentCallSiteTest` 以檔案系統掃描 repo，掃到 repo 根目錄下的 `.kilo/worktrees/secret-deposit/backend/services/{agent_router,wa_collab_orchestrator}.py`（`git worktree list` 顯示它是本 repo 另一個已登錄的 worktree，detached 在 `4ef3e04`；不在本工作樹的 `git ls-files` 中、`git status` 不列出）。CI 的乾淨 checkout 沒有這個目錄。本單元未刪除它（非本單元產物）。
2. **`mcp` 環境限制**：全域 python3 3.13 未裝 `mcp`，`test_mcp_bridge_*` 共 28 筆失敗；在 3.12 venv 下全綠（含本單元補參數的 `test_mcp_bridge_e2e.py`）。
3. **dev 模式的 StrictMode 雙執行**：見 §五；已於乾淨 HEAD 驗證為既存（§十四 R-05），非本單元引入。
8. **建立者被移出後，該專案無人能建立系統、刪除系統或刪除專案**（審查 R-03，不改行為）：三條寫入路徑在守門之後仍保留既有的 `owner_user_id` 檢查。被移出的建立者（`owner_user_id` 仍是他）過不了守門；其餘成員（含 `project_admin`）又不是 `owner_user_id`，過不了擁有者檢查；`SystemCreateAction` 也只對擁有者渲染。這是 functional-design R-01 使用者裁決的直接後果，本單元依裁決不改。**後續承接（需另開 intent 或由 conductor 提交使用者）**：二擇一——(a) 移出建立者時同步把 `owner_user_id` 移轉給一位留下的 `project_admin`（`[PP3]` 選項 C 的方向，需改 `U19` 的移出流程）；(b) 寫入路徑改以 per-project 角色（`project_admin`）判定而非 `owner_user_id`（需改 `U7` 的 `BR6.5` 與前端 `BR82.4` 的渲染條件）。
9. **其他會讀 `schema_rbac.sql` 的部署步驟有同一個問題**（審查 R-01 的延伸檢查，不擴大修改）：`backend/scripts/seed_retention_system_actor.py`（`DEPLOY.md` 2.2.11）經同一個 `extract_blocks`／`SCHEMA_FILE` 讀 `schema_rbac.sql` 的 `K)` 區塊，在 backend 容器內執行同樣會讀不到。而 2.2.7、2.2.9（`U18` 原有段落）、2.2.11 的指令皆為主機形式 `cd backend && python scripts/…` ＋ `DATABASE_URL`，在 staging 上 `db` 服務沒有發布 host port（`DEPLOY.md` 2.1 明令不得發布 5432），主機形式本身就連不到資料庫——實務上只能進容器跑，而進容器跑又會撞上本項（`run_hierarchy_migration.py` 不讀 `schema_rbac.sql`，進容器可行）。本單元只修正 `U23` 自己新增的那一處；其餘建議由 conductor 另案處理（可沿用同一個 `docker compose cp schema_rbac.sql backend:/schema_rbac.sql` 前置步驟）。
4. **交給 tcms-test-cases**：本檔 §六 的突變表轉入 `automation-test-plan.md`；手動桶候選只有一項——staging 部署後以 `docker exec … psql` 驗證 `ix_project_members_user_id` 存在（`DEPLOY.md` 新小節第 3 步），因為沒有任何自動化會發現它缺席。
5. **交給 build-and-test**：在 CI 的 `memory-schema` job（真實 PostgreSQL）確認 `schema_rbac.sql` 連套兩次與遷移腳本皆 exit 0、腳本輸出「索引 9 個」——SQLite 測試庫不驗 PostgreSQL 的 `CREATE INDEX` 語法與可重跑性，本機未跑該 job。
6. **由 conductor 重新提交使用者的開放項**（計畫 §七 第 8 項）：`OPEN-PP23-1`（架構圖計數無來源）、`OPEN-PP23-3`（記憶彙整無來源）、`OPEN-PP23-4`（`[設定]` 無目的地）、`OPEN-PP23-6` 第 ③ 項（大腦對象目錄仍為擁有者範圍）——是否另開 intent。
7. **`OPEN-PP23-9`** 第 ①②③ 項（`U7` 規則 6.2 過時、`K-16` 消費端與新方法、`U23` → `U19` 依賴邊與 `U23` → `U8` 不再使用）仍待下一輪契約追認；第 ④ 項已於本單元處理（`DEPLOY.md`、`backfill_project_members.py` 檔頭）。

## 十二、核可關卡需揭露事項（計畫 §七，依實作結果更新）

1. **級聯刪除**：刪除專案經 `ON DELETE CASCADE` 刪除**全部**成員列（含其他管理者）；刪除系統刪除其**全部**需求欄位值（含其他成員所填）。守門使**被移出的建立者**不再能觸發；**仍是成員的擁有者**觸發它們是 `U7` 既有的合法行為，未改。成功刪除只多記刪除者，不記連帶筆數。
2. **`openapi.json` 漂移**：兩支列舉 operation 的 `description`（+2／−2 行），已重 dump 並重產 `api.d.ts`。
3. **既有 404 的 `detail` 改變**：`U7` 經 `assert_*_owned_by`／`get_project_*` 的 404 由「查不到專案 12」變為「查不到專案」（系統同形），狀態碼不變。實查 `backend/tests`、`frontend/src` 對帶 id 訊息的斷言為 0；全套測試未因此出現新失敗。
4. **跨單元測試檔**：`U7`、`U12`、`U20`、`U21` 的四支測試檔共 15 處只補一個關鍵字參數，斷言不動。
5. **部署後人工步驟**（無聲失敗）：見下方「需人工執行的部署後步驟」。
6. **`test_M3b`** 落地 infrastructure-design §四之一 的建議（非上游定案）。
7. **`DEPLOY.md` 的既存漂移**：「7 個索引」改前已與腳本的 8 筆不符，本次一併改為 9。
8. **開放項**：§十一 第 6 項。
9. **殘留**：**建立者被移出後該專案無人能建立／刪除系統或刪除專案**（§十一 第 8 項，審查 R-03）；守門與寫入之間未加鎖；連帶刪除無筆數紀錄；`U19`／`U20` 的 403／404 可區分（已接受）；`DELETE /systems/{sid}` 對成員非擁有者回專案句（已論證非預言機）；程式回滾會讓寫入守門消失（`OPEN-PP23-10` 隨之重開）；部署冒煙不碰 `/api/hierarchy/*`；連線池約 3 位使用者同時進入系統數多的專案即可耗盡（4 是經驗值）；卸載時在途請求不中止（只丟棄結果）；專案清單的可見 id 查詢早於 `K2` 判定一條語句（D-5）。
10. **e2e 全為攔截式**：不打真實後端；伺服器授權由 `TestClient` 承擔，形狀一致由兩道漂移閘門承擔。

## 十三、需人工執行的部署後步驟（staging `192.168.10.10`，合併部署完成後）

在 repo 根目錄：

```bash
# 前置：2.2.7 的 run_hierarchy_migration.py 已跑過（未跑則依 DEPLOY.md 2.2.7 先跑）
# 先把 schema_rbac.sql 放進 backend 容器的 /schema_rbac.sql（腳本以 BACKEND_DIR.parent 讀它；審查 R-01）
docker compose -f deploy/docker-compose.deploy.yml cp schema_rbac.sql backend:/schema_rbac.sql
docker compose -f deploy/docker-compose.deploy.yml exec backend python scripts/run_meta_schema_migration.py; echo "exit=$?"
# 必須 exit=0，且成功輸出的「索引」為 9 個；無 TTY 的環境加 -T

# <db-container> 取法：docker compose -f deploy/docker-compose.deploy.yml ps -q db
docker exec -i <db-container> psql -U postgres -d cloud360 -c "SELECT indexname FROM pg_indexes WHERE tablename='project_members' AND indexname='ix_project_members_user_id';"
# 應回 1 列
```

不要發布 5432；不要以重跑整支 `schema_rbac.sql` 取代（`C) RBAC` 區塊會覆寫權限矩陣）。遺漏時功能正常、清單查詢無聲變慢，沒有任何自動化會發現。完整說明見 `DEPLOY.md` 2.2.9 的「`U23` 起：部署後再跑一次遷移腳本」小節。

## 十四、審查修正（`review` 1：READY，2 Major ＋ 3 Minor；使用者裁決「這批一起修」）

> 修正完成時間 2026-10-16T23:06:03Z（`date -u` 取值）。審查全文在引擎目錄，唯讀，未修改。

| ID | 嚴重度 | 處置 | 落點 | 驗證 |
|---|---|---|---|---|
| R-01 | Major | **修正部署步驟**，零程式改動：在執行前以 `docker compose -f deploy/docker-compose.deploy.yml cp schema_rbac.sql backend:/schema_rbac.sql` 把檔案放到腳本實際讀取的位置（容器內 `REPO_ROOT` 為 `/`）。選 (a) 而非新增參數（腳本 `main()` 明定不接受選項，改它需動 `U18` 的契約與測試；`cp` 是最小改動）或 (c)（直接下 `CREATE INDEX` 會繞過腳本的後條件查驗，結束碼 0 不再代表 9 個索引都在） | `DEPLOY.md` 2.2.9「`U23` 起」小節第 2 步（說明原因、2a 複製、2b 執行；複製檔隨下次部署重建容器而消失）；本檔 §二 複驗表、§十三 | **以等價方式實測（未能在 staging 或本機 docker 實走）**：本機 docker daemon 未啟動、也無法連到 staging，故在 scratchpad 重建容器內的目錄形狀（`<root>/app` ＝ 複製的 `backend/`，`<root>` 對應容器的 `/`），對本機 PostgreSQL 的一個拋棄式資料庫 `u23_r01_check`：先套 `schema_rbac.sql` 再 `DROP INDEX ix_project_members_user_id`（模擬 staging「表在、索引不在」）。① 未放檔直接跑（3.12 venv）：`exit=1`，錯誤逐字「無法從 schema_rbac.sql 取出 DDL：[Errno 2] No such file or directory」——**重現審查所述失敗**；② 把 `schema_rbac.sql` 複製到 `<root>/schema_rbac.sql` 後再跑：`exit=0`，輸出「索引 9 個」，`pg_indexes` 回 1 列；③ 再跑一次：`exit=0`（可重跑）。拋棄式資料庫已 `DROP`。**未驗證的部分**：`docker compose cp` 本身在 staging 的行為（Compose v2 支援此子指令，本機 client 為 v5.5.1）與複製後檔案對容器內 `appuser` 的可讀性——後者依 Docker 的 cp 語意沿用來源檔權限；staging 實走仍待人工 |
| R-02 | Major | 需求籤的 `selected`、`drafts`、`fieldErrors`、`savedStale` 上提到 `ProjectDetailPage`（以 `RequirementsInputState` 物件傳入），需求籤只保留「儲存中」「重新整理中」兩個暫態；載入成功時在 `.then` 內重設（不在 effect body 同步 setState） | `frontend/src/pages/ProjectDetailPage.tsx`、`frontend/src/components/projects/RequirementsTab.tsx`；新 e2e 'keeps unsaved input and failure marks after switching tabs' | e2e 23 passed；突變 `F11`（三個狀態改回需求籤本地 `useState`）→ 該新案紅（`1 failed, 22 passed`），還原 → `23 passed`；lint 0 errors |
| R-03 | Minor | 不改行為，寫入殘留與開放項並指定兩個承接方向 | 本檔 §十一 第 8 項、§十二 第 9 項 | — |
| R-04 | Minor | 以渲染時推導 `invalidId = !Number.isInteger(projectId) \|\| projectId <= 0`：為真時直接渲染 `ProjectNotFound`、LiveRegion 播報「查不到這個專案」、effect 不發請求 | `frontend/src/pages/ProjectDetailPage.tsx`；新 e2e 'renders not-found for a non-numeric project address'（斷言 not-found、無「正在載入專案…」、`/api/hierarchy` 請求 0） | 突變 `F12`（`invalidId` 恆假且 effect 回到 `!Number.isFinite` 直接 return）→ 該新案紅，還原 → `23 passed` |
| R-05 | Minor | 以 `git worktree add --detach <scratchpad>/head-wt HEAD`（`a898f31`）建乾淨 HEAD，`node_modules` 以符號連結共用，起 dev server（`:5197`）跑 `member-pages.spec.ts` ＋ `memory-page.spec.ts` | 本檔 §五、§十一 第 3 項 | HEAD：`9 failed, 16 passed`；本工作樹 dev server 同兩支：`9 failed, 16 passed`，失敗案名逐一相同（member-pages 3 案：`queries pending reselections…`、`updates the list in place…`、`issues exactly one member-list request…`；memory-page 6 案：`first load sends exactly three GETs…`、`paging during a delayed resync…`、`re-entering the page refetches…`、`a failing refetch after a delete…`、`zones load in parallel…`、`double-clicking next…`）→ **既存，非本單元引入**。worktree 已 `git worktree remove --force` 並 `prune`，`git worktree list` 不再列出；未 stash、未動目前工作樹 |

### 十四之一、修正後的重跑結果

| 項目 | 結果 |
|---|---|
| 本單元後端（3.12 venv，全單元 11 模組） | `Ran 145 tests` OK |
| 同上（全域 python3，去掉 `test_mcp_bridge_e2e`） | `Ran 130 tests` OK |
| `dump_openapi.py --check` | 一致 |
| `validate_repo_contract.py`／`validate_env_contract.py` | 皆 passed |
| `npm run lint` | `✖ 2 problems (0 errors, 2 warnings)`（同基準） |
| `npm run build` | 綠 |
| `npm run check:types` | 一致 |
| e2e 本 spec（dev server） | 23 passed |
| e2e 本 spec ＋ `member-pages` ＋ `memory-page`（production build） | 48 passed |

### 十四之二、突變（審查修正新增）

| 代號 | 突變 | 改動檔 | 套用後 | 還原後 |
|---|---|---|---|---|
| `F11` | 需求籤輸入狀態改回需求籤本地 `useState`（切籤即卸載） | `frontend/src/components/projects/RequirementsTab.tsx` | 紅（1 failed；22 passed）：`keeps unsaved input and failure marks after switching tabs` | 綠（23 passed） |
| `F12` | 非數字專案 id 回到「effect 直接 return、停在載入中」 | `frontend/src/pages/ProjectDetailPage.tsx` | 紅（1 failed；22 passed）：`renders not-found for a non-numeric project address` | 綠（23 passed） |

應用程式檔集合未增減（只修改既有的 `DEPLOY.md`、`ProjectDetailPage.tsx`、`RequirementsTab.tsx`、`project-pages.spec.ts`），`source-manifest.json` 仍為 39 筆。

## 十五、合併前必修第 14 項：成員與需求欄位端點不洩漏專案／系統是否存在（計畫 §九 Step 16–20）

> 完成時間 2026-10-24T06:44:33Z（`date -u +%Y-%m-%dT%H:%M:%SZ` 取值）。使用者裁決 `[PP-MB14]`=A（2026-10-24）。零 DDL、零新環境變數、零新依賴。

### 十五之一、實作（Step 16、Step 18）

| 檔 | 改動 |
|---|---|
| `backend/services/membership_facade.py` | `_require_project_role`：非成員（`resolve_project_role` 回 `None`）改丟 `MembershipNotFound(PROJECT_NOT_FOUND_DETAIL)`，照記 `log_denied`；是成員但非 `project_admin` 仍丟 `MembershipForbidden`（403）。`_assert_project_exists` 三處 `f"查不到專案 {project_id}"` 改為 `PROJECT_NOT_FOUND_DETAIL`（沿用 `hierarchy_facade` 的常數，不另抄字串）。缺 `K2` 轉 404 的行為保留。四個端點（清單、邀請、移出、改角色）共用這兩個方法，故一次涵蓋 |
| `backend/services/membership_errors.py` | `MembershipNotFound` docstring：原「不用於非成員」改寫為「`resolve_project_role` 仍回 `None`，受保護操作的非成員拒絕改用本例外」 |
| `backend/services/membership_router.py` | `NOT_FOUND_RESPONSE`／`FORBIDDEN_RESPONSE` 說明改寫（403 不再含「不是該專案的成員」；404 涵蓋非成員） |
| `backend/services/requirement_field_facade.py` | `_authorize` 非成員：先 `_log_denied(..., "not_member")`（WARNING 照記）再丟 `RequirementFieldNotFound`；拆出 `_log_denied`（只記不拋），`_deny` 改為呼叫它後丟 403 |
| `backend/services/requirement_field_errors.py` | 新增 `NOT_FOUND_DETAIL = SYSTEM_NOT_FOUND_DETAIL`（沿用 `hierarchy_facade`）；`RequirementFieldNotFound` 訊息一律為「查不到系統」、**不含 id**（`system_id` 仍留在屬性上） |
| `backend/services/requirement_field_router.py` | `ERROR_RESPONSES` 的 403／404 說明改寫 |
| `openapi.json`、`frontend/src/types/api.d.ts` | `python3 scripts/dump_openapi.py`（輸出「已寫入 openapi.json」）→ `npm run gen:types` 重產；兩檔各含 7 處「合併前必修第 14 項」（`grep -c`）。**如實記載**：兩檔對 HEAD 的 diff 也含工作樹內其他單元尚未提交的 schema（例如 `DeleteUserConflict`），那是由現行程式碼決定性產出，不是本節新增 |
| `frontend/src/membership/membershipApi.ts` | 新增 `PROJECT_NOT_FOUND_MESSAGE = '查不到這個專案'` 與 `ProjectNotFoundError`；`fetchMembers` 對 404 丟它（不顯示伺服器訊息）；403 維持原權限句。成員清單頁與成員詳情頁都經 `fetchMembers`，故 `MemberDetailPage.tsx` 不需改碼 |
| `frontend/src/pages/MembersListPage.tsx` | 註解同步（「`list_members` 對非成員回 404」） |

### 十五之二、測試（Step 17、Step 19）

| 檔 | 案例 | 對應 |
|---|---|---|
| `backend/tests/test_membership_endpoints.py` | `test_E1` 非成員兩案 403→404（**方法名不改**）；新增 `test_E11`（四端點 ×「不存在 vs 非成員」status＋`content` 逐位元相同、本體 `{"detail": "查不到專案"}`、不含任一 id、成員列數不變）、`test_E12`（成員但非管理者寫入 403；缺 `K3` 對存在／不存在 id 皆 403 且 `content` 相同）、`test_E13`（非成員 404 後 `membership.denied` 照記） | N1、N2 |
| `backend/tests/test_membership_facade.py` | `test_F5b`：非成員改斷言 `MembershipNotFound`，訊息與不存在的專案相同 | N1 |
| `backend/tests/test_requirement_field_facade.py` | `test_F7`／`test_F8`／`test_R3`：非成員改斷言 `RequirementFieldNotFound`；`F8`／`R3` 仍斷言恰一行 `reason=not_member` 的 WARNING | N3、N4 |
| `backend/tests/test_requirement_field_http.py` | `test_H1` ②⑩⑫ 三列 403→404；新增 `test_H8`（讀寫清三端點逐位元相同、`{"detail": "查不到系統"}`、不含 id、列數不變）、`test_H9`（三次 404 恰三行 `requirement_field.denied`、`reason=not_member`） | N3、N4 |
| `backend/tests/test_mcp_bridge_e2e.py` | `test_ac11_4_1`：直接存取改為 404，經 MCP 為 `not_found` 且 `message` 等於直接存取的 `detail`；`test_every_branch_and_success_leak_nothing` 的 `forbidden` 分支改由缺 `K4` 的成員（`no_k4`）承擔，另加 `not_found (非成員)` 分支（subTest 標籤，非 TCMS 案名） | N5 |
| `frontend/tests/e2e/member-pages.spec.ts` | 新增 `shows a fixed not-found sentence without the project id when the member list is 404`（清單與詳情皆顯示「查不到這個專案」，頁面文字不含專案編號 48213 與舊形狀 detail）、`keeps the permission sentence when the member list is 403`；stub 加 `membersErrorBody` 選項 | N6 |

### 十五之三、重跑結果（Step 20 閘門）

| 指令（`backend/` 內皆帶 `HYPOTHESIS_STORAGE_DIRECTORY=<scratchpad>/hyp PYTHONDONTWRITEBYTECODE=1 python3 -B`） | 結果 |
|---|---|
| 修改前基準：`-m unittest tests.test_membership_endpoints tests.test_membership_facade tests.test_project_visibility_endpoints tests.test_requirement_field_facade tests.test_requirement_field_http tests.test_mcp_bridge_e2e` | `Ran 76 tests` OK |
| 只改實作、尚未改測試，同一指令 | `FAILED (failures=13, errors=6)`（全部是預期改變的非成員案） |
| 改完測試，同一指令 | `Ran 81 tests` OK（新增 E11、E12、E13、H8、H9） |
| `-m unittest discover -s tests` | `Ran 1319 tests` OK（`skipped=3`） |
| `python3 -B scripts/dump_openapi.py --check` | 「規格檔與後端程式碼一致。」exit 0 |
| `npm run check:types` | 「API 型別檔與規格檔一致。」 |
| `npm run lint` | `✖ 2 problems (0 errors, 2 warnings)`（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344` 的 `exhaustive-deps`，同既有基準） |
| `npx tsc -b` | exit 0 |
| `npm run build` 後 `npx vite preview --port 4791`；`BASE_URL=http://localhost:4791 npx playwright test tests/e2e/member-pages.spec.ts` | `13 passed` |
| 同上，`tests/e2e/project-pages.spec.ts`（回歸） | `23 passed` |
| repo 根：`python3 scripts/validate_repo_contract.py`／`validate_env_contract.py` | 皆 passed |

### 十五之四、突變（套用 → 紅 → 還原 → sha256 對照基線 → 綠；後端帶 `HYPOTHESIS_NO_SHRINK=1`）

還原一律以檔案編輯工具逆向改回，**未用 `git checkout`**（工作樹含 Step 1–15 尚未提交的改動，checkout 會一併抹掉）。

| 代號 | 突變 | 套用後（指令 → 紅） | 還原後 sha256（＝基線） | 綠 |
|---|---|---|---|---|
| `M14-1` | `membership_facade._require_project_role` 非成員改回 `raise MembershipForbidden(...)` | `-m unittest tests.test_membership_endpoints` → `FAILED (failures=6)`：`test_E1`、`test_E11`（GET／POST／DELETE／PATCH 四個 subTest）、`test_E13` | `0779d0f5…eea72ac` | `Ran 13 tests` OK |
| `M14-2` | `_assert_project_exists` 不存在分支改回 `f"查不到專案 {project_id}"` | `tests.test_membership_endpoints tests.test_membership_facade` → `FAILED (failures=5)`：`test_E11` 四個 subTest、`test_F5b` | `0779d0f5…eea72ac` | `Ran 29 tests` OK |
| `M14-3` | `requirement_field_facade._authorize` 非成員改回 `self._deny(..., "not_member")`（403） | `tests.test_requirement_field_http tests.test_requirement_field_facade tests.test_mcp_bridge_e2e` → `FAILED (failures=16, errors=5)`：含 `test_H8` 三個 subTest、`test_H9`、`test_H1` ②⑩⑫ 九個 subTest、`test_F7` 三個、`test_F8`、`test_R3`、`test_ac11_4_1`、leak 測試 `not_found (非成員)` 兩個 mode | `0d7e4f37…e5557056` | `Ran 36 tests` OK |
| `M14-4` | 拿掉非成員的 `self._log_denied(...)`（只丟 404） | 同上指令 → `FAILED (failures=3)`：`test_H9`、`test_F8`、`test_R3` | `0d7e4f37…e5557056` | `Ran 36 tests` OK |
| `F14` | `membershipApi.fetchMembers` 的 404 改回 `throw new Error(detailMessage(body, '讀取成員失敗'))`（顯示伺服器訊息） | 重 build 後 member-pages e2e → `1 failed, 12 passed`：`shows a fixed not-found sentence without the project id when the member list is 404` | `7d2ac75c…3059dbb` | 重 build 後 `13 passed` |

### 十五之五、取代關係與殘留

- **取代**：`../carried-review-items.md:41` 的「R-01 使用者裁決：接受為殘留……U19 成員清單與 U20 需求欄位端點仍以 404／403 區分」由本節取代（合併前必修第 14 項，`[PP-MB14]`=A）。該檔與已凍結的設計檔**不回改**；`security-design.md` §八 殘留第 4 項同樣以本節為準。
- **殘留 1**：`membership_service.lock_project`（`:259`）與 `assert_still_has_admin`（`:667`）仍以 `f"查不到專案 {project_id}"` 拋 404；`change_role` 對目標非成員回「使用者 X 不是專案 Y 的成員」。三者只在呼叫者**已通過管理者判定**之後才可達（併發刪除或目標不在專案內），呼叫者已知該專案存在，不構成存在性探測；本節不改。
- **殘留 2**：「零成員列專案的擁有者」在階層端點可見（`BR87.1` 的擁有者分支），但成員端點以**成員列**判定，故他打成員頁由 403 變為 404「查不到專案」。行為面同樣是拒絕，只是狀態碼改變；與階層端點的可見語意不一致屬既有設計（成員頁只認成員列），本節未擴大。
- **殘留 3**：前端寫入端點（邀請、移出、改角色）的 404 仍顯示伺服器 `detail`——後端該字串已改為不含 id 的「查不到專案」，故不洩漏編號；計畫只要求清單與詳情改固定句。
- **ADR-0006 四面向**：IAM——授權判定順序與結果（放行／拒絕）不變，只改非成員拒絕的對外狀態碼與訊息；稽核——兩處拒絕 log 照記，各有測試鎖住（`test_E13`、`test_H9`，`M14-4` 紅燈證實）；網路暴露——收窄（少一個存在性訊號），無新端點；加密——不適用（無資料存放或傳輸變更）。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-26T02:45:33Z -->

以既有實作逐步查驗已核可計畫，未修改任何程式碼。

- **計畫勾選**：47／47。勾選時留意的偏離（不構成不符）：`ALWAYS_VISIBLE` 寫成帶 docstring 的 `def`（語意相同）；`DEPLOY.md` 部署步驟比計畫多一步 `compose cp schema_rbac.sql`（R-01 的修正，容器內 `REPO_ROOT` 為 `/`、build context 只有 `backend/`，照計畫原指令會失敗）；Step 13「零變更」以 U23 commit `8677b7d` 判定，工作樹內同類檔的改動屬其他單元。
- **測試**（工作樹含其他單元未提交改動，數字為此工作樹上的結果）：
  - 後端全套 1319 OK（skipped=3）；本單元五檔 membership_data 12、visibility_queries 9、visibility_static 6、visibility_endpoints 16、write_guard 22 皆 OK；11 模組加 `test_requirement_field_http` 合跑 192 OK；`dump_openapi.py --check` 一致。
  - 前端 `npm run lint` 0 errors（2 個既存 `exhaustive-deps`：`AssessmentPage:395`、`WorkspacePage:344`）；`check:types`、`check:ws-types` 一致；兩份 tsconfig `--noEmit` 通過；`vite build` 輸出至 scratchpad。
  - e2e（page.route mock，對 scratchpad build 的 `vite preview`）：`project-pages.spec.ts` 23 ＋ `member-pages.spec.ts` 14，共 37 passed。
  - `validate_repo_contract.py`、`validate_env_contract.py` 通過；repo 內未留下新的快取或建置產物。
- **突變抽驗**（scratchpad 副本，還原後 sha256 與基線相同）：G1、M6、N1（facade 守門）、M14-1、D1、F3 皆紅→綠。**存活一道**：把 `hierarchy_service.assert_project_owned_by` 的訊息改回帶 id 全綠——該位置在守門之後，只有「可見但非擁有者的成員」會走到，本就知道專案存在，不構成存在性探測；但計畫 §五 對 N1「任一處改回…→該路徑的逐位元比較案紅」的字面說法過強。
- **合併前必修第 14 項**：已落地並實測通過（非成員 404 不含 id、角色不足仍 403、拒絕 log 照記；前端清單／詳情與三個寫入函式皆顯示固定句「查不到這個專案」）。第 23 項（`MembersListPage.tsx:55` 非數字 `projectId` 停在載入中）仍待處置、屬 member-pages-ui；本單元頁首 `[成員]` 連結一律帶數字 id，使用流程碰不到。
- **ADR-0006 四面向**：IAM（`K2` 只在 `HierarchyFacade`、寫入順序為授權→可見性守門→擁有者→service）、Encryption（無新持久資料或傳輸，新檔瀏覽器儲存 API 0 命中）、Network exposure（無新端點）、Audit logging（刪除成功記 `actor_user_id`、非成員拒絕記 WARNING）皆與前文一致。
- **前端結構約束**：未新增 Context；資料抓取兩層（純抓取函式＋`.then` 更新＋`cancelled` 旗標）；state 一律回傳新物件。
- **grep 判準**：與前文一致（facade／service 不 import membership、`_visible_project_ids_select` 恰 1 處、`ix_project_members_user_id` 四處同步、前端新檔 `console.` 0、`FANOUT_CONCURRENCY` 恰 1 處）。
- **本摘要既有文字的過時處（原文不回改）**：§一、§五 全套結果「1157 FAILED」已由 §十五 的 1319 OK 取代；§一 lint 行號 `:365`／`:302` 現為 `:395`／`:344`；static 5 案現 6（U14 加 `S3b`）、membership_data 9 案現 12；§十五 member-pages「13 passed」現 14；§十五 殘留 3「寫入端點 404 仍顯示伺服器 detail」已被 review-02 R-07 推翻（三個寫入函式改丟 `ProjectNotFoundError`），處置見 merge-blockers 第 14 列。`traceability.json` 中 `AC12.5.2` 有後端與畫面兩列，為重複列而非缺口。

