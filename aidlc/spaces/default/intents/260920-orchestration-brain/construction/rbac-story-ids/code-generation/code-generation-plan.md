# Code Generation Plan — `U3 rbac-story-ids`（`spec`，S）

<!-- Stage: code-generation（Construction 3.5）· Unit: rbac-story-ids · kind: spec -->

## 〇、本計畫的範圍，與它比上游原始定義寬的那一處

本單元交付 **`K1`–`K4` 四個 story id 的 seed 語意**：`role_permissions` 矩陣由
**308** 列增為 **352** 列（11 角色 × 32 story id）。零端點、零畫面、零容器、
零環境變數、零新依賴。

**改動面比「只改 seed 資料」寬一處**，這是 `nfr-requirements` `[Q2]`=A 的後果：
`backend/services/rbac.py` 的 `ensure_missing_role_permissions` 要改 log 行為
（`SEC-4`）。不寫在這裡的話，實作者會以為 `rbac.py` 不在範圍內。

### 數字全部由腳本從 repo 實算，不照抄上游

| 量 | 值 | 取得方式 |
|---|---|---|
| 既有矩陣 | **308** 列 ＝ 11 角色 × 28 story id（組合完整、無缺漏） | 以 `ast` 解析 `backend/services/rbac_seed_data.py` 的 `DEFAULT_ROLE_PERMISSIONS` |
| 新增 | **44** 列 ＝ 11 × 4 | 同上 |
| 完成後 | **352** 列 ＝ 11 × 32 | 308 ＋ 44 |
| `K3.view` 持有者 | **8**；`K3.edit` **4**；全 `false` **3** | 由 `functional-design` 的 `BR5.1`／`BR5.2` 推導後複算 |
| 有 `K3.view` 無 `K3.edit` 的角色 | **4**（`Developer`／`FinOps_Analyst`／`Security_Reviewer`／`Platform_Owner`） | 腳本重算 |

`units-generation` 逐字要求「施工時須以 `rbac_seed_data.py` 的實際角色數複算，
不得照抄」——已照做。**11 項不變量檢查全部 PASS。**

---

## 一、十二個實作步驟（`test-after`，依 Testing Contract 的 `plan_profile.steps`）

Testing Contract 的 `methodology` 為 **`test-after`**、`test_strategy` 為
**`standard`**。`plan_profile.steps` 的十四個基準步驟中，**六個對本單元不適用**
（`Repository / data access`、`API / endpoint`、`Frontend behavior` 三層各兩步
——本單元零端點、零畫面、不新增任何資料存取函式），已依 stage 檔的
「omitting genuinely inapplicable layers without changing the methodology」省略，
並在此逐一記明理由。

### Step 1 — 驗證既有 test runner，記錄 unit-scoped 指令

對應 `plan_profile.runner_step`，且 `runner_ready_before_first_test: true`。
本單元是 brownfield，runner 已存在，故本步是**驗證**而非建置。
精確指令記於 `unit-test-instructions.md §一`。

- [x] 1a. 確認 `cd backend && python -m unittest discover -s tests -v` 目前全綠（基準）
- [x] 1b. 記錄基準測試數，供 Step 12 的前後比對

**承載**：Testing Contract 的 runner 前置；`team.md ## Testing Posture` 的既成事實

### Step 2 — 資料模型層：`rbac_seed_data.py` 新增 44 列

- [x] 2a. 在 `DEFAULT_ROLE_PERMISSIONS` 清單末端（`]` 之前）插入 44 列
- [x] 2b. 順序為 `K1` 11 列 → `K2` 11 列 → `K3` 11 列 → `K4` 11 列，角色順序沿用
      `CANONICAL_ROLES`（與既有 308 列的排列慣例一致）
- [x] 2c. 旗標值依 `functional-spec.md §一′` 的 44 列表，逐列核對

**承載**：`BR5.1`／`BR5.2`／`BR6.1`／`BR6.2`／`EC-4`／`BR3.4`′　**故事**：`US1.4`、`US9.2`

### Step 3 — 資料模型層的測試（`test-after` 的第一個測試步）

