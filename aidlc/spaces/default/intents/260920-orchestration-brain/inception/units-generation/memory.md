<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-25T17:46:53Z — **我在選項標題裡寫了一個沒算過的數字，然後被自己的枚舉推翻**。`[UG:G1]` 選項 A 的標題是「中粒度，**約 12 個**」，照該選項自己定的軸（一種驗證方式 × 一個資料擁有者）誠實展開是 **17 個**。這正是 `project.md` 的 `delivery-planning:dp-L1` 那條規則——「寫下任何可以被計算的數字之前先實際算一次」——而我在同一個 intent 內又犯一次，且這次的數字出現在**選項標題**裡，也就是使用者用來做決定的那句話。處置是在 Step 4 的計畫核可關卡把落差、17 超出既有實務上界（實測 5／9／12）、以及壓到 12 需要 5 次把兩種驗證方式塞進同一單元（＝使用者已拒絕的選項 B 的代價）三件事一起攤開，讓使用者重新決定。**可執行補強**：選項標題裡出現的任何數量，在寫下之前就要枚舉一次，不能留到產出階段才算——因為選項是使用者做決定的依據，產出只是結果。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-25T17:46:53Z — **`traceability` sensor 的 `tokenPresent` 不接受反引號與全角「、」作為分隔符**，而本專案的文件慣例正好兩者都用。它的實作（`aidlc-sensor-traceability.ts:221–224`）要求 token 前後是空白／`,`／`;`／`/` 或字串邊界，所以 `` `U11`、`U12` `` 這種寫法會讓整張 story map 被判為「無任何 story-to-unit 對應」——錯誤訊息是 `target "U11" is not mapped`，看起來像對應漏了，實際是**分隔符不合**。我先試了「把單元名稱也放進欄位」仍失敗，才回去讀 sensor 原始碼找到真因。處置是該欄改為純文字 ＋ 半角逗號，並在檔內就地註明這是格式要求而非美感選擇，否則下一個人會把它改回反引號。
- 2026-09-25T18:03:46Z — **我把一條規則寫進 `project.md ## Mandated`，然後在下一站立刻違反同一條**。domain-design 的閘門上，審查 R-03 抓到「`ADR-0006` 零命中」，我把它升格為規則並逐字寫「逐一對照本專案的 hard constraint……給六項自檢加第七項」。那條規則在本站是**載入狀態**的（`load-steering` 交付了 9 段 memory 層，含 `project.md`），而本站五份產出對 `ADR-0006` 的命中數是 **0**——同一個缺口，隔一站再犯，而且這次是在明知規則存在的情況下。**根因不是不知道，是我的實際自檢程序沒有變**：我跑的仍是那六項，而我自己寫的那條說「六項裡沒有這一項」——我描述了缺口卻沒有把它加進我真正會執行的清單。可執行補強：把「逐項對照 ADR-0006 四面向 ＋ PBT hard constraint」當成**自檢第七項**，與前六項一起在摘要確認區塊逐項報告；沒有出現在那張表裡就等於沒跑。規則寫進 `## Mandated` 只保證它被載入，不保證它被執行。
- 2026-09-25T18:03:46Z — **我揭露了較輕的阻塞、漏了較重的，而且兩者形狀相同**。本站明白寫出 `U9 memory-purge` 卡在 `OQ-13`（4 次命中），卻對 `U11 intent-router` 卡在 `OQ-10`／`OQ-4` 零提及——而後者更嚴重：`OQ-10` 質疑的是路由層**能不能產出可比較的信心值**，若不能，`U11` 責任裡寫成已定案的「0–1 信心值」與「門檻 0.7」兩句都要改寫，而 `OQ-4`／`OQ-10` 是上游標明**無自然承接站**的兩項（`OQ-13` 至少有 `infrastructure-design`）。可執行檢查：列完單元後，把 `requirements.md` 的每一個 `OQ-<n>` 逐一問「它未定案會讓哪個單元無法完成」，而不是只寫出自己剛好想到的那一個。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-25T17:46:53Z — **17 個單元超出本專案既有實務上界，但軸是使用者選的，我不替他壓**。實測既有三個 intent 為 5／9／12 個單元；17 明顯偏多，跨單元契約也從而變多（23 條邊）。但 `[UG:G1]`=A 的軸誠實展開就是 17，而壓到 12 的每一次合併都會讓某個單元的「完成了嗎」同時指涉兩種驗證判準——那正是選項 B 的代價而使用者已拒絕 B。所以正確處置是把落差與代價攤開後讓他重選，而不是我自己挑一個折衷數字然後宣稱符合他的選擇。他看過之後選了接受 17。
- 2026-09-25T17:46:53Z — **`U6 embedding-port → U1 brain-infra` 這條邊刻意選了較嚴的判準**。`EmbeddingPort` 的 `stub` 與 `fulltext` 兩個實作不需要任何基礎設施就能建與驗，所以嚴格說它可以是第五個可平行根。但 `ollama` 與 `fastembed` 兩個實作要能被驗證就需要 Ollama 服務與模型快取 volume。我選了「整個單元要能被驗證」這個較嚴的判準，代價是少一個可平行根，換到的是「這個單元完成了嗎」不會有一個部分成立的答案。此取捨已寫進 artifact 的 Assumptions，讓 2.9 知道它可以改。
- 2026-09-25T18:03:46Z — **我在 `U4` 的注意事項引用了 `AC9.1.4` 的不變量，卻沒提已知會打破它的缺口**。domain-design 自檢查出的 `DG-2`（`Project`／`System` 刪除的 cascade 未定）會讓「`system_id IS NULL` 計數為 0」在**執行期**被打破，而我在 `U4` 逐字寫了「遷移的不變量檢查必須大聲失敗」——引用了那條不變量，卻沒有帶上它的已知威脅。`DG-1`／`DG-2`／`DG-3` 在本站三份產出的命中數是 **0**。這比完全沒提更糟：讀 `U4` 的人會以為那條不變量只要遷移做對就成立。教訓：引用上游的不變量時，要一併帶上上游自己標出的、會打破它的缺口——兩者在上游是相鄰的兩段，在下游卻只抄了前一段。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-25T17:46:53Z — 六項自檢**零新發現**，這是本 session 第一次。前三站（user-stories 跳過自檢、refined-mockups 查出 8 處、domain-design 查出 3 處）的軌跡顯示自檢在收斂。但要注意本站的產出性質較機械（DAG、對照表、計數），而 domain-design 的 R-01 是**語意自我矛盾**——那一類在本站的產出形態下較難出現，所以零發現未必代表自檢變強了。
- 2026-09-25T17:46:53Z — **`OQ-13`（90 天清除 workflow 如何取得資料庫連線）仍未解**，且它是 `U9 memory-purge` 這個單元能否完成的前提：workflow 跑在 GitHub Actions 上，而資料庫在自架 staging 主機後面。上游指派 `infrastructure-design`（CONDITIONAL），本站不定案，但要點出它是一個**單元層級的阻塞**而非細節——`U9` 在它定案前無法完成。
