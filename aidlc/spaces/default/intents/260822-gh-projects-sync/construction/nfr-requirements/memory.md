<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-08-29T13:29:57Z — U-8：缺口 P-1。NFR-S1 把「開 PR（FR-G1）」歸進「repo 內容寫入」，但 `.github/workflows/deploy.yml:174-175` 在本 repo 上正在運行的設定把推分支（`contents: write`）與開 PR（`pull-requests: write`）分列兩行且各有註解——權限集合是**四項**不是三項。這與 ADR-0014 剛修掉的 K-1 是同一類歸併錯誤：**修一個歸併錯誤時沒有掃描同句話裡的其餘歸併**。
- 2026-08-29T13:29:57Z — U-8：缺口 P-2。NFR-P3 的兩組 concurrency group 窮舉的是「事件 vs 排程對帳」，反向同步是排程但不是對帳，落在兩者之外從未被指派。裁定自成第三組且 `cancel-in-progress: false`——中途取消會停在「`pending_reverse` 已寫、PR 未開」這個唯一不一致視窗上。
- 2026-08-29T13:32:57Z — U-10b：逐檔解析 `.github/workflows/*.md` 的 `on:` 區塊，**六支**吃 `pull_request`，其中 `code-drift-alert`／`local-dev-drift` 已有 `paths:` allowlist 自我排除，**四支無過濾**（`ui-regression`／`pr-reviewer`／`lint-fix`／`contract-guard`）。加上 `ci.yml`（U-10a 負責），一則反向 PR 發動五組 workflow。單元定義的完成判準只點名 `ui-regression`。
- 2026-08-29T13:32:57Z — U-10b：單元定義寫的替代方案「等價的 label 機制」在觸發層不存在——GitHub Actions 的 `on:` 只有 `branches-ignore`／`paths-ignore`／`tags-ignore`，**沒有 `labels-ignore`**。label 只能做到 job 層 `if:`，仍會配 runner。故機制定為 `paths-ignore`，與 U-10a 同一條 glob、不同檔。
- 2026-08-29T13:43:35Z — U-9：缺口 Q-1。完成判準第 3 條要求「憑證做範圍外寫入時回 403」，但 NFR-S1 的第 1 項是**組織層** Projects 讀寫——組織層授權下沒有任何組織內的 Project 是範圍外的，該斷言因此恆不可能成立。依 `project.md` 的既有教訓（恆真 AC 改寫而非刪除），防禦意圖為真、落點錯誤，指派 units-generation 的 U-9 完成判準第 3 條，確認人為 Bolt 0 的 gate（與缺口 P-1 同一決定點）。指派目標是 EXECUTE stage 而非 CONDITIONAL，無無聲落空風險。
- 2026-08-29T13:43:35Z — U-9：失敗語意必須分「斷言失敗」與「外部錯誤」兩類且第一行即可辨。兩者在 CI 上長得一樣時，人會學會「紅了就重跑」，而那正是第一類最不該得到的反應。連帶：第二段刻意**不重試**（與 U-6／U-7 相反）——靠重試才綠的驗證，證明的東西比它宣稱的少。
- 2026-08-30T05:10:02Z — 送審前自檢（`project.md` 強制、非 functional-design 專屬）在派 reviewer 之前跑完六項，找到 **2 個真缺口 ＋ 1 個一致性觀察**：
①【檢查 2 契約端點三問】**U-2 的 SEC-2 白名單約束會禁止渲染 [US:S-6 AC 5] 的告示**——該節逐字禁止 `render` 輸出任何未在其四列表格中列出的欄位，而 functional-design 的 ADR-0015 §12 為 `Block`／`Context` 增設了 `rejection_notice`，表格沒同步。**安全約束與功能規則直接衝突**，且方向是「安全規則把功能擋掉」而非留洞。已補列並在約束句加上「每新增欄位必須同步本表」的維護提醒。
②【檢查 6 可算的數字】U-1 的 IAM 判定仍寫「output 是四個字串」，而 functional-design iteration 4 已增設第五個 output `scope_note`。
③【檢查 4 檔案集合一致性】12 個單元中只有 3 個（U-1／U-2／U-10a）有 `nfr-requirements-questions.md`，其餘 9 個沒有。份數本身符合 `produces_kinds`（library 2 份、service 5 份、ui 3 份、無 kind 的 U-11 全 5 份），問題在**問題檔的有無沒有一致的判準或說明**。列為觀察，未改。
- 2026-08-30T05:10:02Z — 檢查 3（引用逐字核對）發現 `ADR-0006` 在本 intent 的 `inception/decisions/` 不存在——它在 baseline record（`260802-default`）且檔名為 `0006-adopt-aidlc-framework.md`。**引用有效，非缺陷**；記下來是因為 nfr 層有 10 處引用它，而跨 record 的 ADR 引用在本 intent 是第一次出現，下一個做同型核對的人會撞到同一個假警報。
- 2026-08-30T05:48:54Z — 單輪審查合計 **5 Critical、9 Major、6 Minor**，READY 7 個／NOT-READY 5 個。**與 functional-design 最大的差別：這次沒有任何一項是「修正自己造成」**——原因是本 stage 從一開始就套用了那個順序（所有編輯在派工前做完、收據最後），所以 reviewer 看到的是一個穩定的狀態，而不是我邊修邊審的移動標靶。
- 2026-08-30T05:48:54Z — 兩個最有價值的發現都是**「機制在它自己指認的失敗路徑上無效」**這個形狀：①U-10a 選 `paths-ignore` 擋 `pull_request`，而該事件的路徑過濾比對的是**整個 PR diff** 不是本次 push，同步回寫進到有 PR 的分支時過濾永不成立——而它自己 `:29` 就寫「真正會發動的是 `pull_request`」；②U-9 的靜態檢查指向 `.md`／`.lock.yml`，而四支 workflow 已定案為純 `.yml`，唯一的機械化閘門恆綠。**兩者都不是「漏寫」，是選了一個對自己已寫下的診斷無效的機制**——與 `functional-design:c10`（偵測 X 而 X 不可達）同源，但發生在機制選擇層而非規則層。

