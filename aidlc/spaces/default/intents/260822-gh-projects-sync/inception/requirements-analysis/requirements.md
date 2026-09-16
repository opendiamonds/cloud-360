# Requirements — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: requirements-analysis（Inception 2.3）· Record: 260822-gh-projects-sync
     來源標籤：[Q<n>]／[F<n>] 指本站問題檔的已選答案；[intent:*]／[feas:*]／[scope:*] 指上游 artifact；
     [ADR-*] 指決策紀錄；[V-<n>] 指本站問題檔的查證紀錄表。
     每條需求皆有二元可判的驗收判準；判準寫「正常」「成功」者不算判準。 -->

## 上游輸入

本需求集的每一條都可追溯到下列已核可產出（`phases/inception.md` 的 Traceability 要求）：

- **intent-statement**（`../../ideation/intent-capture/intent-statement.md`）：問題陳述、四類受益者、三項成功指標（零人工更新／一致率／可追溯）。
- **scope-document**（`../../ideation/scope-definition/scope-document.md`，Revision 1）：CAP-1～CAP-11、Won't Have W-2～W-4、上線前置依賴 P-1～P-5。
- **intent-backlog**（`../../ideation/scope-definition/intent-backlog.md`，Revision 1）：PU-0～PU-10 與依賴性質。
- **feasibility-assessment** 與 **constraint-register**（`../../ideation/feasibility/`）：Conditional GO、R-1～R-7、C-T1～C-T9／C-O1～C-O6／C-R1～C-R4、ADR-0006 四面向判定。
- **initiative-brief**（`../../ideation/approval-handoff/`，Revision 1）：未解項 U-1～U-7 與其指派落點。
- **ADR-0013**（`../decisions/0013-aidlc-projects-sync-scoping.md`）與其修訂對象 **ADR-0012**。
- **codekb（brownfield 掃描產出）**，位於 `aidlc/spaces/default/codekb/cloud-360/`，基準 commit `9307dbc`：
  - **architecture.md** — 「開發流程層架構（一）AI-DLC 狀態表徵」提供 `intents.json`／`aidlc-state.md`／audit shard 三個資料源的欄位契約、兩套狀態詞彙的語意差別與版控邊界；「（二）gh-aw workflow 語料」提供 `safe-outputs` 用量、`.md` ↔ `.lock.yml` 漂移無守門員、與 `ci.yml`／`deploy.yml` 的共存面。
  - **code-structure.md** — `.github/workflows/` 的佈局與 `scripts/` 的跨分支狀態，界定新 workflow 的落點。
  - **business-overview.md** — 開發流程層資產盤點，確認本機制的使用者是開發流程本身而非產品終端使用者。
- **team-practices**：本 intent 的 scope 跳過 `practices-discovery`（`aidlc-state.md ## Scope Configuration` 列於 Stages to Skip），故無該站產出；團隊實踐改由 `aidlc/spaces/default/memory/team.md` 與 `project.md` 直接提供（branch／commit 規範、測試底線 A／B／C、三塊結構性盲區）。此缺席為 scope 設計而非缺漏。

## 意圖分析

**使用者要達成的目標，不只是要的功能**：讓「AI-DLC 內部走到哪」這件事**不需要有人記得**就會出現在 Project #16 上。三項成功指標中，真正的核心是**可信度**——看板一旦有一格是錯的，整塊板子就不再被拿來當依據（`intent-statement` 記載的既成事實：看板上有 item 標記為 In review，對應 issue 其實已關閉）。

因此本需求集的取捨一律偏向**「寧可不寫，不可寫錯」**：解析不到就跳過（FR-J2）、寫入前先回讀（FR-C1）、分岔就通報（FR-J1）、有爭議就暫停覆寫（FR-G3）。這個取向直接來自 [Q2]／[Q4]／[Q5] 三題的已選答案，也解釋了為什麼 `Backlog` 與 `Nice to have` 兩格刻意留給人工（FR-B1）。

**四類受益者對應到的可觀察結果**：開發者不再手動改狀態（FR-B）、協作者在看板上的操作算數不會被彈回（FR-G3）、只看看板的觀看者第一次看得到 intent 存在（FR-A1）、未來的自己能回溯（FR-E1 的 issue 留痕 ＋ FR-F1 的 stage 欄位）。

---

## 功能需求

### FR-A 綁定建立（← CAP-1、PU-1、[feas:Q8]）

| # | 需求 | 驗收判準（二元可判） |
| --- | --- | --- |
| FR-A1 | intent 誕生時，機制須在 Project #16 自動建立一則 issue、加入看板，並將 Status 設為 `Ready` | 新 intent 的 record 首次被推送後，Project #16 出現一則對應 issue，其 Status 欄位值為 `Ready` |
| FR-A2 | 建立的同時須把該 issue 的編號寫回 intent 的 record，之後一律查表，不得以標題語意推測 | record 內存在一個可機器讀取的欄位，其值等於 FR-A1 建立的 issue 編號；且後續任何一次同步的目標 issue 編號皆取自該欄位 |
| FR-A3 | 綁定編號與同步狀態檔的回寫，須推送到**觸發本次同步的那個分支**，commit 訊息含 `[aidlc-sync]` 標記 | 觸發分支上出現一個 commit，其訊息含 `[aidlc-sync]`，且其變更僅涉及 record 目錄下的綁定編號與 `sync-state.json` [F2=A] |
| FR-A4 | 帶 `[aidlc-sync]` 標記的 commit 不得再次觸發同步 | 對 FR-A3 產生的 commit，同步 workflow 不執行任何看板寫入（防迴圈第二道防線，[ADR-0012 §4]） |

### FR-B 正向狀態同步與對照表（← CAP-2、CAP-3、PU-3、PU-4、[Q1]）

**對照表是本機制的核心功能需求，本節即為其正式定義。** 依 [Q1=A]：

