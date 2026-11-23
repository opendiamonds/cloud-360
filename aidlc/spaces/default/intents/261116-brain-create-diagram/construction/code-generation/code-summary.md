# Code Summary — 讓大腦直接建立新的架構圖

> 分支 `danniel/feat/brain-create-diagram`（自 `origin/ut` 開出，2026-11-17）。**未 commit、未 push**（依 conductor 指示）；commit 與 PR 標題屆時依 ADR-0010 用中文 type（建議 `功能(brain): 大腦可直接建立新的架構圖並以草稿狀態保護`）。
> 方法：test-after（計畫的 Testing Contract）。

## 檔案（依單元）

### U1 diagram-drafts

| 檔案 | 改動 |
|---|---|
| `backend/models.py` | `UserDiagram.status`（`draft`／`ready`、非空、預設 `ready`、`ck_user_diagrams_status`）；常數 `DIAGRAM_STATUS_*`、`DRAFT_REJECTED_DETAIL` |
| `backend/services/hierarchy_migration.py` | `_ensure_diagram_status_column`（由 `_ensure_hierarchy_schema` 呼叫；inspector 判斷、同一條敘述加欄＋CHECK） |
| `schema_rbac.sql` | `ADD COLUMN IF NOT EXISTS status` ＋ `pg_constraint` 守門的 CHECK ＋ COMMENT ＋ 驗證範例、檔頭清單 |
| `DEPLOY.md` | 表格加列、2.2.7 加欄位說明與「草稿狀態欄位」小節（升級順序、驗證、回復） |
| `backend/services/hierarchy_service.py` | `list_diagrams_of_system(include_drafts=…)` 必填、回四元組、新到舊；刪除系統檢查註明含草稿 |
| `backend/services/hierarchy_facade.py` | facade 同步；`record_diagram_change` docstring 修訂 K-07 並寫明出處（契約 C5） |
| `backend/services/work_orchestrator.py` | 呼叫端改 `include_drafts=True`；存回送 `finalize=True`；`failure_for_status` 帶 `draft_rejected` |
| `backend/services/user_router.py` | 清除預設專案、刪除使用者兩處註明含草稿（行為不變） |
| `backend/services/collab_router.py` | `as_draft`、`finalize`、四支端點的 `response_model`（`DiagramCreated`／`DiagramSaved`／`MyDiagramItem`／`DiagramDetail`）、`diagram_status`、`reject_if_draft`、分享回 409 |
| `backend/services/review_router.py`、`agent_router.py` | 評核（兩處）與 WA 共編拒絕草稿 |
| `backend/cost/estimate_intake_router.py` | 估價綁圖：圖存在、屬於呼叫者且為草稿才回 409（擁有權優先） |
| `openapi.json`、`frontend/src/types/api.d.ts` | 重新產生 |

### U2 brain-create-flow

| 檔案 | 改動 |
|---|---|
| `backend/services/brain_diagram_creation.py`（新） | `decide`、`make_title`、`creation_change_texts`（純函式）；候選建構（純函式）；`create_draft`、`record_creation`、`load_target_facts`、`list_owned_systems`（I/O） |
| `backend/services/intent_routing_decisions.py`、`intent_routing_port.py`、`intent_routing_types.py`、`intent_routing.py` | `wants_new_diagram` 題併入同一次請求；`new_diagram_probability` 留在 `IntentDecision`（行程內、不 repr、不進觀測） |
| `backend/services/work_orchestrator_capabilities.py` | `CapabilityError.draft_rejected`；`create_diagram`；`put_diagram(finalize=…)` |
| `backend/services/work_orchestrator_rules.py` | `PHRASES["draft_rejected"]`、`failure_for_status` 的 409 分支 |
| `backend/services/brain_ws_contract.py`、`ws-contract.json`、`frontend/src/types/ws-contract.d.ts` | `ClarifyPayload.kind` 加四值；`ClarifyCandidate` 加 `systemId`／`diagramId`／`action` |
| `backend/services/brain_gateway_rules.py` | `TargetRef.diagram_id`（選填） |
| `backend/services/brain_gateway.py` | 新建流程（判定 → `user_can_arch` 預檢 → 建草稿 → 記變更紀錄 → 切換對象 → 交辦）；四種反問與點選（候選集合比對 ＋ `set_work_target` 重新驗證 ＋ 失效重列）；`_reread_target` 比對 `diagram_id`；log 白名單加非內容欄位；`build_brain_gateway` 注入 `CapabilityClient` |

