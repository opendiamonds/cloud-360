## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本單元的功能設計整體自洽，且對上游落差（U4 的 source 欄位、isDefault 只能由遷移寫、K-07 擴充消費端、UPDATE 路徑上外鍵無效）查得相當紮實。US9.2 的三條 AC 都有指名規則。審查發現兩項 Major，都落在授權面：(1) 變更紀錄寫入路徑（W4）沒有擁有者檢查，且 BR5.6 與 W4 的方法簽名互相矛盾；(2) 全檔從未說明哪個操作要求 K2 的哪個 action（view 或 edit），開發者必須自行猜測。這兩項已被落地的程式在實作時補上（hierarchy_facade.py:344-375、:201-209），設計本身沒有，所以凍結的設計與程式不一致。其餘為 Minor。依規則（Critical 為 0、Major 為 2）判 READY，但這兩項 Major 建議在關卡上交人裁決，並以程式為準回補或記為 corrections。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/hierarchy-service/functional-design/rules.md > BR5.2、BR5.6、BR6.5 `applies_to`；functional-spec.md > W4 | W4 與 BR5.2 把 `record_diagram_change` 的簽名寫成 `(principal, diagram_id, requirement_summary, requirement_label)`，沒有行為者參數；但 BR5.6 要求 `actorUserId` 必須是實際造成異動的人、不得預設為 session 擁有者。依簽名，facade 只能從 principal 取值，正是 BR5.6 禁止的預設，兩條規則自相矛盾。另 BR6.5 的 `applies_to` 只列 create_system、delete_project、delete_system、改名，**不含 record_diagram_change**，W4 也沒有擁有者檢查：任何具 K2 的角色都能對他人的架構圖寫入變更紀錄，且行為者可任填，會污染 ADR-0006 audit logging 面。程式已兩者都補上：`actor_user_id` 為必填具名參數、並呼叫 `assert_diagram_owned_by`（hierarchy_facade.py:344-375），**程式這一邊是對的**，設計是缺口。W4 步驟 4 說「來源值必須在允許值集合內」，但簽名沒有 source 參數，來源由誰填也沒寫（應由 facade 固定為 brain_orchestration）。 | 在 W4、BR5.2 補上 `actor_user_id` 必填參數及其與 principal 的關係；把 `record_diagram_change` 納入 BR6.5 的 `applies_to` 並寫明圖的擁有者檢查與「查不到」回應形狀；寫明 source 由 facade 固定而非呼叫端傳入。以 corrections 檔承載，不改凍結產出。 | New |
| R-02 | Major | construction/hierarchy-service/functional-design/rules.md > BR1.1；functional-spec.md > W1–W7 | 全檔只寫「經 K2 判定」，BR1.1 的例外帶 `action=<action>`，但從未定義各操作對應 K2 的 view 還是 edit（列舉讀取、resolve_work_target、查詢變更紀錄、建立、刪除、record_diagram_change、BR6.4 的存在驗證各為何）。allow/deny 雙向測試（team.md 的 A、B 規則）需要明確的角色×action 預期，開發者必須自行猜。程式實作為讀取用 view、寫入與刪除用 edit（hierarchy_facade.py:201-209 及各方法首行），**這個選擇合理，但設計沒有寫**，唯讀角色能否呼叫 resolve_work_target 之類的行為因此不可由設計驗證。 | 補一張操作到 K2 action 的對照表（含 BR6.4 各方法），並將期望的 allow/deny 矩陣寫入規則，作為 TestClient 測試的依據。 | New |
| R-03 | Minor | rules.md > BR1.4；functional-spec.md > §八 第 2 點 | BR1.4 宣稱 principal「只能由授權入口鑄造」使繞過成為「型別層事實」，並稱關閉 K-07 `residual_gap` 的一半。實作（hierarchy_facade.py:141-190）是 Python 的 `_MINT` 哨兵加 `mint_principal(user)`：哨兵是模組私有名稱而非不可取得，`mint_principal` 又接受任何帶 id 與 role 的物件（該檔自己的註解承認輕量物件可用）。這是強約定，不是型別層保證。設計沒有指定機制，也沒有說明 `mint_principal` 的呼叫者必須是誰。 | 把「型別層事實」改寫為「強約定」，並規定哪些模組可呼叫 `mint_principal`（例如僅認證 dependency），納入 BR1.5 的 import 掃查。 | New |
| R-04 | Minor | rules.md > BR6.3 `logic` | 第一句「IF 該紀錄所屬的架構圖上溯到的專案不屬請求者 THEN 不出現」是 iteration 2 之前的舊判定，下一行 AND 卻規定「不上溯 system→project、以 `user_diagrams.user_id` 判定」。同一條規則內兩種判定並存，W5、W8 與程式（list_diagram_changes 以 owner_user_id 過濾）採後者，但開發者只讀 `logic` 欄會照第一句實作，而該實作對新圖會整個斷掉（W8 已實測）。 | 刪除舊判定那一句，只留擁有者判定與 fail-closed。 | New |
| R-05 | Minor | rules.md > BR6.1、functional-spec.md > W7、W2、W6；inception/decisions/0022-work-target-names-and-brain-read-visibility.md | 設計的讀取與寫入範圍皆為「僅擁有者」，且 facade 方法沒有可見性參數。落地程式已依 ADR-0022 與 U23 讓 `list_projects`、`list_systems`、`create_system`、`delete_*` 加上必填的 `project_visible` 守門（hierarchy_facade.py:267-343），並新增 `list_projects_by_ids`、`list_systems_unscoped`、`describe_work_target` 等方法。這是核可的後續修訂，**程式與 ADR-0022 是對的**，但凍結設計沒有 corrections 檔，照設計重做會倒退。同類新增的 `Principal.is_approved` 目前 HierarchyFacade 自己未讀取（程式註解已承認），待核准帳號能否建立專案設計也沒說。 | 以 corrections 檔指向 ADR-0022，標明 BR6.1、BR6.2 的射程已被取代；另決定待核准帳號是否受 K2 之外的限制。 | New |
| R-06 | Minor | rules.md > BR4.4、BR4.3；functional-spec.md > §七之二 DG-2 列 | DG-2 被宣告為「兩種懸空都不可能發生」，但範圍只算架構圖與系統。落地程式的註解顯示刪專案會連帶 CASCADE 刪除成員列，刪系統會連帶刪除需求欄位值（hierarchy_facade.py:287-312）；設計把 U19、U20 列為消費端，卻沒有規則說明這些連帶刪除是否可接受、是否需先警告。擁有者刪自己的專案，影響限於自己範圍，故不嚴重，但關閉宣稱過寬。 | 在 BR4.4 補寫連帶刪除的後果與是否需要確認，並收窄 DG-2 的關閉宣稱。 | New |
| R-07 | Minor | traceability.json > coverage > AC9.2.1 | AC9.2.1 的 Then 是「新專案出現在我可選的作業對象中」，這取決於列舉路徑（W7、BR6.1），但目標只指到 BR2.1，沒有指名 BR6.1。若列舉的過濾寫錯，追溯表仍顯示 OK。 | 把 AC9.2.1 的目標補上 BR6.1，並說明驗證需有「建立後立即列出可見」的斷言。 | New |
| R-08 | Minor | functional-spec.md > §四之二之一 | `/api/hierarchy/diagram-changes` 的 `label` 條件僅寫「字串比對」，未定義精確相等、前綴還是子字串，也沒有大小寫與長度（上限 255）的規則；回應也沒有上限或分頁。大量紀錄累積時（清除機制不存在，BR5.5）是無界回應。 | 明定比對語意與回應筆數上限。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀檔核對上游（unit-of-work.md、story-map）與本單元 4 份產出 | U7 指派的 US9.2（AC9.2.1–AC9.2.3）均有規則落點；US11.1 三條 AC 正確標為 Deferred 至 U23 | 追溯完整，僅 R-07 的目標指名偏弱 |
| 抽查程式 hierarchy_facade.py、hierarchy_router.py | 409 顯式宣告、HierarchyForbidden 不是 HTTPException、BR6.5 的擁有者檢查皆已落地 | 與設計一致；R-01、R-02、R-05 為設計與程式的落差，程式一側較完整 |
| 驗證指令（測試、lint） | 未執行 | 依 brief 禁止產生快取或寫檔 |