| record 側的觀察 | 看板 Status | 說明 |
| --- | --- | --- |
| intent 已誕生，尚無任何 in-scope stage 動過 | `Ready` | 對應 FR-A1 的初始值 |
| 任一 in-scope stage 的 checkbox 為 `[-]`（進行中）或 `[R]`（使用者退回、修訂中） | `In progress` | |
| 任一 in-scope stage 的 checkbox 為 `[?]`（gate 開著、等待人工核准） | `In review` | 此訊號**只存在於 checkbox**，top-level `Status` 沒有對應值 [V-4] |
| workflow 完成 | `Done` | |
| `## Runtime State` 的 `Parked` 欄位**非空** | **不覆寫**（凍結於最後已知值） | 優先於上列四條。`park` 寫 `Parked`／`Parked At Stage` 但**不動任何 checkbox**（`aidlc-state.ts:842-843`），故若不特判，被 park 的 intent 會被持續誤判為 `In progress`／`In review` [F4=A] |
| — | `Backlog`／`Nice to have` | **機制永不寫入**，保留給人工分類 |

| # | 需求 | 驗收判準 |
| --- | --- | --- |
| FR-B1 | 機制須依上表決定 Status，且**不得寫入 `Backlog` 或 `Nice to have`** | 對每一組上表的 record 狀態，機制產出的 Status 與表格一致；且任何情況下機制送出的 Status 值不為 `Backlog`／`Nice to have` |
| FR-B2 | 對照表的判定須為**決定性邏輯**（純 Actions 步驟），不得由 LLM 判斷 | 對照表的實作可在不呼叫任何 LLM 的情況下對給定的 record 輸出唯一 Status（`project.md ## Forbidden`：決定性的映射邏輯應優先放在純 Actions 步驟；[feas:R-3]） |
| FR-B3 | `[S]`（在 scope 內但被 `--stage`／`--phase` 跳過）與 `— SKIP`（不在 scope 內）**皆不影響 Status**，但兩者的差別不得被抹平 | 兩個只在 `[S]`／`— SKIP` 上不同的 record 產出相同的 Status；且兩者的差別出現在自訂欄位或 issue 受管區塊中，可被讀出 [V-3] |
| FR-B4 | 同步須由**任何分支的 push** 觸發，並由 PR 生命週期事件觸發；PR 事件的寫入優先於推送事件 | push 到任一分支（含 `danniel/**`）會觸發同步；當 PR 事件與 push 事件同時存在時，最終寫入的值來自 PR 事件 [Q3=D] [feas:Q9] |
| FR-B5 | PR 開啟時寫入 `In review`、PR 合併時寫入 `Done` 的既有決定，須與 FR-B1 的對照表**合併為單一判定**，不得成為第二套規則（「同一個判定函式」是維護性意圖，屬 code review 層級的檢查，非黑箱可驗證，故不放進 AC） | 對**相同的 record 訊號**，經 PR 事件觸發與經 push 事件觸發所得到的 Status **相同**；且同一輸入只產出一個 Status（無多重輸出） |
| FR-B6 | `Parked` 非空時，機制**不得送出該 item 的 Status 寫入**；暫停這件事改由 FR-F1 的自訂欄位表達（見 FR-F4），且該 intent 移出 FR-D2 的對帳補平範圍與 NFR-O2 的一致率分母 | 給定一個 `## Runtime State` 含非空 `Parked` 的 record，機制對其 item **不發出任何 Status 寫入請求**；`unpark` 清除該欄位後，下一次同步恢復依 FR-B1 判定 [F4=A] |

### FR-C 寫入前回讀確認（← CAP-6、PU-2、[feas:Q10]）

| # | 需求 | 驗收判準 |
| --- | --- | --- |
| FR-C1 | 每次寫入看板前，須先回讀目標 item 並與預期比對，不符即**中止寫入**並開 issue | 給定一個目標 item 的實際值與預期不符的情境，機制不送出寫入請求，且產生一則 issue 記錄該不符 |
| FR-C2 | 首次建立（FR-A1）時尚無可回讀的既有對象，須有一條**首建專屬**的檢查取代 FR-C1 | 首建路徑存在一項與 FR-C1 不同的檢查，且該檢查在目標脈絡錯誤時會中止建立（[feas:R-1] 指定於設計階段補上，本站確立其為需求而非選項） |
| FR-C3 | 對帳與事件同步可並行（見 NFR-P3），同時寫入同一 item 的防護由 FR-C1 承擔 | 兩條路徑同時對同一 item 寫入時，後到者的回讀比對會偵測到前者已寫入的結果，並依 **FR-C1 的唯一結果**處置：中止寫入並開 issue。本條不引入第二種分支——「重算後仍寫入」不是合格結果 [F3=A] |

### FR-D 排程對帳（← CAP-4、PU-6、[intent:Q6]）

| # | 需求 | 驗收判準 |
| --- | --- | --- |
| FR-D1 | 機制須每日執行一次對帳，掃描已綁定的 intent 並補齊差異 | 存在一個每日執行的排程觸發，其執行時段不與 `daily-digest`（`0 23 * * 1-5`）、`agentics-maintenance`（`37 0 * * *`）、`release-watch`（weekly）重疊 [Q7=A] |
| FR-D2 | 對帳的範圍**僅涵蓋已綁定且未 park 的 intent**，不碰既有未綁定的 item | 對帳的處理清單等於「record 內存在 FR-A2 綁定編號」**且**「`Parked` 欄位為空」的 intent 集合；既有 71 個未綁定 item 不被讀取也不被寫入 [scope:W-4] [intent:Q12]；已 park 者不進補平清單而改列「已暫停」清單 [F4=A] |
| FR-D3 | 在框架單次操作次數上限（C-T5）的實際值確認前，對帳一次只處理固定數量的 intent | 對帳的單次處理量存在一個明確的上限值，且該值可在不改動判定邏輯的情況下調整 [Q7=D] |
| FR-D4 | 對帳補平的次數須被記錄為可觀測指標 | 每次對帳產出一個可讀取的數值，表示本輪補平了幾個 intent 的落差 [Q3=D] |

### FR-E 失敗通報（← CAP-5、PU-5、[intent:Q9]）

| # | 需求 | 驗收判準 |
| --- | --- | --- |
| FR-E1 | 同步失敗須使 workflow 紅燈並自動開 issue | 給定一個寫入失敗的情境，workflow 的結束狀態為失敗，且產生一則 issue |
| FR-E2 | 對帳發現的不一致視為一種需要通報的失敗 | 對帳偵測到落差時，除補平外亦產生 FR-E1 所述的通報 |
| FR-E3 | 每則通報 issue 須能指出**是哪個 intent、哪個 stage、什麼時間** | issue 內文含 intent 的識別字、觸發當下的 stage 標識與 ISO 8601 時間戳（`intent-statement` 的第三項成功指標） |

