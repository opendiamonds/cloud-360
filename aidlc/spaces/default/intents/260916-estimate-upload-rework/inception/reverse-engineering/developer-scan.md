# Developer Code Scan — cloud（Cloud-360）

- 掃描時間：2026-09-16
- 倉庫：`cloud`（單一 repo，workspace root 即 repo root）
- 專案型態：brownfield
- 實際掃描到的 HEAD：`cd2754d291eb37086646d80f1fed2abf209e9805`（2026-09-16 11:32:20 +0800）
- 指派單所鎖定的 source fingerprint：`git:37b327b8bdc49dac2a2e0974270f8944f2abd9c8`（**與實際 HEAD 不符，見「異常」段**）
- 掃描廣度：全 repo 重新掃描；深度：Standard

## Developer Code Scan Results

### Scan Coverage

- **Analyzed deeply**：
  - `backend/cost/`（全部 18 支 `.py` 的 import／export 面逐檔確認；`config.py`、`cost_router.py`、`pricing_client.py` 逐行讀完；`cost_service.py`、`cost_pricing_agent.py` 讀完全部函式簽名與授權段落）
  - `backend/main.py`（逐行）
  - `backend/models.py`（class 與 `__tablename__` 全表清單）
  - `backend/database.py`（`init_db` 與五支 `_ensure_*_schema` patch 的 DDL 清單）
  - `backend/Dockerfile`（逐行）
  - `backend/requirements.txt`（逐行）
  - `scripts/validate_cost_calculator_boundary.py`（逐行）
  - `scripts/validate_repo_contract.py`（`REQUIRED_FILES`／`REQUIRED_RECORD_FILES`／`REQUIRED_TEXT` 前段）
  - `scripts/validate_env_contract.py`（六項檢查的函式清單與 `backend/.env.example` 反向比對規則）
  - `.github/workflows/ci.yml`（逐行）
  - `deploy/docker-compose.deploy.yml`（逐行）
  - `openapi.json`（以程式列舉全部 45 paths／54 operations）
  - `frontend/package.json`、`frontend/src/App.tsx` 路由表、`frontend/src/cost/slotRegistry.tsx`、`frontend/src/cost/supportedRegions.ts`
- **Skimmed only**：
  - `backend/services/`（22 支模組：只確認對外 router 掛載點、被 `backend/cost/` 引用的符號，以及 `llm_provider`／`llm_limits` 的公開函式名；未逐行讀 `diagram_builder.py`、`wa_rule_engine.py`、`wa_collab_orchestrator.py` 等大檔）
  - `backend/tests/`（43 支測試：以檔名、行數、測試框架 import 與 `cost.*` patch 目標統計；未逐案閱讀）
  - `frontend/src/pages/`、`frontend/src/components/`、`frontend/src/utils/`（只做行數盤點與 `/api/cost` 呼叫點定位；`CostPage.tsx` 只讀 API 呼叫段落，未逐行）
  - `frontend/tests/e2e/regression.spec.ts`（只讀 C1 成本頁那一段的規格註解）
  - `deploy/render-env.sh`、`deploy/.env.example`、`deploy/docker-compose.test.yml`、`backend/.env.example`（以關鍵字定位 `COST_PRICING_*`／AWS 憑證段落，未逐行）
  - `.github/workflows/` 其餘 31 個檔（只確認檔名與 Playwright／`COST_PRICING_USE_SDK` 出現位置）
  - `schema.sql`、`schema_rbac.sql`（只比對成本相關 DDL 的有無與位置）
  - `README.md`、`DEPLOY.md`、`LOCAL-DEV.md`、`TESTING.md`、`CLAUDE.md`、`AGENTS.md`（關鍵字定位）
  - `backend/prompts/`、`backend/lenses/`（僅列檔名，未讀內容）
- **Noted only（依指派單排除深度分析）**：`.claude/`（272 檔，upstream AI-DLC 框架）、`aidlc/`（776 檔，AI-DLC 工作區）

### Packages Found

追蹤檔總數依頂層目錄：`aidlc/` 776、`.claude/` 272、`backend/` 120、`.github/` 109、`frontend/` 64、`scripts/` 9、`deploy/` 5。應用程式碼為 `backend/` + `frontend/` 共 184 檔。

