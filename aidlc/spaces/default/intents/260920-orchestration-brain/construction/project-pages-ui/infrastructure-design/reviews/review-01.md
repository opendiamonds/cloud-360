## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-15T23:53:15Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/infrastructure-design/cicd-pipeline.md > 二、部署步驟 第 5、6 列 | 新設計問題。第 5、6 列是「遺漏遷移會無聲失敗」唯一的偵測手段，但照字面在 staging 做不到。第 5 列的 `cd backend && python scripts/run_meta_schema_migration.py` 需要帶 `+psycopg` 後綴的 DATABASE_URL，而 staging 的 `db` 服務沒有 host port（DEPLOY.md:206 逐字寫 db 服務沒有 host port、不要為了讓 psql 能連就去發布 5432；compose 的 DATABASE_URL 主機名是 `@db:5432`，只在 compose 網路內可解析）。第 6 列的 `psql "$DATABASE_URL"` 與第 5 列用同一變數，但 DEPLOY.md:221 逐字說給 psql 的那一份不能帶 `+psycopg` 後綴，兩者互相排斥。執行者照本檔做會在第 5 或第 6 步卡住，或改去發布 5432，違反既有暴露面控制。本檔說「照 DEPLOY.md 2.2.9」，但 2.2.9 本身也沒給 staging 主機的可執行形式 | 把第 5、6 列改成在 staging 主機可直接複製執行的形式：第 5 列改為經 `docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env exec backend python scripts/run_meta_schema_migration.py`（先確認該腳本有被 COPY 進 backend image）；第 6 列改為 DEPLOY.md:206 的 `docker exec` 形式的 psql。DEPLOY.md 新增段落同步寫這兩條 | New |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/infrastructure-design/cicd-pipeline.md > 四之一 補強 | 新設計問題。補強斷言寫成讀檔文字確認 EXPECTED_INDEXES 區塊含該索引名，但同一檔案中該字串還會出現在 BLOCK_SENTINELS["J"]（本單元自己要加的第 3 項）與註解裡。若實作成整檔 assertIn，從 EXPECTED_INDEXES 刪掉該列後仍為綠，突變驗證落空，補強形同虛設 | 明定斷言只比對 EXPECTED_INDEXES 元組內的三元組形式（例如正規式比對 `("public", "project_members", "ix_project_members_user_id")`），突變驗證須涵蓋只刪 EXPECTED_INDEXES、保留 BLOCK_SENTINELS 這一種 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/infrastructure-design/cicd-pipeline.md > 四、各失敗路徑由哪一道閘門抓 的判定欄 | 新設計問題。第一節已承認 ut 沒有必要狀態檢查（我以 gh api 複驗，required_status_checks 為 null），但第四節對第 1 至 6、11、12 列標 ✅「抓得到」，把「CI 會紅」與「合併會被擋」混為一談，讀者會以為這些路徑有擋閘 | ✅ 欄改標「訊號（不擋合併）」，或在表頭加一句限定 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/infrastructure-design/cicd-pipeline.md > 三、合併順序約束 第 5、6 列 | 新設計問題。第 5 列後果「表不存在則專案清單 500」忽略 database.py:90 的 create_all 會在啟動時建表（本檔二之一 (b) 自己承認），後果被高估。第 6 列要求 U20 到 U23 到 U21，但 git log 顯示 U21 mcp-bridge 提交（763a45a）早於 U23，該約束的所述後果沒有對應到實際依賴，也已無法遵守 | 第 5 列改述為缺 COMMENT 與需先跑 2.2.7 的真實後果；第 6 列改為說明它是 bolt-plan 的排序性質並承認已非現況，或刪除 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/infrastructure-design/cicd-pipeline.md > 二、部署步驟 第 5 列 與 infrastructure-specification.md > 二之一 (b) 列 | 既存漏審。第 5 列漏列 DEPLOY.md 的前置條件：2.2.7 的 run_hierarchy_migration.py 必須先跑過。另 (b) 路徑由 create_all 建表會缺 COMMENT（test_membership_data.py 檔頭 OPEN-ID19-1 已記），(b) 列「需要人工：否」沒提這個既知缺口 | 第 5 列補前置條件；(b) 列補一句引用 OPEN-ID19-1 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| jq 實算 traceability.json | upstream_ids 27、coverage 27（OK 7、N/A 20）、reverse 3、缺漏 0 | 與宣稱的 27、7、20 一致 |
| git show origin/ut:schema_rbac.sql 計 project_members | 0 | 與二之一「ut 上沒有 project_members」一致 |
| gh api branches/ut/protection | required_status_checks 為 null | 「ut 沒有必要狀態檢查」屬實 |
| schema_rbac.sql:879 與 DEPLOY.md:988 | C 區塊開頭確有 DELETE FROM role_permissions | 「不能用重跑整支 schema_rbac.sql 代替」屬實 |
| EXPECTED_INDEXES 實數與 DEPLOY.md:674 | 腳本 8 筆、DEPLOY 寫 7，加本單元 1 筆為 9 | 「7 到 9」的更正說法成立 |
| ci.yml 359-374、435-447、286-294、313 | 兩次套用 schema、step B 逐筆查 EXPECTED_INDEXES、OpenAPI drift、MCP drift 均如所述；backend/tests 對 EXPECTED_INDEXES 0 命中 | CI 閘門逐道判定成立；EXPECTED_INDEXES 漏列確無閘門 |
| nginx.conf、compose logging、Dockerfile、database.py 行號 | 均符合 | 零新服務、零新埠的證據可複驗 |

### Summary

索引到達三種資料庫狀態的推論、合併約束 1 至 4、c6 不適用的四點論證、回滾代價揭露、traceability 實算與 ADR-0006 四面向判定都成立。但唯一的偵測手段（第 5、6 列）在 staging 主機上照字面無法執行，因 db 無 host port 且 DATABASE_URL 的 psycopg 後綴與 psql 互斥，須修正才能 READY。三類計數：新引入 0、既存漏審 1、新設計問題 4（含 1 Major、3 Minor）。
