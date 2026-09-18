# A3 Services


### ReviewService（編排核心）

1. 驗證使用者對 `diagram_id` 可讀＋A3.edit  
2. 載入 `xml_data`  
3. `WaRuleEngine.evaluate` → 寫入 review 列（status=`rules_complete`）→ SSE `rules_done`  
4. 呼叫 `ReviewAgent`（Anthropic Agent SDK + OpenRouter）→ 串流建議 → SSE 增量  
5. 建議完成 → 更新 DB（status=`complete`）→ SSE `complete`  
6. Agent 失敗：保留規則結果；SSE `error`（suggestions 可空）；status=`rules_only` 或同等  

### ReviewAgent 與 A1 關係

| 項目 | A1 DesignAgent | A3 ReviewAgent |
|---|---|---|
| SDK | Anthropic Agent SDK | **相同** |
| 路由／環境 | OpenRouter env 映射 | **相同約定** |
| 模組檔 | `design_agent.py` | **獨立** `review_agent.py`（Q1=D） |
| MCP | `cloud360-design` / draw tool | **獨立** server／tool（建議文案） |
| System prompt | 產圖 | WA 建議（AWS 為主） |

禁止：另起非 Agent SDK 的平行 LLM HTTP 客戶端作為主路徑。

### SSE 事件（建議契約）

| event / type | payload 摘要 |
|---|---|
| `rules_done` | `review_id`, scores, findings |
| `suggestion_delta` | text chunk |
| `complete` | full suggestions, status |
| `error` | code, message, `review_id?` |

### FE 編排

- AssessmentPage / Workspace：開 SSE → 先渲染規則結果 → 再填建議  
- Sidebar：A3.view → `/assessment`
