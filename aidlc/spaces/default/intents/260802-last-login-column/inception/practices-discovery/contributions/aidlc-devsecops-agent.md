**Collaborator:** aidlc-devsecops-agent

## Contribution

本檔為 Step 3 盲審的安全與供應鏈視角。所有主張皆附可複驗的檔案路徑與行號；凡屬**我的判斷**而非既有事實或人類已明述之規則者，逐項標示為「[建議]」，供 lead 分流到 `evidence.md` 的訪談題目而非 `discovered-rules.md`。

**本輪最重要的一句話**：本 repo 的安全治理落差不在「缺工具」，而在**既有機制的實際作用域小於規則所宣稱**。`project.md` 有兩條 `## Forbidden` 明文寫「會擋（CI 紅燈）」，但實測其中一條在 CI 是 no-op、另一條看不到應用程式碼。這比任何一項待修的技術債都更需要在 practices 層被記載，因為它讓「我們有護欄」這個前提本身不成立。

---

### A. 建議併入 `team-practices.md` 的段落

#### A-1 → `## Deployment`（供應鏈與可重現建置）

**既成事實（證據支持）**

- `backend/requirements.txt` 共 12 行依賴（`fastapi[standard]`、`pydantic`、`uvicorn`、`httpx`、`python-dotenv`、`sqlalchemy`、`psycopg2-binary`、`passlib[bcrypt]`、`bcrypt`、`pyjwt`、`claude-agent-sdk`、`hypothesis`），**無一有版本約束，且 repo 無任何 lockfile**（無 `requirements.lock`、無 `pyproject.toml`、無 `poetry.lock`）。已直接讀檔確認。
- 三處各自在執行當下解析最新版：CI 的 `backend` job（`pip install -r requirements.txt`，`.github/workflows/ci.yml`）、`backend/Dockerfile` 的 image build、staging 的 `docker compose up -d --build`（`.github/workflows/deploy.yml:119`）。
- 其他未 pin 的執行期元件：backend image 內以 `npm i -g` 安裝的 Claude Code CLI、`cloudflared` 與 `adminer` 的 image tag 皆為 `latest`。
- 對照組：frontend 有已 commit 的 `package-lock.json`，且 CI 用 `npm ci`（嚴格照 lockfile 安裝，非 `npm install`）。

**供應鏈意涵（本輪新增的評估，非既有記載）**

1. **可重現建置不成立**：CI 綠燈不能證明 staging 跑的是同一組套件版本。「CI 綠但部署紅」這類故障在沒有 lockfile diff 的情況下無法從 git 追溯。
2. **無法回答「我們是否受某個 CVE 影響」**：沒有解析後的版本基準（SBOM／lockfile），任何弱點通報都只能靠人工到 staging 上跑 `pip freeze` 才知道現況，而那個現況下次 build 就會變。
3. **無 pin 亦無 hash 校驗**：上游帳號遭接管、惡意版本發布、typosquat 這三類供應鏈攻擊在本 repo 沒有任何阻擋層，且下一次 `docker compose up --build` 會自動拉進來。
4. **治理不對等的方向是錯的**：治理鬆的是 backend，而 backend 正是持有 JWT 簽章、密碼雜湊、DB 連線與全部授權判斷的一側。

**[建議] 規則形式（分兩段，需訪談定案）**

- **第一段（可立即生效）**：`ALWAYS` 新增或變更 backend 依賴時，該依賴必須帶版本約束；不得以無約束形式加入 `requirements.txt`。
- **第二段（需先完成技術債 T5）**：全量 pin＋產生 lockfile，並讓 CI／Docker build／staging 三處都以 lockfile 安裝。

分兩段的理由：把「全量 pin」直接定為硬規則，會讓 T5 修完前的每個 PR 都處於不合規狀態，規則會在第一週就被當場繞過；只約束「新增」則立刻可執行，且是單向收斂的。

