# 程式結構（Code Structure）

> Reverse Engineering 合成產物｜repo `cloud`｜工作樹掃描日 2026-09-16｜intent `260916-estimate-upload-rework`｜mode **Full rescan**

## 頂層目錄與檔案分佈

追蹤檔總數（`git ls-files` 依頂層目錄統計）：

| 目錄 | 追蹤檔數 | 性質 |
|---|---|---|
| `aidlc/` | 776 | AI-DLC 工作區（memory、intents、codekb、knowledge）；本次僅列名未深讀 |
| `.claude/` | 272 | upstream AI-DLC 框架；本次僅列名未深讀 |
| `backend/` | 120 | 應用程式碼 |
| `.github/` | 109 | CI 與 33 支 workflow（含 gh-aw 的 `.md` 規格與 `.lock.yml` 產物成對） |
| `frontend/` | 64 | 應用程式碼 |
| `scripts/` | 9 | repo 層工具（2,477 行） |
| `deploy/` | 5 | 部署設定 |

**應用程式碼為 `backend/` + `frontend/` 共 184 檔。**

## `backend/` 組織

`backend/` 是 **flat module 而非 Python package**（無頂層 `__init__.py`，以 `sys.path` 為根 import），因此 `from cost.cost_router import ...`、`from services.auth import ...` 的形式成立。

| 子目錄／檔案 | 內容 | 規模 |
|---|---|---|
| `main.py` | FastAPI 應用組裝：CORS、startup、6 次 `include_router` 掛到 5 個前綴 | 60 行 |
| `models.py` | SQLAlchemy ORM，11 個 model class | — |
| `database.py` | `init_db()` 與 5 支 `_ensure_*_schema()` 啟動補丁 | — |
| `env_bootstrap.py` | 強制由 `backend/.env` 載入環境變數，不依賴 process 啟動目錄 | — |
| `cost/` | C1 成本估算領域套件：18 支 `.py`（6,382 行）、9 份 YAML、2 份 fixture | 最大的單一領域套件 |
| `services/` | 22 支模組（約 8,000 行）：auth／RBAC／collab／架構圖產生／WA review／LLM provider | — |
| `tests/` | 43 檔、5,277 行 | `unittest` + `hypothesis` |
| `prompts/` | 4 支 system prompt（Markdown）+ 3 份 drawio 範本（XML） | 靜態資產 |
| `lenses/` | WA lens 定義 JSON（AWS／GCP／Azure 各一） | 靜態資產 |
| `scripts/` | `dump_openapi.py`、2 支 Azure Calculator spike | 工具 |

### `backend/cost/` 檔案分類

| 分類 | 檔案 |
|---|---|
| HTTP 層 | `cost_router.py` |
| 協調層 | `cost_service.py`、`cost_pricing_agent.py` |
| 純函式層 | `cost_calculator.py`（零相依、零 I/O） |
| 查價 Port | `pricing_client.py`、`pricing_sdk.py`、`pricing_azure.py`、`pricing_gcp.py`、`pricing_offer_parser.py`、`pricing_query_parser.py`、`pricing_units.py` |
| SKU 對應 | `sku_mapper.py`（YAML 規則）、`sku_ai_resolver.py`（LLM 推論） |
| Calculator 自動化 | `azure_calculator_runner.py`（803 行）、`gcp_calculator_runner.py`（979 行）、`gcp_calculator_product_resolver.py` |
| 圖資源擷取 | `diagram_extractor.py` |
| 快取 | `price_cache.py`（DB 快取；磁碟快取在 `pricing_client` 內） |
| 設定 | `config.py`（葉節點，import 時載入 9 份 YAML） |
| 資料資產 | `aws_region_locations.yaml`、`calculator_azure_map.yaml`、`calculator_azure_regions.yaml`、`calculator_gcp_map.yaml`、`calculator_gcp_regions.yaml`、`pricing_coverage.yaml`、`pricing_urls.yaml`（307 行）、`sku_map.yaml`（263 行）、`supported_regions.yaml`、`fixtures/azure_calculator_stub.html`、`fixtures/gcp_calculator_stub.json` |

## 資料模型（`backend/models.py` 的 11 張表）

