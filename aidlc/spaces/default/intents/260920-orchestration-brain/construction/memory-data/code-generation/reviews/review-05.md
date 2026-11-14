## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-03 | Fixed | Minor | schema_rbac.sql 第 594-609 行現已建立 cloud360_memory 並 REVOKE public 的表、序列與 CREATE；第 555-559 行註解與 DEPLOY.md 2.2.8 都已改為如實說明邊界由專用角色承擔，並明寫先前的寫法是錯的。CI 的 R0-R3 步驟已存在。邊界在執行期是否真的被使用（memory_router 仍用擁有者連線）是 memory-service 的承接項（merge-blockers 第 48 列），不屬本單元。 |
| R-07 | Still applies | Minor | .github/workflows/ci.yml 第 376 行步驟名仍寫 S1-S13，腳本實際為 S1、S3-S15（verify_memory_schema.sql 檔頭第 1-2 行也仍寫 S1-S12 加 S13）。共用檔，本單元不阻擋，下一個動到 ci.yml 的單元順手處理。 |
| R-08 | Still applies | Minor | code-generation-plan.md 第 168 行已勾選，文字仍指名錯的 run id 40423381616，旁邊沒有註記。 |
| R-09 | Fixed | Minor | merge-blockers.md 第 29 列已明寫與第 20 列同一缺陷，並指定以第 20 列的描述與完成條件為準。 |
| R-10 | Still applies | Minor | code-summary.md 六之 4（約第 129-131 行）仍寫 N-2 尚未在真實 CI 上跑過，全檔沒有任何一處註記 OPEN-CG5-2 已由 CI 關閉；新增的重跑一節也沒補。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-generation-plan.md > 第 152、153、191 行三個未勾格；code-summary.md > 整站重跑後的勾選回復 | 三個未勾格的理由（A1 未 commit、CI 未跑新版 SQL、本機無 Docker）已過期：據 conductor 說明，CI run 42454550208（head ff537a7）的 Memory schema job 已對現行樹實跑 S1-S13 並通過。新節只寫「沿用 HEAD 的未勾理由」，讀者會以為仍無任何真實 PostgreSQL 驗證。我不能用 gh 查證該 run，只能採信 conductor 的陳述。 | 由 conductor 查證該 run 的 memory-schema job（含兩次套用與 R0-R3 步驟）後，在新節補一行指名 run id 與強度，並把第 152、153 行勾選；第 191 行改註為以 CI 取代本機驗證，或維持未勾但改寫理由。 |
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-summary.md > 整站重跑後的勾選回復 第二點 | 新節以收據 reviewed-source-7f71872725c8.tsv 為基準，但單元目錄下已有更新的 reviewed-source-519575fb8272.tsv（2026-11-08 20:23），其四個雜湊與現行樹逐一相同。節內「3 同、1 變」的敘述對最新收據不成立。 | 補一句最新收據 519575fb8272 與現行樹四檔全同，或註明 3 同 1 變是相對較舊收據。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| shasum -a 256 對四個共用檔重算，與 7f71872725c8 比對 | ci.yml、DEPLOY.md、schema_rbac.sql 相同；verify_memory_schema.sql 由 2905225a 變為 5afb60c2 | 與 conductor 的 3 同 1 變一致 |
| shasum 對 reviewed-source-519575fb8272.tsv | 四檔全部等於現行樹 | 以最新收據為準則無任何變動 |
| git log 與 git show ff537a7 -- backend/scripts/verify_memory_schema.sql | 唯一改動是 S15 檢索查詢標記區內新增一行 expires_at 過濾（第 487 行，+1 行） | 屬 U8 的 S15 區塊，位於 S15_SEARCH_QUERY_BEGIN 與 END 之間；S1-S13 的斷言（第 1-292 行）零改動。S15 的 fixture 行（第 400-470 行）未設任何 expires_at，過濾不影響其預期筆數；該過濾對 NULL 與未過期的列放行 |
| git diff HEAD 對 code-generation-plan.md | 零差異 | 只有勾選字元的回復屬實；未勾格為第 152、153、191 行 |
| code-summary.md 新節核對 | 18 勾 3 未勾屬實；未勾三格與計畫一致；收據判定為 3 同 1 變對 7f71 屬實，但已被更新收據取代 | 內容屬實，僅時效落後 |
| 測試與 gh | 依限制未執行 | CI 通過一事僅採信 conductor 與 brief 的陳述，標為未獨立查證 |

### Summary

本單元自上次 READY 後沒有程式改動；唯一變動的 verify_memory_schema.sql 是 U8 的 S15 查詢鏡像多一行過期過濾，不碰 S1-S13，也不影響 S15 的 fixture，因此不破壞本單元的斷言。先前五項 Minor 中 R-03、R-09 已修復，R-07、R-08、R-10 仍是紀錄精確度問題，另新增兩項紀錄時效的 Minor，皆不阻擋，判定 READY。C3（membership-service）依指示未重複報告。

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
