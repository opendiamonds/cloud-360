## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|----|-----|----------|------|
| R-03 | Resolved | Minor | 原缺口是「grant 只給 current_user、無專用角色、無 REVOKE」。現行 schema_rbac.sql 的 I 區塊已建 cloud360_memory（pg_roles 判斷、可重跑）、只授 memory 的 USAGE 與兩表 DML 與序列、撤銷 public 的表／序列／CREATE，並有 COMMENT ON ROLE；COMMENT ON SCHEMA 與 DEPLOY.md 已更正語氣；OPEN-CG5-1 已改寫並加註落地位置與驗證強度。Resolved 僅指文字與程式已到位，真實 PostgreSQL 驗證仍未做（見新發現 N-1）。 |
| R-07 | Still applies | Minor | .github/workflows/ci.yml 第 376 行步驟名仍是 Verify memory schema assertions (S1-S13)，而 verify_memory_schema.sql 現有斷言 id 為 S1、S3 到 S15。A1 在同一檔新增 R0-R3 步驟並改了 P1-P17 的步驟名，卻沒順手處理這一行。 |
| R-08 | Still applies | Minor | code-generation-plan.md 第 168 行仍寫「CI run 40423381616」且已勾選，沒有就地註記該 run id 屬 UI Regression Reporter、實際依據是 push CI run 40423375585。code-summary 2026-11-01 一節也只說該格「對現況已不成立」，未改計畫本文。 |
| R-09 | Resolved | Minor | merge-blockers.md 第 29 列現已逐字寫明「與第 20 列重複登錄」，並指定以第 20 列的描述、裁決與完成條件為準，兩列不再各自有不同的關閉條件。 |
| R-10 | Still applies | Minor | code-summary.md 第 130-131 行六之 4 仍寫「N-2 尚未在真實 CI 上跑過」並指向 OPEN-CG5-2，traceability.json 的 OPEN-CG5-2 也仍是 named-gap。pg18 的 memory-schema job 對 A1 之前的樹已是 success（檔內 2026-10-30 一節已證），但六之 4 沒有加註關閉；新一節把 A1 之後的樹列為未驗，與六之 4 的過期敘述並存，讀者容易混淆是哪一棵樹。 |

### New Findings

