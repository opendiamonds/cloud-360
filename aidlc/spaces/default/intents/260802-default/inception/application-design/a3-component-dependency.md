# A3 Component Dependency


### 相依矩陣

| From \\ To | ReviewRouter | ReviewService | WaRuleEngine | ReviewAgent | ReviewRepo | UserDiagram | RBAC | DesignAgent |
|---|---|---|---|---|---|---|---|---|
| ReviewRouter | — | uses | — | — | — | — | uses | — |
| ReviewService | — | — | uses | uses | uses | uses | uses | — |
| ReviewAgent | — | — | — | — | — | — | — | **peer**（同 SDK，不呼叫） |
| AssessmentPage | HTTP/SSE | — | — | — | — | list via collab | can(A3) | — |
| Workspace CTA | HTTP/SSE | — | — | — | — | current id | can(A3) | CTA after A1 |

### 通訊模式

```text
[Browser]
   |  Bearer JWT + SSE
   v
ReviewRouter ----> ReviewService ----+----> WaRuleEngine
                      |              |
                      |              +----> ReviewAgent (Agent SDK / OpenRouter)
                      v
                 ReviewRepository ----> PostgreSQL
                      ^
                      |
                 UserDiagram (U-A2) 提供 xml_data
```

### 資料流（單次評核）

1. FE POST `/api/architecture/reviews` `{ diagram_id, provider: "aws" }`  
2. 規則結果入庫 + SSE `rules_done`  
3. Agent 建議串流 + SSE `suggestion_delta`  
4. SSE `complete`；FE 可之後 GET 歷史  

### 耦合注意

- ReviewAgent **不得** import DesignAgent 產圖邏輯；僅可共用薄層 env／SDK bootstrap（若後續抽取）。  
- 規則引擎不得依賴 Agent（保持可測）。
