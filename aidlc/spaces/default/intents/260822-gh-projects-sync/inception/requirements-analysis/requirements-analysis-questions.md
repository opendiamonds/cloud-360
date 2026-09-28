# Requirements Analysis Questions — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: requirements-analysis（Inception 2.3）· Record: 260822-gh-projects-sync
     Depth: Standard（~5-8 題）· 本檔為本 stage 的正式作答紀錄，是決策可追溯性的權威來源。
     每題請在 [Answer]: 後填入選項字母（可複選者以逗號分隔），或填 X 並附說明。 -->

## 上游輸入

- **intent-statement**（`../../ideation/intent-capture/intent-statement.md`）：問題陳述、四類受益者、三項成功指標。
- **scope-document**（`../../ideation/scope-definition/scope-document.md`，Revision 1）：CAP-1～CAP-11、Won't Have、上線前置依賴 P-1～P-5。
- **intent-backlog**（`../../ideation/scope-definition/intent-backlog.md`，Revision 1）：PU-0～PU-10 與依賴性質。
- **feasibility-assessment**／**constraint-register**（`../../ideation/feasibility/`）：Conditional GO、R-1～R-7、C-T1～C-T9／C-O1～C-O6／C-R1～C-R4、ADR-0006 四面向判定。
- **initiative-brief**（`../../ideation/approval-handoff/`，Revision 1）：U-1～U-7 未解項與其指派落點。
- **ADR-0013**（`../decisions/0013-aidlc-projects-sync-scoping.md`）與其修訂對象 **ADR-0012**。
- **codekb**（`aidlc/spaces/default/codekb/cloud-360/`，基準 `9307dbc`）：`architecture.md` 的「開發流程層架構（一）AI-DLC 狀態表徵」與「（二）gh-aw workflow 語料」兩節為本站出題的主要事實來源。

## 已由上游定案、本站不重問

依 `project.md ## Corrections`「宣稱某事已由上游定案並據此省略提問時，必須能引用該定案的具體選項字母或原文」，以下逐項附出處：

| 事項 | 已定案內容 | 出處（可逐字複驗） |
| --- | --- | --- |
| 映射層級 | intent → Project #16 的**一則 issue**；不涉及 story 層 | ADR-0013 §1 |
| 承載形式 | gh-aw safe-outputs；**不建 `scripts/`** | ADR-0013 §3；`constraint-register` C-T7 |
| 與主流程耦合度 | 不得在 `.claude/` 下新增任何檔案；觸發為 `on: push` 而非 stage／hook | ADR-0012 §6（ADR-0013 明示未修訂） |
| 觸發事件種類 | 推送與 PR 生命週期兩條；**PR 事件優先於推送** | `feasibility-assessment` 前提 2、[feas:Q2] [feas:Q9]；C-T8 |
| 綁定方式 | 自動建立追蹤項目的同一時機記錄識別碼並寫回 intent 紀錄，之後一律查表 | `feasibility-assessment` 前提 3、[feas:Q8] |
| 狀態欄位是否改動 | **維持既有 6 個選項不變**，只用其中三格表達開工後語意 | `constraint-register` C-T6、[feas:Q4] |
| 細粒度進展落點 | 外置到看板**自訂欄位**，欄位由機制自動建立；框架不支援則退回人工建立 | `scope-document` CAP-7、[scope:Q4] [scope:Q9] |
| 寫入前防護 | 寫入前回讀目標項目並比對，不符即中止並開 issue | CAP-6、[feas:Q10] |
| 失敗通報 | workflow 紅燈 ＋ 自動開 issue；對帳不一致亦視為失敗 | CAP-5、[intent:Q9] |
| 反向同步是否做 | **做**；一律開 PR，不直接推 `ut`；防迴圈沿用三道防線 | ADR-0013 §2；ADR-0012 §4 |
| 排除項 | 跨 repo 支援、自動關閉 issue、既有 71 個項目的一次性對正 | `scope-document` Won't Have W-2／W-3／W-4 |
| 憑證輪替與撤銷路徑 | 已判定為 ADR-0006 IAM 面的未定義處置，**已指派 raid-log 追蹤**，非本站決定 | `feasibility-assessment` ADR-0006 判定表 IAM 項、R-5 |
| CAP-11 的可行性補評估與驗證落點 | 已指派 **application-design**（U-6、U-7） | `initiative-brief` 未解項表 |

## 本站查證紀錄（非來源標籤，供題幹與選項引用）

本輪於 `9307dbc` 工作樹實地複驗，結果如下；下游引用時請以此處為準：

