# Monitoring Design — u1-iac-api

> Q3=A · 對齊 observability-design（無 Prometheus／OTel）。

## Metrics & KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| （本輪無） | — | — | NFR／Q3：不新增 metrics 義務 |

## Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| （可選）log 規則 | `error.code=generate_timeout` 暴增 | Warning | 既有 log 管線訂閱者 |
| 容器掛掉 | 既有主機／compose 健康 | Critical | 既有運維通道 |

## SLIs / SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| D1 成功且＜90s | best-effort；非正式對外 SLA | 演示／staging 週期 |
| 非 LLM API p95＜2s | 工程目標 | 抽樣 log `duration_ms` |

## Logs & Tracing

| 面向 | 設計 |
|---|---|
| 聚合 | 容器 stdout → 既有 staging log 收集（若有） |
| 格式 | `cloud360.iac.*` 結構化；含 request_id |
| Tracing | **不做** OTel |
| Dashboard | **不**新增 Grafana 面板義務 |

<!-- confirmed: Looks correct -->
