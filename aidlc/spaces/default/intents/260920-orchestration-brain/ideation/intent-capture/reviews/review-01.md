## Review

**Verdict:** NOT-READY

<!-- 審查員依 conductor brief 的評分規則寫的是「NEEDS REVISION」
     （brief 原文：有任一 Major 以上給 NEEDS REVISION）。引擎的正規 token 為
     READY / NOT-READY，語意相同，此處僅做 token 正規化，審查判斷未被改動。
     artifact 內的 Review 區塊保留審查員原文。 -->
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-09-21T09:27:44Z
**Iteration:** 1

<!-- 審查員寫 2，是把回跳前那一輪（stage 重置前）算進去；回跳已重置本 stage，
     引擎端本輪的 review ordinal 為 1。此處對齊引擎編號，審查內容未改動。 -->

### Findings

| ID | Severity | Location | Finding | Required action |
|---|---|---|---|---|
| R-01 | — | `intent-statement.md`（「本次確認納入產品邊界的能力（內容來自使用者的原始描述，「納入邊界」這個確認動作本身由 Q9 的作答支撐）[desc][Q9]：…」） | **Resolved.** 修訂 1 已把標籤補為 `[desc][Q9]`，並在句中明講「納入邊界」這個確認動作由 Q9 支撐。與 iteration 1 的要求一致。 | 無。 |
| R-02 | — | `intent-statement.md`（「系統各自有其成本，而**跨雲分析是專案層級**的面向。[desc]」，對照 Assumptions 第 2 項） | **Resolved.** 跨雲分析已改回專案層級，與 Assumptions 第 2 項及原始描述逐字（"跨雲分析（by專案）"）一致，矛盾消除。 | 無。 |
| R-03 | — | `intent-statement.md`（「系統必須能明確指出使用者當下正在處理哪一個對象。[Q5]」） | **Resolved.** 句尾已補 `[Q5]`。 | 無。 |
| R-04 | Minor | `intent-statement.md` Success Metrics ＋ Assumptions 第 1 項 | 未變動，仍為非阻擋事項：三項成功指標門檻值全數留待後續階段。 | 非阻擋；建議下游 stage 優先處理。 |
| R-05 | Critical | `intent-statement.md` Target Customer 表「成本／FinOps 關注者」列（「適用前提：共享工作階段的頁面範圍仍為下方三處、不含成本頁面——服務是在入口處完成的，不以該頁加入共享範圍為前提」，標為 `[Q2][Q12][Q7]`）；`stakeholder-map.md` 同一列（標為 `[Q2][Q12][Q7]`） | 本輪把成本關注者由「間接服務」改為「直接服務」後，產生了與 Q7（共享工作階段不含 `/cost`）字面上的同型張力——**與 Q10 處理的張力形狀完全相同**（Q2 列管理者為服務對象 vs Q7 排除 `/admin/*`）。Q10 的處置是加開一題、由使用者親自選出解法（C：改列間接服務）。本輪對成本這個一模一樣形狀的張力，卻**沒有加開對應的新題**，而是由 conductor 在 artifact 內自行寫出一句解釋性文字（「服務是在入口處完成的，不以該頁加入共享範圍為前提」）去化解它，並掛上 `[Q7]` 標籤。逐字核對 Q7 的作答內容（選項 A：「只有入口頁 ＋ `/workspace` ＋ `/assessment`：實際會用到 AI 的頁面。」）——**沒有任何一個字**談到「成本問題可以在入口頁內完成、不需要涉入 `/cost` 頁」；Q12 的作答內容（選項 A：「大腦把成本類問題路由到既有 `/api/cost/v1`，使用者真的問得到成本答案；不新建成本能力。」）也**沒有**談到答案要在哪個頁面呈現、是否需要導向 `/cost`。這句「適用前提」是 conductor 在產出 artifact 當下自行合成的推論，不是任何一題的字面內容，卻用 `[Q<n>]` 標籤包裝成「已由問答確認」的樣子——這正是 `intent-capture:c11` 要防的形狀（掛標籤前須逐字核對，不得憑印象／推論引用），且與同一份文件內 Q10 已建立的處置先例不一致：同型張力，一個用追問定案、一個用單方面文字定案。下游（feasibility、scope-definition）會把這句話當成已確認的產品邊界（成本答案是否需要導向 `/cost` 頁、是否需要在入口頁內完整渲染 SSE），但它從未被使用者確認過。 | 比照 Q10 的處置方式，針對此一新張力加開一題（例如：「成本問題的答案要在入口頁內就地呈現，還是導向 `/cost` 頁？」），由使用者選定後再回填 Target Customer 表與 stakeholder-map 對應列；在取得確認前，不得以推論句搭配 `[Q<n>]` 標籤呈現為已確認事實。 |
| R-06 | Major | `intent-statement.md`（「編排能力本次**自建**，不改造既有已上線的成本能力，兩者並行。[Q13] 此決定的已知代價——系統內將並存兩份同類的執行機制——已於作答時向決策者揭露；如何鎖住兩者的一致性屬後續階段的約束項，不在本階段定案。[Q13]」） | 對照 `intent-capture-questions.md` Q13 的揭露文字：「repo 內將並存**兩份 OpenRouter 客戶端與兩套串流事件語意**。`team.md` 的 `## Code Style ## 單一真實來源` 要求……」——具體是哪兩份機制、以及這牴觸了 `team.md` 哪一條既有規則，Q13 講得很清楚。但 artifact 把它委婉化為「兩份同類的執行機制」，**沒有點名 OpenRouter 客戶端與串流語意，也沒有提到這與 `team.md` 單一真實來源規則的關係**。下游 stage（feasibility、scope-definition）多半只讀 artifact、不會逐句比對問題檔，若只看 `intent-statement.md`，會知道「有代價、使用者已知情」，但不會知道代價具體是什麼、也不會被提醒去對照既有的專案規則。這不是「假裝沒有代價」（確有寫「已知代價」），但把可執行的具體資訊留在了問題檔裡，沒有隨決策一起搬進正式產出。 | 把 Q13 揭露的具體內容（兩份 OpenRouter 客戶端、兩套串流事件語意、與 `team.md` 單一真實來源規則的關係）寫進 `intent-statement.md` 本文，而非僅以「同類的執行機制」帶過；讓 feasibility 不需要回頭讀問題檔就能承接這個約束項。 |
| R-07 | Major | `intent-capture-questions.md` 查證紀錄 V7（「`schema_rbac.sql` 有 `archive_diagram_cost`、`archive_diagram_cost_line`、`archive_cost_audit_event` 三表」） | 實地查證 `schema_rbac.sql`：這三張表的區塊標題逐字為「**C1 Cost / FinOps tables — RETIRED (U3 legacy-cost-retirement)**」，且三張表個別的 `COMMENT ON TABLE` 逐字皆為「**retired: … app must not read/write; drop after >=90d**」——這三張表是被明文禁止讀寫的**退役表**，不是成本能力的實際儲存層。真正供 `backend/cost/` 套件使用的現行表是 `estimate_sets`、`estimates`、`estimate_line_items`、`estimate_shares`、`estimate_audit_events`、`advice`（`schema_rbac.sql` 219–283 行，對應 `backend/models.py` 的 `EstimateSet`／`Estimate`／`EstimateLineItem`／`EstimateShare`／`EstimateAuditEvent`／`Advice`），V7 完全沒有提到。V7 是為了推翻「成本能力不存在」而做的查證，其核心結論（成本能力確實存在）本身正確（由 23 個檔案、10 條端點、`CostPage` 路由等其餘證據獨立支撐），但**援引的 schema 證據恰好指向相反方向**——把「明文禁止使用的退役表」誤植為「成本能力存在」的支撐證據。查證紀錄雖標註「非來源，不得引用進 artifact」，但下游 stage 仍可能讀取問題檔取得脈絡，這個錯誤若被沿用會讓 feasibility／scope-definition 誤以為 `archive_diagram_cost` 系列是可用的資料模型。 | 修正 V7，改引用現行使用中的六張表（`estimate_sets`／`estimates`／`estimate_line_items`／`estimate_shares`／`estimate_audit_events`／`advice`），並移除或改寫對 `archive_*` 三表的引用，註明其為退役表、app 不得讀寫。 |
| R-08 | Minor | `intent-statement.md`／`stakeholder-map.md`／`intent-capture-questions.md` 全文的「修訂 1」標記 | 逐一核對後，這些標記（Problem Statement 的跨雲分析修正、Initial Scope Signal 的成本段落修正、Review 區塊前言、stakeholder-map 底部的兩項變更說明、questions.md 的 Q6／Q11 取代註記與 Assumption Confirmation 修正說明）都對應到真正需要說明的實質變更或流程要求（避免被誤判為迴歸、滿足 `requirements-analysis:260822-ra-L3`／`approval-handoff:260823-rev1-c1` 的重新確認要求），未發現屬於噪音、可拿掉而不損及可讀性的標記。 | 無需處理；本項為送審前自檢的查核結果，非缺陷。 |