| # | 查證 | 結果 |
| --- | --- | --- |
| V-1 | `intents.json` 目前 `status: "in-flight"` 的列 | **4 列**：`260802-default`、`260802-last-login-column`、`260806-a1-a3-ux`、`260822-gh-projects-sync`。其中 `260802-last-login-column` 的狀態檔實為 `Status: Completed`（註冊表未翻，因其 7 個 operation stage 是 `[S]` 而非走完 `complete-workflow` 路徑） |
| V-2 | `git check-ignore -v aidlc/spaces/default/intents/260822-gh-projects-sync/.aidlc-sync-state.json` | **被忽略**，命中 `.gitignore:52` 的 `aidlc/spaces/*/intents/*/.aidlc-*` |
| V-3 | per-stage checkbox 值域 | 六值：`[ ]` 未開始／`[-]` 進行中／`[?]` 等待核准（gate 開著）／`[R]` 修訂中（使用者退回）／`[x]` 完成／`[S]` 經 `--stage`／`--phase` 跳過；另有**正交**的 `— EXECUTE`／`— SKIP` 後綴 |
| V-4 | 狀態檔 top-level `Status` 值域 | 只有 `Running`／`Completed` 兩值，**沒有「等待核准」**。`260806-a1-a3-ux` 的 gate 開著（`[?]`）但 `Status` 仍是 `Running` |
| V-5 | `260802-default` 的狀態檔結構 | **只有 1 個 H2**，沒有 `## Stage Progress`／`## Current Status`／`## Scope Configuration`／`## Session Resume Point`；任何 parser 對其每一個機器欄位都回 `null` |
| V-6 | stage 列集合跨 record 一致性 | **不一致**：`260816`／`260822` 的 CONSTRUCTION 有 8 列（含 `tcms-test-cases`），其餘三個 record 只有 7 列且完全沒有該行 |
| V-7 | 本 intent 的 record 版控狀態 | `260822-gh-projects-sync/` 整個目錄**目前 untracked**，`intents.json` 的對應新列亦只存在於工作樹 |
| V-8 | 現有 gh-aw 語料中的 Projects 使用 | **零先例**：11 個 workflow 無一宣告 `projects: read`／`projects: write`、無一使用 `projects` toolset、無一使用 Projects 相關 safe-output |

---

## Q1. stage 進展要如何映射到看板的 6 個 Status 選項？

看板有 6 格：Backlog / Nice to have / Ready / In progress / In review / Done。AI-DLC 側可讀的訊號有兩套（V-3、V-4）：per-stage checkbox 六值 ＋ 正交的 EXECUTE／SKIP 後綴，以及只有兩值的 top-level `Status`。[feas:Q4] 已定案不改動看板欄位、只用其中三格表達開工後語意，本題定義的是**那張對照表本身**——它是整個機制的核心功能需求，目前尚未存在。

A. **三態映射 ＋ 明確的「不映射」清單**：intent 誕生但尚無任何 stage 動過 → `Ready`；任一 in-scope stage 為 `[-]` 或 `[R]` → `In progress`；任一 stage 為 `[?]`（gate 開著等人核准）→ `In review`；workflow 完成 → `Done`。`Backlog` 與 `Nice to have` **不由機制寫入**，保留給人工分類。並明訂 `[S]`（被跳過的 EXECUTE stage）與 `— SKIP`（不在 scope 內）**兩者都不影響 Status**，但其差別必須寫進自訂欄位或 issue 受管區塊，不得抹平（保住 V-3 指出的「三種沒打勾其實是三件事」）。看得到的效果：看板能區分「正在跑」與「卡在等我核准」，而後者正是目前最常被遺忘的狀態。

B. **四態（把誕生態放進 Backlog）**：同 A，但「已誕生、IDEATION 尚未開始」→ `Backlog`；`Ready` 改為保留給「已通過 ideation 的 approval-handoff、可以進 INCEPTION」。看得到的效果：看板左側能看出哪些 intent 只是被登記、還沒真的排上。代價：機制會寫入 `Backlog`，人工把卡片拖進 `Backlog` 的動作與機制的判斷可能互相打架。

C. **兩態最小面**：只寫 `In progress`（workflow 進行中）與 `Done`（完成），其餘四格完全不碰。看得到的效果：衝突面最小、最不可能寫錯；代價是「卡在等我核准」這件事看板上看不出來，而 intent-capture 記載的既成失真正是這一類。

D. **維持 feasibility 的現狀假設：只把對照表寫進 agent 的提示，實際填哪一格由 agent 依 record 內容判斷**。這是 [feas:Q5] 目前記載的形狀（「該填哪個狀態仍由代理人判斷」）。代價：`project.md ## Forbidden` 明載 gh-aw 是 LLM 驅動、屬本 repo 三塊結構性盲區之一，且「決定性的映射邏輯應優先放在純 Actions 步驟」——本選項與該規則正面衝突，且 [feas:R-3] 已把「錯誤狀態靜默寫入」列為風險。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-23T15:33:48Z · Mode: guided · batch 1/2 -->

---

## Q2. 「這個 intent 現在的狀態」要以哪一個資料源為準？

V-1 實測：`intents.json` 的 `status` 與各 record `aidlc-state.md` 的 `Status` **已經分岔**——`260802-last-login-column` 在註冊表是 `in-flight`，在狀態檔是 `Completed`。成因不是 bug 而是機制（註冊表只在 `complete-workflow` 路徑翻轉）。codekb 對此的結論是：必須挑一個作為單一來源並寫明，或同步兩者並在分岔時明確報告，**不得靜默取其一**。

A. **以 `aidlc-state.md` 為準，分岔時照樣同步但一併開 issue 報告**：狀態檔是唯一帶 stage 粒度的來源（Q1 的對照表本來就要讀它）；註冊表只用來列舉有哪些 intent。偵測到兩者分岔時仍依狀態檔寫入看板，同時開一張 issue 記錄分岔的 intent 與兩邊的值。

B. **以 `aidlc-state.md` 為準，分岔時中止該 intent 的同步並開 issue**：同 A 的來源選擇，但把分岔視為「資料不可信」，該 intent 這一輪不寫入，等人處理。代價：一個舊 record 的陳年分岔會讓它永遠停在錯誤狀態。

