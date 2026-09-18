# A3 Component Methods

> High-level signatures only; business rules → Construction FD.


### ReviewRouter

| Method | I/O | 目的 |
|---|---|---|
| `POST /api/architecture/reviews` | body: `{ diagram_id, provider? }` → **SSE** | 發起評核；事件含 `rules_done`／`suggestion_delta`／`complete`／`error` |
| `GET /api/architecture/reviews` | query: `diagram_id?` → list JSON | 歷史列表（A3.view） |
| `GET /api/architecture/reviews/{id}` | → review detail JSON | 重開詳情 |

權限：發起需 A3.edit；讀取需 A3.view（或對該 diagram 有權＋A3.view）。

### ReviewService

| Method | I/O | 目的 |
|---|---|---|
| `start_review(user, diagram_id, provider="aws")` | → AsyncIterator[SSEEvent] | 編排全流程 |
| `list_reviews(user, diagram_id?)` | → list[ReviewDTO] | |
| `get_review(user, review_id)` | → ReviewDTO | |

### WaRuleEngine

| Method | I/O | 目的 |
|---|---|---|
| `evaluate(xml: str, provider: str) -> RuleResult` | RuleResult: scores, findings[] | 純函式／可測；無 I/O 副作用 |

### ReviewAgent

| Method | I/O | 目的 |
|---|---|---|
| `run_suggestions(xml_summary, rule_result, …) -> AsyncIterator[str]` | 建議文字串流 | ClaudeSDKClient + A3 MCP tool（例：`emit_review_suggestions`） |

### ReviewRepository

| Method | 目的 |
|---|---|
| `create` / `update_suggestions` / `get` / `list_by_diagram` | 持久化 |

### FE

| 元件方法／行為 | 目的 |
|---|---|
| `AssessmentPage.runReview(diagramId)` | EventSource／fetch stream 消費 SSE |
| `WorkspacePage.openWellArchitected()` | 對 current diagram POST reviews |
| post-A1 CTA handler | 產圖成功後同 POST |