#### A-2 → `## Deployment`（Secret 處置與 ADR-0006 的落差表達）

**既成事實（證據支持）**

- `backend/services/auth.py:13` 的 JWT 簽章金鑰有程式內預設值：未注入時**靜默**使用一個已進版控的固定字串簽發 token。同一字串亦以明文出現在 `backend/.env.example:32`（即同一個已知值在 repo 內有兩份副本）。任何取得 repo 的人可偽造任意身分的 token。本檔依 `team.md ## Forbidden` 不轉載該字串。
- `deploy/docker-compose.test.yml:34` 對 `JWT_SECRET` 使用 shell 預設值語法，缺少注入時仍以一個固定測試值啟動。**該檔正是 `ui-regression` agentic workflow 每個 PR 自動起的短生命週期 stack**，即這是一條自動化執行、且會落到「有預設金鑰」狀態的路徑。
- `.github/workflows/deploy.yml:71` 的 `Require the secrets that must not default` 步驟會在缺少 `POSTGRES_PASSWORD` 或 `JWT_SECRET` 時失敗，其錯誤訊息也明白指出「沒有它 `auth.py` 會用預設值」。**但這道檢查只保護 staging 部署一條路徑**；本機開發、`docker-compose.test.yml`、其他任何啟動方式都沒有等價檢查。
- `deploy/.env.example:14` 的示範值是佔位字串並附產生指令（`openssl rand -hex 32`），這一份寫法是正確的，與 `backend/.env.example` 的寫法不一致。
- 預設帳號：`backend/database.py` 在空 DB 時建立 11 個 persona 帳號（密碼為可預測樣式）與一個最高權限帳號，全部 `approved` 且帶正式角色；最高權限帳號的 bcrypt hash 亦已 commit 進 `schema_rbac.sql`。

**落差該怎麼表達（這是我對第 2 題的核心回答）**

不要寫成「T6／T7 是待修的技術債」。正確的表達是：**ADR-0006 的 security baseline 目前沒有承載機制。**

- ADR-0006 把 security baseline 綁在 `extensions/security/baseline/` 這個 AI-DLC v1 的 extension 路徑上（`aidlc/spaces/default/intents/260802-default/inception/decisions/0006-adopt-aidlc-framework.md:22`）。
- v2 遷移（ADR-0011）移除了 extension 機制。**該路徑在整個 repo 已不存在**（全樹搜尋確認：僅 `project.md:55` 的 `## Decided` 一行與兩份 ideation 文件在引用它，沒有任何實體檔案）。
- 因此這條 hard constraint 現在只是 `## Decided` 的一行備註：`## Mandated` 與 `## Forbidden` 沒有任何 `ALWAYS`／`NEVER` 形式，也沒有任何自動檢查。

**它不是「未被滿足」，是「沒有被表達成可執行的東西」。** T6／T7／T8 之所以能長期存在，正是因為約束失去承載後，沒有任何一層會在變更時提起它。

因此 practices-discovery 本輪的正確動作，不是列舉待修項，而是**把 baseline 的四個面向（IAM、encryption、network exposure、audit logging）重新落成 v2 規則層的操作型規則，並為每一項指名檢查點**。且必須在本輪做——本 intent 同時觸及 IAM（RBAC seed 變更）與 audit logging（稽核欄位本身）。

**[建議] 規則形式（需訪談定案）**

- `ALWAYS` 安全關鍵環境變數（JWT 簽章金鑰、DB 密碼）缺少時啟動失敗，不得有程式內預設值。
- `NEVER` 在任何被自動化啟動的 compose 檔，為安全關鍵變數提供 shell 預設值 fallback。
- `ALWAYS` 示範／persona 帳號的建立以環境變數明確開啟，預設關閉。

#### A-3 → `## Deployment`（掃描面：現況與既有掃描器的真實作用域）

**缺什麼（已逐項查證，非推測）**

