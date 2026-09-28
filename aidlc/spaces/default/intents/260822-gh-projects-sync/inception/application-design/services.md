# Services — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: application-design（Inception 2.5）· Record: 260822-gh-projects-sync
     本機制沒有長駐服務。「service」在此指四支 workflow 各自的執行單元——
     它們有各自的觸發、生命週期、並行特性與失敗語意。
     上游輸入清單見 `components.md` §上游輸入。 -->

## 這個機制沒有長駐服務

本設計刻意不引入任何常駐處理程序、資料庫或對外端點（[req:NFR-S4]／[req:NFR-S5]）。四個執行單元全部是 GitHub-hosted runner 上的短生命週期 workflow run，跑完即消失。狀態只存在兩處：**Project #16 本身**與 **record 目錄下的 `sync-state.json` 與綁定編號**。

這帶來一個必須寫下來的後果：**沒有任何地方可以放「跨輪的記憶」**，除非它落在上述兩處或 GitHub 的既有資源上。[Q5=A] 的失敗收斂之所以選「以既有 issue 為記憶」，正是因為它不需要新的持久狀態。

## 四個執行單元

### S-A `forward-sync`（事件觸發）

| 項目 | 內容 |
| --- | --- |
| 觸發 | `push`（任一分支，含 `danniel/**`）＋ `pull_request`（`opened`／`synchronize`／`closed`）[req:FR-B4] |
| 生命週期 | 單次執行掃過 **`intents.json` registry 內的全部 intent**，逐一分流：**無綁定編號者走首建路徑**（C-3 `create_item`，[req:FR-A1]）；**已綁定者**比對 `sync-map` 判定與 `sync-state.json`，**有漂移才寫**。**不是**本次事件的 diff。見下方「為什麼不用事件 diff」 |
| concurrency | `aidlc-sync-event-${{ github.repository }}-${{ github.event.pull_request.head.ref \|\| github.ref_name }}`，`cancel-in-progress: false`。PR 事件取 head 分支名、push 事件取分支名，**同一分支上的兩條事件路徑因此落在同一組**（[req:NFR-P3] 成立），不同分支互不排隊 |
| 延遲目標 | 自 push 完成到看板更新 ≤ 5 分鐘（[req:NFR-P1]，量測型，[US:S-9 AC 6]） |
| 失敗語意 | 外部錯誤 → 紅燈 ＋ 通報；機制的正常判斷（`parked`／`unparseable`／`suppressed`／`undecidable`／`Aborted`）→ **不紅燈**，記入受管區塊與對帳報告 |
| 冪等性 | **必須冪等**。同一 commit 重跑不得產生第二則 issue（[US:S-1 AC 6]）、不得重複追加受管區塊（C-6 的 `parse` 先於 `render`） |
| 自我排除 | 訊息含 `[aidlc-sync]` 的 commit 不觸發任何看板寫入（[req:FR-A4]）。**與 registry 驅動選取的調和**（reviewer iteration 2 Major）：改為非 diff 選取後，本條有**兩道各自獨立成立的防線**——①**結構性**：回寫 commit 的內容就是剛寫進看板的值，寫完後 `sync-state.json` 與看板一致 ⇒ 下一輪判定**無漂移** ⇒ 不產生任何寫入，這道防線不依賴任何判斷；②**顯式**：workflow 層在 HEAD commit 訊息含 `[aidlc-sync]` 時整輪 skip，作為②的快速路徑。**兩道都是整輪層級，不是逐 record 層級**——這消除了「該 gate 整個 run 還是只 gate 一個 record」的歧義。**已知代價**（reviewer iteration 3 Minor）：整輪 skip 意謂該次 run 內**其他 intent 的漂移也一併不處理**，要等下一次事件或隔日對帳。此延遲的量級與上方「並行取消」殘留風險同一數量級（下一次事件即涵蓋，因選取為 registry 驅動、自癒），故不另設逐 record 的例外——逐 record gate 會讓防線①與②的層級不一致而重新引入原本要消除的歧義。**適用前提**：若最終憑證為 `GITHUB_TOKEN`，平台本身即不為其產生的 push 觸發 workflow，防線②變成恆真、由平台承接——[Q2=A] 選的是 GitHub App，故防線②**確實會被執行** |

