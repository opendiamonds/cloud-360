<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-25T02:33:46Z — **在 mob brief 裡點名具體問題，比丟一份草稿有效得多**。給設計師的 brief 直接問「US4.3 那條界線守不守得住」，它回來的不是意見而是四項可複驗的證據（openapi 42 條 path 零稽核端點、前端 audit 零命中、AdminPage 表頭是帳號名冊、estimate_audit_events 只寫不讀），把我原本寫成「本站未確認」的東西變成「已查證必然需要新畫面」。更有價值的是它自己補了對照組（AC8.1.2 的最後活動時間**真的**由既有介面滿足），證明那道檢驗不是一律喊 scope-uncovered。
- 2026-09-25T03:37:36Z — **框架的 id 文法不接受字母後綴，而拆故事的本能寫法正好會產生它**。把 `US4.1` 拆成 `US4.1a`／`4.1b`／`4.1c` 後才發現 `.claude/tools/aidlc-sensor-traceability.ts:61-62` 的 pattern 是 `US\d+\.\d+` 與 `AC\d+\.\d+\.\d+`，帶後綴的一個都比對不到；而 `units-generation` 與 `domain-design` 用同一組 pattern 從 `stories.md` 解析上游，所以那三則故事與 9 條 AC 會對**每一個**下游追溯消費者隱形，不只 traceability sensor。可執行檢查：新增任何 id 之前，先用該檔的 pattern 對它 grep 一次。
- 2026-09-25T03:37:36Z — **重新編號的方向要看「既有 id 被誰引用過」，不是看讀起來順不順**。文件順序排成 `US4.1→4.2→4.3→4.4→4.5` 顯然比 `4.1→4.4→4.5→4.2→4.3` 好讀，但前者要把既有的 `US4.2`／`US4.3` 往後推——而它們已被三份 contribution 檔引用 11 處，推完之後那些引用會**靜默指向另一則故事**，沒有任何機制會報錯。新號接在尾端、既有號不動，是唯一不會製造假引用的方向。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-25T02:33:46Z — 草稿把 US4.3 的範圍界線寫成「本站不預判它需不需要新畫面，只把界線寫在故事旁邊」。這個寫法看似謹慎，實際上是**把可查證的事留給下游去撞**——設計師用四個 grep 就證明了它必然需要。教訓：凡是「實作時可能發現 X」的寫法，先問一句「X 現在查得出來嗎」；查得出來就不該寫成待確認。
- 2026-09-25T03:37:36Z — `requirements.md` 的 `FR4.3a`／`FR4.3b`／`FR4.5a` 落在同一個 id 文法問題上（會被解析成 `FR4`），但**沒有回改**——依 `project.md` 的 `refined-mockups:c3`，下游不回改已核可的上游，改為在 `stories.md` 就地標明、追溯表以群組 `FR4` 承接、列為交接事項。這與我修自己這一站的 `US4.1a` 是不同性質的兩件事，不能因為「順手」就一起改。
- 2026-09-25T03:45:57Z — **mob 整合的失敗模式是「選擇性整合」，而且它在產出上看不出來**。reviewer 把三份 contribution 逐項對照整合後的 `stories.md`，找出約十二項有證據的發現被無聲落掉，其中數項是貢獻者自評 Major、且**正好落在本檔宣稱零容忍的那一類缺陷**（不可構造的 Given、無法造假的 Then）——我修了 lead 自己發現的與被標 Critical 的那幾項（`AC1.4.3`／`AC1.4.4`、`AC4.1.1`、`AC9.1.4`），剩下的 Major 沒有處置也沒有拒絕理由。關鍵在於：落掉的東西在 artifact 上不留痕跡，只有把 contribution 檔當成 checklist 逐項對照才看得出來。可執行做法：整合完成後，對每一份 contribution 的每一項編號發現，在整合產出中指出它的落點（AC／DoD／Assumptions）或寫下拒絕理由，兩者皆無即為未整合。這件事的成本極低（貢獻者已經把證據與建議修法都寫好了），而不做的代價是 mob 這個模式本身失去意義——三位專家的獨立視角付了代價卻只用了最顯眼的那部分。
- 2026-09-25T03:45:57Z — **`AC4.3.1` 留下一個指向不存在內容的 forward reference**（「該操作的觸發面見下方註」，全檔 grep 無此註）。這比完全沒寫更糟：它讓讀者以為有人處理過。形狀上與「不可構造的 Given」同類——看起來已解決，實際是死指標。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-25T03:37:36Z — **追溯表的 FR→故事對應改用機械推導（從 `stories.md` 的 `[RA:FR…]` 引用抽取），而不是手寫**。代價是它的正確性等於引用的正確性：某則故事若引了一條它其實沒滿足的 FR，推導出來的覆蓋就是假的，而表本身看不出來。換到的是可複驗——任何人重跑同一段抽取都會得到同一張表，且 49 條子需求無一漏接是算出來的而非目測。已在送審 brief 中點名請 reviewer 攻擊這一點。
- 2026-09-25T03:37:36Z — **contribution 檔保留 `US4.1a/b/c` 的舊 id 不改**。它們是三位支援者互不相見時各自寫下的證據，改掉等於竄改紀錄；代價是讀者對照 contribution 與 `stories.md` 時會看到對不上的 id，已在 `stories.md` 的群組說明寫明原因。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-25T02:33:46Z — 設計師指出 `[R7]`（響應式 ＋ WCAG 2.1 AA，rough-mockups 已核可）在 `requirements.md` 與 `stories.md` **雙雙零命中**——一整項已核可決定在 Inception 蒸發。這不是本站獨有的疏漏：requirements-analysis 也沒接它。待確認它應該落在哪一站（refined-mockups 的視覺契約？nfr-requirements 的可用性 NFR？），以及為什麼兩站都沒接到。
- 2026-09-25T03:37:36Z — 上一條 `[R7]` 的待確認已在本站處置：新增「`[R7]` 的處置」一節，兩條 `AC-A11Y.*` 明記無自動化承載層（前端無 unit／component 測試框架、Playwright 未接 axe-core）。**但「為什麼 requirements-analysis 與本站都沒接到一項已核可的 Ideation 決定」這個問題本身沒有答案**——那是流程缺口不是內容缺口，留給 approval gate 由人判斷要不要回頭補。
- 2026-09-25T03:37:36Z — `NFR10`（路由層模型定案）指派給 `nfr-requirements`，而該站是 CONDITIONAL、其下游 `nfr-design` 的執行條件又依賴它已執行，故兩站會一併 skip。依 approval-handoff 那一輪學到的形狀，已寫明「無自然承接站」並指定屆時判定 skip 的人須把本項重新提交給使用者。這條指派會不會真的落空，本站無法保證。
- 2026-09-25T03:57:13Z — **ADR-0006 的 property-based testing hard constraint 在本站沒有落點，而核可不會記錄它**。ADR-0006 逐字點名 agent routing 需 PBT，本 intent 建的就是意圖識別與路由（`FR1.3`／`FR1.6`／`FR1.7`）；`stories.md` 全檔 `property-based`／`hypothesis` 零命中，無任何 DoD 要求它。此項**不在** reviewer 的 findings 表內（是我在階段摘要自查出的第 11 項），所以 gate 的 Approve 不會把它映射成 Accepted risk——它沒有任何機制承載。已在核可關卡向使用者具名揭露後由其選擇 Approve。**指定承接**：`units-generation`（ALWAYS）須把路由相關單元的測試策略納入 PBT，`build-and-test`（3.6，ALWAYS）為其驗證落點。這一條記在這裡是因為它是本 record 唯一會留下的痕跡。
- 2026-09-25T03:57:13Z — reviewer 的 R-01～R-10 十項於 Approve 時全數轉為 Accepted risk。其中 R-04（四條不可構造／無法造假的 AC）、R-06（「我的記憶」畫面零 AC 且無入口）、R-07（`AC4.3.1` 的死指標）會直接被 `units-generation` 讀成已核可的驗收面。若下游發現切不出可驗證的單元，源頭是這十項而不是它自己。
