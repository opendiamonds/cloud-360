## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本單元採精簡方式，以引用 K-15 與 ADR-015 代替重寫。問題不在精簡本身，而在引用過程中把契約欄位集合縮小：`entities.md` 只抄了 K-15 的五個語意欄位，沒有抄下游（`FR12.4b`、`AC12.2.2`、`K-17`）所需的其餘欄位。照這份設計實作的人建不出 `AC12.2.2` 要顯示的變更紀錄，也無法回答「誰清了需求欄位」。`traceability.json` 把全部 AC 記為 N/A，而且其中數條 AC 的文字與 `stories.md` 不符，所以 story map 指派給本單元的 `US11.2`、`US12.1` 實際上沒有可驗證的承載。已落地的 `schema_rbac.sql` 在多處已修正這些缺口（程式端較對），但設計檔本身仍凍結在錯的版本。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Critical | construction/project-meta-data/functional-design/entities.md > ReselectionEvent attributes；functional-spec.md §六 ER 圖 | `ReselectionEvent` 只有 `projectId` 與 `acknowledgedAt` 兩個欄位。`requirements.md` 的 FR12.4b 要求稽核含「誰、何時、對誰、舊角色、新角色」，`AC12.2.2` 的 Then 要顯示「誰在何時把角色由什麼改為什麼」。設計沒有 promoted_user、previous_owner、previous_role、new_role、occurred_at，這些事實無處存放，AC 不可能滿足。落地的 `schema_rbac.sql:636-690` 已補上 `promoted_user_id`、`previous_owner_user_id`、`previous_role`、`new_role`、`occurred_at`、`cause`，並在 `:588-592` 自述「本單元的 entities.md 比它少九個欄位」。**程式端是對的，設計檔是錯的。** | 在更正檔或回補紀錄中，把 `ReselectionEvent` 的完整欄位集合（含 `cause` 及兩個欄位依 cause 改變語意的規則）寫成本單元的權威實體定義，並指向 `OPEN-ND18-1`。 | New |
| R-02 | Major | entities.md > SystemRequirementField；BR1.4 | 實體缺少 `agent_group`、`field_key`、`updated_by`、`updated_at`。(a) 唯一約束寫成「同一系統內同一欄位名至多一列」，與落地的三欄鍵 `uq_system_requirement_fields_group_key (system_id, agent_group, field_key)`（`schema_rbac.sql:710`）不符，兩欄鍵會讓不同 agent 組的同名欄位互相排擠。(b) BR1.4 與 K-15 宣稱「清空可稽核（誰清、何時清）」，但設計只有 `cleared_at`，沒有「誰」的欄位；`contract-summary.md` 的 K-17 清空時另需留 `updatedBy`。ADR-0006 audit logging 的處置因此落空。 | 補上四個欄位與三欄唯一鍵，並明寫「誰清」由 `updated_by` 承載、「寫入時誰、何時」的讀寫者。 | New |
| R-03 | Major | construction/project-meta-data/functional-design/traceability.json > coverage（AC12.1.2、AC12.1.3、AC11.2.1、AC11.2.2、AC11.2.3）；unit-of-work-story-map.md 的 `US11.2`／`US12.1` 列 | 追溯的 AC 描述與 `stories.md` 不符。實際文字：`AC12.1.2`＝「邀請動作可用，不需額外授權」（`stories.md:761`），traceability 寫成「邀請成功後果」；`AC12.1.3`＝「未被邀請者看不到專案」（`:762`），traceability 寫成「邀請者溯源 invited_by」並對應 BR1.5（那是 `updated_on_behalf_of`）；`AC11.2.1`＝「未填以文字標示」（`:699`）、`AC11.2.2`＝「分組標題與欄位集合一致」（`:700`）、`AC11.2.3`＝「儲存失敗不丟失輸入」（`:701`），traceability 分別寫成無列／有值／清空的資料層描述。另 14 項中 13 項狀態為 N/A，僅 NFR8 為 OK。結果是 story map 指派給 U18 的 `US11.2`、`US12.1`（理由是「資料層就可能壞掉的斷言」）沒有任何一項可核對的承載。AC12.1.3 的非成員可見性斷言尤其無人認領（本單元沒有任何索引或約束支持它，也未指給 U19 / U23）。 | 依 `stories.md` 的逐字文字重寫追溯表；對每條 AC 寫明資料層前提（例如 `AC12.1.1` 需要 `project_members` 有建立者那一列）與實際承擔斷言的單元，N/A 必須指向具名單元。 | New |
| R-04 | Major | entities.md > ProjectMember.role、invitedBy；functional-spec.md §四；rules.md BR1.1 | `role` 沒有值集合；落地為 `CHECK (role IN ('project_admin','member'))`（`schema_rbac.sql:604`）。更大的缺口是 `AC12.1.1` 的前提：建立專案者必須有一列（角色為專案管理者）。`components.md:886` 寫為「建立專案時的自動寫入」，但本單元沒有說這一列由誰寫、用什麼角色、`invited_by` 為何空。`ProjectMember` 的寫入端因此只有 K-16 的邀請，三問「誰寫」缺一腿。`invitedBy` 的 constraints 說「遷移或系統建立」，但沒有任何遷移存在（K-15 明說無資料寫入）。 | 寫明 role 的封閉值集合，以及建立者列的寫入者（指名單元與呼叫點）；刪除「遷移」的措辭或指出遷移來源。 | New |
| R-05 | Major | entities.md「三種狀態」表；rules.md BR1.3、BR1.4 | 三態模型只有說明表，沒有不變量。設計沒有規定「已填」狀態 `cleared_at` 必為 NULL，也沒有規定清空後重新填值時誰把 `cleared_at` 重設為 NULL。缺少時，一列可同時有值且 `cleared_at` 有值，而兩種讀法都說得通，三態退化為「看寫入端當時想的是哪一種」。`schema_rbac.sql:715` 已加 `ck_system_requirement_fields_cleared_has_null_value` 修補，但設計沒有承諾，也沒有指派 U20 寫入端的重設責任。BR1.4 只約束清空動作，不約束清空後的重新填寫。 | 新增規則：`cleared_at IS NOT NULL ⇒ value IS NULL`（DB 層 CHECK），以及重新填值時必須清除 `cleared_at`，並指派 U20 為責任單元。 | New |
| R-06 | Major | rules.md BR2.3；functional-spec.md §六 ER 圖與文字 fallback；entities.md > SystemRequirementField.updatedOnBehalfOf | BR2.3 宣稱「四條外鍵必須存在」，ER 圖亦畫出 `projects \|\|--o{ reselection_events`。落地不符：`reselection_events.project_id` 刻意**無**外鍵（`schema_rbac.sql:636-640` 與 `:674` 的 COMMENT：稽核須比專案活得久，CASCADE 會抹掉紀錄，RESTRICT 會擋住刪除專案）；`updated_on_behalf_of` 是 `VARCHAR(64)` 且無外鍵（`:706`），與設計的「`users.id` 或 agent 識別」兩可寫法不同。**落地端較對**（符合 FR12.4b 的稽核目的），但 BR2.3 若被當成驗收條件，會要求加回外鍵而破壞稽核。外鍵清單另需補上 `project_members.invited_by → users.id`。 | 修正 BR2.3 與 ER 圖：改為三條必有外鍵加「稽核表刻意無外鍵」的聲明及其理由；把 `updated_on_behalf_of` 定為 agent 識別字串、不得為外鍵。 | New |
| R-07 | Major | rules.md BR3.1、BR3.2；functional-spec.md §三、§九 `OPEN-P1` | 既有環境（`192.168.10.10`，非空 volume）的建表路徑被整段延後（「本站不預選」，落點 `code-generation`／部署決策），`OPEN-P1` 沒有擁有者或截止點。BR3.1 的「大聲失敗」被寫成針對 `database.py` 的 `_ensure_*` 路徑，若實際走腳本路徑（落地為 `backend/scripts/run_meta_schema_migration.py`，見 `schema_rbac.sql:581-585`）則該規則沒有對應的約束。設計因此留下「規則存在但適用對象未定」的空洞：實作者選了不同路徑，BR3.1 便不再約束它。此項為 K-15 自己的 `known_constraint_inherited_from_K04`，必須在本單元收斂，不能再丟給下游。 | 把「大聲失敗」改寫為與路徑無關的驗收條件（建表失敗須使啟動或部署以非零狀態結束），並指名路徑與擁有者；以實際落地的腳本核對該條件成立（本審查未執行腳本，僅讀 SQL 註解）。 | New |
| R-08 | Minor | functional-spec.md 〇、rules.md BR3.1 引用；entities.md ProjectMember.role | 行號引用不準：`rbac.py:33／:288` 指全域 `Project_Admin`，實際 `backend/services/rbac.py` 中 `"Project_Admin"` 在 `:27`，`:33` 是 `"Platform_Admin"`，`:288` 是 `return current_user`，`:312` 為 `return admin.role == "Project_Admin"`。此錯誤沿襲自 `project.md` 的既有措辭，並非本單元獨有，但本單元重述時未核對。`database.py:257`／`:304`／`:192` 的 except 形狀核對屬實。 | 以 `:27`／`:312` 取代，或改為引用符號名稱。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取 `schema_rbac.sql:568-790` 與 `entities.md`／`rules.md` 逐項比對 | 欄位與約束有 6 處不符（R-01、R-02、R-05、R-06 及 role／FK） | 落地端多數已修正，設計檔未回補 |
| 對 `stories.md` 逐字核對 AC12.1.1-3、AC11.2.1-3 | 5 條追溯描述與原文不符 | R-03 |
| 核對 `database.py` 的 except 形狀（`:192`、`:257`、`:304`） | 屬實 | BR3.1 的事實前提成立 |
| 核對 `rbac.py:33`／`:288` | 不符 | R-08 |
| 未執行任何測試或指令（brief 禁止寫檔與快取） | N/A | 腳本是否大聲失敗未經實測，見 R-07 |

### 計數

Critical 1、Major 6、Minor 1。
