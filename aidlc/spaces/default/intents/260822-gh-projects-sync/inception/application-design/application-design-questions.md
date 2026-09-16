# Application Design — 設計計畫與問題

<!-- Stage: application-design（Inception 2.5）· Record: 260822-gh-projects-sync
     來源標籤：[req:*] 指 requirements.md；[US:S-n AC m] 指 stories.md；[kb:*] 指 codekb；
     [OQ-n]／[US-OQ-n] 指上游指派給本站的待決事項。 -->

## 上游輸入

- **requirements.md**（Revision 1，已核可）：40 FR、15 NFR、6 約束、8 假設、8 待決問題。
- **stories.md**（Revision 1，已核可）：4 personas、11 則故事、65 條 AC、全域 DoD、PRE-1、US-OQ-1～7。
- **codekb**（基準 `9307dbc`）：`architecture.md` 的「開發流程層架構」三節、`component-inventory.md` 的 11 支 gh-aw 盤點、`dependencies.md`。
- **team-practices**：scope 跳過 `practices-discovery`，由 `memory/team.md` 與 `project.md` 直接提供。

## 本站要產出決定的九項（上游明確指派）

| # | 事項 | 來源 |
| --- | --- | --- |
| OQ-1 | repo 內容寫入權如何收斂到最小 ＋ 重跑 ADR-0006 四面向判定 | requirements |
| OQ-2 | 反向路徑的驗證落點與正確性判準 | requirements |
| OQ-3 | CAP-11（反向同步）的可行性補評估 | requirements |
| OQ-8 | 新增自訂欄位使既有 71 個未綁定 item 該欄位為空 | requirements |
| US-OQ-1 | 重複失敗的通報收斂手段 ＋ 補回一條二元可判的 AC | user-stories |
| US-OQ-3 | 「機制刻意不寫」在看板側的可感知形式 | user-stories |
| US-OQ-4 | 自訂欄位承載三種事實時的格式與長度上限 | user-stories |
| US-OQ-5 | S-10 AC 2 測試 item 的歸屬 | user-stories |
| US-OQ-6 | fixture 機制的建立方式與測試用綁定編號 | user-stories |
| US-OQ-7 | 決定性映射邏輯的承載形式（使 S-10 AC 1 有可驅動的對象） | user-stories |

## 已由上游定案、不重問

| 事項 | 出處 |
| --- | --- |
| Status 對照表六列（含 `Parked` 優先覆寫、兩格永不寫入） | [req:FR-B] 表格，[Q1=A][F4=A] |
| 反向同步只寫同步專用檔、不動 `aidlc-state.md`、開 PR 給人審 | [req:FR-G1～G4]，[Q5=D]，ADR-0013 §2 |
| 同步狀態檔路徑 `<record>/sync-state.json`（不得以 `.aidlc-` 開頭） | [req:C-N1]，[Q6=A] |
| 對帳每日一次、避開三支既有排程 | [req:FR-D1]，[Q7=A] |
| 自訂欄位為**單一**欄位、承載 stage slug ＋ 編號 | [req:FR-F1]，[Q8=A] |
| OQ-7 三擇一 = **B（遷移）**：`scripts/aidlc_sync_*.py` 三支遷移到 gh-aw／Actions | 使用者裁決 2026-08-24T04:02:35Z |
| `project.md ## Forbidden` 的邊界 = **無人值守的自動化**，以觸發來源判定；stage 觸發的工具不在此限 | 使用者裁決 2026-08-24T04:02:35Z |

## 本站查證到、且與已核可需求衝突的事實（出題前的唯讀查證，非來源登錄）

**V-1（衝突）**：`NFR-P3`／[US:S-2 AC 11] 要求「事件觸發的兩條路徑（PR、push）共用一個 concurrency group 且 `cancel-in-progress: false`」。但 [kb:architecture.md] 實測記載 **gh-aw 的 concurrency group 由編譯器依觸發型別產生，作者寫不了**：PR 觸發 → `gh-aw-<workflow>-<pr number||ref||run_id>` 且 **`cancel-in-progress: true`**；push 觸發 → `…-<ref||run_id>`、無 cancel；schedule → `gh-aw-<workflow>`、無 cancel。**單一 workflow 同時宣告 `pull_request` 與 `push` 時編譯器產生什麼，codekb 未記載、本站未實測**——但至少 PR 那一型與 NFR-P3 直接牴觸。

