# Bolt Plan — AI-DLC ↔ GitHub Projects 同步

<!-- Stage: delivery-planning（Inception 2.8）· Record: 260822-gh-projects-sync
     來源標籤：[ug:*] units-generation 三份產出；[ad:*] application-design；
     [req:*]／[US:*] requirements.md／stories.md；[Qn]／[F1] 本站問題檔。 -->

## 適用的既有實踐（Step 2 解析結果）

| 段落 | 解析結果 | 對本計畫的具體後果 |
| --- | --- | --- |
| `## Way of Working` | Construction Bolt 分支 base／target 為 `ut`，**squash-merge** | 每個 Bolt 對應 `ut` 上一個 commit，分支名依 `<uploader>/<type>/<slug>` |
| `## Walking Skeleton` | **`skeleton: off`**（`team.md` Q3 定案） | **Bolt 1 是一般 Bolt**，不設額外的 skeleton gate 與儀式 |
| `## Deployment` | deploy-on-merge 至自有 staging；Construction 與 Operations 連續（ADR-0008） | **每個 Bolt 邊界都是一次真實部署**——這是下方同批次約束存在的唯一理由 |

## Bolt 0 — 上線前置關卡（不是 Bolt）

依 [Q4=A]，PRE-1 在計畫中的身分是**關卡而非交付批次**：它不產出程式碼，`scope-document` 明記 CAP-9「Must，但不構成交付批次」，[ug:unit-of-work.md] 的 12 個單元也不含它。列在此處是為了讓「它必須在 Bolt 1 開工前全綠」這件事有一個看得到的位置。

**留痕形式**（[US-OQ-2] 指派本站裁定的具體產出）：**七項**實測各一份記錄，寫入 **`<record>/construction/PRE-1-results.md`**，每項含**實際執行的呼叫或設定**、**得到的回應**、**判定**三欄。〔**經 ADR-0016 §8 更正**（2026-08-31T00:31:34Z）：本段原寫「五項……寫入 `pre-1-findings.md`」，但該檔**從未存在**，證據實際累積於 `PRE-1-results.md`（至今六輪）。以既有檔為正本、改本處指名，理由是改檔名會斷開既有引用。項數更正見表下註記。〕`stories.md` 明文「不得以文件敘述代替驗證」——只引用官方文件的項目視為未完成。

