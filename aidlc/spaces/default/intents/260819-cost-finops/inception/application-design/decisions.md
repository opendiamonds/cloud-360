# Decisions — C1 成本估算

<!-- Stage: application-design。本檔 ADR 為 intent 級設計決策，不取代 repo 根 ADR-0006 等。 -->

## 上游輸入

requirements（含 OQ-1／2／5）、stories、team-practices、architecture、Q1–Q5=A、refined-mockups。

---

# ADR-C1-01：新套件 `backend/cost/` 而非塞進 `user_router`

## Status
Accepted

## Date
2026-08-19

## Context
HEAD 無 cost bounded context。team-practices 要求 C1 走三層，且不得把邏輯寫進 `user_router.py`／`wa_rule_engine.py`。

## Decision
新增 `backend/cost/`（router、service、extractor、mapper、calculator、pricing_client）。`main.py` 以 prefix `/api/cost` 掛載。前端 `CostPage` 新檔，不改 Assessment 當宿主。

## Consequences
Construction 目錄與測試 `backend/tests/test_cost_*.py` 有固定落點。OpenAPI 新 tag `cost`。

## Alternatives Considered
- 寫進 `services/collab` 或 A3：違反「COST-* ≠ TCO」與禁止污染 WA 引擎。
- 獨立微服務：超出 mvp 單體與部署模型。

## Reversibility
中等。prefix 穩定後契約難改；套件內檔案可再拆。

---

# ADR-C1-02：四種變更權用 `C1` + `C1h`／`C1r`／`C1b`／`C1o`

## Status
Accepted（Q1=A）

## Context
`Action` 只有 view／edit／review。現 C1 種子 Architect／Editor 的 `can_edit` 為 False，FinOps 為 True，無法表達四種互斥變更。

## Decision
- `C1.view`：進頁、讀快照、讀稽核、Sidebar。
- `C1h.edit`：時數；`C1r.edit`：區域；`C1b.edit`：預算；`C1o.edit`：SKU／小時價覆寫。
- 不改 `role_permissions` 表形狀。
- 新增 `ensure_missing_role_permissions()`：只插入缺失的 `(role, story_id)`，**禁止**依賴現有 `force=False` 全表 no-op。

預設 edit：Architect=`C1h`+`C1r`；FinOps=`C1o`+`C1b`；Editor=`C1b`。A 規則 allow／deny 測試。

## Consequences
Admin 矩陣多四列 story。`STORY_IDS` 與 `schema_rbac.sql` 必須列出。既有 staging 列在補缺失 ensure 後才生效。

## Alternatives Rejected
- **B 硬編碼角色**：Admin 無法調權；與矩陣單一真實來源衝突。
- **C 加四個 boolean 欄**：J3b UI＋schema 爆炸，超出本輪。

## Reversibility
低。story id 進種子與測試後不宜改名。

---

# ADR-C1-03：兩張狀態表，不把估價寫進 XML

## Status
Accepted（Q2=A）

## Context
橫幅與第二人同一總額要求伺服器持久化。XML 是畫布真實來源，但覆寫不應污染 draw.io 模型。

## Decision
`diagram_cost`（區域、預算）＋ `diagram_cost_line`（hours、sku_override、hourly_override）。PK／UK：`(diagram_id, mxcell_id)`。圖刪 cascade。每次 snapshot 以 XML 重擷取後對齊；消失的 id 刪行；新 id 時數 24。

## Consequences
`schema_rbac.sql` 名稱雖歷史，遷移仍須寫在同一部署文件鏈（schema SQL + `DEPLOY.md` + `database.py` ensure）。

## Alternatives Rejected
- JSONB 欄：稽核舊值與部分更新差；SQLite 測試分叉。
- XML 自訂屬性：與「不寫回圖模型」衝突。

## Reversibility
中等。可遷移到別的表，但 API 快照形狀宜穩。

---

# ADR-C1-04：Postgres 價目快取 TTL 24h

## Status
Accepted（Q3=A）

## Context
NFR-4 5 秒；無 Redis；禁止帳單 API。

## Decision
表 `pricing_cache` 鍵為 `(cloud, sku, region)`。命中且 `now - fetched_at < 24h` 不打外網。Miss／過期走 `pricing_client`。失敗不寫正價。無公開端點的雲：不呼叫 client。

