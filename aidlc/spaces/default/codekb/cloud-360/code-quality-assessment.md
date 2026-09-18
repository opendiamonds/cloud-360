# Code Quality Assessment — Cloud-360

> 逆向工程產出。基準 commit `c3de2c8`（branch `danniel/fix/production-path-check-noop`，2026-08-17）。
> 技術債以**根因叢集**組織，再以**嚴重度分級**排序 —— 不照掃描流水號排列，
> 因為流水號不表達修復順序，而叢集會。
>
> **測試數字為靜態計數**（`grep -c`），本次未執行後端測試套件與 Playwright。
> 哪些檢查真的跑過、哪些沒跑，逐項列在「本次實測方法」一節。

## 評估摘要

前一版 codekb 的一句話結論是：「這個 repo 的**知識**保存得很好，但**知識的自動執行**很弱 ——
規則寫在文件裡而不是寫在檢查器裡。」

**本次重掃後，這句話需要修正。** 過去一輪的變更集中在**把規則變成檢查器**：

| 面向 | 評價 | 依據 |
|---|---|---|
| 文件品質 | **優於一般水準** | 25 支後端模組中 22 支有載明「職責／安全邊界／契約」的模組級 docstring；`DEPLOY.md`(450)／`LOCAL-DEV.md`(361)／`TESTING.md`(242)；註解說明「為什麼」的比例高 |
| 程式碼衛生 | **優於一般水準** | 全 repo `TODO`／`FIXME`／`HACK`／`XXX` 標記數為 **0**；無被註解掉的死碼區塊 |
| 流程護欄 | **顯著改善** | CI 由「4 job／約 6 個檢查」增為 **4 job／11 個實質檢查步驟**；新增規格漂移、型別漂移、環境設定契約、規格不得外洩四道 |
| **跨語言契約** | **從無到有，但覆蓋 1/10** | `openapi.json → api.d.ts` 建置期契約鏈 + 兩道 CI gate。**但只有 `AdminPage.tsx` 消費** |
| **HTTP 層測試** | **從零到有，但覆蓋 3/45** | `test_user_list_endpoint.py`(282 LOC／17 test) 證明 `TestClient` 採用成本為零 |
| 架構清晰度 | 良好但不均勻 | `wa_*` 與 `review`／`lens` 家族分層乾淨；`user_router`／`collab_router` 仍無 service 層 |
| **一致性機制** | **部分改善** | schema 三源、矩陣雙 seed、角色清單多副本**仍全靠人工**；但新欄位（`last_activity_at`）已正確落三處，證明規則可行 |
| **測試涵蓋** | **不足但方向正確** | 42/45 operation 無 HTTP 層測試；無覆蓋率量測。e2e 由 6 增為 14 case 且已覆蓋 Admin 頁 |
| **靜態檢查** | **前後端仍不對等** | 前端 ESLint + `tsc` 且 CI 強制；後端**零** linter／formatter／type checker |
| 安全預設值 | 需處理 | JWT secret 有程式內預設、預設帳號密碼寫死、一個業務端點無驗證 |

**修正後的一句話結論**：這個 repo 已經開始**把知識寫進檢查器**，而且做得很正確
（規格漂移、型別漂移、環境契約三道都是把過去只寫在文件裡的規則變成 gate）。
**目前的主要問題不再是「沒有機制」，而是「機制已建好但尚未擴散」** ——
型別鏈覆蓋 1/10、HTTP 層測試覆蓋 3/45。同時仍有一塊**結構性盲區**（WebSocket 與 SSE）
是任何既有機制都碰不到的。

## 本次實測方法（哪些是執行結果、哪些是靜態計數）

### 實際執行並取得結果（可引用為執行結果）

| 指令 | 結果 |
|---|---|
| `python3 scripts/validate_repo_contract.py` | **passed**（exit 0） |
| `python3 scripts/validate_env_contract.py` | **passed**（exit 0） |
| `npx eslint .`（於 `frontend/`） | **0 errors, 3 warnings** |

三個 warning 皆為 `react-hooks/exhaustive-deps`：`AssessmentPage.tsx:365`（缺
`detectProviderFromXml`）、`LoginPage.tsx:36`（缺 `requestedRole`）、
`WorkspacePage.tsx:301`（缺 `fetchDiagrams`）。
規則層記為 `:279` 的第三項已位移至 `:301` —— 同一個 warning，行號漂移。

### 未執行（數字為靜態計數，**不得**引用為「通過」）

| 項目 | 未執行原因 |
|---|---|
| `python -m unittest discover -s tests` | 掃描環境的 `.venv` 與系統 python3 皆缺 `fastapi`／`hypothesis`（17 個 import error）。**這是掃描環境限制，不是 repo 問題** —— CI 的 backend job 會安裝完整依賴 |
| `npx playwright test` | 需 `docker-compose.test.yml` 起完整 stack |
| `docker build` | 未執行；Dockerfile 為靜態閱讀 |

因此下列數字皆為 `grep -c` 的靜態計數：**212 個 `def test_`**、**13 個 `@given`**、
**14 個 e2e `test()`**。正確說法是「repo 內有 212 個測試函式」，
**不是**「212 個測試通過」。

