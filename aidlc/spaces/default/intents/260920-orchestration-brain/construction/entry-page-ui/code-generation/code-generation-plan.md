# Code Generation Plan — `U14 entry-page-ui`

> 撰寫時間：**未取得**——本計畫起草期間 plan-approval guard 擋下所有 shell 指令（含 `date -u`），依 `project.md` 不編造時間戳。
>
> 本計畫把四站設計（functional-design 修訂 1、nfr-requirements、nfr-design、infrastructure-design）落成程式、測試、部署步驟與文件，並**逐項處置四站審查帶下來的 26 項**（`../carried-review-items.md`：functional-design 8、nfr-requirements 7、nfr-design 7、infrastructure-design 4；以 `grep -c "^| R-"` 對該檔實數為 26，見 §二）。
>
> 使用者在各關卡的裁決優先於設計產出中對應的段落：`[EP1]`–`[EP6]`=A、`[EPN1]`=A、`[EPD1]`=A、`[EPI1]`=A、`[EPI2]`=A；functional-design `R-01`／`R-02`／`R-03`（2026-10-17T02:06:14Z）；nfr-requirements `R-01`／`R-02`（2026-10-17T03:58:59Z）；nfr-design `R-01`／`R-02`（2026-10-17T04:30:21Z）；infrastructure-design `R-01`–`R-04`（2026-10-17T04:59:34Z）。
>
> **契約增量 C-8 與三處可見性守門的 ADR 草案**為 `adr-0022-draft.md`（同目錄），**隨本計畫的 Plan Approval 一併核可**（`functional-spec.md` §二之一第 6 點的前置關卡）；核可後於 Step 1 原樣移入 `inception/decisions/0022-work-target-names-and-brain-read-visibility.md`。
>
> 方法論為 `test-after`（§九 的 Testing Contract）：每一層先實作，再寫並執行該層測試。**設計檔一律不回改**（`team.md ## Corrections`）；設計文字的更正與取代寫進 code-summary 的「設計文字回補表」。

## 一、交付範圍

本單元的六個可測層對應如下（`test-after` 的層名沿用 Testing Contract）：

| 層 | 本單元的落點 |
|---|---|
| Data model | `U2` 的 WS 契約模型 `WorkTargetPayload`（C-8 三欄）與兩份產生檔；**零 DDL** |
| Repository / data access | `U7` 的服務層純查詢 `describe_work_target`；`U19`／`U23` 的可見性閉包批次化 |
| Business logic | `U7` 的 `HierarchyFacade` 四個讀取方法的守門 |
| API / endpoint | `U13` 的大腦 WS 介面：組裝、`_names_for`、握手快照與三個扇出點、目錄、直接設定 |
| Frontend behavior | 入口頁、兩個子頁面的掛點、對話紀錄 store、連線 hook、e2e 兩層 |
| Environment / build | `deploy.yml` 步驟 6a（`[EPI1]`=A）、`eslint.config.js` 的 tests 區塊（併入 Step 11） |

### 一之一、後端應用程式（7 檔，其中 1 份為產生檔）

| # | 路徑 | 改什麼 | 步驟 |
|---|---|---|---|
| 1 | `backend/services/brain_ws_contract.py` | `WorkTargetPayload`（`:282-302`）新增 `projectName`／`systemName`／`diagramName`：`Optional[str] = Field(description=…)`，**無預設**（ADR D-1）；description 逐字寫明 null 的五種成因與「空字串原樣送出」 | 3 |
| 2 | `ws-contract.json`（repo 根目錄） | `cd backend && python scripts/dump_ws_contract.py` 重 dump（產生檔，不手改） | 3 |
| 3 | `backend/services/hierarchy_service.py` | 新增純查詢 `describe_work_target(db, *, owner_user_id, project_id=None, system_id=None, diagram_id=None) -> WorkTargetNames`（`NamedTuple`：`names` 三鍵、`project_ids: FrozenSet[int]`＝三元組中出現的相異所屬專案 id、`explicit: bool`）；專案層主鍵＋擁有者一條、系統層 `systems` join `projects` 一條、圖層 `user_diagrams` left join `systems` 一條（同時取圖所屬系統的 `project_id`）；查不到或不屬請求者該層 `None`，**不拋** | 5 |
| 4 | `backend/services/membership_facade.py` | `__init__` 新增私有 `self._visible_ids: Dict[int, FrozenSet[int]] = {}`；`project_visibility`（`:518-533`）回傳的閉包改為「該 user 首次呼叫時以 `membership_service.visible_project_ids` 取集合（一條 SQL）存入 `self._visible_ids`，之後一律集合成員判斷」（ADR D-5）；docstring 寫明暫存的存活範圍與「實例其他方法不讀暫存」 | 5 |
| 5 | `backend/services/hierarchy_facade.py` | 新增 `describe_work_target`（ADR D-2：① 授權 → ② 服務層 → ③ 明確指定路徑判 `found.project_ids` 全部可見，否則三名稱 null；只有圖的路徑不判可見性、不推導上層）；`list_projects`／`list_systems`／`resolve_work_target` 加 `project_visible`（必填、無預設、keyword-only；ADR D-3、D-4）；型別註記 `Callable[[int], bool]`；更新 `:238-254` 的註解段為「四個讀取路徑與三個寫入路徑」；**不 import** 任何成員關係符號 | 7 |
| 6 | `backend/services/brain_gateway.py` | `_HierarchyResolver.__init__`（`:565`）加 keyword-only 必填 `membership_facade_factory`，`resolve_work_target`（`:569-576`）以 `project_visible=self._membership_facade_factory(db).project_visibility(principal)` 傳入；`BrainGateway.__init__`（`:593-622`）加必填 `membership_facade_factory`；新增 `async _names_for(conn, triples)`（ADR D-7）；`_work_target_envelope(session, segment_id, names)`、`_snapshot_envelopes(session, items, names_by_segment)` 仍為同步；握手（`:820-858`）在第一個 `try` 之後、`ready` 之前呼叫 `_names_for`；`_set_target_confirmed`（`:1323`）、`_on_set_work_target`（`:1426`）、`_on_set_sharing_mode`（`:1445-1451`）扇出前 `await _names_for`；`_build_catalog`（`:1226-1243`）以 `vis = self.membership_facade_factory(db)` 在三個呼叫點傳 `project_visible=vis.project_visibility(principal)`；`build_brain_gateway(app, *, membership_facade_factory)`（`:1569`）把同一 factory 交給 `_HierarchyResolver` 與 `BrainGateway`；模組 docstring 的界線說明補「唯一的成員關係依賴經注入」 | 9 |
| 7 | `backend/main.py` | `:84` 改為 `build_brain_gateway(app, membership_facade_factory=membership_facade.MembershipFacade)`；`:82-83` 的註解補「漏傳時啟動失敗、import smoke 不觸發」 | 9 |

### 一之二、後端測試（新增 2、修改 7）

| # | 路徑 | 新增或修改 | 內容 | 步驟 |
|---|---|---|---|---|
| 8 | `backend/tests/test_ws_contract.py` | 修改 | `_SERVER_PAYLOAD_SAMPLES` 的 `WORK_TARGET`（`:69-74`）與 `_ADR0020_FIELDS` 的 C-4 最小樣本（`:320`）補三個名稱欄位（`None`）——**只補欄位、不改期望**；新增 `Adr0022NameFieldTest` 兩案：缺任一名稱欄位即 `ValidationError`、三欄為 `None` 與字串（含 `""`）皆可構造並讀回 | 4 |
| 9 | `backend/tests/test_describe_work_target.py` | **新增** | `DescribeWorkTargetTest`（facade 層、真實 SQLite，§四之一 (a)–(j) 共 12 案）、`VisibilityBatchTest`（3 案）、`StatementCountTest`（5 案，`before_cursor_execute` 計數、`tearDown` 以 `event.remove` 卸除，`EPN-23`）、`CatalogStatementCountTest`（以真實 `HierarchyFacade`／`MembershipFacade` 與 SQLite session 呼叫 `BrainGateway._build_catalog`，2 案） | 6、8、10 |
| 10 | `backend/tests/test_hierarchy_service.py` | 修改 | `:191`、`:199`、`:212`、`:214`、`:216` 五處補 `project_visible=ALWAYS_VISIBLE`（`tests/helpers.py` 既有）——**斷言不動**；新增 `BrainReadVisibilityTest` 6 案（`list_projects` 對被移出者不含、對零成員列建立者含；`list_systems` 對被移出者拋 `HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL)`；`resolve_work_target` 的 `[EPD1]`=A ①②③） | 8 |
| 11 | `backend/tests/test_project_visibility_static.py` | 修改 | 新增 `GUARDED_READS`；`S2`、`S3` 改檢 `WRITE_METHODS ∪ GUARDED_READS`；`S3` 加例外 `S3_EXCEPTIONS = {("services/session_store.py", "resolve_work_target")}`（精確比對）與「讀取方法呼叫點 ≥ 5」下限；新增 `test_S3b_exception_list_is_exact`（例外清單恰一筆且該呼叫點確實存在）；模組 docstring 的「五條」改寫為「五條，其中第 2、3 條擴及四個讀取方法」。`S1`、`S4`、`S5` **不改** | 8 |
| 12 | `backend/tests/brain_gateway_fakes.py` | 修改 | `FakeHierarchy` 新增 `describe_work_target`（可設 `names_by_triple`、`describe_raises`）；`list_projects`／`list_systems`／`resolve_work_target` 接受並**套用** `project_visible`（`invisible` 集合的專案：列舉排除、`list_systems` 拋 `HierarchyNotFound`、`resolve_work_target` 依 ADR D-4 兩分支）；新增 `FakeVisibility`（`invisible: set`、`factory(db)`、`project_visibility(principal)`）；`Harness` 的 `_HierarchyResolver(...)`（`:322`）與 `BrainGateway(...)`（`:343-355`）傳 `membership_facade_factory=self.visibility.factory` | 10 |
| 13 | `backend/tests/test_brain_gateway_startup.py` | 修改 | `:60` 的 `side_effect=lambda app: …` 改 `lambda app, **kw: …`，並斷言 `kw["membership_facade_factory"] is membership_facade.MembershipFacade`（新增的必填關鍵字使原 lambda `TypeError`——ADR Consequences 第 1 點的唯一例外）；新增一案：`build_brain_gateway(app)` 不帶 factory → `TypeError` | 10 |
| 14 | `backend/tests/test_brain_gateway_handshake.py` | 修改 | 新增 3 案：快照的 `work_target` 帶名稱；`describe_work_target` 拋一般例外時握手完成（非 1011）、名稱 null、恰一筆 `work_target_names_failed`；拋 `HierarchyForbidden` 時名稱 null 且 `assertNoLogs`。`:198` 的 `boom(*a, **k)` 不改 | 10 |
| 15 | `backend/tests/test_brain_gateway_turn.py` | 修改 | 新增 8 案（§四之一 gateway 層）。`:356` 的 `list_systems` 次數斷言與 `:578` 的逐欄比對**不改**（名稱不走 `list_systems`；兩側皆含名稱） | 10 |
| 16 | `backend/tests/test_brain_ws_deploy_probe.py` | **新增** | 以 `yaml.safe_load` 讀 `deploy.yml`，4 案鎖住步驟 6a 的位置、形狀與診斷輸出（§三 Step 13）；形狀比照 `test_mcp_bridge_deploy.py` 的 `DeployWorkflowTest` | 13 |

