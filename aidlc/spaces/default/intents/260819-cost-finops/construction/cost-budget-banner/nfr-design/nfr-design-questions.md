# NFR Design — 釐清問題（cost-budget-banner）

> Stage: nfr-design（3.3）· Unit: `cost-budget-banner` · B2 · kind 省略 → 全套 design  
> 上游：`../nfr-requirements/`、`../functional-design/business-logic-model.md`。

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| session dismiss only | SEC-B-2、REL-B-4 |
| GET /banner ≤3s 非 NFR-4 路徑 | PERF-B-1 |
| `banner_for` 輕量 total | FD |
| B1 不 import register | FD |

---

## Q1. banner 聚合實作？

A. **迴圈 visible diagrams；每圖呼叫 service 內部 lightweight total**（重用 calculator + DB lines，不組完整 snapshot DTO）。**（建議）**  
B. N 次完整 GET snapshot HTTP 內部呼叫。代價：過慢。  
C. Not yet defined  

[Answer]: A. **lightweight total helper**

---

## Q2. 前端 fetch 時機？

A. **Layout mount 且 can(C1.view)；與 CostPage 並行**。**（建議）**  
B. 僅 CostPage mount。代價：非 cost 路由看不到橫幅。  
C. Not yet defined  

[Answer]: A. **Layout mount 並行**

---

## Plan Approval

- [x] 計畫已核可（Q1–Q2=A）