## 與 `team.md` 現行記載的落差（如實記載，不逕行修改規則層）

> `aidlc/spaces/default/memory/team.md` 的「既成事實」段落有數項已被本次實測推翻。
> **規則層的修訂須走 practices-discovery 的 affirmation gate，不由 reverse-engineering
> stage 逕行變更**，故此處只如實記載落差，`team.md` 未被本次 stage 修改。
> **下次 practices-discovery 應覆核本節。**
>
> 依賴釘選的落差另見 `dependencies.md` 的「依賴釘選現況」。

| # | `team.md` 現行記載 | 本次實測 | 對下游判斷的影響 |
|---|---|---|---|
| 1 | 「**零 HTTP 層測試**，全 repo 無 `TestClient` 使用」「路由函式本身零覆蓋」 | `backend/tests/test_user_list_endpoint.py`（282 LOC、**17 個 test**、2 個 `TestClient(app)` 建構點），涵蓋 `GET /api/auth/list`、`PUT /{id}/active`、`PUT /{id}/role` **3 個 operation** | `team.md` 自訂規則 **B（新增／修改 HTTP 端點需 `TestClient` 測試）已有現成範本可抄**，不再是零起點。連 `StaticPool` 這個非顯然的前置條件都已解決 |
| 2 | 「`tsc -b` 對前後端 schema 落差**無效**」「`AdminPage.tsx` 的 `DbUser` 是手寫本地 interface，`fetchUserList` 內把 `any` 直接放行」 | `AdminPage.tsx:12-13` 已改為 `components['schemas']['UserSchema']` / `['UserListPage']`；新增 `openapi.json → openapi-typescript → api.d.ts` 契約鏈與**兩道 CI 漂移 gate** | **這條缺口在 `AdminPage` 上已被封住**。但其餘 9 支 fetch 檔仍是舊形狀 —— 評估「有沒有型別保護」時**不能一概而論，要看碰到哪一支檔** |
| 3 | 「CI（`ci.yml`）**四道關卡**依序為 `repo-contract` → `frontend`（lint + `tsc -b` + build）→ `backend`（import smoke + `unittest`）→ `docker-build`」 | **job 數確實仍是 4**（本次以解析 `jobs:` 區塊確認，非目測），但**步驟清單已過時**：實際為 **11 個實質檢查步驟**，新增 `validate_env_contract.py`、`check:types`、`dump_openapi.py --check`、spec-not-served 四道 | 評估「這條變更路徑有沒有守門」時**必須用新的 11 步清單**，用舊的四道會低估既有保護 |
| 4 | 「Playwright **6 case**，涵蓋登入與 RBAC 可視性，**無一導覽至 Admin 頁**」 | **3 個 describe／14 個 `test()`**：身分驗證(4)、RBAC 存取控制(2)、**使用者管理頁 — 最後活動時間與分頁(8)**。第三個 describe 整組導覽至 `/admin/users` | `team.md` 自訂規則 **C（前端資料形狀變更需 e2e 斷言）已被實際執行**。Admin 頁不再是 e2e 空白區 |
| 5 | 「模組級 docstring 覆蓋率 **16/18**」 | **22/25**（分母含 `backend/*.py` 3 支 + `services/*.py` 22 支）。缺的三支是 `main.py`、`database.py`、`auth.py` | 分母變了（模組數由 18 增為 25），比率上升。**`team.md` 記載缺 2 支、實測缺 3 支**（`auth.py` 未被列出） |
| 6 | 「`user_router.py` **831 LOC**」「`collab_router.py` 527 LOC」 | `user_router.py` **884 LOC**（+53）；`collab_router.py` 527 LOC（未變） | 微幅漂移，不影響判斷 |
| 7 | 「Property-based：**5 個檔共 8 個 `@given`**」 | **7 個檔共 13 個 `@given`**：`test_activity`(4)、`test_design_agent`(2)、`test_diagram_builder`(2)、`test_wa_rule_engine`(2)、`test_auth`(1)、`test_collab`(1)、`test_diagram_icons`(1) | PBT 實踐持續擴散，且**新模組 `activity.py` 是最大單一貢獻者**（4 個） |

### 複驗後**仍然成立**的 `team.md` 記載

不是所有記載都過期，下列本次複驗仍為真，下游可放心沿用：

- ESLint `0 errors, 3 warnings`（行號位移一處）
- **backend 無 linter／formatter／type checker**
- **frontend 無 unit／component 測試框架**（`devDependencies` 只有 `@playwright/test`）
- **完全無覆蓋率量測機制**
- 零 `TODO`／`FIXME`／`HACK`／`XXX` 標記
- 角色清單與密碼雜湊的手寫副本
- `user_router`／`collab_router` 無 service 層
- 根目錄無 `.prettierrc`
- secret 掃描與 production 路徑檢查的作用域落差（見叢集 C3）

## 品質正面訊號

這些是需要**保護**的資產，不要在後續重構中弄丟：

1. **零 TODO／FIXME／HACK／XXX 標記**。在 8,700+ LOC 後端與 10,500+ LOC 前端中不常見，
   代表未完成的工作被追到別的地方（issue／spec）而不是留在程式碼裡。
