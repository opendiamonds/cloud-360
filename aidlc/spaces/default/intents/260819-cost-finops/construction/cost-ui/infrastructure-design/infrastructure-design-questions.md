# Infrastructure Design — 釐清問題（cost-ui）

> Stage: infrastructure-design（3.4）· Unit: `cost-ui` · kind: **ui**

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| 同一 SPA bundle / nginx | embedded |
| lazy route `/cost` | nfr-design |
| regions 建置期常數 | FD |

---

## Q1. 前端部署產物？

A. **Vite build 併入既有 frontend image**；`/cost` code-split chunk。**（建議）**  
B. 獨立 micro-frontend。代價：違 ADR-C1-01。  
C. Not yet defined  

[Answer]: A. **既有 frontend image**

---

## Plan Approval

- [x] 計畫已核可（Q1=A）
