# 異常偵測設定

**本站不設自動異常偵測**（不用 CloudWatch Anomaly Detection 或統計基準模型）。

## 理由

異常偵測需要一段穩定的基準。staging 的大腦每小時只有個位數到數十輪對話，而且 2026-11-15 才把路由模型換成 Jev 1.14（ADR-0024）——**目前沒有任何可信的基準期**。在這種流量下，以統計方法判斷「偏離基準」會頻繁誤報，而誤報會讓讀者學會忽略 `alarms.md` 的真告警。

## 取而代之

| 上游想抓的異常 | 現在的做法 |
|---|---|
| 反問率偏離基準 ±50%（`intent-router` monitoring-design §二） | 每週以 `log-queries.md` Q3 人工檢視，累積兩週資料後再定固定門檻 |
| 槽位數長期恆為 1（多意圖路徑變死碼） | 同上，Q3 的 `slots=` 分佈 |
| 錯誤率突增 | 已由 `alarms.md` 的固定門檻 `TURN_ERRORS`／`LLM_UNAVAILABLE` 承接 |

## 何時重新評估

累積兩週 Jev 1.14 的線上資料後（約 2026-11-30），依 Q3 的實際分佈把「反問率異常」改寫成固定門檻，加進 `brain-health-watch.yml` 的判斷步驟，並補一條突變驗證。上游 `performance-design.md`、`reliability-design.md`、`security-design.md`、`monitoring-design.md` 與 `infrastructure-specification.md` 沒有其他要求異常偵測的項目。
