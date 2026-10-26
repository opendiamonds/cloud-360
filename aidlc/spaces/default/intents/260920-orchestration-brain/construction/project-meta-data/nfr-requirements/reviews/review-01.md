## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站是 DDL-only 單元的精簡 nfr-requirements：只記本站新定案的 `[P1]`=A（一支獨立遷移腳本、大聲失敗、不動啟動路徑、DEPLOY.md 記步驟），其餘 NFR 以 traceability 的 N/A 加承載者指向上游。以引用代替重寫的做法足以承載本單元（零端點、零進程、零新技術），ADR-0006 四面向各有判定，BR3.1 的處置也有二元判準。已抽查的引用與落地程式一致：`unit-of-work.md:443`/`:444`/`:448`、契約 `K-15` 的「不含任何資料寫入」、`database.py` 的 `except` 位置、`run_meta_schema_migration.py` 與 `DEPLOY.md` 2.2.9，且 `database.py` 的 diff 為空。主要缺口是 NFR8.2–NFR8.5 的二元判準寫得比落地實作鬆，漏掉腳本的順序前置條件。這一點在下游補上了，但需求層沒有，故列為 Major。其餘為 Minor。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/project-meta-data/nfr-requirements/security-requirements.md > 一、定案內容表（NFR8.2–NFR8.5） | 四項二元判準只要求「腳本存在、可執行」「非零碼」「diff 為空」「DEPLOY.md 有 psql 驗證」，沒有寫下腳本的**前置條件**與**成功的語意**。(a) 三張新表的外鍵指向 `U4` 的 `projects`／`systems`，故 `run_hierarchy_migration.py` 必須先跑過。需求層完全沒提，code-summary 第 8 項自承「上游沒有寫下的順序前置條件」，是 code-generation 才補上守門（`run_meta_schema_migration.py` 檔頭）。(b) 因 DDL 皆為 `IF NOT EXISTS`，既有環境若已有同名但約束不同的表，腳本可靜默 exit 0 而結構是錯的。NFR8.3 只涵蓋「DDL 失敗」，不涵蓋「DDL 被跳過」，與 BR3.1「大聲失敗」的意圖有落差（實作靠 COMMIT 前後條件終檢補上，需求未要求）。(c) 腳本需要的 DB 權限（建立 schema、`CREATE EXTENSION vector`、對 `current_user` 授權）也未列為需求，而這是 ADR-0006 IAM 面向對本站唯一實質的落點。判準寫得鬆，下游的好實作無需求依據，換人實作可能退化。 | 補充或以 corrections 方式記載：(1) 順序前置條件（`U4` 腳本先於本腳本，缺時以可讀訊息擋下）；(2) 「exit 0 ⟺ 預期物件與約束皆存在」的成功語意判準（後條件終檢）；(3) 執行腳本所用 DB 角色所需的最小權限。 | New |
| R-02 | Minor | construction/project-meta-data/nfr-requirements/traceability.json > upstream_ids 與 coverage（NFR8.2–NFR8.5） | `NFR8.2`–`NFR8.5` 列在 `upstream_ids`，但上游 `requirements.md` 的 NFR8（約 :537）只談「Redis 新增環境變數須同 PR 寫入 render-env.sh 與 .env.example」，沒有這四個子編號，也沒有 NFR8.1。它們是本站新創的 id，卻被記成上游，造成循環自我引用；同時 NFR8 的原意（compose 變數完整性）被延伸為 DB 遷移腳本，延伸未在 requirements 標示。 | traceability 將 NFR8.2–NFR8.5 標為「本站新增」而非 upstream；說明 NFR8.1 缺號的原因，並註明與上游 NFR8 原意的關係（本單元對原意的結論是零新環境變數）。 | New |
| R-03 | Minor | construction/project-meta-data/nfr-requirements/security-requirements.md > 一、NFR8.2「建立 U5 ＋ U18 的全部新物件」 | NFR8.2 把 `U5` 已交付的 `memory` schema 與兩張表的既有環境路徑（`OPEN-M5`）併入本單元的判準，但 `unit-of-work.md:443`/`:444` 只指派 U18 自己的三張表，契約 `K-15` 也只涵蓋三表。跨單元的責任轉移（U5 的缺口由 U18 的腳本承擔、U5 的 grant 邊界由本腳本落實）有使用者裁決 `[P1]`=A 作依據，但沒有在 unit-of-work 或 U5 側留下對應記載。本審查依規定未開啟 U5 內容，無法確認 U5 側是否已承接此點。 | 在本站或下游記載「U5 的既有環境路徑由 U18 腳本承擔」，並確認 U5 的 `OPEN-M5` 已標為由本單元處置，避免兩單元對同一缺口各自宣稱。 | New |
| R-04 | Minor | construction/project-meta-data/nfr-requirements/traceability.json > NFR6（N/A，target U5）；tech-stack-decisions.md > 三、驗證載體 | NFR6（真實 PostgreSQL CI job）在本單元被標為 N/A 並指向 U5，但 tech-stack-decisions 明確沿用該 job 並要求新增三態模型與外鍵斷言，本單元實際依賴 NFR6。另上游 NFR6 寫 `postgres:16-alpine`，實際 `ci.yml` 使用 `pgvector/pgvector:pg18`（:343、:588），tech-stack 採後者但未註明與上游偏離。 | NFR6 改為 partial（承載者 U5、本單元擴充斷言），並在 tech-stack-decisions 註明映像與上游 NFR6 的差異及原因。 | New |
| R-05 | Minor | construction/project-meta-data/nfr-requirements/security-requirements.md > 二、ADR-0006 Audit logging 列、一之誠實代價 | Audit logging 判為「適用」，但只列欄位名，沒有可判定的需求（例如改選事件須與角色變更同交易寫入、`cleared_at` 與 `value=NULL` 須同時成立的 CHECK）。另外：規定的是新增物件的失敗路徑，沒有寫成功後的回復路徑（遷移成功但需撤回時的 DROP 順序與影響），而 `project.md` 的 Operation 護欄要求部署程序含 rollback 步驟。兩者下游有部分處置（如 DEPLOY.md 的 rollback 說明、三態 CHECK），但需求層缺位。 | 將 audit logging 面向轉成至少一條二元判準；補一句回復立場（純新增、可 DROP，列出順序）或明記為 N/A 並說明理由。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 引用抽查（unit-of-work.md:443/:444/:448、K-15 observable_side_effects、database.py 的 except 位置 :192/:228/:257/:304、DEPLOY.md 2.2.7/2.2.9） | 全部相符 | 精簡形式的引用可複驗，無錯誤引用 |
| backend/database.py diff（NFR8.4） | git diff --stat 為空 | NFR8.4 判準成立 |
| backend/scripts/run_meta_schema_migration.py 對照 NFR8.2/8.3 | 單一交易、COMMIT 前後條件終檢、失敗 rollback ＋ 非零碼；DDL 取自 schema_rbac.sql 單一來源 | 實作符合且強於需求（支持 R-01 的觀察：需求判準偏鬆） |
| traceability.json 結構（coverage 項目與 N/A 承載者） | 全 15 項有狀態與 target | 無缺漏；僅 R-02、R-04 的語意問題 |
