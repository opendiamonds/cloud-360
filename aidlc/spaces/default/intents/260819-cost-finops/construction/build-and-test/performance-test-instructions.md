# Performance Test Instructions — 260819-cost-finops（B1）

> B1 無專用 load test 框架；NFR 以 stub 模式 + 人工量測承接。

## Scope（B1）

| 路徑 | 目標（設計） | B1 驗證 |
|---|---|---|
| GET `/api/cost/diagrams/{id}` | p95 < 2s（warm cache） | 人工／staging 抽查 |
| pricing_client 首次 miss | httpx 3s timeout | code review + stub 預設 |

## 本機抽查（可選）

```bash
# test stack 起來後
time curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8090/api/cost/diagrams/1 > /dev/null
```

## Pass Criteria（B1）

- 無自動化 perf gate 紅燈（尚未引入 k6／locust）
- stub 模式下 e2e 單 case < 30s timeout

B2（banner 輪詢）再評估是否加 e2e 延遲斷言。
