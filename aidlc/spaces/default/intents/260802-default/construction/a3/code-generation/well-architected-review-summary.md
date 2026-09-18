# A3 Code Summary — Well-Architected Review

> Unit `U-A3` · Story A3 MVP · Code Generation 2026-07-23


### 已實作

| 層 | 路徑 | 說明 |
|---|---|---|
| Model | `backend/models.py` → `ArchitectureReview` | 評核持久化 |
| Schema | `backend/database.py` → `_ensure_a3_schema` | 既有 DB 建表 |
| Rules | `backend/services/wa_rule_engine.py` | ~16 啟發式規則；加權分數；lean mxCell |
| Agent | `backend/services/review_agent.py` + `prompts/wa_review_system_prompt.md` | 同 Agent SDK／OpenRouter；獨立 MCP |
| Orchestrator | `backend/services/review_orchestrator.py` | 狀態機、60s、audit log、SSE 事件 |
| API | `backend/services/review_router.py` | POST/GET reviews、retry-suggestions |
| Mount | `backend/main.py` | `/api/architecture` |
| Tests | `test_wa_rule_engine.py`、`test_review_authz.py` | PBT ≥3＋ACL |
| FE | `AssessmentPage.tsx`、`App`、`Sidebar`、`WorkspacePage` CTA／按鈕 | `/assessment` |

### API

- `POST /api/architecture/reviews` → SSE  
- `GET /api/architecture/reviews?diagram_id=`  
- `GET /api/architecture/reviews/{id}`  
- `POST /api/architecture/reviews/{id}/retry-suggestions` → SSE  

### 已知限制／風險

- 多並行 Agent **無**應用層上限（依 NFR Design）  
- SSE 中斷後靠 GET 補齊，不自動重連  
- 無 API key 時規則仍可完成，建議進入 `rules_only`  
- PDF／SPOF／GCP／Azure 規則未做  

### 手動驗收建議

1. 以 Alex／Hannah 登入 → Sidebar「評估儀表板」  
2. 選圖執行評核 → 見分數與發現 → 有 key 時見建議串流  
3. Workspace 產圖 CTA／Well-Architected 按鈕進 `/assessment?diagramId=`  
4. Fiona 對分享圖可開啟同一報告（A3.view）  
