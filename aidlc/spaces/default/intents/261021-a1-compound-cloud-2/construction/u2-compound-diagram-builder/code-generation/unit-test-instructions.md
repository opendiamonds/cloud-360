# Unit Test Instructions — U2: u2-compound-diagram-builder

> Stage: code-generation (3.5) · Phase: Construction · Scope: feature · Depth: Standard
> Unit: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**

---

## 1. 測試框架與環境設置 (Test Framework & Environment Setup)

- **框架**: Python 3.11 `unittest` 與 `xml.etree.ElementTree`
- **測試檔案路徑**: `backend/tests/test_diagram_builder_compound.py`
- **執行環境**: 本專案虛擬環境 (`.venv/bin/python3`)

---

## 2. 單元執行指令 (Unit-Scoped Test Command)

在執行任何測試前，確保執行以下專屬此單元的精確指令：

```bash
PYTHONPATH=backend .venv/bin/python3 -m unittest backend/tests/test_diagram_builder_compound.py
```

或過濾執行 U2 幾何與連線測試：

```bash
PYTHONPATH=backend .venv/bin/python3 -m unittest backend/tests/test_diagram_builder_compound.py -k "TestCompoundDiagramBuilder"
```

---

## 3. 測試範圍與覆蓋率目標 (Coverage Targets & Test Cases)

- **覆蓋率門檻**: 行覆蓋率 $\ge 80\%$。
- **核心測試案例清單 (5-8 tests)**:
  1. `test_hub_and_spoke_layout_ordering_and_buffer`: 驗證 Azure(左)、AWS(中)、GCP(右) 的水平排列順序，且相鄰兩雲之 X 軸間距恰為 120px 緩衝走廊。
  2. `test_cloud_container_dimensions`: 驗證中央 AWS 容器寬度 $\ge 480\text{px}$，兩翼 Azure 與 GCP 容器寬度各 $\ge 360\text{px}$。
  3. `test_group_styles_application`: 驗證產出的 XML 節點正確套用 `GROUP_STYLES` 中的 `azure_cloud`, `aws_cloud`, `gcp_cloud` 樣式。
  4. `test_cross_cloud_orthogonal_edges`: 驗證跨雲連線均包含 `edgeStyle=orthogonalEdgeStyle;` 樣式標記。
  5. `test_capsule_protocol_label`: 驗證跨雲連線中點標籤具備純白圓角背景 (`labelBackgroundColor=#FFFFFF;rounded=1;`) 與深色文字 (`fontColor=#1E293B;`)，符合 WCAG AA 規範。
  6. `test_compound_xml_validity`: 驗證產出之 XML 字串可由 `xml.etree.ElementTree` 成功解析為標準 Draw.io / mxGraph 結構，無語法異常。

---

## 4. 測試資料與 Mock 指引 (Mocking Guidance)

- Mock `fetch_icon_from_n8n` 回傳輕量 SVG 假資料，避免在測試圖表幾何結構時發起不必要的外部 HTTP 請求。

