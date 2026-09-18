# A3 NFR Design Patterns

> Unit `U-A3` · Decisions: `construction/plans/a3-nfr-design-plan.md`


### 1. 決策摘要

| Q | 決策 |
|---|---|
| 1 | Agent **單次** 60s；失敗 → `rules_only`；僅顯式 `retry-suggestions` |
| 2 | SSE 中斷後 FE **GET 補齊**；不自動重連 SSE |
| 3 | 規則同步；只解析必要 mxCell；>2MB **warn 仍嘗試** |
| 4 | Audit 用 **Python logging**（結構化一行）；無 audit 表 |
| 5 | **`ReviewOrchestrator`** 擁有狀態機／timeout／audit |
| 6 | **無**應用層並行上限（文件註明風險） |

### 2. Resilience

| Pattern | 作法 |
|---|---|
| Fail-open on rules | 規則成功即持久化；Agent 失敗不回滾規則 |
| Single-shot Agent | `wait_for(60s)` 一次；無自動重試／無退避迴圈 |
| Explicit retry | `POST .../retry-suggestions` 再開一輪 Agent（仍單次 60s） |
| SSE disconnect | 連線斷不保證重播；客戶端 `GET /reviews/{id}` 讀 DB |
| Best-effort process | 進程重啟可丟進行中 SSE；已寫入 status／findings 仍可讀 |

### 3. Performance

| Pattern | 作法 |
|---|---|
| Sync rule path | `WaRuleEngine.evaluate` 在編排內同步執行（目標 p95≤5s） |
| Lean parse | 只抽 mxCell 必要屬性／標籤；不做完整 DOM 美化 |
| Large XML | `len(xml) > 2MB` → **warn** log，仍嘗試；極端失敗 → SSE／HTTP error |
| Agent bound | 60s 硬牆；超時視同 Agent 失敗 → `rules_only` |

### 4. Security

| Pattern | 作法 |
|---|---|
| Authz gate | Router／Orchestrator 入口：JWT、非 Pending、A3 + diagram ACL |
| Structured audit | `logger.info`／專用 logger：`action`, `user_id`, `review_id`, `diagram_id` |
| No sensitive bodies | log **禁止** XML、suggestions 全文 |
| Provider unsupported | 建 `unsupported` 列；仍打 audit（action=`review_unsupported`） |

### 5. Scalability

| Pattern | 作法 |
|---|---|
| No app throttle | 不實作全域 Agent 計數器／每圖互斥 |
| Capacity note | 文件與 code summary 註明：多並行依賴 Uvicorn／OS 記憶體；過載表現為慢或 5xx |

### 6. Observability

| Pattern | 作法 |
|---|---|
| Timing logs | 規則耗時、Agent 耗時、status 轉換 |
| Optional counters | 若現有 metrics 存在：complete／rules_only／unsupported；否則僅 log |

### 7. 對 NFR Requirements 追溯

| NFR ID | 本設計落點 |
|---|---|
| NFR-A3-01／01a | Authz + logging audit |
| NFR-A3-03／04 | Single-shot timeout + rules_only |
| NFR-A3-04a／06 | 無併發閘 + GET 補齊 |
| NFR-A3-07 | 結構化 timing／status log |