| Model class | `__tablename__` | 領域 |
|---|---|---|
| `User` | `users` | 認證與 RBAC |
| `RoleAuthorizationRequest` | `role_authorization_requests` | RBAC |
| `RolePermission` | `role_permissions` | RBAC（故事級權限矩陣） |
| `UserDiagram` | `user_diagrams` | 協作／架構圖（`xml_data` blob） |
| `UserDiagramChat` | `user_diagram_chats` | 協作 |
| `ArchitectureReview` | `architecture_reviews` | A3 審核 |
| `WaLens` | `wa_lenses` | A3 lens |
| **`DiagramCost`** | **`diagram_cost`** | **C1** |
| **`DiagramCostLine`** | **`diagram_cost_line`** | **C1** |
| **`PricingCache`** | **`pricing_cache`** | **C1** |
| **`CostAuditEvent`** | **`cost_audit_event`** | **C1** |

`database.py` 的 5 支啟動補丁為 `_ensure_a4_schema`（184）、`_ensure_j5_schema`（212）、`_ensure_a3_schema`（259）、`_ensure_cost_schema`（329-395）、`_ensure_last_activity_schema`（397）。成本 DDL 的另一個真實來源是 `schema_rbac.sql:169-212`；`schema.sql` 沒有任何成本 DDL。

## `frontend/` 組織

| 目錄 | 內容 |
|---|---|
| `src/pages/` | 9 頁：`WorkspacePage`、`AssessmentPage`、`CostPage`、`AdminPage`、`RolePermissionsPage`、`AuthorizationRequestsPage`、`LoginPage`、`ForbiddenPage`、`WaitingApprovalPage` |
| `src/components/` | 12 個共用元件：`Layout`、`Sidebar`、`RouteGuard`、`DrawioCanvas`、`ChatBox`、`DiagramPreviewPanel`、`ShareModal`、`LensCriteriaEditor`、`NavChromeContext`、`LastActivityCell`、`PaginationControl`、`SuggestionRichText` |
| `src/cost/` | C1 前端輔助：`slotRegistry.tsx`（18 行）、`supportedRegions.ts`（48 行） |
| `src/config/api.ts` | URL 組裝集中點（`apiUrl()`／`wsUrl()`），52 處 `fetch()` 一致沿用 |
| `src/types/api.d.ts` | 2,751 行，由 `openapi.json` 經 `npm run gen:types` 產生 |
| `tests/e2e/` | `regression.spec.ts`（667 行單檔，Playwright） |

## 程式慣例（既成事實）

- **Python**：檔名 `snake_case.py`；router 一律 `*_router.py`；WA 引擎一律 `wa_*` 前綴；logger 以 `logging.getLogger("cloud360.<module>")` 為主（5 支仍用 `__name__`）。
- **React**：元件與頁面 `PascalCase.tsx`，頁面一律 `*Page.tsx`；非元件 TS 檔名混用 kebab-case 與 camelCase（`auth-context.ts` 為既存例外）。
- **後端分層依家族而異**：`cost`、`review`／`lens`／`wa_*` 為三層；`user`／`collab` 商業邏輯直寫 handler（`user_router.py` 896 行、`collab_router.py`）。
- **錯誤處理**：DB 與驗證錯誤直接 `raise HTTPException` 快速失敗；`try/except` 只用於外部依賴邊界（LLM、webhook、檔案）且必須降級或記 log。
- **抑制標記極少**：全 repo `noqa`／`eslint-disable`／`type: ignore`／`@ts-*` 合計 23 處，多為測試檔調整 `sys.path` 所需的 `# noqa: E402`。
- **註解密度高且多寫「為什麼」**：`ci.yml`、`requirements.txt`、`docker-compose.deploy.yml` 的註解已達規格等級。

## 建置與產物鏈

| 產物 | 來源 | 守門機制 |
|---|---|---|
| `openapi.json` | `backend/scripts/dump_openapi.py` | CI backend job 的 `--check` |
| `frontend/src/types/api.d.ts` | `openapi.json` 經 `npm run gen:types` | CI frontend job 的 `npm run check:types` |
| `deploy/.env` | `deploy/render-env.sh` | `validate_env_contract.py` 禁止 workflow 繞過自行產生 |
| DB 初始 schema | `schema_rbac.sql` 掛進 `docker-entrypoint-initdb.d` | **僅空 volume 生效**；既有環境靠 `database.py` 的 `_ensure_*_schema()` |
