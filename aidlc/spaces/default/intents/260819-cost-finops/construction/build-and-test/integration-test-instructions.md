# Integration Test Instructions — 260819-cost-finops（B1）

> 本 repo 的「整合」= 短生命週期 docker stack + Playwright e2e + 真實 PostgreSQL  
> Upstream: `cost-ui` code-summary、team-practices 底線 C

## Stack 啟動

```bash
docker compose -f deploy/docker-compose.test.yml up -d --build
# 瀏覽器打 http://localhost:8090
```

環境內嵌：`COST_PRICING_STUB=1`、seed `admin/admin123`、fresh `schema_rbac.sql`。

## Playwright（C1 B1）

```bash
cd frontend
npm ci
npx playwright install chromium   # 首次
BASE_URL=http://localhost:8090 npx playwright test tests/e2e/regression.spec.ts --grep "成本頁"
```

## 預期（B1 五 case）

| Case | 斷言 |
|---|---|
| Sidebar | Platform_Admin 見「成本 → 預估成本」 |
| 區域 + 總額 | stub `$86.40/月`、EC2 label |
| B1 DOM | `cost-budget`／`cost-banner`／`cost-overspend-flag` **0 命中** |
| 時數 | PUT hours 4 → reload → `$14.40/月` |
| 文案 | pie `compute: $86.40`、coverage 三雲文案 |

測試帳號：註冊 **Project_Architect**（A1.edit + C1h/C1r.edit + 自有圖可見）。

## Full Regression（選跑）

```bash
BASE_URL=http://localhost:8090 npx playwright test tests/e2e/regression.spec.ts
```

本輪實跑 **17/19** 通過；2 失敗為既有 admin 分頁 case（非 C1 引入）。

## Pass Criteria

- C1 `--grep "成本頁"`：**5/5**
- 無 LLM／n8n 呼叫（成本路徑）
