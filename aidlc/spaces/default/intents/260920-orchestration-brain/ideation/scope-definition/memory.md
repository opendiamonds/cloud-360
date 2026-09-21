<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-09-21T07:09:49Z — 抽象的衝突清單不足以讓人察覺答案讀反；**具體呈現「照此執行下一步會產出什麼」才有效**。本站先以矛盾偵測列出 S9 結果與 [Q1]／[Q3]／[Q5] 的三處衝突並明示「方向可能讀反」，使用者回覆「沒反，就是這樣」；直到 S10 把後果具體化為「兩項 Must 各自依賴一項 Should，故 Must 集合無法獨立交付」，使用者才主動更正為 8 Must／2 Should。下次遇到「答案與多處上游定案衝突且疑似讀反」時，直接推導到下一步的具體產出，不要停在衝突清單。
- 2026-09-21T02:56:24Z — feasibility 的 [F8] 是單選題，使用者選「有預算或成本上限」，**未選中**「有目標時程」。依 `scope-definition:c1`（未選中的選項不得被當成排除），時程並未被回答，故本站以 S7 補問硬期限，而非推定為「無期限」。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-09-21T07:09:49Z — S9 的分級曾被記為反向（降 8 項、Must 僅 2 項）並據以在 S10 寫出「Must 集合無法獨立交付」的發現。使用者更正後，本站同步改了三處：S9 的答案與後果段、S10 的先行發現段（依賴方向由 Must→Should 改為 Should→Must，結論由「阻塞」改為「可獨立交付」）、以及「三處衝突失效、不得帶入 scope-document」的明記。依 `rough-mockups:rev1-c10`，更正須一路追到最下游的落點。
- 2026-09-21T02:56:24Z — 依 `scope-definition:c5`（單一決策者、依賴序已定的 backlog 不做 WSJF／RICE 數值評分——沒有真實輸入的相對分數是虛假精確），本站的 intent-backlog 將以 MoSCoW ＋ 依賴序表達優先，不產生任何數值分數。決策者為單一人由 intent-capture [Q8]=A 確認。
- 2026-09-21T02:56:24Z — stage 檔 Step 4 提及 value stream map，但 `produces` 清單未列該檔。依 `scope-definition:c3`（produces 清單是 artifact 集合的正式來源），value stream map 將併入 `scope-document.md` 的段落表達，不自創新檔。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
