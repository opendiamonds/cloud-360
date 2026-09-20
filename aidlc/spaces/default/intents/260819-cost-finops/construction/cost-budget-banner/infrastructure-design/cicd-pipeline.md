# CI/CD Pipeline — cost-budget-banner

> Unit: `cost-budget-banner` · B2

## 1. B1 CI（否定測試）

- Playwright：`cost-budget`、`cost-banner` **0 命中**
- TestClient：PUT budget → **404**

## 2. B2 CI 增量

| 測試 | 內容 |
|---|---|
| TestClient | C1b allow/deny PUT budget |
| TestClient | GET /banner 2xx shape |
| Playwright | 超支場景橫幅 visible；session dismiss reload 再現 |

## 3. Pipeline

- 同一 `ci.yml` / `ui-regression`
- 同一 deploy workflow；B2 merge 後 staging 驗 AC-7.x

## 4. Code Gen 檢查清單

- [ ] B2 Bolt PR 含 e2e + TestClient
- [ ] 不拆獨立 workflow
