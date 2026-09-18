<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-03T04:58:32Z — 使用者 Q3 先選 X 無說明、追問後以逐字輸入「ACDE」定案 Won't Have 清單；B（報表匯出）以「未承諾」狀態記入 scope-document，不推定其未來去向。
- 2026-08-03T04:58:32Z — Q1=A（四項全 Must）與 N 未定並存：解讀為「N 於 requirements-analysis 定案」升格為上線前置依賴，記入兩份 artifact 的 assumptions 與 PU-3 依賴，不視為矛盾。
- 2026-08-03T04:58:32Z — stage 檔 Step 5 提及 value stream map 但 outputs 未列獨立檔案；解讀為併入 scope-document 的 ## 價值流 段落。
- 2026-08-04T00:40:07Z — Revision 1（backward jump）：下游 rough-mockups 的 Q5=B/Q5a=B 觸發 scope 擴充；以 Modify 模式修訂而非重做，既有 Q1–Q4 答案與 Won't Have 清單不動，僅疊加第五項能力 (e) 與 PU-5；修訂來源記入問題檔 Revision 1 段。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-03T04:58:32Z — 省略 stage 檔範例的「hard deadlines」題：feasibility Q5=A 已確認無時程阻塞，重問違反「不重問已決事項」。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-03T04:58:32Z — backlog 不做 WSJF／RICE 數值評分：單一決策者、四項全 Must、依賴序已定，編造相對分數只會製造虛假精確；以 MoSCoW＋依賴序表達優先即足。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-03T04:58:32Z — 四項 proto-unit 的粒度是否即最終 Unit 切分，留 units-generation 檢驗。
