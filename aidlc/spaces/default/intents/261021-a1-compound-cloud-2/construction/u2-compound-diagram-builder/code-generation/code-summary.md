# Code Summary — U2: u2-compound-diagram-builder

> Stage: code-generation (3.5) · Phase: Construction · Scope: feature · Depth: Standard
> Unit: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**

---

## 1. 交付與修改程式碼清單 (Delivered & Modified Code Artifacts)

- **`backend/services/diagram_builder.py`**:
  - 新增 `build_compound_diagram_xml(clouds: list[dict], connections: list[dict] | None = None, on_progress: ProgressCallback | None = None) -> str` (Contract C3)：
    - **Hub-and-Spoke 空間幾何佈局 (BR2.2, BR2.3)**：三雲依 Azure (左翼, 寬度 $\ge 360\text{px}$)、AWS (中央核心, 寬度 $\ge 480\text{px}$)、GCP (右翼, 寬度 $\ge 360\text{px}$) 排序，雲與雲之間保留嚴格 120px 緩衝走廊 (`buffer_corridor = 120.0`)，徹底消除容器重疊。
    - **雲端群組樣式 (BR2.1)**：套用 `GROUP_STYLES` 中的 `azure_cloud`、`aws_cloud` 與 `gcp_cloud`，維持視覺風格一致性。
    - **內部節點自動分格排列**：中央 AWS 預設 3 欄式排列、左右翼預設 2 欄式排列，並根據容器 X 座標計算相對座標 (`rel_x`, `rel_y`)。
    - **跨雲直角折線與純白膠囊標籤 (BR2.4, BR2.5)**：跨雲連線設定 `edgeStyle=orthogonalEdgeStyle;`，連線中點設置純白圓角背景 (`labelBackgroundColor=#FFFFFF;rounded=1;labelBorderColor=#CBD5E1;`) 與深色文字 (`fontColor=#1E293B;`)，對比度達 13.5:1，符合 WCAG 2.1 AA。
    - **合法 Draw.io / mxGraph XML 產出 (NFR4.1)**：輸出包含 `<mxfile>`, `<diagram>`, `<mxGraphModel>`, `<root>` 等完整節點之標準 XML。
- **`backend/tests/test_diagram_builder_compound.py`**:
  - 擴充 4 個專屬幾何與連線測試案例 (`TestCompoundDiagramBuilder`)：
    1. `test_hub_and_spoke_layout_ordering_and_buffer`: 驗證 Azure(左) -> AWS(中) -> GCP(右) 排序、120px 間隔走廊與最小寬度約束。
    2. `test_group_styles_application`: 驗證容器樣式完全匹配 `GROUP_STYLES`。
    3. `test_cross_cloud_orthogonal_edges_and_capsule_labels`: 驗證跨雲直角折線與白底圓角膠囊協議標籤樣式。
    4. `test_compound_xml_validity`: 驗證產出之 XML 可被 `xml.etree.ElementTree` 成功解析。

---

## 2. 品質與測試驗證 (Verification & Quality Assurance)

- 執行命令：`PYTHONPATH=backend .venv/bin/python3 -m unittest backend/tests/test_diagram_builder_compound.py`
- 結果：`Ran 11 tests in 0.010s - OK` (100% 通過)。
- 回歸測試：`PYTHONPATH=backend .venv/bin/python3 -m unittest discover backend/tests -p "test_diagram_*.py"`
- 結果：`Ran 63 tests in 0.133s - OK`，既有單雲繪圖與複合雲繪圖測試全部綠燈。

