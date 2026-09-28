# Observability Requirements — cost-advice-agent

## NFR-O.1 — SSE 進度（NFR2）

`progress`／`heartbeat`（15s）事件；完成／失敗／timeout 終態。

## NFR-O.2 — 日誌欄位

結構化：set_id、status、duration_ms、error_code；遵守 NFR9.1。

## NFR-O.3 — 稽核

可選 `advice_started`／`advice_completed`／`advice_failed`（無金額／原文）。
