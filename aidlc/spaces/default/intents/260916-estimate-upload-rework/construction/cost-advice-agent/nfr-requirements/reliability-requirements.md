# Reliability Requirements — cost-advice-agent

## NFR-R.1 — 逾時（BR7.6／Q3 FD）

`started_at`＋5 分鐘 → `failed`＋`timed_out`；SSE `timeout`。

## NFR-R.2 — 卡住清理（BR7.10）

讀取／啟動時若 generating 逾時則標 failed。

## NFR-R.3 — 斷線（BR7.7）

SSE 斷線不取消背景 job。

## NFR-R.4 — 降級

查價／Should 類失敗不阻 Must 省錢建議完成（若 LLM 可用）。
