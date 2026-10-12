## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

本站對上一站 review-01 的設計層發現（R-01、R-02、R-03、R-04、R-06、R-07、R-08）大多吸收正確：九列矩陣與 rbac_seed_data.py:349-359 的 K4 種子逐列相符（Developer 僅 view、SRE 無 view、Project_Editor 有 edit），列 ⑤ 與 ⑧ 的結論和 BR41.2 先於 BR41.3、BR41.4 的順序一致；條件式 UPDATE ... WHERE value IS NOT NULL 在 PostgreSQL READ COMMITTED 下第二個併發清空會重評 WHERE 而得 0 列，推論成立；DO 區塊以 information_schema 與 pg_constraint 的 conkey 為條件、避開 FORBIDDEN_FKS，方向正確。未發現 Critical。有兩項 Major：其一是「僅掛在本 router 的錯誤形狀處置」在 FastAPI 沒有對應機制，產出沒有指名可行做法，開發者必須猜；其二是 CI 的 A–D 步驟只走 psql 路徑，沒有執行 run_meta_schema_migration.py，而 NFR20.25 的欄位級後條件與 DO 區塊經 psycopg 執行的行為正是該腳本才有，另外 C/D 的 fixture 與清理未定。其餘為 Minor。兩項 Major 未超過 2，故為 READY，建議 code-generation 開工前先補 R-01、R-02。

### Findings