### FR-F 細粒度進展外置（← CAP-7、PU-7、[scope:Q4] [scope:Q9]、[Q8]）

| # | 需求 | 驗收判準 |
| --- | --- | --- |
| FR-F1 | 機制須以**單一**看板自訂欄位承載目前 stage 的 slug ＋ 編號 | 對應 item 的該自訂欄位值形如 `requirements-analysis (2.3)`，且與 record 的 `Current Stage` 一致 [Q8=A] |
| FR-F2 | 該自訂欄位由機制自動建立；框架不支援建立欄位時退回人工建立，且此退路須被明確通報而非靜默 | 欄位不存在且無法自動建立時，機制產生一則說明「需人工建立欄位」的 issue，並跳過該欄位的寫入（其餘 Status 同步不受影響）[scope:Q9] |
| FR-F3 | FR-B3 的 `[S]`／`— SKIP` 差別須落在此欄位或 issue 受管區塊 | 存在一個可讀取的位置記錄該差別，且其內容能區分「被跳過的 EXECUTE stage」與「不在 scope 內的 stage」 |
| FR-F4 | `Parked` 非空時，該自訂欄位須寫出暫停事實與暫停當下的 stage | 對一個 `Parked` 非空的 record，其 item 的自訂欄位值含 `parked` 字樣與 `Parked At Stage` 的值（例如 `parked @ requirements-analysis`）；`unpark` 後下一次同步恢復 FR-F1 的一般格式 [F4=A] |

### FR-G 反向同步（← CAP-11、PU-10、[ADR-0013 §2]、[Q5]）

| # | 需求 | 驗收判準 |
| --- | --- | --- |
| FR-G1 | 機制須定時把看板端的狀態變更（含人工拖動卡片）拉回，並**開 PR** 呈現給人審，不得直接推 `ut` | 看板端發生人為狀態變更後，機制產生一個以 `ut` 為 base 的 PR；`ut` 上不出現未經 PR 的相關 commit [ADR-0012 §5] |
| FR-G2 | 反向同步**只寫入同步專用檔案，不得改動 AI-DLC 引擎擁有的欄位**（`aidlc-state.md` 的 `Status`／`Current Stage`／checkbox） | FR-G1 產生的 PR，其 diff 不含 `aidlc-state.md` 的任何一行 [Q5=D] |
| FR-G3 | 正向同步偵測到某 intent 有**未處理的反向紀錄**時，須暫停覆寫該 intent 的 Status，直到對應 PR 被合併或關閉 | 在反向 PR 開啟期間，正向同步不對該 item 送出 Status 寫入；PR 關閉或合併後恢復 [Q5=D] |
| FR-G4 | 防迴圈三道防線須同時成立：受管區塊內容雜湊比對、`[aidlc-sync]` 來源標記排除、狀態欄位單向 | 三項各自有可獨立驗證的實作；關閉任一項時存在一個可重現的迴圈情境 [ADR-0012 §4] |

### FR-H README 指路文字（← CAP-8、PU-9、[intent:Q11]）

| # | 需求 | 驗收判準 |
| --- | --- | --- |
| FR-H1 | repo 根目錄的 `README.md` 須增加**一段**文字，說明 Project #16 是需求清單的正本 | `README.md` 存在一段含 Project #16 連結的文字；README 的既有結構與總覽敘述未被改動 |

### FR-I 驗證層與憑證實測（← CAP-9、CAP-10、PU-0、PU-8、[feas:Q6]）

| # | 需求 | 驗收判準 |
| --- | --- | --- |
| FR-I1 | 對照表（FR-B1）須有 dry-run 斷言，輸出預期結果並比對，不觸及真實 API | 存在一組測試，對給定的 record 輸入斷言其輸出 Status，且執行時不發出任何對 GitHub API 的寫入請求 |
| FR-I2 | 須有對真實測試 item 的端到端驗證，涵蓋權限與 API 契約這類 dry-run 看不到的失敗 | 存在一個在 CI 中實際寫入並讀回斷言的流程，其失敗會使 workflow 紅燈 |
| FR-I3 | 憑證可行性須以最小可行呼叫先行實測，**不得以文件敘述代替驗證** | 存在一次實際執行並留下結果的呼叫，證明鑄出的憑證確實帶 ~~組織層~~ **個人帳號 Projects v2** 看板寫入權 [feas:R-7]（U-1／P-3）〔**經 ADR-0016 §1／§2 更正**（2026-08-31T00:37:44Z）：見 `../decisions/0016-credential-topology-and-pre1-amendments.md`〕 |
| FR-I4 | 框架單次操作次數上限的**實際值**與超限行為（截斷／報錯／靜默略過）須在 FR-I3 的同一輪實測中一併確認 | 實測結果記載了上限值與超限時的觀察行為 [Q7=D] [feas:R-6] |
| FR-I5 | 反向路徑（FR-G）的正確性判準與正向不同型，須有專屬的驗證設計 | 存在一組針對「該不該把這個看板變更寫回 record」的斷言，與 FR-I1／FR-I2 分開（U-7，收斂手段由 application-design 決定） |

### FR-J 資料源解析規則（跨切；← [Q2]、[Q4]、codekb `architecture.md`）

| # | 需求 | 驗收判準 |
| --- | --- | --- |
| FR-J1 | 「這個 intent 現在的狀態」一律以 `aidlc-state.md` 為準；`intents.json` 只用於列舉有哪些 intent | 判定 Status 的輸入只來自 record 的狀態檔；`intents.json` 的 `status` 欄不參與 Status 判定 [Q2=A] |
| FR-J2 | 偵測到 `intents.json` 與狀態檔分岔時，**照 FR-J1 寫入**，並另開一則 issue 記錄該 intent 與兩邊的值 | 給定一個分岔的 record（現況：`260802-last-login-column`），機制仍寫入且產生一則含兩邊值的 issue [Q2=A] [V-1] |
| FR-J3 | 解析不出必要欄位的 record 一律**跳過、不寫入看板** | 給定一個缺少 `## Stage Progress` 等區塊的 record（現況：`260802-default`），機制不對其產生任何看板寫入 [Q4=C] [V-5] |
| FR-J4 | stage 清單一律從各 record 的檔案本身解析，**不得寫死** | 給定兩個 stage 列集合不同的 record（現況：含／不含 `tcms-test-cases`），機制對兩者都正確判定，無錯位 [Q4=C] [V-6] |
| FR-J5 | 已知的結構性例外須以白名單明列；白名單外的無法解析者才進對帳報告 | 白名單中列有 `260802-default`；對帳報告的「無法解析」清單不含白名單項目 [Q4=C] |
| FR-J6 | 自行解析狀態檔時，須複製引擎 `getField()` 的語意（行錨定、全檔搜尋、第一個 match 即回傳、找不到回 `null` 而非空字串） | 對一個在正式欄位之前另有同名 `- **X**: ` 行的 record，機制讀到的值與引擎讀到的值相同（codekb `architecture.md`「欄位解析語意」） |

