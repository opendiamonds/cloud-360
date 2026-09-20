# 元件清冊（Component Inventory）

> Reverse Engineering 合成產物｜repo `cloud`｜工作樹掃描日 2026-09-16｜intent `260916-estimate-upload-rework`｜mode **Full rescan**
> 每個元件標註本次的**驗證深度**：`deep`＝逐檔或逐行讀過，`inventory`＝只做檔名、行數與介面面盤點。深度分佈的正式紀錄在 `reverse-engineering-timestamp.md`；元件名稱即下列 H3 標題，`## Scope of Analysis` 逐字引用它們。

## 後端元件

### backend-app-shell

- **深度**：deep（`backend/main.py` 逐行、`env_bootstrap.py` 介面）
- **職責**：FastAPI 應用組裝——CORS 中介層、startup 事件（`configure_provider_env` + `init_db`）、6 次 `include_router` 掛到 5 個前綴、根端點。
- **依賴**：`services.*` 五個 router、`cost.cost_router`、`database.init_db`、`services.llm_provider`。
- **健康**：healthy。60 行、零商業邏輯，是乾淨的組裝點。
- **關鍵事實**：`main.py:13` 的 `from cost.cost_router import router as cost_router` 是 **`backend/cost/` 唯一的進入邊**。

### persistence-orm

- **深度**：deep（`models.py` 的 class 與 `__tablename__` 全表、`database.py` 的 `init_db` 與 5 支 `_ensure_*_schema` 的 DDL 清單）
- **職責**：SQLAlchemy ORM 定義（11 張表）與啟動時的 schema 補丁。
- **依賴**：PostgreSQL、`psycopg2-binary`（測試中被 mock）。
- **健康**：at-risk。同一份 DDL 有兩個真實來源（`schema_rbac.sql` 與 `_ensure_*_schema()`），無機械一致性檢查；`_ensure_*_schema` 的 raw SQL 不在單元測試覆蓋內（測試走 SQLite in-memory）。

### cost-domain

- **深度**：deep（18 支 `.py` 的 import／export 面逐檔確認；`config.py`、`cost_router.py`、`pricing_client.py` 逐行）
- **職責**：C1 成本估算全域——HTTP 面、業務協調、SKU 對應、查價、Calculator 自動化、agent 建議、稽核。
- **依賴（套件外）**：`database.get_db`、`models`（4 張 C1 表 + `User`／`UserDiagram`）、`services.auth`、`services.rbac`、`services.collab_router` 的**兩個私有函式**、`services.wa_rule_engine.sanitize_mxgraph_xml`、`services.llm_provider`、`services.llm_limits`、`claude_agent_sdk`、`backend/prompts/cost_pricing_agent_system.md`。
- **健康**：at-risk。內部相依無循環且分層清楚，但含兩支 god module（`gcp_calculator_runner.py` 979 行、`azure_calculator_runner.py` 803 行）、跨模組引用私有函式，且 Calculator 路徑在部署環境不可用。
- **關鍵事實**：`backend/services/` 之中**沒有任何模組** import `cost.*`（全域比對確認）。相依方向單向為 `main → cost → services`。

### architecture-generation

- **深度**：inventory（只確認 router 掛載點與公開符號；`diagram_builder.py` 未逐行）
- **職責**：A1 由自然語言產生架構圖——`agent_router`（HTTP）、`prompt_guard`（平台自我竄改預檢）、`design_agent`（LLM）、`diagram_builder`（結構轉 mxGraph XML、向 n8n 取圖示 SVG）。
- **依賴**：`claude_agent_sdk`、`services.llm_provider`、n8n webhook、`backend/prompts/`。
- **健康**：at-risk。`diagram_builder.py` 1,818 行，是 repo 最大的單一模組。

### wa-review

- **深度**：inventory（`wa_rule_engine.py`、`wa_collab_orchestrator.py` 未逐行）
- **職責**：A3 Well-Architected 審核——`review_router`、`review_agent`、`review_orchestrator`、`wa_rule_engine`、`wa_score_service`、`wa_collab_orchestrator`。
- **依賴**：`claude_agent_sdk`（`review_agent`）、`backend/lenses/*.json`、ORM。
- **健康**：at-risk。`wa_rule_engine.py` 973 行；其 `COST-*` 啟發式 findings **不是** TCO 計算，不得當成成本能力（`project.md` `## Forbidden` 已立規則）。`sanitize_mxgraph_xml` 被 `cost.diagram_extractor` 借用。