| ID | Severity | Location | Finding | Status |
|---|---|---|---|---|
| R-01 | Major | nfr-design/security-design.md 第五節；logical-components.md 的 requirement_field_router 列 | 【證據】第五節宣稱「領域例外由本 router 的 handler 轉成…」與「框架驗證錯誤以僅掛在本 router 的處置轉成同一形狀」，卻沒說機制。我在本機 FastAPI 0.111.0 實測 APIRouter.__init__ 的參數（prefix、tags、dependencies、responses、route_class、lifespan 等），沒有 exception_handlers；repo 內 main.py 也沒有任何全域 handler，現有 membership_router／hierarchy_router 用的是每個路由 try/except 加 _translate 回 HTTPException(detail=str)。因此「僅掛 router」只剩兩條可行路：自訂 route_class 覆寫 get_route_handler 並捕捉 RequestValidationError，或在 app 層以領域例外型別註冊 handler。開發者若找不到，最順手的做法是 app.add_exception_handler(RequestValidationError)，那正是產出明言不得做的全域改動（會改變其他端點的 422）。三個衍生問題也沒處理：(1) 框架的本體／路徑驗證在 handler 本體之前執行，故待核准或無權限者送壞本體會得到 422 而非 403，BR41.5（授權先於任何驗證）與 BR41.6 的拒絕 log 在這條路徑上失效，產出需明說這是已知順序例外或調整；(2) route decorator 的 responses 若不宣告 422 的 model，openapi.json 與 api.d.ts 仍是預設 HTTPValidationError，與實際回應形狀不符，U23 的「只處理一種 422 形狀」在型別層不成立，而 CI 漂移閘門抓不到這種不符；(3) 本 router 的 detail 為 dict（code、system_id…），與現有兩個 router 的 detail 為字串不同，U23 與 U21 要知道。 | New |
| R-02 | Major | nfr-design/reliability-design.md 第三節（驗證 A–D 與後條件段） | 【證據】A–D 全部用 psql -f schema_rbac.sql。但 DEPLOY.md 與腳本 docstring 都寫明既有環境的唯一路徑是 run_meta_schema_migration.py，而 NFR20.25 的欄位級後條件、以及 DO 區塊經 psycopg cursor.execute 整段送出的行為，只存在於該腳本；memory-schema job 沒有 pip install，所以新增的後條件程式碼在 CI 完全不被執行（functional-design review-02 R-02 的同一缺口，僅換了落點）。另外 C／D 有三處未定：(1) schema_rbac.sql 自帶 BEGIN／COMMIT，而 verify_meta_schema.sql 結尾是 ROLLBACK，C 的 fixture 必須先 commit 才能被 D 的重套用看到，須新建含 users、projects、systems 與一列 system_requirement_fields 的 committed fixture；(2) 重套用 schema_rbac.sql 會 DELETE 後重播 role_permissions，且 H) 區塊若含回填會替新 fixture 使用者建預設專案，fixture 的清理順序（projects.owner_user_id 與 project_members.user_id 無 ON DELETE）沒有寫；(3) A–D 放在 job 的哪個位置沒有指定，放在 P1–P12 與 R1–R10 之前會讓這些斷言面對一個含 committed 列的資料庫。【建議】在 concurrency job（已有 pip install 與真實 PostgreSQL）或 memory-schema 加 setup-python 步驟，讓 A 之後的收斂改走 run_meta_schema_migration.py 並斷言其結束碼與對「未收斂」狀態的非零結束（突變：拿掉後條件時應變紅）；寫明 fixture 的建立、清理順序與步驟位置（建議放在 R1–R10 之後）。 | New |
| R-03 | Minor | nfr-design/security-design.md 第二節（九列矩陣） | 矩陣仍有三個測不到的真實錯誤實作：(1) 列 ② 的「非成員」若用完全沒有任何成員身分的使用者，則把 BR41.4 寫成「該使用者是否為任何專案的成員」或誤用使用者預設專案 id 查成員，列 ② 仍全綠；應規定 ② 的使用者是「另一個專案的成員」，目標系統屬於他不是成員的專案；(2) 沒有「project_admin 且有 K4.edit」的正向寫入列（列 ⑤ 只測 project_admin 被全域層擋下），把 BR41.4 寫成只放行 member 的突變不會變紅，review-01 R-01 建議的 project_admin／member 各一例也沒落實；(3) 沒有 Platform_Admin 非成員列，它是最高權限全域角色，BR41.4 沒有 bypass，這是刻意的就該用一列鎖住，否則日後有人加 admin 繞過不會有測試紅燈。另外列 ② 與 ⑦ 並陳，等於寫明有 K4 權限者可由 403／404 差異枚舉 system id 是否存在；BR41.3 的 note 已揭露，但 security-design 的 STRIDE 式說明未承接。 | New |
| R-04 | Minor | nfr-design/performance-design.md 第二節（SQL 表：cleared_at = now()、updated_at = now()） | 依方言用 now() 會讓 BR43.4／NFR20.22／BR45.5 的「no-op 不更新 cleared_at、updated_at」測試在 SQLite 無法變紅：SQLAlchemy 的 func.now() 在 SQLite 編成 CURRENT_TIMESTAMP，解析度為秒，同一秒內「不該更新」與「更新成同值」不可分辨，project.md 的突變驗證要求（把修正改回錯的行為、測試必須紅）因此做不到；PostgreSQL 的 now() 又是交易起始時間，同一交易內多次呼叫相同。【建議】時間戳由 Python 端以可注入的時鐘取值並當綁定參數傳入兩種方言；測試則先直接插入帶固定舊時間的列，再呼叫清空並斷言欄位不變。 | New |
| R-05 | Minor | nfr-design/reliability-design.md 第三節；security-design.md 第七節 | 部署順序未寫。deploy.yml 在合併後自動部署新後端，但 run_meta_schema_migration.py 是手動步驟（deploy.yml 與 deploy/ 皆無引用，DEPLOY.md 約 764 行的順序表只到 U19）。在手動收斂之前，任何帶 on_behalf_of 的寫入對仍為 integer 的欄位會得 PostgreSQL 的型別錯誤而回 500；目前尚無 U13／U21 呼叫者，所以影響有限，但這是已知可預見的失敗，應在 DEPLOY.md 2.2.9 的順序表新增一列（先收斂、後上線），並承接 functional-spec 的 OPEN-RF20-8（腳本輸出與 DEPLOY.md 須如實描述它不再是純 DDL；腳本結尾仍印「不塞任何資料」）。nfr-design 的 0 題文件沒有帶入 OPEN-RF20-8。 | New |
| R-06 | Minor | nfr-design/reliability-design.md 第三節（收斂敘述步驟 1–3）；logical-components.md 第三節（爆炸半徑） | DO 區塊細節有四個可補強處：(1) 步驟 2 的 DROP CONSTRAINT 在 PostgreSQL 會同時對被參照的 users 表取 ACCESS EXCLUSIVE 鎖，並持有到整個遷移交易結束，爆炸半徑表只寫了本表，漏掉 users（所有登入都碰它）；若有閒置交易持鎖，等待中的鎖請求還會讓後續查詢排隊，建議區塊內先 SET LOCAL lock_timeout，逾時大聲失敗；(2) 步驟 3 的 USING NULL 對任何非 NULL 值是靜默丟棄，而這條路徑的原則是大聲失敗（NFR20.25），建議存在非 NULL 值時 RAISE EXCEPTION 而不是清掉；(3) information_schema 與 pg_constraint 的查詢應限定 table_schema = current_schema() 與表名，並以 to_regclass 取表，避免同名表誤判；(4) 「首次收斂時表內無代寫值、鎖時間可忽略」成立的前提是沒有人手動寫過，應寫成區塊內的檢查而非假設。 | New |
| R-07 | Minor | nfr-design/reliability-design.md 第一節（測試：另一個 session 重讀）；performance-design.md 第二節（依 session.bind 選方言） | 兩處測試細節與 repo 現況不符：(1) 理由寫「同一個 session 會看到自己未提交的變更，驗不出回滾」，但 tests/helpers.py 用 StaticPool，所有 session 共用同一條 SQLite 連線，另一個 session 同樣看得到未提交內容，所以「換 session」並不提供隔離，測試能否變紅取決於實作是否真的呼叫 rollback，而不是 session 隔離；請把理由改成「斷言 rollback 被呼叫並且重讀值不變」；(2) 以 session.bind.dialect.name 選方言，session 以 get_db 覆寫或非 bind 方式建立時 session.bind 可能是 None，改用 session.get_bind().dialect.name。另外 RETURNING 守衛測試（SQLite 版本不足時明確失敗）設計得好，建議一併把 sqlite3.sqlite_version 印進失敗訊息。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 本機 FastAPI 0.111.0 的 APIRouter.__init__ 簽名檢視（唯讀） | 無 exception_handlers 參數，僅 route_class 可作 router 範圍攔截 | 支撐 R-01；repo 釘選的 0.141.1 未能安裝比對，結論以 FastAPI 一貫設計為據，code-generation 須實測 |
| rbac_seed_data.py:349-359 對 K4 列 | Developer、FinOps_Analyst、Security_Reviewer、Platform_Owner 僅 view；Project_Architect、Project_Editor、Project_Admin、Platform_Admin 有 view 與 edit；SRE、Ops_Lead、Platform_Engineer 皆無 | 九列矩陣的角色舉例全部正確 |
| run_meta_schema_migration.py 讀碼 | 以 DBAPI cursor 整段 execute 區塊；後條件目前無欄位級檢查；FORBIDDEN_FKS 以（表，被參照表）為鍵 | DO 區塊可原樣送出；本站不使用 FORBIDDEN_FKS 的決定正確；後條件新增部分在 CI 不被執行（R-02） |
| verify_meta_schema.sql 讀碼 | 行為斷言包在交易內並以 ROLLBACK 結尾 | 不留 committed 列，A–D 需自帶 fixture（R-02） |
| ci.yml memory-schema job 讀碼 | 已套用 schema_rbac.sql 兩次，無 Python 步驟 | A–D 可加在此 job，但只能走 psql（R-02） |

### Summary

設計方向正確且大半吸收了上游審查：矩陣、單一敘述加 RETURNING、條件式清空、條件式收斂都站得住。需要在開工前補齊的是兩處「描述了目標卻沒給可行機制或驗證載體」：router 範圍的錯誤形狀處置（FastAPI 的 APIRouter 沒有 exception_handlers，須指名 route_class 或等價做法，並處理 422 先於授權與 openapi 宣告）、以及把收斂驗證延伸到 run_meta_schema_migration.py 並寫清 fixture 與清理。
