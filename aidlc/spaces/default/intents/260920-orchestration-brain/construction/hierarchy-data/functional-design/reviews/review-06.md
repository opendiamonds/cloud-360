## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary
設計本身自洽，四條 AC9.1.1 至 AC9.1.4 都有落點，ADR-0006 四面向也有逐項判定。但設計與已落地程式有四處矛盾，且每一處都是程式比設計正確。這四處是：既有圖表的擁有者欄位名稱寫錯、`DiagramChangeRecord.diagram_id` 的刪除語意完全沒寫、遷移執行位置仍寫「未定」、`OQ-H1` 沒有反映已上線的刪除使用者行為。舊審查（`reviews/review-04.md` 與 `review-05.md`）指出的這些問題，在目前凍結的產出裡仍然存在，所以在此重新列出，不視為已處置。Major 共 4 項，超過 2 項，判 NOT-READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | `construction/hierarchy-data/functional-design/entities.md`（`ArchitectureDiagram.owner_user_id`，約 `:133`；`:239`）、`rules.md:129`／`:132`／`:226`／`:232`／`:235`（`BR2.3`、`BR3.3`）、`functional-spec.md:157`／`:163`、`traceability.json`（`AC9.1.3`、`BR3.3`） | 四份產出把既有架構圖表的擁有者欄位稱為 `owner_user_id`，實際欄位是 `user_id`。`backend/models.py:99` 是 `user_id = Column(Integer, ForeignKey("users.id"), nullable=False)`；`backend/services/hierarchy_migration.py` 的遷移 SQL 用 `d.user_id`、`WHERE user_id = :owner`；`schema_rbac.sql` 的 `user_diagrams.system_id` COMMENT 也寫 `user_id answers "who created it"`。`owner_user_id` 這個名字只存在於本單元新建的 `Project`（與 `DiagramChangeRecord.actor_user_id` 的相鄰概念）。`BR2.3` 的「遷移不得修改的既有欄位清單」與 `BR3.3` 的「權威來源是 system_id，不是 owner_user_id」都拿一個不存在的欄位名當對照。依設計寫 `UPDATE`、測試或 `U7`／`U10`／`U14` 的歸屬判斷時，欄位名會對不上。**程式是對的，設計錯。** | 把所有指既有圖表擁有者的 `owner_user_id` 改為 `user_id`，並在 `entities.md` 的 `ArchitectureDiagram` 欄位註明「既有欄位名為 `user_id`」。`Project.owner_user_id` 不動。 | New |
| R-02 | Major | `entities.md`（`DiagramChangeRecord.diagram_id` 與 relationships，約 `:176–179`、`:231–234`）、`rules.md`（`BR1.*` 全組）、`functional-spec.md`（`SM-1` 的「圖被刪除」邊、`§五`、`§六` Audit logging 列） | 設計對 `DiagramChangeRecord.diagram_id` 被參照的圖刪除時要怎麼辦，一個字都沒寫。已落地的 DDL 已經決定了：`schema_rbac.sql` 的 `diagram_change_records` 區塊與 `hierarchy_migration.py` 都是 `ON DELETE CASCADE`，也就是刪圖會帶走該圖所有變更紀錄。`functional-spec.md §六` 把這張表定位為稽核資料，並說 `actor_user_id` 的存在理由是回答「是誰讓這張圖變成這樣」；CASCADE 使這個答案在圖被刪除時一併消失。本單元對另外兩個外鍵（System→Project、圖→System）各寫了規則，並在 `BR1.2.source` 論證「為何不選 CASCADE」，第三個外鍵卻沒有對應規則，也沒有說明為何此處相反。契約端點三問中，新建實體的「誰清」缺口就出在這裡。 | 在 `entities.md` 的 `diagram_id.constraints` 或新增一條 `BR1.*` 寫明圖被刪除時變更紀錄的處置與理由；`§五` 的誠實狀態與 `§六` Audit logging 列要寫明稽核列會隨圖消失；若採 CASCADE，須與 `BR1.2` 拒絕 CASCADE 的理由並列，說明兩者為何相反。 | New |
| R-03 | Major | `functional-spec.md §八`「遷移的執行位置未定」（約 `:314–316`）、`rules.md`（`BR2.4.logic`） | `§八` 逐字寫「啟動路徑、獨立指令、或兩者皆可」，`BR2.4` 只禁止遷移「只」存在於啟動路徑的副作用。這個被留下的選項會直接破壞本單元最強調的不變量：`init_db()` 由 `main.py` 的 startup 事件呼叫，而它整段包在 `except Exception` 加 log 的形狀裡，遷移掛在那裡，失敗就變成一行日誌加一個看起來正常啟動的服務，等於 `AC9.1.4` 明文要否掉的 `logger.warning` 形狀。已落地的程式明確否決它：`hierarchy_migration.py` 模組 docstring 寫「不掛在啟動路徑上，`main.py` 不匯入本模組」，並由 `backend/scripts/run_hierarchy_migration.py` 以非零結束碼收場。設計握有這項證據（`rules.md` 的 `BR2.3.source` 引用 ADR-002「靜默吞掉失敗」），卻留下「同時掛啟動路徑」的字面可遵守繞法。 | 在 `BR2.4` 或 `§八` 明寫「不得掛在啟動路徑上（含同時掛）」，理由是 `init_db()` 的既有形狀會吞例外使 `BR2.1` 失效；並把「執行位置未定」收窄為「落點為部署期獨立指令」。 | New |
| R-04 | Major | `functional-spec.md §八` `OQ-H1`（約 `:263–270`）、`traceability.json` reverse `OQ-H1`、`rules.md`（`BR3.2` 的適用範圍）、`entities.md`（`DiagramChangeRecord.actor_user_id`） | `OQ-H1` 把「刪除使用者時其 `Project` 怎麼辦」記為尚未發生的開放問題，但已落地的預設已經在生效：`projects.owner_user_id` 與 `diagram_change_records.actor_user_id` 的外鍵都沒有 `ondelete`（`schema_rbac.sql`、`hierarchy_migration.py`），行為上是拒絕。而 `backend/services/user_router.py:308–323` 的 `_hard_delete_user` 只檢查使用者是否還擁有圖（`owned > 0` 時回 403 並附可理解訊息），之後直接 `db.delete(user)`。遷移只為持有圖的使用者建預設專案（`BR2.5`），本輪沒有刪除專案的路徑；因此「曾持有圖、現已刪光圖」的使用者仍有預設專案，管理員硬刪除他會撞上外鍵並以未處理的 `IntegrityError`（500）收場。這正是 `BR3.2` 要消除的「不明所以的伺服器錯誤」，而 `BR3.2` 的適用範圍逐字只含 `BR1.1`／`BR1.2` 的拒絕。`actor_user_id` 的外鍵有同樣的後果，但 `OQ-H1` 只提 `Project.owner_user_id`。 | 在 `OQ-H1` 補記已落地的實際預設與它同 `_hard_delete_user` 的交互，把 `actor_user_id` 一併納入；並把「刪除使用者被專案或變更紀錄擋下時的錯誤訊息」納入 `BR3.2` 的適用範圍，或另立一項指給 `U7`。 | New |
| R-05 | Minor | `functional-spec.md:34–49`（`WF-1` 前言「順序不可調換」與步 5「必須在步 4 之後」） | `WF-1` 把刪除約束列為獨立的步 5，並以粗體寫「必須在步 4 之後」，而已落地的實作把 FK 的 `ON DELETE RESTRICT` 與加欄放在同一條 `ALTER TABLE ... ADD COLUMN ... REFERENCES ... ON DELETE RESTRICT` 敘述內，與步 1／2 同時建立（SQLite 無法對既有表追加 FK）。同一節的 `:48` 已自己寫「嚴格說順序可換」，所以真相在原地，但本檔宣稱是有序行為的真實來源，前言與粗體仍與程式相反。 | 把步 5 改記為「與步 1／2 同時建立」，或把前言的「順序不可調換」收窄為「步 3 必須先於步 4」。 | New |
| R-06 | Minor | `functional-spec.md §五`（誠實狀態清單）、`entities.md`（`DiagramChangeRecord`） | 對新建實體 `DiagramChangeRecord`，契約端點三問只答了兩腿：誰寫（`U12`）、誰讀（無）。「誰清」沒有任何交代，全產出對保存期、清除、retention 零命中。下游已需要它：同單元 `nfr-requirements` 另立 `U4-R1`（90 天保存期），且該單元自己承認本 intent 結束時這張表實際上不會被清除。本站先於該站執行，無法引用 `U4-R1`，但可以要求把缺口列為具名開放項。 | 在 `§五` 的誠實狀態清單補「清除端：無，本站不定案」並升為具名開放項，落點對齊 `U4-R1` 的承接站。 | New |
| R-07 | Minor | `traceability.json` reverse 的 `BR1.3`（`target` 欄） | 該列寫「每位使用者至多一組預設專案／系統的唯一性約束……是 `BR2.2` 的資料庫層承載」。「一組」是複合性質，`rules.md §三` 已明寫它不能單靠約束，另需 `BR2.5` 的獨佔寫入紀律。其餘產出已修正，這一處仍保留過度宣稱。已落地程式的註解反而是對的。 | 把該 `target` 的「每位使用者至多一組」改為兩層原子約束的表述，並指向 `rules.md §三`。 | New |
| R-08 | Minor | `rules.md:150`、`traceability.json`（`AC9.1.2` 與 `BR2.4` 兩列，約 `:20`、`:67`） | 三處引用 `stories.md:432-419`，範圍是倒的（起點大於終點）。實際記載該失敗模式的是 `stories.md` 約 `:432–445` 的註記段落（`AC9.1.4` 在 `:428`，`logger.warning` 一句在 `:445`）。`functional-spec.md:52` 與 `rules.md:100` 的 `:445` 引用是對的。依範圍讀的人會找不到。 | 改為 `stories.md:432–445`，並逐處用開檔核對定位。 | New |
| R-09 | Minor | `functional-spec.md:292` | 錯字「取消歸屮操作」，應為「取消歸屬」。同段其餘寫法皆正確。 | 改為「取消歸屬」。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 手動核對 AC 覆蓋（`traceability.json` 對 story map） | AC9.1.1 至 AC9.1.4 皆有 `BR*` 落點 | 覆蓋完整，無孤兒 AC |
| 設計對已落地程式抽查（`models.py`、`schema_rbac.sql`、`hierarchy_migration.py`、`user_router.py`） | 四處矛盾：欄位名、`diagram_id` 刪除語意、執行位置、刪除使用者交互 | 對應 R-01 至 R-04，皆為程式正確、設計需修 |
| ADR-0006 四面向逐項判定（`functional-spec.md §六`） | IAM、Encryption、Network exposure、Audit logging 皆有判定與理由 | 有落點；Audit logging 的缺口見 R-02、R-06 |
| 專用驗證工具 | 本輪未執行 | 審查範圍限於本單元，未跑會寫檔的指令 |
