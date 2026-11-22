# Code Generation Plan — U3: u3-design-agent-compound

> Stage: code-generation (3.5) · Phase: Construction · Scope: feature · Depth: Standard
> Unit: `u3-design-agent-compound` (kind: `service`)
> Upstream References:
> - [functional-spec](../functional-design/functional-spec.md)
> - [rules](../functional-design/rules.md)
> - [entities](../functional-design/entities.md)
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C3, C4)
> - [security-design](../nfr-design/security-design.md)

---

## Testing Contract

```json
{
  "version": 1,
  "methodology": "custom",
  "source": "team",
  "ordering": "先於 `backend/tests/test_diagram_builder_compound.py` 實作單元測試驗證 Hub-and-Spoke 幾何與 n8n 通訊，再進行前端 Toolbar 選單與對話串接。",
  "scope": "feature",
  "test_strategy": "standard",
  "project_type": "brownfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. Specific\nmethodology — TDD, BDD, ATDD, or classic test-after — is captured by the\ntesting-strategy stage when it ships.\n\nUntil then, our default per scope is:\n- `mvp`, `enterprise`, `feature`, `infra` → tests written alongside\n  code; minimum 80% line coverage; tests run in CI before merge.\n- `bugfix`, `security-patch` → regression test for the specific\n  bug/vulnerability; existing test suite must remain green.\n- `poc`, `refactor`, `workshop` → existing test suite remains green;\n  no new test floor required.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "- **Methodology**: custom\n- **Ordering**: 先於 `backend/tests/test_diagram_builder_compound.py` 實作單元測試驗證 Hub-and-Spoke 幾何與 n8n 通訊，再進行前端 Toolbar 選單與對話串接。\n- **Coverage Target**: 維持 `org.md` 最低 80% line coverage 目標宣稱。\n- **變更護欄義務**:\n  - **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 role_permissions seed 變更需雙向驗證。\n  - **B — HTTP 端點變更需 TestClient 測試**：斷言 status code 與 response_model。\n  - **C — 前端資料形狀變更需 e2e 斷言**：涉及前端展示之結構變更需 Playwright 驗證。\n  - **D — 混合雲專屬測試集**：新增 `backend/tests/test_diagram_builder_compound.py`，完整斷言三雲 XML 群組、Hub-and-Spoke 空間佈局、跨雲直角折線與協議標籤、以及 n8n compound 上行與 fallback 降級。"
    },
    {
      "layer": "project",
      "text": "**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含 property-based 測試，不得只有 example-based：IaC generator、cost calculator、agent routing。其餘模組沿用 `org.md` 的預設門檻。"
    }
  ],
  "obligations": {
    "strategy": "standard",
    "strategy_volume": [
      "Five to eight tests per component.",
      "Unit tests plus integration tests for key boundaries.",
      "Add E2E, performance, or security tests when requirements demand them."
    ],
    "scope_floor": [
      "Meet an 80% line-coverage floor.",
      "Run the selected tests in CI before merge."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "custom",
    "runner_step": "Verify the existing test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Verify the existing test runner/configuration and record the exact unit-scoped command.",
      "Custom ordering - 先於 `backend/tests/test_diagram_builder_compound.py` 實作單元測試驗證 Hub-and-Spoke 幾何與 n8n 通訊，再進行前端 Toolbar 選單與對話串接。",
      "Implementation and tests - preserve that exact ordering; do not convert it to layer-local TDD.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:f9e45d666607b24875797eeb270ec8f11e1b604516cc055582e62458984e51cf",
  "contract_sha256": "sha256:97a80fd0481255fd4c527a056644947ee2f760150b832aedae0718f45857d708"
}
```

---

## Implementation Steps

- [x] Step 1: 建立或擴充單元測試驗證 Agent 支援 `provider="compound"`、提示詞包含多雲拓撲指引與權限防護 (對應 US2.1, US2.2, BR3.1, BR3.2, BR3.3)
- [x] Step 2: 擴充 `backend/services/design_agent.py` 之 `draw_architecture_diagram` tool，參數支援 `provider="compound"` 並路由至 `build_compound_diagram_xml` (對應 US2.1, BR3.1)
- [x] Step 3: 更新 `backend/prompts/cloud_architecture_system_prompt.md` 注入 Hub-and-Spoke 混合雲拓撲幾何規範 (AWS 居中、Azure/GCP 分置兩翼) (對應 US2.2, BR3.3)
- [x] Step 4: 加入 `can_edit_architecture` RBAC 權限校驗防護，未授權者阻擋繪圖操作並回傳防護訊息 (對應 BR3.2, ADR-0006)
- [x] Step 5: 執行單元測試驗證通過率 100%，維護 source-manifest 與 traceability 矩陣 (對應 CON3, NFR5.1)
