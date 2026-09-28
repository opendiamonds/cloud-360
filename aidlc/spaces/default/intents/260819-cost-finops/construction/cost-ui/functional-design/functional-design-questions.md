# Functional Design — 釐清問題（cost-ui）

> Stage: functional-design（Construction 3.1，inline）· Unit: `cost-ui` · Kind: **ui**
> 上游：`refined-mockups/`、`component-methods.md`、`components.md`。
> **成本揭露**：4 題 + `frontend-components.md`。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 路由 `/cost`；`CapabilityRoute storyId="C1"` | `components.md`、AC-1.1 |
| test-id 表 | `mockups.md` |
| 第一段無 budget／banner／overspend DOM | ADR-C1-08、AC-1.16 |
| generated `api.d.ts` 契約 | Q5=A units-generation |
| 時數 0–24 前端先挡 | `interaction-spec.md` |
| 圓餅 SVG + `cost-pie-legend` | refined-mockups Q1=A |

---

## Q1. 全未定價時「每月總額」區怎麼畫？

> mockups M5b 已補：保留 heading，不渲染 `cost-total` 節點。

A. **保留 h2「每月總額」+ 說明「尚無已定價列，不能當成對外估價」；`cost-total` 0 命中；圓餅 section 仍顯示但無切片（僅 legend 空態）**。**（建議，對齊 M5b）**  
B. 整段 monthly total section 移除。代價：與 mockups heading 順序不一致。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **M5b：保留 heading、無 cost-total、圓餅空態**

---

## Q2. B2 跨 unit DOM 掛點？

> UG reviewer Minor：functional-design 寫死機制。

A. **`CostPage` 預留 `<div data-slot="cost-overspend" data-testid="cost-overspend-slot" />`（空）；`Layout` 預留 `<div data-slot="cost-banner" />`。第一段 slot 存在但子節點 0；B2 由 `cost-budget-banner` 注入 `OverspendFlag`／`OverspendBanner`。**（建議）**  
B. 條件 import 第二 bundle。代價：與 B1 同批部署耦合。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **data-slot 空掛點**

---

## Q3. 切圖與 deep link？

A. **`/cost?diagram={id}` 預選；下拉變更時 `navigate` 更新 query（replace）**；`SuccessCostCta` 用同一 query。**（建議）**  
B. 只用 React state 不寫 URL。代價：重新整理丟選圖。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **query diagram= 同步**

---

## Q4. 無 C1.view 的 Sidebar？

A. **不渲染「成本」NavGroup（不是 disabled）**；直接輸入 `/cost` 由 `CapabilityRoute` → `/403`。**（建議）**  
B. 顯示灰掉連結。代價：AC-1.1 要求「看不到」。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **整組不渲染**

---

## Plan Approval

- [x] 計畫已核可（Q1–Q4=A）
