# 監控設計 — `U12 work-orchestrator`

**無新監控管線。** repo 尚無指標或告警管線（`project.md ## Deployment`：observability 仍是真實待辦），本單元不單獨建立。

| 訊號 | 落點 | 用途 |
|---|---|---|
| 狀態轉換 INFO、失敗 WARNING（含失敗類別） | 後端既有 stdout log（`"cloud360.work_orchestrator"`） | 維運者追查單一工作項為何失敗（`NFR12.24`–`NFR12.26`） |
| sink、變更紀錄、記憶寫入失敗 WARNING | 同上 | 發現「工作項成功但旁支寫入失敗」 |

**判定失效條件**：若 repo 日後引入 metrics 管線，失敗類別列舉值（`../nfr-design/observability-design.md`）可直接作為計數器標籤，不需改 log 形狀。
