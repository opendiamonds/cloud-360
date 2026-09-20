# 系統架構（Architecture）

> Reverse Engineering 合成產物｜repo `cloud`｜工作樹掃描日 2026-09-16｜intent `260916-estimate-upload-rework`｜mode **Full rescan**
> 每個 Mermaid 區塊都附文字 fallback（ADR-0009 與 `team.md` `## Mandated` 的內容驗證要求）。

## 架構風格

**模組化單體（Modular Monolith）＋ SPA 前端**，證據如下：

- 單一 FastAPI process 掛載 6 個 router 到 5 個 URL 前綴（`backend/main.py:51-56`），沒有跨 process 的服務邊界、沒有訊息佇列、沒有服務間 HTTP 呼叫。
- 單一 PostgreSQL 資料庫由所有領域共用（11 張 ORM 表，見 `code-structure.md`）；領域之間以 Python import 直接耦合，不是以契約解耦。
- 部署為 4 個容器（db、backend、frontend、cloudflared），一次整包上線（`deploy/docker-compose.deploy.yml`）。

模組邊界的清晰度**依領域而異**，這是既成事實而非待修違規：`cost`、`review`／`lens`／`wa_*` 家族有清楚的 router → service → 純函式三層；`user`／`collab` 家族的商業邏輯直寫在 handler 裡。

## 元件關係總覽

```mermaid
graph TD
  subgraph FE["frontend SPA - React 19 + Vite"]
    ROUTES["App.tsx 路由與 RouteGuard"]
    COSTPAGE["CostPage"]
    OTHERPAGES["Workspace / Assessment / Admin 等 8 頁"]
  end

  subgraph BE["backend - FastAPI 單一 process"]
    MAIN["main.py 應用組裝"]
    COST["cost 套件 - C1 成本估算"]
    SVC["services 套件 - A1 / A3 / J / collab"]
    ORM["models.py + database.py"]
  end

  subgraph EXT["外部依賴"]
    PG[("PostgreSQL 16")]
    DRAWIO["embed.diagrams.net"]
    LLM["OpenRouter 或 claude CLI"]
    N8N["n8n webhook - 圖示 SVG"]
    PRICE["雲端公開價目端點"]
    CALC["Azure / GCP Calculator 網頁"]
  end

  ROUTES --> COSTPAGE
  ROUTES --> OTHERPAGES
  COSTPAGE -->|"/api/cost"| MAIN
  OTHERPAGES -->|"/api/architecture, /api/auth, /api/collab"| MAIN
  MAIN --> COST
  MAIN --> SVC
  COST --> SVC
  COST --> ORM
  SVC --> ORM
  ORM --> PG
  OTHERPAGES --> DRAWIO
  SVC --> LLM
  SVC --> N8N
  COST --> LLM
  COST --> PRICE
  COST --> CALC
```

**文字 fallback**：前端 SPA 由 `App.tsx` 的路由表與 `RouteGuard` 分派到 9 個頁面，其中 `CostPage` 打 `/api/cost`，其餘頁面打 `/api/architecture`、`/api/auth`、`/api/collab`。後端 `main.py` 同時掛載 `cost` 套件與 `services` 套件；`cost` 單向依賴 `services`（授權、LLM provider、XML 清理），`services` 不反向依賴 `cost`。兩者都經 `models.py`／`database.py` 存取同一個 PostgreSQL。外部依賴中，draw.io 由前端直連，LLM、n8n、雲端公開價目端點與 Azure／GCP Calculator 網頁由後端呼叫。

## `backend/cost/` 內部結構

```mermaid
graph LR
  ROUTER["cost_router"] --> SERVICE["cost_service"]
  SERVICE --> AGENT["cost_pricing_agent"]
  SERVICE --> CALCPURE["cost_calculator 純函式"]
  SERVICE --> EXTRACT["diagram_extractor"]
  SERVICE --> CACHE["price_cache"]
  SERVICE --> PCLIENT["pricing_client"]
  SERVICE --> SKU["sku_mapper"]
  SERVICE --> SKUAI["sku_ai_resolver"]
  SERVICE --> AZRUN["azure_calculator_runner"]
  SERVICE --> GCPRUN["gcp_calculator_runner"]
  AGENT --> PCLIENT
  AGENT --> SKU
  AGENT --> SKUAI
  AGENT --> AZRUN
  AGENT --> GCPRUN
  AGENT --> EXTRACT
  PCLIENT --> PGCP["pricing_gcp"]
  PCLIENT --> PAZ["pricing_azure"]
  PCLIENT --> POFFER["pricing_offer_parser"]
  PCLIENT --> PSDK["pricing_sdk - boto3"]
  PSDK --> PQUERY["pricing_query_parser"]
  PGCP --> PUNITS["pricing_units"]
  PAZ --> PUNITS
  POFFER --> PUNITS
  PQUERY --> PUNITS
  GCPRUN --> GRESOLVE["gcp_calculator_product_resolver"]
  GRESOLVE --> SKUAI
  SKUAI --> SKU
  CONFIG["config - 讀 9 份 YAML"]
  SERVICE --> CONFIG
  AGENT --> CONFIG
  PCLIENT --> CONFIG
  SKU --> CONFIG
```