---

## 非功能需求

| # | 面向 | 需求 | 驗收判準 |
| --- | --- | --- | --- |
| NFR-P1 | 延遲 | 同步延遲上限為 **5 分鐘，自 record 被推送起算** | 自觸發 push 完成到看板 Status 更新的間隔不超過 5 分鐘（在無對帳並行的前提下，見 NFR-P3）[C-T8 經 Q3=D 重新定錨] |
| NFR-P2 | 頻率 | 對帳每日一次（見 FR-D1） | 同 FR-D1 |
| NFR-P3 | 並行 | **事件觸發的兩條路徑（PR、push）共用一個 concurrency group 且 `cancel-in-progress: false`；排程對帳自成一組**，兩者可並行 | 兩個事件觸發的執行不會互相取消而是排隊；對帳的執行不佔用事件路徑的佇列。NFR-P1 的 5 分鐘只受事件佇列影響 [Q7=C 經 F3=A 修訂] |
| NFR-P4 | 吞吐 | 在 C-T5 上限值確認前，對帳單次處理量須有明確上限（見 FR-D3） | 同 FR-D3 |
| NFR-S1 | IAM | （**再經 ADR-0015 §8 更正：權限集合實為四項**——第四項為 **Pull requests 寫入**，開 PR 與推分支在 GitHub 權限模型中是兩個獨立權限；驗收判準的「等於上述兩項」須同步改為四項。確認人為 Bolt 0 的 gate，且必須在憑證鑄造之前。見 `../decisions/0015-functional-design-upstream-amendments.md`。指標補於 2026-08-30T00:48:38Z）（**經 ADR-0014 更正**：權限集合為**三項**——組織層 Projects 讀寫 ＋ 用途受限的 repo 內容寫入 ＋ **Issues 寫入**。此處原文維持，更正內容與理由見 `../decisions/0014-permission-set-and-alert-convergence.md`） 機制需要的權限為**組織層 Projects 讀寫 ＋ repo 內容寫入**；後者的用途**限於** record 目錄下的綁定編號與 `sync-state.json`（FR-A3）、以及開 PR（FR-G1） | ~~憑證實際被授予的權限集合等於上述兩項，無額外授予。~~**見下方「已解消的矛盾 R-1」**〔**經 ADR-0016 §2 改述**（2026-08-31T00:37:44Z）：無論取兩項、三項或四項，本判準在新憑證拓樸下**結構性不可滿足**——`repo` scope 必然帶來遠多於列舉項的權限。改為：**憑證所需的 scope 集合為 `project` ＋ `repo`（或 `public_repo`，待 PRE-1-c）兩項，且不含其餘額外 scope**；`repo` 的過度授予改列為**已知殘餘風險**，不再偽裝成可通過的驗收項。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`〕 |
| NFR-S2 | IAM | Projects 憑證存為**獨立 secret**，不重用既有憑證；同步 workflow 與其他 agentic workflow 不共用 token | secrets 清單中該憑證為獨立項；其他 workflow 的設定不引用它 [ADR-0012 §5，ADR-0013 明示維持] |
| NFR-S3 | 機密 | 版控中不得留存任何憑證字串 | `python3 scripts/validate_repo_contract.py` 通過 [C-R3] |
| NFR-S4 | Encryption | 傳輸層由 GitHub API 的 HTTPS 承擔；靜態機敏資料僅有上述憑證，由平台 secret 機制保管；機制不自行儲存任何機敏資料 | 機制不新增資料庫、不落地任何含機敏內容的檔案 [feas:ADR-0006 判定表] |
| NFR-S5 | Network exposure | **不適用**：不新增對外服務、不開埠、不新增可被外部存取的端點；全部行為是託管執行環境對 GitHub API 的出站呼叫 | 新增的檔案不含任何監聽或端點宣告 [feas:ADR-0006 判定表] |
| NFR-S6 | Audit logging | 每次 Status 變更皆可回答「哪個 intent、哪個 stage、什麼時間」 | 見 FR-E3；且成功的寫入亦在 workflow log 中留下同樣三項資訊 [intent:Q3] |
| NFR-O1 | 可觀測 | 「對帳補平次數」為可讀取的指標（見 FR-D4） | 同 FR-D4 |
| NFR-O2 | 一致率 | （**經 ADR-0015 §9 標記：「目標為 0」在白名單記錄存在期間結構性不可達**——U-7 的分子含 `unparseable`／`whitelisted`，而 `260802-default` 已核實在白名單內（FR-J5），使分子恆 ≥ 1。二選一：目標改為「分子中不含 `mismatch` 類」，或 `whitelisted` 退出分子。確認人為 Bolt 2 的 gate。此處原文維持，見 `../decisions/0015-functional-design-upstream-amendments.md`。指標補於 2026-08-30T00:48:38Z）一致率的分母 = 已綁定的 intent − 有未處理反向紀錄者 − **`Parked` 非空者**；分子 = 其中看板與 record 不一致者，目標為 **0** | 對帳輸出一個依此定義計算的數值，且「等待人工裁決」與「已暫停」**兩份清單各自獨立列出** [F1=A] [F4=A] [intent:Q12] |
| NFR-C1 | 共存 | 既有 CI 四道關卡（`repo-contract`／`frontend`／`backend`／`docker-build`）與 `deploy.yml` 不得因本變更而破壞 | 本變更後 `ci.yml` 的四個 job 與 `deploy.yml` 的行為與變更前相同 [C-O4] |
| NFR-C2 | 共存 | 新 workflow 的 `name`（＝ body H1）須與現有 11 支不同 | `.github/workflows/` 下無重複 `name`（codekb `architecture.md`「共存面」表） |
| NFR-M1 | 可維護 | 新增 workflow 繼承既有的 `.md` ↔ `.lock.yml` 漂移風險（改了 `.md` 未重編則 CI 全綠但行為維持舊的），此風險須被明確承接而非忽略 | 需求文件記載此風險並指派收斂落點（見 OQ-4）；本站不裁定收斂手段 |

---

## 約束

沿用 `constraint-register` 的 C-T／C-O／C-R 全部條目，**本站修訂與新增如下**：

| # | 約束 | 本站處置 |
| --- | --- | --- |
| C-T6 | 狀態欄位維持既有 6 個選項不變 | **維持**。FR-B1 只寫其中四格（`Ready`／`In progress`／`In review`／`Done`），另兩格留給人工 |
| C-T8 | 同步延遲上限推送後 5 分鐘 | **重新定錨**為「自 record 被推送起算」，並限定於「無對帳並行」的前提（NFR-P1、NFR-P3）。變更理由：codekb 查證確認遠端只看得到已 commit 的內容，原措辭在 record 未推送時不可判定 [Q3=D] |
| C-T7 | 不得以 repo 內新增的實作程式承載 | **維持**。FR-B2 的「決定性邏輯」須落在純 Actions 步驟或 gh-aw 的非 LLM 環節，不得新增 `scripts/` 下的程式 |
| C-N1（新） | 同步狀態檔置於 `<record>/sync-state.json`，**不得以 `.aidlc-` 開頭** | 新增。理由：`.gitignore:52` 的 `aidlc/spaces/*/intents/*/.aidlc-*` 會擋掉 ADR-0012 §4 指定的路徑，而該檔需進版控才能跨 runner 比對 [Q6=A] [V-2] |
| C-N2（新） | 不得以修改 `.gitignore` 或任何 upstream 框架檔來解決 C-N1 | 新增。`project.md ## Forbidden`：專案規則不得寫進會被框架升級整批覆蓋的檔案 |
| C-N3（新） | 反向同步的 PR 不得含 `aidlc-state.md` 的任何變更 | 新增。理由：狀態轉移為引擎所有，外部改寫會與狀態機打架且 audit 無對應事件（FR-G2）[Q5=D] |

