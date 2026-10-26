# 監控設計 — `U19 membership-service`

> 本檔實作 `nfr-design/observability-design.md` 的策略。該檔已定下四類事件的
> 級別、欄位與事件名前綴；本檔不重複它，只補**平台層**的落點：這些事件實際
> 落在哪裡、誰讀得到、以及哪些監控面在本 repo 根本沒有承載機制。

## 一、先說清楚本 repo 有什麼、沒有什麼

| 支柱 | 本 repo 現況 | 本單元能做什麼 |
|---|---|---|
| **Logs** | **有**：結構化 log → stdout／stderr → docker logs | 唯一真正的觀測載體。四類事件全部落在這裡 |
| **Metrics** | **無**：無 Prometheus、無 CloudWatch、無任何 exporter | 無承載機制。**不設計假的指標** |
| **Traces** | **無**：無 OpenTelemetry、無 X-Ray | 同上 |
| **Alerts** | **無**：告警需要 metrics 當對象 | 同上 |

**這不是本站的省略，是 `observability-requirements.md §四` 與
`observability-design.md §二` 已核可的判定**，承接 `OPEN-ND19-7`。
下面的「Metrics & KPIs」與「Alerts」兩表因此是**可量測的事實加上「目前無承載機制」
的誠實標記**，不是一組假裝已布建的門檻。

## 二、Metrics & KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| 每專案管理者數 | `project_members`（查詢，非指標管線） | **恆 ≥ 1**（`BR2.1` 的不變量） | 它是 `[FD1]`=A 的全部理由。**無 metrics 管線故無法持續監看**；可查但沒有人會定期查。本站的替代設計是把它做成**回填腳本的自我終檢**與**併發測試的斷言**，而非一個沒人看的儀表板數字 |
| 鎖等待時長 | **應用層計時**（取鎖前後各取一次時間） | 超過門檻記 WARN（門檻值為程式常數，`OPEN-ND19-6` 指派 `code-generation`） | 它是鎖競爭唯一的痕跡。**為什麼不用 `pg_stat_activity`**：那需要輪詢，屬 metrics 範疇而本 repo 沒有該管線（`observability-design.md §一之二`） |
| 授權拒絕次數 | WARN log（`membership.denied`）的出現次數 | **不設門檻** | 拒絕是**正常的業務結果**（使用者沒有權限），不是系統異常。設門檻會製造常態噪音——同 `U7` 的同形判定 |
| 自動改選次數 | INFO log（`membership.reselected`） | 不設門檻 | 稽核由 `reselection_events` 表承載（使用者讀得到）；log 只給維運者看「它有跑」 |
| 零成員專案數 | `projects` LEFT JOIN `project_members` | **恆為 0**（`NFR12.18` 的二元判準） | `[ND1]`=A 的驗收面。同第一列：**可查但無管線**，故真正的守門是回填腳本的終檢與 `create_project_with_owner` 的交易邊界 |

**第 1 與第 5 列是本表最重要的兩列，而它們的結論是「不靠監控」**：
兩個不變量都沒有可持續監看的承載機制，所以設計上把它們壓到**可在 CI 與腳本裡
二元判定**的位置（併發測試、回填終檢），而不是指望有人看儀表板。

## 三、Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| — | — | — | — |

**本單元不設任何告警，而且是因為沒有承載機制，不是因為不需要。**
`observability-design.md §二` 已核可此判定並指名承接站
`observability-setup`（4.4，**`CONDITIONAL`**）。

**`OPEN-ND19-7` 的落空風險在此重述**：該站是 `CONDITIONAL`，若被 skip，
判定 skip 的執行者必須把四項觀測面重新提交使用者。本 intent 已有三次指派落空的
實例，故這一句不是形式主義。

## 四、SLIs / SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| — | — | — |

**零新進程故無獨立可用性面**：本單元在既有 FastAPI process 內，
「它不可用」等於「backend 不可用」，沒有可獨立量測的失效模式
（`logical-components.md §二之一`、`reliability-requirements.md §四`）。
為它設一個 SLO 會產生一個與既有 backend SLO 重複且無法獨立量測的數字。

## 五、Logs：四類事件的平台落點

