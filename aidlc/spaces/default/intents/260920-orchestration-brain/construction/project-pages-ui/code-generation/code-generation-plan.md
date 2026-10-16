# Code Generation Plan — `U23 project-pages-ui`

> 撰寫時間：**未取得**——本計畫起草期間 plan-approval guard 擋下所有 shell 指令（含 `date -u`），依 `project.md` 不編造時間戳。
>
> 本計畫把四站設計（functional-design 修訂 1、nfr-requirements、nfr-design、infrastructure-design）落成程式、測試與文件，並**逐項處置四站審查帶下來的 20 項**（`../carried-review-items.md`：functional-design 5、nfr-requirements 6、nfr-design 4、infrastructure-design 5，見 §二；以 `grep -c "^| R-0"` 實數為 20）。使用者在各關卡的裁決優先於設計產出中對應的段落：`[PP1]`=A、`[PP2]`=A、`[PP3]`=A、`[PPN1]`=A（補索引）、`[PPD1]`=A（刪除者 log）；functional-design R-01（三條寫入路徑套用 `[PP3]` 判準，2026-10-15T22:46:22Z）；nfr-requirements R-01（不含 id 的固定訊息）與 R-02（索引沿用 `U18` 遷移路徑、不動啟動路徑，2026-10-15T23:20:19Z）；nfr-design R-01（U19／U20 的 403／404 可區分接受為殘留，2026-10-15T23:39:42Z）；infrastructure-design R-01（部署後步驟一律容器內形式、不發布 5432，2026-10-15T23:54:17Z）。
>
> 方法論為 `test-after`（§八 的 Testing Contract）：每一層先實作，再寫並執行該層測試。**設計檔一律不回改**（`team.md ## Corrections`）；設計文字的更正與取代寫進 code-summary 的「設計文字回補表」。

## 一、交付範圍

### 一之一、後端

**新檔**