**V-2**：`.md` frontmatter 的 `permissions:` **只套用到 `agent` job**；實際執行寫入的是 `safe_outputs` 與 `conclusion` 兩個 job，其權限由編譯器**依 `safe-outputs:` 的宣告**注入。[kb] 明文把「在 `.md` 寫 `projects: write`」列為新作者最容易踩的坑。

**V-3**：本 repo 11 支 workflow **沒有一支寫過 Projects v2**，沒有任何 `projects` toolset 或相關 safe-output 的使用先例。ADR-0013（2026-08-23 查官方文件）確認框架有 `update-project`／`create-project`／`create-project-status-update` 三個 safe-output 與供讀取的 `projects` toolset——**該事實來自 ADR-0013，非本 repo 語料**。

**V-4**：`.md` ↔ `.lock.yml` 的 `frontmatter_hash`／`body_hash` 涵蓋的是 `.md` 兩半，**可偵測「改了 `.md` 沒重編」，偵測不到「該用新版編譯器重編」**；且**全 repo 無任何守門員**。

**V-5**：`ci.yml` 的 `concurrency: ci-CI-<ref>` ＋ `cancel-in-progress: true` ＋ `on: pull_request`（無分支過濾）。[US:S-1 AC 7] 已把「回寫 commit 不得取消既有 CI run」列為 AC。

**V-6**：gh-aw 一律 GitHub-hosted runner，不佔用 `deploy.yml` 的 self-hosted runner。

---

## 問題


### Q1. 承載形式：這套機制要跑在 gh-aw、純 Actions，還是兩者分工？（US-OQ-7 ＋ V-1）

這是本站最大的一個決定，且它同時決定 US-OQ-7（S-10 AC 1 的斷言有沒有可驅動的對象）與 NFR-P3 能不能被滿足。

A. **全部走純 Actions workflow**：正向同步、對帳、反向同步三條路徑都是手寫 workflow，Projects v2 以 `gh` CLI／GraphQL 直接呼叫；決定性映射邏輯放在 `.github/actions/<name>/action.yml` 的 composite action。看得到的效果：①concurrency group 完全由我們寫，NFR-P3 可照字面滿足 ②全路徑零 LLM，全域 DoD 的「全路徑無 LLM」與 FR-B2 自動成立 ③composite action 可被一支測試 workflow 以 fixture 驅動，S-10 AC 1 有對象 ④單一憑證路徑。代價：Projects v2 的 GraphQL 呼叫**本 repo 無先例**（V-3），要自己處理分頁、欄位 id 查詢與錯誤碼；`safe-outputs` 的便利（自動注入權限、自動開 issue）全部要自己寫。

B. **分工：正向同步＋對帳走純 Actions，反向同步走 gh-aw**：反向路徑用 `create-pull-request`／`update-project` 等 safe-output。看得到的效果：反向路徑省下手寫 PR 建立與權限處理。代價：兩種承載形式、兩條憑證路徑、兩套除錯方式；且反向同步其實也是決定性的（讀看板 → 比對 sync-state → 寫檔 → 開 PR），沒有判斷性工作需要 LLM——用 gh-aw 等於為了省一段程式碼而引入一個 LLM 步驟到 `project.md` 點名的盲區裡。

C. **全部走 gh-aw**：三條路徑都是 gh-aw workflow，用 `update-project` safe-output 寫看板。看得到的效果：權限由編譯器依 `safe-outputs:` 宣告注入（避開 V-2 的坑）；不必手寫 GraphQL。代價：**NFR-P3 照字面無法滿足**——concurrency group 由編譯器依觸發型別產生，PR 觸發型固定 `cancel-in-progress: true`（V-1）；且 gh-aw 必含 agent step，決定性映射只能放 `pre-agent-steps`，而該區塊有**靜默丟棄 `timeout-minutes` 且回報 0 warnings** 的已知缺陷（v0.81.6 實測，v0.86.2 未複驗），PR #510 曾因此燒掉約 6 小時 runner 時間。

X. Other（請說明）

[Answer]: A（經 F1 收斂）— 純 Actions；並依 [F1=A] 追加約束：以 reusable workflow（`on: workflow_call`）或 composite action 承載，Project 編號、組織名、record 根目錄、自訂欄位名一律為 input，不得寫死  <!-- 2026-08-24T10:07:10Z -->

### Q2. 憑證與最小權限：怎麼收斂 repo 內容寫入權？（OQ-1）

