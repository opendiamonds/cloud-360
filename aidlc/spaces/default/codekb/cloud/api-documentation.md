# API 文件（API Documentation）

> Reverse Engineering 合成產物｜repo `cloud`｜工作樹掃描日 2026-09-16｜intent `260916-estimate-upload-rework`｜mode **Full rescan**
> 端點清單以 `openapi.json` 程式列舉為準（本次深度分析項目），並與 `cost_router.py` 逐一核對。

## HTTP API 總覽

`openapi.json` 共 **45 paths／54 operations**，全部前綴 `/api/*`，另加根 `GET /`。

| 群組 | 掛載前綴 | operations | 來源 router |
|---|---|---|---|
| architecture（agent／review／lens） | `/api/architecture` | 16 | `agent_router`、`review_router`、`lens_router`（三者共用同一前綴） |
| auth／user／RBAC | `/api/auth` | 16 | `user_router` |
| collab | `/api/collab` | 12 | `collab_router` |
| **cost（C1）** | `/api/cost` | **9** | `cost_router` |
| root | `/` | 1 | `main.py` |

## `/api/cost` 的 9 個 operations

| # | Method 與路徑 | `cost_service` 對應函式 | 說明 |
|---|---|---|---|
| 1 | `GET /api/cost/diagrams` | `list_diagrams` | 可估價的架構圖清單 |
| 2 | `GET /api/cost/diagrams/{diagram_id}` | `get_snapshot` | 成本快照；query `run_agent` 預設 `true`，會觸發 `cost_pricing_agent` |
| 3 | `GET /api/cost/diagrams/{diagram_id}/audit` | `get_audit` | 該圖的 `cost_audit_event` 稽核紀錄 |
| 4 | `GET /api/cost/diagrams/{diagram_id}/calculator-export/csv` | `export_calculator_excel` | GCP Calculator 匯出 |
| 5 | `GET /api/cost/diagrams/{diagram_id}/calculator-export/xlsx` | `export_calculator_excel` | Azure Calculator 匯出 |
| 6 | `PUT /api/cost/diagrams/{diagram_id}/region` | `apply_region` | 套用估價區域（story `C1r`） |
| 7 | `PUT /api/cost/diagrams/{diagram_id}/lines/{mxcell_id}/hours` | `apply_hours` | 每日時數（story `C1h`） |
| 8 | `PUT /api/cost/diagrams/{diagram_id}/lines/{mxcell_id}/override` | `apply_override` | 單價覆寫（story `C1o`） |
| 9 | `PUT /api/cost/diagrams/{diagram_id}/sku`（實為 `/lines/{mxcell_id}/sku`） | `apply_sku` | SKU 覆寫（story `C1o`） |

授權形狀一致：`cost_router` 以 FastAPI 依賴取得 `database.get_db`、`models.User`、`services.auth.get_current_user`，再由 `cost_service` 呼叫 `services.rbac.user_can` 檢查故事權限——`C1.view` 用於讀取，`C1h`／`C1r`／`C1o` 的 `edit` 用於四個 `PUT`。

## 契約同步規則（硬性）

改動任何端點必須在**同一個 PR** 內同時重產兩份衍生物，否則 CI 兩道 drift 閘門都會紅燈：

1. `python scripts/dump_openapi.py`（實際路徑為 `backend/scripts/dump_openapi.py`）重產 `openapi.json` — backend job 以 `--check` 驗證。
2. `npm run gen:types` 重產 `frontend/src/types/api.d.ts`（2,751 行）— frontend job 以 `npm run check:types` 驗證。

此外，`fastapi[standard]==0.141.1` 與 `pydantic==2.13.4` 是**精確釘選**的，目的正是讓 `openapi.json` 的輸出具位元決定性。升級這兩者會使 dump 漂移。

## 內部 API（非 HTTP）：in-process MCP server

`cost_pricing_agent.py:43-49` 以 `claude_agent_sdk` 自建一個 in-process MCP server，名稱 `cloud360-cost`，暴露 3 個 tool（FQN 形如 `mcp__cloud360-cost__<tool>`）：

| Tool | 用途 |
|---|---|
| `list_mapped_resources` | 列出已完成 SKU 對應的架構圖資源 |
| `fetch_official_hourly` | 向公開價目端點取得每小時官方價 |
| `run_azure_calculator_estimate` | 以 Playwright 驅動 Azure Calculator 產生估價 |

**這 3 個 tool 契約是 agent 介面的唯一正式定義**；搭配的 system prompt 以路徑載入自 `backend/prompts/cost_pricing_agent_system.md`。任何 agent 框架遷移都必須逐一決定這 3 個 tool 的去留與對應物，並處理 prompt 檔的歸屬（拆除後會成為孤兒檔）。

## 對外呼叫的第三方 API

| 目的 | 端點類型 | 呼叫者 | 憑證需求 |
|---|---|---|---|
| AWS 價目 | Bulk／Offer 公開端點 | `pricing_client` → `pricing_offer_parser` | 無 |
| AWS 價目（替代路徑） | Pricing Query API（boto3） | `pricing_sdk` | **需 IAM 憑證**；由 `COST_PRICING_USE_SDK` 控制，工作樹現況預設 `0`（關閉） |
| Azure 價目 | Retail Prices 公開端點 | `pricing_azure` | 無 |
| GCP 價目 | Cloud Billing Catalog | `pricing_gcp` | `GCP_BILLING_API_KEY` |
| Azure／GCP Calculator | 官方 Calculator 網頁（Playwright 驅動） | `azure_calculator_runner`、`gcp_calculator_runner` | 無，但**需要瀏覽器二進位** |
| LLM 推論 | OpenRouter 或本機 `claude` CLI | `services.llm_provider` | 依 provider |
| 架構圖元件圖示 | n8n webhook（Basic Auth） | `services.diagram_builder` | `N8N_USER`／`N8N_PASSWORD` |

允許呼叫的價目主機白名單記在 `backend/cost/pricing_urls.yaml`（307 行）的 `allowlist_hosts`。

## 前端路由表（`frontend/src/App.tsx`）

`/login`、`/403`、`/waiting-approval`、`/workspace`、`/assessment`、`/cost`、`/admin/users`、`/admin/authorization-requests`、`/admin/role-permissions`、`/admin`（redirect）、`/`（redirect）、`*`。

**`App.tsx:24` 的根路徑導向第一順位為 `if (can('C1','view')) return <Navigate to="/cost" replace />;`**；側欄入口在 `Sidebar.tsx:201` 的 `NavLink to="/cost"`。這兩處與 9 個端點同屬 C1 的對外介面面，變更時必須一併處理。