**一支新檔**，同時承載三組斷言——三者都只需要解析
`DEFAULT_ROLE_PERMISSIONS`，分檔會把同一份解析寫三次，而
`team.md` 的「單一真實來源」正是本單元在防的東西（`nfr-design` 的 `D-10`）。

- [x] 3a. `U3-V4`：長度 == 352 **且**組合完整（每個 `(role, story_id)` 恰一列）
- [x] 3b. `U3-V1`：存在角色持有 `A1` view 但不持有 `K3` 任何旗標
- [x] 3c. `U3-V2`：存在角色不持有 `K4` 任何旗標
- [x] 3d. `U3-V3`：每個持有 `K2.edit` 的角色，`K3.edit` 亦為 true
- [x] 3e. `U3-V5`：四個新 id 的 `can_review` 在全部 44 列皆為 false
- [x] 3f. 五條的失敗訊息各自說出它保護哪一條 AC（`nfr-design` 的 `D-12`）
- [x] 3g. 跑綠

**承載**：`U3-V1`–`U3-V5`　**驗證方式**：`nfr-design` 的 `D-10`／`D-12`

### Step 4 — 業務邏輯層：`rbac.py` 的 log 擴充（`SEC-4`）

**這是 `[Q2]`=A 擴進來的改動面**，2 行以內。

- [x] 4a. `ensure_missing_role_permissions`（`rbac.py:110` 附近）的 `logger.info`
      擴充為一行彙總，含被插入的 `(role, story_id)` 配對
- [x] 4b. 層級維持 `INFO`；**不**改為逐列一行（會在既有環境首次啟動刷 44 行）
- [x] 4c. log 只寫 `(role, story_id)`，**不含任何使用者身分**

**承載**：`SEC-4`、`nfr-design` 的 `D-6`　**ADR-0006 面向**：audit logging

### Step 5 — 業務邏輯層的測試：log 斷言（`D-7`）

- [x] 5a. 以 `assertLogs` 捕捉，斷言 `K1`／`K2`／`K3`／`K4` 四個字串都在捕捉到的訊息中
- [x] 5b. 與 Step 3 **同一支測試檔**
- [x] 5c. 跑綠

**承載**：`SEC-4` 的可驗證條件、`nfr-design` 的 `D-7`

### Step 6 — 完整性層：兩份 seed 副本逐列等值測試（`SEC-5`）

- [x] 6a. 解析 `schema_rbac.sql` 的 `INSERT INTO role_permissions` 區塊
      ——**以「`INSERT INTO role_permissions` 之後、下一個裸 `;` 之前」定位，
      不得寫死行號**（本單元自己的 44 列插入就會讓行號位移）
- [x] 6b. 比對 `(role, story_id, can_view, can_edit, can_review)` 的 tuple 集合
- [x] 6c. 失敗時輸出三段 diff：只在 SQL 的列／只在 Python 的列／兩邊都有但旗標不同的列，
      各最多列前 10 筆並附該段總數（`nfr-design` 的 `D-5`）
- [x] 6d. 與 Step 3／Step 5 同一支測試檔
- [x] 6e. 跑綠

**承載**：`SEC-5`、`BR4.4`′、`nfr-design` 的 `D-4`／`D-5`

### Step 7 — 部署資產同步（**blocking**）：`schema_rbac.sql`

- [x] 7a. `INSERT INTO role_permissions` 區塊加同樣 44 列（與 Step 2 逐列一致）
- [x] 7b. 檔頭第 12 行「預設矩陣（308 列）」→ 352
- [x] 7c. **第 761 行不要動成「從 308 改 352」** ——它**現在就寫 `-- 352`** 而
      該檔區塊實算為 308，屬 `6f9227d`（2026-08-23）的既存漂移（`RR-4`）。
      本單元加完 44 列後它**碰巧變成正確**；不得去找一個不存在的「308」

**承載**：`BR4.1`′、`U3-D1`、`project.md ## Mandated`（blocking）

### Step 8 — 部署資產同步（**blocking**）：`DEPLOY.md` 五處

- [x] 8a. `:577`「寫入設計預設矩陣（約 **308** 列，11 角色 × 各 Story）」
- [x] 8b. `:591`「或確認啟動後 `role_permissions` 列數約 308」
- [x] 8c. `:596`「`-- 預期約 308`」
- [x] 8d. `:1259`「Seeds ~**308** `role_permissions` rows.」（**英文段落**）
- [x] 8e. `:1270`「or confirm ~308 rows after backend empty-DB seed」（**英文段落**）

