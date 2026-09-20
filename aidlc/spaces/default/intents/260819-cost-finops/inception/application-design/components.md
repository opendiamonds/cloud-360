# Components — C1 成本估算

<!-- Stage: application-design（Inception 2.6）· Q1–Q5=A。 -->

## 上游輸入

- **requirements**（`../requirements-analysis/requirements.md`）
- **stories**（`../user-stories/stories.md`）
- **architecture**／**component-inventory**（`aidlc/spaces/default/codekb/cloud/`）
- **team-practices**（`../practices-discovery/team-practices.md`）
- **refined-mockups**（`../refined-mockups/`）

## 風格

維持現況 **模組化單體**：FastAPI 加一個 router prefix，React 加一頁與 Layout 橫幅。不新開微服務、不新 Redis。

新後端套件目錄：`backend/cost/`（與 `services/wa_*` 平行，避免再塞進已過重的 `services/`）。Router 仍由 `main.py` `include_router(..., prefix="/api/cost")`。

禁止：`user_router.py`、`wa_rule_engine.py`、`parse_diagram_summary` 當列集合。

---

## 後端元件

| 元件 | 職責 | 不職責 |
|---|---|---|
| `cost_router` | HTTP：認證依賴、status code、Pydantic schema、OpenAPI | 公式、httpx、直接組 SQL |
| `cost_service` | 編排：可見性、擷取、對照、快取、覆寫、預算、稽核寫入、超支判定 | 純加總公式；不 raise 公式例外當 HTTP |
| `diagram_extractor` | 從目前 XML 取出可估價 mxCell（FR-1.1 規則） | SKU 對照、計價 |
| `sku_mapper` | 讀 YAML 對照；唯一命中／未命中／一對多 | HTTP |
| `cost_calculator` | 純函式：小時價、小計、總額、圓餅四類、超支布林 | DB、httpx、`HTTPException` |
| `pricing_client` | Port：打公開價目；測試可 stub | 讀 `diagram_cost`；Cost Explorer |
| `price_cache` | 讀寫 `pricing_cache` 表；TTL 24h | 計算小計 |
| `rbac`（既有） | `require_story_action("C1"\|"C1h"…)` | 硬編碼角色表（Q1 不用 B） |

## 前端元件

| 元件 | 職責 |
|---|---|
| `CostPage` | `/cost`：圖下拉、總額、圓餅、資源表、定價假設 |
| `HoursInput`／`RegionField`／列上 SKU 與覆寫欄 | 就地編輯；非法不送出 |
| `PieBreakdown` | 本頁 SVG＋`cost-pie-legend` |
| `OverspendBanner` | `Layout` 主區頂；第一段不掛載 |
| `SuccessCostCta` | Workspace 成功卡第四顆 |
| `Sidebar` | 「成本 → 預估成本」；無 `C1.view` 不渲染 |

`auth-context` 的 `can(story, action)` 須能查 `C1h` 等新 id（矩陣 API 已按 story 回傳；前端型別跟著 OpenAPI）。

## 資料元件

| 表 | 所有權 |
|---|---|
| `diagram_cost` | 每圖：`pricing_region`、`monthly_budget`（nullable） |
| `diagram_cost_line` | 每圖×`mxcell_id`：`hours`、`sku_override`、`hourly_override` |
| `pricing_cache` | 雲＋SKU＋區域 → 小時價、`fetched_at` |
| `cost_audit_event` | 覆寫與預算變更 |

`user_diagrams` 仍是圖 XML 的唯一來源；估價列每次以目前 XML 重擷取後用 `mxcell_id` 對齊行表。

## 權限元件（Q1）

| story id | 本輪使用的 action | 預設 edit |
|---|---|---|
| `C1` | `view` 進頁／讀快照／讀稽核／Sidebar | （維持現種子的 view） |
| `C1h` | `edit` 改每日時數 | `Project_Architect` |
| `C1r` | `edit` 改估價區域 | `Project_Architect` |
| `C1b` | `edit` 改每圖預算 | `FinOps_Analyst`、`Project_Editor` |
| `C1o` | `edit` 指定 SKU 或覆寫小時價 | `FinOps_Analyst` |

其他角色：有 `C1.view` 者只讀；無 view 則 `/cost` → `/403`。

**種子缺口**：現有 `ensure_role_permissions_seeded(..., force=False)` 在表非空時 **整段 no-op**，不會插入新的 `(role, story_id)`。Construction 必須加「只補缺失列」的 ensure（不 delete 既有矩陣），並同步 `schema_rbac.sql`／`DEPLOY.md`。

## 公開介面（router 前綴 `/api/cost`）

見 `component-methods.md`。前端路由 `/cost`（mockups）；`App.tsx` 以 `CapabilityRoute storyId="C1" action="view"` 包裹。
