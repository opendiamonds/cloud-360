# Domain Entities — cost-ui

> Unit: `cost-ui` · 消費 OpenAPI 型別，不新增後端實體。

## ViewModel

前端狀態以 **generated API 型別** 為準（`Snapshot`、`LineOut` 等）。額外 UI-only 狀態：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `pageStatus` | `empty \| loading \| error \| ready` | 殼層 |
| `fieldErrors` | `Record<mxcellId, string>` | 時數校驗 |
| `selectedDiagramId` | `number \| null` | 與 URL query 雙向同步 |

## 不持久化

無 localStorage 快取 snapshot；切頁重抓（對齊 FR-1.5 伺服器對齊）。

## 與 cost-api 契約

| API | UI 使用 |
|---|---|
| GET `/diagrams` | 下拉 |
| GET `/diagrams/{id}` | 主畫面 |
| PUT hours/region/sku/override | 就地編輯 |

`coverage`、`pricing_as_of` 顯示於定價假設區（FR-3.5）；格式見 `frontend-components.md` §PricingAssumptions。

## B2 擴充點

| slot | 預期 B2 注入 |
|---|---|
| `data-slot="cost-overspend"` | `OverspendFlag` test-id `cost-overspend-flag` |
| `data-slot="cost-banner"` | `OverspendBanner` test-id `cost-banner` |

B1 兩 slot `children.length === 0`（由 `mountCostSlot` 未呼叫保證）。

## Slot Registry

見 `business-logic-model.md` §Slot Registry API；`mountCostSlot` 由 cost-ui export，B2 register 使用。