**行號為本計畫撰寫時的實測值，施工前須重新核對**——後兩處在英文段落內，
照中文關鍵詞搜尋會漏掉（這是上游只找到兩處的原因）。

**承載**：`BR4.2`′、`U3-D1`

### Step 9 — `STORY_FEATURE_LABELS` 補四個鍵

- [x] 9a. `user_router.py` 的 `STORY_FEATURE_LABELS`（`:60` 起）新增四個鍵
- [x] 9b. **不**加入 `CATALOG_EXCLUDED_STORIES`（`:90`）——`BR4.5` 已定案照既有
      先例發布（`J3a`／`J3b` 這兩個管理類標籤已經是公開的）
- [x] 9c. 知悉：這四個標籤會出現在**公開的** `/roles/catalog`（`:310`，
      無 `Depends(get_current_user)`）。這是已接受的揭露，不是缺陷

**承載**：`BR4.3`′、`BR4.5`、`SEC-3`　**ADR-0006 面向**：network exposure（適用一處）

### Step 10 — 突變驗證（**本計畫的交付條件**）

每一條斷言都必須**改回錯的行為 → 跑測試 → 確認紅燈 → 還原 → 複驗綠燈**，
並把突變內容與紅燈訊息寫進 `code-summary.md`。

- [x] 10a. `M1`（`U3-V4` 長度）：刪掉任一列 → 長度斷言紅
- [x] 10b. `M2`（`U3-V4` 組合）：把一列的 `story_id` 由 `K4` 改成 `K3`
      → 長度仍 352、**組合斷言紅**。**這一項不可省**：只驗長度會漏掉
      「列數對但組合有缺漏」，而 `BR3.4`′ 逐字要求同時驗兩者
- [ ] 10c. `M3`（`U3-V1`）：把 `SRE` 的 `K3` 列改為 `(True, False, False)` → 紅
- [ ] 10d. `M4`（`U3-V2`）：同上，改 `K4` → 紅
- [x] 10e. `M5`（`U3-V3`）：把 `Project_Architect` 的 `K3` 改為 `(True, False, False)` → 紅
- [x] 10f. `M6`（`U3-V5`）：把任一列第三個旗標改為 `True` → 紅
- [x] 10g. `M7`（`SEC-4` 的 log 斷言）：把 log 改回只記列數 → `assertLogs` 斷言紅
- [x] 10h. `M8`（`SEC-5`）：只改 Python 那份的一列旗標、不動 SQL → 三段 diff 的第三段紅
- [x] 10i. **每次突變後先 grep 確認檔案真的變了**，再跑測試
      （`test-case-authoring.md §5` 記過一次突變沒生效而被誤讀為「測試沒抓到」）

**承載**：`construction.md` 禁止「無論實作對錯都會通過」的測試

### Step 11 — 既有測試保持綠燈

- [x] 11a. `cd backend && python -m unittest discover -s tests -v` 全套跑綠
- [x] 11b. 與 Step 1b 的基準數比對：新增數 == 本單元新增的測試數，**既有項零失敗**
- [x] 11c. 特別確認 `backend/tests/test_rbac.py` 與 `test_collab.py`
      （後者 import `DEFAULT_ROLE_PERMISSIONS`）未被連帶破壞

**承載**：Testing Contract 的 `scope_floor`「Keep the existing test suite green.」

### Step 12 — 文件與追溯

- [x] 12a. `code-summary.md`：改動檔清單、關鍵決定、八項突變的結果、與計畫的偏離
- [x] 12b. `source-manifest.json`：列出本單元建立／修改／刪除的每一條應用程式路徑
- [x] 12c. `traceability.json`：每一條 AC／`BRx.y`／`SEC-*`／`U3-V*` 的 `OK` target
      必須是一個**存在的** workspace 相對檔案路徑

---

## 二、刻意省略的六個基準步驟，逐一記明理由