---

## 已解消的矛盾

`phases/inception.md` 要求「不得把未解的矛盾往下傳，須明確 surface 並 resolve」。本站發現三處，處置如下：

**R-1 — `feasibility-assessment` 的 ADR-0006 IAM 判定原文已不成立。**
該表 IAM 列寫「權限限縮為組織層看板讀寫，**不索取 repo 內容寫入權**」。但三項已核可決定各自都需要寫 repo：CAP-1 寫回 issue 編號（[feas:Q8]，**與該 IAM 判定同屬 feasibility 一站，該站自身即已內含此矛盾**）、Q6=A 的 `sync-state.json` 進版控、ADR-0013 §2 的反向同步開 PR；[F2=A] 再加上寫回觸發分支。
**處置**：NFR-S1 已改寫為**加了適用前提的版本**（組織層 Projects 讀寫 ＋ 用途受限的 repo 內容寫入），使字面不再衝突。**（後續：ADR-0014 再補入第三項 Issues 寫入——本段記載的是 R-1 當時的處置，非最終集合；現行集合為三項，見 `../decisions/0014-permission-set-and-alert-convergence.md`。）****收斂手段列為 application-design 的開放決策**（見 OQ-1），與 `initiative-brief` U-6 已指派的「IAM 面重新判定」合流。上游 artifact 依既有紀律不回改。

**R-2 — [Q7=C] 的字面被 [F3=A] 修訂。**
Q7=C 原文為「三條路徑共用一個 concurrency group」；F3=A 改為「事件觸發兩路徑共用一組、對帳自成一組」。
**處置**：NFR-P3 已以 F3=A 的形式寫入。**下游一律以 NFR-P3 為準，不得引用 Q7=C 的「三路徑共用」字面。**

**R-3 — ADR-0012 §4 指定的同步狀態檔路徑與它自己的「需進版控」要求矛盾。**
**處置**：C-N1 已指定新路徑。ADR-0012 §4 需要一條修訂註記（見 OQ-5），實際落筆屬後續 stage。

---

## 假設

| # | 假設 | 待驗證者 |
| --- | --- | --- |
| A-1 | ~~組織層具備安裝 GitHub App 的管理權限，且安裝流程不受組織政策阻擋；未經實際嘗試~~ **已判定為不適用**〔**ADR-0016 §1**（2026-08-31T00:37:44Z）：`opendiamonds` 為個人帳號（實測 `GET /orgs/opendiamonds` → 404），**無組織**可安裝 App、亦無組織政策可阻擋；憑證身分已改為擁有者帳號 token，GitHub App 路徑整條退場。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`〕 | ~~P-1，併入 FR-I3 的實測~~ **N/A** |
| A-2 | 框架承載 App 識別碼的變數名稱與其文件描述不一致（名稱指向應用程式識別碼、敘述指向用戶端識別碼），實作時需逐一嘗試確認 | FR-I3 |
| A-3 | 框架的看板更新行為（依欄位名稱設定單選欄位、名稱不分大小寫）在本 repo 的實際執行環境中如文件所述；~~目前只查證文件、未實測~~ **已實測，部分推翻**〔**ADR-0016 §4.2**（2026-08-31T00:37:44Z）：「依名稱、不分大小寫」是**框架便利層**行為，**非平台行為**。GraphQL 層實測——`value:{text:"In progress"}` 回 `VALIDATION: Did not receive a single select option Id...`；`value:{singleSelectOptionId:"07486f86"}` 成功；大小寫變體回 `VALIDATION: The single select option Id does not belong to the field`。走直接 GraphQL 時，每個單選欄位需**額外一次讀取**做 per-project 的 name→id 解析。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`〕 | FR-I3 |
| A-4 | 看板的狀態欄位識別碼在實作期間保持穩定；若有人手動改動欄位定義，綁定與映射需重新確認 | 持續 |
| A-5 | 框架支援自動建立看板自訂欄位；安全輸出清單中未見此型別，不可行則依 FR-F2 退回人工建立 | U-2／P-4 |
| A-6 | 「未處理的反向紀錄」的偵測方式（FR-G3）假設反向 PR 的開關狀態可被正向同步讀取；未驗證 | application-design |
| A-7 | 新增自訂欄位會使既有 71 個 item 該欄位為空；此空值是否對看板使用者造成困擾未經確認 | 未指派 |
| A-8 | FR-A3 寫回觸發分支的做法，假設同步身分對 feature 分支有寫入權且不受分支保護規則阻擋；未驗證 | application-design，與 OQ-1 合流 |

