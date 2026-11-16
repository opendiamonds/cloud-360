# CI/CD Pipeline — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T04:41:16Z（`date -u` 取值）。
>
> **結論先講**：`ci.yml`、`ui-regression`、`package.json` scripts 的改動為 **0 行**；`deploy.yml` 新增一步（`[EPI1]`=A：一道免 token 的子協定透傳檢查、失敗即擋部署）。
> 本單元的新測試全部被既有 job 撿到，契約增量由既有兩道 WS 漂移閘門把關。本站的實質內容是四件事：
> (1) 一個上游沒發現的缺口——**既有 14 個 e2e 的落地斷言會因 `BR91.1` 必然變紅**（§三之二，處置依 `[EPI2]`=A）；
> (2) 與 `U13` 同一次合併的判定與合併前檢查（§三）；(3) 部署後檢查，含 Cloudflare 子協定透傳在 staging 主機上可直接執行的人工步驟（§五）；
> (4) 失敗路徑表，以「CI 訊號／擋部署／只能人工／無偵測」區分（§四）。
> 本站未執行任何 CI 步驟、測試或部署；判定皆依 workflow 原文與行號。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-design/logical-components.md` | §一 改動清單與測試檔；§三 失敗域；§五 合併前檢查 |
| `../nfr-design/security-design.md` | §六之六 lint 區塊與突變；§七 突變清單 M1–M15 |
| `../nfr-design/performance-design.md` | §一 退避與終止碼的 e2e 測法 |
| `../nfr-requirements/tech-stack-decisions.md` | `NFR5.140`、`NFR5.141`、`EPN-22`、`EPN-24` |
| `../functional-design/functional-spec.md` | §二之一 第 6 點（C-8 落點順序，同一次合併）、§八之三 |
| `../carried-review-items.md` | functional-design `R-07`（合併前檢查的可執行形式）、nfr-requirements `R-04`（StrictMode 只存在於開發建置） |
| `../../brain-gateway/infrastructure-design/cicd-pipeline.md` §一 | `ui-regression` 斷言到 `ready` 即每個 PR 機械驗證 nginx 一跳（本單元是兌現它的那一方） |
| `../../brain-gateway/code-generation/code-summary.md` §六 | 合併前 secret 確認、部署後三層實測的現行版本 |
| `inception/delivery-planning/bolt-plan.md` | `B6`＝`U13`、`U14`（`:294`，Bolt 內順序 `U13` → `U14`）；交錯執行序列 `:494` |

## 一、CI 閘門逐道影響

`ci.yml` 除 `gate` 外的每個 job 都只 `needs: gate`，故並行執行（`ci.yml:559` 的註解逐字）。

| Job／步驟 | 位置 | 對本單元的影響 | 本單元要做的事 |
|---|---|---|---|
| `repo-contract`：五支 validator | `ci.yml:141-176` | 無新必要檔、無新環境變數；新檔名不含 `prod`／`production`／`secrets` path part | commit 前本機跑 `validate_repo_contract.py`、`validate_env_contract.py` |
| `frontend`：`npm run lint` | `:197-198` | 新增前端檔受 16 條 error 級 hook 規則與子協定規則約束；**新增 `tests/**/*.ts` 區塊**後 lint 也檢查 spec 不得手寫訊框（`EPN-19`、`EPN-22`） | 規則共用常數 `WS_SUBPROTOCOL_RESTRICTIONS`；既有 `member-pages.spec.ts:573` 的 `{ loc, msg, type }` 必須仍綠（選擇器要求同時有 `type` 與 `payload` 鍵） |
| `frontend`：API type contract drift（`check:types`） | `:206-207` | **不受影響**：C-8 不改任何 HTTP 端點（`HierarchyFacade` 方法的呼叫者只有 `U13` 與測試，`grep` 確認 router 不呼叫 `list_projects`／`list_systems`／`resolve_work_target`） | — |
| `frontend`：**WS contract type drift**（`check:ws-types` → `scripts/check-ws-types.mjs`） | `:218-219`；`package.json:15` | 由 committed `ws-contract.json` 重產型別並與 committed `src/types/ws-contract.d.ts` 比對；重 dump 了 JSON 卻沒重產型別 → **紅** | §一之一 的順序 |
| `frontend`：`npm run build`（`tsc -b && vite build`） | `:222-223` | 新頁面、元件與 `src/brain/testing/wsFrames.ts` 都在 `src` 下，由 `tsc -b` 檢查；契約欄位改名 → 建構器內的具名 payload 型別紅（`BR98.4` 的突變） | — |
| `frontend`：Spec must not be served statically | `:232-240` | 不受影響：`ws-contract.json` 在 repo 根目錄，`.d.ts` 編譯後消失 | — |
| `backend`：Import FastAPI app | `:269-277` | 只驗匯入；**抓不到** `membership_facade_factory` 漏傳（組裝在 startup hook，`infrastructure-specification.md` §八） | — |
| `backend`：OpenAPI spec drift | `:286-294` | 不受影響（零 HTTP 變更） | — |
| `backend`：**WS contract spec drift**（`dump_ws_contract.py --check`） | `:304-305` | `WorkTargetPayload` 加三欄後未重 dump `ws-contract.json` → **紅** | §一之一 |
| `backend`：MCP tool spec drift | `:313-314` | 不受影響：輸入是 `openapi.json` 與 allowlist | — |
| `backend`：Run unit tests | `:317-320` | 新檔 `test_describe_work_target.py` 與七支修改檔（`logical-components.md` §一之一 測試表）由 `unittest discover` 撿到（`EPN-24`）；`membership_facade_factory`、`project_visible` 必填無預設 → 既有呼叫漏補即 `TypeError` 紅（fail-closed） | 既有呼叫只補關鍵字參數、不改期望值（`test_brain_gateway_startup.py:60` 的 lambda 例外，見 `logical-components.md`） |
| `memory-schema`、`concurrency`（真實 PostgreSQL） | `:322` 起、`:545` 起 | 不受影響：無 DDL、無列鎖語意 | — |
| `docker-build` | `:628` 起 | 不受影響：兩個 Dockerfile 不改 | — |
| **`ui-regression`**（gh-aw，Playwright） | `ui-regression.lock.yml:558` 為 `timeout 15m npx playwright test`；`frontend/playwright.config.ts:10` `testDir: './tests/e2e'`；`post-steps` 讀 `.stats.unexpected`（`:1061`） | 新 spec `tests/e2e/entry-page*.spec.ts` 丟進即被撿到。真實 stack 層經 nginx 連 `ws://localhost:8090/api/brain/ws`（`docker-compose.test.yml:190`），斷言到 `ready` 即**每個 PR 機械驗證 nginx 這一跳**的子協定透傳；金鑰為空（`:83`），交辦類只能以 `routeWebSocket` 驗。**既有 14 個測試會紅**，見 §三之二 | 新 e2e；既有斷言依 `[EPI2]`=A 處置 |