各雲 URL 仍 OQ-3／infrastructure-design。本輪 client 介面穩定，實作可用 stub 先綠測試。

## Alternatives Rejected
- 每次即時查：難以保證 5 秒與穩定來源時間。
- 只讀 fixture 當生產官方價：違反 FR-2.1 字面。

## Reversibility
高。TTL 可調；可改 Redis 而不改 Snapshot 契約。

---

# ADR-C1-05：SKU 對照表為 repo YAML

## Status
Accepted（Q4=A）

## Context
對照需可測、可 diff；本輪無 Admin 維護故事。

## Decision
`backend/cost/sku_map.yaml` 啟動載入。一對多的建議 UI 留 functional-design；mapper 本輪回 `ambiguous` → 列 `unpriced`。

## Alternatives Rejected
- Python dict：難審。
- DB＋Admin：無故事。

## Reversibility
高。可改載入來源而不改 mapper 介面。

---

# ADR-C1-06：稽核 HTTP 綁在圖資源下

## Status
Accepted（Q5=A）

## Context
故事允許暫查 DB；Construction 需要 TestClient 掛點。

## Decision
表 `cost_audit_event`。`GET /api/cost/diagrams/{diagram_id}/audit`。寫入點：覆寫小時價、指定 SKU、改預算。時數／區域本輪不寫稽核。

## Alternatives Rejected
- 扁平 `/api/cost/audit?diagram_id=`：較不像資源。
- 本輪無 HTTP：QA 無掛點。

## Reversibility
中等。路徑進 OpenAPI 後視為契約。

---

# ADR-C1-07：USD 兩位小數

## Status
Accepted（本站定，未另問）

## Context
故事把小數位留給設計。PBT 需要固定比較。

## Decision
calculator 出口量化到小數兩位（銀行家捨入或四捨五入在 functional-design 寫死一種）。JSON number。顯示 `tabular-nums`。

## Consequences
Hypothesis 比較量化後的 Decimal，不用 raw float。

## Reversibility
中等。改位數會動 e2e 字串。

---

# ADR-C1-08：第一段不註冊預算／橫幅

## Status
Accepted（stories AC-1.16）

## Decision
第一段：不 `include` budget 路由與 `GET /banner`（或恒 404）、不在 `Layout` import `OverspendBanner`。第二段同一 service 加掛。用建置開關或第二個模組檔，不用 CSS `hidden`。

## Reversibility
高。

---

# ADR-C1-09：三雲皆 `official_list`（覆寫 OQ-3 初案）

## Status
Accepted

## Date
2026-08-23

## Context
Infrastructure-design Q&A 初案與 mockups M2 曾定「僅 AWS 官方價；GCP／Azure `manual_override_only`」。實作期間已接上 GCP Cloud Billing Catalog 與 Azure Retail Prices，且區域下拉需依圖雲過濾，living docs 與程式不一致。

## Decision
1. `pricing_coverage.yaml`：`aws`／`gcp`／`azure` 皆 `mode: official_list`。
2. Allowlist hosts：`pricing.us-east-1.amazonaws.com`、`cloudbilling.googleapis.com`、`prices.azure.com`。
3. 查價路徑：AWS Bulk JSON **或** boto3 `pricing.get_products`（禁止 Cost Explorer）；GCP Catalog HTTP + 可選 `GCP_BILLING_API_KEY`（禁止帳號型 Billing SDK）；Azure Retail Prices 公開免帳號。
4. Snapshot 增 `diagram_cloud`、`allowed_regions`；跨雲 region PUT → 400。
5. 歷史 Q&A／diary **不改寫**；以本 ADR + 更新後的 living docs 為準。

## Consequences
- 定價假設文案改為三雲「走官方價」。
- CI 仍用 `COST_PRICING_STUB=1`；本機 GCP 需 key 才有真實價。
- `cicd-pipeline` 靜態 gate 不再全面禁 `boto3`（僅禁帳單／管理面）。

## Alternatives Considered
- 維持 GCP／Azure manual-only：與已交付程式衝突，FinOps 無法對非 AWS 圖估價。
- 盲目對未映射 label 打 API：拒絕（仍需 sku_map 代表規格）。

