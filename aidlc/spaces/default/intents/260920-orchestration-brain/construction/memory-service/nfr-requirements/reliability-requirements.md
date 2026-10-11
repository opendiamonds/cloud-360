# 可靠性需求 — `U8 memory-service`

> 本單元**不是一個獨立的服務**，它是既有 FastAPI 進程內的三層。
> 故它沒有自己的可用性面——可用性由既有應用程式承載。
> 本檔談的是**失敗時的行為**與**資料耐久性**這兩件它真的擁有的事。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `requirements.md` `NFR4` | 狀態外部化與重啟還原（本單元的狀態全在 PostgreSQL，見 §二） |
| `functional-design/rules.md` | `BR3.5`（提供者不可用時大聲失敗）、`BR4.2`／`BR5.3`（同交易邊界）、`BR4.3`（冪等語意） |
| `inception/contract-design/contract-summary.md` | `K-08` 的 `retry_and_idempotency`；`K-06` 的 `EmbeddingProviderUnavailable` |
| `org.md` `## Deployment` | deploy-on-merge 至自架 staging；production 不在範圍 |

## 一、可靠性需求

| id | 需求 | 二元判準 | 來源 |
|---|---|---|---|
| **`NFR4.20`** | 本單元**不持有任何行程內狀態**；重啟後所有記憶與稽核完整還原 | 本單元新增的模組中沒有模組層可變容器（dict／list／set）承載跨請求狀態；重啟後查詢結果不變 | `NFR4`；見 §二 |
| **`NFR4.21`** | `write` 與 `delete`／`widen_scope` 的稽核寫入必須與資料變更同交易；任一失敗則兩者皆不生效 | 以交易中止測試：強制失敗後記憶列數與稽核列數皆不變 | `BR4.2`／`BR5.3`；`FR4.7` |
| **`NFR4.22`** | embedding 提供者不可用時**大聲失敗並列出可選值**，不得靜默降級為其他提供者 | 以不可用的提供者設定呼叫 `write`／`search` → 拋 `EmbeddingProviderUnavailable`，且回應含可選值；`memory_records` 無新列 | `BR3.5`；`K-06` |
| **`NFR4.23`** | 本單元**不實作** retry／backoff／circuit breaker | 本單元新增的模組中無重試迴圈、無 backoff 計時 | 見 §三 |

## 二、`NFR4.20`：本單元天然滿足 `NFR4`，但理由要寫下來

`NFR4` 的關注點是行程內狀態在重啟後消失。本單元的狀態**全部在 PostgreSQL**
——它沒有 session、沒有快取（`scalability-requirements.md §三` 刻意不加）、
沒有佇列。

**但這不是可以不檢查的事**：`project.md` 記載 repo 內有**三處既有行程內狀態
容器**（`collab_router` 的連線字典、`advice_orchestrator` 的
`_executor`／`_progress`／`_inflight`、`pricing_client` 的磁碟快取），
而 `NFR4` 明確把它們排除在本 intent 之外。
本單元**不得**照抄那個形狀——`NFR4.20` 的判準就是那個檢查。

## 三、`NFR4.23`：不重試是刻意的，不是遺漏

| 操作 | 冪等性（`K-08` 逐字） | 失敗時的正確行為 |
|---|---|---|
| `write` | **非冪等**（重複呼叫產生第二列記憶） | **呼叫端不得自動重試**——重試會製造重複記憶 |
| `search` | 唯讀冪等 | 可由呼叫端重試 |
| `delete` | 冪等（已刪除者再刪為 `MemoryNotFound`） | 可重試，但不產生第二筆稽核（`BR4.3`） |

`nfr-design-guide.md` 的 retry／circuit-breaker pattern 是為「呼叫會失敗的外部
依賴」而設。本單元的依賴有兩個：同一主機上的資料庫，以及 `U6 EmbeddingPort`。
前者失敗的正確反應是讓請求失敗；後者的失敗行為已由 `BR3.5` 定為大聲失敗。

**`write` 的非冪等性是這一條的關鍵**：在它上面加自動重試，會在一次網路抖動後
留下兩筆一樣的記憶，而使用者看不出哪一筆是多的。

## 四、不適用的可靠性面向（逐項附理由）

| 面向 | 判定 |
|---|---|
| 可用性 SLA／SLO | **N/A**：本單元不是獨立服務，沒有自己的可用性面。既有應用程式的可用性未定 SLO（repo 無 metrics 基礎，`U9` 的 `monitoring-design.md` 已查證），故本單元無法宣告一個它不控制的數字 |
| RTO／RPO | **N/A，但指出一個真實缺口**：本單元的資料耐久性完全依賴既有的 PostgreSQL 備份策略，而**本站查不到任何備份需求或機制的記載**。這不是本單元能決定的（屬部署面），但「90 天的個人對話歷程沒有已記載的備份策略」是一個應該被看到的事實。記為 `N8-9` |
| 多區／容錯移轉 | **N/A**：單主機 compose（ADR-0007），production 不在範圍 |
| 優雅降級 | **N/A 且刻意**：`BR3.5` 明文禁止降級（靜默降級會讓整批記憶以錯的提供者寫入，之後因 `BR3.2` 的分群永久不可被檢索到） |