C. **以 `intents.json` 為準**：註冊表是單一檔案、解析成本最低。代價：它只有 `in-flight`／`complete` 兩值（且沒有 `parked`／`abandoned`），Q1 的 `In review` 與任何 stage 粒度都做不到，等於把 Q1 壓成 C 選項的兩態。

D. **兩者都讀，取「較保守」的值**：例如任一來源說完成就當完成，或任一來源說進行中就當進行中（方向需指定）。代價：分岔會被靜默吸收，正是 codekb 點名不得為之的形狀。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-23T15:33:48Z · Mode: guided · batch 1/2 -->

---

## Q3. 遠端只看得到已 commit 的內容——「零人工更新」與「推送後 5 分鐘」要如何收斂？

這是本站發現的**最尖銳的矛盾**，兩邊都是已核可的內容：

- 已核可的目標：成功指標之一是**零人工更新**（`intent-statement`），約束 C-T8 訂下**推送後 5 分鐘**的延遲上限。
- 新查證的事實（V-7）：跑在 GitHub Actions 上的 workflow 看到的是已合併的快照。本 intent 自己的整個 record 目錄**現在就是 untracked**——它對遠端**不存在**。而「in-flight」正是看板最需要即時反映的那一段。codekb 的原話是：**同步的更新頻率不由 cron 決定，由「人什麼時候 commit 並合併 record」決定。**

A. **接受邊界，改寫指標的措辭**：同步在**任何分支的 push** 上觸發（含 `danniel/**`），5 分鐘上限改為「自 record 被推送起算」，並在需求文件明記「零人工更新」的範圍是「不需要人去改看板」，不含「不需要人 commit record」。看得到的效果：開發者照常 commit 就會同步，不需要額外動作；代價是尚未 commit 的本機進展看板上看不到。

B. **同 A，但只在 `ut`／`main` 觸發**：只同步已合併的狀態。看得到的效果：看板只反映「已進主幹」的事實，不會被 feature 分支上的中途狀態干擾；代價是 in-progress 的 intent 在合併前完全不出現在看板上，而那正是最需要可視性的階段。

C. **加一道本機保險**：同 A，另在 AI-DLC 的 stage 完成流程加一個提醒／檢查，讓 record 未 commit 時被指出來。代價：ADR-0012 §6 的硬約束是「與主流程零耦合、不得在 `.claude/` 下新增任何檔案」，任何掛在 stage 上的鉤子都會撞到它，需先評估是否構成違反。

D. **同 A，並讓排程對帳承擔補救**：接受即時性有洞，改由 CAP-4 的低頻對帳定期把落差補平，並把「對帳補平的次數」當成可觀測指標——次數高就代表 commit 習慣需要調整。

X. Other（請說明）

[Answer]: D  <!-- 2026-08-23T15:33:48Z · Mode: guided · batch 1/2 -->

---

## Q4. 遇到「讀不動」或「形狀不同」的 record 時，機制要怎麼辦？

V-5：`260802-default` 只有 1 個 H2，沒有 `## Stage Progress` 等四個區塊，任何 parser 對它的每一個機器欄位都回 `null`——這不是資料缺漏，是格式不同。V-6：stage 列的集合跨 record 不一致（`tcms-test-cases` 只存在於較新的 record），任何寫死 stage 清單的對映會在舊 record 上錯位。V-1：4 列 `in-flight` 中有 1 列與狀態檔分岔。

A. **明確跳過並記錄**：解析不出必要欄位的 record 一律跳過、不寫入看板，並在對帳報告中列為「無法解析」清單（不開 issue，避免每次對帳都紅燈）。stage 清單一律從各 record 的檔案本身解析，不寫死。

B. **明確跳過並開 issue**：同 A，但每發現一個無法解析的 record 就開 issue。代價：`260802-default` 是長期存在的結構性例外，這會變成每次對帳都重複開同一張 issue。

C. **跳過 ＋ 一次性白名單**：同 A，並把已知的結構性例外（目前只有 `260802-default`）明列在設定中，其餘無法解析者才進報告。看得到的效果：報告裡只剩真正的新問題。

D. **盡力而為**：解析不到 stage 粒度時退回用 `intents.json` 的 `status` 寫入粗略狀態。代價：與 Q2 的單一來源決定可能互相牴觸，需一併確認。

X. Other（請說明）

[Answer]: C  <!-- 2026-08-23T15:33:48Z · Mode: guided · batch 1/2 -->

---

## Q5. 反向同步要把看板端的變更寫回 record 的**什麼地方**？

ADR-0012 §2 的逐欄位真實來源訂下「**狀態歸 GitHub**」，ADR-0013 §2 採納並要求反向一律開 PR。但落點尚未定義，而這裡有一個真實的張力：`aidlc-state.md` 的 `Status`／`Current Stage`／checkbox **是 AI-DLC 引擎擁有的欄位**——`project.md ## Mandated` 與框架協定都規定狀態轉移一律由工具寫入，人工／外部改寫會與引擎的狀態機打架（例如把 `[?]` 改成 `[x]` 而 audit 沒有對應的 `GATE_APPROVED`）。

A. **寫進獨立的同步紀錄，不碰引擎欄位**：反向同步只把「看板上有人把這張卡片拖到 X、時間、操作者」寫進一個同步專用檔案，並以 PR 呈現給人審。引擎欄位一律不動。看得到的效果：協作者在看板上的操作留下痕跡且不會被下次同步彈回，但 record 的權威狀態仍由 AI-DLC 引擎維持。

