# Code Generation Plan — U2: u2-compound-diagram-builder

> Stage: code-generation (3.5) · Phase: Construction · Scope: feature · Depth: Standard
> Unit: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> Upstream References:
> - [functional-spec](../functional-design/functional-spec.md)
> - [rules](../functional-design/rules.md)
> - [entities](../functional-design/entities.md)
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C2, C3)
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

- [x] Step 1: 擴充單元測試集 `backend/tests/test_diagram_builder_compound.py`，新增 U2 Hub-and-Spoke 幾何座標、跨雲折線與純白膠囊標籤測試案例 (對應 US3.1, US3.2, US3.3, US3.4)
- [x] Step 2: 實作 Hub-and-Spoke 空間佈局演算法 `calculate_compound_layout`，確保 Azure 左(360px)、AWS 中(480px)、GCP 右(360px) 與 120px 緩衝走廊 (對應 US3.1, BR2.2, BR2.3)
- [x] Step 3: 實作 `build_compound_diagram_xml`，套用 `GROUP_STYLES` 容器樣式並進行節點分組佈局 (對應 US3.1, US3.2, BR2.1)
- [x] Step 4: 實作跨雲直角折線路由 (`orthogonalEdgeStyle`) 與純白膠囊圓角協議標籤 (`#FFFFFF` 背景、`#1E293B` 文字、13.5:1 對比度) (對應 US3.3, US3.4, BR2.4, BR2.5)
- [x] Step 5: 整合 XML 實體轉義與防禦性校驗，確保產出合法之 Draw.io / mxGraph XML (對應 NFR2.1, NFR4.1)
- [x] Step 6: 執行全套單元測試驗證通過率 100%，更新 source-manifest 與 traceability 矩陣 (對應 CON3, NFR5.1)
