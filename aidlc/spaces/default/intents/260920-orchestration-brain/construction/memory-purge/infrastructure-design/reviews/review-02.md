## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-08T09:52:39Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `cicd-pipeline.md` §三「資料庫存取」列 ＋ §四；`infrastructure-specification.md` §四「自架 runner」列 | 清除 workflow 的 `docker compose exec -T db psql` 調用，設計中從未指明等效於 `deploy.yml` 的 `-f deploy/docker-compose.deploy.yml --env-file deploy/.env` 的專案固定方式（`deploy.yml` 全部 docker compose 呼叫都帶 `-f`，見 `deploy.yml:124\,137\,198\,250`）。更關鍵的是：`infrastructure-specification.md` §四已明文指出「本單元是第一個在自架 runner 上排程觸發的 workflow」，但從未分析清除與 `deploy.yml` 共用同一自架 runner 時的互動——若兩者恰好同時被排入（`deploy.yml` 以 `on: pull_request` 觸發、清除以 `on: schedule` 觸發，二者 `concurrency` group 不同，GitHub 不會互相序列化；是否自然序列化取決於該 runner label 底下實際登記的 runner 行程數，設計文件未查證此點），清除的 `BEGIN...COMMIT` 交易可能恰好與 `deploy.yml` 的 `docker compose up -d --remove-orphans` 重建 `db` 容器的窗口重疊，造成連線在交易提交邊界附近被中斷——這是一種 CI 不會抓、且牽涉到 `OPEN-ID9-4` 已承認「清除不可回滾」的操作之上的額外風險面，目前完全未被記載。 | 在 `cicd-pipeline.md` 補一節：(1) 明確固定清除 workflow 的 compose 呼叫方式（帶 `-f deploy/docker-compose.deploy.yml --env-file deploy/.env` 或等效機制，不依賴預設工作目錄）；(2) 查證該自架 runner label 底下登記的 runner 行程數，若為單一行程則記載「天然序列化，不需額外 concurrency 群組」，若可能有多行程則須新增與 `deploy.yml` 共用的 concurrency 群組或等效互斥機制，並記載最壞情況（交易邊界連線中斷）的實際後果（連線中斷早於 COMMIT 確認時，PostgreSQL 會回滾該交易，不會留下部分寫入；但此結論未被本站驗證或寫下，應補上）。 | New |
| R-02 | Minor | `cicd-pipeline.md` §五之一；`traceability.json` `OPEN-ID9-4` | `OPEN-ID9-4` 要求的 dry-run 僅執行 `SELECT count(*)`。這驗證的是「有沒有命中」，不驗證「命中的是不是對的那批列」——一個把 `expires_at` 與 `created_at`寫反、或時區換算錯誤的選取條件，仍可能回一個看起來合理的非零數字而通過人工目視，且這恰好是 `OPEN-ID9-4` 自己點名的「不可回滾操作的前置驗證」所要防的那類錯誤。 | 在 `code-generation` 的 blocking 檢查項中，把 dry-run 的輸出由單一 count 加強為至少印出選取範圍的邊界（如最舊與最新的 `expires_at`／`occurred_at` 各一筆，或抽樣 N 筆的 id ＋ 時間戳），讓人工核對能看到「選到的是哪些列」而非只看到「選到了幾列」。 | New |

### 摘要

- `new-design-problem`：2（R-01、R-02）
- `pre-existing-unreviewed`：0
- `propagated-from-upstream`：0

本站的核心交付物（`NFR7.13` 的監看機制）設計推理嚴謹、取捨誠實（代理指標 vs 直接指標的對照表、`issues: write` 無先例的自我更正、監看鏈在哪裡停止的理由都寫明），且本次逐一開檔核對的全部引用（`deploy.yml:27/146-148/402`、`daily-digest.md:13` 的 `permissions`、`user_router.py:533/695`、`backend/tests/helpers.py` 的 `make_session()`、`contract-summary.md:389`、`requirements.md:794` 的 `OQ-13`、`nfr-design/security-design.md §四` 的 ADR-0006 表、7 個既有排程 workflow 全部 GitHub 託管的查證）**事實與定位均準確**，無一處像本 intent 先前教訓記錄過的「內容對行號錯」或「行號對內容錯」。兩項發現都是本站補強的新發現，不構成對上游或現有設計判斷的否定，READY。

### 覆蓋範圍

**已查證**：
- (a) 監看機制可行性——`gh api .../runs?status=success` 搭配 `actions: read` 的權限模型正確；7 個既有排程 workflow 全數跑在 GitHub 託管 runner（實測 `grep` 確認，非 9 個檔案而是 7 個唯一 workflow，`.lock.yml` 為 gh-aw 編譯產物非獨立 workflow）；3 天門檻的理由站得住；`status=success` 過濾的必要性（`ID9-SUCCESS-FILTER`）正確。
- (b) 三個既列的 CI 盲點（`RETURNING *`、步驟拆分破壞交易邊界、`runs` 預設含失敗）逐一核實為真；另找出第四個——R-01（並發／連線路徑風險），以及確認「單一 `psql -c`」措辭本身足以防止「多個 `-c` 旗標＝多筆交易」這個潛在誤讀，不另立發現。
- (c) 系統 actor 無回歸的三項逐一開檔核對：`user_router.py:695`／`:533` 逐字相符，`make_session()` 的 `create_all()` 確認不執行 seed；另額外查證 `docker-compose.test.yml`（e2e 用）**確實**掛載 `schema_rbac.sql` 到 `docker-entrypoint-initdb.d`，但相關 e2e 斷言（`frontend/tests/e2e/regression.spec.ts`）用的是相對計數（`totalBefore`）或 `is_active` 過濾路徑的同一測項，未見任何依賴絕對筆數的斷言會被系統 actor 列打破。
- (d) 監看鏈停止點的論證（依賴面嚴格縮小）站得住，殘留風險誠實記載為 `OPEN-ID9-1`。
- (e) 不可逆性論證正確；dry-run 驗證強度提出 R-02。
- (f) 全部列出的 `file:line` 引用逐一開檔核對，無誤。
- (g) `infrastructure-specification.md §六` 的 ADR-0006 表與 `nfr-design/security-design.md §四` 逐格比對一致，未改動任何上游判定；`cicd-pipeline.md` 與 `monitoring-design.md` 之間的門檻值（3 天）、權限集合（`actions: read`／`issues: write`）互相一致；本站四份產出內未見完整可執行 YAML 或超過 15 行的程式片段，符合設計站層級。

**未深入查證（受限於審查範圍與時間）**：
- 未實際連線 GitHub API 驗證 `gh api .../actions/workflows/<id>/runs` 對一個**尚未存在**的 workflow id 的行為（本單元兩個 workflow 都還沒落地，純屬紙面設計，無法以執行驗證）。
- 未查證該自架 runner 標籤 `[self-hosted, linux, x64, cloud360]` 底下實際登記的 runner 行程數量（這正是 R-01 要求補查的項目，審查本身無法存取該主機）。
- 未對 `nfr-design/security-design.md` 的審查歷史（`reviews/review-01.md` 等）做完整複核，僅引用其 §二／§三／§四 的定案內容作為上游依據核對一致性。

VERDICT: READY
