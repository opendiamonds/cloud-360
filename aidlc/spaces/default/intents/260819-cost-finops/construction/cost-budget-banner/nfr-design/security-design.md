# Security Design — cost-budget-banner

> Unit: `cost-budget-banner` · B2 · 承接 `../nfr-requirements/security-requirements.md`

## 1. IAM

| 操作 | Story |
|---|---|
| GET `/banner` | `C1.view` |
| PUT `.../budget` | `C1b.edit` |
| 顯示 OverspendBanner | 前端 `can('C1','view')` + API 過濾 |

## 2. 資訊暴露（SEC-B-1）

`banner_for` **僅**迭代 `visible_diagrams(user)`：

- owned ∪ shared（與 collab 語意一致）
- 回應不含他人私有圖 id 列表全文（僅 `sample` 一筆 metadata）

## 3. Dismiss 語意（SEC-B-2 / SEC-B-3）

| 允許 | 禁止 |
|---|---|
| session 內 hide DOM | localStorage「永不再顯示」 |
| reload 後再 GET | 削弱 RBAC 的 client-only 永久關閉 |

## 4. Audit

`apply_budget` 成功 → `record_audit(field=monthly_budget)`（與 cost-api 共用表）。

## 5. XSS

橫幅文案使用 React escape；`sample.title` 來自 API 字串節點。

## 6. Code Gen 檢查清單

- [ ] 無 C1.view 不 fetch banner
- [ ] PUT budget TestClient allow/deny C1b
- [ ] 無 localStorage dismiss key
