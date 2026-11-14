## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

本輪為修訂後的複驗。review-01 的八項發現中，R-02（第四種列）、R-03（追認清單與 K-16 矛盾）、R-04（BR41.3 理由）、R-07（儲存後重讀）、R-08（部分覆蓋標示）在產出中確實已修，並已對照 schema_rbac.sql、DEPLOY.md、hierarchy_facade.py、membership_facade.py 與 K-15／K-16／K-17 核對；BR47.1 對 DEPLOY.md 影響面的更正也屬實（DEPLOY.md 的 system_requirement_fields 只有 593 行的「9 欄」一列，沒有外鍵總數）。R-01 與 R-05、R-06 只修了一半，修正本身引入或遺留了新問題：最重要的是 BR47.2 的「既有值一律轉 null」與「可重跑」互相矛盾，照字面實作會在第二次執行時清掉合法資料（Major）。其餘為 Minor。依判準（零 Critical、Major 不超過 2）給 READY；BR47.2 建議在 code-generation 開工前先改寫規則文字。

### Findings

| ID | Severity | Location | Finding | Status |
|---|---|---|---|---|
| R-01 | Major | rules.md BR47.2（logic 與 note）；functional-spec.md OPEN-RF20-8 | 【證據】BR47.2 同時要求兩件事：「欄位型別改為 VARCHAR(64)，既有值一律轉為 null」與「重跑兩次結果相同是硬要求」。run_meta_schema_migration.py 直接解析並重新執行整個 J) 區塊，DEPLOY.md 2.2.9 也寫明該指令可重跑（「已實測重跑為 exit 0」）。若收斂敘述實作成無條件的 ALTER COLUMN ... TYPE VARCHAR(64) USING NULL，第一次執行後 facade 寫入的 agent 組識別字（例如 cost），會在下一次重跑（例如 staging 重跑遷移腳本、或 U18 先上線後再跑一次）被全部清成 null，且不會有任何錯誤：這正是 K-17 要保護的「哪些值是大腦代寫」溯源資料，靜默遺失。規則的「轉 null」只在欄位仍為 integer 時才安全，但規則沒有寫出這個前置條件。另外無條件 ALTER TYPE 在 PostgreSQL 會取 ACCESS EXCLUSIVE 鎖並重寫表。【建議】改寫 BR47.2：收斂敘述必須以欄位目前的型別為條件（僅當 information_schema 顯示該欄為 integer 才執行轉型與清值；僅當外鍵存在才 DROP CONSTRAINT，名稱以 pg_constraint 查而非硬寫自動產生的名稱），並把「第二次執行不改變任何已存資料」寫成可驗證的硬要求。 | New |
| R-02 | Minor | rules.md BR47.3；functional-spec.md 第十一節 R-01 列 | BR47.3 的欄位級斷言放在 verify_meta_schema.sql，但該檔由 CI 的 memory-schema job 對「全新資料庫」執行，新 DDL 建出的表必然符合斷言，所以舊定義資料庫的收斂路徑在 CI 完全不被走到；規則同時把 run_meta_schema_migration.py 的後條件寫成「由 code-generation 決定」，而真正會在 staging 這類收斂目標上跑的恰恰是這支腳本的後條件。結果是 BR47.2 的「staging 可收斂」仍然沒有任何機械驗證，與 review-01 R-01(e) 要解的問題相同。【建議】把腳本後條件的欄位級檢查（型別為 character varying、該欄無外鍵）改為必做；並要求一個測試或 CI 步驟先以舊定義建表、再執行 J) 區塊兩次，斷言型別、無外鍵、以及第二次執行不動資料。 | New |
| R-03 | Minor | rules.md BR42.5 note；functional-spec.md OPEN-RF20-1、3.3 步驟 4 | BR42.5 只在呼叫端帶 on_behalf_of 時才擋空值。on_behalf_of 是自填標示（BR45.4／OPEN-RF20-1），U21 經 HTTP、U13 同進程呼叫時若省略它，空字串仍走 BR43.2 變成清空，並被記成「本人清空」，review-01 R-06 要防的靜默清值與溯源失真在這條路徑依然成立。產出沒有把「代寫路徑一律帶 on_behalf_of」寫成 U13／U21 的義務，BR42.5 的保護因此取決於呼叫端自律。【建議】在 OPEN-RF20-1 或新開放項指派 U21（工具 schema 層對空值直接拒絕或強制帶標示）與 U13 承接，並在 BR42.5 的 note 誠實寫明「此規則只保護有自報代寫身分的呼叫」。 | New |
| R-04 | Minor | rules.md BR46.4；functional-spec.md 2.2 表格、OPEN-RF20-3 | BR46.4 只處理 PUT 本體的形狀錯誤。三個路由的路徑參數（system_id 非整數）與 JSON 解析失敗仍會產生框架預設的 422，其形狀（清單式 detail）與領域例外的 422 不同；2.2 表中 GET 只宣告 403／404，DELETE 宣告了 422，兩者不一致，也使「U23 只需處理一種 422 形狀」的硬要求在 GET 與路徑參數上不成立。路徑參數回顯的是路徑片段而非欄位值，不涉機敏，所以僅是形狀一致性問題。【建議】在 BR46.4 把範圍明寫為「三個路由的全部框架 422」，或明確記載路徑參數錯誤為已知例外，並讓 2.2 表三個路由的 responses 宣告一致。 | New |
| R-05 | Minor | functional-spec.md 第九節自檢 5 | 自檢 5 仍寫「規則數 33」，同節自檢 6 與第六節表格是 37（實數：6＋5＋7＋6＋5＋4＋4＝37，與 rules.md 的 YAML 條目數一致）。這是修訂後遺留的舊數字，同一份檔內兩處互相矛盾，也是 project.md 反覆記載的「改完要重掃衍生計數」同型失誤。【建議】改為 37，或刪去該處的具體數字。 | New |
| R-06 | Minor | rules.md BR44.1；functional-spec.md 2.3；entities.md FieldView | BR44.1 把第四種列（value 與 clearedAt 皆為 null）視為 never_filled，但該列的 updated_at、updated_by 是 NOT NULL，實際有值。FieldView 的 updatedAt／updatedBy／updatedOnBehalfOf 在此情形要回列上的值還是回 null，規則沒有說。回列上的值會讓 filledState 為 never_filled 的欄位帶有「最後更新者」，與「對使用者的意義與無列相同」互相牴觸，U23 也無從判斷該不該顯示；各實作者很可能選不同答案。【建議】在 BR44.1 補一句：never_filled 的 FieldView 一律回 null 的 updatedAt／updatedBy／updatedOnBehalfOf（含第四種列），並在 TestClient 案例中直接插入第四種列驗證。 | New |
| R-07 | Minor | functional-spec.md 2.1；rules.md BR41.2 | 複驗順帶發現的小落差：K-17 的 own_responsibility 與 anti_double_check 兩處字面都把全域 K4 層歸給 router 的 require_story_action，OPEN-RF20-5 第 5 項已追認偏離，但該項只寫「全域層落在 facade」，未明列 K-17 的這兩處字面需一併改寫；另 K-17 的 returns 使用 unfilled_count（snake_case），本單元回應為 unfilledCount，未列入追認。屬契約修訂時的清單完整性。【建議】把這兩點併入 OPEN-RF20-5 的追認清單。 | New |
| R-08 | Minor | rules.md BR44.1；functional-spec.md OPEN-RF20-7 | 驗證 review-01 R-02：第四種列的推導已全函數化，3.4 步驟 2、狀態機文字、entities.md FilledState、OPEN-RF20-7 結案四處同步，U18 的 CHECK（cleared_at IS NULL OR value IS NULL）核對屬實，三個分支確實窮盡。 | Resolved |
| R-09 | Minor | rules.md BR41.3、BR41.4；functional-spec.md 3.1 | 驗證 review-01 R-04：BR41.3 已改寫為實際行為並明列 K2.view 為隱含前置，與 hierarchy_facade.py 的 get_project_of_system 先 _authorize(view) 一致；BR41.2 以 user_can 在 facade 內評估與 membership_facade.py 的 _authorize_global 同形，BR41.1 的 is_approved 與 Principal 欄位存在。 | Resolved |
| R-10 | Minor | traceability.json；functional-spec.md OPEN-RF20-3、第十一節 | 驗證 review-01 R-03、R-07、R-08：追認清單已補齊六項並點名 K-16 的矛盾；OPEN-RF20-3 已補「儲存後以重讀結果更新兩處」；AC11.2.1 與 AC11.2.3 的 note 首句已標示僅資料層部分。BR47.1 對 DEPLOY.md 的更正（只補 2.2.9 一行、欄數維持 9、刪除外鍵數 8 到 7）與 DEPLOY.md 593 行及全文 grep 結果相符；repo 內除 schema_rbac.sql 兩處外確無其他程式引用 updated_on_behalf_of。 | Resolved |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 規則數計數（rules.md YAML 條目） | 37（6＋5＋7＋6＋5＋4＋4） | 與第六節、自檢 6 一致；自檢 5 的 33 為殘留（R-05） |
| 對照 schema_rbac.sql:681-723 | 欄位仍為 INTEGER REFERENCES users；CHECK 為 cleared_at IS NULL OR value IS NULL | 確認 BR47 尚未落地屬預期；第四種列與 BR44.1 的窮盡性成立 |
| 對照 run_meta_schema_migration.py、verify_meta_schema.sql | 腳本重執行 J) 區塊；FORBIDDEN_FKS 以（表，被參照表）為鍵；verify 對全新資料庫執行 | 支撐 R-01、R-02 |
| 對照 DEPLOY.md 2.2.9 | 593 行「9 欄」一列，無外鍵總數、無 updated_on_behalf 文字 | BR47.1 的更正屬實 |
| 對照 K-15／K-16／K-17 | 追認清單涵蓋主要差異；K-17 兩處字面與 unfilled_count 命名未列 | R-07 |
| 範圍限制 | 未開啟其他單元的產出目錄 | 符合審查範圍 |

### Summary

修訂把 review-01 的兩項 Major 都實質處理了：影響面識別更正、第四種列結案，使用者也在完整代價下重新裁決。新材料中最需要在 code-generation 前處理的是 BR47.2：「既有值轉 null」缺少「僅當欄位仍為 integer」的前置條件，與可重跑的硬要求互相矛盾，照字面實作會在重跑時靜默清掉代寫溯源資料。其餘為可併入 code-generation 的 Minor；本輪未發現 Critical，Major 僅一項，故為 READY。