| 套件／目錄 | 類型 | 語言 | 用途 |
|---|---|---|---|
| `backend/` | FastAPI 應用（flat module，非 package） | Python 3.12 | API 進入點 `main.py`，掛 6 個 router |
| `backend/cost/` | 領域套件（18 py + 10 yaml/fixture，6,382 行） | Python | C1 成本估算：查價、SKU 對應、Calculator 自動化、agent |
| `backend/services/` | 領域服務（22 py，約 8,000 行） | Python | auth／RBAC／協作／架構圖產生／WA review／LLM provider |
| `backend/tests/` | 測試（43 檔，5,277 行） | Python | `unittest` + `hypothesis` |
| `backend/prompts/` | 靜態資產 | Markdown／XML | 4 支 system prompt + 3 份 drawio 範本 |
| `backend/lenses/` | 靜態資產 | JSON | WA lens 定義（AWS／GCP／Azure 各一） |
| `backend/scripts/` | 工具 | Python | `dump_openapi.py`、2 支 Azure Calculator spike |
| `frontend/` | SPA | TypeScript／React 19 | Vite + Tailwind 4，9 個頁面 |
| `frontend/src/cost/` | 前端 C1 輔助 | TypeScript | `slotRegistry.tsx`（18 行）、`supportedRegions.ts`（48 行） |
| `frontend/tests/e2e/` | E2E | TypeScript | Playwright（667 行單檔） |
| `scripts/` | repo 層工具（9 檔，2,477 行） | Python | 3 支契約驗證、2 支 TCMS、3 支 AIDLC 同步、1 支快取預熱 |
| `deploy/` | 部署設定 | YAML／Shell | compose（deploy／test）、`render-env.sh`、cloudflared |

### 🔴 `backend/cost/` 相依全圖（ASSUM-04 去風險的核心產出）

#### 套件內部有向邊（`A → B` 表示 A import B）

```
cost_router      → cost_service
cost_service     → config, cost_calculator, azure_calculator_runner,
                   gcp_calculator_runner, cost_pricing_agent,
                   diagram_extractor, price_cache, pricing_client,
                   sku_mapper, sku_ai_resolver
cost_pricing_agent → azure_calculator_runner, config, diagram_extractor,
                   gcp_calculator_runner, pricing_client, sku_mapper,
                   sku_ai_resolver
pricing_client   → config, pricing_gcp, pricing_azure,
                   pricing_offer_parser, pricing_sdk
pricing_sdk      → config, pricing_query_parser
pricing_azure    → config, pricing_units
pricing_gcp      → config, pricing_units
pricing_offer_parser  → pricing_units
pricing_query_parser  → pricing_units
sku_ai_resolver  → config, sku_mapper
sku_mapper       → config
azure_calculator_runner → config
gcp_calculator_runner   → config, gcp_calculator_product_resolver,
                          sku_ai_resolver
gcp_calculator_product_resolver → config, sku_ai_resolver
price_cache      → （套件內無；只依賴 models.PricingCache）
cost_calculator  → （純函式，零套件內相依，亦零 I/O 相依）
config           → （葉節點；讀 9 份 YAML）
```

文字說明（Mermaid fallback）：`cost_router` 是唯一的 HTTP 入口，單向呼叫 `cost_service`；`cost_service` 是扇出最廣的協調層（10 條內部邊）；`config` 是扇入最廣的葉節點（12 個模組引用）；`cost_calculator` 是唯一零相依的純函式模組；無偵測到循環引用。

#### 反向索引（誰 import 誰）