### U3 draft-ui

| 檔案 | 改動 |
|---|---|
| `frontend/src/projects/projectsApi.ts` | `MyDiagram` 改由產生型別推導；`isDraft` |
| `frontend/src/components/DraftBadge.tsx`（新） | 「草稿」標示 |
| `frontend/src/components/projects/SystemDiagrams.tsx`、`OverviewTab.tsx` | 草稿標示；計數排除草稿 |
| `frontend/src/pages/WorkspacePage.tsx`、`components/DrawioCanvas.tsx` | 「儲存架構圖」送 `finalize: true`（自動存檔與評核前寫回不送）；歷史選單標示「（草稿）」；`data-testid` |
| `frontend/src/components/brain/ClarifyCandidates.tsx` | 四種新反問的提示文字（契約 C6 的 Open Question 於本站定案） |
| `frontend/src/brain/testing/wsFrames.ts` | `clarifyFrame` 補新欄位（產生型別將其列為必填 nullable） |

## 測試

- 新增：`tests/test_diagram_drafts_schema.py`（5）、`test_diagram_drafts_hierarchy.py`（5）、`test_diagram_drafts_api.py`（12）、`test_brain_diagram_creation.py`（18，含 6 個 `@given`）、`test_brain_diagram_creation_flow.py`（18）、`frontend/tests/e2e/diagram-drafts.spec.ts`（3）。
- 同步既有：`test_diagram_system_attach.py`、`test_work_orchestrator_store.py`、`test_work_orchestrator_flow.py`、`work_orchestrator_fakes.py`、`test_intent_routing_decisions.py`、`test_work_orchestrator_rules.py`（皆為契約要求的形狀變更，未放寬任何斷言）。
- 後端全套：基準 `Ran 1542 tests … OK (skipped=3)` → 變更後 `Ran 1601 tests … OK (skipped=3)`。
- 前端：`npm run lint` 0 errors（2 個既存 warning）；`npm run build` 通過；`check:types`／`check:ws-types` 一致。Playwright：以 `vite preview` 在本機服務已建置的前端、全部 API 與 WebSocket 由 `page.route` 樁化（不需後端與任何密鑰），`diagram-drafts.spec.ts` 3 passed；相關既有 spec（project-pages、entry-page、object-picker、brain-assistant）共 135 passed。
- 突變驗證（皆紅燈後還原複驗綠燈）：拿掉閘道 `can_edit` 預檢 → NFR5 deny 案紅；`reject_if_draft` 失效 → 評核／共編／分享／`draft_rejected` 五案紅；計數不排除草稿 → e2e 計數案紅（Expected "1"／Received "2"）。

## 與計畫的偏差

1. **遷移不用 `ADD COLUMN IF NOT EXISTS`**：SQLite 不支援；改以 inspector 判斷、同一條敘述加欄＋CHECK（與 `system_id` 同形）。`schema_rbac.sql`（PostgreSQL）仍用 `IF NOT EXISTS`。
2. **判定表第三列與 FR6.3 衝突的處置**：作業對象是**草稿**且 p ≥ t 時判為「修改（接著畫同一張）」而非新建——同一句「幫我畫一張…」的 p 必然 ≥ t，照表會違反 FR6.3b 的「再說一次不另建」。已在 `decide` docstring 標〔推導〕，可推翻。
3. **新反問說明文字的落點**：`ClarifyPayload` 沒有文字欄，且輪次狀態機不允許先送 token 再送 clarify；故 FR3.6 的「其餘請用切換對象選取」附在最後一筆候選的標籤後；FR3.5 失效時「重新列出」做到了，但「回覆說明」那一句無處可放（未做）。
4. **NFR4 的判定類別記在閘道事件 `diagram_decision`**，不在路由觀測事件——判定需要作業對象事實，只有閘道有。
5. **`wants_new_diagram` 缺題時為 `None`（視為不明）**，不判 `MalformedRouting`；出現但越界仍拒絕。
6. **「切換對象選單」沒有可標示的地方**：`ObjectPicker` 只列專案與系統、不列圖；可切到圖的選單是工作區歷史選單，已標示。
7. **`DRAFT_REJECTED_DETAIL` 放在 `models.py`**：`work_orchestrator_rules` 為純函式層、不得 import `models`（AST 測試鎖住），故 `PHRASES` 存同字串並以測試鎖相等。
8. **閘道新建流程以 `diagram_client_factory` 是否注入為開關**：`build_brain_gateway` 一律注入；既有閘道測試的替身組裝不注入，行為不變。

