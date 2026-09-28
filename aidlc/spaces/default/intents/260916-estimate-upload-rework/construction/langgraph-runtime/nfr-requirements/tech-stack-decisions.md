# Tech Stack Decisions — langgraph-runtime

> Unit: `langgraph-runtime`（U6）· kind: **library** · Q1–Q6=A。

| 面向 | 決策 | 理由 |
|---|---|---|
| 語言／執行期 | **既有 Python 3**（backend） | brownfield；無新 runtime |
| 模組位置 | **`backend/services/langgraph_runtime.py`**（＋必要時同目錄小輔助） | FD Q1=A |
| 圖執行框架 | **`langgraph==1.2.11`** | FD Q6=A；PyPI 當前穩定線；釘死版本（code-gen 若需同 minor patch 升級須同步改本表） |
| OpenAI 相容客戶 | **`langchain-openai==1.6.2`**（`ChatOpenAI`，`base_url=https://openrouter.ai/api/v1`） | Q4=A；與 OpenRouter 官方相容路徑 |
| 預設模型 slug | **`google/gemini-3.7-flash`** | 與 `llm_provider._OPENROUTER_DEFAULT_MODEL` 對齊；U7 可覆寫 |
| 逾時預設 | **60 秒** | Q1=A |
| 重試 | **無**（本 unit） | Q2=A |
| 既有 LLM 路徑 | **不改 `llm_provider`／不移除 `claude-agent-sdk`** | FR10.3、FD Q2=A |
| 測試 | **`unittest` + mock**；選跑 `scripts/smoke_langgraph_openrouter.py` | FD Q4=A；不強制 CI 真金鑰 |
| 新基礎設施 | **無**（無佇列、無新服務、無 Playwright） | NFR8 |

## 依賴變更（code-gen 必做）

| 套件 | 動作 | 備註 |
|---|---|---|
| `langgraph` | **新增 `langgraph==1.2.11`** | 圖執行 |
| `langchain-openai` | **新增 `langchain-openai==1.6.2`** | OpenRouter 相容客戶 |
| `claude-agent-sdk` | **保留不動** | FR10.3 |

## 不做

- 不引入完整 `langchain` 全家桶以外、與本路徑無關的實驗套件
- 不在本 unit 安裝 Playwright／瀏覽器
- 不把 LangGraph 路徑接到 `claude` CLI

<!-- confirmed: Looks correct -->
