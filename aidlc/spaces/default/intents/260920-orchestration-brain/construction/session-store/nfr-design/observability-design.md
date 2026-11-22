# Observability Design — `U10 session-store`

> 設計階段產出。本 repo **沒有 metrics、沒有 tracing、沒有告警管道**
> （`observability-requirements.md` 已實測記載），故本檔設計的是**日誌**這一根
> 支柱，並為另外三根指出它們缺什麼。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `observability-requirements.md` | `NFR4.60`（`MEMORY STATS` 訊號）、`NFR4.61`（每次拋出一筆 ERROR）、`NFR4.62`（兩種成因可區分）、`NFR4.63`（白名單）、`NFR4.64`（還原驗證可重跑）；`OPEN-N10-4`／`OPEN-N10-5` |
| `security-requirements.md` | `NFR4.45` 的內容禁令——與白名單是同一道檢查的兩面 |
| `reliability-requirements.md` | `NFR4.51` 的降級形狀；本檔的原因碼要餵得出它 |
| `performance-requirements.md` | `NFR3.40`–`NFR3.43` 的耗時——日誌要能承載它才驗得了 |
| `scalability-requirements.md` | `NFR4.60` 的使用率門檻（35%／100%） |
| `tech-stack-decisions.md` | `NFR8.41` 的客戶端須能區分 OOM，否則 `NFR4.62` 不可實作 |
| `functional-spec.md` | `W8` 的失效路徑；§七的 Audit logging 格（本單元刻意不寫稽核列） |
| `contract-summary.md`（`K-09`） | 五個方法與其單一例外型別 |

## 一、結構化日誌：欄位集合即白名單

```json
{
  "level": "ERROR",
  "logger": "cloud360.session_store",
  "event": "session_backend_unavailable",
  "method": "append_message",
  "sessionKey": "…",
  "segmentId": "workspace",
  "reason": "redis_oom",
  "elapsedMs": 1003
}
```

**`logger` 名稱為 `cloud360.session_store`**——`team.md` 逐字記載 repo 內兩種形狀
並存（11 支用 `cloud360.<module>`、5 支用 `__name__`），並定「新模組一律
`"cloud360.<module>"` 形式」。本單元為新模組，採前者。

**欄位集合就是 `NFR4.63` 的白名單，沒有第二份清單。** 實作上以一個固定的
建構函式產生日誌紀錄，**不接受任意 `**kwargs`**——白名單若只存在於文件，
下一個人加一個欄位時不會有任何東西擋他。

### 明確排除（承 `security-design.md` §一）

| 不入日誌 | 理由 |
|---|---|
| `SessionMessage.text` | Confidential；public repo 的 Actions log 公開可讀 |
| 整個 `ConversationSegment`／`BrainSession` | 同上，且 `logger.warning(f"...{session}")` 是最容易犯的形狀 |
| 三層作業對象識別碼的**組合** | `security-requirements.md` 的分級逐字「組合起來會洩漏某人正在看哪個專案」 |

## 二、日誌事件清單（與 `observability-requirements.md` 的等級表一一對應）

| 事件 | 等級 | 何時 | 欄位 |
|---|---|---|---|
| `session_backend_unavailable` | ERROR | 每次拋出（`NFR4.61`） | `method`、`sessionKey`、`reason`、`elapsedMs` |
| `session_segment_created` | INFO | `BR2.4` 建段 | `sessionKey`、`segmentId` |
| `session_history_trimmed` | DEBUG | `BR3.4` 丟棄訊息 | `sessionKey`、`segmentId`、`droppedCount`。**不得含被丟棄的內容** |
| `session_retry` | WARN | 冪等方法的每一次重試（`[D2]`=A） | `method`、`sessionKey`、`attempt`、`reason` |
| `load`／`touch` 的正常路徑 | **不記** | — | 每次互動都發生，記它只是噪音 |
| `HierarchyForbidden` 向上傳遞 | **不記** | — | 由 `K-07` 自己的層記；重記會雙份且可能夾帶識別碼 |

**`session_retry` 是本檔新增的**（`observability-requirements.md` 的表沒有它）。
理由：`[D2]`=A 的重試會把尾端延遲拉到 3 秒以上（見 `performance-design.md`），
而若重試完全不留痕跡，「偶爾很慢」就查不出成因。WARN 級是因為它代表
**已發生但已被處理**的異常——正是 `nfr-requirements-guide.md` 對 WARN 的定義。

