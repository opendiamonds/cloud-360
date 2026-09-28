# Decisions — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: application-design（Inception 2.5）· Record: 260822-gh-projects-sync
     每則 ADR 含 Context／Decision／Consequences／Alternatives Rejected／Reversibility。
     編號 ADR-A<n> 為本站流水號，與 `<record>/inception/decisions/` 的 ADR-00NN 系列不同層級：
     後者是專案級架構決策，本檔是本 intent 的設計決策。
     上游輸入清單見 `components.md` §上游輸入。 -->

## ADR-A1 — 三條路徑全部以手寫 GitHub Actions 承載，不使用 gh-aw

**Context.** [req:FR-B2] 要求對照表判定為決定性邏輯、不由 LLM；[req:NFR-P3] 要求事件觸發兩路徑共用一個 concurrency group 且 `cancel-in-progress: false`；[US-OQ-7] 要求映射邏輯有一個可被 fixture 驅動的承載形式。`project.md ## Forbidden`（2026-08-24 收窄後）禁止以 repo 內程式承載**無人值守**的自動化，本機制正屬此類。

**Decision.** 三條路徑（正向、對帳、反向）＋ 一支自我測試全部是手寫 Actions workflow。決定性映射與解析（C-1／C-2）落在 composite action `.github/actions/aidlc-sync-map/action.yml`。

**Consequences.**
- `NFR-P3` 可照字面滿足——concurrency group 由我們自己寫。
- 全路徑零 LLM，[req:FR-B2] 與全域 DoD 的「全路徑無 LLM」自動成立。
- composite action 可被 `aidlc-sync-selftest.yml` 以純文字 fixture 驅動，[US:S-10 AC 1] 有對象。
- **本 repo 無 composite action 先例**（`.github/actions/` 不存在），此為首例；且 `validate_repo_contract.py` 的 `REQUIRED_FILES` 不涵蓋它，被改名或刪除時無機制攔截——記為已知缺口，收斂手段留 construction。
- Projects v2 的 GraphQL 呼叫（分頁、欄位 id 查詢、錯誤碼）全部新寫，[kb] 確認 11 支既有 workflow 無一寫過 Projects v2。

**Alternatives Rejected.**
- **全部走 gh-aw**：`NFR-P3` 照字面**無法**滿足——[kb] 實測 gh-aw 的 concurrency group 由編譯器依觸發型別產生、作者寫不了，PR 觸發型固定 `cancel-in-progress: true`。且 gh-aw 必含 agent step，決定性邏輯只能放 `pre-agent-steps`，而該區塊有「靜默丟棄 `timeout-minutes` 且回報 0 warnings」的已知缺陷（v0.81.6 實測；PR #510 因此燒掉約 6 小時 runner 時間）。
- **分工（正向純 Actions、反向 gh-aw）**：反向同步其實也是決定性的（讀看板 → 比對 `sync-state` → 寫檔 → 開 PR），沒有判斷性工作需要 LLM。為省一段程式碼而把 LLM 步驟引進 `project.md` 點名的三塊結構性盲區之一，代價與收益不成比例。

**Reversibility.** 中等。改走 gh-aw 需重寫觸發與並行設計，且要接受 `NFR-P3` 不成立——那需回跳 requirements。**視為不易反轉。**

## ADR-A2 — 單一 GitHub App ＋ 以分支保護收斂 repo 寫入權

**Context.** [OQ-1] 指派本站產出 repo 內容寫入權的收斂方案並重跑 ADR-0006 四面向判定。`requirements.md` 的 R-1 已記載 feasibility 的 IAM 判定原文（「不索取 repo 內容寫入權」）**已不成立**——CAP-1 寫回 issue 編號、[Q6=A] 的 `sync-state.json` 進版控、ADR-0013 §2 的反向同步開 PR 三者各自都要寫 repo。GitHub App **沒有路徑層級的權限限制**。

**Decision.** （**經 ADR-0014 更正**：權限集合為**三項**——組織層 Projects 讀寫 ＋ 用途受限的 repo 內容寫入 ＋ **Issues 寫入**。此處原文維持，更正內容與理由見 `./0014-permission-set-and-alert-convergence.md`） 單一 GitHub App 同時持有組織層 Projects 讀寫與 repo contents 寫入；對 `ut` 與 `main` 設分支保護使該 App 無法直推。正向回寫只進 feature 分支，反向只能開 PR。

**Consequences.**
- [US:S-10 AC 5] 的 Given 舉了**兩個**範圍外寫入的例子，本設計**只滿足其中一個**：
  - **直推 `ut`／`main`** → 分支保護會拒絕，**403 真的產生**，這半邊是會失敗的斷言。
  - **修改 record 目錄以外的檔案** → **本設計無機制可產生 403**。GitHub App 的權限模型沒有路徑層級授權（這正是 OQ-1 一開始被指派的理由），分支保護管的是「哪個分支可以推」而非「這個 commit 動了哪些路徑」。
  **先前版本不加保留地宣稱整條 AC「是一條會失敗的斷言而非宣稱」，與本則 ADR 下一段自承的「路徑層級的收斂靠 code review 而非機制」自相矛盾**——此為 reviewer iteration 1 Finding 1（Critical）的修正。
  **處置（surface ＋ resolve）**：候選機制為 **GitHub Repository Rulesets 的 file-path restriction**（`restrict file paths` 規則可讓推送含指定路徑外檔案時被拒），它是分支保護以外、確實在推送時產生拒絕的機制。**本站未實測其是否適用於 GitHub App 身分與本組織方案**，列入 **PRE-1 的實測項**（PRE-1 的細項清單在已核可的 `stories.md`，本站不回改該檔；新增項記於下方「本站對 PRE-1 的追加實測項」）。若實測不可行，S-10 AC 5 的第二個例子在本設計下無法成立，屆時須依 `project.md`（`user-stories:c4`：恆真／不可達的 AC 改寫而非刪除）回 user-stories 把該例子改寫到碰得到真實失敗面的層次，**不得留一條實作者只能默默弱化的斷言**。
