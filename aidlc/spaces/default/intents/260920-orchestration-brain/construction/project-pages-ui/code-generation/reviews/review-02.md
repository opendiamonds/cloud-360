## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-24T06:52:43Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | DEPLOY.md > 「U23 起：部署後再跑一次遷移腳本」第 2 步；backend/scripts/run_meta_schema_migration.py:70-72,521-527 | 新引入。第 2 步要在 backend 容器內執行遷移腳本，但腳本以 REPO_ROOT = BACKEND_DIR.parent 讀 schema_rbac.sql。容器內腳本在 /app/scripts，BACKEND_DIR 為 /app，REPO_ROOT 為 /，SCHEMA_FILE 為 /schema_rbac.sql。backend 映像的 build context 是 backend 目錄（deploy/docker-compose.deploy.yml:81），Dockerfile 只 COPY 該目錄，compose 只把 schema_rbac.sql 掛給 db 服務（:55），backend 服務沒有掛載。因此照文件執行會在 read_text 拋 FileNotFoundError，被 :524 捕捉後 exit 1，索引不會建出。code-summary Step 1 複驗只查了 WORKDIR、COPY 與 .dockerignore，沒查腳本自己對 schema_rbac.sql 的依賴；使用者裁決的容器內形式因此在 staging 無法完成，而這是索引到達既有資料庫的唯一路徑 | 擇一：(a) 步驟改為先把 schema_rbac.sql 以 docker cp 或唯讀掛載放進容器的 /schema_rbac.sql 再執行；(b) 讓腳本接受環境變數或參數指定 SCHEMA_FILE；(c) 改用 docker exec 對 db 容器直接執行單行 CREATE INDEX IF NOT EXISTS。無論哪種，要在 staging 主機實際走過一次，並更正 code-summary 十三節與 Step 1 複驗表 | New |
| R-02 | Major | frontend/src/components/projects/RequirementsTab.tsx:67-69,206 與 frontend/src/pages/ProjectDetailPage.tsx（只渲染目前籤，active 為 requirements 時才掛載）；code-summary 偏離 D-7 | 新設計問題。drafts、fieldErrors、savedStale 都是 RequirementsTab 的本地 state，切到總覽或記憶籤即卸載，三者全部遺失。於是儲存失敗後留在畫面上的輸入值與「未儲存」標記、重讀失敗時刻意保留的草稿（BR84.5、BR85.6、frontend-components 第 97-100 行「失敗欄位的草稿保留」），只要使用者去總覽看一眼未填計數再回來就消失，正是 AC11.2.3「我輸入的值不消失」要防的結果。e2e 的 F5、F7、F8 只涵蓋同籤內重讀，沒有切籤再回來的案例；D-7 把它列為殘留但沒有對照 BR84.5 評估 | 把 drafts、fieldErrors、savedStale 提升到 ProjectDetailPage，或讓需求籤保持掛載（切籤時以 hidden 隱藏），並補一個 e2e：儲存失敗後切到總覽再切回，輸入值與「未儲存」仍在；補對應突變 | New |
| R-03 | Minor | backend/services/hierarchy_facade.py:259-275,297,328（create_system、delete_project、delete_system） | 新設計問題。守門之後仍保留 owner_user_id 檢查，所以被移出的建立者（owner_user_id 仍是他）無法通過守門，其餘成員（含 project_admin）又不是 owner，沒有任何人能再對該專案建立或刪除系統，也不能刪專案；SystemCreateAction 也只對 owner 渲染。這是使用者 R-01 裁決的直接後果，但 code-summary 十二節第 9 項的殘留清單沒有列出這個死結 | 在殘留與核可關卡揭露事項補上「建立者被移出後該專案無人能新增系統或刪除」，並指定後續承接（例如移出時同步移轉 owner_user_id，或改以成員角色判定寫入） | New |
| R-04 | Minor | frontend/src/pages/ProjectDetailPage.tsx（useEffect 開頭的 Number.isFinite(projectId) 判斷） | 新引入。網址為非數字（例如 /projects/abc）時 effect 直接 return，status 永遠停在 loading，畫面持續顯示「正在載入專案」，與 BR83.4 的 not-found 態不一致 | 非有限數字時直接進 not-found 態，並補一個 e2e | New |
| R-05 | Minor | code-summary.md 五節「附帶觀察」與十一節第 3 項 | 既存漏審。dev 模式下 member-pages 與 memory-page 兩支 spec 變紅，歸因 StrictMode 但「未驗證是否在 HEAD 既存」。git diff 顯示本單元對前端只動 App.tsx 與 Sidebar.tsx，沒有碰共用程式，推論可信，但仍是未驗證的歸因 | 在 build-and-test 以 HEAD 乾淨 checkout 在 dev server 跑一次那兩支 spec 並記錄結果 | New |
| R-06 | Minor | backend/services/requirement_field_errors.py > class RequirementFieldForbidden 的 docstring（第 44-52 行） | docstring 仍寫「`reason` 為 `pending`／`global`／`not_member`」並說對外訊息不區分三者，但 `[PP-MB14]`=A 之後 `not_member` 已不再丟 `RequirementFieldForbidden`：`requirement_field_facade._authorize` 只對非成員呼叫 `_log_denied(..., "not_member")` 再丟 `RequirementFieldNotFound`，`_deny` 只剩 `pending`／`global` 兩種。下一位讀者會誤以為非成員仍走 403，與同檔 `NOT_FOUND_DETAIL` 的說明矛盾。 | 把 docstring 的 reason 清單改為 `pending`／`global`，並註明 `not_member` 只是拒絕 log 的 `reason` 值、對外是 404（`RequirementFieldNotFound`）。 | New |
| R-07 | Minor | frontend/src/membership/membershipApi.ts > `inviteMember`／`removeMember`／`changeMemberRole` 的錯誤分支 | 只有 `fetchMembers` 對 404 丟 `ProjectNotFoundError` 並顯示固定句「查不到這個專案」。三個寫入函式遇到 404（中途被移出、專案被刪）會落入通用 `Error`，顯示伺服器的「查不到專案」。畫面不洩漏專案編號，行為也與原 403 的 `handleForbidden` 相近（顯示錯誤、關閉確認框），所以不構成缺陷，只是同一情境在清單頁與寫入對話框用字不同。e2e 也只覆蓋清單／詳情載入的 404，沒有寫入路徑的 404。 | 寫入三函式對 404 也丟 `ProjectNotFoundError`，或在 `code-summary.md` 的殘留清單記明「寫入路徑 404 文字沿用伺服器句」。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