2. **註解解釋「為什麼」而非「做什麼」**。這是本 repo 最突出的特徵，且已成慣例：
   - `requirements.txt` 檔頭解釋為何用 `==` 而非 `~=`
   - `check-api-types.mjs` 解釋這道 gate 在防什麼、為何別的檢查防不住
   - `llm_provider.py` 用 40+ 行解釋為何必須 `del` 而非清空環境變數
   - `user_router.py` 解釋為何 `UserSchema` 的新欄位刻意不設預設值
   - `fetch_icon_from_n8n()` 逐字寫「這條路徑原本靜默 return，是最難查的一種降級」
   - `helpers.py` 解釋為何必須用 `StaticPool`
3. **模組級 docstring 載明契約**。`agent_router.py` 直接寫「契約（前端依賴，請勿變更）」
   並列出 request/response 形狀 —— 在 SSE 缺乏機械檢查的情況下，這是唯一的契約紀錄。
4. **一致的降級策略，且降級留下訊號**。逾時落 `rules_only`、圖示失敗用 fallback **並記
   WARNING**、無 DB lens 回退 JSON。系統面對外部失敗時的行為是**可預測的**。
5. **純函式引擎層 + 政策常數分離**。新模組（`activity`、`prompt_guard`、`llm_limits`）
   一致採用「模組層政策常數 + 純判定函式 + 薄寫入器」形狀，這是它們能有
   property-based 測試的直接原因。
6. **把規則變成檢查器的四道新 gate**（本輪最大進步）：規格漂移、型別漂移、
   環境設定契約、規格不得外洩。
7. **`deploy.yml` 有完整 rollback 路徑**：失敗時還原 last-good、開 revert PR、
   dispatch Deploy Doctor workflow。

## 測試現況

### 規模與工具

| 側 | 位置 | 規模 | 框架 |
|---|---|---|---|
| Backend | `backend/tests/` | 21 測試檔 + `helpers.py` + `__init__.py`，**3,199 LOC**；**212 個 `def test_`（靜態計數）** | Python 內建 `unittest` + `hypothesis` + `unittest.mock` + **`starlette.testclient.TestClient`**（**未使用 pytest**） |
| Frontend e2e | `frontend/tests/e2e/` | 1 檔 `regression.spec.ts`，**490 LOC**；3 describe／**14 個 `test()`（靜態計數）** | Playwright（chromium 單一 project） |
| Frontend unit/component | — | **無** | 無 vitest、無 jest、無 `@testing-library/*` |

**測試 DB 策略**：`tests/helpers.py` 在任何 DB import 前
`sys.modules.setdefault("psycopg2", MagicMock())`，改用 in-memory SQLite；
**必須用 `StaticPool`**（`TestClient` 在另一個執行緒跑 app，預設 pool 會讓它看到
`no such table`）；每 session 以 `ensure_role_permissions_seeded(db, force=True)` 灌 308 列。

### 測試檔規模（LOC／test 數）

`test_diagram_builder.py`(546／18)、`test_user_list_endpoint.py`(282／17)、
`test_llm_provider.py`(243／**25**)、`test_diagram_builder_edges.py`(234／11)、
`test_diagram_icons.py`(196／19)、`test_collab.py`(184／12)、
`test_j3a_view_permission.py`(172／10)、`test_wa_rule_engine.py`(150／9)、
`test_wa_lens_engine.py`(146／8)、`test_activity.py`(142／19)、`test_auth.py`(124／10)、
`test_j5_authz.py`(123／9)、`test_review_authz.py`(93／5)、`test_lens_service.py`(86／6)、
`test_design_agent.py`(85／7)、`test_prompt_guard.py`(71／9)、`test_rbac.py`(56／6)、
`test_collab_suggestions.py`(52／2)、`test_wa_collab.py`(48／3)、`test_llm_limits.py`(41／5)、
`test_review_agent.py`(39／2)

**觀察**：測試最密集的三支（`llm_provider` 25、`diagram_icons` 19、`activity` 19）
**全都是本輪新增或大幅改動的模組** —— 新程式碼的測試密度明顯高於既有程式碼。

### Property-based 測試（ADR-0006 hard constraint）

**現況：7 個檔、共 13 個 `@given`**（前一版為 5 檔 8 個）

| 檔案 | `@given` 數 |
|---|---|
| `test_activity.py` | **4** |
| `test_design_agent.py` | 2 |
| `test_diagram_builder.py` | 2 |
| `test_wa_rule_engine.py` | 2 |
| `test_auth.py` | 1 |
| `test_collab.py` | 1 |
| `test_diagram_icons.py` | 1 |

**約束落點問題（維持不變）**：`project.md` 的 `## Testing Posture` 點名三個必須有 PBT 的
模組 —— **IaC generator、cost calculator、agent routing** —— 這三者在本 repo
**仍無對應實作模組**（對照 `business-overview.md` 的能力表，D 群 IaC 與 C 群成本
目前只存在於權限矩陣）。

因此該 hard constraint 目前**沒有可驗證的落點**：既沒有違反，也沒有被滿足。
**這是規則與實況的落差，不是違規。** 實際存在的 13 個 `@given` 落在圖形組裝、規則引擎、
驗證、共編與活動政策上，是自發的良好實踐而非規則要求。