B. **寫進 issue 的受管區塊外，record 不動**：把差異記在 GitHub 側（issue 留言），repo 完全不回寫。代價：ADR-0013 §2 的立論是「拖動的卡片會被下次同步彈回原位比沒有同步更糟」——若正向同步下一輪仍依 record 覆寫看板，本選項並未解決該問題，需一併決定正向是否要讓步。

C. **PR 直接修改 `aidlc-state.md` 的對應欄位**：字面符合「狀態歸 GitHub」。代價：與引擎的狀態機直接衝突（見上），且 audit shard 不會有對應事件，`/aidlc --status` 與看板會以另一種方式再度分岔。

D. **A ＋ 正向讓步**：同 A，並規定正向同步在偵測到「該 intent 有未處理的反向紀錄」時暫停覆寫該 intent 的 Status，直到 PR 被合併或關閉。看得到的效果：真正做到卡片不被彈回；代價是多一個狀態要維護。

X. Other（請說明）

[Answer]: D  <!-- 2026-08-23T15:37:56Z · Mode: guided · batch 2/2 -->

---

## Q6. 同步狀態檔要放哪裡？（ADR-0012 指定的位置實測放不進版控）

ADR-0012 §4 指定同步狀態記錄放 `<record>/.aidlc-sync-state.json`，並明載**需進版控**才能跨 runner 比對。V-2 實測：該路徑被 `.gitignore:52` 的 `aidlc/spaces/*/intents/*/.aidlc-*` 擋掉——ADR 指定的位置與它自己的要求互相矛盾，且 `.gitignore` 的該區塊來自 upstream 框架檔。

A. **改用不以 `.aidlc-` 開頭的檔名**，仍放在 record 目錄下（例如 `<record>/sync-state.json`）。看得到的效果：不動 upstream 檔、可進版控、與 record 同進退。代價：ADR-0012 的原文需要一條修訂註記。

B. **移出 record 目錄**，集中放一份（例如 `aidlc/spaces/<space>/sync-state.json` 或 `.github/` 下）。看得到的效果：一個檔案涵蓋全部 intent，對帳時只讀一次。代價：與「AI-DLC 產出一律位於 record 目錄下」的既有慣例不同，需明記為例外。

C. **改 `.gitignore` 加例外規則**（`!aidlc/spaces/*/intents/*/.aidlc-sync-state.json`）。看得到的效果：ADR-0012 原文不用改。代價：`.gitignore` 是 upstream 隨框架升級覆蓋的檔案，例外會在下次升級時消失且無人察覺——`project.md ## Forbidden` 已規定不得以改 upstream 檔來表達專案規則。

D. **不落地任何狀態檔**：每次同步都以回讀看板 ＋ 讀 record 現況即時比對，不保存上一輪狀態。看得到的效果：少一個要維護的檔案；代價是防迴圈三道防線中的「內容雜湊比對」需要另尋基準（需確認是否仍成立）。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-23T15:37:56Z · Mode: guided · batch 2/2 -->

---

## Q7. 排程對帳的頻率、與 PR 優先序的互動、以及多 intent 並行要怎麼定？

上游明載未決：`feasibility-assessment` 的 Assumptions「排程對帳的頻率尚未決定；其與 [Q9] 觸發優先序的互動亦未定義」，R-2「推送與 PR 兩條觸發可能互相覆寫，排程對帳與此優先序的互動未定」，R-6「框架的看板更新輸出有預設操作次數上限，多個 intent 同時推進時可能靜默截斷」（C-T5，上限值未確認）。V-1 顯示目前就有 4 個 intent 掛在 `in-flight`。另 codekb 記載現有排程時段為 `daily-digest` `0 23 * * 1-5`、`agentics-maintenance` `37 0 * * *`、`release-watch` weekly。

（可複選，請以逗號分隔）

A. **對帳每日一次**，避開既有排程時段（`daily-digest` `0 23 * * 1-5`、`agentics-maintenance` `37 0 * * *`、`release-watch` weekly）；每次涵蓋全部已綁定的 intent。

B. **對帳每 6 小時一次**，提高補救即時性；代價是 API 呼叫量與紅燈頻率上升。

C. **三條路徑共用一個 concurrency group、`cancel-in-progress: false`**：PR ＞ push ＞ 對帳的優先序以排隊而非取消實作，後到者等前者跑完再寫，確保最後寫入的是最新事實，並消除 [feas:R-2]「兩條觸發互相覆寫」的風險。

D. **先量測再定上限行為**：把「框架單次操作次數上限的實際值與超限行為（截斷／報錯／靜默略過）」列為 CAP-9 憑證實測的一併驗證項（目前 C-T5 上限值未確認，而 V-1 顯示已有 4 個 intent 掛在 `in-flight`）；未確認前對帳一次只處理固定數量的 intent。

X. Other（請說明）

[Answer]: A, C, D  <!-- 2026-08-23T15:37:56Z · Mode: guided · batch 2/2 -->

---

## Q8. 看板自訂欄位要承載什麼內容？

CAP-7 已定案細粒度進展外置到自訂欄位、欄位由機制自動建立（[scope:Q4] [scope:Q9]），但欄位裡放什麼尚未定義。可用的訊號見 V-3／V-6：目前 stage slug、所屬 phase、in-scope 進度計數（本 intent 為 19 個 EXECUTE stage）、以及 EXECUTE／SKIP 與 `[S]` 的區別。

