# 業務總覽（Business Overview）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-10-01｜intent `261001-a2-langgraph`｜mode **Focused merge（STALE）**
> 保留前一版（`260916-estimate-upload-rework`）成本域敘述；本輪更新 Assessment／agent／LangGraph／`llm_provider` 焦點。深度分佈見 `reverse-engineering-timestamp.md`。

## 產品定位與價值主張

Cloud-360 是 AI-native 的多雲（AWS／GCP／Azure）架構設計與運維平台。核心價值鏈為「以自然語言描述需求 → 產生可編輯的 draw.io 架構圖 → 以 Well-Architected（WA）lens 審核 → 由同一份架構圖推導成本」，並以故事級 RBAC 控制誰可檢視、編輯、審核與改價。

執行環境限於自有 staging（`cloud360.danniel.cc`，ADR-0007）；雲端供應商 production 仍在範圍外（ADR-0001／ADR-0002）。方法論基礎為 Spec-Driven Development 與 AI-DLC v2（ADR-0011）。

**C1 成本估算**（前一 intent 驗證）：`backend/cost/`、`/api/cost` 9 個 HTTP operations、4 張資料表、`/cost` 前端頁面已可運行。細節見同檔既有段落與 `component-inventory.md`／`dependencies.md`（本輪未重新深讀 cost）。

## 主要使用者旅程

| 故事／領域 | 主角 | 目標 | 入口 | 現況 |
|---|---|---|---|---|
| A1 架構圖生成 | 架構師／工程師 | 以聊天提示產生與迭代架構圖，於 embed.diagrams.net 畫布編輯並持久化 | `/workspace` | 可運行；**Design Agent 已改 LangGraph** |
| A3 評估與審核 | 審核者／架構師 | 對已存架構圖執行 WA review、檢視 findings 與分數、管理 lens | `/assessment` | 可運行；**Review／Lens 仍 Claude Agent SDK** |
| C1 成本估算 | FinOps 分析師／架構師 | 由架構圖推導逐項成本、調整區域與每日時數、覆寫 SKU 與單價、匯出 Calculator 估價檔 | `/cost` | 可運行（前一版深讀；本輪 shallow） |
| J 管理（權限） | 管理員 | 使用者管理、角色授權請求、角色–故事權限矩陣 | `/admin/*` | 可運行 |
| 協作 | 協作者 | 架構圖 CRUD、聊天歷史、分享、WebSocket 同步 | `/api/collab` + WS | 可運行 |

導覽與落地頁由故事權限驅動。`frontend/src/App.tsx` 根路徑導向第一順位仍為 `can('C1','view')` → `/cost`（前一版事實；本輪確認路由表含 `/assessment`）。

## C1 成本估算的業務行為（現況｜前一版保留）

1. **估價來源為自動取價**：`pricing_client` 依雲別分派至 AWS Bulk／Azure Retail／GCP Catalog；另有 `pricing_sdk`（預設關閉）。
2. **SKU 對應**：`sku_mapper`（YAML）優先，未命中改走 `sku_ai_resolver`（LLM）。
3. **Agent 產生建議**：`cost_pricing_agent` 以 `claude_agent_sdk` 建立 in-process MCP `cloud360-cost`。
4. **Calculator 自動化**：Azure／GCP runners 以 Playwright 驅動官方 Calculator（部署映像缺瀏覽器二進位，見 `code-quality-assessment.md`）。
5. **可調參數**：區域（`C1r`）、每日時數（`C1h`）、SKU／單價覆寫（`C1o`），寫入 `cost_audit_event`。

能力盤點與掛鉤清單見 `component-inventory.md`、`dependencies.md`。

## Assessment／Agent 框架現況（本輪焦點）

| 表面 | 框架 | 產品意義 |
|---|---|---|
| A1 Design／產圖 | **LangGraph**（`StateGraph` + `ToolNode` + `ChatAnthropic`） | 已迁；模型經 `get_design_model_name`（openrouter 預設 `google/gemini-2.5-flash`） |
| A3 Review 建議 | **Claude Agent SDK**（`ClaudeSDKClient`，無工具） | **本 intent 重構目標**；預設 `google/gemini-3.7-flash`（openrouter） |
| A3 Lens 作答 | **Claude Agent SDK** + MCP `emit_lens_answers` | **本 intent 重構目標**；一般模型 `get_model_name` |
| 規則分數 | 純函式 `wa_rule_engine.evaluate` | 無 LLM |
| `langgraph_runtime` | LangGraph helpers（OpenRouter／`ChatOpenAI`） | 與 Assessment **未接線**；與 Design 的 Anthropic-compat 適配平行 |

Intent 名稱含「A2」；產品面 Assessment 路由與 story 為 **A3**。OpenAPI `generate` 說明另提及架構編輯權「A1／A2／A4」——requirements 階段需對齊命名。

## 範圍與邊界

**In scope（目前可運行）**：FastAPI 後端、React SPA、PostgreSQL、staging Docker、CI、gh-aw workflows、Kiwi TCMS。

**Out of scope（除非新 ADR）**：雲端供應商 production、direct production IaC、destructive cloud operations、native iOS／Android。

## 與本 intent 的業務關聯

Intent `261001-a2-langgraph` 要把 **Assessment（A3）評核路徑的 agent 框架改為 LangGraph**，同時維持前端 SSE 契約。從業務面看：

- 使用者在 `/assessment` 發起評核／collab／retry 時，不應感知底層由 SDK 換成 LangGraph；前端**不傳** LLM model 名，僅傳雲 `provider`。
- Design 已迁、Review／Lens 未迁 → 重構邊界清楚，但映像仍依賴 Node／`claude` CLI（Review／Lens），全迁後才可評估移除。
- 模型真相源為 `llm_provider`（部署預設 OpenRouter）；`langgraph_runtime` 另有 OpenAI-compat 適配——统一 runtime 時需選一或做薄適配。
