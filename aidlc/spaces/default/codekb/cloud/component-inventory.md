# 元件清冊（Component Inventory）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-11-05｜HEAD `0bffc82`｜intent `261105-d-iac-generation`｜mode **Focused merge（STALE）**
> 元件名稱＝下列 H3；`## Scope of Analysis` 的 `analyzed.components` 僅列**本輪深讀**者。其餘元件保留前一輪散文，標示驗證深度（shallow／inventory）與漂移。
> 證據標籤：`[實讀]`／`[抽查]`／`[繼承]` 同 `business-overview.md`。

## 後端元件

### backend-app-shell

- **深度**：deep（本輪重讀 `main.py`）
- **職責**：載入 `backend/.env`（`load_backend_dotenv(override=True)`）、`configure_provider_env`、CORS（`CORS_ORIGINS`）、startup（`init_db`）、掛載 7 個 router（L52–58）、`GET /` 健康回應。
- **依賴**：`services.{agent,user,collab,review,lens}_router`、`cost.{estimate_intake,advice_stream}_router`、`llm_provider.configure_provider_env`、`database.init_db`。
- **健康**：healthy。
- **本輪**：確認**無 IaC router**；cost 現掛 `estimate_intake_router`／`advice_stream_router`（前一輪為 `cost_router`）[實讀]。

### persistence-orm

- **深度**：shallow（前一輪 deep，STALE demote；表清單未於本輪驗證）
- **職責**：ORM 與 `_ensure_*_schema()`；與 D 相關僅 `role_permissions`。
- **健康**：at-risk（DDL 雙軌）[繼承]。cost 表集合可能已隨 cost 重構改變，**以 HEAD 重讀為準**。

### cost-domain

- **深度**：shallow（前一輪 deep，STALE demote）
- **職責（HEAD 輕量證據）**：估價表上傳／解析／驗證（`estimate_*`）、sets／shares／audit（openapi `/api/cost/v1`）、建議 agent（`cost_advice_agent`，LangGraph＋OpenRouter）、公開／目錄價 `pricing_*` [抽查：目錄列表；實讀：openapi]。
- **漂移**：前一輪所記 `cost_router`／`cost_service`／`cost_calculator`／`sku_mapper`／`*_calculator_runner`／`diagram_extractor`／`price_cache` 在 HEAD **不存在**；「相依方向 `main → cost → services`」仍可能成立但未複驗 [抽查]。
- **健康**：unknown（待 C 柱 intent 重掃）。

### architecture-generation

- **深度**：deep（本輪：`agent_router`）；`design_agent` 僅 grep／skim
- **職責**：A1 產圖 SSE（`/generate`）與 A1↔A3 collab（`/generate-wa-collab`）；`require_arch_action("edit")`；`prompt_guard` 平台自改預檢；LLM 金鑰預檢；`diagram_id` 存取檢查。`design_agent` 為 LangGraph（`StateGraph`＋`ChatAnthropic`）[抽查]。
- **依賴**：`services.rbac`、`prompt_guard`、`llm_provider`、`review_orchestrator.get_accessible_diagram`、`wa_collab_orchestrator`、`design_agent`。
- **健康**：at-risk。docstring 與 log 仍稱「Agent SDK」（過時）；SSE 契約只在 docstring；`MemorySaver`／`_progress_queue` 限制 [繼承]。

### langgraph-runtime

- **深度**：deep（本輪重讀）
- **職責**：OpenRouter（OpenAI-compatible）LangGraph 共用 helpers：`openrouter_chat_model`、`invoke_graph`、`stream_graph`、`astream_graph`、`RuntimeAuthError`、`InvokeOutcome`。刻意與 `llm_provider`／舊 SDK **平行、不改其語意**。
- **依賴**：`langchain-openai`（現已列入 `requirements.txt` [抽查]）。
- **消費者（HEAD）**：`review_agent`、`wa_lens_engine`、`cost_advice_agent`（grep）[抽查]；`design_agent` **不** import。
- **健康**：healthy。註：模組 docstring 稱 cost-advice 節點屬 U7，本模組不擁有業務 graph——D 柱採同一分工。

### wa-review

- **深度**：shallow（前一輪 deep，STALE demote）
- **職責**：A3 評核 SSE、分數、collab；規則純函式 `wa_rule_engine`。
- **漂移**：Review 建議已為 LangGraph＋`openrouter_chat_model`，**非** Claude Agent SDK（`review_agent` L133–181；`tests/test_a3_langgraph_migration.py` 斷言 source 無 `claude_agent_sdk`／`ClaudeSDKClient`）[抽查]。orchestrator 層與 SSE 契約未複驗。
- **健康**：unknown（前一輪 at-risk）。

### lens-management

- **深度**：shallow（前一輪 deep，STALE demote）
- **職責**：Lens 作答與 CRUD。
- **漂移**：`wa_lens_engine.answer_lens_with_agent` 現為 `StateGraph`＋`openrouter_chat_model`（L541–614）[抽查]，前一輪「SDK＋MCP `emit_lens_answers`」不再成立。
- **健康**：unknown。

### collaboration

- **深度**：shallow／inventory
- **職責**：架構圖 CRUD、聊天、分享、WS、`workspace/bootstrap`、`last-opened`（openapi）[實讀 openapi]；Workspace 呼叫之持久化。
- **健康**：at-risk（商業邏輯在 handler）[繼承]。

### identity-and-rbac

