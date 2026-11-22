# Logical Components — U2: u2-compound-diagram-builder

> Stage: nfr-requirements (3.2) / nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**

---

## 1. 模組與類別架構 (Module & Class Structure)

- **模組位置**: `backend/services/diagram_builder.py`
- **主要公開函式**: `build_compound_diagram_xml(clouds: list[CloudContainerSpec], connections: list[CrossCloudConnectionSpec]) -> str`
- **核心架構元件**:
  - `CompoundLayoutCalculator`: 幾何空間計算器（處理 Hub-and-Spoke 480/360/120 座標）。
  - `MxCellBuilder`: mxGraph XML 節點建構器（套用 GROUP_STYLES 與 XML 轉義）。
  - `CrossCloudEdgeRenderer`: 直角折線與白底圓角協議標籤生成器。

