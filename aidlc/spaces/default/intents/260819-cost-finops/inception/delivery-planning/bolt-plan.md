# Bolt Plan — C1 成本估算

> Stage: delivery-planning（Inception 2.8）· Intent: `260819-cost-finops`
> 上游：`requirements.md`、`stories.md`、`mockups.md`、`components.md`、`unit-of-work.md`、`unit-of-work-dependency.md`、`unit-of-work-story-map.md`、`team-practices.md`。
> 問答：Q1=A 兩段增量、Q2=A 不打 WSJF、Q3=A `stage-major`、Q4=A 嚴格序列、Q5=A stub 價目。

## 適用的既有實務（自 memory 層解析，非本站新定）

| 事項 | 定案 | 來源層 |
|---|---|---|
| Construction worktree 的 base 與 merge target | `ut` | `org.md ## Way of Working` |
| Bolt 分支合併 | Construction Bolt **squash-merge** 進 `ut`；一般 PR 維持 merge commit | `team.md ## Way of Working` |
| Walking skeleton | **本 intent `skeleton: off`**；第一 Bolt 無額外 skeleton gate | `team.md ## Walking Skeleton` Q1 定案 A（覆蓋 mvp scope 檔的 `skeleton: on`） |
| 部署 | **deploy-on-merge** 至自有 staging | `org.md`／`project.md ## Deployment` |
| Bolt 執行 | **嚴格序列**（Q4=A） | 本站 |
| 設計階段迭代 | **`stage-major`**（預設；不呼叫 `set-construction-iteration`） | 本站 Q3=A |

## 序列總覽

```
B1  cost-schema-rbac + cost-calculator + cost-api + cost-ui
    → squash-merge ut → staging 部署 → 驗收第一段（C1-1～C1-5）
B2  cost-budget-banner
    → squash-merge ut → staging 部署 → 驗收第二段（C1-6～C1-7）
```

**DAG 相容性**：序列**完全尊重** `unit-of-work-dependency.md` 的五條邊。Bolt 1 同時包含兩個根與它們的下游 `cost-api`／`cost-ui`（捆綁理由見下，不是把根「排在」api 之前當獨立部署）。Bolt 2 的入邊（`cost-api`、`cost-ui`）皆已在 Bolt 1。**無拓樸偏離**。

每個 Bolt 跑 Construction **3.1–3.7**（functional-design … ci-pipeline）。intent 級 **3.8 `tcms-test-cases`** 在兩個 Bolt 之後執行一次，不另開 Bolt。

---

## B1 — 第一段預估成本（可單獨上線）

**包含單元**：`cost-schema-rbac`（spec）＋ `cost-calculator`（library）＋ `cost-api`（service）＋ `cost-ui`（ui）

**為何合併**：分開部署會違反兩條已學到的規則。

- `delivery-planning:c3`：單拆 schema 或 calculator 湊不出使用者可展示的信心假說（沒有讀取端、沒有畫面）。
- `delivery-planning:c6`：deploy-on-merge 下，`/api/cost*` 與 generated `api.d.ts`／`CostPage` **不得分批**；api 先合 `ut` 會讓 staging 出現無消費者的新契約。

捆在同一 Bolt **不是**把 DAG 讀成施工順序；是經濟上唯一能同時滿足假說與同批部署的切法。schema∥calculator 的拓樸平行仍存在於 Bolt **內部**的設計／測試工作，不變成兩次 merge。

**Walking skeleton 標記**：否

**對應故事**：主責 C1-1～C1-5（`unit-of-work-story-map.md`）。C1-6／C1-7 本 Bolt **不交付**。

**Definition of Done**：