---

## 範圍外

| # | 排除項 | 來源 |
| --- | --- | --- |
| OOS-1 | 跨 repo 支援：其他 repo 的 intent 也同步到本看板 | `scope-document` W-2 |
| OOS-2 | 自動關閉 issue：完成時除設 `Done` 外亦關閉對應 issue | `scope-document` W-3 |
| OOS-3 | 既有 71 個項目的一次性對正（歷史漂移修正） | `scope-document` W-4；FR-D2 據此限定對帳範圍 |
| OOS-4 | `story → Issue` 的映射層級 | ADR-0013 §1：保留為未來方向，本次不涉及 story 層 |
| OOS-5 | Wiki 單向鏡像 | ADR-0012 §3：決定維持，但不在本 intent 範圍 |
| OOS-6 | 修改看板既有的 6 個 Status 選項 | C-T6 |
| OOS-7 | 在 `.claude/` 下新增任何檔案、或以 stage／hook 觸發同步 | ADR-0012 §6 硬約束 |
| OOS-8 | 看板互動的其餘項目（排序、篩選等）——本次唯一新增的看板互動是自訂欄位的呈現 | `scope-document`；`project.md ## Corrections`（同家族排除項須兩處明寫） |

---

## 待決問題

以下為本站**明確指派而非被動記載**的開放決策。每項都標明落點與必須產出的決定。

| # | 待決事項 | 指派落點 | 必須產出的決定 |
| --- | --- | --- | --- |
| OQ-1 | **如何把 repo 內容寫入權收斂到最小**（見 R-1、A-8）。~~GitHub App 無路徑層級的權限限制，故收斂只能靠其他手段~~〔**經 ADR-0016 §7 改寫**（2026-08-31T00:37:44Z）：**維持開放決策**，但收斂目標由「收斂到 record 目錄」（已確定無機制可達——App 路徑層級限制不存在、Rulesets 因 repo 為 public 且非 org 所有而 `422`、分支保護不涵蓋 feature 分支）改為**可達的次佳目標**：以 `public_repo` 取代 `repo`，把爆炸半徑限制在公開 repo。**待 PRE-1-c 實測**（`public_repo` 的文件原文未逐字涵蓋 issues 與 pull requests，不得憑推定採用）。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`〕 | **application-design**（與 U-6 合流） | 一個具體的收斂方案，並重跑 ADR-0006 四面向判定 |
| OQ-2 | **反向路徑的驗證落點與正確性判準**（FR-I5） | **application-design**（U-7） | 一組與正向不同型的斷言設計 |
| OQ-3 | **CAP-11 的可行性補評估**——本 intent 的 feasibility 未涵蓋 GitHub → repo 路徑 | **application-design**（U-6） | 技術可行性表、風險與四面向判定各補一列 |
| OQ-4 | **`.md` ↔ `.lock.yml` 編譯漂移的守門員**（NFR-M1）。材料已在檔案裡（`frontmatter_hash`／`body_hash`），但目前無任何 CI 檢查 | **ci-pipeline**（U-4） | 是否新增檢查，以及若不新增的理由 |
| OQ-5 | **ADR-0012 §4 的修訂註記**（見 R-3） | **construction**——與 `sync-state.json` 實際落地於**同一個 PR**，使註記與它所描述的路徑變更同進同出，可在該 PR 的 review 上被確認 | 加在 ADR-0012 §4 的註記文字：指明同步狀態檔路徑已由 ADR-0013 之後的 requirements-analysis 改為 `<record>/sync-state.json`，理由是原路徑被 `.gitignore` 排除而與該節「需進版控」的要求自相矛盾 |
| OQ-6 | **十一項全 Must 且宣告一次做完，與短生命週期分支實務在 deploy-on-merge 下的張力** | **delivery-planning**（U-5） | Bolt 切分方案 |
| OQ-7 | **PR #508 已合併的 `scripts/aidlc_sync_*.py` 三支腳本**與 ADR-0013 §3 及 `project.md ## Forbidden` 的衝突（「既有豁免／遷移到 gh-aw／收窄規則」三者擇一） | **使用者裁決**（本站與 reverse-engineering 皆只記載、不裁定） | 三者擇一的明確決定 |
| OQ-8 | **A-7**：新增自訂欄位（FR-F1）使既有 71 個未綁定 item 的該欄位為空 | **application-design**（與 FR-F／PU-7 的欄位建立同屬一組決定） | 空值是否需要處理；若需要，列出補值方式與其與 OOS-3「不做既有 71 項一次性對正」的邊界（補欄位值不等於對正 Status，兩者須分開判定） |

---

## Revision 1（2026-08-24，reviewer iteration 1 findings）

`aidlc-product-lead-agent` 於 iteration 1 判定 NOT-READY（3 Major + 2 Minor）。五項全數處理，**未回跳上游、未重開已核可的 approval gate**：

| Finding | 嚴重度 | 處置 |
| --- | --- | --- |
| 1 — FR-B 對照表漏 `Parked` 訊號 | Major | **新增決定 [F4=A]**（另行取得人工確認，未沿用先前的 Looks correct）：對照表新增 `Parked` 非空一列（不覆寫、優先於其餘四條）、新增 FR-B6、FR-F4，並修訂 FR-D2 與 NFR-O2 將已 park 者移出對帳補平範圍與一致率分母。本站已獨立複驗 `aidlc-state.ts:842-843`／`:859-860` 確認該欄位為真實機制且 6 個 record 皆未設過（機制存在、尚未發生） |
| 2 — FR-C3「中止**或重算**」二元不可判 | Major | AC 改為只認 FR-C1 的唯一結果（中止＋開 issue），明文「重算後仍寫入不是合格結果」。採 reviewer 建議的第一支：`重算` 原意即「重讀後仍依 FR-C1 判定」，非第二種結果 |
| 3 — OQ-8 落點「未指派」且產出欄自我指涉 | Major | 落點改為 **application-design**（與 FR-F／PU-7 的欄位建立同組），產出改寫為具體物並補上與 OOS-3 的邊界 |
| 4 — OQ-5 落點不具體 | Minor | 改為 **construction，與 `sync-state.json` 同一個 PR**，並寫出註記文字要說什麼 |
| 5 — FR-B5 的 AC 混合黑箱行為與程式碼結構 | Minor | AC 改為純黑箱版（兩條觸發路徑對相同 record 訊號得到相同 Status）；「同一個判定函式」的維護性意圖移至需求本文並註明屬 code review 層級 |

