# Code Summary — langgraph-runtime（U6）

> Unit: `langgraph-runtime` · kind: **library**  
> 計畫：同目錄 `code-generation-plan.md`（5 步，全數完成）  
> Plan Approval：`Approve Plan`（session `cursor-dda1653e-8198-4f07-9792-97a2d6a7d904`）

## 變更檔案

| 檔案 | 變更 | 對應 |
|---|---|---|
| `backend/requirements.txt` | 新增 `langgraph==1.2.11`、`langchain-openai==1.6.2`；保留 `claude-agent-sdk` | Step 1、FR10.3、BR10.3 |
| `backend/services/langgraph_runtime.py` | **新增** OpenRouter 客戶、`invoke_graph`／`stream_graph`／`astream_graph`、`RuntimeAuthError` | Step 2–3、FR10.1–10.2、BR10.*、NFR9.* |
| `backend/tests/test_langgraph_runtime.py` | **新增** 8 個 unittest（mock；CI 不打真 API） | Step 4、BR10.6、NFR7.1 |
| `scripts/smoke_langgraph_openrouter.py` | **新增** 選跑 live smoke；無金鑰 exit 0 | Step 4、BR10.6 |

**未變更（刻意）**：`llm_provider.py`、建議圖節點／提示詞（U7）、查價（U5）、上傳 API（U2）、TCMS 手寫。

## 關鍵實作決定

1. **平行路徑**：`openrouter_chat_model` 只讀 `OPENROUTER_API_KEY`＋`https://openrouter.ai/api/v1`，不改 CLI／Anthropic env。
2. **缺金鑰先於 import**：`RuntimeAuthError` 在載入 `langchain_openai` 之前拋出，訊息含變數名、不含金鑰值。
3. **逾時／重試**：預設 timeout=60s、`max_retries=0`（本 unit 不自動重試）。
4. **回傳形狀**：`invoke_graph → InvokeOutcome`；串流雙入口 sync／async 皆產 `StreamEvent`。
5. **圖拓樸**：runtime 只呼叫傳入物件的 `invoke`／`stream`／`astream`，不內建成本建議節點。

## 測試

| 指令 | 結果 |
|---|---|
| `cd backend && PYTHONPATH=. python3 -m unittest tests.test_langgraph_runtime -v` | 8 OK |
| `python3 scripts/smoke_langgraph_openrouter.py` | SKIP（無金鑰）exit 0 |
| `python3 scripts/validate_repo_contract.py` | exit 0 |

## 與計畫的偏離

無實質偏離。ChatOpenAI 測試以 `sys.modules` stub 注入，避免本機未裝套件時 mock 路徑失敗；CI 仍會依 `requirements.txt` 安裝真實套件。

## 不做（交其他 unit）

成本建議圖節點／提示詞／三類建議（U7）、查價、上傳、TCMS 手寫、CI 強制真 OpenRouter。
