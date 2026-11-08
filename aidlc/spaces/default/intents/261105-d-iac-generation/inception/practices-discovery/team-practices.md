# 團隊實踐（Team Practices）

> practices-discovery 產物｜intent `261105-d-iac-generation`｜HEAD `0bffc82`｜2026-11-05T15:48:45Z
>
> **Final Integration（Step 5）**：人工訪談 Q1–Q8 已定案；Summary Confirmation = Looks correct。本檔於確認授權後由 orchestrator 重存（recovery）。
> 五個 H2 供後續 `practices-promote` 整段替換 `team.md`（見 `project.md` Corrections `practices-discovery:c1`）。
> Commit message 範例／regex code fence 已自 cost-finops 核可稿還原（Q8=A），避免 promote 抹掉 ADR-0010 範例。
> Story D 本輪定案已寫入各節；草稿中的 proposed 標記已全部清除。

---

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

---

### 本輪覆核（命名合規抽樣，非新規則）

- HEAD `0bffc82` 近期 commit 多數已使用中文 type（`功能`／`修正`／`文件`／`建置`／`雜項`／`重構`／`整合`）；仍可見少數英文 type（如 `fix(env)`、`fix(ci)`）——與「規則生效後合規率留待覆核」的既有記載一致，**本輪不另立罰則**。
- 作用中工作分支 `luojingting/feat/d-iac-generation` 符合 `<uploader>/<type>/<slug>`。


---

## Walking Skeleton

**Q3 定案：`skeleton: off`。**

初答為 C（`skeleton: on`），經訪談內成本確認後改為 A。理由：本專案自 baseline 起已有可運行的 backend／frontend、CI（四道 gate）、自動部署（含 rollback 自動化）與 10 組 agentic workflow，管線成熟度已超過「需要走 skeleton 驗證端到端管線是否打通」的階段；本 intent（`users` 表加最後活動欄位並顯示於 Admin 表格）是在既有頁面加欄，不是打通新架構，沒有 bootstrap 標的。第一個 Bolt（若本 intent 走 Construction）照常跑，不需額外一輪 gate 與儀式。

若未來個別大型 intent（例如引入全新技術層）需要 skeleton 驗證，可在該 intent 的 scope 檔逐案開啟，不需改動團隊預設值。

> **Q1 定案（A）**：260819-cost-finops 雖屬全新 Cost／FinOps 功能域（greenfield，無 calculator、無 router、無 CostPage），人工訪談確認本 intent **不開啟** walking skeleton。Bolt 序列照常從第一個 Construction Bolt 開始，不需額外一輪 skeleton gate 與儀式。

---

> **本輪 Q1 定案（A）— intent `261105-d-iac-generation`**：即使將引入 IaC 產碼／掃描／Secret 與三個 agent，仍維持本 intent **`skeleton: off`**。第一個 Construction Bolt 照常跑，不另開骨架儀式；不改團隊預設值。



---

## Testing Posture

- **Methodology**: custom
- **Ordering**: 同一 PR 合併前必須齊備 A／B／C 變更範圍義務，以及已 Affirm 之純函式核心（IaC generator、scanner、redactor）所需的 PBT／突變測試；不得把測試留到後續 PR。


### 既成事實

