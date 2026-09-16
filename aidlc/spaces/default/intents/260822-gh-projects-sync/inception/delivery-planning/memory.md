<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-29T04:17:18Z — 把「風險優先」的**目的**與**形式**分開：本 intent 的三個最大不確定性（憑證權限、`createProjectV2Field`、Rulesets 適用性）全都不需要寫程式就能證偽，所以做成 Bolt 0 關卡而非一個 Bolt。純風險優先會為它們生出一個沒有可展示成果的批次——達成同樣的「投入前先知道」，卻多付一個 Bolt 的儀式成本。
- 2026-08-29T04:17:18Z — [US-OQ-2] 指派本站裁定 PRE-1 的留痕形式，定為 `<record>/construction/pre-1-findings.md` 的五項記錄，每項含「實際執行的呼叫或設定／得到的回應／判定」三欄。三欄是為了讓 `stories.md` 的「不得以文件敘述代替驗證」變成可檢查的——只填第三欄而第一欄空白，即為未完成。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-29T04:17:18Z — U-11 在依賴圖上是 L0（無入邊、XS）卻排到最後一個 Bolt，這是本計畫**唯一**偏離拓撲順序之處，已在 `risk-and-sequencing-rationale.md` 專節說明：README 指向 Project #16 的價值取決於那個看板上有東西可看，在 Bolt 1 之前出貨等於把 P3 指向一個空看板。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-29T04:17:18Z — over-suppression 與 G-1 兩項風險**沒有被提前**。兩者分別需要 U-8 與 U-7 存在才測得到／修得了，提前只能靠拆散已核可的單元邊界，代價高於收益。這是取捨不是疏漏，已在 rationale 的風險表明記「排序沒有把最後兩項風險提前」。
- 2026-08-29T04:17:18Z — Bolt 1 為 7 個單元，超出 `org.md` 偏好的短生命週期分支尺度。這是兩條同批次約束疊加的結構下限（U-6 需 U-1～U-5 同批、U-10a 需與 U-4 同批），不是湊批。[Q1=B] 的另一端是 9 個單元（union-find 實算），更差。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-29T04:17:18Z — **我在 Revision 表裡寫下一個沒算過的數字**：「雙向讀法下仍是 8 個（一進一出）」——實際 union-find 算出是 9 個（U-10a 經 U-4、U-10b 經 U-8 各自併入同一群組，兩個都在裡面）。發現後已改為實算值並註明算法。這與本輪剛在 units-generation 持久化的教訓（計數是受影響事實）是同一個根：我對「一進一出」有直覺，就沒去驗。直覺產生的數字與算出來的數字在文件上長得一樣。
- 2026-08-29T04:17:18Z — `functional-design` 為 CONDITIONAL 且 per-unit，G-1 的修補指派給它。若 U-7 那輪被判「無新資料模型」而 skip，[US:S-2 AC 4] 會靜默地繼續不可滿足。已寫進 `bolt-plan.md` 的 Bolt 2 gate 與 phase-check 的未結項表，但**沒有機制**保證有人在那個 gate 上真的檢查。
