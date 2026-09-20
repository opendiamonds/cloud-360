# NFR Requirements — 釐清問題（cost-schema-rbac）

> Unit: `cost-schema-rbac` · kind: **spec** · Q1–Q2=A 預填

## Q1. ADR-0006 IAM 面向落點？

A. **本 unit 是 IAM 種子與表 DDL 的落點**；`ensure_missing_role_permissions` 屬 IAM 資料變更，需 plan/impact/rollback 說明寫進 security artifact。**（建議）**  
[Answer]: A

## Q2. 效能／可用性 SLO？

A. **不訂延遲 SLO**；驗證靠 migration 測試與 brownfield 補種子測試。**（建議）**  
[Answer]: A

## Plan Approval

- [x] 計畫已核可
