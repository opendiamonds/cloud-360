# 監控設計 — `U9 memory-purge`

> 本檔是本單元最重要的一份產出：`NFR7.13` 的偵測機制（`OPEN-N9-1`，
> 上游標為 `blocking-downstream`，**本站是它指定的落點**）。
>
> **本單元的核心失敗模式不是「它壞了」，是「它什麼都沒做」**——而那在
> Actions 清單上只是少一列，而少一列沒有顏色。

## 一、本 repo 有什麼、沒什麼（與其他單元一致，不重複推導）

| 支柱 | 現況 | 本單元能做什麼 |
|---|---|---|
| **Logs** | 有：stdout → Actions log | 清除的輸出；但**漏跑時沒有 log 可看** |
| **Metrics** | **無** | 無承載機制 |
| **Traces** | **無** | 同上 |
| **Alerts** | **無 metrics 基礎的告警**，但有 **GitHub Issues** 這條既有管道（`daily-digest`／`release-watch` 都用它） | **本單元用它**——這是本 intent 第一次把 issue 當成告警而非摘要 |

## 二、Metrics & KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| **清除 workflow 最後一次成功的時間** | **GitHub Actions API**（`gh api .../actions/workflows/<id>/runs?status=success`） | 逾 **3 天**即開 issue | **這是本單元唯一真正被監看的指標。** 選它而非「資料庫裡最舊的逾期列」的理由見 §二之一 |
| 逾期未清的記憶列數 | `memory.memory_records WHERE expires_at < now()` | **不設監看** | 它直接量測真正關心的事，但**查它需要連資料庫**，而資料庫在那台可能離線的主機後面——檢查會與被偵測的失敗同時消失（`[ID1]` 選項 D 的否決理由） |
| `memory_audit_events` 的列數成長 | 同上 | **不設監看** | 同上。本單元是該表唯一的 DELETE 端，故漏跑會讓它無上界成長——但這個後果由同一個偵測涵蓋 |
| 清除刪除的列數 | Actions log | **不設門檻** | 正常值高度波動（取決於 90 天前的使用量），設門檻只會製造噪音。它是**事後診斷**資料而非監看指標 |

### 2.1 為什麼用代理指標而不是直接指標

直接指標（「資料有沒有被清掉」）比代理指標（「workflow 有沒有跑」）更貼近需求。
但本單元的情境讓前者不可用：

| | 直接指標 | 代理指標 |
|---|---|---|
| 量測對象 | 資料庫狀態 | GitHub 的 run 歷史 |
| 需要連資料庫 | **是** | **否** |
| 主機／runner 離線時 | **檢查本身也消失** | **仍然可執行** |
| 能否偵測「排程沒排入」 | 間接（資料變舊）但要等到逾期才看得出 | **直接** |

**上游固定的判準是「必須不依賴那個 runner」**，而那正好排除了直接指標的所有可達實作
（除了「暴露資料庫給 GitHub 託管 runner」，而那已在 `[N1]` 被否決）。
**故這裡用代理指標不是將就，是判準的唯一解。**

### 2.2 門檻為 3 天的理由

清除每日執行。門檻取 3 天而非 1 天：

| 門檻 | 問題 |
|---|---|
| 1 天 | 任何單次失敗（GitHub Actions 偶發故障、runner 重啟、維護窗口）都開 issue → 噪音，而噪音會讓告警被忽略 |
| **3 天** | 容忍兩次連續失敗；而 90 天保存期之下，3 天的延遲對合規意義無實質影響 |
| 7 天以上 | 一週無人察覺，而 `FR4.5` 的合規意義建立在它真的會到期之上 |

**門檻值以 workflow 內的常數承載，不設為環境變數**——同 `NFR12.27` 的同形理由
（`project.md` 的環境設定契約要求任何 compose 消費的變數三處同步，而一個門檻不值得）。

## 三、Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| **清除 workflow 逾期未成功** | `now() - 最後成功時間 > 3 天` | 高（它代表一條已核可的保存期需求正在失效） | **GitHub Issue**（`gh issue create`），帶固定標題前綴以便去重 |

### 3.1 去重：同一個問題不得每天開一個新 issue

監看者每日執行，故若清除持續漏跑，它會連續多日命中門檻。
**設計要求**：開 issue 前先以固定標題前綴查詢是否已有 open issue；
有則**不開第二個**（可選擇追加一則 comment）。

**沒有這一條的後果**：一週後有七個相同的 issue，而那與沒有告警的效果接近
——它會訓練讀者忽略它。

### 3.2 監看者自己漏跑怎麼辦（誠實記載，不假裝已解決）

監看者跑在 GitHub 託管 runner 上，故它不受自架 runner 離線的影響。
**但它仍可能因 GitHub Actions 整體故障、repo 設定變更或 workflow 被停用而不執行。**