- 四表存在；`ensure_missing_role_permissions()` 只補缺失 `(role, story_id)`，不依賴 `force=False` 全表 no-op（ADR-C1-02；`team-practices` 規則 A）
- `cost_calculator` 純函式 + Hypothesis（NFR-3／ADR-0006）；未定價列不加總
- 第一段 HTTP：`GET /diagrams`、`GET /diagrams/{id}`、`PUT region`／`hours`／`sku`／`override`、`GET audit`。**不註冊** `PUT budget`、**不註冊** `GET /banner`（ADR-C1-08）
- `openapi.json` 與 `frontend/src/types/api.d.ts` 無 drift
- `pricing_client` 可 stub；無區域 0 次官方價 HTTP；`PriceUnsupported` 不發外網
- 擷取 overlay 新模組；禁止 `user_router.py`／`wa_rule_engine.py`／`parse_diagram_summary` 當列集合（`components.md`）
- Playwright：Sidebar「成本 → 預估成本」、列對到圖、圓餅文字清單、時數 0–24、產圖 CTA；預算欄／「已超支」／橫幅 test-id **0 命中**（AC-1.16；對齊 `mockups.md`）
- TestClient：無權 403、圖不可見 404、時數非法 422（`team-practices` 規則 B）
- 同步 `schema_rbac.sql`、`DEPLOY.md`、`database.py` ensure

**信心假說**：*「架構師能從 Sidebar 打開／cost，看到對到圖的資源列與（stub）官方價總額，並用每日時數重算；FinOps 能覆寫小時價；畫面上沒有預算或超支橫幅。」*

**預期展示**：staging 以 Architect 登入 → 「成本 → 預估成本」→ 選圖看到列與圓餅；改時數後總額變；無 C1.view 帳號看不到該組且 `/cost` 進 `/403`。產圖成功卡有「查看預估成本」。

**已知風險**：種子 no-op、extractor 誤用 WA 摘要、無區域仍打價目。見 `risk-and-sequencing-rationale.md`。

---

## B2 — 每圖預算與進產品橫幅

**包含單元**：`cost-budget-banner`（省略 kind）

**Walking skeleton 標記**：否

**對應故事**：主責 C1-6、C1-7。協作沿用 Bolt 1 已交付的 `is_overspent`、`CostPage`／`Layout` 掛點。

**Definition of Done**：

- `PUT /api/cost/diagrams/{id}/budget`（`C1b.edit`）與 `GET /api/cost/banner` 已註冊
- 成本頁出現預算欄（`cost-budget`）與「已超支」（`cost-overspend-flag`）；`Layout` 主區頂掛 `OverspendBanner`（`cost-banner`），Sidebar 右側（`mockups.md`）
- 未設預算不超支；多圖一條橫幅；不能永遠關閉；無 inbox
- 覆寫／預算變更寫 `cost_audit_event`
- Playwright：設預算後總額大於預算則旗標與橫幅出現；進入其他受保護頁仍見橫幅
- 跨 unit DOM 擴充機制（開關／第二模組檔／slot）在本 Bolt 的 functional-design 寫死一種（UG reviewer Minor 3）

**信心假說**：*「為圖設定每月預算後，超支會同時出現在成本頁與每次進入產品的橫幅；未設預算的圖不會誤報超支。」*

**預期展示**：FinOps／Editor 寫入預算 → 總額超過時 Architect 在 `/cost` 看到「已超支」，進 Workspace 仍見橫幅（含圖名、總額、預算）。

---

## Bolt 間約束

| 約束 | 說明 |
|---|---|
| 序列 | B2 不得在 B1 合進 `ut` 並通過第一段驗收前 merge |
| 同批 | B1 內部四 unit 一次 squash；禁止 api 與 ui 分 PR 進 `ut` |
| 第一段 DOM | B1 部署後橫幅與預算欄必須 0 命中；B2 才掛上 |
| 價目 URL | B1 允許 stub；真實公開端點 URL 屬 B1 的 infrastructure-design（OQ-3），不是 B2 的閘 |

## 不在本計畫內

C2／C3、egress、Cost Explorer、超支 LLM 建議、獨立微服務。
