# Build & Test Results

> 實際執行時間：2026-08-20（本機）

## 摘要

| 項目 | 結果 |
|---|---|
| Backend unittest | **223 通過** / 0 失敗 |
| `validate_repo_contract.py` | 通過 |
| `validate_env_contract.py` | 通過（補 `COST_PRICING_STUB` 後） |
| `validate_cost_calculator_boundary.py` | 通過 |
| `dump_openapi.py --check` | 通過 |
| Frontend lint | 0 errors、3 warnings（既有） |
| Frontend `check:types` | 通過 |
| Frontend `npm run build` | 通過 |
| Playwright `--grep 成本頁` | **5/5** |
| Playwright 全 `regression.spec.ts` | **17/19**（2 failed） |

## Playwright 失敗（非 C1）

| Case | 錯誤摘要 |
|---|---|
| 刪除後仍停在原頁次… | 分頁／刪除流程（AC-5.6） |
| 超出範圍的頁次顯示空態… | route 改寫第 5 頁後未見空態文字 |

兩者屬既有 admin 分頁 suite；C1 五 case 在同一 run 全過。

## C1 子集明細

```
Platform_Admin 看得到成本 Sidebar 入口          OK
選區域後顯示月估總額且列對到 EC2 label         OK
B1 頁面不含 budget／banner／overspend-flag      OK
調整每日時數後月估總額更新                      OK
圓餅圖例與定價假設文案正確                      OK
```

環境：`deploy/docker-compose.test.yml`、`COST_PRICING_STUB=1`、`BASE_URL=http://localhost:8090`。

## 修正後重驗

| 修正 | 重跑 | 結果 |
|---|---|---|
| `get_snapshot()` + `db.commit()` | cost e2e hours case | 200 PUT + UI $14.40 |
| `COST_PRICING_STUB` in `.env.example` | `validate_env_contract.py` | exit 0 |