不改、只回歸：`test_brain_gateway_fanout.py`（`:283`、`:312`、`:315` 只比對 type 序列）、`test_brain_gateway_memory.py`、`test_brain_gateway_limits.py`（禁止清單**不得放寬**）、`test_dump_ws_contract.py`（`:187`、`:205` 只碰 `SetWorkTargetPayload`）、`test_mcp_bridge_deploy.py`（6a 不插在其釘住的兩步之間）、`U23` 的 `test_project_visibility_queries.py`／`test_project_visibility_endpoints.py`／`test_project_write_guard.py`、`test_membership_facade.py`。

### 一之三、前端（新增 23、修改 7、產生檔 1）

**新檔**（位置依 `frontend-components.md` §二 的拆分，`react-refresh/only-export-components`）

| # | 路徑 | 內容 |
|---|---|---|
| 17 | `frontend/src/brain/brainTranscript.ts` | context 物件、型別、`useBrainTranscript`、純 reducer（`append`／`updateTurn`／`interruptOpenTurns`／`reset`）、`TRANSCRIPT_MAX_PER_SEGMENT = 500`；對照為 `turnSegment: Record<turnId, SegmentId>`（`performance-design.md` §二之二） |
| 18 | `frontend/src/brain/BrainTranscriptContext.tsx` | 只匯出 `BrainTranscriptProvider`；`useEffect(() => subscribeAuthBoundary(() => dispatch({ type: 'reset' })), [subscribeAuthBoundary])`；**無 `BrainTranscriptKeyed`**（`security-design.md` §六之一） |
| 19 | `frontend/src/brain/brainProtocol.ts` | 純函式（無 React）：入站封包的寬鬆解析與窮盡分派表、`error.code` 的 `never` 窮盡、關閉碼分流、退避排程 `BASE = [1, 2, 4, 8, 15, 15]` 秒、`delayFor(n)`（**n 自 0 起算**，nfr-design `R-07`）、抖動 `0.8 + 0.2 × Math.random()`、子協定陣列（由 `WsSubprotocol` 型別取值）。**設計補強**：`logical-components.md` 未列此檔，抽出是為了讓 `useBrainConnection.ts` 只承載 effect 與 ref，純判斷集中一處（code-summary 記明） |
| 20 | `frontend/src/brain/brainSession.ts` | `BrainSessionContext`、型別、`useBrainSession`（`react-refresh` 拆檔，與 #33 成對） |
| 21 | `frontend/src/brain/useBrainConnection.ts` | 單一 effect 建連線；cleanup 依序清計時器 → `interruptOpenTurns` → `ws.close(1000)` → ref 歸 null；**不得**以 ref 去重；`hello` → 核對 `ready.protocolVersion`；4401／4400／4403 `terminal`；4403 → 至多一次 `refreshMe()`、**不 `navigate`**；`ready` 後快照逐項取代作業對象、工作項、`sharing_mode` |
| 22 | `frontend/src/brain/useWorkspaceTargetSync.ts` | `onPageReady(snapshot)`、`markOrigin(origin)`、`onDiagramDeleted(id)`；ref：`pendingInitialTarget`、對齊旗標、`pendingEchoes`（≤ 8、`ready` 時清空）、`openedBy`、頁面狀態鏡像；匯出純函式 `decideInitialAlignment(input) → 'open' \| 'hold' \| 'writeback' \| 'none'`；**無連線（含無 `K1`）時所有入口為 no-op**（nfr-design `R-05`） |
| 23 | `frontend/src/brain/useAssessmentTargetSync.ts` | 同上，評核頁版本；呼叫 #22 匯出的 `decideInitialAlignment` |
| 24 | `frontend/src/brain/testing/wsFrames.ts` | 每種伺服器訊息一個建構函式，**只收原始型別引數**；函式內先宣告 `const payload: components['schemas']['<Name>Payload'] = {…}` 再組 `WsEnvelope`；情境序列函式；`encodeFrame(env: WsEnvelope): string`；不 import 任何 vite 專屬 API；不被任何 app 程式匯入 |
| 25 | `frontend/src/utils/unsavedWork.ts` | `isCanvasDirty(saveStatus, xml)`（由 `WorkspacePage.tsx:118-121` **原樣抽出**）、`hasUnsavedAssessmentWork(uploadedXml, optimizeDraft)` |
| 26 | `frontend/src/pages/EntryPage.tsx` | 入口頁：頁首（標題 ＋ `MemoryShortcut`，`canSeeMemoryEntry`）、`BrainSession(page="entry")` 與其子元件；`data-testid="brain-entry-page"` |
| 27–39 | `frontend/src/components/brain/{BrainSession, ContextBar, SyncNotice, WorkItemDock, WorkItemList, ConversationView, EntryEmptyState, StreamingMessage, ClarifyCandidates, CostAnswerCard, ConnectionNotice, BrainInput, SubpageBrainPanel}.tsx`（13 檔） | 元件責任照 `frontend-components.md` §三；`ContextBar` 的 `data-state`（五態）與三個名稱節點的 `data-id`、`""` 顯示「（未命名）」、null 顯示「（無法顯示名稱）」；`ConversationView` 內含使用者原句與 `brain-transcript-truncated`；testid 照 `frontend-components.md` §八 全表；播報一律經既有 `LiveRegion` |

**改檔**

| # | 路徑 | 改什麼 | 步驟 |
|---|---|---|---|
| 40 | `frontend/src/context/auth-context.ts` | `AuthContextType` 加 `subscribeAuthBoundary: (listener: () => void) => () => void` | 11 |
| 41 | `frontend/src/context/AuthContext.tsx` | `useRef<Set<() => void>>` 保存訂閱者；`subscribeAuthBoundary` 為 `useCallback([])`；`notifyAuthBoundary()` 在 `logout()`（`:56`）與 `login()`（`:82`）**第一行**同步呼叫；`refreshMe()`／`applyUser()` 不通知 | 11 |
| 42 | `frontend/src/App.tsx` | 樹改為 `AuthProvider → BrainTranscriptProvider → BrowserRouter`（**不帶 `key`**）；`DefaultRedirect`（`:24-34`）在 `isPending` 之後、`canArch` 之前插入 `if (can('K1','view')) return <Layout><EntryPage /></Layout>;`；`*` 路由（`:234-241`）改為 `<Navigate to="/" replace />`（`BR91.3`） | 11 |
| 43 | `frontend/src/components/Sidebar.tsx` | 所有群組與獨立項之前新增 `K1 view` 時渲染的「入口」`NavLink`（`to="/"`、`end`、`data-testid="sidebar-entry-link"`、`aria-current`），獨立 `<nav>`；改寫 `:214-215` 的 `U23` 註解（入口已落地） | 11 |
| 44 | `frontend/src/pages/WorkspacePage.tsx` | `handleCanvasExit`（`:116-129`）改呼叫 `isCanvasDirty`（行為不變）；`fetchDiagrams`（`:152-164`）回傳 `{ ok, list }`（僅 `response.ok` 分支 `ok = true`）；bootstrap `finally`（`:296-298`）呼叫 `onPageReady({ openedDiagramId, openedBy: 'bootstrap', diagrams, listOk, unsaved })`；bootstrap（`:282`）與下拉（`:313`）處 `markOrigin`；刪除處理器（`:340` 起）呼叫 `onDiagramDeleted`；大腦掛點（`ContextBar` ＋ `SyncNotice` ＋ `SubpageBrainPanel`）只在 `can('K1','view')` 時掛載。**不夾帶重構**（`team.md`） | 11 |
| 45 | `frontend/src/pages/AssessmentPage.tsx` | 清單請求（`:246`）的 `.then` 與新增的 `.catch` 呼叫 `onPageReady({ diagrams, listOk })`；網址參數與下拉（`:1268`）處 `markOrigin`；把 `hasUnsavedAssessmentWork(uploadedXml, optimizeDraft)` 交給掛點；刪除（`:813`）呼叫 `onDiagramDeleted`；`K1` 掛載條件同上 | 11 |
| 46 | `frontend/eslint.config.js` | `:42-66` 的三條子協定規則抽成檔內常數 `WS_SUBPROTOCOL_RESTRICTIONS`，原區塊展開它；新增 `files: ['tests/**/*.ts']` 區塊，展開同一常數 ＋ 兩條訊框選擇器（`ObjectExpression:has(> Property[key.name='type']):has(> Property[key.name='payload'])` 與 `key.value` 版） | 11 |
| 47 | `frontend/src/types/ws-contract.d.ts` | `npm run gen:ws-types` 重產（產生檔） | 3 |

