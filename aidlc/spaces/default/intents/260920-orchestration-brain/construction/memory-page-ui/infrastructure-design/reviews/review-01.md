## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

「零新基礎設施」的核心主張成立：我逐項抽查 nginx 代理（`frontend/nginx.conf:16-17`）、`playwright.config.ts:10` 的 testDir、`ui-regression.lock.yml:558` 的裸 `playwright test`、`docker-compose.test.yml:102` 的 `EMBEDDING_PROVIDER` 預設 stub，行號與內容皆正確，且已落地的 `memory-page.spec.ts` 與 `memory_facade._authorize_approved` 也與設計方向一致。缺口在三處：ADR-0006 四面向沒有逐項判定表（project.md 明定須用表）、`DELETE` 403 宣告的設計主張已被程式推翻、以及 Sidebar 位置依據的 `:209-216` DEMO 區塊已不存在。三項皆非 Critical，故判 READY；其中兩項建議在關卡上交由人裁決。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-page-ui/infrastructure-design/infrastructure-specification.md（全檔）、monitoring-design.md §二 | project.md 與 requirements-analysis:c4 要求 ADR-0006 四面向（IAM、encryption、network exposure、audit logging）以逐項判定表呈現。本站只散見於各檔：network 在 §一「網路」列、encryption 只靠 NFR7.90 一句帶過、audit logging 在 monitoring-design.md §二 以「屬 U8」轉移、IAM 只在 §二 共用檔表提到「已核准」檢查。沒有任何一處明列四面向判定與不適用理由。 | 補一張四面向判定表，每格附理由與證據；audit logging 一格須指出 U8 的具體承接位置，而非僅寫「屬 U8」。 | New |
| R-02 | Major | construction/memory-page-ui/infrastructure-design/cicd-pipeline.md §三 表第二列、§四「同批次約束」 | 設計稱「`DELETE` 現刻意不宣告 403（`[D1]`=A）」，但已落地的 `backend/services/memory_router.py:249` 對 DELETE 宣告了 `responses={**FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE}`，即 403 已宣告。設計與程式矛盾；程式一側才是對的，因為 facade 的 `_authorize_approved`（`memory_facade.py:184`）使 pending 帳號對 DELETE 也會得到 403，不宣告反而讓 OpenAPI 說謊。此外 §三 第三列的 `test_memory_contract.py` `C3` 宣稱「router 不做授權判定」，我未讀該測試，但 router 檔頭 `:39` 已明寫授權落在 facade，兩者需一併核對。 | 在 cicd-pipeline.md 加更正註記說明 DELETE 已宣告 403 且為正確；確認 `openapi.json` 與 `api.d.ts` 已同步重 dump（以 `dump_openapi.py --check` 結果為證）。 | New |
| R-03 | Minor | construction/memory-page-ui/infrastructure-design/infrastructure-specification.md §二 第二列 | 「置於 `:209-216` DEMO SCOPE 區塊之外」引用的區塊已隨 U13 移除；現況 `Sidebar.tsx:242` 註解自述 DEMO 已移除，「我的記憶」在 `:248`。引用本身已失效，且 `grep DEMO SCOPE` 在 Sidebar.tsx 零命中。 | 改為描述現況位置（「專案」之後的獨立 div）並註明原行號已隨 U13 失效。 | New |
| R-04 | Minor | construction/memory-page-ui/infrastructure-design/cicd-pipeline.md §一 表「既有 spec」列 | 稱 `frontend/tests/e2e/` 下僅三支 spec，現況為十個檔（含 `a11y.spec.ts`、`a11y-baseline.json`、`memory-page.spec.ts` 等）。「新 spec 丟進目錄即被撿到」的結論不變，但計數是快照。另 `a11y.spec.ts` 為既有閘門，本站未討論新頁是否需納入 a11y 掃描點。 | 改為不寫具體計數，或標明查證時間；補一句 a11y 基準是否需涵蓋 `/memory`。 | New |
| R-05 | Minor | construction/memory-page-ui/infrastructure-design/infrastructure-specification.md §二 第三列 | 後端檢查的落點寫成「router 或 facade，由 code-generation 定案」，本站留了開放決策。程式已定案為 facade，但設計文件未回寫；對只讀設計的下游，爆炸半徑與回滾描述無法判定落點。 | 回寫落點為 facade，並註明其對 `Principal.is_approved` 的依賴。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 抽查 nginx／playwright／ui-regression／compose 行號 | 4 項皆正確 | 「零新基礎設施」的主要證據可信 |
| 抽查 Sidebar／App.tsx／memory_router／memory_facade | `:209-216` 失效；DELETE 已宣告 403；facade 已含 `_authorize_approved` | 對應 R-02、R-03、R-05 |
| 依指示未執行任何測試／lint／建置 | 未執行 | 僅靜態抽查 |
