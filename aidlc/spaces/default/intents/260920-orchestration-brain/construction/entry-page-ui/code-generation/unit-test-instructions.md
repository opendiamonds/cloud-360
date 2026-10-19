# Unit Test Instructions — `U14 entry-page-ui`

## 一、框架與設定

- **後端**：Python 內建 `unittest` ＋ `unittest.mock` ＋ `ast` ＋ SQLAlchemy 事件計數，**不是 pytest**（`team.md`）。測試資料庫為 `tests/helpers.py` 的 in-memory SQLite（`psycopg2` 以 `MagicMock` 取代），角色經 `ensure_role_permissions_seeded(db, force=True)` 播種。閘道測試沿用 `tests/brain_gateway_fakes.py` 的 `Harness`（真 `SessionStore` ＋ Redis 替身、真認證、其餘替身注入），本單元在其中新增 `FakeVisibility` 並讓 `FakeHierarchy` 套用 `project_visible`。
- **前端**：只有 Playwright e2e（chromium 單一 project，`frontend/playwright.config.ts`，`testDir: './tests/e2e'`）。**沒有** unit／component 測試框架，本單元不新增（`team.md` D 項不採、`EPN-21`）。已安裝 `@playwright/test` 1.61.1，`routeWebSocket`（≥ 1.48）、`page.clock`、`emulateMedia` 皆為內建 API。
- **e2e 兩層**（`BR98.4`、`EPN-24`）：
  - **攔截層** `tests/e2e/entry-page.spec.ts`：`page.routeWebSocket('**/api/brain/ws', …)` 扮演伺服器；`page.route('**/api/auth/me')` 控制全域權限（`K1`／`A1`／`A3`／`C1`／`J3a`）；子頁面既有的圖清單、bootstrap、圖讀取等 HTTP 一律 `page.route` 攔截。**伺服器訊框只能由 `frontend/src/brain/testing/wsFrames.ts` 的匯出函式產生**，spec 內不得出現含 `type` 與 `payload` 鍵的物件字面量（lint 機械化，`EPN-19`）。
  - **真實 stack 層** `tests/e2e/entry-page-live.spec.ts`：對 `deploy/docker-compose.test.yml` 起的 stack（nginx → backend → Redis／PostgreSQL），以 seed 帳號 `admin` 登入；金鑰為空（`OPENROUTER_API_KEY: ""`），故只斷言握手、`ready`、狀態推送、`prompt_guard` 攔截與錯誤呈現。
- **新增設定**：無。新測試檔放進 `backend/tests/` 即被 `python -m unittest discover -s tests` 撿到；新 spec 放進 `frontend/tests/e2e/` 即被 `ui-regression` 的裸 `npx playwright test` 撿到。`frontend/tests` 不在任何 tsconfig 內，spec 本身不受 `tsc -b` 檢查——型別保護由 `src/brain/testing/wsFrames.ts`（在 `src` 內）承擔。
- **授權不 mock**（facade 層）：`test_describe_work_target.py` 與 `test_hierarchy_service.py` 走真實的 `HierarchyFacade`、`MembershipFacade`、`membership_service` 與 `user_can`；閘道層以 `FakeVisibility` 替身，但其 `invisible` 集合的語意與真實閉包相同。
- **skip**：本單元新增的測試中 `skipTest`／`skipUnless`／`skipIf`／`SkipTest`／`test.skip`／`test.fixme` 為 0。
- **規格註解**（tcms 必做 3b）：每個新增或改動的 e2e `test()` 前有 `/** @purpose @given @step @pass @story @ui @api */`；後端測試方法的 docstring 帶 `@purpose`／`@story`，有 HTTP 端點者才寫 `@api`（本單元後端受測對象全無 HTTP 端點——WS 與 facade——故**不寫** `@api`，不得捏造；WS 端點以 `@ui` 不適用，改在 `@given` 寫明 `/api/brain/ws`）。
- **名稱穩定性**：`describe` 為 `U14 entry page` 與 `U14 entry page live stack`；每個 `test` 字串合併後不得再改（Kiwi 案例名稱 `<describe> › <test>`）。既有 15 案中只有 `管理員登入後進入工作區` 改名（`[EPI2]`=A）。

## 二、本單元的執行指令（都限定本單元的檔案）

在 `backend/` 目錄執行：