**這些紅燈是訊號，不是合併閘門**：`ut` 沒有任何必要狀態檢查（`ci.yml:557-562` 的註解逐字，`OPEN-ID19-6`；`project-pages-ui` 的審查員曾以 `gh api` 複驗
`required_status_checks` 為 null，本站未重查）。上表「會紅」的意思是「合併者若看了檢查結果就會看見」，任一 job 紅燈都**不會擋住合併**。

### 一之一、本機產生順序（C-8，順序不可換）

1. 改 `backend/services/brain_ws_contract.py` 的 `WorkTargetPayload` → `cd backend && python scripts/dump_ws_contract.py`（重寫 repo 根目錄的 `ws-contract.json`，`dump_ws_contract.py:43`、`:58`）。
2. `cd frontend && npm run gen:ws-types`（`package.json:14`：`openapi-typescript ../ws-contract.json -o src/types/ws-contract.d.ts`）。
3. 兩檔與契約模組同一個 commit。先跑 2 再跑 1，`check:ws-types` 比對的是舊 JSON 產的型別，CI 照樣紅。
4. `openapi.json`、`api.d.ts` **不需重產**；若 diff 出現它們，代表誤改了 HTTP 層，應回頭查。

### 一之二、e2e 名稱穩定性（硬約束）

`ui-regression.lock.yml:568` 的 Kiwi 回報步驟以 `--summary-template '${name}'` 作為案例鍵，改名會讓舊案例成為孤兒。本單元新 e2e 的
`describe › test` 字串在 code-generation 落地後即固定，`tcms-test-cases` 站只同步不改名。既有測試只改名一個（`[EPI2]`=A，§三之二）。

