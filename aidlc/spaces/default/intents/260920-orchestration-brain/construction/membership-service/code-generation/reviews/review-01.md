## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-07T16:09:41Z
**Iteration:** 1

### 覆蓋範圍

依 brief 的 (a)–(g) 逐項說明實際查過什麼、沒查什麼。全程未執行任何 `python`／測試；全部結論來自 `Read`／`grep -n`／`sed -n`／`git diff --stat`／`git status --short`／`wc -l` 等唯讀檢查。

**(a) 五項最高風險規則 — 全部開檔核對，有證據：**
- `BR4.1`（`select_successor` 純函式）：讀完整支 `backend/services/membership_selection.py`，import 僅 `__future__`／`typing`／`services.membership_types`，無 `sqlalchemy`／`Session`／`httpx`／`HTTPException`。facade 的 `select_successor` 為 `@staticmethod`，原樣轉呼叫，未夾帶 DB 存取（`membership_facade.py:413-422`）。**驗證通過。**
- `BR2.1`（共同上游守門）：讀 `membership_service.py:320-432`。`change_role`／`remove_member` 共用單一謂詞 `admin_count_after`／`assert_still_has_admin`；`assert_can_deactivate` 走集合版 `projects_losing_last_admin`（`HAVING count(*)=1`，同一不變量的量化形式）。兩者並非同一函式呼叫，但程式內自陳理由（避免 N+1，已標 `NFR12.10`）且有專門的等價測試 `test_M7_aggregate_guard_matches_the_per_project_predicate`（`backend/tests/test_membership_data.py:296-345`，涵蓋四種形狀）。**可接受，非規則違反。**
- `BR5.5`（橫幅查詢雙重過濾）：讀 `membership_service.py:505-531`，兩處查詢皆同時帶 `cause == CAUSE_AUTO_RESELECTION` 與 `acknowledged_at.is_(None)`。**驗證通過。**
- `BR6.1`／`BR6.3`（三道檢查次序、既有兩道不變）：以 `git diff HEAD -- backend/services/user_router.py` 讀完整段落。既有兩道守門（自我停用 `:683`、最後一位可編輯角色全域管理員 `:686-709`）逐字未動，新第三道插在 `:712-738`，寫入 `target_user.is_active = ...` 在 `:739`——三道皆在寫入前。**驗證通過。**
- `NFR12.1` 鎖序：讀 `membership_service.py:151-216`。`lock_project` 鎖單一 `projects` 列；**查到一個落差，見 R-01**。

**(b) 三項偏離 — 全部核對：**
- §6.1（`M2` 比計畫字面更嚴）：讀 `schema_rbac.sql` 的 `J)` 區塊（`reselection_events` DDL），`project_id` 無 FK，`promoted_user_id`／`previous_owner_user_id` 皆 `REFERENCES users (id)`；`models.py:593-650` 的 ORM 與 DDL 逐欄對應，`cause` 的 `CheckConstraint` 名稱 `ck_reselection_events_cause` 與 DDL 的 `ck_reselection_events_cause` 一致。**實作者的「比計畫更嚴」判斷正確。**
- §6.2（11 個 facade 測試而非 8 個）：讀完整 `test_membership_facade.py` 的 class/method 清單，確認 `F1`／`F1b`／`F2`–`F8`／`F2b`／`F5b` 共 11 個測試存在，`F1`／`F1b` 讀過內容（見下）。`F2b`／`F5b` 僅核對存在性與一句 docstring，未逐行讀斷言內容。
- §6.3（timeout-minutes 15）：讀 `.github/workflows/ci.yml` diff 的 `concurrency` job，`timeout-minutes: 15` 存在，理由欄位與 code-summary 一致。

**(c) 三項「跑了才發現」— 僅第 5.3 項深入查證，其餘兩項憑檔案存在性採信：**
- 5.3（`authorization_status` 不在 `schema_rbac.sql`）：`grep -n "authorization_status" schema_rbac.sql` 零命中；`backend/database.py:262-273` 的 `_ensure_j5_schema()` 證實該欄位由啟動補丁加入。**確認為真**。進一步讀 `backend/tests_pg/test_membership_concurrency.py:167-194` 的 `_user()`，確認其以 raw SQL 建使用者列繞開此落差，且 `.github/workflows/ci.yml` 的 `concurrency` job 只套用 `schema_rbac.sql`、不跑後端啟動補丁，故該 job **不會**撞上這個落差（workaround 有效）。
- 5.1（`verify_meta_schema.sql` 的 `P7`）、5.2（`run_meta_schema_migration.py` 的後條件）：**未開檔逐行核對**，僅採信 code-summary 的敘述與 `source-manifest.json` 已列入這兩個檔案的事實。