| 誰監看監看者 | **沒有人** |
|---|---|
| 這是無限遞迴嗎 | 是——任何監看鏈都必須在某處停止 |
| 為什麼停在這裡是可接受的 | 監看者的依賴面（GitHub 自身）**嚴格小於**被監看者的依賴面（GitHub ＋ 自架主機 ＋ 該主機上的 runner 服務 ＋ 資料庫容器）。每一層監看都在縮小依賴面，而停在「只依賴 GitHub」是本 repo 能達到的最小面 |
| 殘留風險 | GitHub Actions 長期故障或 workflow 被誤停用時，**兩者同時靜默**。記為 `OPEN-ID9-1` |

**這一節的存在本身是設計的一部分**：`project.md` 記過「不可達的規則是死碼，
卻在文件上長得像已解決」，而一條沒有說明自己邊界的監看設計會讓讀者以為
漏跑已被完全排除。

### 3.3 `issues: write` 沒有先例——這是本設計唯一的權限增量

| 查證 | 結果 |
|---|---|
| `daily-digest.md` 的 `permissions` | `contents: read`／**`issues: read`**／`pull-requests: read`／**`actions: read`** |
| 它怎麼開 issue | gh-aw 的 `safe-outputs: create-issue:`——**一條經過消毒的獨立寫入路徑**，不是把 `issues: write` 授給 agent |
| 本 repo 有任何排程 workflow 持有 `issues: write` 嗎 | **沒有** |
| 本設計需要的權限 | `actions: read`（**有先例**，`daily-digest.md:13`）＋ **`issues: write`**（**無先例**） |

**提問時我把這一點說得比實情寬**（寫成「既有兩個排程 workflow 已有 `issues` 權限
的先例」），作答後開檔核對更正。**結論不變，但代價要如實記載。**

#### 兩個可行的替代方案，本站不預選

| 方案 | 內容 | 取捨 |
|---|---|---|
| **直接 `issues: write`**（本設計的預設） | 監看者 workflow 宣告 `permissions: {contents: read, actions: read, issues: write}` | 最簡單、純 Actions、無 LLM。代價：一個本 repo 無先例的寫入權限。**範圍已是最小**（`issues: write` 不含 `contents: write`，不能改程式碼） |
| **改用 gh-aw 的 `safe-outputs`** | 沿用既有兩個排程 workflow 的形狀 | 權限與既有一致。代價：它會把一個**二元的時間戳比較**放進 LLM 路徑，而 `project.md` 把「所有 LLM 路徑」列為三塊結構性盲區之一——`[ID1]` 選項 B 已因同一理由被否決 |

**本站的判斷**：預設採直接 `issues: write`，並把它作為**具名的權限增量**
交給關卡（而非藏在實作細節裡）。若使用者或 repo 維護者偏好不新增該權限，
替代方案已寫明且不需重新設計——只需改監看者的輸出方式。記為 `OPEN-ID9-2`。

## 四、SLIs / SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| — | — | — |

**本單元無 SLO**，理由與其他單元不同，故寫明：它不是一個服務，沒有可用性面。
它是一個排程作業，而「它有沒有按時跑」已由 §三 的告警承載
——那是**告警**而非 SLO（沒有誤差預算可言：漏跑就是漏跑）。

## 五、Logs & Tracing

| 項目 | 設計 |
|---|---|
| 清除的輸出 | Actions log。須印出**兩條 DELETE 各自刪除的列數**與**稽核 INSERT 的列數**，三者是事後診斷的唯一依據 |
| 不得印出的內容 | **記憶內容、`content`、`embedding`、任何使用者可識別資料**。清除處理的是個人對話歷程，而 Actions log 在 public repo 中公開可讀——`project.md` 逐字記過「一次意外 echo 即等同公開發布」 |
| 監看者的輸出 | 最後成功時間、距今天數、是否命中門檻。**不含任何資料庫內容**（它本來就不連資料庫） |
| 保留期 | 沿用 GitHub Actions 的既有保留設定，不新增 |
| Tracing | **無**（repo 無 OpenTelemetry／X-Ray；且兩個 workflow 各自是單步驟作業，無跨服務呼叫鏈） |

### 5.1 一條容易被忽略的禁令

清除的 SQL 若寫成 `DELETE ... RETURNING *`（為了印出刪了什麼），
**會把記憶內容印進公開可讀的 Actions log**。

**設計要求**：只能 `RETURNING id`（或僅取 `row_count`），**絕不 `RETURNING *`**。
這是一個單字之差、CI 不會抓、而後果是公開發布使用者的私人對話歷程。
記為本單元在 `code-generation` 的 blocking 檢查項。
