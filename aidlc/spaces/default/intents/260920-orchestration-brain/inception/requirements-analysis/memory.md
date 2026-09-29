<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-24T23:59:31Z — **codekb 重掃是這一站真正的槓桿**：8 題裡有 4 題（R5 WS 契約閘門、R6 WS 兩個行為、R7 行程記憶體、R8 schema 驗證）**只有在讀過本輪 codekb 之後才問得出來**。上游 ideation 四站沒有一站碰到「這條需求能不能被驗證」這個面向，因為那需要知道 openapi.json 不含 websocket、測試把 PG 換成 SQLite、三處行程內狀態靠單 worker 成立。若沿用舊 store（停在 c3de2c8）這四題會全部漏掉，而它們各自都落在 Must 能力上。
- 2026-09-25T00:08:24Z — **契約端點三問的「寫入端」是最容易漏的那一問，而且要對新建的資料模型跑、不只對欄位跑**。我對 `users.last_activity_at`、Redis session、WS 訊息契約、記憶列的擁有者／可見範圍都跑了三問，因此自己查出 OQ-9（Redis session 誰清）。但審查又找到三處同形狀的缺口，全部是寫入端：`projects`／`systems` 兩個新表誰建立／誰能讀改刪、記憶列的可見範圍誰設定與變更、FR4.5 的 90 天清除由什麼承載。共同點是我把三問跑在「已存在的欄位」上，沒跑在「本 intent 新建的實體」上——而新實體的寫入端恰恰是最沒有既有程式可參照、最需要需求指名的那一端。
- 2026-09-25T00:08:24Z — **「本階段新增、scope 未涵蓋」清單的收集判準太窄**。我只列了「我在答案裡明確選出來的新機制」（N-1 到 N-4），漏了「已核可上游決定所隱含、但本站未落地的義務」——新 RBAC story id（來自 `[R8]`）與 90 天清除機制（來自 `[RA:R2]`＋`project.md` 禁止 repo 內無人值守排程的條款）。前者甚至會觸發兩份部署資產的 blocking 同步。判準應該是「本站之後多出來的工作量」，不是「本站做的選擇」。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-24T23:59:31Z — 問了 9 題（8 ＋ 1 加開），略高於 Standard 的 5–8 題上緣。理由：4 題是 approval-handoff 明確指派的義務、4 題是 codekb 查出的驗證缺口、1 題是覆蓋檢查逼出來的（R1=A 要求標註集但沒人負責產生）。壓到 8 以內就得砍掉其中一項指派義務或一個 Must 能力的驗證路徑。
- 2026-09-24T23:59:31Z — 能力 5、6 的可測不變量**不成題**、直接寫進 artifact，只把能力 3 成題（R4）。判準是「有沒有產品層的分岔」：能力 5 是「N 個意圖 → N 個工作項」、能力 6 是「第 N 輪解析第 N−1 輪的指涉詞」，兩者沒有可選的另一種做法；能力 3 的「另開新對話時作業對象怎麼辦」有四種真實走法。把沒有分岔的事做成選擇題，會製造使用者選過但其實無從選的紀錄。
- 2026-09-25T00:08:24Z — **只掃上游的 `[Answer]` 不夠，散文裡的指派也要掃**。審查抓到兩項 Critical，兩項都是上游已核可決定在本站落空，而且**都不在作答本身，在作答周邊的散文裡**：rough-mockups 第 12 節的「刻意不在本站定案的」段逐字把「信心判定門檻」指派給 requirements-analysis，`[R8]`＝A 的作答後果段寫明「需新增 RBAC story id 與權限矩陣項目」。我建「不重問清單」時逐題核對了 R1–R8 的 `[Answer]`，卻沒讀那些段落，於是把兩項交付義務當成不存在。可執行檢查：對每一份上游 artifact，除了讀作答，還要 grep 本站 slug（`requirements-analysis`）與「本站不預選」「留待」「指派」「需新增」這類字樣。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-24T23:59:31Z — R1 的三個門檻值（80%／95%／2 秒）是工程判斷，**現在沒有依據**——能力 1 尚未存在，無基準可比。取捨是：選項 C（只定量測方法）會讓 AC 不可二元可判且是第二次延後（[F7] 已延後一次），選項 A 則承擔「數字可能不對」的風險但保住可驗收性。處置是把「沒有依據」這件事本身寫進 A-3，並附首次實測後的校正條款，而不是讓數字看起來像有依據。
- 2026-09-25T00:08:24Z — 在給審查者的 brief 裡主動點名自己最可能出錯的七處（含「80% 門檻算不算把猜測打扮成需求」）。結果它對其中兩處**判我站得住**（A-3 的誠實標註、FR1.3 的可達性 caveat），並把火力轉到旁邊真正的缺陷（NFR2 連量測母體都沒有、FR1.3 缺門檻值）。這比不揭露有價值：揭露讓它不必花時間重新判斷我已經想過的部分，直接去找我沒想到的。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-24T23:59:31Z — **來源標籤撞號**：rough-mockups 與本站都用 R1–R8 編號。本站以 `[RA:R<n>]` 前綴區隔並在 artifact 開頭寫了警告，但這是**事後補救**——問題檔的題號已被摘要確認收據凍結，無法改。下一個用 `R` 當題號前綴的 stage 會再撞一次。可考慮的規則：題號前綴以 stage slug 的縮寫決定（rough-mockups→RM、requirements-analysis→RA），不要用單一字母。
