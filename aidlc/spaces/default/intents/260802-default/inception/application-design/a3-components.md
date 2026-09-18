# A3 Components

> Unit preview: `U-A3` · Story A3 MVP  
> Decisions: `a3-application-design-plan.md`（Q1=D 獨立 Agent＋Anthropic Agent SDK；Q2=B SSE；Q3=A 儀表板頁；Q4=A architecture/reviews；Q5=A ReviewService）


### 元件一覽

| 元件 | 層 | 職責 |
|---|---|---|
| `ReviewRouter` | BE HTTP | `/api/architecture/reviews*`：JWT、A3 RBAC、SSE／查詢歷史 |
| `ReviewService` | BE 應用服務 | 編排：載入 XML → 規則引擎 → 持久化 → 呼叫 Review Agent → 更新建議；推 SSE 事件 |
| `WaRuleEngine` | BE 領域 | 解析 draw.io XML，產出可重現硬性發現與支柱分數（deterministic） |
| `ReviewAgent` | BE AI | **獨立**模組（如 `review_agent.py`）；使用與 A1 **相同** Anthropic Agent SDK + OpenRouter；自有 MCP tool／system prompt；產出建議文案 |
| `ReviewRepository` | BE 資料 | `architecture_reviews`（及 findings JSON）CRUD |
| `AssessmentPage` | FE 頁 | `/assessment`（或 `/reviews`）：選圖、發起評核、歷史列表、詳情 |
| `ReviewPanel` / CTA | FE | Workspace：Well-Architected 按鈕；A1 產圖後 CTA；消費 SSE |
| `Sidebar` 連結 | FE | A3.view 可見「評估儀表板」 |

### 非本 Unit 擁有（依賴）

| 元件 | 擁有 Unit | A3 用法 |
|---|---|---|
| `UserDiagram` / collab | U-A2 | 評核輸入 XML、選圖列表 ACL |
| `DesignAgent` / agent_router | U-A1 | 產圖後 CTA；**不**合併進 design_agent；僅同 SDK 家族 |
| Auth / RBAC | U-J | A3 view／edit／review |

### 介面（高層）

- FE → `ReviewRouter`：HTTP + SSE（`Authorization: Bearer`）
- `ReviewService` → `WaRuleEngine`：同步函式呼叫
- `ReviewService` → `ReviewAgent`：async／串流建議
- `ReviewService` → `ReviewRepository`：ORM