- 單一憑證、單一輪替點、單一稽核面。
- 與已核可的 [req:FR-A3]（回寫到觸發分支的 commit）相容，不需回跳。
- **App 對 feature 分支仍有完整寫入權**，可改 record 目錄以外的檔案；路徑層級的收斂靠 code review 而非機制。這是本案的已知殘留風險。

**Alternatives Rejected.**
- **雙憑證分離**：爆炸半徑分得更開，但兩個憑證要輪替與稽核；且若 repo 側用 `GITHUB_TOKEN`，它產生的 push **不觸發後續 workflow**，[req:FR-A4] 的 `[aidlc-sync]` 防線變成恆真、改由平台承接——一條不可證偽的 AC。
- **回寫也走 PR**：權限收斂最徹底，但與 [req:FR-A3]／[F2=A] **直接牴觸**，需回跳 requirements。

**Reversibility.** 高。改為雙憑證只需換 secret 與呼叫端，不動元件介面。

### ADR-0006 四面向重新判定（[OQ-1] 要求的產出）

| 面向 | feasibility 原判定 | 本站重新判定 | 依據 |
| --- | --- | --- | --- |
| **IAM** | 「權限限縮為組織層看板讀寫，**不索取 repo 內容寫入權**」——**已不成立** | **（ADR-0014 再更正：三項，補 Issues 寫入）** 權限集合 = 組織層 Projects 讀寫 ＋ repo contents 寫入；後者以**分支保護**收斂為「僅 feature 分支」，`ut`／`main` 直推回 403。可觀察、二元、有 AC（[US:S-10 AC 5]） | ADR-A2；`requirements.md` R-1 |
| **Encryption** | 傳輸由 HTTPS 承擔；靜態機敏僅憑證，由平台 secret 保管 | **維持**。本設計不新增資料庫、不落地任何含機敏內容的檔案；`sync-state.json` 只存綁定編號與最後已知值，無機敏 | [req:NFR-S4] |
| **Network exposure** | 不適用——不新增對外服務、不開埠 | **維持**。四支 workflow 全部是託管執行環境對 GitHub API 的**出站**呼叫，無監聽、無端點宣告 | [req:NFR-S5] |
| **Audit logging** | 每次 Status 變更可回答「哪個 intent、哪個 stage、什麼時間」 | **強化**。除 [req:FR-E3] 的通報 issue 外，受管區塊（C-6）額外記載每一次「機制決定不寫」的原因類別與時間戳——原判定只涵蓋寫入，本站補上不寫的那一半 | C-6；[US-OQ-3] |

## ADR-A3 — 獨立測試 Project ＋ 由真實引擎產生的 fixture

**Context.** [US-OQ-5]／[US-OQ-6]。[US:S-10 AC 2] 需要真實 item 做端到端寫入讀回；[US:S-4] 全部、[US:S-3 AC 6] 前半、[US:S-9 AC 2／AC 3] 共五處的 Given 在今日 repo 不可達（實測 6 個 record 的 `Parked` 全部落空）。

**Decision.** 端到端測試對一個**獨立於 #16 的測試 Project** 執行。

> **經 ADR-0016 §3 增列兩個限定條件**（2026-08-31T00:37:44Z）——原文只要求「獨立於 #16」，實測顯示不足：
> 1. **必須與 repo 同擁有者**。掛在別的帳號名下的測試 Project **碰不到 `Issue.projectItems`**——它會穩定回 `0`，看起來像 `read_item` 壞了。更糟的形狀是反過來：實作為了讓測試過而把 `0` 當成正常分支，那個分支在正式組態下永遠走不到。實證為 `linkProjectV2ToRepository` 的錯誤訊息逐字：`Only projects owned by the same owner as the repository can be linked.`
> 2. **Status 欄位的選項名稱必須與 #16 一致**（`Backlog／Nice to have／Ready／In progress／In review／Done`）。新建 Project 的預設值是 `Todo／In Progress／Done`；照預設值測，U-3 的映射邏輯會對著一組**正式環境不存在的選項名**被驗證通過。
>
> 現行測試看板為 **#23「AIDLC sync 測試看板（PRE-1）」**（`opendiamonds` 名下），選項已以 `updateProjectV2Field` 對齊。**但兩邊的 option id 不同**——對齊是組態上的補救、非設計上的保證，故 ADR-0016 §R2 指派 **U-9 的 selftest 斷言測試看板的選項集與 #16 一致**。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`fixture record 由 `aidlc-state.ts park` 等真實引擎命令產生，放 `<record>/.test-fixtures/`，**不註冊進 `intents.json`**。

**Consequences.**
- 測試 item 永不進入 P3 的視野（他是「看板寫錯傷害最大」的 persona）。
- 並行 CI 各自寫測試看板，不會互相回讀不符而**自動增生 issue**——這條路徑若不隔離是真實的：`ci.yml` 的 `on: pull_request` 無分支過濾。
- fixture 由真實引擎產生，不與引擎格式漂移；手寫假的 `aidlc-state.md` 會變成「用自己的猜測驗自己的猜測」，而 C-2 的職責正是複製引擎語意。
- **需多建一個 Project**（組織層資源，需權限）。
- fixture 不註冊進 registry ⇒ 不被 C-2 的列舉撿到（[req:FR-J1]：`intents.json` 只用於列舉）。**這是設計決定，不是假設。**
- 實測三道 `park` 閘門（`aidlc-state.ts:824-836`）：`autonomous` 模式拒絕、`Status == "Completed"` 拒絕、`Current Stage` 為空拒絕——fixture 的產生腳本必須避開這三種狀態。

