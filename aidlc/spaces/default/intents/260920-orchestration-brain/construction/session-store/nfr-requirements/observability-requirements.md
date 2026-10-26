# Observability Requirements — `U10 session-store`

> 編號自 `.60` 起（`.40`–`.57` 已由本單元其餘四份 NFR 檔佔用）。
> 本檔的立場：**本 repo 今天沒有任何 metrics、tracing 或告警管道**，所以本檔的
> 多數條目是「要新增什麼」而不是「要設多少」。如實這樣寫，不假裝已有承載機制。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `requirements.md:500-508`（`NFR4`） | 重啟還原的可測不變量——它需要被觀測才知道有沒有成立 |
| `rules.md`（本單元） | `BR3.6`（內容不得入 log）、`BR6.1`（Redis 不可用大聲失敗） |
| `functional-spec.md`（本單元） | `W8` 的失效路徑；§七的 Audit logging 格 |
| `contract-summary.md:684-742`（`K-09`） | 五個方法與其 `raises` |
| `deploy/docker-compose.deploy.yml:195-205` | `U1` 逐字記載的可觀測性限制：`INFO` 為 `@slow @dangerous`，兩個設定身分都跑不了 |
| `codekb/chiton/technology-stack.md:151`／`:206` | `:151` 逐字「**`org.md` 宣告的「Formatter: Black (Python)」「Linter: Ruff，CI 強制」在 backend 側不成立**」——這是本 repo 既有的「宣告與承載機制有落差」的實例，本檔對 SLO 採同樣的誠實處理：**不訂沒有量測與告警承載的百分比**。`:206` 確認 Redis 服務已佈建含 healthcheck，但 healthcheck 只證明 PONG，不證明容量 |

## 本 repo 的既有可觀測層（實測，不是假設）

| 支柱 | 現況 | 證據 |
|---|---|---|
| Logging | Python `logging`，輸出到容器 stdout。**無集中式收集、無索引、無保存政策** | `team.md` 的既成事實；`backend/services/*.py` 的 `logging.getLogger("cloud360.<module>")` 形狀 |
| Metrics | **完全沒有**。無 metrics endpoint、無 Prometheus、無 CloudWatch | 全 `backend/` 無 metrics 套件 |
| Tracing | **完全沒有** | 同上 |
| Alerting | **完全沒有**告警管道 | `U1` 的 `monitoring-design.md` 已記載（`I8-2`：索引失效在生產無偵測面） |

**所以本檔不訂 SLI／SLO 門檻**——`nfr-reliability-guide.md` 逐字要求 SLO 要有
量測與告警，而三者皆無。訂一個沒有承載機制的百分比是假精確。本檔改為定義
**必須存在的訊號**與**它們的承載機制缺口**。

## 需求

| ID | 需求 | 判定方式 | 來源 |
|---|---|---|---|
| **NFR4.60** | Redis 記憶體使用率須有一個**應用端可讀**的訊號 | 以 `MEMORY STATS` 取得（`U1` 逐字指出 `INFO` 在兩個身分下都不可用，`MEMORY STATS` 與主機端 `docker stats` 是僅有的替代）。**本條只要求訊號存在且可讀**，不要求告警——告警管道不存在，見下方 `OPEN-N10-4` | `[N3]`=A；`U1` 的 compose 註解 |
| **NFR4.61** | `SessionBackendUnavailable` 每次拋出都須產生一筆 **ERROR** 級日誌，含 `sessionKey` 與失敗的方法名，**不含**任何段內容 | 靜態斷言日誌呼叫的引數白名單（與 `NFR4.45` 同一道檢查）；整合測試斷言拋出時確有該筆日誌 | `BR6.1`；`BR3.6`；`construction.md` 逐字「Errors must be surfaced」 |
| **NFR4.62** | 記憶體耗盡造成的寫入失敗（`noeviction` 的 `OOM`）須與「Redis 不可達」在日誌上**可區分** | 兩者都走 `SessionBackendUnavailable`，但日誌須帶不同的原因碼。**這是本檔最要緊的一條**：`[N3]`=A 把容量問題從「無聲」變成「有聲」，若兩種成因在日誌上同形，就只是把無聲換成了含糊 | `[N3]`=A；`NFR4.51` |
| **NFR4.63** | 本單元的日誌欄位採**白名單**：`sessionKey`、`segmentId`、方法名、筆數、耗時、錯誤原因碼 | 白名單而非黑名單——黑名單漏一個就等於沒有。與 `NFR4.45` 是同一道靜態檢查的兩面（安全面禁止什麼、可觀測面允許什麼） | `BR3.6`；`EC6` |
| **NFR4.64** | 重啟還原（`NFR4.53`–`NFR4.57` 五項）須有一次**可重複執行**的驗證程序 | 單元定義逐字的「重啟還原測試」。本條要求它是可重跑的腳本或測試，不是一次性的人工確認——否則 `NFR4` 的不變量只在某一天成立過 | `NFR4`；`BR7.1` |

## 日誌等級對照（本單元）

| 事件 | 等級 | 欄位 |
|---|---|---|
| `SessionBackendUnavailable`（不可達） | ERROR | `sessionKey`、方法名、原因碼 `redis_unreachable` |
| `SessionBackendUnavailable`（記憶體耗盡） | ERROR | `sessionKey`、方法名、原因碼 `redis_oom` |
| `HierarchyForbidden` 向上傳遞 | **不記** | 由 `K-07` 自己的層記；本單元重記會造成雙份且可能夾帶識別碼 |
| 段建立（`BR2.4`） | INFO | `sessionKey`、`segmentId` |
| 上限修剪丟棄訊息（`BR3.4`） | DEBUG | `sessionKey`、`segmentId`、丟棄筆數。**不得含被丟棄的內容** |
| 一般的 `load`／`touch` | **不記** | 每次互動都會發生，記它等於製造噪音 |

## 具名缺口

### `OPEN-N10-4`：`NFR4.60` 的訊號有了，但沒有任何告警管道消費它

本 repo 無 Prometheus、無 CloudWatch、無任何告警通道。`NFR4.60` 要求訊號**可讀**，
但「可讀」與「有人會看」是兩回事。`[N3]`=A 之下記憶體耗盡會讓寫入失敗——使用者
會立刻知道，但**維運不會主動知道**。

**這不是本單元能關的**：告警管道是跨單元的基礎設施。
**承接**：`U1 brain-infra` 的 `monitoring-design.md` 已記載同形缺口 `I8-2`
（索引失效在生產無偵測面），而 `U1` **已完成且在游標之前**。
**故本項無自然承接站**，依 `project.md` 的規則如實記載並於完成摘要重新提交使用者。

### `OPEN-N10-5`：`NFR4.62` 的兩種原因碼需要 Redis 客戶端能區分 OOM 錯誤

`noeviction` 之下 Redis 對寫入回覆 `OOM command not allowed when used memory
> 'maxmemory'`。要把它與連線失敗區分，Redis 客戶端必須把它表達為一個**可判別的
錯誤型別或可比對的錯誤字串**，而不是一個泛用的例外。

**本站不選客戶端套件**（見 `tech-stack-decisions.md` 的 `NFR8.41`：選型留 `code-generation`），
故本條是**對選型的約束**而非對實作的約束：所選的客戶端必須能做到這個區分，
否則 `NFR4.62` 不可實作。**承接**：`U10` 的 `code-generation`（3.5，**ALWAYS**，游標之後）。