- **深度**：deep（本輪限於：`user_router` 的 roles／role-permissions／標籤、`rbac_seed_data`）；`rbac.py`、`auth.py` 僅 skim
- **職責**：JWT、授權狀態、故事級權限矩陣 `(role, story, view, edit, review)`；`CANONICAL_ROLES`、`STORY_IDS`（由種子衍生；D 種子涵蓋 11 個角色）；`require_story_action`／`require_arch_action` 掛載樣板。
- **D 柱種子**：見 `business-overview.md` 與 `code-structure.md`；`FinOps_Analyst` D 全 false。
- **健康**：at-risk。標籤與角色清單存在多份副本（`team.md` 已知：`STORY_FEATURE_LABELS` 與 `RolePermissionsPage` 兩處手寫）。

### llm-gateway

- **深度**：shallow（前一輪 deep，STALE demote）
- **職責**：`LLM_PROVIDER`（`openrouter`｜`cli`）、模型 getter、`configure_provider_env`、token／XML 限額。
- **漂移**：`llm_provider.py` 頂註仍寫「Every LLM feature … claude-agent-sdk … spawns the `claude` CLI」，但 HEAD 後端 import 已零 SDK；`agent_router` 仍呼叫 `configure_provider_env`／`llm_auth_ready`／`auth_error_message` [抽查]。Design 仍靠它的 `ANTHROPIC_*` 映射。
- **健康**：at-risk（註解過時；雙 OpenRouter 適配）。

### openapi-contract

- **深度**：deep（本輪：全 path／operation 盤點）
- **職責**：HTTP 契約凍結快照（42 paths／55 operations）；`/api/cost/v1` 10 operations；**零 IaC 條目**。SSE 端點 200 schema 為空物件。
- **健康**：healthy（drift 閘門）。

### iac-d-pillar-surface

- **深度**：deep（本輪新增；前端 stub＋後端 RBAC 標籤／種子）
- **類型**：**現況＝預留表面，非功能元件**。包含：(1) Workspace「生成 IaC 代碼」按鈕與 `showComingSoon`；(2) D1／D2／D3 在 `user_router.STORY_FEATURE_LABELS`、`RolePermissionsPage` 的標籤與描述；(3) `DEFAULT_ROLE_PERMISSIONS` 的 D 種子。
- **職責（實際）**：讓管理員可設定 D 權限、讓使用者看到「即將推出」；**不**產生、掃描或處理任何 IaC／secret。
- **缺口**：無 router、無 service、無純函式 generator／scanner、無 agent、無 D 頁面／路由、無 OpenAPI 條目、無測試；CTA 未檢查 `D1` 權限。
- **依賴**：`rbac.require_story_action`（待掛）、`langgraph_runtime`（建議底座）、Workspace SSE 消費形狀。
- **健康**：stub。「矩陣領先實作」，不得讀為已有能力。

## 前端元件

### frontend-routing

- **深度**：deep（本輪重讀 `App.tsx`）
- **職責**：路由與落地頁；`CapabilityRoute storyId action` 閘頁；無 D 路由。
- **健康**：at-risk（根導向優先順序為前一輪事實，本輪未重驗）。

### workspace-page

- **深度**：deep（本輪新增：IaC CTA、WA 導覽、權限旗標、toast CTA 列）
- **職責**：A1 工作區——聊天、draw.io 畫布、產圖 SSE、儲存／bootstrap、完成 toast（含 IaC stub 與 Well-Architected 導覽）。
- **依賴**：`/api/architecture/generate-wa-collab`（實際產圖入口）、`/api/collab/*`、`auth-context`（`can`／`canArch`）。
- **健康**：at-risk。大型單檔（>1100 行）；D 柱落地需動此檔。

### role-permissions-page

- **深度**：deep（本輪新增：標籤與 pillar）
- **職責**：J3b 權限矩陣 UI；`PILLAR_LABELS`（D＝基礎建設即程式碼）、story 短名與描述。
- **依賴**：`/api/auth/role-permissions`、`/roles/catalog`。
- **健康**：healthy；標籤副本需與後端同步。

### assessment-page

- **深度**：shallow（前一輪 deep，STALE demote）
- **職責**：`/assessment` 儀表板；發起評核、collab、retry、選圖 [繼承]。
- **健康**：at-risk（大型頁面）[繼承]。

### frontend-cost-support / frontend-cost-page / frontend-shell / frontend-feature-pages

- **深度**：shallow（前一輪或 inventory）
- **職責**：見前一輪；cost 前端現況（上傳估價表流程）本輪未讀。

## 契約、CI、部署、測試（前一輪保留｜shallow）

### contract-validators / ci-core / agentic-workflows / deploy-workflow / deployment-compose / deployment-config / schema-sql-assets / ops-and-sync-scripts / backend-test-suite / frontend-e2e-suite / static-prompt-assets

前一輪盤點可作散文參考；**本輪未重驗證**。測試相關觀察：HEAD 有 41 個 `backend/tests/test_*.py` [抽查：`ls`]；其中 `test_a3_langgraph_migration.py`、`test_langgraph_runtime.py`、`test_cost_advice_agent.py` 與 LangGraph 路徑相關；前一輪 shallow 清單中的 `scripts/validate_cost_calculator_boundary.py`，HEAD 是否仍存在、是否仍對應現行 cost 模組，未驗證。

## 外部與基礎設施

PostgreSQL、embed.diagrams.net、OpenRouter（LLM；`cli` 模式仍保留為本機選項）、n8n（圖示）、Cloudflare Tunnel、Kiwi TCMS。Backend 映像依 `Dockerfile` 頂註已不含 Node／`claude` CLI [抽查]。
