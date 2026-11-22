## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-06T15:22:34Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Status |
|---|---|---|---|---|
| R-01 | Major | `security-design.md` §一（`[ND1]`=A 落地）及 §六殘餘風險第 2 項 vs `inception/contract-design/contract-summary.md` 的 `K-15` `foreign_keys` 清單 | `[ND1]`=A 把 `reselection_events.project_id` 決定為**不設外鍵**，而這張表的 FK 原本同時出現在三處：`entities.md`、`rules.md` 的 `BR2.3`、以及共享契約 `contract-summary.md` 的 `K-15.foreign_keys`（逐字列出 `"reselection_events.project_id → projects.id"`，`K-15` 的消費端為 `U19`／`U20`）。本文件明確查出並處置了 `rules.md` 的 `BR2.3` 不一致（`OPEN-ND18-2`，指派 `code-generation` 修訂 `rules.md`），但同一份文件在 §一之一自己寫下「`entities.md`、契約 `K-15` 的 `foreign_keys` 清單、`rules.md` **三處**都沒有提到 `ON DELETE`」——證明作者知道 `K-15` 是三個宣告位置之一，卻只對 `rules.md` 開了修訂指派，`K-15`（跨單元共享契約，`U19`／`U20` 會讀）完全沒有被列入 `OPEN-ND18-2` 或任何其他 open item。`project.md` 對這個失敗形狀有多筆既存教訓（「跨檔掃查要按事實列舉」「同一份檔案內我正確引用了 blocking 規則兩次，然後對本輪新增的三張表漏套用」），本處正是同一形狀：同一個事實（四條外鍵）在三個已知的宣告位置之一被修正，另一個同樣已被自己點名的位置被漏掉。下游風險具體且可指認：`U19`／`U20` 的設計者若信任 `K-15` 的 `foreign_keys` 清單（這是它們唯二被告知的契約來源），會誤以為 `reselection_events.project_id` 有資料庫層參照完整性保護——而 `BR2.3` 自己的 `violation_behaviour` 逐字警告的正是這個情境（「少了外鍵則可寫入指向不存在專案的列，而這類列不會被任何應用層檢查發現」）。 | New |
| R-02 | Minor | `security-design.md` §三之三表格最後一列與 §四之一 vs `functional-design/entities.md` 的 `SystemRequirementField.entity_constraints` | `entities.md` 宣告的唯一約束逐字為「**同一系統內同一欄位名至多一列**」，即 `(system_id, field_key)` 兩欄。但 `security-design.md` 在 §三之三與 §四之一兩處都把它改寫成三欄複合鍵 `(system_id, agent_group, field_key)`，且未註明這是對 `entities.md` 原文的擴充或更正。兩者若語意不同（`agent_group` 是否影響 `field_key` 的唯一性範圍），`code-generation` 建索引／約束時會依兩份文件得到不同的 DDL；若語意相同（`agent_group` 由 `field_key` 決定，三欄鍵只是冗餘），文件應明寫這一點，否則讀者無法分辨這是刻意加寬還是筆誤。 | New |
| R-03 | Minor | `security-design.md` §二之二、§二之三、§五（`backend/scripts/run_hierarchy_migration.py` 的行號引用）；`nfr-design-questions.md`（`unit-of-work.md` 的行號引用） | 兩處既有程式的行號引用有小幅偏移，內容本身正確：① `U4` 腳本「終檢通過」訊息的 `print()` 實際在 `run_hierarchy_migration.py:82`，文件引用為 `:83`；`traceback.print_exc(file=sys.stderr)` 實際在 `:68`，文件引用為 `:69`。② `nfr-design-questions.md` 引用 `unit-of-work.md:448` 的「自動改選挑選函式應為不讀 DB 純函式」一段，實際位於約 `:446`。`project.md` 對「內容對而行號錯」這個形狀有多筆既存教訓，列出以便核可時留意；不影響本站任何設計結論。 | New |

### Validation Tool Results

No validation tools were specified for this stage's dispatch; none were run. All findings above are grounded in direct `file:line` verification against `security-requirements.md`、`entities.md`、`rules.md`、`functional-spec.md`、`contract-summary.md`、`inception/domain-design/components.md`、`inception/user-stories/stories.md`、`inception/requirements-analysis/requirements.md`、`inception/units-generation/unit-of-work.md`、`schema_rbac.sql`、`backend/services/hierarchy_service.py`、`backend/services/hierarchy_facade.py`、and `backend/scripts/run_hierarchy_migration.py`.

### Summary

The nine-missing-columns finding (§三), the `CASCADE`-vs-`RESTRICT` reasoning against `hierarchy_service.delete_project`, the `P-FK0`/`P-SURV` test design, the index-coverage analysis, and the ADR-0006 four-face table all check out against the cited upstream artifacts and backend code — this is unusually well-verified work, including exact `file:line` precision on roughly a dozen citations. The one real gap (R-01) is that the document fixes the `BR2.3` side of a three-way inconsistency (`entities.md` / `rules.md` / `contract-summary.md` all declaring a fourth foreign key that `[ND1]=A` now removes) but never flags the `contract-summary.md` `K-15` side, even though the document itself names `K-15` as one of the three declaring locations. Since `K-15` is a cross-unit contract read by `U19` and `U20`, this is worth the human's attention before approving, but it does not block implementability of this unit's own design and is a single Major finding, well under the NOT-READY threshold.
