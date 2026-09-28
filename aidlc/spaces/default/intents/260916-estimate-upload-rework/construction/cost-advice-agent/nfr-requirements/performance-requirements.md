# Performance Requirements — cost-advice-agent

> Unit: U7 · Q1–Q6=A

## NFR1.1 — 端到端建議時窗

繼承 **NFR1**：自上傳完成至建議產出目標 3 分鐘、上限 5 分鐘（`started_at` 起算）。逾時見 reliability／BR7.6。

## NFR1.2 — LLM 呼叫預算（Q5=A）

單次建議 job ≤ 3 次 `invoke_graph`；超出則剩餘 Should 類別寫入 `unavailable_reasons`，Must（saving）優先。

## NFR1.3 — SSE

Heartbeat 每 15 秒（Q2=A）；不得阻塞背景 worker。