## Deviations
- 2026-08-29T13:29:57Z — P-1 依 `units-generation:260822-ug-L2` 的形狀處置（標缺口、寫明哪條 AC 不可滿足、指派具體落點），**未逕自修改 NFR-S1 或 ADR-0014**；兩者都已通過核可，與 U-4 那兩處（本站自己尚未過閘的產出）性質不同。指派目標非 CONDITIONAL stage，故無該規則所指的無聲落空風險。
- 2026-08-29T13:32:57Z — U-10b 的完成判準由「`ui-regression` 未執行」擴大為「四支皆未執行」（未經人工提問）。`ui-regression` 最貴（其註解逐字記載 PR #510 燒掉約七小時 runner、零測試執行），但另三支 `engine: copilot` 是 LLM 路徑，會對機器產生的單檔 PR 產出 AI 審查留言並吃額度。只擋最貴那支達不到 [US:S-6 AC 7] 的意圖。
- 2026-08-29T13:43:35Z — U-8 的承載形式先前誤寫為 gh-aw 的 `.md` ＋ `.lock.yml`，已更正為純 Actions 兩檔拆分。三處一致依據：[ug:unit-of-work.md] U-8 交付欄逐字、U-6 與 U-7 的 tech-stack 皆已定案為純 Actions。ADR-0013 §3 的承載位置表仍記 `.md`（gh-aw 形式），該落差的收斂發生在 U-6，本站沿用不重開。
- 2026-08-29T13:43:35Z — U-10b 的機制（`paths-ignore`）與 U-6 的 D-1 裁定**理由**相左：D-1 把「`branches-ignore` 讓 run 根本不被建立」列為選擇分支前綴的優點之一。對 `pull_request` 事件，`branches-ignore` 過濾的是 base 而非 head，若此說成立該理由不成立——但本站在 repo 內找不到可複驗的設定，故不當成已證實。選 `paths-ignore` 的決定性理由是**它在兩種讀法下都正確**。D-1 的裁定本身（分支前綴＋label）不動，只是不把 U-10b 押在它上面；語意查證併入 PRE-1 的同一則測試 PR。
- 2026-08-29T13:43:35Z — U-8 的分支名由 D-1 的 `aidlc-sync/reverse/<date>` 擴充為含 `<intent_id>`。這是 E-2（一 intent 一 PR）的必要後果而非偏好：同一天兩個 intent 被改動時 `<date>` 無法區分，兩則 PR 會撞同一分支名。D-1 作成時尚無 E-2。
- 2026-08-30T05:10:02Z — **本 stage 從一開始就套用 functional-design 學到的順序**：所有編輯（兩項 open item ＋ 兩個自檢缺口）在派 reviewer **之前**做完，收據留到最後。functional-design 花了七輪才發現這個順序——引擎的收據新鮮度規則（「A later declared-artifact write clears the matching receipt」）使「先審後修」必然作廢收據，而我前六輪每次都這樣做。
- 2026-08-30T05:27:01Z — **兩組 reviewer 首次派工雙雙超時，根因是我給的讀取面過大**：`exempt` 有 97 筆，而 brief 又禁止目錄操作，於是它們逐檔 `Read`、一次一個 round trip。停掉時 Group A 還停在讀 manifest、Group B 才讀到 U-1／U-2。**不是 agent 慢，是派工設計錯誤。** exempt 的作用是「可讀範圍」（安全邊界），不是「該讀清單」（工作量）——我把兩者混為一談，等於要求它們讀完整個 record。
- 2026-08-30T05:27:01Z — 復原時只加兩點：**先寫骨架再分批補**（讀完兩三個單元就寫表頭與骨架，之後逐列 Edit，不等全部查完才一次寫入），以及**明講 exempt 是可讀不是該讀、本輪只需要哪幾份**。第一點針對的是「跑很久然後一無所獲」這個失敗模式——functional-design 的 iteration 5 已經因此損失過一整輪（Group B 死在『正要寫入』那一步，分析全部丟失）。**這條該在那時就寫進派工預設，而不是等到再犯一次。**
- 2026-08-30T05:48:54Z — U-1 的 Q2 出現**人工裁決紀錄矛盾**：`[Answer]` 記 A（「不設額外防線」），而同行註解與 artifact 逐字都是選項 C（「列為 U-9 斷言」），使 U-9 背的跨三個 Bolt 交付約束壓在一個沒被記為選中的選項上。依 `user-stories:260822-us-L3`**重新取得人工裁決**（C）而非替它主張原意——從紀錄上看，「堅持」與「造假」無法區分，重取的成本遠低於讓下游繼承一份無法查證的授權。這是本 session 第二次套用該規則，兩次都成立。
- 2026-08-30T05:48:54Z — §13 的 learnings 問題已呈示（三項候選：exempt 是可讀範圍非該讀清單／先寫骨架再分批補／機制選擇的可達性），**使用者未作答，故未 persist 任何規則**。不推定為「無新增」——三項候選仍在本 diary 與 `aidlc-learnings.ts surface` 的輸出中，下一個 stage 或使用者主動提起時可重新呈示。

