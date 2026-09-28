# NFR Requirements — 釐清問題（langgraph-runtime）

> Unit: `langgraph-runtime`（U6）· kind: **library**  
> Stage: nfr-requirements · 適用產物：security-requirements、tech-stack-decisions、traceability  
> （performance／scalability／reliability／observability 對 library **多為 N/A**；本 unit 僅釘與 OpenRouter 呼叫相關的安全／可測試／tech 邊界）  
> 作答：在每題 `[Answer]:` 後填選項字母（例如 `A`）。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 模組 `backend/services/langgraph_runtime.py`；`invoke_graph → InvokeOutcome`；`stream_graph`／`astream_graph` | FD Q1–Q3=A、R-01／R-02 |
| OpenRouter OpenAI 相容；讀 `OPENROUTER_API_KEY`；不改 `llm_provider` | FD Q2=A、FR10.2 |
| 缺金鑰 → RuntimeAuthError（變數名、不含值）；不 fallback CLI | FD Q5=A、BR10.4 |
| CI mock；真推論本機／手動 smoke | FD Q4=A、BR10.6 |
| 保留 `claude-agent-sdk`；釘 `langgraph`＋OpenAI 相容客戶 | FD Q6=A、FR10.3 |
| 圖節點／建議語意屬 U7；本 unit 無建議節點 | U6 boundaries、BR10.5 |
| 端到端 3–5 分鐘（NFR1）、進度 UI（NFR2）、事件稽核（NFR5）非本 unit 獨責 | requirements／U7／U2 |
| NFR7 TCMS 為 intent 級 blocking；本 stage 是否手寫測案另問 | project.md Mandated |

---

## Questions

### Question 1
**對 OpenRouter 單次推論的逾時怎麼釘？**（本 unit 對外 helper 的預設）

A. **預設 60 秒** HTTP／客戶端逾時；呼叫端（U7）可經 `config` 覆寫。逾時上拋可診斷錯誤（不含金鑰）。**（建議）**

B. **預設 180 秒**（貼齊 NFR1 建議窗的一部分）；可覆寫。

C. **不設預設逾時**——完全交給底層 SDK／呼叫端。

X) Other

[Answer]: A — 預設 60 秒逾時；呼叫端可覆寫；逾時錯誤不含金鑰
---

### Question 2
**暫時性失敗（5xx／網路抖動）的重試？**

A. **本 unit 不做自動重試**；一次失敗即上拋。重試／backoff 由 U7 編排（避免雙重重試放大費用）。**（建議）**

B. **有限重試**：最多 2 次、指數退避（上限例如 5 秒），僅對明確暫時性錯誤。

C. **無限重試直到逾時**（不建議）。

X) Other

[Answer]: A — 本 unit 不做自動重試；重試由 U7 編排
---

### Question 3
**預設模型 slug？**（smoke 與未指定 model 時）

A. **釘一個 OpenRouter 上可用的 Claude／等效 slug**（例如 `anthropic/claude-sonnet-4` 或 code-gen 當下確認的穩定 slug），寫進 tech-stack；U7 可覆寫。**（建議）**

B. **不釘預設**：每次呼叫必須顯式傳 model，否則錯誤。

C. **讀環境變數**（如 `OPENROUTER_DEFAULT_MODEL`），無值則錯誤。

X) Other

[Answer]: A — 釘穩定 OpenRouter slug（tech-stack 寫死；U7 可覆寫）
---

### Question 4
**Tech stack — OpenAI 相容客戶選哪一個？**（FD Q6=A 已定「langgraph＋相容客戶」，此題釘套件）

A. **`langgraph` + 官方 `langchain-openai`（或 `langchain_openai.ChatOpenAI`）**，版本寫死在 `requirements.txt`；base_url 指 OpenRouter。**（建議）**

B. **`langgraph` + 裸 `openai` SDK**（`AsyncOpenAI`），自行組 message；少一層 langchain。

C. **只用 `httpx` 手打 chat completions**（無 openai／langchain-openai）。

X) Other

[Answer]: A — langgraph + langchain-openai；版本釘死；base_url 指 OpenRouter
---

### Question 5
**錯誤與日誌的金鑰紅線（NFR9 精神落在本 unit）？**

A. **契約**：例外訊息、StreamEvent、InvokeOutcome、log 不得含 `OPENROUTER_API_KEY` 值；可含變數名與上游 status code。unittest 至少一條突變／斷言覆蓋。**（建議）**

B. **僅文件載明**；不要求專用測試斷言。

X) Other

[Answer]: A — 例外／事件／log 不得含金鑰值；unittest 覆蓋
---

### Question 6
**本 stage 是否產出 TCMS 手寫測案？**（NFR7）

A. **否**——歸後續 `tcms-test-cases` stage；本 unit 以 unittest＋mock／選跑 smoke 滿足可測試性。**（建議；與 U1 Q6=A 一致）**

B. **是**——本 stage 另寫 TCMS 案例草稿。

X) Other

[Answer]: A — 本 stage 不寫 TCMS；歸 tcms-test-cases
---

## Consolidated Summary Confirmation

**U6 `langgraph-runtime` NFR 定案**

| 項 | 定案 |
|---|---|
| 逾時 | 預設 60 秒；可覆寫（Q1=A） |
| 重試 | 本 unit 不自動重試；交 U7（Q2=A） |
| 預設模型 | tech-stack 釘穩定 OpenRouter slug；U7 可覆寫（Q3=A） |
| 套件 | `langgraph` + `langchain-openai`；版本釘死（Q4=A） |
| 金鑰紅線 | 訊息／事件／log 不含值；有測試斷言（Q5=A） |
| TCMS | 本 stage 不手寫；歸 `tcms-test-cases`（Q6=A） |

**將產出**：security-requirements.md、tech-stack-decisions.md、traceability.json（library：performance／scalability／reliability／observability 標 N/A）。

**後果**：code-gen 須釘相依版本與 60s 預設逾時；真實 OpenRouter 仍為選跑 smoke。

[Answer]: Looks correct

確認後產出 security／tech-stack／traceability。

