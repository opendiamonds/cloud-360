# Frontend Components — cost-ui

> Unit: `cost-ui` · Q1–Q4=A · 上游：`mockups.md`、`interaction-spec.md`、`design-system-mapping.md`。

## 元件樹

```
Sidebar
  └─ CostNavGroup (can C1.view)
CostPage (/cost, CapabilityRoute)
  ├─ DiagramSelect
  ├─ CostPageShell (states)
  │    ├─ RegionField (cost-region)
  │    ├─ TotalSection
  │    │    ├─ cost-total (aria-live polite) | M5b 說明文字
  │    │    └─ cost-unpriced-count
  │    ├─ PieBreakdown (SVG + cost-pie-legend)
  │    ├─ ResourceTable
  │    │    └─ rows: label, HoursInput, sku/override cols
  │    └─ div[data-slot=cost-overspend]  (B2 掛點)
Layout (既有)
  └─ div[data-slot=cost-banner]  (B2 掛點；B1 空)
SuccessCostCta (Workspace 卡)
```

## 元件規格

### CostNavGroup

| Prop | 型別 | 說明 |
|---|---|---|
| — | — | 無 props；內讀 `useAuth().can('C1','view')` |

**Render**：false → null。true → Sidebar 在「架構」與「Admin」之間插入「成本 → 預估成本」連到 `/cost`。

### CostPage

| State | 來源 |
|---|---|
| `diagramId` | `useSearchParams().diagram` 或下拉 |
| `snapshot` | GET `/api/cost/diagrams/{id}` |
| `status` | empty / loading / error / ready |

**Mount**：有 id → fetch；無 id 且有 items → 選第一張；無 items → empty。

### HoursInput

| Prop | 型別 |
|---|---|
| `mxcellId` | string |
| `value` | number |
| `readOnly` | boolean (`!can('C1h','edit')`) |
| `onCommitted` | `(hours)=>PUT` |

test-id：`cost-hours-input`（每列 `data-mxcell-id` 區分）。非法不呼叫 `onCommitted`。

### RegionField

`<select data-testid="cost-region">`；選項來自 snapshot **`allowed_regions`**（後端依 `diagram_cloud` 自 `supported_regions.yaml` `by_cloud` 過濾；無法偵測雲時為扁平全清單）。前端常數 `frontend/src/cost/supportedRegions.ts` 僅作 fallback／標籤對照，**須與 YAML 同 PR 同步**。**本輪無** `GET /regions` API。跨雲區域 PUT → **400**。`readOnly` when `!can('C1r','edit')`。未填時顯示 FR-4.1 提示；首次查價提示文案依 `diagram_cloud` 區分（AWS／GCP／Azure）。

### TotalSection

| 子節點 | 條件 |
|---|---|
| `cost-total` | `snapshot.total != null`（M5b 否則 0 命中） |
| `cost-unpriced-count` | **`unpriced_count > 0` 才渲染**；`== 0` 時 **0 命中**（不顯示「0 項尚未定價」） |

文案：`{unpriced_count} 項尚未定價`（與 mockups M2 一致）。

### PricingAssumptions（定價假設區）

`coverage[]` + `pricing_as_of` + 公式摘要（FR-3.2）。**coverage 渲染規則**（e2e 比對字串）：

| `mode` | 片段 |
|---|---|
| `official_list` | `{CLOUD} 走官方價` |
| `manual_override_only` | `{CLOUD} 全 Manual Override` |

- 雲名：`aws`→`AWS`、`gcp`→`GCP`、`azure`→`Azure`；多條以 **` · `** 分隔。現況三雲皆 `official_list`（mockups M2／ADR-C1-09：「AWS 走官方價 · GCP 走官方價 · Azure 走官方價」）。
- `pricing_as_of` 非 null：追加 ` · 官方價截至 {ISO-8601 UTC}`。

### PieBreakdown

SVG 四色 + `cost-pie-legend` 文字列。`total==null` 或 pie 全 0：無 arc，legend 顯示「—」。

### ResourceTable 覆寫欄

SKU／hourly override：`can('C1o','edit')` 可編；否則唯讀。Manual Override 顯示文字標籤（FR-2.3）。

### SuccessCostCta

`navigate('/cost?diagram=' + diagramId)`；與既有 Workspace CTA 並列。

## B1 禁止渲染（AC-1.16）

下列 test-id **0 命中**：`cost-budget`、`cost-overspend-flag`、`cost-banner`（slot 容器可存在，flag/banner 元件不 mount）。

## API 整合

型別：`frontend/src/types/api.d.ts`（generated）。Client：既有 fetch wrapper；403 不 crash 頁面（表單只讀）。

## 樣式

`tabular-nums` 於金額；總額字級較大（mockups）；危險色僅 B2 使用，B1 不引入 overspend 色。
