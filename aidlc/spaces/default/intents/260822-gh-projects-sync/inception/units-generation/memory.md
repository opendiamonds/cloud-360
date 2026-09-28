<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-08-27T23:04:37Z — 切分先盤出本設計實際有**六種不可互相替代的驗證方式**（純函式 fixture／純文字雜湊／真實 Projects API／git 與 repo 行為／Issues REST／workflow 執行期），再讓單元邊界落在這六類上。這使 [Q1] 的選項不是抽象偏好而是「哪一種切法會讓單一單元同時指涉兩種判準」。
- 2026-08-27T23:04:37Z — 第⑥類（workflow 執行期）**拆成四個單元而非一個**：四支 workflow 的失敗模式彼此不同（事件觸發／排程產報告／開 PR 防迴圈／CI 紅綠）。這是 11 個單元略高於 [Q2=A] 的 8–10 的唯一原因，在計畫核可關卡向使用者明示後才產出。
- 2026-08-27T23:04:37Z — 故事與單元**刻意用兩把不同的尺**：故事依「可觀察的成果」切（user-stories [Q2=A]），單元依「驗證方式」切（本站 [Q1=A]）。五則故事因此橫跨多個單元——這是必然而非缺陷，已在 story map 明記理由。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-29T03:54:57Z — Revision 1：把 U-10 拆為 U-10a（`ci.yml` `paths-ignore`，消費端 U-4）／U-10b（反向 PR 的高成本 workflow 排除，消費端 U-8）。判準來自 `project.md` 的 `cid:units-generation:c6`「驗證方式**與失敗模式**是否同類」——rev0 只套用了前半（兩者都是建置與觸發設定）就合併，漏掉後半（失敗模式分別是開發者 CI run 被取消 vs 反向 PR 燒約 6 小時 runner）。reviewer 獨立複驗後認定拆分正當，並指出 rev0 自己的邊表就已明列 U-10 有兩個消費端。

## Deviations
- 2026-08-27T23:31:37Z — **同型傳播失敗第三次發生，而且是在我剛採納那條教訓、也確實做了掃查之後**。reviewer iteration 2 抓到「跨單元的故事」表仍寫 S-2 為 `U-1、U-6`、S-3 為 `U-1、U-3、U-5`，都漏了剛補上的 U-7。根因不是沒掃，是**掃的方式錯**：我按「本輪改過的字串」grep，而那張表用不同的形式表達同一個事實（「這則故事橫跨哪些單元」），所以查不到。正確做法是按**事實**掃——問「這個事實在本 repo 有幾種表達形式」，逐一列舉後才 grep。
- 2026-08-27T23:31:37Z — **上游契約缺口的處置沿用 U-3 的 403 形狀**：標出、說明影響（S-2 AC 4 目前不可滿足）、指派具體落點與具體欄位（functional-design 增設 `undecidable: [intent_id]`），**不逕自修改已通過三輪 reviewer 的 application-design 型別**。reviewer 判定此形狀正確，但補了一個我沒想到的風險：`functional-design` 是 CONDITIONAL 且 per-unit，U-7 那輪若被判為「無新資料模型」而 skip，修補會連帶被跳過。已寫入 G-1。
- 2026-08-27T23:04:37Z — **同批次約束不進 yaml edge block**。[Q3=A] 要求它與依賴邊區分，但 edge block 只有 `depends_on` 一個欄位，放不下第二種關係。處置：yaml 只放真正的技術依賴（下游 fan-out 依它計算），同批次約束寫在散文的獨立表格並明標「這不是 DAG 邊」。**不擴充 yaml schema**——那是引擎契約，擅改會讓 fan-out 解析失敗。
- 2026-08-27T23:04:37Z — 產出 `unit-of-work.md` 後才發現初稿把 [US:S-1 AC 7] 同時掛在 U-4 與 U-10 的完成判準上，會形成 `U-4 → U-10 → U-4` 的**環**。改為只歸 U-10（讓那件事為真的機制是 `ci.yml` 的 `paths-ignore`，不是 U-4 的回寫行為），並在 U-4 增設「不擁有」欄記明理由與消環的動機。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-29T03:54:57Z — Q1～Q4 的原答案與 Step 5 的計畫核可**不重取**：拆分不改變切分軸、粒度區間的意圖、部署模型或 kind 標註原則，改的是 rev0 對「U-10 兩半是否同一失敗模式」的判斷。reviewer 獨立認定此不重取為正當。

## Tradeoffs
- 2026-08-27T23:04:37Z — U-1 把 C-1 `sync-map` 與 C-2 `record-reader` 併為一個單元（而非依元件切成兩個）：兩者共用一個 composite action、共用一套 fixture、共用一次部署，驗證方式完全相同；拆開會讓「這個單元完成了嗎」重複問兩次同一件事。代價是與 `components.md` 的元件編號不是一對一，追溯靠對照表。
- 2026-08-27T23:04:37Z — U-7 把 [ad:S-B] 對帳 workflow 與 [ad:C-7] `reconciler` 併為一個單元：兩者是同一個東西的兩面，拆開後 workflow 沒有邏輯、reconciler 沒有觸發，都無法獨立驗收。
- 2026-08-27T23:04:37Z — U-9 自我測試獨立成單元而非散進各被測單元：它的驗證方式是「CI 紅綠與突變驗證」，與被測對象的驗證方式不同類；且散進去會讓每個單元的完成判準多一條元層次的「有沒有寫測試」。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-29T03:54:57Z — Bolt 1 仍為 7 個單元（U-1～U-6 ＋ U-10a）。這不是切分不足，是兩條**既有且本輪未動**的同批次約束疊加的結果（U-6 需要 U-1～U-5 全在同批、U-10a 需與 U-4 同批）。拆分只解掉「U-10 同時綁 U-4 與 U-8」造成的 8 單元巨型 Bolt，沒有也無法縮小這 7。

## Open questions
- 2026-08-27T23:04:37Z — **U-3 的完成判準只涵蓋 [US:S-10 AC 5] 的一半**：「直推保護分支回 403」可由分支保護產生，「改 record 目錄以外的檔案回 403」在本設計下無機制。已列 PRE-1-a 實測；不可行時該 AC 需回 user-stories 改寫。**這是 construction 開工前就該知道的事**。
- 2026-08-27T23:04:37Z — **U-8 的 over-suppression 未實測**：本設計以「讀 PR 的 diff 是否含該 intent 的 record 路徑」做逐 intent 判定，但先例（`--all-intents` 開單一 PR）形狀不同。[US:S-6 AC 3] 已含反例要求，實測落在 construction。
- 2026-08-27T23:04:37Z — **[req:OQ-7] 的三支既有腳本遷移不在本 intent 的單元集合內**。使用者已裁決為 B（遷移到 gh-aw／Actions），但那是本 intent 之外的工作，需另立 intent 或併入 construction 的獨立任務。本站只記載歸屬，不擅自納入。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-29T03:54:57Z — reviewer 本輪的 2 個 Major 皆為傳播失敗（`unit-of-work.md` 的「11 個單元…唯一原因」、story map 的「無空單元——11 個單元」），且發生在我剛把 `260822-ug-L1`（按事實掃、非按字串掃）寫進 `project.md` **之後**。我掃了 `U-10` 這個字串，沒掃「單元總數」這個事實——同型失誤在本 intent 已第四次。既有教訓的可執行性仍不足：它說「按事實列舉」，但沒有規定**改動前先寫下受影響事實清單**這個動作。
