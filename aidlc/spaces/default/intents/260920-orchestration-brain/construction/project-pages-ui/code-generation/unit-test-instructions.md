# Unit Test Instructions — `U23 project-pages-ui`

## 一、框架與設定

- **後端**：Python 內建 `unittest` ＋ `unittest.mock` ＋ `starlette.testclient.TestClient` ＋ `ast`，**不是 pytest**（`team.md`）。測試資料庫為 `tests/helpers.py` 的 in-memory SQLite（`psycopg2` 以 `MagicMock` 取代），角色經 `ensure_role_permissions_seeded(db, force=True)` 播種。HTTP 測試以 `TestClient(app)` ＋ `app.dependency_overrides` 覆寫 `get_db` 與 `get_current_user`，樣板比照 `tests/test_membership_endpoints.py`；`TestClient(app)` 直接使用不觸發 startup 的 `init_db()`。
- **前端**：只有 Playwright e2e（chromium 單一 project，`frontend/playwright.config.ts`）。**沒有** unit／component 測試框架，本單元不新增（`team.md` D 項不採、`PPN-21`）。e2e **全部以 `page.route()` 攔截**，不打真實後端，形狀沿用 `tests/e2e/member-pages.spec.ts` 的 `setupApp`：seed token、攔截 `/api/auth/me` 控制全域權限（`K2`／`K3`／`K4`）、攔截本單元的 7 個端點並記錄請求。
- **新增設定**：無。新測試檔放進 `backend/tests/` 即被 `python -m unittest discover -s tests` 撿到；新 spec 放進 `frontend/tests/e2e/` 即被 `ui-regression` 的裸 `npx playwright test` 撿到（`PPN-23`）。
- **授權不 mock**：後端測試走真實的 `HierarchyFacade`、`MembershipFacade`、`membership_service` 與 `user_can`；只覆寫身分來源（`get_current_user`）與 DB session。
- **skip**：本單元新增的測試檔中 `skipTest`／`skipUnless`／`skipIf`／`SkipTest` 為 0。
- **規格註解**（tcms 必做 3b）：每個新增的 e2e `test()` 前有 `/** @purpose @given @step @pass @story @ui @api */`；後端測試方法的 docstring 帶 `@purpose`／`@story`／`@api`（受測對象無 HTTP 端點者——例如靜態鎖、service 層謂詞——**不寫** `@api`，不得捏造）。
- **名稱穩定性**：e2e 的 `describe` 為 `U23 project pages`，每個 `test` 字串合併後不得再改（Kiwi 案例名稱 `<describe> › <test>`，改名即成孤兒）。

## 二、本單元的執行指令（都限定本單元的檔案）

在 `backend/` 目錄執行：

```bash
# 就緒檢查與基準（Step 2）：本單元會改到或依賴的既有模組
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_membership_data tests.test_hierarchy_service tests.test_membership_facade tests.test_membership_endpoints -v

# Data model（Step 4）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_membership_data -v

# Repository / data access（Step 6）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_project_visibility_queries -v

# Business logic 與跨單元回歸（Step 8）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_project_visibility_static -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_hierarchy_service tests.test_work_orchestrator_store tests.test_requirement_field_facade tests.test_mcp_bridge_e2e tests.test_membership_facade -v

# API / endpoint（Step 10）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_project_visibility_endpoints tests.test_project_write_guard tests.test_project_visibility_queries -v
python scripts/dump_openapi.py --check

# 全單元（Step 15）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_membership_data tests.test_project_visibility_queries tests.test_project_visibility_static tests.test_project_visibility_endpoints tests.test_project_write_guard tests.test_hierarchy_service tests.test_work_orchestrator_store tests.test_requirement_field_facade tests.test_mcp_bridge_e2e tests.test_membership_facade tests.test_membership_endpoints -v
python scripts/dump_openapi.py --check
```

在 `frontend/` 目錄執行：

```bash
# 就緒檢查（Step 2）：檔案尚不存在時應回報 0 個測試，而不是設定錯誤
npx playwright test tests/e2e/project-pages.spec.ts --list

# 靜態閘門（Step 9、Step 11）
npm run lint
npm run build
npm run check:types

# e2e（Step 12、Step 15）
npx playwright test tests/e2e/project-pages.spec.ts
```

e2e 需要前端被服務於 `BASE_URL`（預設 `http://localhost:8090`，即 `deploy/docker-compose.test.yml` 的 nginx 入口，見 `LOCAL-DEV.md` 的 Docker 模式）。因為本 spec 全部攔截 API，也可改用 `npm run dev` 並以 `BASE_URL=http://localhost:5173 npx playwright test tests/e2e/project-pages.spec.ts` 執行。**不需要** `claude` CLI、n8n webhook、資料庫或後端。