## Reversibility
中等。改回 `manual_override_only` 需同步 YAML、UI 文案與測試。

---

# ADR-C1-10：Pricing Agent 模擬 Azure Calculator 填寫（API 降為 tool；整圖總價以 agent 為準）

## Status
Accepted（待 Construction 實作；本 ADR 為設計定案，**不**表示已上線）

## Date
2026-08-30

## Context

C1 現行（ADR-C1-09）以 `cost_service` 逐列呼叫 `pricing_client`（AWS Bulk／Pricing SDK、GCP Catalog、Azure Retail Prices），再以 `cost_calculator.total_priced()` **加總各列 subtotal** 作為 `snapshot.total` 的唯一來源。此路徑快、可 cache、CI 可 stub，但與 FinOps 實務上常用的 **雲端供應商 Pricing Calculator 網頁**（使用者手動加產品、選 region、調數量後看 Estimate）在操作模型與數字呈現上不一致；代表規格（`sku_map.yaml`／`default_products*`）也無法涵蓋 Calculator 上全部組合與選項。

產品方向（2026-08-30 定案）：

1. **官方價 HTTP API 保留**，但改為 **Pricing Agent 的 MCP tool**，不再由 `cost_service` 直接逐列驅動總價。
2. **`snapshot.total` 改以 Agent 估價結果為 authoritative 來源**（整張架構圖一個總價），不再以「各列 subtotal 相加」為唯一真值。
3. **Azure 先行**：Agent 須能 **協助並模擬使用者在** [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/) **上的填寫行為**（加產品、選 region、設數量／選項），讀取頁面 Estimate 總價；GCP／AWS 官方 Calculator 採 **相同模式** 後續擴展。

參考頁面行為（非 API）：Calculator 為互動式 SPA；使用者從產品目錄加入服務、在 estimate 面板調整 region 與用量，頁尾顯示 **Estimated monthly cost**（及明細）。本 ADR 要求 Agent 路徑產出的總價對齊該 Estimate，而非僅 Retail API 代表規格換算值。

## Decision

### 1. 新增 `cost_pricing_agent`（對齊 A1 執行模型）

- 使用與 A1 相同堆疊：**FastAPI → `claude-agent-sdk` → Claude Code CLI 子行程 → LLM**（`services.llm_provider` 之 `openrouter`／`cli`）。
- 新增 `backend/cost/cost_pricing_agent.py`（或 `backend/services/cost_pricing_agent.py`，Construction 定案時與 `cost/` 邊界一致即可），由 **`cost_service` 在需要整圖估價時呼叫**（非前端直連）。
- Agent 選項對齊 `design_agent`：`tools=[]`、`allowed_tools` 僅白名單 MCP tool、`disallowed_tools` 禁 Bash／Read／Write／Edit／Glob／Grep／**未核准之** WebSearch／WebFetch；`max_turns` 與 token 上限另於 NFR 定案。
- Agent **不得**自行發起任意 URL HTTP；對 Calculator 的互動 **只**能經 §2 之 browser tool（Playwright，URL allowlist）。

### 2. MCP tools（Agent 唯一對外能力）

| Tool | 職責 | 實作備註 |
|---|---|---|
| `list_mapped_resources` | 自架構圖 XML 列出可估價列（label、sku、category、mxcell_id） | 包裝既有 `diagram_extractor` + `sku_mapper` |
| `fetch_official_hourly` | 查單一 cloud／sku／region 之官方 list 價（輔助對規格、sanity check、填表前比對） | 包裝既有 `pricing_client.fetch_hourly`（**ADR-C1-09 路徑保留**） |
| `run_azure_calculator_estimate` | **模擬使用者在 Azure Pricing Calculator 填寫**並回傳 Estimate | Playwright；見 §3 |

後續增量（本 ADR 預留、Construction 不阻塞 Azure 先行）：

- `run_gcp_calculator_estimate` → GCP Pricing Calculator
- `run_aws_calculator_estimate` → AWS Pricing Calculator  

三雲 **同一 Agent 契約**：輸入 `{ cloud, region, line_items[] }`，輸出 `{ total_usd, currency, lines?, assumptions[], source_url }`。

### 3. Azure Calculator 模擬填寫（必達行為）

**目標 URL（唯一允許的 calculator host）：**

