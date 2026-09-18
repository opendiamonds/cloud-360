# Team Practices — Cloud-360（Lead Integration，practices-discovery re-run）

> 本檔為 Step 5 Lead Integration 定稿版，整合草稿、三位 support agent 的盲審
> contribution、與人工訪談（`practices-discovery-questions.md` Q1–Q6）的定案結果。
> 核可後將**整段替換** `aidlc/spaces/default/memory/team.md` 的五個對應 section
> （非合併），因此既有內容逐字保留、只做延伸與空白 section 補完。
>
> **記載姿態（Q1=C 分層寫）**：本檔只寫**真實成立的現況**——已落地的實務、已查證
> 的事實、已由訪談定案的新規則。凡是「規則宣稱大於實際承載機制」的落差，如實記載
> 落差本身（不美化、不假裝已解決），需要補上承載機制的待辦另列於
> `discovered-rules.md`，不在本檔混入未實現的理想。

## Way of Working

### Branch 命名

所有新建分支必須遵循 `<uploader>/<type>/<slug>`：

- `<uploader>`：開分支者慣用的英文小寫 handle（建議與 GitHub username 一致）。Danniel 一律用 `danniel`。
- `<type>`：**一律英文小寫**，限定 `feat`（新功能）、`fix`（bug 修復）、`docs`（純文件／spec）、`chore`（CI、依賴、版本維護）、`refactor`（行為不變的重構）、`test`（測試補強）。
- `<slug>`：英文小寫、連字號分隔、3–5 個詞概述變更目的。

合規範例：`danniel/feat/rbac-permission-matrix`、`danniel/fix/agent-routing-bug`、`danniel/chore/dependency-bump`。
不合規：`feat/aidlc-rules`（缺 uploader）、`Danniel/feat/foo`（大寫）、`danniel/feature/foo`（type 不在清單）、`danniel/feat/foo_bar`（底線非連字號）。

不溯及既往：本規則建立前的既有分支保留原名直到合併。不適用於 `dependabot/*`、`release/*` 等自動產生的分支。

執行 `git checkout -b` / `git switch -c` 前必須先確認 branch name 合規；使用者若下達衝突指令，先提醒衝突並請使用者確認。

**既有分支命名先例**：`git branch -a` 顯示既有 remote 分支多數已呈現 `<name>/<type>/<slug>` 形狀（如 `doreen/feat/a1-nl-to-architecture`、`luojingting/feat/a3-well-architected-review`、`luojingting/fix/a1-issue-fixes`），與現行規則精神一致，只是 uploader 不限 `danniel`。視為既有規則的自然先例，規則本身不需修改。

### Commit message 與 PR 標題

一律使用**繁體中文**，包含 type、描述、body 與 PR 標題（ADR-0010）。格式沿用 conventional commits，但 type 改為中文：

```
<type>(<scope>)<!>: <描述>

<body（可選，繁體中文）>

<footer（可選）>
```

`<type>` 限定下列中文詞，英文對應僅供理解與 branch 命名換算，**不得**寫進 commit message：

| 中文 type | 英文對應 | 用途 |
|---|---|---|
| `功能` | feat | 新功能 |
| `修正` | fix | bug 修復 |
| `文件` | docs | 文件變更（純 markdown / spec） |
| `格式` | style | 純格式調整，不影響行為 |
| `重構` | refactor | 重構，行為不變 |
| `效能` | perf | 效能改善 |
| `測試` | test | 測試補強或修正 |
| `建置` | build | 建置系統、依賴升級 |
| `整合` | ci | CI / CD 設定與 workflow |
| `雜項` | chore | 其他雜項維護 |
| `還原` | revert | 還原先前的 commit |

維持英文不翻譯的部分（識別字或被機器解析的 token）：`<scope>`（如 `(rbac)`、`(deploy)`、`(frontend)`）、`BREAKING CHANGE:` footer 與 breaking 標記 `!`、trailer（`Co-Authored-By:`、`Signed-off-by:`、`Refs:`）、內文中的程式碼／指令／檔名／專有名詞。

範例：

```
功能(rbac): 新增角色與故事的權限矩陣
修正(deploy): 讓 cloudflared 以 uid 1000 讀取 0400 憑證
整合(ci): 新增 Lint Fixer agentic workflow
```

