# Security Requirements — U3: u3-design-agent-compound

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 安全需求 (Security Targets)
- **RBAC 授權檢驗 (NFR4.3)**: 強制要求 `A1.edit` 權限，未授權者阻擋工具調用。
- **Prompt Injection 防護 (NFR4.4)**: 提示詞模板隔離使用者輸入，防止惡意指令覆蓋系統規則。
