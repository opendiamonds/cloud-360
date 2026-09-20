# Component Dependency — C1 成本估算

## 上游輸入

components.md、architecture.md、team-practices.md、stories.md、requirements.md

## 依賴矩陣

| 從 \ 到 | router | service | extractor | mapper | calculator | pricing_client | price_cache | rbac | diagrams | YAML | SPA |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cost_router | — | sync | — | — | — | — | — | sync | — | — | — |
| cost_service | — | — | sync | sync | sync | sync* | sync | — | sync | — | — |
| extractor | — | — | — | — | — | — | — | — | — | — | — |
| mapper | — | — | — | — | — | — | — | — | — | 讀檔 | — |
| calculator | — | — | — | — | — | — | — | — | — | — | — |
| pricing_client | — | — | — | — | — | — | — | — | — | — | — |
| CostPage | HTTP | — | — | — | — | — | — | can() | — | — | — |
| OverspendBanner | HTTP | — | — | — | — | — | — | can() | — | — | Layout |
| Sidebar | — | — | — | — | — | — | — | can(C1) | — | — | — |

\* 僅 cache miss。calculator **零**依賴到 client／DB。

禁止邊：extractor → `wa_rule_engine`；router → calculator 直呼（可測性）；SPA → 直連雲價目。

## 溝通

全同步、行程內函式呼叫（backend）或 HTTPS JSON（SPA）。無事件、無 queue。

## 資料流

```
[XML user_diagrams] --> extractor --> mapper --> lines
[diagram_cost_line] --> align by mxcell_id
[diagram_cost.region] --> cache/client --> hourly
lines+hourly+hours --> calculator --> total/pie
override/budget --> cost_audit_event
total+budget --> overspent --> banner
```

<!-- Text fallback: 圖 XML 與列狀態表對齊後查價，純函式出總額；覆寫與預算寫稽核；超支驅動橫幅。 -->

## 共用資源

- PostgreSQL：新四表 + 既有 `user_diagrams`／`role_permissions`
- 無共用 Redis
- 公開價目外網：僅 `pricing_client`

## 前端掛載

```
Layout --> Sidebar
Layout --> OverspendBanner (第二段)
Layout --> CostPage | Workspace | …
Workspace --> SuccessCostCta --> /cost
```