- `https://azure.microsoft.com/en-us/pricing/calculator/`（及同 host 下 SPA 導航，不得跳轉至登入後帳單或任意第三方）

**Agent + Playwright 分工（強制）：**

- **Agent（LLM）**：依架構圖與 `list_mapped_resources` 產出 **結構化 `line_items`**（Calculator 產品名稱／類別、region、數量、必要選項）；可呼叫 `fetch_official_hourly` 輔助選代表規格；**不**直接以自然語言「猜 DOM」逐步點擊。
- **Playwright（確定性腳本）**：接收 `line_items`，在 Calculator 上執行與使用者等價的操作序列，例如：
  1. 開啟／重置 estimate（新 session 或清空購物車語意）
  2. 依產品對照表 **加入對應 Azure 服務**（搜尋或目錄點選）
  3. 設定 **Region** 與 **用量**（VM 規格、儲存 GB、AKS node 等）
  4. 讀取頁面 **Estimated monthly cost**（及可選明細列）作為 `total_usd`
- 產品對照表放 repo（例：`backend/cost/calculator_azure_map.yaml`），與 `sku_map.yaml` 可交叉引用；Agent 只輸出 **map 內合法 key**，腳本不解析自由文字 label。

**模擬「使用者填寫」的定義（驗收用）：**

- 操作必須經 **真實 browser 事件**（click／fill／select），非對 Calculator 背後 API 的未公開 endpoint。
- 總價來源為 **Calculator UI 顯示的 Estimate**，非 `prices.azure.com` Retail API 加總（Retail API 僅能經 `fetch_official_hourly` tool 使用）。
- 單次估價須留 **audit 摘要**（用了哪些 `line_items`、Playwright 步驟數、Estimate 字串快照 hash 或截圖 path 存 audit 表／object storage 之設計留 NFR；至少 log correlation id）。

**失敗語意：**

- Calculator 無法開啟、selector 失效、Estimate 讀不到 → Agent run 失敗；`snapshot.total` 為 `null`，`pricing_source` 標 `azure_calculator_failed`；**不得** silent fallback 到舊 `total_priced()` 加總（除非另開 ADR 允許 hybrid）。

### 4. Snapshot 與總價權威（取代整圖加總）

- **`snapshot.total`**：取自 Agent 最終 `CostEstimateResult.total_usd`（Azure 階段即來自 `run_azure_calculator_estimate` 讀取之 Estimate）。**不再**以 `cost_calculator.total_priced(lines)` 為唯一 authoritative 來源。
- **`lines[]`**：仍來自 extractor／mapper 與 DB 時數；`subtotal` 可為 Agent 拆分建議值或 `null`；列級 `hourly_list` 可仍由 `fetch_official_hourly` tool 填寫供 UI 展示，**但不得**與 `total` 不一致時覆寫 `total`。
- **`pie`**：由 Agent 回傳之 bucket 或依 `lines[]` 比例展示；若 Agent 僅給總價，pie 可為 null 或單一 bucket（Construction 定案）。
- **新增欄位（OpenAPI 同步）**：建議 `pricing_source`（`azure_calculator`｜`gcp_calculator`｜…｜`agent_failed`）、`pricing_as_of`（Agent run 完成時間）、可選 `agent_assumptions`（字串陣列，對應 Calculator 假設摘要）。
- **`coverage` 文案**：Azure 改為「走 Azure Pricing Calculator 估價」；過渡期其他雲仍可用 API tool 直至各自 Calculator tool 就緒（見 §5）。

### 5. 雲別 rollout

| 階段 | 行為 |
|---|---|
| **Phase A（本 ADR 最小交付）** | `diagram_cloud == azure` 且 region 已設 → **必須**走 Pricing Agent + `run_azure_calculator_estimate` 定 `total` |
| **Phase B** | GCP／AWS 新增對應 calculator tool；同一 Agent orchestration |
| **Phase C（可選）** | 移除 `cost_service` 內對 `pricing_client` 的直接呼叫路徑，僅剩 Agent tools |

在 Phase A 完成前，**不得**宣稱 C1 Azure 估價已符合本 ADR。

### 6. 與 ADR-C1-09 的關係

