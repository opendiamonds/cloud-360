## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-15T23:38:42Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-design/security-design.md > 八 殘留 第 4 項；七 ADR-0006 Network exposure 格 | 既存漏審。殘留第 4 項把成員頁與需求欄位端點的「不存在 vs 不可見」是否可區分推給 U19／U24 自己的規則，Network exposure 格卻寫「固定訊息使 id 枚舉只得到同一句 404」。實讀程式顯示兩處現在就可區分：membership_facade.py 的 list_members 先 _assert_project_exists（不存在回 404），再 _require_project_role（存在但非成員回 MembershipForbidden，即 403，:150-159）；requirement_field_facade.py 的 _authorize 對不存在系統回 RequirementFieldNotFound（404），對存在但非成員走 _deny(not_member) 回 RequirementFieldForbidden（403）。因此專案 id 與系統 id 的存在性仍可由 GET 成員清單與需求欄位端點以 403／404 差別枚舉，本單元五條路徑做到逐位元相同，整體的存在性預言機並未關閉。residual 的措辭讓核可者以為「由那兩個單元管」代表已有規則在管，實際沒有。 | 把殘留第 4 項與 Network exposure 格改寫為已實查的事實：註明上述兩處端點現況為 403 對 404 可區分、其行號與回應，並說明本單元的裁決範圍只涵蓋五條路徑；在核可關卡明列為待使用者知情接受或另開項目（例如要求 U19／U24 與 U20 把非成員一律回 404），不得再用「由那兩個單元自己的規則管」帶過。 | New |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-design/security-design.md > 二之四 靜態鎖 第 2 條 | 新設計問題。第 2 條把「接收者是 hierarchy_service 模組名」的呼叫整個豁免，且只掃屬性呼叫。router 若 import hierarchy_service 後直呼 hierarchy_service.delete_project(db, project_id=...)，或用 from services.hierarchy_service import delete_project 後以裸名呼叫，既跳過 K2 又跳過守門，靜態鎖仍綠。突變 G5 只涵蓋 router 傳 lambda，不涵蓋這條旁路。這是既有 BR1.5 殘留，但本設計把靜態鎖寫成關閉繞過的機制，宣稱強度高於實際。 | 靜態鎖加一條：hierarchy_service 的 create_system、delete_project、delete_system 在 backend/ 非 tests/ 內只准出現在 hierarchy_facade.py（含 Attribute 與 Name 兩種形式），並加對應突變；或在 §八 如實記為殘留。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-design/security-design.md > 二之三 測試矩陣 (e)；二之五 突變 G3 | 新設計問題。守門早於 409 的案例 (e) 只涵蓋 delete_project（底下仍有系統）。delete_system 也有自己的 409（hierarchy_service.py 的預設系統不可刪、底下仍有 N 張架構圖，訊息帶張數），被移出的擁有者若守門被誤置於 service 之後，會由張數探測到內容，而矩陣沒有 delete_system 版本，G3 也只點名 (e)。 | 補 (e') 被移出的擁有者對「底下仍有架構圖」的系統刪除須得 404 而非 409，並讓 G3 對 delete_system 也各自適用。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-design/logical-components.md > 三 索引與遷移的落點 | 新設計問題。project.md 必做 1 要求新增物件時更新 schema_rbac.sql 的檔頭涵蓋清單與驗證註解。九項落點未列：schema_rbac.sql 檔頭 J 區塊的涵蓋說明（約 :12），以及檔尾 J 區塊驗證註解（約 :1261-1280，已有 project_members 欄位數與 ix_reselection_events_unack 的 pg_indexes 查詢）應補 ix_project_members_user_id 的查詢與預期。漏掉不會讓任何測試紅，屬無聲漂移。 | 在 §三 加第 10 項：schema_rbac.sql 檔頭涵蓋說明與檔尾驗證註解補上新索引的存在查詢。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| grep：六處帶 id 的專案或系統訊息 | hierarchy_service.py 為 :70、:77、:180、:199、:381、:388，:89 為架構圖 | 與設計的「六處，:89 不動」相符 |
| grep：三個寫入方法的測試呼叫點 | test_hierarchy_service.py 11（排除 :77 的 service 層呼叫）、test_work_orchestrator_store.py 2、test_requirement_field_facade.py 1、test_mcp_bridge_e2e.py 1，合計 15；非測試呼叫點為 router 三處 | 15 與 3 屬實；無以 callable 傳遞的第四種形式；test_hierarchy_service.py:164 的簽章測試只看第一參數為 principal，不受新增 keyword-only 參數影響 |
| grep：兩句訊息的斷言 | backend 測試與 frontend 內 0 處（命中皆為來源程式） | 改訊息不需改任何既有斷言，屬實 |
| 計數：run_meta_schema_migration.py 的 EXPECTED_INDEXES | 8 筆，EXPECTED_CONSTRAINTS 9、EXPECTED_TABLES 5 | DEPLOY.md:674 的「7 個索引」確為既存漂移，8 加 1 為 9 屬實 |
| 讀取：schema_rbac.sql、models.py、test_membership_data.py | project_members DDL :594-606、CASCADE 於 :596、ddl_indexes 正規式與 test_M3 同設計描述；reselection_events.project_id 無外鍵 | 索引落點與 test_M3 的約束描述正確；角色變更稽核列不隨專案刪除而消失，殘留表未漏列 |
| 讀取：SQLAlchemy 預設池 | database.py:37 為 create_engine(db_url)，無池參數；Dockerfile 單一 uvicorn | 15 條連線與 3 位使用者耗盡的算式成立 |
| 未執行測試、python、npm | 依指示僅讀檔與 grep | UNION 的索引選用屬 planner 行為，設計已明講不設 EXPLAIN 斷言 |

### Summary

守門順序（權限、系統先取所屬專案、可見性、擁有者、409）、必填無預設的簽章、固定訊息的六處位置與 15 處測試呼叫點、索引 9 個落點與 8 變 9 的數字、11 項帶入項落點與 ADR-0006 四面向判定，逐項對照現行程式後皆成立，五條路徑內找不到仍可區分存在與不存在的旁路。主要風險是 R-01：同一安全目標在 U19 成員清單與 U20 需求欄位端點仍以 403 對 404 洩漏存在性，而殘留措辭把它推給別的單元；其餘三項為 Minor。三類計數：新引入 0、既存漏審 1、新設計問題 3。無 Critical、1 個 Major，依規則為 READY。
