# NFR Design Questionnaire — U3: u3-design-agent-compound

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)
> 追溯上游基準：
> - [security-requirements](../nfr-requirements/security-requirements.md) (NFR4.3, NFR4.4)
> - [performance-requirements](../nfr-requirements/performance-requirements.md)
> - [functional-spec](../functional-design/functional-spec.md)

---

## 1. 單元非功能設計邊界說明 (NFR Design Scope for Service Unit)

本單元 `u3-design-agent-compound` 作為後端服務單元，產物包含：
1. **performance-design.md**: SSE 非同步串流與緩衝佇列設計。
2. **security-design.md**: RBAC 裝飾器 (`@require_permission("A1.edit")`) 與 Prompt 注入邊界。
3. **scalability-design.md**: FastAPI async 連線池與非阻塞排程。
4. **reliability-design.md**: 結構化 JSON 驗證與 1 次重試狀態機。
5. **observability-design.md**: 結構化日誌輸出格式與分佈式追蹤整合。
6. **logical-components.md**: `DesignAgentService` 與 `DiagramToolExecutor` 元件劃分。

---

## 2. 非功能設計關鍵問卷 (Clarifying Questions)

### Q1. RBAC 權限攔截實作模式 (RBAC Enforcement Pattern)
在 Agent Tool 呼叫前，權限檢查採何種架構實作？
- [A] **依賴注入裝飾器 (FastAPI Dependency / Decorator)**：在工具入口函式套用 `@check_permission("A1.edit")`，未達標自動產生友善拒絕事件。（推薦）
- [B] **在業務程式碼內部手動 if 判斷**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出全套 Service NFR Design 產物前，請確認以下彙整摘要正確無誤：

- **RBAC 模式 (Q1)**: [A] 依賴注入裝飾器 `@check_permission("A1.edit")`。

Does this all look correct before I generate the NFR design artifacts for U3?
- Looks correct
- Request changes

[Answer]: Looks correct
