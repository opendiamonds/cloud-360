## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

整體設計紮實：授權順序、三態推導、單一查詢推導計數與明細（BR44.4）、四題答案的落實都核對無誤；BR41.2 把全域 K4 檢查放進 facade 的偏離，對 U23（HTTP）、U13（同進程）、U21（HTTP）三個消費者都成立，且與已交付的 U19 membership_facade.py:93-111 同形。阻擋點有兩項 Major：其一，BR47 對 U18 已交付資料表改動的影響面識別有誤，且與使用者在 FD1 看到的選項文字（「不需要 ALTER」）不一致；其二，U18 明確指派給本單元的 OPEN-CG18-7（第四種未命名狀態）在四份產出中零提及，使 BR44.1 的推導與 3.4 清空流程對該列沒有定義。其餘為 Minor。

### Findings

| ID | Severity | Location | Finding | Status |
|---|---|---|---|---|
| R-01 | Major | functional-spec.md 第八節 OPEN-RF20-6；rules.md BR47.1／BR47.2；functional-design-questions.md FD1 選項 A 文字 | 【證據】(a) FD1 選項 A 的文字逐字寫「因為尚未部署，不需要 ALTER」，並列出需同步 run_meta_schema_migration.py 的後條件清單；但 BR47.2 新增「讓已用舊定義建表的資料庫收斂、可重跑」的硬要求（等於要寫 ALTER 或移除外鍵），BR47.1 卻完全沒提 migration 腳本。使用者核可的是「不需 ALTER」，artifact 實作的是另一件事，影響面比他看到的大。(b) BR47.1 說 DEPLOY.md 2.2.9 節要把「外鍵數 8 → 7」同步，但實查 DEPLOY.md 沒有任何「總共 8 條外鍵」的文字（只有 :674 的「3 條外鍵刪除行為」，不含 updated_on_behalf_of，不受影響）；「8」只存在於 U18 的 code-summary.md 與 traceability.json 的 CG-SCHEMA-J，那不是部署資產。真正要改的是 schema_rbac.sql:690（DDL）與 :723（COMMENT）；DEPLOY.md 完全沒有 updated_on_behalf 的文字，blocking 同步義務的實際內容（要在 2.2.9 補什麼）未被正確識別。(c)「U18 尚未部署」目前成立（origin/ut 不含 J 區塊，已實查），但 U18 與 U20 屬不同 Bolt，U18 先合併並在 192.168.10.10 跑 run_meta_schema_migration.py 是可能的順序；BR47.2 把收斂範圍寫成「本機 dev 資料庫」，漏了 staging。(d) 整數欄位改為 VARCHAR(64) 時，既有非空值（若有）會變成「123」這類不屬於任何 groupKey 的字串，直接違反 BR42.3；規則未規定如何處置既有值。(e) verify_meta_schema.sql 與 run_meta_schema_migration.py 的後條件都沒有對 updated_on_behalf_of 的型別或「無外鍵」做斷言，BR47.2 的「重跑收斂」沒有任何機械驗證。(f) backend/models.py 沒有 system_requirement_fields 的 ORM 模型（只有 ProjectMember、ReselectionEvent），U20 要讀寫此表就得新增模型或走原生 SQL；U19 為前兩者建立了 test_membership_data.py 的 ORM／DDL 一致性測試，BR47 沒有對應要求；BR43.5 的單一 upsert 在測試用的 SQLite 與正式 PostgreSQL 的方言差異也未交代。【建議】改寫 BR47.1／BR47.2：明列真正受影響的資產（schema_rbac.sql DDL＋COMMENT、DEPLOY.md 2.2.9 需補的內容、是否動 verify_meta_schema.sql 與腳本後條件）；刪除或更正「外鍵數 8→7」；明確寫出既有非空值的處理；把收斂範圍擴到 staging；向使用者揭露 FD1 的實際代價比選項文字大，必要時請其再確認；補上 ORM 模型、一致性測試與 upsert 方言策略的歸屬。 | New |
| R-02 | Major | functional-spec.md 3.4 步驟 2、第九節自檢 1；rules.md BR44.1；entities.md FilledState.derivation | U18 code-summary.md:116 的 OPEN-CG18-7 明文指派給 U20：CHECK 允許第四種狀態 value IS NULL AND cleared_at IS NULL（列存在、從未填也沒清空），「揭露供 U20 在 facade 層判定是否需要額外守門」。我對本單元四份產出 grep OPEN-CG18-7 與「第四」均為 0 命中，指派落空。後果可具體指出：BR44.1 的三條推導（無列／value 非 null／value 為 null 且 clearedAt 非 null）對該列沒有輸出；3.4 的清空流程三個分支也都不涵蓋它；FilledState 的 allowed_values 無法表達它。經 facade 的寫入確實到不了（寫入必設 value、清空必設 clearedAt），但直接 SQL、手動修資料或日後別的寫入路徑都能造出，而 BR44.5「回應欄位集合恆等於宣告集合」會在此列處因推導無值而崩或回傳未定義的 filledState。自檢 1「可達性」只檢查了三個條件，沒有針對這一格。【建議】在 BR44.1 補一條全函數的推導（建議：value 與 clearedAt 皆為 null 一律視為 never_filled 並計入 unfilled），讓 3.4 把該列當成「無列」處理（寫入走 upsert 自然覆蓋，清空為 no-op）；並在開放項明記 OPEN-CG18-7 由本站結案及其判定。 | New |
| R-03 | Minor | functional-spec.md 2.1、2.3、OPEN-RF20-5；contract-summary.md K-17 與 K-16 | OPEN-RF20-5 的追認清單不完整，與 K-17 字面的差異至少還有四處：(1) K-17 的 system_id 是 str，本單元與 HierarchyFacade.get_project_of_system(system_id: int) 一致用整數，是型別偏離；(2) K-17 clear_field 的 returns 逐字寫「FieldView（value 為 null、clearedAt 有值）」，本單元的 FieldView 沒有 clearedAt 欄位（entities.md 與 2.3 皆無），這是移除而非新增，且 U13／U21 無法在回應中核對 clearedAt，只能靠 filledState；(3) write_field 多拋 RequirementFieldValidationError，K-17 的 raises 清單沒有；(4) on_behalf_of 由自由 str 或 None 收窄為已宣告的 groupKey。另有一條相關矛盾：contract-summary.md 的 K-16 two_facade_layers 寫「U20 不得重複呼叫 require_story_action（它的 router 已經做了）」，與 BR41.2 的「router 不掛 dependency、facade 自己評估」互相矛盾，需在契約修訂中一併改掉，否則 U21／U13 的實作者會依 K-16 字面假設 router 已檢查。【建議】併入 OPEN-RF20-5。 | New |
| R-04 | Minor | rules.md BR41.3、BR41.4 | BR41.3 的理由寫「不以錯誤碼洩漏系統是否存在」，但 HierarchyForbidden 轉 NotFound 只涵蓋缺 K2.view 這個罕見分支（11 個 canonical role 都有 K2.view）。實際路徑是：持有 K4.view 的非成員對「存在的系統」得到 403（BR41.4），對「不存在的系統」得到 404；system id 是整數、可枚舉，存在性仍可被探測。BR41.3 還說這是「沿用 U7 與 U19 的同一慣例」，但 U7 的 BR6.1 是對非擁有者回 NotFound，並非同形。K-17 的 on_denied 要求 Forbidden，所以未必是缺陷，但理由欄與實際行為不符，ADR-0006 IAM 面的判定不該靠一句不成立的理由。另外 get_project_of_system 內部隱含要求 K2.view，這是 BR41 未寫出的第三個全域權限。【建議】改寫 BR41.3 的理由為實際行為，或讓非成員也回 404，並明列 K2.view 為隱含前置。 | New |
| R-05 | Minor | rules.md BR46.1、BR46.3；functional-spec.md 2.2 | BR46.3 要求錯誤回應不含欄位值，但 PUT 的請求本體由 FastAPI／Pydantic 驗證（例如 value 缺漏或型別錯誤），框架預設的 422 會在 detail 的 input 回顯原始輸入；同一個狀態碼 422 因此有兩種來源與兩種本體形狀（框架的清單式 detail 與領域例外的固定文字）。BR46.1 只談領域例外的對映，沒有處理框架產生的那一種。【建議】規定框架 422 的處置（自訂 handler 或在 BR46.3 註明例外），讓兩者形狀一致，使 U23 只需處理一種。 | New |
| R-06 | Minor | rules.md BR43.2、BR45.3；functional-spec.md 3.3 步驟 4 | FD3=A 針對的是人類在畫面刪空輸入框；但 BR43.2 對所有呼叫端一視同仁，包括 U13／U21 的 agent 路徑。LLM 產生空字串或只有空白的參數並不罕見，結果是使用者先前填的值被靜默清空，而且 on_behalf_of 即使帶入也被 BR45.3 丟棄，清空事件記成「本人清空、無代寫標示」，使 BR45.2 要保護的「分辨哪些是自己填的」在這條路徑失效。K-17 另有表達明確意圖的 clear_field，兩者並存使「空值寫入」對 agent 而言是最危險的入口。這不推翻 FD3，但屬於設計風險。【建議】對 on_behalf_of 非 null 的空值寫入回 RequirementFieldValidationError（要清空請用 clear_field），或至少在開放項記錄此風險與承接單元（U21）。 | New |
| R-07 | Minor | functional-spec.md 2.2、OPEN-RF20-3；rules.md BR44.4 | BR44.4 在伺服器端確實滿足 I-4（單一查詢、同一回應）。但寫入與清空只回單一 FieldView，不帶 unfilledCount，所以 AC11.3.2（儲存後總覽籤計數 N−1）必須由 U23 在每次儲存後再發一次 GET；OPEN-RF20-3 只要求「兩個籤讀同一次 GET」，沒說明儲存後的重讀，也沒禁止本地推算計數。若 U23 改用本地加減推算，I-4 的保證就在前端這一半悄悄失效。【建議】在 OPEN-RF20-3 補上「儲存後以重讀結果更新兩處，不得本地推算」，或讓寫入回應直接帶新的 unfilledCount。 | New |
| R-08 | Minor | traceability.json AC11.2.1、AC11.2.3 | 兩條的 status 皆為 OK，但 AC11.2.1 的 Then（文字標示「未填」且不依賴顏色）與 AC11.2.3 的 Then（畫面告知失敗且輸入值不消失）主體都在 U23 的畫面，本單元只貢獻資料與錯誤契約；note 欄有如實揭露，但 status 沒有部分覆蓋的表達，下游只讀 status 會以為整條 AC 已由本單元關閉。AC11.2.3 的 target 是 BR46.2、BR46.1，兩者都不驗「輸入值不消失」。【建議】若 sensor 允許，改標部分覆蓋；否則在 note 首句明寫「僅資料層部分，畫面層由 U23 承擔」。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 手動交叉核對（schema_rbac.sql:681-723、DEPLOY.md 2.2.9、run_meta_schema_migration.py、verify_meta_schema.sql、backend/models.py） | 發現 BR47 影響面誤識 | 見 R-01；DEPLOY.md 無「外鍵總數 8」、無 updated_on_behalf 文字；models.py 無對應 ORM |
| 引用核對（user_router.py:422、App.tsx:25、rbac_seed_data.py:349-358、membership_facade.py:93-111、hierarchy_facade.py:374） | 皆吻合 | 自檢 3 所列引用可信；BR41.2 對 U19 先例的描述屬實 |
| git branch -r --contains（J 區塊首次引入的 commit） | 僅 origin/danniel/docs/orchestration-brain-ideation | 「U18 未部署」目前為真，但為時間脆弱的前提，見 R-01(c) |
| grep OPEN-CG18-7（本單元四份產出） | 0 命中 | 證實 R-02 |
| 範圍限制 | 未開啟其他單元的產出目錄；僅開啟 U18 的 code-summary.md | 符合審查範圍 |

### Summary

四題決定（FD1–FD4）大致被忠實落實，BR41.2 的偏離與 BR44.4 對 I-4 的滿足都站得住腳；阻擋點是 R-01（BR47 對 U18 已交付資料表的改動影響面有誤，且超出使用者在 FD1 看到的成本描述）與 R-02（U18 指派的第四種狀態未結案）。兩者補齊後，其餘 Minor 可併入下一輪契約修訂。