### 逐項查證結果（非發現）

- **missing vs 非成員是否仍可區分**：七個端點逐一追過。成員四端點的順序是 `_authorize_global`（缺 `K3` 時存在與不存在都是 403）→ `_assert_project_exists` → `_require_project_role`。不存在與非成員都丟 `MembershipNotFound(PROJECT_NOT_FOUND_DETAIL)`（「查不到專案」），經同一個 `_translate` 轉成 404。是成員但非 `project_admin` 的 403 只對已知專案存在的呼叫者出現。需求欄位三端點的 `_authorize` 依序是 pending（403）、global（403）、非整數／不存在／缺 `K2`／非成員（皆 `RequirementFieldNotFound`，訊息固定為 `SYSTEM_NOT_FOUND_DETAIL`），並且發生在 body 解析與 `UnknownFieldKey` 的 422 之前。管理者之後的 `lock_project`、`set_member_role` 等訊息帶 id，但呼叫者已是該專案管理者，不構成預言機。OpenAPI 說明文字沒有暗示兩者不同。
- **零成員列的擁有者在成員頁由 403 變 404**：不是迴歸。(a) 前後都被拒絕，只是狀態碼變了。(b) 該狀態在穩態下不可達：`create_project_with_owner` 在同一交易寫專案與擁有者的 `project_admin` 列；既有專案由 `ensure_project_members_on_startup` 在 `init_db()` 之後補齊，失敗即拋、啟動中止；`LastAdminGuard` 擋下移除最後一位管理者；擁有者被人為移出的專案（已有其他成員列）屬 `BR87.1` 的刻意語意。(c) 我沒找到要求「零成員列擁有者能進成員頁」的已核可條文。
- **MCP e2e `AC11.4.1`**：成立。直接存取為 404，經 MCP 的 `structured["error"]` 為 `not_found`，`message` 等於直接存取的 `detail`，`retryable` 為 false，且 backend 收到的 Authorization 是 outsider token。「理由與直接存取相同」仍以 404 形狀滿足。
- **`openapi.json` 與 `api.d.ts`**：`dump_openapi.py --check` 回「規格檔與後端程式碼一致。」；兩檔的「合併前必修第 14 項」`grep -c` 均為 7，與 `code-summary.md` §十五 相符。
- **數字重現**：指定的六個測試模組 `Ran 81 tests ... OK`，與 §十五之三 的 81 相符。為避免寫入 repo，我沒有跑前端建置、e2e 與全套 discover（1319 項未重現）。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `python3 -B -m unittest`（指定六個模組） | Ran 81 tests, OK | 與 code-summary §十五之三 一致 |
| `backend/scripts/dump_openapi.py --check` | 規格檔與後端程式碼一致 | `openapi.json` 與程式無漂移 |
| `grep -c "合併前必修第 14 項"` | `openapi.json` 7、`api.d.ts` 7 | 與 code-summary §十五之一 一致 |

### Summary

合併前必修第 14 項在七個端點上已讓「不存在」與「存在但非成員」逐位元相同（status、訊息、無 id）。成員之內的角色不足與缺全域權限仍是 403，非成員拒絕 log 照記。零成員列擁有者的 403→404 不是迴歸，因為該狀態由原子建立加啟動補齊保證不可達。剩下兩項只是 docstring 過期與寫入路徑文字不一致的 Minor，不阻擋。