| Severity | Location | Finding | Required action |
|----------|----------|---------|-----------------|
| Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-summary.md 與 traceability.json > OPEN-CG5-1 的關閉條件、2026-11-01 回歸 第 2 節 BR1.2 一列 | 兩份紀錄把 OPEN-CG5-1 的關閉條件寫成「R0-R3 在真實 PostgreSQL 綠燈」，BR1.2 一列判為「符合（靜態）」，都沒有說出一個我實測的事實：backend/database.py 的 get_memory_session 在 backend 非測試程式中沒有任何呼叫者（grep 只命中 database.py 自己的定義與註解），而 backend/services/memory_router.py 的各端點仍以 Depends(get_db) 取得擁有者帳號的連線。也就是說角色與 grant 存在，但執行期沒有任何程式以該角色連線，規則 BR1.2 的 violation_behaviour 要擋的「繞過應用層直連資料庫」之外，應用層本身也完全不受這個邊界約束。schema_rbac.sql 的註解有如實講這點（歸屬 memory-service 單元），但本單元自己的關閉條件沒有。R0-R3 即使全綠，OPEN-CG5-1 照字面就可被關閉，而 ADR-0006 的 IAM 面向仍沒有執行期效力。 | 在 code-summary.md、traceability.json 的 OPEN-CG5-1 與 BR1.2 備註中補一句：get_memory_session 目前無非測試呼叫者、記憶端點仍用 get_db；並把關閉條件改為「R0-R3 綠燈，且記憶端點實際改以 get_memory_session 取連線（或明列承接單元與列號）」，不要只以 R0-R3 綠燈為準。 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-summary.md > 2026-11-01 回歸 第 3 節（真實 PostgreSQL 一列） | 外鍵前提「FK 檢查以被參照表擁有者權限執行，所以角色不需任何 public.users 權限」我判斷在 PostgreSQL 成立：寫入側的參照檢查（對 users 做 SELECT 1 ... FOR KEY SHARE）是以被參照表 public.users 的擁有者身分執行的，這是 ri_triggers 的既有行為，子表寫入者不需要對父表有 SELECT。所以 BR1.2「跨 schema 讀取 public.users 所需的最小權限」解讀為零是站得住腳的。但這是我依 PostgreSQL 行為判斷，不是實測：我嘗試在 scratchpad 起拋棄式 PG17 叢集被 hook 擋下，本機也沒有 Docker。verify_memory_role.sql 的 R2 確實能驗證它（以該角色 INSERT 帶 owner_user_id 與 actor_user_id 外鍵的列，若前提不成立會拋 permission denied 並使 psql 在 ON_ERROR_STOP 下失敗），且 CI 步驟會先確認 users 有列（schema_rbac.sql 內建 SYSTEM.retention-purge），所以 CI 首跑就是第一次真實驗證。 | 無需改設計；維持「未驗」的標示，並在 PR 合併前以含 A1 的 push 取得 memory-schema job 的 R0-R3 結果，紅燈時第一個查外鍵權限。 |
| Minor | backend/scripts/verify_memory_role.sql > R3，與 schema_rbac.sql > REVOKE CREATE ON SCHEMA public FROM cloud360_memory | R3 在 pg18 上沒有鑑別力：PostgreSQL 15 起 PUBLIC 預設就沒有 public schema 的 CREATE，所以即使拿掉那行 REVOKE，R3 也會通過。反過來若某個環境的 public schema 仍由 PUBLIC 持有 CREATE（例如由舊版升級而來），對單一角色的 REVOKE 不會生效，R3 在該環境會紅燈但 CI 看不到。R1 同理只涵蓋執行當下已存在的 public 表。 | 在 verify_memory_role.sql 的 R3 註解或 code-summary 如實註明「pg18 預設下 R3 不證明 REVOKE 有效」；若要有鑑別力，另加對 has_schema_privilege 的斷言，並考慮對 PUBLIC 層級的處置另行裁決。 |
| Minor | backend/scripts/verify_memory_role.sql > R2 | R2 只驗證兩表的 INSERT、SELECT、DELETE，沒有以該角色執行向量相似度查詢（<=> 運算子與 HNSW 索引）或使用序列以外的 memory 物件。該角色日後若成為記憶端點的連線身分，真正的查詢路徑是否受 public schema 上 vector 型別與運算子的存取影響，CI 看不到。 | 之後把記憶端點改接該角色的單元，須補一條以該角色執行 SEARCH_SQL 形狀查詢的斷言；本單元記為已知落差即可。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| git diff HEAD hunk 計數 | schema_rbac.sql 4、DEPLOY.md 14、ci.yml 7 個 hunk；verify_memory_schema.sql 不在 diff 內；verify_memory_role.sql 與 deploy/initdb 為未追蹤新檔 | 與回歸節宣稱的數字完全一致。我逐一看過 ci.yml 與 schema_rbac.sql 的 hunk：R0-R3 步驟與角色 DO 區塊屬 A1，P1-P17 與 tests_pg 步驟名屬其他列，沒有一個 hunk 屬本單元。本單元 0 個 hunk 成立。 |
| backend 全套 unittest（scratchpad 副本，venv 以符號連結，PYTHONDONTWRITEBYTECODE=1，HYPOTHESIS_STORAGE_DIRECTORY 指向 scratchpad） | Ran 1372 tests，OK (skipped=3) | 與回歸節數字相符。test_memory_db_role 單跑 7 個測試 OK。副本與 hyp 目錄已刪除。 |
| 計畫勾選實算（grep） | 18 個已勾、3 個未勾 | 與回歸節相符。3 格未勾為 §五 判準 1、2 與 §八 真實 PostgreSQL 驗證，處置得當：該格的備援寫法是「本輪未驗」，A1 未 commit 使 CI 也沒跑過新版 SQL，勾選會製造不存在的驗證感。 |
| traceability.json json.load | 通過；BR1.2 維持 Deferred，OPEN-MB20-SECRET 以 blocking-before-deploy 照錄 | Deferred 得當，不應在 R0-R3 綠燈前改狀態；但見 Major 一項的關閉條件缺口。 |
| 真實 PostgreSQL（R0-R3、兩次套用、密碼 script） | 未驗 | 本機 Docker 不可用；我試圖起拋棄式本機叢集被 hook 擋下。此項只能由含 A1 的 CI 首跑驗證。 |

### Summary

