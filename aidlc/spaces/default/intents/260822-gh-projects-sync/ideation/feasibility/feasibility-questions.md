# Feasibility & Constraints — 釐清問題

> Stage: feasibility（Ideation 1.3）· Depth: Standard · Scope: aidlc-github-projects-sync
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> 上游輸入：`../intent-capture/intent-statement.md`（intent-statement）。market-research 依 scope 設計跳過，其可選輸入（competitive-analysis、market-trends、build-vs-buy）不存在。

## Sources

查證事實（僅用於出題與選項設計，依 ideation 規則不寫入產出 artifact 的設計層）：

### 外部文件（本輪實際查證）

- [ext:E1] GitHub Docs — `GITHUB_TOKEN` 為 repository-scoped，**Projects v2 的讀與寫都不在其範圍**（org 與個人 project 皆然）；以 `GITHUB_TOKEN` 查詢 `projectV2` 節點會回空清單且不報錯。必須改用 PAT 或 GitHub App。<https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects>
- [ext:E2] gh-aw《Authentication (Projects)》— 支援兩種憑證：fine-grained PAT（org 專案需 `Organization Projects: Read and write`）或 GitHub App token（需 `Organization projects: Read and write`）。gh-aw 認得的 secret 名稱為 `GH_AW_WRITE_PROJECT_TOKEN`（寫）與 `GH_AW_READ_PROJECT_TOKEN`（讀）。<https://github.github.com/gh-aw/reference/auth-projects/>
- [ext:E3] gh-aw《Safe Outputs》— `update-project` safe-output 可對既有 issue 設定欄位，agent 輸出形如 `{"type":"update_project","content_type":"issue","content_number":123,"fields":{"Status":"In progress"}}`；**欄位名不分大小寫且會自動正規化**，single-select（如 Status）可直接以選項名稱設定；`max` 預設 10 次操作；需 write-capable token。另有 `projects` toolset 供讀取 project item 與欄位值。<https://github.github.com/gh-aw/reference/safe-outputs/>
- [ext:E4] 同上 — gh-aw 另有 `create-issue`、`add-comment`、`dispatch-workflow`、`create-check-run` 等 safe-output，可承載 [intent:Q9] 要求的失敗通知。

### 本 repo 現況（本輪實際查證）

- [repo:R1] `aidlc/spaces/*/intents/*/aidlc-state.md` **在版控內**；`.gitignore` 只排除 `active-intent` cursor、`.aidlc-clone-id`、`runtime-graph.json`、`.aidlc-*` 與 `.aidlc-sessions/`。`git ls-files` 確認既有 intent 的 state 檔已被追蹤。CI 讀得到它，但**只讀得到已 commit 並 push 的狀態**。
- [repo:R2] AI-DLC 的 stage 推進發生在**開發者本機**（`aidlc-orchestrate.ts report` 就地改寫 record 內的 `aidlc-state.md`）。在 push 之前，GitHub 端看不到任何變化。
- [repo:R3] repo 內既有 12 組 gh-aw workflow（`.md` 與 `.lock.yml` 成對）。已使用的 safe-outputs 僅 `create-issue`、`add-comment`、`add-labels`、`close-issue`、`push-to-pull-request-branch`；toolsets 僅 `context`、`repos`、`issues`、`pull_requests`、`actions`。**零 Projects 使用先例**，全部 `engine: copilot`。
- [repo:R4] repo 內沒有任何 workflow 使用 PAT 或 GitHub App token；`deploy.yml` 的 secrets 全是部署用值（POSTGRES_PASSWORD 等），與 GitHub API 權限無關。新增 project 憑證是**本 repo 的第一把 GitHub API 憑證**。
- [repo:R5] gh-aw 的 `.lock.yml` 目前**不受任何 CI 閘門驗證**；`ci.yml` 的四個 job（repo-contract、frontend、backend、docker-build）都不涵蓋它。
- [repo:R6] Project #16「Cloud-360 開發計劃」（`PVT_kwHOD75-tc4BXNPF`）Status 欄位 id 為 `PVTSSF_lAHOD75-tc4BXNPFzhSbt0w`，6 個選項：Backlog / Nice to have / Ready / In progress / In review / Done。目前 71 個 item，Done 66、In progress 2、In review 1、Backlog 1、Nice to have 1。
- [repo:R7] 本 intent 的 scope 執行 33 個 stage 中的 19 個，橫跨 IDEATION / INCEPTION / CONSTRUCTION 三個 phase（OPERATION 全數 SKIP）。

