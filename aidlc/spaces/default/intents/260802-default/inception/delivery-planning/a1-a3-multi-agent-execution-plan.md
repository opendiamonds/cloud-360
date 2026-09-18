# A1 ↔ A3 Multi-Agent — Execution Plan

> Requirements: `inception/requirements/a1-a3-multi-agent-requirements.md`  
> Answers: `inception/plans/a1-a3-multi-agent-questions.md`  
> Branch: `luojingting/feat/a1-ux-optimize`


### 1. 範圍與影響

| 面向 | 判定 |
|---|---|
| 架構 | 新增 `wa_collab_orchestrator`；複用 design_agent／review_agent／lens |
| 資料模型 | 可不新增表；結束可寫 `architecture_reviews` |
| API | 新增 SSE：`POST /api/architecture/generate-wa-collab` |
| FE | Workspace 產圖改走協作＋預覽套用；Assessment 加優化按鈕 |
| 部署 | 無 schema 強制變更 |

### 2. 階段取捨

| 階段 | 執行？ | 理由 |
|---|---|---|
| RA／WP | ✅ | 本輪 |
| User Stories | ✅ | A1／A3 增量 AC |
| FD | ✅ 精簡 | 狀態機＋SSE 契約 |
| Code Gen | ✅ | 後端 orchestrator → FE |
| Build & Test | ✅ | 單元測 score／FSM；手動 E2E |

### 3. 工作包

1. **評分可重用函式** — 對 XML＋provider 跑規則＋lens，回傳 overall／findings（不強制建 review）  
2. **Collab orchestrator** — 2 輪 FSM、雙 speaker SSE、達標／失敗  
3. **API** — `generate-wa-collab`（messages、current_xml、provider?）  
4. **Workspace FE** — 改呼叫、transcript、preview、套用  
5. **Assessment FE** —「優化至 WA ≥ 80」  
6. **測試／摘要／checklist**

### 4. 風險

| 風險 | 緩解 |
|---|---|
| 兩輪仍難達 80 | 硬失敗＋人工；findings 清楚列出 |
| LLM／lens 耗時 | 進度事件；timeout 與 A3 對齊 |
| 對話成本 | max_turns／compact findings |