**Branch type 與 commit type 已解耦**：branch 名稱維持英文 type（中文在 `gh` CLI、URL 與部分 CI 工具需 percent-encoding），commit 用中文 type，兩者以上表換算。

```
branch：danniel/feat/rbac-permission-matrix
commit：功能(rbac): 新增角色與故事的權限矩陣
```

適用於人工 commit、AI agent 產生的 commit／PR 標題、CI 自動產生的 commit（`deploy.yml` 的 revert PR、gh-aw workflow 的 push）。不溯及既往；不適用 `dependabot/*` 等第三方工具與 git 預設的 merge commit 訊息。

中文 type 無法被 conventional-commits 生態的預設 parser 解析；未來若接 changelog 產生器需自訂 preset，可用 regex：

```
^(功能|修正|文件|格式|重構|效能|測試|建置|整合|雜項|還原)(\([a-zA-Z0-9_,\-\/\.]+\))?!?: .+
```

### PR 合併方式（Q2 定案：視情況並用）

`org.md` 宣告「squash-merge Bolt branches 進 `ut`」，但既有 PR（`#465`、`#433`、`#431`、`#420`、`#418`、`#477`）實測皆以 **`Merge pull request` 合併 commit** 進入歷史，非 squash。訪談定案為 C：**依分支性質分流**，不是全盤改採一種策略：

- **Construction Bolt 分支**：走 **squash-merge**，每個 Bolt 對應 `ut` 上一個 commit，貼合 `org.md` 精神與 delivery-planning 的 Bolt 序列。
- **一般 feature／fix／chore PR**（本專案目前既有 PR 皆屬此類，尚未有正式 AI-DLC v2 Bolt 分支落地）：維持 **merge commit**，如實延續既有實務。

規則生效前的 PR 標題中英混用（如 `feat(A1): improve workspace chat UX`）不溯及既往；規則生效後的 PR 標題合規率留待下次 practices-discovery 覆核。

## Walking Skeleton

**Q3 定案：`skeleton: off`。**

初答為 C（`skeleton: on`），經訪談內成本確認後改為 A。理由：本專案自 baseline 起已有可運行的 backend／frontend、CI（四道 gate）、自動部署（含 rollback 自動化）與 10 組 agentic workflow，管線成熟度已超過「需要走 skeleton 驗證端到端管線是否打通」的階段；本 intent（`users` 表加最後活動欄位並顯示於 Admin 表格）是在既有頁面加欄，不是打通新架構，沒有 bootstrap 標的。第一個 Bolt（若本 intent 走 Construction）照常跑，不需額外一輪 gate 與儀式。

若未來個別大型 intent（例如引入全新技術層）需要 skeleton 驗證，可在該 intent 的 scope 檔逐案開啟，不需改動團隊預設值。

## Testing Posture

### 既成事實