### 一之三、`ui-regression` 的時間預算

整個 Playwright 執行有 15 分鐘上限（`:558`）。本單元新增兩層 e2e（`EPN-24`），退避與 4403 案以 `page.clock` 快轉、不以真實等待。
**未量測**新增後的總時長；若逾時，`timeout` 以非零結束而 `post-steps` 的報告不存在即失敗（`:1061`），屬訊號、不擋合併。

## 二、部署步驟（`deploy.yml`，合併進 `ut` 觸發）

| # | 步驟 | 位置 | 本單元的影響 |
|---|---|---|---|
| 1 | PR 合併進 `ut` 觸發；自架 runner、`concurrency: deploy-10-10` 不可中斷、30 分鐘逾時 | `deploy.yml:10-28` | — |
| 2 | 必要 secret 檢查（含 `OPENROUTER_API_KEY`） | `:71-93` | 沿用 `U13`；本單元不新增 |
| 3 | `render-env.sh` → `up -d --build --remove-orphans` | `:124`、`:129` | 原地替換；backend 重建即全部大腦連線重連（`infrastructure-specification.md` §三） |
| 4 | 前端本機、Redis ACL、Ollama 模型、資料面 `/api/auth/login` 401 | `:131`、`:200`、`:250`、`:313` | 資料面探測是 `membership_facade_factory` 漏傳時**唯一會擋部署**的步驟（backend 起不來 → 持續 502） |
| 5 | 公開網址 `/` 經 tunnel | `:358` | 只打 `/`，不碰 WS |
| 6 | mcp-bridge 健康（不擋）、Redis 重啟後 session 存活 | `:388`、`:447` | — |
| **6a** | **大腦 WS 子協定經 tunnel 透傳檢查（`[EPI1]`=A，新增）** | 新增於 `:447` 那一步之後、`:570` 之前 | 見 §二之一 |
| 7 | 記錄 last-good（`if: success()`） | `:570-575` | 6a 若擋部署，壞版本不會成為 last-good |
| 8 | 刪除 `deploy/.env` | `:577-579` | — |

### 二之一、步驟 6a 的設計（`[EPI1]`=A）

**原理**：只帶 `cloud360.brain.v1`、不帶 token 的升級請求，閘道會 accept 並回送協定名、再以 4401 關閉（`infrastructure-specification.md` §二之一 第 1 點）。
看到 `HTTP/1.1 101` 與 `sec-websocket-protocol: cloud360.brain.v1` ＝ 協定名項在 Cloudflare 兩跳雙向透傳；請求方向被剝 → 403；回應方向被剝 → 沒有那一行。
不需任何 secret，輸出只含狀態列與協定名。示意（≤ 15 行，實作由 code-generation 定）：

```bash
set -uo pipefail
for _ in $(seq 1 12); do
  HDRS=$(curl -sS -o /dev/null -D - --http1.1 --max-time 5 \
    -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
    -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' -H 'Sec-WebSocket-Protocol: cloud360.brain.v1' \
    https://cloud360.danniel.cc/api/brain/ws 2>/dev/null || true)   # 101 之後 curl 等到逾時、結束碼 28，屬正常
  if grep -q '^HTTP/1.1 101' <<<"$HDRS" && grep -qi '^sec-websocket-protocol: *cloud360\.brain\.v1' <<<"$HDRS"; then
    echo "brain WS: subprotocol survives the tunnel both ways"; exit 0
  fi
  sleep 5
done
echo "::error::brain WS handshake through the tunnel did not return 101 + cloud360.brain.v1 (see OPEN-EP14-13)" >&2
exit 1
```