**給下游的建議**：當 IaC generator 或 cost calculator 真的開始實作時，
這條約束會立刻生效且是 blocking 的，應在設計階段就規劃 property 的定義。

### E2E 涵蓋範圍（本輪顯著擴張）

`regression.spec.ts` 三個 describe、14 個 case：

| describe | case 數 | 涵蓋 |
|---|---|---|
| 身分驗證 | 4 | 登入頁顯示、錯誤密碼被拒、管理員登入進工作區、登出返回登入頁 |
| 角色權限存取控制 (RBAC) | 2 | `Platform_Admin` 看得到系統管理區、`Developer` 看不到 |
| **使用者管理頁 — 最後活動時間與分頁** | **8** | 表格出現最後活動時間欄且有值或破折號；分頁控制顯示總筆數與頁次；切到第 2 頁取得不重複帳號且處置後仍停在第 2 頁；角色調整不影響活動欄；切頁期間分頁控制不消失且鍵盤可達；刪除後仍停在原頁次；超出範圍頁次顯示空態；小螢幕改卡片佈局 |

**全部 case 帶 `@purpose`／`@api`／`@ui`／`@story`／`@pass` 結構化規格註解**，
供 `tcms_validate.py` 機械比對（寫了不存在的端點或路徑會被擋下）。

`ui-regression` workflow **是真閘門**：讀 `pw-report.json` 的 `.stats.unexpected`，
非 0 即 `exit 1`；容忍 `stats.flaky`，`retries: 1`。

**仍存在的缺口**：A1 產圖與 A3 評核這兩條核心價值鏈**沒有任何 e2e 覆蓋**
（皆需 LLM，難以在 CI 穩定執行）。

### 覆蓋率

**完全不存在量測機制。** 無 `.coveragerc`、無 `coverage` 依賴、無 `pytest-cov`、
CI 無 coverage 步驟、無門檻閘門。

`org.md` 為 `feature` scope 宣告的「最低 80% line coverage」目前**既無法量測也無法強制**，
是宣告而非閘門。`team.md` 已如實記載此事並改以三項變更範圍內、二元可判、零工具成本的
規則（A／B／C）作為現階段的實際門檻 —— **本次實測顯示 B 與 C 都已被實際執行**。

### 最重要的測試缺口

**42/45 operation 沒有 HTTP 層測試。**

| Router | operations | 有 HTTP 層測試 |
|---|---|---|
| `user_router` | 16 | **3**（`GET /list`、`PUT /{id}/active`、`PUT /{id}/role`） |
| `collab_router` | 12 | 0 |
| `review_router` | 9 | 0 |
| `lens_router` | 5 | 0 |
| `agent_router` | 2 | 0 |
| root | 1 | 0 |

**這是「尚未擴散」而非「做不到」**：`test_user_list_endpoint.py` 已證明採用成本為零 ——
依賴齊備（`fastapi[standard]` + `httpx` 已在 `requirements.txt`）、
`app.dependency_overrides` 可覆寫 `get_db`／`get_current_user`、
`TestClient(app)` 不觸發 `@app.on_event("startup")` 的 `init_db()`、
`StaticPool` 這個非顯然的前置條件也已解決。

**零測試的關鍵模組**：`review_orchestrator.py` 的狀態機主體（510 LOC）、
`wa_score_service.py`（104 LOC）。其中 **`review_orchestrator` 特別值得注意**：
它是系統中唯一有明確狀態流轉、逾時分支與降級語意的元件，正是最需要測試的形狀 ——
**而它的狀態機正好就是本次發現 `unsupported` 死契約的地方**（見 T-3）。

## Linting 與靜態檢查

| 側 | linter | formatter | type checker | CI 強制 |
|---|---|---|---|---|
| Frontend | ESLint 10 flat config（16 條 error 級 react-hooks 規則） | 無（無 `.prettierrc`） | `tsc -b`（隨 `npm run build`）**+ `check:types` 跨語言契約 gate** | **是**，但 `eslint .` 未加 `--max-warnings 0`，只擋 error |
| Backend | **無** | **無** | **無** | 僅 import smoke + unittest + 規格漂移 gate |

**`org.md` 的落差（仍然成立）**：該層寫「Linter: ESLint, Ruff, golangci-lint 等，
在 CI 執行、失敗阻擋 PR」與「Formatter: Prettier (JS/TS), Black (Python)，配置在 repo root」。
**在本 repo，Python 側完全不成立，前端也沒有 Prettier**。

**ESLint 規則已實質影響程式碼形狀**（不只是風格，是結構約束，違反即 CI 紅燈）：

- `react-refresh/only-export-components` → `AuthContext` 必須拆成 `AuthContext.tsx` + `auth-context.ts`
- `react-hooks/set-state-in-effect`（error） → `AdminPage` 的資料抓取被迫拆成
  純抓取的 `fetchUserList` + 呼叫端 `fetchUsers` + `useEffect` 內的 `cancelled` flag
- `react-hooks/immutability`（error） → state 更新一律回傳新物件

**任何新增前端資料來源都必須沿用此形狀，否則 CI 紅燈。**

## CI/CD 護欄

### `ci.yml` — 4 個 job、11 個實質檢查步驟

