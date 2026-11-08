# 程式品質評估（Code Quality Assessment）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-11-05｜HEAD `0bffc82`｜intent `261105-d-iac-generation`｜mode **Focused merge（STALE）**
> **本輪未執行任何測試、lint、build**；下列數字皆為靜態計數或 grep，不是執行結果。證據標籤：`[實讀]`／`[抽查]`／`[繼承]` 同 `business-overview.md`。

## 測試（本輪相關）

| 項目 | 現況 |
|---|---|
| 測試框架 | `unittest`＋Hypothesis（`team.md` 既成事實）[繼承] |
| 測試檔數 | `backend/tests/test_*.py` 共 41 個（`ls` 計數）[抽查] |
| LangGraph 相關 | `test_langgraph_runtime.py`、`test_langgraph_migration.py`、`test_a3_langgraph_migration.py`（斷言 `review_agent` source 不含 `claude_agent_sdk`／`ClaudeSDKClient`）、`test_cost_advice_agent.py` [抽查] |
| `@given`（property-based） | 多檔含 `@given`（本輪僅 `rg -c` 抽樣前 20 檔，未全量彙總）[抽查] |
| **IaC／D 柱測試** | **無**：深讀路徑與 openapi 無 D 端點可掛 TestClient；dev 報告確認無對應測試 [實讀 dev 報告] |
| 覆蓋率設定 | absent（無法量測 `org.md` 的 80%）[繼承；dev 報告亦確認] |
| 結構性盲區 | LLM 路徑／n8n 圖示取得／本機環境殘值——`project.md` 認定仍成立；D 柱 LLM 路徑落在第一塊盲區 [繼承] |

## Lint／CI（摘要）

前端 ESLint flat config＋`tsc -b`；後端無 Ruff／Black／mypy（`team.md`）。CI／deploy 本輪未重讀 [繼承]。

## 文件品質與漂移（本輪觀察）

| 位置 | 漂移 | 證據 |
|---|---|---|
| `backend/services/agent_router.py` docstring／log | 稱「LLM 迴圈由 design_agent（Agent SDK）負責」「Agent SDK 路徑」；`design_agent` 實為 LangGraph | [實讀 agent_router／抽查 design_agent] |
| `backend/services/llm_provider.py` 頂註 | 稱「Every LLM feature … runs through claude-agent-sdk … spawns the `claude` CLI」；後端 SDK import 已零 | [抽查：head] |
| `backend/Dockerfile` 頂註 | **已更新**（「LangGraph + OpenRouter … no Claude Code CLI / Node runtime」）——前一輪記錄的過時問題**已解決** | [抽查：head] |
| `LOCAL-DEV.md` L25／L70 | 已寫 A3 不再需要 claude CLI；L139／L250／L372 仍提及 `claude` CLI／`command -v claude`，是否仍為現行隱性前置條件未核 | [抽查：rg] |
| `backend/.env.example`、`deploy/render-env.sh` | 仍提及 `claude` CLI（cli 模式說明） | [抽查：rg] |
| `requirements.txt` 的 `fastapi==0.111.0` vs `team.md` 的 `fastapi[standard]==0.141.1` | 版本與 extras 不一致 | [抽查] |
| 前一輪 cost 全節 | 描述的模組已不存在 | [抽查：目錄列表] |

## 技術債（與 D 相關）

1. **矩陣領先實作**：D1／D2／D3 有種子與標籤，無任何後端／頁面／OpenAPI／測試；風險是被誤讀為已有能力（`project.md` NEVER 規則的同形）[實讀]。
2. **CTA 與權限脫鉤**：「生成 IaC 代碼」不檢查 `D1`；無種子權限的角色仍可點到 stub [實讀]。
3. **標籤副本**：`STORY_FEATURE_LABELS`（後端）與 `RolePermissionsPage`（前端）各維護 story 短名，D 新增／更名需兩處同步 [實讀]。
4. **SSE 契約只存於 docstring**：OpenAPI 200 schema 空物件；D 若沿用 SSE，易重蹈 [實讀]。
5. **雙 OpenRouter 適配**並存（`llm_provider` vs `langgraph_runtime`）[實讀 runtime／抽查]。
6. **ADR-0006 PBT**：IaC generator 為點名落點；repo 尚無模組，首個 generator 落地即 blocking [dev 報告＋memory]。
7. **首個 D 端點的測試義務**：allow／deny 雙向 TestClient（`team.md` Q3 定案）＋ OpenAPI／`api.d.ts` drift 同步 [memory]。
8. **God file**：`WorkspacePage.tsx`（>1100 行）、`user_router.py`（`team.md` 記 831 LOC 且無 HTTP 層測試）——D 柱不得趁機改這兩支的結構（`team.md` 分層規則）[繼承／實讀行號]。

## 前一輪保留債（shallow｜未重驗）

Design `_progress_queue` 非 thread-safe、`MemorySaver` 進程內、schema 雙軌、rollback 權限未評估等見前一輪；cost 區（跨模組私有函式、快取重疊、死種子等）**已因 cost 重構而失效或未知**，不得視為 HEAD 現況。前一輪「Dockerfile 過時」與「`langchain-openai` 未 pin／未列入」兩項已在 HEAD 修復 [抽查]。

## 安全基線（摘要）

LLM 經 OpenRouter；缺 key 以 `RuntimeAuthError` 大聲失敗、不自動退回 CLI（`langgraph_runtime` 契約）[實讀]。`/generate*` 有平台自改預檢 [實讀]。IaC 的 IAM／encryption／network exposure／audit logging 四面向於 D 柱落地時須逐項判定（ADR-0006）；本輪無 D 程式碼可評。
