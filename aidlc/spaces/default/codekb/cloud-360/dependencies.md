# Dependencies — Cloud-360

> 逆向工程產出。**基準 commit `9307dbc`（2026-08-23）**；前一基準為 `c3de2c8`（2026-08-17）。
> **本輪為兩區定向掃描 ＋ 差異標註，不是完整重掃**。節標題後的新鮮度標記：
> **［本輪重寫］**｜**［本輪機械複驗］**｜**［差異標註］**｜**［沿用 `c3de2c8`］**。
> 讀法與跨分支限制見 `reverse-engineering-timestamp.md`。
>
> **用詞提醒**：在標記為［沿用 `c3de2c8`］或［差異標註］的段落內，「本輪／本次」指的是
> **`c3de2c8` 那一輪掃描**；在［本輪重寫］／［本輪機械複驗］段落內，以及任何加 **★** 的
> 條目，指的才是本輪（`9307dbc`，2026-08-23）。
>
> 套件版本清單見 `technology-stack.md`；本檔聚焦**依賴關係與其風險含義**。

## 外部套件依賴 ［差異標註］

### Backend（`backend/requirements.txt`，12 條）

依「若此依賴消失或 breaking change，影響多大」分級：

| 依賴 | 釘選 | 爆炸半徑 | 說明 |
|---|---|---|---|
| `fastapi[standard]` + `uvicorn` | **`==0.141.1`** / 未 pin | **全系統** | 整個 HTTP 面。`[standard]` extra 是隱性依賴來源（httptools、websockets 等未直接宣告） |
| `pydantic` | **`==2.13.4`** | **全系統** | 所有 request/response schema。~~程式碼仍有 v1 風格殘留~~ **★ 本輪已解除**（`orm_mode` → `ConfigDict(from_attributes=True)`） |
| `sqlalchemy` + `psycopg2-binary` | 未 pin | **全系統** | 唯一持久層存取途徑 |
| `claude-agent-sdk` | 未 pin | **A1 + A3 建議階段** | 產圖與改善建議都經此；失效時 A3 降級為 `rules_only`，A1 完全無法產圖 |
| `pyjwt` + `bcrypt` | 未 pin | **全部驗證** | 登入與 token 驗證 |
| `httpx` | 未 pin | 局部 + **測試基礎設施** | n8n webhook 呼叫；**亦為 `starlette.testclient.TestClient` 的前置依賴** |
| `python-dotenv` | 未 pin | 啟動 | `.env` 載入。★ 本輪：唯一呼叫點收斂到 `backend/env_bootstrap.py`，路徑釘死（見 H8） |
| `hypothesis` | 未 pin | 僅測試 | property-based 測試 |
| `passlib[bcrypt]` | 未 pin | **零** | **宣告但程式碼未 import**，可安全移除（全樹未見 `passlib`） |

**未宣告但實際被使用的傳遞依賴**：`fastapi[standard]` extra 帶入的 uvicorn workers、
httptools、websockets 等。WebSocket 端點實際依賴 `websockets`，但該套件**未在
`requirements.txt` 直接列出**，靠 extra 傳遞。若 FastAPI 改變 extra 內容，
WebSocket 功能可能無聲失效 —— 而 WebSocket 又剛好在機械檢查的盲區內（見 `architecture.md`）。

### Frontend（`frontend/package.json`）

| 依賴 | 爆炸半徑 | 說明 |
|---|---|---|
| `react` + `react-dom` (v19) | **全前端** | |
| `react-router-dom` (**v7** ← ★ 本輪 major bump) | **全前端** | 路由與 guard 組合。**v7 的破壞性變更本輪未查證** |
| `html2canvas` + `jspdf` | 局部 | 僅 A3 的 PDF 匯出與 PNG 匯出 |

**唯一有 lockfile 的依賴集合**（`package-lock.json` 已 commit，CI 用 `npm ci`）。

**非宣告依賴**：`openapi-typescript@7.13.0` 以 `npx --yes` 在執行期抓取，
版本字串手寫於兩處且無一致性檢查（見下方 R-8）。

## 依賴釘選現況（與 `team.md` 現行記載不符，待覆核） ［沿用 `c3de2c8`］

> **本節記載的是本次實測到的現況。** `aidlc/spaces/default/memory/team.md` 的
> `## Code Style` 段目前寫「**Backend 依賴 100% 未 pin、無 lockfile**：11 個
> `requirements.txt` 依賴……加 `hypothesis` 共 12 行，**無一有版本約束**」。
> **該記載已被本次實測推翻。**
>
> **規則層的修訂須走 practices-discovery 的 affirmation gate，不由 reverse-engineering
> stage 逕行變更**，故此處只如實記載落差，`team.md` 未被本次 stage 修改。
> 下次 practices-discovery 應覆核本節。