**Alternatives Rejected.**
- **#16 上的專用測試 item**：不需新資源，但 P3 視野裡多一張持續閃動的卡片，且並行 CI 寫同一 item 會觸發 [req:FR-C1] 而自動開 issue。
- **每次執行建立、結束刪除的臨時 item**：刪除失敗會留孤兒卡片且無人清理；CI 中斷時必留殘留。

**Reversibility.** 高。測試看板是 config（`project_number` input），換一個即可。

## ADR-A4 — 可感知性：受管區塊承載完整敘述，自訂欄位只放短前綴；不一致時以受管區塊為準

**Context.** [US-OQ-3]（[M1=B] 指派本站）要求「機制刻意不寫」在看板側可感知，涵蓋回讀不符已中止／已暫停／待人工裁決三種情形。[Q3=C] 選擇兩者並用。但 [US-OQ-4] 已指出單一自訂欄位要承載 stage、`parked @`、`skipped` 三種事實，長度壓力大。

**Decision.** 完整敘述（原因類別、時間戳、對照表列、`[S]`／`— SKIP` 差別、OOS-2 說明、「空欄位 = 不受管」說明）一律在受管區塊；自訂欄位只放一個字元類的短前綴（無／`parked @ `／`skipped `／`frozen: `），總長上限 50 字元，超出時截斷 stage-slug 尾端而**保留前綴**。**兩處不一致時以受管區塊為準。**

**Consequences.**
- 列表視圖有訊號（前綴），詳細視圖有真相（受管區塊），兩種讀者都被服務。
- 同一事實兩處呈現 ⇒ 必然有不一致的時刻（欄位寫成功、區塊寫失敗，或反之）。**優先序明文定案**避免下游各自猜測。
- 前綴不可被截斷這條規則是刻意的：截掉狀態訊號比截掉 stage 名稱危險得多。
- **P3 仍需點開卡片才看得到原因**。列表視圖上他只知道「這格被凍住了」，不知道為什麼。此為 [Q3=C] 的殘留代價，如實記載。

**Alternatives Rejected.**
- **只用受管區塊**：列表視圖完全無差別，P3 掃視看板時看不出任何異常。
- **只用自訂欄位**：長度壓力使三種事實必有一種被截斷，且無處放時間戳與原因類別。

**Reversibility.** 高。前綴與區塊格式都是 C-1／C-6 的內部決定，但**改區塊格式是一次性遷移點**，見 ADR-A6。

## ADR-A5 — 一致率分母維持上游 NFR-O2 的兩類排除

**Context.** `aidlc-quality-agent` 在 user-stories 的 round 1 提出的 AC 1 改寫用的是 `k−2`（兩類排除）；`aidlc-design-agent` 指出「第三類（回讀不符已中止）目前落在沒被想到而不是決定計入」但**明寫不裁定**。lead 曾自行草擬「擴為三類」的版本並在 stories.md 駁回它——該駁回的歸屬敘述已於 reviewer iteration 1 更正。

**Decision.** 分母 = 已綁定 − 有未處理反向紀錄 − `Parked` 非空，**維持上游 NFR-O2 的兩類**。`aborted`（回讀不符已中止）**計入分母且計入分子**，但另列獨立清單。

**Consequences.**
- 不擅自擴充已核可的指標定義（`project.md` 禁止下游擴大已核可範圍）。
- 指標在 `aborted` 被清理前不為 0——**這是正確行為**：那些 item 的看板值是機制自己判定無法擔保的，本來就是真的不一致，且每一個都已由 [req:FR-C1] 開了 issue。
- P4 分辨「壞了」與「正確地不動」的需求由**三份獨立清單**滿足，不需動分母。

**Alternatives Rejected.**
- **擴為三類排除**：會讓「機制刻意不寫」與「機制放棄擔保」被歸為同類，而後者是待清理的異常。且屬下游擅改已核可指標定義。

**Reversibility.** 高，但需回跳 requirements 修訂 NFR-O2。

## ADR-A6 — 受管區塊格式是一次性遷移點

**Context.** C-6 的 `content_hash` 是防迴圈第一道防線（[req:FR-G4]）。反向同步以「受管區塊內容雜湊與上次相同 ⇒ 無人為變更」判定。

**Decision.** 受管區塊的格式一旦上線即視為**契約**。任何格式變更必須伴隨一次明確的重新基準化（把所有受管 item 的雜湊重算並寫回 `sync-state.json`），且該遷移必須在**單一 PR 內完成**。

**Consequences.**
- 不做重新基準化就改格式 ⇒ 下一輪反向同步把**全部**受管 item 誤判為「有人為變更」⇒ 產生一個涵蓋所有 intent 的巨大反向 PR，且正向同步對全部 intent 進入 `suppressed`。**這是本設計最危險的單一失誤模式。**
- 因此 C-6 的格式應盡早穩定；construction 階段的任何格式調整都要走這條遷移路徑。

**Alternatives Rejected.**
- **以欄位級比對取代整塊雜湊**：可避免格式變更引發全面誤判，但要為每個欄位定義比對規則，複雜度顯著上升，且 [req:FR-G4] 明文要求「受管區塊**內容雜湊**比對」為三道防線之一。

**Reversibility.** 低。**這是本設計中最不易反轉的決定**，故明確標示。

