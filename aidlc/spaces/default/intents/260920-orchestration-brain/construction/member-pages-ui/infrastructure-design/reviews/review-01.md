## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U24 member-pages-ui 的 infrastructure-design 採「零新基礎設施」的精簡形式，結論經抽查成立：`frontend/nginx.conf:16-17` 的 `location /api/` 確實涵蓋 membership 端點，`ui-regression.lock.yml:558` 為裸 `npx playwright test`，`playwright.config.ts:10` 的 `testDir` 為 `./tests/e2e`，`deploy/docker-compose.test.yml` 的 backend 環境變數皆自帶預設，`Layout.tsx` 已依設計直接渲染 `ReselectionBanner` 而不走 `slotRegistry`（`slotRegistry.tsx:9-10` 的靜默 no-op 引用正確）。唯一實質缺口是 CI/CD 檔把 `ui-regression` 描述為能抓「前端讀錯 role」的唯一有效閘門，但已落地的 `member-pages.spec.ts` 全部以 `page.route()` 攔截、不打真實後端，這個限制沒有被寫進閘門判定。其餘為行號引用過期與 ADR-0006 四面向未成表的小問題。本站未派審查員，故本次為首次獨立複驗；`git log --all -- deploy/nginx.conf` 一項因審查環境的 shell 限制無法執行，僅以 `ls deploy` 與 workflow 檔內容佐證。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/member-pages-ui/infrastructure-design/cicd-pipeline.md > 二、四（第 6 道閘門）、五 | 文件把 `ui-regression` 寫成對「前端把伺服器回傳的 role 讀錯或漏讀」唯一有效的一道，並說它「對每個 PR 自動起的短生命週期 stack」執行。已落地的 `frontend/tests/e2e/member-pages.spec.ts:6` 自述「全部走 page.route() 攔截，不打真實後端」，`:138` 以 `**/api/membership/**` 整段攔截。因此 stub 的回應形狀是手寫的，真實後端的 `MemberView.role` 若改名或改型，e2e 仍綠燈；第 4 道 OpenAPI drift 又只在後端改 schema 且前端用了產生型別時才有保護，而第 3 道表內已承認手寫型別會放行 `any`。文件把「品質完全押在第 6 道」寫成事實，卻沒寫出第 6 道在本單元其實碰不到真實 nginx、真實後端與真實 DB。 | 在 cicd-pipeline.md 第四節補一條誠實記載：本單元 e2e 為純前端 stub，真實 nginx 到後端的 membership 路徑與回應形狀在 CI 內沒有任何自動化覆蓋；並寫明前後端形狀一致性由誰承擔（例如 U19 的後端 TestClient 測試加 gen:types 產生型別是否被 U24 實際使用）。若無人承擔，登記為開放項。 | New |
| R-02 | Minor | construction/member-pages-ui/infrastructure-design/infrastructure-specification.md > 二（爆炸半徑列） | 文中引用 `App.tsx` 的 `:52／:65／:78／:91／:103／:116` 作為 `Layout` 包覆每個路由的證據。實際 `<Layout>` 出現在 `App.tsx` 第 36、72、85、98、116、134、147、160、180、193、206、219、232 行，六個引用行號有五個對不上（僅 `:116` 巧合相符）。結論（Layout 包覆所有已驗證路由）成立，但定位錯誤，照行號去讀的人會讀到別的內容。 | 以實際行號重寫該列，或改為「`App.tsx` 內共 13 處 `<Layout>`」並附取得方式。 | New |
| R-03 | Minor | construction/member-pages-ui/infrastructure-design/infrastructure-specification.md > 四（查證表 LOCAL-DEV.md:569） | 引用 `LOCAL-DEV.md:569` 為「它自己寫對了」的證據，實際該句在 `LOCAL-DEV.md:588`；同檔 `:641` 的同步規則句才是列出 `deploy/nginx.conf` 的位置，文件沒有引用這一行。內容正確、定位錯誤（前次 review 無記錄，屬首次發現）。另外 `local-dev-drift` 的 workflow 有兩處需修：`local-dev-drift.md:9`、`:58` 與編譯產物 `local-dev-drift.lock.yml:58`，文件只提前者。 | 更正行號為 `:588`，補上 `:641` 與 `local-dev-drift.lock.yml:58`，使 OPEN-ID24-1 的修復範圍完整（改 .md 後須重新編譯 lock 檔）。 | New |
| R-04 | Minor | construction/member-pages-ui/infrastructure-design/infrastructure-specification.md > 二（改動列） | 設計寫「新增交棒橫幅的宿主與操作列兩個節點」且基準為「全檔 22 行」。已落地的 `Layout.tsx` 為 32 行，只新增 `<ReselectionBanner />` 一個節點（`:26`），位置在 `data-slot="cost-banner"`（`:17`）之後、`{children}`（`:27`）之前，位置與設計一致，但節點數與設計不符。這可能是操作列被收進元件內部，但文件沒有交代。 | 說明操作列是否已併入 `ReselectionBanner` 內部，或更正「兩個節點」的敘述，使設計與落地一致（落地的一邊較可信）。 | New |
| R-05 | Minor | construction/member-pages-ui/infrastructure-design/infrastructure-specification.md > 一（部署架構表） | `project.md` 要求每項變更逐一檢查 ADR-0006 四面向（IAM、encryption、network exposure、audit logging），且不得僅以「已有 ADR-0006」帶過。本站的表有網路（`/api/` 反向代理）與儲存／瀏覽器儲存禁用，但 encryption（走既有 Cloudflare Tunnel 的 TLS，未寫明）與 audit logging（前端不寫稽核，屬 U19，未寫明）兩面沒有出現，IAM 只間接見於 `can("K3","edit")`。零變更不等於免判定。 | 在規格內加一張四列判定表，各列一句理由與出處；可引用 nfr-design/security-design.md 的對應段落。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取 `frontend/nginx.conf` | `:16` 為 `location /api/ {`，`:17` 為 `proxy_pass http://backend:8000;` | 規格的反向代理引用正確 |
| 讀取 `ui-regression.lock.yml` | `:558` 為 `run: timeout 15m npx playwright test`；Kiwi 步驟含「must stay stable」與「orphans」註解 | CI 步驟與名稱穩定性約束引用正確 |
| 讀取 `playwright.config.ts` | `:10` 為 `testDir: './tests/e2e'` | 正確 |
| 讀取 `slotRegistry.tsx` | `:9-10` 為 `querySelector` 與 `if (!el) return () => undefined` | portal 靜默 no-op 的引用正確 |
| 讀取 `Layout.tsx` | 32 行，單一 `<ReselectionBanner />` | 見 R-04 |
| grep `App.tsx` 的 `<Layout` | 13 處，行號與規格不符 | 見 R-02 |
| grep `LOCAL-DEV.md` 與 workflows 的 `nginx.conf` | `LOCAL-DEV.md:588`、`:641`；`local-dev-drift.md:9/:58`；`local-dev-drift.lock.yml:58`；`deploy/` 目錄下無 `nginx.conf` | `deploy/nginx.conf` 不存在的主張成立（git 歷史未能查）；行號見 R-03 |
| 讀取 `member-pages.spec.ts` | `:6` 自述全部 `page.route()`；7 個以上案例，含 console 與四控件斷言 | 設計列出的案例大致已落地，但為 stub 層級，見 R-01 |
| 讀取 `docker-compose.test.yml` | backend 環境變數皆 `${VAR:-default}` 形狀；前端 `8090:80` | 「CI 測試 stack 無新變數」成立 |