| 項目 | `team.md` 現行記載 | 本次實測（`backend/requirements.txt`） |
|---|---|---|
| 釘選比例 | 「100% 未 pin」「無一有版本約束」 | **2/12 精確釘選**：`fastapi[standard]==0.141.1`、`pydantic==2.13.4` |
| 釘選理由 | （未記載） | 檔頭有逐字說明：OpenAPI 規格輸出在同一版本組下位元決定性、跨版本會飄（實測 20 行差異），不釘會讓規格漂移 gate 在無關 PR 上變紅且與真實漂移不可區分 |
| 釘選形式 | （未記載） | **刻意選 `==` 而非 `~=`** —— 相容釋出形式仍會在次版本線上浮動，選錯等於沒釘 |
| lockfile | 「無 lockfile」 | **仍然成立**（無 `requirements.lock`／`poetry.lock`／`pyproject.toml`） |
| 前後端對照 | 「Frontend 對照組有已 commit 的 `package-lock.json`」 | **仍然成立** |

**正確的現況陳述**：釘選已從「完全沒有」變成「覆蓋兩支最影響規格輸出的依賴」。
但**釘選動機是規格 gate 的訊號可信度，不是供應鏈可重現性** —— 後者仍未解，
其餘 10 支在 CI／Docker build／staging 三處各自解析當下最新版。

## 外部服務依賴 ［差異標註］

| 服務 | 必要性 | 失敗行為 | 設定 |
|---|---|---|---|
| **PostgreSQL** | **必要** | 系統無法啟動 | compose 內的 `db` 服務 |
| **OpenRouter** | **A1／A3 建議必要**（`LLM_PROVIDER=openrouter`，部署預設） | `llm_auth_ready()` 為 false 時回明確錯誤訊息；A3 建議階段降級為 `rules_only` | `ANTHROPIC_BASE_URL=https://openrouter.ai/api`；`OPENROUTER_API_KEY` 映射為 `ANTHROPIC_AUTH_TOKEN` |
| **本機 claude CLI** | A1／A3 建議必要（`LLM_PROVIDER=cli`，本機開發） | 需已 `claude login`；**容器不可用** | macOS Keychain／`~/.claude` |
| **n8n webhook** | **選填** | 用灰底 fallback 圖示並**記 WARNING**，不中斷產圖 | `N8N_WEBHOOK_URL`、`N8N_USER`／`N8N_PASSWORD`（HTTP Basic，可選） |
| **Cloudflare Tunnel** | staging 對外必要 | 外部無法連線；主機內部仍可運作 | `deploy/cloudflared/config.yml`，憑證 0400、以 uid 1000 讀取 |
| **Kiwi TCMS**（`tcms.danniel.cc`） | 流程用，非執行期 | `ui-regression` 無法回報結果；`tcms_sync.py` 需 `~/.tcms.conf` | 於 `dc-infra` repo 維運 |
| **Slack** | 流程用，非執行期 | `deploy.yml` 的 notify job 在 token 未設時整段跳過 | `SLACK_*` secret |

### LLM 供應商切換的環境變數語意（`llm_provider.py`）

這一段的細節容易被誤實作，模組 docstring 有 40+ 行說明：

- `LLM_PROVIDER=cli` 時，**必須 `del` 六個衝突的環境變數，而不是設為空字串** ——
  清空成 `""` 仍會被 Agent SDK 視為「已設定」，導致它嘗試用空憑證連 OpenRouter。
- `ANTHROPIC_API_KEY` **必須留空／不存在**，否則 Agent SDK 會直連 Anthropic 而非 OpenRouter。

### 環境變數依賴 ［本輪重寫］

**本輪新增了一個支配性的環境變數 `APP_ENV`**，它決定其他幾個變數缺值時的行為
（詳見 `architecture.md` 的「`APP_ENV` 閘門」）。

