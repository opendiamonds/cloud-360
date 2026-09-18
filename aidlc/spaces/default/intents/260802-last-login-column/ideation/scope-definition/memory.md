<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-08-10T11:00:00Z — **[Revision 2]** 分頁列為獨立能力 (f) 而非併入 (b) 的 DoD：它有自己的驗收面（回應形狀、兩種佈局的互動、型別契約）與失敗模式，且跨 U2／U3／U5 三個單元。埋進 (b)（「管理介面顯示該欄位」）會讓一個**改 API 回應契約**的變更被歸類成顯示問題，在 units-generation 時失去可追蹤的獨立身分。
- 2026-08-10T11:00:00Z — **[Revision 2]** 明確保留「依最後活動時間排序／篩選」的排除，並在 scope-document 與 backlog 兩處寫明「分頁是本次新增的**唯一**清單互動」。不寫這句的話，下游很容易把分頁讀成「清單互動已解禁」，進而自行補上排序 —— 那是 intent-capture 階段就定案的排除。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-03T04:58:32Z — 使用者 Q3 先選 X 無說明、追問後以逐字輸入「ACDE」定案 Won't Have 清單；B（報表匯出）以「未承諾」狀態記入 scope-document，不推定其未來去向。
- 2026-08-03T04:58:32Z — Q1=A（四項全 Must）與 N 未定並存：解讀為「N 於 requirements-analysis 定案」升格為上線前置依賴，記入兩份 artifact 的 assumptions 與 PU-3 依賴，不視為矛盾。
- 2026-08-03T04:58:32Z — stage 檔 Step 5 提及 value stream map 但 outputs 未列獨立檔案；解讀為併入 scope-document 的 ## 價值流 段落。
- 2026-08-04T00:40:07Z — Revision 1（backward jump）：下游 rough-mockups 的 Q5=B/Q5a=B 觸發 scope 擴充；以 Modify 模式修訂而非重做，既有 Q1–Q4 答案與 Won't Have 清單不動，僅疊加第五項能力 (e) 與 PU-5；修訂來源記入問題檔 Revision 1 段。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-03T04:58:32Z — 省略 stage 檔範例的「hard deadlines」題：feasibility Q5=A 已確認無時程阻塞，重問違反「不重問已決事項」。

## Tradeoffs
- 2026-08-10T11:00:00Z — **[Revision 2]** PU-6 與 PU-5 的關係記為**避免重工的排序約束**，不是技術依賴。分頁本身不需要等 PU-1〜3（清單端點是既有功能），但卡片佈局若先以「一次拿到全部」為前提設計完成，加分頁時要重做一次。如實區分這兩種約束，讓 units-generation／delivery-planning 知道它可以在記明重工緩解方式的前提下覆寫，而不是把它當成不可動的 DAG 邊。
- 2026-08-10T11:00:00Z — **[Revision 2]** 維持「無次級優先層」而非把分頁列為 Should。理由不只是尊重 Q1 的既有定案 —— 分頁會改變 U2 的回應契約，先上無分頁版再加分頁等於**改兩次契約**，而每次契約變更都連帶 U5 的型別與 U3 的呈現。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-03T04:58:32Z — backlog 不做 WSJF／RICE 數值評分：單一決策者、四項全 Must、依賴序已定，編造相對分數只會製造虛假精確；以 MoSCoW＋依賴序表達優先即足。

## Open questions
- 2026-08-10T11:00:00Z — **[Revision 2]** 分頁與逾期標示的互動未解：逾期帳號可能散落在多頁，稽核者是否需要「本頁以外還有幾個逾期」這類跨頁彙總資訊？本站不預判，留 refined-mockups 評估。這是分頁對本 intent **核心價值**（一眼看出哪些帳號逾期）的實質影響，不是純呈現細節。
- 2026-08-10T11:00:00Z — **[Revision 2]** 本次 jump 重置了 14 個 stage 的完成標記（scope-definition 至 nfr-requirements）。artifact 檔案都在，但每一站的 approval gate 都要重走，且各站需自行判斷「哪些內容因分頁而需修訂、哪些原樣沿用」。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-03T04:58:32Z — 四項 proto-unit 的粒度是否即最終 Unit 切分，留 units-generation 檢驗。
