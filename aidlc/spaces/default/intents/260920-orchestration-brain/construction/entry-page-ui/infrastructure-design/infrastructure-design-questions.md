# Infrastructure Design 問題檔 — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T04:41:16Z（`date -u` 取值）。單元類型 **`ui`**（含 C-8 的後端改動：`U7`／`U2`／`U13`）；`produces_kinds` 使四份產出全數適用。
>
> 本站出 **2 題**（`EPI1`、`EPI2`）。兩題都是查證時才浮現、且有真實取捨的事項：`EPI1` 來自一個上游沒有用到的事實（閘道對「只帶協定名、不帶 token」的
> 握手會先 accept 再以 4401 關閉，`backend/services/brain_gateway.py:723-726` 經 `:651-653`），使 Cloudflare 那一跳的子協定透傳**可以免 token 自動驗證**；
> `EPI2` 來自一個上游沒有發現的缺口（既有 e2e 的落地斷言與 `BR91.1` 直接衝突，見 `cicd-pipeline.md` §三）。其餘事項由上游定案或 repo 現況決定，逐項判定見下表。
> 產出檔已依兩題的**建議項**寫成，並在每個受影響處標明「待 `EPI1`／`EPI2` 裁決」與其他選項下的改法。

## 〇、上游已定案、本站不重問

| 事項 | 定案 | 出處 |
|---|---|---|
| 協定維持 `v: 1`、`U13` 與 `U14` 同一次合併、合併前三項檢查 | `NFR5.141`；帶入項 functional-design `R-07` | `../nfr-design/logical-components.md` §五 |
| 零新環境變數、零 compose 變更、零新依賴 | `NFR8.140`、`EPN-21` | `../nfr-requirements/tech-stack-decisions.md` |
| 子協定方案（雙子協定、只回送協定名）；token 不進網址 | `U13` functional-design `[GW1]`=A；`EPN-16` | `../../brain-gateway/infrastructure-design/infrastructure-design-questions.md` §一 |
| `OPENROUTER_API_KEY` 為部署必要 secret、DEMO 後端在第一次進 `ut` 前移除 | `U13` `[IG1]`=A、`[IG2]`=A | 同上 §三 |
| Cloudflare 那一跳若剝除標頭：沒有不改契約的修法，回到使用者裁決、裁決前以 revert 回滾 | `U13` infrastructure-design 第 4.5 節 | `../../brain-gateway/infrastructure-design/infrastructure-specification.md:123-129` |
| 部署後三層實測（L1／L2／L3，需 token、只能人工） | `U13` code-generation | `../../brain-gateway/code-generation/code-summary.md` §六之二 |

## 一、stage 檔六個 focus area 的逐項判定

| focus area | 判定 | 依據 |
|---|---|---|
| 部署策略 | **有標的：同批約束、部署後實測、部署重啟造成的重連** | `infrastructure-specification.md` §三、§四；`cicd-pipeline.md` §三、§五 |
| 運算／儲存／網路 | **無新資源；一處逐跳查證（沿用 `U13`）** | `frontend/nginx.conf:16-32` 已承載 WS 升級；`deploy/cloudflared/config.yml:11-18` 無可調標頭設定 |
| 監控 | **無新管線**；新增一筆 WARNING 的查詢方式 | `monitoring-design.md` |
| CI/CD | **有標的：`EPI1`（部署流程）、`EPI2`（既有 e2e）** | `cicd-pipeline.md` §一、§三、§四 |
| Secrets 管理 | **無標的** | 零新 secret；部署後人工檢查沿用 `U13` 的 token 處置（不經 argv、不進 log） |
| 擴縮政策 | **無標的** | 單一 uvicorn 進程與閘道的應用層上限不變；`U14` 每分頁一條連線（`EPN-01`） |

## 二、問題

### EPI1. 部署流程要不要加一道**免 token** 的子協定透傳自動檢查？（`OPEN-EP14-13`）