A. **目前 stage 的 slug ＋ 編號**（例如 `requirements-analysis (2.3)`）。看得到的效果：看板上直接看得出卡在哪一站；代價是 stage graph 變動時字串會跟著變。

B. **所屬 phase**（`IDEATION`／`INCEPTION`／`CONSTRUCTION`／`OPERATION`）。看得到的效果：粒度較粗但穩定，不會因 stage graph 變動而失效，且可被看板的分組／篩選功能有效使用。

C. **stage slug ＋ 進度計數合併成一個字串**（例如 `requirements-analysis (2.3) · 7/19`）。看得到的效果：資訊最完整、一眼看出還剩多少；代價是分母隨 scope 不同而不同（跨 intent 不可比），且欄位值無法被分組／篩選有效使用。

D. **兩個自訂欄位**：一個放 A（stage）、一個放 B（phase）。看得到的效果：兼得可篩選與細粒度；代價是自動建立欄位的可行性本身就是未驗證項（U-2／P-4），建兩個等於把該風險加倍。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-23T15:37:56Z · Mode: guided · batch 2/2 -->

---

---

## 追問（Step 8 矛盾偵測的結果）

答案收齊後對全集做矛盾偵測與覆蓋檢查，發現三處**已選答案之間、或已選答案與已核可上游之間**的真實牴觸。三題皆為本輪新增，未被前八題涵蓋。

### F1. Q5=D 的「暫停覆寫」窗口，算不算違反「一致率為 0」的成功指標？

Q5=D 規定：正向同步偵測到該 intent 有未處理的反向紀錄時，**暫停覆寫它的 Status**，直到 PR 被合併或關閉。這正是它能阻止「卡片被彈回」的機制。但 `intent-statement` 的成功指標之一是「綁定到 AI-DLC intent 的 item 中，看板狀態與 record 實際狀態**不一致者為 0**」——在那個窗口裡，看板與 record **依設計就是不一致的**。兩者字面牴觸，必須明訂一個判定方式。

A. **窗口內不計入分母**：一致率的分母排除「有未處理反向紀錄」的 intent，並在對帳報告中另列為「等待人工裁決」清單。與 [intent:Q12]「沒有對應 record 的既有 item 不進分母」是同型的處理。
B. **窗口內視為一致**：只要反向紀錄已被正確捕捉且 PR 已開，就視為機制運作正常、計為一致。代價：一張長期沒人處理的 PR 會讓真實的不一致被計成一致。
C. **窗口內視為不一致，但設寬限期**：例如 PR 開啟 24 小時內不計入，超過才計為不一致並通報。看得到的效果：拖著不處理的 PR 會自己浮出來。
D. **不設窗口，改讓反向 PR 阻擋正向**：PR 未處理前該 intent 完全不同步（正向也不寫），一致率照算。代價：比 Q5=D 更強的停擺，且 record 端後續的真實進展也不會上板。

[Answer]: A  <!-- 2026-08-23T15:40:58Z · Mode: guided · follow-up -->

### F2. 綁定編號與同步狀態檔要以什麼路徑回寫進 repo？

CAP-1 要求「把 issue 編號寫回 intent 的紀錄」，Q6=A 又決定同步狀態檔 `<record>/sync-state.json` 需進版控——兩者都表示**正向同步必須寫回 repo**，但寫回的路徑從未被指定。ADR-0012 §5 的「一律開 PR、不直接推 `ut`」原文是針對**反向同步**，未涵蓋這兩項。Q3=D 又決定在**任何分支的 push** 上觸發，因此回寫本身也是一次 push，需與防迴圈第二道防線（`[aidlc-sync]` 來源標記）一併考慮。既有語料中 `push-to-pull-request-branch` 已被 2 支 workflow 使用（V-8 之外的既有事實）。

A. **回寫到觸發它的那個分支**：push 到 `danniel/xxx` 就寫回 `danniel/xxx`，commit 訊息帶 `[aidlc-sync]` 讓下一輪排除。看得到的效果：綁定編號與 record 同進同出，PR 合併時一起進 `ut`，不需要額外的 PR。
B. **一律開 PR 對 `ut`**：與反向同步同一條路徑、同一種審查。代價：每個 intent 誕生都會多開一張只改編號的 PR。
C. **用 `push-to-pull-request-branch`**：若觸發來自 PR 就推到該 PR 的分支；若來自非 PR 分支的 push 則延後到 PR 開啟時再寫。代價：沿用既有慣例但邏輯分支較多，且 intent 誕生到 PR 開啟之間綁定編號尚未落地。
D. **不回寫 repo**：綁定關係只存在 GitHub 側（例如以 issue 標題或標籤帶 intent slug 反查）。代價：直接推翻 [feas:Q8]「自動建立時記錄識別碼並寫回 intent 紀錄，之後一律查表」這條已核可的決定，需回跳修訂。

[Answer]: A  <!-- 2026-08-23T15:40:58Z · Mode: guided · follow-up -->

### F3. Q7=C 的「排隊不取消」與 C-T8 的「推送後 5 分鐘」如何並存？

Q7=C 決定三條路徑共用 concurrency group 且 `cancel-in-progress: false`（後到者排隊）。Q7=A 又決定對帳每日一次且**每次涵蓋全部已綁定的 intent**。C-T8 是已核可的硬約束：同步延遲上限為推送後 5 分鐘。若一次全量對帳正在跑，一個 push 觸發的同步會排在它後面——全量對帳的時間隨 intent 數線性增長，5 分鐘上限沒有任何機制保證。

