# Unit of Work — C1 成本估算

> Stage: units-generation（Inception 2.7）· Intent: `260819-cost-finops`  
> 本輪只切 **C1**（七則 Must）。C2／C3 不建 unit。  
> 來源：`components.md`、`component-methods.md`、`services.md`、`component-dependency.md`、`decisions.md`、`requirements.md`、`stories.md`。  
> Q1=A、Q2=A、Q4=A、Q5=A（覆寫 Q3 初選 B）。計畫已核可。  
> **本檔不定施工順序**；拓樸見 `unit-of-work-dependency.md`。

## 拆分原則

| 原則 | 說明 |
|---|---|
| 驗證同類（project.md `units-generation:c6`） | 單元邊界依「完成了嗎」的失敗模式切：schema／種子是建置期契約；calculator 是純函式 PBT；api 是 TestClient HTTP；ui 是 Playwright；第二段預算／橫幅是另一組端點＋DOM |
| 部署模型 | **embedded**：同一 FastAPI process、同一 SPA bundle（ADR-C1-01、Q4=A）。Unit = 邏輯 Module，不是微服務 |
| 契約 | `/api/cost*` 進 `openapi.json`；`cost-ui` 用 generated `api.d.ts`（Q5=A、`component-methods.md` 慣例） |
| 禁止 | 寫進 `user_router.py`／`wa_rule_engine.py`；`parse_diagram_summary` 當列集合；Cost Explorer／帳單 API；本輪 LLM 超支建議 |
| 既有 HEAD | 不把 U-J／U-A1／U-A2 列入本 intent 的 yaml unit（它們已在產品內）。本輪假設 JWT、`require_story_action`、`UserDiagram` XML、Workspace 成功卡已存在 |

## Unit 一覽

本輪 **5** 個 unit。故事 **7** 則（C1-1～C1-7）。驗收標準 **47** 條（C1-1：13；C1-2：5；C1-3：2；C1-4：9；C1-5：9；C1-6：4；C1-7：5）。

| Unit | kind | 複雜度 | 部署 | Construction 目錄 |
|---|---|---|---|---|
| `cost-schema-rbac` | spec | S | 就地消費（SQL／種子進既有 Postgres 與 `schema_rbac.sql`） | `construction/cost-schema-rbac/` |
| `cost-calculator` | library | M | 無獨立 runtime；被 `cost-api` import | `construction/cost-calculator/` |
| `cost-api` | service | L | embedded 既有 backend 容器；prefix `/api/cost` | `construction/cost-api/` |
| `cost-ui` | ui | L | embedded 既有 frontend bundle；路由 `/cost` | `construction/cost-ui/` |
| `cost-budget-banner` | （省略 kind，完整設計矩陣） | M | 同上兩容器；第二段加掛路由與 Layout | `construction/cost-budget-banner/` |

`cost-budget-banner` 同時含第二段 HTTP 與 Layout／成本頁 DOM，沒有單一 kind 能同時排除 NFR 與 UI 產物，故省略 kind（Q1=A）。

## Unit 定義

### cost-schema-rbac（spec）

- **職責**：四表與 RBAC 種子契約。擁有 `diagram_cost`（含可空 `monthly_budget`）、`diagram_cost_line`、`pricing_cache`、`cost_audit_event`；`C1`／`C1h`／`C1r`／`C1b`／`C1o` 列入 `STORY_IDS` 與 `schema_rbac.sql`。
- **必做**：`ensure_missing_role_permissions()` 只插入缺失 `(role, story_id)`。**禁止**依賴 `ensure_role_permissions_seeded(..., force=False)` 在表非空時的整段 no-op（ADR-C1-02；`rbac.py` 現況）。
- **不職責**：HTTP 形狀、公式、頁面。第一段即使不寫預算，欄位仍可存在且為 NULL。
- **同步**：`schema_rbac.sql`、`DEPLOY.md`、`database.py` ensure。
- **驗證失敗模式**：遷移後表／UK 不存在；staging 已有 `role_permissions` 列時新 story id 仍缺。