> **只有政策、沒有機制（reviewer iteration 1 Finding 7）**：上述「必須伴隨重新基準化、且在單一 PR 內完成」是**流程紀律**，不是機制——本設計沒有任何欄位、檢查或 CI 步驟能在「改了格式卻沒重新基準化」時擋下合併。對照之下，本 repo 對同型風險（改 schema 卻沒同步 `DEPLOY.md`）是有 `project.md ## Mandated` 的 blocking 規則的。
> **指派**：把「設計一個機制（而非流程紀律）使格式變更與重新基準化不能脫鉤」列為 **functional-design 的待辦**，例如在受管區塊內嵌一個格式版本號並讓反向同步在版本不符時拒絕判定為人為變更。本站只確立需要機制，不指定形式。

## ADR-A7 — 既有 71 個未綁定 item 不處理，空欄位即「不受管」

**Context.** [OQ-8]。新增自訂欄位使既有 71 個未綁定 item 該欄位為空（假設 A-7）。OOS-3 排除「既有 71 項的一次性對正（歷史漂移修正）」。

**Decision.** 不對既有 71 項做任何寫入。空值即「不受管」的標記，該規則寫進受管 item 的受管區塊說明。

**Consequences.**
- 完全不觸及 OOS-3，零額外工作。
- **規則只寫在受管 item 上**——看未綁定 item 的人不會看到那段說明。
- P3 面對一塊約 9% 受管、91% 空欄位的板子，**仍可能得出「這板子不準」的結論**——而那正是本 intent 要消滅的結論。此代價已在 [Q6] 選項本文向使用者揭露並被接受，如實記入。

**Alternatives Rejected.**
- **一次性填為 `unmanaged`**：板面上明確，且本站判斷它不落入 OOS-3（填新欄位不改任何既有欄位）；但需使用者確認而非本站認定，使用者選擇不做。
- **單選欄位加預設值**：**技術上不可行**——Projects v2 的單選欄位選項需預先列舉，而 stage slug 是開放集合（[req:FR-J4] 明文各 record 的 stage 集合不同）。

**Reversibility.** 高。日後要補值只是一次性腳本。

## ADR-A8 — 失敗收斂以既有 issue 為記憶，不新增持久狀態

**Context.** [US-OQ-1]。[US:S-8] 原 AC 4 因不可二元判定被移除，本站須產出收斂手段並補回一條二元 AC。難點：判定「同一個失敗的重複」需要失敗身分＋跨輪持久狀態，而**沒有任何需求要求那份記憶存在**。

**Decision.** 失敗身分 = `(intent_id, reason_code)`。以該鍵搜尋**開啟中**的通報 issue：命中則追加 comment 並更新標題計數，未命中才開新 issue。**GitHub issue 本身就是那份記憶。**

**補回 S-8 的二元 AC**：
> **Given** 同一個 `(intent_id, reason_code)` 的失敗連續發生兩輪，**When** 第二輪結束，**Then** 該鍵對應的**開啟中**通報 issue 數為 1，且該 issue 的 comment 數增加 1。

**Consequences.**
- 零新增持久狀態；`sync-state.json` 不承載失敗歷史，職責不被混淆。
- issue 被人工關閉後下次會開新的——**這是想要的行為**，代表人已處理過而問題復發。
- 每輪多一次搜尋 API 呼叫。
- 並行時可能短暫產生兩則同鍵 issue，由下輪的 `resolve_if_open` 收斂。
  > **本句經 ADR-0014 更正，不可達**：`resolve_if_open` 只在失敗**不再發生**時被呼叫，而重複正是在失敗持續時產生的。收斂改由 `notify` 承擔（命中多筆時取最舊追加、其餘關閉），規則見 U-5 的 `business-rules.md` R-2 群。ADR-A8 的其餘部分維持有效。

**Alternatives Rejected.**
- **寫進 `sync-state.json`**：每輪都要寫該檔 ⇒ 每輪產生一個 `[aidlc-sync]` commit，放大 [US:S-1 AC 7] 的 CI 觸發量問題。
- **沉默窗口**：窗口內的新失敗完全不通報，不同根因的第二次失敗會被吞掉。

**Reversibility.** 高。

## ADR-A9 — 反向路徑的驗證判準與正向不同型

**Context.** [OQ-2] 指派本站產出「一組與正向不同型的斷言設計」。正向的判準是「輸出的 Status 對不對」；反向的判準是「**該不該**把這個看板變更寫回 record」——後者是決策的正確性，不是計算的正確性。

**Decision.** 反向路徑的斷言以「該寫／不該寫」的成對反例構成，落在 S-D `selftest`：

| 情境 | 期望 |
| --- | --- |
| 看板變更的來源 commit 訊息含 `[aidlc-sync]` | **不產生 PR**（機制自己的寫入不算人為變更） |
| 受管區塊內容雜湊與 `sync-state.json` 記錄的相同 | **不產生 PR** |
| 人工在看板上改了 Status，雜湊因此不同 | **產生 PR**，且 diff 不含 `aidlc-state.md` 任何一行 |
| 反向 PR 開啟期間，intent X 在 PR 內、Y 不在 | 正向對 X `suppressed`、對 Y **照常寫**（[US:S-6 AC 3] 的逐 intent 反例） |

**Consequences.** 每一條都有成對的正反情境，避免「只驗該寫、不驗不該寫」的單邊斷言。
**Alternatives Rejected.** 沿用正向的值比對斷言——它驗不到「不該寫時有沒有克制」。
**Reversibility.** 高。

## ADR-A10 — 可重用性是設計的性質，不是本次的交付能力

**Context.** [F1=A]。使用者希望此機制未來可被所有採用 AI-DLC 的 GitHub 專案使用。但可重用性不在 CAP-1～CAP-11 的能力清單內，屬新增；而 `scope-document` W-2 排除的是「其他 repo 的 intent 同步到**本**看板」，與此不同，故**不違反排除項**。

