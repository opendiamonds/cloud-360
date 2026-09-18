# A3 Application Design Plan & Questions

> Stage: Inception → Application Design（A3）  
> Inputs: `a3-well-architected-requirements.md`, `stories.md` §A3, `a3-execution-plan.md`  
> Hard constraint: LLM path = **same Anthropic Agent SDK + OpenRouter as A1**


### 執行檢查清單

- [x] `application-design/a3-components.md`
- [x] `application-design/a3-component-methods.md`
- [x] `application-design/a3-services.md`
- [x] `application-design/a3-component-dependency.md`
- [x] `application-design/a3-application-design.md`（彙總）
- [x] Q1 解讀：獨立 Agent＋Anthropic Agent SDK（不併 design_agent）
- [ ] 補 `frontend-backend-specification.md` 索引（可於 Units／FD 一併補；本回合以 a3-* 為準）

---

## Question 1
A3 的 **Agent 程式邊界**怎麼切？（皆須共用 A1 的 Agent SDK runtime）

A) **新模組** `review_agent.py`（或同等）：獨立 MCP server／tool（如 `emit_review_suggestions`），與 `design_agent.py` 並列，共用 env／SDK 初始化 helper

B) **擴充** `design_agent.py`：同一 MCP server 加 A3 tool；依呼叫情境切 system prompt

C) **抽出共用** `agent_runtime.py`：A1／A3 都呼叫；各自保留 `design_agent`／`review_agent` thin wrapper

D) Other (please describe after [Answer]: tag below)

[Answer]:Ｄ 獨立agent 但是要使用anthropic agent sdk

### Question 2
評核 API 的**回應型態**？

A) **同步 JSON**：一次回傳規則發現＋（完成後的）LLM 建議

B) **SSE**（對齊 A1 generate）：先推規則結果，再推 LLM 建議進度／完成

C) **兩段式**：`POST` 立即存規則結果並回 `review_id`；客戶端再 `GET`／輪詢取 LLM 建議

D) Other (please describe after [Answer]: tag below)

[Answer]:B

### Question 3
**評估儀表板**放哪？

A) 新路由頁（如 `/assessment` 或 `/reviews`）＋ Sidebar 連結（需 A3.view）

B) 做在 `WorkspacePage` 內的全屏 panel／drawer，不另開頁

C) Admin 區子頁（與授權申請同層）

D) Other (please describe after [Answer]: tag below)

[Answer]:A

### Question 4
後端 **API 前綴**偏好？

A) `/api/architecture/reviews…`（掛在 architecture 模組旁，靠近 A1）

B) `/api/reviews…`（獨立 router）

C) `/api/collab/diagrams/{id}/reviews…`（掛在 diagram 資源下）

D) Other (please describe after [Answer]: tag below)

[Answer]:A

### Question 5
規則引擎與 Agent 的**編排擁有者**？

A) **ReviewService**（應用服務）先跑規則，再呼叫 review Agent；router 只做 HTTP／權限

B) **Agent 主導**：Agent tool 內呼叫規則函式（較難測、耦合高）

C) Other (please describe after [Answer]: tag below)

[Answer]:A