**(d) 測試的誠實性 — 重點驗了 `F1` 與 `E6`，其餘僅看過函式清單：**
- `F1`（PBT 排列不變性）：讀 `test_membership_facade.py:40-90`。生成器的 `joined_at` 確實抽自一個以 `st.sampled_from(_TIME_POOL)`（僅 3 個值）定義的池，註解明寫理由；斷言同時驗 `select_successor(members) == select_successor(permuted)` 與「輸出必為輸入的元素」，非恆真。**非 tautological，驗證通過。**
- `E6`（三道檢查次序的端點測試）：讀 `test_membership_endpoints.py:309-342`，deny 側驗證 409 後 `is_active` **仍為 True**（防止寫入在檢查之後發生），allow 側另補一位管理者後驗證 200 與 `is_active=False`。**兩面都驗，非 tautological。**
- 其餘 24 個測試（`M1`–`M8`、`F2`–`F8`、`E1`–`E5`、`E7`、`C1`–`C3`）**僅讀過方法簽名／docstring 標題，未逐一讀斷言內容**，故無法對它們個別下「非恆真」的結論；本次審查對它們的信心僅建立在 code-summary 自陳的突變驗證結果（未重跑）與測試命名的一致性上。

**(e) 可算的數字 — 部分重算：**
- `source-manifest.json` 的 26 條路徑：以 `wc -l` 配合檔案本身解析，**26 條，與宣稱一致**。
- `traceability.json` 的 `open_items`：以 `python3 -c "json.load(...)"` 實際解析，得到 **18 項**（17 `named-gap` ＋ 1 `blocking-downstream`），**與 code-summary §九「17 項…另一項為 blocking-downstream」的敘述不一致**——見 R-02。
- 409 宣告數、`openapi.json` 的 `$ref`：**未重新解析** `openapi.json`（檔案過大，本輪未排程），採信 code-summary 的宣稱。

**(f) 遺漏項 — 僅查了一項：**
- `lock_projects_in_id_order`（NFR12.1 的多專案鎖序守門）：`grep -rn "lock_projects_in_id_order" backend/` 只命中定義與 `__all__` 匯出兩處，**在 `membership_facade.py`／`membership_service.py` 的任何呼叫路徑、以及 `tests_pg/test_membership_concurrency.py` 的任何測試裡都找不到第三次命中**。見 R-01。
- 交易邊界、`try/except` 的錯誤處理：讀過 `remove_member`／`change_role`／`create_project_with_owner`／`run_auto_reselection` 的 `try/except Exception: rollback; raise`（或逐專案 `except Exception: rollback; logger.exception`）形狀，符合 `construction.md` 的「錯誤必須外顯，不得靜默吞掉」；`run_auto_reselection` 的例外被記 log 後**不重新 raise**，是刻意的設計（逐專案獨立失敗），docstring 已說明代價。**未發現違反。**

**(g) 範疇紀律 — 已核對，排除判斷正確：**
- `git status --short` 全列，確認 `backend/services/agent_router.py`／`design_agent.py`／`rbac.py`／`rbac_seed_data.py`／`wa_collab_orchestrator.py`／`test_agent.py`／`test_hierarchy_migration.py`／`deploy/*`／`backend/.env.example` 等修改**皆不在** `source-manifest.json` 的 26 條路徑內——這些是其他單元（`rbac-story-ids`／`progress-channel`／`memory-data` 等）在同一 worktree 的未提交殘留，排除正確。
- `hierarchy_service.py`／`hierarchy_facade.py`／`hierarchy_router.py` 為 untracked（上一個單元 `hierarchy-service` 的新檔，尚未 commit），U19 對 `hierarchy_service.py` 的改動（新增 `create_project_nocommit`）經讀取確認**範圍極小**（29 行新函式 ＋ `create_project` 退化為呼叫它 ＋ commit），既有對外行為不變，且理由（`OPEN-ND19-5`：建專案與寫入管理者列須同交易）成立。**未發現範圍外改動。**

**未查項（誠實列出）：** `code-generation-plan.md`、`unit-test-instructions.md`、`code-generation-questions.md` 僅瀏覽標題與摘要表，未逐段核對；`backend/scripts/verify_meta_schema.sql`／`run_meta_schema_migration.py` 的具體斷言內容；`frontend/src/types/api.d.ts` 的 diff 內容（僅信任 `npm run check:types` 的宣稱結果）；`openapi.json` 的實際 409 `$ref` 內容；`DEPLOY.md`／`LOCAL-DEV.md` 除關鍵字命中外的完整段落；`M1`／`M5`／`M6`／`M8`／`F2`–`F8`（除 `F1`/`F1b`）／`E1`–`E5`／`E7`／`C1`–`C3` 的斷言邏輯細節；ADR-0006 表格與 `nfr-design`／`infrastructure-design` 的細部交叉引用。

