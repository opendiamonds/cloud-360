# 可觀測性需求 — `U8 memory-service`

> 本 repo 的可觀測性現況已由 `U9` 逐一查證：**有 logs（stdout → Actions／容器
> 日誌）、無 metrics、無 traces、無 metrics 基礎的告警**，告警的唯一既有管道是
> GitHub Issues。本檔不發明不存在的承載機制。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `memory-purge/infrastructure-design/monitoring-design.md`（`U9`，已交付） | 四支柱現況表（logs 有、metrics／traces 無、告警只有 issue 管道） |
| `functional-design/rules.md` | `BR2.2`／`BR4.1`／`BR5.1`／`BR6.1` 的拒絕路徑（本檔 `NFR6.21` 的量測對象） |
| 本站 `security-requirements.md` | `NFR6.21`（日誌不得含記憶內容）——本檔是它的量測面 |
| 本站 `performance-requirements.md` | `NFR3.20`／`NFR3.21`（延遲量測必須記錄列數與提供者） |
| `project.md` | 本 repo 為 public、Actions log 公開可讀；logger 命名一律 `cloud360.<module>` |

## 一、可觀測性需求

| id | 需求 | 二元判準 | 來源 |
|---|---|---|---|
| **`NFR7.30`** | 每一次授權拒絕都留下一筆結構化日誌，含 principal 識別字、`memoryId`、以及 `reason`（`owner` 或 `scope`） | 以無權身分呼叫四條端點各一次 → 四筆日誌，各含三個欄位 | ADR-0006 audit logging |
| **`NFR7.31`** | 授權拒絕的日誌**不得含** `content`、`embedding` 或任何記憶內容 | 對拒絕路徑的日誌輸出做字串比對：不含 fixture 記憶的 `content` | `NFR6.21` |
| **`NFR7.32`** | embedding 提供者不可用時的日誌必須含**提供者名稱與可選值**，不得只寫「失敗」 | 觸發 `EmbeddingProviderUnavailable` → 日誌含選定的提供者名與可選清單 | `BR3.5` |
| **`NFR7.33`** | 本單元新增的 logger 一律為 `cloud360.<module>` 形式 | 新增模組中 `logging.getLogger` 的引數皆為該形式，不用 `__name__` | `team.md` `## Code Style`（逐字：新模組一律 `"cloud360.<module>"`） |

## 二、Metrics 與 SLI/SLO

| SLI | SLO | 量測窗口 |
|---|---|---|
| — | — | — |

**本單元無 SLO，理由具體**：

1. **沒有 metrics 承載機制**。`U9` 已逐一查證 repo 無 metrics、無 traces。
   在沒有時間序列儲存的情況下宣告一個百分位 SLO，等於宣告一個沒有人會量的數字。
2. `NFR3.20`／`NFR3.23` 的延遲門檻**是需求而非 SLO**：它們在
   `build-and-test`（3.6）以一次性量測驗證，不是持續量測的誤差預算。
3. 本單元不是獨立服務，沒有可用性面（見 `reliability-requirements.md §四`）。

**不假裝有**：若日後引入 metrics 管線，本單元的候選 SLI 是
`search` 的延遲百分位與授權拒絕率，但那需要先有承載機制。記為 `N8-10`。

## 三、Logging

| 項目 | 設計 |
|---|---|
| 層級 | 授權拒絕為 `WARNING`（它是可恢復的、預期會發生的）；提供者不可用為 `ERROR` |
| 不得記錄的內容 | **記憶內容、`embedding`、任何可識別的使用歷程**。這是 `NFR7.31` |
| 成功路徑 | **不逐筆記錄**。每輪對話寫一筆 episodic（`BR7.1`）意味著成功寫入是高頻事件；逐筆記錄會把日誌變成記憶內容的第二份副本，而那正是 `U5` 刻意不讓稽核表含內容的同一個理由 |
| 保留期 | 沿用既有容器日誌設定，不新增 |

### 3.1 這一條的風險比它看起來高

`project.md` 逐字：「一次意外 echo 即等同公開發布」。本單元處理的是
**個人對話歷程**，而最容易出錯的位置正是拒絕路徑的日誌——
寫 `logger.warning(f"denied: {memory}")` 會把整列（含 `content`）帶進日誌，
而它在功能上完全正常、測試也會綠。

**故 `NFR7.31` 的判準是字串比對而非人工審查**：測試要拿 fixture 的
`content` 去比對日誌輸出，確認不命中。

## 四、Tracing

**無**（repo 無 OpenTelemetry／X-Ray）。本單元是進程內的三層呼叫，
無跨服務呼叫鏈；唯一的外部呼叫是 `U6` 的 embedding（而 `U6` 自己的契約
`K-06` 不含 tracing 要求）。

## 五、本單元需要被看到但沒有承載機制的一件事

**`search` 回空集合是正常還是故障，從外部看不出來。**

| 情境 | 可觀察結果 |
|---|---|
| 使用者真的沒有記憶 | `search` 回空 |
| `BR3.2` 的 `embeddingModel` 分群把全部列排除（換過提供者而未重新 embed） | `search` 回空 |
| `BR2.2` 的可見範圍過濾把全部列排除 | `search` 回空 |

三者在 `U15` 的畫面上**完全一樣**，而第二種是缺陷。

**本站不發明 metrics 去區分它們**（無承載機制），而是要求
`NFR7.34`：`search` 回空時，日誌須記錄**候選集合在每道過濾之後的筆數**
（可見範圍過濾後、`embeddingModel` 過濾後），使三種情境在事後診斷時可區分。
筆數不是內容，故不違反 `NFR7.31`。

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR7.34`** | `search` 回空集合時，日誌記錄兩道過濾各自之後的候選筆數 | 製造「換提供者後未重新 embed」的情境 → 日誌顯示可見範圍過濾後筆數 > 0 而 `embeddingModel` 過濾後筆數為 0 |
