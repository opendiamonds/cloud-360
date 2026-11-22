# Integration Test Instructions — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: build-and-test (3.6) · Phase: Construction · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 整合測試範圍

驗證混合雲在以下模組邊界的協同運作：
1. **Design Agent (`design_agent.py`)** 接收自然語言設計意圖，呼叫 `draw_architecture_diagram` 工具（指定 `provider="compound"`、包含 `clouds` 拓撲與 `connections` 連線）。
2. **Diagram Builder (`diagram_builder.py`)** 接收多雲拓撲資料，向 n8n 服務請求各雲服務圖示（上行 payload 強制為 `provider="compound"`），並執行空間幾何計算產出 Draw.io XML。
3. **安全與降級防護**:
   - 權限防護：未授權角色 (`can_edit=False`) 觸發 RBAC 攔截。
   - 網路逾時防護：n8n 服務超過 5.0 秒或回傳異常時自動降級至本地 SVG 圖示。

---

## 2. 整合測試執行命令

```bash
PYTHONPATH=backend .venv/bin/python3 -m unittest \
  backend/tests/test_diagram_builder_compound.py \
  backend/tests/test_design_agent.py \
  backend/tests/test_diagram_icons.py
```

### 驗收標準
- 全數 40 個測試案例 100% 通過（OK）。
- 涵蓋 Hub-and-Spoke 空間佈局、雲間直角折線與純白膠囊標籤渲染。
- 驗證上行 payload `provider = "compound"` 與 5.0 秒逾時 fallback。