| 變數 | 用途 | 未設定時的行為 |
|---|---|---|
| **`APP_ENV`** ★ | 決定不安全開發預設值是否允許生效。`LOCAL_APP_ENVS = {local, test, ci}` | **預設 `"local"`——最寬鬆的一檔。忘記設等於宣告自己是開發環境**，所有不安全預設值重新啟用，且沒有任何錯誤 |
| `JWT_SECRET` | JWT 簽章金鑰 | ★ **已改為條件式 fail-fast**：`APP_ENV ∈ {local,test,ci}` 才 fallback 到 `INSECURE_DEV_SECRET`；否則 **`raise RuntimeError`（import 期失敗）**。前一版記載的「靜默 fallback」**已失效** |
| **`CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`** ★ | bootstrap admin 的密碼 | 未設且 `APP_ENV` 非 local/test/ci → **不建立 admin 帳號**，只記 log。三個環境（`backend/.env.example`、`deploy/.env.example`／`render-env.sh`、`docker-compose.test.yml`）已全部補上此變數 |
| **`ALLOW_INSECURE_DEFAULT_USERS`** ★ | 明確 opt-in 允許固定密碼帳號 | 預設關；`backend/.env.example` 以註解形式列出 |
| **`ALLOW_INSECURE_DEFAULT_PERSONAS`** ★ | 明確 opt-in 允許建立 11 位 persona demo 帳號 | 預設關（僅 `APP_ENV=local` 自動建立） |
| **`VITE_ENABLE_DEMO_QUICK_USERS`** ★ | 前端登入頁是否顯示 demo 帳號快速填入 | `LoginPage.tsx:13` 的判定為 `import.meta.env.DEV \|\| VITE_ENABLE_DEMO_QUICK_USERS === 'true'`——**dev build 一律顯示**，production build 需明確開啟。宣告於 `frontend/src/vite-env.d.ts:9`、範本於 `frontend/.env.example:23` |
| `LLM_PROVIDER` | LLM 存取模式 | 預設 `openrouter` |
| `OPENROUTER_API_KEY` | LLM 存取 | `llm_auth_ready()` 為 false，A1／A3 建議端點回明確錯誤 |
| `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` | Agent SDK 導向 OpenRouter | 由 `llm_provider` 從 `OPENROUTER_API_KEY` 推導 |
| `ANTHROPIC_API_KEY` | — | **必須留空**，否則 Agent SDK 直連 Anthropic |
| `N8N_WEBHOOK_URL` | 動態圖示 | 直接回 fallback 灰底圖示（**此路徑不記 log**，屬正常路徑） |
| `N8N_USER` / `N8N_PASSWORD` | n8n HTTP Basic | 不帶認證；若 n8n 要求認證則回非 200 → **記 WARNING** + 灰底圖示 |
| `CORS_ORIGINS` | CORS allowlist（逗號分隔） | 預設 `http://localhost:5173,http://127.0.0.1:5173` |
| `VITE_API_BASE_URL` | 前端 API base（**build ARG，非 runtime**） | 改值必須**重建 frontend image**，不能只重啟容器 |
| DB 連線變數 | PostgreSQL | 見 `DEPLOY.md` 與 `.env.example` |

**三環境設定分離**由 `scripts/validate_env_contract.py` 在 CI 強制（六項檢查）：
本機 dev（`backend/.env`、`frontend/.env`）／CI 測試（`docker-compose.test.yml` 內嵌）／
部署（`deploy/.env`，由 `deploy/render-env.sh` 產生）。

**歷史教訓（已成規則）**：新增 compose 消費的變數時，同一個 PR 必須讓 `render-env.sh` 寫它、
`deploy/.env.example` 列它 —— **失敗模式無聲**：無 fallback 的變數缺值時只會變成空字串，
服務照常啟動但功能降級。實例：`N8N_USER`／`N8N_PASSWORD` 曾從未被寫入，
導致每次部署的架構圖 icons 都靜默退回灰底佔位圖。
（**該實例的可觀測性已由 PR #499 改善**：現在至少會留下 WARNING。）

**憑證不得含 `$`**：docker compose 會對 `--env-file` 的值做內插，`ab$cd` 會被無聲截斷成
`ab`，資料庫因此以遠弱於預期的密碼運行且無任何錯誤。`render-env.sh` 已對此擋下。

## 外部平台依賴：GitHub 與 gh-aw ［本輪重寫］

開發流程本身依賴一條在 `c3de2c8` 版本未被記載的外部鏈。**它不影響產品執行期，
但缺了它，本 repo 的品質閘門與流程自動化全部停擺。**