### lens-management

- **深度**：inventory
- **職責**：WA lens 的 CRUD、驗證與建議（`lens_router`、`lens_service`、`wa_lens_engine`）。
- **依賴**：`backend/lenses/`（AWS／GCP／Azure 各一份 JSON）、ORM、`claude_agent_sdk`（`wa_lens_engine`）。
- **健康**：healthy。

### collaboration

- **深度**：inventory
- **職責**：架構圖 CRUD、聊天歷史、分享、WebSocket 同步（`collab_router`、`collab_suggestions`）。
- **依賴**：ORM、`services.auth`。
- **健康**：at-risk。商業邏輯直寫 handler（無 service 層），且其**私有函式** `_user_can_access_diagram`、`_visible_diagrams` 被 `cost_service.py:43` 跨套件引用。

### identity-and-rbac

- **深度**：inventory（`user_router.py` 896 行未逐行；`rbac_seed_data.py` 的 C1 相關 story id 已確認）
- **職責**：JWT 認證、密碼雜湊、故事級權限評估、角色授權請求、最後活動時間（`user_router`、`auth`、`rbac`、`rbac_seed_data`、`activity`）。
- **依賴**：ORM、`passlib`／`bcrypt`／`pyjwt`。
- **健康**：at-risk。`user_router.py` 為 god module；`rbac_seed_data.py` 有 5 組 C1 系列 story id（`C1`、`C1h`、`C1r`、`C1b`、`C1o`，各 11 列），其中 **`C1b` 已在 seed 裡但無任何程式引用**（B2 budget 的遺留）。

### llm-gateway

- **深度**：inventory（只確認公開函式名）
- **職責**：LLM provider 切換（OpenRouter 或本機 `claude` CLI）與用量限制（`llm_provider`、`llm_limits`）。
- **依賴**：`claude_agent_sdk`、`httpx`。
- **健康**：healthy。被 `cost` 與 `services` 雙邊共用，是跨領域的共享核心。

### openapi-contract

- **深度**：deep（`openapi.json` 以程式列舉全部 45 paths／54 operations）
- **職責**：對外 HTTP 契約的凍結快照，是前端型別與 CI drift 閘門的共同基準。
- **依賴**：`backend/scripts/dump_openapi.py`、精確釘選的 `fastapi`／`pydantic` 版本。
- **健康**：healthy。有雙向 drift 閘門保護。

## 前端元件

### frontend-routing

- **深度**：deep（`frontend/src/App.tsx` 路由表與根導向邏輯）
- **職責**：12 條路由的宣告、`RouteGuard` 掛載、登入後的預設落地頁決策。
- **依賴**：`auth-context` 的 `can()`。
- **健康**：at-risk（對本 intent 而言）。`App.tsx:24` 的根導向第一順位是 `if (can('C1','view'))` → `/cost`，成本頁的存廢會改變所有 FinOps 角色的落地行為。

### frontend-cost-support

- **深度**：deep（`slotRegistry.tsx` 18 行、`supportedRegions.ts` 48 行）
- **職責**：C1 前端的可插拔 slot 註冊與支援區域清單。
- **依賴**：`CostPage`。
- **健康**：degraded。`slotRegistry.tsx` 的兩個 slot 名稱 `cost-overspend`／`cost-banner` 對應 B2 功能，E2E 明確斷言這些 testid 命中數為 0（ADR-C1-08 規定 B1 不得渲染）——**是刻意未啟用的死碼**。

### frontend-cost-page

- **深度**：inventory（964 行，只讀 API 呼叫段落）
- **職責**：`/cost` 頁面——圖選擇、逐項成本表、區域與時數控件、覆寫操作、Calculator 匯出。
- **依賴**：`/api/cost` 9 個端點、`frontend-cost-support`、`src/config/api.ts`。
- **健康**：at-risk。964 行的 god component；`CostPage.tsx:705` 在 UI 上要求使用者自行執行 `playwright install chromium`，等於把部署缺陷轉嫁為使用者指示。

### frontend-shell

- **深度**：inventory
- **職責**：`Layout`、`Sidebar`（含 `NavLink to="/cost"`，`Sidebar.tsx:201`）、`RouteGuard`、`NavChromeContext`、`auth-context`。
- **依賴**：`/api/auth/me`。
- **健康**：healthy。

