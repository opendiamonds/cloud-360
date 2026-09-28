# Functional Design 問答：U6 `langgraph-runtime`

本 Unit 是 **library**：LangGraph 執行骨架＋OpenRouter（OpenAI 相容）接入，**不含**成本建議圖節點（屬 U7）。B2 DoD：相依可裝、一次成功推論、可重用執行／串流輔助、**不得移除** `claude-agent-sdk`（FR10.3）。

本站釘**行為與邊界**，不寫實作碼。

## Sources

- **[S1]** U6：`unit-of-work.md` — 引入 LangGraph、OpenRouter 接入、圖執行／串流輔助；不含 U7 節點
- **[S2]** FR10.1–10.3；B2 DoD（bolt-plan）
- **[S3]** 既有 `services/llm_provider.py` 服務 **claude-agent-sdk／CLI** 路徑（`OPENROUTER_API_KEY` → Anthropic 相容變數）；LangGraph 需**平行**的 OpenAI 相容路徑（FE-8／feasibility）
- **[S4]** domain `CostAdviceAgent` 擁有圖節點與建議語意；本 Unit 只提供可被 U7 呼叫的執行期底座

---

## Q1 模組落點

- **A.** `backend/services/langgraph_runtime.py`（＋必要時同目錄小輔助模組）— 與既有 agent 服務同層，U7 直接 import
- **B.** `backend/agents/langgraph_runtime/` 套件目錄 — 預留多圖擴充；本 intent 只放 runtime
- **C.** `backend/cost/langgraph_runtime.py` — 掛在 cost 套件下（與估價表同域）
- **X.** Other (please specify)

[Answer]: A — `backend/services/langgraph_runtime.py`（＋必要時同目錄小輔助）；與既有 agent 服務同層
---

## Q2 OpenRouter 客戶端與既有 `llm_provider` 的關係

既有 `llm_provider` 把 OpenRouter 接到 **Anthropic／claude CLI**。LangGraph 走 **OpenAI 相容** chat completions。

- **A.** **新建**獨立 helper（例：`openrouter_openai_client()`），讀既有 `OPENROUTER_API_KEY`＋固定 `https://openrouter.ai/api/v1`；**不**改 `llm_provider` 的 CLI 語意
- **B.** 擴充 `llm_provider` 回傳兩種客戶端（CLI 設定＋ OpenAI 相容 client），單一模組擁有所有 LLM 設定
- **C.** 強制 LangGraph 也經 `claude-agent-sdk`（與 FR10.2／可行性結論矛盾，不建議）
- **X.** Other (please specify)

[Answer]: A — 新建獨立 OpenAI 相容 helper，讀 `OPENROUTER_API_KEY`＋`https://openrouter.ai/api/v1`；不改 `llm_provider` CLI 語意
---

## Q3 公開執行 API 形狀（供 U7 接上）

- **A.** 兩個入口：`invoke_graph(graph, state, *, config?) → state` 與 `stream_graph(graph, state, *, config?) → Iterator[event]`；圖本體由呼叫端（U7）編譯後傳入
- **B.** 單一 `run(graph_factory, input, *, stream: bool)`，內部負責 compile
- **C.** 只提供「已 compile 的預設空圖＋echo 節點」示範物件，U7 自行繞過 helper 直接用 LangGraph API
- **X.** Other (please specify)

[Answer]: A — `invoke_graph` 與 `stream_graph`；圖由呼叫端（U7）編譯後傳入
---

## Q4 B2「一次成功推論」驗證怎麼落地

- **A.** `scripts/smoke_langgraph_openrouter.py`（或同等）＋ unittest **mock** 路徑；真金鑰 smoke 為手動／本機選跑（CI 無金鑰不紅）
- **B.** CI 必跑真實 OpenRouter 呼叫（需 secret）；失敗則整條紅
- **C.** 僅文件記載手動 curl／腳本步驟，無自動化
- **X.** Other (please specify)

[Answer]: A — smoke 腳本＋unittest mock；真金鑰 smoke 手動／本機選跑，CI 無金鑰不紅
---

## Q5 缺 `OPENROUTER_API_KEY` 時 runtime 行為

- **A.** 建構／呼叫時拋明確領域錯誤（訊息含變數名、**不含**金鑰值）；與既有 `llm_auth_ready()` 精神一致——部署缺密要吵
- **B.** 回傳空結果／靜默跳過（讓 U7 自己決定）
- **C.** 自動 fallback 到本機 `claude` CLI（混淆兩條路徑，違反「平行 OpenAI 相容」）
- **X.** Other (please specify)

[Answer]: A — 缺金鑰拋明確領域錯誤（含變數名、不含金鑰值）
---

## Q6 相依套件範圍（本 Unit 引入）

- **A.** 釘 `langgraph`＋官方建議的 OpenAI 相容客戶（例如 `langchain-openai` 或 `openai`），版本寫死在 `requirements.txt`；**保留** `claude-agent-sdk` 不動
- **B.** 只加 `langgraph`，HTTP 呼叫手寫 `httpx` 打 OpenRouter
- **C.** 引入完整 `langchain` 全家桶（範圍過大）
- **X.** Other (please specify)

[Answer]: A — 釘 `langgraph`＋OpenAI 相容客戶；保留 `claude-agent-sdk`
---

## Consolidated Summary Confirmation

**U6 `langgraph-runtime` 行為定案**

| 項 | 定案 |
|---|---|
| 模組落點 | `backend/services/langgraph_runtime.py`（＋必要時同目錄小輔助）（Q1=A） |
| OpenRouter | 新建 OpenAI 相容 helper；讀 `OPENROUTER_API_KEY`＋`https://openrouter.ai/api/v1`；不改 `llm_provider`（Q2=A） |
| 公開 API | `invoke_graph`／`stream_graph`；圖由 U7 編譯後傳入（Q3=A） |
| B2 驗證 | smoke 腳本＋unittest mock；真金鑰本機選跑；CI 無金鑰不紅（Q4=A） |
| 缺金鑰 | 拋明確領域錯誤（變數名、不含值）（Q5=A） |
| 相依 | 釘 `langgraph`＋OpenAI 相容客戶；保留 `claude-agent-sdk`（Q6=A） |

**將產出**：entities.md、rules.md、functional-spec.md、traceability.json（library，無 frontend-components）。

**後果**：與既有 agent SDK 路徑平行共存；U7 擁有圖節點與建議語意，本 Unit 只提供執行／串流底座與一次成功推論的去風險證明。

[Answer]: Looks correct

確認後產出 entities／rules／functional-spec／traceability。