| 約束 | 理由 |
|---|---|
| 位置在 `Verify sessions survive a Redis restart` 之後 | `backend/tests/test_mcp_bridge_deploy.py:101-104` 釘住 mcp-bridge 健康步驟的**前一步**是 tunnel 步驟、**後一步**以 `Verify sessions survive a Redis restart` 開頭；插在兩者之間會使該 unittest 紅 |
| 在 `Record this commit as the last-good deployment`（`:570`）之前 | 失敗時壞版本不成為 last-good |
| 失敗即 `exit 1`、不加 `continue-on-error` | `[EPI1]`=A：deploy job 失敗 → `rollback` 還原 last-good、開 revert PR、交 Deploy Doctor；Slack 通知（即 `U13` 第 4.5 節對 L3 失敗定下的處置） |
| 結束碼 28 不得中止步驟 | 既有 PROBE-CONTRACT P-5（`deploy.yml:331-334` 的註解）：未被 `if`／`|| true` 保護的指令替換在 `set -e` 下會中止。示意以 `set -uo pipefail`（不含 `-e`）＋ `|| true` 處理 |
| **不得**加進 `rollback` job 的驗證 | last-good 可能早於 `U13`，該版本沒有 `/api/brain/ws`，會讓回滾本身失敗 |
| 只在 `ut` 合併觸發的部署有回滾 | `rollback` 的條件是 `pull_request` 且 merged（`:596-602`）；手動 `workflow_dispatch` 失敗不回滾 |
| code-generation 的本機驗證 | 對 `docker compose -f deploy/docker-compose.test.yml` 起的 stack 把 URL 換成 `http://localhost:8090/api/brain/ws` 各跑一次正、反案：正案通過；**拿掉 `Sec-WebSocket-Protocol` 標頭後必須以非零結束**（突變），結果記入 code-summary。Cloudflare 那一跳只在第一次部署時才真正被驗證 |
| 不證明的事 | `bearer.` 項的請求方向、瀏覽器端（`Origin`、正式 bundle 的實際網址）——仍由 §五之二 的人工步驟承擔 |

## 三、合併順序約束

| # | 約束 | 性質 | 不遵守的後果 | 如何確認 |
|---|---|---|---|---|
| 1 | `U13` 與 `U14` **同一次**合併進 `ut` | 契約（`NFR5.141`：`v: 1` 的論證前提是 `U14` 之前前端沒有 WS 消費者） | 若 `U13` 先上線而 C-8 晚到，任何在中間出現的消費端都會讀到缺欄位的訊息；`v: 1` 的「不需升版」不再成立 | 合併前三項檢查（`logical-components.md` §五），**人工、在分支上、合併之前**執行；squash 之後 `origin/ut..HEAD` 不再成立 |
| 2 | C-8 的 ADR → `U7` → `U2` → `U13` → 前端，同一次合併 | 技術（`functional-spec.md` §二之一 第 6 點） | 只上一部分：例如契約模組與產生檔不同 commit → 兩道 WS 漂移閘門紅（訊號） | §一之一 |
| 3 | `ws-contract.json`、`ws-contract.d.ts`、契約模組同一個 commit | 技術（漂移閘門） | `WS contract spec drift` 或 `check:ws-types` 紅 | §一之一 |
| 4 | `BR91.1` 的落地改動與既有 e2e 斷言的處置（`[EPI2]`=A）同一個 PR | 技術（`ui-regression`） | 14 個既有測試紅（訊號） | §三之二 |
| 5 | 晚於 `U19`、`U23` | 技術依賴：`main.py` 組裝 `MembershipFacade`（`U19`）；本單元修改 `U23` 的靜態鎖 `test_project_visibility_static.py` | 已滿足：兩者的程式已在本分支上、早於本單元（`membership_facade.py` 在 `origin/ut..HEAD` 有提交紀錄；`U23` 為 `8677b7d`） | `git log --oneline origin/ut..HEAD -- backend/services/membership_facade.py` 有輸出 |
| 6 | 合併前 `OPENROUTER_API_KEY` 已在 Actions **secrets** 而不在 variables | 部署（`U13` 帶入；含此檢查的 `deploy.yml` 與本單元同一次進 `ut`） | secret 未設 → 第一次部署即失敗並回滾整個 intent | `U13` code-summary §六之一 的兩條 `gh api` 指令（**由使用者執行**） |
| 7 | DEMO 後端已移除（`[IG2]`=A） | 部署安全 | — | 已滿足：`backend/services/brain_router.py` 不存在（合併前檢查第 3 項） |

