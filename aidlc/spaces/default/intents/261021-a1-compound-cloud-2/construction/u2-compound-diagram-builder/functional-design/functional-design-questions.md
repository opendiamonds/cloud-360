# Functional Design Questionnaire — U2: u2-compound-diagram-builder

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> 追溯上游基準：
> - [unit-of-work](../../../inception/units-generation/unit-of-work.md)
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C2, C3)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR3.1~FR3.3, NFR1, NFR2, CON1)
> - [stories](../../../inception/user-stories/stories.md) (US3.1~US3.4)

---

## 1. 單元實作職責與幾何邊界說明 (Functional Scope & Geometry)

本單元 `u2-compound-diagram-builder` 是本功能之核心骨架函式庫（Walking Skeleton），封裝三雲 Hub-and-Spoke 幾何空間佈局與 mxGraph XML 序列化：
- **主要函式**: `build_compound_diagram_xml(clouds: list[CloudContainerSpec], connections: list[CrossCloudConnectionSpec]) -> str`
- **幾何規範**: 中央 AWS 容器基準寬度 480px，左右雙翼 Azure 與 GCP 各 360px，雲與雲間保留 120px 緩衝走廊。
- **樣式映射**: 套用既有 `GROUP_STYLES` (`aws_cloud`, `azure_cloud`, `gcp_cloud`)。
- **連線路由**: 強制使用 `edgeStyle=orthogonalEdgeStyle;` 直角折線，連線中點標註純白膠囊協議標籤（對比度 13.5:1，符合 WCAG 2.1 AA）。

---

## 2. 功能細部設計關鍵問卷 (Clarifying Questions)

### Q1. Hub-and-Spoke 雙翼左右對稱分配規則 (Spoke Allocation)
在三雲拓撲中，中央固定為主要雲（預設 AWS），兩側 Spoke 雲之左右分佈規則為何？
- [A] **左側固定 Azure、右側固定 GCP**：維持固定的幾何鏡像對稱關係（左翼 Azure 360px、中 AWS 480px、右翼 GCP 360px），保證產圖結果之高度確定性（Deterministic layout）。（推薦）
- [B] **依據節點多寡動態對調左右翼**：節點較多者置於左側。

[Answer]: [A]

### Q2. 跨雲連線標籤樣式宣告 (Protocol Label mxGraph Style)
為防止協議標籤（如 "Direct Connect"、"VPN Tunnel"）與折線重疊並確保 WCAG 2.1 AA 對比度，其 mxGraph cell 樣式如何組裝？
- [A] **純白圓角膠囊樣式**：`rounded=1;fillColor=#FFFFFF;strokeColor=#CBD5E1;fontColor=#1E293B;fontSize=11;fontStyle=1;labelBackgroundColor=#FFFFFF;`，確保文字周圍具備足夠 padding 且完全覆蓋底線。（推薦）
- [B] **透明底無邊框樣式**：僅顯示文字無背景遮罩。

[Answer]: [A]

### Q3. XML 命名空間與標準相容性 (mxGraph XML Compatibility)
產出之 XML 是否嚴格相容既有 draw.io 單雲架構？
- [A] **100% 繼承標準 mxGraph 根結構**：`<mxfile><diagram><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>...</root></mxGraphModel></diagram></mxfile>`，確保支援 Draw.io 匯出、本機儲存與即時編輯。（推薦）
- [B] **擴充非標準 XML 標籤**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `entities.md`、`rules.md`、`functional-spec.md` 與 `traceability.json` 前，請確認以下彙整摘要正確無誤：

- **佈局對稱 (Q1)**: [A] 左翼 Azure 360px、中央 AWS 480px、右翼 GCP 360px，具備確定性 120px 緩衝走廊。
- **協議標籤樣式 (Q2)**: [A] 純白圓角膠囊覆蓋樣式（`#FFFFFF` 背景、`#1E293B` 字體、對比度 13.5:1）。
- **XML 規範相容 (Q3)**: [A] 100% 標準 mxGraph 階層，無縫相容既有畫布與匯出功能。

Does this all look correct before I generate the functional design artifacts for U2?
- Looks correct
- Request changes

[Answer]: Looks correct
