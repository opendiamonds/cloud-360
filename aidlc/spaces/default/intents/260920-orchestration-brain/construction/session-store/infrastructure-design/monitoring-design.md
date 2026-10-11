# Monitoring Design — `U10 session-store`

> 本檔把 `observability-design.md` 的策略落到這個平台上。
> **本 repo 沒有 metrics 系統、沒有 tracing、沒有告警管道**，故下方多數列的
> 「Routes to」是空的——那是事實，不是待填。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `observability-design.md` | 日誌事件清單、三個原因碼、`MEMORY STATS` 採集設計、四支柱的逐項處置 |
| `reliability-design.md` | 失敗分類；還原五項 |
| `scalability-design.md` | 35%／100% 兩道容量門檻 |
| `performance-design.md` | 延遲預算（P95 20ms／150ms／200ms）與重試對尾端的影響 |
| `security-design.md` | 日誌白名單與內容禁令 |
| `logical-components.md` | 失敗域與爆炸半徑——告警若存在，應該對齊它 |
| `components.md` | `SessionContext` 的 `external_dependencies`（Redis） |
| `functional-spec.md` | `W8` 的失效路徑 |
| `contract-summary.md`（`K-09`） | 單一例外型別 |

## 一、Metrics & KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| Redis 記憶體使用率 | `MEMORY STATS`（app 身分可執行；**`INFO` 不可**——`U1` 註解逐字 `@slow @dangerous`，兩個身分都跑不了） | 35%（`NFR4.40` 的承諾區上緣）／100%（寫入開始失敗） | `[N3]`=A 之後，觸頂的後果是**寫入失敗**而非無聲淘汰。這個指標是唯一能提前看到它的東西 |
| `session_backend_unavailable` 事件數（依 `reason` 分） | 應用日誌 | 無門檻（無告警管道） | 三個原因碼分辨「Redis 掛了」「記憶體滿了」「指令被拒」——第三種通常代表 ACL 或 Lua 的部署問題 |
| `session_retry` 事件數 | 應用日誌 | 無門檻 | 重試會把尾端延遲拉到 3 秒以上（`performance-design.md`）；沒有這個訊號，「偶爾很慢」查不出成因 |
| `session_history_trimmed` 的 `droppedCount` | 應用日誌（DEBUG） | 無門檻 | 若穩態下每次都 > 1，代表 200 的上限相對於實際使用偏小 |
| 方法耗時 `elapsedMs` | 應用日誌 | 對照 `NFR3.40`–`NFR3.42` | **本 repo 無 metrics 系統**，故 P95 無法連續計算；驗證落在 `build-and-test` 的測試內計時 |

**全部五列的 Source 都是「應用日誌」或「一次性查詢」，沒有一列是 metrics 系統**——
這是本 repo 的現況（`observability-requirements.md` 已實測記載）。把它們列成表，
是為了讓下一個導入 metrics 的人知道**該先接哪五個**。

## 二、Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| Redis 記憶體逼近上限 | 使用率 ≥ 35% 持續 | 應為 ticket | **（無）** — `OPEN-N10-4` |
| Redis 不可達 | `reason=redis_unreachable` 連續出現 | 應為 page | **（無）** — `OPEN-N10-4` |
| 寫入因 OOM 被拒 | `reason=redis_oom` 出現任一次 | 應為 page | **（無）** — `OPEN-N10-4` |
| Lua／ACL 問題 | `reason=redis_command_error` 出現任一次 | 應為 page | **（無）** — 它會在第一次呼叫就出現，不是漸進 |

**`Routes to` 四列皆為空，而且不是本單元能填的。** 本 repo 無 Prometheus、
無 CloudWatch、無通知通道；`U1` 的 `monitoring-design.md` 已記載同形缺口 `I8-2`
（索引失效在生產無偵測面），而 `U1` 已完成且在游標之前。
`OPEN-N10-4` 已如實記為**無自然承接站**並於閘門重新提交使用者。

**為什麼仍然把這張表寫出來**：告警的**條件與嚴重度**是本站能決定的，
只有**路由**不能。把條件寫下來，使未來接上管道的人不必重新推導一次；
把路由留空並指名缺口，使它不會被誤讀成已經有人收。

## 三、SLIs / SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| — | **本單元不設 SLO** | — |

**理由（承 `reliability-requirements.md`，不重開）**：`nfr-reliability-guide.md`
逐字要求 SLO 要有量測與告警，而本 repo 三者皆無；部署目標是自有 staging，
production 不在範圍。**訂一個無法量測也無人值守的百分比是假精確。**

## 四、Logs & Tracing

- **彙整策略**：容器 stdout → Docker 的 `json_file` driver（`docker-compose.test.yml`
  的 `logging: *json_file_bounded` 錨點顯示 repo 已有 bounded 設定的慣例）。
  **無集中式收集、無索引、無保存政策**——查詢方式是 `docker compose logs`。
- **結構化形狀**：見 `observability-design.md` §一。`logger` 名稱為
  `cloud360.session_store`（`team.md` 逐字要求新模組一律 `"cloud360.<module>"`）。
- **欄位白名單以單一建構函式強制**，不接受任意 `kwargs`——白名單若只存在於文件，
  下一個加欄位的人不會有任何東西擋他。
- **Tracing**：無。本單元是同進程元件，沒有跨服務邊界。能做的只是**不阻礙**——
  日誌帶 `sessionKey`，使未來導入 correlation id 時有現成的關聯鍵。
- **Dashboard**：無（無 metrics 即無儀表板）。

## 五、`MEMORY STATS` 採集點的設計

| 面向 | 決定 | 理由 |
|---|---|---|
| 位置 | backend 行程內的低頻取樣 | 需要的是**連續**訊號而非單次快照 |
| 頻率 | 低頻（分鐘級），**不在熱路徑上** | `MEMORY STATS` 是診斷指令，放進每次呼叫會讓它自己變成效能問題 |
| 輸出 | INFO 級結構化日誌 | 沒有 metrics 系統可送；日誌是唯一載體 |
| 是否違反 `project.md` 的「禁止以 repo 內程式承載無人值守的流程自動化」 | **否** | 該條的判準逐字是「由事件或排程觸發、無人在迴圈內」且標的是「**流程自動化與外部系統同步**」。行程內對自身依賴的記憶體取樣不是外部同步，不落在禁令範圍。**此判定逐字寫出，不憑直覺** |

## 六、部署後的還原驗證（`[I1]`=B）

這是本單元**唯一**真的會被執行的驗證機制，形狀見 `cicd-pipeline.md` §三。
在監看面的意義：它是 `NFR4.53`–`NFR4.57` 五項的唯一偵測面，
而它的執行頻率等於**部署頻率**（deploy-on-merge），不是連續的。