**文字 fallback**：`cost_router` 是唯一 HTTP 入口，單向呼叫 `cost_service`；`cost_service` 是扇出最廣的協調層（10 條內部邊）；`config` 是扇入最廣的葉節點（12 個模組引用，於 import 時載入 9 份 YAML）；`cost_calculator` 是唯一零相依的純函式模組（ADR-0006 property-based testing 的落點）；`pricing_client` 之下分為 GCP、Azure、offer parser 與 boto3 SDK 四條查價支線，四者最終都收斂到 `pricing_units`。套件內**未偵測到循環引用**。完整的正反向相依表在 `dependencies.md`。

## 互動圖（Interaction Diagrams）

以下三張圖描述跨元件的實際業務交易。

### 交易一：C1 取得架構圖成本快照

```mermaid
sequenceDiagram
  participant U as FinOps 使用者
  participant FE as CostPage
  participant R as cost_router
  participant S as cost_service
  participant RB as services.rbac
  participant X as diagram_extractor
  participant M as sku_mapper 與 sku_ai_resolver
  participant P as pricing_client
  participant C as price_cache
  participant DB as PostgreSQL

  U->>FE: 開啟 /cost 並選擇架構圖
  FE->>R: GET /api/cost/diagrams/ID 帶 run_agent
  R->>S: get_snapshot
  S->>RB: user_can C1 view
  RB-->>S: 允許或拒絕
  S->>DB: 讀 user_diagrams 的 xml_data
  S->>X: 解析 mxGraph XML 取得資源列
  X-->>S: mxcell_id 與 label 清單
  S->>M: 對每個資源解析 SKU
  M-->>S: SKU 或未對應
  S->>C: 查 pricing_cache 24 小時內的價格
  alt 快取未命中
    S->>P: 向雲端公開價目端點查現價
    P-->>S: 每小時單價
    S->>C: 寫回 pricing_cache
  end
  S->>DB: upsert diagram_cost 與 diagram_cost_line
  S-->>R: 成本快照
  R-->>FE: JSON 回應
  FE-->>U: 逐項成本與月費
```

**文字 fallback**：使用者在 `/cost` 選圖後，前端呼叫 `GET /api/cost/diagrams/ID`。`cost_router` 轉交 `cost_service`，後者先經 `services.rbac.user_can` 檢查 `C1.view`，再從 `user_diagrams` 取出 mxGraph XML 交給 `diagram_extractor` 解析成資源列，逐項以 `sku_mapper`（YAML 規則）或 `sku_ai_resolver`（LLM）解析 SKU。價格先查 `pricing_cache`（24 小時 TTL），未命中才經 `pricing_client` 向雲端公開價目端點取價並寫回快取。結果 upsert 進 `diagram_cost`／`diagram_cost_line` 後回傳。`run_agent` 查詢參數預設為 `true`，會額外觸發 `cost_pricing_agent`。

### 交易二：調整每日時數與稽核

```mermaid
sequenceDiagram
  participant U as 架構師
  participant FE as CostPage
  participant R as cost_router
  participant S as cost_service
  participant RB as services.rbac
  participant CALC as cost_calculator 純函式
  participant DB as PostgreSQL

  U->>FE: 修改某一列的每日時數
  FE->>R: PUT /api/cost/diagrams/ID/lines/MXCELL/hours
  R->>S: apply_hours
  S->>RB: user_can C1h edit
  RB-->>S: 允許或拒絕
  S->>DB: 讀 diagram_cost_line 現值
  S->>CALC: 以時數與單價重算月費
  CALC-->>S: 新金額
  S->>DB: 更新 diagram_cost_line
  S->>DB: 寫入 cost_audit_event 含舊值與新值
  S-->>R: 更新後的列
  R-->>FE: JSON 回應
  FE-->>U: 就地更新該列與總計
```

**文字 fallback**：時數、區域、SKU、單價覆寫四種寫入操作共用同一形狀——router 轉交 service、service 檢查對應故事權限（`C1h`／`C1r`／`C1o` 的 `edit`）、讀現值、交由純函式 `cost_calculator` 重算、更新 `diagram_cost_line`，並把「誰、何時、舊值、新值」寫進 `cost_audit_event`。稽核寫入與資料更新在同一交易內，沒有非同步補寫路徑。

