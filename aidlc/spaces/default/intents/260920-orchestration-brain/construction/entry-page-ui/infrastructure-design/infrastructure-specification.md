# Infrastructure Specification — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T04:41:16Z（`date -u` 取值）。本站是**設計**站：描述需要什麼基礎設施與為什麼，不寫 IaC。
>
> 結論：**零新服務、零新埠、零新環境變數、零新 secret、零 DDL、零 nginx／cloudflared 設定變更、零新依賴。**
> 本單元的基礎設施面是**既有路徑的使用方式**：前端三頁經既有 `location /api/` 升級轉發連上 `U13` 的 `/api/brain/ws`，
> 後端改動（C-8：`U7`／`U2`／`U13`）落在既有 `backend` 容器。真正的工作是三件事：Cloudflare 那一跳的子協定透傳仍未實測（`OPEN-EP14-13`，
> `[EPI1]`=A：部署流程新增免 token 的自動檢查）、每次部署重建 backend 容器時所有入口頁連線會一起重連（§三）、以及合併順序與部署後檢查（`cicd-pipeline.md`）。
> 另有一項屬 CI 面、記在 `cicd-pipeline.md` §三之二：既有 14 個 e2e 的落地斷言會因 `BR91.1` 必然變紅（`[EPI2]`=A：改斷言、只改名一個）。
> 本站未執行任何程式、測試或部署；行號皆於撰寫當下以 `grep -n`／`sed -n` 實讀，`git` 事實以本機追蹤分支 `origin/ut` 為準（本站未 fetch）。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-design/logical-components.md` | §一 改動清單（後端七個元件、前端十餘檔、`eslint.config.js`）；§一之三 不變的設定；§三 失敗域；§五 合併前檢查 |
| `../nfr-design/security-design.md` | §一 factory 注入、§六之二 4403 落點、§六之五 log 與 token、§八 ADR-0006 四面向、§十 殘留 |
| `../nfr-design/performance-design.md` | §一 每頁一條連線與退避、§一之三 握手預算（支援 3 分頁）、§三 名稱查詢成本 |
| `../functional-design/functional-spec.md` | §二之一 C-8；§八之二 `OPEN-EP14-13`、`OPEN-EP14-15`；§八之三 第 3–5 點 |
| `../nfr-requirements/tech-stack-decisions.md` | `NFR5.140`、`NFR5.141`、`NFR8.140`、`EPN-21`–`EPN-24` |
| `../carried-review-items.md` | 三站帶入項；本站處置其中與部署／CI 相關者（`traceability.json` reverse） |
| `inception/domain-design/components.md`、`inception/contract-design/contract-summary.md` | 唯一通道為 WS、三頁各一條連線、掛載點與路由（`K-12`、`K-13`） |
| `../../brain-gateway/infrastructure-design/infrastructure-specification.md` 第四、五節 | 逐跳查證、閒置逾時、三層實測與回退（本檔沿用、不重抄） |
| `../../brain-gateway/code-generation/code-summary.md` §六、§七 | 部署後實測清單的現行版本；交接給 `U14` 的 11 項 |

## 一、部署架構：逐項判定（附證據）

| Facet | Choice | Rationale |
|---|---|---|
| 運算模型 | **不變**：既有 docker compose 7 個服務 | `deploy/docker-compose.deploy.yml` 的服務鍵 `db`(:35)、`backend`(:79)、`redis`(:184)、`ollama`(:312)、`frontend`(:353)、`cloudflared`(:375)、`mcp-bridge`(:400)。C-8 的後端改動在 `backend` 容器；前端三頁與元件是 `frontend`（nginx）容器內的靜態資產 |
| 行程模型 | **不變**：單一 uvicorn 行程 | `backend/Dockerfile:30` 無 `--workers`。`U13` 的連線登錄與握手限流都在行程記憶體內；本單元每分頁至多一條連線（`EPN-01`），不改變這個假設 |
| 網路（反向代理） | **不變** | `frontend/nginx.conf:16-32` 的 `location /api/` 已含 `proxy_http_version 1.1`、`Upgrade`／`Connection` 改寫（`:18-21`）與 600 秒讀寫逾時（`:30-31`）；`$connection_upgrade` 的 map 在映像內產生（`frontend/Dockerfile` 的 `upgrade-map.conf`）。新路由 `/`（入口頁）與萬用路由由 `:35-37` 的 `try_files … /index.html` 承接，不需新 `location` |
| 公開入口 | **不變** | `deploy/cloudflared/config.yml:11-18`：單一 hostname、`service: http://frontend:80`、`tcpKeepAlive: 30s`；無可調整標頭的設定 |
| 埠 | **零新增** | 不新增 compose `ports:`；`FRONTEND_HOST_PORT` 不變 |
| 前端連線位址 | **建置時內嵌，不新增變數** | `frontend/src/config/api.ts:19-22`：`VITE_WS_BASE_URL` 未設時由 `VITE_API_BASE_URL` 的 `http→ws`／`https→wss` 推導；部署建置參數 `VITE_API_BASE_URL: ${PUBLIC_URL}`（`docker-compose.deploy.yml` frontend `args`），`PUBLIC_URL=https://cloud360.danniel.cc`（`deploy/render-env.sh:123`）。故 staging 的入口頁一律連 `wss://cloud360.danniel.cc/api/brain/ws`——**即使頁面是從區網 IP 打開，WS 也走 Cloudflare**（§二之一 的部署後檢查因此只能以公開網址執行）。CI 測試 stack 為 `ws://localhost:8090/api/brain/ws`（`docker-compose.test.yml:190`），只經 nginx |
| 儲存策略 | **零**：無 DDL、無新表、無新 Redis 鍵 | C-8 的三個名稱**不儲存**，每次推送重查（`functional-spec.md` §二之一第 4 點）；`project.md` 的 schema ↔ deploy 同步規則不觸發（§五） |
| 瀏覽器儲存 | **零** | `EPN-13`：新增前端程式不寫 `localStorage`／`sessionStorage`／IndexedDB／Cache Storage；`refreshMe()` 以相同值重寫既有 token 鍵屬既有行為（`security-design.md` §六之五） |
| 環境變數 | **零新增**（`NFR8.140`） | 本單元不碰任一 `.env.example`、`render-env.sh` 或 compose；`python3 scripts/validate_env_contract.py` 無新標的。`frontend/.env.example` 既有的可選 `VITE_WS_BASE_URL` 不需設定 |
| Secret | **零新增** | 沿用 `U13` 已定的 `OPENROUTER_API_KEY` 為部署必要 secret（`deploy.yml:71-93`）；本單元不新增任何憑證，`project.md` 的「secret 須落在 secrets 而非 variables」查證不觸發 |
| 依賴 | **零新增**（`EPN-21`） | `routeWebSocket`、`page.clock`、`emulateMedia` 皆為已安裝的 Playwright 內建 API（`frontend/package-lock.json` 的 `@playwright/test` 為 1.61.1）；後端計數用 SQLAlchemy 內建事件 |
| 環境 | 三個（本機 dev／CI 測試／staging），不變 | 三者的 WS 路徑不同：本機 vite 直連 uvicorn（不經 nginx）；CI 經 nginx 一跳；staging 經 Cloudflare edge → `cloudflared` → nginx 三跳 |
| IaC 方式 | 不變（compose ＋ `deploy.yml`） | 雲端 IaC 不在範圍（ADR-0001／ADR-0002） |
| 資源規模 | **不變** | 閘道上限為應用層常數（每 key 10 條、每行程 200 條、每 key 每分鐘 30 次握手——`brain_gateway_rules.py:79` 等，數值屬 `U13`）；本單元的壓力分析見 §三 |