> **為什麼不用事件 diff 決定處理哪些 record（reviewer iteration 1 Finding 2／3 的共同修法）**
>
> 最自然的實作是「看這次 push／PR 改了哪些 record 目錄」。本設計**不採**，因為它同時踩兩個坑：
>
> 1. **fixture 隔離只會對一半路徑成立。** ADR-A3 的「fixture 不註冊進 `intents.json` 故不被列舉」只約束 C-7 的**列舉**。S-A 若依 diff 推導，`.test-fixtures/<slug>/aidlc-state.md` 一被建立或變動就會被當成真實 record，送進配置給 **Project #16** 的 C-3——正是 ADR-A3 要避免的事。
> 2. **被 concurrency 取消的 run 會造成真正的遺漏，不只是延遲。** GitHub Actions 的 concurrency 只允許同組內一個 in-progress ＋ 一個 pending；第三個 run 排入時會**取消掉那個 pending run**，且此行為與 `cancel-in-progress` 的設定無關。若被取消的 run 處理的是**另一個** record，那個 record 就完全不會被事件路徑同步，要等隔日對帳。
>
> **改為 registry 驅動後兩者同時消失**：選取一律走 `intents.json` 的 registry（fixture 不在其中 ⇒ 永不被選中，與 C-7 同一條保護），且每一次執行都掃過**當下全部 intent**（無綁定者建立、已綁定且有漂移者補上）⇒ 任何被取消的中間 run，其工作都被下一次執行涵蓋，事件路徑因此是**自癒**的。
>
> **首建不被漏掉**（reviewer iteration 2 Critical）：選取條件是「registry 內的全部 intent」，**不是**「已綁定的 intent」。新誕生的 intent 在 registry 內但尚無綁定編號，走首建分支——若把條件寫成「已綁定且有漂移」，[req:FR-A1]／[US:S-1 AC 1]（Must、CAP-1、本系統的第一則故事）就永遠不會觸發。此為 iteration 1 修正時的措辭疏失，非設計意圖。
>
> **殘留的失效模式**（如實記載）：若某分支的最後一次事件 run 被取消（下一個事件到達後才輪到它，而它又被更後面的取消），該分支要等到再有事件或隔日對帳。以 6 個 record 的現況規模，單次全掃描成本可忽略；規模成長時以 `reconcile_batch_size` 同型的上限收斂。

### S-B `reconcile`（排程觸發）

| 項目 | 內容 |
| --- | --- |
| 觸發 | `schedule`（每日一次，避開 `0 23 * * 1-5`／`37 0 * * *`／weekly monday）＋ `workflow_dispatch` [req:FR-D1] |
| 生命週期 | 掃描全部**已綁定且未 park** 的 intent，單次處理量受 `reconcile_batch_size` 上限 |
| concurrency | `aidlc-sync-reconcile-${{ github.repository }}`，`cancel-in-progress: false`——**自成一組，與 S-A 可並行**（[req:NFR-P3]） |
| 失敗語意 | **單一 intent 失敗不中止整輪**；補平成功**不使 workflow 紅燈**（[US:S-7 AC 5]，解掉「成功補平 ⇒ 紅燈」那條矛盾） |
| 產出 | `ReconcileReport`：補平計數、一致率、**（G-1 修補後為六份清單）** 五份清單、延遲樣本（型別見 `component-methods.md`）。**缺口 G-1 於 U-7 的 functional-design 補入 `undecidable`**，清單數由五變六；欄位表見 `../../construction/U-7-reconcile-workflow/functional-design/domain-entities.md` |
| 與 S-A 的競爭 | 兩者可能同時寫同一 item。處置在 C-3 的寫入前回讀——後到者 `Aborted` 並列入 `aborted` 清單（[req:FR-C3]，唯一結果，「重算後仍寫入」不合格） |

### S-C `reverse-sync`（排程觸發）

| 項目 | 內容 |
| --- | --- |
| 觸發 | `schedule` ＋ `workflow_dispatch` [req:FR-G1] |
| 生命週期 | 讀看板現況 → 雜湊比對 → 有人為變更則寫同步專用檔並**開 PR** |
| concurrency | 與 S-B **同一組**（兩者都是排程、都碰 record，不應並行） |
| 寫入邊界 | **PR 的 diff 不得含 `aidlc-state.md` 任何一行**（[req:FR-G2]）；`ut` 上不出現未經 PR 的相關 commit |
| 對 S-A 的影響 | 反向 PR 開啟期間，S-A 對該 intent 的 Status 寫入**暫停**（`reason_code = "suppressed"`，[req:FR-G3]）。**逐 intent 判定，非全域**——[US:S-6 AC 3] 已含反例要求（X 在 PR 內、Y 不在，Y 照常寫） |
| 成本控制 | 反向 PR 須讓高成本的 `on: pull_request` workflow（至少 `ui-regression`）不對其執行（[US:S-6 AC 7]）。具體手段留 construction |