| # | 實測項 | 判定影響 | 阻擋 |
| --- | --- | --- | --- |
| 1 | 憑證帶**三項**權限：組織層 Projects 讀寫、用途受限的 repo 內容寫入、**Issues 寫入**。各至少一次真實呼叫，**必須包含一次開 issue**（ADR-0014）〔**經 ADR-0015 §8 更正為四項**：另加 **Pull requests 寫入**（開 PR 與推分支是兩個獨立權限），須在憑證鑄造前生效。見 `../decisions/0015-functional-design-upstream-amendments.md`。指標補於 2026-08-30T00:48:38Z〕〔**再經 ADR-0016 §1／§2 更正**（2026-08-31T00:31:34Z）：**「組織層」前提作廢**——實測確認 `opendiamonds` 是**個人帳號**（`GET /orgs/opendiamonds` → 404），無組織可授此權限。憑證身分改為**擁有者帳號 token**，第一項改讀作**個人帳號 Projects v2 讀寫**（由 `project` scope 承載）。且**四項不再是可分別授予的四項**：後三項由 `repo`（或 `public_repo`，待 PRE-1-c）scope **整包**承載，故 NFR-S1 的「無額外授予」判準結構性不可滿足，已於 ADR-0016 §2 改述。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`〕 | 全部寫入路徑 | 全部 Bolt |
| 2 | 框架單次操作次數上限（C-T5）實際值與超限行為 | [US:S-7 AC 3] 的上限值 | Bolt 2 |
| 3 | `createProjectV2Field` 是否可用 | [US:S-5 AC 2] 走哪一支 | Bolt 1 |
| 4 | 順帶回答 A-1／A-2／A-3／A-8 | A-8 直接決定 [US:S-1 AC 6] 的失敗模式是否真實 | Bolt 1 |
| PRE-1-a | Repository Rulesets 的 file-path restriction 是否適用於 ~~GitHub App 身分與本組織方案~~ 本 repo〔前提經 ADR-0016 §1 作廢：無 GitHub App、無組織〕 | [US:S-10 AC 5] 第二個例子**能否成立**；不成立時該 AC 需回 user-stories 改寫 | Bolt 4 |
| **PRE-1-b** | 以真實憑證對真實 issue 呼叫 `Issue.projectItems`，確認 (a) 該欄位存在且可查；(b) 回傳可依 Project id 過濾；(c) 一個 issue 屬多個 Project 時的回傳形狀符合 U-3 的 R-1.4 假設 | U-3 的 `read_item` 全部建立在這條路徑上，而 `write_status`／`create_item`／`write_field` 又全部經過 `read_item`。本 repo 從無 Projects v2 先例 | **Bolt 1** |
| **PRE-1-c** | 鑄一顆 **`public_repo` ＋ `project`** 的 classic PAT，實測**四條寫入路徑**：Projects 寫入、contents 寫入、開 issue、開 PR。任一條失敗即退回 `repo` | 憑證的爆炸半徑能否由「該帳號可存取的全部 repo，含私有」縮到「公開 repo」——即 OQ-1 唯一剩下的可達收斂手段，並決定 ADR-0006 **IAM 面**的判定能否結案 | **Bolt 1**（更精確：**憑證鑄造之前**） |

> **PRE-1-b 由 ADR-0015 §1 增列（指標補於2026-08-30T00:48:38Z）。** 本表先前只有五項，且 Bolt 1 的 DoD 只檢查第 1／3／4 項——存在「核心查找路徑零驗證即依 deploy-on-merge 上線」的真實機率。完整理由見 `../decisions/0015-functional-design-upstream-amendments.md`。**留痕形式與其餘各項相同**（寫入 ~~`<record>/construction/pre-1-findings.md`~~ **`PRE-1-results.md`**，見 ADR-0016 §8），故上方「五項實測各一份記錄」現應讀作**六項**。

> **PRE-1-c 由 ADR-0016 §7 增列（2026-08-31T00:31:34Z）。** 它的由來值得記在這裡，因為它是本表**唯一一項不是為了補驗證缺口、而是為了收斂權限**而存在的：ADR-0016 初版逐字宣稱 OQ-1 的「收斂手段**已耗盡**」，該宣稱在同一天被為了補測其 Alternatives B 而做的 scope 探查推翻——官方 scope 文件逐字，`repo` 為「public **and private**」而 `public_repo` 為「**Limits access to public repositories**」，而本 repo 為 public。**推翻它的事實（repo 為 public）第四輪就已實測記載，只是當時只被記到「PRE-1-a 的 ruleset 不可行」那一側。**
>
> **為什麼不能直接改用 `public_repo` 而要實測**：該 scope 的文件原文列舉「code, commit statuses, repository projects, collaborators, and deployment statuses」，**沒有逐字寫 issues 與 pull requests**。憑「歷來應該有涵蓋」就採用，正是 ADR-0014 點名的 **K-1 誤解**（把 Issues 當成 Contents 的一部分）換一個外衣——而那個誤解的特性正是**會讓 PRE-1 通過而 Bolt 1 失敗**。
>
> 加計本項後，本表為 **七項**（1／2／3／4／PRE-1-a／PRE-1-b／PRE-1-c），留痕檔為 `PRE-1-results.md`。完整理由見 `../decisions/0016-credential-topology-and-pre1-amendments.md`。

> **行號偏移告示（2026-08-31T00:31:34Z）。** 本檔本輪新增 PRE-1-c 一列與其註記段、Bolt 1 DoD 一行，**PRE-1 表之後的內容整體下移**。本 record 內多份 reviewer 查證記錄以 `bolt-plan.md:<行號>` 逐字引用本檔——那些引用**如實記載了審查當時所見**，不回改（回改等於竄改審查紀錄）。讀取舊引用時請以錨點（段落標題、表格列的識別字）而非行號定位。
>
> **附帶的系統性觀察**：本檔已被 ADR-0013／0014／0015／0016 反覆修訂，**部分行號引用在本輪之前就已失準**（例如多處以 `:51` 指稱「Bolt 1 的 Definition of Done」，而該行現為 Bolt 序列表的一列）。對持續被修訂的 artifact 使用行號引用，其失效是結構性的而非偶發——後續產出宜改用錨點引用。

**為什麼是關卡不是 DoD 條目**：PRE-1 存在的理由正是要在投入實作**之前**知道憑證走不走得通。把它併進 Bolt 1 的 DoD（[Q4=B]）等於實作完才發現拿不到權限。

## Bolt 序列

依 [Q3=A] **嚴格循序**：一次一個 Bolt 走完 3.1–3.7，前一個完成才開下一個的 gate。理由是 `deploy.yml` 的 `concurrency: deploy-10-10` 為 `cancel-in-progress: false`，兩個 Bolt 同時合併會排隊部署；且 squash-merge 假設每個 Bolt 對應 `ut` 上一個 commit，平行合併時順序不確定。

| Bolt | 名稱 | 單元 | 複雜度合計 | 承載故事 |
| --- | --- | --- | --- | --- |
| 1 | 推送後看板自己更新 | U-1、U-2、U-3、U-4、U-5、U-6、U-10a | L×1、M×4、S×2、XS×1 | S-1、S-2、S-3、S-4、S-5 |
| 2 | 每日對帳與可信度 | U-7 | L×1 | S-7、S-9 |
| 3 | 看板上的人工改動算數 | U-8、U-10b | M×1、XS×1 | S-6 |
| 4 | 持續生效的斷言 | U-9 | M×1 | S-10 |
| 5 | README 指路 | U-11 | XS×1 | S-11 |

S-8（通報）由 U-5 承載、隨 Bolt 1 出貨；[ug:unit-of-work-story-map.md] 的跨單元對照表顯示 S-2／S-3 各有一條 AC 橫跨 U-1 與 U-7，故兩者在 Bolt 1 與 Bolt 2 之間**分兩批完成**——這不是遺漏，是該 AC 的判定與清單成員身分本就分屬兩個單元。

### Bolt 1 — 推送後看板自己更新

- **單元**：U-1 映射與解析 composite action、U-2 受管區塊渲染與雜湊、U-3 看板客戶端、U-4 record 回寫與同步狀態、U-5 通報、U-6 正向同步 workflow、U-10a `ci.yml` 的回寫排除
- **是否為 walking skeleton**：**否**。`team.md` 定案 `skeleton: off`，本 Bolt 依一般 Bolt 處理。
- **信心假說**：一個新 intent 的 record 被推送之後，Project #16 在**無人操作**的情況下出現一則綁定的 issue 且 Status 正確；機制拿不準時看板保持沉默而不是寫入猜測；整個過程不干擾開發者當下正在跑的 CI。
- **可展示**：推一個新 record → 看板上出現 item（Status `Ready`）→ 推進一個 stage → item 的 Status 與自訂欄位跟著動 → 期間該分支既有的 `ci.yml` run 沒有被取消。
- **Definition of Done**：七個單元各自的完成判準（見 [ug:unit-of-work.md]）全部通過；`stories.md` 全域 DoD 中適用於本 Bolt 的項目（NFR-S2 憑證獨立 secret、NFR-S3 repo contract 通過、NFR-S4 不新增 DB、**全路徑無 LLM**、**測試資料策略**的 fixture 機制）成立；PRE-1 第 1／3／4 項已綠。**〔ADR-0015 §2 增列兩條（指標補於 2026-08-30T00:48:38Z）〕**
  - **PRE-1-b 已綠**（見上方 PRE-1 表）。
  - **PRE-1-c 已綠**（見上方 PRE-1 表）。**〔ADR-0016 §7 增列，2026-08-31T00:31:34Z〕** 判定為「已綠」的形式有兩種，**兩種都算通過**：(a) 四條寫入路徑在 `public_repo` 下全數成立 ⇒ 憑證以 `public_repo` 鑄造；(b) 任一條失敗 ⇒ 退回 `repo`，並在留痕中如實記載「`repo` 為**必要**而非便宜行事」。**未執行**則不算通過——那會讓 ADR-0006 的 IAM 面判定停在「處置待定」而被誤讀為已結案。
  - **揭露 `write_status` 回讀視窗的資料遺失路徑**：Projects v2 無 compare-and-swap，回讀與 mutation 之間的視窗內若有協作者改動，該改動會被**靜默丟失**——沒有反向 PR、沒有紅燈、沒有通報，每日對帳也不會發現（覆寫後看板與 record 一致）。這是一條使用者從未被告知的真實資料遺失路徑，**本條要求核可者看見它**，不是技術檢查。理由與被否決的替代方案見 `../decisions/0015-functional-design-upstream-amendments.md`。
- **為什麼是七個單元**：[ug:unit-of-work-dependency.md] 的同批次約束表第一列——U-6 單獨上線等於「機制開始寫看板但沒有寫入前回讀、沒有分岔通報、沒有回寫綁定」，`stories.md` 的 G1／G3 明文禁止；第三列 U-10a ＋ U-4 是真捆綁。兩條疊加即為七。這是**結構逼出來的下限**，不是把不相干的東西湊成一批。

### Bolt 2 — 每日對帳與可信度

- **單元**：U-7 對帳 workflow 與編排器
- **信心假說**：看板與 record 之間的落差會被每天發現並補平，而且「補平了幾筆、一致率多少」這個數字本身站得住——分母排除了機制正確地選擇不動作的情形（[ad:ADR-A5] 維持上游兩類排除）。
- **可展示**：手動觸發一次對帳 → 產出報告含補平計數、一致率（分母／分子）、三份獨立清單（`已暫停`／`無法解析`／`issue 與 Status 不相稱`）→ 人為造一筆落差 → 下一輪自動補平且計數 +1。
- **Definition of Done**：**〔ADR-0015 於本 gate 增列三條（指標補於 2026-08-30T01:31:09Z）——見 `../decisions/0015-functional-design-upstream-amendments.md`〕**
  - **§3**：對帳報告須能區分「今天沒處理到」與「今天處理了且一致」（U-7 的 R-3.4）。具體形式待 PRE-1 第 2 項實測 C-T5 之後決定，接手點在此登錄。
  - **§9**：NFR-O2 的「目標為 0」已被證實為結構性不可達，本 gate 須確認採用哪一種重新表述。
  - **§13**：`components.md` 的 reconcile 元件鏈補上 **C-4**（U-7 補平後回寫 `SyncState`，否則 U-6 的回讀守門每次都拿過期的 `expected`）；且 `actions/checkout` 必須釘 **`ref: ut`**（`schedule` 只在預設分支 `main` 觸發，而 `main` 落後於 `ut`，不釘就會拿過期 record 對帳且**靜默失真**）。規則落點為 U-7 的 R-6／R-7 群。 U-7 完成判準通過；PRE-1 第 2 項（單次操作上限實際值）已綠並反映在 [US:S-7 AC 3] 的上限設定；`stories.md` 全域 DoD 的**排程不衝突**（不與 `daily-digest` `0 23 * * 1-5`、`agentics-maintenance` `37 0 * * *`、`release-watch` `39 16 * * 1` 碰撞）成立。
- **上游契約缺口 G-1 的處置點**：[ug:unit-of-work.md] 標出 [US:S-2 AC 4] 要求對帳報告有「無法判定」清單，而 [ad:component-methods.md] 的 `ReconcileReport` 只有 `unparseable`——兩個 `reason_code` 不能互相頂替。修補落點為 functional-design 增設 `undecidable: [intent_id]`。**該 stage 為 CONDITIONAL 且 per-unit，U-7 那輪若被判為「無新資料模型」而 skip，這個修補會連帶被跳過**——本 Bolt 的 gate 必須確認它沒有被跳過。

### Bolt 3 — 看板上的人工改動算數

- **單元**：U-8 反向同步 workflow、U-10b 反向 PR 的高成本 workflow 排除
- **信心假說**：協作者在看板上拖動卡片之後，機制會把它變成一個**等人決定的 PR**，而不是在下一輪默默改回去；而且這個每日 PR 不會燒掉整個 runner 預算。
- **可展示**：在看板上改一張卡的 Status → 反向同步開出以 `ut` 為 base 的 PR，diff 不含 `aidlc-state.md` → 該 PR 開啟期間，正向同步對**該 intent** 暫停覆寫、對其他 intent 照常寫 → 該 PR 沒有觸發 `ui-regression`。
- **Definition of Done**：U-8 與 U-10b 完成判準通過；[ad:decisions.md] CAP-11 補評估標記為「未驗證」的 **over-suppression** 已實測（先例 `--all-intents` 開單一 PR 的形狀不同，[US:S-6 AC 3] 已含反例要求）。
- **排序約束**：U-8 必須在 U-6 之後（[Q1=C] 保留的不可覆寫排序邊）。U-8 先上而 U-6 尚無 FR-G3 暫停覆寫分支時，反向 PR 開啟的整段期間正向同步會把協作者的改動輾回去——正是本 Bolt 要交付的事會被自己破壞。

### Bolt 4 — 持續生效的斷言

- **單元**：U-9 自我測試 workflow
- **信心假說**：映射被改壞、判定邏輯被搬進 LLM agent step、憑證被用來做範圍外寫入——這三類回歸會讓 CI 紅燈，而不是安靜地上線。
- **可展示**：把映射的 `[?]` 改成 `In progress` → CI 紅燈且輸出指出預期與實得；把判定搬進 agent step → 靜態檢查失敗。
- **Definition of Done**：U-9 完成判準通過；PRE-1-a 已有結論——若 Rulesets 的 file-path restriction 不適用，[US:S-10 AC 5] 的第二個例子需回 user-stories 改寫，**本 Bolt 不得以「無機制可產生 403」為由把該 AC 標為通過**。
- **為什麼放在被測對象之後**：U-9 的 `depends_on` 含 U-6／U-7／U-8，它斷言的是端到端行為，被測對象不存在時斷言無意義。

### Bolt 5 — README 指路

- **單元**：U-11 README 指路段落
- **信心假說**：第一次接觸這個專案的人，從 README 找得到 Project #16。
- **可展示**：README 出現含 Project #16 連結的段落；`git diff --numstat` 對 `README.md` 的刪除行數為 0。
- **Definition of Done**：U-11 完成判準通過。
- **排序說明**：U-11 在依賴圖上是 L0（無入邊），技術上可以第一個做。**刻意放最後**——理由見 `risk-and-sequencing-rationale.md`「偏離拓撲順序之處」。

## 與上游的對應

本計畫的單元邊界、`kind`、依賴與同批次約束一律引自 [ug:unit-of-work.md]、[ug:unit-of-work-dependency.md] 與 [ug:unit-of-work-story-map.md]（2.7 Revision 1 已核可），元件歸屬引自 [ad:components.md]，故事與 AC 引自 `stories.md`，需求編號引自 `requirements.md`。本站**不新增**任何單元、不改動任何單元邊界，只選一條通過 DAG 的路徑。
