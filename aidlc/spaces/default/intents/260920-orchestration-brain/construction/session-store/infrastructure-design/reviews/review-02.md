## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary
本單元的基礎設施增量（`noeviction`、`BRAIN_SESSION_HISTORY_MAX`、Redis 客戶端依賴）都有落點，且已落地的程式與設定（`deploy/render-env.sh:139`、兩份 `.env.example`、`docker-compose.test.yml:113`、`docker-compose.deploy.yml:130`／`:258-261`）與設計一致。前次 review-01 的兩項實質發現（R-01、R-02）在凍結的產出中仍原樣存在，但已落地的 `deploy.yml` 已經改對：還原驗證步驟輪詢 120 秒而非等 healthcheck，且註解逐字撤回「整個 stack 剛重啟過」的錯誤主張。所以這兩項是「設計文件錯、程式對」，列為 Major 而非 Critical，由人在關卡上裁決是否接受設計文件落後於程式。ADR-0006 四面向：IAM（ACL 身分）、network exposure（無 `ports:`）、audit logging（日誌白名單）皆有落點，encryption 以「compose 內部網路、無 TLS」隱含處理但未逐字判定（見 R-05）。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/session-store/infrastructure-design/cicd-pipeline.md > 三「步驟設計」第 3 列（第 69 行） | 前次 review-01 已提（R-01）。步驟 3 寫「重啟 redis 容器，等 healthcheck 轉綠」，與同單元 nfr-design 的 reliability-design §五「不依賴 healthcheck 判斷可用性」以及 infrastructure-specification §三自承的「passes during AOF loading」直接矛盾。已落地的 `.github/workflows/deploy.yml`（步驟 `Verify sessions survive a Redis restart`，約 447-566 行）改為以 app ACL 身分輪詢最長 120 秒（第 533 行的錯誤訊息可證），所以**程式是對的、設計文件是錯的**。 | 把第 3 列改為「以 app 身分輪詢實際讀取，直到成功或逾時」，或在文件加更正註記指向 `deploy.yml` 的實作；下游依文件重寫此步驟的人才不會退回 healthcheck 判準。 | New |
| R-02 | Major | construction/session-store/infrastructure-design/cicd-pipeline.md > 三「三項必須寫進產出的代價」第 2 項（第 85-87 行） | 前次 review-01 已提（R-02）。文件稱「緩解：放在重啟過整個 stack 之後，額外一次重啟不新增使用者可感知的損失」。`deploy.yml:129` 的 `up -d --build --remove-orphans` 無 `--force-recreate`，redis 設定未變時不會被重建，故此步驟在多數部署是**唯一一次**讓 staging session 中斷的動作。已落地的 `deploy.yml` 註解（約 437-446 行）已逐字撤回該主張並改以「放最後、其餘檢查通過後才中斷」處理，**程式的說法是對的**。 | 改寫該項代價：明說每次部署都會新增一次 Redis 中斷，並接受該代價，或限定為 redis 服務定義有變時才跑；與 `deploy.yml` 註解對齊。 | New |
| R-03 | Minor | construction/session-store/infrastructure-design/traceability.json（整檔，`upstream_ids`） | 前次 review-01 已提（R-03）。實測 `grep NFR8.42 traceability.json` 無命中，但 `infrastructure-specification.md` 表格第 1 列以名稱引用 `NFR8.42`，且 `infrastructure-design-questions.md` §一 已履行 nfr-requirements review `R-04` 指派的「確認 CI 測試 stack 是否需同步 noeviction」。已履行的義務未進追溯檔。 | 於 traceability.json 新增 `NFR8.42` 條目，指向 infrastructure-design-questions.md §一 與 infrastructure-specification.md 第 1 列。 | New |
| R-04 | Minor | construction/session-store/infrastructure-design/infrastructure-specification.md > 一（`docker-compose.deploy.yml` 的 `:234-235`）與二（`deploy.yml:195`）；cicd-pipeline.md > 三（`deploy.yml:195`） | 行號引用與現況不符，屬「內容對、定位錯」。現況：redis 的 `--maxmemory` 在 `docker-compose.deploy.yml:258`、`--maxmemory-policy` 在 `:260`，`noeviction` 註解在 `:261`；`Verify the Redis ACL actually took effect` 步驟在 `deploy.yml:200`（原寫 195）。這些行號是本單元自己的程式落地後才位移，但文件宣稱為「實讀」。 | 更新行號，或改以步驟名稱／鍵名定位而非行號。 | New |
| R-05 | Minor | construction/session-store/infrastructure-design/infrastructure-specification.md > 二 Networking／五（缺 encryption 判定） | project.md 要求 ADR-0006 四面向在產出中明列。本檔對 IAM（ACL 雙使用者）、network exposure（無 `ports:`）、audit logging（日誌白名單，引自上游）有處置；encryption 沒有任何一列判定。Redis 連線為 compose 內部網路明文，session 內容（對話文字）在 AOF volume 上未加密落地，這是需要明文接受或標為不適用的事實，而非省略。 | 補一列 encryption 判定：傳輸（compose 內網明文，理由）與靜態（AOF volume 未加密，理由與接受範圍）。 | New |

### Validation Tool Results
| Tool | Result | Interpretation |
|------|--------|----------------|
| 檢視 `deploy.yml` 還原驗證步驟 | 有輪詢（120 秒）、放最後、註解撤回錯誤主張 | 確認 R-01、R-02 為「設計文件落後於程式」，程式一側是對的 |
| 檢視 env 契約落點 | `render-env.sh:139`、兩份 `.env.example`、test compose `:113`、deploy compose `:130` 皆在 | 增量第 2 項完整落地，無遺漏 |
| grep `NFR8.42` traceability.json | 0 命中 | 確認 R-03 |
| 未執行測試／lint／建置 | 依 brief 禁止產生快取 | 本審查僅靜態讀取 |