### cost-calculator（library）

- **職責**：純函式（`component-methods.md`）：`hourly_from_monthly`、`line_subtotal`（含覆寫 `O × h × 30`）、`total_priced`、`pie_buckets`（compute／database／network／other）、`is_overspent`（`budget is None` → False；相等 False）。出口 USD 兩位小數（ADR-C1-07）。
- **不職責**：DB、httpx、`HTTPException`、OpenAPI。模組內禁止那些 import。
- **驗證失敗模式**：Hypothesis 量化後 Decimal 不相等；未定價列被加進總額。

### cost-api（service）

- **職責**：`backend/cost/` 的 router／service／extractor／mapper／pricing_client／price_cache。第一段 HTTP：`GET /diagrams`、`GET /diagrams/{id}`、`PUT .../region`、`PUT .../lines/{mxcell_id}/hours|sku|override`、`GET .../audit`。`main.py` prefix `/api/cost`。
- **契約**：快照形狀與 status 語意以 `component-methods.md` 為準；`coverage` 為雲別 `official_list`｜`manual_override_only`。無權 403、圖不可見 404、時數非法 422。
- **第一段禁止**：不註冊 `PUT .../budget`、不註冊 `GET /banner`（ADR-C1-08）。`budget` 回應恒 `null`、`overspent` 恒 `false`。
- **定價 Port**：`PriceHit`／`PriceMiss`／`PriceUnsupported`（無端點不發 HTTP → unpriced）。SKU 表 `backend/cost/sku_map.yaml`。快取 TTL 24h。
- **驗證失敗模式**：TestClient 403／404／422；OpenAPI dump drift；extractor 誤用 `parse_diagram_summary`；無區域仍打價目 URL。

### cost-ui（ui）

- **職責**：Sidebar「成本 → 預估成本」、`CostPage`（`/cost`、`CapabilityRoute storyId="C1"`）、`PieBreakdown` SVG、`HoursInput`／`RegionField`、列上 SKU／覆寫、產圖成功卡 `SuccessCostCta`、空狀態與載入／錯誤。test-id 見 refined-mockups。
- **契約消費**：generated `api.d.ts`（Q5=A），對齊 `openapi.json` 的 `/api/cost*`。
- **第一段禁止**：不掛 `OverspendBanner`；預算欄與「已超支」test-id 0 命中（AC-1.16）。
- **驗證失敗模式**：Playwright 找不到入口或列；無 C1.view 仍見「成本」組；非法時數仍送出。

### cost-budget-banner（完整矩陣）

- **職責**：第二段：`PUT .../budget`、`GET /banner`、成本頁「已超支」、`Layout` 主區頂（Sidebar 右側）`OverspendBanner`。多圖一條橫幅；未設預算不超支。
- **不職責**：改 calculator 公式（沿用 `is_overspent`）；改第一段擷取規則。
- **驗證失敗模式**：第一段建置若誤掛橫幅 DOM；有預算且總額大於預算時橫幅不出現；inbox 被加回來。

## 約束（對 Construction）

| 項 | 來源 |
|---|---|
| 三層不可塌進 `user_router` | `components.md`、`stories.md` C1-1 DoD |
| 種子只補缺失列 | `decisions.md` ADR-C1-02 |
| 公開價、禁止帳單 | `requirements.md` FR-2 |
| 兩段增量皆 Must；第一段可單獨通過其自身驗收（不交付 `cost-budget-banner` 時 AC-1.16 的預算／橫幅 DOM 為 0 命中） | `stories.md` 優先序 |
| 金額 USD 兩位 | ADR-C1-07 |

此表是產品範疇與驗收約束，**不是** Bolt 施工順序；施工排程由 2.8 Delivery Planning 決定。
