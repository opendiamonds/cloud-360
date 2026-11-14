## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U16 是純前端單元，精簡形式（by-reference）對「零後端、零部署元件、零環境變數」這個主張是足夠的：我核對了 `ci.yml:197-198` 的 lint 步驟、`frontend/Dockerfile`（正式建置後由 nginx 服務，故請求計數類 e2e 對 CI stack 即為正式建置）、`eslint.config.js` 已落地的選單區塊（含 `D-06` 補的 `window.*` 儲存選擇器）、`unit-of-work.md:52` 的 embedded 宣告、`bolt-plan.md:338`／`:509` 的 B7 歸屬，皆與產出相符；選單檔案內也查無主控台、儲存、`innerHTML`、`RegExp`、`new WebSocket`。唯一實質缺口在共用基礎設施：產出把後端連線池列為共用資源，並引用兩個並未討論連線池的段落作為處置依據，而 `fanoutQueue.ts` 自己的註解明說並行上限 4 保護不了連線池。其餘為回滾、驗證機制與追溯的 Minor。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/object-picker-ui/infrastructure-design/infrastructure-specification.md > Shared Infrastructure 表「後端 SQLAlchemy 連線池」列；traceability.json > OPN-01 | 該列處置欄寫「`performance-design.md` §一之三、`D-03`」，但實查 `nfr-design/performance-design.md` 全文無「連線池／池」字樣，§一之三只是請求數觸發表，`D-03` 談的是重抓與 `reloadKey`，兩者都不承載連線池處置。`frontend/src/projects/fanoutQueue.ts:18-21` 的註解逐字寫明並行上限 4「不是連線池的保護機制」，後端為單一 uvicorn 進程（`backend/Dockerfile:30`，無 workers 參數）、`database.py:37` 的 `create_engine(db_url)` 用預設池（5＋10＝15 條），「約 3 位使用者同時進入系統數多的專案即可耗盡」。本單元每位使用者的搜尋補抓是 4 並行、共 P−已載入數 個請求（`N-02` 第 5 點，P＝專案數），4 位使用者同時搜尋即可超過 15。池耗盡的爆炸半徑是全站所有 API（單進程、共用池），不只是選單；規格卻只寫「補抓同時最多 4 個請求」，沒有總量、沒有容量上限假設、沒有耗盡時的行為（被選單的 `error` 態吸收，還是拖累他人）。`traceability.json` 把 `OPN-01` 判 OK 並指向這一列，但該列沒有寫 `N-02` 第 5 點的上界公式。 | 在 Shared Infrastructure 補一段容量說明：寫出每位使用者的請求總量公式（開啟 1～2、搜尋補抓至多 P−已載入數）、並行 4、單進程池 15 的算式與可同時搜尋的使用者數；明寫耗盡時後端請求排隊或逾時的後果與本單元的降級（群組 `error`＋重試）；把這項列為「接受的殘留」並交關卡知情，或指定承接（例如補抓前檢查專案數上限、或交 `U23` 的 `fanoutQueue` 加全域節流）；同時修正該列的引用，改指實際承載處。 | New |
| R-02 | Minor | construction/object-picker-ui/infrastructure-design/infrastructure-specification.md > Deployment 表「部署路徑」列；cicd-pipeline.md > 合併順序 | 精簡形式未寫回滾路徑。本單元與 `U15` 同屬 B7，且修改 `U14` 的 `ContextBar.tsx`、`U17` 的 `a11y.spec.ts` 與共用的 `eslint.config.js`；squash 進 `ut` 後若部署失敗，`deploy.yml` 的 rollback job 還原的是整個 B7（含 `U15`），而非只退 U16。產出也沒說明 U16 退出後 `ContextBar` 的行為是否回到 `U14` 原狀（入口鈕消失屬預期）。`phases/operation.md` 與 `project.md ## Deployment` 都把回滾視為與實作同一條 pipeline 的環節。 | 在 Deployment 表補一列回滾：沿用 `deploy.yml` 既有 rollback、回滾粒度為 B7 整個 squash commit、U16 單獨退出的影響（選單入口消失、其餘 `U14` 功能不變）。 | New |
| R-03 | Minor | construction/object-picker-ui/infrastructure-design/cicd-pipeline.md > WS 漂移閘門列與 infrastructure-specification.md > Environments；traceability.json > OPN-22、OPN-23 | `OPN-22`（`package.json` 鍵集合不變）與 `OPN-23`（`a11y-baseline.json` 的 `entries` 維持空陣列）在 traceability 判 OK，但 cicd 與規格只寫了 `ws-contract.json` 前後雜湊比對一項驗證機制；另兩項的比較基準與取值指令只在 `nfr-design/logical-components.md` §三，infrastructure-design 本站沒有承接，也沒有說明這三項比對是人工步驟（寫進 code-summary）而非 CI 閘門。讀者會以為三者都有 CI 守門，實際上三項都不在任何 workflow 內。 | 在 cicd-pipeline.md 增列一小表，三項比對各寫：由誰、何時、用什麼指令取值、結果落在哪份產出；並明說它們不是 CI 閘門，防線是 code-summary 的人工記錄。 | New |
| R-04 | Minor | construction/object-picker-ui/infrastructure-design/monitoring-design.md > 指標與 log；告警 | 「零新 metric、零新告警」在無前端遙測的 repo 是誠實的，但規格沒有說明 R-01 的失敗模式（`/api/hierarchy/*` 在補抓期間回 5xx 或逾時）現況由什麼觀察：只列了 CI 時期的訊號，沒有任何上線後的可觀察點（例如 uvicorn access log 的 `/api/hierarchy/projects/{id}/systems` 5xx 計數），也沒有明寫「上線後無訊號」是接受的殘留。 | 補一行：上線後唯一可用的訊號（後端 access log）與其查法，或明寫此處無運行期訊號並列為殘留。 | New |
| R-05 | Minor | construction/object-picker-ui/infrastructure-design/traceability.json > upstream_ids | `upstream_ids` 只取 10 條，略過本單元 23 條需求中 `OPN-26`（`team.md` A／B／C 適用判定）與 `OPN-25`（突變結果記錄）等與交付管線有關的條目；其中 `OPN-26` 的 C 規則（新畫面須 e2e）正是 `cicd-pipeline.md` 的 ui-regression 列在承載的，卻未列入覆蓋。`NFR2.160`、`NFR11.160` 判 N/A 的理由正確，但整體選取準則沒寫，無法確認是刻意精簡還是漏列。 | 在 traceability 的 note 或 cicd-pipeline 補一句選取準則，並把 `OPN-26` 判為 OK 指向 ui-regression 列。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 引用核對 `ci.yml:198` | `npm run lint` 位於 197-198 | 與 cicd-pipeline.md 相符 |
| 引用核對 `unit-of-work.md:52`、`bolt-plan.md:338`／`:509` | 皆相符（embedded、B7 含 U15／U16） | 部署路徑主張成立 |
| `frontend/Dockerfile`、`playwright.config.ts` | nginx 服務正式建置；`npx playwright test` 跑整個 tests/e2e | 請求計數類 e2e 於 CI 即為正式建置，`D-01` 的前提成立 |
| 選單檔案靜態查詢（console、儲存、innerHTML、RegExp、new WebSocket） | 僅註解命中，程式碼 0 | 與 lint 區塊及 `security-design.md` 相符 |
| `eslint.config.js:40-110` 對照 `security-design.md` §一 | 區塊已落地並含 `D-06` 的 `window.*` 選擇器 | 設計與落地一致 |
| 連線池主張 grep（`performance-design.md`） | 0 命中 | 支持 R-01：引用的處置段落不存在連線池內容 |
| 本審查未執行任何測試、建置或 lint | 依 brief 禁止產生快取 | 不對 e2e 綠燈作任何斷言 |
