# Functional Design — 釐清問題（cost-budget-banner）

> Stage: functional-design · Unit: `cost-budget-banner` · Kind: **（省略）**
> 第二段（B2）；B1 不交付但 FD 與 B1 同批寫完（stage-major）。
> 上游：`cost-ui` slot 契約、`cost-api` service 方法、`cost-calculator` `is_overspent`。

## 已由上游定案

| 決策 | 來源 |
|---|---|
| `PUT .../budget`、`GET /banner` | B2 DoD |
| `C1b.edit` 預算；`C1.view` 讀 banner | ADR-C1-02 |
| 多圖一條橫幅；不可永久關閉 | C1-7 |
| 注入 `cost-ui`／`Layout` slot | `cost-ui` FD Q2=A |
| 稽核預算變更 | ADR-C1-06 |

---

## Q1. B2 如何掛進 bundle？

A. **獨立模組 `frontend/src/cost/budget-banner/` + `backend/cost/budget_routes.py`；B2 merge 時在 `App.tsx`／`Layout.tsx` 加一行 register 把元件填進 slot；不用 feature flag CSS hidden**。**（建議，ADR-C1-08）**  
B. 改 `cost-ui` 原始檔 `#ifdef`。代價：B1/B2 難分 Bolt。  
C. Not yet defined  

[Answer]: A. **獨立模組 + register 填 slot**

---

## Q2. `GET /banner` 聚合邏輯？

A. **對使用者可見且設了 budget 的每圖算 snapshot total；`is_overspent(total,budget)`；回 `{active, count, sample}`；無超支 `active=false`**。**（建議）**  
B. 只檢查當前 cost 頁選中圖。代價：違 AC-7.3。  
C. Not yet defined  

[Answer]: A. **全可見圖聚合**

---

## Q3. 橫幅「關閉」行為？

A. **僅 session 級 dismiss（刷新／重登後再現）；無 localStorage 永久關閉**。**（建議，AC-7.3）**  
B. 可永久 dismiss。代價：違故事。  
C. Not yet defined  

[Answer]: A. **session dismiss only**

---

## Plan Approval

- [x] 計畫已核可（Q1–Q3=A）