| 依賴 | 必要性 | 失敗行為 | 版本治理 |
|---|---|---|---|
| **GitHub Actions** | 全部 CI／CD／agentic workflow | 無 CI 護欄；deploy-on-merge 停擺 | — |
| **gh-aw**（GitHub Agentic Workflows） | 11 組 workflow 的編譯器與 runtime | 編譯器只在**本機／人工**執行；CI 不跑它。缺它 = 無法產生新的 `.lock.yml`，既有 `.lock.yml` 仍照跑 | **`v0.81.6`**（`actions-lock.json` 以 SHA pin `github/gh-aw-actions/setup@v0.81.6`）。`origin/ut` 已升至 **`v0.86.2`** |
| **GitHub Copilot CLI**（`engine: copilot`） | 11 組 workflow 全部 | `agent` job 失敗 → `ui-regression`（真閘門）擋 PR，其餘 10 組靜默不產出 | `engine_versions.copilot = 1.0.65`（`ut` 上 `1.0.79`），**由 gh-aw 決定，非本 repo 宣告** |
| **ghcr.io 容器**（`gh-aw-firewall`、`github-mcp-server`、`gh-aw-mcpg`） | agent job 執行環境 | 拉取失敗即 job 失敗 | **全部 digest pin** |
| **Projects v2**（尚未使用） | ADR-0013 的目標 | — | **`GITHUB_TOKEN` 不涵蓋 Projects v2 的 GraphQL 寫入**；需 classic PAT 或 GitHub App token，且 ADR-0012／0013 要求**存為獨立 secret、不重用既有的** |

**四個 secret**（列在每個 `.lock.yml` 的 manifest 標頭）：`COPILOT_GITHUB_TOKEN`、
`GH_AW_GITHUB_MCP_SERVER_TOKEN`、`GH_AW_GITHUB_TOKEN`、`GITHUB_TOKEN`。

### 這條鏈的兩個結構性弱點

1. **`.md` ↔ `.lock.yml` 沒有同步守門員**（見 `architecture.md`）。這是一條**真實存在、
   無自動化防護**的失效路徑：改 `.md` 忘記 `gh aw compile`，CI 全綠而行為維持舊的。
2. **升級是一次性大批動作**。PR #532 一個 commit 重編了全部 11 個 `.lock.yml`
   （每個 1,500+ 行的生成檔），**review 面積極大而內容不可人工核對**。
   對照組是 `.github/aw/actions-lock.json`——它小、可讀，是這次升級唯一能被人看懂的 diff
   （`setup-cli` 條目消失、`setup` 換 SHA）。

## 隱性硬依賴 ［差異標註］

這一節是本檔最重要的部分 —— 這些依賴**不在任何依賴宣告檔內**，但缺了系統就壞。

### H1 — backend runtime 需要 Node 22 + Claude Code CLI

`claude-agent-sdk` 的運作方式是 **spawn 一個 `claude` CLI 子行程**，不是純 Python 的
HTTP client。因此 backend 容器內必須具備：

1. **Node.js 22 runtime**
2. **全域安裝的 `@anthropic-ai/claude-code`**（可執行檔 `claude` 在 PATH 上）

這兩者寫在 `backend/Dockerfile`、`DEPLOY.md` 與 `LOCAL-DEV.md`，**但不在 `requirements.txt`**。
一個「只看 requirements.txt 就以為能跑」的環境（例如本機 venv、或某個精簡過的 base image）
會在 **A1 產圖時（請求期）才失敗**，而非建置期，且錯誤訊息未必指向缺少 CLI。

**判定為硬依賴的理由**：影響 A1 全部與 A3 的建議階段，涵蓋系統的兩條核心價值鏈。

**版本治理現況**：`@anthropic-ai/claude-code` 以 `npm i -g` 安裝且**無版本 pin**，
每次 image build 取最新版。

### H2 — `schema_rbac.sql` 只在空 volume 時執行

`deploy/docker-compose.deploy.yml` 把 repo 根目錄的 `schema_rbac.sql` 掛載為
`/docker-entrypoint-initdb.d/01-schema_rbac.sql`。PostgreSQL 官方 image 的行為是
**只在資料目錄為空時執行 initdb 腳本**。

**後果**：既有環境更新 `schema_rbac.sql` **不會**自動生效。schema 演進實際上依賴
`backend/database.py` 的**四個** `_ensure_*_schema()` 在每次啟動時執行的 `ALTER TABLE`。
換句話說，**部署腳本與執行期 schema 是兩條分開的演進路徑**。

### H3 — nginx 的 SSE 設定是功能性依賴

`frontend/nginx.conf` 的 `proxy_buffering off` 與 600 秒 timeout **不是效能調校，是功能前提**。
少了它們，A1 與 A3 的 SSE 串流會被緩衝住（使用者看到長時間空白後一次爆出）或提前斷線。
任何反向代理層的更動都必須保留這兩項。

### H4 — `ci.yml` 的檔名是 load-bearing

`scripts/validate_repo_contract.py` 的 `REQUIRED_FILES` 包含 `.github/workflows/ci.yml`
這個路徑本身。**改名 CI 檔會讓 repo contract 驗證失敗。**

