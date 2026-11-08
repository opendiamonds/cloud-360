# 程式結構（Code Structure）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-11-05｜HEAD `0bffc82`｜intent `261105-d-iac-generation`｜mode **Focused merge（STALE）**
> 證據標籤：`[實讀]`＝本輪 analyzed.paths；`[抽查]`＝architect 本輪目錄列表／grep；`[繼承]`＝前一輪未複驗。

## 頂層目錄與檔案分佈

應用程式碼為 `backend/` + `frontend/`。本輪深讀集中在 Workspace／RBAC 矩陣／A1 agent router／`langgraph_runtime`／`main.py`／`openapi.json`；其餘為 skimmed 或 inventory。

| 目錄 | 性質（本輪） |
|---|---|
| `backend/services/` | **焦點檔**：`agent_router`、`user_router`、`langgraph_runtime`、`rbac_seed_data` 深讀；其餘（`rbac`、`design_agent`、`review_*`、`wa_*`、`collab_router`…）僅 skim／grep |
| `backend/cost/` | 目錄列表已與前一輪不同（見下）；僅 skim [抽查] |
| `frontend/src/pages/` | `WorkspacePage.tsx`、`RolePermissionsPage.tsx` 深讀（IaC／D 相關符號與關鍵區段）；其餘 skim |
| `frontend/src/App.tsx` | 深讀：路由表 |
| `openapi.json` | 深讀：path／operation 盤點（42 paths、55 operations；腳本計數） |
| `aidlc/`、`.claude/`、`deploy/`、`scripts/` | 未深讀 |

## `backend/` 組織

`backend/` 為 flat module（無頂層 `__init__.py`）。

| 子目錄／檔案 | 內容 | 本輪深度 |
|---|---|---|
| `main.py` | `load_backend_dotenv`、`configure_provider_env`、CORS、startup（`init_db`）、7 個 `include_router`（L52–58） | **deep** |
| `services/agent_router.py` | A1 `POST /generate`、`/generate-wa-collab`（SSE）；`require_arch_action("edit")`；`prompt_guard` 預檢；docstring 契約段 | **deep** |
| `services/user_router.py` | `/api/auth`：登入／註冊／使用者管理／授權請求／roles／role-permissions；`STORY_FEATURE_LABELS` 含 D1／D2／D3 | **deep（D／RBAC 相關區段）** |
| `services/rbac_seed_data.py` | `DEFAULT_ROLE_PERMISSIONS`；D1／D2／D3 種子（L117–149） | **deep** |
| `services/langgraph_runtime.py` | `openrouter_chat_model`、`invoke_graph`／`stream_graph`／`astream_graph`、`RuntimeAuthError` | **deep** |
| `services/rbac.py` | `STORY_IDS`（L37）、`require_arch_action`（L188）、`require_story_action`（L255） | skim（符號層） |
| `services/design_agent.py`、`review_agent.py`、`wa_lens_engine.py` | LangGraph agent；見 `architecture.md` | skim／grep [抽查] |
| `services/llm_provider.py`、`llm_limits.py` | Provider 開關與限額 | skim（前一輪 deep，已 demote） |
| `cost/` | HEAD 現有：`estimate_*`（intake／parser／readers／validator／audit／access）、`advice_*`、`cost_advice_agent`、`pricing_*`、`sku_catalog`、`workload_context`、`config` 與 yaml 資產 | skim [抽查：目錄列表] |
| `tests/` | 見 `code-quality-assessment.md`（HEAD 有 41 個 `test_*.py`；`ls` 計數） | skim [抽查：目錄列表] |
| `Dockerfile`、`requirements.txt` | 本輪僅 head／全文讀取輕量複驗（見 `technology-stack.md`），不在 analyzed.paths | [抽查] |

### 前一輪結構敘述的漂移

前一輪 `backend/cost/` 的 `cost_router`、`cost_service`、`cost_calculator`、`sku_mapper`、`*_calculator_runner`、`diagram_extractor`、`price_cache` 在 HEAD 目錄列表**皆不存在** [抽查]。前一輪該節與「11 張 ORM 表」「`_ensure_cost_schema`」等屬 [繼承]，不得視為 HEAD 現況。

## IaC／D 相關檔案分佈（本輪重點）

| 符號 | 位置 | 說明 |
|---|---|---|
| `showComingSoon('IaC 代碼生成')` | `frontend/src/pages/WorkspacePage.tsx` L259–265（定義）、L966（呼叫） | 前端 stub [實讀] |
| 「生成 IaC 代碼」按鈕 | 同檔 L964–970 | 與 `goWellArchitected()` 同列 [實讀] |
| `D1`／`D2`／`D3` 標籤 | `RolePermissionsPage.tsx` L41–43（短名）、L75–77（描述）；`user_router.py` L71–73 `STORY_FEATURE_LABELS` | 標籤兩處手寫副本 [實讀] |
| `PILLAR_LABELS` D＝「基礎建設即程式碼」 | `RolePermissionsPage.tsx` | [實讀 dev 報告] |
| D 種子 | `rbac_seed_data.py` L117–149 | 33 列（11 角色 × 3 story）[實讀] |
| 後端 IaC 模組／router／頁面／測試 | — | **無**（`frontend/src` 與 `backend`（排除 tests）對 `iac|terraform` 不分大小寫 grep，僅上列命中）[抽查] |

## 程式慣例

- WA 引擎 `wa_*`；router `*_router.py`；logger 多為 `"cloud360.<module>"`（`agent_router` 用 `__name__`）。[繼承／實讀 agent_router]
- 前端 `fetch` 一律經 `apiUrl()`（`config/api.ts`）。[繼承；dev 淺層確認]
- 標籤副本：story 短名在 `user_router.STORY_FEATURE_LABELS` 與 `RolePermissionsPage` 各維護一份（D 柱新增或更名須兩處同步；`team.md` 單一真實來源規則）。

## 資料模型（摘要｜繼承）

前一輪記載 11 張 ORM 表與 `_ensure_*_schema` 補丁；本輪未重讀 `models.py`／`database.py`，且 cost 區已漂移，故**表清單以 HEAD 重讀為準**。與 D 直接相關者僅 `role_permissions`。

## `frontend/` 組織

| 路徑 | 本輪 |
|---|---|
| `src/App.tsx` | deep：路由表含 `/workspace`（A1）、`/assessment`（A3）、`/cost`（C1）、`/admin/users`、`/admin/authorization-requests`（J3a）、`/admin/role-permissions`（J3b）；無 D 路由 |
| `src/pages/WorkspacePage.tsx` | deep（IaC CTA、WA 導覽、權限旗標） |
| `src/pages/RolePermissionsPage.tsx` | deep（標籤、pillar） |
| `src/context/auth-context.ts`、`src/config/api.ts` | skim |
| 其餘 pages／components／cost | skim／inventory |

## 建置與產物鏈

| 產物 | 來源 | 守門 |
|---|---|---|
| `openapi.json` | `backend/scripts/dump_openapi.py` | CI `--check`（`team.md`） |
| `frontend/src/types/api.d.ts` | `gen:types` | `check:types` |
| backend 映像 | `backend/Dockerfile`（python:3.12-slim；本輪 head 所見無 Node／claude CLI）[抽查] | CI docker build |
