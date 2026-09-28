# NFR Requirements — 釐清問題（cost-budget-banner）

> Unit: `cost-budget-banner` · B2 · 與 B1 同批寫 NFR

## Q1. NFR-1 橫幅 a11y？

A. **橫幅 CTA 可 Tab 聚焦**；無「永遠關閉」；session dismiss 仍須鍵盤可達關閉。**（建議）**  
[Answer]: A

## Q2. NFR-4 是否適用 banner 聚合？

A. **GET /banner 非 5s 關鍵路徑**；允許 O(可見圖數)×snapshot 成本，但須 timeout 保護單請求。**（建議）**  
[Answer]: A

## Plan Approval

- [x] 計畫已核可
