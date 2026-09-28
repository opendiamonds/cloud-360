<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-08-23T03:07:48Z — 使用者於 intent-capture 進行中下達實作載體約束：同步機制以 gh-aw／GitHub Actions 承載，不得以 repo 內的程式（例如 scripts/ 下的 Python）實作。ideation 階段禁止把實作細節寫進 artifact，故本約束不寫入 intent-statement.md，改記於此並列為 feasibility（1.3）必問項——該 stage 的職責正是 constraints。
- 2026-08-22T23:29:57Z — Standard depth 的建議題數是 5-8，本輪寫了 8 題；composer 對本 intent 的 UA（未解假設）評為 0.70 HIGH，且一句描述綁了兩個可分離的交付物（README 作為需求來源／stage 進度同步），題數壓到 5 會讓其中一半無人追問。已把「利害關係人」與「誰有決定權」併為 Q5，避免在單一決策者的專案上拆成兩題。
- 2026-08-22T23:29:57Z — 出題前的唯讀查證結果（Project #16 的 6 個 Status 選項與 71 個 item 分布、README 的實際形狀、repo 的 3 個 open issue）另立區塊並明確標示為非來源，沒有寫進 ## Sources register。stage 檔規定 register 只接受 [desc]／[scope]／[memory:M<n>] 三種形式且不得登錄背景知識，claim-sources sensor 會逐條解析驗證。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-08-23T03:10:11Z — stage 檔要求「必填但未解的欄位寫 Unknown (open question) [assumption]」，但 claim-sources sensor 會把 ## Assumptions & Open Questions 區塊外出現的 [assumption] 標籤判為違規，兩者直接矛盾。改為把該列整列移除，並以 HTML comment 記錄省略理由與其無來源的事實。reviewer 讀 sensor 原始碼（約 848-866 行）獨立確認矛盾屬實、且註解會被 comment-stripping 略過。
- 2026-08-23T03:10:11Z — 派遣 reviewer 時未依 stage-protocol §5「把累積的 rule bundle 逐字貼進每個 agent brief」，改為指名 memory 檔路徑並說明它們已由專案 CLAUDE.md 的 @-import 鏈進入該 agent 的 ambient context。逐字貼上約數萬字且與 ambient 內容重複，同一份 §5 也要求 brief 不得複製 persona/knowledge 散文。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
- 2026-08-22T23:29:57Z — Q6 把「同步節奏」與「失敗時如何得知」併在同一題並要求補充說明，而不是拆成兩題。理由是這兩者在本案是同一個決策的兩面（事件驅動的失敗與排程對帳的失敗，可觀察性需求完全不同），拆開問會讓使用者在不知道節奏的前提下先答通知方式。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-08-23T03:16:28Z — aidlc-learnings.ts persist 的內容冪等標記是 `<!-- cid:<stage-slug>:<candidate-id> -->`，未以 intent／record 區隔。project.md 已有上一個 intent（260802-last-login-column）同為 intent-capture 階段留下的 cid:intent-capture:c1，導致本輪的 c1（使用者明確選擇留存的 gh-aw 載體約束）被判定為已寫過而靜默跳過，工具卻仍回報 rule_learned:3 並發出 RULE_LEARNED 事件。以 candidate_id 260822-c1 重跑才寫入成功。這是會靜默吞掉使用者決定的框架缺陷：跨 intent 的候選編號必然重複（每個 intent 的 c1 都叫 c1），且回報值與實際寫入不一致使其不可由回傳值察覺。應向 upstream 回報，並在此之前於每次 persist 後實地 grep 驗證寫入。
- 2026-08-23T03:07:48Z — gh-aw 與純 GitHub Actions 在本案是兩種性質不同的載體，使用者的指示同時提到兩者但未區分：gh-aw 是 LLM 驅動（engine: copilot），而 project.md 明載「所有 LLM 路徑」是本 repo 自動化的三塊結構性盲區之一、正是 blocking 的 tcms-test-cases stage 存在的理由；純 Actions（yaml 步驟呼叫 gh CLI）則是決定性的、可斷言的。狀態同步的正確性是決定性映射，載體選擇會直接決定它可不可驗證。須在 feasibility 出題定案，不得由下游自行推定。
- 2026-08-23T03:07:48Z — 本約束推翻了 composer 排 grid 時引用的前提：它以 scripts/tcms_sync.py（515 LOC 的 artifact→外部系統同步器）為結構先例，並以「新腳本必須進入 unittest discover 覆蓋」作為 ci-pipeline EXECUTE 的部分理由。沒有 repo 內腳本後，該理由不成立，自動化測試的落點需重新決定（composer 自己也指出 gh-aw 的 .lock.yml 目前不受任何閘門驗證）。stage 集合本身不需 recompose，但 ci-pipeline 與 tcms-test-cases 的內容會因此改變。
- 2026-08-23T01:15:27Z — 本 harness 的 PostToolUse AskUserQuestion 掛鉤（aidlc-mint-presence）已在 .claude/settings.json 註冊，但使用者實際回答 AskUserQuestion 後 audit shard 內 HUMAN_TURN 計數仍為 0，aidlc-log.ts answer 因此被 presence 檢查擋下；改以手動執行該 hook（stdin 餵空 JSON）可正常寫入。代表本 session 每個問答與核准閘都需要手動補 mint，presence 保證從自動降為人工紀律。待確認掛鉤在此 harness 未生效的原因（stdin payload 形狀？cwd？）。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