### 上游已定案（不重問）

- [intent:Q6] 同步節奏：事件驅動即時更新 ＋ 低頻排程對帳。
- [intent:Q9] 失敗通知：workflow 紅燈 ＋ 自動開 issue；排程對帳發現不一致亦視為需通知的失敗。
- [intent:Q12] 一致率的分母只涵蓋已綁定到 AI-DLC intent 的 item；未綁定的既有 item 不進分母。
- [intent:Q7/Q11] 需求清單正本在 Project #16；README 只加一段指路文字，不改結構。
- [intent:Q5] 單一決策者；其他 repo 協作者為受影響方，告知即可。

### 規則層

- [memory:M1] `project.md#Forbidden` — NEVER 以 repo 內新增的實作程式承載流程自動化與外部系統同步；此類機制一律以 gh-aw 或 GitHub Actions workflow 承載。
- [memory:M2] `project.md#Mandated` — ALWAYS 對每一項變更檢查 ADR-0006 security baseline 的四個面向（IAM、encryption、network exposure、audit logging）。
- [memory:M3] `project.md#Mandated` — 每個 intent 的 construction 必經 `tcms-test-cases` stage 並完成覆蓋盤點、手動測案、**實際寫出並跑綠的自動化腳本（含突變驗證）**、TCMS 同步（blocking）。
- [memory:M4] `team.md#Deployment` — CI 四道關卡為 repo-contract → frontend → backend → docker-build，皆在 PR 與 push 觸發。

---

## Q1. CI 端要用哪一種憑證存取 Project #16？

> 查證：`GITHUB_TOKEN` 讀寫 Projects v2 都不行 [ext:E1]，gh-aw 只認 fine-grained PAT 或 GitHub App [ext:E2]。你先前決定的「幫 `opendiamonds` 帳號補 project scope」是針對**你本機的 `gh` CLI**，不會給 CI 任何權限——這是兩把不同的鑰匙。本 repo 目前沒有任何 GitHub API 憑證先例 [repo:R4]，所以這是第一把。

A. Fine-grained PAT — 以你的帳號開一把，權限限縮為 `Organization Projects: Read and write`，存成 repo secret `GH_AW_WRITE_PROJECT_TOKEN`。最快，但綁在個人帳號上：你離開或 token 到期，同步就停。
B. GitHub App — 在 org 安裝一個 App，權限 `Organization projects: Read and write`，以 App token 認證。與個人帳號解耦、可稽核到 App 身分，但要多做一次 App 建置與私鑰保管。
C. 先用 PAT，之後遷移到 App — 本次以 A 落地，並把「遷移到 App」列為明確的後續待辦而非模糊願望。
D. 都不用 — 放棄 CI 自動寫入，改為本機手動觸發（此選項與 [intent:Q6] 的事件驅動定案相衝突，選它等於要改上游決定）。
E. Not yet defined — 留到設計階段再定。
X. Other (please specify)

[Answer]: B

## Q2. 「事件驅動」的事件是什麼？

> 查證：AI-DLC 的 stage 推進發生在你的本機，改寫的是 record 內的 `aidlc-state.md` [repo:R2]；該檔在版控內 [repo:R1]，但 GitHub 在 **push 之前完全看不到**。所以「stage 一完成就即時更新」在 GitHub 側沒有可掛的鉤子——除非改由本機推送。這是 [intent:Q6] 的「事件驅動」在實作面必須先解決的落差。