| 面向 | 現況 |
|---|---|
| SAST | 無（無 CodeQL、無 Semgrep、無 bandit） |
| DAST | 無 |
| 依賴弱點掃描（SCA） | 無 —— `.github/` 下無 `dependabot.yml`；CI 無 `pip-audit`／`npm audit`；無 Renovate |
| Secret 掃描 | 僅 `validate_repo_contract.py` 的一道檢查，作用域見下 |
| 容器 image 掃描 | 無（`docker-build` job 只 build，`push: false`） |

10 組 gh-aw agentic workflow（`code-drift-alert`、`contract-guard`、`daily-digest`、`deploy-doctor`、`issue-triage`、`lint-fix`、`pr-reviewer`、`release-watch`、`spec-sync`、`ui-regression`）**無一是安全掃描**。

**更重要的是：既有掃描器的實際作用域小於 `project.md` 的宣稱**（本輪最重要的新發現）

1. `validate_no_obvious_secrets()`（`scripts/validate_repo_contract.py:347`）逐一讀取 `contract_files()` 的回傳值。`contract_files()`（同檔 `:273`）= `REQUIRED_FILES` 的 12 個 repo 層檔案 ＋ baseline record 的必要檔 ＋ 該 record 的 audit shard。**`backend/`、`frontend/`、`deploy/`、`schema_rbac.sql`、任何 `.env.example` 都不在其中。** 也就是說，本 repo 唯一的 secret 掃描器**結構上看不到應用程式碼**。
2. `validate_no_production_config_added()`（同檔 `:330`）的輸入是 `git diff --name-only`（unstaged）∪ `git diff --name-only --cached`（staged）。CI 是乾淨 checkout，兩者皆為空集合 → **這道檢查在 CI 恆為 no-op**，只在本機有未提交變更時才作用。
3. `project.md ## Forbidden` 對這兩條都寫「`scripts/validate_repo_contract.py` 會擋（CI 紅燈）」。**就這兩條而言，規則宣稱的強度高於機制的實際強度。**

**這個缺口該如何定位（第 3 題的回答）**

不是「缺工具」，是 **`code-quality-assessment.md` 叢集 C3 根因（規則寫在文件裡而不是寫在檢查器裡）在安全治理層的最嚴重實例**。它比已被記載的 T16（`DEPLOY.md` 雙語盲區）嚴重一個量級：T16 的後果是文件不整齊，這裡的後果是**團隊以為有 secret 掃描，實際上沒有**。錯誤的安全感比沒有防護更危險，因為它會讓後續決策以「有護欄」為前提。

**[建議] 導入優先序（依成本／效益，非嚴重度）**

1. **擴大 `validate_no_obvious_secrets()` 的作用域**到全 repo（排除 `node_modules`／`dist`／`.git`／`frontend/package-lock.json`），或改用 GitHub secret scanning／`gitleaks`。修既有腳本的成本最低，且直接消除盲區。
2. **修正 `validate_no_production_config_added()` 的 diff 基準**（PR 情境對 base ref，push 情境對 `HEAD~1`），讓它在 CI 真的會擋。
3. **`.github/dependabot.yml`**（`pip` ＋ `npm` ＋ `github-actions` 三個 ecosystem）。設定檔層級。注意：**backend 因無 lockfile，Dependabot 對它幾乎無效**——這反過來又是 A-1 應該 pin 的獨立理由，兩者互為前提。
4. **`pip-audit` 加進 CI 的 `backend` job**（一行 step，不需 lockfile 也能掃已解析的環境），這是在 T5 完成前唯一能對 backend 生效的 SCA。
5. **SAST：CodeQL**（`python` ＋ `javascript-typescript`），零設定成本的起點。
6. **DAST 優先序最低**。自有 staging 上技術可行，但在授權測試尚不存在的情況下，先補 allow/deny 測試的效益遠高於黑箱掃描。

#### A-4 → `## Code Style`（backend 無 linter 的安全實質性）