**Decision.** 承載物全部參數化（`project_number`、`project_owner`、`record_root`、`stage_field_name`、`whitelist`、`reconcile_batch_size` 為 input；`app_id`／`app_private_key` 為 secret），拆為 `*-impl.yml`（`on: workflow_call`）＋ 薄外層。**本次不交付**版本策略、安裝文件、範本 workflow、跨 repo 憑證指引。

**Consequences.**
- 不需回跳、不需重走 gate，額外成本近乎零。
- 未來抽取時不必在 workflow 各處挖出寫死的值。
- **「可以被重用」與「已被驗證可重用」是兩件事**——本次沒有任何 AC 驗證它在另一個 repo 跑得起來。這個區別必須寫下來，否則六個月後會有人以為它已經是個可安裝的產品。

**Alternatives Rejected.**
- **正式擴充範圍**：散佈物成為交付項與驗收面，但需回跳 scope-definition 與 requirements、重走兩個 gate 與 reviewer，且 11 則故事與 65 條 AC 需增補。
- **改走 AI-DLC extension／skill**：與 [req:FR-B4]（push／PR 觸發）、[req:NFR-P1]（推送後 5 分鐘）**直接牴觸**——skill 是人在迴圈內觸發。等於把核心價值從「不需要有人記得」改成「跑 AI-DLC 時順便」，而「零人工更新」是 `intent-statement` 的第一項成功指標。

**Reversibility.** 高（往 B 案走只是增補，不需推翻既有設計）。

## 本站對 PRE-1 的追加實測項

PRE-1 的細項清單定於已核可的 `stories.md`（[Q5=A] 於 user-stories 定案）。本站設計過程中逼出**一項該清單沒有、但必須在同一輪實測中一併確認**的項目。依既有紀律不回改已核可的上游 artifact，故記於此，由 construction 併入 PRE-1 執行：

| # | 追加實測項 | 為什麼必須在 PRE-1 這一輪做 | 來源 |
| --- | --- | --- | --- |
| PRE-1-a | **GitHub Repository Rulesets 的 file-path restriction 是否適用於 GitHub App 身分與本組織方案** | 它決定 [US:S-10 AC 5] 的第二個例子（修改 record 目錄以外的檔案應回 403）在本設計下**能否成立**。不成立時該 AC 需回 user-stories 改寫（依 `user-stories:c4`），而那是 construction 開工前就該知道的事，不是實作到一半才發現 | ADR-A2；reviewer iteration 1 Finding 1 |

## CAP-11（反向同步）可行性補評估（[OQ-3] 要求的產出）

feasibility 站未涵蓋 GitHub → repo 這條路徑。本站補評估：

| 面向 | 判定 | 依據 |
| --- | --- | --- |
| **技術可行性** | **可行**。讀 Projects v2 item 現況為 GraphQL query；開 PR 為 `gh pr create` 或 REST。兩者都不需要新服務或新依賴 | ADR-A1 的承載形式 |
| **逐 intent 歸屬** | **未驗證，且是本路徑的真正風險**。先例（`aidlc_sync_pull.py --all-intents`）一次處理全部 intent 並開**單一** PR，在該形狀下「某 intent 有未處理反向紀錄」無法只從 PR 開關狀態判定 ⇒ 一個開著的 PR 會讓**全部** intent 一起 `suppressed`（over-suppression）。本設計以「讀 PR 的 diff 是否含該 intent 的 record 路徑」判定，[US:S-6 AC 3] 已含反例要求 | `requirements.md` A-6 的更正 |
| **成本** | 每日一次反向 PR 會觸發 6 支 `on: pull_request` 的 gh-aw（含 `ui-regression`，該檔自述曾在單一 PR 燒掉約 6 小時 runner 時間）。**[US:S-6 AC 7] 已把排除高成本 workflow 列為 AC** | [kb:component-inventory] |
| **ADR-0006 四面向** | IAM：反向路徑只需 Projects **讀** ＋ repo 寫（開 PR），不需 Projects 寫；但因採單一 App（ADR-A2），實際權限集合仍是聯集。Encryption／Network exposure：與正向相同，無新增。Audit logging：反向 PR 本身即稽核痕跡，且不動 `aidlc-state.md`（[req:FR-G2]）使引擎的狀態機不受污染 | ADR-A2 的判定表 |
| **Go / No-Go** | **GO**，但 over-suppression 是必須在 construction 實測的一項——它不是設計缺陷，是先例形狀與需求形狀的落差 | — |

## Review

**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 3（驗證輪）
**Verdict:** READY

> 依指示逐檔重讀全部五份 artifact（`components.md`、`component-methods.md`、`component-dependency.md`、`services.md`、`decisions.md`），不採信本節先前版本、lead 的修法自述或其掃描腳本結果，判定全部獨立重新推導。§12a 的「驗證輪不計入原始 iteration 上限，以缺陷來源判斷」在本輪適用：下方六項對應的是 iteration 2 判定為 2 Critical／3 Major／1 Minor 的六項殘留（iteration 2 表內的 #1、#8、#9、#10、#11、#12），逐項核對其修法是否落地、有無propagation 遺漏、有無修法本身引入的新缺陷。

### 逐項驗證 iteration 2 findings