- **Backend 測試框架**為 Python 內建 `unittest` + `hypothesis` + `unittest.mock`，**未使用 pytest**。CI 以 `python -m unittest discover -s tests -v` 執行（`ci.yml`）。測試 DB 策略見 `backend/tests/helpers.py`：在任何 DB import 前 `sys.modules.setdefault("psycopg2", MagicMock())`，改走 in-memory SQLite，每 session `ensure_role_permissions_seeded(db, force=True)`。規模：`backend/tests/` 14 個測試檔 + `helpers.py` + `__init__.py`。
- **Frontend e2e** 為 Playwright（chromium 單一 project），涵蓋登入與 RBAC 可視性共 6 case，且無一導覽至 Admin 頁；`ui-regression` gh-aw workflow 每 PR 對短生命週期 stack 執行並回報 Kiwi TCMS。**這是真閘門**：`post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`；容忍 `stats.flaky`，`retries: 1`。
- **Frontend 完全沒有 unit／component 測試框架**：`frontend/package.json` 的 `devDependencies` 只有 `@playwright/test`，無 vitest、無 jest、無 `@testing-library/*`；`scripts` 只有 `test:e2e`。前端的唯一自動化驗證層就是那 6 個 e2e case。
- **Property-based testing**：5 個檔共 8 個 `@given`（`test_diagram_builder` 2、`test_design_agent` 2、`test_wa_rule_engine` 2、`test_auth` 1、`test_collab` 1），皆落在純函式模組，屬自發良好實踐。`project.md` ADR-0006 點名的三個 hard-constraint 落點（IaC generator、cost calculator、agent routing）在本 repo **尚無對應實作模組**，故該約束目前對 repo 現況為 N/A（非豁免、非違反），本 intent 亦不觸及。
- **完全沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）。`org.md` 宣告的「最低 80% line coverage」目前**既無法量測也無法強制，是宣告而非閘門**——這是誠實記載，不是待補的美化用語，也不在本檔弱化 `org.md` 的宣告（弱化會與 strict-additive 矛盾）。真正可執行的收斂方式見下方「本輪新增規則」。
- **零 HTTP 層測試**：全 repo 無 `TestClient` 使用。`review_router.py`、`agent_router.py`、`lens_router.py` 完全無測試檔引用；`user_router.py` 僅 3 個私有 helper（`_build_role_catalog`、`_hard_delete_user`）被 `test_j5_authz.py` 直接呼叫，**路由函式（HTTP 層、`Depends` 鏈、`response_model` 序列化）本身零覆蓋**。
- **測試落點沿架構分層，非隨機分布**：engine／service 類純函式模組（`wa_rule_engine`、`wa_lens_engine`、`diagram_builder`、`rbac`、`lens_service`、`collab_suggestions`、`llm_limits` 等）皆有對應測試檔；router（HTTP 層）類模組（`review_router`、`agent_router`、`lens_router`、`user_router`）幾乎無測試涵蓋。團隊會為可直接呼叫的純函式寫測試，不為需要組裝請求的路由寫測試。
- **正面實務（已落地，非待 affirm 的理想）**：近四次功能 commit 皆在同一個 commit 內附上後端測試，非事後補——`b19e0d6`（`test_wa_lens_engine.py` +48、`test_wa_rule_engine.py` +16）、`92f7f29`（`test_diagram_builder.py` +51）、`a4de2c3`（`test_collab_suggestions.py` +52、`test_llm_limits.py` +41、`test_wa_collab.py` +48）、`b77d456`（`test_wa_rule_engine.py` +34）。`org.md` 的「tests written alongside code」在本專案是已落地的實務，但邊界要一併寫清楚：這些測試無一落在 router 層，無一落在前端。
- **既有授權測試皆在 service 層**：`test_rbac.py`（`test_user_can`、`test_user_can_arch`、`test_permissions_map_for_role`）、`test_j5_authz.py`（`test_pending_user_can_is_false`、`test_null_role_cannot`、`test_project_admin_cannot_approve_owner` 等）、`test_review_authz.py`，皆非 HTTP 層測試。

### 本輪新增規則（Q4 定案：A + B + C，D 不採）

依據：本 intent 的六道現有 CI 閘門（`repo-contract`、frontend lint、`tsc -b`、backend import smoke、backend `unittest`、`ui-regression`）逐一查證後，**對「後端漏欄位、序列化成 null、前端渲染成空白」這條失敗路徑全部無效**——不是覆蓋率不足的程度問題，是這條變更路徑上沒有任何自動化斷言存在的有無問題。三項零新依賴的測試底線本輪起生效：

