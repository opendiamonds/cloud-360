# 觀測設計 — `U19 membership-service`

> 本站設計上游 `nfr-requirements` 的 **29 條 `NFR12.x`** 的承載形式。
> 本站**不複寫** `functional-design` 的 29 條 `BR` 規則（`team.md` 的單一真實來源）。
>
> `U19` 是 `service`，故六份設計產出全部適用（`U5`／`U18` 只有 `security-design`）。


## 〇、兩個載體的界線（本檔的組織原則）

| 載體 | 對象 | 誰讀 | 設計在 |
|---|---|---|---|
| **稽核列**（`reselection_events`） | 成功的角色變更（人工 ＋ 自動） | **使用者** | `functional-design` 的 `BR5.1`–`BR5.6`（本站不複寫） |
| **結構化 log** | 拒絕、鎖等待、自動改選的執行與跳過 | 維運者 | 本檔 |

## 一、四類 log 事件的形狀

| 事件 | 級別 | 欄位 | NFR |
|---|---|---|---|
| 授權拒絕 | **WARN** | `story_id`／`action`／`project_id`／`principal` | `NFR12.6`／`NFR12.26` |
| 鎖等待 | **WARN** | `project_id`／等待時長 | `NFR12.27` |
| 自動改選**執行** | **INFO** | `project_id`／被選中者／被停用的 owner | `NFR12.28` |
| 自動改選**跳過**（冪等命中） | **INFO** | `project_id`／跳過原因 | `NFR12.29` |

### 1.1 本站的設計增量：四者共用一個事件名前綴，而不是四種自由格式

| 設計 | 內容 |
|---|---|
| 事件名 | `membership.denied`／`membership.lock_wait`／`membership.reselected`／`membership.reselect_skipped` |
| 為什麼需要它 | repo 的既有 log 是自由格式字串（`team.md` 記載 11 支模組用 `logging.getLogger("cloud360.<module>")`）。**沒有穩定的事件名，就沒有任何東西能把這四類事件從一般 log 中篩出來**——而 `NFR12.6`–`NFR12.29` 的全部價值在於事後能找到它們 |
| logger 名稱 | `cloud360.membership`（沿用 `team.md` 的「新模組一律 `"cloud360.<module>"` 形式」） |

### 1.2 鎖等待的量測位置（`NFR12.27`）

**它不能用資料庫的鎖等待統計**——那需要 `pg_stat_activity` 的輪詢，屬 metrics 範疇
而本 repo 沒有 metrics 管線。設計為**應用層計時**：取鎖前後各取一次時間，
差值超過一個門檻即記 WARN。

**門檻本站不定值**（需要競爭資料），設計為可設定常數，預設由 `code-generation` 給。
記為 `OPEN-ND19-6`。**不把它寫成環境變數**——`project.md` 的環境設定契約要求
任何 compose 消費的變數都要同步 `render-env.sh` 與 `.env.example` 三處，
而一個 log 門檻不值得那個同步成本。

## 二、四項刻意不設計的觀測面（承 `observability-requirements.md` §四）

| 不設計 | 理由（承上游，本站不改） |
|---|---|
| 分散式追蹤 | repo 無 OpenTelemetry／X-Ray |
| metrics／儀表板 | repo 無 metrics 管線 |
| 告警門檻 | 無 metrics 即無可設門檻的對象 |
| SLI／SLO | 零新進程、無獨立可用性面 |

**本站確認這四項無 pattern 可設計**，並指名承接：它們屬 `project.md ## Deployment`
列為「Operations 中尚未落地的維運學科」，落點是 `observability-setup`（4.4，`CONDITIONAL`）。
**該 stage 是 CONDITIONAL，故若被 skip，判定 skip 的執行者須把這四項重新提交使用者**
——本 intent 已有三次指派落空的實例。記為 `OPEN-ND19-7`。

## 三、本站查出的一件事：拒絕 log 會洩漏專案存在性

`NFR12.6` 的拒絕 log 含 `project_id`。對一個**非成員**的拒絕，
該 log 證實了「存在一個 id 為 N 的專案」——而那個使用者本來不該知道它存在
（`AC12.1.3`：未被邀請者看不到該專案）。

| 評估 | 結論 |
|---|---|
| 誰能讀到這個 log | **只有維運者**，不是被拒的使用者 |
| 故這是洩漏嗎 | **不是**——使用者看不到 log。`BR1.5` 的拒絕回應本身不含專案資訊 |
| 為什麼仍寫下來 | 若日後有人把這類 log 接到使用者可見的錯誤頁或支援工具，它就變成洩漏。**界線是「log 不得進入使用者可見面」**，而這條界線目前只由「沒有人這樣做」維持 |

記為 `OPEN-ND19-8`（named-gap，非本輪缺陷）。