## 二、基礎設施服務

| Service | Role | Configuration | Notes |
|---|---|---|---|
| FastAPI（`backend`） | application ＋ WS 端點 | C-8 程式改動；**組裝改動**：`main.py:84` 的 `build_brain_gateway(app)` 改為帶必填 `membership_facade_factory`（`logical-components.md` §一之一）。零設定改動 | 組裝在 startup hook 內——漏傳時是**啟動失敗**（fail-closed），不是匯入失敗；哪道閘門會發現見 `cicd-pipeline.md` §四第 5 列與 §八 的對齊修正 |
| nginx（`frontend`） | static ＋ reverse proxy ＋ WS 升級 | 新增前端資產；`nginx.conf` 不改 | `src/brain/testing/wsFrames.ts` 不被任何 app 程式匯入，不進正式 bundle（`functional-design` 審查 `R-04` 已確認此點；完成條件見 `cicd-pipeline.md` §四第 19 列） |
| `cloudflared` | 公開入口（TLS 終結於 Cloudflare edge） | 不改 | 子協定透傳未實測，見 §二之一 |
| Redis（`redis`） | session 狀態 | 不改 | C-8 不新增鍵；作業對象與工作項由 `U8`／`U13` 讀寫 |
| PostgreSQL（`db`） | database | 不改 | `describe_work_target` 為純查詢；每次推送每組三元組 ≤ 5 條、快照 ≤ 15 條 SQL（`EPN-06`，使用者裁決）；目錄路徑改為一次批次可見性查詢（nfr-design 帶入項 `R-02` 裁決） |
| Ollama／mcp-bridge | — | 不碰 | `mcp_bridge/allowlist.json` 只含 `/api/requirements/*`；C-8 不改任何 HTTP 端點，`openapi.json` 與 `generated_tools.json` 不漂移 |

