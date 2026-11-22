# Code Summary — U3: u3-design-agent-compound

> Stage: code-generation (3.5) · Phase: Construction · Scope: feature · Depth: Standard
> Unit: `u3-design-agent-compound` (kind: `service`)

---

## 1. 交付與修改程式碼清單 (Delivered & Modified Code Artifacts)

- **`backend/services/design_agent.py`**:
  - 擴充 `@tool draw_architecture_diagram`：
    - 支援 `provider="compound"` 混合雲合約入參。
    - 支援 `clouds` 與 `connections` 參數，並於混合雲模式下直接調用 `build_compound_diagram_xml`，若僅傳入傳統 `groups/nodes/edges` 亦具備自動適配映射至 Azure/AWS/GCP 三雲容器之能力。
    - 引入 `can_edit: bool = True` 權限校驗防護（RBAC `A1.edit`），未授權使用者呼叫時直接攔截並回覆明確之權限不足警示。
- **`backend/prompts/cloud_architecture_system_prompt.md`**:
  - 注入混合雲架構與多雲識別規則：明確宣告系統支援「混合雲 (Compound)」，引導模型在識別出多雲需求時調用 `provider="compound"`。
  - 明確注入 Hub-and-Spoke 幾何拓撲規範：中央核心雲為 AWS（寬度 $\ge 480\text{px}$），左翼為 Azure（寬度 $\ge 360\text{px}$），右翼為 GCP（寬度 $\ge 360\text{px}$），緩衝間隔 120px，連線標籤採純白圓角膠囊格式。
- **`backend/tests/test_design_agent.py` & `backend/tests/helpers.py`**:
  - 新增 `TestDesignAgentTool` 單元測試集：
    1. `test_draw_architecture_diagram_accepts_compound_provider`: 驗證混合雲入參成功觸發 `build_compound_diagram_xml`。
    2. `test_draw_architecture_diagram_rbac_guard`: 驗證 `can_edit=False` 時被安全拒絕並提及 `A1.edit`。
    3. `test_loaded_prompt_forbids_markdown_in_chat`: 驗證系統提示詞包含混合雲與 Hub-and-Spoke 規範。

---

## 2. 品質與測試驗證 (Verification & Quality Assurance)

- 執行命令：`PYTHONPATH=backend .venv/bin/python3 -m unittest backend/tests/test_design_agent.py`
- 結果：`Ran 9 tests in 0.061s - OK` (100% 通過)。