**交錯執行序列**（`bolt-plan.md:494`）把 `B13`（含 `U23`）排在 `B6`（`U13`、`U14`）之前；本分支的實際 commit 順序與之相符（`U23` 已提交、`U14` 尚未）。
全部單元在同一個功能分支上，實務上整個 intent 是**一次**合併進 `ut`，故第 1、2 列由分支結構自然滿足，合併前檢查是為了防止有人改為分批 cherry-pick。

### 三之一、`delivery-planning:c6`（破壞性契約變更與消費端不得分批）不適用的四點論證

1. **逐字觸發條件**：「既有端點的回應形狀變更」。
2. **契約是否全新**：`/api/brain/ws` 尚未部署過（`fa8ce42` 不在 `origin/ut`），對部署環境而言是全新端點；C-8 是**加欄位**（三個必存在、可為 null 的名稱），不移除、不改型別。
3. **要防的失敗模式是否存在**：「舊消費端讀到新形狀而壞」——部署環境沒有任何舊消費端；本分支上唯一的消費端就是 `U14` 自己，且型別由同一次重產。
4. **反方向是否已被擋住**：前端先於後端上線不可能——兩者在同一個映像建置與同一次 `up -d --build` 上線；合併約束第 1 列另外要求同一次合併。

本站判定 c6 不適用；但第 1 列的「同一次合併」仍然**必要**，理由是 `NFR5.141` 的 `v: 1` 論證，不是 c6。兩者在依賴圖上長得一樣，故分開寫。提交核可關卡採納。

### 三之二、既有 e2e 的落地斷言（上游未發現的缺口；`[EPI2]`=A）

**缺口**：`BR91.1` 使具 `K1 view` 者造訪 `/` 時停在入口頁；登入成功後一律 `navigate('/')`（`frontend/src/pages/LoginPage.tsx:107`）；
e2e 的 `admin`（`Platform_Admin`）與核准後的 `Developer` 都有 `K1 view`（`schema_rbac.sql:1206`、`:1198`）。下列斷言描述的正是被刻意改掉的舊落點：

| 檔 | 斷言位置 | 受影響的測試 |
|---|---|---|
| `regression.spec.ts` | `:73` | `管理員登入後進入工作區`（`:71`）——**此測試的目的就是落點** |
| 〃 | `:90` | `登出後返回登入頁`（`:88`） |
| 〃 | `:113` | `Platform_Admin 看得到系統管理區`（`:111`） |
| 〃 | `:158`、`:173` | `Developer 看不到系統管理區`（`:141`） |
| 〃 | `:189`（`gotoAdmin` 內） | `使用者管理頁 — 最後活動時間與分頁` 的 8 個測試（`:218`–`:475`，`gotoAdmin(` 呼叫 8 處） |
| `estimate-workspace.spec.ts` | `:17`（`login` helper 內）、`:35` | `上傳 AWS CSV 後顯示明細與檢查`（`:33`）、`官方估價教學彈窗顯示截圖與官方連結`（`:72`） |

合計 **14 個測試**（4 ＋ 8 ＋ 2）。上游的「既有 `regression.spec.ts` 必須保持綠燈」（`functional-spec.md:349`）以「不改它們」的讀法不可滿足；
以「改了斷言之後仍綠」的讀法可滿足。

**處置（`[EPI2]`=A）**：`管理員登入後進入工作區`（`:71`）改斷言入口頁並改名為「管理員登入後進入入口頁」——舊 Kiwi 案例成為孤兒，由 `tcms-test-cases`
在同步報告記明並把舊案例標為停用；其餘 13 個測試**名稱不變**，落點斷言改為 `not.toHaveURL(/\/login$/)`（需要工作區時再 `page.goto('/workspace')`），
並同步更新 `@purpose`／`@step` 註解；不得順手放寬其他斷言（code review 逐一核對）。新落點本身由本單元的入口頁 e2e 驗證（`EPN-17`）。

不受影響：`regression.spec.ts:55` 的 `not.toHaveURL(/\/workspace/)`（錯誤密碼）、
`:153` 的 `/waiting-approval`；`memory-page.spec.ts:215` 已用 `not.toHaveURL(/\/login$/)`；`member-pages.spec.ts` 以 `NEUTRAL_LANDING`（`:90` 的 `/memory`）直接前往。