### S-D `selftest`（PR 觸發）

| 項目 | 內容 |
| --- | --- |
| 觸發 | `pull_request`，且僅當同步相關路徑變動 |
| 生命週期 | 兩段：①以**純文字 fixture** 驅動 C-1／C-2 的 dry-run 斷言（不發任何 API 寫入請求）②對**獨立測試 Project** 驅動 C-3 的端到端寫入讀回 |
| 為什麼要獨立測試 Project | [Q4=A]。放 #16 會讓測試 item 成為第 72 張卡進入 P3 視野；且 `ci.yml` 的 `on: pull_request` 無分支過濾，多個 PR 並行會寫同一個 item、觸發 [req:FR-C1] 的回讀不符而**自動增生 issue** |
| 失敗語意 | **這是真閘門**：斷言失敗 → CI 紅燈（[US:S-10 AC 1／AC 2]） |
| 突變驗證 | 把映射改壞（`[?]` → `In progress`）時斷言必須失敗——此為 AC 本身的一部分，不是另立的元層次 AC |

## 編排模式：orchestration，不是 choreography

四個單元之間**不互相發送事件**。每個單元自己編排它需要的元件呼叫（C-7 是 S-B 的編排者；S-A 的編排寫在 workflow step 序列裡）。

理由：choreography 需要一個事件匯流排，而本設計刻意零新增基礎設施。單元之間唯一的「通訊」是**透過共享狀態**（Project item、`sync-state.json`、通報 issue），且每一次讀取都伴隨回讀比對或雜湊比對，不假設對方的寫入已完成。

## 服務契約

| 契約 | 提供者 | 消費者 | 破壞性變更的影響 |
| --- | --- | --- | --- |
| `Decision` 的欄位集合 | C-1 | S-A、S-B | 新增 `reason_code` 值 → 所有消費端的 switch 需有 default 分支（不得靜默落入「照寫」） |
| `<record>/sync-state.json` 的 schema | C-4 | S-A、S-B、S-C | **跨輪相容性必須維持**——舊格式的檔案在新版讀取時不得崩潰。schema 需含版本欄位 |
| 受管區塊的標記與內容雜湊 | C-6 | S-C（防迴圈） | 改變區塊格式會使**所有既有 item 的雜湊失效**，下一輪反向同步會把全部 item 誤判為「有人為變更」。**這是本設計最危險的一次性遷移點**，見 ADR-A6 |
| 自訂欄位名 | Config | C-3 | 改名等同新增欄位；既有值不會遷移 |
| 通報 issue 的標題慣例與 label | C-5 | C-5 自己（跨輪搜尋） | 改變慣例會讓既有開啟中 issue 找不到，退化為每輪開新 issue |

## 擴縮特性

| 面向 | 現況 | 上限 |
| --- | --- | --- |
| intent 數 | 6 個 record，其中 5 個可解析 | S-B 的單次處理量由 `reconcile_batch_size` 宣告；框架單次操作次數上限（C-T5）的實際值待 PRE-1 實測 |
| 看板 item 數 | 71 個既有未綁定 ＋ 逐步增加的受管 item | Projects v2 的分頁由 C-3 內部處理，介面不暴露 |
| 事件頻率 | 每次 push 一輪；`danniel/**` 分支為主 | concurrency group 以**分支**為界，不同分支互不排隊。**同分支**高頻 push 時：GitHub 只保留一個 pending run，第三個以後到達會取消先前的 pending——但因選取為漂移驅動，被取消 run 的工作由下一次執行涵蓋，**不造成遺漏、只造成延遲**。延遲直接影響 [req:NFR-P1] 的 5 分鐘，量測方式為 [US:S-9 AC 6] 的 20 次取樣 ≥19 次達標 |
| runner | 全部 GitHub-hosted | 不佔用 `deploy.yml` 的 self-hosted runner（[kb] 確認 gh-aw 亦然） |