**背景**：入口頁唯一的通道是 `/api/brain/ws`，它要求瀏覽器在 `Sec-WebSocket-Protocol` 同時帶 `cloud360.brain.v1` 與 `bearer.<token>`，伺服器只回送前者。
這個標頭在 Cloudflare edge／`cloudflared` 兩跳的請求與回應方向是否原樣透傳，**至今沒有實測**（`OPEN-GW13-6`，本單元沿用為 `OPEN-EP14-13`）；
CI 的 `ui-regression` 只走 nginx 一跳。`U13` 當時判定自動化做不到，理由是「正向實測需要有效 token，而 Actions log 公開」——這個理由**對帶 token 的實測仍成立**。
本站查證後發現另一條路：只送 `cloud360.brain.v1`、不帶 token 時，閘道**先 accept 並回送協定名、再以 4401 關閉**（`brain_gateway.py:723-726` → `:651-653`）。
所以從部署 runner 對公開網址送一個只帶協定名的升級請求，看到 `HTTP/1.1 101` 與 `sec-websocket-protocol: cloud360.brain.v1`，就證明協定名這一項在 Cloudflare 兩跳
**雙向**都透傳了；請求被剝除時閘道不 accept（回 403），回應被剝除時看不到那一行。它**不**證明 `bearer.` 那一項在請求方向存活——那一半仍只能由 `U13` 的人工 L3 實測證明。
部署 runner 本來就會打公開網址（`deploy.yml:358` 起的 tunnel 步驟），不需要新 secret，輸出只有狀態列與協定名、不含任何 token。

A) **加進 `deploy.yml`，失敗即部署失敗**（建議）：在 `Verify sessions survive a Redis restart` 之後、`Record this commit as the last-good deployment`（`deploy.yml:570`）之前新增一步，
   重試數次（比照 tunnel 步驟），全部失敗才判失敗。
   得到：每一次部署（含日後改 `frontend/nginx.conf`、換 `cloudflared` 映像）都機械驗證 Cloudflare 兩跳的協定名雙向透傳；失敗時**不會**把入口頁不可用的版本記為 last-good，
   既有 `rollback` job 自動還原並開 revert PR——正好就是 `U13` 第 4.5 節對「L3 失敗」定下的處置（回滾、再交使用者裁決）。
   代價：`deploy.yml` 多一步，影響全部單元的部署；本 intent 第一次進 `ut` 時若失敗，回滾會連同整個 intent 一起退回（last-good 在 intent 之前）；Cloudflare 一時異常可能造成誤回滾（以重試緩解）；
   `bearer.` 項與瀏覽器端的實際體驗仍要人工確認（`cicd-pipeline.md` §五）。新步驟不得放進 `rollback` job 的驗證——last-good 若早於 `U13` 就沒有這個端點，會讓回滾本身失敗。
B) **加進 `deploy.yml`，但只發警告、不擋部署**：同一步驟改為 `continue-on-error: true`，失敗寫 `::warning::` 與 `GITHUB_STEP_SUMMARY`（比照 `deploy.yml:388` 的 mcp-bridge 健康步驟）。
   得到：同樣的訊號、不會誤回滾。代價：入口頁不可用的版本照常上線**並記為 last-good**——之後任何一次部署失敗，自動回滾會回到這個壞版本。
C) **不改管線，把同一道 curl 加進人工部署後檢查**（與 `U13` 的三層實測同一次執行）。
   得到：本單元維持「零 workflow 變更」。代價：沒人執行就沒有訊號；之後每次改 nginx／`cloudflared` 映像時要靠記得重跑。
D) **其他**：請說明。

[Answer]: A <!-- 2026-10-17T04:50:39Z 使用者經選單作答（選項順序與本檔一致，建議項為 A；選項 D「其他」由選單內建的 Other 承載） -->

### EPI2. 既有 e2e 的「登入後落在 `/workspace`」斷言要怎麼處置？