### H5 — 測試依賴 `helpers.py` 的 import 順序與 `StaticPool`

兩個獨立的隱性前提：

1. `backend/tests/helpers.py` 必須在**任何資料庫模組 import 之前**執行
   `sys.modules.setdefault("psycopg2", MagicMock())`，測試才能改走 in-memory SQLite。
   **測試檔的 import 順序因此是有意義的，不能自由重排。**
2. SQLite engine 必須用 **`StaticPool`**。原始碼註解說明：預設的 `SingletonThreadPool`
   會讓每個執行緒拿到各自的空資料庫，而 **`TestClient` 在另一個執行緒裡跑 app**，
   沒有 `StaticPool` 時端點測試會看到 `no such table`。
   **這是 HTTP 層測試能運作的前置條件**，寫新的端點測試時不要換掉它。

### H6 — 產生型別檔與規格檔必須與程式碼同批 commit（本輪新增）

`openapi.json` 與 `frontend/src/types/api.d.ts` 是 **committed 產物**，各有一道 CI gate
比對它們與程式碼是否一致。**改了 `response_model`、路由或查詢參數卻沒重跑產生器，
CI 會紅燈** —— 這是刻意的設計（讓漂移可見），但對不知情的貢獻者是隱性前置條件。

必跑：`python scripts/dump_openapi.py`（backend）與 `npm run gen:types`（frontend）。

### H7 — `LOCAL-DEV.md` 是隱性前置條件的唯一記載處

`LOCAL-DEV.md`（361 行）是**唯一**寫下本機執行全部功能所需隱性前置條件（`claude` CLI
子行程、n8n webhook）的文件，**過期即等於沒有**。既有規則要求異動
`backend/database.py` 的 schema 補丁、`deploy/nginx.conf`、任一 `.env.example` 或
`render-env.sh` 時同步更新它，並由 `local-dev-drift` workflow 在 PR 上提醒（非阻擋）。

### H8 — `APP_ENV` 與 `.env` 的載入路徑（★ 本輪新增）

兩個彼此相依的隱性前提：

1. **`APP_ENV` 決定安全預設值是否啟用，但它自己沒有 fail-fast。**
   `os.environ.get("APP_ENV", "local")` 的預設是最寬鬆的一檔。任何新環境若沒設它，
   會取得已知的 JWT 金鑰與（若同時 opt-in）固定密碼帳號，**且不會有任何錯誤**。
2. **`.env` 只從 `backend/.env` 載入，路徑由 `backend/env_bootstrap.py` 釘死。**
   舊的 `load_dotenv()` 會沿 cwd 往上找第一份 `.env`，**實際發生過載到使用者家目錄
   `.env` 的事故**。`main.py` 與 `database.py` 都必須經由此模組——
   `database.py` 是被 `main.py` 匯入的、比 `main.py` 自己那行更早跑，
   **只修 `main.py` 完全無效**。回歸測試 `tests/test_dotenv_path.py` 守著這件事。

**兩者合起來的失效模式**：`.env` 載錯 → `APP_ENV` 讀不到 → 取預設 `"local"` → 不安全預設值
全部啟用。第 2 點修好之後第 1 點的風險面才收斂，但**「忘記設 `APP_ENV`」本身仍無檢查**。

## 內部跨模組依賴 ［差異標註］

### 依賴方向（Backend）

```
main.py
  └─> 5 個 router
        ├─> rbac ──────> auth ──> activity ──> models ──> database
        ├─> 各自的 orchestrator / service / agent
        └─> models

agent_router ──> prompt_guard （純函式，前置檢查）

orchestrator 層
  ├─> wa_rule_engine   (葉節點，零依賴)
  ├─> wa_lens_engine   (葉節點，零依賴)
  ├─> review_agent / design_agent ──> llm_provider ──> 外部 CLI 子行程
  └─> models

design_agent ──> diagram_builder ──> (選填) n8n webhook
```

**無循環依賴**（掃描未發現）。依賴方向一致由外向內：router → service → engine／model。

### 關鍵內部依賴