**我的判定：風險是實質的，但實質性不來自「風格不一致」，而是缺的那一類檢查正好與安全高度重疊。**（第 5 題的回答）

- Ruff 可啟用的 `S` 規則集（bandit 移植）能直接偵測本 repo **已經存在**的形狀：硬編碼的密碼／密鑰預設值（即 T6／T7）、以 `assert` 做驗證、不安全的隨機源、SQL 字串拼接。也就是說，**若當初 backend CI 有 Ruff＋`S`，T6 與 T7 這兩個 P1 會在引入它們的那個 PR 就被擋下**，不會活到逆向工程階段才被發現。
- 無 type checker 的安全面向：`role` 為 `Optional[str]`、`authorization_status` 是字串狀態機，兩者都在授權判斷路徑上。`backend/services/rbac.py` 的 guard 組合是全系統的安全決策點，卻是最沒有靜態保證的部分。
- 對照前端：ESLint 已被證明能改變程式碼**結構**（`react-refresh` 迫使 `AuthContext` 拆檔、`react-hooks` 的 `set-state-in-effect` 迫使資料抓取拆分）。後端零檢查不是「風格自由」，是**安全相關的靜態訊號被整片放棄**。

**誠實標記成本**：對 7,171 LOC 一次性導入會產生大量既有告警。**[建議]** 規則寫成「新增／修改的 backend 檔案必須通過 Ruff」（逐檔納管或對 diff 檢查），而非「全 repo 一次過」，否則第一次紅燈就會被停用。

#### A-5 → `## Testing Posture`（授權測試，與 HTTP 測試分開）

**既成事實**：`backend/tests/` 已有授權測試，但都在 service 層而非 HTTP 層——`test_rbac.py`（`test_user_can`、`test_user_can_arch`、`test_permissions_map_for_role`）、`test_j5_authz.py`（`test_pending_user_can_is_false`、`test_null_role_cannot`、`test_project_admin_cannot_approve_owner` 等）、`test_review_authz.py`。

**[建議]**：本 intent 的核心變更是**授權矩陣變更**，其對應的測試可以在既有 `user_can` 層立刻寫出，**不需要等 `TestClient` 的決策**。規則應寫成「`role_permissions` 預設值的任何變更，必須附上該 (role, story, action) 的 allow 與 deny 雙向測試」。這與「新增端點需 `TestClient` 測試」是兩條獨立的規則，不應合併成一題（理由見 Positions 第 5 點）。

---

### B. 對 `discovered-rules.md` 的判定（明確分類）

我完全同意 lead 的收錄判準：**只收人類已明述的硬約束，不收我的建議**。依此判準逐項分類：

| 我的發現 | 分類 | 去處 |
|---|---|---|
| 依賴未 pin／無 lockfile（A-1） | 事實發現，非人類已明述之規則 | `evidence.md` ＋ 訪談題 |
| JWT 預設值、預設帳號（A-2 前半） | 事實發現 | `evidence.md` ＋ 訪談題 |
| **ADR-0006 security baseline 失去承載（A-2 後半）** | **人類已明述的硬約束，但尚未以規則形式收錄** | **`discovered-rules.md ## Mandated`** |
| 掃描器作用域小於宣稱（A-3） | 事實發現（規則已存在，是機制不符） | `evidence.md` ＋ 訪談題 |
| backend 無 linter（A-4） | 事實發現 | `evidence.md` ＋ 訪談題 |
| WebSocket 無授權、`roles_catalog` 匿名觸發 seed（D-2） | 事實發現 | `evidence.md` ＋ 訪談題 |

**唯一一項我認為應補進 `discovered-rules.md ## Mandated`**：