**附帶事實**：這 14 個測試登入後都會在 `/` 或 `/workspace` 掛載大腦連線，對真實測試 stack 發起握手（`record=True` 會更新 `admin` 的最後活動時間，
既有「最後活動時間欄有值或破折號」的斷言本就容許有值）。同一帳號在 60 秒內的握手次數上限 30（`brain_gateway_rules.py:79`）；套件 `workers: 1`、每個測試結束即關閉頁面，
**推論**不會觸及上限，但未量測。

## 四、各失敗路徑由誰發現（stage → gate 對照）

性質欄四種值：**CI 訊號（不擋合併）**＝某個 CI job 會紅，但 `ut` 無必要狀態檢查；**擋部署（自動回滾）**＝`deploy` job 失敗並觸發 `rollback`；
**只能人工**＝§五之二 的步驟；**無偵測**＝目前沒有任何機制。

| # | 失敗路徑 | 發現者 | 性質 |
|---|---|---|---|
| 1 | 改了契約模組、沒重 dump `ws-contract.json` | backend `WS contract spec drift`（`ci.yml:304-305`） | CI 訊號（不擋合併） |
| 2 | 重 dump 了、沒重產 `ws-contract.d.ts` | frontend `check:ws-types`（`:218-219`） | CI 訊號（不擋合併） |
| 3 | 名稱欄位給了預設值（產生的 TS 欄位變可選） | `test_ws_contract.py` 新增「缺任一名稱欄位即失敗」一案 | CI 訊號（不擋合併） |
| 4 | 前端以手寫 interface 讀名稱，繞過產生的型別 | 無機械閘門；code review ＋ `NFR5.140` 的檢查 | 無偵測（僅 review） |
| 5 | `main.py` 漏傳 `membership_facade_factory` | `test_brain_gateway_startup.py` 的關鍵字斷言（unittest）；`ui-regression` stack 的 backend 起不來 → 全部 e2e 紅；部署資料面探測持續 502（`deploy.yml:313` 起）。**import smoke 抓不到**（`infrastructure-specification.md` §八） | CI 訊號 ＋ 擋部署（自動回滾） |
| 6 | 呼叫點傳恆真的可見性判定 | 擴充後的 `S3` 靜態鎖 ＋ 突變 M4（`security-design.md` §五、§七） | CI 訊號（不擋合併） |
| 7 | `hierarchy_facade.py`／`brain_gateway.py` import 成員關係符號 | `test_brain_gateway_limits.py:379-383` 的禁止清單 | CI 訊號（不擋合併） |
| 8 | 新前端程式寫死子協定字串 | `npm run lint`（`eslint.config.js:42-66` 的三條規則） | CI 訊號（不擋合併） |
| 9 | spec 手寫含 `type`＋`payload` 鍵的訊框 | 新 `tests/**/*.ts` lint 區塊 | CI 訊號（不擋合併） |
| 10 | 新 lint 區塊只列新選擇器，`tests/` 失去三條子協定規則 | **無機械閘門**：`tests/` 下目前沒有任何 `new WebSocket(...)`，規則消失不會讓任何東西變紅 | 無偵測 → §四之一 補強 |
| 11 | 新 lint 選擇器太寬，誤擋既有 spec | `npm run lint` 對 `member-pages.spec.ts:573` | CI 訊號（不擋合併） |
| 12 | 既有 14 個 e2e 的落地斷言未處置 | `ui-regression` | CI 訊號（不擋合併） |
| 13 | 新 e2e 的 `describe › test` 名稱日後被改 | 無；Kiwi 舊案例變孤兒 | 無偵測（§一之二 為約束） |
| 14 | `U13` 與 `U14` 被分批合併 | 合併前三項檢查（人工） | 只能人工（合併前） |
| 15 | Cloudflare 剝除協定名項（任一方向） | 步驟 6a（`[EPI1]`=A） | 擋部署（自動回滾） |
| 16 | Cloudflare 保留協定名、剝除 `bearer.` 項（請求方向） | `U13` 的 L3 實測（帶 token） | 只能人工 |
| 17 | 瀏覽器特有的失敗（`Origin`、bundle 內嵌網址錯誤、混合內容） | §五之二 的瀏覽器檢查 | 只能人工 |
| 18 | 部署重啟期間後端不可用超過約 60 秒，使用者需手動重連 | §五之二 第 7 步的觀察 | 只能人工 |
| 19 | `src/brain/testing/wsFrames.ts` 被 app 程式匯入而進正式 bundle | 無；完成條件以 grep 涵蓋（§四之一） | 無偵測 → §四之一 |
| 20 | `work_target_names_failed` 持續出現（DB 或授權異常使名稱全為 null） | 無告警；`monitoring-design.md` §四 的查詢 | 只能人工 |
| 21 | `ui-regression` 因新增案例逾時 15 分鐘 | `ui-regression`（`:558`、`:1061`） | CI 訊號（不擋合併） |