`requirements.md` 的 R-1 已記載 feasibility 的 ADR-0006 IAM 判定原文不成立——機制需要「組織層 Projects 讀寫 ＋ repo 內容寫入」，後者用於寫綁定編號、`sync-state.json`（FR-A3）與開 PR（FR-G1）。GitHub App **沒有路徑層級的權限限制**，所以收斂只能靠其他手段。[US:S-10 AC 5] 已要求「範圍外寫入應回 403」成為一條可失敗的 AC。

A. **單一 GitHub App ＋ 以分支保護收斂**：一個 App 同時持有 Projects 讀寫與 repo contents 寫入；對 `ut`／`main` 設分支保護使該 App 無法直推，正向回寫只能進 feature 分支、反向只能開 PR。看得到的效果：S-10 AC 5 的 403 由分支保護產生，是真的會失敗的斷言；單一憑證、單一輪替點。代價：App 對 feature 分支仍有完整寫入權（可改 record 以外的檔案），路徑層級收斂靠 code review 而非機制。

B. **雙憑證分離**：一個 App 只有 Projects 讀寫（無 repo 權限），另一個更窄的憑證（或 `GITHUB_TOKEN`）負責 repo 回寫。看得到的效果：看板寫入與 repo 寫入的爆炸半徑完全分開；Projects 憑證外洩不會被拿來改 code。代價：兩個憑證要輪替與稽核；且 `GITHUB_TOKEN` 產生的 push **不會觸發後續 workflow**（[US:S-1 AC 5] 的適用前提正是這件事），若用它回寫，`[aidlc-sync]` 防線變成恆真、由平台承接。

C. **單一 App ＋ 回寫改走 PR（不直推任何分支）**：連綁定編號與 `sync-state.json` 都以 PR 形式回寫。看得到的效果：repo 側完全沒有直推路徑，權限收斂最徹底。代價：與 [req:FR-A3]（回寫到觸發分支的 commit，訊息含 `[aidlc-sync]`）**直接牴觸**——那條是已核可需求且 [F2=A] 明確定案；採此案需回跳 requirements 修訂。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-24T10:07:10Z（讀自 date -u，即時寫入） -->

### Q3. 「機制刻意不寫」要以什麼形式讓看板前的人看得見？（US-OQ-3）

user-stories 的 [M1=B] 已定案「新增 US-OQ-3 指派本站」。要涵蓋三種情形（回讀不符已中止／已暫停／待人工裁決），並回答與 FR-F1「單一自訂欄位」約束的關係。

A. **寫進 issue 的 `<!-- aidlc:managed -->` 受管區塊**：FR-G4 已建立該機制、FR-B3／FR-F3 已核可它為合法承載位置，Projects 卡片點開即見。看得到的效果：不動自訂欄位（FR-F1 的「單一」不受影響）；三種情形各自有原因類別與時間戳；`Done` 卡片下掛開啟中 issue 的說明（OOS-2 的必然後果）與未綁定 71 項的可分辨性都能放同一處。代價：需要點開卡片才看得到，看板列表視圖上仍無差別。

B. **在自訂欄位值上加前綴**（如 `⚠ frozen: requirements-analysis (2.3)`）：看得到的效果：列表視圖直接可見，不必點開。代價：與 US-OQ-4 的格式／長度問題直接疊加（該欄位已要承載 stage、`parked @`、`skipped` 三種事實），且 Projects 的單選欄位若採用會爆選項數；看板寬度有限，容易被截斷。

C. **A ＋ B 並用**：受管區塊放完整原因與時間戳，自訂欄位加一個短前綴。看得到的效果：兩種視圖都看得見。代價：同一事實兩處維護，兩者不一致時以誰為準需再定；且 US-OQ-4 的長度壓力不減。

X. Other（請說明）

[Answer]: C  <!-- 2026-08-24T10:07:10Z（讀自 date -u，即時寫入） -->

### Q4. 測試 item 與 fixture 要放哪裡？（US-OQ-5 ＋ US-OQ-6）

兩者是同一組決定。[US:S-10 AC 2] 需要一個真實測試 item 做端到端寫入讀回；[US:S-4／S-3 AC 6／S-9 AC 2-3] 共五處的 Given 在今日 repo 不可達，需要由 `aidlc-state.ts park` 產生、帶測試用綁定編號、且不屬於任何真實 intent 的 fixture record。

