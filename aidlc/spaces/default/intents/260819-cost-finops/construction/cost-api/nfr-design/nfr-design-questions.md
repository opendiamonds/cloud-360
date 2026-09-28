# NFR Design — 釐清問題（cost-api）

> Stage: nfr-design（3.3）· Unit: `cost-api` · kind: **service**  
> 上游：`../nfr-requirements/`、`../functional-design/business-logic-model.md`。

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| NFR-4 ≤5s（快取／override、≤50 列） | PERF-A-1 |
| pricing 3s timeout、0 retry | PERF-A-2、FD |
| 404→403 順序在 service 內 | SEC-A-1、FD Q2=A |
| 單列定價失敗降級 | REL-A-1 |
| 無 Redis／queue | SCL-A-4 |

---

## Q1. Snapshot 5s 量測落點？

A. **Playwright `cost-total` + staging 手動**；CI TestClient 不量 5s。**（建議，對齊 PERF-A-4）**  
B. CI 內 sleep 斷言。代價：flaky。  
C. Not yet defined  

[Answer]: A. **Playwright + staging**

---

## Q2. 邏輯編排核心命名？

A. **`CostService` 單類**（與 `component-methods.md` 一致）；子元件為 module-level 函式／薄 class。**（建議）**  
B. 拆 `SnapshotOrchestrator` 與 A3 同型。代價：與 AD 命名分歧。  
C. Not yet defined  

[Answer]: A. **CostService**

---

## Q3. pricing cache 儲存？

A. **Postgres `pricing_cache` 表**；UK(cloud, sku, region)；TTL 24h 懶淘汰。**（建議）**  
B. 進程內 LRU。代價：重啟 miss、多 worker 不一致。  
C. Not yet defined  

[Answer]: A. **Postgres cache 表**

---

## Plan Approval

- [x] 計畫已核可（Q1–Q3=A）