**reviewer 另記錄但不構成本站缺陷的觀察**（本站接受並在此留痕）：上游 `feasibility-assessment` 的「12 組既有代理式工作流程」疑似多算——`ls .github/workflows/*.md` 實測為 11 個 gh-aw workflow，另有 4 個非 gh-aw 的純 Actions workflow（`agentics-maintenance.yml`／`ci.yml`／`copilot-setup-steps.yml`／`deploy.yml`）。本站的 V-8 與 NFR-C2 用的是 11，內部一致；上游數字的校正留給下一輪 codekb 或 practices-discovery，**本站不回改已核可的上游 artifact**。

## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-23T23:10:06Z
**Iteration:** 2

### 機械檢查（sensor 重跑，本輪）

```
bun .claude/tools/aidlc-sensor.ts fire required-sections --stage requirements-analysis --output-path .../requirements.md                    → exit 0
bun .claude/tools/aidlc-sensor.ts fire upstream-coverage --stage requirements-analysis --output-path .../requirements.md                    → exit 0
bun .claude/tools/aidlc-sensor.ts fire required-sections --stage requirements-analysis --output-path .../requirements-analysis-questions.md → exit 0
bun .claude/tools/aidlc-sensor.ts fire upstream-coverage --stage requirements-analysis --output-path .../requirements-analysis-questions.md → exit 0
```

四次執行前後比對 `.aidlc-sensors/` 目錄內容：執行前後皆只有 `intent-capture/claim-sources-{b6e703bf,c10dad1d}.md` 兩份既有陳舊記錄（intent-capture 站的舊產物，與本站無關），本輪四次執行未新增任何 `requirements-analysis/` 失敗檔，四項全過。

### Iteration 1 findings 逐項驗證（回檔案核對實際改動，非轉引 Revision 1 自述）

| # | 原嚴重度 | 實際改動（逐字核對） | 判定 |
|---|---|---|---|
| 1 — FR-B 對照表漏 `Parked` 訊號 | Major | FR-B 對照表新增一列（`requirements.md:55`）：「`## Runtime State` 的 `Parked` 欄位非空 → 不覆寫（凍結於最後已知值），優先於上列四條」。新增 FR-B6（:65，AC：`Parked` 非空時「不發出任何 Status 寫入請求」，`unpark` 後「恢復依 FR-B1 判定」）與 FR-F4（:99，AC：自訂欄位值含 `parked` 字樣與 `Parked At Stage` 值）。FR-D2（:80）與 NFR-O2（:154）同步改寫，明確把已 park 者移出對帳範圍與一致率分母，並與 F1 的「等待人工裁決」清單分列為獨立的「已暫停」清單，不互相混淆。**我獨立重讀了程式碼**（不轉引 requirements.md 的引用）：`aidlc-state.ts:842-843`（`handlePark` 寫 `Parked`／`Parked At Stage`，只動 `## Runtime State`，不碰任何 checkbox 欄位）、`:859-860`（`handleUnpark` 清除同兩個欄位）——引用行號精確符合，且 `handlePark` 對 `Status === "Completed"` 會直接 `error()` 拒絕，故不存在「Parked 與 Done 同時成立」的競態，「優先於上列四條」不產生新歧義。逐一 `grep "^\- \*\*Parked\*\*"` 6 個 record 的 `aidlc-state.md`，全部落空，與 Revision 1 表「6 個 record 皆未設過」的宣稱一致。 | **Resolved** |
| 2 — FR-C3「中止或重算」二元不可判 | Major | `requirements.md:73` 現讀：「後到者的回讀比對會偵測到前者已寫入的結果，並依 **FR-C1 的唯一結果**處置：中止寫入並開 issue。本條不引入第二種分支——『重算後仍寫入』不是合格結果」。「或重算」字樣已完全移除，AC 只剩單一可觀察結果，與 FR-C1（:71）的「中止＋開 issue」一致，QA 可寫出唯一的 pass/fail 斷言。 | **Resolved** |
| 3 — OQ-8 落點「未指派」且產出欄自我指涉 | Major | `requirements.md:236` 現讀：指派落點欄為「**application-design**（與 FR-F／PU-7 的欄位建立同屬一組決定）」，產出欄為「空值是否需要處理；若需要，列出補值方式與其與 OOS-3『不做既有 71 項一次性對正』的邊界（補欄位值不等於對正 Status，兩者須分開判定）」。落點具體、產出為可交付物而非「決定要不要決定」的自指句，且與 OOS-3 的邊界已明寫。 | **Resolved** |
| 4 — OQ-5 落點不具體 | Minor | `requirements.md:233` 現讀：落點欄改為「**construction**——與 `sync-state.json` 實際落地於**同一個 PR**」，產出欄寫出具體註記文字（指明路徑變更緣由）。 | **Resolved** |
| 5 — FR-B5 的 AC 混合黑箱行為與程式碼結構 | Minor | `requirements.md:64` 現讀：AC 為「對**相同的 record 訊號**，經 PR 事件觸發與經 push 事件觸發所得到的 Status **相同**；且同一輸入只產出一個 Status（無多重輸出）」——純黑箱、外部可觀察。原「同一個判定函式」的維護性意圖移到需求本文並註明「屬 code review 層級的檢查，非黑箱可驗證，故不放進 AC」，未殘留在 AC 裡。 | **Resolved** |

五項全數確認為真實修復，非僅 Revision 1 自述；FR-B6／FR-D2／NFR-O2 三處對 park 語意的描述互相一致（同一個排除集合、同一個「已暫停」清單措辭），未見交叉引用漂移。