- **觸發**：所有 `pull_request` + push 到 `main`／`ut`／`danniel/**`／`chore/**`
- **並行控制**：`concurrency` 取消同 ref 的舊 run
- **權限**：`contents: read`（最小權限，正確）

| Job | # | 步驟 | 檢查內容 |
|---|---|---|---|
| `repo-contract` | 1 | `validate_repo_contract.py` | REQUIRED_FILES/TEXT、record baseline、文件語言、禁止路徑、禁止內容 |
| | 2 | **`validate_env_contract.py`** | **三環境設定分離與完整性（六項）** |
| `frontend` | 3 | `npm ci` | 由 committed lockfile 安裝 |
| | 4 | `npm run lint` | ESLint（只擋 error） |
| | 5 | **`npm run check:types`** | **型別漂移 gate**：重產型別到暫存檔並與 committed 逐位元比對 |
| | 6 | `npm run build` | `tsc -b` typecheck + vite build |
| | 7 | **Spec must not be served statically** | **`find dist -name 'openapi*'` 非空即 fail**（防規格檔被靜態公開） |
| `backend` | 8 | `pip install -r requirements.txt` | — |
| | 9 | Import smoke | `python -c "import main; print(main.app.title)"` |
| | 10 | **`dump_openapi.py --check`** | **規格漂移 gate**：由程式碼重 dump 並與 committed `openapi.json` 比對 |
| | 11 | `python -m unittest discover -s tests -v` | 212 個測試函式 |
| `docker-build` | 12–13 | buildx 建 backend + frontend image | `push: false`，`cache-from/to: type=gha` |

**加上 `ui-regression`（gh-aw，真閘門），PR 上共有 5 個會擋下合併的檢查來源。**

### `deploy.yml` — 3 個 job

- **`deploy`**：self-hosted runner `[self-hosted, linux, x64, cloud360]`、`timeout-minutes: 30`、
  `concurrency: deploy-10-10` 且 `cancel-in-progress: false`（正確 —— 部署不該被中斷）。
  步驟含「Require the secrets that must not default」→ `render-env.sh` 寫 `deploy/.env` →
  compose up → 等本機 frontend → 等公開 hostname（Tunnel）→ 記錄 last-good →
  **`if: always()` 移除 `deploy/.env`**（正確的清理）
- **`rollback`**：還原 last-good、擷取失敗 log、開 revert PR、dispatch Deploy Doctor。
  **權限提升為 `contents: write` + `pull-requests: write` + `actions: write`** ——
  功能上必要，但**可否進一步縮窄尚未被評估過**（見 T-11）
- **`notify`**：Slack（token 未設時整段跳過）

### 11 組 gh-aw agentic workflows

僅 `ui-regression` 是阻擋型；其餘 10 組為提問／自動修／開 issue 型。
完整清單見 `component-inventory.md`。

## 文件品質

| 文件 | LOC | 定位 |
|---|---|---|
| `DEPLOY.md` | 450 | 部署程序；schema 變更時 **blocking** 必須同步 |
| `LOCAL-DEV.md` | 361 | 本機開發；**唯一**記載兩個隱性硬依賴（`claude` CLI 子行程、n8n webhook）之處 |
| `TESTING.md` | 242 | **測試案例格式的唯一真實來源**（六個必填欄位、手動／自動化分流判準、`required-sections` 機械標記） |
| `README.md` | 174 | 專案入口 |
| `CLAUDE.md` | 108 | AI agent 指引 |
| `AGENTS.md` | 25 | 其他 harness 的入口 |

**模組級 docstring 覆蓋 22/25（88%）**。缺的三支是 `main.py`、`database.py`、`auth.py`
—— **全是基礎設施層的關鍵檔**（`database.py` 含 4 支啟動期 schema 補丁與 366 LOC；
`auth.py` 是驗證核心且含 `get_current_user` 的寫入副作用）。

**前一版記載的兩項文件缺陷，本次複驗**：

- `CLAUDE.md` 提到的頂層 `tools/`／`workflows/` 目錄不存在 —— 本次 `CLAUDE.md` 已改寫，
  該敘述已不在（`CLAUDE.md` 由 9,380 B 縮為 108 行）。
- `DEPLOY.md` 的雙語分段 —— 本次未見中英並列的 H2 分段。

## 技術債登記簿

### 分級準則

| 級別 | 定義 |
|---|---|
| **P1** | 已造成或即將造成**正確性或安全性**的實際失效；或會阻擋當前進行中的工作 |
| **P2** | **侵蝕型**風險：不會馬上壞，但隨每次變更放大，且缺乏發現機制 |
| **P3** | 衛生與局部問題：影響可讀性、一致性或單點行為，範圍可控 |

### 叢集 C1 — 「多源真實」（仍是最重要的叢集，但已出現正確樣板）

**根因：同一件事實有多份手寫來源，且沒有任何機制驗證它們一致。**