| 模組 | 套件內引用者 | 套件外引用者 |
|---|---|---|
| `config.py` | 12 個模組（見上） | `scripts/warm_aws_pricing_cache.py` |
| `pricing_units.py` | `pricing_azure`, `pricing_gcp`, `pricing_offer_parser`, `pricing_query_parser` | `tests/test_pricing_units.py` |
| `pricing_offer_parser.py` | `pricing_client` | `tests/test_pricing_client.py` |
| `pricing_query_parser.py` | `pricing_sdk` | 無 |
| `pricing_sdk.py` | `pricing_client` | `tests/test_pricing_sdk.py` |
| `pricing_azure.py` | `pricing_client` | `tests/test_pricing_azure.py` |
| `pricing_gcp.py` | `pricing_client` | `tests/test_pricing_gcp.py` |
| `pricing_client.py` | `cost_service`, `cost_pricing_agent` | `scripts/warm_aws_pricing_cache.py`, `tests/test_pricing_client.py`, `tests/test_pricing_azure.py` |
| `price_cache.py` | `cost_service` | `scripts/warm_aws_pricing_cache.py` |
| `sku_mapper.py` | `sku_ai_resolver`, `cost_service`, `cost_pricing_agent` | `tests/test_sku_mapper.py`, `tests/test_sku_ai_resolver.py` |
| `sku_ai_resolver.py` | `cost_service`, `cost_pricing_agent`, `gcp_calculator_product_resolver`, `gcp_calculator_runner` | `tests/test_sku_ai_resolver.py` |
| `diagram_extractor.py` | `cost_service`, `cost_pricing_agent` | `tests/test_diagram_extractor.py` |
| `cost_calculator.py` | `cost_service` | `tests/test_cost_calculator.py`, **`scripts/validate_cost_calculator_boundary.py`（CI 關卡，以路徑讀檔）** |
| `azure_calculator_runner.py` | `cost_service`, `cost_pricing_agent` | `tests/test_azure_calculator_runner.py`, `tests/test_azure_calculator_live.py` |
| `gcp_calculator_runner.py` | `cost_service`, `cost_pricing_agent` | `tests/test_gcp_calculator_runner.py` |
| `gcp_calculator_product_resolver.py` | `gcp_calculator_runner` | `tests/test_gcp_calculator_product_resolver.py` |
| `cost_pricing_agent.py` | `cost_service` | `tests/test_cost_pricing_agent.py` |
| `cost_service.py` | `cost_router` | `tests/test_cost_api*.py`（3 檔，透過 TestClient） |
| `cost_router.py` | 無 | **`backend/main.py:13`** |

#### `backend/cost/` → 套件外的相依（拆除時會留下的孤兒／需保留的介面）

| 來源 | 目標（套件外） | 備註 |
|---|---|---|
| `cost_router.py` | `database.get_db`, `models.User`, `services.auth.get_current_user` | 標準 FastAPI 依賴 |
| `cost_service.py` | `models.CostAuditEvent/DiagramCost/DiagramCostLine/User/UserDiagram` | 4 張待退役表 |
| `cost_service.py` | **`services.collab_router._user_can_access_diagram`、`_visible_diagrams`（私有函式跨模組引用）** | 破壞封裝，重寫時需重新決定授權來源 |
| `cost_service.py` | `services.rbac.user_can` | C1／C1h／C1r／C1o 權限檢查 |
| `diagram_extractor.py` | `services.wa_rule_engine.sanitize_mxgraph_xml` | 新的上傳解析路徑若仍讀 mxGraph XML 會需要它 |
| `sku_ai_resolver.py` | `services.llm_provider`（4 個符號） | OpenRouter／CLI provider 切換 |
| `gcp_calculator_product_resolver.py` | `services.llm_provider.llm_auth_ready` | |
| `gcp_calculator_runner.py` | `services.llm_provider.llm_auth_ready` | |
| `cost_pricing_agent.py` | `claude_agent_sdk`（外部套件）、`services.llm_limits.agent_sdk_env`、`services.llm_provider` | 遷移 LangGraph 的正面戰場 |
| `cost_pricing_agent.py` | `backend/prompts/cost_pricing_agent_system.md`（以路徑載入） | 拆除時會變孤兒檔 |
| `price_cache.py` | `models.PricingCache` | |
| `config.py` | 9 份同目錄 YAML | 見下 |

**反向確認**：`backend/services/*.py` 之中**沒有任何一支** import `cost.*`（已全域比對）。相依方向是單向的 `main → cost → services`，這對退役有利。

#### `backend/cost/` 的非 Python 資產（9 份 YAML + 2 份 fixture）

