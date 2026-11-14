<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-09-21T09:41:39Z — iteration 2 審查的 R-05（Critical）指出：修訂 1 把成本關注者改為直接服務後所製造的新張力，與本 stage 稍早以 Q10 處理過的張力**形狀完全相同**（服務對象 vs 共享頁面範圍），但我對前者加開問題讓使用者定案、對後者卻自己寫了一句推論句並掛 [Q7] 標籤。逐字核對 Q7／Q12 的作答，兩題都沒有一個字支持那句話。已加開 Q14 由使用者定案（=A 就地在入口頁呈現），並把兩檔的標籤改掛 [Q14]。
- 2026-09-21T09:41:39Z — R-07 揭露我先前的查證方式有結構性缺陷：以 `grep "CREATE TABLE.*cost"` 取得三張表名就當成「成本能力存在」的證據，未讀其區塊標題與 COMMENT——那三張表逐字標註「RETIRED … app must not read/write」，方向與結論相反。結論本身由其他證據獨立成立，但引用的證據是反的。已改引用現行六張表並註明取得方式。
- 2026-09-21T09:24:28Z — 修訂 1：回跳本站的觸發是上游前提失效，但實際查證發現失效的是**兩項**不是一項——V2（成本能力不存在）與 V6 的 LangGraph 半邊（引用為 0）皆被 PR #647 推翻，V6 的 Redis 半邊仍成立。原本只記錄了 V2 一項，代表當時的影響評估本身也是憑印象而非重跑查證。處置為新增 V7／V8／V9 addendum，V2／V6 原文保留（它們記載的是當時為真的事實）。
- 2026-09-21T09:24:28Z — Q13（編排層落位）是 V8 揭露後才存在的岔路，修訂前的產出裡完全沒有這個維度。這說明「上游前提失效」不只會讓既有答案過期，也會讓**原本不需要問的問題變成必須問**；只比對既有主張是否仍成立，會漏掉後者。
- 2026-09-20T17:55:24Z — Q5 定案為「本次一併建立專案／系統階層」，使本 intent 從「加一層編排」擴為「同時建立新的核心資料模型」。此決定會觸發 project.md 的 blocking 規則（schema_rbac.sql 與 DEPLOY.md 必須同步），下游 feasibility 與 scope-definition 必須把它當成第一級範圍項而非附帶工作。
- 2026-09-20T17:30:29Z — 描述中的「專案 → 系統 → 架構圖」階層在 repo 中不存在，故不視為既有事實而改列為 Q5 的待決問題；`schema_rbac.sql` 只有 users→user_diagrams，backend 全樹 `system_id` 命中 0 次。若逕自當成既有階層，整份需求會建立在一個不存在的資料模型上。
- 2026-09-20T17:30:29Z — 描述點名的「成本及 FinOps agent」在 repo 中只有 `FinOps_Analyst` 這個 RBAC 角色，沒有任何成本資料、服務或模組，故 Q6 把「編排既有能力」與「同時建成本能力」拆成不同選項，讓範圍差異顯性化。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-09-21T09:24:28Z — Consolidated Summary Confirmation 與 Assumption Confirmation 依規則清空後，我是**先改 artifact 再重新取得確認**，順序與 PRE-GENERATION SUMMARY STOP 相反。理由是 Modify 模式下被確認的對象就是那份修訂後的內容，但這確實是與協定字面的偏離，如實記載而非事後合理化。
- 2026-09-21T09:24:28Z — 一併修正了前一輪審查的 R-01／R-02／R-03（三項在上一輪以 advisory 呈到關卡後未被修就通過）。嚴格說這超出「修訂失效前提」的範圍，但它們就在我正在改的段落上，且 R-02 的矛盾會直接誤導下游的資料模型層級判斷。
- 2026-09-20T17:55:24Z — 收齊答案後的矛盾偵測抓到兩處跨題不一致（Q2 的管理者 vs Q7 的共享範圍、Q2 的成本關注者 vs Q6 的成本空殼），依 stage-protocol §3 加開 Q10／Q11 當場定錨並回寫問題檔，未讓歧義流入下一階段。問題數因此由 9 增為 11。
- 2026-09-20T17:30:29Z — 依 project.md 的 `intent-capture:c3`，出題前的唯讀查證結果（V1–V6）寫進問題檔的獨立「查證紀錄（非來源）」區塊，未登錄進 `## Sources` register；register 僅保留 [desc]／[scope]／[memory:M1–M3] 三種允許形式。
- 2026-09-20T17:30:29Z — 問題數為 9 題，略高於 Standard depth 的 5–8 題指引。理由是本 intent 橫跨編排框架、session 層、三種記憶、串流、推播與多意圖識別六個面向，且其中兩個面向（專案階層、成本能力）的前提在 repo 中不成立，壓到 8 題以內會使其中一項無法被問到。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
- 2026-09-21T09:41:39Z — Q14 定案為 A（就地在入口頁呈現）而非 C（導向 /cost）。取捨是：A 讓 Q7=A 已核可的三頁範圍維持不變、不觸發回跳上游修訂，代價是入口頁要承擔巢狀串流轉送——而該代價已是登記在案的未定案項（Assumptions 第 5 條），不是本題新增的負擔。
- 2026-09-21T09:24:28Z — Q13 使用者選 B（大腦自建獨立 runtime），而 A（沿用既有）在「單一真實來源」上明顯較優。代價已在選項說明中揭露並由使用者知情選擇，處置是把「鎖住兩份 runtime 一致性的驗證」下推為 feasibility 的約束項，而不是在本站推翻決定或在 artifact 裡淡化代價。
- 2026-09-21T09:24:28Z — 成本關注者改為直接服務對象後，與 Q7=A（共享範圍不含成本頁）形成與 Q10 完全相同形狀的潛在矛盾。選擇在 artifact 本文加適用前提讓字面不再衝突（依 user-stories:c9），而非只記進 Assumptions 指派下游——後者只做到 surface 沒做到 resolve。
- 2026-09-20T17:55:24Z — Q11 定案為 B（空殼要能正確回「尚未提供」）而非 C（實作最小成本能力）。取捨是：保住「成本關注者」這個角色在第一版有可驗證的行為（路由正確、回覆明確），同時不把成本資料來源這個獨立子系統拉進本 intent——而本 intent 已因 Q5=B 承擔了新資料模型。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-09-21T09:41:39Z — 本檔 2026-09-21T08:59:32Z 那筆 Open questions 的內容有誤，在此更正而非刪除：它寫「`schema_rbac.sql` 有 `archive_diagram_cost`、`archive_diagram_cost_line`、`archive_cost_audit_event` 三表」並以此作為成本能力存在的證據，實際上這三張表是明文退役、app 不得讀寫的表（見 iteration 2 的 R-07）；現行成本表為 `estimate_sets`／`estimates`／`estimate_line_items`／`estimate_shares`／`estimate_audit_events`／`advice` 六張。該筆同時把下游受影響落點寫為「共 8 處」，實算為 feasibility 6 處、scope-definition 11 處。
- 2026-09-21T09:24:28Z — claim-sources sensor 在修訂**之前**就是紅燈（11 項發現），而該 sensor 自 2.7.0 升級後未再變動，故非版本漂移——代表上一輪的關卡是在 blocking sensor 紅燈的情況下通過的，機制上如何發生尚未查明。本輪已依通過的同類單元（260822-gh-projects-sync）量測慣例修好並全綠，但「為什麼上一輪能過」這件事本身值得在下一次 practices-discovery 追查。
- 2026-09-21T09:24:28Z — 下游受影響落點經 grep 實算為 feasibility 6 處、scope-definition 11 處（原診斷寫「共 8 處」是憑印象低估）。feasibility 的 C-T9「repo 內不存在任何設定類端點」需在該站重新查證——成本能力新增的 10 條端點中雖無設定類端點，但該句是在成本能力不存在時寫的，其依據已不同。
- 2026-09-21T08:59:32Z — **上游前提已失效，待以 Modify 模式回跳修訂**。本 intent 的 intent-capture 查證 V2 記載「成本／FinOps 能力完全不存在，`FinOps_Analyst` 只是 RBAC 角色名」，該事實在當時為真，但 `ut` 已於 2026-09-20T14:43Z 合併 PR #647（cost-estimation-finops），成本能力現已存在且規模不小：`backend/cost/` 套件含 `estimate_intake_router` 與 `advice_stream_router`；`/api/cost/v1/` 下 6 條端點，其中 `GET /sets/{set_id}/advice/stream` 為**串流式成本建議**；前端有 `CostPage`（路由 `/cost`，`can('C1','view')` 者登入即導向）；`schema_rbac.sql` 有 `archive_diagram_cost`、`archive_diagram_cost_line`、`archive_cost_audit_event` 三表。故第一版的問題不再是「要不要做一個會回『尚未提供』的空殼」，而是「大腦要怎麼編排一個已經存在、且自身也有串流的成本 agent」——這是不同的問題，不是同一問題的細節修正。受影響落點經逐一核對為 8 處：intent-capture 的 V2／[Q6]=C／[Q11]=B、`intent-statement.md` 的 Target Customer 成本列與 Initial Scope Signal、`stakeholder-map.md` 的成本關注者定位、feasibility 的 S 條目與能力表成本列、`constraint-register.md` 的 C-T9／C-S2、scope-definition 的 S3／S9 與 `scope-document.md`／`intent-backlog.md` 的分級與序 9。使用者已裁決**跳回 intent-capture 以 Modify 模式修訂**（非 feasibility——過期事實與 Q6／Q11 的決定都在 intent-capture）。未於本 session 執行的理由：AI-DLC 框架於本 session 期間由 2.7.0 升級至 2.9.0，指令介面與 stage 協定均已變更，而本 session 載入的是 2.7.0 協定；以舊協定驅動新引擎執行會動到生命週期狀態並重走三道關卡的操作，風險是污染稽核紀錄。應由新 session 以 2.9.0 協定執行。
- 2026-09-20T17:30:29Z — 「openrouter 的 gemini flash 3.7」型號存在與否，先前判斷有誤已由使用者更正為 `google/gemini-3.7-flash`；本機端為 Claude Code CLI 的 Claude Sonnet。兩者屬實作層選擇，本階段不寫入產出，待 feasibility／nfr 階段定錨。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
