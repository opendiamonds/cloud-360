# Reliability Requirements — cost-budget-banner

> Unit: `cost-budget-banner` · B2

## REL-B-1 無預算

- `monthly_budget IS NULL` → 不超支、banner inactive（BR-B-2、AC-6.5）

## REL-B-2 banner 失敗

- GET `/banner` 5xx → Layout **不 crash**；不顯示橫幅（降級）
- PUT budget 失敗 → 列級錯誤；保留舊 budget

## REL-B-3 與 CostPage 一致

- `overspent` 與 `OverspendFlag` 同源 calculator 規則；避免 banner 與頁面矛盾

## REL-B-4 session dismiss

- reload 後 banner 再現（AC-7.3）；非可靠性故障