| 依賴邊 | 性質 | 風險 |
|---|---|---|
| 5 個 router → `rbac` | 全域橫切，設計意圖 | `rbac` 的任何行為變更影響全部端點 |
| **`auth.get_current_user` → `activity.record_activity`** | **本輪新增的全域橫切** | **使「取得目前使用者」變成有條件的寫入路徑**，影響每一個帶憑證的請求。任何在請求鏈上加副作用的設計都要考慮與它的交互（交易邊界、失敗處理、節流視窗） |
| `rbac` → `rbac_seed_data` | **`STORY_IDS` 由 `DEFAULT_ROLE_PERMISSIONS` 動態導出** | 改 seed 資料即改變全系統的 story 清單 |
| `database.init_db` → `rbac.ensure_role_permissions_seeded` | 啟動時的 seed | 見下方「資料層依賴」 |
| `agent_router` → `review_orchestrator.get_accessible_diagram` | 跨家族依賴 | A1 協作端點需要 A3 的存取判定函式，是唯一的跨家族依賴 |
| `design_agent` / `review_agent` → `llm_provider` | 環境設定集中點 | 兩個 agent 共用；供應商切換的語意錯誤會同時影響兩者 |
| `wa_score_service` → `wa_lens_engine` | 與 A3 同源打分 | 確保協作模式與正式評核用同一套計分 |

### 前端內部依賴

```
App.tsx ──> RouteGuard (ProtectedRoute / CapabilityRoute)
              └─> auth-context (useAuth) ──> AuthContext.tsx (Provider)
pages/* ──> config/api.ts (apiUrl / wsUrl)
         └─> 直接 fetch()，無中介層（52 處，10 支檔）
AdminPage ──> types/api.d.ts（唯一消費者）+ LastActivityCell + PaginationControl
WorkspacePage ──> ChatBox / DrawioCanvas / ShareModal / hooks/useCollaboration
AssessmentPage ──> DiagramPreviewPanel / SuggestionRichText / utils/*
```

**注意**：`AuthContext.tsx` 與 `auth-context.ts` 的拆分是 lint 規則強制的
（`react-refresh/only-export-components`），不是自願的設計選擇。合併兩檔會導致 CI 紅燈。

## 資料層依賴：三份 schema 來源 ［差異標註］

這是全系統最需要小心的依賴結構。

| 來源 | 宣稱角色 | 實際涵蓋 | 何時生效 |
|---|---|---|---|
| `schema_rbac.sql`（**510** 行 ← 本輪複驗） | 新環境唯一要跑的完整腳本；`DEPLOY.md` 指定 | users／user_diagrams／diagram_shares／user_diagram_chats／role_permissions + 308 列 seed／architecture_reviews／wa_lenses／**`users.last_activity_at`**。**缺 J5 全部**；★ **本輪起不再建立任何帳號**（D) 區塊已刪除） | 手動 `psql -f`，或 initdb（**僅空 volume 一次**） |
| `models.py` + `database.py` 的 4 支 `_ensure_*_schema()` | ORM 定義與啟動補丁 | **全部表** + J5 欄位（唯一來源） | **每次後端啟動** |
| `schema.sql`（78 行） | 精簡核心 DDL 參考 | 缺 `wa_lenses`、`role_permissions`、J5 全部；`users.role` 仍 `NOT NULL` | 從不自動執行 |

**執行期的真實權威是第二列。** 任何以 `.sql` 檔推斷 schema 的判斷都會出錯。

`project.md ## Mandated` 把 `schema.sql` 列為「建議一併更新（非 blocking）」，
故它的落後是**規則允許的落差**；但架構層需知道它不是完整 schema。

### 啟動期 DDL 補丁的執行順序

`database.py::init_db()` 依序呼叫：
`_ensure_a4_schema()` → `_ensure_j5_schema()` → `_ensure_a3_schema()` →
`_ensure_last_activity_schema()`，另有 `_apply_security_reviewer_j3a_view(db)`。

**這不是 migration 工具**（無 Alembic、無版本表、無 down 路徑），是冪等的 DDL 補丁函式，
每次啟動全跑一遍。自行管理交易邊界 —— `_apply_security_reviewer_j3a_view` 的 docstring
明寫「不提交則寫入被靜默丟棄」。

### seed 依賴（四個觸發點）