A. **對帳與事件同步用不同的 concurrency group**：事件觸發（PR／push）共用一組維持排隊語意；對帳自成一組，兩者可並行，並由 CAP-6 的寫入前回讀承擔「同時寫入同一個 item」的防護。看得到的效果：5 分鐘上限只受事件佇列影響，不受對帳長度影響。
B. **對帳讓位**：對帳開始前先檢查有無事件同步在排隊，有就直接放棄這一輪、等下一次排程。看得到的效果：單一 group 的簡單模型維持不變；代價是繁忙期的對帳可能連續數輪不執行。
C. **對帳分片**：每次對帳只處理固定數量的 intent（與 Q7=D 的上限量測結果對齊），把單次執行時間壓在可預期的範圍內。看得到的效果：與 Q7=D 天然搭配；代價是全量涵蓋需要數輪才走完一圈。
D. **放寬 C-T8**：把 5 分鐘上限改為只約束「事件觸發且無對帳進行中」的情況，並明記對帳期間的延遲不計入。代價：修改一條已核可的約束，需在需求文件明記變更理由。

[Answer]: A  <!-- 2026-08-23T15:40:58Z · Mode: guided · follow-up -->

### F4. 被 `park` 的 intent 要映到哪一格？（reviewer iteration 1 的 Major 1）

reviewer 實測指出 Q1=A 的對照表**漏了第三種訊號**。本站已獨立複驗屬實：

- `aidlc-state.ts:842-843` 的 `park` 會把 `Parked`（時間戳）與 `Parked At Stage`（stage slug）寫進 `## Runtime State`，`unpark`（`:859-860`）才清除。
- **`park` 不改動任何 checkbox，也不改 top-level `Status`。** 因此被 park 的 intent 會沿用暫停當下的 checkbox（多半是 `[-]` 或 `[?]`），在現行對照表下被持續判為 `In progress`／`In review`。
- 目前 6 個 record **都沒有**設過這兩個欄位（`grep` 全部落空）——是「機制真實存在但尚未發生」的缺口，不是臆測。
- 連帶影響：FR-D2 的對帳範圍與 NFR-O2 的一致率分母目前都不排除已 park 的 intent，等於讓機制**持續宣稱一個已知暫停的 intent 正在進行**——正是 `intent-statement` 記載的核心痛點在本機制自己身上重演。

A. **凍結 Status ＋ 自訂欄位註記 ＋ 移出分母**：`Parked` 非空時機制**不改動**該 item 的 Status（維持最後已知值），但在 FR-F1 的自訂欄位寫出 `parked @ <Parked At Stage>`；同時把該 intent 移出 FR-D2 的對帳補平範圍與 NFR-O2 的一致率分母，另列為「已暫停」清單。看得到的效果：看板不會謊稱它在跑，暫停這件事在自訂欄位上看得見，且一致率的分母不含機制刻意不維護的項目——與 [F1=A] 對「未處理反向紀錄」的處理是同一形狀。代價：Status 那一格仍停在暫停當下的值（可能是 `In progress`），只有自訂欄位說得出真相。

B. **映到 `Backlog`**：`Parked` 非空 → 寫入 `Backlog`。看得到的效果：看板左側一眼看出它被擱置，不需要看自訂欄位。代價：與 [Q1=A] 已定案的「`Backlog`／`Nice to have` **不由機制寫入**，保留給人工分類」**直接衝突**，需明文開一個例外；且 `unpark` 時機制要能正確把它推回正確的格，多一條回復路徑。

C. **映到 `Ready`**：`Parked` 非空 → 寫入 `Ready`（等待重啟）。看得到的效果：不需要動用保留給人工的兩格。代價：與「已誕生、尚無 stage 動過」的 `Ready` 語意混淆——看板上兩種完全不同的處境會同格，觀看者分不出「還沒開始」與「做到一半停了」。

D. **完全排除，不表達**：`Parked` 非空時該 intent 不參與同步（不寫 Status、不寫自訂欄位），僅記入對帳報告的「已暫停」清單。看得到的效果：機制絕不寫錯，實作最單純。代價：卡片停在最後一次寫入的值且**看板上完全沒有線索**，比 A 少掉自訂欄位那條線索，觀看者看不出差別。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-23T23:03:39Z · Mode: guided · reviewer iteration 1 findings -->

### 追問後的第二輪矛盾偵測（本站判定，非新增提問）

F1-F3 收齊後再跑一次全集比對，另有兩項須記明，兩者都不另開題：

1. **F3=A 修訂了 Q7=C 的字面。** Q7=C 原文是「三條路徑共用一個 concurrency group」，F3=A 把它改為「**事件觸發兩路徑共用一組、對帳自成一組**」。下游一律以 F3=A 為準，不得直接引用 Q7=C 的「三路徑共用」。

