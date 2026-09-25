<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-25T04:44:20Z — **出題前實測翻轉了兩個看似免費的選項**。線框 §12 的反問候選看起來能「沿用既有 `ChatBox` 的選項 UI 免費解決」，實測 `src/utils/parseChoiceOptions.ts` 才發現那是 regex 掃訊息內文的**文字解析**（`^([A-Ea-e])[.．、)）:\s]\s*(.+?)$`），承載不了候選的結構資料；而「WS 沿用既有前例」同樣不免費——唯一的既有 WS 消費點 `useCollaboration.ts:24` 正是 FR8.5 禁止的 query-string token，且其 `onmessage` 用字串嗅探 `<mxGraphModel` 判內容、**零訊息封包**。兩項查證各自把一題從形式題變成真選擇。反向的收穫是 `CostPage.tsx:119` 已讀 `?estimate=`，讓 D5 成為零後端改動。
- 2026-09-25T04:44:20Z — **`/memory` 不需要新 story id，而這是查出來的不是推論**。本 repo 每條能力路由都包 `CapabilityRoute storyId=...`，直覺會以為新路由必然要新 story id、連帶觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步。但 `App.tsx:38–41` 的 `/waiting-approval` 是 `ProtectedRoute` 單獨使用的既有前例，而記憶是使用者自己的資料（`[RA:FR4.3a]` 擁有者由記憶層依已驗證身分設定），把關的是擁有者欄位而非角色。依 `project.md` 的 `functional-design:c16`——宣告缺口前先確認它在機制上真的存在——這一項從「疑似回補項」變成「明確不是」。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-25T04:44:20Z — **`upstream-coverage` sensor 我第一次是空轉的**。不帶 `--consumes` 時它直接回 `pass: true, reason: "no upstream"`，看起來跟通過一模一樣；帶上之後立刻 FAIL。更正確的用法還要帶 `--deliverables`——sensor 原始碼明文寫「Coverage is a property of the STAGE's output, not of each file」，逐檔跑會把「這份檔沒理由引用某上游」誤報成缺口。補齊 `team-practices` 的引用時反而挖出一條四份產出都漏的真約束：`react-hooks/set-state-in-effect` 是 error 級，所有新增資料來源都必須走 `AdminPage.tsx` 的兩層抓取形狀，否則 `npm run lint` 紅燈。教訓：回報「某檢查通過」之前，先確認那個檢查這一輪**實際驗了什麼**。
- 2026-09-25T04:56:25Z — **我在 artifact 裡宣稱「提問時已揭露某項代價」，而問題檔裡零命中**。審查的 R-01 抓到四處，我自己複驗後發現比它說的更糟：揭露文字只存在於我送給 AskUserQuestion 的 option description，**問題檔的選項本文完全沒有**（`誤建`／`80%`／`各做一份`／`不一致的狀態` 在該檔各 0 次；D2 的選項 D 逐字只有「A ＋ B 並存：選單可建、對話也可建。」）。更糟的是「誤建比誤讀霧重」那句在選單裡掛在**選項 B**，而使用者選的是 **D**——所以 `mockups.md` M5 寫「我在選項說明裡已揭露這一點，使用者仍選了並存」是雙重錯誤。**根因**：我把選單當成紀錄。選單是一次性的 UI，問題檔才是下游與 reviewer 會拿去複驗的正式來源；兩者不一致時，同一個 `[Answer]: D` 在兩份紀錄中指向不同內容，而**只有問題檔留得下來**。可執行做法：送 AskUserQuestion 之前，先把每個選項的完整 description 逐字寫進問題檔，再從問題檔複製到選單——方向不能反。既有的 `intent-capture:fc73edfe` 講「揭露給使用者的具體度要搬進 artifact」，管的是選項→artifact；本條管更前面一段：**選單→問題檔**，那一段斷了，後面整條鏈都是空的。
- 2026-09-25T04:56:25Z — **「指派到 ALWAYS 站」不等於「指派到能關掉這個缺口的站」**。審查 R-02 抓到 H-3：我把「記憶檢視／刪除缺 AC」指派給 `units-generation` 並寫「ALWAYS——故本項不會落空」，但實查該站的 produces 是 `unit-of-work`／`unit-of-work-dependency`／`unit-of-work-story-map`／`traceability`，**沒有 `stories`**；全樹只有 `user-stories` 產出它。所以它結構上補不了 AC，execution 是 ALWAYS 也沒用。同型問題也在 H-2／H-6／H-7 的 fallback `tcms-test-cases`——它跑在 code 寫完之後。既有的 `approval-handoff:5d0af04b` 講「找不到誠實的承接目標就寫無自然承接站，不要填一個看起來合理的站」、`260920:approval-handoff:e4b6b5c2` 講「要回 stage-graph.json 確認 slug 存在並記下 execution」——兩條我都照做了，仍然錯，因為兩條都只驗「站存在嗎」與「會不會被 skip」，**沒有驗「那一站的 produces 裡有沒有這個缺口要改的那份 artifact」**。可執行檢查：每個指派都要能指出承接站的 `produces` 清單裡哪一份檔會被改；指不出來就是無效指派。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-25T04:44:20Z — **`clarify` 訊息刻意不帶信心數值上畫面**。直覺會想顯示「信心 62%」讓使用者理解為何被反問，但 **OQ-10** 記載 `[RA:FR1.6]`（路由層必須輸出 0–1 信心值）**可能不成立**，屆時觸發條件改為「候選並列且無單一最高分」，而上游明寫「畫面本身不必改」。若把信心值列為必填 Prop，替代表達就渲染不出來——畫面會因為一個尚未定案的模型選型而壞掉。代價是使用者少一個解釋線索；換到的是設計對 `nfr-requirements` 的兩種結局都成立。
- 2026-09-25T04:44:20Z — **對話式建立一律先確認，這是我加的防護不是使用者的定案**。`[DM:D2]`=D 讓建立成為由意圖識別觸發的寫入操作，而 `[RA:NFR1]` 對意圖識別只承諾 80%。我在選項說明裡已揭露「誤建比誤讀霧重」，使用者仍選並存——那是他的決定；但「照單全收」與「照單全收且不補防護」是兩件事。處置是寫入型交辦一律確認，且明寫此確認**與 `[RA:FR1.7]` 的 0.7 門檻無關**（信心 0.99 也要確認，因為問題不是大腦多確定，而是使用者有沒有要）。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-25T04:44:20Z — 自檢 1 查出兩個**可達性未驗證**的防禦性狀態：`CostAnswerCard.no-estimate-id`（`completed` 回應是否一定帶估價 id，上游無規定；我初版寫的可達路徑「job 以 failed 終止」是**錯的**，failed 有自己的狀態）與 `StreamingMessage.empty-stream`（大腦是否可能零內容結束串流；注意 `prompt_guard` 命中回的是有內容的固定訊息，不走此態）。兩者皆保留為防禦性狀態並指派 `contract-design`（H-6／H-7）。
- 2026-09-25T04:44:20Z — 自檢 2 查出兩處契約缺口，**都在「誰清」這一問**：work-item 集合無人清除（G-1）、作業對象無人清回 `no-object`（G-2，使該態只在首次使用可達）。這與 requirements-analysis 那一輪的教訓同形——「寫入端是三問中最容易漏的一問」在那裡成立，這裡則是**清除端**。兩者皆非實作細節而是狀態語意問題，需與 `[RA:NFR4]` 的重啟還原一併決定，故不自行定案，指派 `domain-design`（H-8）。
- 2026-09-25T04:44:20Z — `accessibility-checklist.md` 把 `AC-A11Y.1`／`AC-A11Y.2` 的自動化承載從「無」改善為「部分」（`[axe]` 14 項有承載、`[人工]` 23 項沒有），但**未回改 `stories.md`**（已核可，依 `refined-mockups:c3` 不回改上游）。兩份文件因此對同一件事有不同敘述，本檔為較新的事實——這個落差是刻意的，但下一個讀 `stories.md` 的人不會知道。