A. **獨立測試 Project ＋ fixture record 放 `<record>/.test-fixtures/`**：測試看板與 #16 完全分離；fixture record 以真實引擎命令產生但放在本 intent 的 record 目錄下、加 `.test-fixtures/` 子目錄。看得到的效果：①測試 item 永不進入 P3 的視野 ②並行 CI 各自寫測試看板，不會互相回讀不符而增生 issue ③fixture 由真實引擎產生，不與引擎格式漂移。代價：要多建一個 Project（組織層資源，需權限）；fixture record 若被 `intents.json` 掃到會變成第 7 個 intent，需確認掃描邊界。

B. **#16 上的專用測試 item ＋ 同上 fixture**：不另建 Project，在 #16 上開一個標記為測試用的 item。看得到的效果：不需新增組織層資源。代價：P3 的視野裡多一張持續閃動的卡片（他是「看板寫錯傷害最大」的那個 persona）；並行 CI 寫同一個 item 會觸發 S-3 AC 1 而自動開 issue。

C. **每次執行建立、結束刪除的臨時 item**：在 #16 上動態建立、跑完刪除。看得到的效果：不長期佔位。代價：刪除失敗會留下孤兒卡片且無人清理；建立／刪除本身要權限；CI 中斷時必留殘留。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-24T10:13:57Z（讀自 date -u，即時寫入） -->

### Q5. 重複失敗的通報怎麼收斂？（US-OQ-1）

[US:S-8] 原 AC 4（「須避免把 P1 淹沒」）因不可二元判定已移除，本站須產出收斂手段**並補回一條二元可判的 AC**。難點：判定「是不是同一個失敗的重複」需要**失敗身分＋跨輪持久狀態**，而目前沒有任何需求要求那份記憶存在。

A. **以既有 issue 為記憶：同類失敗更新既有 issue 而非開新的**：以 `(intent id, 失敗類別)` 為鍵搜尋開啟中的通報 issue，命中則追加一則 comment 並更新標題計數。看得到的效果：不需新增持久狀態——GitHub issue 本身就是那份記憶；P1 的通知量從「每輪一則」降為「每輪一個 comment」。可補的 AC：「Given 同一個 `(intent, 類別)` 的失敗連續發生兩輪，When 第二輪結束，Then 該類別的開啟中通報 issue 數為 1」。代價：搜尋既有 issue 是額外一次 API 呼叫；issue 被人工關閉後會重開一則新的（可接受，代表人已處理）。

B. **寫進 `sync-state.json` 的失敗計數**：在同步狀態檔記錄每個 `(intent, 類別)` 的最後通報時間與次數。看得到的效果：記憶在 repo 內、可版控、可稽核。代價：`sync-state.json` 每輪都要寫，等於每輪都產生一個 `[aidlc-sync]` commit（放大 [US:S-1 AC 7] 的 CI 觸發量問題）；且該檔的用途原本只是同步狀態，塞進失敗歷史會混淆職責。

C. **沉默窗口：同一 `(intent, 類別)` 在 N 小時內只通報一次**：以 issue 的建立時間判定。看得到的效果：實作最單純。代價：窗口內的新失敗完全不通報，若第二次失敗是不同根因會被吞掉；N 的值是另一個要定的參數。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-24T10:13:57Z（讀自 date -u，即時寫入） -->

### Q6. 既有 71 個未綁定 item 的空自訂欄位怎麼處理？（OQ-8）

新增自訂欄位會使既有 71 個未綁定 item 的該欄位為空（assumption A-7）。[US:S-5] 上線的那一刻這件事就變成公開且不可撤回的。邊界：補欄位值**不等於**對正 Status，OOS-3「不做既有 71 項一次性對正」仍然有效。

A. **不處理，空值即為「不受管」的標記，並寫進 US-OQ-3 的受管區塊說明**：看得到的效果：零額外工作；空／非空成為受管與否的天然區分子；而「空 = 不受管」這條規則寫在受管 item 的說明裡，讓看到的人查得到。代價：規則只寫在受管 item 上，看未綁定 item 的人不會看到；P3 面對一塊約 9% 受管、91% 空欄位的板子，仍可能得出「這板子不準」的結論。

B. **一次性把 71 個 item 的該欄位填為固定值（如 `unmanaged`）**：看得到的效果：板面上明確標示，不需要點開任何東西。代價：這是對既有 71 項的一次性寫入——**需確認它是否落入 OOS-3 的排除範圍**（本站判斷：OOS-3 排除的是「Status 的歷史漂移修正」，填一個新欄位的說明值不改任何既有欄位，不在其內；但這需要使用者確認而非本站自行認定）。