| 事件名 | 級別 | 欄位 | 誰讀得到 |
|---|---|---|---|
| `membership.denied` | WARN | `story_id`／`action`／`project_id`／`principal` | **只有維運者**（docker logs）。刻意不進 UI、不進稽核表 |
| `membership.lock_wait` | WARN | `project_id`／等待時長 | 同上 |
| `membership.reselected` | INFO | `project_id`／被選中者／被停用的 owner | 同上。**使用者看到的那一份在 `reselection_events` 表**，不是這裡 |
| `membership.reselect_skipped` | INFO | `project_id`／跳過原因 | 同上 |

### 5.1 logger 名稱與保留期

| 項目 | 值 | 依據 |
|---|---|---|
| logger 名稱 | `logging.getLogger("cloud360.membership")` | `team.md ## Code Style`：11 支模組用 `"cloud360.<module>"` 形式，5 支用 `__name__` 屬**已知不一致**，新模組一律用前者。本單元是新模組 |
| 保留期 | **沿用既有 docker logs 設定，本單元不新增轉送或保留規則** | `DEPLOY.md §5.6` 已為 stack 設過日誌上限；本單元不改它 |

**為什麼事件名前綴是本單元真正需要的東西**：repo 的既有 log 是自由格式字串。
**沒有穩定的事件名，就沒有任何東西能把這四類事件從一般 log 中篩出來**——
而 `NFR12.6`–`NFR12.29` 的全部價值在於事後找得到它們
（`observability-design.md §一之一`）。

### 5.3 這四個事件名是一個**沒有擁有者的契約端點**（本站自檢 2 的產出）

| 三問 | 答案 |
|---|---|
| 誰寫 | `U19` 的 facade 與 router |
| 誰讀 | 維運者（`docker logs` ＋ 字串篩選）。**沒有任何程式讀它們** |
| 誰保證它們不被改名 | **沒有人。** 沒有常數、沒有 enum、沒有測試、沒有 CI 檢查 |

**失敗模式**：下一個人重構時把 `membership.denied` 改成別的字串，
**什麼都不會壞**——沒有編譯錯誤、沒有紅燈、沒有執行期錯誤。
壞掉的是「事後找得到它們」這個唯一的價值，而那要到有人真的去找時才發現。

**本站的設計決定：把四個事件名定為模組層常數**（而非散落的字面字串），
使改名至少是一個可被 grep 到的集中動作。**不為它寫測試**——
一條「斷言常數的值等於某個字面字串」的測試驗的是它自己，不是任何行為
（`project.md` 記過恆真斷言的形狀）。記為 `OPEN-ID19-7`（named-gap）。

### 5.2 兩件刻意不做的事

| 不做 | 理由 |
|---|---|
| **不把拒絕寫進 `reselection_events`** | `[N2]`=A。拒絕不是角色變更，`previous_role`／`new_role` 對它無意義；且拒絕是高頻事件，會把成員詳情頁的變更紀錄查詢用無關列拖慢（而該查詢目前**無可用索引**，`OPEN-ND19-4`） |
| **不讓任何 log 進入使用者可見面** | `observability-design.md §三`：拒絕 log 含 `project_id`，對一個非成員而言那證實了「存在一個 id 為 N 的專案」。目前不是洩漏（使用者讀不到 log），而**這條界線只由「沒有人這樣做」維持**。`OPEN-ND19-8` |

## 六、新 CI job 的可觀測性（本站新增的一小項）

`[ID1]`=A 的 `concurrency` job 驗的是一個**併發**行為，而併發測試最常見的失敗
不是「斷言不成立」而是「卡住」。

| 項目 | 設計 |
|---|---|
| 逾時 | job 層設明確 `timeout-minutes`（值由 `code-generation` 定），**不靠 runner 預設的 360 分鐘**——一個死鎖的併發測試會把 runner 佔住數小時 |
| 失敗訊息 | 測試須在超時路徑印出**兩個執行緒各自卡在哪一步**（barrier 前／取鎖中／已提交）。只印 `assertEqual` 失敗對診斷無用 |
| 不得以 `sleep` 製造交錯 | `unit-of-work.md` 對 `U22` 已記過「一個 flaky 的併發測試等於沒有測試」；順序須以 barrier 釘住（`NFR12.1` 的後果第 3 項） |

**為什麼寫在監控設計裡**：這是本單元唯一新增的執行環境，而它的失敗模式
（卡住而非紅燈）與既有 job 不同類。既有 job 的失敗都是立即且有訊息的。
