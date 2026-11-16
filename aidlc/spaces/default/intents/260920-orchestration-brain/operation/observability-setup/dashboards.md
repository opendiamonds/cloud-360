# Dashboards

**本站不產出 dashboard 規格**（[Q1]=A）。

本 repo 部署在單台自架 staging，沒有 Grafana、CloudWatch 或任何可以掛 dashboard 的平台。`project.md` 記載的規則是：先畫一份沒有地方可放的 dashboard，是把「有設計」誤當成「有監控」。上游 `construction/intent-router/infrastructure-design/monitoring-design.md` §五與 `construction/brain-infra/infrastructure-design/monitoring-design.md` 同一定調。

## 取而代之的「看板」

| 需求 | 實際承載處 |
|---|---|
| 一眼看到大腦現在健不健康 | `brain-health-watch.yml` 每小時一次 run 的 **step summary**（計數表＋7 天可用性＋觸發中的告警） |
| 出事時被通知 | GitHub issue「[brain-health] 大腦服務告警」／「[brain-health] 網站從外部無法使用」＋ Slack（`alarms.md`） |
| 深入查一個時段 | `log-queries.md` Q1–Q6 |

## 何時重新評估

引入任何監控平台（需新 ADR，見 [Q1] 選項 B／C）時，`alarms.md` 的九個告警與 `slo-config.md` 的三個 SLO 都已有足夠的定義可以直接建圖。上游 `performance-design.md`、`reliability-design.md`、`security-design.md` 與 `infrastructure-specification.md` 的指標定義屆時一併沿用。
