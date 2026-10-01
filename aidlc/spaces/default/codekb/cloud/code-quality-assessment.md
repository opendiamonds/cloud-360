# 程式品質評估（Code Quality Assessment）

> Reverse Engineering 合成產物｜repo `cloud`｜掃描日 2026-10-01｜intent `261001-a2-langgraph`｜mode **Focused merge（STALE）**
> 本輪未執行測試套件。成本／CI 盲區等前一版發現保留為 shallow 參考；下列為 Assessment／LangGraph 焦點更新。

## 測試（本輪相關）

| 項目 | 現況 |
|---|---|
| LangGraph | `backend/tests/test_langgraph_runtime.py`、`test_langgraph_migration.py`（deep） |
| 手動 | `backend/test_agent.py`；`scripts/smoke_langgraph_openrouter.py`（無 key 則 SKIP） |
| `test_llm_provider.py` | 存在但**未深讀** |
| 覆蓋率設定 | 仍 absent（前一版） |
| 結構性盲區 | LLM 路徑／n8n／本機殘值——`project.md` 認定仍成立（本輪未發現新閘門） |

## Lint／CI（摘要）

前端 ESLint＋tsc；後端無 linter／formatter／typecheck（前一版）。CI／deploy 細節未本輪重讀。

## 文件品質與漂移（本輪）

- **Dockerfile L2–5**：仍寫 Design 由 `ClaudeSDKClient` 驅動——**過時**（Design 已 LangGraph；CLI 仍為 Review／Lens）。
- **`llm_provider.py` L3–4**：寫「Every LLM feature … claude-agent-sdk」——**過時**（Design／`langgraph_runtime` 例外）。
- Router／agent docstring 其餘仍詳盡。

## 技術債（本輪焦點）

1. **雙框架並存**：Design＝LangGraph；Review／Lens＝SDK——本 intent 重構目標。
2. **`langgraph_runtime` 與 Assessment 斷開**；且與 `llm_provider` 雙 OpenRouter 適配。
3. **依賴缺口**：`claude-agent-sdk`、`langchain-openai` 未 pin／未列入 `requirements.txt`。
4. **Design `_progress_queue`**：非 thread-safe 多租戶；**MemorySaver** 進程內、重啟即失。
5. **Intent「A2」vs story「A3」**命名不一致。
6. **God modules**（前一版列舉仍參考）：`AssessmentPage`、`diagram_builder`、`wa_rule_engine` 等。

## 前一版保留債（shallow｜未重驗）

部署缺 Playwright 瀏覽器、cost 跨模組私有函式、schema 雙軌、雙層價目快取、`C1b` 死種子、slot 死碼、rollback 權限未評估等——見前一版完整清單；對本 refactor 非首要，但 STALE 後不得視為已重新驗證。

## 安全基線（摘要）

LLM 經 OpenRouter 或本機 CLI；缺 key 須失敗可見。ADR-0006 其餘面向未本輪深度重驗。