```bash
# 就緒檢查與基準（Step 2）：本單元會改到或依賴的 16 個既有模組
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_ws_contract tests.test_dump_ws_contract tests.test_hierarchy_service tests.test_project_visibility_static tests.test_project_visibility_queries tests.test_project_visibility_endpoints tests.test_project_write_guard tests.test_membership_facade tests.test_brain_gateway_handshake tests.test_brain_gateway_turn tests.test_brain_gateway_fanout tests.test_brain_gateway_startup tests.test_brain_gateway_limits tests.test_brain_gateway_memory tests.test_session_store_behaviour tests.test_mcp_bridge_deploy -v
python scripts/dump_ws_contract.py --check
python scripts/dump_openapi.py --check

# Data model（Step 4）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_ws_contract tests.test_dump_ws_contract -v
python scripts/dump_ws_contract.py --check

# Repository / data access（Step 6）＋ U23 回歸
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_describe_work_target.VisibilityBatchTest -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_project_write_guard tests.test_project_visibility_queries tests.test_project_visibility_endpoints tests.test_membership_facade -v

# Business logic（Step 8）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_describe_work_target tests.test_hierarchy_service tests.test_project_visibility_static -v

# API / endpoint（Step 10）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_brain_gateway_handshake tests.test_brain_gateway_turn tests.test_brain_gateway_fanout tests.test_brain_gateway_startup tests.test_brain_gateway_limits tests.test_brain_gateway_memory tests.test_describe_work_target -v
python scripts/dump_openapi.py --check

# Environment / build（Step 13）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_brain_ws_deploy_probe tests.test_mcp_bridge_deploy -v

# 全單元（Step 15）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_ws_contract tests.test_dump_ws_contract tests.test_describe_work_target tests.test_hierarchy_service tests.test_project_visibility_static tests.test_project_visibility_queries tests.test_project_visibility_endpoints tests.test_project_write_guard tests.test_membership_facade tests.test_brain_gateway_handshake tests.test_brain_gateway_turn tests.test_brain_gateway_fanout tests.test_brain_gateway_startup tests.test_brain_gateway_limits tests.test_brain_gateway_memory tests.test_session_store_behaviour tests.test_brain_ws_deploy_probe tests.test_mcp_bridge_deploy -v
python scripts/dump_ws_contract.py --check
python scripts/dump_openapi.py --check
```

在 `frontend/` 目錄執行：

```bash
# 就緒檢查（Step 2）：檔案尚不存在時應回報 0 個測試，而不是設定錯誤
npx playwright test tests/e2e/entry-page.spec.ts tests/e2e/entry-page-live.spec.ts --list

# 契約型別與靜態閘門（Step 4、Step 11、Step 12）
npm run gen:ws-types          # 只在 Step 3 契約改動後執行一次；之後以 check 驗證
npm run check:ws-types
npm run check:types
npm run lint
npm run build

# e2e 攔截層（Step 12、Step 15）：只需前端被服務於 BASE_URL
npx playwright test tests/e2e/entry-page.spec.ts

# e2e 真實 stack 層與既有 15 案（Step 12、Step 15）：需要 docker-compose.test.yml 的 stack
npx playwright test tests/e2e/entry-page-live.spec.ts tests/e2e/regression.spec.ts tests/e2e/estimate-workspace.spec.ts
```

**e2e 的服務方式**：預設 `BASE_URL=http://localhost:8090`，即 `docker compose -f deploy/docker-compose.test.yml up -d --build` 的 nginx 入口（見 `LOCAL-DEV.md` 的 Docker 模式）。攔截層也可改用 `npm run dev` 並以 `BASE_URL=http://localhost:5173 npx playwright test tests/e2e/entry-page.spec.ts` 執行——此時 `wsUrl()` 組出的位址會被 `routeWebSocket` 攔下，**不需要**後端、Redis、`claude` CLI 或 n8n。真實 stack 層與既有 15 案**必須**用 compose stack（要真的登入 seed 帳號與握手）。

在 repo 根目錄執行（Step 13、Step 14）：

```bash
python3 scripts/validate_repo_contract.py
python3 scripts/validate_env_contract.py
```

步驟 6a 的本機驗證（Step 13，對 compose stack；正案應以 0 結束，拿掉 `Sec-WebSocket-Protocol` 標頭的突變 D1 應以非零結束並印出三項診斷）：以 `.github/workflows/deploy.yml` 中該步驟的 `run` 內容，把網址換成 `http://localhost:8090/api/brain/ws` 執行一次。