- **Backend 測試框架**為 Python 內建 `unittest` + `hypothesis` + `unittest.mock`，**未使用 pytest**。CI 以 `python -m unittest discover -s tests -v` 執行（`ci.yml`）。測試 DB 策略見 `backend/tests/helpers.py`：在任何 DB import 前 `sys.modules.setdefault("psycopg2", MagicMock())`，改走 in-memory SQLite，每 session `ensure_role_permissions_seeded(db, force=True)`。規模：`backend/tests/` **本輪覆核（HEAD `0bffc82`）41 個 `test_*.py`**（含 cost／estimate／pricing／langgraph 等；前版「21 個／HEAD `c3de2c8`」已過時）。
- **Frontend e2e** 為 Playwright（chromium 單一 project），涵蓋登入與 RBAC 可視性；`ui-regression` gh-aw workflow 每 PR 對短生命週期 stack 執行並回報 Kiwi TCMS。**這是真閘門**：`post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`；容忍 `stats.flaky`，`retries: 1`。HEAD 現有 e2e 涵蓋登入、RBAC 與 Admin 等；**本輪覆核：仍無 Story D／IaC 頁 e2e**（D 柱無專屬頁面，僅 Workspace Coming Soon stub）。成本頁現況留待 C 柱既有規則，不在本 intent 覆寫。
- **Frontend 完全沒有 unit／component 測試框架**：`frontend/package.json` 的 `devDependencies` 只有 `@playwright/test`，無 vitest、無 jest、無 `@testing-library/*`；`scripts` 只有 `test:e2e`。前端的唯一自動化驗證層就是 Playwright e2e。
- **Property-based testing**：本輪覆核（HEAD `0bffc82`）至少 12 個測試檔含 `@given`（約 19 處），仍集中於純函式模組，屬自發良好實踐。`project.md` ADR-0006 點名的三個 hard-constraint 落點（**IaC generator**、cost calculator、agent routing）中，**IaC generator 在本 repo 仍無對應實作模組**，故該約束對 Story D 現況為 N/A（非豁免、非違反）。**本 intent 一旦落地 IaC generator 純函式核心，ADR-0006 PBT 約束隨即由 N/A 轉為 blocking。**本輪另 Affirm（Q5=B）：**scanner 與／或 redactor 亦列為 PBT 核心**。
- **HTTP 層 TestClient 現況**：`backend/tests/test_user_list_endpoint.py` 用 `starlette.testclient.TestClient` 測 `/api/auth/list` 分頁欄位（樣板在 `tests/helpers.py`）。樣板仍在 `tests/helpers.py`；本輪覆核另有 `test_estimate_intake_api.py`、`test_me_endpoint.py` 等 TestClient 使用例。**無任何 D1／D2／D3／IaC router 可測**（OpenAPI 零 IaC 條目）。
- **Story D／IaC 測試完全缺席（本輪焦點）**：無 `test_*iac*`／`test_*terraform*`；`backend/tests/` 對 D1／D2／D3 業務端點 0 命中；`test_rbac.py` 未將 D 柱 allow／deny 當 Story D 落地義務覆蓋。C 柱測試現況已由後續 intent 推進，本檔不覆寫其效力。
- **完全沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）。`org.md` 宣告的「最低 80% line coverage」目前**既無法量測也無法強制，是宣告而非閘門**。
- **既有授權測試皆在 service 層**：`test_rbac.py`、`test_j5_authz.py`、`test_review_authz.py` 皆非 HTTP 層測試。

### 本輪新增規則（Q4 定案：A + B + C，D 不採）

依據：本 intent 的六道現有 CI 閘門（`repo-contract`、frontend lint、`tsc -b`、backend import smoke、backend `unittest`、`ui-regression`）逐一查證後，**對「後端漏欄位、序列化成 null、前端渲染成空白」這條失敗路徑全部無效**——不是覆蓋率不足的程度問題，是這條變更路徑上沒有任何自動化斷言存在的有無問題。三項零新依賴的測試底線本輪起生效：