`aws_region_locations.yaml`、`calculator_azure_map.yaml`、`calculator_azure_regions.yaml`、`calculator_gcp_map.yaml`、`calculator_gcp_regions.yaml`、`pricing_coverage.yaml`、`pricing_urls.yaml`（307 行，含 allowlist_hosts 與 AWS 產品規格）、`sku_map.yaml`（263 行）、`supported_regions.yaml`；`fixtures/azure_calculator_stub.html`、`fixtures/gcp_calculator_stub.json`。全部由 `config.py` 在 **import 時**載入——`config.py` 一旦保留，這些 YAML 就不能刪；反之若 `pricing_client.py` 要留下當作 agent 的查價工具，至少 `pricing_urls.yaml`、`pricing_coverage.yaml`、`aws_region_locations.yaml`、`supported_regions.yaml` 必須跟著留。

### Build System

- **Type**：多套件並行——pip（backend）、npm（frontend）、Docker／docker compose（部署）
- **Config Files**：`backend/requirements.txt`、`backend/Dockerfile`、`frontend/package.json`＋`package-lock.json`、`frontend/Dockerfile`、`frontend/vite.config.ts`、`frontend/tsconfig{,.app,.node}.json`、`frontend/tailwind.config.js`、`frontend/postcss.config.js`、`frontend/eslint.config.js`、`frontend/playwright.config.ts`、`docker-compose.yml`（根）、`deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml`、`deploy/render-env.sh`
- **Build Dependencies**：
  - `backend/main.py` → `cost.cost_router`（唯一的 cost 掛載邊）
  - `openapi.json` ← `backend/scripts/dump_openapi.py`（CI 以 `--check` 擋漂移）
  - `frontend/src/types/api.d.ts` ← `openapi.json`（`npm run gen:types`，CI 以 `npm run check:types` 擋漂移）
  - `deploy/.env` ← `deploy/render-env.sh`（`validate_env_contract.py` 強制 workflow 不得繞過）
  - db 初始化 ← `schema_rbac.sql`（掛進 `docker-entrypoint-initdb.d`），**僅在空 volume 生效**；既有環境靠 `backend/database.py` 的 `_ensure_*_schema()` 補丁

### APIs Discovered

`openapi.json` 共 **45 paths／54 operations**，全部前綴 `/api/*`（另加根 `GET /`）。

| 群組 | 掛載點 | operations |
|---|---|---|
| architecture（agent／review／lens） | `/api/architecture` | 16 |
| auth／user／RBAC | `/api/auth` | 16 |
| collab | `/api/collab` | 12 |
| **cost（C1，本次退役目標）** | `/api/cost` | **9** |
| root | `/` | 1 |

**`/api/cost` 的 9 個 operations（與 `cost_router.py` 逐一核對一致）**：

1. `GET /api/cost/diagrams` → `cost_service.list_diagrams`
2. `GET /api/cost/diagrams/{diagram_id}`（query `run_agent`，預設 `true`）→ `get_snapshot`
3. `GET /api/cost/diagrams/{diagram_id}/audit` → `get_audit`
4. `GET /api/cost/diagrams/{diagram_id}/calculator-export/csv`（GCP）→ `export_calculator_excel`
5. `GET /api/cost/diagrams/{diagram_id}/calculator-export/xlsx`（Azure）→ `export_calculator_excel`
6. `PUT /api/cost/diagrams/{diagram_id}/region` → `apply_region`（story `C1r`）
7. `PUT /api/cost/diagrams/{diagram_id}/lines/{mxcell_id}/hours` → `apply_hours`（story `C1h`）
8. `PUT /api/cost/diagrams/{diagram_id}/lines/{mxcell_id}/override` → `apply_override`（story `C1o`）
9. `PUT /api/cost/diagrams/{diagram_id}/lines/{mxcell_id}/sku` → `apply_sku`（story `C1o`）

**內部 API（非 HTTP）**：`cost_pricing_agent.py` 以 `claude_agent_sdk` 自建一個 in-process MCP server `cloud360-cost`，暴露 3 個 tool：`list_mapped_resources`、`fetch_official_hourly`、`run_azure_calculator_estimate`（FQN 形如 `mcp__cloud360-cost__<tool>`）。遷移 LangGraph 時這 3 個 tool 契約是唯一的 agent 介面定義。

**前端路由表（`frontend/src/App.tsx`）**：`/login`、`/403`、`/waiting-approval`、`/workspace`、`/assessment`、`/cost`、`/admin/users`、`/admin/authorization-requests`、`/admin/role-permissions`、`/admin`（redirect）、`/`（redirect）、`*`。