C. **把該欄位設為有預設值的單選欄位，預設即 `unmanaged`**：看得到的效果：新舊 item 都自動有值，不需一次性寫入。代價：Projects v2 的單選欄位選項有限且要預先列舉，而 stage slug 是開放集合（FR-J4 明文各 record 的 stage 集合不同），單選欄位承載不了。**本站判斷此案技術上不可行**，列出僅為完整性。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-24T10:13:57Z（讀自 date -u，即時寫入） -->

---

## 追問（Step 4 的矛盾分析觸發）

### F1. 可重用性：要以什麼身分承接？（Q1 的重新框定）

使用者對 Q1 的回覆是重新框定而非選項之一：「希望未來這個機制是所有 GitHub 專案套用 AI-DLC 流程都可以用的，看是要用成 AI-DLC 流程的 extension 的 skill 還是要變成共用的 gh-aw 都行」。

**本站查證後的兩項發現，兩者都改變這題的形狀：**

1. **那兩條路不等價，且落在剛收窄的規則兩側。** AI-DLC 的 extension／skill 是 **stage 或 slash command 觸發、人在迴圈內**；而 [req:FR-B4] 要求「任何分支的 push 觸發，並由 PR 生命週期事件觸發」、[req:NFR-P1] 要求「自 record 被推送起算 5 分鐘」。**skill 不會因 push 而啟動，人工觸發也讓 5 分鐘不可判定**——採 skill 路線等於改變產品本身（「跑 `/aidlc` 時順便同步」而非「推送後自動同步」），需回跳 requirements 修訂 FR-B4 與 NFR-P1。

2. **可重用性不在已核可範圍內，但也未被排除。** `scope-document` W-2 排除的是「其他 repo 的 intent 也同步到**本**看板」（跨 repo 資料匯集），與「機制可被其他 repo 安裝、各自同步到各自的看板」不是同一件事，故**不違反排除項**；但它也不在 CAP-1～CAP-11 的能力清單內，屬新增能力。依 `project.md ## Corrections`，下游不得擅自擴大已核可範圍。

A. **設計為可參數化，本次只交付本 repo 的安裝**：承載形式取 Q1 的 A（純 Actions）＋ **reusable workflow（`on: workflow_call`）或 composite action**，把 Project 編號、組織名、record 根目錄、自訂欄位名全部作為 input，**不寫死任何一個**。其他 repo 未來要用時寫一支三行的呼叫端 workflow 即可。看得到的效果：可重用性成為設計的**性質**而非交付的**能力**——不需回跳、不需重走 gate、幾乎零額外成本，且符合 architect 的「Reversibility over perfection」。代價：本次不交付散佈所需的東西（版本標記、安裝說明、範本 workflow、跨 repo 的憑證指引），其他 repo 真的要用時仍需一次額外工作。

B. **正式擴充範圍為「可被其他 repo 安裝」**：回跳 scope-definition 以 Modify 模式新增一項能力，重走該站 gate 與其後的 requirements 影響面。看得到的效果：散佈物（版本策略、安裝文件、範本、憑證指引）成為本次的交付項與驗收面。代價：回跳兩站、重走兩個 gate 與 reviewer；且本 intent 的 11 則故事與 65 條 AC 需增補對應的驗收面。

C. **改走 AI-DLC extension／skill 路線**：把機制做成 stage 觸發的工具（依剛收窄的規則，可用 `scripts/` 下的 Python，比照 `tcms` plugin 的形狀）。看得到的效果：與 AI-DLC 的整合最自然，散佈方式與 tcms 相同；且不需要組織層 Projects 憑證跑在無人值守的 workflow 裡。代價：**與 [req:FR-B4]、[req:NFR-P1] 直接牴觸**，需回跳 requirements-analysis 修訂那兩條——等於改變本 intent 的核心價值主張（從「不需要有人記得」變成「跑 AI-DLC 時順便」），而「零人工更新」正是 `intent-statement` 的第一項成功指標。

D. **本次不考慮可重用性**：寫死 Project #16 與本 repo 路徑，可重用性記為未來方向。看得到的效果：實作最短。代價：未來要抽取時，寫死的值散在 workflow 各處，抽取成本遠高於一開始就參數化。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-24T10:09:04Z（讀自 date -u，即時寫入） -->

---

## Step 4 — 矛盾與模糊分析（本站判定）

答案收齊後執行 stage 檔 Step 4 的強制分析：