### 一之四、e2e（新增 2、修改 2）

| # | 路徑 | 內容 | 步驟 |
|---|---|---|---|
| 48 | `frontend/tests/e2e/entry-page.spec.ts` | `describe('U14 entry page')`：`routeWebSocket` 扮演伺服器、`page.route` 攔截 `/api/auth/me` 與子頁面既有 HTTP；訊框**只**由 #24 的建構器產生；49 案（`unit-test-instructions.md` §三之二） | 12 |
| 49 | `frontend/tests/e2e/entry-page-live.spec.ts` | `describe('U14 entry page live stack')`：真實測試 stack（`docker-compose.test.yml`），5 案 | 12 |
| 50 | `frontend/tests/e2e/regression.spec.ts` | `[EPI2]`=A ＋ infra `R-01`／`R-02`：13 個測試的落點斷言處置（§三 Step 12） | 12 |
| 51 | `frontend/tests/e2e/estimate-workspace.spec.ts` | `:17`（`login` helper）、`:35`：`toHaveURL(/\/(workspace\|cost)/)` 改 `not.toHaveURL(/\/login$/)` ＋ 正向錨點 | 12 |

### 一之五、部署、文件與紀錄

| # | 路徑 | 內容 | 步驟 |
|---|---|---|---|
| 52 | `.github/workflows/deploy.yml` | 新增步驟 6a「Verify the brain WS subprotocol survives the tunnel」於 `Verify sessions survive a Redis restart`（`:447`）之後、`Record this commit as the last-good deployment`（`:570`）之前；**不**加進 `rollback` job | 13 |
| 53 | `DEPLOY.md` | 新增一節「入口頁部署後實測」（`cicd-pipeline.md` §五之三 的建議，**採用**，非 blocking） | 14 |
| 54 | `inception/decisions/0022-work-target-names-and-brain-read-visibility.md` | 由 `adr-0022-draft.md` 原樣移入，只改 Status 行與標題的「草案」 | 1 |
| 55 | `construction/entry-page-ui/code-generation/{code-summary.md, traceability.json, source-manifest.json}` | Step 15 | 15 |

**不改的檔**（`NFR8.140`、`EPN-21`、`EPN-24`）：`deploy/*`（含 compose、`render-env.sh`、`.env.example`）、`backend/.env.example`、`frontend/.env.example`、`frontend/nginx.conf`、`deploy/cloudflared/config.yml`、`.github/workflows/ci.yml`、`ui-regression` workflow、`backend/requirements.txt`、`frontend/package.json` 與 `package-lock.json`、`backend/database.py`、`schema_rbac.sql`、`schema.sql`、`openapi.json`、`frontend/src/types/api.d.ts`、`LOCAL-DEV.md`。

**零 DDL、零新環境變數、零 secret、零對外埠、零新服務、零新依賴、零 HTTP 端點變更。**

**各層檔案數**：後端應用 7（含產生檔 1）；後端測試 9（新 2、改 7）；前端 31（新 23、改 7、產生檔 1）；e2e 4（新 2、改 2）；部署與文件 2；紀錄 4（ADR 1 ＋ 三份 Step 15 產出）。

## 二、帶入項處置表（`../carried-review-items.md` 全部 26 項）

類型：「程式」＝改程式並配測試；「文件」＝`DEPLOY.md`／ADR／註解；「紀錄」＝只在 code-summary 記明落點、更正或理由。突變代號見 §五。

| ID | 站別 | 處置 | 類型 | 步驟 |
|---|---|---|---|---|
| R-01 | functional-design（Major，裁決） | `describe_work_target` 套 `U23` 可見性（ADR D-2）；`U13` 不 import 成員層，以 factory 注入（ADR D-6）；被移出建立者雙向測試 (b)／(a)／(c)，另加 (b2) | 程式 | 5、7、8、9、10 |
| R-02 | functional-design（Major，裁決） | 首次對齊 (2) 加未儲存前置條件 → `hold`、不回寫、提示「開啟這張圖」並以 `window.confirm` 確認；晚到（重連後）＋未儲存畫布 e2e（E30）；突變 F8 | 程式 | 11、12 |
| R-03 | functional-design（Major，裁決） | 清除綁 `login()`／`logout()` 事件（`subscribeAuthBoundary`），不依賴 `User.id`、`BrowserRouter` 之上無 `key`；e2e「`/me` 失敗後換人登入」（E43）與不登出直接換人（E44）；靜態完成條件 `grep -c "key=" App.tsx BrainTranscriptContext.tsx` 為 0；突變 F5、F6、T4 | 程式 | 11、12 |
| R-04 | functional-design | 建構器只收原始型別、內部先宣告具名 payload 型別；spec 只呼叫匯出函式；lint 選擇器機械化 spec 內手寫訊框；突變 C3、T1 | 程式 | 11、12 |
| R-05 | functional-design | 回聲抑制改 `pendingEchoes`（≤ 8，`ready` 清空）；連選 X、Y e2e（E32）；突變 F11 | 程式 | 11、12 |
| R-06 | functional-design | `/workspace` 的 `fetchDiagrams` 回傳 `{ ok, list }`、`listOk` 為假兩向不同步並顯示說明（E36，F23）；空字串名稱顯示「（未命名）」（E23，F24） | 程式 | 11、12 |
| R-07 | functional-design | 以 ADR D-9 的論證取代「若 `U13` 先進 `ut`」分支；合併前三項檢查只在分支上執行（§七 第 3 點）；code-summary 記明 | 文件／紀錄 | 1、15 |
| R-08 | functional-design | `openedBy`：作業對象已有非 null 層級而 diagramId 為 null 時，bootstrap 開的圖不回寫；e2e（E35）；突變 F12 | 程式 | 11、12 |
| R-01 | nfr-requirements（Major，裁決） | `list_projects`／`list_systems` 加必填 `project_visible`（ADR D-3），`_build_catalog` 三呼叫點注入；被移出者說出前專案名 → `not_found_message`、0 則 `clarify`、0 次設定，對照可見同名專案唯一命中（雙向）；突變 H1、H2、G5 | 程式 | 7、8、9、10 |
| R-02 | nfr-requirements（Major，裁決） | 每組 ≤ 5、快照 ≤ 15（含 `_authorize`），`StatementCountTest` 鎖住、1 與 50 個專案語句數相同；突變 W5 | 程式 | 8、10 |
| R-03 | nfr-requirements | 注入物暴露 `project_visibility`、由 `main.py` 組裝；`S3` 例外清單一筆並同步註明（ADR D-6、D-8）；突變 G7 | 程式 | 8、9、10 |
| R-04 | nfr-requirements | StrictMode 的三項 code review 檢查（cleanup 必關、不以 ref 去重、無 effect 外建連線）於 code-summary 逐條回報；`vite dev` 手動案交 `tcms-test-cases` 分桶 | 紀錄 | 11、15 |
| R-05 | nfr-requirements | `EPN-03` 計數限定同一頁面實例；子頁面 4403 落點依 `security-design.md` §六之二（不導航、`refreshMe()` 至多一次、`K1` 掛載條件），三案 e2e（E9–E11）；突變 F7 | 程式 | 11、12 |
| R-06 | nfr-requirements | 抽出共用 `isCanvasDirty`；`/assessment` 晚到＋未存檔上傳 e2e（E31）；突變 F9 | 程式 | 11、12 |
| R-07 | nfr-requirements | 抖動維持 ×[0.8, 1.0]、理由改述為「降低同秒重連」；宣告支援 3 個分頁完整重試（`performance-design.md` §一之三），code-summary 記明 | 紀錄 | 15 |
| R-01 | nfr-design（Major，裁決） | 只有圖的三元組不推導上層、不判可見性、保留圖名；明確指定前專案者三名稱 null（ADR D-2）；`[EPD1]`=A 測試 ② 斷言三個名稱實際值 `{null, null, "<圖名>"}`（turn 層 ＋ facade (e2)）；突變 W3 | 程式 | 7、8、10 |
| R-02 | nfr-design（Major，裁決） | 可見性批次化（ADR D-5）：`list_projects` 固定 3 條、目錄可見性成本常數；`StatementCountTest`／`CatalogStatementCountTest` 鎖住；突變 V2；performance-design §三之三 的「2 ＋ 5N」由 code-summary 回補表更正為「3 ＋ 3N（可見性 ＋1 常數）」，**目錄總數仍隨 N 線性**的既有成本於 §七 第 1 點揭露 | 程式／紀錄 | 5、6、8、10、15 |
| R-03 | nfr-design | (b2)：被移出的建立者**另是第二專案的成員**；原 M2（`is_project_visible` 拿掉外層條件）因閉包改走集合而不再經過該函式，**改以等價突變 V1**（閉包忽略 pid、回「是否有任何可見專案」）承接，(b2) 必須紅；原 M2 仍由 `U23` 的 `test_project_visibility_queries` 承擔 | 程式／紀錄 | 6、8 |
| R-04 | nfr-design | `HierarchyForbidden` **不記 log**、其他例外記 `work_target_names_failed`；(f) 的期望改為「名稱 null ＋ `assertNoLogs`」；ADR-0006 audit 列同步（ADR Security 表）；突變 G2 | 程式 | 9、10 |
| R-05 | nfr-design | 無連線時同步 hook 全部入口 no-op；e2e：`K1` 撤銷後畫布不受影響且送出 `set_work_target` 0 則（E38）；突變 F22 | 程式 | 11、12 |
| R-06 | nfr-design | 三元組中出現的每個相異所屬專案皆判可見性（圖層以 left join 取所屬專案，不增語句數）；(i)：`project_id` 可見而系統改掛到不可見專案 → 三名稱 null；突變 W4 | 程式 | 5、7、8 |
| R-07 | nfr-design | 章節引用更正（`nfr-design-questions.md` 的「§五之二」實為 `security-design.md` §六之二）記入 code-summary 回補表；`delayFor(n)` 的 n 自 0 起算並於 `brainProtocol.ts` 註解寫明 | 程式／紀錄 | 11、15 |
| R-01 | infrastructure-design（Major，裁決） | `regression.spec.ts:55` 改 `toHaveURL(/\/login$/)` 並更新 `@step`／`@pass`／`@note`；合計 15 個既有測試；突變 X1（以 `page.route` 讓 `/api/auth/login` 對錯誤密碼回 200 ＋ token，該測試必須紅） | 程式 | 12 |
| R-02 | infrastructure-design（Major，裁決） | 依賴落點斷言的否定式檢查先加正向錨點：`:176` 前加 `sidebar-entry-link` 可見；其餘 12 個測試各列其後續正向斷言作為錨點（`unit-test-instructions.md` §三之三 對照表）；突變 X2 | 程式 | 12 |
| R-03 | infrastructure-design | 步驟 6a 失敗時印出最後一輪的 HTTP 狀態列、是否有 `sec-websocket-protocol` 一行（是／否）、curl 結束碼，三種失敗（403／101 無協定標頭／網路失敗）可區分；不輸出任何標頭值以外的內容、不含 token；`test_brain_ws_deploy_probe.py` 鎖住 | 程式 | 13 |
| R-04 | infrastructure-design | Kiwi 孤兒案例（「管理員登入後進入工作區」）由 `tcms-test-cases` 站人工停用並記入 `tcms-sync-report.md`；本站於 code-summary 交接 | 紀錄 | 15 |

