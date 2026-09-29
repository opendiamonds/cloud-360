<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-09-21T10:33:56Z — 修訂 1 冒出與 Q10／Q11 同型的張力：上游已把成本關注者改為直接服務對象、明言第一版就問得到答案，而能力 10 仍是 Should（不做也能上線）。依本輪稍早寫進 project.md 的規則（同型張力必須比照先例加開問題由使用者定案），開了 S11 而非自行裁量，定案為 A（升 Must，9/1）。這條規則在寫入後的第一個 stage 就派上用場。
- 2026-09-21T10:33:56Z — 本站上一輪寫的一句話被這次驗證了：「兩項 Should 排在最後，但不是因為它們是 Should——是因為技術依賴綁在序 2 與序 3 之後。即使升為 Must，順序也不會改變。」能力 10 確實升了 Must 而位置不變。把「位置由什麼決定」與「分級」分開寫，使這次修訂只需改分級欄，不需重排序。
- 2026-09-21T07:09:49Z — 抽象的衝突清單不足以讓人察覺答案讀反；**具體呈現「照此執行下一步會產出什麼」才有效**。本站先以矛盾偵測列出 S9 結果與 [Q1]／[Q3]／[Q5] 的三處衝突並明示「方向可能讀反」，使用者回覆「沒反，就是這樣」；直到 S10 把後果具體化為「兩項 Must 各自依賴一項 Should，故 Must 集合無法獨立交付」，使用者才主動更正為 8 Must／2 Should。下次遇到「答案與多處上游定案衝突且疑似讀反」時，直接推導到下一步的具體產出，不要停在衝突清單。
- 2026-09-21T02:56:24Z — feasibility 的 [F8] 是單選題，使用者選「有預算或成本上限」，**未選中**「有目標時程」。依 `scope-definition:c1`（未選中的選項不得被當成排除），時程並未被回答，故本站以 S7 補問硬期限，而非推定為「無期限」。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-28T22:28:51Z — **修訂 2 把新需求定為「新增能力 11」而非「取代能力 9」，是為了保住已交付的東西。** 能力 9 的定義逐字只有「專案 → 系統 → 架構圖 階層」六個字、指的是資料模型，而 `U4` 已經把三張表與遷移程序做完並 commit（1441 行，PR #650 開著）。取代會讓 `US9.1`／`US9.2` 兩則已核可故事與那些程式失去追溯目標，下游要重新掛點。並列則兩邊都成立：能力 9 是資料模型，能力 11 是其上的管理面。
- 2026-09-28T22:28:51Z — **四處衝突在提問前就查證到底，題幹才問得準。** 最關鍵的是 `Project_Admin` 已經是既有全域角色（`rbac.py:33`、`:288`）——若沒查到這一點，會照會議結論的字面把 `project_admin` 寫進需求，下游到 domain-design 才會撞上，那時 11 個角色與 330 列矩陣都已經被下游引用。同理 `users.role` 是單一字串、`require_story_action` 表達不了 per-project 角色，這決定了「兩層串聯」是唯一不動既有矩陣的形狀。

## Deviations
- 2026-09-21T10:33:56Z — Must 佔比由 80% 升為 90%，更高於 prioritization-frameworks.md 的 60% 建議上限。未再次 push back——[S8] 已就此 push back 過一次且決策者據以降級；本輪是前提變動後的再定案，且已在選項中揭露佔比後果。依 scope-definition:c5 如實記載佔比事實，不重複質疑同一件事。
- 2026-09-21T07:09:49Z — S9 的分級曾被記為反向（降 8 項、Must 僅 2 項）並據以在 S10 寫出「Must 集合無法獨立交付」的發現。使用者更正後，本站同步改了三處：S9 的答案與後果段、S10 的先行發現段（依賴方向由 Must→Should 改為 Should→Must，結論由「阻塞」改為「可獨立交付」）、以及「三處衝突失效、不得帶入 scope-document」的明記。依 `rough-mockups:rev1-c10`，更正須一路追到最下游的落點。
- 2026-09-21T02:56:24Z — 依 `scope-definition:c5`（單一決策者、依賴序已定的 backlog 不做 WSJF／RICE 數值評分——沒有真實輸入的相對分數是虛假精確），本站的 intent-backlog 將以 MoSCoW ＋ 依賴序表達優先，不產生任何數值分數。決策者為單一人由 intent-capture [Q8]=A 確認。
- 2026-09-21T02:56:24Z — stage 檔 Step 4 提及 value stream map，但 `produces` 清單未列該檔。依 `scope-definition:c3`（produces 清單是 artifact 集合的正式來源），value stream map 將併入 `scope-document.md` 的段落表達，不自創新檔。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-28T22:28:51Z — **能力 11 與能力 10 之間我刻意不列依賴，即使會議結論明講成本 agent 要取用 SLA／TPS。** 能力 10 的定義逐字是「辨識成本需求、路由到既有 `/api/cost/v1`、把狀態事件轉譯」——它不需要需求欄位就成立。能力 11 是讓它**更有用**，不是它成立的前提。列成依賴會憑空製造一條排序約束，而下游會把它當成不可覆寫的 DAG 邊。已在產出內寫明這個判斷與理由。
- 2026-09-28T22:28:51Z — **`system_admin` 這個名字在下游被我明文禁用。** 使用者選 A（就是既有的 `Platform_Admin`），若文件仍寫 `system_admin` 當別名，等於把剛在 S14 避免掉的同名異義問題換個位置再犯一次。作答後果段逐字寫死「不得再出現 system_admin 這個別名」。