1. **無模糊語言**：六題與一則追問皆為單一選項字母。
2. **一項跨題矛盾已在收齊前解消**：Q1 的原始回覆（extension/skill 或共用 gh-aw 皆可）與 [req:FR-B4]／[req:NFR-P1] 的觸發模型牴觸，已由追問 F1 當場定錨為 A（設計可參數化、不改觸發模型、不回跳）。
3. **一項需在設計中特別處理的組合**：[Q3=C]（受管區塊 ＋ 自訂欄位短前綴並用）與 [US-OQ-4]（單一欄位已要承載 stage／`parked @`／`skipped` 三種事實）疊加後，欄位長度壓力上升。本站在 `components.md` 以「短前綴限一個字元類、完整敘述一律落在受管區塊」收斂，並在 `decisions.md` 記為 ADR。**兩處不一致時以受管區塊為準**，此優先序由本站定案並寫入設計。
4. **[Q6=A] 的連帶**：「空值 = 不受管」這條規則只寫在受管 item 的受管區塊裡，看未綁定 item 的人看不到。本站接受此代價（[Q6=A] 選項本文已載明），不另闢新機制；但把它記入 `decisions.md` 的 Consequences，使下游知道 P3 仍可能得出「這板子不準」的結論。
5. **[Q4=A] 的待確認邊界**：fixture record 放 `<record>/.test-fixtures/`，需確認它**不會**被 `intents.json` 的掃描邊界撿成第 7 個 intent。本站在 `component-methods.md` 指定掃描以 `intents.json` 的 registry 為準（[req:FR-J1]：`intents.json` 只用於列舉），fixture 不註冊即不會被列舉；此為設計決定而非假設。

無需追問。

---

## §13 Learnings（stage 結束儀式）

`surface` 交出 11 個候選。多數為本站的描述性紀錄（元件切分判準、各 ADR 的取捨理由），抽不出跨 intent 可複用的判準，不提請採納。下列三項提請採納——**三項都是本站實際造成損害的失誤或實際奏效的作法**。

### L1. 要採納哪些學習寫進 `project.md`？（可複選）

A. **[c4+c5] 改動已產出的 artifact 前，先列出「本輪要改動的每一個主張」，改完逐一 grep 全部產出檔**。本站 reviewer iteration 2 的 6 項發現與 iteration 3 的 1 項新發現**全部**是跨檔傳播失敗（改 `decisions.md` 沒改 `components.md`／`component-methods.md`；改 `services.md` 的 concurrency 沒改 `components.md`；改選取演算法沒改另外兩檔的資料流敘述；補標籤時沒注意同表下方已有排除說明），沒有一項是新的設計錯誤。既有的 `units-generation:c6b` 講的是「同步衍生的**數字與引用**」，不涵蓋「跨檔案傳播同一個**決定**的改動」。附帶：**掃查腳本本身也要驗**——本站第一版腳本有 shell 引號與 Python bug，且把表格簡寫（`FR-B1、B2、B3` 前綴只掛第一個）誤報為未覆蓋。

B. **[c8] 當自己的修法偏離 reviewer 的建議時，在下一輪 brief 中主動點名該偏離並要求它最用力打**。本站對 finding 2／3 沒照 reviewer 的兩條建議分別處理，改用單一上游修法（選取改為 registry 驅動）同時解掉兩者。主動請它攻擊的結果是引出一個我沒想到的問題（首建被排除），而那正是需要被抓到的。理由：偏離建議本身沒問題，但**沒有揭露的偏離**會讓下一輪 reviewer 把它當成已驗證過的部分而略過。

C. **[c7] 使用者的回覆若是重新框定而非選項之一，先查證兩條路是否等價，再決定是否需要追問**。本站 Q1 的回覆是「extension/skill 或共用 gh-aw 都行」，查證後發現兩者落在剛收窄的規則兩側、且前者與已核可的 `FR-B4`／`NFR-P1` 直接牴觸——不是同一個產品的兩種包裝。若直接挑一條，等於替使用者做了一個他不知道自己在做的選擇。

D. **以上皆不採納**

[Answer]: A, B, C  <!-- 2026-08-24T22:51:42Z（讀自 date -u，即時寫入）· §13 -->

### L2. 還有什麼要補進來的嗎？

A. **Nothing to add** — 就上面選的那些
B. **Add a note** — 我有一項要自己寫

[Answer]: Nothing to add  <!-- 2026-08-24T22:51:42Z（讀自 date -u，即時寫入）· §13 -->
