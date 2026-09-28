<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-23T15:49:54Z — Depth 為 Standard，產出 8 題；並在問題檔前置一張「已由上游定案、不重問」表，13 項逐項附**可逐字複驗的出處**（ADR 節次／constraint 編號／[feas:Q<n>] 選項字母），依 `project.md ## Corrections` 的可引用性規則——引用不出來就代表未被定案、應補問。
- 2026-08-23T15:49:54Z — 把 Q1／Q7／Q8 由 5 個選項收斂為 4，因為 harness 每題上限為 4；收斂方式是**先改問題檔再提問**（Q1 把原 D 的「不映射清單」併進 A、Q7 把原 C+D 的兩個 concurrency 選項合併），確保「問題檔內容」與「實際問出去的選項」逐字一致，而不是在提問時臨時換一組。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-23T15:49:54Z — 追問 F1～F3 為本站在 Step 8 矛盾偵測後新增，不在原 8 題內；三題皆為**已選答案之間、或已選答案與已核可上游之間**的字面牴觸（F1 暫停覆寫窗口 vs 一致率為 0；F2 回寫路徑從未被指定；F3 排隊不取消 vs 5 分鐘上限），非措辭模糊。
- 2026-08-23T15:49:54Z — 第二輪矛盾偵測發現的兩項不另開題，改以「**改寫需求本文加適用前提，使字面不再衝突 ＋ 把收斂手段列為指派給下游的開放決策**」處理（NFR-S1 與 OQ-1、NFR-P3 與 R-2）。依 `project.md ## Corrections`：只記進 Assumptions 並指派下游只做到 surface、沒做到 resolve，兩者缺一都會讓下游把待決事項讀成已定案。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-23T15:49:54Z — 選擇**不為「機制需要 repo 內容寫入權」另開一題**：CAP-1（[feas:Q8]）、Q6=A、ADR-0013 §2 三項已核可決定各自都逼出該權限，沒有可選的替代答案，出一題只會是單一可行解的假選擇。改為在 Step 10 的 Consolidated Summary 明白揭露後果（含「本 repo 最大的單一權限授予比 feasibility 當時預期的更大」），讓使用者在確認點看到再按下 Looks correct。
- 2026-08-23T15:49:54Z — Q1 的對照表刻意不寫入 `Backlog`／`Nice to have` 兩格：換得「人工分類不會被機制覆蓋」，代價是看板左側兩格的語意完全由人維持、機制不保證其正確。此取捨與本 intent 的核心價值（可信度）一致——寧可不寫，不可寫錯。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-23T15:49:54Z — OQ-7（PR #508 已合併的 `scripts/aidlc_sync_*.py` 三支腳本，與 ADR-0013 §3 及 `project.md ## Forbidden` 的衝突）仍**待使用者裁決**，本站與 reverse-engineering 皆只記載不裁定。它會實質影響 construction 的落點：若決定遷移到 gh-aw，那是本 intent 之外的額外工作量。
- 2026-08-23T15:49:54Z — `upstream-coverage` sensor 對本站 `consumes` 清單的判定方式未實測。該清單含 `team-practices`，而本 intent 的 scope 跳過 `practices-discovery`、該 artifact 不存在。本站的處置是在「上游輸入」段落**具名並說明缺席理由**（比照 ideation 各站對 competitive-analysis／wireframes 的寫法），但 sensor 是否接受這種寫法未經驗證。
