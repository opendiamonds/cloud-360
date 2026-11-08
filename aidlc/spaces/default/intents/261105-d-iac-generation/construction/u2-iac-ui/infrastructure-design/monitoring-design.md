# Monitoring Design — u2-iac-ui

> Q3=A · 對齊 NFR：無 RUM／無前端 metrics SDK。  
> 承接 `performance-design`／`security-design`；UI 無獨立 `observability-design`（薄適用）。

## Metrics & KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| （本輪無） | — | — | NFR／Q3：不新增前端 metrics 義務 |

## Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| （可選）後端關聯 | U1 `generate_timeout`／5xx 暴增 | Warning | 既有 log 訂閱者（非 UI SDK） |
| SPA 容器掛掉 | 既有 compose／主機健康 | Critical | 既有運維通道 |

## SLIs / SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| D1 UI 可 busy 至 settle（≥90s Abort） | 工程目標；非正式對外 SLA | 手動／Playwright |
| 錯誤可依 `error.code` 顯示短語 | 100% 已知 code 有文案 | e2e／手動 |

## Logs & Tracing

| 面向 | 設計 |
|---|---|
| 瀏覽器 | **禁止** console dump HCL／密文；無 RUM 事件串 |
| 伺服器關聯 | 依賴 U1 `cloud360.iac.*`＋request_id |
| Tracing | **不做** 前端 OTel |
| Dashboard | **不**新增 Grafana／RUM 面板義務 |

<!-- confirmed: Looks correct -->
