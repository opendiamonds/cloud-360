## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | DEPLOY.md > 「U23 起：部署後再跑一次遷移腳本」第 2 步；backend/scripts/run_meta_schema_migration.py:70-72,521-527 | 新引入。第 2 步要在 backend 容器內執行遷移腳本，但腳本以 REPO_ROOT = BACKEND_DIR.parent 讀 schema_rbac.sql。容器內腳本在 /app/scripts，BACKEND_DIR 為 /app，REPO_ROOT 為 /，SCHEMA_FILE 為 /schema_rbac.sql。backend 映像的 build context 是 backend 目錄（deploy/docker-compose.deploy.yml:81），Dockerfile 只 COPY 該目錄，compose 只把 schema_rbac.sql 掛給 db 服務（:55），backend 服務沒有掛載。因此照文件執行會在 read_text 拋 FileNotFoundError，被 :524 捕捉後 exit 1，索引不會建出。code-summary Step 1 複驗只查了 WORKDIR、COPY 與 .dockerignore，沒查腳本自己對 schema_rbac.sql 的依賴；使用者裁決的容器內形式因此在 staging 無法完成，而這是索引到達既有資料庫的唯一路徑 | 擇一：(a) 步驟改為先把 schema_rbac.sql 以 docker cp 或唯讀掛載放進容器的 /schema_rbac.sql 再執行；(b) 讓腳本接受環境變數或參數指定 SCHEMA_FILE；(c) 改用 docker exec 對 db 容器直接執行單行 CREATE INDEX IF NOT EXISTS。無論哪種，要在 staging 主機實際走過一次，並更正 code-summary 十三節與 Step 1 複驗表 | Resolved (reviewer) |
| R-02 | Major | frontend/src/components/projects/RequirementsTab.tsx:67-69,206 與 frontend/src/pages/ProjectDetailPage.tsx（只渲染目前籤，active 為 requirements 時才掛載）；code-summary 偏離 D-7 | 新設計問題。drafts、fieldErrors、savedStale 都是 RequirementsTab 的本地 state，切到總覽或記憶籤即卸載，三者全部遺失。於是儲存失敗後留在畫面上的輸入值與「未儲存」標記、重讀失敗時刻意保留的草稿（BR84.5、BR85.6、frontend-components 第 97-100 行「失敗欄位的草稿保留」），只要使用者去總覽看一眼未填計數再回來就消失，正是 AC11.2.3「我輸入的值不消失」要防的結果。e2e 的 F5、F7、F8 只涵蓋同籤內重讀，沒有切籤再回來的案例；D-7 把它列為殘留但沒有對照 BR84.5 評估 | 把 drafts、fieldErrors、savedStale 提升到 ProjectDetailPage，或讓需求籤保持掛載（切籤時以 hidden 隱藏），並補一個 e2e：儲存失敗後切到總覽再切回，輸入值與「未儲存」仍在；補對應突變 | Resolved (reviewer) |
| R-03 | Minor | backend/services/hierarchy_facade.py:259-275,297,328（create_system、delete_project、delete_system） | 新設計問題。守門之後仍保留 owner_user_id 檢查，所以被移出的建立者（owner_user_id 仍是他）無法通過守門，其餘成員（含 project_admin）又不是 owner，沒有任何人能再對該專案建立或刪除系統，也不能刪專案；SystemCreateAction 也只對 owner 渲染。這是使用者 R-01 裁決的直接後果，但 code-summary 十二節第 9 項的殘留清單沒有列出這個死結 | 在殘留與核可關卡揭露事項補上「建立者被移出後該專案無人能新增系統或刪除」，並指定後續承接（例如移出時同步移轉 owner_user_id，或改以成員角色判定寫入） | Resolved (reviewer) |
| R-04 | Minor | frontend/src/pages/ProjectDetailPage.tsx（useEffect 開頭的 Number.isFinite(projectId) 判斷） | 新引入。網址為非數字（例如 /projects/abc）時 effect 直接 return，status 永遠停在 loading，畫面持續顯示「正在載入專案」，與 BR83.4 的 not-found 態不一致 | 非有限數字時直接進 not-found 態，並補一個 e2e | Resolved (reviewer) |
| R-05 | Minor | code-summary.md 五節「附帶觀察」與十一節第 3 項 | 既存漏審。dev 模式下 member-pages 與 memory-page 兩支 spec 變紅，歸因 StrictMode 但「未驗證是否在 HEAD 既存」。git diff 顯示本單元對前端只動 App.tsx 與 Sidebar.tsx，沒有碰共用程式，推論可信，但仍是未驗證的歸因 | 在 build-and-test 以 HEAD 乾淨 checkout 在 dev server 跑一次那兩支 spec 並記錄結果 | Resolved (reviewer) |
| R-06 | Minor | backend/services/requirement_field_errors.py > class RequirementFieldForbidden 的 docstring（第 44-52 行） | docstring 仍寫「`reason` 為 `pending`／`global`／`not_member`」並說對外訊息不區分三者，但 `[PP-MB14]`=A 之後 `not_member` 已不再丟 `RequirementFieldForbidden`：`requirement_field_facade._authorize` 只對非成員呼叫 `_log_denied(..., "not_member")` 再丟 `RequirementFieldNotFound`，`_deny` 只剩 `pending`／`global` 兩種。下一位讀者會誤以為非成員仍走 403，與同檔 `NOT_FOUND_DETAIL` 的說明矛盾。 | 把 docstring 的 reason 清單改為 `pending`／`global`，並註明 `not_member` 只是拒絕 log 的 `reason` 值、對外是 404（`RequirementFieldNotFound`）。 | Resolved (reviewer) |
| R-07 | Minor | frontend/src/membership/membershipApi.ts > `inviteMember`／`removeMember`／`changeMemberRole` 的錯誤分支 | 只有 `fetchMembers` 對 404 丟 `ProjectNotFoundError` 並顯示固定句「查不到這個專案」。三個寫入函式遇到 404（中途被移出、專案被刪）會落入通用 `Error`，顯示伺服器的「查不到專案」。畫面不洩漏專案編號，行為也與原 403 的 `handleForbidden` 相近（顯示錯誤、關閉確認框），所以不構成缺陷，只是同一情境在清單頁與寫入對話框用字不同。e2e 也只覆蓋清單／詳情載入的 404，沒有寫入路徑的 404。 | 寫入三函式對 404 也丟 `ProjectNotFoundError`，或在 `code-summary.md` 的殘留清單記明「寫入路徑 404 文字沿用伺服器句」。 | Resolved (reviewer) |
| R-08 | Minor | backend/services/hierarchy_service.py > assert_project_owned_by（第 73-77 行）；aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/code-generation/code-summary.md > 重做段「突變抽驗」；backend/tests/test_project_write_guard.py > test_d_create_system_member_not_owner_404、test_d_delete_project_member_not_owner_404、test_d_delete_system_member_not_owner_404 | 重做段記錄的存活突變，我在 scratchpad 副本獨立重現：把 `assert_project_owned_by` 的訊息改回 `f"查不到專案 {project_id}"` 後，write_guard、visibility_endpoints、hierarchy_service、visibility_static 共 79 案仍全綠（唯一的 error 是副本缺 repo 根目錄的 schema_rbac.sql，與突變無關）。判定：它不構成存在性探測。守門在 facade 第 3 步先擋非成員，只有「可見但非擁有者」的成員才會走到這個訊息，而他請求的就是自己可見專案的 id；`delete_system` 帶出的是他本就看得到的所屬專案 id。真正的缺口是測試強度：d 組三案只斷言狀態碼 404、不斷言 `detail`，g 組逐位元比較又只覆蓋「被移出者」走守門的路徑，所以守門之後的固定訊息沒有任何斷言保護。計畫 §五 對 N1 的字面敘述（任一處改回帶 id 即該路徑的逐位元比較案變紅）因此過強。 | 在 d 組三案各補 `assertEqual(response.json(), {"detail": "查不到專案"})`（`delete_system` 為專案句），把守門後的訊息固定下來；並更正 code-summary 或計畫對 N1 的說法，改成「守門前路徑受逐位元比較保護，守門後路徑受 d 組訊息斷言保護」。 | Unresolved |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/code-generation/code-summary.md > 十二節第 1 項（級聯刪除）；backend/services/hierarchy_facade.py > delete_project（第 308-316 行） | 揭露事項寫「仍是成員的擁有者觸發級聯刪除是 U7 既有的合法行為」，但沒有點明一個後果：刪除專案的授權只看 `owner_user_id`，不看 per-project 角色。`delete_project` 在可見性守門之後只呼叫 `assert_project_owned_by`，所以只要建立者仍有成員列，不論他現在在專案內是 `project_admin` 還是一般成員，都能刪專案並連帶刪除其他管理者的成員列與全部系統的需求欄位值。我沒有追溯 `change_role` 是否允許把建立者降為一般成員，無法確認這個組合在現行資料流下是否可達，所以只列為揭露缺口，不列為缺陷。 | 在十二節第 1 項補一句「刪除專案與系統只認 `owner_user_id`，不查 per-project 角色」，並在核可關卡請使用者確認接受；若確認建立者可被降為一般成員，則把它連同十一節第 8 項的後續承接一併列入。 | Unresolved |
| R-10 | Minor | 無 | 本輪未發現新的缺陷。獨立複驗結果見下方 Validation Tool Results：44 對 6 的檔案分類、三個後端檔的 hunk 子集重建、兩個前端檔的判定、回歸與勾選數字皆成立。 | 無需動作 | New |