ADR-0006 的 security baseline 在 `CLAUDE.md` 第 3 章「Standing Constraints」被人類逐字列為 `Hard constraint（IAM、encryption、network exposure、audit logging）`，且 `CLAUDE.md` 本身是 `REQUIRED_FILES` 的成員之一。它符合「人類已明述」與「硬約束」兩個條件，卻只以 `project.md ## Decided` 的一行備註存在，且該行指向一個 v2 遷移後已不存在的路徑。這正是 `discovered-rules.md` 的收錄情境。

建議措辭（保守，只重述人類已明述的內容，不夾帶我的建議）：

```
ALWAYS 對每一項變更檢查 ADR-0006 security baseline 的四個面向
（IAM、encryption、network exposure、audit logging）；此為 hard
constraint（CLAUDE.md 第 3 章 Standing Constraints）。原承載該約束的
v1 路徑 `extensions/security/baseline/` 已隨 v2 遷移（ADR-0011）移除，
本條為其在 v2 規則層的落點。
```

---

### C. 建議追加的訪談題目（接續 `evidence.md` 既有 8 題，編號 9–13）

**Q9 — backend 依賴的 pin 政策**

A. 立即全量 pin ＋ 產生 lockfile ＋ 三處改用 lockfile 安裝（一次到位，需一個獨立 PR）
B. 分兩段：本輪只定「新增依賴必須帶版本約束」為硬規則，全量 pin 列為技術債 T5
C. 維持現狀，只加 `pip-audit` 到 CI 讓弱點可見
D. 改用 `pyproject.toml` ＋ 現代工具鏈（uv／poetry），一併解決 pin 與工具設定
E. 其他（請說明）

`[Answer]:`

**Q10 — 安全關鍵環境變數的預設值處置**

A. 移除 `auth.py` 的程式內預設值，缺少時啟動失敗（fail fast）；`backend/.env.example` 改為佔位字串＋產生指令，比照 `deploy/.env.example` 的寫法
B. 同 A，並一併移除 `deploy/docker-compose.test.yml` 對 JWT 金鑰的 shell 預設值語法（`ui-regression` 改由 workflow 注入隨機值）
C. 維持現狀，只在 `.env.example` 與 README 加強警語
D. 現在不動，列為技術債並記錄具名的風險接受
E. 其他（請說明）

`[Answer]:`

**Q11 — 掃描器導入範圍與優先序**

A. 只做「修既有腳本」：擴大 `validate_no_obvious_secrets()` 的作用域 ＋ 修正 `validate_no_production_config_added()` 的 diff 基準
B. A ＋ `.github/dependabot.yml`（pip／npm／github-actions）
C. B ＋ CI 的 `pip-audit` step
D. C ＋ CodeQL（python／javascript-typescript）
E. 全部不做，本輪只記錄缺口

`[Answer]:`

**Q12 — 端點授權宣告是否成為明文規則**

A. 成為硬規則：新增或修改任何 HTTP／WebSocket 端點時必須明確宣告其授權 guard；無 guard 者必須在 PR 說明匿名可達的理由與影響面
B. 同 A，並額外加一條：匿名可達的端點不得呼叫任何具寫入語意的函式（針對 `roles_catalog` 觸發 seed 的形狀，而非針對該單一端點）
C. 只記入技術債（T8），不成為規則
D. 成為規則，但本輪先只涵蓋 HTTP，WebSocket 另案處理
E. 其他（請說明）

`[Answer]:`

**Q13 — RBAC 權限變更的雙處同步是否成為 blocking 規則**

A. 成為硬規則：任何 `role_permissions` 預設值變更必須同時改 `schema_rbac.sql` 與 `backend/services/rbac_seed_data.py`，且 PR 須附兩份來源的一致性驗證輸出
B. 同 A，並加上「必須附該 (role, story, action) 的 allow／deny 雙向測試」
C. 不定規則，等 T3 的 CI 一致性檢查做好再說
D. 同 B，並額外要求「權限授予的評估對象是該 guard 所守護的**全部端點回應內容**，不得以 UI 可見性為準」
E. 其他（請說明）