| # | 路徑 | 內容 |
|---|---|---|
| 1 | `backend/tests/test_project_visibility_queries.py` | 可見性謂詞的 service 層五身分案例（Step 5）；兩支列舉端點的 SQL 語句數不變性（`PPN-06`，Step 9） |
| 2 | `backend/tests/test_project_visibility_static.py` | `ast` 靜態鎖：`BR87.7` ＋ `security-design.md` §二之四 三條 ＋ nfr-design R-02 的第四條（Step 7） |
| 3 | `backend/tests/test_project_visibility_endpoints.py` | 兩支列舉端點：五身分 × 兩端點 ＋ 缺 `K2`、系統清單的「不存在 vs 不可見」逐位元比較（Step 9） |
| 4 | `backend/tests/test_project_write_guard.py` | 三條寫入路徑的守門矩陣 (a)–(g) ＋ (e')、`[PPD1]` 的 `assertLogs`（Step 9） |

**改檔**

| # | 路徑 | 改什麼 | 步驟 |
|---|---|---|---|
| 5 | `schema_rbac.sql` | `J)` 區塊 `project_members` 的 `CREATE TABLE` 之後加單行 `CREATE INDEX IF NOT EXISTS ix_project_members_user_id ON project_members (user_id);`（不加 schema 前綴）；改寫 `:608-615` 的「刻意不建」註解；檔頭 `:12-13` 的 J 區塊涵蓋說明補此索引；檔尾 `:1260-1281` 的 J 驗證註解補 `pg_indexes` 查詢與預期 | 3 |
| 6 | `backend/models.py` | `ProjectMember.__table_args__`（`:584`）加 `Index("ix_project_members_user_id", "user_id")`；改寫 `:579-583` 的「刻意沒有額外索引／不得自行補 `index=True`」註解 | 3 |
| 7 | `backend/scripts/run_meta_schema_migration.py` | `EXPECTED_INDEXES`（`:155-170`）加 `("public", "project_members", "ix_project_members_user_id")`；`BLOCK_SENTINELS["J"]`（`:104-117`）加 `"ix_project_members_user_id"`；`:584` 的輸出由 `len()` 計算，自動變為 9，不改 | 3 |
| 8 | `backend/tests/test_membership_data.py` | `test_M3` 的 docstring 改寫「`project_members.user_id` 被補上 `index=True`（刻意不建）」一句；新增對 ORM 與 DDL 各一次的 `assertIn("ix_project_members_user_id", …)`；旁邊新增 `test_M3b`：以 `ast.parse` 讀遷移腳本原始碼、`ast.literal_eval` 取 `EXPECTED_INDEXES` 的值，斷言三元組 `("public", "project_members", "ix_project_members_user_id")` 在其中（infrastructure-design R-02） | 4 |
| 9 | `backend/services/hierarchy_service.py` | 新增 `list_projects_by_ids(db, *, project_ids) -> List[Project]`（空集合直接回 `[]`、不發 `IN ()`；依 id 遞增）；六處帶 id 的 f-string（`:70`、`:77`、`:180`、`:199`、`:381`、`:388`）改用常數，`:89`（架構圖）不改 | 5 |
| 10 | `backend/services/membership_service.py` | 新增私有 `_visible_project_ids_select(user_id)`（`UNION` 兩半，`performance-design.md` §二之一）與公開 `visible_project_ids(db, *, user_id) -> List[int]`、`is_project_visible(db, *, project_id, user_id) -> bool`；兩者都只由 `_visible_project_ids_select` 組出 | 5 |
| 11 | `backend/services/hierarchy_facade.py` | `HierarchyNotFound`（`:78`）之後定義 `PROJECT_NOT_FOUND_DETAIL = "查不到專案"`、`SYSTEM_NOT_FOUND_DETAIL = "查不到系統"` 並加入 `__all__`；新增 `list_projects_by_ids`、`list_systems_unscoped`（第一行 `_authorize(principal, "view")`，docstring 寫明唯一合法呼叫端是 `MembershipFacade`，放在新的段落標題下、**不放進** `BR6.4` 的「判定支援型查詢」段，因為它們回傳 model 物件）；三個寫入方法改為 `project_visible: Callable[[int], bool]` 必填、keyword-only、無預設，內部順序照 `security-design.md` §二之二；`delete_system` 第 2 步直呼 `hierarchy_service.get_project_of_system`；`delete_project`／`delete_system` 在 service 成功返回後各記一行 `logger.info("刪除專案 project_id=%s actor_user_id=%s", …)`（系統同形，`[PPD1]`=A，使用 `:47` 的既有 logger）。兩個常數在 Step 5 先加（service 層要 import） | 5、7 |
| 12 | `backend/services/membership_facade.py` | 從 `hierarchy_facade` 匯入 `PROJECT_NOT_FOUND_DETAIL`；新增 `list_visible_projects(principal)`、`list_visible_systems(principal, *, project_id)`、`project_visibility(principal) -> Callable[[int], bool]`。`list_visible_systems` 的順序：`HierarchyFacade.project_exists`（`HierarchyForbidden` **原樣上拋**）→ 不存在 `MembershipNotFound(PROJECT_NOT_FOUND_DETAIL)` → `is_project_visible` 為假同例外同訊息 → `list_systems_unscoped`。**不經** `_assert_project_exists`（`BR87.2`） | 7 |
| 13 | `backend/tests/helpers.py` | 新增 `ALWAYS_VISIBLE = lambda _pid: True`（附 docstring：只供「驗擁有者檢查等其他行為」的既有測試補參數用；靜態鎖第 3 條禁止非測試程式傳此形狀） | 7 |
| 14 | `backend/tests/test_hierarchy_service.py` | 11 處 facade 寫入呼叫補 `project_visible=ALWAYS_VISIBLE`（`:219`、`:231`、`:233`、`:323`、`:331`、`:346`、`:351`、`:359`、`:374`、`:387`、`:391`）；`:77` 是 `hierarchy_service.create_system`（service 層），不改。**斷言不動** | 7 |
| 15 | `backend/tests/test_work_orchestrator_store.py` | `:198`、`:199` 補參數（`U12` 的測試檔）。斷言不動 | 7 |
| 16 | `backend/tests/test_requirement_field_facade.py` | `:87` 補參數（`U20` 的測試檔）。斷言不動 | 7 |
| 17 | `backend/tests/test_mcp_bridge_e2e.py` | `:61` 補參數（`U21` 的測試檔）。斷言不動 | 7 |
| 18 | `backend/services/hierarchy_router.py` | `list_projects`／`list_systems` handler 改委派 `membership_facade.MembershipFacade(db).list_visible_*`，docstring 改寫（`list_projects` 的「被分享或以成員身分取得的存取在本輪看不到任何東西」與 `list_systems` 的「專案不屬請求者時回 404」皆為假）；三支寫入 handler 傳 `project_visible=membership_facade.MembershipFacade(db).project_visibility(principal)`（principal 先 `mint_principal` 一次存入區域變數）。路徑、`response_model`、狀態碼、`responses=` 宣告**一律不動**（`BR87.4`） | 9 |
| 19 | `openapi.json` | 重 dump（只有兩支 operation 的 `description` 漂移） | 9 |
| 20 | `backend/scripts/backfill_project_members.py` | 只改檔頭 `:18-21` 那一句（`functional-spec.md` §八之一 第 5 項的改寫文字），不改行為 | 14 |
| 21 | `DEPLOY.md` | 見 Step 14 | 14 |

**跨單元測試檔**：#14–#17 共 **15 處**呼叫只補一個關鍵字參數 `project_visible=ALWAYS_VISIBLE`，涉及 `U7`、`U12`、`U20`、`U21` 四個已交付單元的測試檔；任何斷言、fixture、案例名稱都不動。以 `grep -rn "\.create_system(\|\.delete_project(\|\.delete_system(" backend` 於本計畫撰寫時實查：測試 15 處（`test_hierarchy_service.py` 的 12 次命中減 `:77` 的 service 呼叫）、非測試僅 `hierarchy_router.py` 3 處（`:243`、`:267`、`:287`）。

### 一之二、前端

**新檔**（位置沿用 `U24`：非視覺模組在 `src/<領域>/`、頁面在 `src/pages/`、元件在 `src/components/<領域>/`）

| # | 路徑 | 內容 |
|---|---|---|
| 22 | `frontend/src/projects/fanoutQueue.ts` | `FANOUT_CONCURRENCY = 4`（唯一定義處）、`createFanoutQueue(limit)`、`FanoutCancelled`；FIFO、`cancel()` 後未發出者以 `FanoutCancelled` 拒絕；無 React 依賴、**無 `console.`** |
| 23 | `frontend/src/projects/projectsApi.ts` | 純抓取：`listProjects`、`listSystems`、`createProject`、`createSystem`、`listDiagramChanges`；型別取自 `src/types/api.d.ts`；`apiUrl()` ＋ 手寫 `Authorization` ＋ `res.ok` ＋ `data.detail`（`team.md` Code Style） |
| 24 | `frontend/src/projects/requirementsApi.ts` | 純抓取：`readFields`、`writeField`（空值 `PUT` 不帶 `on_behalf_of`，`BR84.6`） |
| 25 | `frontend/src/projects/objectCreateAction.ts` | `BR82.1` 的唯一建立寫入點：`objectCreateAction(kind, name, parentProjectId?)`；去頭尾空白後為空即擋；409／403／其他三類錯誤分類（`BR82.2`）；單次動作恰發一次、不重試（`BR82.3`） |
| 26 | `frontend/src/pages/ProjectsListPage.tsx` | 清單頁四態（`BR81.2`／`BR81.3`）、列的子狀態（Map 缺鍵＝載入中、`BR81.4`）、扇出佇列（`PPN-01`–`PPN-04`）、`LiveRegion`；頁內子元件 `ProjectListSkeleton`／`ProjectListEmpty`／`ProjectListError`／`ProjectListRow` |
| 27 | `frontend/src/pages/ProjectCreatePage.tsx` | 建立表單；成功導向 `/projects/<id>?tab=overview`（`BR82.5`） |
| 28 | `frontend/src/pages/ProjectDetailPage.tsx` | 持有唯一一份 `fieldsBySystem`（`BR85.1`）；詳情頁扇出（端點 5 全部先於端點 7，`PPN-02`）；`not-found`（`BR83.4`）；頁內子元件 `ProjectDetailHeader`（只有 `[成員]`，`BR83.3`）、`ProjectNotFound` |
| 29 | `frontend/src/components/projects/ProjectTabs.tsx` | tablist／tab／tabpanel、方向鍵與 Home／End、`?tab=` 以 `replace` 更新（`BR83.1`、`BR83.2`、`NFR11.102`） |
| 30 | `frontend/src/components/projects/OverviewTab.tsx` | 計數清單（系統 N、架構圖「尚無法取得」`BR86.1`、未填 Σ `BR85.2`）、`PendingRequirements` 子元件、`K4` 隱藏（`BR85.5`） |
| 31 | `frontend/src/components/projects/RecentChanges.tsx` | 逐系統結果合併排序取 5（`BR86.2` 排序與 null 處理）；標示逐字「只含經大腦、已歸屬系統、且為你自己擁有之圖的變更」、空態逐字「沒有符合條件的變更紀錄」、部分失敗「部分變更無法取得」（functional-design R-02） |
| 32 | `frontend/src/components/projects/RequirementsTab.tsx` | 系統選擇、`fieldset`／`legend`、`drafts`／`fieldErrors`／`savedStale`、`[儲存]` 逐欄 `PUT` 後呼叫 `onSaved`、`[重新整理]`（`BR85.6`）、唯讀說明（`BR84.7`）、`RequirementsEmpty` 子元件（`BR84.1`） |
| 33 | `frontend/src/components/projects/RequirementField.tsx` | 標籤、輸入（無 `K4 edit` 時 `readOnly`）、「未填」「未儲存」「已儲存、重新整理失敗」文字經 `aria-describedby` 關聯；更新者三值（`BR84.4`，標題以 `updated_on_behalf_of` 對回應 `groups[].group_key` 比對，比對不到降級「由大腦」） |
| 34 | `frontend/src/components/projects/SystemCreateAction.tsx` | 兩處渲染（總覽計數旁、需求籤空狀態）；渲染條件 `ProjectOut.owner_user_id === 目前使用者 id && can('K2','edit')`（`BR82.4`）；成功後呼叫 `onCreated()` 由頁面重讀系統清單 |
| 35 | `frontend/src/components/projects/MemorySummaryTab.tsx` | 固定說明「專案記憶的彙整尚未提供」＋ 唯讀說明，不發請求（`BR86.3`） |
| 36 | `frontend/tests/e2e/project-pages.spec.ts` | Playwright e2e，全部 `page.route()` 攔截（形狀沿用 `member-pages.spec.ts` 的 `setupApp`），每個 `test()` 前有 `@purpose`／`@given`／`@step`／`@pass`／`@story`／`@ui`／`@api` 規格註解 |

**改檔**

| # | 路徑 | 改什麼 | 步驟 |
|---|---|---|---|
| 37 | `frontend/src/App.tsx` | 新增三條路由：`/projects`（`CapabilityRoute storyId="K2" action="view"`）、`/projects/new`（`K2` `edit`）、`/projects/:projectId`（`K2` `view`），與既有 `/projects/:projectId/members` 系列共存 | 11 |
| 38 | `frontend/src/components/Sidebar.tsx` | 第一層新增「專案」`NavLink`（`data-testid="sidebar-projects-link"`，`can('K2','view')` 時渲染，沿用 `linkClass`）；位置在「我的記憶」之前（`U14` 的「入口」未落地，線框 §14） | 11 |
| 39 | `frontend/src/types/api.d.ts` | `npm run gen:types` 重產（只因 `openapi.json` 的 description 變動） | 9 |

### 一之三、紀錄

| # | 路徑 | 內容 |
|---|---|---|
| 40 | `construction/project-pages-ui/code-generation/{code-summary.md, traceability.json, source-manifest.json}` | Step 14 |

**不改的檔**（`NFR8.100`、`PPN-21`–`PPN-23`、使用者裁決「不動啟動路徑」）：`backend/database.py`、`backend/requirements.txt`、`frontend/package.json`、`package-lock.json`、`.github/workflows/*`、`deploy/*`（含 compose、`render-env.sh`、`.env.example`）、`backend/.env.example`、`frontend/.env.example`、`frontend/nginx.conf`、`LOCAL-DEV.md`、`schema.sql`（`project_members` 不在其中）。

**零新環境變數、零 secret、零對外埠、零新服務、零新依賴；唯一 DDL 是一個索引。**

## 二、帶入項處置表（`../carried-review-items.md` 全部 20 項）

類型：「程式」＝改程式並配測試；「文件」＝`DEPLOY.md`／腳本檔頭；「紀錄」＝只在 code-summary 記明落點、更正或理由。

| # | 站別 | ID | 處置 | 類型 | 步驟 |
|---|---|---|---|---|---|
| 1 | functional-design | R-01（Major，使用者裁決） | 三條寫入路徑加可見性守門（`security-design.md` §二）：注入的 `project_visible` 必填無預設、順序為 `K2 edit` → 守門 → 擁有者檢查 → service（含 409）；被移出的擁有者回 404 且四表列數不變；零成員列只認擁有者。`TestClient` allow／deny 雙向（`test_project_write_guard.py` 的 (a)–(g)、(e')），突變 `G1`–`G9`。code-summary 寫明 `OPEN-PP23-10` **於本單元關閉**、`functional-spec.md` 的「無自然承接站」一句以裁決為準；兩條級聯（刪專案刪全部成員列、刪系統刪需求欄位值）在核可關卡重新揭露（§七 第 1 項） | 程式／紀錄 | 7、8、10、15 |
| 2 | functional-design | R-02 | `RecentChanges` 標示逐字「只含經大腦、已歸屬系統、且為你自己擁有之圖的變更」、空態逐字「沒有符合條件的變更紀錄」；e2e 斷言兩句；traceability 的 `BR86.2` note 補「未歸屬系統的圖（`OPEN-H11`）查不到」 | 程式 | 11、12、15 |
| 3 | functional-design | R-03 | 身分 ③ 構造為「**另一專案的成員**」並對兩支端點斷言；突變 `M5`（拿掉 `list_projects_by_ids`／`list_systems_unscoped` 第一行 `K2`，含可見集合為空的缺 `K2` 使用者）與 `M6`（成員那一半漏寫與目標專案的關聯） | 程式 | 6、10 |
| 4 | functional-design | R-04 | 詳情頁佇列先入列全部端點 5（系統 id 遞增）、再入列全部端點 7；儲存後重讀、`[重新整理]`、端點 1、進頁那一次端點 2、建立後的系統清單重讀**不經佇列**（`performance-design.md` §一之一）。e2e 斷言順序（`PPN-02`） | 程式 | 11、12 |
| 5 | functional-design | R-05 | 設計檔不回改；code-summary 記明「`functional-spec.md` §十之一 第一個空表為格式缺陷，以散文後的單一表格為準」 | 紀錄 | 15 |
| 6 | nfr-requirements | R-01（Major，使用者裁決） | 兩個無 id 常數定義於 `hierarchy_facade.py`；六處 f-string 改用常數；逐路徑例外型別與訊息照 `security-design.md` §一之二（`delete_system` 的「不存在」與「不可見」皆用系統句）。測試以 `response.content` 逐位元比較「從未存在的 id」與「請求者不可見的既有 id」，四條路徑（系統清單、建立系統、刪除專案、刪除系統）各一案 | 程式 | 5、7、10 |
| 7 | nfr-requirements | R-02（Major，使用者裁決） | 索引寫進 `schema_rbac.sql` `J)` 區塊、`models.py`、`EXPECTED_INDEXES`、`BLOCK_SENTINELS["J"]`；`DEPLOY.md` 2.2.9 改計數（7 → 9，並更正 7 本身已與腳本的 8 不符）、新增部署後重跑遷移腳本步驟與驗證指令；**不動** `database.py`，故 `LOCAL-DEV.md` 同步不觸發 | 程式／文件 | 3、4、14 |
| 8 | nfr-requirements | R-03 | `project_visible` 必填無預設 keyword-only（漏傳即 `TypeError`，fail-closed）；靜態鎖第 2 條斷言 `kw_defaults` 對應項為 `None`、第 3 條斷言每個非 service 層呼叫都帶 `project_visible=<…>.project_visibility(...)`；`delete_system` 為「載入系統取得 `project_id` → 守門 → 擁有者檢查」 | 程式 | 7、8 |
| 9 | nfr-requirements | R-04 | 守門早於擁有者檢查與一切 409：(e) 被移出的擁有者刪除「底下仍有系統」的專案得 404 非 409；突變 `G3` | 程式 | 7、10 |
| 10 | nfr-requirements | R-05 | 已由 `performance-design.md` §三 改寫（4 是經驗值、只限單人突發、不保護連線池；耗盡條件約 3 位使用者同時進頁）。不改程式；code-summary 照錄並於核可關卡揭露 | 紀錄 | 15 |
| 11 | nfr-requirements | R-06 | code-summary 的殘留與 ADR-0006 Audit 格寫明「成功的級聯刪除無筆數紀錄」；`[PPD1]`=A 補上刪除者 `actor_user_id`（`assertLogs` ＋ 突變）；並更正上游「刪除不記稽核」為「有 INFO log、原本無 actor」（`security-design.md` §五之一） | 程式／紀錄 | 7、10、15 |
| 12 | nfr-design | R-01（Major，使用者裁決：接受為殘留） | 不改 `U19`／`U20` 的程式與測試。code-summary 以**實讀後**的檔名、行號與回應改寫 `security-design.md` §八 殘留第 4 項：`membership_facade.py` 的 `list_members`（先 `_assert_project_exists` 回 404、再 `_require_project_role` 回 403）與 `requirement_field_facade.py` 的 `_authorize`（不存在 404、非成員 403），可探出專案／系統 id 是否存在（不洩漏內容）；Network exposure 格同步改寫為「本單元會回 404 的四條路徑（系統清單與三條寫入）不存在與不可見逐位元相同；上述兩處仍可區分」 | 紀錄 | 15 |
| 13 | nfr-design | R-02 | 靜態鎖加第 5 條：`backend/`（排除 `tests/`）內，`hierarchy_service` 的 `create_system`／`delete_project`／`delete_system` 不論 `Attribute`（`hierarchy_service.delete_project(...)`）或 `Name`（`from services.hierarchy_service import delete_project` 後裸呼叫）形式，只准出現在 `hierarchy_facade.py`。突變 `G8`（router 直呼模組屬性）、`G9`（`from … import` 後裸呼叫） | 程式 | 8 |
| 14 | nfr-design | R-03 | 補 (e')：被移出的擁有者刪除「底下仍有架構圖」的系統得 404 非 409（以 ORM 建一列 `user_diagrams` 指向該系統構造）；`G3` 對 `delete_project` 與 `delete_system` 各執行一次 | 程式 | 10 |
| 15 | nfr-design | R-04 | `schema_rbac.sql` 檔頭 J 區塊涵蓋說明（`:12-13`）與檔尾 J 驗證註解（`:1260-1281`）補 `ix_project_members_user_id` 的存在查詢與預期（1 列）。完成條件以 `grep -c` 報告 | 程式 | 3 |
| 16 | infrastructure-design | R-01（Major，使用者裁決） | `DEPLOY.md` 新段落的部署後步驟用容器內形式：先列前置的 2.2.7 階層遷移；遷移腳本 `docker compose -f deploy/docker-compose.deploy.yml exec backend python scripts/run_meta_schema_migration.py`（沿用容器的 `DATABASE_URL`；映像 `WORKDIR /app`、`COPY . .`、`backend/.dockerignore` 不排除 `scripts/`——撰寫時實讀）；驗證 `docker exec -i <db-container> psql -U postgres -d cloud360 -c "SELECT indexname FROM pg_indexes WHERE tablename='project_members' AND indexname='ix_project_members_user_id';"`（形式與 `DEPLOY.md:213-214` 相同）。**不發布 5432**。Step 1 再實讀一次服務名與工作目錄後定稿 | 文件 | 1、14 |
| 17 | infrastructure-design | R-02 | `test_M3b` 以 `ast.literal_eval` 取 `EXPECTED_INDEXES` 的**值**比對三元組，不做整檔 `assertIn`；突變只刪 `EXPECTED_INDEXES` 那一列、保留 `BLOCK_SENTINELS["J"]` → 必須紅 | 程式 | 4 |
| 18 | infrastructure-design | R-03 | `cicd-pipeline.md` §四 的 ✅ 改讀為「訊號（不擋合併）」——`ut` 無必要狀態檢查。設計檔不回改，寫進 code-summary 的設計文字回補表 | 紀錄 | 15 |
| 19 | infrastructure-design | R-04 | 第 5 列後果改述為「`create_all` 會建表，真實後果是缺 COMMENT 與需先跑 2.2.7」；第 6 列（`U20` → `U23` → `U21`）標為 bolt-plan 的排序性質、已非現況（`763a45a` 的 `U21` 已早於本單元）。寫進 code-summary 的回補表 | 紀錄 | 15 |
| 20 | infrastructure-design | R-05 | `DEPLOY.md` 新段落的第一步即 2.2.7 前置條件；(b) 路徑（`create_all` 建表）註明缺 COMMENT（引用 `OPEN-ID19-1`）且仍須跑一次遷移腳本 | 文件 | 14 |

**計數**：20 項，**0 項拒絕**。類型欄含「程式」或「文件」者 15 項（#1、#2、#3、#4、#6、#7、#8、#9、#11、#13、#14、#15、#16、#17、#20）；只做紀錄者 5 項（#5、#10、#12、#18、#19）；15 ＋ 5 ＝ 20。步驟欄指向 §三 的 Step 編號。

**Major 項的突變驗證**：#1（`G1`–`G9`）、#6（§五 的訊息比較突變 `N1`–`N3`）、#7（`D1`–`D3`）各配「套用 → 紅 → 還原 → 綠」；#12 為接受的殘留，無程式變更。

## 三、步驟（`test-after`：逐層先實作、再寫並執行該層測試）

後端指令一律在 `backend/` 目錄執行，前端指令在 `frontend/` 目錄執行，**只跑本單元的模組或被本單元改到的既有模組**，不跑全套。

### Step 1 — 結構骨架與事實複驗（plan_profile：Project structure and production configuration skeleton）

- [x] 建 `frontend/src/projects/` 與 `frontend/src/components/projects/` 兩個目錄（以第一個檔的建立帶出，不放空檔）。
- [x] **唯讀複驗**（寫進 code-summary「Step 1 複驗紀錄」）：
  - `deploy/docker-compose.deploy.yml` 的服務鍵 `backend`（`:79`）、`db`（`:35`），無 `container_name`、無 `${VAR:?}` 必填插值（撰寫時 `grep -c ":?"` 為 0，故 `deploy/.env` 已被部署清理時 `compose exec` 只會對空白變數發警告，不會失敗）；
  - `backend/Dockerfile` 的 `WORKDIR /app`（`:14`）與 `COPY . .`（`:19`）、`backend/.dockerignore` 不排除 `scripts/` → 容器內 `/app/scripts/run_meta_schema_migration.py` 存在；
  - `DEPLOY.md` 2.2.7（`:330`）、2.2.9（`:583`、`:660`、`:674`、`:687-693`）、`:867` 的現行文字；`:213-214` 的 `docker exec` 形式；
  - `schema_rbac.sql` `J)` 區塊的 `project_members` DDL 結束行與 `:608-615` 註解；`run_meta_schema_migration.py` 的 `EXPECTED_INDEXES` 實為 8 筆。
- [x] 任一事實與本計畫不符 → 停下，把差異交 conductor，不自行改計畫。

### Step 2 — 測試執行器就緒（plan_profile：Verify the existing test runner/configuration）

- [x] 後端（本單元會改到或依賴的既有模組，作為基準綠燈）：
  `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_membership_data tests.test_hierarchy_service tests.test_membership_facade tests.test_membership_endpoints -v`
- [x] 前端：`npm run lint`、`npm run check:types`（基準）；`npx playwright test tests/e2e/project-pages.spec.ts --list`（檔案尚不存在時應回報 0 個測試而非設定錯誤）。
- [x] 把以上確切指令與基準結果（含既有的 `0 errors, N warnings`）記入 code-summary。基準若非綠燈 → 停下回報，不在本單元修。

### Step 3 — Data model / database behavior：實作

- [x] `schema_rbac.sql`：§一之一 #5 全部四處（`CREATE INDEX` 單行、無 schema 前綴；`:608-615` 改寫為「`user_id` 側由 `U23` 建立：條件 ① 已成立（專案清單改讀成員列，`[PP1]`=A）；條件 ② 仍未決，與本索引無關」；檔頭 J 說明；檔尾驗證註解 `-- 應回 1 列`）。
- [x] `models.py`：§一之一 #6。
- [x] `run_meta_schema_migration.py`：§一之一 #7。
- **落實**：帶入項 #7、#15。
- **驗證**：`grep -c "ix_project_members_user_id"` 對 `schema_rbac.sql`、`backend/models.py`、`backend/scripts/run_meta_schema_migration.py` 各 ≥ 1（`schema_rbac.sql` 預期 ≥ 3：DDL、檔頭、檔尾）。

### Step 4 — Data model / database behavior：測試

- [x] `test_membership_data.py`：§一之一 #8（`test_M3` docstring ＋ 兩個點名 `assertIn`；新增 `test_M3b`）。
- **突變**：`D1` 只從 `EXPECTED_INDEXES` 刪該列、保留 `BLOCK_SENTINELS["J"]` → `test_M3b` 紅；`D2` DDL 寫成 `ON public.project_members` → `test_M3` 紅；`D3` 只拿掉 ORM 的 `Index` → `test_M3` 紅（集合不等與點名斷言皆紅）。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_membership_data -v`
- **限制（如實記載）**：SQLite 測試庫不驗 PostgreSQL 的 `CREATE INDEX` 語法與可重跑性；那由 CI 的 `memory-schema` job 對真實 PostgreSQL 連套兩次 `schema_rbac.sql` 並執行遷移腳本承擔（`cicd-pipeline.md` §一）。本機不跑該 job。

### Step 5 — Repository / data access：實作

- [x] `hierarchy_service.py`：新增 `list_projects_by_ids`；六處 f-string 改常數（§一之一 #9）。
- [x] `membership_service.py`：§一之一 #10。成員那一半 `select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)`；擁有者那一半 `select(Project.id).where(Project.owner_user_id == user_id, ~exists().where(ProjectMember.project_id == Project.id))`；`union` 兩者。**不得**改寫成以 `projects` 驅動的 `OR`（`performance-design.md` §二之一）。
- [x] `hierarchy_facade.py`：只先加兩個常數與 `__all__`（service 層 import 它們；方法改動在 Step 7）。
- **落實**：帶入項 #6（訊息面）、#3（謂詞形狀）。
- **驗證**：`grep -n "import.*membership" backend/services/hierarchy_facade.py backend/services/hierarchy_service.py` 為 0；`grep -c "NOT EXISTS\|project_members\|ProjectMember" backend/services/hierarchy_facade.py backend/services/hierarchy_service.py` 皆 0；`grep -c "def _visible_project_ids_select" backend/services/membership_service.py` 為 1。

### Step 6 — Repository / data access：測試

- [x] `test_project_visibility_queries.py` 的 `VisibilityPredicateTest`：對 `visible_project_ids` 與 `is_project_visible` 構造五身分（① 擁有者且有成員列、② 成員、③ **另一專案的成員**、④ 被移出的擁有者、⑤ 零成員列專案的擁有者），各斷言集合與布林值；另一案：使用者無任何成員列也非擁有者 → `[]`。共 7 案。構造方式見 `unit-test-instructions.md` §六。
- **突變**：`M1`（拿掉成員那一半）→ ② 紅；`M2`（拿掉「零成員列」條件）→ ④ 紅；`M3`（拿掉擁有者那一半）→ ⑤ 紅；`M6`（成員那一半在 `is_project_visible` 中漏掉與目標專案的關聯）→ ③ 紅。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_project_visibility_queries -v`

### Step 7 — Business logic：實作

- [x] `hierarchy_facade.py`：§一之一 #11 的其餘部分。三個寫入方法逐步順序：

  | 步 | `create_system` | `delete_project` | `delete_system` |
  |---|---|---|---|
  | 1 | `_authorize(principal, "edit")`（403） | 同左 | 同左 |
  | 2 | — | — | `project_id = hierarchy_service.get_project_of_system(self._db, system_id=…)`；不存在 → 404 系統句 |
  | 3 | `project_visible(project_id)` 為假 → `HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL)` | 同左 | 為假 → `HierarchyNotFound(SYSTEM_NOT_FOUND_DETAIL)` |
  | 4 | `assert_project_owned_by`（既有） | 同左 | `assert_system_owned_by`（既有） |
  | 5 | `hierarchy_service.create_system` | `hierarchy_service.delete_project`（409 在此）→ 成功後 actor log | `hierarchy_service.delete_system`（409）→ 成功後 actor log |

- [x] `membership_facade.py`：§一之一 #12。
- [x] `tests/helpers.py`：§一之一 #13。
- [x] 四支既有測試檔 15 處補參數：§一之一 #14–#17。
- **落實**：帶入項 #1、#6、#8、#9、#11（log 部分）。
- **驗證**：`grep -n "project_visible" backend/services/hierarchy_facade.py` 命中三個簽章與三處呼叫；`grep -rn "\.create_system(\|\.delete_project(\|\.delete_system(" backend/tests` 的每一筆 facade 呼叫都帶 `project_visible=`（逐筆列入 code-summary）。

### Step 8 — Business logic：測試

- [x] `test_project_visibility_static.py`（`ast.walk` 掃 `backend/` 全部 `.py`，排除 `tests/`；形狀沿用 `tests/test_mcp_bridge_static.py`）：
  1. `BR87.7`：屬性名 `list_projects_by_ids`／`list_systems_unscoped` 的 `ast.Call` 只出現在 `services/membership_facade.py` 的 `MembershipFacade` 類別內。
  2. `HierarchyFacade` 的 `create_system`／`delete_project`／`delete_system` 的 `FunctionDef`：`project_visible` 在 `kwonlyargs` 且 `kw_defaults` 對應項為 `None`。
  3. 對屬性名 `create_system`／`delete_project`／`delete_system` 的每一個呼叫，若接收者不是名為 `hierarchy_service` 的 `Name`，必須帶 `project_visible=` 關鍵字，且其值是對屬性 `project_visibility` 的 `ast.Call`（不得是 `Lambda`／`Name`／`Constant`）。
  4. `project_visibility` 的 `FunctionDef` 只出現在 `MembershipFacade` 類別內。
  5. （nfr-design R-02）`hierarchy_service` 的 `create_system`／`delete_project`／`delete_system`：`Attribute` 形式（接收者為 `hierarchy_service`）與 `Name` 形式（經 `from services.hierarchy_service import …`）的呼叫只准出現在 `services/hierarchy_facade.py`；同時斷言 `backend/` 非 `tests/` 內沒有任何 `ImportFrom` 從 `services.hierarchy_service` 匯入這三個名稱。
- [x] 既有測試回歸（含 15 處補參數的四支檔與 `T2b`）。
- **突變**：`BR87.7-M`（在 `hierarchy_router.py` 直呼 `list_systems_unscoped`）→ 第 1 條紅；`G4`（`project_visible` 預設 `None` 且為 `None` 時略過）→ 第 2 條紅；`G5`（router 改傳 `lambda _pid: True`）→ 第 3 條紅；`G8`（router 直呼 `hierarchy_service.delete_project`）→ 第 5 條紅；`G9`（`from services.hierarchy_service import delete_project` 後裸呼叫）→ 第 5 條紅；`G7`（`hierarchy_service` 內另寫一份成員查詢）→ Step 5 的 grep 非 0（靜態檢查，記入 code-summary）。
- **驗證**：
  `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_project_visibility_static -v`
  `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_hierarchy_service tests.test_work_orchestrator_store tests.test_requirement_field_facade tests.test_mcp_bridge_e2e tests.test_membership_facade -v`

### Step 9 — API / endpoint：實作

- [x] `hierarchy_router.py`：§一之一 #18。
- [x] 重 dump 與重產（順序不可換，`cicd-pipeline.md` §一之一）：`cd backend && python scripts/dump_openapi.py` → `cd frontend && npm run gen:types`；兩檔與 handler 改動同一個 commit。
- **落實**：`BR87.4`、帶入項 #1（router 端）。
- **驗證**：`cd backend && python scripts/dump_openapi.py --check`；`cd frontend && npm run check:types`；`git diff --stat openapi.json` 只有 description 行（逐行判讀寫入 code-summary：路徑、`response_model`、狀態碼、`responses` 不變）。

### Step 10 — API / endpoint：測試

- [x] `test_project_visibility_endpoints.py`（`TestClient(app)` ＋ `dependency_overrides`，樣板比照 `tests/test_membership_endpoints.py`）：
  - 五身分 × 兩端點（專案清單皆 200，斷言是否含目標；系統清單斷言狀態碼與內容），共 10 案；
  - 缺 `K2`（非 canonical role）：專案清單 403；**另一位可見集合為空的非 canonical 使用者**專案清單仍 403（`M5` 的必要構造）；系統清單對存在與不存在的 `project_id` 皆 403；
  - `PPN-13`：系統清單對「從未存在的 id（`max(id)+1000`）」與「③ 請求者不可見的既有 id」，`status_code` 相等且 `response.content` 逐位元相等。
- [x] `test_project_write_guard.py`：三條路徑 × (a)(b)(c)(d)(f) 共 15 案，加 (e)（僅 `delete_project`）1 案、(e') 1 案、(g) 三條路徑的逐位元比較 3 案（`delete_system` 為「不存在的系統」vs「被移出擁有者對既有系統」，兩者皆為系統句）、`[PPD1]` 成功刪除專案與系統各 1 案（`assertLogs("cloud360.hierarchy_facade", "INFO")` 含 `actor_user_id=<請求者 id>`，且不含專案名或系統名）。(b)／(e)／(e') 斷言 `projects`、`systems`、`project_members`、`system_requirement_fields` 四表列數前後相等。
- [x] `test_project_visibility_queries.py` 的 `ListingStatementCountTest`：`setUp` 以 `event.listen(engine, "before_cursor_execute", …)` 掛計數器、`tearDown` 以 `event.remove` 卸除；每案先暖身一次再歸零；專案清單 P＝1 與 P＝8、系統清單 S＝1 與 S＝8 的語句數各相等（`PPN-06`）。
- **突變**：見 §五 的 `M1`–`M6`、`G1`–`G3`、`G6`、`N1`–`N3`、`L1`、`Q1`–`Q3`。
- **驗證**：
  `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_project_visibility_endpoints tests.test_project_write_guard tests.test_project_visibility_queries -v`
  `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_hierarchy_service -v`（`T2b` 回歸）
  `python scripts/dump_openapi.py --check`

### Step 11 — Frontend behavior：實作

- [x] §一之二 #22–#35、#37、#38。資料抓取一律兩層形狀（`BR88.1`）：純抓取函式 → 呼叫端 `.then/.catch/.finally` 更新 state → `useEffect` 內 `cancelled` 旗標；loading 初始播報以 `useState` 初始值帶入，不在 effect body 同步 `setState`；state 更新一律回傳新 `Map`／`Set`。
- [x] 佇列：`ProjectsListPage` 在端點 1 完成後依專案 id 遞增入列；`ProjectDetailPage` 在端點 1、2 依序完成後先入列 S 個端點 5（具 `K4 view`）、再入列 S 個端點 7；effect cleanup 依序 `cancelled = true`、`queue.cancel()`；`tab` **不在** effect 依賴陣列。
- [x] `data-testid` 照 `frontend-components.md` §八 全表。
- **落實**：帶入項 #2、#4；`BR81`–`BR86`、`BR88`；`PPN-16`–`PPN-18`、`PPN-21`。
- **驗證**：`npm run lint`（0 errors；warnings 數不得高於 Step 2 基準）；`npm run build`（含 `tsc -b`）；`npm run check:types`。
- **grep 完成條件**（逐筆判讀寫入 code-summary）：本單元新增前端檔中 `owner_user_id` 只出現在 `SystemCreateAction` 的渲染條件（`PPN-16`）；`localStorage`／`sessionStorage`／`indexedDB` 為 0（`PPN-17`）；`console.` 只允許固定字串、`fanoutQueue.ts` 為 0（`PPN-18`）；`createProject(`／`createSystem(` 的呼叫只在 `objectCreateAction.ts`（`BR82.1`）；`FANOUT_CONCURRENCY` 定義恰 1 處。

### Step 12 — Frontend behavior：測試

- [x] `frontend/tests/e2e/project-pages.spec.ts`：`describe` 名稱 `U23 project pages`（**合併後不得改**，`cicd-pipeline.md` §一之二）；案例見 `unit-test-instructions.md` §三。
- **突變**：見 §五 的 `F1`–`F10`。
- **驗證**：`npx playwright test tests/e2e/project-pages.spec.ts`（前端需服務於 `BASE_URL`，見 `unit-test-instructions.md` §二）。

### Step 13 — Environment / build configuration（本單元零改動，只驗證）

- [x] repo 根目錄：`python3 scripts/validate_repo_contract.py`、`python3 scripts/validate_env_contract.py`。
- [x] `git diff --stat` 中 `deploy/`、`*.env.example`、`.github/workflows/`、`backend/requirements.txt`、`backend/database.py` 為零變更；`frontend/package.json` 的 `dependencies` 與 `devDependencies` 鍵集合前後相同（`NFR8.100`、`PPN-21`–`PPN-23`）。
- [x] 新檔路徑不含 `prod`／`production`／`secrets` path part。

### Step 14 — Documentation：`DEPLOY.md` 與腳本檔頭（schema ↔ deploy blocking 同步）

- [x] **2.2.9 表**（`:591` `project_members` 列）補「索引：`uq_project_members_project_user`、`ix_project_members_user_id`（`U23`）」。
- [x] **`:674`**：「7 個索引」改為「**9** 個索引」，並加一句：改前的 7 已與腳本不符（`EXPECTED_INDEXES` 實為 8 筆，`U8` 的 HNSW 索引加入時未同步），本次一併更正。
- [x] **2.2.9 新增小節「`U23` 起：部署後再跑一次遷移腳本（建 `ix_project_members_user_id`）」**，在 staging 主機可直接複製執行：
  1. 前置：2.2.7 的 `run_hierarchy_migration.py` 已跑過（未跑則依 2.2.7 先跑）；
  2. `docker compose -f deploy/docker-compose.deploy.yml exec backend python scripts/run_meta_schema_migration.py; echo "exit=$?"` → 必須為 0（容器自帶 `DATABASE_URL`；`deploy/.env` 已被部署清理時 compose 對空白變數只發警告；無 TTY 的環境加 `-T`）；
  3. 驗證：`docker exec -i <db-container> psql -U postgres -d cloud360 -c "SELECT indexname FROM pg_indexes WHERE tablename='project_members' AND indexname='ix_project_members_user_id';"` → 應回 **1 列**（`<db-container>` 取法同 `:213`；`POSTGRES_USER`／`POSTGRES_DB` 若非預設值，比照 `:214` 代換）；
  4. **不要**為此發布 5432，也**不要**改以重跑整支 `schema_rbac.sql` 取代第 2 步（`C) RBAC` 區塊的 `DELETE FROM role_permissions;`）；
  5. 遺漏時的後果：功能正常、專案清單的成員半邊不走索引，**無聲**；部署冒煙不碰 `/api/hierarchy/*`，沒有任何自動檢查會發現；
  6. 三種資料庫狀態：空 volume（initdb 自動建）、表尚不存在（`create_all` 連同索引建表，但缺 COMMENT——`OPEN-ID19-1`——仍須跑一次第 2 步）、表已存在無索引（只有第 2 步能建）；兩種合併順序下人工步驟相同；
  7. 回滾：程式回滾不需動索引；只有索引本身有問題時 `DROP INDEX IF EXISTS ix_project_members_user_id;`，之後重跑第 2 步可重建。
- [x] **`:867`**：「`hierarchy_facade.list_projects` 目前是 owner-scoped……既有的專案列表路徑不經本單元」改寫為「`U23` 落地後專案清單改讀成員列；擁有者只在零成員列時可見，故回填未跑時擁有者仍看得到自己的專案，但需求籤與成員頁會拒絕他」。
- [x] `backend/scripts/backfill_project_members.py` 檔頭 `:18-21` 同一句改寫（不改行為）。
- [x] **`LOCAL-DEV.md` 同步判定：不觸發**——本單元不改 `backend/database.py` 的 schema 補丁、`deploy/nginx.conf`／`frontend/nginx.conf`、任一 `.env.example` 或 `render-env.sh`（使用者裁決「不動啟動路徑」）。code-summary 記明判定依據。
- **完成條件**：`grep -c "ix_project_members_user_id"` 對 `schema_rbac.sql`、`backend/models.py`、`backend/scripts/run_meta_schema_migration.py`、`DEPLOY.md` 各 ≥ 1；`grep -n "7 個索引" DEPLOY.md` 為 0；`grep -n "owner-scoped" DEPLOY.md backend/scripts/backfill_project_members.py` 的殘留逐筆判讀（歷史敘述可留，現況敘述不可留）。
- **落實**：帶入項 #7、#16、#20。

### Step 15 — Traceability 與 code-summary

- [x] `code-summary.md`：Step 1 複驗紀錄、Step 2 基準；§二 全部 20 項的落點；突變結果（§五 全表逐列：改了什麼、哪一案紅、還原後綠）；設計文字回補表（`BR87.6`／`OPEN-PP23-10` 被 R-01 取代；`[PP3]` 的「零 schema 變更」被 `[PPN1]`=A 取代；`BR86.2` 文字由 R-02 取代；`security-design.md` §八 第 4 項依 nfr-design R-01 以實讀事實改寫；`cicd-pipeline.md` §四 ✅ 的意義、§三 第 5、6 列；`performance-requirements.md` §二之一 的「確認」改為經驗值；`functional-spec.md` §十之一 空表）；`OPEN-PP23-10` 關閉；ADR-0006 四面向（§六）；交給 build-and-test 的事項；§七 揭露清單。
- [x] `traceability.json`：11 條 AC ＋ 本單元的 `BRx.y` ＋ 繼承的 `NFR8.100`、`NFR11.100`–`.102`；每個 `OK` 指向一個存在的實作或測試檔。
- [x] `source-manifest.json`：§一 的全部應用程式路徑（含 `openapi.json`、`frontend/src/types/api.d.ts`、四支被補參數的既有測試檔）。
- [x] **全單元重跑**：`unit-test-instructions.md` §二「全單元」兩條指令與 `dump_openapi.py --check`、`npm run check:types`。

## 四、步驟 ↔ 故事追溯

| AC | 驗證 | 步驟 |
|---|---|---|
| `AC11.1.1`（擁有者在總覽看到建立系統動作） | e2e：擁有者且 `K2 edit` → `system-create-action` 存在；成員非擁有者 → 不存在 | 11、12 |
| `AC11.1.2`（無系統時需求籤為空狀態而非空選擇器） | e2e：剛建立的專案 → `requirements-empty` 存在、`requirements-system-select` 不在 DOM | 11、12 |
| `AC11.1.3`（建立系統後系統數 0 → 1） | e2e：建立後重讀系統清單、`project-count-systems` 為 1；pathname 不變（`NFR11.100`） | 11、12 |
| `AC11.2.1`（未填欄位有文字「未填」） | e2e：`requirements-unfilled-<g>-<k>` 文字存在且為該欄 `aria-describedby` 指向 | 11、12 |
| `AC11.2.2`（組與欄位取自回應） | e2e：stub 回應的 `title`／`label`／`x/y` 原樣出現；改 stub 即改畫面 | 11、12 |
| `AC11.2.3`（部分失敗保留輸入） | e2e：兩欄儲存、其一 `PUT` 失敗 → 失敗欄保留輸入並標「未儲存」；重讀失敗 → 成功欄保留並標「已儲存、重新整理失敗」、`[重新整理]` 出現（`BR85.6`） | 11、12 |
| `AC11.3.1`（總覽未填數＝需求籤未填文字數） | e2e：單一系統專案，兩處數字相等 | 11、12 |
| `AC11.3.2`（儲存後總覽反映新值） | e2e：儲存一欄後切到總覽為 N−1；切籤零請求（`PPN-05`） | 11、12 |
| `AC11.3.3`（全填時為 0 且無未填標示） | e2e：總覽顯示 0、需求籤「未填」節點數 0 | 11、12 |
| `AC12.1.3`（非成員看不到專案） | `TestClient`：③ 清單不含、系統清單 404；e2e：系統清單 404 → `project-not-found` | 5、6、9、10、12 |
| `AC12.6.3`（被邀請的成員看得到專案） | `TestClient`：② 清單含、系統清單 200 | 5、6、9、10 |
| （連帶）`AC12.6.2` 在本單元五條路徑上的伺服器側拒絕 | `TestClient`：④ 清單不含、系統清單 404；寫入守門 (b)／(e)／(e') 404 且資料不變 | 6、7、10 |

## 五、突變驗證彙整（每項：套用 → 確認紅 → 還原 → 確認綠，結果逐列寫入 code-summary 與 tcms-test-cases 的 `automation-test-plan.md`）

| 代號 | 突變 | 必須紅的案 | 來源 | 步驟 |
|---|---|---|---|---|
| `D1` | 只從 `EXPECTED_INDEXES` 刪該列、保留 `BLOCK_SENTINELS["J"]` | `test_M3b` | infra R-02 | 4 |
| `D2` | DDL 寫成 `ON public.project_members` | `test_M3` | logical-components §三 #1 | 4 |
| `D3` | 只拿掉 ORM 的 `Index` | `test_M3`（集合與點名） | `PPN-07` | 4 |
| `M1` | 拿掉成員那一半 | ②（service 層與端點） | `BR87.5` | 6、10 |
| `M2` | 拿掉「零成員列」條件 | ④ | `BR87.5` | 6、10 |
| `M3` | 拿掉擁有者那一半 | ⑤ | `BR87.5` | 6、10 |
| `M4` | 系統清單改經 `_assert_project_exists` | 缺 `K2` 案、既有 `T2b` | `BR87.5` | 10 |
| `M5` | 拿掉 `list_projects_by_ids` 或 `list_systems_unscoped` 第一行 `K2`（各一次） | 缺 `K2` 案（含可見集合為空者，專案清單須仍 403 而非 200 `[]`） | FD R-03 | 10 |
| `M6` | `is_project_visible` 的成員半邊漏掉與目標專案的關聯 | ③ 的系統清單得 200 | nfr-design §三 | 6、10 |
| `BR87.7-M` | `hierarchy_router.py` 直呼 `list_systems_unscoped` | 靜態鎖第 1 條 | `BR87.7` | 8 |
| `G1` | 拿掉守門 | (b)：201／204 且列數改變 | FD R-01 | 10 |
| `G2` | 守門移到 `_authorize` 之前（或在 router／`MembershipFacade` 先判） | (f)：得 404 | `PPN-14a` | 10 |
| `G3` | 守門移到 service 呼叫之後（`delete_project`、`delete_system` 各一次） | (e)、(e')：得 409 | NR R-04、ND R-03 | 10 |
| `G4` | `project_visible` 預設 `None` 且為 `None` 時略過 | 靜態鎖第 2 條 | NR R-03 | 8 |
| `G5` | router 改傳 `lambda _pid: True` | 靜態鎖第 3 條 | NR R-03 | 8 |
| `G6` | `delete_system` 的守門改拋專案句 | (g) 的刪除系統比較案 | `PPN-14c` | 10 |
| `G7` | `hierarchy_service` 內另寫一份成員查詢 | Step 5 的 grep 非 0 | `PPN-14b` | 8 |
| `G8` | router 直呼 `hierarchy_service.delete_project` | 靜態鎖第 5 條 | ND R-02 | 8 |
| `G9` | `from services.hierarchy_service import delete_project` 後裸呼叫 | 靜態鎖第 5 條 | ND R-02 | 8 |
| `N1` | 任一處改回 `f"查不到專案 {project_id}"` | 該路徑的逐位元比較案 | NR R-01 | 10 |
| `N2` | 系統清單的「不可見」改拋 `MembershipForbidden`（403） | 系統清單比較案 | NR R-01 | 10 |
| `N3` | 系統清單的「不存在」改用帶 id 的訊息 | 系統清單比較案 | NR R-01 | 10 |
| `L1` | 拿掉 `[PPD1]` 的 actor log（各方法一次） | `assertLogs` 案 | `[PPD1]`=A | 10 |
| `Q1` | `list_visible_projects` 改為對每個候選專案呼叫 `is_project_visible` | P＝1 與 P＝8 語句數不等 | `PPN-06` | 10 |
| `Q2` | `list_projects_by_ids` 改為逐 id `db.get` | 同上 | `PPN-06` | 10 |
| `Q3` | 系統清單逐系統 lazy load 子物件 | S＝1 與 S＝8 不等 | `PPN-06` | 10 |
| `F1` | `enqueue` 直接執行（等同全發） | `PPN-01` 在途最大值 6 | `PPN-01` | 12 |
| `F2` | 詳情頁兩段入列對調 | `PPN-02` 順序 | FD R-04 | 12 |
| `F3` | 清單 `slice(0, 4)` | `PPN-03` 第 5、6 列缺 | `PPN-03` | 12 |
| `F4` | 拿掉 cleanup 的 `cancel()` | `PPN-04`（3 秒內 > 4） | `PPN-04` | 12 |
| `F5` | 把 `tab` 放進 effect 依賴 | `PPN-05` 切籤有請求 | `PPN-05` | 12 |
| `F6` | 建立系統成功後 `navigate` | `NFR11.100` | `NFR11.100` | 12 |
| `F7` | 失敗欄位的草稿被重讀結果覆蓋 | `AC11.2.3` 案 | `BR84.5` | 12 |
| `F8` | 重讀失敗時清除成功欄位草稿 | `BR85.6` 案 | `BR85.6` | 12 |
| `F9` | `[儲存]` 改為不看 `can('K4','edit')` | `BR84.7` deny 案 | `BR84.7` | 12 |
| `F10` | 更新者標題改取欄位所屬組的 legend | `BR84.4` 案 | `BR84.4` | 12 |

共 **36** 道（`D` 3、`M` 6、`BR87.7-M` 1、`G` 9、`N` 3、`L` 1、`Q` 3、`F` 10）。

## 六、blocking 同步義務與 ADR-0006

### 六之一、`project.md` 三條規則的判定

| 規則 | 判定 | 落點 |
|---|---|---|
| schema ↔ deploy 同步（`schema_rbac.sql` ＋ `DEPLOY.md`，**blocking**） | **觸發**（索引變更） | Step 3（`schema_rbac.sql` 四處）、Step 14（`DEPLOY.md` 四處）；未完成不得標示本站完成 |
| `LOCAL-DEV.md` 同步 | **不觸發**：不改 `database.py` 的 schema 補丁、nginx 設定、`.env.example`、`render-env.sh` | Step 13 以 `git diff --stat` 證明 |
| env contract（三環境分離） | **不觸發**：零新變數 | Step 13 跑 `validate_env_contract.py` |

### 六之二、ADR-0006 四面向（逐格對照 `infrastructure-specification.md` §五）

| 面向 | 上游判定 | 本計畫判定 | 落點 |
|---|---|---|---|
| IAM | 適用（擴充） | **相同** | 列舉放寬（`BR87`）、寫入守門（`PPN-14`–`14c`）、固定訊息（`PPN-13`）、靜態鎖五條；`K2` 判定仍只在 `HierarchyFacade` 一份 |
| Encryption | 相同（落點 `U21`） | **相同** | 零新傳輸、零新持久資料；草稿不落地（`PPN-17`） |
| Network exposure | 相同（落點 `U21`） | **相同**，但措辭依 nfr-design R-01 改寫：本單元會回 404 的四條路徑「不存在 vs 不可見」逐位元相同；`U19` 成員清單與 `U20` 需求欄位端點仍可區分（使用者已接受為殘留） | 零新端點、零新埠 |
| Audit logging | 適用（擴充，`[PPD1]`=A） | **相同** | 成功刪除記 `actor_user_id`；連帶刪除筆數不記（殘留） |

**PBT**：不適用（非 IaC generator、cost calculator、agent routing）；可見性兩分支以五身分與守門矩陣 example-based 窮舉。

## 七、核可關卡需揭露事項

1. **級聯刪除的重新揭露**（functional-design R-01 要求）：刪除專案會經 `ON DELETE CASCADE` 刪除**全部**成員列（含仍在的其他管理者）；刪除系統會刪除該系統**全部**需求欄位值（含其他成員所填）。本單元的守門使**被移出的建立者**不再能觸發；**仍是成員的擁有者**觸發它們是 `U7` 既有的合法行為，不改。成功刪除只多記刪除者，不記連帶筆數。
2. **`openapi.json` 會漂移**（只有兩支 operation 的 description）：`[PP1]` 選項 A 原文寫「不漂移」，使用者是在那句話下作答的；實際上必須重 dump 並重產 `api.d.ts`（Step 9）。
3. **既有 404 的 `detail` 文字改變**：`U7` 的建立系統、刪除、變更紀錄等路徑經 `assert_*_owned_by` 的 404，`detail` 由「查不到專案 12」變為「查不到專案」（狀態碼不變）。實查 `backend/tests`、`frontend/src` 對兩句訊息的斷言為 0；`U20` 自行包裝例外，不受影響。
4. **跨單元測試檔**：`U7`、`U12`、`U20`、`U21` 的四支測試檔共 15 處補一個關鍵字參數，斷言不動。
5. **部署後人工步驟**：staging 合併後必須在主機上跑一次遷移腳本並以 `psql` 驗證索引（Step 14 的容器內指令）。遺漏時**無聲**，沒有任何閘門或冒煙檢查會發現；`ut` 也沒有必要狀態檢查，CI 紅燈只是訊號。
6. **設計補強被採用**：`infrastructure-design` §四之一 建議的 `EXPECTED_INDEXES` 斷言以 `test_M3b` 落地（非上游定案，依 infra R-02 定形）。
7. **`DEPLOY.md` 的既存漂移**：「7 個索引」改前已與腳本的 8 筆不符，本次一併改為 9。
8. **由 conductor 重新提交使用者的開放項**：`OPEN-PP23-1`（架構圖計數無來源）、`OPEN-PP23-3`（記憶彙整無來源）、`OPEN-PP23-4`（`[設定]` 無目的地）、`OPEN-PP23-6` 第 ③ 項（大腦的對象目錄仍為擁有者範圍，被邀請的成員在專案頁看得到、大腦看不到）——是否另開 intent。
9. **殘留**：守門與寫入之間未加鎖；連帶刪除無筆數紀錄；`U19`／`U20` 的 403／404 可區分（已接受）；`DELETE /systems/{sid}` 對成員非擁有者回專案句（已論證非預言機）；程式回滾會讓寫入守門消失（`OPEN-PP23-10` 重開）；部署冒煙不碰 `/api/hierarchy/*`；連線池約 3 位使用者同時進系統數多的專案即可耗盡（4 是經驗值）；卸載時在途請求不中止（只丟棄結果）。
10. **e2e 全為攔截式**：與 `U24` 相同，不打真實後端；伺服器授權由 `TestClient` 承擔，前端與後端的形狀一致性由生成型別與兩道漂移閘門承擔。

## 八、方法論與 contract 基線的對應

`test-after` 的五個可測層：**Data model / database behavior**＝Step 3–4（索引、ORM、遷移腳本常數）；**Repository / data access**＝Step 5–6（可見性謂詞、`list_projects_by_ids`、訊息常數）；**Business logic**＝Step 7–8（facade 守門與委派、靜態鎖、既有測試回歸）；**API / endpoint**＝Step 9–10（router、`openapi.json`、`TestClient`、語句數）；**Frontend behavior**＝Step 11–12（三頁、佇列、e2e）。plan_profile 的 Project structure／runner 兩步為 Step 1–2；Environment/build configuration 為 Step 13（零改動、只驗證）；Documentation and traceability 為 Step 14–15。方法論未改。

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