### Frameworks & Libraries

**backend（`requirements.txt`）**

| 名稱 | 版本 | 用途 |
|---|---|---|
| `fastapi[standard]` | `==0.141.1`（精確釘選） | Web 框架；與 pydantic 一起釘死是為了 `openapi.json` 的位元決定性 |
| `pydantic` | `==2.13.4`（精確釘選） | 資料驗證／OpenAPI schema |
| `uvicorn` | 未釘 | ASGI server |
| `httpx` | 未釘 | 查價 HTTP client（AWS Bulk／Azure Retail／GCP Catalog／OpenRouter） |
| `sqlalchemy` | 未釘 | ORM |
| `psycopg2-binary` | 未釘 | Postgres driver（測試中被 mock） |
| `passlib[bcrypt]`／`bcrypt`／`pyjwt` | 未釘 | 認證 |
| `python-dotenv` | 未釘 | `env_bootstrap.py` |
| `claude-agent-sdk` | 未釘 | **本次要換成 LangGraph／OpenRouter** |
| `hypothesis` | 未釘 | property-based testing（ADR-0006 hard constraint） |
| `PyYAML` | `>=6.0` | `cost/config.py` |
| `boto3` | 未釘 | **僅 `cost/pricing_sdk.py` 使用；該檔要刪，boto3 即可從 requirements 移除** |
| `playwright` | 未釘 | **Azure／GCP Calculator runner；退役後可移除** |

**frontend（`package.json`）**：React `^19.2.6`、react-dom `^19.2.6`、react-router-dom `^7.18.2`、html2canvas `^1.4.1`、jspdf `^4.2.1`；dev 端 Vite `^8.0.12`、TypeScript `~6.0.2`、ESLint `^10.3.0`、typescript-eslint `^8.59.2`、Tailwind `^4.3.0`、`@playwright/test` `^1.56.0`、`@types/node` `^24.12.3`。

**其他 runtime**：Postgres 16-alpine、Node 22（backend 映像內，為 `claude-agent-sdk` 需要的 `@anthropic-ai/claude-code` CLI）、cloudflared。

### Test Coverage

- **Test Directories**：`backend/tests/`（43 檔、5,277 行）、`frontend/tests/e2e/`（1 檔、667 行）
- **Test Frameworks**：`unittest`（全部 backend 測試）＋ `hypothesis`（7 檔：`test_activity`、`test_auth`、`test_collab`、`test_cost_calculator`、`test_design_agent`、`test_diagram_builder`、`test_diagram_icons`）；前端 `@playwright/test`
- **執行方式**：CI 為 `python -m unittest discover -s tests -v`（backend job）、`npx playwright test`（`ui-regression` workflow，對短生命週期 test stack）
- **Coverage Config**：**absent**——repo 內無 `.coveragerc`、`pytest.ini`、`pyproject.toml` 或任何覆蓋率門檻設定；沒有數字化的覆蓋率把關
- **測試替身**：`backend/tests/helpers.py` 以 `MagicMock` 取代 `psycopg2`，並用 SQLite in-memory + `StaticPool` 建 session；因此 **backend 單元測試從未跑過真正的 Postgres DDL**（`_ensure_*_schema` 的 raw SQL 不在單元測試覆蓋內）
- **C1 相關測試共 17 檔**：`test_cost_api`、`test_cost_api_azure_agent`、`test_cost_api_gcp_agent`、`test_cost_calculator`、`test_cost_pricing_agent`、`test_azure_calculator_runner`、`test_azure_calculator_live`、`test_gcp_calculator_runner`、`test_gcp_calculator_product_resolver`、`test_diagram_extractor`、`test_pricing_azure`、`test_pricing_client`、`test_pricing_gcp`、`test_pricing_sdk`、`test_pricing_units`、`test_sku_ai_resolver`、`test_sku_mapper`。其中多支以 `@patch("cost.<module>.<symbol>")` 字串路徑 patch，模組改名會靜默失效而非報錯。

### Code Quality Indicators