| id | 級別 | 內容 |
|---|---|---|
| **T-1** | **P1** | **Schema 三處來源不一致，J5 物件僅存在於 runtime 補丁。** `users.authorization_status` 與 `role_authorization_requests` 表**只存在於 `database.py::_ensure_j5_schema()`**，在 `schema_rbac.sql`、`schema.sql`、`DEPLOY.md` 表清單中找不到。新環境用 initdb 建出的 `users` 沒有 `authorization_status` 欄位、`role` 仍 `NOT NULL`；J5 功能能運作純粹依賴啟動時的 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` |
| **T-2** | **P1** | **`schema_rbac.sql` 宣稱可重跑，實際會破壞資料。** 無條件的 `DELETE FROM role_permissions;` 使「重跑腳本取得新 DDL」與「保留 Admin UI 調整」互斥 —— **而 T-1 的修法正好需要重跑** |
| **T-4** | **P2** | **RBAC seed 雙來源、無同步驗證。** 308 列預設矩陣同時存在於 `schema_rbac.sql` 與 `rbac_seed_data.py`。後者 docstring 寫「改 SQL 後重跑產生腳本」，**但該產生腳本不存在於 repo**，CI 也無一致性檢查 |
| **T-5** | **P2** | **`schema.sql` 已嚴重落後**（78 行）。缺 `wa_lenses`、`role_permissions`、J5 全部物件，且 `users.role` 仍 `NOT NULL`。`project.md` 已把它列為「建議一併更新（非 blocking）」，故屬**規則允許的落差**，但任何以此檔推斷 schema 的判斷都會出錯 |
| （附） | **P3** | **角色清單四份手寫副本**：`rbac.py::CANONICAL_ROLES`（正本）、`auth.py::require_any_user`、`user_router.py::ROLE_DISPLAY_NAMES`、`AdminPage.tsx::AVAILABLE_ROLES`（**已與正本順序漂移**）、`schema_rbac.sql` seed |
| （附） | **P3** | **密碼雜湊兩份逐字副本**：`auth.py::get_password_hash` 與 `database.py::hash_password` |

#### 本輪出現的正確樣板（重要，改變了這個叢集的判斷）

**`users.last_activity_at` 的加入有正確落三處**（ORM／`_ensure_last_activity_schema()`／
`schema_rbac.sql`，後者由 523 行成長為 531 行）。

這證明 `project.md` 的 blocking 同步規則**實務上可行**，
**J5 是歷史欠帳而非結構性做不到**。同理，`openapi.json → api.d.ts` 這條鏈是
「跨語言副本 + 一致性檢查」的正確範例，可作為處理其餘副本（尤其 T-4 的矩陣雙 seed）的樣板。

**T-1 與 T-2 仍必須被視為一組**：修 T-1 需要重跑 `schema_rbac.sql`，而重跑會觸發 T-2。

### 叢集 C2 — 「機制已建好但尚未擴散」（本輪的新叢集，投報率最高）

**根因：基礎設施已就位，邊際採用成本遠低於建立成本，但尚未推廣。**

| id | 級別 | 內容 |
|---|---|---|
| **T-6** | **P2** | **產生型別檔採用率 1/10。** `api.d.ts`（2,385 行，兩道 CI gate 保護）**只被 `AdminPage.tsx` 使用**；其餘 9 支做 `fetch()` 的檔仍手寫本地 interface，與後端 `response_model` 無編譯期連結。**「有沒有型別保護」取決於碰到哪一支檔** |
| **T-7** | **P2** | **HTTP 層測試覆蓋 3/45 operation。** 採用成本已被 `test_user_list_endpoint.py` 證明為零（依賴齊備、`dependency_overrides` 可用、`StaticPool` 前置條件已解決、不觸發 `init_db()`）。`review_orchestrator` 的狀態機主體與 4 個 router 完全無覆蓋 |
| **T-8** | **P3** | **產生器版本字串手寫兩份**：`package.json` 的 `gen:types` 與 `check-api-types.mjs:21` 的 `GENERATOR` 常數。腳本註解自承「兩處若不一致，這道 gate 會比對到不同產生器的輸出而誤報」，**無機制鎖住一致** |

**這個叢集的特徵**：每一項的修法都是「多做幾次已經做過的事」，不需要新工具、新依賴或
新決策。**投報率高於 C1 的逐項修補**。

### 叢集 C3 — 「結構性驗證盲區」（無法用既有機制解決）

**根因：既有機制的作用域小於規則所宣稱，或標的根本不在機制的輸入範圍內。**

| id | 級別 | 內容 |
|---|---|---|
| **T-3** | **P2** | **WebSocket 與 SSE 契約無任何機械檢查，且已造成實際的死契約。** `/api/collab/ws/{workspaceId}` 與 10 種 SSE 事件名不在 `openapi.json`，故 `dump_openapi.py --check`／`check-api-types.mjs`／`tcms_validate.py` **三者皆碰不到**。**實測後果**：`AssessmentPage.tsx:632` 與 `:1195` 處理 `unsupported` 事件／狀態，但後端 `review_orchestrator` 的 status 賦值點只有 `pending`／`rules_complete`／`rules_only`／`complete` 四種，**從未寫入 `unsupported`，也從未發出該 SSE 事件**。前端兩段程式碼不可達，而所有檢查全綠 |
| **T-9** | **P2** | **無覆蓋率量測。** `org.md` 的 80% 門檻是宣告而非閘門，既無法量測也無法強制 |
| **T-10** | **P2** | **Python 側無 lint／format／type check。** 前端有 ESLint + `tsc` 且 CI 強制，後端完全沒有對等物 |
| **T-12** | **P2** | **Secret 掃描看不到應用程式碼。** `validate_no_obvious_secrets()` 只讀 `contract_files()`（repo 層必要檔 + record 必要檔 + audit shard），**看不到 `backend/`、`frontend/`、`deploy/`、`schema_rbac.sql`、任何 `.env.example`**。本 repo 唯一的 secret 掃描器結構上看不到程式碼 |
| **T-13** | **P2** | **禁止 production 路徑檢查在 CI 恆為 no-op。** `validate_no_production_config_added()` 以 `git diff --name-only`（unstaged ∪ staged）為輸入，CI 是乾淨 checkout，兩者皆空集合。**註記：目前 branch 名 `danniel/fix/production-path-check-noop` 顯示這一項正在被處理中** |

**T-3 是這個叢集中最值得優先處理的**，因為它不是「規則沒被強制」而是
**「已經真的壞了而且沒人知道」**。修法不能靠既有機制，需要新增：
SSE 事件名的共用常數（前後端各一份 + 一致性測試）、或端點層的串流測試、或 e2e 斷言。

### 叢集 C4 — 「安全預設值與未受保護面」

**根因：開發便利性的預設值被留在了會被部署的路徑上。**

| id | 級別 | 內容 |
|---|---|---|
| **T-14** | **P1** | **JWT secret 有可用的程式內預設值。** 未注入時**靜默**使用該固定字串簽 token —— 任何人都能偽造任意身分的 token。`deploy.yml` 有 secrets 檢查保護 **staging 這一條路徑**；**本機與 `docker-compose.test.yml` 無等價檢查**，且失敗模式是靜默的 |
| **T-15** | **P1** | **預設帳號密碼寫死。** `database.py` 在空 DB 時建立 persona 帳號，密碼為 `<username>123`，**全部 `approved` 且帶正式角色**；另建 `admin`（`Platform_Admin`）。`schema_rbac.sql` 亦 commit 了其 bcrypt hash。任何新環境開機即帶多個可預測憑證的帳號，其中一個是最高權限 |
| **T-16** | **P1** | **WebSocket 端點無驗證。** `/api/collab/ws/{workspace_id}` 是唯一沒有任何 `Depends` guard 的業務端點。連線層不檢查 JWT，任何知道 workspace id 的連線都能收到共編廣播。**且它同時在 T-3 的檢查盲區內** |
| **T-11** | **P2** | **`deploy.yml` rollback job 權限較寬**：`contents: write` + `pull-requests: write` + `actions: write`，在 self-hosted runner 執行。功能上必要（要開 revert PR 並 dispatch workflow），**但可否縮窄（改用 GitHub App token，或把「開 revert PR」拆到最小權限獨立 job）尚未被評估過** —— 不記為已評估無虞 |
| （附） | **P2** | **公開端點可觸發 seed**：`GET /api/auth/roles/catalog`（無驗證）在回應前呼叫 `ensure_role_permissions_seeded(db, force=False)`。實際影響有限（表非空即 return），但這是一條**匿名可達的寫入路徑** |

**與 ADR-0006 security baseline 的關係**：該 ADR 把 IAM、encryption、network exposure、
audit logging 列為 hard constraint。T-14／T-15／T-16 三項都落在 **IAM 與 network exposure**
面向，是這條 hard constraint 目前最明確的未滿足處。

### 叢集 C5 — 「衛生與局部」

| id | 級別 | 內容 |
|---|---|---|
| **T-17** | **P3** | **殘留的一條靜默降級路徑。** `fetch_icon_from_n8n()` 已由 PR #499 為五條降級路徑加上 WARNING，但當回應為 JSON 物件、`_svg_from_entry()` 取不到 SVG、且巢狀 `data` 也取不到時，控制流正常離開 `try` 落到最後的 `return fallback_svg`，**這一條沒有 log**。相較修正前是明顯收斂的殘留面 |
| **T-18** | **P3** | **`frontend/tailwind.config.js` 為死碼。** Tailwind v4 下未被任何 `@config` 載入，實際生效的是 `src/index.css` 的 `@theme`。檔案仍存在會誤導讀者以為它是設定來源 |
| **T-19** | **P3** | **超大檔案**：`AssessmentPage.tsx`(1,861)、`diagram_builder.py`(**1,818，由 288 成長六倍**)、`WorkspacePage.tsx`(1,193)、`wa_rule_engine.py`(973)、`user_router.py`(884)。**性質不同**：`diagram_builder` 與 `wa_rule_engine` 大但高內聚且有測試保護，可接受；`user_router` 大且低內聚（缺 service 層），最值得拆但需先有端點測試 |
| **T-20** | **P3** | **已知 deprecated API**：`main.py:41` 的 `@app.on_event("startup")`；`auth.py:33,35` 的 `datetime.utcnow()`。**因 `fastapi`／`pydantic` 現已精確釘選，不是立即風險**，但會在升版時浮現。**注意 `activity.py` 已正確使用 timezone-aware 寫法**，同一件事兩支模組做法不一致 |
| **T-21** | **P3** | **`passlib[bcrypt]` 疑為未使用依賴**：`auth.py` 直接 `import bcrypt`，全樹未見 `passlib` import。需確認是否可移除（本次未做刪除驗證） |
| **T-22** | **P3** | **環境不一致**：PostgreSQL 15（本機 `docker-compose.yml`）vs 16（staging 與 CI 測試 stack） |
| **T-23** | **P3** | **`@types/react-router-dom@^5.3.3` 版本錯配**：搭 `react-router-dom@^6.22.0`；v6 起自帶型別，此套件多餘且描述 v5 API |
| **T-24** | **P3** | **模組 docstring 缺 3 支關鍵基礎設施檔**：`main.py`、`database.py`、`auth.py` |

### 級別索引

| 級別 | 項目 | 數量 |
|---|---|---|
| **P1** | T-1、T-2、T-14、T-15、T-16 | 5 |
| **P2** | T-3、T-4、T-5、T-6、T-7、T-9、T-10、T-11、T-12、T-13 | 10 |
| **P3** | T-8、T-17、T-18、T-19、T-20、T-21、T-22、T-23、T-24 | 9 |

## 修復順序建議

排序依據是「解鎖後續工作的能力」與「阻止債務再生」，不是嚴重度單一維度。

**第一梯次 — 已經壞了但沒人知道**

1. **T-3 的具體實例**：修掉 `unsupported` 死契約。要嘛後端補上該狀態的產生邏輯，
   要嘛移除前端的兩段不可達分支與後端封存查詢中的 vestigial 值。
   **同時決定 SSE 事件名的契約承載形式**（共用常數 + 一致性測試，或端點層串流測試）
   —— 只修實例不修機制的話，下一個事件名還會再壞一次。
2. **T-1 + T-2 一起處理**（不可拆）。在 `schema_rbac.sql` 建立一條**不破壞資料的
   schema 演進路徑**：把無條件的 `DELETE FROM role_permissions;` 改為冪等的 upsert，
   或把 seed 與 DDL 拆成兩支腳本。完成後把 J5 物件補進 `schema_rbac.sql` 與 `DEPLOY.md`。
   **這是所有觸及 `users` 表的工作的前置條件**，且 `last_activity_at` 已證明流程可行。

**第二梯次 — 擴散既有機制（投報率最高，無需新工具或新決策）**

3. **T-7**：把 `TestClient` 測試推到其餘 router。建議順序依風險：
   `review_orchestrator` 的狀態機（最複雜、有降級語意）→ `collab_router`（12 個 operation
   且含無授權的 WebSocket）→ `lens_router`／`agent_router`。
4. **T-6**：把產生型別接到其餘 9 支 fetch 檔。每接一支就少一個「後端加欄前端漏接」的面。
5. **T-4**：寫一個 CI 步驟比對 `schema_rbac.sql` 的 308 列 INSERT 與 `rbac_seed_data.py`
   的 308 筆 tuple。**這比補上那支「不存在的產生腳本」更直接**，且能立刻阻止漂移。
   `check-api-types.mjs` 是現成的樣板。
6. **T-8**：把產生器版本字串收斂為單一來源（例如由 `package.json` 讀出）。

**第三梯次 — 安全預設值**

7. **T-14**：移除 `JWT_SECRET` 的程式內預設值，改為缺少時**啟動失敗**（fail fast）。
8. **T-15**：把 persona 帳號的 seed 改為需明確開關（環境變數）；`admin` 預設密碼改為
   啟動時產生並要求首次登入變更，或同樣改為必須注入。
9. **T-16**：為 WebSocket 端點加入 JWT 驗證（連線時以 query param 或 subprotocol 傳 token）
   並檢查該使用者對 workspace 的存取權。**與 T-3 一併處理較經濟**（兩者標的相同）。

**第四梯次 — 補上缺席的機制**

10. **T-12 + T-13**：擴大 `validate_no_obvious_secrets()` 的作用域到應用程式碼；
    修正 production 路徑檢查的 diff 基準使其在 CI 真的生效
    （**後者似乎正在進行中**，見目前的 branch 名）。
11. **T-10 + T-9**：加入 Ruff（lint + format）與 coverage 量測到 backend CI job。
    兩者都是設定檔層級的工作，成本低、立刻讓 `org.md` 的宣告變成可執行的閘門。
12. **T-11**：評估 rollback job 的權限能否縮窄。

**第五梯次 — 衛生**

13. T-17（補上最後一條靜默路徑的 log）、T-18（刪掉死碼 `tailwind.config.js`）、
    T-21（移除 `passlib`）、T-23（移除 `@types/react-router-dom`）、
    T-20（換掉 deprecated API，並讓 `auth.py` 與 `activity.py` 的時間處理一致）、
    T-22（統一 PostgreSQL 版本）、T-24（補三支基礎設施檔的 docstring）。
14. T-19 的 `user_router.py` 拆分（抽出 service 層）—— **前置條件是 T-7 先為它建立
    端點測試保護**；重構與功能變更混在同一個 PR 不可驗證。
15. T-5（補齊或明確廢止 `schema.sql`）—— 若 `schema_rbac.sql` 已是唯一部署腳本，
    **刪掉 `schema.sql` 比維護它更誠實**。
