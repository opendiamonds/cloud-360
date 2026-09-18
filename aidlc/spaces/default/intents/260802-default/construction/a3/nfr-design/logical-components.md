# A3 NFR Logical Components

> Unit `U-A3` · Q5=C — `ReviewOrchestrator` owns the state machine


### 1. 邏輯元件圖

```text
FE (Assessment / Workspace)
        |  HTTP + SSE
        v
 ReviewRouter          ← JWT / A3 RBAC / diagram ACL 閘門
        |
        v
 ReviewOrchestrator    ← status 機、timeout、audit log、SSE 事件序
        |
        +---> ReviewRepository (DB)
        +---> WaRuleEngine (sync；啟發式分數／填答／Lens 失敗備援 findings)
        +---> WaLensEngine (離線 Lens 計分＋權威 findings)
        +---> ReviewAgent (Agent SDK，輸入＝Lens findings)
```

### 2. 元件職責

| 元件 | 職責 | 非職責 |
|---|---|---|
| `ReviewRouter` | 路由、依賴注入、將 Orchestrator async 迭代轉 SSE／JSON | 業務狀態機、timeout |
| `ReviewOrchestrator` | `pending→rules_complete→complete｜rules_only｜unsupported`；Lens／Agent；audit；SSE | 解析 XML 細節、LLM prompt |
| `WaRuleEngine` | 純函式啟發式評分；填答關鍵字；Lens 失敗時備援 findings | I/O、auth、UI 權威發現 |
| `WaLensEngine` | 載入 Custom Lens、riskRules 計分、`findings_from_lens_score` | 改 DB status |
| `ReviewAgent` | Agent SDK 串流建議（依 Lens findings） | 改 DB status |
| `ReviewRepository` | CRUD `architecture_reviews` | ACL 決策（由上層傳入已授權上下文） |
| `AuditLogger`（函式／薄包裝） | 結構化 logging 一行 | 持久化 audit 表 |

### 3. 與 FD 對齊說明

Application／Functional Design 原以 `ReviewService` 為編排核心。NFR Design **Q5=C** 將狀態機上收至 **`ReviewOrchestrator`**。Code Generation 應：

1. 新增 `review_orchestrator.py`（或同等）為編排入口；  
2. 若保留 `ReviewService` 名稱，須為 Orchestrator 的別名或薄委派，**不可**兩處各自改 status。

### 4. 無新增基礎設施元件

| 類型 | 本期 |
|---|---|
| Queue / Redis / Worker | ❌ |
| Audit DB table | ❌ |
| Circuit breaker 函式庫 | ❌（單次嘗試即可） |
| SSE resume store | ❌ |

### 5. 客戶端邏輯元件（FE）

| 元件 | NFR 行為 |
|---|---|
| SSE consumer | 消費至 complete／error；中斷後 **不**自動 EventSource 重連同一流 |
| Review detail loader | 中斷或重整 → `GET /reviews/{id}` |
| Retry suggestions button | 僅 `rules_only` 顯示；呼叫 retry API |

### 6. Code Gen 檢查清單（NFR）

- [ ] Orchestrator 單次 `wait_for(60)`  
- [ ] 無自動 Agent retry loop  
- [ ] XML >2MB warn  
- [ ] audit log 欄位齊、無 XML／suggestions  
- [ ] 無全域併發計數器  
- [ ] FE GET 補齊路徑  
