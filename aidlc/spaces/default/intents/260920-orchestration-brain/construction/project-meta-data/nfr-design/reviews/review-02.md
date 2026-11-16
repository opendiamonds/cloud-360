## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

`U18 project-meta-data` 的 nfr-design 產出（`security-design.md`、`traceability.json`）整體自洽且查證紮實：`[ND1]`=A 的 CASCADE 與不設外鍵取捨有具體的行為迴歸論證（`delete_project` 對 `IntegrityError`）、`P-FK0`／`P-SURV` 手段與目的雙斷言、索引覆蓋分析、audit logging 為本單元唯一適用面向且四面向逐格對照上游。主要缺口有兩處，皆為設計未涵蓋而非設計錯誤：（1）跨單元共享契約 `K-15` 的 `foreign_keys` 仍列第四條外鍵，本站只對 `rules.md` 開修訂指派（前次 review-01 已提 R-01，凍結產出未補；已落地的 code-generation 摘要 `OPEN-CG18-2` 已承接揭露）；（2）本站回補九個欄位後，其中數個欄位本身就是外鍵，卻未對它們逐條表態 `ON DELETE`，違反本站 §一之一自己寫下的慣例。兩項 Major 未超過 2 項門檻，判 READY；`OPEN-ND18-3`（`FR12.2` 稽核無承載者）把實體邊界決定丟給 code-generation，屬值得人在關卡權衡的風險。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | `construction/project-meta-data/nfr-design/security-design.md` 第一節與第六節第 2 項，以及 `traceability.json` 的 `OPEN-ND18-2`；對照 `inception/contract-design/contract-summary.md` 的 `K-15` `foreign_keys` | 前次 review-01 已提 R-01，凍結產出仍未補。`[ND1]`=A 把 `reselection_events.project_id` 收為不設外鍵，但 `OPEN-ND18-2` 只指派修訂 `rules.md` 的 `BR2.3`。本文件第一節之一自己寫道 `entities.md`、`K-15` 的 `foreign_keys`、`rules.md` 三處都列了該外鍵，卻沒有把 `K-15` 列入任何 open item。`K-15` 是 `U19`／`U20` 讀取的跨單元契約，信任它會誤以為該欄位有參照完整性保護，而 `BR2.3` 的 `violation_behaviour` 警告的正是這個情境。已落地的 `code-generation/code-summary.md` 的 `OPEN-CG18-2` 已揭露「`BR2.3` 與 `K-15` 兩處」，故風險已被下游承接；但本站的設計紀錄本身仍是缺口，且 `OPEN-ND18-2` 的落點只有 `rules.md`。 | 在關卡上確認 `K-15.foreign_keys` 的修訂已有明確承接站與擁有者（`contract-design` 或 `code-generation` 的 summary），並在 `OPEN-ND18-2` 補列 `K-15`。凍結產出不回改，以 `OPEN-CG18-2` 為準向下傳遞。 | New |
| R-02 | Major | `construction/project-meta-data/nfr-design/security-design.md` 第一節之二 外鍵表（僅 4 列）、第三節之一／之三（回補九個欄位）；對照 `code-generation/code-summary.md` 第 115 行（實際外鍵總數 8 條） | 本站第一節之一確立慣例：「要嘛決定 `ON DELETE`，要嘛在 COMMENT 寫明沒決定與落點，兩者皆無是漏項」，但第一節之二只對 4 個外鍵欄位表態。第三節回補的九個欄位中，`promotedUserId`、`previousOwnerUserId`、`updatedBy`、以及 `ProjectMember.invitedBy` 與 `updated_on_behalf_of` 這類使用者參照欄位，天然會成為指向 `users.id` 的外鍵，但本站對它們零處置、零 `ON DELETE`、零 COMMENT 要求。後續 code-generation 實查出 `BR2.3` 從未列舉的 5 條外鍵（總數 8 條，`OPEN-CG18-3`），證明這是本站設計遺漏而非實作多餘。後果不小：`reselection_events` 的 `promoted_user_id` 若為預設 `NO ACTION`，則稽核列會阻擋使用者硬刪除（與 `OQ-H1` 刻意未決衝突），也使 `[ND1]`=A「稽核獨立存活」的敘述只對 `project_id` 成立。 | 回補一張涵蓋全部使用者參照欄位的 `ON DELETE` 決定表（或明寫沿用 `projects.owner_user_id` 的「刻意不決定、COMMENT 標落點 `OQ-H1`」慣例），並確認 `P-SURV` 與使用者硬刪除情境不互相矛盾。凍結產出不回改，在關卡以 `OPEN-CG18-3` 為準，記錄本站遺漏。 | New |
| R-03 | Minor | `construction/project-meta-data/nfr-design/security-design.md` 第三節之三表格與第四節之一（`(system_id, agent_group, field_key)`）；對照 `functional-design/entities.md`（「同一系統內同一欄位名至多一列」） | 前次 review-01 的 R-02 仍留在凍結產出：本站把 `entities.md` 的兩欄唯一約束寫成三欄，卻未在 nfr-design 內標明這是刻意加寬或更正；只有下游 `code-summary.md` 第 107 行才寫明「刻意加寬」與理由。兩欄與三欄語意不同（不同 `agent_group` 下可否有同名 `field_key`），讀本站產出的人無從分辨。 | 於關卡備註此為已知對齊差異，語意以 `code-summary.md` 與 `P11` 兩半斷言為準；不需回改產出。 | New |
| R-04 | Minor | `construction/project-meta-data/nfr-design/security-design.md` 第二節之二（`:83`）、第二節之三（`:69`）；`nfr-design-questions.md`（`unit-of-work.md:448`） | 前次 review-01 的 R-03 已提：`run_hierarchy_migration.py` 的行號引用疑似偏移 1 行（終檢訊息約 `:82`、`traceback.print_exc` 約 `:68`），`unit-of-work.md` 引用約偏 2 行。本次因審查範圍限制未能重新開啟 `backend/scripts/` 複驗，故沿用前次結論，不影響設計結論。 | 核可時留意；後續引用該腳本時一律重驗行號。 | New |
| R-05 | Minor | `construction/project-meta-data/nfr-design/traceability.json` 的 `OPEN-ND18-3`；`security-design.md` 第三節之四 | `FR12.2` 的人工角色變更稽核無承載者，而 `AC12.2.2` 的 Given 已要求同一變更紀錄承載它；本站「不自行決定表的語意範圍」並把實體邊界決定指派給 code-generation。code-generation 是實作站，不是 domain／functional design，指派給它等於讓實作者在建表時自行裁決實體語意，且 `code-summary.md` 明示該項仍開（`reselection_events` 的 `previous_role`／`new_role` 刻意不設 CHECK 以免替它先下結論）。這是已命名的缺口、有證據，但落點不在能改實體邊界的站。 | 關卡上由人確認 `OPEN-ND18-3` 的決策者與時點（決定 `reselection_events` 是否一般化為角色變更稽核表），避免 `U19` 先依自動改選專用語意實作後再返工。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| （無指定驗證工具） | 未執行 | 本站未列驗證工具；且依審查範圍限制，不得開啟其他單元或應用程式碼目錄，也不得執行會寫檔或產生快取的指令。發現皆依 `nfr-design`、`nfr-requirements`、`functional-design`、`code-generation` 產出及前次 review-01 的逐字內容。 |
