# NFR Design — 釐清問題（cost-ui）

> Stage: nfr-design（3.3）· Unit: `cost-ui` · kind: **ui**  
> 上游：`../nfr-requirements/`、`../functional-design/frontend-components.md`。

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| NFR-4 終點 `cost-total` visible | PERF-U-1 |
| 無 heavyweight chart lib | PERF-U-3 |
| CapabilityRoute + can() gating | SEC-U-1 |
| B1 budget/banner test-id 0 命中 | SEC-U-4 |

---

## Q1. 狀態管理？

A. **元件 local state + fetch**；無 Redux 新 slice。**（建議）**  
B. 全局 cost store。代價：過度工程。  
C. Not yet defined  

[Answer]: A. **local state + fetch**

---

## Q2. Pie 渲染？

A. **原生 SVG** + `cost-pie-legend`；資料來自 snapshot.pie。**（建議）**  
B. 引入 chart.js。代價：違 PERF-U-3。  
C. Not yet defined  

[Answer]: A. **原生 SVG**

---

## Plan Approval

- [x] 計畫已核可（Q1–Q2=A）
