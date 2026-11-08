## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-08 | Still applies | Minor | backend/tests/test_project_write_guard.py 的 test_d 三案（約第 200-217 行）仍只斷言狀態碼 404、不斷言 detail；hierarchy_service.py 第 73 行起的 assert_project_owned_by 仍丟固定句。使用者 2026-10-26 裁決（只記 Minor、不修）仍有效，本輪維持不修是合規的，不另升級。 |
| R-09 | Fixed | Minor | 揭露缺口已補：code-summary 十二節第 1 項之後的區塊級補記（約第 278 行）點明原本只認 owner_user_id、不查 per-project 角色，原文未動。可達性結論我獨立讀碼確認仍成立：membership_facade.change_role（第 348 行起）只對呼叫者要求管理者，目標可為擁有者；第 21 列改動的 projects_losing_last_admin（membership_service.py 第 657 行）只被停用路徑呼叫，不在 change_role 路徑上。 |
| R-10 | Fixed | Minor | 原列只是「無新缺陷」的記錄，無待辦。其基準（44 對 6）已被本輪收據更新取代。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/code-generation/code-summary.md > 本輪新節「一、Step 21」的「收據比對」段、「三、Step 23」的「前端」段、「四、勾選重設」第一項 | 新節宣稱「最新收據 reviewed-source-7bd6cf134ce2.tsv 的 50 檔逐位元相同、0 檔變動」「收據內 21 個前端檔逐位元相同」「frontend/ 下沒有比收據新的原始檔」，並以此作為前端各格（lint、check:types、tsc -b、vite build、e2e）未重跑仍維持勾選的唯一理由。我對該收據 50 檔逐檔 shasum -a 256，結果是 15 檔不同：DEPLOY.md、run_meta_schema_migration.py、hierarchy_facade.py、hierarchy_router.py、membership_facade.py、membership_service.py、五個後端測試檔、openapi.json、schema_rbac.sql，以及兩個前端檔 frontend/src/components/Sidebar.tsx（2026-11-01 01:21 改，新增 aria-label，第 35 列 (c)）與 frontend/src/types/api.d.ts（2026-11-07 改，新增 503 回應與描述）。這兩個檔的 mtime 都晚於該收據（2026-10-31 21:42），所以 find -newer 的說法也不成立。目錄內另有較新的收據 reviewed-source-225da72b9a44.tsv（2026-11-08 10:56，晚於 code-summary 寫入時間），現行樹與它 50 檔全部相同。也就是說紀錄比對的是已過期的收據，結論寫反了。實質風險小（Sidebar 只加一個 aria-label，api.d.ts 是產生檔的描述與 503 條目），但前端格的勾選依據是不實陳述，而前端驗證本輪確實沒跑。 | 更正新節三處說法：改以最新收據 225da72b9a44 比對（現況 50 檔相同），並如實寫出相對 7bd6cf134ce2 有 15 檔變動、其中前端兩檔是 Sidebar.tsx 的 aria-label 與 api.d.ts 的產生內容；前端各格要嘛實際重跑 lint／check:types／tsc／e2e，要嘛在勾選處明寫「前端兩檔自上次驗證後改過、本輪未重驗、由 CI 的 ui-regression 承擔」，不得再寫成逐位元相同。 |
| Minor | backend/services/membership_service.py > can_administer_project 第 447-451 行（有成員列即回 False 的分支） | 這個分支在刪除路徑上不可達：可見集合的擁有者那一半只在零成員列時成立（_visible_project_ids_select 的 NOT EXISTS），擁有者若已有成員列卻不是成員，會在可見性守門先得 404，走不到 project_admin 判定。新測試四案與 write_guard 的 (c)、(b) 案都碰不到它，把這兩行拿掉測試仍全綠。這是縱深防禦而非缺陷，但 docstring 與 code-summary 把它寫成有測試鎖住。 | 在 docstring 或 code-summary 註明該分支是守門失效時的後備、目前由可見性守門先擋，沒有獨立測試；或補一個直接呼叫 can_administer_project 的單元案（有成員列的非成員擁有者回 False）。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 讀碼：hierarchy_facade.delete_project／delete_system | 第 339／376 行擁有者檢查之後，第 342／379 行判 project_admin，不成立丟 HierarchyProjectAdminRequired（第 101 行，轉 403，固定句第 98 行） | A3 授權修正在位，順序正確：非擁有者仍 404 |
| 讀碼：membership_service.can_administer_project（第 430 行） | 角色非 None 時回 role 是否為 project_admin；無角色時有成員列即 False、否則看擁有者 | 兩支條件與紀錄所述一致；零成員列擁有者等價條件保留符合 2026-11-08 裁決 |
| 讀碼：router 注入 | hierarchy_router.py 第 295、326 行以 MembershipFacade.project_admin_check 注入，第 570 行為閉包 | 與紀錄行號全部相符 |
| 其他刪除路徑 grep | 非測試程式中 delete_project／delete_system 的呼叫只有 hierarchy_router 兩個 handler；hierarchy_service 的刪除函式只被 facade 呼叫，test_project_visibility_static 另有靜態鎖 | 未發現繞過 project_admin 判定的刪除路徑 |
| 讀碼推演：test_project_delete_requires_admin 四案 | 案例 1、2 降級後 403 加資料不變；案例 3 仍為管理者的建立者 204（allow 側）；案例 4 非擁有者管理者 404。拿掉檢查或判定改永真，案例 1、2 紅；判定改永假，案例 3 紅 | 鎖得住，allow／deny 雙向齊全；有成員列但非成員的擁有者分支見 Minor |
| shasum 比對收據 7bd6cf134ce2 | 50 檔中 15 檔不同（含前端兩檔） | 與新節宣稱相反，見 Major |
| shasum 比對收據 225da72b9a44 | 50 檔 0 檔不同 | 現行樹與最新收據一致 |
| git diff 計畫檔 | 只新增 20 行（九之二與九之三兩節），無刪除；全檔已勾 56、未勾 0 | 除新節外內文未變，勾選數字相符 |
| 行號核對 | code-summary 補記與新節所引 hierarchy_facade 98／101／112／342／379、membership_service 430／657／748、membership_facade 348／570、router 295／326 全部相符；A3 紀錄漂移（552 到 570、343 到 342、380 到 379）說明屬實 | 無誤。brain-infra 的 code-summary 第 447 行起因屬他單元、被審查掃描限制擋下，未開啟，A3 紀錄所述僅以現行程式碼驗證 |
| 測試／工具執行 | 依限制未執行任何測試或建置指令 | 回歸數字（134、184、1397）未獨立複驗，僅信紀錄 |

### Summary

第 25 列的授權修正與測試讀碼成立：擁有者檢查之後要求 project_admin，無繞過路徑，降級建立者的可達性結論仍對，揭露補記與行號也準確。唯一實質問題是新節拿已過期的收據宣稱 50 檔逐位元相同，實際有 15 檔不同（含 Sidebar.tsx 與 api.d.ts 兩個前端檔），前端各格的勾選理由因此不實，需更正敘述或補驗；其餘為 Minor，整體可放行。

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

> R-08 Not re-checked this round

> R-09 Not re-checked this round

> R-10 Not re-checked this round