A. push 觸發 — workflow 於 push 到任何分支且異動 `aidlc/spaces/*/intents/*/aidlc-state.md` 時執行。語意最貼近「狀態變了就同步」，延遲＝你多久 push 一次。
B. PR 生命週期觸發 — 以 PR 開啟／更新／合併為事件（配合 stage→Status 對應，PR 開啟≈In review、合併≈Done）。與現有 CI 的觸發模型一致，但看不到 PR 之前的 ideation／inception 進展。
C. A ＋ B 兩者都要 — push 反映細粒度 stage 進展，PR 事件反映交付里程碑。覆蓋最完整，代價是兩條觸發路徑都要維護且可能互相覆寫。
D. 只靠排程 — 放棄事件驅動，純靠低頻排程掃描補齊（等於把 [intent:Q6] 的 C 降級為 B，需要你確認改變上游決定）。
E. Not yet defined
X. Other (please specify)

補充：不論選哪一項，請一併說明可接受的**最大延遲**（例如「push 後 5 分鐘內」「當天內」），這會成為可驗證的成功條件。

[Answer]: C

## Q3. 一個 AI-DLC intent 要怎麼對應到 Project #16 的某個 item？

> 查證：目前雙方都不記得對方——`aidlc-state.md` 沒有 issue 編號欄位，Project item 也沒有 intent 識別碼 [repo:R1][repo:R6]。`update-project` 需要明確的 `content_number`（issue 編號）才能設欄位 [ext:E3]，所以綁定機制不存在就寫不進去。這是整個機制的地基。

A. intent 記住 issue — 在 intent 的 record 內放一個宣告檔（或 state 欄位）寫明它對應哪個 issue 編號，由開新 intent 時填寫。單向、明確、可被機器讀取；代價是多一個要人維護的欄位。
B. issue 記住 intent — 在 issue body 放一行 intent record 名稱（例如 `AI-DLC: 260822-gh-projects-sync`），workflow 反查。不用改 AI-DLC 的檔案格式；代價是散在 71 個 item 上、無法用檔案 diff 驗證。
C. 靠分支名稱推導 — 由 `<uploader>/<type>/<slug>` 的 slug 對回 intent，再由 PR 關聯的 issue 找到 item。零額外維護；但 slug 與 intent 名稱不保證一致，最脆弱。
D. 由 agent 依標題語意比對 — 讓 gh-aw 的 LLM 自行判斷哪個 item 對應這個 intent。零設定；但錯配是靜默的，且會直接寫壞真實看板。
E. Not yet defined
X. Other (please specify)

[Answer]: D
>
> **⚠️ 本答案已由 Q8=A 取代為 A**：綁定改為在自動開 issue 時把編號寫回 intent record，之後查表不猜。原答案保留作為決策軌跡，不改寫。

## Q4. 19 個執行中的 stage 要怎麼對應到 6 個 Status？

> 查證：本 intent 的 scope 執行 19 個 stage，橫跨三個 phase [repo:R7]；Status 只有 6 個選項，其中 Backlog／Nice to have／Ready 語意上都在「還沒開工」之前 [repo:R6]。也就是說真正能表達「進行中」的只有 In progress／In review／Done 三格，粒度落差很大。

A. 三態粗對應 — intent 誕生→In progress；PR 開啟→In review；workflow 完成或 PR 合併→Done。最簡單、最不會錯，但看板上看不出 19 個 stage 走到哪。
B. 依 phase 對應 — IDEATION／INCEPTION→In progress；CONSTRUCTION→In progress（同格）；PR 開啟→In review；完成→Done。實質與 A 幾乎相同，因為 Status 欄位撐不出更多格。
C. 三態 ＋ 進度寫在別處 — Status 用 A 的三態，細粒度的 stage 進展改以 issue 留言或 item 的其他欄位承載（Project 可加自訂欄位）。看板可讀性最好，代價是要新增欄位並多一條寫入路徑。
D. 加開 Status 選項 — 修改 Project #16 的 Status 欄位、新增對應 AI-DLC phase 的選項。表達力最強，但會改動一個已有 71 個 item 的既有欄位，影響現有所有 item 的語意。
E. Not yet defined
X. Other (please specify)

[Answer]:C

## Q5. 哪些邏輯必須是決定性的（純 Actions 步驟），哪些可以交給 gh-aw 的 agent 判斷？