### 四之一、本站新增的補強（第 10、19 列；設計補強，非上游定案）

- **第 10 列**：code-generation 做一次性突變——在 `frontend/tests/` 下暫放一行 `new WebSocket(u, ['bearer.x'])`，`npm run lint` 必須紅，還原後複驗綠；結果記入 code-summary。
  它驗的是「`WS_SUBPROTOCOL_RESTRICTIONS` 真的展開進了 tests 區塊」，這件事在正常檔案集合下不會被任何東西觸發。
- **第 19 列**：完成條件 `grep -rn "brain/testing" frontend/src --include='*.ts' --include='*.tsx' | grep -v '^frontend/src/brain/testing/'` 為 0（app 程式不得匯入）。

兩項都是零依賴的一次性檢查；code-generation 採用或於 code-summary 記明拒絕理由，並於核可關卡揭露。

## 五、部署後檢查

### 五之一、自動（`deploy.yml` 內）

既有：資料面 `/api/auth/login` 401、公開網址 `/`。新增：步驟 6a（§二之一，`[EPI1]`=A）。三者都不需要 token。

### 五之二、人工（維運者，在 `192.168.10.10` 與一台能開 `https://cloud360.danniel.cc` 的瀏覽器）

**時機**：含本單元的變更第一次部署成功後、宣告入口頁可用之前；之後每次改 `frontend/nginx.conf`、`cloudflared` 映像或 ingress 時重跑第 1–4 步。
結果寫進 `build-and-test` 的產出（每步一列：指令或操作、`date -u` 時間、觀察值、通過與否）；**未完成第 1、4 步不得宣稱 `OPEN-EP14-13`／`OPEN-GW13-6` 結案**。

| # | 步驟 | 指令或操作 | 通過條件 |
|---|---|---|---|
| 1 | `U13` 的三層實測（帶 token） | 依 `brain-gateway/code-generation/code-summary.md` §六之二 第 1–4 項：`read -rs BRAIN_PROBE_TOKEN && export BRAIN_PROBE_TOKEN`；`docker exec -i -e BRAIN_PROBE_TOKEN -e BRAIN_WS_URL=<L1／L2／L3 網址> cloud360-backend-1 python - < probe.py`（`probe.py` 放 scratch 目錄、不進 repo）；標頭層以 `curl -H @"$hdr"` 檢查並遮罩；做完 `unset BRAIN_PROBE_TOKEN` | 三層皆 `negotiated: cloud360.brain.v1` → `got: ready`；標頭檢查有 `101` 與協定名、遮罩後無 `[REDACTED]`。這一步是 `bearer.` 項在 L3 存活的**唯一**證據 |
| 2 | 確認執行中的 nginx 就是 repo 的設定 | `docker exec cloud360-frontend-1 nginx -T \| grep -n -A16 'location /api/'` | 輸出與 `frontend/nginx.conf:16-32` 一致；無 `proxy_hide_header Sec-WebSocket-Protocol` |
| 3 | 免 token 的協定名探測（複核步驟 6a；6a 失敗回滾後用於定位） | 在主機上執行 §二之一 的 curl 一次（不需任何變數） | `HTTP/1.1 101` 且有 `sec-websocket-protocol: cloud360.brain.v1` |
| 4 | **瀏覽器端**（`OPEN-EP14-13` 的本意：入口頁可連線） | 以公開網址開頁（**不得**用區網 IP：bundle 的 WS 基底內嵌為公開網址，`infrastructure-specification.md` §一），以具 `K1 view` 的測試帳號登入 → 落在 `/`；開發者工具 Network 篩 WS，點 `/api/brain/ws` | 狀態 `101`；回應標頭有 `sec-websocket-protocol: cloud360.brain.v1`；網址**不含** `?`；Messages 先見送出的 `hello`、再見 `ready` 與 `work_target`／`sharing_mode`／`work_items` 快照；畫面不出現「無法連線到大腦」。**不得**截圖或複製請求標頭（含 token） |
| 5 | 對話一輪 | 在入口頁送一句一般訊息 | 逐字出現回覆（或封閉表內的錯誤訊息原樣顯示）；`docker logs --since 10m cloud360-backend-1 2>&1 \| grep 'cloud360.brain_gateway:turn_end '` 恰多一筆該輪的 `turnId`，該行不含所送文字 |
| 6 | 子頁面 | 依序進 `/workspace`、`/assessment` | 每頁 Network 中恰一條未關閉的 `/api/brain/ws`，前一頁那條已關閉；脈絡列顯示名稱或「（未命名）」，不是「（無法顯示名稱）」 |
| 7 | 部署重啟的實際表現（下一次部署時順帶觀察） | 部署開始前開著入口頁；部署完成後不重新整理 | 依 `EPN-02` 在約 60 秒內自行恢復（脈絡列回到正常態、對話紀錄保留）；若出現「重新連線」按鈕，記下大約時長——這是 `infrastructure-specification.md` §三「未量測」那一格的第一筆資料 |

