## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-25T06:13:20Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | DEPLOY.md > 2.2.8 U5 記憶層 schema（第 599 行起，「既有非空 volume 的建立路徑尚未定案」）；aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-summary.md > 六、未完成／待處置 第 2 項（OPEN-M5） | 這兩處都說記憶 schema 在既有非空 volume 上的建立路徑「未決、部署前必須先決定」，但這已不成立：`backend/scripts/run_meta_schema_migration.py` 的 `BLOCKS_TO_RUN = ("X", "I", "J")` 把記憶區塊 `I)` 納入，DEPLOY.md 2.2.9（約第 684-700 行）也明寫該腳本一次建立 U5 與 U18 的全部新物件。讀 2.2.8 的部署者會被告知要先決定一件已經決定的事，或不知道要跑哪支腳本，而 2.2.8 正是本單元負責的 blocking 部署資產。 | 把 DEPLOY.md 2.2.8 該段改成指向 2.2.9 的 `run_meta_schema_migration.py`，並註明它同時涵蓋 `I)` 區塊；把 code-summary 第六節第 2 項的 OPEN-M5 標為已由 U18 的遷移腳本關閉，附上腳本路徑。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-summary.md > 重新查驗表 第 1、2 列 | 判準 1、2 未勾，理由站得住腳（本機無 PostgreSQL，且 `a5200fc` 之後 schema 有變更）。我逐項核對了 `git diff a5200fc -- schema_rbac.sql`：記憶區塊（`I)`，約第 450-560 行）沒有任何變動；改動只有檔頭註解、`ix_project_members_user_id`（`CREATE INDEX IF NOT EXISTS`）、U20 的條件式 DO 區塊（欄位已是 varchar 時直接 RETURN）以及三處 COMMENT 文字（單引號數量為偶數，語法無誤）。兩次套用與 S1-S13 受影響的風險低，但這仍是推論，不是 CI 結果。 | 在摘要補一句：記憶區塊自 `a5200fc` 起位元組未變，風險來自其他單元的 DDL，下次推送後以 CI 的 `memory-schema` job 判定。不需阻擋。 | Resolved (reviewer) |
| R-03 | Major | schema_rbac.sql > I) 區塊末尾 grant 的 DO 區塊（第 546-566 行）；DEPLOY.md > 2.2.8 開頭（「BR1.2 的 grant 邊界整個作用方式就是只開放 memory schema」）；code-summary.md > 六、第 1 項（OPEN-CG5-1） | 規則 BR1.2 要求對「記憶層使用的資料庫角色」只授予 `memory` schema 的權限、不授予 `public` 寫入權。實際寫的 grant 只是 `GRANT ... TO current_user`，也就是執行 DDL 的那個角色（部署中是 `POSTGRES_USER`，擁有全部物件）。這個授權對它是空操作：沒有建立任何記憶專用角色，也沒有對 `public` 做任何 REVOKE，所以「資料庫層的唯一邊界」並不存在。OPEN-CG5-1 只說「沒有 CI 斷言」，把問題描述成未驗證；但問題其實是未實作。COMMENT ON SCHEMA 與 DEPLOY.md 又寫成邊界靠 grant 運作，讀的人會以為資料庫層已有隔離。 | 如實改寫三處：把 OPEN-CG5-1 改為「BR1.2 的邊界目前未落地（無記憶專用角色），grant 對連線角色為空操作」，並在 DEPLOY.md 2.2.8 與 schema COMMENT 去掉「grant 邊界已生效」的語氣。同時指定承接單元或後續工作（建立記憶專用角色、REVOKE `public` 寫入、加第二角色的 CI 斷言），不要只標為「未驗證」。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-generation-plan.md > 五、完成判準 第 1、2 項（已勾選）；code-summary.md > 重做 > 七項判準 第 1、2 列 | 判準第 1 項寫的是「`N-2` job 綠燈」，勾選依據卻是本機 PG17 的一次性叢集。計畫 §六 的解讀只允許兩種做法：引用 CI 最近一次結果，或據實記為本輪未驗。PG17 不是 CI 的 pg18，最近的 CI 綠燈又早於現行樹，所以這個勾選比 §六 允許的更強。code-summary 自己已承認 pg18 未驗，但計畫上的方框仍是無條件打勾。 | 在計畫第 1、2 項旁註明「以本機 PG17 實跑代替，pg18 的 CI 結果待下次推送確認」，或把勾選改為附條件，避免日後只讀計畫的人把它當成 CI 已綠。 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-generation-plan.md > 五、第 7 項；code-summary.md > 重做 > 第 7 列 | 第 7 項改為勾選，依據是 manifest 的 4 個寫入路徑都不在「不動的檔案」清單。就 §六「只看本單元自己的變更」的解讀而言，這個判斷站得住，且 code-summary 已揭露與上一節「未勾、無法驗證」不同。但以「寫入範圍」判定本質上是同義反覆：manifest 只列本單元宣稱會寫的檔，無法偵測本單元是否也動了清單內的檔（例如 `models.py`）。提交歸屬仍不可得，所以這格比其他六格弱。 | 在計畫該格註明「依寫入範圍判定，未經 commit diff 驗證」，不要與其他六格以同等語氣呈現。 | New |
| R-06 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-data/code-generation/code-summary.md > 三、突變驗證；重做一節「突變本輪未重跑」 | 9 項突變 M1-M9 是針對舊版 `verify_memory_schema.sql`（S1-S12）做的。該檔現已擴到 576 行並加入 S13-S15，S1-S12 的邏輯是否被改動未重新檢查，重做一節卻沿用舊紀錄。本輪既然零改動，沿用本身可接受，但「突變全部 RED」的結論的時效性沒有說明。 | 在突變一節加註「對應的是 U5 交付當時的 S1-S12，之後其他單元新增 S13-S15，未重跑」；或下次動到該檔時重跑 M1-M9 至少一次。 | New |
| R-07 | Minor | .github/workflows/ci.yml > memory-schema job 步驟名「Verify memory schema assertions (S1-S13)」（約第 359-362 行）；unit-test-instructions.md 的「S1-S12」 | 步驟名寫 S1-S13，腳本實際已有 S1、S3-S15，測試說明與計畫仍寫 12 條。code-summary 已列為凍結文件落差，但共用的 ci.yml 步驟名是活的文件，會誤導看 CI 輸出的人。 | 下一個動到 ci.yml 的單元順手把步驟名改為不寫死數字；本單元記為已知落差即可，不阻擋。 | New |

