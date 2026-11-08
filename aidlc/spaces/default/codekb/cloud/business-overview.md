# 業務總覽（Business Overview）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-11-05｜HEAD `0bffc82`｜intent `261105-d-iac-generation`｜mode **Focused merge（STALE）**
> 本輪焦點：Story D（IaC 產生）相關的 Workspace／RBAC／agent 表面。其餘散文保留前一輪（`261001-a2-langgraph`）內容，並以證據標籤標明可信度。深度分佈見 `reverse-engineering-timestamp.md`。
>
> **證據標籤**：`[實讀]`＝developer 對本輪 analyzed.paths 的實讀；`[抽查]`＝architect 本輪以 grep／`head`／目錄列表做的輕量複驗（**不在** analyzed.paths，不等於深讀）；`[繼承]`＝前一輪 codekb 散文，本輪未複驗。

## 產品定位與價值主張

Cloud-360 是 AI-native 的多雲（AWS／GCP／Azure）架構設計與運維平台。核心價值鏈為「以自然語言描述需求 → 產生可編輯的 draw.io 架構圖 → 以 Well-Architected（WA）lens 審核 → 由同一份架構圖推導成本」，並以故事級 RBAC 控制誰可檢視、編輯、審核與改價。[繼承]

執行環境限於自有 staging（`cloud360.danniel.cc`，ADR-0007）；雲端供應商 production 仍在範圍外（ADR-0001／ADR-0002）。方法論基礎為 Spec-Driven Development 與 AI-DLC v2（ADR-0011）。

## 主要使用者旅程

| 故事／領域 | 主角 | 目標 | 入口 | 現況 |
|---|---|---|---|---|
| A1 架構圖生成 | 架構師／工程師 | 以聊天提示產生與迭代架構圖，於 embed.diagrams.net 畫布編輯並持久化 | `/workspace` | 可運行；Design Agent＝LangGraph [實讀 agent_router／抽查 design_agent] |
| A3 評估與審核 | 審核者／架構師 | 對已存架構圖執行 WA review、檢視 findings 與分數、管理 lens | `/assessment` | 可運行；**Review／Lens 已於 HEAD 改為 LangGraph＋OpenRouter**（前一輪記為 SDK，已過時）[抽查] |
| C1 成本估算 | FinOps 分析師／架構師 | 現行 story 標籤為「上傳與檢視估價表」；`/api/cost/v1` 有 sets／advice／shares | `/cost` | 可運行；**前一輪「自動取價＋9 operations」敘述已被 HEAD 取代**（見下節）[實讀 openapi／抽查目錄] |
| **D1／D2／D3 IaC** | 平台／開發／資安 | D1 Terraform 產出、D2 IaC 安全掃描、D3 Secret／敏感值處理 | **無頁面、無 API**；僅 Workspace 產圖成功 toast 的「生成 IaC 代碼」按鈕 | **矩陣領先實作**：只有 RBAC 種子＋權限頁標籤＋Coming Soon stub [實讀] |
| J 管理（權限） | 管理員 | 使用者管理、角色授權請求、角色–故事權限矩陣 | `/admin/*` | 可運行 |
| 協作 | 協作者 | 架構圖 CRUD、聊天歷史、分享、WebSocket 同步 | `/api/collab` + WS | 可運行（openapi 見 `api-documentation.md`） |

導覽與落地頁由故事權限驅動：`App.tsx` 的路由表含 `/workspace`（A1）、`/assessment`（A3）、`/cost`（C1）、`/admin/users`／`/admin/authorization-requests`（J3a）、`/admin/role-permissions`（J3b）；**無 D／IaC 路由** [實讀]。

## Story D（IaC 產生）業務現況（本輪焦點）

1. **產品面只有一個入口且為 stub**：Workspace 產圖成功（含 WA collab 通過）後的完成 toast，在 `showCtas` 為真時出現「生成 IaC 代碼」按鈕；點擊呼叫 `showComingSoon('IaC 代碼生成')`，toast 文字為「IaC 代碼生成即將推出」、hint「此功能尚在規劃中，請先繼續對話編輯或手動儲存架構圖。」，並關閉 CTA 區（`WorkspacePage.tsx` L259–265、L964–970）。按鈕**不檢查** `D1` 權限，也不呼叫任何 API [實讀]。
2. **同區塊的 Well-Architected 按鈕是真功能**：`goWellArchitected()` 檢查 A3 view／edit 與 diagramId，必要時引導先儲存再導向 `/assessment`（`WorkspacePage.tsx` L408 起）。IaC 按鈕尚未與其對等落地 [實讀]。
3. **權限矩陣已預先存在 D 柱**：`RolePermissionsPage` 標籤 D1「Terraform 產出」、D2「IaC 安全掃描」、D3「Secret／敏感值」，pillar 顯示名「基礎建設即程式碼」；`rbac_seed_data.DEFAULT_ROLE_PERMISSIONS` 為 `(role, story, view, edit, review)`，**edit=true** 的角色為：D1＝`Project_Architect`、`Developer`、`Platform_Engineer`；D2＝`Platform_Engineer`、`Security_Reviewer`；D3＝`Developer`、`Security_Reviewer`；`FinOps_Analyst` 的 D1／D2／D3 全為 false；其餘角色多為 view-only [實讀]。
4. **決策約束（來自記憶層，非 code）**：D1／D2／D3 預設各對應一個 agent，不由單一 agent 包辦（market-research 階段 correction，2026-11-05）；`direct production IaC` 與 destructive cloud operations 在範圍外，IaC 的任何 apply 皆須 plan＋impact＋rollback＋人工閘門。
5. **不得誤讀**：種子與權限頁的 D 欄 ≠ 已有 IaC 能力。與 C1 歷史「矩陣領先實作」同形（`project.md` reverse-engineering:c9）。