## 三、三個原因碼的判定來源（`NFR4.62` 的實作形狀）

| 原因碼 | 判定方式 | 風險 |
|---|---|---|
| `redis_unreachable` | 客戶端的連線層例外（連線拒絕／逾時／DNS） | 低 |
| `redis_oom` | Redis 回覆以 `OOM ` 開頭的錯誤 | **中**——靠字串比對。`NFR8.41` 要求選型須能把它表達為可判別的錯誤；若客戶端只給泛用例外，本碼退化成字串匹配，而錯誤訊息文字是 Redis 的實作細節 |
| `redis_command_error` | 其他指令層錯誤（ACL 拒絕、腳本錯誤） | 低 |

**中風險那一列如實標明**，並指出它的承接：`OPEN-N10-5`（`U10` 的 `code-generation`）。

## 四、`NFR4.60` 的使用率訊號：採集點與它的限制

- **採集指令**：`MEMORY STATS`（app 身分可執行；`INFO` 不可——`U1` 的 compose
  註解逐字記載它是 `@slow @dangerous` 且兩個身分都跑不了）。
- **採集點**：**不**在每次呼叫時採——那會把一個診斷指令放進熱路徑。
  設計為**一個獨立的、低頻的採集點**（例如隨健康檢查節奏），其結果以 INFO 級
  日誌輸出。
- **門檻**：`scalability-design.md` 的 35%／100% 兩道。
- **它的限制，明寫**：`OPEN-N10-4` ——**沒有任何告警管道消費這個訊號**。
  本 repo 無 Prometheus、無 CloudWatch、無通知通道。所以 `NFR4.60` 在今天的
  實際效果是「**事後可查**」而非「**事前可知**」。不把它寫成監控，因為它不是。

## 五、Metrics 與 Tracing：本檔不設計，並說明為什麼

| 支柱 | 本檔的處置 |
|---|---|
| **Metrics** | **不設計**。repo 內零基礎設施，引入它是跨單元的工具鏈決策，不由本單元夾帶（`tech-stack-decisions.md` 已把它列為否決項並附理由）。`NFR3.40`–`NFR3.43` 的延遲驗證改由 `build-and-test` 的測試內計時承載 |
| **Tracing** | **不設計**。本單元是同進程元件，沒有跨服務邊界；真正需要 trace 的是 `U13 → U11 → U12` 那條鏈，屬那些單元。本單元能做的只是**不阻礙**——即日誌帶 `sessionKey`，使未來導入 correlation id 時有現成的關聯鍵 |
| **Alerting** | **不設計**，`OPEN-N10-4` 已記為無自然承接站 |
| **Dashboard** | **不設計**，同上（無 metrics 即無儀表板） |

**這一節的存在本身就是產出**：`nfr-design` 的 stage 檔逐字要求設計「metrics
collection architecture、distributed tracing strategy、alerting rules、dashboard
specifications」。本檔對四者皆為「不設計」，而逐項寫出理由，**不是略過**——
下游若讀到四個空白，會以為是遺漏。

## 六、`NFR4.64` 的還原驗證：設計為可重跑的腳本

`NFR4.64` 要求重啟還原有「可重複執行」的驗證程序。設計形狀：

1. 寫入一個涵蓋 `NFR4.53`–`NFR4.57` 五項的 fixture session（三段皆存在、各有訊息、
   各有不同的作業對象、`pageModes` 兩鍵其一為 `isolated`、TTL 已被續期過）。
2. 重啟 Redis 容器（不是 backend——**AOF 還原是 Redis 的事**）。
3. 逐項讀回比對五項，**含剩餘 TTL 落在預期區間**（不是滿額、不是 0）。

**第 2 步的對象是 Redis 而不是 backend**，這一點值得寫明：`NFR4` 的字面是
「重啟 **backend**」，但 backend 無狀態（`scalability-design.md` §擴展形狀），
重啟它什麼都不會掉。**真正會掉東西的是重啟 Redis**，所以驗證要打在那裡才有意義。
**承接**：`U10` 的 `build-and-test`（3.6，`ALWAYS`）；此為本檔對該站的具體交付要求。