- ADR-C1-09 之 **HTTP allowlist 與 `pricing_client` 實作保留**，作為 Agent tool `fetch_official_hourly` 的後端；**不刪除** Retail／Catalog 路徑。
- **Authoritative 總價來源**由 ADR-C1-09 之「逐列 official_list + 加總」改為 **本 ADR 之 Agent + Calculator（Azure 先行）**；兩 ADR 並存，衝突時 **總價以 ADR-C1-10 為準**。
- `pricing_coverage.yaml` 之 `mode: official_list` 仍描述 **API tool 能力**；Calculator 為 **另一定價來源**，在 snapshot 以 `pricing_source` 區分，不強求寫入 `coverage.mode` 新 enum（Construction 可增 `calculator` 文案）。

### 7. 安全與運維（hard constraints）

- **SSRF**：Playwright 僅允許 `azure.microsoft.com`（Calculator 階段）；禁止 Agent 或腳本導向任意 host。
- **Credential**：Calculator 公開頁 **不要求** Azure 帳號登入；禁止引入 `azure-identity` 等帳號 SDK 操作 Calculator（與 ADR-C1-09 一致）。
- **部署**：backend 映像需 **headless Chromium**（Playwright）；staging 出站須能連 `azure.microsoft.com`；CI 預設 **不**跑真實 Calculator（mock HTML fixture 或 skip）。
- **成本／延遲**：單次估價預期 **數十秒～數分鐘**；須有 request timeout 與 UI loading 狀態；NFR 另訂 P95。
- **RBAC**：沿用 `C1.view` 觸發估價；Agent run 寫入 `cost_audit_event`（新 event type 或 extension）。

## Consequences

- **優點**：總價與 [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/) 使用者可見 Estimate 一致；減少代表規格 YAML 與 Calculator 選項漂移；GCP／AWS 可複製同一 Agent＋Playwright 模式。
- **代價**：實作與維運複雜度顯著高於 ADR-C1-09；UI 改版需更新 Playwright selector；估價慢、耗 LLM token；Docker 映像變大；e2e／CI 需分層（mock calculator page vs 慢速 live）。
- **測試**：保留 `fetch_official_hourly` 之 unit 測試；新增 calculator map 與 Playwright fixture 測試；Agent 整合測試 mock MCP tools；**不得**僅依賴 Retail API 測試宣稱 Calculator 路徑正確。
- **文件**：實作啟動前須更新 `component-methods.md`（Agent 契約、`pricing_source`）、`infrastructure-services.md`（Chromium、allowlist）、`DEPLOY.md`（出站、timeout）；本 ADR 不修改歷史 Q&A 原文。

## Alternatives Considered

- **維持 ADR-C1-09 逐列 API 加總**：與「Calculator 一致」產品目標不符；拒絕作為 Azure 總價來源。
- **純 LLM 逐步點 DOM（無 Playwright 腳本）**： fragile、難測、易 hallucinate 點錯；拒絕。
- **只爬 Calculator 背後未公開 API**：違反「模擬使用者填寫」與 SSRF 精神；拒絕。
- **API 加總與 Calculator 雙總價並列**：使用者已定案 **整圖總價以 Agent／Calculator 取代**；拒絕雙 authoritative total。
- **Retail API 結果冒充 Calculator**：違反 §3 驗收；僅允許作 `fetch_official_hourly` tool 輔助。

## Reversibility

**低～中等**。一旦前端與 e2e 依 `pricing_source=azure_calculator` 與新 `total` 語意建置，回退需同步 Agent、Playwright、OpenAPI 與 UI 文案。`pricing_client` 可保留作 tool 以便回退至 ADR-C1-09 模式（需新 ADR 或 feature flag）。