### frontend-feature-pages

- **深度**：inventory（僅行數盤點與 `/api/cost` 呼叫點定位）
- **職責**：其餘 8 頁——Workspace（A1）、Assessment（A3）、Admin、RolePermissions、AuthorizationRequests、Login、Forbidden、WaitingApproval，以及 12 個共用元件。
- **依賴**：`/api/architecture`、`/api/auth`、`/api/collab`、embed.diagrams.net。
- **健康**：at-risk。`AssessmentPage.tsx` 1,861 行、`WorkspacePage.tsx` 1,194 行為 god component。

## 契約、CI 與部署元件

### contract-validators

- **深度**：deep（三支皆為本次深度分析對象）
- **職責**：CI `repo-contract` job 的三連發機械閘門。
  1. `scripts/validate_repo_contract.py`——必要檔／必要文字／繁中／禁止 `prod`｜`production`｜`secrets` 路徑／禁止憑證字串。
  2. `scripts/validate_env_contract.py`——六項環境設定檢查，其中 `validate_local_dev_template_is_complete()` **反向掃描** `backend/` 讀到的所有環境變數並強制它們記載於 `backend/.env.example`。
  3. `scripts/validate_cost_calculator_boundary.py`——以**硬編碼路徑** `backend/cost/cost_calculator.py` 檢查它不得 import `httpx`／`requests`／`sqlalchemy`／`fastapi`；**檔案不存在即 `return 1`（CI 紅燈）**。
- **依賴**：repo 檔案系統佈局本身。
- **健康**：at-risk（對本 intent 而言）。第 2、3 支與 C1 的檔案佈局硬綁定，退役動作若不同步修改它們會直接讓 CI 紅燈。

### ci-core

- **深度**：deep（`.github/workflows/ci.yml` 逐行）
- **職責**：5 個 job——`gate`（同步回寫閘門）、`repo-contract`、`frontend`（lint + `tsc -b` + build + `check:types`）、`backend`（import smoke + `unittest` + OpenAPI `--check`）、`docker-build`（buildx 兩個 image，`push: false`）。
- **依賴**：`contract-validators`、`openapi-contract`、`backend-test-suite`。
- **健康**：healthy，但覆蓋面有結構性盲區（見 `code-quality-assessment.md`）。

### agentic-workflows