| `plan_profile.steps` 的項目 | 省略理由 |
|---|---|
| `Project structure and production configuration skeleton.` | brownfield，結構已存在；本單元不新增任何模組或設定檔 |
| `Repository / data access - implement.` ＋ 其測試 | 本單元不新增任何資料存取函式。寫入端 `ensure_missing_role_permissions` **既有**且已被 `database.py:184` 呼叫；本單元只改變它迭代的資料與它的 log |
| `API / endpoint - implement.` ＋ 其測試 | **零端點**（`SEC-1`）。`BR7.1`–`BR7.3` 的 allow/deny 雙向屬 `U3-A1`–`U3-A3`，已具名交接 `U19`（`nfr-design` 的 `D-13`／`D-14`） |
| `Frontend behavior - implement.` ＋ 其測試 | **零畫面**。`STORY_FEATURE_LABELS`（Step 9）是後端字典，不是前端程式 |
| `Environment/build configuration.` | 零新環境變數、零 CI 設定變更（`SEC-2`）。新測試由既有 `unittest discover` 自動撿到 |

**`methodology` 未被改變**：每一個適用的層都是「先實作、再寫並跑該層的測試」
（Step 2→3、Step 4→5），與 `test-after` 一致。

---

## 三、本單元明確不做的事

- 不新增任何 router 檔、service 層讀寫函式或可從 HTTP 觸達的入口（`SEC-1`）。
- 不建表、不加欄、不改既有欄位的型別或約束。
- 不修改既有 308 列中的任何一列。
- 不引入任何套件（`backend/requirements.txt` 不變）、容器、環境變數。
- 不改 CI 設定（`ci.yml` 不變）。
- 不引入 rate limiting（`RR-1` 已定為接受，承接站 `observability-setup`）。
- 不收斂 `database.py:186` 的重複 log（`nfr-design` 的 `D-9`）。
- 不在本單元斷言 `U19` 的測試存在（`nfr-design` 的 `D-14`：那會製造反向依賴邊）。
- 不實作 `U3-A1`–`U3-A3`——它們是對 `U19` 的具名義務，**但須列進
  `code-summary.md` 的已交接項**，避免被讀成本單元漏做。

---

## 四、ADR-0006 四面向（本計畫的落實位置）

| 面向 | 落實步驟 |
|---|---|
| **IAM** | Step 2（預設值）、Step 3（三條可達性保證 ＋ 完整性）、Step 6（兩份副本等值）、Step 10（突變驗證） |
| **Encryption** | 不適用——不新增欄位、不儲存機密值 |
| **Network exposure** | Step 9c（知悉四個標籤經公開端點揭露，已接受；`RR-1` 的 DoS 面已具名並指派） |
| **Audit logging** | Step 4（log 擴充）、Step 5（斷言）、Step 10g（突變）。**仍未處置**：`BR7.1`–`BR7.3` 的拒絕事件稽核由 `H-8` 指派 `U19` |

**PBT hard constraint 判定 N/A**：`rules.md` 實算 `calculation` 類規則為 0；
`BR7.4` 點名的挑選純函式（真正的 PBT 標的，性質為**排列不變性**）是 `U19` 的
交付物，已由 `U3-A3` 具名交接，**不讓它在兩個單元之間掉落**。

---

## 五、故事 ↔ 步驟追溯

| 故事 | 步驟 | 說明 |
|---|---|---|
| `US1.4` | Step 2、3、7、8、9 | `K1` 的 seed 語意與同步義務 |
| `US9.2` | Step 2、3、7、8、9 | `K2` 的 seed 語意與同步義務 |
| （無指派故事） | Step 4、5、6、10、11、12 | `SEC-4`／`SEC-5` 與驗證義務。**`H-10` 已記載** `unit-of-work-story-map.md` 沒有把 `US11`／`US12` 任何一則指給 `U3`，故 `K3`／`K4` 的 seed 在故事層沒有支點——那是上游缺口，不是本計畫漏列 |

---

<!-- 以下為 `bun .claude/tools/aidlc-testing-posture.ts render` 的輸出，逐字貼入。
     `applicable_notes` 的三段 text 是 org.md／team.md／project.md 的
     `## Testing Posture` 段落經 JSON 轉義後的內容；`contract_sha256` 是本計畫
     與 Part 2 派工之間的唯一綁定值（plan-approval guard 比對它）。 -->

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