> R-01 Reviewer note: DEPLOY.md 第 599-603 行已改為「既有非空 volume 的建立路徑：見 2.2.9」，並指出 `run_meta_schema_migration.py` 的 `BLOCKS_TO_RUN = ("X", "I", "J")` 含記憶區塊 `I`（我讀了該腳本第 95 行，屬實）。code-summary 第六節第 2 項 OPEN-M5 已標為已關閉並附腳本路徑。

> R-02 Reviewer note: code-summary 重新查驗表第 1 列已寫明記憶區塊 `I)` 自 `a5200fc` 起位元組未變、風險來自其他單元 DDL、下次推送後由 CI 判定；「重做」一節又補上 PG17 實跑與待確認 pg18 的說明。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 讀取 schema_rbac.sql 第 441-566 行 | 兩表 9 欄與 7 欄、四條 CHECK、五個索引（含 `occurred_at`）、全部 `IF NOT EXISTS`，與 code-summary 描述一致 | 契約結構（BR1.1、BR1.3、BR2.x、BR3.x、BR4.1、NFR7.2）屬實；後續單元新增的 HNSW 索引沒有破壞本單元契約 |
| 讀取 ci.yml 第 315-400 行 | `pgvector/pgvector:pg18`，兩次套用後再執行驗證腳本 | N-2 設計與計畫 §四 一致；本機未啟動資料庫，也未執行測試 |
| 讀取 run_meta_schema_migration.py 第 95 行 | `BLOCKS_TO_RUN = ("X", "I", "J")` | 確認 R-01 的修正依據成立 |

### Summary

R-01、R-02 兩項先前發現均已修正，單元交付的 DDL、CI job 與 DEPLOY.md 與計畫一致，沒有 Critical。唯一的 Major 是 BR1.2 的 grant 只授權給 `current_user`，實際不構成邊界，卻被文件描述為已生效的資料庫層隔離；其餘 4 項為 Minor（判準 1、2、7 的勾選強度、突變時效、CI 步驟名）。計數：Critical 0、Major 1、Minor 4。
