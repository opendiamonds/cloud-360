## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-11-06T07:39:16Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `aidlc/spaces/default/intents/261105-d-iac-generation/construction/u2-iac-ui/infrastructure-design/infrastructure-specification.md` > Table "Infrastructure Services" > nginx row | 文件寫 "既有 `deploy/nginx.conf`"，但 `find` 確認實際路徑為 `frontend/nginx.conf`（frontend Docker image 的 `COPY nginx.conf` 亦指向同位置）。路徑錯誤不影響執行期行為，但會誤導實作者在 `deploy/` 目錄下尋找 nginx 設定。 | 將 `deploy/nginx.conf` 更正為 `frontend/nginx.conf`，與 Dockerfile 及 `CLAUDE.md` 的「`deploy/nginx.conf`」規則進行同步確認（後者可能亦需更正）。 | New |
| R-02 | Major | `aidlc/spaces/default/intents/261105-d-iac-generation/construction/u2-iac-ui/infrastructure-design/cicd-pipeline.md` > Table "Pipeline 對照" > "ui-regression（Playwright）" row | 設計宣告 `ui-regression` 為「紅燈擋（unexpected≠0）」，同時新增 IaC 頁 e2e，並「允許 MSW／stub 至 U1 合入」。然而：(1) 整個 `frontend/src/` 目錄下無任何 MSW 相關檔案（`msw`、`setupWorker` 關鍵字 grep 零命中）；(2) `deploy/docker-compose.test.yml` 的 ui-regression stack 建置真實 frontend 與 backend image，Playwright 連至 `localhost:8090/api/iac`，而該路徑在 U1 合入前後端回 404；(3) MSW 為 Service Worker 層攔截器，需 `mockServiceWorker.js` 在 nginx 靜態資源中存在、且 app 在測試環境初始化 worker——三者目前均不存在。在未指定「MSW 在 CI Playwright 環境的啟用機制」或「U2 e2e 僅在 U1 合入後才納入閘門」的前提下，開發者無法從本 artifact 推導出讓閘門在 U1 前保持綠燈的具體做法。 | 在 `cicd-pipeline.md` 明確選取下列策略之一並寫入文件：(a) 以 Playwright `page.route()` 在測試檔本身攔截 `/api/iac` 請求（無需 Service Worker；僅需 Playwright native API，不新增依賴）；(b) 安裝 `msw` 並說明 CI 環境的 `mockServiceWorker.js` 生成與 nginx 靜態服務方式；(c) 明記「IaC 頁 e2e 在 U1 合入後才加入 ui-regression 閘門」，使平行開發期間僅測試殼層可達性（如 `/workspace` 路由 200、CTA disabled），API 路徑測試在 U1 合入後補入。 | New |
| R-03 | Minor | `aidlc/spaces/default/intents/261105-d-iac-generation/construction/u2-iac-ui/infrastructure-design/traceability.json` > upstream_ids | Traceability sensor 以 regex `\bNFR\d+\.\d+\b` 比對 ID，但本 unit NFR 設計使用 `NFR-PERF-UI-*`／`NFR3.UI.*` 格式（無法命中），故 sensor 報 FAILED。人工交叉比對確認 `traceability.json` 的七個 ID 與 `nfr-design/` 實際 ID 一致，覆蓋具有人類可讀意義。Dispatch brief 已標記此為 advisory gap，不要求補造不存在的 `NFRx.y` ID。 | （諮詢性建議）可在 `traceability.json` 加一個 `"id_format_note"` 欄位說明本 unit 的 NFR ID 命名慣例，以利未來工具演進時不誤報。非 blocking。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| traceability sensor（`\bNFR\d+\.\d+\b`） | FAIL（零命中） | 工具誤報：本 unit NFR ID 格式為 `NFR-PERF-UI-*`／`NFR3.UI.*`，regex 不匹配。人工核對確認七個 ID 均對應 `nfr-design/` 實際條目，覆蓋人類可讀意義完整（見 R-03）。 |
| nginx 路徑驗證（`find` + Dockerfile 比對） | FAIL（路徑不符） | `frontend/nginx.conf` 存在且正確，但 `infrastructure-specification.md` 寫 `deploy/nginx.conf`（見 R-01）。 |
| MSW 存在性驗證（`grep -rl msw frontend/src`） | FAIL（零命中） | 整個 frontend codebase 無 MSW 安裝，與 cicd-pipeline.md「允許 MSW／stub」宣稱不一致（見 R-02）。 |
| nginx timeout 與 D1 90s 兼容性 | PASS | `proxy_read_timeout 600s` ≫ AbortController ≥90s；client 端先 abort，nginx 不會比 UI timeout 更早斷線。 |
| `VITE_API_BASE_URL` 環境契約 | PASS | Dockerfile `ARG VITE_API_BASE_URL=http://localhost:8090`；compose 覆蓋為 `${PUBLIC_URL}`；`deploy/.env.example` 不含 localhost——與 Q2=A 及 env contract 一致。 |
| App.tsx 路由對齊 | PASS | `/workspace` 路由存在，`WorkspacePage` 含「Coming Soon」stub（`showComingSoon('IaC 代碼生成')`），符合「Workspace 路由下取代 Coming Soon」的設計意圖。 |
| Secret 未洩漏（前端映像） | PASS | `docker-compose.test.yml` 的 frontend build 無任何 LLM／雲端金鑰；cicd-pipeline.md「前端映像不承載 LLM／雲端金鑰」宣稱成立。 |
| infra-spec ↔ U1 infra-spec 共用層對齊 | PASS | U1 與 U2 均宣告 `staging compose／nginx／Tunnel` 由平台共享，access boundary 為同源 HTTP `/api/iac`；無衝突。 |

### Summary

本設計的核心架構決策（沿用既有 frontend Docker／nginx、同源反代、無新 CDN／RUM、ui-regression 閘門擴充）與 Q1–Q4=A 一致，且與既有 `deploy/docker-compose.test.yml` 、`frontend/Dockerfile`、`frontend/nginx.conf` 三項實體檔案可交叉驗證。主要審查關切集中於 R-02：`cicd-pipeline.md` 宣稱「允許 MSW／stub 至 U1 合入」但 codebase 中無 MSW 安裝、CI test stack 使用真實 backend image，開發者在 U1 合入前若照設計新增 IaC e2e 測試，閘門會因 404 而紅燈——本設計未給出能讓開發者自行決策的備選方案。在把 R-02 策略補入 `cicd-pipeline.md` 後，本 unit 的基礎設施設計即可支援無架構師在旁的完整實作。
