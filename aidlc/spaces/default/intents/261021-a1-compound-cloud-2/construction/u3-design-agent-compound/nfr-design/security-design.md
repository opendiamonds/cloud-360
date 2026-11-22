# Security Design — U3: u3-design-agent-compound

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)
> 追溯上游基準：
> - [security-requirements](../nfr-requirements/security-requirements.md) (NFR4.3, NFR4.4)

## 1. 安全架構設計 (Security Architecture)
- 套用 `@require_permission("A1.edit")` 攔截器 (NFR4.3)，於 Tool 呼叫前校驗 JWT token 所包含之 claims。
- 提示詞模板採用嚴格邊界標記 (NFR4.4)（`<system_instructions>` 與 `<user_query>`），阻斷越權提示詞注入。
