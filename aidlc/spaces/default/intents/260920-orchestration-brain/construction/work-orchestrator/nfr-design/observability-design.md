# 觀測設計 — `U12 work-orchestrator`

> 承接 `NFR12.24`–`NFR12.26`。

- `logger = logging.getLogger("cloud360.work_orchestrator")`（`NFR12.24`）。
- 單一出口 `_log_transition(item, old, new)`：INFO，`extra` 不用，訊息格式固定為
  `work_item=%s capability=%s %s->%s stage=%s`；失敗時另一筆 WARNING `work_item=%s failure=%s`，失敗類別為列舉值
  `forbidden／unauthorized／timeout／expired_on_recovery／capability_failed／connection_lost／not_found／target_unresolved`（`NFR12.25`）。
- sink 失敗、變更紀錄寫入失敗、記憶寫入失敗各一筆 WARNING，只含類別名（`NFR12.26`）。
- 不新增 metrics；repo 尚無 metrics 管線。