2. **本機制需要 repo 內容寫入權，`feasibility-assessment` 的 ADR-0006 IAM 判定原文已不成立。** 該表 IAM 列寫的是「權限限縮為組織層看板讀寫，**不索取 repo 內容寫入權**」，但下列三項已核可決定各自都需要寫 repo：CAP-1「把 issue 編號寫回 intent 的紀錄」（[feas:Q8]，與 IAM 列同屬 feasibility 一站，該站自身即已內含此矛盾）、Q6=A 的 `<record>/sync-state.json` 進版控、ADR-0013 §2 的反向同步開 PR。F2=A 再加上「寫回觸發它的那個分支」。

   **處置（依 `project.md ## Corrections`「surface 之外還要 resolve」）**：requirements.md 的 IAM 需求本文直接寫成**加了適用前提的版本**——「組織層 Projects 讀寫 ＋ repo 內容寫入，後者的用途限於 record 目錄下的綁定編號與同步狀態檔、以及開 PR」——使字面不再衝突；並把「如何把 repo 寫入權收斂到最小」明列為 **application-design 的開放決策**（與 `initiative-brief` U-6 已指派的「IAM 面重新判定」合流），而非被動記載的已知限制。**本站不裁定收斂手段。**

---

## Consolidated Summary Confirmation

以下是本 stage 十二題的完整已答清單。**未取得 `Looks correct` 之前不得產出 `requirements.md`。**

> **Revision 1（2026-08-24，reviewer iteration 2 的 Major）**：本區塊原以「十一題」取得 `Looks correct`（`15:45:52Z`），但 F4 答於 `23:03:39Z`——晚於那次確認近 7.5 小時，故該確認**物理上不可能涵蓋 F4**，而 F4 正是 FR-B6／FR-F4／FR-D2／NFR-O2 四條需求的唯一依據。依 `project.md ## Corrections`（修訂新增的項目必須另行取得確認，不得沿用舊確認），本區塊補入 F4 與其後果，`[Answer]:` 清空重新取得確認。**Q1–Q8、F1–F3 的原答案與決議內容一字未動**；requirements.md 的 F4 相關內容已於 iteration 1 修正時寫入，本次確認是補上它缺少的確認關卡，不是要求重寫。

### 已答清單

| 題 | 主題 | 已選 | 決議內容 |
| --- | --- | --- | --- |
| Q1 | stage → Status 對照表 | **A** | 三態映射：誕生未動→`Ready`；任一 stage `[-]`／`[R]`→`In progress`；任一 `[?]`→`In review`；完成→`Done`。`Backlog`／`Nice to have` 不由機制寫入。`[S]` 與 `— SKIP` 皆不影響 Status，但兩者差別須寫進自訂欄位或受管區塊，不得抹平 |
| Q2 | 狀態的真實來源 | **A** | 以 `aidlc-state.md` 為準；`intents.json` 只用來列舉 intent。分岔時**照樣寫入**並另開 issue 記錄兩邊的值 |
| Q3 | commit 邊界 | **D** | 任何分支的 push 皆觸發；5 分鐘上限重新定義為「自 record 被推送起算」；「零人工更新」的範圍明記為「不需要人去改看板」，不含「不需要人 commit record」；由 CAP-4 對帳補救，且**對帳補平次數列為可觀測指標** |
| Q4 | 異常 record | **C** | 解析不出必要欄位者一律跳過不寫入；stage 清單一律從各 record 檔案本身解析（不寫死）；已知結構性例外（目前僅 `260802-default`）列入白名單，其餘無法解析者才進對帳報告 |
| Q5 | 反向同步寫回落點 | **D** | 只寫進同步專用檔案並開 PR，**引擎欄位一律不動**；且正向同步偵測到該 intent 有未處理的反向紀錄時**暫停覆寫其 Status**，直到 PR 合併或關閉 |
| Q6 | 同步狀態檔位置 | **A** | 改用不以 `.aidlc-` 開頭的檔名，仍置於 record 目錄下（`<record>/sync-state.json`）；ADR-0012 §4 原文需一條修訂註記 |
| Q7 | 對帳與並行 | **A, C, D** | 對帳每日一次且避開既有排程時段；優先序以**排隊而非取消**實作（`cancel-in-progress: false`）；框架單次操作次數上限的實際值與超限行為列為 CAP-9 實測的一併驗證項，未確認前對帳一次只處理固定數量的 intent |
| Q8 | 自訂欄位內容 | **A** | 承載目前 stage 的 slug ＋ 編號（例如 `requirements-analysis (2.3)`），單一欄位 |
| F1 | 一致率與暫停窗口 | **A** | 「有未處理反向紀錄」的 intent **不計入一致率分母**，另列為「等待人工裁決」清單（與 [intent:Q12] 同型處理） |
| F2 | 回寫路徑 | **A** | 綁定編號與 `sync-state.json` **寫回觸發它的那個分支**，commit 訊息帶 `[aidlc-sync]` 供下一輪排除 |
| F3 | 排隊 vs 5 分鐘上限 | **A** | **事件觸發兩路徑共用一組** concurrency group、**對帳自成一組**，兩者可並行；同時寫入同一 item 由 CAP-6 的寫入前回讀承擔防護 |
| F4 | 被 `park` 的 intent 映到哪一格 | **A** | `Parked` 非空時**不改動** Status（凍結於最後已知值），但 FR-F1 的自訂欄位寫出 `parked @ <Parked At Stage>`；該 intent 移出對帳補平範圍與一致率分母，另列「已暫停」清單 |

### 四項需要你一併確認的後果

這四項是上述答案的**直接後果**，不是新問題，但都會實際改變已核可文件的敘述（第 4 點為本次 Revision 1 新增）：