| # | 對應 repair | 原嚴重度 | 判定 | 證據 |
|---|---|---|---|---|
| iter2-#1 | Repair 2：403 過度宣稱殘留於 `components.md`／`component-methods.md` | Critical | **Resolved** | `components.md:72`：「[US:S-10 AC 5] 的**兩個例子中只有這一個**可由分支保護產生真的 403，另一個「改 record 目錄以外的檔案」在本設計下無機制可產生 403——見 ADR-A2 與 PRE-1-a」；`component-methods.md:95-97`：「權限邊界的可觀察面」明列「不得提供」的兩種方法，緊接一段以「但『介面不提供』與『嘗試時回 403』是兩件事（reviewer iteration 2 Critical）」開頭的更正段落，逐字複述 ADR-A2 的拆解並自陳「此處先前的措辭……已更正」。三份文件（`decisions.md` ADR-A2、`components.md:72`、`component-methods.md:95-97`）現在對同一件事給出**同一個答案**，iteration 2 抓到的「同一份設計套件內權威文件與實作規格文件互相矛盾」的形狀已消除。 |
| iter2-#8 | Repair 1：`[req:FR-A1]` 首建被漂移驅動選取排除 | Critical | **Resolved** | `services.md:21`：S-A 生命週期改寫為「單次執行掃過 `intents.json` registry 內的全部 intent，逐一分流：**無綁定編號者走首建路徑**（C-3 `create_item`，[req:FR-A1]）；**已綁定者**比對 `sync-map` 判定與 `sync-state.json`，有漂移才寫」——這是兩支並存、互不覆蓋的判斷（未綁定 OR 已綁定且有漂移），不再是「已綁定 AND 有漂移」的單一 AND 條件。`services.md:37` 新增「首建不被漏掉（reviewer iteration 2 Critical）」段落，明文指出「若把條件寫成『已綁定且有漂移』，[req:FR-A1]／[US:S-1 AC 1]……就永遠不會觸發」並承認「此為 iteration 1 修正時的措辭疏失」。`components.md:106` 的 Workflow 承載表仍把 `[req:FR-A]` 整組列給 `aidlc-sync-forward.yml`——這在新演算法下**不再矛盾**（forward workflow 確實同時承載首建與漂移補平兩支分流）。`component-dependency.md:45`「若無則先請 C-3 board-client 建立 item」這段資料流敘述也與新演算法一致（描述的是單一 record 走到 C-4 之後的分支，本就假設「有 record 被選中」，選取條件的修正發生在更上游，不影響這段敘述本身的正確性）。 |
| iter2-#9 | Repair 4：`[req:FR-A4]` 自我排除與漂移驅動選取未調和 | Major | **Partially resolved — 判斷後降級為 Minor 殘留（理由見下方子節）** | `services.md:26` 新增「與 registry 驅動選取的調和（reviewer iteration 2 Major）」段落，明文選定「兩道都是整輪層級，不是逐 record 層級」——iteration 2 兩種讀法的其中一種（「整輪不寫」）已被明文選定，「該 gate 整個 run 還是只 gate 一個 record」的**歧義**已消除，也未落入「僅該 record 不寫」需要重新引入 diff 判斷、與新規則自相矛盾的那個分支。**但**原建議的第二部分——「若選『整輪不寫』，需承認並評估它對其他 intent 漂移補平的延遲影響」——這句話要求的具體承認與評估**未出現**：`services.md:26` 全段沒有一句提及「其他 intent」或量化這個延遲，`grep -n "延遲\|其他 intent" services.md` 只命中既有的、與此無關的 NFR-P1 延遲目標列與 ADR-A9/擴縮特性表裡既有的並行取消殘留風險段落（`services.md:39`、`services.md:95`），兩者都是**修法前就存在**的段落，不是為 FR-A4 這個交界新寫的。 |
| iter2-#10 | Repair 3：`components.md` concurrency 字串殘留舊版 | Major | **Resolved** | `components.md:113`：`aidlc-sync-forward.yml`：`group: aidlc-sync-event-${{ github.repository }}-${{ github.event.pull_request.head.ref \|\| github.ref_name }}`；`services.md:22` 為同一字串。逐字比對相同，`components.md:113` 下方並附「理由與殘留風險見 `services.md` S-A」的指標，不再是兩個可能各自漂移的獨立副本。 |
| iter2-#11 | Repair 5：`FR-H1` 在同一張表內被列為「workflow 層承載」又被排除説明宣稱「無元件」 | Major | **Resolved** | `component-dependency.md:95` 的 `workflow 層` 列現為「FR-B4、**B5**、G1、G2、G3、**I1**、**I2**、**I5**、NFR-P3、**NFR-S2**、**NFR-S3**、**NFR-C2**」——`H1` 已移除；`:98` 維持「**FR-H1**（README 指路）為單段文字，無元件」；`:103` 新增更正註記「**FR-H1 於 reviewer iteration 2 Major 後從『workflow 層』列移除**……先前補標籤時誤加到 workflow 層，使同一張表對同一條需求給出兩種歸屬」。同一張表內部已不再自相矛盾。 |
| iter2-#12 | Repair 6：`component-dependency.md` 雙向對照表殘留未引用的 NFR 標籤（`NFR-C2`／`S4`／`S5`／`P2`／`P4`） | Minor | **Resolved，但修法本身在同一張表內引入一項新的自相矛盾（Minor，見本輪新發現 #13）** | `NFR-C2` 已補進 `:95` 的 `workflow 層` 列；`:100` 新增 `NFR-S4／S5` 為否定性約束、無單一元件承載的排除説明；`:101` 新增 `NFR-P2／P4` 已由 `C-7` 的 `FR-D1／FR-D3` 承接、「此處不重複列」的排除説明。**標籤缺席**的原始缺口確實已消除（見下方機械複驗）。但 `:101` 這句「此處不重複列」與同一張表 `:93` 的 `C-7` 列**直接矛盾**——見本輪新發現 #13。 |

### 對 iter2-#9 殘留判斷的說明（降級理由）