### Summary

修訂 1 對前次審查的三項發現（R-01、R-02、R-03）處置得當，逐字核對後皆為
真修正，非換句話說；「修訂 1」標記的使用範圍也經逐一核對，未發現噪音。

但本輪查出兩項新缺陷，皆源自修訂 1 本身：

1. **R-05（Critical，新引入）**——成本關注者由間接服務改為直接服務後，
   與 Q7 的共享範圍產生張力，這個張力的處置**沒有比照同一份文件內剛建立
   的 Q10 先例**（加開追問、由使用者定案），而是由 conductor 單方面寫出
   一句未經確認的推論句，並掛上 `[Q2][Q12][Q7]` 標籤包裝成「已確認」。
   逐字核對 Q7、Q12 的作答內容，兩者都沒有支撐這句推論。這是本輪最嚴重
   的問題：它讓一個實質上仍待決的產品邊界（成本答案是否需要導向
   `/cost` 頁）看起來像已經拍板，直接違反 grounding contract 的核心保證。
2. **R-06（Major，新引入）**——Q13 揭露的具體代價（兩份 OpenRouter 客戶端、
   兩套串流語意、牴觸 `team.md` 單一真實來源規則）在寫進 `intent-statement.md`
   時被稀釋成「兩份同類的執行機制」，遺漏了下游若只讀 artifact、不回頭讀
   問題檔就會漏接的具體資訊。

另查出一項既存但前次審查未抓到的問題：
3. **R-07（Major，既存漏審）**——查證紀錄 V7 引用的三張 `schema_rbac.sql`
   表格經核對後是明文標註「已退役、app 不得讀寫」的表，並非成本能力的
   實際儲存層；真正在用的六張表完全沒被引用。V7 的核心結論仍然正確（由
   其餘證據獨立支撐），但這個具體引用是錯的，且發生在修訂 1 才新增的
   查證段落中——嚴格說屬於本輪新增內容裡的既存性錯誤，一併計入本輪缺陷。

計數：Critical 1（R-05）、Major 2（R-06、R-07）、Minor 2（R-04、R-08）、
已解決 3（R-01、R-02、R-03）。來源分類：新引入 2 項（R-05、R-06，皆為修訂 1
新增內容造成）、既存漏審 1 項（R-07，查證內容雖是修訂 1 新增，但其失誤
性質是「查證品質不足」而非「修訂邏輯錯誤」，故獨立列出）、新設計問題 0 項。
因存在 Critical 發現，Verdict 為 NEEDS REVISION。