**背景**：`BR91.1` 讓具 `K1 view` 的使用者造訪 `/` 時直接看到入口頁，不再導往 `/workspace`。登入頁成功後一律 `navigate('/')`（`frontend/src/pages/LoginPage.tsx:107`），
而 e2e 用的 seed 帳號 `admin`（`Platform_Admin`）與自行註冊後核准的 `Developer` 都有 `K1 view`（`schema_rbac.sql:1206`、`:1198`）。因此 `U14` 上線後，下列既有斷言**必然失敗**：
`frontend/tests/e2e/regression.spec.ts` 的 `toHaveURL(/\/workspace/)` 共 6 處（`:73`、`:90`、`:113`、`:158`、`:173`、`:189`；其中 `:189` 在 `gotoAdmin` 內，被 8 個測試共用），
與 `estimate-workspace.spec.ts:17`、`:35` 的 `toHaveURL(/\/(workspace|cost)/)`——**共 14 個測試**在 `ui-regression` 變紅。上游寫的是「既有 `regression.spec.ts` 必須保持綠燈」
（`../functional-design/functional-spec.md:349`），但沒有發現這些斷言本身就在描述被 `BR91.1` 刻意改掉的舊落點，所以「不改它們而保持綠燈」做不到。
另一層限制：Kiwi TCMS 以測試名稱作為案例鍵（`--summary-template '${name}'`；`.github/workflows/ui-regression.lock.yml:568` 的註解逐字「changing it orphans the old cases」）。

A) **改斷言、只為一個測試改名**（建議）：`管理員登入後進入工作區`（`:71`）的目的就是落點，改為斷言入口頁並改名為「管理員登入後進入入口頁」——舊 Kiwi 案例成為孤兒，
   在 `tcms-test-cases` 的同步報告記明並把舊案例標為停用；其餘 13 個測試的目的不是落點，**名稱不變**，只把落點斷言改為 `not.toHaveURL(/\/login$/)`
   （需要工作區時再 `page.goto('/workspace')`），並更新其 `@purpose`／`@step` 註解。
   得到：每個測試名稱與它驗的事一致；新落點另由本單元的入口頁 e2e 驗證（`EPN-17`）。代價：一個孤兒案例；14 個測試的斷言與註解在同一個 PR 改動，審查要逐一核對沒有順手放寬其他斷言。
B) **全部不改名，只改斷言**：零孤兒。代價：`管理員登入後進入工作區` 的名稱與內容長期不符，而名稱正是 TCMS 上看得到的那一行（`@purpose` 會更新，名稱不會）。
C) **在測試 helper 內登入後一律 `page.goto('/workspace')`**，連 `:71` 也一樣：零孤兒、名稱表面成立。代價：`:71` 實際上不再驗任何落點，卻保有「進入工作區」的名稱與歷史結果——
   這是 B 的代價換了一個更難看出來的形狀。
D) **其他**：請說明。

[Answer]: A <!-- 2026-10-17T04:50:39Z 使用者經選單作答（選項順序與本檔一致，建議項為 A；選項 D「其他」由選單內建的 Other 承載） -->

## 三、考慮過、刻意不出成題目的候選（附理由）

| # | 候選 | 不出題的理由 |
|---|---|---|
| 1 | 把帶 token 的 L3 實測放進 workflow | `U13` 已判定不可行（需要有效 token、Actions log 公開）；本站重查理由仍成立。`EPI1` 是它可自動化的那一半 |
| 2 | 改 `frontend/nginx.conf` 以「確保」轉送 `Sec-WebSocket-Protocol` | nginx 預設即轉送全部請求標頭，`U13` code-summary §六之二第 5 點已更正該回退為 no-op；本單元無需改動（`infrastructure-specification.md` §二） |
| 3 | 把 `DEPLOY.md` 補上「入口頁部署後實測」一節 | `U13` infrastructure-design 第 6.4 節列為建議、至今未落地（`grep -n "入口頁部署後實測" DEPLOY.md` 為 0）。補文件無取捨、無替代方案，本站直接列為 code-generation 的建議項（`cicd-pipeline.md` §五之二），採用或於 code-summary 記明拒絕理由 |
| 4 | 量測部署重啟期間的後端不可用時間，決定退避 60 秒是否夠 | 沒有量測來源；退避 60 秒是已核可的 `EPN-02`。本站把「重啟期間入口頁的實際表現」列為部署後人工觀察項（`cicd-pipeline.md` §五第 7 步），不重開 `EPN-02` |
| 5 | `CI import smoke` 對 `membership_facade_factory` 漏傳無效（`logical-components.md` §三 第 1 列的「誰會發現」含它） | 這是對上游一句說明的**對齊修正**，不是新決定：`build_brain_gateway` 在 startup hook 內呼叫（`backend/main.py:84`，`:82-83` 的註解逐字說明 import smoke 不觸發它），故 import smoke 抓不到。真正會發現的閘門見 `cicd-pipeline.md` §四第 5 列；上游檔不回改 |
