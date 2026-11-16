## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

a11y-gate（U17，packaging）在本站的足跡確實只有一個 devDependency 加一支 Playwright spec，三份產出（infrastructure-specification、cicd-pipeline、monitoring-design）自洽，且逐項寫明「沒有」與其失效條件，可承載本站內容。我抽查的事實都成立：`ui-regression.md` 的 `timeout 3m npm ci`（:174）、`timeout 15m npx playwright test`（:191）、`BASE_URL: http://localhost:8090`（:187）、post-steps 讀 `stats.unexpected`（:284-288）、全檔無 `upload-artifact`；`playwright.config.ts` 的 `fullyParallel: false`／`workers: 1`／CI `retries: 1`（:14,17,18）；`unit-of-work.md:53` 的 standalone 登記；`bolt-plan.md` 的 B8 與交錯順序；`frontend/package.json:25` 只在 devDependencies。未發現 Critical 或 Major；以下六項 Minor 是不精確或缺少歸屬之處，不阻擋。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Minor | construction/a11y-gate/infrastructure-design/cicd-pipeline.md 第一張表 deploy.yml 列（「否」） | 該列判定「deploy.yml 否」並稱 devDependency 不進產品 image。最終 image 確實不含它（frontend/Dockerfile 為多階段，final 階段只複製 dist），但 build 階段 `RUN npm ci`（frontend/Dockerfile:8）會安裝全部 devDependencies，所以新套件與 lockfile 一致性同樣會影響 docker-build job 與 deploy 的映像建置。A11Y-S2 只把 lockfile 不同步的後果歸給 CI 的 npm ci。 | 在該列與 Stage→Gate 表補上「docker-build 與 deploy 的 build 階段也會 npm ci」，並說明新套件只存在於丟棄的 build 階段。 | New |
| R-02 | Minor | construction/a11y-gate/infrastructure-design/infrastructure-specification.md「CI 資源成本」表與 Shared Infrastructure 表 | 成本表寫「多兩個套件（@axe-core/playwright 加 axe-core）」，Shared 表寫「只新增一個 devDependency」。`frontend/package.json` 只列 @axe-core/playwright（:25），axe-core 是它的傳遞相依。兩處並不矛盾，但沒有說明，讀者可能以為要在 package.json 手動加兩個。 | 成本表註明 axe-core 為傳遞相依，直接宣告的只有一個。 | New |
| R-03 | Minor | construction/a11y-gate/infrastructure-design/monitoring-design.md Metrics 表「flaky 數」列與「基準清單筆數」列 | 兩項訊號沒有機制也沒有人：flaky 數「不擋，但非 0 時須看」，而 ui-regression 的 post-steps 只回報（echo）flaky，沒有人被指定去看；基準清單筆數「只准減少」完全靠審查把關，沒有任何機械檢查，來源欄寫 a11y-baseline.json 容易被讀成自動訊號。 | 各補一欄「誰看、何時看」，並明寫基準筆數只准減少是人工審查規則而非機械閘門（或指向 A11Y-S9 規則 3 在 spec 內的對應斷言，若有）。 | New |
| R-04 | Minor | construction/a11y-gate/infrastructure-design/cicd-pipeline.md「閘門本身的回滾路徑」第 2 點 | 以 describe 層級 `test.skip` 暫時關閉閘門的說法有兩處未寫明：(a) skipped 在 post-steps 的 `stats.unexpected` 中不算失敗，所以整支被跳過時 PR 為綠，「看得出被關掉」只靠 TCMS 回報，而該回報是 best-effort；(b) 只 skip 單一掃描點時，過期檢查會因讀回的檔案數不足 18 而失敗（nfr-design/security-design.md:93），所以第 2 點只有在 describe 層級整體 skip 才成立。 | 補寫這兩點：只准整體 skip，並要求 skip 時附 issue 連結且在 PR 說明；單點 skip 不可行。 | New |
| R-05 | Minor | construction/a11y-gate/infrastructure-design/infrastructure-specification.md（全檔）與 monitoring-design.md Logs 段 | ADR-0006 四面向在本站沒有逐項判定表，散落在各處：network exposure 有（Networking 列與失效條件），audit logging 有（證據留存缺口，如實寫明綠燈零留存、紅燈只留 PR 留言摘要），IAM 與 encryption 只隱含於「無 secret」。另「GitHub-hosted runner」是斷言，`ui-regression.md` 沒有顯式 runs-on，我未能自該檔證實。留存缺口交給 build-and-test 判定，但未指明判定所需的決策者與不補的後果。 | 加一張四行小表（IAM、encryption、network exposure、audit logging，各附判定與理由，不適用者寫理由）；把 runner 類型改為引用其出處或改寫為「依 ui-regression 既有設定」；留存缺口註明由誰決定及未補的後果。 | New |
| R-06 | Minor | construction/a11y-gate/infrastructure-design/infrastructure-specification.md「CI 資源成本」測試時間列；cicd-pipeline.md Stage→Gate 表 timeout 列 | 這兩處的掃描次數（18）與上游不一致的部分來自上游：nfr-requirements/security-requirements-corrections.md:86 寫 17 次、security-requirements.md H-2 寫 14 次，而 nfr-design 的 18 個掃描點才是正確計數（21 個 test 中 18 次 axe、1 個手機寬度不跑 axe、2 個基準檢查）。本站採 18 正確，但沒有說明為何與 H-2 的 14／17 不同，下一位讀者會以為是錯誤。另 code-generation 已本機實測 13.4s（code-summary.md:130），本站「未量測」為凍結當時狀態。 | 加一句「以 nfr-design 的 18 為準，取代 H-2 的 14 與更正附錄的 17」，並註明本機已有 13.4s 的初步實測、CI 實測仍交 build-and-test。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| traceability.json 檢視（infrastructure-design/traceability.json） | 13 個 upstream_ids 均有 OK 或 N/A 落點，N/A 皆附理由 | 結構完整；N/A 的 C-02／C-06／C-07／D-01／D-02 屬 spec 內部結構，確無基礎設施面 |
| 事實抽查：ui-regression.md、playwright.config.ts、package.json、frontend/Dockerfile、unit-of-work.md:53、bolt-plan.md | 逐項與產出宣稱相符，唯 R-01、R-02 所述兩處不精確 | 設計與落地無實質矛盾；無 upload-artifact 的缺口屬實，產出如實記載 |
| 依規定未執行任何會寫檔或產生快取的指令 | 未執行 | 僅用唯讀指令 |