**計數**：26 項，**0 項拒絕**。類型含「程式」者 22 項（functional-design 7、nfr-requirements 5、nfr-design 7、infrastructure-design 3）；只做紀錄或文件者 4 項（functional-design R-07、nfr-requirements R-04、R-07、infrastructure-design R-04）——22 ＋ 4 ＝ 26。各站 8 ＋ 7 ＋ 7 ＋ 4 ＝ 26。

## 三、步驟（`test-after`：逐層先實作、再寫並執行該層測試）

後端指令一律在 `backend/` 目錄執行，前端指令在 `frontend/` 目錄執行，**只跑本單元的模組或被本單元改到的既有模組**。

### Step 1 — 結構骨架、ADR 落檔與事實複驗（plan_profile：Project structure and production configuration skeleton）

- [x] 把 `adr-0022-draft.md` 原樣複製為 `inception/decisions/0022-work-target-names-and-brain-read-visibility.md`，只改 Status 行為「Accepted（2026-10-17 隨 `U14` Plan Approval 核可）」與標題去掉「（草案）」；草案檔保留不刪（可追溯）。
- [x] 建 `frontend/src/brain/`、`frontend/src/brain/testing/`、`frontend/src/components/brain/`（以第一個檔帶出，不放空檔）。
- [x] **唯讀複驗**（寫進 code-summary「Step 1 複驗紀錄」，逐項附行號）：`brain_gateway.py` 的 `:565`、`:593-622`、`:820-858`、`:869-907`、`:1226-1243`、`:1301-1324`、`:1403-1451`、`:1569-1598`；`hierarchy_facade.py:366-405`；`membership_facade.py:518-533`；`membership_service.py:337-379`；`brain_ws_contract.py:282-302`；`main.py:82-85`；`test_hierarchy_service.py:191`／`:199`／`:212-216`；`test_brain_gateway_startup.py:60`；`brain_gateway_fakes.py:322`、`:343-355`；`WorkspacePage.tsx:116-129`、`:152-164`、`:269-301`、`:304`、`:327`、`:340`、`:441`；`AssessmentPage.tsx:139-158`、`:187`、`:232-248`、`:560`、`:743`、`:813`、`:1268`；`App.tsx:24-34`、`:234-241`；`AuthContext.tsx:56`、`:82-93`；`LoginPage.tsx:107`；`eslint.config.js:42-66`；`Sidebar.tsx:214-215`；`deploy.yml:447`、`:570`、`:596-602`；`test_mcp_bridge_deploy.py:101-104`。
- [x] `grep -rn "\.list_projects(\|\.list_systems(\|\.resolve_work_target(\|\.describe_work_target(" backend` 的非測試命中恰為：`brain_gateway.py` 4 處（`:572`、`:1230`、`:1235`、`:1239`）、`session_store.py:387`、`hierarchy_facade.py` 對 service 層的呼叫——與本計畫一致才續行。
- [x] 任一事實與本計畫不符 → 停下，把差異交 conductor，不自行改計畫。
- **落實**：functional-design R-07（ADR D-9 落檔）。

### Step 2 — 測試執行器就緒（plan_profile：Verify the existing test runner/configuration）

- [x] 後端基準：`unit-test-instructions.md` §二 的「基準」指令（本單元會改到或依賴的 16 個既有模組）。
- [x] 前端基準：`npm run lint`（記下現有 `0 errors, N warnings`）、`npm run build`、`npm run check:ws-types`、`npx playwright test tests/e2e/entry-page.spec.ts tests/e2e/entry-page-live.spec.ts --list`（檔案尚不存在時應回報 0 個測試而非設定錯誤）。
- [x] `python scripts/dump_ws_contract.py --check`、`python scripts/dump_openapi.py --check` 基準綠。
- [x] 基準若非綠燈 → 停下回報，不在本單元修。

### Step 3 — Data model：實作（`U2` 契約，ADR D-1）

- [x] `brain_ws_contract.py`：§一之一 #1。
- [x] 產生順序（**不可換**，`cicd-pipeline.md` §一之一）：`cd backend && python scripts/dump_ws_contract.py` → `cd frontend && npm run gen:ws-types`；三檔（契約模組、`ws-contract.json`、`ws-contract.d.ts`）同一個 commit。
- **驗證**：`grep -c projectName ../ws-contract.json` ≥ 1；`git diff --stat` 中 `openapi.json`、`frontend/src/types/api.d.ts` **零變更**（出現即代表誤改 HTTP 層，回頭查）。

### Step 4 — Data model：測試

