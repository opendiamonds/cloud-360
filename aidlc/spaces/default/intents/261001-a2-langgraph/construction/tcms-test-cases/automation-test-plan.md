# 自動化測試計畫 — A3 Assessment → LangGraph

> Intent：`261001-a2-langgraph`  
> 分桶見 `manual-test-cases.md`。真 LLM／本機 `.env` 歸手動桶。

## 1. 已自動化落點（本 stage 不重寫邏輯）

| 層級 | 路徑 | 涵蓋 |
|---|---|---|
| Backend unittest | `backend/tests/test_a3_langgraph_migration.py` | Review 串流 mock、Lens 結構化答案、無 SDK import、auth 安全訊息、簽名保留 |
| Backend unittest | `backend/tests/test_langgraph_runtime.py` | OpenRouter client、secret redaction |
| Backend unittest | `backend/tests/test_review_agent.py`、`test_wa_lens_engine.py` | fallback／heuristic／score |

規格註解：`test_a3_langgraph_migration.py` 檔首已補 `@purpose`／`@api`／`@given`／`@step`／`@pass`／`@story`。**不**在 TCMS 手寫自動化描述。

## 2. 本 stage 新寫腳本

無。核心腳本已於 `code-generation` 落地；本 stage 僅補規格註解。

## 3. Open items

真實 OpenRouter SSE、重試建議、本機缺金鑰 UI 降級 → 手動 M-1～M-3。

## 4. 突變驗證

對 `test_run_review_agent_streams_chunks_via_openrouter` 暫時把預期 chunks 改成 `["WRONG"]`：

| 步驟 | 結果 |
|---|---|
| 突變後執行該測 | **FAILED**（`Lists differ: ['建議一', '建議二'] != ['WRONG']`） |
| 還原後再跑 | **OK** |

證明該測能抓住「串流內容不對」的回歸，而非永遠綠燈。