## 未完成與風險

- ~~**部署前置（重要）**~~ **已由修訂 1 取代**（backend 啟動時自動補欄位，見下方「修訂 1」）。原文：既有 volume 必須先跑 `cd backend && python scripts/run_hierarchy_migration.py` 補 `user_diagrams.status`，否則新版 backend 讀圖全數 500。`deploy.yml` 不呼叫遷移腳本；`hierarchy_migration` 模組契約明文不掛啟動路徑，故本站未自行改為啟動時補欄位——是否改為啟動時自動補（比照 `ensure_project_members_on_startup`）需要人裁決。已寫入 `DEPLOY.md`。
- NFR1（判定準確率重測）、NFR2（首字 P50）需真實模型與部署環境，排在 build-and-test。
- 前端 e2e 在 CI 的 `ui-regression` 短生命週期 stack 上尚未執行過（本機以 `vite preview` 跑過）。
- ~~`LOCAL-DEV.md` 未改~~（修訂 1 已動 `backend/database.py` 啟動補丁，故已同步更新 `LOCAL-DEV.md`）。

## 修訂 1（2026-11-19 核可關卡要求修改；計畫 Step 20–27）

來源：審查 `construction/brain-create-flow/code-generation/reviews/review-01.md`（整體）、`review-02.md`、`construction/diagram-drafts/code-generation/reviews/review-01.md`、`construction/draft-ui/code-generation/reviews/review-01.md`。使用者裁決：Major 二採「backend 啟動時只補該欄位」；偏差 #2 接受、不改。各單元的檔案層級改動見各自的 `code-summary.md`「修訂 1」。

| Step | 改了什麼 | 主要檔案 |
|---|---|---|
| 20 | 啟動補丁 `_ensure_diagram_status_schema()`：只補 `user_diagrams.status`、可重跑、不跑整套階層遷移、失敗即啟動失敗；DEPLOY.md 改寫升級說明並補回退警告；LOCAL-DEV.md 同步 | `backend/database.py`、`DEPLOY.md`、`LOCAL-DEV.md` |
| 21 | 建草稿呼叫加期限 `DIAGRAM_CREATE_TIMEOUT_SEC = 15.0`（經 `GatewayTiming.wait_for`）；逾時＝結果不明、不重試、不交辦 | `backend/services/brain_gateway.py` |
| 22 | 意圖反問選定後帶回 `new_diagram_probability` | `backend/services/brain_gateway.py` |
| 23 | 403 分流：`CapabilityError.arch_forbidden`（detail 以 `ARCH_FORBIDDEN_DETAIL_PREFIX` 開頭）；缺架構權限才回申請角色的說明，其餘回 `CREATE_FORBIDDEN_MESSAGE` | `backend/models.py`、`services/rbac.py`、`services/work_orchestrator_capabilities.py`、`services/brain_gateway.py` |
| 24 | 兩條恆真的性質測試改寫；`build_brain_gateway` 注入接線測試 | `backend/tests/test_brain_diagram_creation.py`、`test_brain_gateway_startup.py` |
| 25 | 取名碼位上限 200（扣後綴預留後主題 ≤ 184 碼位），PBT 補總長性質；開頭落單組合記號去除 | `backend/services/brain_diagram_creation.py` |
| 26 | 掛圖下拉與評核頁下拉標示草稿；評核 409 顯示 detail；`Diagram`／`DiagramStub` 由產生型別推導；反問依 kind 的 `aria-label` 與「都不要」 | `frontend/src/components/projects/SystemDiagrams.tsx`、`pages/AssessmentPage.tsx`、`pages/WorkspacePage.tsx`、`components/brain/ClarifyCandidates.tsx`、`tests/e2e/diagram-drafts.spec.ts` |
| 27 | `draft-ui` 追溯補 FR3.4／FR6.2／FR6.4a；三單元 `code-summary.md` 與 `source-manifest.json` 更新；全套重測 | 本檔與各單元紀錄 |