- **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 `role_permissions` 預設值變更，必須有測試同時驗證「該角色能做到」與「其他角色做不到」。零新依賴，直接擴充既有 `test_rbac.py`／`test_j5_authz.py` 形狀。本 intent 的 `Security_Reviewer` 取得 `J3a:view` 即屬此類。
- **B — 新增或修改 HTTP 端點需 `TestClient` 測試**：斷言其 status code 與 `response_model` 的欄位集合。採用成本為零——`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，`starlette.testclient.TestClient` 前置條件已滿足；新測試檔放進 `backend/tests/` 即被現有 `python -m unittest discover -s tests` 撿到；`get_db`（`database.py:31`）與 `get_current_user`（`services/auth.py:39`）為穩定的模組層函式，可用 `app.dependency_overrides` 覆寫，且 `require_story_action` closure 依賴上述兩者，真實 `user_can` 授權路徑仍會被執行；以 `TestClient(app)` 直接使用不觸發 `@app.on_event("startup")` 的 `init_db()`，不需要真實 DB。
- **C — 前端資料形狀變更需 e2e 斷言**：例如本次 Admin 表格加欄，須新增至少一個 Playwright case 斷言表頭出現該欄位、且至少一列顯示值或既定的「從未」佔位。用既有 Playwright，不需新依賴，且是目前**唯一**能碰到 `AdminPage` 的自動化層。
- **D（不採用）— 引入前端 unit／component 測試框架**：需新增依賴（Vitest 或類似），成本明顯較高，且屬獨立的工具鏈決策，不由本次加欄 feature 夾帶。C 項的 e2e 斷言已覆蓋本 intent 的加欄驗證需求。

### 80% 覆蓋率門檻的定位

**維持 `org.md` 原文，不在本檔弱化或改寫其宣稱**（把「80% 是目標不是閘門」寫進 `team.md` 會構成 `team.md` 弱化 `org.md` 的矛盾，屬 §13 learning admission 應擋下的形狀）。如實記載目前無法量測、無法強制的現況（見上），並以上述 A/B/C 三項變更範圍內、二元可判、零工具成本的規則作為現階段的實際門檻——它們衡量的是 PR 作者能控制的增量，而非量不到的存量百分比。導入 `coverage.py` 量測工具列為待補承載機制（見 `discovered-rules.md`）。

## Deployment

延伸 `org.md` 與 `project.md` 已定案的部署模型（Construction／Operations 連續、deploy-on-merge 至 `192.168.10.10`，見 ADR-0007／ADR-0008），記載團隊層級的執行細節：

- **CI（`ci.yml`）四道關卡**依序為 `repo-contract` → `frontend`（lint + `tsc -b` typecheck + build）→ `backend`（import smoke + `unittest`）→ `docker-build`（buildx 建兩個 image，`push: false`）。四者皆為 PR 與 push 到 `main`／`ut`／`danniel/**`／`chore/**` 時觸發，`concurrency` 會取消同 ref 的舊 run。
  - **`tsc -b` 對前後端 schema 落差無效**：`AdminPage.tsx` 的 `DbUser` 是手寫本地 interface，`fetchUserList` 內 `const data = await res.json(); return data;` 把 `any` 直接放行為 `DbUser[]`。前端型別與後端 `UserSchema` 無任何編譯期連結——這道 typecheck 看似有型別保護，實際對「後端加欄、前端漏接」這類變更無效，必須被誠實記載，不能被誤當成已有的護欄。
- **`deploy.yml`** 於 PR closed（merge）到 `ut` 或手動 `workflow_dispatch` 觸發，跑在自架 runner（`[self-hosted, linux, x64, cloud360]`），30 分鐘逾時，`concurrency: deploy-10-10` 且 `cancel-in-progress: false`（部署中不可被新 run 打斷）。
- **Rollback 已具備自動化路徑**：部署失敗時，`rollback` job 會還原 last-good、開 revert PR、dispatch Deploy Doctor agentic workflow 自癒。此 job 權限提升為 `contents: write` + `pull-requests: write` + `actions: write`——**這是刻意放寬（功能需要），但可否進一步縮窄（改用 GitHub App token，或把「開 revert PR」拆到最小權限獨立 job）尚未被評估過**，不記為已評估無虞。
- 部署後會清理 `deploy/.env`（避免機敏檔留在 runner 上）。
- `POSTGRES_PASSWORD`／`JWT_SECRET` 缺少時，`deploy.yml` 的「Require the secrets that must not default」步驟會讓部署失敗——**但這道檢查只保護 staging 部署這一條路徑**；本機開發、`deploy/docker-compose.test.yml`（`ui-regression` 每個 PR 自動起的短生命週期 stack）等其他啟動方式沒有等價檢查。

### 已知的規則宣稱與機制落差（如實記載，不美化）

`project.md ## Forbidden` 現有兩條規則的宣稱強度高於機制的實際強度：

- **Secret 掃描**：`validate_no_obvious_secrets()`（`scripts/validate_repo_contract.py:347`）只讀取 `contract_files()`（12 個 repo 層必要檔 + baseline record 必要檔 + audit shard）。`backend/`、`frontend/`、`deploy/`、`schema_rbac.sql`、任何 `.env.example` 都不在其中——本 repo 唯一的 secret 掃描器結構上看不到應用程式碼。
- **禁止 production 路徑**：`validate_no_production_config_added()`（同檔 `:330`）以 `git diff --name-only`（unstaged ∪ staged）為輸入。CI 是乾淨 checkout，兩者皆為空集合，**這道檢查在 CI 恆為 no-op**，只在本機有未提交變更時才作用。

這兩項不是「缺工具」，是既有機制的實際作用域小於規則所宣稱——修復方式（擴大掃描器作用域、修正 diff 基準）列為待補承載機制（見 `discovered-rules.md`），本輪不逕自變更腳本行為（未經訪談定案）。

## Code Style

我們依循既有的語言慣例與已生效的檢查工具，並如實記載工具鏈的落差：

- **Frontend**：ESLint 10（flat config：`js.recommended` + `tseslint.recommended` + `react-hooks.flat.recommended`（`eslint-plugin-react-hooks@7.1.1`，16 條 error 級規則：`rules-of-hooks`、`static-components`、`use-memo`、`preserve-manual-memoization`、`immutability`、`globals`、`refs`、`set-state-in-effect`、`error-boundaries`、`purity`、`set-state-in-render`、`config`、`gating`；另 `exhaustive-deps`、`incompatible-library`、`unsupported-syntax` 為 warn 級）+ `react-refresh.vite`）+ `tsc -b`（隨 `npm run build` 觸發型別檢查）。CI 只擋 **error**：`npm run lint` = `eslint .`，未加 `--max-warnings 0`，現況為 `0 errors, 3 warnings`（`AssessmentPage.tsx:365`、`LoginPage.tsx:36`、`WorkspacePage.tsx:279` 皆為 `exhaustive-deps`），這是已知既存狀態，不代表「lint 沒在跑」。**根目錄無 `.prettierrc`**——`org.md` 預設的 Prettier 從未被引入，非「引入後又拿掉」。

- **前端：lint 規則造成的結構約束**（不是團隊的美學選擇，而是 lint 規則的直接後果，違反即 CI 紅燈；升級或更換 lint 套件時本節同步重審）：
  - **Context 拆兩檔**（`react-refresh/only-export-components`）：Provider 元件放 `.tsx`，型別與 hook 放同名 `.ts`。現例 `AuthContext.tsx` + `auth-context.ts`。
  - **資料抓取拆兩層**（`react-hooks/set-state-in-effect`，error）：拆成①純抓取函式（不碰 state，回傳資料）②呼叫端在 `.then/.catch/.finally` 更新 state ③`useEffect` 內用 `cancelled` flag 防卸載後 setState。現例 `AdminPage.tsx` 的 `fetchUserList` / `fetchUsers` / `useEffect`。任何新增前端資料來源都必須沿用此形狀。
  - **不可就地修改物件**（`react-hooks/immutability`，error）：state 更新一律回傳新物件（現例 `setUsers((prev) => prev.map(...))`）。

- **前端 API 呼叫現況**：URL 組裝已集中於 `src/config/api.ts`（`apiUrl()` / `wsUrl()`），52 處 `fetch()`（10 支檔）一致沿用。未集中的是認證標頭（40 處手寫 `Authorization: Bearer`）、401 處理、錯誤解包與回應型別。新增呼叫點時沿用現有形狀（`apiUrl()` + 手寫 header + `res.ok` 判斷 + `data.detail` 取錯誤訊息），不要單點自創抽象。

- **Backend（既成事實，非理想）**：完全沒有 linter、formatter、type checker（無 Ruff、無 Black、無 mypy／pyright）。`org.md` 宣告的「Formatter: Black (Python)」「Linter: Ruff 等，CI 強制」在 backend 側不成立，這不是團隊決議不用，是尚未補上，導入方式列為待補承載機制（見 `discovered-rules.md`）。
- **Backend 依賴 100% 未 pin、無 lockfile**：11 個 `requirements.txt` 依賴（`fastapi[standard]`、`pydantic`、`uvicorn`、`httpx`、`python-dotenv`、`sqlalchemy`、`psycopg2-binary`、`passlib[bcrypt]`、`bcrypt`、`pyjwt`、`claude-agent-sdk`）加 `hypothesis` 共 12 行，無一有版本約束，CI／Docker build／staging 部署三處各自解析當下最新版，可能彼此不同。Frontend 對照組有已 commit 的 `package-lock.json`，CI 用 `npm ci`。此為既成事實，導入 pin／lockfile 的具體做法未經本輪訪談定案，列為待補承載機制。
- **零 TODO／FIXME／HACK／XXX 標記**（全 repo），且無死碼區塊——這是應該保護、不應在後續規範中弱化的既有紀律。
- **模組級 docstring 覆蓋率 16/18**：其中 router 類多為單行摘要（如 `user_router.py` 僅單行功能清單，無安全邊界、無契約段），`agent_router.py` 的「契約（前端依賴，請勿變更）」是最完整的樣板。建議追認為既成慣例，新模組沿用 `agent_router.py` 的樣板深度。

- **命名慣例**（既成事實）：
  - Python 檔名／router：`snake_case.py`；router 一律 `*_router.py`；WA 引擎一律 `wa_*` 前綴——一致，追認為規則。
  - React 命名：元件與頁面 `PascalCase.tsx`；頁面一律 `*Page.tsx`——一致，追認為規則。
  - 非元件 TS 檔名：**已知不一致**（`auth-context.ts` kebab-case vs `useCollaboration.ts`／`diagramViewer.ts` camelCase）。新規則：hook 檔沿用 `use*.ts`，其餘 camelCase；`auth-context.ts` 為既存例外，不強制改名。
  - logger 命名：**已知不一致**（11 支模組用 `logging.getLogger("cloud360.<module>")`，5 支用 `__name__`：`collab_router`、`design_agent`、`agent_router`、`diagram_builder`）。新模組一律 `"cloud360.<module>"` 形式；本 intent 觸及的 `user_router.py` 已是此形式。
  - `HTTPException` 呼叫風格：**已知不一致**（`user_router.py` 內同檔混用 12 處具名引數 `status_code=`、17 處位置引數）。記為已知不一致，不強制統一（純格式改動的收益低於 diff 噪音）；新程式碼沿用所在函式鄰近寫法。

- **後端分層**：分層成熟度依模組家族而異，這是已知且刻意保留的現況，不是待修的違規。
  - `review` / `lens` / `wa_*` 家族：router → orchestrator/service → 純函式引擎 → model，三層清楚；純函式引擎層（`wa_rule_engine.py`／`wa_lens_engine.py`／`diagram_builder.py`）不讀 DB、不連外，是 property-based 測試的實際落點。
  - `user` / `collab` 家族：無 service 層，商業邏輯直寫 handler（`user_router.py` 831 LOC、`collab_router.py` 527 LOC）。
  - 規則依改動落點分流：**新模組／新業務邏輯**一律走三層形狀，純運算下沉到不讀 DB 的函式；**修改 `user_router.py`／`collab_router.py`** 就地沿用既有形狀，不趁機夾帶 service 層抽取（這兩支目前無 HTTP 層測試保護，重構與功能變更混在同一個 PR 不可驗證，抽 service 層是獨立任務，前置條件是先有端點測試）；不得在這兩支之外新建「router 直寫商業邏輯」的模組。

- **錯誤處理形狀**（既成事實）：`user_router.py` 有 0 個 `try/except`，全部靠 `raise HTTPException` 快速失敗；`review_router.py`（4 個）、`collab_router.py`（5 個）的 `try/except` 都用在外部呼叫邊界。既有慣例：DB／驗證錯誤直接 `raise HTTPException`，不 try/except 吞掉；`try/except` 只用在外部依賴邊界（LLM、webhook、檔案）且必須降級或記 log，不得靜默。與 `construction.md` 的「Errors must be surfaced」一致。

- **單一真實來源**：當同一份事實已存在於程式中（角色清單、權限矩陣、schema 欄位），新增第二份物化前必須先確認是否有既有常數或 API 可直接使用。若確實無法避免（如跨語言邊界），新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試；無法寫測試的副本不新增。
  - 已知既有副本與正本（既成事實，本輪不強制立即消除，收斂方式待後續評估）：角色清單正本 `services/rbac.py::CANONICAL_ROLES`；副本 `services/auth.py::require_any_user`（11 個字串手寫 allowlist）、`services/user_router.py::ROLE_DISPLAY_NAMES`、`frontend/src/pages/AdminPage.tsx::AVAILABLE_ROLES`（已與正本順序漂移）、`schema_rbac.sql` seed。密碼雜湊正本 `services/auth.py::get_password_hash`；副本 `database.py::hash_password`（逐字相同）。
