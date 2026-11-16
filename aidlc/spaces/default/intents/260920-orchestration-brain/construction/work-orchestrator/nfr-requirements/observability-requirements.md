# 觀測需求 — `U12 work-orchestrator`

## 〇、本單元的觀測面

工作項狀態對使用者已經可見（`work_items` 推送）。觀測需求是給**維運者**的：一個工作項為什麼失敗、停在哪一步，
要能從 log 判斷，而 log 本身不得洩漏使用者內容或憑證（`NFR12.6`／`NFR12.11`）。

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR12.24`** | logger 名稱為 `"cloud360.work_orchestrator"`（`team.md ## Code Style` 的新模組慣例） | grep 本單元模組的 `getLogger` 引數 |
| **`NFR12.25`** | 每次狀態轉換記一筆 INFO：`workItemId`、`capability`、原狀態 → 新狀態、`dispatchStage`；失敗另記 WARNING，含失敗類別（403／401／逾時／逾期掃描／能力回報失敗／連線中斷），不含例外原文以外的使用者內容 | 走一次失敗路徑：擷取到的 log 恰含一筆該工作項的 WARNING，且含失敗類別字串 |
| **`NFR12.26`** | sink 失敗、facade 寫入失敗（變更紀錄、procedure 記憶）各記 WARNING（`BR56.8`、`BR51.4`、`BR51.5`），不含訊息內容 | 替身拋例外各一案：各有一筆 WARNING，且不含標記內容 |

## 刻意不設的目標

| 不設 | 理由 |
|---|---|
| metrics／告警 | repo 尚無 metrics 管線（`project.md ## Deployment`：observability 仍是真實待辦）；本單元不單獨建立 |
| 分散式追蹤 | 呼叫皆在同一行程內（ASGI 傳輸），log 的 `workItemId` 已足以串起一次交辦 |
