<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-08-10T12:00:00Z — **[Revision 1]** 分頁對本 intent 的核心價值有**實質損害**，不只是多一個控制項：核心價值是「一眼看出哪些帳號已逾期」，分頁後若只能看本頁，「到底有幾個逾期」這個問題就從一眼可得變成 O(頁數) 次翻頁。全域逾期計數是對此損害的**補償措施**，不是額外的資訊裝飾 —— 這個定位寫進了 artifact，避免下游把它當可選項砍掉。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-04T00:48:32Z — Q5=B 引發的 scope 擴充依協定回跳 scope-definition 修訂重審後才回到本 stage 產出 artifact；本 stage 未擅自在 wireframe 中夾帶未核可的範圍。
- 2026-08-04T00:48:32Z — 逾期標示的圖示在 ASCII 線框以 (!) 表達（emoji ⚠ 非基本 ASCII，違反線框字元標準）；實作圖示樣式留 refined-mockups。
- 2026-08-04T00:48:32Z — 載入／錯誤態解讀為「沿用既有頁面模式」，不重新設計 — 本 feature 是加欄不是改版（載入模式除外於 PU-5 的卡片改造範圍）。

## Deviations
- 2026-08-11T15:00:00Z — **[Revision 1，iteration 5]** 傳播終於乾淨（五輪來首次無殘留）。但我對「不需重設 Assumption Confirmation」的判定**錯了**：我用「operative 內容未變」當判準，而 reviewer 指出**先前被確認的那個狀態本身就內部不一致**（第 3 條與第 1、2 條互相矛盾），拿它當比較基準沒有意義。修掉矛盾就等於改變了已確認的集合，必須重新確認。教訓：**判斷「是否需要重新確認」時，先確認「上次確認的到底是什麼」—— 若上次確認的內容本身有矛盾，任何修正都構成實質變更。**
- 2026-08-11T15:00:00Z — **[Revision 1，iteration 5]** 行內刪除線標註被判定偏離本檔既有慣例（原文不改寫、以區塊級 addendum 覆寫）。已改回：兩處選項本文回復原狀，改由單一 addendum 區塊同時涵蓋 A 與 C 的不成立處。教訓：**沿用既有 artifact 的更正慣例，不要因為別的檔案用過某種手法就套過來** —— U2 用行內標註是那份檔案的形狀，這份檔案的形狀是區塊級 addendum。
- 2026-08-11T14:00:00Z — **[Revision 1，iteration 4]** reviewer 找到**第六、七處**殘留，其中一處是 Revision 1 段落**開頭的「本站定案」blockquote** —— 整段最先被讀到的句子，前三輪審查都沒觸及。修正後我自己再跑一次全檔掃描，又找出**三處 reviewer 未點名的真殘留**（`user-flow` 兩處與其在問題檔的逐字轉錄）：它們寫「全域計數回答了『有幾個』但不回答『它們在哪』」，這句話**預設計數存在**，而它現在不做了。
- 2026-08-11T14:00:00Z — **[Revision 1，iteration 4]** 上述第 3 條假設的措辭同步**判定不需重設 Assumption Confirmation**：`project.md` 的重設觸發條件是 assumptions 的**新增或刪除**，本次是既有條目的措辭澄清，其 operative 內容（限制存在、排序／篩選仍在 Won't Have、不擴大範圍）完全未變，只更新了「計數是否存在」這個前提子句。判定理由已寫進問題檔，供 reviewer 覆核。
- 2026-08-11T13:00:00Z — **[Revision 1，reviewer iteration 3]** reviewer 回覆了 iteration 2 交付的判斷請求，答案是「**不夠**」：「標註候選但留在線框」的折衷應改為**完全移出主線框**。三個理由中最有力的是先例論證 —— 文件自己對「稽核報表匯出」的處置就是完全不進線框、只記於 Assumptions，而兩者**核可地位相同**（皆未經 scope 核可）。另兩個：本輪查獲的傳播失敗就是該折衷脆弱的現場證據；**視覺位階的說服力大於文字標註**，畫進 box 的東西會被下游當作照著做的對象。已照做。
- 2026-08-11T13:00:00Z — **[Revision 1，reviewer iteration 3]** Finding B 的修正只覆蓋三處中的兩處，且延伸出第五處：Assumptions 的對應條目**已逐字轉錄進問題檔並完成人工確認** —— 矛盾被鎖進已核可的紀錄。修正該條目因此連帶需要重設 Assumption Confirmation。教訓：**修正若涉及已被轉錄／已被確認的內容，傳播範圍要一路追到最下游的確認點**，不能只改來源。
- 2026-08-11T11:00:00Z — **[Revision 1，reviewer iteration 2]** 兩項新 Major **都是修正的不完整傳播**：①「屬本站設計判斷、上游未表態」的揭露只補到三處中的兩處，`user-flow.md` 那張表與 `wireframes.md` 自己的「重新評估」表（結構上還先於有揭露的段落出現）都漏了；②全域計數的地位在文件內自相矛盾——「設計決策摘要」與線框把它當已確立決定，「便利功能」表卻承認它可移除。這是本 session 第四次同型失誤，與 `cid:units-generation:c6b` 記載的模式相同。
- 2026-08-11T11:00:00Z — **[Revision 1，reviewer iteration 2]** reviewer 回答了我明確請它判斷的產品問題，答案是我沒想到的：全域計數**根本不在 `scope-document` 的任何清單中**（不在六項 Must、不在 Won't Have、不在未承諾），是我在 Critical 論證撤回後自行保留、帶真實後端成本的**候選能力**，不該與六項已核可能力同等視覺位階入線框。已在兩個 box 標註「候選」、設計決策摘要新增一列明記「未經 scope 核可，若要實作須先經核可」。教訓：**論證垮台後，靠那個論證存在的東西不會自動獲得別的正當性 —— 要重新問它憑什麼在這裡。**
- 2026-08-11T09:00:00Z — **[Revision 1，reviewer 更正]** 我在初版宣稱「本 intent 的核心價值是稽核者一眼看出哪些帳號已逾期」，**無任何來源標籤**，且與上游不符：`intent-statement.md` 記載的是「存取稽核對**『帳號是否仍在使用』**的查驗需求」—— **逐帳號**的證據取得。分頁前能一次看完全部帳號，是「清單不分頁」這個**技術現況的副作用**，從未被上游確認為產品需求。我把副作用當成了需求。
- 2026-08-11T09:00:00Z — **[Revision 1，reviewer 更正]** 上述無來源主張是整套「分頁損害核心價值 → 全域計數是必要補償」論證的**唯一**基礎，而該論證還一度被寫進 `project.md` 的永久規則層。規則已改寫為真正的教訓（引用核心價值前須回上游逐字核對並掛來源標籤）。全域計數保留，但定位降為**便利功能**。
- 2026-08-11T09:00:00Z — **[Revision 1，reviewer 更正]** 兩個新 ASCII box 違反本檔既有標準：既有慣例是 **`len()` 字元數**（桌面 72／小螢幕 34、逐行一致），我用**顯示寬度**補齊，做出 len=54／47 的 box。`project.md` 的 learned rule `cid:rough-mockups:c4` 逐字寫的就是「驗證每行**字元數**一致」—— 我違反的正是為此存在的那條規則。已重新以 `len()` 產生並驗證。教訓：**沿用既有 artifact 的格式時，先量測既有樣本的實際慣例，不要用自己認為「更正確」的標準**。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-04T00:56:50Z — reviewer iteration 1 NOT-READY 修正：ASCII box 改以腳本產生保證每行字元數一致（手寫 CJK 混排必然數錯）；user-flow 補流程圖；tooltip 文案改標示例；小螢幕註記補 landmark。手寫 ASCII box 含 CJK 時應一律用腳本驗證字元數。