### 二之一、WebSocket 逐跳路徑（沿用 `U13` 第四節，補本單元特有的三點）

逐跳靜態查證、閒置逾時與三層實測步驟的正本在 `U13`（`brain-gateway/infrastructure-design/infrastructure-specification.md:44-129`，現行實測清單為
`brain-gateway/code-generation/code-summary.md` §六之二），本檔不重抄。本單元補三點：

| # | 事實 | 證據 | 對本單元的意義 |
|---|---|---|---|
| 1 | 只帶協定名、不帶 token 的握手，閘道會**先 accept 並回送協定名**、再以 4401 關閉 | `brain_gateway.py:723-726`（`offer.bearer_token is None` → `_accept_and_close(ws, 4401)`），`:651-653`（`ws.accept(subprotocol=rules.PROTOCOL_NAME)`）；協定名缺漏時則是未 accept 即 `close()`（`:719-722`，`ws_refused reason=no_protocol`） | Cloudflare 兩跳對協定名項的**雙向**透傳可以免 token 驗證：看到 `101` 與 `sec-websocket-protocol: cloud360.brain.v1` 即成立。這是 `[EPI1]`=A 部署檢查（`cicd-pipeline.md` 步驟 6a）的依據；`bearer.` 項的請求方向仍只能由帶 token 的 L3 實測證明 |
| 2 | 閘道**不檢查** `Origin` | `brain_gateway.py` 對 `origin` 的 grep 只命中交辦來源變數（`:507-523`），握手路徑無 `Origin` 判斷；`main.py` 的 `CORSMiddleware` 不作用於 WebSocket | 頁面從區網 IP 打開時連公開網址的 WS 不會因跨來源被拒。跨站 WebSocket 劫持不成立：token 在子協定標頭，瀏覽器不會自動附帶（不同於 cookie）。列入 §七 Network exposure |
| 3 | 正式 bundle 的 WS 基底在建置時內嵌 | §一「前端連線位址」列 | 部署後的**瀏覽器**檢查必須以 `https://cloud360.danniel.cc` 開頁；換主機名需要重建前端映像，與既有 REST 行為相同 |

## 三、部署重啟與重連（本單元新引入的部署期行為）

`deploy.yml:129` 的 `up -d --build --remove-orphans` 以**原地替換**重建有變更的容器（非 blue-green）。`U14` 上線後，每一次重建 `backend`，
所有開著入口頁、`/workspace`、`/assessment` 的分頁會同時失去大腦連線，並依 `EPN-02` 的排程（約 1、2、4、8、15、15 秒，乘 0.8–1.0 抖動，
累計 ≥ 60 秒才放棄）重連。

| 面向 | 內容 |
|---|---|
| 使用者可見結果 | 後端在放棄前回來：脈絡列與常駐區以伺服器推送覆蓋（`NFR4.140`），本地對話紀錄保留、進行中的輪次轉 interrupted。後端超過約 60 秒才回來：該分頁顯示「無法連線到大腦」與「重新連線」按鈕，需使用者手動按 |
| 後端不可用的時長 | **未量測**。`--build` 先建映像再替換容器，不可用窗口是「舊容器停止到新容器接受連線」；新容器的 startup hook 會建閘道元件與 `init_db()`（`main.py:84-85`）。本站沒有任何量測來源，列為部署後人工觀察（`cicd-pipeline.md` §五第 7 步） |
| 握手預算 | 每 key 每分鐘 30 次（`brain_gateway_rules.py:79`）；`performance-design.md` §一之三 實算單分頁 60 秒內 8–9 次、宣告支援 3 分頁。部署重啟是「全部分頁同時重連」最常見的觸發點；第 4 個以上分頁可能有部分握手被限流（`security-design.md` §十 第 6 項的殘留），被拒不累積、60 秒後照常放棄 |
| 每行程上限 | 每行程 200 條（`U13` 常數）；重連期間不會超過重啟前的連線數 |
| 部署中的舊分頁 | 第一次含 `U14` 的部署：舊分頁的 bundle 沒有 WS 客戶端，不受影響；重新整理後才載入新 bundle。nginx 對 `index.html` 無長期快取（`nginx.conf:39-42` 只對帶雜湊的靜態資產設 30 天） |
| 回滾後的新分頁 | 回滾到不含 `U13` 的 last-good 時，已載入新 bundle 的分頁會連一個不存在的端點：握手失敗、依「其他」續退避、60 秒後放棄並顯示說明，**不會**形成重試風暴（重連有上限，`EPN-02`） |

