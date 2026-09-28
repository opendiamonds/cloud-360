# NFR Requirements — 釐清問題（cost-api）

> Unit: `cost-api` · kind: **service**

## Q1. NFR-4 五秒怎麼驗？

A. **Playwright 或手動計時**：已快取／已覆寫、≤50 列、GET snapshot 至 `cost-total` 可見 ≤5s；冷查價目**排除**。**（建議）**  
[Answer]: A

## Q2. pricing_client 逾時與 NFR-4？

A. **單 SKU connect+read 各 3s、不重試**（FD Q1=A）；整包 snapshot 仍須在無冷查時 ≤5s。**（建議）**  
[Answer]: A

## Q3. 出站 HTTPS 威脅模型？

A. **只允許公開價目 URL 白名單（infra-design 定 URL）**；禁止 Cost Explorer 字串；stub 可測。**（建議）**  
[Answer]: A

## Plan Approval

- [x] 計畫已核可