> 查證：`update-project` 是 gh-aw 的 **safe-output**——agent 產出結構化 JSON，實際的 GraphQL 變更由框架執行 [ext:E3]，所以「寫入動作」本身已是決定性的。真正由 LLM 決定的是「該填哪個 Status」與「該對哪個 item」。同時 `project.md` 記載「所有 LLM 路徑」是本 repo 三塊結構性盲區之一，而 `.lock.yml` 目前不受任何閘門驗證 [repo:R5]。

A. 映射全決定性 — stage→Status 與 intent→item 的判定都寫成純 Actions 步驟（讀檔、查表、呼叫 `gh`），gh-aw 只用在失敗時撰寫 issue 內容這種真正需要判斷的地方。可驗證性最高。
B. 全部交給 gh-aw — 單一 agentic workflow 讀 record、判斷狀態、產出 `update_project` safe-output。實作最少，但整條核心邏輯落在無法斷言的路徑上。
C. 混合但以 gh-aw 為主 — gh-aw 負責讀取與判斷，但映射規則以一份明確的對照表寫在 workflow 的 prompt 中，並要求 agent 逐項引用。介於兩者之間，可驗證性取決於 prompt 紀律。
D. Not yet defined — 留到 application-design 定案。
X. Other (please specify)

[Answer]:C

## Q6. 沒有 repo 內腳本可以寫 unittest，這個機制要怎麼證明它是對的？

> 查證：`project.md` 的 `tcms-test-cases` 是 blocking stage，要求**實際寫出並跑綠的自動化腳本並做突變驗證** [memory:M3]；但 [memory:M1] 禁止以 repo 內程式承載本機制，而 `.lock.yml` 不受任何閘門驗證 [repo:R5]。這兩條規則在本 intent 相交，驗證落點必須在本階段就決定，不能留到 construction 才發現無處可放。

A. 對真實的測試 item 做端到端驗證 — 在 Project #16 建一個專用的測試 item，workflow 於 CI 中對它實際寫入並讀回斷言。碰得到真實 API 與真實權限；代價是會在正式看板上留下一個測試用 item。
B. 對另開的測試 Project 驗證 — 另建一個拋棄式 Project 當測試標的，不污染 #16。乾淨；代價是測試環境與正式環境不同（權限、欄位 id 都不同），漏掉的正是環境差異類缺陷。
C. 只驗映射邏輯 — 把 stage→Status 的對照抽成可獨立執行的檢查（例如 workflow 內的 dry-run 步驟輸出預期結果並比對），不碰真實 API。可在 CI 穩定執行；但完全不驗證權限與 API 契約。
D. A ＋ C — 映射邏輯用 dry-run 斷言，另加一個對真實測試 item 的端到端 case。覆蓋最完整，工作量最大。
E. Not yet defined
X. Other (please specify)

[Answer]:D

## Q7. 一個新 intent 誕生時，要不要自動在 Project #16 建立對應的 item？

> 查證：[intent:Q12] 已定「一致率只算已綁定的 item」，但沒有定「綁定怎麼開始」。目前 71 個 item 都是既有 issue [repo:R6]，而新 intent 未必有對應 issue（本 intent 自己就沒有）。`update-project` 可以把既有 issue 加進看板，`create-issue` 可以開新 issue [ext:E3][ext:E4]。

A. 不自動建立 — 只同步「已經有對應 item」的 intent；沒有綁定的 intent 就不同步，由你手動決定要不要建。範圍最小、最不會產生垃圾 item。
B. 自動開 issue 並加入看板 — intent 誕生時自動開一張 issue、加進 Project #16、設為 In progress。完全自動；代價是每個實驗性或被放棄的 intent 都會在看板上留下痕跡。
C. 提示但不自動 — 偵測到沒有綁定的 intent 時開一張提醒 issue（或留言），由你決定要不要建立正式 item。折衷。
D. Not yet defined
X. Other (please specify)

[Answer]: B

---

## 追問（第一輪答案分析後）

編號延續 Q1–Q7。來源為矛盾偵測與完整性檢查。

## Q8. Q3=D（LLM 語意比對綁定）與 Q7=B（自動開 issue 並加入看板）互相抵觸

