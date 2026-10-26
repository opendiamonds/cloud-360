## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U23 project-pages-ui 的 NFR 產出（performance、security、tech-stack、traceability）自洽，承接上游的可追溯性數字經實算相符（upstream 11、coverage 11、reverse 23），ADR-0006 四面向與 PBT 判定逐格有落點，PPN-14a 的「403 不得變 404」陷阱（七個有 K2 view 無 K2 edit 的角色）經 rbac_seed_data.py 實測成立。前次 review-01 的六項發現仍留在凍結的產出裡，但其中兩項實質問題已由已落地的程式處置，程式端是對的：PROJECT_NOT_FOUND_DETAIL／SYSTEM_NOT_FOUND_DETAIL 已改為不含 id 的常數，ix_project_members_user_id 已進 schema_rbac.sql、models.py、run_meta_schema_migration.py 與 DEPLOY.md。故無 Critical、僅 1 項 Major，判 READY；剩餘缺口是「設計檔未記下程式已做對的事」，由人在關卡知情即可。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/project-pages-ui/nfr-requirements/tech-stack-decisions.md > 一 PPN-25；performance-requirements.md > 二 PPN-07 | 前次 review-01 R-02 已提。PPN-25 與 PPN-07 只列 schema_rbac.sql、models.py、DEPLOY.md 三處同步，沒有說索引如何到達既有資料庫（create_all 不補舊表索引，deploy.yml 不跑遷移腳本），也沒列 scripts/run_meta_schema_migration.py 的 EXPECTED_INDEXES 與 DEPLOY.md 的索引計數。PPN-07 的驗收（grep 與 test_M3 名稱集合）在 staging 沒有索引時仍全綠。已落地的程式端是對的：run_meta_schema_migration.py:118 與 :176 已納入新索引，DEPLOY.md:678 把計數 7 改 9，DEPLOY.md:849 起新增「部署後再跑一次遷移腳本」小節與 psql 驗證。故落差是設計檔漏列，不是實作漏做 | 在核可關卡如實記載：PPN-25 的同步清單以已落地的程式為準（含遷移腳本與 DEPLOY.md 計數、既有環境重跑步驟）；若要補強檢查，加一條「對既有資料庫套用後 pg_indexes 含該索引」的可判定形式 | New |
| R-02 | Minor | construction/project-pages-ui/nfr-requirements/security-requirements.md > 二 PPN-13；三之二 PPN-14c | 前次 review-01 R-01 已提。PPN-13 要求對「不存在的 id」與「不可見的既有 id」各打一次且 detail 逐位元相等，在訊息內嵌 id 時不可能通過；產出沒有要求訊息必須是不含 id 的固定常數，也沒逐路徑寫明拒絕時的例外型別與樣板。已落地的程式端是對的：hierarchy_facade.py:114-115 定義 PROJECT_NOT_FOUND_DETAIL＝「查不到專案」與 SYSTEM_NOT_FOUND_DETAIL＝「查不到系統」，hierarchy_service.py 的 assert_project_owned_by 使用常數，delete_system 的不可見走「查不到系統」（hierarchy_facade.py:335）。因此該二元檢查現在可通過，嚴重度降為 Minor | 設計檔不回改；在 code-summary 或關卡摘要記明「PPN-13 的前提是固定常數訊息，以程式為準」 | New |
| R-03 | Minor | construction/project-pages-ui/nfr-requirements/security-requirements.md > 三之二 末段建議形狀 | 前次 review-01 R-03 已提。產出的建議形狀未規定可見性判定參數必填。已落地的程式端是對的：hierarchy_facade.py:261 註解寫明 project_visible 必填、無預設、keyword-only，七個方法皆同，漏傳時 Python 直接報錯，比設計檔要求的更嚴 | 無需改程式；關卡摘要記明程式比設計嚴格 | New |
| R-04 | Minor | construction/project-pages-ui/nfr-requirements/security-requirements.md > 三之二 PPN-14 四案 | 前次 review-01 R-04 已提。PPN-14 四案只涵蓋「專案內無系統」的刪除，沒有「被移出的擁有者對底下仍有系統的專案刪除須得 404 而非 409」，也沒寫守門必須早於衝突檢查。若守門落在衝突檢查之後，409 訊息帶的剩餘系統數會成為存在性預言機。本次未抽查程式端的檢查順序 | code-generation 或 tcms 階段補一案並確認守門順序；未確認前視為開放項 | New |
| R-05 | Minor | construction/project-pages-ui/nfr-requirements/performance-requirements.md > 二之一 PPN-01 依據表 | 前次 review-01 R-05 已提。上限 4 只算單人在途數（4＋1＝5）。實測 backend/database.py:37 為 create_engine(db_url) 預設池（常駐 5、溢出 10），單一 uvicorn 進程；三位以上使用者同時進頁即可耗盡連線，與 4 或 8 無關。文中把 4 稱為「確認」並以池容量為理由，說服力被高估；數值可接受 | 關卡摘要註明此上限只降低單人突發、不保護連線池 | New |
| R-06 | Minor | construction/project-pages-ui/nfr-requirements/security-requirements.md > 五 Audit logging；六 Audit 格 | 前次 review-01 R-06 已提。Audit logging 判定為「相同（沿用既有）」，殘留只列「被拒絕的嘗試查不到」，沒有如實列出成功的級聯刪除：delete_project 會 CASCADE 刪光成員列、delete_system 會刪掉他人填的需求欄位，而成功的刪除不留稽核。該破壞力正是 PPN-14 的前提 | 在關卡摘要補記「成功的級聯刪除無稽核」為已知殘留，供人知情接受 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| traceability.json 實算（python json） | stage／unit 各 16 鍵；upstream_ids 11、coverage 11、reverse 23 | 與四份產出宣稱的 11／23 一致 |
| 引用實測（rbac_seed_data.py:327-337） | Developer、FinOps_Analyst、SRE、Ops_Lead、Platform_Engineer、Security_Reviewer、Platform_Owner 七個角色 K2 view＝True、edit＝False | PPN-14a 的 403 變 404 陷阱論證成立，七個數字正確 |
| 程式抽查（hierarchy_facade.py、hierarchy_service.py、run_meta_schema_migration.py、DEPLOY.md、schema_rbac.sql、models.py） | 固定常數訊息、必填 project_visible、索引於 DDL／ORM／遷移腳本／DEPLOY.md 皆已落地 | R-01、R-02、R-03 的缺口在程式端已處置，設計檔未同步 |
| 測試、lint、建置 | 未執行 | 依 brief 僅讀檔，無執行層驗證 |
