## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站（U23 project-pages-ui 的 infrastructure-design）結論為零新服務、零新埠、零新環境變數、零新 secret，只多一個索引 `ix_project_members_user_id`。我抽查的證據都成立：索引已落在 `schema_rbac.sql:609`、`models.py:595`、`run_meta_schema_migration.py` 的 `EXPECTED_INDEXES`（:176）與 `BLOCK_SENTINELS`（:118），`deploy.yml` 對遷移腳本 0 命中，compose 日誌輪替為 50m 乘 5，`backend/Dockerfile` 沒有 `--workers`。ADR-0006 四面向各有落點，PBT 不適用的判定也正確。主要問題是：前次 review-01 的 R-01（staging 上無法照字面執行的部署與驗證指令）、R-03、R-04、R-05 仍留在凍結的 `cicd-pipeline.md` 與 `infrastructure-specification.md`；程式端與 `DEPLOY.md` 已把正確做法補上（R-01、R-05 已修；R-02 的測試也已落地），設計檔與落地不一致，以落地那邊為正。1 項 Major、5 項 Minor，不阻擋。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/project-pages-ui/infrastructure-design/cicd-pipeline.md > 二、部署步驟 第 5、6 列 | 前次 review-01 R-01 已提，凍結產出仍未改。第 5 列寫 `cd backend && python scripts/run_meta_schema_migration.py`，第 6 列寫 `psql "$DATABASE_URL"`。staging 的 db 服務不發布 5432，且兩者需要的 DATABASE_URL 形式互斥，照字面無法執行。落地的 `DEPLOY.md:849-909` 已改成 `compose cp schema_rbac.sql backend:/schema_rbac.sql` 後 `compose exec backend python scripts/run_meta_schema_migration.py`，驗證改用 `docker exec ... psql`，並說明容器內腳本讀的是 `/schema_rbac.sql`。這一點也是本檔原先沒發現的：只 exec 而不先複製檔案會失敗。設計檔與落地矛盾，**DEPLOY.md 是對的**。 | 在 `cicd-pipeline.md` §二 第 5、6 列加更正註記（不必重寫凍結檔），指明以 `DEPLOY.md` 的 `U23` 小節為可執行正本，並把「先複製 schema_rbac.sql 進容器」列為第 5 步前置。 | New |
| R-02 | Minor | construction/project-pages-ui/infrastructure-design/cicd-pipeline.md > 四之一 補強 | 前次 review-01 R-02 已提。設計寫「以讀檔文字確認 EXPECTED_INDEXES 區塊含索引名」，整檔字串比對在只刪 EXPECTED_INDEXES 那一列時仍會綠。落地的 `test_membership_data.py` 的 `test_M3b` 已改用 `ast` 取 `EXPECTED_INDEXES` 的值比對三元組，並在 docstring 說明原因，所以程式正確、設計描述過時。 | 在設計檔註記「落地以 ast 取值比對為準」，避免下一個讀者照字面改回整檔比對。 | New |
| R-03 | Minor | construction/project-pages-ui/infrastructure-design/cicd-pipeline.md > 四、各失敗路徑由哪一道閘門抓 判定欄 | 前次 review-01 R-03 已提。同檔 §一 已承認 `ut` 沒有必要狀態檢查，§四 卻對第 1 至 6、11、12 列標「抓得到」，把「CI 會紅」與「合併會被擋」混為一談。 | 判定欄改標「訊號（不擋合併）」，或在表頭加一句限定。 | New |
| R-04 | Minor | construction/project-pages-ui/infrastructure-design/cicd-pipeline.md > 三、合併順序約束 第 5、6 列 | 前次 review-01 R-04 已提。第 5 列「表不存在則專案清單 500」與同檔 `infrastructure-specification.md` 二之一 (b) 自己承認的 `create_all` 建表互相矛盾，後果被高估。第 6 列要求 U20、U23、U21 的順序，而 U21 的提交（763a45a）早於 U23（8677b7d），已無法遵守，屬 bolt-plan 排序性質而非技術依賴。 | 第 5 列改述為缺 COMMENT 與需先跑 2.2.7 的真實後果；第 6 列註明為排序性質且已非現況。 | New |
| R-05 | Minor | construction/project-pages-ui/infrastructure-design/infrastructure-specification.md > 二之一 (b) 列「需要人工嗎」欄 | 前次 review-01 R-05 已提。(b) 列寫「否」，但 create_all 建的表缺 COMMENT（`OPEN-ID19-1`），落地的 `DEPLOY.md:849-909` 第 6 點明寫此情形仍須跑遷移腳本；本檔同列括號又自稱「本來就要求」，欄位值與括號內文互相矛盾。 | 欄位值改為「是（補 COMMENT 與驗證）」並引用 `OPEN-ID19-1`。 | New |
| R-06 | Minor | construction/project-pages-ui/infrastructure-design/cicd-pipeline.md 與 infrastructure-specification.md 與 monitoring-design.md 的 `deploy.yml`／`DEPLOY.md` 行號引用 | 行號漂移。例如 `DEPLOY.md:691`（「不呼叫任何遷移腳本」）現在位於 `DEPLOY.md:855`；`DEPLOY.md:660`、`:988` 同樣已移位；`deploy.yml:570-575`、`:596`、`:618`、`:143`、`:355` 在 U14 於 :565 之後插入 53 行後全部下移。事實本身仍成立（`deploy.yml` 對遷移腳本 0 命中），但行號已無法機械複驗。另外 §二 第 3 列稱冒煙不碰其他路徑，現在 deploy 多了 U14 的 brain WS subprotocol 步驟，「只有三項冒煙」的說法已不完整（對本單元的結論不變，仍沒有碰 hierarchy）。 | 加一句「行號為撰寫當下，之後已漂移」的註記，或改引用段落標題而非行號。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep 索引名於 models.py、schema_rbac.sql、遷移腳本、DEPLOY.md、test_membership_data.py | 各處均有命中（models.py:595、schema_rbac.sql:609、遷移腳本 :118 與 :176、測試 M3 與 M3b） | 設計宣稱的九項落點已落地；SQL、ORM、EXPECTED_INDEXES 三者一致 |
| grep deploy.yml 的 migrat | 0 命中 | 「deploy.yml 不呼叫任何遷移腳本」成立，人工步驟的必要性成立 |
| compose 日誌與 Dockerfile | `max-size: 50m`、`max-file: 5`；Dockerfile 無 `--workers` | 稽核日誌保留量與單進程主張成立 |
| git diff deploy.yml | 在 :565 之後新增 53 行 U14 步驟，與本單元無關 | 屬他單元改動，但使行號引用漂移（R-06） |
| 契約端點三問 | 本單元新增索引為唯讀加速結構，無欄位；新方法與 log 於 nfr-design 已指名擁有者與呼叫者 | 無缺口 |
| ADR-0006 四面向 | IAM、Encryption、Network exposure、Audit logging 各有逐格判定且與 nfr-design 一致 | 通過 |