### 修訂 1 的測試結果

- 後端全套：`cd backend && .venv/bin/python -m unittest discover -s tests` → `Ran 1613 tests in 135.821s` `OK (skipped=3)`（基準 1601，新增 12：schema 4、flow 4、startup 1、取名 3；兩條性質為改寫、不計新增）。
- 契約：`dump_openapi.py --check`「規格檔與後端程式碼一致。」；`dump_ws_contract.py --check`「WS 契約規格檔與後端程式碼一致。」；`validate_repo_contract.py`、`validate_env_contract.py` 皆 passed；前端 `check:types`「API 型別檔與規格檔一致。」。
- 前端：`npm run lint` 0 errors、2 個既存 warning（`AssessmentPage.tsx`、`WorkspacePage.tsx` 的 `exhaustive-deps`）；`npm run build` 通過。
- Playwright：**以本機 `vite preview`（port 4173）服務建置產物、API 與 WebSocket 全部 `page.route` 樁化執行，未在 CI 的 `ui-regression` stack 上跑過**。`diagram-drafts.spec.ts` 5 passed；連同 project-pages、entry-page、object-picker、brain-assistant 共 137 passed。

### 修訂 1 的突變驗證（皆紅燈後還原複驗綠燈）

**Step 24 改寫的性質測試**（原寫法對下列每一項都會維持綠燈：性質 1 的斷言只比較輸入數字，性質 4 對同一輸入呼叫兩次）：

| 突變（`brain_diagram_creation.decide`／`_zone`） | 結果 |
|---|---|
| M1：作業對象是正式圖、p ≥ t 改判 `MODIFY` | 性質 1 紅 |
| M3：系統有圖無草稿、`p is None` 時直接 `CREATE`（與不明區數值分流） | 性質 4 紅（初版性質 4 以兩個獨立 p 再過濾同區，此突變**存活**；改為依區域構造 p 後才抓到） |
| M4：作業對象是草稿、p ≥ t 改判 `CREATE`（推翻已接受的偏差 #2） | 性質 1 紅 |
| M5：新建區邊界改為 `p > 0.5 and p >= (t + 0.5) / 2` | 性質 4 與性質 2 紅 |

**其餘步驟**：

| Step | 突變 | 結果 |
|---|---|---|
| 20 | 拿掉 `init_db` 內的 `_ensure_diagram_status_schema()` 呼叫 | `test_init_db_calls_the_status_patch` 紅 |
| 21 | 期限改傳 `diagram_create_timeout_sec * 2`（注入時鐘不再觸發） | 卡住案紅（10 秒後才由兜底逾時） |
| 22 | 重建時 `new_diagram_probability=None` | 意圖反問保留 p 案紅（直接建了圖） |
| 23 | 閘道 403 不看 `arch_forbidden`；`_is_arch_forbidden` 不比對前綴 | 文字分流案紅；端點分類案紅 |
| 24 | 正式組裝 `diagram_client_factory=None` | 接線測試紅 |
| 25 | `_truncate_graphemes` 不檢查碼位 | 碼位上限性質與單一巨大字元案紅（初版性質用 `st.lists` 產生組合記號、數量偏小，此突變**存活**；改為 `st.integers(0,120)` 指定數量後抓到，並因此查出系統名退回路徑會以落單組合記號開頭，已修） |
| 26 | 掛圖下拉不加「（草稿）」；`readErrorDetail` 回原文 | 掛圖案紅；評核案紅 |

### 修訂 1 的偏差與未處理

- Step 23：repo 內沒有 K2 403 的既有文字，新增 `CREATE_FORBIDDEN_MESSAGE`，文字需人確認。
- Step 21：期限 15 秒由本站選定（審查要求由人定），可在關卡調整。
- Step 20：啟動補丁失敗會讓 backend 啟動失敗（刻意不同於其他 `_ensure_*` 的 warning），已寫入 DEPLOY.md／LOCAL-DEV.md。
- 審查中未列入 Step 20–27 的項目維持原狀：FR3.5 說明句（契約缺文字欄）、`pick_system` 候選未依 K2 edit 過濾、跨連線重複建草稿、`updated_at` NULL 排序方言差、PostgreSQL 實跑遷移（build-and-test）、`goWellArchitected` 對草稿仍導向評核頁。