- **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 `role_permissions` 預設值變更，必須有測試同時驗證「該角色能做到」與「其他角色做不到」。零新依賴，直接擴充既有 `test_rbac.py`／`test_j5_authz.py` 形狀。C1 的 RBAC seed 種子已存在（`FinOps_Analyst` 與 C1 相關欄位）；若本 intent 改動 C1 預設值（例如讓架構師 edit 時數），屬 seed 變更，須 A 規則測試。
- **B — 新增或修改 HTTP 端點需 `TestClient` 測試**：斷言其 status code 與 `response_model` 的欄位集合。採用成本為零——`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，`starlette.testclient.TestClient` 前置條件已滿足；新測試檔放進 `backend/tests/` 即被現有 `python -m unittest discover -s tests` 撿到；`get_db`（`database.py:31`）與 `get_current_user`（`services/auth.py:39`）為穩定的模組層函式，可用 `app.dependency_overrides` 覆寫；以 `TestClient(app)` 直接使用不觸發 `@app.on_event("startup")` 的 `init_db()`，不需要真實 DB。C1 若新增 `/api/cost*` 端點，須依 B 規則補 TestClient 測試，且 CI 的 OpenAPI drift 檢查會要求同步更新 `openapi.json`。
- **C — 前端資料形狀變更需 e2e 斷言**：例如本次 Admin 表格加欄，須新增至少一個 Playwright case 斷言表頭出現該欄位、且至少一列顯示值或既定的「從未」佔位。用既有 Playwright，不需新依賴，且是目前**唯一**能碰到前端頁面的自動化層。C1 若新建 Cost 頁，資料形狀為全新，須 C 規則 e2e 斷言。
- **D（不採用）— 引入前端 unit／component 測試框架**：需新增依賴（Vitest 或類似），成本明顯較高，且屬獨立的工具鏈決策，不由本次加欄 feature 夾帶。C 項的 e2e 斷言已覆蓋本 intent 的加欄驗證需求。

- **Q3 定案（A）— C1 HTTP 消費者的最小授權測試義務**：即使 `role_permissions` seed 資料未修改（C1 種子已存在於 `rbac_seed_data.py`），第一個 C1 HTTP 端點落地時仍須補 allow/deny 雙向 TestClient 測試——「具 C1 權限的角色應收到 2xx」與「無 C1 權限的角色應收到 403」兩個案例缺一不可。此為 A 規則與 B 規則的交叉要求，適用於本 intent 新增的任何 `/api/cost*` 端點。

### 80% 覆蓋率門檻的定位

**維持 `org.md` 原文，不在本檔弱化或改寫其宣稱**（把「80% 是目標不是閘門」寫進 `team.md` 會構成 `team.md` 弱化 `org.md` 的矛盾，屬 §13 learning admission 應擋下的形狀）。如實記載目前無法量測、無法強制的現況（見上），並以上述 A/B/C 三項變更範圍內、二元可判、零工具成本的規則作為現階段的實際門檻。導入 `coverage.py` 量測工具列為待補承載機制（見 `discovered-rules.md`）。

---

### Story D 本輪定案（`261105-d-iac-generation`，訪談 Q2–Q6／Q8）

- **既有 A／B／C 對新模組的一般效力（已定案）**：改 D 種子 → A；新增／修改 `/api/iac*`（或等價）→ B；真 UI／資料形狀取代 Coming Soon → C。
- **Q2 定案（A）— D 柱第一個 HTTP 消費者的最小授權測試**：D1／D2／D3 **任一**故事的第一個 HTTP 消費者落地時，即使 `role_permissions` seed 未改，仍強制 allow／deny 雙向 TestClient（有權 → 2xx、無權 → 403）。此為 A／B 交叉要求，對齊 C1 Q3 形狀；**codekb 若寫「D 已比照 team.md Q3」不可信——該 Q3 僅鎖定 C1。**
- **Q3 定案（A）— D2 掃描自動化落點**：本 intent 只要求 unittest 測「編排＋報告形狀」（工具／CLI 可 stub）；**不**新增 CI IaC scan job；工具品牌不預填進 Mandated。
- **Q4 定案（A）— D3 Secret 測試最低線**：D3 落地時強制負向測試＋redaction 突變驗證（注入明文樣式 → 輸出／log／artifact 不得出現該明文；拿掉遮罩 → 測試應紅）；contract 掃描作用域擴大另排、不阻塞本條。
- **Q5／Q6 交叉 — 決定性核心先於 LLM**：每個故事先有可離線斷言的決定性核心（D1 generator 含 PBT；D2 報告形狀／scanner；D3 redactor）；LLM 編排進手動／TCMS「只能手動」桶。
- **Q8 定案（A）**：Methodology＝`custom`；Ordering＝同 PR 齊備 A／B／C 與已 Affirm 核心之 PBT／突變義務（見節首）。


---

## Deployment

延伸 `org.md` 與 `project.md` 已定案的部署模型（Construction／Operations 連續、deploy-on-merge 至 `192.168.10.10`，見 ADR-0007／ADR-0008），記載團隊層級的執行細節：

- **CI（`ci.yml`）管線**依序為 `repo-contract` → `frontend`（lint + `tsc -b` typecheck + build）→ **OpenAPI spec drift 檢查**（`backend/scripts/dump_openapi.py --check`，`c3de2c8` 起新增）→ `backend`（import smoke + `unittest`）→ `docker-build`（buildx 建兩個 image，`push: false`）。管線觸發條件：PR 與 push 到 `main`／`ut`／`danniel/**`／`chore/**`；`concurrency` 會取消同 ref 的舊 run。
  - **`tsc -b` 對前後端 schema 落差無效**：`AdminPage.tsx` 的 `DbUser` 是手寫本地 interface，`fetchUserList` 內 `const data = await res.json(); return data;` 把 `any` 直接放行為 `DbUser[]`。前端型別與後端 `UserSchema` 無任何編譯期連結——這道 typecheck 看似有型別保護，實際對「後端加欄、前端漏接」這類變更無效，必須被誠實記載，不能被誤當成已有的護欄。OpenAPI drift 檢查（新增後）可補上此缺口：若後端回應 schema 改動但 `openapi.json` 未重 dump，CI 即紅燈；前端 `gen:types` 產生的 `src/types/api.d.ts` 依此更新，縮窄型別缺口——但仍不是零缺口（手寫 interface 仍可存在）。
- **`deploy.yml`** 於 PR closed（merge）到 `ut` 或手動 `workflow_dispatch` 觸發，跑在自架 runner（`[self-hosted, linux, x64, cloud360]`），30 分鐘逾時，`concurrency: deploy-10-10` 且 `cancel-in-progress: false`（部署中不可被新 run 打斷）。
- **Rollback 已具備自動化路徑**：部署失敗時，`rollback` job 會還原 last-good、開 revert PR、dispatch Deploy Doctor agentic workflow 自癒。此 job 權限提升為 `contents: write` + `pull-requests: write` + `actions: write`——**這是刻意放寬（功能需要），但可否進一步縮窄（改用 GitHub App token，或把「開 revert PR」拆到最小權限獨立 job）尚未被評估過**，不記為已評估無虞。
- 部署後會清理 `deploy/.env`（避免機敏檔留在 runner 上）。
- `POSTGRES_PASSWORD`／`JWT_SECRET` 缺少時，`deploy.yml` 的「Require the secrets that must not default」步驟會讓部署失敗——**但這道檢查只保護 staging 部署這一條路徑**；本機開發、`deploy/docker-compose.test.yml`（`ui-regression` 每個 PR 自動起的短生命週期 stack）等其他啟動方式沒有等價檢查。

### 已知的規則宣稱與機制落差（如實記載，不美化）

`project.md ## Forbidden` 現有一條規則的宣稱強度高於機制的實際強度：

- **Secret 掃描（雙軌，devsecops 盲評校正）**：`validate_no_obvious_secrets()`（`scripts/validate_repo_contract.py`）現況為——(1) 字面 `FORBIDDEN_CONTENT_PATTERNS`（PEM 等）仍主要掃 `REQUIRED_FILES`／contract 必要檔；(2) `SECRET_VALUE_REGEXES`（AWS／GCP 賦值形狀）已對 `git ls-files` **全域**掃追蹤文字檔。剩餘缺口：無 gitleaks 類通用高熵規則、PEM 字面樣式仍偏 contract 檔、**執行期**回應／log／artifact 明文不在 contract 範圍（由 D3 負向＋突變測試補上，Q4=A）。



> 原本並列於此的第二項已解決，故從上面的清單移除：禁止 production 路徑的檢查原先以 working-tree diff 為比對基準，在 CI 的乾淨 checkout 下不會擋到任何東西。intent `260816-production-path-check`（issue #509）已把比對基準改為 `git ls-files` 全域掃描，並補上回歸測試 `backend/tests/test_repo_contract_production_paths.py`（在暫存 git repo 內以乾淨工作樹重現 CI 條件）。`discovered-rules.md` 對應記載：**本輪標為已解決**（HEAD `0bffc82` 確認 `validate_no_production_config_added()` 以 `git ls-files` 全域掃描；回歸測試 `backend/tests/test_repo_contract_production_paths.py` 仍在）。

---

### Story D 部署／產品邊界（本輪定案）

- **平台／產品不 apply（Q7=A）**：D 柱 API／agent **不得**代使用者對雲端執行 apply／destroy；產出與掃描報告即可。人工 high-risk gate（plan＋impact＋rollback＋核准）仍適用於任何真 apply，但**不得**被解讀成「核准後平台可代 apply」。staging 的 `deploy.yml`→`192.168.10.10` 與此正交。
- **無 CI IaC scan job（Q3=A）**：本 intent 不新增 checkov／tfsec／gitleaks／trivy 等 CI 掃描步驟；D2 自動化落在 unittest 編排＋報告形狀。
- **D3 與 secret 機制**：產品路徑靠負向／突變測試；contract 掃描擴大另排。



---

## Code Style

我們依循既有的語言慣例與已生效的檢查工具，並如實記載工具鏈的落差：

- **Frontend**：ESLint 10（flat config：`js.recommended` + `tseslint.recommended` + `react-hooks.flat.recommended`（`eslint-plugin-react-hooks@7.1.1`，16 條 error 級規則：`rules-of-hooks`、`static-components`、`use-memo`、`preserve-manual-memoization`、`immutability`、`globals`、`refs`、`set-state-in-effect`、`error-boundaries`、`purity`、`set-state-in-render`、`config`、`gating`；另 `exhaustive-deps`、`incompatible-library`、`unsupported-syntax` 為 warn 級）+ `react-refresh.vite`）+ `tsc -b`（隨 `npm run build` 觸發型別檢查）。CI 只擋 **error**：`npm run lint` = `eslint .`，未加 `--max-warnings 0`，現況為 `0 errors, 3 warnings`（`AssessmentPage.tsx:365`、`LoginPage.tsx:36`、`WorkspacePage.tsx:279` 皆為 `exhaustive-deps`），這是已知既存狀態，不代表「lint 沒在跑」。**根目錄無 `.prettierrc`**——`org.md` 預設的 Prettier 從未被引入，非「引入後又拿掉」。

- **前端：lint 規則造成的結構約束**（不是團隊的美學選擇，而是 lint 規則的直接後果，違反即 CI 紅燈；升級或更換 lint 套件時本節同步重審）：
  - **Context 拆兩檔**（`react-refresh/only-export-components`）：Provider 元件放 `.tsx`，型別與 hook 放同名 `.ts`。現例 `AuthContext.tsx` + `auth-context.ts`。
  - **資料抓取拆兩層**（`react-hooks/set-state-in-effect`，error）：拆成①純抓取函式（不碰 state，回傳資料）②呼叫端在 `.then/.catch/.finally` 更新 state ③`useEffect` 內用 `cancelled` flag 防卸載後 setState。現例 `AdminPage.tsx` 的 `fetchUserList` / `fetchUsers` / `useEffect`。任何新增前端資料來源都必須沿用此形狀。
  - **不可就地修改物件**（`react-hooks/immutability`，error）：state 更新一律回傳新物件（現例 `setUsers((prev) => prev.map(...))`）。

- **前端 API 呼叫現況**：URL 組裝已集中於 `src/config/api.ts`（`apiUrl()` / `wsUrl()`），52 處 `fetch()`（10 支檔）一致沿用。未集中的是認證標頭（40 處手寫 `Authorization: Bearer`）、401 處理、錯誤解包與回應型別。新增呼叫點時沿用現有形狀（`apiUrl()` + 手寫 header + `res.ok` 判斷 + `data.detail` 取錯誤訊息），不要單點自創抽象。

- **Backend（既成事實，非理想）**：完全沒有 linter、formatter、type checker（無 Ruff、無 Black、無 mypy／pyright）。`org.md` 宣告的「Formatter: Black (Python)」「Linter: Ruff 等，CI 強制」在 backend 側不成立，這不是團隊決議不用，是尚未補上，導入方式列為待補承載機制（見 `discovered-rules.md`）。
- **Backend 依賴 pin 現況**：`fastapi[standard]==0.141.1` 與 `pydantic==2.13.4` 精確釘選（因 OpenAPI dump 位元決定性）；其餘 10 個套件仍未 pin、無 lockfile。CI／Docker build／staging 部署三處各自解析當下最新版，可能彼此不同。Frontend 對照組有已 commit 的 `package-lock.json`，CI 用 `npm ci`。此為既成事實，導入 pin／lockfile 的具體做法未經本輪訪談定案，列為待補承載機制。
- **零 TODO／FIXME／HACK／XXX 標記**（全 repo），且無死碼區塊——這是應該保護、不應在後續規範中弱化的既有紀律。
- **模組級 docstring 覆蓋率 16/18**：其中 router 類多為單行摘要（如 `user_router.py` 僅單行功能清單，無安全邊界、無契約段），`agent_router.py` 的「契約（前端依賴，請勿變更）」是最完整的樣板。建議追認為既成慣例，新模組沿用 `agent_router.py` 的樣板深度。

- **命名慣例**（既成事實）：
  - Python 檔名／router：`snake_case.py`；router 一律 `*_router.py`；WA 引擎一律 `wa_*` 前綴——一致，追認為規則。
  - React 命名：元件與頁面 `PascalCase.tsx`；頁面一律 `*Page.tsx`——一致，追認為規則。
  - 非元件 TS 檔名：**已知不一致**（`auth-context.ts` kebab-case vs `useCollaboration.ts`／`diagramViewer.ts` camelCase）。新規則：hook 檔沿用 `use*.ts`，其餘 camelCase；`auth-context.ts` 為既存例外，不強制改名。
  - logger 命名：**已知不一致**（11 支模組用 `logging.getLogger("cloud360.<module>")`，5 支用 `__name__`：`collab_router`、`design_agent`、`agent_router`、`diagram_builder`）。新模組一律 `"cloud360.<module>"` 形式；C1 新增的 cost router／calculator 須沿用此形式。
  - `HTTPException` 呼叫風格：**已知不一致**（`user_router.py` 內同檔混用 12 處具名引數 `status_code=`、17 處位置引數）。記為已知不一致，不強制統一（純格式改動的收益低於 diff 噪音）；新程式碼沿用所在函式鄰近寫法。

- **後端分層**：分層成熟度依模組家族而異，這是已知且刻意保留的現況，不是待修的違規。
  - `review` / `lens` / `wa_*` 家族：router → orchestrator/service → 純函式引擎 → model，三層清楚；純函式引擎層（`wa_rule_engine.py`／`wa_lens_engine.py`／`diagram_builder.py`）不讀 DB、不連外，是 property-based 測試的實際落點。
  - `user` / `collab` 家族：無 service 層，商業邏輯直寫 handler（`user_router.py` 831 LOC、`collab_router.py` 527 LOC）。
  - 規則依改動落點分流：**新模組／新業務邏輯**一律走三層形狀，純運算下沉到不讀 DB 的函式；**修改 `user_router.py`／`collab_router.py`** 就地沿用既有形狀，不趁機夾帶 service 層抽取（這兩支目前無 HTTP 層測試保護，重構與功能變更混在同一個 PR 不可驗證，抽 service 層是獨立任務，前置條件是先有端點測試）；不得在這兩支之外新建「router 直寫商業邏輯」的模組。C1 新增 cost_router 與 calculator 須走三層形狀。

- **錯誤處理形狀**（既成事實）：`user_router.py` 有 0 個 `try/except`，全部靠 `raise HTTPException` 快速失敗；`review_router.py`（4 個）、`collab_router.py`（5 個）的 `try/except` 都用在外部呼叫邊界。既有慣例：DB／驗證錯誤直接 `raise HTTPException`，不 try/except 吞掉；`try/except` 只用在外部依賴邊界（LLM、webhook、檔案）且必須降級或記 log，不得靜默。與 `construction.md` 的「Errors must be surfaced」一致。

- **單一真實來源**：當同一份事實已存在於程式中（角色清單、權限矩陣、schema 欄位），新增第二份物化前必須先確認是否有既有常數或 API 可直接使用。若確實無法避免（如跨語言邊界），新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試；無法寫測試的副本不新增。
  - 已知既有副本與正本（既成事實，本輪不強制立即消除，收斂方式待後續評估）：角色清單正本 `services/rbac.py::CANONICAL_ROLES`；副本 `services/auth.py::require_any_user`（11 個字串手寫 allowlist）、`services/user_router.py::ROLE_DISPLAY_NAMES`、`frontend/src/pages/AdminPage.tsx::AVAILABLE_ROLES`（已與正本順序漂移）、`schema_rbac.sql` seed。密碼雜湊正本 `services/auth.py::get_password_hash`；副本 `database.py::hash_password`（逐字相同）。

- **Q4 定案（A）— C1 Cost 功能域的三層形狀與純函式約束**：`cost_router`（HTTP 層，FastAPI router）→ `cost_service`（業務協調，可讀 DB）→ 純函式 `cost_calculator`（計算核心，不讀 DB、不連外、不 raise `HTTPException`）+ 獨立 `pricing_client`（外部計價 Port，包裝 `httpx`）。禁止把 cost 邏輯寫入 `user_router.py` 或 `wa_rule_engine.py`；`cost_calculator` 模組內禁止 import `httpx`、任何 DB session 型別，以及 `HTTPException`——這是 ADR-0006 PBT 約束能在計算核心起作用的結構前提。**ADR-0017 §1–§2、§4＋§8 修訂**：三層形狀與純函式禁令保留，純函式層由 `cost_calculator` 改錨至估價表解析器（解析 AWS CSV／Azure XLSX／GCP CSV），PBT 約束原樣移轉。`pricing_client` 於 §1 廢止後由 §8 恢復，職責改為 agent 按需查價的 Port（只對公開免帳號端點），不再是取價主路徑。

- **Q2 計價 API 規範（交叉參照 `discovered-rules.md` Forbidden）**：`pricing_client` 一律只對接公開免帳號的計價端點（如 AWS Pricing API 公開 endpoint）；禁止使用需雲端供應商帳號憑證的 Cost Explorer、Billing API 或同類 API。完整約束見 `discovered-rules.md ## Forbidden ## C1 計價 API`。**ADR-0017 §3、§4＋§8 修訂**：本條原樣有效。估價一律來自上傳的官方估價表，不得以自動取價產生估價；agent 得經 `pricing_client` 查公開免帳號端點確認現價，結果只寫入建議文字。需帳號憑證者（含走 IAM 的 boto3 Pricing Query API）仍全禁。**ADR-0018 §1＋§2 再修訂**：**目錄價類**的需憑證端點解禁——AWS Price List Query API（IAM，權限限於 `pricing:GetProducts`／`DescribeServices`／`GetAttributeValues`）、GCP Cloud Billing Catalog API（API key 須綁定該 API）；Azure 維持公開 Retail Prices 不變。**帳單與用量類**（Cost Explorer、Cost and Usage Report、Cost Management、Billing Export）**維持全面禁止**——此禁令是前者得以解禁的對價，不得一併放寬。`pricing_sdk.py` 與 `boto3` 由「確定刪除」改為保留。

### Story D 結構定案（`261105-d-iac-generation`，訪談 Q5＝B、Q6＝A）

- **既有規則（已定案）**：新模組／新業務邏輯一律走三層；純運算下沉到不讀 DB 的函式；純函式層禁止 `httpx`、DB session、`HTTPException`（service 層仍可 `raise HTTPException`，對齊 `backend/cost/` 先例）；新模組 logger 用 `"cloud360.<module>"`。
- **Q5 定案（B）— 領域套件與 PBT 擴張**：D 柱採 **`backend/iac/`** 領域套件（對齊 `backend/cost/`），內含 router → service／orchestrator → 純函式核心＋三 agent；檔名用領域語彙（如 `iac_generate_*`／`iac_scan_*`／`iac_secret_*`），**禁止** `d1_*`／`d2_*`／`d3_*` story-id 檔名前綴（權限仍用 `require_story_action("D1"|"D2"|"D3", …)`）。本輪 Affirm：**generator（ADR-0006）以及 scanner 與／或 redactor 皆為 PBT 核心**——落地同一 PR 須含 Hypothesis，不得只有 example-based。
- **Q6 定案（A）— Agent 底座**：D1／D2／D3 三 agent 一律走既有 `langgraph_runtime`＋OpenRouter，禁止再增 Claude-SDK-only／Anthropic-only 路徑；**不**要求本 intent 收斂既有 `design_agent`。agent 檔與 router 同屬 `backend/iac/`。
- **API 掛載建議（執行慣例）**：獨立前綴（如 `/api/iac/...`），勿塞進 `agent_router`／`user_router`。
- **UI**：沿用 Layout／Workspace 語彙與資料抓取兩層形狀；真 CTA 替換 Coming Soon 時須接 D1 權限檢查（現況 CTA 不檢查 `D1`——產品／設計待修）。

