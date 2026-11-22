# Logical Components — U3: u3-design-agent-compound

> Stage: nfr-requirements (3.2) / nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 邏輯元件架構 (Logical Component Architecture)
- `DesignAgentService`: 管理對話狀態與 LLM 互動鏈。
- `MultiCloudPromptBuilder`: 動態組裝多雲提示詞與幾何規則。
- `RbacPermissionGuard`: 權限檢查切面裝飾器。