## 四、合併、同批與資料相容

| 面向 | 判定 | 細節 |
|---|---|---|
| 與 `U13` 同一次合併 | **必要**（`NFR5.141`） | 協定維持 `v: 1` 的論證前提是「`U14` 之前前端沒有任何 WS 消費者」；合併前三項檢查見 `logical-components.md` §五，在本檔不重抄。本分支 `origin/ut..HEAD` 現為 89 個 commit，含 `U13`（`fa8ce42`）與 `U23`（`8677b7d`），`fa8ce42` 不在 `origin/ut`（`git merge-base --is-ancestor` 為否）；`backend/services/brain_router.py` 不存在；`ws-contract.json` 尚無 `projectName`（C-8 未實作，屬預期） |
| `delivery-planning:c6` | **不適用**（四點論證在 `cicd-pipeline.md` §三之一） | 欄位增量、無既存部署消費者 |
| 資料相容 | **無資料遷移** | 名稱不儲存；Redis 中的作業對象形狀不變；回滾不需反向遷移 |

## 五、`project.md` 同步／blocking 規則的逐項判定

| 規則 | 觸發條件 | 本單元判定 |
|---|---|---|
| schema ↔ deploy 同步（`schema_rbac.sql` ＋ `DEPLOY.md`） | DDL、seed 語意變更 | **不觸發**：無 DDL、不新增 story id、不改 seed（`functional-spec.md` §八之三第 5 點） |
| `LOCAL-DEV.md` 同步 | 異動 `backend/database.py` 的 schema 補丁、nginx 設定、任一 `.env.example`、`render-env.sh` | **不觸發**：四者皆不碰。`LOCAL-DEV.md:22` 已記載入口頁的本機前置條件（Redis ＋ 金鑰），無需修改 |
| env contract（三環境分離） | 新增 compose 消費的變數 | **不觸發**：零新變數 |
| 單一真實來源（`team.md`） | 跨語言副本 | 本單元前端只經產生的 `ws-contract.d.ts` 讀名稱欄位（`NFR5.140`），訊息字數上限不寫死（`EPN-27`）——無新副本 |

## 六、共用基礎設施

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| `/api/brain/ws` 端點、連線登錄、握手限流 | `U13` | `U14`（唯一的瀏覽器消費端） | 只經子協定帶 token 的握手；前端判斷 `K1` 只是呈現，拒絕在閘道（`EPN-17`） |
| `ws-contract.json`、`frontend/src/types/ws-contract.d.ts` | `U2`（契約模組 `brain_ws_contract.py`） | `U13`、`U14` | 兩檔只重 dump／重產，不手改；`ws-contract.json` 在 repo 根目錄、`.d.ts` 編譯後消失，不進 `dist/` |
| `HierarchyFacade` 的四個方法 | `U7` | `U13`（目錄、名稱、設定目標）、`U23` 的靜態鎖 | 可見性判定只經注入的 `project_visibility` 閉包；`hierarchy_facade.py` 與 `brain_gateway.py` 不 import 成員關係符號（`test_brain_gateway_limits.py:379-383` 的禁止清單） |
| `MembershipFacade.project_visibility` | `U19` | `U23`、`U14`（經 `main.py` 組裝） | 唯一的靜態邊是 `main.py → services.membership_facade` |
| `eslint.config.js` 的子協定規則 | ADR-0019 §5（`U2` 起） | 全前端；本單元新增 `tests/**/*.ts` 區塊 | 抽成共用常數 `WS_SUBPROTOCOL_RESTRICTIONS`，兩個區塊展開同一份（`security-design.md` §六之六） |
| `ui-regression` 測試 stack（`deploy/docker-compose.test.yml`） | 全 repo | 全部 e2e | 本單元不改它；`OPENROUTER_API_KEY: ""`（`:83`）使真實 stack 層只能斷言到握手、ready、狀態推送與錯誤呈現 |