在 repo 根目錄執行（Step 13）：

```bash
python3 scripts/validate_repo_contract.py
python3 scripts/validate_env_contract.py
```

**跨單元測試檔的說明**：`test_hierarchy_service`（`U7`）、`test_work_orchestrator_store`（`U12`）、`test_requirement_field_facade`（`U20`）、`test_mcp_bridge_e2e`（`U21`）出現在本單元的指令中，是因為本單元在其中共 15 處補了 `project_visible=ALWAYS_VISIBLE`；它們的斷言不屬本單元、也不被本單元修改。`test_membership_facade`／`test_membership_endpoints`（`U19`）是 `MembershipFacade` 新增方法的回歸面。

## 三、測試清單與數量（standard：每元件 5–8 案）

### 三之一、後端

| 檔案 | 元件 | 案例 |
|---|---|---|
| `test_membership_data.py`（改） | 索引的 ORM／DDL／遷移腳本一致性 | `test_M3` 加兩個點名 `assertIn`（ORM、DDL）；新增 `test_M3b`：以 `ast.parse` ＋ `ast.literal_eval` 取 `run_meta_schema_migration.py` 中 `EXPECTED_INDEXES` 的**值**，斷言三元組 `("public", "project_members", "ix_project_members_user_id")` 在其中（不得整檔 `assertIn`，因為同名字串也出現在 `BLOCK_SENTINELS["J"]` 與註解，infrastructure-design R-02） |
| `test_project_visibility_queries.py` | `membership_service` 可見性謂詞（`VisibilityPredicateTest`，7 案） | ① 擁有者且有成員列、② 成員、③ **另一專案的成員**、④ 被移出的擁有者、⑤ 零成員列專案的擁有者、⑥ 無任何關聯者 → `[]`；`visible_project_ids` 依 id 遞增；`is_project_visible` 對同五身分的布林值 |
| 〃 | 兩支列舉端點的語句數（`ListingStatementCountTest`，2 案） | 專案清單 P＝1 vs P＝8 相等；系統清單 S＝1 vs S＝8 相等（`PPN-06`）；`setUp` 掛 `event.listen(engine, "before_cursor_execute", …)`、`tearDown` 以 `event.remove` 卸除；每案先暖身再歸零 |
| `test_project_visibility_static.py` | `ast` 靜態鎖（5 案） | 1 `BR87.7` 兩個 unscoped 方法只被 `MembershipFacade` 呼叫；2 三個寫入方法的 `project_visible` 為 keyword-only 且無預設；3 非 service 層的寫入呼叫都帶 `project_visible=<…>.project_visibility(...)`（不得是 `Lambda`／`Name`／`Constant`）；4 `project_visibility` 只定義在 `MembershipFacade`；5 `hierarchy_service` 的三個寫入函式（`Attribute` 與 `Name` 兩種形式）只出現在 `hierarchy_facade.py`，且無 `from services.hierarchy_service import` 這三個名稱（nfr-design R-02） |
| `test_project_visibility_endpoints.py` | `GET /api/hierarchy/projects`、`GET /api/hierarchy/projects/{project_id}/systems`（15 案） | 五身分 × 兩端點（10）；缺 `K2`（非 canonical role）專案清單 403（1）；**可見集合為空**的非 canonical 使用者專案清單仍 403、不是 200 `[]`（1）；缺 `K2` 的系統清單對存在與不存在的 id 皆 403（2）；系統清單「從未存在的 id」vs「③ 不可見的既有 id」→ 狀態碼相等且 `response.content` 逐位元相等（`PPN-13`，1）。10＋1＋1＋2＋1＝15 |
| `test_project_write_guard.py` | 三條寫入路徑的守門（22 案） | 三路徑 × (a) 擁有者且為成員 201／204、(b) 被移出的擁有者 404 且四表列數不變、(c) 零成員列專案的擁有者 201／204、(d) 成員非擁有者 404、(f) `Developer`（有 `K2 view` 無 `K2 edit`）非成員 403 非 404 → 15 案；(e) 被移出的擁有者刪「底下仍有系統」的專案 404 非 409（僅 `delete_project`）1 案；(e') 被移出的擁有者刪「底下仍有架構圖」的系統 404 非 409 1 案；(g) 三路徑「不存在 vs (b) 同一請求者」的逐位元比較 3 案（`delete_system` 兩側皆為「查不到系統」）；`[PPD1]` 成功刪除專案、系統各 1 案（`assertLogs("cloud360.hierarchy_facade", "INFO")` 含 `actor_user_id=<請求者 id>`，不含專案名、系統名）。15＋1＋1＋3＋2＝22 |

(a)–(d) 的請求者皆持**具 `K2 edit` 的角色**（如 `Project_Editor`），否則會先在 403 停下而測不到守門（`PPN-14`）。

### 三之二、前端（`frontend/tests/e2e/project-pages.spec.ts`）

以可觀察行為計（無 component 測試框架，唯一介面是整頁 DOM 與網路請求）。

| # | 案例 | 對應 |
|---|---|---|
| 1 | Sidebar 在 `K2 view` 時出現「專案」、無 `K2` 時不出現；直接進 `/projects` 被導向 `/403` | `BR81.1` |
| 2 | 清單 empty 與 error 兩態文字不同、error 有 `[重試]`；列的「尚無系統」與「系統清單讀取失敗」 | `BR81.2`–`BR81.4` |
| 3 | 建立專案：空白名稱擋下；409／403／其他三類文案且名稱保留；成功導向 `/projects/<POST 回應的 id>?tab=overview`，pathname 變更恰 1 次 | `BR82.2`、`BR82.5`、`NFR11.101` |
| 4 | 建立系統：擁有者且 `K2 edit` 時 `system-create-action` 存在、成員非擁有者時不存在；成功後「系統 N」0 → 1、pathname 不變；pending 期間連點只發一次 `POST` | `AC11.1.1`、`AC11.1.3`、`BR82.3`、`BR82.4`、`NFR11.100` |
| 5 | 無系統的專案：需求籤為 `requirements-empty`、無選擇器 | `AC11.1.2`、`BR84.1` |
| 6 | 需求籤：組 `legend`、欄位標籤、`x/y` 與 `input_hint` 取自 stub；未填欄位有「未填」文字且被 `aria-describedby` 指向 | `AC11.2.1`、`AC11.2.2`、`BR84.2`、`BR84.3` |
| 7 | 更新者三值；`updated_on_behalf_of` 指向**另一組**時顯示該請求組的標題；指向不存在的 key 時降級為「由大腦」 | `BR84.4` |
| 8 | `K4 edit` allow／deny：`Project_Editor` 看到可編輯欄位與 `requirements-save`；`Developer` 看到 `readOnly` 欄位、無 `requirements-save`、有 `requirements-readonly-notice`，且「未填」與更新者照常顯示 | `BR84.7` |
| 9 | 部分失敗：兩欄儲存、其一 `PUT` 回 422 → 失敗欄保留輸入、標「未儲存」與 `detail`；成功欄呈現重讀值 | `AC11.2.3`、`BR84.5` |
| 10 | 重讀失敗：`PUT` 成功但其後的 `GET` 失敗 → 成功欄保留送出值並標「已儲存、重新整理失敗」、總覽「無法取得」、`[重新整理]` 成功後回到正常 | `BR85.6` |
| 11 | 清空：有值欄改空白儲存 → `PUT` 本體為空值且不帶 `on_behalf_of`、不發 `DELETE` | `BR84.6` |
| 12 | 單一系統專案：總覽未填數 ＝ 需求籤「未填」文字數；儲存一欄後切到總覽為 N−1；全填時為 0 且「未填」節點數 0 | `AC11.3.1`–`AC11.3.3`、`BR85.2`–`BR85.4` |
| 13 | 無 `K4 view`：無需求籤、`tab=requirements` 退回總覽、總覽無未填與待補兩區、零次端點 5 請求 | `BR83.2`、`BR85.5` |
| 14 | tablist：方向鍵、Home／End 切籤；`aria-selected`；切籤三次 pathname 不變、`history.length` 不增、`/api/**` 請求數不增 | `BR83.1`、`NFR11.102`、`PPN-05` |
| 15 | 總覽佔位：架構圖「尚無法取得」；記憶摘要籤固定說明且零次 `/api/memory/*`；頁首只有 `[成員]`、無 `[設定]` | `BR86.1`、`BR86.3`、`BR83.3` |
| 16 | 最近變更：標示逐字「只含經大腦、已歸屬系統、且為你自己擁有之圖的變更」；空態逐字「沒有符合條件的變更紀錄」；最多 5 筆、`created_at` 為 null 排最後、同值依 id 由大到小；某系統失敗 → 「部分變更無法取得」 | `BR86.2`、functional-design R-02 |
| 17 | 系統清單 404（非成員或被移出的建立者）→ `project-not-found`，不呈現成「尚無系統」 | `AC12.1.3`（畫面面）、`BR83.4`、W8 第 6 步 |
| 18 | 清單頁扇出：P＝6、端點 2 延遲 1 秒 → 在途最大值**恰 4**；第 5、6 個延遲 3 秒期間該兩列為載入子狀態，最終 6 列皆為「N 個系統」 | `PPN-01`、`PPN-03` |
| 19 | 詳情頁扇出：S＝3、端點 5／7 延遲 → 在途最大值恰 4；前 S 個請求皆為端點 5（系統 id 遞增）、後 S 個為端點 7 | `PPN-01`、`PPN-02` |
| 20 | 卸載：P＝8、端點 2 延遲 2 秒、0.5 秒後導航離開 → 3 秒內端點 2 總數 ≤ 4 | `PPN-04` |
| 21 | console：全部案例中 console 不含 stub 的專案名、系統名、欄位值（獨特字串） | `PPN-18` |

在途計數以 `page.on('request')` 與 `requestfinished`／`requestfailed` 對扇出端點的 URL 樣式（端點 2：`/api/hierarchy/projects/\d+/systems$`；端點 5、7 各自的樣式）維護。斷言「恰 4」而非「≤ 4」：退化成序列時「≤ 4」會靜默通過。

## 四、突變驗證（每項：套用 → 確認紅 → 還原 → 確認綠）

完整 36 道見 `code-generation-plan.md` §五。執行方式：

1. 在工作樹套用突變（只改一處）。
2. 執行該突變對應步驟的**單元指令**（§二），確認指定案例紅燈，記下失敗的測試名稱與訊息第一行。
3. `git checkout -- <該檔>` 還原，重跑同一指令確認綠燈。
4. 把「突變代號、改了哪個檔的哪一行、哪一案紅、還原後綠」寫入 `code-summary.md` 的突變結果表；tcms-test-cases 站將其轉入 `automation-test-plan.md`。

`G7`（`hierarchy_service` 內另寫成員查詢）是靜態 grep 檢查：套用後 `grep -c "NOT EXISTS\|project_members\|ProjectMember" backend/services/hierarchy_service.py` 應大於 0，還原後為 0。

前端 `F1`–`F10` 的指令一律為 `npx playwright test tests/e2e/project-pages.spec.ts`；突變期間不提交、不推送。

## 五、覆蓋率

repo 沒有覆蓋率量測機制（`team.md`：`org.md` 的 80% line coverage「既無法量測也無法強制」）。本單元**不宣稱**百分比，也不弱化該宣稱。實際門檻：

- `team.md` A 規則：本單元不改 `role_permissions` 種子，但改了授權行為 → 以 allow／deny 雙向 `TestClient` 承擔（列舉五身分 ＋ 缺 `K2`、寫入 (a)–(g)）。
- B 規則：兩支修改的列舉端點與三支加守門的寫入端點全部有 `TestClient` 斷言狀態碼與回應內容。
- C 規則：三個新頁面的資料形狀由 e2e 21 案斷言。
- §四 的 36 道突變驗證。

## 六、Mock 與測試資料

- **身分**：測試建立 `User`（`Project_Editor`、`Developer`、一個非 canonical role 的使用者），以 `dependency_overrides[get_current_user]` 注入；角色權限經 `ensure_role_permissions_seeded(db, force=True)`。
- **專案與成員列的構造**（`security-design.md` §二之三）：
  - ① 擁有者且有成員列：經 `MembershipFacade.create_project_with_owner`（同一交易寫入建立者的 `project_admin` 列）。
  - ② 成員：以 ORM 為該使用者加一筆 `ProjectMember(role="member")`。
  - ③ 另一專案的成員：該使用者是**另一個**專案的成員、不是目標專案的成員。
  - ④ 被移出的擁有者：① 建立 → ORM 為第二位使用者寫一筆 `project_admin` → ORM 刪除建立者的成員列（`owner_user_id` 仍是建立者）。
  - ⑤ 零成員列專案的擁有者：以 ORM 直接建 `Project` 不寫成員列。
  - (e') 系統底下的架構圖：以 ORM 建一列 `UserDiagram(system_id=<該系統>)`。
- **既有測試的補參數**：一律 `project_visible=ALWAYS_VISIBLE`（`tests/helpers.py`），語意與修改前相同。
- **列數比較**：(b)／(e)／(e') 在請求前後各以 `db.query(<Model>).count()` 讀 `Project`、`System`、`ProjectMember`、`SystemRequirementField` 四表。
- **log 斷言**：`self.assertLogs("cloud360.hierarchy_facade", level="INFO")`，比對 `actor_user_id=<id>`。
- **前端 stub**：專案名、系統名、欄位值各以獨特假字串（例如 `e2e-project-<字尾>`）產生，供 `PPN-18` 的 console 斷言；延遲以 `page.route` 內 `await new Promise(r => setTimeout(r, ms))` 構造。
- **限制（如實記載）**：e2e 不碰真實後端，前後端形狀一致由 `openapi.json` 漂移閘門與 `check:types` 承擔；SQLite 不驗 PostgreSQL 的索引語法，由 CI 的 `memory-schema` job 承擔；staging 的索引存在與否只能部署後人工 `psql` 驗證。