---

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-19T08:19:45Z
**Iteration:** 1

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Minor | `component-methods.md` GET `/diagrams/{id}` | `coverage` 欄位列於快照回應 body，但在 `component-methods.md` 與 `cost_calculator` 簽名中均無定義（公式、單位或預設值皆缺）。Construction 開發者須自行推斷其語意（定價列數 / 總列數？百分比？）。 | 在 `component-methods.md` 補一行：`coverage`：`priced` 列數 ÷ 總擷取列數（0.0–1.0），無列時為 `null`；或在 functional-design 明確定義，並在此檔標記「見 functional-design」。 |
| 2 | Minor | `ADR-C1-08` / `component-methods.md` GET `/banner` | ADR-C1-08 明確排除「budget PUT 路由」與「OverspendBanner 掛載」，但未說明 `GET /banner` 端點在第一增量是否註冊。若 TestClient 測試直接呼叫 `/banner`，`banner_for()` 需能在 `monthly_budget` 全為 NULL 時安全回傳 `{active: false}`（`is_overspent(total, None) → False` 可保證），但此行為未在 ADR 中明文確認，Construction 可能誤判需整個排除。 | 在 ADR-C1-08 補一句：「第一段可註冊 `/banner` 端點，`banner_for()` 在無預算列時恒回傳 `{active: false, count: 0}`；如不註冊則一律 404 並在 TestClient 測試中跳過。兩者皆可接受，Construction 擇一記錄於 functional-design。」 |
| 3 | Minor | `services.md` / `component-methods.md` `pricing_client` | 設計要求「無公開端點的雲：不呼叫 client」（FR-2.2），但 `pricing_client.fetch_hourly(cloud, sku, region)` 的介面未定義此偵測機制。若 OQ-3 infrastructure-design 交付的是「URL 字典」，`cost_service` 需要某種機制（空 URL？設定旗標？`PriceMiss` 子類型？）判斷「此雲本輪無端點」。目前 `PriceHit / PriceMiss` 二元無法區分「無端點」與「有端點但查詢失敗」，可能造成 `price_fetch_failed` 與 `unpriced` 混用。 | 在 `component-methods.md` 的 `pricing_client` 節補第三個回傳型態 `PriceUnsupported`（或文字說明）表示「該雲本輪無公開端點，不應計入失敗重試」；`cost_service` 針對此型態將列狀態設為 `unpriced` 而非 `price_fetch_failed`，與 FR-2.2 AC 一致。 |

### Validation Tool Results

| 工具 | 結果 | 說明 |
|---|---|---|
| 依賴矩陣循環偵測（手動） | PASS | `component-dependency.md` 矩陣為有向無環圖：router → service → {extractor, mapper, calculator, pricing_client\*, price_cache, diagrams}；calculator 與 extractor 均為葉節點，無反向邊。 |
| `force=False` no-op 驗證（`rbac.py` L63–65） | PASS（gap 已知） | 確認 `ensure_role_permissions_seeded(force=False)` 在表非空時整段 no-op；C1h／C1r／C1b／C1o 確實不在 `rbac_seed_data.py`（L82–91 僅 `C1`）。設計已在 ADR-C1-02 與 `components.md` 第 72 行明確標記此缺口為 Construction 義務，DoD 第 5 條亦覆蓋。 |
| calculator 禁止 httpx（靜態） | PASS（設計強制） | `component-methods.md` 明文禁止模組內 `httpx`、`Session`、`HTTPException`；模組尚未存在，無反例。 |
| 第一增量 overspent 洩漏檢查 | PASS | `is_overspent(total, None) → False`（`component-methods.md`）；ADR-C1-08 第一段 `overspent` 恒 `false` 可由此保證，不需 hardcode。 |
| OpenAPI dump 義務 | PASS | `dump_openapi.py --check` 確認存在；ADR-C1-01 Consequences 明列 OpenAPI 新 tag `cost`；requirements.md DoD 第 6 條強制。 |
| 跨元件引用解析 | PASS | 所有 story id（`C1`、`C1h`、`C1r`、`C1b`、`C1o`）在 requirements.md FR 中有對應；`require_story_action` 在既有 `rbac.py` 存在；`UserDiagram` ORM 模型在現有 collab stack 確認；`dump_openapi.py` 確認存在。 |

### Summary

設計結構清晰、依賴無環、三層分層正確。關鍵架構決策（ADR-C1-01 至 08）均有可追溯的 FR 根據，且明確記錄了 `force=False` 種子缺口、第一增量排除範圍與純函式計算器的禁止邊。三項 Minor 發現均不影響實作可行性：`coverage` 欄位語意可由 functional-design 補齊，`/banner` 增量規則一行即可澄清，`PriceUnsupported` 型態缺失可在 functional-design 補充介面。Construction 開發者具備足夠信息可開始實作，無需返回設計者澄清架構決策。