### 交易三：A1 從自然語言到架構圖

```mermaid
sequenceDiagram
  participant U as 架構師
  participant FE as WorkspacePage
  participant AR as agent_router
  participant PG as prompt_guard
  participant DA as design_agent
  participant DB2 as diagram_builder
  participant N8N as n8n webhook
  participant DB as PostgreSQL

  U->>FE: 輸入架構需求
  FE->>AR: POST /api/architecture 產圖請求
  AR->>PG: 平台自我竄改預檢
  alt 命中防護
    PG-->>AR: 固定拒絕訊息
    AR-->>FE: 不呼叫 LLM 直接回覆
  else 通過
    AR->>DA: 呼叫 LLM 產生結構化描述
    DA-->>AR: 節點與連線結構
    AR->>DB2: 轉換為 mxGraph XML
    DB2->>N8N: 取得元件圖示 SVG
    N8N-->>DB2: SVG 或失敗
    DB2-->>AR: mxGraph XML
    AR->>DB: 寫入 user_diagrams
    AR-->>FE: 架構圖 XML
  end
  FE-->>U: 於 draw.io 畫布呈現
```

**文字 fallback**：A1 產圖請求先過 `prompt_guard` 的平台自我竄改預檢（命中則不呼叫 LLM，回固定拒絕訊息，見 `project.md` `## Mandated`）；通過後由 `design_agent` 呼叫 LLM 取得結構化描述，`diagram_builder` 轉成 mxGraph XML 並向 n8n webhook 取元件圖示 SVG（失敗則降級為灰底佔位圖），最後寫入 `user_diagrams` 並回傳給前端於 draw.io 畫布呈現。C1 的估價正是消費這份 XML。

## 資料流與持久化

- **唯一寫入路徑**：所有 DDL 有兩個真實來源——`schema_rbac.sql`（僅在空 volume 經 `docker-entrypoint-initdb.d` 生效）與 `backend/database.py` 的 5 支 `_ensure_*_schema()` 啟動補丁（既有環境靠它升級）。兩者必須手動保持一致，沒有機械檢查。
- **成本相關 4 張表**（`diagram_cost`、`diagram_cost_line`、`pricing_cache`、`cost_audit_event`）只存在於 `schema_rbac.sql:169-212` 與 `_ensure_cost_schema()`（`database.py:329-395`）；`schema.sql` **完全沒有**成本 DDL。
- **雙層快取重疊**：`pricing_client` 在 `backend/cost/.pricing_offer_cache/` 寫 24 小時磁碟快取，`price_cache` 又在 `pricing_cache` 表寫 24 小時快取，兩套 TTL 各自為政。

## 關鍵設計決策與其後果

| 決策 | 位置 | 後果 |
|---|---|---|
| 成本域採 router → service → 純函式三層＋獨立 pricing port | `cost_router`／`cost_service`／`cost_calculator`／`pricing_client` | ADR-0006 的 PBT 約束有明確落點；`validate_cost_calculator_boundary.py` 以硬編碼路徑機械強制純函式層不得 import `httpx`／`requests`／`sqlalchemy`／`fastapi` |
| 成本套件放在 `backend/cost/` 而非 `backend/services/` 之下 | 目錄結構 | 相依方向單向為 `main → cost → services`；`services` 無任何模組 import `cost.*`，退役面的耦合因此極窄 |
| OpenAPI 與前端型別以 CI drift 閘門綁定 | `dump_openapi.py --check`、`npm run check:types` | 任何端點變更必須在同一 PR 重產 `openapi.json` 與 `frontend/src/types/api.d.ts` |
| Agent 以 in-process MCP server 暴露工具 | `cost_pricing_agent.py:43-49` | `cloud360-cost` 的 3 個 tool 是 agent 介面的唯一契約定義，遷移框架時必須逐一對應 |
| 根路徑導向以 C1 為第一順位 | `frontend/src/App.tsx:24` | 成本頁同時是 FinOps 角色的落地頁，存廢變更會改變登入後行為 |

## 架構強化機會

1. **DDL 單一真實來源**：`schema_rbac.sql` 與 `_ensure_*_schema()` 的重複應收斂為單一來源或加上一致性檢查。
2. **跨模組私有函式引用**：`cost_service.py:43` 引用 `services.collab_router._user_can_access_diagram` 與 `_visible_diagrams`，破壞封裝；授權來源應提升為公開介面。
3. **快取層重疊**：磁碟快取與 DB 快取應擇一，或明確定義兩者的職責分界。
4. **God module**：`diagram_builder.py`（1,818 行）、`gcp_calculator_runner.py`（979 行）、`wa_rule_engine.py`（973 行）等已達難以測試的規模，清單與行數見 `code-quality-assessment.md`。
