<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-23T23:22:55Z — 彙整站的「不重問」清單必須逐條附上可引用的選項字母或原文，而不是憑印象宣稱「上游定案了」。本站對 stage 檔列的 6 個範例題 ＋ 自行想到的 3 個共 9 項逐一回查依據，結果全部查得到（[Q8]、[S7]、[F7]、[F10]、[F11]、[F13]、[S8]/[S9]/[S11]、[S10]，以及兩站 SKIP），於是真正未定案的只剩 5 題。不做這一步會走向兩種錯誤之一：以為彙整站沒什麼好問的而整批跳過，或把已定案的事重問一遍。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-23T23:22:55Z — 本站只問 5 題，落在 Standard 深度 5–8 題的下緣。理由是四站核可關卡已通過、兩站為 SKIP，絕大多數內容都有可引用的定案；5 題全部集中在同一種缺口——「上游做了決定但沒指名誰執行」。依 `approval-handoff:c1` 把省略清單與逐項依據寫進問題檔前言，而不是只在日記交代。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-23T23:22:55Z — H4 的四個落點中，只有 `tcms-test-cases`（3.8）是 `execution: ALWAYS`、不可能被 skip，也只有 `contract-design`（2.8）能從結構上預防兩份 runtime 漂移——「不會被 skip」與「能預防」不可兼得。處置是把這個取捨在摘要確認前完整攤開讓決策者自己選，再用轉移規則補回被放棄的那一半，而不是由我替他挑一個看起來比較好的。
- 2026-09-23T23:22:55Z — 交接表第 11 列（Jev）找不到誠實的轉移目標：`nfr-requirements`（3.2）被 skip 時，唯一主題相鄰的 `nfr-design`（3.3）的執行條件正是「NFR Requirements 已執行」，必然一併 skip。選擇寫「無自然承接站」並指定屆時判定 skip 的 conductor 重新提交給使用者，而不是填一個看起來合理的站。填假目標會讓表格看起來完整，實際上是死指派——比空著更糟，因為空著至少看得出來。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-23T23:22:55Z — 本站訂定的轉移規則（CONDITIONAL 站被 skip 時義務自動轉移至指定站）沒有任何機械檢查承載，生效完全仰賴屆時的 conductor 讀到 `initiative-brief.md` 的交接表。這是個可以做成 sensor 的形狀（掃 artifact 內的「指派給 <stage>」字樣、比對 stage-graph 的 execution 欄、要求 CONDITIONAL 者必須附轉移目標），但本站未提案，留待日後。