iteration 2 把 finding #9 判為 Major，理由是「兩種讀法都未被設計明文選定」與「都各自帶著未被承認的代價」兩者複合。本輪重讀後，**前者（功能實作歧義）已被消除**——`services.md:26` 明文選定「整輪層級」，且該選擇避開了「僅該 record 不寫」分支原本會與 `component-methods.md:78` 的「不得依事件 diff 推導 record」規則自相矛盾的那個風險；一個依此規格實作的開發者不會被引導去寫出違反新規則的程式碼，這是原始 Major 判定中權重最高的那部分。

殘留的「未承認代價」本身，經與本設計既有的風險揭露慣例對照：`services.md:39`（並行取消殘留風險）已對**同類**的「某次事件路徑被跳過，需等下一次事件或隔日對帳補上」的後果做過如實記載與規模化評估（「以 6 個 record 的現況規模，單次全掃描成本可忽略」）。FR-A4 整輪 skip 造成的延遲，其**上界**與並行取消造成的延遲上界相同（下一次非自我排除事件，或隔日 S-B 對帳，兩者較早者），且觸發頻率更低（僅在 HEAD commit 恰為機制自身回寫時發生，而非任何高頻事件）。也就是說，**這個代價的量級已經被本設計的其他段落間接圈定過**，只是沒有在 FR-A4 這一列被逐字覆誦一次——這是一個文件完整性缺口（該寫但沒寫），不是一個未被理解、可能導致實作走錯路的功能缺口。故判斷降級為 Minor，不計入 Major 門檻，但仍列為待補（見下方新發現）。

### 本輪對選取演算法改動的獨立覆核（是否引入新問題）

- **`NFR-P1`（5 分鐘延遲目標）**：新演算法要求 S-A 每次執行都掃過**全部**（現況 6 個）registry intent，而非只處理事件 diff 涉及的 record。`services.md:39` 與 `:95` 已明文記載「以 6 個 record 的現況規模，單次全掃描成本可忽略；規模成長時以 `reconcile_batch_size` 同型的上限收斂」，且 `NFR-P1` 本身以 [US:S-9 AC 6] 的 20 次取樣量測型 AC 承接，不是靜態宣稱。**未發現新衝突**。
- **`[US:S-1 AC 7]`（回寫 commit 不得取消既有 `ci.yml` run）**：該 AC 的防線是 `component-methods.md:108` 的 `ci.yml` `paths-ignore`（或等價手段），與 S-A 內部如何選取要處理的 record **無關**——回寫 commit 本身觸及的檔案集合（綁定編號、`sync-state.json`）不因選取演算法改變而改變。**未發現新衝突**。
- **S-A 與 S-B（`reconcile`）是否變成同一件事**：不成立。S-A（`services.md:21`）比對的是 `sync-map` 判定結果 vs **本地快取**的 `sync-state.json`；S-B／`reconcile`（`services.md:46`、`component-dependency.md:49`）對每個已綁定且未 park 的 intent 走一次「C-2 → C-1 → **C-3 回讀**」——即比對判定結果 vs **即時回讀**的看板現況，經外部 API。兩者的代價與可偵測的漂移類型不同（S-A 抓不到「板子被外部改過但本地快取沒發現」這類漂移，S-B 可以），依 `component-dependency.md` 的依賴矩陣，S-A 全程不呼叫 C-3。**未發現新衝突**。
- **首建分支是否重新開啟 fixture 隔離漏洞**：不成立。`component-methods.md:78` 已把「事件路徑（S-A）與排程路徑（S-B／S-C）一律以 `intents.json` 的 registry 為選取來源」的規則同時涵蓋 S-A 的兩支分流（未綁定→首建、已綁定→漂移判斷）——選取來源仍是 registry 本身，`.test-fixtures/` 因未註冊進 `intents.json` 而**在任一分支都不會被列舉到**，不會被誤判為「無綁定編號的新 intent」而觸發首建。**未發現新衝突**。

### 機械複驗（獨立重跑，不採信 lead 的掃描結果）

- **`[req:*]` 雙向覆蓋**：以 `grep -oE '(FR|NFR)-[A-Z][0-9]+'` 獨立抽取 `requirements.md` 的完整 ID 集合，得 **40 FR ＋ 15 NFR ＝ 55 項**，與 `components.md:9` 宣稱的計數一致。以同一 regex 掃五份 artifact 得 53 項顯式引用，缺 `FR-F1`、`FR-I2`；逐一核對後兩者確實存在，只是以省略記法出現在逗號清單中（`component-dependency.md:88` 的「…B6、**F1**、F3…」、`:90`／`:95`／`:105` 的「…F2、**I2**…」）——**55/55 全數覆蓋，反向亦無虛構 ID**（顯式引用集合 ⊂ `requirements.md` 的 55 項集合，無多餘）。此為 iteration 2 finding #4／#12 補齊後的獨立複驗，結果與 lead 的宣稱一致，但發現一項 lead 掃描腳本未抓到的內部矛盾（見下方新發現 #13）。
- **內部交叉引用**：`ADR-A1`～`ADR-A10` 十則 ADR 全數在 `decisions.md` 有對應標題、被引用處全部可解析，無 `ADR-A11+` 之類的懸空引用。`C-1`～`C-7` 七個元件 ID 在五份檔案中全數一致使用，無孤兒引用。`PRE-1-a` 在 `decisions.md`（定義處＋兩處引用）與 `components.md:72`、`component-methods.md:97` 三處引用彼此一致。

### 本輪新發現