## Tradeoffs
- 2026-08-10T12:00:00Z — **[Revision 1]** 選頁碼式而非游標式，明知它要多一次計數查詢。判準是稽核場景的實際動作：稽核者要「掃過全部帳號」並能「跳回某頁重新核對」，游標式兩者都做不到。效能代價換的是這個場景真正需要的能力。
- 2026-08-10T12:00:00Z — **[Revision 1]** 「逾期優先排序」是解決逾期散落多頁的最直接手段，但它是**排序** —— 而排序在上一站（scope-definition Revision 2）剛被明確保留於 Won't Have。選它等於立刻推翻上一站定案，所以列為選項 C 並明寫此代價，不採用。這是把「不擅自擴大已核可範圍」落實到選項設計裡，而非只寫在規則層。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-04T00:48:32Z — 小螢幕卡片線框只畫一種佈局（標籤: 值 逐行式），未併列多方案：PU-5 是剛擴充的範圍，先給單一基準讓 reviewer 與 gate 有具體對象，替代方案留 refined-mockups 探索。

## Open questions
- 2026-08-10T12:00:00Z — **[Revision 1]** 全域計數回答了「有幾個」，**沒有回答「它們在哪」**。逐一處理逾期帳號仍須翻頁尋找。完整解法需要排序或篩選，兩者都在 Won't Have，故如實記載為限制而非缺陷。若未來稽核者反映此痛點，需另立項而非在本 intent 補做。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-04T01:00:02Z — reviewer iteration 2 的 Finding 5（Minor）：wireframes Assumptions 的 skeleton 句掛了不對應的 [Q5] 標籤；READY 後不回改（會使 review receipt 失效且 iteration 已用罄），refined-mockups 修訂該檔時一併移除。
- 2026-08-04T00:48:32Z — 響應式斷點值（以既有內容破版處為準）留 refined-mockups 定值。
- 2026-08-04T00:48:32Z — 既有頁面是否已有 skeleton 載入慣例，refined-mockups 時查證對齊。