- **Linting**：前端 ESLint（`frontend/eslint.config.js`，CI `npm run lint`）＋ `tsc -b`。**backend 無 linter 也無 formatter**（repo 內無 ruff／flake8／black／mypy 設定），Python 端唯一的機械把關是 import smoke test 與三支自製契約腳本。
- **CI/CD**：`.github/workflows/` 共 33 檔。核心是 `ci.yml`（5 jobs：`gate` 同步回寫閘門、`repo-contract`、`frontend`、`backend`、`docker-build`）與 `deploy.yml`（自架 runner 部署至 `192.168.10.10`）。其餘為 gh-aw agentic workflows（`.md` 規格 + `.lock.yml` 產物成對）：`ui-regression`、`pr-reviewer`、`spec-sync`、`code-drift-alert`、`contract-guard`、`deploy-doctor`、`local-dev-drift`、`lint-fix`、`issue-triage`、`daily-digest`、`release-watch`，以及 7 支 `aidlc-sync-*`。
- **契約閘門（`repo-contract` job 三連發）**：
  1. `scripts/validate_repo_contract.py` — 必要檔／必要文字／繁中／禁止 `prod`｜`production`｜`secrets` 路徑／禁止憑證字串
  2. `scripts/validate_env_contract.py` — 六項；其中 `validate_local_dev_template_is_complete()` **反向掃描 `backend/` 讀到的所有環境變數，強制它們都記載於 `backend/.env.example`**
  3. `scripts/validate_cost_calculator_boundary.py` — **以硬編碼路徑 `backend/cost/cost_calculator.py` 檢查它不得 import `httpx`／`requests`／`sqlalchemy`／`fastapi`；檔案不存在即 return 1（紅燈）**
- **漂移雙閘門**：`python scripts/dump_openapi.py --check`（backend job）與 `npm run check:types`（frontend job）——動到任何端點就必須在同一 PR 重產 `openapi.json` 與 `frontend/src/types/api.d.ts`。
- **Documentation**：README、CLAUDE.md、AGENTS.md、DEPLOY.md（含 6 群資料表對照）、LOCAL-DEV.md、TESTING.md 齊備且維護良好；程式內註解密度高且多為「為什麼」而非「做什麼」（`ci.yml`、`requirements.txt`、`docker-compose.deploy.yml` 的註解已到規格等級）。
- **Naming／函式規模**：命名清晰度良好；`cost_service.build_snapshot`（280–410 行區段）與兩支 calculator runner（979／803 行）屬於 god-module 等級。
- **抑制標記**：全 repo `noqa`／`eslint-disable`／`type: ignore`／`@ts-*` 合計僅 23 處，多為測試檔的 `# noqa: E402`（`sys.path` 調整所需）。

### Technical Debt Signals

1. **TODO／FIXME／HACK 僅 1 處**（且是 `validate_env_contract.py` 內的 placeholder 字串清單，不是真的待辦）——債務不是以註解形式存在，而是以下列結構形式存在。
2. **God modules**：`backend/services/diagram_builder.py`（1,818 行）、`backend/cost/gcp_calculator_runner.py`（979 行）、`backend/services/wa_rule_engine.py`（973 行）、`backend/services/user_router.py`（896 行）、`backend/cost/azure_calculator_runner.py`（803 行）、`frontend/src/pages/AssessmentPage.tsx`（1,861 行）、`WorkspacePage.tsx`（1,194 行）、`CostPage.tsx`（964 行）。
3. **跨模組引用私有函式**：`cost_service.py:43` `from services.collab_router import _user_can_access_diagram, _visible_diagrams`——底線開頭的符號被另一個套件依賴。
4. **部署映像缺 Playwright 瀏覽器**：`backend/Dockerfile` 安裝了 Node 與 `@anthropic-ai/claude-code`，但**沒有** `playwright install chromium`。`requirements.txt` 裝了 `playwright` 套件，執行期卻無瀏覽器二進位。`frontend/src/pages/CostPage.tsx:705` 也在 UI 上要求使用者自行 `playwright install chromium`。結論：Azure／GCP Calculator runner 在 staging 容器內結構性不可用——這條路徑實際上只在本機可跑。
5. **schema 雙軌且不對稱**：`schema.sql` **完全沒有**任何成本相關 DDL；4 張 C1 表只存在於 `schema_rbac.sql`（第 169–212 行）與 `backend/database.py::_ensure_cost_schema()`（第 329–395 行，含一段把 `pricing_cache.hourly` 改成 `NUMERIC(12,6)` 的補丁）。同一份 DDL 有兩個真實來源，且 `schema_rbac.sql` 只在空 volume 生效。
6. **backend 無 linter／formatter／型別檢查**：前端有三道（lint、typecheck、build），後端只有 import smoke。
7. **無覆蓋率門檻**：43 支測試沒有任何量化把關。
8. **測試以字串 patch 模組路徑**：`@patch("cost.pricing_client.fetch_hourly_via_sdk")` 這類寫法在重構搬檔時會靜默失效。
9. **依賴大多未釘版本**：`requirements.txt` 14 項只有 2 項精確釘選；`boto3`、`playwright`、`claude-agent-sdk` 皆浮動。
10. **雙層磁碟／DB 快取重疊**：`pricing_client.py` 自行在 `backend/cost/.pricing_offer_cache/` 寫 24h 磁碟快取，`price_cache.py` 又在 Postgres `pricing_cache` 寫 24h 快取——兩套 TTL 各自為政。
11. **`deploy/.env.example` 仍保留註解掉的 `AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY`（第 94–95 行）**，與 `DEPLOY.md:126` 明文宣告「不要加、也不會進容器」互相矛盾（雖僅為註解，仍是誤導來源）。

