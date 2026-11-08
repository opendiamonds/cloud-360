# 相依關係（Dependencies）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-11-05｜HEAD `0bffc82`｜intent `261105-d-iac-generation`｜mode **Focused merge（STALE）**
> 證據標籤：`[實讀]`／`[抽查]`／`[繼承]` 同 `business-overview.md`。

## 跨套件相依方向

```
backend/main.py ──► backend/services/*_router ──► services (rbac / llm_provider / langgraph_runtime) ──► models / database
                └─► backend/cost/*_router      ──► services.langgraph_runtime（cost_advice_agent）
```

- `main.py` 直接 import `services` 的 5 個 router 與 `cost` 的 2 個 router [實讀]。
- `cost.cost_advice_agent` → `services.langgraph_runtime`（lazy import，L139）[抽查]。
- 前一輪「`services` 不 import `cost.*`」本輪**未反證也未複驗**（[繼承]）；cost 內部結構已漂移，不得沿用邊表。

## 與 Story D 相關的相依邊（本輪）

| 來源 | 目標 | 備註 |
|---|---|---|
| `WorkspacePage` | `/api/architecture/generate-wa-collab`、`/api/collab/*` | 實際產圖入口（A1↔A3）[實讀] |
| `WorkspacePage`「生成 IaC 代碼」 | **無**（`showComingSoon`） | 不連任何 API、不查 D1 [實讀] |
| `WorkspacePage`「Well-Architected」 | `can A3`／`canArch`、`/assessment`、儲存圖 API | 對照組 [實讀] |
| `RolePermissionsPage` | `/api/auth/role-permissions`、`/roles/catalog` | D 標籤與矩陣編輯 [實讀] |
| `user_router` | `rbac_seed_data.DEFAULT_ROLE_PERMISSIONS`、`CANONICAL_ROLES`、`STORY_IDS` | reset-defaults／roles [實讀] |
| `agent_router` | `rbac.require_arch_action`、`prompt_guard`、`design_agent`、`wa_collab_orchestrator`、`review_orchestrator.get_accessible_diagram`、`llm_provider` | A1 路徑 [實讀] |
| `rbac.require_story_action` | `get_current_user`、`get_db`、`user_can` | D 端點可直接 Depends；目前無 D 消費者 [抽查] |
| `langgraph_runtime` | `langchain-openai`（lazy）、`OPENROUTER_API_KEY` | 消費者：`review_agent`、`wa_lens_engine`、`cost_advice_agent`；**D 尚無** [實讀／抽查] |
| `design_agent` | `langchain-anthropic`、`llm_provider` 的 `ANTHROPIC_*` | 不經 `langgraph_runtime` [抽查] |

**未來 D 的相依建議（非定案）**：`d*_router` → service → 純函式核心（不得 import `httpx`／DB session／`HTTPException`，對齊 `team.md` 三層與 ADR-0006 落點）；LLM 節點經 `langgraph_runtime`；授權經 `require_story_action("D1"|"D2"|"D3", …)`；平台自改預檢沿用 `prompt_guard`。

## 雙 OpenRouter 適配（仍並存）

1. `llm_provider._configure_openrouter_env`：設 `ANTHROPIC_BASE_URL`／`ANTHROPIC_AUTH_TOKEN`，供 Design `ChatAnthropic` 使用 [繼承／抽查]。
2. `langgraph_runtime.openrouter_chat_model`：`ChatOpenAI`＋OpenAI-compatible base，Review／Lens／Cost advice 使用 [實讀]。

D 柱選 (2) 可避免擴大 (1) 的適配面。

## 外部套件共用

| 套件 | 消費者 | 備註 |
|---|---|---|
| `langgraph`／`langchain-*` | `design_agent`、`review_agent`、`wa_lens_engine`、`cost_advice_agent`、`langgraph_runtime` | 未 pin；`langchain-openai` 已列入 requirements [抽查] |
| `claude-agent-sdk` | **後端無 import** | 不在 requirements；`tests/test_a3_langgraph_migration.py` 斷言 Review source 無 SDK import [抽查] |
| `httpx` | `llm_provider`、cost（pricing 等） | |
| `hypothesis` | 測試 | PBT hard constraint 的工具 |

## `backend/cost/`（⚠ 前一輪邊表與「八類掛鉤」已不可沿用）

前一輪的成本套件 DAG（`cost_router → cost_service → …`）與八類掛鉤（CI／env／DDL／RBAC／前端／OpenAPI／測試）所指檔案多數已不在 HEAD。HEAD 重寫後之邊未讀，**不在此重建**；下游若需 cost 相依，請以專門的 C 柱重掃為準。

## 建置期相依

`openapi.json` ← `dump_openapi.py`；`api.d.ts` ← `gen:types`；`deploy/.env` ← `render-env.sh`；DB init ← `schema_rbac.sql`（僅空 volume）。[繼承]