**失敗時**：第 1 步 L1 失敗 → 應用層缺陷；L2 失敗、L1 通過 → 依 `U13` code-summary §六之二 第 5 項定位 nginx；L3 失敗、L2 通過（或第 3 步失敗）→ Cloudflare 剝除，
**沒有不改契約的修法**，以 revert PR 回滾並交使用者裁決（`U13` 第 4.5 節）；第 4 步失敗而第 1、3 步通過 → 瀏覽器特有因素，先比對 `Origin`、bundle 內的 WS 網址與主控台錯誤，記錄後交使用者。

### 五之三、`DEPLOY.md` 補一節（建議，非 blocking）

`U13` infrastructure-design 第 6.4 節建議在 `DEPLOY.md` 新增「入口頁部署後實測」，至今未落地（`grep -n "入口頁部署後實測" DEPLOY.md` 為 0）；現行步驟只存在於 record。
本單元是入口頁第一次對使用者可見的那一次合併，建議 code-generation 把 §五之二 第 1–4 步（第 1 步以引用 `U13` code-summary §六之二 的方式）與步驟 6a 的存在及失敗時的判讀（`[EPI1]`=A）寫進 `DEPLOY.md`。
不觸發 `project.md` 的 schema ↔ deploy blocking 規則（無 DDL）；採用或於 code-summary 記明拒絕理由。

## 六、回滾

| 面向 | 內容 |
|---|---|
| 自動 | `ut` 合併觸發的部署失敗時，`rollback` job（`deploy.yml:596-602`）還原 last-good、開 revert PR、交 Deploy Doctor。本 intent 第一次進 `ut` 時 last-good 在 intent 之前，回滾會退回**整個** intent |
| 手動 | `git revert` 本 intent 的合併 commit；不需動資料庫或 Redis（無 DDL、名稱不儲存） |
| 回滾後的用戶端 | 已載入新 bundle 的分頁連不上 WS，依退避 60 秒後放棄並顯示說明，不形成重試風暴（`infrastructure-specification.md` §三） |
| 安全面代價 | 回滾使 `U13` 目錄、名稱、直接設定三處的可見性守門一併消失——但同時 `/api/brain/ws` 本身也不存在，故不會重開被移出者經大腦取得名稱的路徑 |
| 資料 | 無資料遷移，無需反向遷移 |

## 七、CI/CD 中的 secrets

零新增。步驟 6a 不讀任何 secret、輸出不含 token；人工檢查的 token 只存在於維運者 shell 的環境變數，不經 `docker exec` 或 `curl` 的 argv、不進任何 log 或 issue
（`U13` code-summary §六之二 第 1、2、4 項）。CI 中的 `JWT_SECRET: ci_only_not_a_real_secret` 與測試 stack 的 `OPENROUTER_API_KEY: ""` 為既有的非機密值。