## Handoff Summary

- **Intent-relevant finding（退役面的精確邊界）**：`backend/cost/` 對外的耦合出奇地窄——**進入邊只有一條**（`backend/main.py:13` `from cost.cost_router import router as cost_router`），且 `backend/services/` 之中沒有任何模組 import `cost.*`（已全域比對確認，相依方向單向為 `main → cost → services`）。但退役 inventory 若只列「9 endpoints + 4 tables + Playwright runners + spike scripts」，會漏掉以下 **8 類套件外掛鉤**：
  1. `scripts/warm_aws_pricing_cache.py:42-44` 直接 import `cost.config`／`cost.price_cache`／`cost.pricing_client`——刪 `price_cache.py` 會讓這支腳本壞掉。
  2. **`scripts/validate_cost_calculator_boundary.py` 是 CI `repo-contract` job 的第三步，以硬編碼路徑指向 `backend/cost/cost_calculator.py`，檔案不存在就 `return 1`。刪掉 `cost_calculator.py` 而不同時改 `ci.yml` 與這支腳本，CI 立刻紅燈。**
  3. `backend/database.py::_ensure_cost_schema()`（329–395 行）與 `schema_rbac.sql:169-212`——4 張表有兩個 DDL 真實來源，且 `DEPLOY.md:219-238` 的資料表對照表也要同步（`project.md` 的 schema↔deploy 同步是 blocking 規則）。
  4. `backend/services/rbac_seed_data.py` 的 5 組 story id：`C1`（11 列，view 權限）、`C1h`、`C1r`、`C1b`、`C1o`（各 11 列）。`cost_service.py` 實際使用的是 `C1`.view 與 `C1h`／`C1r`／`C1o`.edit；**`C1b` 已在 seed 裡但無任何程式引用（B2 budget 的遺留）**。
  5. **`frontend/src/App.tsx:24` 的根路徑導向邏輯是 `if (can('C1','view')) return <Navigate to="/cost" replace />;`**——移除成本頁不只是刪一條 route，會改變所有 FinOps 角色登入後的落地頁。另有 `Sidebar.tsx:201` 的 `NavLink to="/cost"`。
  6. `frontend/src/types/api.d.ts`（2,751 行，由 `openapi.json` 產生）與 `openapi.json` 本身：改動 9 個端點必須在同一 PR 重跑 `python scripts/dump_openapi.py` 與 `npm run gen:types`，否則 CI 的兩道漂移閘門都會紅。
  7. `validate_env_contract.py` 的 `validate_local_dev_template_is_complete()` **反向強制**：`backend/` 讀到的每個環境變數都必須在 `backend/.env.example` 有記載。移除 `COST_PRICING_STUB`／`COST_PRICING_USE_SDK`／`COST_PRICING_SDK_TIMEOUT`／`COST_PRICING_OFFER_READ_TIMEOUT`／`COST_PRICING_AGENT`／`COST_PRICING_AGENT_SKIP_LLM`／`GCP_BILLING_API_KEY` 這些讀取點時，`backend/.env.example`（94–124 行）、`deploy/.env.example`、`deploy/render-env.sh:92`、`deploy/docker-compose.deploy.yml:57`、`deploy/docker-compose.test.yml:40`、`.github/workflows/deploy.yml:101,201` 必須一起改，否則環境契約紅燈。
  8. 17 支 C1 測試檔 + `frontend/tests/e2e/regression.spec.ts` 第 492 行起的整段成本頁回歸（依賴 test stack 內嵌的 `COST_PRICING_STUB=1` 與 `$86.40 / 月` 這個 stub 硬編碼期望值）。
