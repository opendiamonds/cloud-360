# CI/CD Pipeline — U2: u2-compound-diagram-builder

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> 追溯上游基準：
> - [security-design](../nfr-design/security-design.md) (NFR3.2, NFR4.2)

---

## 1. 構建與持續整合管線規範 (CI/CD Pipeline Specifications)

### 1.1 核心測試套件整合 (Core Test Suite Integration)
- **測試命令**: `pytest backend/tests/test_diagram_builder_compound.py -v`
- **關鍵斷言覆蓋**:
  - `test_hub_and_spoke_coordinates`: 驗證中央 AWS (寬 480)、左翼 Azure (寬 360)、右翼 GCP (寬 360) 之 X 座標及 120px 緩衝區。
  - `test_cross_cloud_edge_style`: 驗證 `edgeStyle=orthogonalEdgeStyle;` 與純白膠囊標籤樣式。
  - `test_xml_validity`: 驗證產生之 XML 可被 `xml.etree.ElementTree.fromstring()` 無錯誤解析。
  - `test_node_capacity_limit`: 驗證超過 500 節點拋出 ValueError。

### 1.2 程式碼品質與合約校驗
- 整合於既有 `.github/workflows/ci.yml`，在 PR 發起時機械執行。