> R-08 Reviewer note: 現況未變。test_project_write_guard.py 第 191-217 行的 test_d 三案仍只斷言 status_code 為 404，沒有斷言 detail；hierarchy_service.py 第 73-77 行 assert_project_owned_by 仍丟固定常數 PROJECT_NOT_FOUND_DETAIL。守門之後的固定訊息仍無測試保護。使用者 2026-10-26 已裁決只記 Minor、不列合併前必修，本輪如實維持 Unresolved，不影響裁決。

> R-09 Reviewer note: 現況未變。code-summary.md 十二節第 1 項（約第 276 行）仍只寫「仍是成員的擁有者觸發它們是 U7 既有的合法行為」，沒有補上「刪除專案與系統只認 owner_user_id，不查 per-project 角色」。後端風險本身已由 merge-blockers 第 25 列登記（先查可達性），但該列 (d) 要求同步的十二節揭露文字尚未落地，核可關卡看不到這句話。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 收據 reviewed-source-6bd395cc48d7.tsv 逐檔 shasum -a 256（50 檔） | 44 檔相同，6 檔不同，分別為 DEPLOY.md、requirement_field_errors.py、requirement_field_facade.py、test_requirement_field_http.py、MembersListPage.tsx、member-pages.spec.ts | 與 code-summary 一節完全一致。membershipApi.ts、hierarchy_facade.py、hierarchy_service.py、membership_facade.py、本單元的可見性與寫入守門測試檔皆在相同的 44 檔內，可見性過濾、15 處 ALWAYS_VISIBLE 補丁、階層端點 404 收斂不受影響 |
| 獨立重建 hunk 子集（difflib 枚舉，7a50a40~1 到 7a50a40） | requirement_field_errors.py 9 取 7 相符，requirement_field_facade.py 8 取 7 相符，DEPLOY.md 19 取 16 相符 | 雜湊相符即為子集的決定性證據。排除的 hunk 為 NUL 欄位固定訊息（errors 第 15、130-132 行）、write 入口擋 NUL（facade 第 374-380 行，位在 _authorize 之後，不影響非成員 404 收斂）、DEPLOY.md 第 730-738、2229、2239 行，皆非本單元段落 |
| 兩個前端檔的子集重建 | 我自行以「7a50a40~1 加 stub 兩處加本單元三案」嘗試，雜湊不符，與開發者敘述一致 | 確實無法證明為子集，開發者如實揭露。補強證據成立：MembersListPage.tsx 整段 diff 逐行讀過，catch 區塊（第 84-89 行）與 404 文案來源未動，後續改動只涉及分頁、非數字 projectId、焦點與註解；membershipApi.ts 第 91 行 PROJECT_NOT_FOUND_MESSAGE 在相同的 44 檔內 |
| 三案存活性突變（副本內把 PROJECT_NOT_FOUND_MESSAGE 改成含專案編號的句子後重建並跑 member-pages） | 第 801、855 行的兩案紅，另兩個非數字網址案也紅；第 838 行的 403 案維持綠 | 證明三案對現行的 MembersListPage.tsx 與 membershipApi.ts 組合仍然有效，不是恆真；403 案綠符合預期（它檢查權限句而非 404 句） |
| 副本回歸：11 模組合跑 | Ran 183 tests，OK | 與 code-summary 二節相同 |
| 副本回歸：六模組（含 test_requirement_field_http） | Ran 82 tests，OK | 相同 |
| 副本回歸：unittest discover 全套 | Ran 1326 tests，OK（skipped=3），約 98 秒 | 相同 |
| dump_openapi.py --check | 規格檔與後端程式碼一致 | 相同 |
| e2e：副本生產建置（vite preview）跑 project-pages.spec.ts 加 member-pages.spec.ts | 43 passed | 相同；member-pages 的 describe 內 test 數 20、project-pages 23，與 code-summary 敘述吻合 |
| 計畫勾選實算（grep -c） | 已勾 52，未勾 0 | 與 code-summary 四節相同；47 既有加 5 本節。勾選的證據鏈（相同檔、重驗、hunk 重建、讀 diff 加 e2e）皆已獨立複驗，非空勾 |

### Summary

本輪的重新驗證站得住：44 對 6 的分類可由雜湊複驗，三個後端檔以獨立的 hunk 子集重建證明收據之後的改動只是第 24 項的 NUL 增補與非本單元的 DEPLOY.md 段落；兩個前端檔無法證明為子集，但逐行重讀加副本實跑 43 案加我自行做的突變都顯示本單元三案仍然有效。前輪兩項 Minor（R-08 測試強度、R-09 十二節揭露）仍未處理，且皆已有使用者裁決或 merge-blockers 第 25 列承接，不阻擋 READY。