1. **`feasibility-assessment` 的 ADR-0006 IAM 判定原文已不成立。** 該表寫「權限限縮為組織層看板讀寫，**不索取 repo 內容寫入權**」，但 CAP-1（寫回 issue 編號，[feas:Q8]，與該判定同屬 feasibility 一站）、Q6=A（`sync-state.json` 進版控）、ADR-0013 §2（反向同步開 PR）三者各自都需要寫 repo，F2=A 再加上「寫回觸發分支」。requirements.md 會把 IAM 需求寫成**加了適用前提的版本**（組織層 Projects 讀寫 ＋ 用途受限的 repo 內容寫入），並把「如何把 repo 寫入權收斂到最小」列為 **application-design 的開放決策**（與 U-6 已指派的 IAM 重新判定合流）。**本 repo 最大的單一權限授予因此比 feasibility 當時預期的更大。**

2. **F3=A 修訂了 Q7=C 的字面。** 下游一律以「事件兩路徑共用一組、對帳自成一組」為準，不得引用 Q7=C 原文的「三路徑共用」。

3. **ADR-0012 §4 需要一條修訂註記**（Q6=A 改變了它指定的同步狀態檔路徑）。requirements.md 會把它列為交付項之一，實際落筆屬後續 stage。

4. **[F4=A] 已改寫 Q1=A 的對照表，且擴大了兩處排除集合**（本次新增，requirements.md 已寫入）。Q1=A 原本是純三態映射；F4=A 在其上加了一條**優先於全部四條**的規則：`## Runtime State` 的 `Parked` 欄位非空時，機制**完全不寫** Status（凍結於最後已知值），改由自訂欄位承載 `parked @ <Parked At Stage>`。連帶：FR-D2 的對帳補平範圍與 NFR-O2 的一致率分母**同時排除**「有未處理反向紀錄」（[F1=A]）與「已 park」兩類，兩處定義逐字一致。**看得見的後果**：一個被 park 的 intent，看板 Status 那格會停在暫停當下的值（多半是 `In progress`），只有自訂欄位說得出它其實停著——這是 F4=A 選項本文即已寫明的代價，不是新增的讓步。

### 確認

Does this all look correct before I generate the requirements artifact?

- **Looks correct** — 依這些答案產出 `requirements.md`
- **Request changes** — 有一題以上要改，改完重新確認

[Answer]: Looks correct  <!-- 2026-08-24T00:12:00Z · Mode: guided · Revision 1（補入 F4 後重新取得；原答案於 2026-08-23T15:45:52Z 取得，不涵蓋 F4） -->

---

## §13 Learnings（stage 結束儀式）

`aidlc-learnings.ts surface` 交出 6 個候選（c1–c6）與 2 項 parked open questions。下列為經 admission 預檢後**提請採納**的三項；未列入者的理由：c1（「已由上游定案」須可逐字引用）與 c4（改寫本文加適用前提＋指派下游開放決策）在 `project.md ## Corrections` 已有等價條文（`scope-definition:260822-c5`、`user-stories:c9`），屬套用既有規則而非新知；c3（F1–F3 皆為字面牴觸而非措辭模糊）與 c6（Q1 刻意不寫 `Backlog`／`Nice to have` 兩格）是本輪的描述性紀錄，抽不出可複用的判準。

第三項（L3）不在 surface 清單內，是本輪 reviewer iteration 2 的 Major finding 6 本身的教訓。

### L1. 要採納哪些學習寫進 `project.md`？（可複選）

A. **[c2] 選項數超過 harness 上限時，先改問題檔再提問**：AskUserQuestion 每題上限 4 個選項；當問題檔寫了 5 個以上，正確處置是**先把問題檔收斂成 4 個**（合併語意相近的選項並記明合併方式）再提問，而不是提問時臨時換一組。理由：問題檔是 stage 的正式來源，下游與 reviewer 都拿它複驗；若它寫 5 個而實際只問了其中 4 個，`[Answer]` 指向的選項字母在兩份紀錄中含意不同，且無人會察覺。

B. **[c5] 沒有替代解的事項不出成題目，改在確認點揭露後果**：當某個結果是多項已核可決定各自逼出的唯一解（本輪：CAP-1、Q6=A、ADR-0013 §2 三者都需要 repo 寫入權），出一題只會是單一可行解的假選擇。正確處置是在 Consolidated Summary Confirmation 明白揭露其後果（含它比上游當時預期更大／更重的部分），讓使用者在按下 `Looks correct` 前看到。理由：假選擇會讓紀錄看起來像有人選過，實際上沒有；揭露則保住知情確認。

C. **[L3] 在 Consolidated Summary Confirmation 之後才新增的追問，必然不被該確認涵蓋**：任何在確認取得**之後**才作答的追問（典型來源是 reviewer findings 觸發的補問），其確認缺口是**結構性**的，不需要判斷——時間戳先後即可機械判定。處置是新增追問的**同一個動作**就要補進確認清單並清空 `[Answer]:` 重新取得確認，不是等下一輪 reviewer 來抓。理由：既有的「修訂新增的項目必須另行取得確認」（`approval-handoff:260823-rev1-c1`）講的是判斷原則，本條給它一個零判斷的觸發時機與機械檢查（比對 `[Answer]` 註解的時間戳與確認區塊的時間戳）。

D. **以上皆不採納**

[Answer]: A, B, C  <!-- 2026-08-24T00:20:00Z · Mode: guided · §13 -->

### L2. 還有什麼要補進來的嗎？

A. **Nothing to add** — 就上面選的那些
B. **Add a note** — 我有一項要自己寫

[Answer]: Nothing to add  <!-- 2026-08-24T00:20:00Z · Mode: guided · §13 -->