`[Answer]:`

---

### D. 本次 intent 的安全常設要求（第 6 題的回答）

本 intent 同時觸及 ADR-0006 baseline 的兩個面向：**IAM**（`Security_Reviewer` 的權限開通）與 **audit logging**（稽核欄位本身）。四項具體要求，前三項是我建議成為常設規則，第四項是我建議下放到 nfr-requirements 的必答項。

#### D-1 權限變更必須雙處同步，且該 PR 自帶一致性證據

**已查證的事實**：`Security_Reviewer` 對 `J3a` 目前在兩份 seed 中都是 `(view=false, edit=false, review=false)` —— `backend/services/rbac_seed_data.py:299` 與 `schema_rbac.sql:475`。兩份來源目前對 `Security_Reviewer` 各有 28 列，數量一致。本 intent 要把 `view` 翻成 true，**必須兩處都改**。

**風險**：沒有任何 CI 檢查會比對這兩份 seed（技術債 T3）。漏改一處的後果不是「文件不同步」，而是**環境相依的授權差異**：以 initdb 建立的新環境走 `schema_rbac.sql`，既有環境走 `rbac_seed_data.py` 的 runtime seed 或 `POST /role-permissions/reset-defaults`（`user_router.py:821`），兩條路徑會產出不同的授權矩陣。**授權矩陣的環境分歧是安全事故的教科書形狀**——在 staging 測到的權限邊界不等於別的環境的權限邊界。

**[建議] 常設要求**：`ALWAYS` 任何 `role_permissions` 預設值的變更，必須同時修改 `schema_rbac.sql` 與 `backend/services/rbac_seed_data.py`，且該 PR 必須附上兩份來源的一致性驗證輸出（列數與逐列差異）。這在 T3 的 CI 檢查完成前是唯一的防線，且比等待 T3 更快生效。

**另需注意的交互作用**：`reset-defaults` 端點與 `schema_rbac.sql` 重跑（T4 的無條件 `DELETE FROM role_permissions;`）都會**重播預設矩陣**。這代表任何經 Admin UI 做出的權限**收回**，都可能被這兩條路徑靜默還原——即權限撤銷不是持久的。這個方向（撤銷被還原）比 T4 已記載的方向（調整被清掉）更具安全意涵，建議在 evidence 中補記。

#### D-2 權限授予的評估對象是端點，不是欄位

**已查證的事實**：`J3a:view` 這一個 guard 同時解鎖兩個端點——

- `GET /api/users/list`（`user_router.py:437`）：回傳全體帳號的 `id`／`username`／`role`／`is_active`／`authorization_status`／`requested_role`。
- `GET /api/users/authorization-requests`（`user_router.py:462`）：回傳**待審的角色升權申請佇列**，含申請人與所申請角色。

兩者共用同一個 `require_story_action("J3a", "view")`。

**意涵**：scope 文件 (d)「開通使用者管理介面的檢視權限」所暗示的範圍**窄於實際授予的範圍**——它同時包含升權申請佇列。前端是否隱藏該區塊**不構成授權控制**：API 層一旦開通，持有 token 者可直接呼叫。

**[建議] 常設要求**：`ALWAYS` 任何 RBAC 權限授予，以「該 (story, action) 所守護的**全部端點的回應內容**」為評估對象，並在 PR 中列出；不得以 UI 上看得到什麼為準。

這條與 `project.md` 既有的 correction（「問授予權限的問題時，選項描述必須寫明授予後實際看得到／做得到什麼」）互補不矛盾：那一條約束的是**提問**，這一條約束的是**實作與審查**。兩者合起來才覆蓋完整。

#### D-3 安全落差的風險接受必須具名留存

**[建議]**：安全相關的落差若決定不在本輪處理（例如 A-2 的 JWT 預設值、T8 的 WebSocket 無授權），必須留下具名的風險接受紀錄，內容含：落差描述、影響面、暫緩理由、重新檢視的觸發條件。「已知但沒寫下來」與「不知道」在事後檢討時無法區分。

