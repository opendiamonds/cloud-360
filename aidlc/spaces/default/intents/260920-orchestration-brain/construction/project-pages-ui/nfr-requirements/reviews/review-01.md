## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-15T23:04:08Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-requirements/security-requirements.md > 二 PPN-13（並行見 三之二 PPN-14c） | 新設計問題。PPN-13 的二元檢查在現行程式下無法通過：HierarchyNotFound 的訊息內嵌 id（backend/services/hierarchy_service.py:70 為「查不到專案 {project_id}」、:77 為「查不到系統 {system_id}」），router 的 _translate 以 str(exc) 當 detail（hierarchy_router.py:129-139）。PPN-13 要求「對不存在的 id 與對非成員可見的既有 id 各打一次」而 detail 逐位元相等，兩個不同 id 的 detail 必然不同，實作者只能改寫既有訊息或讓測試永遠紅。另外未規定各路徑守門拒絕時拋哪個例外與哪個樣板：系統清單走 MembershipNotFound（訊息來源不同於 HierarchyNotFound），delete_system 的不可見若回「查不到專案」會與不存在的「查不到系統」可區分 | 把檢查改成「同一個 id、前後兩種狀態」（例：先以 ORM 建專案打一次得 404 基準，再讓請求者成為不可見者對同一 id 打一次，或對同一 id 比較不存在與不可見），並逐路徑寫明拒絕時的例外型別與訊息樣板必須等同該路徑「不存在」分支（delete_system 用「查不到系統」） | New |
| R-02 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-requirements/performance-requirements.md > 二 PPN-07；aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-requirements/tech-stack-decisions.md > 一 PPN-25、四 | 新設計問題。PPN-07 與 PPN-25 的 blocking 同步清單不完整，且沒有說索引如何到達既有資料庫。(1) project_members 在既有環境是 Base.metadata.create_all 或 scripts/run_meta_schema_migration.py 建的，create_all 對已存在的表不補索引；database.py:90-97 的 _ensure_* 家族沒有它，DEPLOY.md 約 :686-690 逐字「不動啟動路徑（NFR8.4）」且 deploy.yml 不呼叫遷移腳本。照 PPN-25 只改 schema_rbac.sql、models.py、DEPLOY.md，staging 永遠沒有此索引，PPN-07 的驗收（檔案內 grep 與 test_M3 的名稱集合）卻全綠，無任何檢查會發現。(2) run_meta_schema_migration.py 解析 schema_rbac.sql 區塊並以 EXPECTED_INDEXES（:155-170）驗證，DEPLOY.md :674 的「結束碼 0 等價於 … 7 個索引」與腳本輸出計數都需同步，PPN-25 未列。(3) 若選擇改 database.py 補丁，project.md 的 LOCAL-DEV.md 同步義務也被觸發，亦未提 | 在 PPN-25 明定索引到既有 DB 的路徑（擇一：DEPLOY.md 新增必跑 psql 步驟與 \di 驗證，或新增 _ensure 補丁並同步 LOCAL-DEV.md 與 NFR8.4 的說明），把 run_meta_schema_migration.py 的 EXPECTED_INDEXES 與 DEPLOY.md 的計數列入同步清單，並讓 PPN-07 的檢查包含「對既有資料庫套用後索引存在」的可判定形式 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-requirements/security-requirements.md > 三之二 PPN-14a／PPN-14b／PPN-14c、三之二 末段建議形狀 | 新設計問題。建議形狀讓三個寫入方法接受呼叫端注入的 Callable，但未規定參數必填：若給預設值 None，任何漏傳的呼叫端靜默繞過守門，PPN-15 的 ast 鎖只管兩個 unscoped 方法、不管這個參數；目前三個方法只有 hierarchy_router.py:243／267／287 呼叫，所以風險是未來新增呼叫端。delete_system 的守門需要先載入系統才有 project_id，順序（K2 edit 後、載入系統、守門、擁有者檢查）與不存在時的拒絕訊息未寫 | 規定該參數為必填無預設（或加 ast 測試斷言三個方法的所有呼叫皆帶此參數），並在 PPN-14c 寫明載入系統後才守門的順序 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-requirements/security-requirements.md > 三之二 PPN-14 與五 | 新設計問題。PPN-14 的四案只用「專案內無系統」的構造才會是 204，未規定守門必須先於 BR4.4／預設專案等衝突檢查；delete_project 的 409 訊息帶剩餘系統數，若守門落在 service 的衝突檢查之後，被移出者可由 409 與 404 的差別探測到內容 | 加一案：被移出的擁有者對「底下仍有系統」的專案刪除須得 404 而非 409，並寫明守門早於衝突檢查 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-requirements/performance-requirements.md > 二之一 PPN-01 的依據表 | 新設計問題。上限 4 的推導只算單一使用者的在途數（4＋1＝5）。實測 database.py:37 為 SQLAlchemy 預設池（常駐 5、溢出 10，共 15）、單一 uvicorn 進程（backend/Dockerfile:30），故每位使用者的請求上限無法界定池用量：同時進頁的使用者達 3 位以上即可耗盡 15 條連線並排隊，與 4 或 8 無關。文中把 4 稱為「確認」並以池容量為理由，說服力被高估；數值本身可接受 | 改寫為經驗值並寫明多使用者下的耗盡條件，或明說此上限只降低單人突發、不保護連線池；數值不必改 | New |
| R-06 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/nfr-requirements/security-requirements.md > 五 Audit logging 的處置 | 既存漏審。殘留只列「被拒絕的嘗試查不到」，沒有如實列出成功的刪除：delete_project 的 CASCADE 會刪光全體成員列、delete_system 會刪掉他人填的需求欄位（本單元 PPN-14 的前提正是這個級聯），而成功的刪除依 §五 不留任何稽核。ADR-0006 Audit logging 判定為「相同（沿用既有）」但其破壞力是 R-01 裁決後才被承認的 | 在 §五 殘留與 §六 Audit 格補上「成功的級聯刪除無稽核」並標為已知殘留或開放項，供核可關卡知情接受 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| traceability 實算（jq／grep） | upstream_ids 11、coverage OK 2（NFR8、NFR11）、N/A 9、reverse 23；四份產出的 PPN 識別字集合與 reverse 的 id 集合相同（23）；繼承子條 4（NFR8.100、NFR11.100–102），需求總數 27 | 與四份產出宣稱的 11／2／9／23／27 一致，無差異 |
| 引用實測（hierarchy_facade.py:213-240、rbac_seed_data.py:327-337、database.py:37、Dockerfile:30） | 七個 K2 有 view 無 edit 的角色實數為 7；三個寫入方法只認 _authorize(edit) 加擁有者檢查；hierarchy_facade／hierarchy_service 內 NOT EXISTS 與 project_members 命中皆 0 | PPN-14a 的 403 變 404 陷阱論證成立；PPN-14b 的 grep 前提成立 |
| 呼叫端盤點 | create_system／delete_project／delete_system 在非測試程式中只有 hierarchy_router.py 三處呼叫 | PPN-14 範圍涵蓋三條路徑完整；R-01 裁決的四個子情境（三路徑、被移出的擁有者、零成員列、缺 K2 edit）皆有對應條目 |
| 測試可行性（tests/helpers.py） | make_session 把 engine 掛在 db._test_engine，可用 event.listen 計數 | PPN-06 的測法可行 |
| 未執行測試、python、npm | 依指示僅讀檔 | 無執行層驗證 |

### Summary

PPN-14 系列與 PPN-14a 的陷阱論證經實測成立且完整涵蓋 R-01 裁決，traceability 數字正確，ADR-0006 與 PBT 判定及五項不出題的理由站得住（僅審計殘留低報，見 R-06）。但 PPN-13 的二元檢查在現行訊息內嵌 id 的程式下不可能通過（R-01），且 PPN-07 的索引沒有到達既有資料庫的路徑、同步清單漏列遷移腳本與 DEPLOY.md 計數（R-02），故 NOT-READY。三類計數：新引入 0、既存漏審 1（R-06）、新設計問題 5（R-01 至 R-05）。
