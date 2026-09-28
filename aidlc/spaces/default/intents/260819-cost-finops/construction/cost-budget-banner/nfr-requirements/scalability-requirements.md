# Scalability Requirements — cost-budget-banner

> Unit: `cost-budget-banner` · B2

## SCL-B-1 banner 聚合

- O(可見圖 N) snapshot/total 計算；N 為使用者可見 diagram 數
- 多圖超支仍 **一條** 橫幅（AC-7.4）；`count` 欄位承載

## SCL-B-2 不引入

- 背景 job 預計算超支；push notification — out of scope

## SCL-B-3 cache

- 無 banner 專用 cache；依賴 cost-api snapshot 路徑與 DB budget 列