| # | 嚴重度 | 位置 | 問題 | 建議 |
|---|---|---|---|---|
| 13 | Minor | `component-dependency.md:93`（「元件與需求的雙向對照」表，`C-7 reconciler` 列含 `NFR-O1、O2、P1、P2、P4`）vs 同檔 `:101`（「`NFR-P2／P4`……已分別由 `C-7` 的 `FR-D1／FR-D3` 承接，**此處不重複列**」） | 這是 iter2-#12 的修法自己引入的、與 iteration 2 finding #11（`FR-H1`）同型的表格內部自相矛盾，只是規模更小：`:101` 的排除説明句型與其上方三則（`FR-I3／I4`、`FR-H1`、`NFR-M1`、`NFR-S4／S5`）一致，讀起來是在解釋「這個 ID 為什麼**不出現在**表格任何一列」；但 `NFR-P2` 與 `NFR-P4` 這兩個 token **確實逐字出現**在 `:93` 的 `C-7` 列裡（緊接在 `NFR-O1、O2、P1` 之後）。核對修法前的狀態（iteration 2 finding #12 原文：「`NFR-P2／P4` 則是全份 application-design 語料**完全未提及**（不在任何檔案）」）可知，這次修法同時做了兩件事——把 `P2`、`P4` 加進 `:93` 的 `C-7` 列，**又**在 `:101` 加了一句把它們寫成「排除在外、不重複列」——兩個動作互相矛盾，屬同一次修法內部未同步的殘留。**與 `FR-H1` 案不同的是，這裡不構成語意上的歸屬歧義**（兩處都同意 `C-7` 經由 `FR-D1／FR-D3` 承接了 `NFR-P2／P4` 的實質內容，開發者不會因此誤判該實作什麼），純粹是「排除説明宣稱『未列』但表格裡已經列了」的自我矛盾陳述，故列 Minor 而非 Major。 | 二擇一並改齊：若沿用「`NFR-P2／P4` 不需要獨立標籤，隨 `FR-D1／FR-D3` 帶過」的判斷，把 `:93` 的 `C-7` 列中的 `、P2、P4` 移除，只留 `NFR-O1、O2、P1`；若要保留 `:93` 的顯式列示（機械覆核工具更容易抓到），把 `:101` 的「此處不重複列」改寫為「已在上表 `C-7` 列列出；本行補充其承載機制為 `FR-D1／FR-D3`，非獨立能力」。 |

### Attempted refutations that did not hold

- **指定 spot-check（task 第 4 點）：重驗 iteration 2「finding 1 的殘留只是文件層級的措辭問題，不影響設計本身是否可實作」——本輪重驗，該駁斥當時被判定「不成立」，現況為：促成駁斥不成立的**前提本身已被本輪修法移除**，不再需要重新判斷。** iteration 2 判定這個駁斥不成立的理由是：`component-methods.md` 字面會讓開發者寫出一個「改 record 目錄以外的檔案會回 403」的測試，而該測試在 ADR-A2 承認的現實下會恆常紅燈。本輪核對 `component-methods.md:95-97` 現況，那段文字已被替換為與 ADR-A2 完全一致的拆解（見上方 iter2-#1 判定），**不再存在會誤導開發者寫出恆紅測試的字面**。故本輪不需要、也無法重新執行同一個駁斥嘗試——原本讓駁斥不成立的證據（矛盾的字面）已不存在，這正是「finding 1 的殘留不是文件層級的小問題，而是會導致實作走錯路的真缺陷」這個判斷本身被印證的方式：修正它需要動到「這句話寫的是什麼」，而不能只在別處補一句免責聲明，這一點在本輪的修法路徑上得到確認（`components.md` 與 `component-methods.md` 都被直接改寫，不是靠外部指標繞過）。
- **本輪嘗試：「iter2-#9 的殘留代價缺口不是真缺口，因為結構性防線①已經讓延遲代價無關緊要」——部分不成立，判斷為 Minor 而非直接忽略。** 嘗試論證：既然防線①（回寫後 `sync-state.json` 與看板自然一致 ⇒ 下一輪判定無漂移）不依賴防線②（HEAD commit 訊息 skip）就能保證正確性，那麼防線②造成的「整輪提早退出」即使延遲了其他 intent 的漂移補平，也只是效能問題不是正確性問題，可以被視為不需要在 `services.md` 額外書面承認。**查核後未完全站住**：`services.md:26` 目前的寫法把兩道防線都描述為「各自獨立成立」，沒有講清楚防線②其實是可以被拿掉而不影響正確性的純優化——若讀者以為兩道防線都是必要的正確性保證，會誤判「拿掉防線②」是危險的重構，而實際上（依防線①的邏輯）它不是。這正是原建議要求「承認並評估代價」的深層理由：把代價寫清楚，順便也讓「防線②是可選優化」這件事變得可推導，而不是隱含在讀者需要自己重建的推理鏈裡。故此殘留仍列入新發現 / 降級 Minor，不當作已駁斥。
- **本輪嘗試：「registry 全量掃描（無綁定者建立、已綁定者判漂移）與 S-B 的『已綁定且未 park』掃描範圍不同，兩者的並行寫入競爭是否因此在 iter2 未預期的方式擴大」——不成立，維持既有處置有效。** S-A 現在對**全部** intent（含剛首建、尚未有 `sync-state.json` 記錄的）執行，S-B 對「已綁定且未 park」執行；兩者的交集（已綁定、有 `sync-state.json`）維持 iteration 1／2 已核可的「C-3 寫入前回讀，後到者 `Aborted`」處置（`services.md:50`、`components.md:62`），交集外的部分（S-A 獨有的首建分支）不涉及 S-B，S-B 獨有的部分（已綁定但 S-A 本輪未觸發時仍會被 S-B 每日掃到）也未改變既有語意。**未發現新的競爭面**。