> Q7=B 之下，workflow 在 intent 誕生時自己開出 issue——**那一刻 issue 編號是這個動作的直接產物，綁定是已知事實，不需要推測**。Q3=D 卻選擇事後由 LLM 依標題語意猜測對應的 item。系統等於先握有確定答案、丟掉它、之後再用猜的。
> 此外 Q3=D 之下沒有持久的綁定紀錄，[intent:Q12] 定義的「已綁定到 AI-DLC intent 的 item」集合每次執行都可能不同，一致率指標失去分母；intent-capture 的「可追溯」指標（每次 Status 變更都能說出是哪個 intent 觸發）也一併弱化。

A. 改為確定綁定 — 沿用 Q7=B 自動開 issue 的時機，把產生的 issue 編號寫回 intent 的 record（等同 Q3-A），之後所有同步查表不猜。Q3 的答案隨之改為 A。
B. 維持 Q3=D — 接受 LLM 語意比對，並同時接受一致率與可追溯兩項成功指標在本次無法嚴格判定（等於要下修 intent-capture 已核可的成功指標，需明確確認）。
C. 雙軌自我修復 — 有綁定紀錄就查表；沒有紀錄時才由 agent 推測，並把推測結果寫回成為往後的紀錄。
D. 改 Q7 而非 Q3 — 不自動開 issue（Q7 改為 A 或 C），語意比對只用在既有 item 上。
E. Not yet defined
X. Other (please specify)

[Answer]:A. 改為確定綁定 — 沿用 Q7=B 自動開 issue 的時機把 issue 編號寫回 intent record，之後查表不猜；Q3 隨之改為 A

## Q9. Q2 的最大延遲未填，且兩條觸發路徑需要優先順序

> Q2=C 選了 push ＋ PR 兩條觸發，但題目要求一併說明的「可接受最大延遲」沒有填。另外兩條路徑都會寫 Status：PR 開啟寫入 In review 之後，一次 push 可能把它蓋回 In progress——選項本文已標明「可能互相覆寫」是 C 的代價，需要一條優先規則才不會來回跳。

A. push 後 5 分鐘內；PR 事件優先於 push — 里程碑狀態不被細粒度進展覆寫
B. push 後 5 分鐘內；push 優先 — 永遠反映 record 的最新狀態
C. 當天內即可 — 放寬到由排程對帳達成最終一致；PR 事件優先
D. Not yet defined — 延遲與優先序留到設計階段定案
X. Other (please specify)

[Answer]:A. push 後 5 分鐘內；PR 事件優先於 push

## Q10. Q6=D 的兩層驗證都抓不到「錯綁」

> Q6=D 是映射邏輯 dry-run 斷言 ＋ 一個真實測試 item 的端到端。前者只驗 stage→Status，後者只驗一個已知 item——**兩者都驗不到「把對的 Status 寫到錯的 item」**。而錯綁是會直接寫壞真實看板的靜默失敗，且在 Q3=D 之下是最可能發生的失敗模式。本題不論 Q8 選什麼都成立。

A. 寫入前回讀確認 — 每次寫入前先讀該 item 的標題與編號並與預期比對，不符就中止寫入並開 issue
B. 白名單限制 — 同步只對「有明確綁定紀錄」的 item 動作，沒有紀錄的一律不碰
C. 事後對帳偵測 — 由排程對帳比對 record 與看板，不一致就開 issue（接受錯誤先發生、之後才修）
D. 不特別處理 — 接受錯綁風險
X. Other (please specify)

[Answer]:A. 寫入前回讀確認 — 比對不符即中止寫入並開 issue

---

## Consolidated Summary Confirmation

在依這些答案產出 feasibility-assessment.md、constraint-register.md 與 raid-log.md 之前，請確認彙整內容正確。

A. Looks correct — 依這些答案產出 artifact
B. Request changes — 先修改一個以上的答案再產出
X. Other (please specify)

[Answer]: A. Looks correct（使用者原文回覆「continue」，於閱讀彙整後指示繼續；未使用選單作答，故此處記錄其原文與解讀）