| # | 位置 | 觸發時機 | 行為 |
|---|---|---|---|
| 1 | `schema_rbac.sql` 的 seed 區塊 | 手動 `psql -f`；或 initdb（僅空 volume 一次） | **`DELETE FROM role_permissions;` 後 INSERT 308 列。無條件覆寫，Admin UI 調整會遺失** |
| 2 | `rbac.ensure_role_permissions_seeded()` ← `database.init_db()` | **每次後端啟動** | `force=False`：`count > 0` 即 return（表為空才寫）。`force=True`（僅測試）先 DELETE 再重播 |
| 3 | `database.init_db()` | 空 DB 時 | ★ **本輪已加上 `APP_ENV` 閘門**：11 位 persona 帳號**只在 `APP_ENV=local`**（或 `ALLOW_INSECURE_DEFAULT_PERSONAS`）建立；`admin` 的密碼取自 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`，未設且非 local/test/ci 時**不建立**並記 log |
| 4 | `GET /api/auth/roles/catalog` | **任何匿名請求** | 回應前呼叫 `ensure_role_permissions_seeded(db, force=False)` —— **匿名可達的 seed 路徑** |

### 預設矩陣的雙來源

308 列預設矩陣同時存在於 `schema_rbac.sql` 的 INSERT 與
`backend/services/rbac_seed_data.py` 的 `DEFAULT_ROLE_PERMISSIONS`
（本次以 `ast.literal_eval` 實測：**308 筆 tuple、11 角色、28 story**）。

後者 docstring 寫「由 `schema_rbac.sql` 產生（勿手改；改 SQL 後重跑產生腳本）」，
**但該產生腳本不存在於 repo，CI 也沒有任何一致性檢查**。兩者漂移不會被任何機制發現。

### 單一真實來源的既有副本

| 事實 | 正本 | 副本 |
|---|---|---|
| 角色清單 | `services/rbac.py::CANONICAL_ROLES`（11） | `services/auth.py::require_any_user`（手寫 allowlist，且該 guard 本身是死碼）、`services/user_router.py::ROLE_DISPLAY_NAMES`、`frontend/src/pages/AdminPage.tsx::AVAILABLE_ROLES`（**已與正本順序漂移**）、`schema_rbac.sql` seed |
| ★ **輸入上限**（2 MB／100 則／8,000 字） | （無正本） | REST 側在 `SaveDiagramRequest`／`SaveChatRequest` 的 pydantic 約束；WebSocket 側在 `collab_router` 的手寫檢查。**兩份對等副本，無一致性檢查**（R-16） |
| ★ **gh-aw `.md` 的內容** | `.github/workflows/*.md` | 編譯後的 `.lock.yml`（`frontmatter_hash`／`body_hash` **可**驗一致，但**沒有人在驗**——R-14） |
| 密碼雜湊 | `services/auth.py::get_password_hash` | `database.py::hash_password`（**逐字相同**） |
| 權限預設矩陣 | `schema_rbac.sql` seed 區塊 | `services/rbac_seed_data.py`（產生腳本不存在） |
| 產生器版本字串 | （無正本） | `package.json` 的 `gen:types` 與 `check-api-types.mjs:21` 的 `GENERATOR`，**兩份對等副本** |

**既有規則**：新增第二份物化前必須先確認是否有既有常數或 API 可用；
若確實無法避免（如跨語言邊界），新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試。
**`openapi.json → api.d.ts` 這條鏈正是「跨語言副本 + 一致性檢查」的正確範例**，
可作為處理其餘副本的樣板。

## 依賴風險摘要 ［部分本輪重寫］

| id | 風險 | 影響 | 現有緩解 |
|---|---|---|---|
| **R-1** | Backend **10/12 依賴未 pin 且無 lockfile** | CI／image build／staging 三處各自解析最新版；上游 breaking release 直接打到部署 | **部分**：`fastapi`／`pydantic` 已釘，規格 gate 訊號可信；其餘無 |
| ~~**R-2**~~ | ~~`JWT_SECRET` 有程式內預設值，未注入時靜默用已知金鑰簽 token~~ | — | **★ 本輪已大幅緩解**：`_resolve_secret_key()` 改為僅 `APP_ENV ∈ {local,test,ci}` 允許 fallback，否則 import 期 `RuntimeError`。**降級為 R-2b** |
| **R-2b** ★ | **`APP_ENV` 本身沒有 fail-fast，預設值是最寬鬆的 `"local"`** | 忘記設 `APP_ENV`（或 `.env` 被載錯）→ 不安全預設值全部重新啟用（已知 JWT 金鑰、固定密碼帳號），**且沒有任何錯誤訊息**。安全性取決於一個「未設定即取最寬鬆值」的變數 | `deploy.yml` 的 secrets 檢查保護 staging；`env_bootstrap.py` 把 `.env` 路徑釘死，消除了「載到別人的 `.env`」這條路徑。**但「忘記設 `APP_ENV`」本身沒有任何檢查** |
| **R-3** | H1 隱性硬依賴（Node 22 + Claude Code CLI）不在依賴宣告內 | 環境缺件時 A1／A3 建議在**請求期**才失敗 | 寫在 `Dockerfile`、`DEPLOY.md`、`LOCAL-DEV.md` |
| **R-4** | 三份 schema 來源不一致，J5 物件僅存在於 runtime 補丁 | 新環境的表結構與執行期不符；`.sql` 檔不可作為 schema 依據 | `_ensure_*_schema()` 每次啟動修補 |
| **R-5** | 預設矩陣雙來源無同步驗證（產生腳本不存在） | 兩份 308 列可能漂移，無人察覺 | **無** |
| **R-6** | `schema_rbac.sql` 的無條件 `DELETE FROM role_permissions;` | 「重跑取得新 DDL」與「保留 Admin UI 調整」互斥 —— 而 R-4 的修法正需要重跑 | **無** |
| **R-7** | `websockets` 靠 `fastapi[standard]` extra 傳遞，未直接宣告 | extra 內容變動時 WebSocket 可能無聲失效 | **無**（且 WebSocket 在機械檢查盲區內，兩者疊加） |
| **R-8** | `openapi-typescript` 版本字串手寫兩份 | 兩處不一致時型別 gate 會比對到不同產生器的輸出而**誤報** | **無**（腳本註解已自承此風險） |
| **R-9** | 產生型別檔採用率 1/10 | 9 支 fetch 檔的前後端契約仍無編譯期保護，漏改不報錯 | 部分：`AdminPage` 已接上；e2e 對 Admin 頁有斷言 |
| **R-10** | `@anthropic-ai/claude-code` 與 `cloudflared` 用 `latest`／無 pin | image 重建即換版，行為可能改變 | **無** |
| **R-11** | PostgreSQL 15（本機）vs 16（staging／CI 測試 stack） | 本機測不到的版本差異 | **無** |
| **R-12** | SSE 事件名與 WebSocket 契約無任何機械檢查 | 前後端事件名漂移不會被發現 —— **已實測出一個雙向皆死的契約**（`unsupported`） | **無**；僅靠 `agent_router.py` docstring |
| **R-13** | `auth.get_current_user` 有寫入副作用 | 「取得使用者」不再是純讀取；新增請求鏈行為時易忽略交互 | 節流 5 分鐘限制寫入量；`activity.py` 有 19 個測試、4 個 `@given`。★ 本輪新增一個例外面：`get_user_from_token(..., record=False)`（WebSocket 用）**不記活動**，兩條路徑的活動語意不同 |
| **R-14** ★ | **`.md` ↔ `.lock.yml` 無同步 gate** | 改了 gh-aw 的 `.md` 忘記 `gh aw compile`，**CI 全綠、PR 可合併、行為維持舊的**；反向亦然 | **無**。材料已在檔案裡（`frontmatter_hash`／`body_hash`），沒有人在用 |
| **R-15** ★ | **gh-aw 編譯器版本無漂移偵測** | 那對雜湊涵蓋 `.md` 而非編譯輸出（本輪並排 v0.81.6 與 v0.86.2 實測，雜湊逐字相同），因此「該用新編譯器重編了」偵測不到 | **無**；只能人工比對 `compiler_version` |
| **R-16** ★ | **REST 與 WebSocket 有兩份平行的輸入上限**（2 MB／100 則／8,000 字） | REST 那份在 `openapi.json` 內、被兩道 gate 保護；**WebSocket 那份在盲區內、無任何保護**。兩者漂移只有人工比對會發現 | **無** |
| **R-17** ★ | **Projects v2 在本 repo 沒有先例** | 現有 11 支 workflow 沒有一支寫過 Projects v2；`GITHUB_TOKEN` 不涵蓋其 GraphQL 寫入，需 PAT 或 GitHub App token | ADR-0012／0013 要求獨立 secret、不與其他 agentic workflow 共用 token |

**給下游 stage 的操作提醒**：

- 任何觸及 `users` 表的變更會同時踩到 R-4、R-6，以及 R-9（若碰到非 `AdminPage` 的前端）。
- 任何改變 API 回應形狀的變更會踩到 H6（必須同批重產兩份產物）。
- 任何觸及 WebSocket 或 SSE 事件名的變更**沒有任何機制保護**（R-12、R-16），
  必須以人工審查 + e2e 斷言補上。
- **任何改動 gh-aw `.md` 的變更都會踩到 R-14**：`gh aw compile` 必須在同一個 PR 內跑完並
  commit `.lock.yml`，因為沒有任何檢查會提醒你。
- **`origin/ut` 上的 gh-aw 已是 `v0.86.2`**：在本基準上寫的 workflow 併回 `ut` 時，
  重編產出的 `.lock.yml` 會與本基準不同，**這不是 drift 而是版本差**。

落地檢查清單見 `architecture.md` 的「對新變更的架構約束」。
