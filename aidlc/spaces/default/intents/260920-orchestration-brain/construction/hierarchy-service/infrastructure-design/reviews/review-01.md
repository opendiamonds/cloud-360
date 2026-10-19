## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary
「零基礎設施變更」的判定成立：`unit-of-work.md:43` 逐字為 embedded 新 router，`backend/main.py:111` 以 `app.include_router(hierarchy_router, prefix="/api/hierarchy")` 掛入同一 process，未見新服務、監聽埠或環境變數。409 顯式宣告也確實落地：`openapi.json` 中 projects POST、projects DELETE、systems POST、systems DELETE 皆含 `409`，logger 命名也依 `cloud360.hierarchy_service` 形式。缺口是部署時序（本單元端點依賴 U4 的部署期遷移，而本站未寫明）、「五個 path」與落地事實不符、NFR8.1 的二元判準漏列 `.github/workflows/deploy.yml`，以及 ADR-0006 四面向在本站沒有自己的落點。無 Critical，Major 一項，故判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/hierarchy-service/infrastructure-design/infrastructure-specification.md §一 第二列「infrastructure already defined」 | 本站以「U1 已交付基礎設施」為由判定無部署面，但沒有寫出本單元唯一的部署時序前提：`projects`／`systems`／`diagram_change_records` 三表由 U4 的 `hierarchy_migration.py` 建立，且該模組檔頭逐字寫明「部署期的獨立指令，不掛在啟動路徑上，main.py 不匯入本模組」。`grep` 顯示 `.github/` 與 `deploy/` 下沒有任何地方呼叫 `run_hierarchy_migration.py`，只有 `DEPLOY.md:348`、`:408`、`:1439` 要求人工執行「在應用未接流量的窗口內」。因此 `hierarchy_router` 在 deploy-on-merge 後、遷移未跑的環境中，所有 `/api/hierarchy/*` 端點會因表不存在而失敗，而 CI 與 `/health` 都不會發現。這正是 NFR8.1 想防的「無聲降級」類失敗，卻沒有被本站列為前置條件。 | 在 infrastructure-specification.md 增列「部署前置條件」：本單元端點上線前，U4 遷移必須已在目標環境成功執行（結束碼 0）。指名承載處（`DEPLOY.md` 2.2.7）以及未跑時的可觀察症狀。若認為應由 deploy.yml 自動化，則記為指派給 U4 或 build-and-test 的開放事項，不得留白。 | New |
| R-02 | Minor | construction/hierarchy-service/infrastructure-design/cicd-pipeline.md §一 第 1 列、traceability.json NFR5.1 | 文中寫「五個 path 落地後同步重 dump」。落地的 `openapi.json` 在 `/api/hierarchy` 下有 6 個 path、7 個 operation（`/projects` GET＋POST、`/projects/{project_id}` DELETE、`/projects/{project_id}/systems` GET＋POST、`/systems/{system_id}` DELETE、`/diagram-changes` GET）；`hierarchy_router.py` 的 `@router` 裝飾器同為 7 個。「五個」與事實不符（可能是設計期的舊計數，`diagram-changes` 或 U23 之後新增的未被納入）。這是 `project.md` 要求「可計算的數字先算再寫」的同型錯誤。 | 以 `openapi.json` 實算的 path／operation 數取代「五個」，並標明取得方式（例如對 `/api/hierarchy` 前綴的 paths 計數）。 | New |
| R-03 | Minor | construction/hierarchy-service/infrastructure-design/infrastructure-specification.md §二 判準 2 | NFR8.1 的機械判準只列 `deploy/`、`render-env.sh`、`.env.example`、`docker-compose.*.yml`、`nginx.conf`，漏了 `.github/workflows/deploy.yml`；而 cicd-pipeline.md §一 另寫「不改 `deploy.yml`」，兩處的禁止清單不一致。工作樹目前確實有 `.github/workflows/deploy.yml` 的 53 行新增（U14 6a 的 WebSocket 子協定檢查，非本單元），顯示該檔會被同分支的其他單元改動，沒有判準時無法分辨哪些屬於本單元。 | 把 `.github/workflows/deploy.yml` 補進 NFR8.1 的二元判準，並寫明判定範圍是「本單元的 diff」，避免與同分支其他單元的改動混淆。 | New |
| R-04 | Minor | construction/hierarchy-service/infrastructure-design/infrastructure-specification.md（全檔） | `project.md` 要求涉及 IAM、network exposure、audit logging 的變更須在該 stage 產出明列 security 影響與處置，encryption 亦須逐項判定。本站只在表內引用 network exposure（`functional-spec.md` §七之三），IAM、encryption、audit 三面向沒有任何落點，也沒有指向 nfr-design/security-design.md 的 ADR-0006 判定表。本單元雖無基礎設施變更，但「為何四面向在基礎設施層皆無新增」仍應逐項寫下（例如 encryption：沿用既有 PostgreSQL 連線與 TLS 設定，無新傳輸通道）。 | 在 infrastructure-specification.md 增一張四面向逐項判定表，每格附理由並引用 security-design.md 對應段落；不適用者寫明原因。 | New |
| R-05 | Minor | construction/hierarchy-service/infrastructure-design/monitoring-design.md §一 | 「其存活與延遲已被該 process 的既有監控涵蓋」引用 `construction/brain-infra/infrastructure-design/monitoring-design.md`，但本站未說明該文件實際涵蓋哪些指標，也沒有指出 `/api/hierarchy/*` 的錯誤率（特別是 5xx，對應 R-01 的表不存在情境）是否可由既有監控觀察。`phases/operation.md` 要求每個新元件至少有一個健康指標與一個錯誤率指標。本審查依範圍規定未開啟兄弟單元檔案，無法自行驗證該引用。 | 在本站以一句話寫明所依賴的既有指標名稱（健康與錯誤率各一），或把「未驗證」記為開放事項交由 U1 確認。 | New |

### Validation Tool Results
| Tool | Result | Interpretation |
|------|--------|----------------|
| `openapi.json` 解析（`/api/hierarchy` 前綴） | 6 個 path、7 個 operation；四個寫入／刪除 operation 皆宣告 `409` | NFR5.2 的 409 顯式宣告已落地，設計與實作一致；同時證實 R-02 的計數錯誤 |
| `grep run_hierarchy_migration`（`.github`、`deploy`、`DEPLOY.md`） | 僅 `DEPLOY.md` 命中，CI／deploy 無自動呼叫 | 支持 R-01：遷移是人工步驟 |
| `grep getLogger`（`services/hierarchy_*.py`） | 四支皆為 `cloud360.<module>` 形式 | monitoring-design 的 logger 命名義務已落實 |
| `main.py:111` | `include_router(hierarchy_router, prefix="/api/hierarchy")` | 與「embedded 新 router、零新進程」一致 |
| `validate_env_contract.py`／`unittest` | 未執行 | 依 brief 禁止產生快取或寫檔，不在本審查內執行 |
