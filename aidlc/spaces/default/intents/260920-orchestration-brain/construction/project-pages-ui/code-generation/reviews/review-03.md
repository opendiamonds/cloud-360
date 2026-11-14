## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-26T02:52:28Z
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
| R-08 | Minor | backend/services/hierarchy_service.py > assert_project_owned_by（第 73-77 行）；aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/code-generation/code-summary.md > 重做段「突變抽驗」；backend/tests/test_project_write_guard.py > test_d_create_system_member_not_owner_404、test_d_delete_project_member_not_owner_404、test_d_delete_system_member_not_owner_404 | 重做段記錄的存活突變，我在 scratchpad 副本獨立重現：把 `assert_project_owned_by` 的訊息改回 `f"查不到專案 {project_id}"` 後，write_guard、visibility_endpoints、hierarchy_service、visibility_static 共 79 案仍全綠（唯一的 error 是副本缺 repo 根目錄的 schema_rbac.sql，與突變無關）。判定：它不構成存在性探測。守門在 facade 第 3 步先擋非成員，只有「可見但非擁有者」的成員才會走到這個訊息，而他請求的就是自己可見專案的 id；`delete_system` 帶出的是他本就看得到的所屬專案 id。真正的缺口是測試強度：d 組三案只斷言狀態碼 404、不斷言 `detail`，g 組逐位元比較又只覆蓋「被移出者」走守門的路徑，所以守門之後的固定訊息沒有任何斷言保護。計畫 §五 對 N1 的字面敘述（任一處改回帶 id 即該路徑的逐位元比較案變紅）因此過強。 | 在 d 組三案各補 `assertEqual(response.json(), {"detail": "查不到專案"})`（`delete_system` 為專案句），把守門後的訊息固定下來；並更正 code-summary 或計畫對 N1 的說法，改成「守門前路徑受逐位元比較保護，守門後路徑受 d 組訊息斷言保護」。 | New |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/code-generation/code-summary.md > 十二節第 1 項（級聯刪除）；backend/services/hierarchy_facade.py > delete_project（第 308-316 行） | 揭露事項寫「仍是成員的擁有者觸發級聯刪除是 U7 既有的合法行為」，但沒有點明一個後果：刪除專案的授權只看 `owner_user_id`，不看 per-project 角色。`delete_project` 在可見性守門之後只呼叫 `assert_project_owned_by`，所以只要建立者仍有成員列，不論他現在在專案內是 `project_admin` 還是一般成員，都能刪專案並連帶刪除其他管理者的成員列與全部系統的需求欄位值。我沒有追溯 `change_role` 是否允許把建立者降為一般成員，無法確認這個組合在現行資料流下是否可達，所以只列為揭露缺口，不列為缺陷。 | 在十二節第 1 項補一句「刪除專案與系統只認 `owner_user_id`，不查 per-project 角色」，並在核可關卡請使用者確認接受；若確認建立者可被降為一般成員，則把它連同十一節第 8 項的後續承接一併列入。 | New |

> R-01 Reviewer note: DEPLOY.md 的「U23 起」小節第 2 步已改為先 `docker compose -f deploy/docker-compose.deploy.yml cp schema_rbac.sql backend:/schema_rbac.sql`，再 `exec backend python scripts/run_meta_schema_migration.py`，並寫明容器內 `REPO_ROOT` 為 `/` 的原因（DEPLOY.md 第 896-915 行）。我對照 `backend/scripts/run_meta_schema_migration.py:70-72` 與 `backend/Dockerfile`（`WORKDIR /app`、`COPY . .`）確認推論成立。仍屬人工步驟：staging 主機上實走一次尚未做，code-summary 十三節如實列為部署後人工步驟，不影響本單元程式碼的就緒度。