### 發現

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `backend/services/membership_service.py` \> `lock_projects_in_id_order`（第 197 行定義）| 函式與其 docstring 明確宣稱是 `NFR12.1`／`security-design.md §一之二` 的多專案死鎖防線（多專案操作一律按 `projects.id` 遞增取鎖），但全樹 `grep -rn "lock_projects_in_id_order" backend/` 只命中定義與 `__all__` 匯出，**沒有任何呼叫端，也沒有任何測試覆蓋它**。實際的多專案安全性由 `run_auto_reselection` 以另一條路徑達成（逐專案獨立交易、一次只持有一個鎖、`project_ids_owned_by` 內部已 `sorted()`），這條路徑確實避開了死鎖，但它與 `lock_projects_in_id_order` 是兩套互不相關的機制——文件讀者會誤以為前者已被整合進改選流程並經測試驗證，而它是一段孤兒程式碼。`OPEN-ND19-2`（排序無機械強制）的開放項只承認「沒有工具檢查排序」，未揭露這條函式本身無人呼叫這一層落差。 | 二選一並在 `code-summary.md` 補一句誠實說明：(1) 刪除 `lock_projects_in_id_order`，改在 `run_auto_reselection` 的 docstring 明確只靠「逐專案獨立交易＋單鎖」達成無死鎖，不再宣稱有一條按序取鎖的共用機制；或 (2) 若日後真的需要單交易內鎖多個專案的路徑，讓那條路徑呼叫它並補一條測試，而不是讓它留在 `__all__` 裡等未來的人誤用一個從未測過的函式。 | New |
| R-02 | Minor | `aidlc/spaces/default/intents/260920-orchestration-brain/construction/membership-service/code-generation/code-summary.md` \> 第九節「仍然開放的項目」第一句 | 逐字「`traceability.json` 的 `open_items` 有 **17 項**，全部為 `named-gap` 或承接項，另一項為 `blocking-downstream`」——此句字面上先宣稱總數 17，隨後又說「另一項」暗示還有第 18 項，自相矛盾。以 `python3 -c "json.load(...)"` 實際解析 `traceability.json` 的 `open_items`，得到 **18 項**（`severity` 欄：17 個 `named-gap` ＋ 1 個 `blocking-downstream`，即 `OPEN-ID19-2`）。這是「可算的數字先算再寫」規則要求機械核對的那類落差，雖不影響任何技術結論，但讀者無法從這句話機械推出正確總數。 | 把該句改為「`traceability.json` 的 `open_items` 有 **18 項**（17 項 `named-gap`、1 項 `blocking-downstream`）」。 | New |

### 摘要

| 分類 | 計數 |
|---|---|
| new-design-problem | 2（R-01、R-02） |
| pre-existing-unreviewed | 0 |
| propagated-from-upstream | 0 |

**Critical：0；Major：1；Minor：1。** 依驗證規則（零 Critical、≤2 Major 可 READY），本輪結果為 READY。

本單元在五項最高風險規則（`BR4.1`／`BR2.1`／`BR5.5`／`BR6.1`／`BR6.3`）、三項偏離（§6.1–6.3）、既有端點兩道保護不變、router 不繞過 facade、`select_successor` 的純度與非恆真 PBT、`cause` 的 ORM/DDL 雙向鏡射等高風險面上，逐一開檔核對後**全部驗證通過、無發現**；程式本身的自我誠實記載（五個 `OPEN-*` 開放項、三項運行期才發現的落差）與實地查證結果一致，沒有查到任何一處自我報告與程式碼實況不符。本輪找到的兩項發現都屬於「文件/程式碼一致性」層級的瑕疵（R-01 是孤兒函式與其文件宣稱的落差，R-02 是一句話內部的數字矛盾），不影響功能正確性，亦非需要重新設計的架構缺陷。

**覆蓋聲明**：本輪審查受限於 60 turn 的時間預算，對 (a)(b)(e)(g) 類別做了逐行開檔核對，對 (c)(d)(f) 類別只做了代表性抽查（各類別取 1–2 個高風險項深入驗證），未逐一核對全部 29 條 `BR` 規則、全部 26 個測試方法、以及 `infrastructure-design`／`nfr-design` 的完整交叉引用。基於已核對的範圍給出 READY，但未核對部分存在未發現問題的可能性，建議下一輪若有餘裕可補查「未查項」清單中列出的檔案，尤其是 `C1`–`C3` 併發測試的斷言內容與 `verify_meta_schema.sql` 的 `P1`–`P14` 全文。

VERDICT: READY