## 七、ADR-0006 四面向（基礎設施視角；逐格對照 `../nfr-design/security-design.md` §八）

| 面向 | nfr-design 判定 | 本站判定 | 基礎設施面的內容 |
|---|---|---|---|
| **IAM** | 適用（擴充） | **適用（擴充）**——相同 | 擴充全在應用層（目錄、名稱、直接設定三處的可見性判定；子頁面無 `K1` 不掛大腦掛點）。基礎設施層零改動：無新資料庫角色或 grant、無雲端 IAM、無 GitHub token 權限變更。`[EPI1]`=A 的新步驟不需任何權限（`deploy` job 既有權限即可，且不讀任何 secret） |
| **Encryption** | 適用（相同） | **適用（相同）** | 外部 TLS 終結於 Cloudflare edge，`cloudflared` → nginx → backend 在主機內 bridge 網路為明文（與既有 REST 的 `Authorization` 標頭同一信任邊界，`U13` 已記載）；本單元零新傳輸通道、零新持久資料 |
| **Network exposure** | 適用（相同） | **適用（相同）** | 零新端點、零新埠、`nginx.conf`／`config.yml` 不改；本單元是既有 WS 端點的第一個瀏覽器消費端。補充 §二之一第 2 點：閘道不檢查 `Origin`，但 token 不在 cookie，跨站劫持不成立；4403 不再造成重連或導航迴圈（`security-design.md` §六之二）。`[EPI1]`=A 的檢查只送一個不帶 token 的升級請求、立即被 4401 關閉，不新增暴露面 |
| **Audit logging** | 適用（相同） | **適用（相同）** | 不新增稽核事件；新增一筆白名單內的 WARNING `work_target_names_failed`（只帶 `connId`、例外類別名），落在既有 stdout → docker `json-file`（`docker-compose.deploy.yml:62-68`，50m × 5，依容量輪替）。token 不進網址（`EPN-16`），故 nginx 與 uvicorn 的 access log 只記 `/api/brain/ws` 路徑；Cloudflare 端的日誌行為未查證（沿用 `U13`） |

**PBT**：不適用——與 `security-design.md` §九一致（本單元不是 IaC generator、cost calculator、agent routing 三個 hard-constraint 落點）。

## 八、對上游的對齊修正（非本站新定案）

`logical-components.md` §三 第 1 列寫「`membership_facade_factory` 漏傳 → 啟動 `TypeError`……誰會發現：`test_brain_gateway_startup.py`；CI import smoke」。
後半句不成立：`build_brain_gateway` 在 `@app.on_event("startup")` 內呼叫（`backend/main.py:84`），`:82-83` 的註解逐字寫「CI 的 import smoke 與 OpenAPI dump
只設 DATABASE_URL／JWT_SECRET，而以 TestClient(app) 不觸發本 hook」——`ci.yml:269-277` 的 `python -c "import main"` 不執行 startup，抓不到漏傳。
真正會發現的是：`test_brain_gateway_startup.py` 改寫後的關鍵字斷言（unittest）、`ui-regression` stack 的 backend 起不來（全部 e2e 紅）、部署的資料面探測（`deploy.yml:313` 起）
持續 502 而失敗並觸發回滾。上游檔不回改；本站在 `cicd-pipeline.md` §四第 5 列以正確的閘門清單取代。

## 九、殘留（供核可關卡知情接受）

| # | 殘留 | 理由 |
|---|---|---|
| 1 | Cloudflare 兩跳對 `bearer.` 項（請求方向）的透傳只能人工實測 | 需要有效 token，而 Actions log 公開；`[EPI1]`=A 的部署檢查只能自動化協定名項 |
| 2 | 部署重啟期間後端不可用時長未量測；超過約 60 秒時使用者需手動重連 | 無量測來源；退避上限是已核可的 `EPN-02` |
| 3 | 4401 無 token 更新端點，JWT 到期時重新登入即清空對話紀錄（`OPEN-EP14-15`） | 上游已揭露；基礎設施面無處置 |
| 4 | Cloudflare 的閒置上限與訊框上限未查證（沿用 `U13`） | 本站未取得官方數值；`EPN-02` 的重連是最後防線 |