## C1 成本估算的業務現況（前一輪保留，標明已漂移）

前一輪散文記載：`pricing_client` 依雲別自動取價、`sku_mapper`／`sku_ai_resolver`、`cost_pricing_agent`（Claude Agent SDK＋MCP `cloud360-cost`）、Azure／GCP Playwright Calculator runners、`/api/cost` 九個 operations、四張表。[繼承，**已確認不再描述 HEAD**]

本輪觀察到的 HEAD 事實（輕量證據，**未深讀 cost**）：

- `backend/cost/` 目錄現為 `estimate_intake_router`／`estimate_intake_service`／`estimate_parser`／`estimate_readers`／`estimate_validator`／`estimate_audit`／`estimate_access`、`advice_stream_router`／`advice_orchestrator`／`cost_advice_agent`、`pricing_client`／`pricing_azure`／`pricing_gcp`／`pricing_sdk` 等，**已無** `cost_router`／`cost_service`／`cost_calculator`／`sku_mapper`／`*_calculator_runner` [抽查：目錄列表]。
- `main.py` 掛載的是 `estimate_intake_router` 與 `advice_stream_router`，皆在 `/api/cost/v1` [實讀]。
- `openapi.json` 的 `/api/cost/v1/*` 共 6 條路徑、10 個 operations（sets、sets/{id}、advice、advice/stream、shares、share-users）[實讀；以腳本計數]。
- `C1` 的 story 標籤為「上傳與檢視估價表」[實讀 user_router／RolePermissionsPage]。這與 `project.md` 記載的 ADR-0017（估價一律來自上傳的官方估價表）相符。
- 建議（advice）路徑為單節點 LangGraph＋`openrouter_chat_model`（`cost_advice_agent`）[抽查：grep]。

其餘成本細節（資料表、覆寫、稽核）本輪不重述；以 `component-inventory.md` 的 `cost-domain` 標註為準。

## Assessment／Agent 框架現況

| 表面 | 框架 | 證據 |
|---|---|---|
| A1 Design／產圖 | LangGraph（`StateGraph`＋`ChatAnthropic`），經 `llm_provider` 映射 | [抽查] `design_agent.py` L9／L16／L121／L149 |
| A3 Review 建議 | LangGraph（`StateGraph`）＋`langgraph_runtime.openrouter_chat_model` | [抽查] `review_agent.py` L133–181 |
| A3 Lens 作答 | LangGraph（`StateGraph`）＋`openrouter_chat_model` | [抽查] `wa_lens_engine.py` L541–614 |
| C 建議 | LangGraph＋`openrouter_chat_model` | [抽查] `cost_advice_agent.py` L139–156 |
| 規則分數 | 純函式 `wa_rule_engine.evaluate` | [繼承] |
| `langgraph_runtime` | OpenRouter／`ChatOpenAI` helpers；`invoke_graph`／`stream_graph`／`astream_graph`；缺 key → `RuntimeAuthError` | [實讀] |

**重要修正**：前一輪（`261001-a2-langgraph`，掃描當時）記載 Review／Lens 為 Claude Agent SDK、`langgraph_runtime` 未接 Assessment。本輪對 `backend/services/` 與 `backend/cost/` grep `claude_agent_sdk`，**零命中**（以 `claude_agent_sdk` 為 import 名稱搜尋；另以 `claude-agent-sdk|claude-code|claude CLI` 字串搜尋，仍有 `llm_provider.py`、`langgraph_runtime.py`、`tests/test_a3_langgraph_migration.py`、`backend/.env.example`、`deploy/render-env.sh`、`LOCAL-DEV.md` 提及，內容未逐行讀，見 `code-quality-assessment.md`）；`Dockerfile` 頂註已改為「無 Claude Code CLI／Node runtime」。故該 intent 的遷移目標已在 HEAD 落地 [抽查]。尚未複驗：各 orchestrator 的 SSE 事件契約是否同步維持。

## 範圍與邊界

**In scope（目前可運行）**：FastAPI 後端、React SPA、PostgreSQL、staging Docker、CI、gh-aw workflows、Kiwi TCMS。[繼承]

**Out of scope（除非新 ADR）**：雲端供應商 production、direct production IaC、destructive cloud operations、native iOS／Android。

## 與本 intent 的業務關聯

Intent `261105-d-iac-generation` 要為 Story D 補上實作。從 codekb 角度，下游需知：

- 起點是**零**：無 router、無 OpenAPI 條目、無 IaC 純函式模組、無 agent、無頁面、無測試。
- 可複用底座已在 repo：`langgraph_runtime`（OpenRouter＋`invoke_graph`／串流）、`require_story_action("D1"|"D2"|"D3", action)`、Workspace 的 SSE 消費形狀、C 建議路徑的「背景 job＋SSE」形狀。
- 首個 generator 落地即觸發 ADR-0006 的 property-based testing hard constraint；首個 HTTP 端點即觸發 allow／deny 雙向 TestClient 與 `openapi.json` drift 同步。
- CTA 的呈現應與 D1 權限一致（現況對無 D1 edit 的角色仍顯示按鈕）。