## Tradeoffs
- 2026-09-21T10:33:56Z — S11 選 A（升 Must）而非 B（維持 Should）。B 的代價不是範圍小一點，而是與剛核可的上游直接矛盾——一個被寫成「直接服務對象」的角色在第一版可能完全沒被服務到，且需回跳改寫上游措辭。A 的代價是純粹的佔比數字，且實作量因成本 agent 已存在而只剩辨識、路由、狀態轉譯三件事。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-28T22:28:51Z — **能力 11 排序位置（序 2）的反向考量我寫進了產出，不只寫在這裡。** 風險優先把它拉早（per-project 授權層在本 repo 零前例，不確定性不亞於序 1 的遷移風險），但它是最晚提出的需求、設計資訊最少，早做等於用最少資訊設計。兩面都記在該列的排序理由裡，讓下游自己判斷要不要覆寫——而它是「風險優先」產生的位置，不是技術依賴，所以可覆寫。

## Open questions
- 2026-09-21T08:59:32Z — **上游前提已失效，待以 Modify 模式回跳修訂**。本 intent 的 intent-capture 查證 V2 記載「成本／FinOps 能力完全不存在，`FinOps_Analyst` 只是 RBAC 角色名」，該事實在當時為真，但 `ut` 已於 2026-09-20T14:43Z 合併 PR #647（cost-estimation-finops），成本能力現已存在且規模不小：`backend/cost/` 套件含 `estimate_intake_router` 與 `advice_stream_router`；`/api/cost/v1/` 下 6 條端點，其中 `GET /sets/{set_id}/advice/stream` 為**串流式成本建議**；前端有 `CostPage`（路由 `/cost`，`can('C1','view')` 者登入即導向）；`schema_rbac.sql` 有 `archive_diagram_cost`、`archive_diagram_cost_line`、`archive_cost_audit_event` 三表。故第一版的問題不再是「要不要做一個會回『尚未提供』的空殼」，而是「大腦要怎麼編排一個已經存在、且自身也有串流的成本 agent」——這是不同的問題，不是同一問題的細節修正。受影響落點經逐一核對為 8 處：intent-capture 的 V2／[Q6]=C／[Q11]=B、`intent-statement.md` 的 Target Customer 成本列與 Initial Scope Signal、`stakeholder-map.md` 的成本關注者定位、feasibility 的 S 條目與能力表成本列、`constraint-register.md` 的 C-T9／C-S2、scope-definition 的 S3／S9 與 `scope-document.md`／`intent-backlog.md` 的分級與序 9。使用者已裁決**跳回 intent-capture 以 Modify 模式修訂**（非 feasibility——過期事實與 Q6／Q11 的決定都在 intent-capture）。未於本 session 執行的理由：AI-DLC 框架於本 session 期間由 2.7.0 升級至 2.9.0，指令介面與 stage 協定均已變更，而本 session 載入的是 2.7.0 協定；以舊協定驅動新引擎執行會動到生命週期狀態並重走三道關卡的操作，風險是污染稽核紀錄。應由新 session 以 2.9.0 協定執行。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-28T22:28:51Z — **`projects.owner_user_id` 的 FK 沒有 `ON DELETE` 子句（`schema_rbac.sql:328`），所以今天刪除持有專案的使用者會直接 FK 違規失敗。** 會議結論要求「`project_owner` 帳號被移除時自動改選其他人為 `project_admin`」——那個繼任規則現在連執行的機會都沒有，因為刪除本身就會被擋。這不是本站能解的（屬資料模型設計），但它是一個**今天就存在的缺陷**，不是新需求帶來的，且 `U4` 已把這個 FK commit 進去了。指派給 domain-design，並須與 PR #650 的合併時機一起考慮。
- 2026-09-28T22:28:51Z — **子功能 agent 的記憶「被摘要並彙整」到能力 11 這條管道，本站只記為能力描述，沒有任何設計。** 已裁決 `U5`／`U8` 的 per-user 語意記憶與能力 11 是兩件事並存，但「從前者摘要到後者」是一條新的單向管道——誰觸發、多久一次、摘要由誰做、摘要進去之後可見範圍是什麼（前者預設最窄、後者是專案共享）。這四個問題一個都還沒答。
