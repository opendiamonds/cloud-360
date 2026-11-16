## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-16T17:19:36Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | DEPLOY.md > 「U23 起：部署後再跑一次遷移腳本」第 2 步；backend/scripts/run_meta_schema_migration.py:70-72,521-527 | 新引入。第 2 步要在 backend 容器內執行遷移腳本，但腳本以 REPO_ROOT = BACKEND_DIR.parent 讀 schema_rbac.sql。容器內腳本在 /app/scripts，BACKEND_DIR 為 /app，REPO_ROOT 為 /，SCHEMA_FILE 為 /schema_rbac.sql。backend 映像的 build context 是 backend 目錄（deploy/docker-compose.deploy.yml:81），Dockerfile 只 COPY 該目錄，compose 只把 schema_rbac.sql 掛給 db 服務（:55），backend 服務沒有掛載。因此照文件執行會在 read_text 拋 FileNotFoundError，被 :524 捕捉後 exit 1，索引不會建出。code-summary Step 1 複驗只查了 WORKDIR、COPY 與 .dockerignore，沒查腳本自己對 schema_rbac.sql 的依賴；使用者裁決的容器內形式因此在 staging 無法完成，而這是索引到達既有資料庫的唯一路徑 | 擇一：(a) 步驟改為先把 schema_rbac.sql 以 docker cp 或唯讀掛載放進容器的 /schema_rbac.sql 再執行；(b) 讓腳本接受環境變數或參數指定 SCHEMA_FILE；(c) 改用 docker exec 對 db 容器直接執行單行 CREATE INDEX IF NOT EXISTS。無論哪種，要在 staging 主機實際走過一次，並更正 code-summary 十三節與 Step 1 複驗表 | New |
| R-02 | Major | frontend/src/components/projects/RequirementsTab.tsx:67-69,206 與 frontend/src/pages/ProjectDetailPage.tsx（只渲染目前籤，active 為 requirements 時才掛載）；code-summary 偏離 D-7 | 新設計問題。drafts、fieldErrors、savedStale 都是 RequirementsTab 的本地 state，切到總覽或記憶籤即卸載，三者全部遺失。於是儲存失敗後留在畫面上的輸入值與「未儲存」標記、重讀失敗時刻意保留的草稿（BR84.5、BR85.6、frontend-components 第 97-100 行「失敗欄位的草稿保留」），只要使用者去總覽看一眼未填計數再回來就消失，正是 AC11.2.3「我輸入的值不消失」要防的結果。e2e 的 F5、F7、F8 只涵蓋同籤內重讀，沒有切籤再回來的案例；D-7 把它列為殘留但沒有對照 BR84.5 評估 | 把 drafts、fieldErrors、savedStale 提升到 ProjectDetailPage，或讓需求籤保持掛載（切籤時以 hidden 隱藏），並補一個 e2e：儲存失敗後切到總覽再切回，輸入值與「未儲存」仍在；補對應突變 | New |
| R-03 | Minor | backend/services/hierarchy_facade.py:259-275,297,328（create_system、delete_project、delete_system） | 新設計問題。守門之後仍保留 owner_user_id 檢查，所以被移出的建立者（owner_user_id 仍是他）無法通過守門，其餘成員（含 project_admin）又不是 owner，沒有任何人能再對該專案建立或刪除系統，也不能刪專案；SystemCreateAction 也只對 owner 渲染。這是使用者 R-01 裁決的直接後果，但 code-summary 十二節第 9 項的殘留清單沒有列出這個死結 | 在殘留與核可關卡揭露事項補上「建立者被移出後該專案無人能新增系統或刪除」，並指定後續承接（例如移出時同步移轉 owner_user_id，或改以成員角色判定寫入） | New |
| R-04 | Minor | frontend/src/pages/ProjectDetailPage.tsx（useEffect 開頭的 Number.isFinite(projectId) 判斷） | 新引入。網址為非數字（例如 /projects/abc）時 effect 直接 return，status 永遠停在 loading，畫面持續顯示「正在載入專案」，與 BR83.4 的 not-found 態不一致 | 非有限數字時直接進 not-found 態，並補一個 e2e | New |
| R-05 | Minor | code-summary.md 五節「附帶觀察」與十一節第 3 項 | 既存漏審。dev 模式下 member-pages 與 memory-page 兩支 spec 變紅，歸因 StrictMode 但「未驗證是否在 HEAD 既存」。git diff 顯示本單元對前端只動 App.tsx 與 Sidebar.tsx，沒有碰共用程式，推論可信，但仍是未驗證的歸因 | 在 build-and-test 以 HEAD 乾淨 checkout 在 dev server 跑一次那兩支 spec 並記錄結果 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| python3 -B -m unittest tests.test_project_visibility_queries tests.test_project_visibility_static tests.test_project_visibility_endpoints tests.test_project_write_guard tests.test_membership_data | Ran 61 tests, OK | 本單元後端新增與修改測試在全域 python3 下全綠，與 code-summary 數字一致 |
| 讀碼查證：可見性謂詞與守門順序 | 通過 | 可見性只有 _visible_project_ids_select 一份；三條寫入路徑順序為 K2 edit、delete_system 先取所屬專案、守門、擁有者檢查、409；project_visible 必填 keyword-only；不存在與不可見使用同一例外型別與同一常數；ast 靜態鎖與 router 三處注入相符。專案清單先查可見 id 再做 K2 判定，被拒時結果被丟棄，無洩漏，兩條路徑僅差一條 SQL，不構成可用旁路 |
| 讀碼查證：20 項帶入項抽查 | 通過 | #1、#6、#7、#8、#9、#13、#14、#15、#17 的程式與測試落點皆在；#16、#20 的文件落點在，但 R-01 指出其可執行性不成立 |
| 讀碼查證：索引一致性 | 通過 | schema_rbac.sql（DDL、檔頭、檔尾）、models.py 的具名 Index、EXPECTED_INDEXES 實算 9 筆、DEPLOY.md 的 9 與不開 5432 彼此一致 |
| 讀碼查證：fanoutQueue 與詳情頁入列 | 通過 | 並行上限 4、FIFO、cancel 後不再發出；詳情頁先入列全部需求欄位再入列全部變更紀錄；tab 不在 effect 依賴陣列 |

### Summary

授權面（可見性單一定義、三條寫入守門的順序與必填注入、固定訊息、靜態鎖、缺 K2 一律 403）與 20 項帶入項的抽查都成立，未發現洩漏或時序旁路；兩個 Major（R-01 部署步驟在容器內因找不到 schema_rbac.sql 而必然失敗、R-02 切籤遺失失敗草稿）未達 NOT-READY 門檻（Major 為 2、無 Critical），因此 READY，但 R-01 建議在合併前修正。分類計數：新引入 2（R-01、R-04）、新設計問題 2（R-02、R-03）、既存漏審 1（R-05）。
