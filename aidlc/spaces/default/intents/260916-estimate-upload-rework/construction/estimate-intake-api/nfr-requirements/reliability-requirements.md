# Reliability Requirements — estimate-intake-api

> Unit: `estimate-intake-api`（U2）· Q3=A。

## 上傳與 enqueue 分離

| 情境 | 行為 |
|---|---|
| 驗證／parse／寫庫失敗 | 對應 4xx／5xx；**不**建批次（或整筆 rollback） |
| 寫庫成功、enqueue 失敗 | **保留**已 commit 批次；HTTP **仍 201**；寫 `advice_enqueue_failed` AuditEvent；建立 `Advice` 列且 `status=failed`（若尚無列） |
| 重複 enqueue | `Advice.estimate_set_id` **UNIQUE**；不得建第二列 |

## 刪除

- 硬刪級聯必須原子（單交易或 DB CASCADE）；失敗則 5xx 且資料不半刪。

## 重試

- 本 unit **不**提供「重跑建議」HTTP（留給 U7／後續）。
- process 重啟可能丟失 in-flight BackgroundTasks：已知限制；`Advice.status=generating` 逾時清理屬 U7／OQ-DD3，本 unit 文件化即可。

## 健康

- 沿用既有應用健康檢查；不另開 cost 專用 probe。

<!-- confirmed: Looks correct -->