- **`pricing_client.py` 保留的真實成本**：它 import `cost.config`、`cost.pricing_gcp`、`cost.pricing_azure`、`cost.pricing_offer_parser`、`cost.pricing_sdk`。要刪 `pricing_sdk.py` 就必須改寫 `pricing_client.py:20` 與 `:280-283` 的 `use_sdk_enabled()` 分支（`tests/test_pricing_client.py:73-74` 正好 patch 這兩個符號）；`pricing_sdk.py` 是全 repo 唯一的 `boto3` 使用者，刪掉後 `boto3` 可從 `requirements.txt` 移除。同時 `config.py` 與其 9 份 YAML（尤其 `pricing_urls.yaml` 307 行、`pricing_coverage.yaml`、`aws_region_locations.yaml`、`supported_regions.yaml`）以及傳遞相依的 `pricing_units.py`、`pricing_offer_parser.py`、`pricing_gcp.py`、`pricing_azure.py` **都必須跟著保留**——這 8 個檔是 `pricing_client` 的最小存活集合。
- **LangGraph 遷移的介面定義所在**：`cost_pricing_agent.py:43-49` 的 in-process MCP server `cloud360-cost` 與 3 個 tool（`list_mapped_resources`、`fetch_official_hourly`、`run_azure_calculator_estimate`），加上 `backend/prompts/cost_pricing_agent_system.md`（以路徑載入，拆除後會變孤兒）。`claude_agent_sdk` 在 repo 內另有 3 個非 cost 的使用者（`services/design_agent.py`、`services/review_agent.py`、`services/wa_lens_engine.py`），**因此不能因為 C1 遷移就把 `claude-agent-sdk` 從 `requirements.txt` 拿掉，也不能拿掉 `backend/Dockerfile` 裡的 Node 22 與 `@anthropic-ai/claude-code`**。
- **Risks / follow-up**：
  1. **Fingerprint 不符**：指派單鎖定 `git:37b327b8bdc49dac2a2e0974270f8944f2abd9c8`，實測 HEAD 為 `cd2754d291eb37086646d80f1fed2abf209e9805`。本次掃描以實際工作樹為準。architect 在 publish 時若 source fingerprint 比對失敗，需重新 snapshot。
  2. **AWS 憑證移除尚未 commit**：`deploy/render-env.sh`、`deploy/docker-compose.deploy.yml`、`.github/workflows/deploy.yml`、`DEPLOY.md`、`LOCAL-DEV.md` 五檔目前是**未提交的工作樹修改**（`git status` 為 ` M`）。掃描所見的 `COST_PRICING_USE_SDK:-0` 與「不傳遞 AWS 憑證」是工作樹狀態，尚未進入版控歷史。
  3. Playwright 瀏覽器在部署映像中缺席（見技術債 4），意味著「Calculator runner 在 staging 能跑」這個前提從未成立；退役決策若引用「現有 Calculator 路徑的線上表現」作為依據，該依據不存在。
  4. `frontend/src/cost/slotRegistry.tsx` 的兩個 slot 名稱 `cost-overspend`／`cost-banner` 對應 B2 功能，而 E2E 明確斷言這些 testid 命中數為 0（ADR-C1-08 規定 B1 不得渲染）——這是已存在但刻意未啟用的死碼，退役時可一併清掉。
  5. 本次未深讀 `backend/services/` 的大檔與 `frontend/src/pages/` 的實作細節；若後續 stage 需要 WorkspacePage／AssessmentPage 與成本頁之間的資料流細節，需另行補掃。