**落點須留意**：`team.md` 明訂 `decisions-log.md` 為 on-demand、不得自動寫入。因此這條規則若要成立，**必須指定另一個落點**（RAID log 或 ADR），不能預設落到 `decisions-log.md`——否則規則本身會與 `team.md ## Forbidden` 衝突而在學習准入被擋。

#### D-4 稽核欄位本身的稽核性（建議下放 nfr-requirements，非本輪硬規則）

**已查證的事實**：`user_router.py:186` 的 `_audit_append()` 實作是 `logger.info(...)`，寫進容器 stdout。其 docstring 已誠實說明「原本寫入某台開發機的絕對路徑，被 `os.path.exists` 擋著，實際上在任何環境都不會執行」，改走標準 logger。`deploy/docker-compose.deploy.yml` 未設定任何 logging driver 或保存上限；`.github/workflows/deploy.yml:119` 每次合併都執行 `docker compose up -d --build --remove-orphans`，backend 容器被重建、舊容器連同其日誌一併移除。

**推論**：權限稽核事件（誰改了誰的角色、誰重設了權限矩陣）的**實際保存期約等於兩次部署之間的間隔**。在 deploy-on-merge 模式下這可能是數小時。

**這對本 intent 有直接的諷刺性**：本 intent 的價值主張是「提供稽核查驗能力」（scope 文件：`Security_Reviewer` 取得帳號活動證據），但平台自身對「誰改了誰的權限」的稽核軌跡是易失的。ADR-0006 baseline 的四個面向中，audit logging 這一項目前的狀態是「有寫入動作、無保存保證」。

**[建議]**：把「稽核事件需有超出容器生命週期的保存」列為 nfr-requirements 的必答項，**不列為本輪的硬規則**——它需要 observability 的決策，屬於 `project.md ## Deployment` 第 4 點已承認「尚未落地的維運學科」。本輪只需把事實與其對本 intent 的關聯記入 `evidence.md`，讓下游無法宣稱不知情。

---

### E. 給 lead 的整合提醒

- A-3 的兩項掃描器作用域發現，建議**不要**寫成「建議改進」，而是寫成「`project.md ## Forbidden` 現有兩條規則的宣稱與機制不符」。前者會被排進待辦然後遺忘；後者是規則層的正確性問題，會在下一次有人依賴那條規則時立刻造成損害。
- B 段的 `discovered-rules.md` 補登項若採納，`practices-promote` 會把它寫進 `project.md ## Mandated`。措辭已刻意保守到只重述 `CLAUDE.md` 既有文字，應可通過學習准入檢查（不與 `org.md`／`team.md` 任何一層矛盾，只是把既有 `## Decided` 備註升格為操作形式）。
- D-1／D-2 兩項與本 intent 直接相關且成本極低（都是 PR 審查層的要求，不需新工具），建議即使 Q9–Q11 全部選「本輪不做」，這兩項仍應獨立成案。

## Positions