- [x] `test_ws_contract.py`：§一之二 #8。
- **突變**：C1（任一名稱欄位給 `= None` 預設）→ `Adr0022NameFieldTest` 的缺欄位案紅、`gen:ws-types` 產出的欄位變可選；C2（改契約模組後不重 dump）→ `dump_ws_contract.py --check` 紅。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_ws_contract tests.test_dump_ws_contract -v`；`python scripts/dump_ws_contract.py --check`；`cd ../frontend && npm run check:ws-types`。

### Step 5 — Repository / data access：實作

- [x] `hierarchy_service.py`：§一之一 #3。三層查詢形狀照 `performance-design.md` §三之一（系統層一條 join，**不**沿用兩條的 `assert_system_owned_by`）；`project_ids` 收集：`project_id` 參數（若專案層查得）、系統列所屬專案、圖所屬系統的專案；`explicit = project_id is not None or system_id is not None`。
- [x] `membership_facade.py`：§一之一 #4。
- **落實**：functional-design R-01（查詢面）、nfr-design R-02（批次）、nfr-design R-06（相異專案收集）。
- **驗證**：`grep -n "membership\|ProjectMember" backend/services/hierarchy_service.py backend/services/hierarchy_facade.py` 的 import 與查詢命中為 0（docstring 提及除外，逐筆判讀）；`grep -c "_visible_project_ids_select\|visible_project_ids\|is_project_visible" backend/services/membership_facade.py` 的命中只經 `membership_service`。

### Step 6 — Repository / data access：測試

- [x] `test_describe_work_target.py` 的 `VisibilityBatchTest`（3 案）：同一 `MembershipFacade` 實例上三次 `project_visibility(principal)` 產生的閉包共判 10 個 pid → 可見性 SQL 恰 1 條；兩位使用者在同一實例各自 1 條、結果不互相污染；閉包對「可見集合非空但不含目標 pid」回 `False`（V1 的必要構造）。服務層查詢另以 (a)／(e)／(g) 的服務層版本各 1 案涵蓋（併入 `DescribeWorkTargetTest` 的 helper）。
- **突變**：V1（閉包回 `bool(ids)`）→ 第 3 案紅（Step 8 的 (b2) 亦紅）；V2（拿掉暫存、每次呼叫 `is_project_visible`）→ 第 1 案紅。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_describe_work_target.VisibilityBatchTest -v`；`U23` 回歸：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_project_write_guard tests.test_project_visibility_queries tests.test_project_visibility_endpoints tests.test_membership_facade -v`（閉包語意不變，必須全綠）。

### Step 7 — Business logic：實作（`U7` facade，ADR D-2、D-3、D-4）

- [x] `hierarchy_facade.py`：§一之一 #5。`describe_work_target` 步驟：

  | 步 | 動作 | SQL |
  |---|---|---|
  | ① | `_authorize(principal, "view")`；`HierarchyForbidden` 不捕捉 | 1 |
  | ② | `hierarchy_service.describe_work_target(...)` | ≤ 3 |
  | ③ | `found.explicit` 且 `found.project_ids` 任一 `not project_visible(pid)` → `{"projectName": None, "systemName": None, "diagramName": None}` | ≤ 1 |
  | ④ | 否則回 `found.names`（只有圖的路徑：`projectName`／`systemName` 恆為 None，不判可見性） | 0 |

- [x] `resolve_work_target`：服務層解析後，`pid = resolved["projectId"]`；`pid is None or project_visible(pid)` → 回傳；否則 `project_id` 或 `system_id` 非 None → `HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL if project_id is not None else SYSTEM_NOT_FOUND_DETAIL)`；否則 `{"projectId": None, "systemId": None, "diagramId": resolved["diagramId"]}`。
- [x] `test_hierarchy_service.py` 五處補參數（§一之二 #10 前半）。
- **落實**：functional-design R-01、nfr-requirements R-01、nfr-design R-01、R-06、`[EPD1]`=A。
- **驗證**：`grep -n "project_visible" backend/services/hierarchy_facade.py` 命中七個簽章（三寫入＋四讀取）；`grep -n "^from\|^import" backend/services/hierarchy_facade.py` 無成員關係符號。

### Step 8 — Business logic：測試

- [x] `test_describe_work_target.py` 的 `DescribeWorkTargetTest`（12 案，§四之一）與 `StatementCountTest`（5 案）。
- [x] `test_hierarchy_service.py` 的 `BrainReadVisibilityTest`（6 案）。
- [x] `test_project_visibility_static.py`：§一之二 #11。
- **突變**：W1（拿掉 ③）→ (b)、(b2) 紅；W2（`project_visible=None` 且為 None 時略過）→ (h) 與 `S2` 紅；W3（只有圖時推導上層並判可見性、不可見即三名稱 null）→ (e2) 紅；W4（③ 只判 `project_id` 參數）→ (i) 紅；W5（系統層改用 `assert_system_owned_by`）→ `StatementCountTest` 的「完整三元組 ≤ 5」紅；W6（不可見改拋 `HierarchyNotFound`）→ (b) 紅；H1（`list_projects` 拿掉過濾）→ `BrainReadVisibilityTest` 被移出者案紅；H2（`list_systems` 不可見回 `[]`）→ 同檔 `HierarchyNotFound` 案紅；H3（`resolve_work_target` 拿掉可見性）→ ①② 紅；H4（由圖推導也拋 `HierarchyNotFound`）→ ② 紅。
- **驗證**：
  `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_describe_work_target tests.test_hierarchy_service tests.test_project_visibility_static -v`

### Step 9 — API / endpoint：實作（`U13` 大腦 WS 介面，ADR D-6、D-7）

- [x] `brain_gateway.py`：§一之一 #6。`_names_for` 形狀：

  ```python
  async def _names_for(self, conn, triples):
      unique = list(dict.fromkeys(triples))          # 去重、保序
      def _run():
          out = {t: dict(_NO_NAMES) for t in unique}
          try:
              db = self.session_factory()
          except Exception as exc:
              _log(logging.WARNING, "work_target_names_failed", connId=conn.conn_id, exc=type(exc).__name__)
              return out
          try:
              facade = self.hierarchy_facade_factory(db)
              vis = self.membership_facade_factory(db)
              for pid, sid, did in unique:
                  try:
                      out[(pid, sid, did)] = facade.describe_work_target(
                          conn.principal, project_visible=vis.project_visibility(conn.principal),
                          project_id=pid, system_id=sid, diagram_id=did)
                  except HierarchyForbidden:
                      pass                                   # 被拒絕是正常結果，不記（nfr-design R-04）
                  except Exception as exc:
                      _log(logging.WARNING, "work_target_names_failed", connId=conn.conn_id, exc=type(exc).__name__)
                      try: db.rollback()
                      except Exception: pass
          finally:
              db.close()
          return out
      try:
          return await asyncio.to_thread(_run)
      except Exception as exc:                               # 絕不往外拋
          _log(logging.WARNING, "work_target_names_failed", connId=conn.conn_id, exc=type(exc).__name__)
          return {t: dict(_NO_NAMES) for t in unique}
  ```

  （示意；`vis.project_visibility(...)` 必須寫在呼叫點內，不得先存成區域變數——`S3` 要求 `ast.Call`。）
- [x] 握手：第一個 `try`（`:822-834`）之後、第二個 `try`（`:840`）之前，以快照會送出的各段三元組呼叫 `_names_for`，結果交 `_snapshot_envelopes`。
- [x] `main.py`：§一之一 #7。
- **落實**：functional-design R-01（推送面）、nfr-requirements R-01（目錄）、R-03、nfr-design R-04、`[EPD1]`=A（轉接器）。
- **驗證**：`grep -n "membership" backend/services/brain_gateway.py` 只命中參數名、屬性名與 docstring（無 `import`）；`python -c "import main"`（import smoke，抓不到漏傳——如實記載）；`python scripts/dump_openapi.py --check` 綠（零 HTTP 變更）。

### Step 10 — API / endpoint：測試

- [x] `brain_gateway_fakes.py`、`test_brain_gateway_startup.py`、`test_brain_gateway_handshake.py`、`test_brain_gateway_turn.py`：§一之二 #12–#15。
- [x] `test_describe_work_target.py` 的 `CatalogStatementCountTest`（2 案）：N＝1 與 N＝8 時 `_build_catalog` 的語句數分別恰為 3 ＋ 3N（6、27）；N＝51（截斷）且未選定專案時恰 3。
- **突變**：G1（`_names_for` 往外拋）→ handshake 拋例外案得 1011，紅；G2（`HierarchyForbidden` 也記 log）→ `assertNoLogs` 案紅；G3（每組各開一個 session）→ handshake 案以 `session_factory` 呼叫計數斷言恰 1，紅；G4（`_on_set_work_target` 扇出不帶名稱）→ turn 案紅；G5（`_build_catalog` 某呼叫點改傳 `lambda _: True`）→ `S3` 紅；G6（`brain_gateway.py` 加 `from services.membership_facade import MembershipFacade`）→ `test_brain_gateway_limits.py` 既有禁止清單紅；G7（`main.py` 漏傳 factory）→ `test_brain_gateway_startup.py` 紅；G8（不可見時改送 `error(UNAUTHORIZED)`）→ turn 層 (b') 逐位元比較案紅。
- **驗證**：
  `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_brain_gateway_handshake tests.test_brain_gateway_turn tests.test_brain_gateway_fanout tests.test_brain_gateway_startup tests.test_brain_gateway_limits tests.test_brain_gateway_memory tests.test_describe_work_target -v`
  `python scripts/dump_openapi.py --check`

### Step 11 — Frontend behavior：實作

- [x] §一之三 #17–#46。lint 結構約束照 `frontend-components.md` §四：effect body 內不同步 `setState`；訊息處理在 `onmessage` 事件回呼內 dispatch；同步掛點的 effect 只**送 WebSocket 訊息**；`WebSocket`、計時器、對齊旗標、`pendingEchoes`、`openedBy` 放 `useRef`，**render 期間不讀 ref**；reducer 一律回傳新物件。
- [x] 首次對齊只在兩處執行：`work_target` 的 `onmessage` 與頁面在既有非同步續延中呼叫的 `onPageReady`（不在 effect 內，`performance-design.md` §四）。
- [x] `unsavedWork.ts` 抽出後 `handleCanvasExit` 行為不變（Step 12 的既有 e2e 回歸承擔）。
- [x] **code review 三項**（nfr-requirements R-04，寫入 code-summary）：cleanup 必關連線並清計時器；不以 ref 去重；無 effect 外建連線的路徑。
- **落實**：functional-design R-02、R-03、R-04、R-05、R-06、R-08；nfr-requirements R-05、R-06；nfr-design R-05、R-07；`BR91`–`BR98`；`EPN-01`–`EPN-19`。
- **驗證**：`npm run lint`（0 errors；warnings 不得高於 Step 2 基準）；`npm run build`（含 `tsc -b`）；`npm run check:ws-types`；`npm run check:types`（不受影響，回歸）。
- **grep 完成條件**（逐筆判讀寫入 code-summary）：`grep -rnE "localStorage|sessionStorage|indexedDB|caches\." frontend/src/brain frontend/src/components/brain frontend/src/pages/EntryPage.tsx frontend/src/utils/unsavedWork.ts` 為 0（`EPN-13`）；`grep -rn "4000" frontend/src/brain frontend/src/components/brain frontend/src/utils/unsavedWork.ts` 為 0（`EPN-27`）；`grep -rn "fetch(" frontend/src/brain frontend/src/components/brain frontend/src/pages/EntryPage.tsx` 為 0（`EPN-08`；`refreshMe()` 為既有函式的呼叫，不在此列）；`grep -rn "brain/testing" frontend/src --include='*.ts' --include='*.tsx' | grep -v '^frontend/src/brain/testing/'` 為 0（infra §四之一 第 19 列）；`grep -c "key=" frontend/src/App.tsx frontend/src/brain/BrainTranscriptContext.tsx` 皆 0（R-03）；`grep -rn "projectName" frontend/src --include='*.ts*'` 的型別宣告只在 `ws-contract.d.ts`（`NFR5.140`）；`grep -rn "cloud360.brain.v1\|'bearer\.'" frontend/src` 為 0（子協定由型別取值）；`console.` 只帶 `type`／`code`／關閉碼／turnId（逐筆判讀）。

### Step 12 — Frontend behavior：測試

- [x] `entry-page.spec.ts`（49 案）、`entry-page-live.spec.ts`（5 案）：見 `unit-test-instructions.md` §三之二。每個 `test()` 前有 `@purpose`／`@given`／`@step`／`@pass`／`@story`／`@ui`／`@api` 規格註解（受測對象無 HTTP 端點者不寫 `@api`，不得捏造）。`describe › test` 字串**合併後不得改**（`cicd-pipeline.md` §一之二）。
- [x] 既有 15 個測試（`[EPI2]`=A ＋ infra `R-01`／`R-02`）：
  - `管理員登入後進入工作區`（`:71`）**改名**為 `管理員登入後進入入口頁`：斷言 `toHaveURL(/\/$/)` 與 `getByTestId('brain-entry-page')` 可見；`@ui` 改 `/`。
  - `錯誤密碼被拒並停留在登入頁`（`:51`）：`:55` 改 `toHaveURL(/\/login$/)`；`@step`／`@pass`／`@note` 同步改為「仍停在 `/login`」。
  - 其餘 13 個（`:88`、`:111`、`:141` 內 `:158`／`:173`、`gotoAdmin` 的 8 個、`estimate-workspace.spec.ts` 的 2 個）：落點斷言改 `not.toHaveURL(/\/login$/)`，**其後緊接一個正向錨點**（對照表見 `unit-test-instructions.md` §三之三）；`:176` 的 `toHaveCount(0)` 之前必須先斷言 `sidebar-entry-link` 可見（infra `R-02`）。名稱不變，`@purpose`／`@step` 同步更新。不得順手放寬其他斷言（code review 逐一核對，寫入 code-summary）。
- **突變**：見 §五 的 F1–F26、C3、X1、X2。
- **驗證**：`npx playwright test tests/e2e/entry-page.spec.ts`（攔截式，前端服務於 `BASE_URL` 即可）；`npx playwright test tests/e2e/entry-page-live.spec.ts tests/e2e/regression.spec.ts tests/e2e/estimate-workspace.spec.ts`（需 `docker-compose.test.yml` stack，見 `unit-test-instructions.md` §二）；`npm run lint`（spec 檔受新 tests 區塊檢查）。

### Step 13 — Environment / build configuration

- [x] `deploy.yml` 新增步驟 6a（`[EPI1]`=A）：`set -uo pipefail`（不含 `-e`）、最多 12 輪、每輪 `curl -sS -o /dev/null -D - --http1.1 --max-time 5` 帶 `Connection: Upgrade`／`Upgrade: websocket`／`Sec-WebSocket-Version: 13`／固定 `Sec-WebSocket-Key`／`Sec-WebSocket-Protocol: cloud360.brain.v1`，以 `|| RC=$?` 取得結束碼（28 視為正常）；看到 `HTTP/1.1 101` 且有 `sec-websocket-protocol: cloud360.brain.v1` 即 `exit 0`；全部失敗時依 infra `R-03` 印出最後一輪的狀態列、「協定標頭：有／無」、`curl exit=<RC>`，再 `::error::`（引用 `OPEN-EP14-13`）並 `exit 1`。不讀任何 secret、無 `continue-on-error`、不加進 `rollback` job。
- [x] `test_brain_ws_deploy_probe.py`（§一之二 #16，4 案）：位置（前一步以 `Verify sessions survive a Redis restart` 開頭、後一步為 `Record this commit as the last-good deployment`）；`run` 無 `set -e`、無 `continue-on-error`、含 `Sec-WebSocket-Protocol: cloud360.brain.v1` 且不含 `bearer.` 與 `${{ secrets.`；`rollback` job 的步驟不含該名稱；失敗分支輸出狀態列、協定標頭有無與 curl 結束碼三項。
- [ ] **本機驗證**（`cicd-pipeline.md` §二之一 最後一列）：對 `docker compose -f deploy/docker-compose.test.yml up -d` 起的 stack，把 URL 換成 `http://localhost:8090/api/brain/ws`，正案以 0 結束；突變 D1（拿掉 `Sec-WebSocket-Protocol` 標頭）必須以非零結束並印出三項診斷，還原後再綠。結果記入 code-summary。Cloudflare 那一跳只在第一次部署時才真正被驗證（如實記載）。
- [x] repo 根目錄：`python3 scripts/validate_repo_contract.py`、`python3 scripts/validate_env_contract.py`。
- [x] `git diff --stat`：§一之五「不改的檔」皆零變更；`frontend/package.json` 的 `dependencies`／`devDependencies` 鍵集合前後相同（`EPN-21`）。新檔路徑不含 `prod`／`production`／`secrets` path part。
- **突變**：D1（見上）；D2（6a 加 `continue-on-error: true`）→ 測試紅；D3（6a 移到 last-good 之後）→ 測試紅；D4（6a 複製進 `rollback` job）→ 測試紅。
- **驗證**：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_brain_ws_deploy_probe tests.test_mcp_bridge_deploy -v`。

### Step 14 — Documentation

- [x] `DEPLOY.md` 新增「入口頁部署後實測」一節：步驟 6a 的存在與三種失敗訊號的判讀（403＝請求方向被剝；101 無協定標頭＝回應方向被剝；網路失敗＝tunnel／DNS）；`cicd-pipeline.md` §五之二 第 1–4 步（第 1 步以引用 `brain-gateway/code-generation/code-summary.md` §六之二 的方式，不重抄 token 處置）；「**不得**以區網 IP 開頁驗證」的理由；未完成第 1、4 步不得宣稱 `OPEN-EP14-13`／`OPEN-GW13-6` 結案。不含任何 token、不含 secret 樣式字面（`FORBIDDEN_CONTENT_PATTERNS`）。
- [x] 確認 Step 1 的 ADR 正式檔與草案內容一致（只差 Status 與標題）。
- [x] `LOCAL-DEV.md`：**不觸發**（§六之一），code-summary 記明判定依據。
- **完成條件**：`grep -n "入口頁部署後實測" DEPLOY.md` ≥ 1；`python3 scripts/validate_repo_contract.py` 綠。

### Step 15 — Traceability 與 code-summary

- [x] `code-summary.md`：Step 1 複驗紀錄、Step 2 基準；§二 全部 26 項的落點；突變結果（§五 全表逐列：改了什麼、哪一案紅、還原後綠）；設計文字回補表（`functional-spec.md` §二之一第 5 點由 ADR D-9 取代、§九之一 IAM 列「不擴大可見範圍」由 ADR D-2 收緊；`rules.md` `BR93.4` 的 key 形狀、`BR97.5` (2) 的無條件改開、`BR92.5` 的 4403 導航由對應裁決取代；`performance-requirements.md` `EPN-06` 的 ≤ 4／≤ 12 改 ≤ 5／≤ 15、`EPN-02` 的理由改述；`performance-design.md` §三之一 ④' 由 nfr-design R-01 移除、§三之三 的「2 ＋ 5N」改為「3 ＋ 3N」；`security-design.md` §二之二「捕捉全部例外並記 log」改為「`HierarchyForbidden` 不記」、§七 M2 的承接改為 V1；`nfr-design-questions.md` 的「§五之二」→ `security-design.md` §六之二；`cicd-pipeline.md` §三之二 的「14 個」→ 15 個、「不受影響」清單移除 `:55`；`infrastructure-specification.md` §二 PostgreSQL 列的「一次批次可見性查詢」由 ADR D-5 落實）；ADR-0006 四面向（§六之二）；交給 `build-and-test` 與 `tcms-test-cases` 的事項（Kiwi 孤兒、`vite dev` StrictMode 手動案、真實 backend 重啟的 `AC2.1.4` 手動案、部署後人工四步）；§七 揭露清單。
- [x] `traceability.json`：43 條 `OK` 的 AC（`AC1.2.4`、`AC8.1.2`、`AC9.1.2`、`AC9.1.4` 照上游 N/A）＋ 本單元 49 條 `BRx.y` ＋ `nfr-requirements` 的 9 條繼承子條（`NFR2.140`／`.141`、`NFR3.140`／`.141`、`NFR4.140`、`NFR5.140`／`.141`、`NFR8.140`、`NFR11.140`）；每個 `OK` 指向一個存在的實作或測試檔。
- [x] `source-manifest.json`：§一 的全部應用程式路徑（含 `ws-contract.json`、`frontend/src/types/ws-contract.d.ts`、`.github/workflows/deploy.yml`、`DEPLOY.md`、四支只補參數或改 lambda 的既有測試檔、兩支既有 e2e）。
- [x] **全單元重跑**：`unit-test-instructions.md` §二「全單元」指令與 `dump_ws_contract.py --check`、`dump_openapi.py --check`、`npm run check:ws-types`、`npm run lint`、`npm run build`。
- [x] **合併前檢查**（只在分支上、squash 之前，由合併者執行；§七 第 3 點）：寫入 code-summary 的交接段，本站不執行合併。

## 四、步驟 ↔ 故事追溯

### 四之一、後端案例清單（Step 6／8／10）

| # | 身分／情境（ORM 直接構造） | 期望 | 層 | 承接 |
|---|---|---|---|---|
| (a) | 擁有者且為成員，完整三元組 | 三名稱 | facade | `EPN-11` |
| (b) | 被移出的建立者（`owner_user_id`＝他、無他的成員列、專案另有一位成員） | 三名稱皆 null，含他自己的圖名 | facade | FD R-01 |
| (b2) | 同 (b)，另是**第二專案**的成員 | 同 (b) | facade | ND R-03 |
| (b') | 同 (b)，經 `_names_for` 推送 | `work_target` 三名稱 null；序列化與 (g) 逐位元相同 | gateway | `EPN-12` |
| (c) | 建立者、專案零成員列 | 三名稱 | facade | `EPN-11` |
| (d) | 非擁有者的成員，圖是他自己的 | 專案、系統名 null；圖名有值 | facade | `OPEN-EP14-9` 現況 |
| (e) | 自有孤兒圖 | 只有 `diagramName` | facade | `[EP2]` 修訂 1 |
| (e2) | 只有圖、圖掛在被移出者的前專案下 | `{null, null, "<圖名>"}` | facade ＋ gateway（`[EPD1]` ②） | ND R-01 |
| (f) | `K2 view` 撤銷 | facade 拋 `HierarchyForbidden`；經 `_names_for` 三名稱 null、**無 log** | facade ＋ gateway | ND R-04 |
| (g) | 不存在的專案 id | 專案名 null | facade | `EPN-12` |
| (h) | 漏傳 `project_visible` | `TypeError` | facade | `EPN-11b` |
| (i) | `project_id` 可見，`system_id` 的系統屬另一個不可見專案 | 三名稱 null | facade | ND R-06 |
| (j) | 圖標題為 `""` | `diagramName == ""`（不轉 null） | facade | FD R-06 後半 |
| GT1 | `set_work_target` 後扇出 | `work_target` 帶名稱 | gateway | `BR97.2` |
| GT2 | 被移出者說出前專案名稱 | `not_found_message`；0 則 `clarify`；0 次設定 | gateway | NR R-01 |
| GT3 | 可見的同名專案 | 唯一命中並設定 | gateway | NR R-01（雙向） |
| GT4 | `[EPD1]` ①：被移出者明確送前專案 id | 一則 `error`（`target_not_found`）；作業對象不變 | gateway | `[EPD1]`=A |
| GT5 | `[EPD1]` ③：一般擁有者同形狀 | 三層照常解析 | gateway | `[EPD1]`=A（雙向） |
| GT6 | `set_sharing_mode` 的扇出 | 該段 `work_target` 帶名稱 | gateway | `BR97.2` |

（turn 層另含 (b')、(e2) 兩案，共 8 案；handshake 層 3 案。）

### 四之二、AC ↔ 步驟

| AC | 驗證 | 步驟 |
|---|---|---|
| `AC1.4.1`–`AC1.4.4` | e2e E1–E3：`K1` 落地、`isPending` 在前、無 `K1` 走既有瀑布、全無落 `/403` | 11、12 |
| `AC1.1.1`、`AC1.1.2`、`AC5.1.1`、`AC5.1.2` | e2e E16、E17 | 11、12 |
| `AC1.1.3`、`AC8.1.1`、`AC10.2.3` | e2e E12；live L2 | 11、12 |
| `AC1.1.4` | e2e E28、E29、E39 | 11、12 |
| `AC1.1.5`、`AC2.1.1`、`AC2.1.2`、`AC2.2.3`、`AC9.1.1`、`AC10.1.1` | 後端 (a)–(j)、GT1、GT6、handshake；e2e E23 | 3–10、11、12 |
| `AC1.2.1`–`AC1.2.3` | e2e E19、E20 | 11、12 |
| `AC1.3.1`–`AC1.3.3`、`AC5.1.3` | e2e E18 | 11、12 |
| `AC2.1.3` | e2e E27 | 11、12 |
| `AC2.1.4` | e2e E41（`routeWebSocket` 版）；真實 backend 重啟交 `tcms-test-cases` 手動桶 | 11、12 |
| `AC2.2.1`、`AC2.2.2`、`AC9.1.3` | e2e E37、E33；既有 e2e 回歸 | 11、12 |
| `AC3.1.1`–`AC3.1.4` | e2e E25、E26、E40 | 11、12 |
| `AC8.1.3` | e2e E5；live L1 | 11、12 |
| `AC8.1.4` | 既有 `regression.spec.ts` 15 案處置後全綠；子頁面既有對話區不動 | 11、12 |
| `AC10.1.2`–`AC10.1.4` | e2e E21 | 11、12 |
| `AC10.1.5`、`AC10.2.1`、`AC10.2.2`、`AC10.2.4` | e2e E22 | 11、12 |

## 五、突變驗證彙整（每項：套用 → 確認紅 → 還原 → 確認綠；結果逐列寫入 code-summary 與 `tcms-test-cases` 的 `automation-test-plan.md`，`EPN-26`）

| 代號 | 突變 | 必須紅的案 | 來源（`security-design.md` §七 對照） | 步驟 |
|---|---|---|---|---|
| C1 | 名稱欄位給 `= None` 預設 | `Adr0022NameFieldTest` 缺欄位案 | infra §四 第 3 列 | 4 |
| C2 | 改契約不重 dump | `dump_ws_contract.py --check` | infra §四 第 1 列 | 4 |
| C3 | `diagramName` 改名為 `diagramTitle` 並重產型別 | `npm run build`（`wsFrames.ts` 型別錯誤） | `BR98.4` | 12 |
| V1 | 閉包回 `bool(ids)`（忽略 pid） | `VisibilityBatchTest` 第 3 案、(b2) | M2（ND R-03 改承接） | 6、8 |
| V2 | 拿掉暫存、每次 `is_project_visible` | `VisibilityBatchTest` 第 1 案、`StatementCountTest` 的 `list_projects` 等量案 | ND R-02 | 6、8 |
| W1 | `describe_work_target` 拿掉 ③ | (b)、(b2)、(b') | M1 | 8、10 |
| W2 | `project_visible=None` 且為 None 時略過 | (h)、`S2` | M3 | 8 |
| W3 | 只有圖時推導上層並判可見性 | (e2) | ND R-01 | 8 |
| W4 | ③ 只判 `project_id` 參數 | (i) | ND R-06 | 8 |
| W5 | 系統層改用 `assert_system_owned_by` | `StatementCountTest` 完整三元組 ≤ 5 | NR R-02 | 8 |
| W6 | 不可見改拋 `HierarchyNotFound` | (b) | `EPN-12` | 8 |
| H1 | `list_projects` 拿掉過濾 | `BrainReadVisibilityTest` 被移出者案；GT2 | M5 | 8、10 |
| H2 | `list_systems` 不可見回 `[]` | `BrainReadVisibilityTest` `HierarchyNotFound` 案 | NR R-01 | 8 |
| H3 | `resolve_work_target` 拿掉可見性 | `[EPD1]` ①②（facade 與 GT4） | M8 | 8、10 |
| H4 | 由圖推導也拋 `HierarchyNotFound` | `[EPD1]` ② | `[EPD1]` 選項 B | 8 |
| G1 | `_names_for` 往外拋 | handshake 拋例外案（得 1011） | 失敗域 §三 | 10 |
| G2 | `HierarchyForbidden` 也記 log | (f) gateway 案 `assertNoLogs` | ND R-04 | 10 |
| G3 | 每組各開一個 session | handshake 的 `session_factory` 呼叫計數 | `EPN-06` | 10 |
| G4 | `_on_set_work_target` 扇出不帶名稱 | GT1 | `BR97.2` | 10 |
| G5 | `_build_catalog` 某呼叫點傳 `lambda _: True` | `S3` | M4 | 8、10 |
| G6 | `brain_gateway.py` import `MembershipFacade` | `test_brain_gateway_limits.py` | M6 | 10 |
| G7 | `main.py` 漏傳 factory | `test_brain_gateway_startup.py` | NR R-03 | 10 |
| G8 | 不可見時送 `error(UNAUTHORIZED)` | (b') 逐位元比較 | M7 | 10 |
| F1 | `K1` 判斷移到 `isPending` 之前 | E1 | `EPN-17` | 12 |
| F2 | store 加一行 `sessionStorage.setItem` | E45 | `EPN-13` | 12 |
| F3 | `console.warn(payload)` | E46 | `EPN-14` | 12 |
| F4 | token 放進 `?token=` | E5 | `EPN-16` | 12 |
| F5 | Provider 改以 `user?.id ?? "anon"` 為 key、拿掉訂閱 | E43 | M9 | 12 |
| F6 | 只在 `logout()` 通知 | E44 | M10 | 12 |
| F7 | 子頁面 4403 改 `navigate('/')` | E10 | M11 | 12 |
| F8 | `/workspace` 拿掉未儲存條件 | E30 | M12 | 12 |
| F9 | 拿掉 `hasUnsavedAssessmentWork` | E31 | M12 | 12 |
| F10 | 拿掉 `is_owner` 條件 | E33 | M13 | 12 |
| F11 | 回聲改回只比對最近一次送出值 | E32 | M14 | 12 |
| F12 | 拿掉 `openedBy === 'bootstrap'` 條件 | E35 | M15 | 12 |
| F13 | token 緩衝到 `done` 才寫入 | E12 | `NFR3.140` | 12 |
| F14 | 4401 後仍排退避 | E7 | `EPN-03` | 12 |
| F15 | 放棄判準改為固定 3 次 | E8 | `EPN-02` | 12 |
| F16 | 拿掉 500 則上限 | E42 | `EPN-04` | 12 |
| F17 | 對照改回「段＋索引」 | E42 的附帶斷言（token 寫到錯的訊息） | `EPN-05` | 12 |
| F18 | 重連後保留本地工作項 | E41 | `NFR4.140` | 12 |
| F19 | 入口頁加一次 `fetch` | E47 | `EPN-08` | 12 |
| F20 | 拿掉 `aria-busy` 或 LiveRegion 寫入 | E12 | `EPN-09` | 12 |
| F21 | 收到 `cost_card` 時 `navigate('/cost')` | E21 | `NFR11.140` | 12 |
| F22 | 無 `K1` 時同步 hook 仍送出 | E38 | ND R-05 | 12 |
| F23 | 忽略 `listOk` | E36 | FD R-06 | 12 |
| F24 | `""` 顯示「（無法顯示名稱）」 | E23 | FD R-06 | 12 |
| F25 | 跳過 `protocolVersion` 核對 | E5 | `BR92.2` | 12 |
| F26 | cleanup 不關連線 | E6 | `EPN-01` | 12 |
| T1 | spec 內手寫 `{ type: 'work_target', payload: {...} }` | `npm run lint` | `EPN-19` | 12 |
| T2 | tests 區塊漏展開 `WS_SUBPROTOCOL_RESTRICTIONS`：在 `frontend/tests/` 暫放 `new WebSocket(u, ['bearer.x'])` | `npm run lint` | infra §四之一 第 10 列 | 12 |
| T3 | app 程式匯入 `brain/testing/wsFrames` | Step 11 的 grep 非 0 | infra §四之一 第 19 列 | 12 |
| T4 | `App.tsx` 在 `BrowserRouter` 之上加 `key=` | Step 11 的 grep 非 0 | FD R-03 | 12 |
| D1 | 6a 拿掉 `Sec-WebSocket-Protocol` 標頭（本機對測試 stack） | 指令非零結束並印出三項診斷 | infra §二之一 | 13 |
| D2 | 6a 加 `continue-on-error: true` | `test_brain_ws_deploy_probe` | `[EPI1]`=A | 13 |
| D3 | 6a 移到 last-good 之後 | `test_brain_ws_deploy_probe` | `[EPI1]`=A | 13 |
| D4 | 6a 複製進 `rollback` job | `test_brain_ws_deploy_probe` | infra §二之一 | 13 |
| X1 | `page.route` 讓 `/api/auth/login` 對錯誤密碼回 200 ＋ token | `錯誤密碼被拒並停留在登入頁` | infra R-01 | 12 |
| X2 | `page.route` 讓 Developer 的 `/api/auth/me` 帶 `J3a:view` | `Developer 看不到系統管理區`（證明錨點使 `toHaveCount(0)` 在渲染後才判定） | infra R-02 | 12 |

共 **59** 道（C 3、V 2、W 6、H 4、G 8、F 26、T 4、D 4、X 2）。`security-design.md` §七 的 M1–M15 全部有對應列（M2 依 nfr-design R-03 改由 V1 承接，理由見 §二）。

## 六、blocking 同步義務與 ADR-0006

### 六之一、`project.md` 規則的判定

| 規則 | 判定 | 依據 |
|---|---|---|
| schema ↔ deploy 同步（`schema_rbac.sql` ＋ `DEPLOY.md`，**blocking**） | **不觸發** | 零 DDL、不新增 story id、不改 seed；`describe_work_target` 為純查詢（`functional-spec.md` §八之三 第 5 點、`infrastructure-specification.md` §五） |
| `LOCAL-DEV.md` 同步 | **不觸發** | 不改 `backend/database.py` 的 schema 補丁、`deploy/nginx.conf`／`frontend/nginx.conf`、任一 `.env.example`、`render-env.sh`；`LOCAL-DEV.md:22` 已記載入口頁的本機前置條件（Redis ＋ 金鑰） |
| env contract（三環境分離） | **不觸發** | 零新變數；6a 不寫 `deploy/.env`；Step 13 跑 `validate_env_contract.py` |
| 憑證落在 secrets 而非 variables | **本單元不新增 secret**；但本單元與 `U13` 同一次進 `ut`，`U13` 帶入的 `OPENROUTER_API_KEY` 必須在合併前由**使用者**以 `gh api repos/<owner>/<repo>/actions/secrets` 與同路徑 `/variables` 各查一次確認（§七 第 4 點） | `project.md ## Mandated`；`cicd-pipeline.md` §三 第 6 列 |
| repo contract | Step 13、Step 14 跑 `validate_repo_contract.py`；`DEPLOY.md` 新段不含 secret 樣式字面 | `project.md ## Mandated` |
| PBT hard constraint | **不適用**（非 IaC generator、cost calculator、agent routing；以窮舉身分 example-based 驗證） | `security-design.md` §九 |

### 六之二、ADR-0006 四面向（逐格對照 `infrastructure-specification.md` §七）

| 面向 | 上游判定 | 本計畫判定 | 落點 |
|---|---|---|---|
| IAM | 適用（擴充） | **相同** | 名稱、目錄、直接設定三處收緊為「擁有者範圍 ∩ 可見性」（ADR D-2–D-6）；靜態鎖 `S2`／`S3` 擴充；子頁面無 `K1` 不掛大腦掛點；`K1` 前端判斷只是呈現 |
| Encryption | 適用（相同） | **相同** | 零新傳輸、零新持久化；對話紀錄只在記憶體（`EPN-13`） |
| Network exposure | 適用（相同） | **相同** | 零新端點、零新埠；6a 只送一個不帶 token 的升級請求、立即被 4401 關閉；4403 不再造成重連或導航迴圈 |
| Audit logging | 適用（相同） | **相同**（細節依 nfr-design R-04 更正） | 不新增稽核事件；新增一筆白名單內 WARNING `work_target_names_failed`；`HierarchyForbidden` **不記**；前端 console 不含內容 |

## 七、核可關卡需揭露事項

1. **可見性批次化的形狀與目錄成本的讀法**（nfr-design R-02 裁決的落點，ADR D-5）：裁決「一條 SQL 判定整批專案 id，大腦目錄與 `list_projects` 的語句數不隨擁有專案數增加」。本計畫的落點是把 `MembershipFacade.project_visibility` 的閉包改成**每個實例、每位使用者只查一次可見集合**——不新增第二個注入方法（保住 `EPN-11a`「判定只有一份」與 `S3` 的呼叫點形狀）。結果：`list_projects` **固定 3 條**（與 N 無關，完全符合字面）；目錄的**可見性成本固定 ＋1**。但 `_build_catalog` 的**總數**仍是 3 ＋ 3N（N ≤ 50；逐專案 `list_systems` 的授權、擁有者、列舉三條是 `U13` **既有**成本，改前為 2 ＋ 3N）——若裁決的「目錄語句數不隨專案數增加」要讀成**總數**常數，需另把逐專案 `list_systems` 改為一次批次列舉（新增 `U7` 方法、改 `U13` 目錄迴圈），本計畫**未納入**。此改動也**改變了 `U19`／`U23` 的一個方法**（閉包語意不變、SQL 由每次一條改為每實例一條）。
2. **nfr-design R-03 的 M2 改承接**：閉包不再呼叫 `is_project_visible`，原 M2（拿掉其外層條件）在本單元的測試中已不可能被觸發；改以等價突變 V1 承接並保留 (b2) 夾具。原 M2 仍由 `U23` 的測試承擔。
3. **合併前檢查（只在分支上、squash 之前）**：`git log --oneline origin/ut..HEAD` 同時含 `U13` 與 `U14` 的 commit；`grep -c projectName ws-contract.json` ≥ 1；`test -e backend/services/brain_router.py` 為假。任一不成立即停止合併。`U13` 與 `U14` 必須同一次合併（ADR D-9；示範網關的移除已滿足，記憶檔 `[IG2]`=A）。
4. **合併前使用者必做**：以 `gh api repos/<owner>/<repo>/actions/secrets` 與 `gh api repos/<owner>/<repo>/actions/variables` 各查一次，確認 `OPENROUTER_API_KEY` 在 **secrets** 而不在 variables。未設 → 第一次部署即失敗並回滾整個 intent。
5. **`deploy.yml` 多一道擋部署的步驟**（`[EPI1]`=A）：影響全部單元的部署；本 intent 第一次進 `ut` 時若失敗，回滾會退回**整個** intent；Cloudflare 一時異常可能誤回滾（12 輪重試緩解）。
6. **重開已交付單元**：`U2`（契約模組與兩份產生檔）、`U7`（facade、service、測試 5 處補參數）、`U13`（閘道、fakes、三支測試）、`U19`／`U23`（`project_visibility` 閉包、靜態鎖）。既有斷言只補參數不改期望；唯一例外 `test_brain_gateway_startup.py:60` 的 lambda 簽章。
7. **既有 15 個 e2e 改動**，其中 1 個改名 → Kiwi 舊案例成為孤兒，由 `tcms-test-cases` 人工停用。
8. **偏離 `BR92.5` 字面**：4403 不導航（照字面會形成子頁面無限迴圈並丟失畫布）；改為至多一次 `refreshMe()`——這是 `EPN-08`「零 HTTP」唯一的例外（既有端點、只在終止路徑上）。
9. **D-1／D-2／D-3／D-5／D-7 的上游偏離**（`[EP1]`／`[US:U9]`／線框 §6、§20／§21、M3 總額、`AC10.1.3` 的「取代」）在 functional-design 關卡已揭露，本計畫照做、不重開。
10. **e2e 交辦類只以 `routeWebSocket` 驗證**（D-2）：「意圖被辨識」這一環在任何自動化層都只以替身驗證；真實鏈路由 staging 人工驗證。
11. **設計補強被採用**：`brainProtocol.ts` 的拆檔（§一之三 #19）、`test_brain_ws_deploy_probe.py`（鎖住 6a 的位置與形狀）、`DEPLOY.md` 的「入口頁部署後實測」一節（infra 建議、非 blocking）。
12. **`ui-regression` 時間預算未量測**：新增 54 案；退避與 4403 以 `page.clock` 快轉。逾 15 分鐘時 `ui-regression` 紅（訊號、不擋合併）。
13. **殘留**：移出之前已設好的作業對象不追溯清除；成員看得到專案而大腦目錄看不到（`OPEN-EP14-9`）；`U12` 的 `list_diagrams_of_system` 仍只做擁有者範圍；名稱陳舊（`OPEN-EP14-16`）；孤兒圖使 `AC2.2.1`「同一個系統」落空（`OPEN-EP14-17`）；Cloudflare 的 `bearer.` 項只能人工實測；部署重啟的後端不可用時長未量測；`MembershipFacade` 實例內的可見集合暫存在實例存活期間不更新（ADR Consequences 殘留 4）；4401 無 token 更新端點（`OPEN-EP14-15`）。
14. **conductor 的時序提醒**（`project.md ## Mandated`）：`PLAN_APPROVAL_RECORDED` 一記下、派工之前立刻跑 `aidlc-state.ts unit start`；審查收據可能因 `.hypothesis`／`__pycache__` 指紋問題記不進去，屆時依 `review-NN-unreceipted.md` 處置，不得偽造順序。

## 八、方法論與 contract 基線的對應

`test-after` 的五個可測層：**Data model**＝Step 3–4（`U2` 契約模型與兩份產生檔，零 DDL）；**Repository / data access**＝Step 5–6（服務層純查詢、可見性批次）；**Business logic**＝Step 7–8（`U7` facade 四個讀取方法的守門、靜態鎖）；**API / endpoint**＝Step 9–10（`U13` 大腦 WS 的組裝、名稱推送、目錄、直接設定）；**Frontend behavior**＝Step 11–12（入口頁、子頁面掛點、e2e 兩層、既有 15 案處置）。plan_profile 的 Project structure／runner 兩步為 Step 1–2；Environment/build configuration 為 Step 13（`deploy.yml` 6a；`eslint.config.js` 因 Step 12 的 spec 需受其檢查而提前於 Step 11 實作）；Documentation and traceability 為 Step 14–15。方法論未改。

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