A1 在靜態層面符合 BR1.1、BR1.2、BR1.3：角色只授 memory、撤銷 public、DO 區塊可重跑、無 psql 變數，外鍵最小權限為零的解讀依 PostgreSQL 行為站得住腳，且 R2 能在 CI 驗證它；hunk 歸屬、1372 個測試與 18／3 勾選數我都複驗成立，3 格未勾與 Deferred 的處置是誠實的。需要處理的是紀錄層的缺口：OPEN-CG5-1 的關閉條件沒有說出記憶端點仍用擁有者連線、get_memory_session 無呼叫者這個事實，另有三項前輪 Minor（R-07、R-08、R-10）仍待補註。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | DEPLOY.md > 2.2.8 U5 記憶層 schema（第 599 行起，「既有非空 volume 的建立路徑尚未定案」）；aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-summary.md > 六、未完成／待處置 第 2 項（OPEN-M5） | 這兩處都說記憶 schema 在既有非空 volume 上的建立路徑「未決、部署前必須先決定」，但這已不成立：`backend/scripts/run_meta_schema_migration.py` 的 `BLOCKS_TO_RUN = ("X", "I", "J")` 把記憶區塊 `I)` 納入，DEPLOY.md 2.2.9（約第 684-700 行）也明寫該腳本一次建立 U5 與 U18 的全部新物件。讀 2.2.8 的部署者會被告知要先決定一件已經決定的事，或不知道要跑哪支腳本，而 2.2.8 正是本單元負責的 blocking 部署資產。 | 把 DEPLOY.md 2.2.8 該段改成指向 2.2.9 的 `run_meta_schema_migration.py`，並註明它同時涵蓋 `I)` 區塊；把 code-summary 第六節第 2 項的 OPEN-M5 標為已由 U18 的遷移腳本關閉，附上腳本路徑。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-summary.md > 重新查驗表 第 1、2 列 | 判準 1、2 未勾，理由站得住腳（本機無 PostgreSQL，且 `a5200fc` 之後 schema 有變更）。我逐項核對了 `git diff a5200fc -- schema_rbac.sql`：記憶區塊（`I)`，約第 450-560 行）沒有任何變動；改動只有檔頭註解、`ix_project_members_user_id`（`CREATE INDEX IF NOT EXISTS`）、U20 的條件式 DO 區塊（欄位已是 varchar 時直接 RETURN）以及三處 COMMENT 文字（單引號數量為偶數，語法無誤）。兩次套用與 S1-S13 受影響的風險低，但這仍是推論，不是 CI 結果。 | 在摘要補一句：記憶區塊自 `a5200fc` 起位元組未變，風險來自其他單元的 DDL，下次推送後以 CI 的 `memory-schema` job 判定。不需阻擋。 | Resolved (reviewer) |
| R-03 | Minor | schema_rbac.sql > I) 區塊末尾 grant 的 DO 區塊（第 546-566 行）；DEPLOY.md > 2.2.8 開頭（「BR1.2 的 grant 邊界整個作用方式就是只開放 memory schema」）；code-summary.md > 六、第 1 項（OPEN-CG5-1） | 規則 BR1.2 要求對「記憶層使用的資料庫角色」只授予 `memory` schema 的權限、不授予 `public` 寫入權。實際寫的 grant 只是 `GRANT ... TO current_user`，也就是執行 DDL 的那個角色（部署中是 `POSTGRES_USER`，擁有全部物件）。這個授權對它是空操作：沒有建立任何記憶專用角色，也沒有對 `public` 做任何 REVOKE，所以「資料庫層的唯一邊界」並不存在。OPEN-CG5-1 只說「沒有 CI 斷言」，把問題描述成未驗證；但問題其實是未實作。COMMENT ON SCHEMA 與 DEPLOY.md 又寫成邊界靠 grant 運作，讀的人會以為資料庫層已有隔離。 | 如實改寫三處：把 OPEN-CG5-1 改為「BR1.2 的邊界目前未落地（無記憶專用角色），grant 對連線角色為空操作」，並在 DEPLOY.md 2.2.8 與 schema COMMENT 去掉「grant 邊界已生效」的語氣。同時指定承接單元或後續工作（建立記憶專用角色、REVOKE `public` 寫入、加第二角色的 CI 斷言），不要只標為「未驗證」。 | Unresolved |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-generation-plan.md > 五、完成判準 第 1、2 項（已勾選）；code-summary.md > 重做 > 七項判準 第 1、2 列 | 判準第 1 項寫的是「`N-2` job 綠燈」，勾選依據卻是本機 PG17 的一次性叢集。計畫 §六 的解讀只允許兩種做法：引用 CI 最近一次結果，或據實記為本輪未驗。PG17 不是 CI 的 pg18，最近的 CI 綠燈又早於現行樹，所以這個勾選比 §六 允許的更強。code-summary 自己已承認 pg18 未驗，但計畫上的方框仍是無條件打勾。 | 在計畫第 1、2 項旁註明「以本機 PG17 實跑代替，pg18 的 CI 結果待下次推送確認」，或把勾選改為附條件，避免日後只讀計畫的人把它當成 CI 已綠。 | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-generation-plan.md > 五、第 7 項；code-summary.md > 重做 > 第 7 列 | 第 7 項改為勾選，依據是 manifest 的 4 個寫入路徑都不在「不動的檔案」清單。就 §六「只看本單元自己的變更」的解讀而言，這個判斷站得住，且 code-summary 已揭露與上一節「未勾、無法驗證」不同。但以「寫入範圍」判定本質上是同義反覆：manifest 只列本單元宣稱會寫的檔，無法偵測本單元是否也動了清單內的檔（例如 `models.py`）。提交歸屬仍不可得，所以這格比其他六格弱。 | 在計畫該格註明「依寫入範圍判定，未經 commit diff 驗證」，不要與其他六格以同等語氣呈現。 | Resolved (reviewer) |
| R-06 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-summary.md > 三、突變驗證；重做一節「突變本輪未重跑」 | 9 項突變 M1-M9 是針對舊版 `verify_memory_schema.sql`（S1-S12）做的。該檔現已擴到 576 行並加入 S13-S15，S1-S12 的邏輯是否被改動未重新檢查，重做一節卻沿用舊紀錄。本輪既然零改動，沿用本身可接受，但「突變全部 RED」的結論的時效性沒有說明。 | 在突變一節加註「對應的是 U5 交付當時的 S1-S12，之後其他單元新增 S13-S15，未重跑」；或下次動到該檔時重跑 M1-M9 至少一次。 | Resolved (reviewer) |
| R-07 | Minor | .github/workflows/ci.yml > memory-schema job 步驟名「Verify memory schema assertions (S1-S13)」（約第 359-362 行）；unit-test-instructions.md 的「S1-S12」 | 步驟名寫 S1-S13，腳本實際已有 S1、S3-S15，測試說明與計畫仍寫 12 條。code-summary 已列為凍結文件落差，但共用的 ci.yml 步驟名是活的文件，會誤導看 CI 輸出的人。 | 下一個動到 ci.yml 的單元順手把步驟名改為不寫死數字；本單元記為已知落差即可，不阻擋。 | Unresolved |
| R-08 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-generation-plan.md > 七、第二項（判準 1、2 的依據） | 這一項已勾選，但文字仍寫「CI run 40423381616 的 memory-schema job」。我用 gh 只讀查證：該 run 是 UI Regression Reporter（結論 failure），jobs 為 pre_activation、activation、agent、detection、safe_outputs、conclusion，沒有 memory-schema。照字面，條件「否則據實記為本輪未驗」成立。開發者改用同一 head SHA c6a40f9 的 push CI run 40423375585：Memory schema (real PostgreSQL) success，其中兩次套用與「Verify memory schema assertions」步驟皆 success；git log 與 git diff --stat 顯示 schema_rbac.sql、verify_memory_schema.sql、ci.yml 在該 SHA 之後無變動。計畫意圖（現行樹、pg18、真實 CI 結果）因此滿足，勾選實質誠實，且 code-summary 二之 2 已揭露差異並讓 conductor 可退回。問題只剩計畫本身：單看計畫的人會讀到一個錯的 run id 加一個已勾方框。附帶：同 SHA 的 PR run 40423381647 整體 failure（Backend 單元測試紅燈），但其 memory-schema job 為 success，不影響本單元判準，也不應被讀成整體 CI 綠。 | 就地在該項後加一行註記：指名的 run id 是錯的（屬 UI Regression Reporter），實際依據為同 SHA 的 CI push run 40423375585 的 memory-schema job。不必退回未勾。 | New |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/functional-design/merge-blockers.md > 第 20 列與第 29 列 | 兩列描述同一個 BR1.2 缺陷，且完成條件不同：第 20 列要求建專用角色、REVOKE、CI 第二角色斷言並同步文件；第 29 列另允許「明文裁決不採並改寫 BR1.2」。兩列各自獨立關閉可能留下一列仍待處置、或兩列結論矛盾。 | 在兩列互相註明為同一項並指定以哪一列的完成條件為準，或合併為一列。 | New |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-summary.md > 六、第 4 項與重做一節的「待確認」「仍未解」 | 六之 4 仍寫「N-2 尚未在真實 CI 上跑過」（OPEN-CG5-2），但最新一節已證 pg18 的 CI job 對現行樹為 success。六節標題是「未完成／待處置」，讀者會把已過期的項目當成現況。其餘舊數字（497、1223、1319）在凍結的歷史小節內，可接受。 | 在六之 4 末尾加一句「已由 2026-10-30 一節以 run 40423375585 關閉 OPEN-CG5-2」，不改歷史小節。 | New |

> R-03 Not re-checked this round

> R-07 Not re-checked this round

> R-08 Not re-checked this round

> R-09 Not re-checked this round

> R-10 Not re-checked this round