### 本輪新發現（修正過程本身引入，非 iteration 1 殘留）

| # | 嚴重度 | 位置 | 問題 | 建議 |
|---|---|---|---|---|
| 6 | Major | `requirements-analysis-questions.md`（F4 與 `## Consolidated Summary Confirmation`） | 本 stage 檔（`.claude/aidlc-common/stages/inception/requirements-analysis.md` Step 10）明文為 MANDATORY PRE-GENERATION STOP：「After **every original and follow-up** answer is filled, append or update a `## Consolidated Summary Confirmation` entry」，且「Do NOT create `requirements.md` until the confirmation entry contains the user's explicit `Looks correct` answer」。F4（回應本輪 iteration 1 finding 1 而新增，`[Answer]: A  <!-- 2026-08-23T23:03:39Z · Mode: guided · reviewer iteration 1 findings -->`，`requirements-analysis-questions.md:261`）是一則貨真價實的 follow-up 答案，且是 FR-B6／FR-F4／FR-D2／NFR-O2 四條需求的直接依據。但檔案中緊接其後的 `## Consolidated Summary Confirmation` 區塊（:275-312）**完全未更新**：其「已答清單」表仍只列 Q1～Q8、F1～F3 共 11 題，標題逐字寫「以下是本 stage **十一題**的完整已答清單」，不含 F4；其 `Looks correct` 確認時間戳為 `2026-08-23T15:45:52Z`——**早於** F4 的作答時間戳（`23:03:39Z`）近 7.5 小時，物理上不可能涵蓋 F4。等同於：requirements.md 依據 F4 的答案改寫了四條需求，但檔案自己宣稱的「完整已答清單」與其 `Looks correct` 確認，都是在 F4 存在**之前**取得的。這與 `project.md ## Corrections`（learned 2026-08-23, approval-handoff:260823-rev1-c1）點名的形狀同構：「既有的人工確認只涵蓋它作答當下存在的清單；修訂新增的項目必須另行取得確認，不得沿用舊確認寫成『已接受』」——F4 本身雖有直接、獨立的 `[Answer]: A`（形式合規：A–D＋X 選項齊全、`Mode: guided` 標記與其餘題目一致，不是被跳過或臆造的答案），但它從未被納入本 stage 自訂的「整批彙總後才准產出/改寫 artifact」這道機制性關卡，使得該關卡對 requirements.md 現況的「完整」宣稱失真。此問題由本輪修正過程新引入（F4 在 iteration 1 時尚不存在），非 iteration 1 殘留。 | 在 `## Consolidated Summary Confirmation` 的已答清單新增 F4 一列，標題改為「十二題」，並重新走一次 `Looks correct` 確認（哪怕答案內容不變，也要讓確認的時間戳晚於 F4，使宣稱與事實一致）。成本低（一列表格＋一次確認），不涉及內容改寫。 |

### 是否構成 NOT-READY

依 `## Verdict Rules`：零 Critical；Major 計數為 1（finding 6，且有清楚且低成本的補救方式——補一列表格並重新取得一次 `Looks correct`，不需要改動任何需求本文或重開任何上游 gate）；Minor 不設限。1 Major（有清楚補救）未達 `>2 Major` 的 NOT-READY 門檻，故判定 **READY**，並在下方 Summary 明確標出 finding 6 建議在人工核准關卡前一併補上。

### 本輪嘗試推翻但未成立的角度（如實記錄，避免顯得只做確認式覆核）

- **`Parked` 優先序是否與既有四條產生新歧義**：查證 `handlePark` 對 `Status === "Completed"` 直接拒絕（見上），故「已完成」與「已 park」不可能同時成立；「優先於上列四條」在窮舉的四種既有狀態下皆無交集衝突。不成立。
- **FR-B6／FR-F4 是否存在恆真（不可能失敗）判準**：兩者 AC 皆為「不得發生某動作」／「必須含特定字樣」型態，皆可用一個刻意違反的實作使其判假（分別是：仍送出 Status 寫入請求；自訂欄位不含 `parked` 字樣），故非恆真。不成立。
- **FR-D2／NFR-O2／FR-B6 是否互相矛盾**：三處排除集合定義（綁定編號存在 ∧ Parked 為空）逐字一致，「已暫停」清單措辭在 FR-D2 與 NFR-O2 兩處相同，未見漂移。不成立。
- **FR-C3 改寫後是否仍與 FR-C1 留下第二分支**：FR-C3 現況直接引用「FR-C1 的唯一結果」且明文排除重算分支，未留第二種合格結果。不成立。
- **編號／交叉引用是否有未同步之處**：`grep` 全檔 `FR-B[0-9]`／`FR-D2`／`NFR-O2`／`FR-F4`／`OQ-8`／`OQ-5` 等識別碼，「上列四條」「四格」等計數描述與其鄰近表格的實際列數/格數逐一核對相符，未發現殘留舊編號或舊計數。不成立。
- 上述四個角度確實嘗試推翻過，均未能成立；唯一站得住的新問題是 finding 6（Consolidated Summary Confirmation 未同步更新），其性質是**確認機制的完整性**問題，不是需求內容本身的錯誤。

### Summary

Iteration 1 的 3 Major＋2 Minor 全數驗證為真實修復（逐項回檔案核對改動，非採信 Revision 1 自述）：FR-B6／FR-F4 補上 `Parked` 訊號且與 FR-D2／NFR-O2 一致；FR-C3 的「中止或重算」二元不可判已消除；OQ-8／OQ-5 的落點與產出物已具體化。`Parked` 機制的引用（`aidlc-state.ts:842-843`／`:859-860`）與「6 個 record 皆未設過」的宣稱皆已獨立複驗屬實。本輪另發現一項修正過程本身新引入的問題（finding 6）：`requirements-analysis-questions.md` 的 `## Consolidated Summary Confirmation` 未隨 F4 的新增而更新，其「十一題完整已答清單」與 `Looks correct` 確認時間戳皆早於 F4 作答，使該關卡對現況的「完整」宣稱失真——這是 stage 自訂 MANDATORY 步驟的執行落差，不是需求內容錯誤，F4 本身有獨立、合規的人工作答。判定 READY，但建議在人工核准關卡前把 finding 6 的補救（補列＋重新確認）一併做掉，使 Q&A 檔的確認紀錄與 requirements.md 現況真正對齊。
