# 觀測需求 — `U20 requirement-field-service`

## 〇、本單元的觀測面有兩個載體，而它們刻意不同

| 載體 | 回答的問題 | 給誰看 |
|---|---|---|
| **資料列本身**（`updated_by`／`updated_at`／`cleared_at`／`updated_on_behalf_of`） | 「這個值是誰、何時寫或清的，是不是大腦代寫的」 | 使用者（`U23` 的「最後更新」）與稽核 |
| **應用 log**（logger `"cloud360.requirement_fields"`） | 「誰被拒絕了、為什麼」「誰改了哪一欄」 | 維運者 |

稽核紀錄就是資料列本身，**不另建稽核表**——`ADR-015` 定「只保留最新值」，與 `U19`
因 `AC12.2.2` 需要 UI 讀得到的變更紀錄而另建 `reselection_events` 的情況不同。

## 一、拒絕事件

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR20.27`** | 每次授權拒絕寫一行 `WARNING`，欄位為 `story_id`、`action`、`system_id`、`principal` 的 `user_id`、拒絕理由（`pending`／`global`／`not_member`），**不含**欄位值與代寫標示（`BR41.6`） | 以 `assertLogs` 斷言拒絕案例產生恰一行、含上述欄位、不含測試送出的值字串 |

## 二、寫入與清空

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR20.28`** | 每次有效寫入或清空寫一行 `INFO`，欄位為 `system_id`、`agent_group`、`field_key`、`user_id`、動作（`write`／`clear`）、是否為代寫（布林），**不含**值 | `assertLogs` 斷言寫入案例的 log 不含送出的值字串 |
| **`NFR20.29`** | no-op（`BR43.3`／`BR43.4`）不寫 `INFO`，避免重試灌爆 log | 對已清空欄位清空兩次 → 第二次無 `INFO` |

**為什麼不記值**：值是業務機密（`security-requirements.md` 第一節），而 log 的存取範圍與
保存期限比資料庫寬；值本身已在資料列上，log 只需要能把事件定位到那一列。

## 三、logger 命名

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR20.30`** | 新模組一律 `logging.getLogger("cloud360.requirement_fields")`，不用 `__name__` | `team.md ## Code Style` 的慣例；本單元新增檔案 grep `getLogger(__name__)` 為 0 |

## 四、刻意不設的目標（附理由，不留空白）

| 不設 | 理由 |
|---|---|
| 指標（請求率、錯誤率、延遲直方圖） | repo 沒有指標收集管線（`project.md ## Deployment`：observability 仍是真實待辦）；為本單元單獨引入是獨立的基礎設施決定 |
| 告警 | 同上；沒有指標就沒有告警依據 |
| 分散式追蹤 | 單一進程內呼叫，無跨服務邊界 |