- AGREE: 同意 lead 把 `code-quality-assessment.md` 的 T1–T20 判定為「事實發現而非人類已明述的規則」並排除於 `discovered-rules.md` —— 這是本檔最容易被做錯的地方（把觀察偽裝成規則），lead 的判準正確且說明清楚。
- AGREE: 同意 `team-practices.md ## Code Style` 對「backend 完全無 linter／formatter／type checker」與「依賴 100% 未 pin」的**如實記載而非美化為「待補」**；規則層誠實記載落差，是後續能否修復的前提。
- AGREE: 同意把前端 ESLint 造成的結構約束（`AuthContext` 拆檔、資料抓取拆分＋`cancelled` flag）提升為明文 Code Style 規則。從安全角度這也降低新進開發者／agent 誤用 `useEffect` 造成競態與資料洩漏到已卸載元件的機率。
- OBJECT: `discovered-rules.md` 的結論「本輪沒有遺漏的既有硬約束需要補登」漏掉一項**符合其自身收錄判準**的硬約束 —— ADR-0006 的 security baseline 在 `CLAUDE.md` 第 3 章被人類逐字列為 `Hard constraint（IAM、encryption、network exposure、audit logging）`，卻只以 `project.md:55` 的 `## Decided` 備註存在，且該行指向 `extensions/security/baseline/` 這個 **v2 遷移後全 repo 零命中的路徑**；`## Mandated`／`## Forbidden` 沒有任何對應的操作形式，也沒有任何自動檢查。lead 的檢視清單涵蓋了「規則有沒有被記載」，但沒有檢查「已記載的規則是否還有承載機制」。
- OBJECT: `evidence.md` 把 `scripts/validate_repo_contract.py` 記為「已落地的機制」而未查證其實際作用域，這個未查證直接影響了 `discovered-rules.md` 的結論。實測：`validate_no_obvious_secrets()`（`:347`）只掃 `contract_files()`（`:273`，即 12 個必要檔＋baseline record 必要檔＋audit shard），**完全看不到 `backend/`／`frontend/`／`deploy/`／任何 `.env.example`**；`validate_no_production_config_added()`（`:330`）以 `git diff`（unstaged ∪ staged）為輸入，在 CI 的乾淨 checkout 上恆為空集合，**是 no-op**。`project.md ## Forbidden` 對這兩條都寫「會擋（CI 紅燈）」。這個「規則宣稱強於機制實況」的落差，比 lead 已記載的任何一項規則落差（Prettier 未配置、Black／Ruff 不存在、80% 覆蓋率無法量測）都嚴重，因為它讓團隊以為有 secret 掃描。
- OBJECT: `team-practices.md ## Deployment` 把 `deploy.yml` 的 secrets 檢查記為部署管線的正面特徵，但未指出**它只保護 staging 一條路徑**。`deploy/docker-compose.test.yml:34` 對 JWT 簽章金鑰使用 shell 預設值語法，而該檔正是 `ui-regression` workflow 每個 PR 自動起的 stack —— 這是一條自動化執行、且會落到「有預設金鑰」狀態的路徑，不該被「有 secrets 檢查」的正面敘述覆蓋掉。
- OBJECT: `team-practices.md ## Deployment` 把 `rollback` job 的 `contents: write` ＋ `pull-requests: write` ＋ `actions: write` 判定為「刻意放寬（功能需要），非疏漏」—— 這個判定過早，且把 `code-quality-assessment.md` 列為 P2 的 T20 在 practices 文件裡降級成了「已評估無虞」。三項權限宣告在 job 層、跑在 self-hosted runner 上，該 job 內的**任何**步驟都繼承全部三項；是否可縮窄（改用 GitHub App token，或把「開 revert PR」拆到 `ubuntu-latest` 的獨立最小權限 job）從未被評估過。practices 文件不應替一個未評估的項目背書；正確寫法是記為「刻意放寬且尚未評估可否縮窄（T20）」。
- OBJECT: `evidence.md` 的訪談題 4「HTTP 層測試最低要求」把本 intent 的測試需求整個框在 `TestClient` 覆蓋上，但本 intent 的核心安全變更是**授權矩陣變更**（`Security_Reviewer` 取得 `J3a:view`），而既有的 `test_rbac.py`／`test_j5_authz.py`／`test_review_authz.py` 已在 service 層測授權 —— 缺的不是 `TestClient`，是「權限矩陣變更必須有對應的 allow／deny 雙向測試」，這件事**今天就能寫、不需等 `TestClient` 的決策**。合成一題的後果是：若使用者對 `TestClient` 選了「暫緩」，授權測試會被當成 HTTP 測試的子集一起被推遲。應拆成兩題（見本檔 Q13 選項 B）。
