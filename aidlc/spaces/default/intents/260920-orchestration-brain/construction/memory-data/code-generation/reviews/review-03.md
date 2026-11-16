## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

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

> R-03 Reviewer note: 缺陷本身（BR1.2 的 grant 只授給 current_user、無專用角色、無 REVOKE public）仍在共用檔，DEPLOY.md 2.2.8 與 COMMENT ON SCHEMA memory 的語氣也未改。但本單元紀錄層已如實處理：code-summary 六之 1 改寫為邊界未落地並標 IAM 面向，traceability.json 的 BR1.2 改 Deferred 並指名承接，merge-blockers 第 29 列（及先前登錄的第 20 列）列為合併前必修且明寫「落地前不得寫成已生效」。程式與文件修正本輪刻意不做，屬已指名承接的延後，不再以 Major 計；降為 Minor 的前提是第 20、29 列的必修確實擋在合併之前。

> R-04 Reviewer note: 計畫五節下方註記說明判準 1、2 依據以 code-summary 最新一節為準；最新一節明列 CI run 40423375585（pg18、現行樹）。依據已可追溯，不再是無條件打勾。

> R-05 Reviewer note: 計畫五節註記與 code-summary 皆寫明判準 7 依寫入範圍判定、未經 commit diff 驗證、強度弱於其他格。

> R-06 Reviewer note: code-summary 三節加了時效註記；現行斷言 id 我實數為 S1、S3 至 S15 共 14 個、檔案 576 行，與註記相符。unit-test-instructions.md 第 13 行也加了現況註記。

> R-07 Reviewer note: ci.yml 第 376 行步驟名仍為「S1-S13」，腳本實有 S1、S3 至 S15。本單元已在 code-summary 五節記為已知落差並指定落點，不阻擋；活文件仍待下一個動 ci.yml 的單元修。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| gh run view 40423381616 | workflowName=UI Regression Reporter、failure、sha c6a40f9、無 memory-schema job | 確認計畫指名的 run 錯誤 |
| gh run view 40423375585 / gh run list --commit c6a40f9 | CI push、success；Memory schema (real PostgreSQL) success；兩次套用與驗證步驟 success；PR run 40423381647 的 memory-schema 亦 success、整體 failure（Backend job） | 替代依據成立；整體 CI 非全綠，需如實表述 |
| git log c6a40f9..HEAD 與 git diff --stat c6a40f9（schema_rbac.sql、verify_memory_schema.sql、ci.yml、DEPLOY.md） | 皆無輸出 | 該 SHA 之後三個共用檔未變，CI 結果代表現行樹 |
| shasum -a 256 對收據 reviewed-source-a58ef1bdc213.tsv | ci.yml、verify_memory_schema.sql、schema_rbac.sql 與收據逐位元相同；僅 DEPLOY.md 不同（現況 d9b0571c…，收據 2608a131…） | 與 code-summary 一之說明一致 |
| difflib 回退重現（以 624c170:DEPLOY.md 為基底，只換回現行 730 至 738、2229、2239 三段） | 雜湊恰為 2608a131203c6bff1af9e0bddd945b3eb1790be32bf5552cb2d21f7808455ba0 | 獨立證實收據之後 DEPLOY.md 只多 #24、#26 三段；2.2.8 為 531 至 616 行，未被觸及 |
| traceability.json 讀取（python3 -I） | BR1.2 為 Deferred 並指名第 29 列；OPEN-CG5-1 改寫；OPEN-M5 為 resolved | 與 sensor 規則相符（Deferred 為合法狀態且需非空 target）；OPEN-M5 與六之 2 的更正對齊 |
| grep -c 計畫勾選 | 15 勾、0 未勾 | 與 code-summary 處置紀錄一致 |
| grep 斷言 id | S1、S3 至 S15 共 14 個，576 行 | R-06、R-07 的實數屬實 |
| 未執行測試 | 依指示不在工作樹寫檔 | 回歸數字（1326、OK）採信 code-summary 與同 SHA push CI 的 Backend job success，未獨立重跑 |

### Summary

本輪的重新驗證站得住：DEPLOY.md 自收據後的變動我以回退法獨立重現雜湊，確認只有 #24、#26 三段、未觸及 2.2.8；以同 SHA 的 CI push run 40423375585 勾判準 1、2 是誠實的，且開發者已揭露與計畫字面的差異，只需在計畫就地補一行註記，不必退回未勾。R-03 的缺陷仍在共用檔，但本單元紀錄已改為如實的「未落地」並指名承接（merge-blockers 第 29 列，另有第 20 列），故不再構成 Major；其放行前提是這兩列確實擋在合併之前。0 Critical、0 Major，READY。
