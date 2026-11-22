# Infrastructure Design Questionnaire — U3: u3-design-agent-compound

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)
> 追溯上游基準：
> - [security-design](../nfr-design/security-design.md) (NFR4.3, NFR4.4)
> - [logical-components](../nfr-design/logical-components.md)

---

## 1. 基礎設施設計範疇說明 (Infrastructure Scope for Service Unit)

依據 `produces_kinds`，`u3-design-agent-compound` 作為 `service` 類型單元，產出：
- `infrastructure-specification.md`: FastAPI 服務容器運行規格、資源配額。
- `monitoring-design.md`: SSE 串流連線數、延遲與錯誤指標監控。
- `cicd-pipeline.md`: 服務端自動化整合測試與 Lint 檢查。
- `traceability.json`: 追溯上游 `NFR4.3`, `NFR4.4`。

---

## 2. 關鍵確認問卷 (Clarifying Questions)

### Q1. 服務部署模型 (Service Deployment Model)
本單元之運行環境為何？
- [A] **既有 FastAPI 後端容器共享運行**：作為既有 backend 服務之擴充路由與模組，無需額外新增獨立容器或 Kubernetes Deployment。（推薦）
- [B] **獨立微服務容器**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出全套 Service Infrastructure Design 產物前，請確認以下彙整摘要正確無誤：

- **部署模型 (Q1)**: [A] 既有 FastAPI 後端容器共享運行，無額外微服務維運負擔。

Does this all look correct before I generate the infrastructure design artifacts for U3?
- Looks correct
- Request changes

[Answer]: Looks correct
