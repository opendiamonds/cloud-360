<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-23T23:22:55Z — 彙整站的「不重問」清單必須逐條附上可引用的選項字母或原文，而不是憑印象宣稱「上游定案了」。本站對 stage 檔列的 6 個範例題 ＋ 自行想到的 3 個共 9 項逐一回查依據，結果全部查得到（[Q8]、[S7]、[F7]、[F10]、[F11]、[F13]、[S8]/[S9]/[S11]、[S10]，以及兩站 SKIP），於是真正未定案的只剩 5 題。不做這一步會走向兩種錯誤之一：以為彙整站沒什麼好問的而整批跳過，或把已定案的事重問一遍。
- 2026-10-01T23:03:08Z — **修訂 5 的核心工作是吸收三站重跑的結果，而回跳的實際價值超出它要解的問題。** `[H11]`=B 的目的只是補能力 11／12 的可行性評估，但 feasibility 修訂 2 在查「工具怎麼拿到使用者 token」時順帶查出 `design_agent.py` 的模組層全域 `_progress_queue` 會讓**使用者 A 收到 B 產生的架構圖 XML**（已實測）。那是跨使用者資料暴露、坐在能力 1／8 的地基上，而八站都沒碰到它。這件事記進 phase-check 是因為它改變了「回跳值不值得」的評估依據——不是補一張表，是攔下一個會在單一使用者驗收下全部通過的缺陷。
- 2026-10-01T23:03:08Z — **能力 11 需要一張自己的五面向判定表，而我修訂 3 時只為能力 12 立了表。** 修訂 3 那張表的四個「否」（不引入新服務／新暴露面／新依賴／新技術層）是**能力 12 的**；能力 11 在 `[S18]`=A 之後是四個「是」。若不另立一表，讀者會把能力 12 的結論套到能力 11 身上——而那正好是本 intent 風險最高的一項（repo 內零 MCP 前例、`A-7` 未實測）。已在 Go／No-Go 段明寫「不得把能力 12 的四個否讀成能力 11 也是如此」。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-23T23:22:55Z — 本站只問 5 題，落在 Standard 深度 5–8 題的下緣。理由是四站核可關卡已通過、兩站為 SKIP，絕大多數內容都有可引用的定案；5 題全部集中在同一種缺口——「上游做了決定但沒指名誰執行」。依 `approval-handoff:c1` 把省略清單與逐項依據寫進問題檔前言，而不是只在日記交代。
- 2026-10-01T23:03:08Z — **檢查 4 的 4c 差一點讓我去「修正」三份正確的文件。** 以關鍵詞比對「11 Must」時 `scope-document` 與 `initiative-brief` 都是 0 命中，看起來像三份文件不一致；改以欄位解析實算才確認一致——它們以表格形式 `| **Must** | 11 |` 陳述，連續字串比對命中不了。**關鍵詞比對對表格形式的陳述無效**，而若當時直接判為矛盾並動手，會改壞正確的內容。這與本輪的另一個教訓同形：關鍵詞計數是代理指標而非證明（檢查 2 的八項也有兩個 0 命中，逐一判讀後一個假象一個真殘留）。
- 2026-10-01T23:03:08Z — **檢查 4b 的 7 處 `:328` 殘留裡，有 2 處是不得編輯的審查員紀錄。** `reviews/review-06.md` 與 `review-08.md` 引用了錯誤行號（review-06 甚至寫「已直接讀檔確認 `:328`」並判定 accurate），但那是審查員的證據，改它就不再是審查員的紀錄。另 3 處 `memory.md` 是日記在引述錯誤本身，正確。真殘留只有 2 處，皆在已核可的 `scope-definition-questions.md`，依 `refined-mockups:c3` 記在本站而不回改上游。**逐處判讀與一律替換的差別，在這裡就是 5 處誤改。**

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-23T23:22:55Z — H4 的四個落點中，只有 `tcms-test-cases`（3.8）是 `execution: ALWAYS`、不可能被 skip，也只有 `contract-design`（2.8）能從結構上預防兩份 runtime 漂移——「不會被 skip」與「能預防」不可兼得。處置是把這個取捨在摘要確認前完整攤開讓決策者自己選，再用轉移規則補回被放棄的那一半，而不是由我替他挑一個看起來比較好的。
- 2026-09-23T23:22:55Z — 交接表第 11 列（Jev）找不到誠實的轉移目標：`nfr-requirements`（3.2）被 skip 時，唯一主題相鄰的 `nfr-design`（3.3）的執行條件正是「NFR Requirements 已執行」，必然一併 skip。選擇寫「無自然承接站」並指定屆時判定 skip 的 conductor 重新提交給使用者，而不是填一個看起來合理的站。填假目標會讓表格看起來完整，實際上是死指派——比空著更糟，因為空著至少看得出來。
- 2026-10-01T23:03:08Z — **第 19、20 列的轉移目標寫成兩層，不是過度防衛。** 兩者的自然承接站（`contract-design`、`infrastructure-design`）都是 `CONDITIONAL`，而第一順位轉移目標 `functional-design` **也是** `CONDITIONAL` 且為 per-unit——到 `code-generation`（`ALWAYS`）為止才有保證。本 intent 已有兩次指派落空的實例（`[H6]` 的目標站是 `ALWAYS` 但已完成且在游標之前；第 11 列的 Jev **無自然承接站**），所以成本是多寫一欄，不寫的代價是第三次落空。
- 2026-10-01T23:03:08Z — **`需求欄位` 的窄殘留併入既有第 12 列而不另立交接列。** 它與能力 3／5／6 的風險型態（需求寫不清楚而非做不出來）、承接站（`requirements-analysis`）、處置方式（定義可測不變量）完全相同。另立一列只會讓 21 列的交接表更長而不更清楚——而交接表的用途是讓下游一眼看出該接什麼，不是窮盡列舉。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-23T23:22:55Z — 本站訂定的轉移規則（CONDITIONAL 站被 skip 時義務自動轉移至指定站）沒有任何機械檢查承載，生效完全仰賴屆時的 conductor 讀到 `initiative-brief.md` 的交接表。這是個可以做成 sensor 的形狀（掃 artifact 內的「指派給 <stage>」字樣、比對 stage-graph 的 execution 欄、要求 CONDITIONAL 者必須附轉移目標），但本站未提案，留待日後。
- 2026-10-01T23:03:08Z — **R-07 未修，帶進本站的交接表而非在 rough-mockups 修完。** 那一輪 `reviewer_max_iterations` 為 1，改產出會讓 READY 收據失效而無第二次可記。使用者於該站關卡選擇帶進本站處理——實際落點是交接第 19、20 列（`C-T11` 與第二個進程邊界），比寫在線框檔的 Assumptions 更到位，因為它們產生的是**下游工作**而不是畫面說明。

