# CI/CD Pipeline — U3: u3-design-agent-compound

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)
> 追溯上游基準：
> - [security-design](../nfr-design/security-design.md) (NFR4.3, NFR4.4)

## 1. 服務端測試管線 (Service Test Pipeline)
- **測試命令**: `pytest backend/tests/test_design_agent.py -v`
- **覆蓋標的**:
  - `test_agent_compound_intent_detection`: 驗證多雲對話正確切換至 compound。
  - `test_agent_rbac_edit_permission_required`: 驗證缺乏 A1.edit 權限被阻擋。
  - `test_agent_stream_sse_events`: 驗證 status 與 diagram_generated 事件結構。