## Tradeoffs
- 2026-08-29T13:29:57Z — U-8 的憑證選擇（`GITHUB_TOKEN` vs 專用憑證）**不預選**。它同時決定 P-1 是否適用、以及反向 PR 會不會觸發 `on: pull_request`（即 U-10b 的必要性）。後者我在本 repo 的 11 支 workflow 與 `.lock.yml` 中找不到任何設定或註解可據以斷言，故不斷言；改為指派 PRE-1 一次實測同時解掉兩者，成本近乎為零。預選會把一個可消除的不確定性變成賭注。
- 2026-08-29T13:43:35Z — U-9 的靜態檢查腳本用 `python3` 放 repo 內，形式上落在 `project.md ## Forbidden` 那條「不得以 repo 內新增的實作程式承載無人值守流程自動化」的觸發來源判準內（`pull_request` 觸發）。本站判定不適用——規則的標的是「承載同步機制」而非「驗證機制」，且與既有的 `validate_repo_contract.py`（同樣 CI 事件觸發、同樣 repo 內 Python、且是 contract 正式來源）完全同類。**但這條規則是使用者本 session 才收窄過的，判定須在 Bolt 4 的 gate 被確認，不由本站單方面定案。**

## Open questions
- 2026-08-29T12:34:05Z — **stage 契約自身的不一致**：nfr-requirements 的 `consumes` 把 `business-logic-model` 列為 `required: true`，但 functional-design 的四項 `produces_kinds` **都不含 `packaging`**——所以 `kind: packaging` 的單元（U-10a／U-10b）永遠產不出該 artifact，卻在本站被要求引用它。本輪的處置是引用**消費端 U-4 的** `business-logic-model`（U-10a 存在的理由就是服務 U-4 的回寫行為，這個引用有實質內容而非為過 sensor）。此為 upstream 框架檔的問題，不在本專案的修改範圍（`project.md` 禁止改 `.claude/` 表達專案規則）。
- 2026-08-29T13:29:57Z — 反向同步沒有對應 FR-D3／NFR-P4 的批次上限，而它做的是與對帳同量級的掃描。本站不自行補數字（無依據的參數），指派為 C-T5 上限值確認時一併決定。
- 2026-08-29T13:32:57Z — U-10b 的排除機制有一個**跨單元的靜默失效路徑**：`paths-ignore` 只在變更檔案「全部」命中時才跳過，而反向 PR 只動一個檔是 E-1（U-8 的裁定）的後果。未來若有人為反向 PR 多加一個檔，五組 workflow 會重新開始跑且無任何訊號。成因在 U-8、後果在 U-10b，兩邊都已寫入，但**沒有自動化斷言**——與 U-8 的原子性規則同屬「U-9 須明確承接或明確拒收」的清單。