**跨單元測試檔的說明**：`test_ws_contract`／`test_dump_ws_contract`（`U2`）、`test_hierarchy_service`（`U7`）、`test_brain_gateway_*`（`U13`）、`test_project_visibility_*`／`test_project_write_guard`（`U23`）、`test_membership_facade`（`U19`）、`test_session_store_behaviour`（`U8`，`resolve_work_target` 呼叫點的回歸）、`test_mcp_bridge_deploy`（`U21`，`deploy.yml` 步驟位置的回歸）出現在本單元的指令中，是因為本單元改動它們依賴的程式或補了參數；除 §三之一 列明的新增案與 `test_brain_gateway_startup.py:60` 的 lambda 外，它們的斷言不屬本單元、也不被本單元修改。

## 三、測試清單與數量（standard：每元件 5–8 案）

### 三之一、後端

| 檔案 | 元件 | 案例 |
|---|---|---|
| `test_ws_contract.py`（改） | `WorkTargetPayload` C-8 三欄 | 既有樣本補三欄（`None`）；新增 `Adr0022NameFieldTest` 2 案：(1) 三欄任缺一 → `ValidationError`（三次子案）；(2) 三欄為 `None`、`"訂單系統"`、`""` 皆可構造並讀回同值 |
| `test_describe_work_target.py`（新） | `VisibilityBatchTest`（3 案） | 同一 `MembershipFacade` 實例上三次 `project_visibility(principal)` 的閉包共判 10 個 pid → 可見性 SQL 恰 1 條；兩位使用者在同一實例各 1 條且結果互不污染；可見集合非空但不含目標 pid → `False` |
| 〃 | `DescribeWorkTargetTest`（12 案） | (a) 擁有者且為成員 → 三名稱；(b) 被移出的建立者 → 三名稱皆 null（含自己的圖名）；(b2) 同 (b) 且另是第二專案的成員 → 同 (b)；(c) 零成員列建立者 → 三名稱；(d) 非擁有者成員、圖是自己的 → 專案／系統名 null、圖名有值；(e) 自有孤兒圖 → 只有 `diagramName`；(e2) 只有圖、圖在前專案下 → `{null, null, "<圖名>"}`；(f) `K2 view` 撤銷 → `HierarchyForbidden`；(g) 不存在的專案 id → 專案名 null；(h) 漏傳 `project_visible` → `TypeError`；(i) `project_id` 可見而系統屬另一不可見專案 → 三名稱 null；(j) 圖標題 `""` → `diagramName == ""` |
| 〃 | `StatementCountTest`（5 案） | 完整三元組恰 5 條；只有圖 2 條；完整三元組在擁有 1 個與 50 個專案時語句數相同；`list_projects` 在 1 個與 50 個專案時皆恰 3 條；`_names_for` 對三段不同三元組（快照）≤ 15 條且 `session_factory` 恰呼叫 1 次 |
| 〃 | `CatalogStatementCountTest`（2 案） | `_build_catalog`：N＝1 恰 6 條、N＝8 恰 27 條（3 ＋ 3N）；N＝51（截斷）且未選定專案恰 3 條 |
| `test_hierarchy_service.py`（改） | `BrainReadVisibilityTest`（6 案） | `list_projects` 對 (b) 身分不含前專案、對 (c) 身分含；`list_systems` 對 (b) 拋 `HierarchyNotFound` 且訊息為 `PROJECT_NOT_FOUND_DETAIL`；`resolve_work_target` 的 `[EPD1]` ① 明確送前專案 id → `HierarchyNotFound`、② 只送自己掛在前專案下的圖 → `{None, None, 圖}`、③ 一般擁有者同形狀 → 三層照常解析 |
| `test_project_visibility_static.py`（改） | 靜態鎖 | `S2` 檢四個讀取方法 ＋ 三個寫入方法；`S3` 檢同一集合、讀取呼叫點 ≥ 5、例外恰一筆；新增 `test_S3b_exception_list_is_exact`（例外為 `("services/session_store.py", "resolve_work_target")` 且該呼叫確實存在） |
| `test_brain_gateway_startup.py`（改） | 組裝 | `:60` 的 lambda 改 `lambda app, **kw: …` ＋ 斷言 `kw["membership_facade_factory"] is MembershipFacade`；新增：不帶 factory 呼叫 `build_brain_gateway(app)` → `TypeError`（以 `mock.patch` 隔離 Redis 與 router 建構） |
| `test_brain_gateway_handshake.py`（改） | 握手快照（3 案） | 快照的 `work_target` 帶 `FakeHierarchy.names_by_triple` 的名稱；`describe_work_target` 拋 `RuntimeError` → 握手完成（收到 `ready`、非 1011）、名稱 null、`assertLogs` 恰一筆 `work_target_names_failed` 且訊息不含名稱；拋 `HierarchyForbidden` → 名稱 null、`assertNoLogs("cloud360.brain_gateway", "WARNING")` |
| `test_brain_gateway_turn.py`（改） | 扇出、目錄、直接設定（8 案） | GT1 `set_work_target` 扇出帶名稱；GT2 被移出者說出前專案名 → `not_found_message`、0 則 `clarify`、0 次設定；GT3 可見同名專案 → 唯一命中並設定；GT4 明確送前專案 id → 一則 `error`、作業對象不變；(e2) 送自己掛在前專案下的圖 → 作業對象 `{null, null, 圖}`、名稱 `{null, null, "<圖名>"}`、無 `error`；GT5 一般擁有者同形狀 → 三層照常；(b') 不可見與不存在兩種 `work_target` 序列化逐位元相同；GT6 `set_sharing_mode` 扇出的 `work_target` 帶名稱 |
| `test_brain_ws_deploy_probe.py`（新） | `deploy.yml` 步驟 6a（4 案） | 位置（前一步以 `Verify sessions survive a Redis restart` 開頭、後一步為 `Record this commit as the last-good deployment`）；形狀（無 `set -e`、無 `continue-on-error`、含 `Sec-WebSocket-Protocol: cloud360.brain.v1`、不含 `bearer.` 與 `${{ secrets.`）；`rollback` job 不含該步驟；失敗分支輸出狀態列、協定標頭有無、curl 結束碼 |

後端新增案合計：2 ＋ 3 ＋ 12 ＋ 5 ＋ 2 ＋ 6 ＋ 1 ＋ 1 ＋ 3 ＋ 8 ＋ 4 ＝ **47**（`S2`／`S3` 為改寫既有兩案，不計入）。

### 三之二、前端 e2e

**攔截層** `entry-page.spec.ts`（`describe('U14 entry page')`，49 案）

| # | 案例 | 對應 |
|---|---|---|
| E1 | `K1` 使用者造訪 `/` 看到入口頁；`isPending` 先於 `K1` 導 `/waiting-approval` | `BR91.1`、`AC1.4.1`、`AC1.4.3`、`EPN-17` |
| E2 | 無 `K1` 依既有瀑布落地、Sidebar 無入口；全無權限落 `/403` | `BR91.2`、`AC1.4.2`、`AC1.4.4` |
| E3 | 不存在的路徑導回 `/` 再由落地判斷決定 | `BR91.3` |
| E4 | Sidebar 的「入口」置頂並帶 `aria-current`；記憶捷徑與 Sidebar 同判定 | `BR91.4`、`BR91.5` |
| E5 | 連線網址不含 `?` 與 token；先送 `hello`；`ready` 版本不符 → 「版本不相容」且不重試 | `BR92.1`、`BR92.2`、`AC8.1.3`、`EPN-16` |
| E6 | 三頁間切換 5 次後未關閉的大腦連線恰 1 條 | `EPN-01` |
| E7 | 4401 → 重新登入提示且不重連；4400 → 不重試（`page.clock` 快轉 20 秒新連線 0） | `BR92.5`、`EPN-03` |
| E8 | 全部拒絕握手：每次間隔落在排程 ×[0.8, 1.0]、首次失敗後 60 秒內不出現「無法連線到大腦」、之後零自動嘗試、按「重新連線」才重來 | `EPN-02` |
| E9 | 入口頁 4403 ＋ `/me` 無 `K1` → 落到 `/workspace` 且該頁大腦連線 0 | `security-design.md` §六之二 案 1 |
| E10 | `/workspace` 4403 ＋ `/me` 無 `K1` → pathname 不變、面板消失、畫布內容不變 | 案 2 |
| E11 | `/workspace` 4403 ＋ `/me` 仍有 `K1` → 提示出現、快轉 20 秒新連線 0 | 案 3 |
| E12 | 送 `token` 不送 `done` → 文字已可見；串流中 `aria-busy="true"`；`done` 後 LiveRegion 恰寫入 1 次 | `BR93.1`、`NFR3.140`、`EPN-09`、`AC8.1.1`、`AC10.2.3` |
| E13 | `reducedMotion: 'reduce'` 時游標 `animation-name` 為 `none` | `EPN-09` |
| E14 | 零內容 `done` → 「沒有收到回覆」＋ 重試 | `BR93.2` |
| E15 | 送出後送出鈕停用，任一輪終止解除；斷線時該輪 interrupted、不自動重送、按重試只送一次 | `BR93.3`、`BR92.7` |
| E16 | 工作項在常駐區與對話流狀態相同；五狀態文字；「在等：…」；失敗原因；`sideEffect` 的 none／unknown／其他三語意 | `BR94.1`、`BR94.3`、`AC1.1.1`、`AC1.1.2`、`AC5.1.1`、`AC5.1.2` |
| E17 | 常駐區只列處理中與等待中、空集合不渲染、寬度 < 768px 預設收合 | `BR94.2` |
| E18 | 「不是這個」只送一次 `correct_work_item`、按鈕停用到下一則 `work_items`；已停掉項與新項同時可見 | `BR94.4`、`BR94.5`、`AC1.3.1`–`AC1.3.3`、`AC5.1.3` |
| E19 | 意圖反問與對象反問提示不同、不顯示信心值、選定只送一次 | `BR95.1`–`BR95.4`、`AC1.2.1`、`AC1.2.2` |
| E20 | 回絕送 `candidateId: null`、焦點回輸入列、脈絡列不變；候選未決時送新句 → 舊組 stale | `BR95.5`、`AC1.2.3` |
| E21 | 成本完成：徽章轉完成、卡片附在其後、三段文字、無法取價、連結 href 取 `costPageUrl`；pathname 變更 0 次 | `BR96.1`、`BR96.3`、`BR94.7`、`AC10.1.1`–`AC10.1.4`、`NFR11.140` |
| E22 | 成本逾時與失敗的原因文字不同；無 `C1` 權限以失敗與伺服器的權限說明呈現 | `BR96.2`、`BR96.4`、`AC10.1.5`、`AC10.2.1`、`AC10.2.2`、`AC10.2.4` |
| E23 | 脈絡列：三名稱、識別碼有而名稱 null → 「（無法顯示名稱）」、`""` → 「（未命名）」、三識別碼 null → 「尚未選定」；`data-state` 與三個 `data-id` | `BR97.2`、`AC1.1.5`、`AC2.1.1`、`AC2.2.3`、`AC9.1.1`、`NFR2.140` |
| E24 | 入口頁忽略全部 `sharing_mode`、只套用 `shared` 段的 `work_target` | `BR92.4` |
| E25 | 子頁面「改為獨立對話」：伺服器回推才換徽章、面板為空、作業對象改為該段；切回共享時紀錄與作業對象與離開時相同 | `BR97.3`、`BR97.8`、`AC3.1.1`、`AC3.1.2`、`AC3.1.4` |
| E26 | 子頁面面板送出的 `user_message` 帶 `page`；`set_work_target` 帶本頁所讀段 | `BR92.3`、`BR97.4`、`AC3.1.3` |
| E27 | `/cost` 與 `/admin/users` 不掛脈絡列、不開大腦連線 | `BR97.1`、`AC2.1.3` |
| E28 | `/workspace` 快照先到（先於 bootstrap）：就緒後開目標圖 | `BR97.5`、`NFR2.141`、`AC1.1.4` |
| E29 | `/workspace` 快照後到：最終三元組與 E28 相同 | `NFR2.141` |
| E30 | `/workspace` 先拒握手、使用者在畫布新增圖形、再接受並送首筆相符 `work_target`（另一張自有圖）→ 畫布 XML 不變、提示出現、按「開啟這張圖」並確認後才換圖；畫布乾淨的對照組自動開啟 | `EPN-18`、FD `R-02` |
| E31 | `/assessment` 先拒握手、上傳 `.drawio`、再送首筆相符 `work_target` → 「已上傳：<檔名>」仍在、提示出現 | `EPN-18`、NR `R-06` |
| E32 | 使用者自己開圖不出現「作業對象已改為」；一個往返內連選 X、Y，X 的回聲到達時也不出現 | `BR97.5`、FD `R-05` |
| E33 | 開別人分享的圖：客戶端送出的 `set_work_target` 0 則、顯示「這張圖是別人分享的…」 | `EPN-17a`、`BR97.6` ② |
| E34 | 刪除作業對象的圖 → 送 `{projectId, systemId, diagramId: null}`；新建空白畫布 → 不送、顯示「目前畫布未存檔…」 | `BR97.6` ③④ |
| E35 | 入口頁作業對象停在系統 S（diagramId null）→ 進 `/workspace`（bootstrap 開上次的圖）→ 作業對象仍為 S、不送 `set_work_target` | FD `R-08` |
| E36 | 圖清單請求失敗 → 兩向都不同步並顯示「無法確認這張圖的擁有者…」 | `BR97.5` 末段、FD `R-06` |
| E37 | 由 `/workspace` 帶 `diagramId` 進 `/assessment` → 回寫；回入口頁脈絡列對象一致 | `BR97.6`、`AC2.2.1`、`AC2.2.2` |
| E38 | 無 `K1`：子頁面不掛脈絡列與面板；畫布操作後送出的 `set_work_target` 0 則 | ND `R-05` |
| E39 | 入口頁串流中點 Sidebar 換到 `/workspace`：舊頁該輪轉 interrupted；新頁連線收到同一 turnId 的後續 → 合併回 streaming、該輪只顯示一則 | `BR93.7`、`AC1.1.4` |
| E40 | 換頁後回入口頁，共享段對話紀錄仍在 | `BR93.4` |
| E41 | 以 1011 關閉後重連、第二次 `ready` 推送與本地不同的作業對象與工作項 → 畫面被覆蓋、對話紀錄保留 | `NFR4.140`、`AC2.1.4` |
| E42 | 灌入 501 則 → 第 1 則不可見、`brain-transcript-truncated` 出現、第 2–501 則可見；被移除那一輪再收到 `token` → 另建一則、不崩潰、其他訊息內容不變 | `EPN-04`、`EPN-05` |
| E43 | A 登入時 `/api/auth/me` 回 500（user 無 `id`）→ 對話 → 經 Sidebar 登出 → B 登入 → 入口頁與兩子頁面的對話區皆空 | `EPN-15`、FD `R-03` |
| E44 | A 登入並對話 → 以 `history.pushState` ＋ `popstate` 到 `/login`（**不** `page.goto`，不重新載入）→ B 登入 → 對話區為空 | `EPN-15a` |
| E45 | 完成一次對話後 `localStorage`／`sessionStorage` 鍵集合與對話前相同，且全部值不含測試原句 | `EPN-13` |
| E46 | `page.on('console')` 收集的全部訊息不含測試原句、三個測試名稱、token 子字串 | `EPN-14` |
| E47 | 入口頁從掛載到完成一次交辦的 `/api/` 請求集合不含新路徑；子頁面掛面板前後請求數相等 | `EPN-08` |
| E48 | 空狀態只有卡 A（`canArch` 或 `A3`）與卡 C（`C1`）依權限顯示；點卡片填入輸入列、不送出；紀錄為空但作業對象非空時顯示「先前的對話大腦仍記得…」 | `BR98.1`、`BR93.4` |
| E49 | 未知 `type` 安全忽略（畫面不變、console 只記 type）；四種 `error.code` 的 `message` 原樣顯示 | `BR92.6` |

**真實 stack 層** `entry-page-live.spec.ts`（`describe('U14 entry page live stack')`，5 案）

| # | 案例 | 對應 |
|---|---|---|
| L1 | `admin` 登入後落在 `/` 的入口頁；`page.on('websocket')` 的網址為 `/api/brain/ws` 且不含 `?`；收到 `ready` 後脈絡列離開 `connecting` | `BR91.1`、`BR92.1`、`AC8.1.3`（nginx 一跳的子協定透傳） |
| L2 | 送出平台自我竄改類句子 → 固定拒絕訊息原樣顯示 | `AC1.1.3`、`BR93.1` |
| L3 | 送出一般句子（金鑰為空）→ 錯誤訊息原樣顯示、送出鈕恢復 | `BR92.6`、`BR93.3` |
| L4 | 依序進 `/workspace`、`/assessment`：每頁恰一條未關閉的大腦連線、前一頁那條已關閉 | `EPN-01` |
| L5 | Sidebar 的「入口」可見並帶 `aria-current="page"`；記憶捷徑可見 | `BR91.4`、`BR91.5` |

前端新增 e2e 合計 49 ＋ 5 ＝ **54** 案。在途與連線計數以 `page.on('websocket')` 的 `framesent`／`close` 事件維護；訊框比對以 `JSON.parse` 後比對 `type` 與 payload 欄位，不以字串包含。

### 三之三、既有 15 案的處置（`[EPI2]`=A ＋ infrastructure-design `R-01`／`R-02`）

| 檔：行 | 測試 | 新落點斷言 | 其後的正向錨點 |
|---|---|---|---|
| `regression.spec.ts:55` | `錯誤密碼被拒並停留在登入頁` | `toHaveURL(/\/login$/)`（infra `R-01`） | 錯誤訊息可見（既有 `:54`） |
| `:73` | `管理員登入後進入工作區` → **改名** `管理員登入後進入入口頁` | `toHaveURL(/\/$/)` | `getByTestId('brain-entry-page')` 可見 |
| `:90` | `登出後返回登入頁` | `not.toHaveURL(/\/login$/)` | `getByTitle('登出系統')` 可見（隨即點擊，既有 `:91`） |
| `:113` | `Platform_Admin 看得到系統管理區` | 同上 | 「系統管理」可見（既有 `:114`） |
| `:158` | `Developer 看不到系統管理區`（admin 登入段） | 同上 | 前往 `/admin/authorization-requests` 後的列可見（既有 `:165-168`） |
| `:173` | 同上（Developer 登入段） | 同上 | **新增** `getByTestId('sidebar-entry-link')` 可見，**再**斷言 `getByText('系統管理')` 的 `toHaveCount(0)`（infra `R-02`） |
| `:189`（`gotoAdmin`，8 案共用） | `:218`、`:243`、`:269`、`:314`、`:349`、`:397`、`:441`、`:475` 的 8 案 | 同上 | 點擊「使用者角色」後 `heading` 可見（既有 `:190-191`） |
| `estimate-workspace.spec.ts:17`（`login` helper）、`:35` | `上傳 AWS CSV 後顯示明細與檢查`、`官方估價教學彈窗顯示截圖與官方連結` | 同上 | 其後的 `page.goto('/cost')` 與 `toHaveURL(/\/cost/)`（既有 `:58`、`:91`）及頁面元素 |

合計 1 ＋ 1 ＋ 1 ＋ 1 ＋ 1（`:158` 與 `:173` 同一測試）＋ 8 ＋ 2 ＝ **15** 個測試。每案同步更新 `@purpose`／`@step`／`@pass`（必要時 `@ui`）；code review 逐案核對沒有放寬其他斷言，結果寫入 code-summary。

## 四、突變驗證（每項：套用 → 確認紅 → 還原 → 確認綠）

完整 59 道見 `code-generation-plan.md` §五。執行方式：

1. 在工作樹套用突變（只改一處）。
2. 執行該突變對應步驟的**單元指令**（§二），確認指定案例紅燈，記下失敗的測試名稱與訊息第一行。
3. `git checkout -- <該檔>` 還原（產生檔類突變 C2、C3 另以 `python scripts/dump_ws_contract.py` 與 `npm run gen:ws-types` 重產回原狀），重跑同一指令確認綠燈。
4. 把「突變代號、改了哪個檔的哪一行、哪一案紅、還原後綠」寫入 `code-summary.md` 的突變結果表；`tcms-test-cases` 站將其轉入 `automation-test-plan.md`。

特別說明：

- **C3**（`BR98.4`）：在 `brain_ws_contract.py` 把 `diagramName` 改名為 `diagramTitle`、重 dump、`npm run gen:ws-types`，`npm run build` 必須以 `src/brain/testing/wsFrames.ts`（與 `ContextBar`）的型別錯誤紅燈；還原時三檔一起還原並重產。
- **T2**（infra §四之一 第 10 列）：在 `frontend/tests/e2e/` 暫放一個只含 `new WebSocket(u, ['bearer.x'])` 的檔，`npm run lint` 必須紅；刪除後複驗綠。
- **T3／T4**：以 Step 11 的 grep 完成條件判定（非 0 即紅）。
- **D1**：見 §二 末段的本機驗證。
- **X1／X2**：以 `page.route` 在**單一案**內暫時注入（不改 app 程式），跑對應既有測試確認紅，移除後綠。
- 前端 F1–F26 的指令一律為 `npx playwright test tests/e2e/entry-page.spec.ts`；突變期間不提交、不推送。

## 五、覆蓋率

repo 沒有覆蓋率量測機制（`team.md`：`org.md` 的 80% line coverage「既無法量測也無法強制」）。本單元**不宣稱**百分比，也不弱化該宣稱。實際門檻：

- `team.md` A 規則：本單元不改 `role_permissions` 種子，但改了讀取路徑的授權行為 → 以被移出建立者等身分的雙向測試承擔（facade 層 12 案、閘道層 GT2／GT3、GT4／GT5、(b')）。
- B 規則：本單元**零 HTTP 端點變更**（`dump_openapi.py --check` 證明）；WS 介面以 `Harness` 的閘道測試斷言訊息形狀與內容。
- C 規則：前端資料形狀變更（C-8 三欄、入口頁、子頁面掛點）由 e2e 54 案斷言。
- §四 的 59 道突變驗證。

## 六、Mock 與測試資料

- **身分**：`make_user` 建立 `Project_Editor`（具 `K2 view`／`edit`）、`Project_Architect`、以及一個 `K2 view` 被撤銷的身分（以測試資料改 `role_permissions`，`force=True` 播種後覆寫該列）；`mint_principal` 鑄造 `Principal`。
- **專案、成員列與圖的構造**（比照 `U23` 的 `unit-test-instructions.md` §六）：
  - (a) 擁有者且有成員列：`MembershipFacade.create_project_with_owner`。
  - (b) 被移出的建立者：(a) 建立 → ORM 為第二位使用者寫一筆 `project_admin` → ORM 刪除建立者的成員列（`owner_user_id` 仍是建立者）。
  - (b2) 同 (b)，另以 ORM 讓該建立者成為**第二個專案**的成員。
  - (c) 零成員列：ORM 直接建 `Project` 不寫成員列。
  - (d) 非擁有者成員：ORM 加一筆 `ProjectMember(role="member")`，並以 ORM 建一張 `UserDiagram(user_id=<他>, system_id=<該專案的系統>)`。
  - (e) 孤兒圖：`UserDiagram(system_id=None)`。
  - (i) 系統改掛：專案 P（可見）、專案 Q（不可見）、系統 S 的 `project_id=Q`，以 `project_id=P, system_id=S` 呼叫。
  - (j) `UserDiagram(title="")`。
- **語句計數**：`setUp` 以 `event.listen(engine, "before_cursor_execute", _count)` 掛計數器、`tearDown` 以 `event.remove` 卸除；每案先暖身一次（讓 `role_permissions` 等快取路徑一致）再歸零；engine 取自 `tests/helpers.py` 的 `_test_engine`。
- **閘道替身**：`FakeVisibility(invisible={...})` 的 `factory(db)` 回自身，`project_visibility(principal)` 回 `lambda pid: pid not in invisible`；`FakeHierarchy.names_by_triple` 指定 `describe_work_target` 的回傳、`describe_raises` 指定拋出的例外；`session_factory` 以包裝計數呼叫次數（G3）。
- **既有測試的補參數**：一律 `project_visible=ALWAYS_VISIBLE`（`tests/helpers.py` 既有），語意與修改前相同。
- **log 斷言**：`self.assertLogs("cloud360.brain_gateway", level="WARNING")` 比對 `work_target_names_failed` 與 `exc=<類別名>`，並斷言訊息不含測試名稱字串；`HierarchyForbidden` 案用 `assertNoLogs`（Python ≥ 3.10）。
- **前端 stub**：專案名、系統名、圖名、使用者原句、token 各以獨特假字串（例如 `e2e-u14-<字尾>`）產生，供 `EPN-13`／`EPN-14` 的斷言；`/api/auth/me` 的權限回應以 helper 組出（形狀沿用 `member-pages.spec.ts` 的 `setupApp`，該檔 `:573` 的 `{ loc, msg, type }` 不含 `payload` 鍵，不受新 lint 選擇器影響）；退避、4403 與上限案以 `page.clock.install()` ＋ `runFor` 快轉，不以真實等待。
- **限制（如實記載）**：攔截層不碰真實後端，前後端形狀一致由 `ws-contract.json` 漂移閘門、`check:ws-types` 與 `wsFrames.ts` 的 `tsc -b` 承擔；真實 stack 層只經 nginx 一跳，Cloudflare 兩跳由部署步驟 6a（協定名項）與人工實測（`bearer.` 項、瀏覽器端）承擔；真實 backend 重啟（`AC2.1.4`）與 `vite dev` 下的 StrictMode 雙重 effect（nfr-requirements `R-04`）只能手動，交 `tcms-test-cases` 分桶。