> R-02 Reviewer note: 需求籤的 `selected`、`drafts`、`fieldErrors`、`savedStale` 已上提到 `ProjectDetailPage`（`reqSelected`／`reqDrafts`／`reqErrors`／`reqStale`，以 `RequirementsInputState` 傳入），`RequirementsTab` 只保留 `saving`、`reloading` 兩個暫態。e2e 'keeps unsaved input and failure marks after switching tabs' 存在，我重跑通過。

> R-03 Reviewer note: 「建立者被移出後無人能建立或刪除系統與專案」已寫入 code-summary 十一節第 8 項與十二節第 9 項，並指定兩個後續承接方向。程式行為依使用者裁決不改，符合原要求。

> R-04 Reviewer note: `ProjectDetailPage.tsx` 以渲染時推導 `invalidId = !Number.isInteger(projectId) \|\| projectId <= 0`，為真時直接渲染 `ProjectNotFound`，effect 不發請求。e2e 'renders not-found for a non-numeric project address' 存在，我重跑通過。

> R-05 Reviewer note: code-summary 十四節記錄在乾淨 HEAD worktree 的 dev server 上重跑兩支 spec，失敗案名與本工作樹逐一相同，已確認為既存問題。本輪我以 production build 的 `vite preview` 跑 `project-pages.spec.ts` 與 `member-pages.spec.ts`，37 案全部通過。

> R-06 Reviewer note: `requirement_field_errors.py` 的 `RequirementFieldForbidden` docstring 已改為 `reason` 只有 `pending`／`global`，並註明 `not_member` 只是拒絕 log 的值、對外為 404（`RequirementFieldNotFound`），與 `requirement_field_facade._authorize` 一致。

> R-07 Reviewer note: `membershipApi.ts` 的 `inviteMember`、`removeMember`、`changeMemberRole` 遇到 404 都丟 `ProjectNotFoundError`（第 212、253、290 行附近），與 `fetchMembers` 用字一致。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 後端單元：test_membership_data、test_project_visibility_queries、test_project_visibility_static、test_project_visibility_endpoints、test_project_write_guard、test_membership_endpoints、test_requirement_field_http、test_hierarchy_service、test_membership_facade、test_requirement_field_facade | `Ran 151 tests` → `OK`（3.12 venv，快取導向 scratchpad） | 授權順序、成員範圍列舉、固定 404 訊息、靜態鎖與契約測試在目前工作樹上全綠。 |
| 前端 e2e：`project-pages.spec.ts` ＋ `member-pages.spec.ts`（production build 輸出到 scratchpad，`vite preview`） | `37 passed` | 與 code-summary 重做段宣稱的 23 ＋ 14 相符；R-02、R-04 的新增案例皆在其中。已關閉 preview，repo 內未留下 `pw-report.json`、`junit.xml` 或建置產物。 |
| source-manifest.json 路徑存在性 | 50 筆路徑全部存在 | 無遺漏或幽靈路徑。code-summary 十四節「39 筆」是歷史數字，不影響判定。 |
| code-generation-plan.md 勾選 | 47 已勾、0 未勾 | 與重做段「47／47」相符。 |
| traceability.json | 57 列 coverage 皆為 OK；`upstream_ids` 56 個皆有對應列；目標檔皆存在 | 多出的一列是 `AC12.5.2` 的後端與畫面兩列，重做段已說明為重複列而非缺口。 |
| 突變重現（scratchpad 副本，`assert_project_owned_by` 訊息帶 id） | 相關 79 案全綠（唯一 error 為副本缺根目錄 schema_rbac.sql） | 確認存活，見上方第一個新發現；已丟棄副本，未動 repo 檔案。 |

### Summary

七項前輪發現皆已修復，我逐項對照程式碼、DEPLOY.md 並重跑 151 個後端案例與 37 個 e2e 案例，結果全綠。存活的那道突變不構成存在性探測：守門之後只有已知專案存在的成員才會走到該訊息，缺口是測試強度；另有一項級聯刪除授權只認 `owner_user_id` 的揭露缺口，兩者皆為 Minor，故判定 READY。
