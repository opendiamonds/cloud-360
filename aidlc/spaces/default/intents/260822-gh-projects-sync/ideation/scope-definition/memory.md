<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-08-23T05:56:09Z — 十項能力全被列為 Must。一般的優先序方法會判定「全部都是 Must＝沒有優先序」並要求使用者重排，但 project.md 已有一條 correction 明載本專案接受此形狀（單一決策者、全 Must、依賴序已定的 backlog 不做數值評分）。既有規則已定案的事不重開，故本站不挑戰全 Must，改以依賴序承載優先。
- 2026-08-23T05:56:09Z — Q1=E（一次做完全部）被解讀為範圍層的交付意向而非 Bolt 切分決定。理由是 scope-definition 的職責是邊界不是批次，且 delivery-planning 才擁有 Bolt 序；若在本站把 E 讀成「單一 Bolt」，等於越權替 2.8 決定，而 2.8 屆時還要面對 org.md 短生命週期分支的約束。兩份 artifact 都明寫此界線，避免下游誤讀。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-08-23T12:35:55Z — 本 stage 於首次核可後被回跳重開（Modify 模式）。觸發源是 reverse-engineering 開始前發現 ADR-0012（Accepted 2026-08-16）涵蓋同一主題卻全程未被引用，其對「反向同步」的論證（純鏡像會讓拖動的卡片被彈回原位，比沒有同步更糟）具決定性且本站原先未曾考慮。使用者據此把反向同步從 Won't Have 拉進範圍，構成 scope 擴充，依 project.md 規則必須回跳修訂並重走 gate。修訂依據為新開的 ADR-0013。舊 artifact 已歸檔於 archive/2026-08-23-scope-definition/，既有答案與清單不動，修訂來源記入問題檔的 Revision 段。
- 2026-08-23T05:56:09Z — Q2 因 AskUserQuestion 每題最多四個選項而拆成 Q2 與 Q2b 兩題，違反「一題一個決策」的自然形狀。已在 Q2 的註記寫明拆題理由與各題涵蓋的能力編號，避免下游把 Q2b 誤讀為獨立的第二次分級。
- 2026-08-23T05:56:09Z — stage 步驟要求產出 value stream map，但 outputs 清單只有 scope-document、intent-backlog 與問題檔三項。依 project.md 的既有 correction，把價值流併入 scope-document 的一個段落表達，不自創檔案。
- 2026-08-23T05:40:51Z — 更正上一站的一項誤記：feasibility 的 stage 日誌寫下「單一決策者且無外部時程（intent-capture Q4／Q5 已定）」並據此省略時程題，但回頭逐字核對，intent-capture Q4 選的是 A、B、C，而「D. 沒有外部壓力」**未被選取**；Q5 只談決策權，不談時程。「無外部時程」是我的推論而非上游定案，省略該題的理由不成立。本 stage 補問（Q6）。project.md 已有一條規則正是禁止此形狀（撰寫「已由上游定案」清單時須逐字核對最下游的具體決定），本次是該規則被違反的實例，不是新發現。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
- 2026-08-23T05:56:09Z — PU-4 對 PU-3 的依賴標為「避免重工」而非技術依賴。兩者在依賴圖上長得一樣，但前者可由下游在記明緩解方式的前提下覆寫。不區分的話，下游會把經濟性排序當成不可動的 DAG 邊——project.md 已有一條 correction 正是要求做此區分。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-08-23T05:56:09Z — Q9=B 讓 CAP-7 多了一個與 RSK-7 同型的待驗證假設：框架的安全輸出清單有「建立看板」與「建立檢視」，但沒有「建立欄位」。本站已如實記為 assumption 並保留 [Q9] 的人工退路，但這代表本 intent 現在有兩個「必須先驗證才知道能不能做」的點，而非一個。application-design 應把兩者併為同一次驗證，避免分兩趟。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