- **深度**：inventory（只確認檔名與 Playwright／`COST_PRICING_USE_SDK` 出現位置）
- **職責**：11 支 gh-aw agentic workflow（`.md` 規格 + `.lock.yml` 產物成對）：`ui-regression`、`pr-reviewer`、`spec-sync`、`code-drift-alert`、`contract-guard`、`deploy-doctor`、`local-dev-drift`、`lint-fix`、`issue-triage`、`daily-digest`、`release-watch`，另 7 支 `aidlc-sync-*`。
- **依賴**：GitHub Actions、Copilot engine、Kiwi TCMS。
- **健康**：at-risk。`ui-regression` 是真閘門（讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`）；其餘多為建議型。

### deploy-workflow

- **深度**：inventory（只定位 `COST_PRICING_USE_SDK` 與 AWS 憑證段落）
- **職責**：`.github/workflows/deploy.yml`——PR 合併進 `ut` 或手動觸發，於自架 runner 部署至 `192.168.10.10`，含 rollback job（還原 last-good、開 revert PR、dispatch Deploy Doctor）。
- **依賴**：`deployment-compose`、`deployment-config`。
- **健康**：at-risk。rollback job 權限為 `contents: write` + `pull-requests: write` + `actions: write`，刻意放寬且尚未評估可否縮窄。**本檔目前有未提交的工作樹修改**（移除 AWS 帳號憑證傳遞）。

### deployment-compose

- **深度**：deep（`deploy/docker-compose.deploy.yml` 逐行）
- **職責**：4 個服務的部署拓樸——`db`（Postgres 16-alpine，volume `cloud360_db`）、`backend`、`frontend`、`cloudflared`。
- **依賴**：`deploy/.env`（由 `render-env.sh` 產生）、`schema_rbac.sql`（掛進 `docker-entrypoint-initdb.d`）。
- **健康**：at-risk。`DATABASE_URL` 與 `VITE_API_BASE_URL` 由 compose 自行推導，範本不得重複設定；無 fallback 的變數缺值時只會變成空字串並靜默降級。

### deployment-config

- **深度**：inventory（以關鍵字定位 `COST_PRICING_*` 與 AWS 憑證段落）
- **職責**：`deploy/render-env.sh`（`deploy/.env` 的唯一產生點）、`deploy/.env.example`、`deploy/docker-compose.test.yml`（CI 測試 stack）、`backend/.env.example`、cloudflared 設定、`deploy/nginx.conf`。
- **依賴**：`validate_env_contract.py` 的六項檢查。
- **健康**：at-risk。`deploy/.env.example:94-95` 仍保留註解掉的 AWS 憑證行，與 `DEPLOY.md:126` 的明文宣告矛盾。`render-env.sh` 與 compose 目前有未提交的工作樹修改。

### schema-sql-assets

- **深度**：inventory（只比對成本相關 DDL 的有無與位置）
- **職責**：`schema.sql`（無任何成本 DDL）與 `schema_rbac.sql`（成本 DDL 在 169-212 行，含 RBAC seed）。
- **依賴**：`deployment-compose` 的 initdb 掛載。
- **健康**：degraded。只在空 volume 生效，與 `persistence-orm` 的啟動補丁形成雙軌。

### ops-and-sync-scripts

- **深度**：inventory（`warm_aws_pricing_cache.py` 的 import 面已確認）
- **職責**：`scripts/warm_aws_pricing_cache.py`（預熱價目快取，`42-44` 行直接 import `cost.config`／`cost.price_cache`／`cost.pricing_client`）、`scripts/tcms_validate.py`、`scripts/tcms_sync.py`、3 支 `aidlc_sync_*.py`、`backend/scripts/dump_openapi.py`、2 支 Azure Calculator spike。
- **依賴**：`cost-domain`（僅 `warm_aws_pricing_cache.py`）、Kiwi TCMS API。
- **健康**：at-risk。`warm_aws_pricing_cache.py` 是 `cost` 套件的第二個外部消費者，刪 `price_cache.py` 會讓它壞掉。

## 測試與靜態資產

### backend-test-suite

- **深度**：inventory（43 檔以檔名、行數、框架 import 與 `cost.*` patch 目標統計；未逐案閱讀）
- **職責**：`unittest` + `hypothesis` 測試，5,277 行；其中 **17 檔屬 C1**。
- **依賴**：`backend/tests/helpers.py`（以 `MagicMock` 取代 `psycopg2`、SQLite in-memory + `StaticPool`）。
- **健康**：at-risk。多支以 `@patch("cost.<module>.<symbol>")` 字串路徑 patch，模組改名會**靜默失效**而非報錯。

### frontend-e2e-suite

- **深度**：inventory（只讀 C1 成本頁那一段的規格註解）
- **職責**：`frontend/tests/e2e/regression.spec.ts`（667 行單檔，Playwright chromium）。
- **依賴**：`deploy/docker-compose.test.yml` 的短生命週期 stack（內嵌 `COST_PRICING_STUB=1`）。
- **健康**：at-risk。第 492 行起的成本頁回歸依賴 stub 的硬編碼期望值 `$86.40 / 月`。

### static-prompt-assets

- **深度**：inventory（僅列檔名）
- **職責**：`backend/prompts/`（4 支 system prompt + 3 份 drawio 範本）、`backend/lenses/`（3 份 WA lens JSON）。
- **依賴**：以路徑載入，無 import 關係。
- **健康**：at-risk。`cost_pricing_agent_system.md` 在 agent 拆除後會成為孤兒檔，沒有任何機械檢查會發現。

## 外部與基礎設施

| 元件 | 角色 |
|---|---|
| PostgreSQL 16-alpine | 全域單一資料庫，11 張表 |
| embed.diagrams.net | 前端直連的互動圖編輯運行時 |
| OpenRouter 或本機 `claude` CLI | A1／A3／C1 的 LLM 推論後端 |
| n8n webhook | 架構圖元件圖示 SVG（Basic Auth；失敗降級灰底佔位圖） |
| AWS／Azure／GCP 公開價目端點 | C1 取價來源 |
| Azure／GCP Calculator 網頁 | C1 匯出估價檔來源（需 Playwright 瀏覽器） |
| 自架 runner + Cloudflare Tunnel | `192.168.10.10` → `cloud360.danniel.cc` |
| Kiwi TCMS | 測案管理（`tcms.danniel.cc`，於 `dc-infra` repo 維運） |
