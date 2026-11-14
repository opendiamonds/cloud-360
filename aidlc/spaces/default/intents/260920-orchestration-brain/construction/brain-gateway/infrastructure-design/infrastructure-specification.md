# 基礎設施規格 — `U13 brain-gateway`

> 承接 `../nfr-design/` 六份產出與 `../functional-design/functional-spec.md` §8.2 指派給本站的開放項。
> 本單元**不新增任何服務、埠、volume 或環境變數**（`NFR13.44`）；它是 embedded 在既有 `backend` 行程內的
> WebSocket 端點（`functional-spec.md:22`）。本站的實質內容是**既有路徑能不能承載它**（逐跳標頭透傳、
> 單一行程、啟動必要條件）與**它上線的方式**（同批約束、回滾、事後實測）。
> 所有 `<檔名>:<行號>` 引用於 2026-10-13 以 `sed -n`／`awk` 逐行印出核對（HEAD `c724977` 的工作樹）。

## 一、Deployment

| Facet | Choice | Rationale |
|---|---|---|
| 運算模型 | **embedded**：與既有 FastAPI 同一個 uvicorn 行程（`backend/Dockerfile:30`），由 `main.py` 的 startup hook（`main.py:55-77`）建立閘道元件 | 零新進程（`nfr-requirements-questions.md:24`）；扇出與推播靠行程內登錄，屬 `K-12` 已核可的單一行程假設（`A-1`） |
| 行程數 | **恰一個 uvicorn worker**，以 `NFR13.33` 的文字／YAML 測試守住（見第七節） | 多行程時扇出與推播**靜默**失效（`functional-spec.md:440`） |
| 網路拓樸 | 不變：`cloudflared`（`edge`）→ `frontend` nginx（`edge`）→ `backend:8000`（`edge`＋`internal`）→ `redis`／`ollama`／`db`（`internal`）（`deploy/docker-compose.deploy.yml:169`、`:365`、`:390`） | 端點掛在 `/api/brain/ws`，由既有 `location /api/`（`frontend/nginx.conf:16-32`）承載，**不需新 location** |
| 對外路徑 | `wss://cloud360.danniel.cc/api/brain/ws`（`functional-spec.md:33`） | 與 DEMO 同一路徑；DEMO 必須同批刪除（第五節） |
| 儲存 | 不新增。會話狀態只在既有 Redis（AOF、named volume `redis_aof`，`docker-compose.deploy.yml:288-292`）；行程內只有連線暫態（`NFR13.31`） | 重啟即失的只有連線綁定的暫態，重連以 `load`＋`list_items` 取回 |
| 環境 | 本機 dev（`backend/.env`）、CI 測試（`deploy/docker-compose.test.yml`）、staging（`deploy/.env` ← `deploy/render-env.sh`）三者**皆不新增變數**；三個 `REDIS_*` 由「選用」變為「後端啟動必要」（第六節） | `NFR13.32`、`NFR13.44`、`project.md ## Mandated` 三環境分離 |
| IaC | 無。部署資產為 compose 檔與 `deploy.yml`；本單元**不改** `docker-compose.deploy.yml`、`render-env.sh`、`deploy/.env.example`、`frontend/nginx.conf`、`deploy/cloudflared/config.yml`（除非第四節的實測失敗而走 4.5 的 nginx 修法） | 既有路徑靜態查證足以承載（第四節），差的只是實測 |
| 資源額度 | 不改 `backend` 的 `memory: 2g`（`docker-compose.deploy.yml:179`）。新增常駐：4 條 `brain-memory` 執行緒、每連線一個重驗 task；連線上限 200（`NFR13.17`）× 暫存佇列 256（`NFR13.22`）為最壞記憶體界 | 每則訊框 ≤ 64 KiB（`NFR13.19`）只約束**應用層**；uvicorn 在交給應用前仍可緩衝到 16 MiB（第九節殘留）。數值未量測，沿用 compose 檔頭「PROVISIONAL」的定位（`:11-22`） |

## 二、Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| `backend`（uvicorn） | WebSocket 終點 | `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`（`Dockerfile:30`），**無 `--workers`、無 `--ws-*` 參數** | WebSocket keepalive 依 uvicorn 預設的伺服器端 ping（**推論**：`fastapi[standard]` 帶入 `uvicorn[standard]`／`websockets`，預設每 20 秒 ping；`requirements.txt:10` 的 `uvicorn` 未釘版，本站未實讀其原始碼）。不得加 `--ws-ping-interval 0`——那會讓第 4.3 節的兩個閒置逾時生效 |
| `frontend`（nginx） | 反向代理、WS 升級 | `location /api/`：`proxy_http_version 1.1`、`Upgrade`／`Connection` 改寫（`nginx.conf:18-21`）、`proxy_buffering off`、`proxy_read_timeout`／`proxy_send_timeout 600s`（`:29-31`）；`$connection_upgrade` 的 map 在映像內產生（`frontend/Dockerfile:21-23`） | 既有協作 WS（`/api/collab/ws/{workspace_id}`）已走同一 location（`nginx.conf:12-15` 註解）。子協定標頭透傳見第四節 |
| `cloudflared` | 公開入口（TLS 終結於 Cloudflare edge） | `service: http://frontend:80`、`connectTimeout: 30s`、`tcpKeepAlive: 30s`（`deploy/cloudflared/config.yml:11-18`） | `tcpKeepAlive` 的註解逐字為協作 WS 而設（`:17`）；本單元沿用、不改 ingress |
| `redis` | session 狀態（`U10`／`U12` 擁有） | 既有：AOF、`noeviction`、ACL 使用者（`docker-compose.deploy.yml:251-287`） | 本單元只是新的呼叫端。Redis 暫時不可達：握手期間 1011、ready 後該輪 `error`（`NFR13.23`） |
| `ollama` | 記憶嵌入（`U6`／`U8` 擁有） | 既有，`bge-m3`，部署後 `ollama pull`（`deploy.yml:245-282`） | 本單元的預取／episodic 寫入走專用 4 執行緒執行器與 30 秒熔斷（`NFR13.5`、`NFR13.25`）。冷載首呼叫耗時決定 `NFR13.3` 的等待上限，量測落 code-generation／build-and-test（`performance-design.md:95`） |
| `db`（PostgreSQL） | 認證、`K1`、對象目錄 | 既有 | 本單元**無 DDL**——`schema_rbac.sql`／`DEPLOY.md` 的 blocking 同步規則**不觸發** |
| 計費 LLM（OpenRouter） | `U11.classify` 的唯一計費下游 | `OPENROUTER_API_KEY`：GitHub secret → `deploy.yml:109` → `render-env.sh:109`（`${...:-}`，**optional**）→ compose `:91` | 金鑰為空時入口頁**每一輪**失敗（`OPEN-GW13-7`），處置待使用者裁決（第八節、問題檔 `IG1`） |

## 三、Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| `backend` 行程與其 asyncio 事件迴圈 | `brain-infra`（`U1`，部署形狀） | 全部後端 router；`U13` 新增長連線 | 單一行程是 `K-12` 的前提；`U12` 在事件迴圈上的同步 Redis 呼叫（`OPEN-GW13-4`，最壞約 3.3 秒）會延遲所有連線——量測落 build-and-test |
| 預設 `to_thread` 執行緒池 | Python 執行環境 | `U13`（認證、重驗、session 讀寫）、其他 router | 帶入項 26：Redis 故障時與認證共用池，可能延遲撤權（`nfr-design` R-09 揭露）；記憶工作**不**佔此池（`NFR13.5`） |
| Redis ACL 使用者 `REDIS_USER` | `brain-infra` | `U10`、`U12`、`U13` | 同一身分（`+@all -@admin -@dangerous`，無 pub/sub channel 授權，`docker-compose.deploy.yml:247-250`）。本單元不用 pub/sub（單一行程扇出），故無需新增 `&<pattern>` |
| `frontend` nginx 的 `location /api/` | 既有（ADR-0007） | 全部 HTTP API、協作 WS、`U13` | 同一組逾時與升級標頭；改動會同時影響協作 WS |
| `cloudflared` tunnel ingress | 既有 | 全站 | 單一 hostname 規則；本單元不改 |

## 四、WebSocket 逐跳路徑與 `Sec-WebSocket-Protocol` 透傳（`OPEN-GW13-6`）

### 4.1 為什麼這件事是入口頁的單點故障

`[GW1]`=A：瀏覽器同時提供 `cloud360.brain.v1` 與 `bearer.<jwt>`，伺服器只回送 `cloud360.brain.v1`（`NFR13.7`）。
兩個方向任一被剝除都會讓連線失敗，且**不是降級**：
- **請求方向**被剝除 → 伺服器看不到 `cloud360.brain.v1` → 未 accept 即拒絕（HTTP 403，`BR61.3`），也拿不到 token。
- **回應方向**被剝除 → 客戶端提供了子協定、伺服器回應卻沒有 → 瀏覽器依 RFC 6455 中止連線（客戶端看到的是一般的連線失敗）。

`[GW1]` 的 B（回送 `bearer.<jwt>`）同樣依賴這個標頭，**不是**這個風險的替代方案。

### 4.2 逐跳靜態查證

| 跳 | 請求方向 | 回應方向 | 依據 | 判定 |
|---|---|---|---|---|
| 瀏覽器 → Cloudflare edge → `cloudflared` | 未查證 | 未查證 | Cloudflare 官方文件只寫「proxied WebSocket connections 無需額外設定」（[developers.cloudflare.com/network/websockets](https://developers.cloudflare.com/network/websockets)），**未提及子協定標頭**；本站以網路搜尋找不到官方對 `Sec-WebSocket-Protocol` 透傳的明文。`config.yml` 沒有任何可調整標頭的設定（`:13-18` 只有逾時與 TLS） | **未查證**——只能以第 4.4 節的實測判定 |
| `cloudflared` → nginx（`http://frontend:80`） | 同上 | 同上 | 同上 | **未查證** |
| nginx → `backend:8000` | **透傳（靜態判定）** | **透傳（靜態判定）** | (a) `location /api/` 只以 `proxy_set_header` **新增／覆寫** `Upgrade`、`Connection`、`Host`、`X-Real-IP`、`X-Forwarded-For`、`X-Forwarded-Proto`（`nginx.conf:20-26`），沒有任何指令把 `Sec-WebSocket-Protocol` 設為空值；nginx 預設 `proxy_pass_request_headers on`，其餘客戶端標頭原樣轉送（[nginx `ngx_http_proxy_module`](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass_request_headers)）。(b) 回應方向：nginx 預設只隱藏 `Date`、`Server`、`X-Pad`、`X-Accel-*`（同文件 `proxy_hide_header`），本檔無 `proxy_hide_header`。(c) 升級：`proxy_http_version 1.1` ＋ `Upgrade`／`Connection` 改寫是 nginx 官方 WebSocket 代理的標準形狀（[nginx WebSocket proxying](https://nginx.org/en/docs/http/websocket.html)），`$connection_upgrade` 的 map 存在（`frontend/Dockerfile:21-23`） | **靜態判定為透傳**；仍須實測（設定與執行期行為之間還有映像版本） |
| 標頭長度 | `bearer.<jwt>` 單行數百位元組（**推論**，本站未量 JWT 長度） | — | nginx 預設 `large_client_header_buffers 4 8k`，本檔未調整 | 遠低於上限；若日後 JWT 加大量 claim，第一個壞的是此處（HTTP 400） |

**沒有既存證據可借用**：DEMO（`brain_router.py`）也走子協定，但它從未經 `deploy.yml` 部署——DEMO 的 commit `f9c5bda`（2026-09-28）不在 `origin/ut`，而本分支最後一次觸發部署的 head `c6688f1`（2026-09-21）不含它（`git merge-base --is-ancestor` 為否）。協作 WS 經過同一路徑，但**不使用子協定**，只能證明升級本身可行。

### 4.3 閒置逾時（同一路徑的第二個前提）

| 層 | 閒置上限 | 依據 | 本單元的處置 |
|---|---|---|---|
| nginx | 600 秒無讀／寫即斷（`nginx.conf:30-31`） | 設定實讀 | uvicorn 伺服器端 ping（**推論**為預設 20 秒）構成讀寫，連線不會因閒置被 nginx 切斷 |
| Cloudflare edge | 未查證（本站未取得官方數值） | — | 同上；且 `U14` 對 4401／斷線的重連退避（帶入項 10、17）是最後防線 |
| 本單元 | 10 秒 hello 逾時、60 秒背景重驗 | `functional-spec.md` D-12、A-3 | 重驗不送訊框，不構成 keepalive |

### 4.4 部署後實測步驟（分三層定位）

**執行者**：維運者在 `192.168.10.10`（self-hosted runner 所在主機）上手動執行；**不放進任何 workflow**——需要一個有效 token，
而本 repo 為 public、Actions log 公開（`project.md ## Mandated` 的 secrets／variables 規則同一理由）。
**時機**：含 `U13` 的變更部署成功後、宣告入口頁可用之前；之後每次改動 `frontend/nginx.conf`、`cloudflared` 映像或 ingress 時重跑。

**前置**：
1. 以一個**具 `K1.view` 且已核准**的測試帳號登入取得 token，存在 shell 變數 `BRAIN_PROBE_TOKEN`，不寫進檔案、不貼進任何 issue／PR／log；
   做完 `unset BRAIN_PROBE_TOKEN`。
2. 探測腳本 `probe.py`（放 scratch 目錄、不進 repo）；`websockets` 已隨 `fastapi[standard]` 安裝在 backend 映像內（`NFR13.39`：不新增套件）。
   只印訊息型別，不印內容：

```python
import asyncio, json, os, websockets
async def main():
    protos = ["cloud360.brain.v1", "bearer." + os.environ["BRAIN_PROBE_TOKEN"]]
    async with websockets.connect(os.environ["BRAIN_WS_URL"], subprotocols=protos) as ws:
        print("negotiated:", ws.subprotocol)
        await ws.send(json.dumps({"v": 1, "type": "hello", "payload": {"v": 1}}))
        while (t := json.loads(await asyncio.wait_for(ws.recv(), 15))["type"]) != "ready":
            print("got:", t)
        print("got: ready")
asyncio.run(main())
```

**三層執行**（三層皆從 backend 容器內發起，故使用同一份 `websockets`；第一個失敗的層就是剝除標頭的那一跳。`cloud360-backend-1` 為 compose 預設命名 `<project>-<service>-1`，project 名 `cloud360` 見 `docker-compose.deploy.yml:32`）：

| 層 | 指令 | 預期（通過條件，全部成立） |
|---|---|---|
| L1 後端直連（不經 nginx） | `docker exec -i -e BRAIN_PROBE_TOKEN -e BRAIN_WS_URL=ws://127.0.0.1:8000/api/brain/ws cloud360-backend-1 python - < probe.py` | 印出 `negotiated: cloud360.brain.v1`，之後 `got: ready` |
| L2 經 nginx（不經 Cloudflare） | `docker exec -i -e BRAIN_PROBE_TOKEN -e BRAIN_WS_URL=ws://frontend:80/api/brain/ws cloud360-backend-1 python - < probe.py`（`backend` 在 `edge` 網路上，可解析 `frontend`，`docker-compose.deploy.yml:169`、`:365`） | 同 L1 |
| L3 經 tunnel（完整公開路徑） | `docker exec -i -e BRAIN_PROBE_TOKEN -e BRAIN_WS_URL=wss://cloud360.danniel.cc/api/brain/ws cloud360-backend-1 python - < probe.py`（`edge` 未設 `internal: true`，容器有對外路徑，`:397-416`） | 同 L1 |

**標頭層補充檢查**（只看握手、不需 `websockets`；確認回應**不含** token，`NFR13.7` 的部署面複驗）：

```text
curl -sS -o /dev/null -D - --http1.1 --max-time 5 \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  -H "Sec-WebSocket-Protocol: cloud360.brain.v1, bearer.${BRAIN_PROBE_TOKEN}" \
  https://cloud360.danniel.cc/api/brain/ws
```

預期：狀態列 `HTTP/1.1 101`；有一行 `sec-websocket-protocol: cloud360.brain.v1`；整段輸出 `grep -ci bearer` 為 **0**。
（101 之後 curl 會等到 `--max-time` 而以結束碼 28 離開，屬正常。）
**負向對照**：去掉 `cloud360.brain.v1` 只留 `bearer.…` → 預期 `HTTP/1.1 403`（`BR61.3`；這同時證明 DEMO 已不在該路徑上——DEMO 對同一請求會 accept）。

結果寫進 `build-and-test` 的產出（三層各一列：指令、時間 `date -u`、`negotiated` 值、是否 ready）；**未實測不得在任何產出宣稱 `OPEN-GW13-6` 結案**。

### 4.5 失敗時的回退

| 失敗層 | 判讀 | 回退 |
|---|---|---|
| L1 | 應用層缺陷，與基礎設施無關 | 依 code-generation 的修正流程；入口頁不可用期間以 revert PR 回滾（第五節 5.4） |
| L2 失敗、L1 通過 | nginx 剝除或未轉送 | 在 `location /api/` 加 `proxy_set_header Sec-WebSocket-Protocol $http_sec_websocket_protocol;`（請求方向；不得用固定值），確認無 `proxy_hide_header Sec-WebSocket-Protocol`（回應方向）。同一 PR 須同步 `LOCAL-DEV.md`（`project.md ## Mandated` 點名的是 `deploy/nginx.conf`，**實際檔案是 `frontend/nginx.conf`**——該條規則的路徑已不存在，精神仍適用）。協作 WS 同 location，須一併回歸 |
| L3 失敗、L2 通過 | Cloudflare edge 或 `cloudflared` 剝除；`config.yml` 無可調設定 | **沒有不改契約的修法**。唯一不依賴此標頭的方案是 `[GW1]` 的 **C**（accept 後首則訊息帶 token）：須推翻 `[GW1]`=A、改 `K-12`、新 ADR，且引入 `US8` DoD 點名的 pre-accept 暴露面——**必須回到使用者裁決**，不得由實作者逕行改用。query string 帶 token 被 `NFR13.8`／`AC8.1.3` 禁止，不是選項。裁決前以 revert PR 回滾 |

## 五、部署順序、同批約束與回滾（`OPEN-GW13-10`）

### 5.1 現況事實

- 本 intent 的全部程式在單一功能分支 `danniel/docs/orchestration-brain-ideation`，**領先 `origin/ut` 83 個 commit、落後 0 個**（`git log --oneline origin/ut..HEAD | wc -l`）；`origin/ut` 不含任何 brain 單元。
- `deploy.yml` 只在 PR 合併進 `ut` 時觸發（`deploy.yml:10-15`），每次合併即一次真實部署。
- `U13` 與 `U14` 同屬 B6（`bolt-plan.md:294`），同批理由是 `[D3]`=B 的信心假說判準（`delivery-planning/memory.md:7`），**不是** `delivery-planning:c6`。

### 5.2 必須同批的變更（不得分屬兩次合併）

| 變更 | 必須與誰同批 | 不同批會怎樣 | 是否有機械閘門 |
|---|---|---|---|
| 刪除 DEMO 後端：`backend/services/brain_router.py`、`main.py:7`、`main.py:110-112` | `U13` 的 handler（同一路徑 `/api/brain/ws`） | 兩者並存時同一路徑註冊兩個 WebSocket 路由，先註冊者勝出——行為取決於 `include_router` 順序，**無聲**；只刪 DEMO 不上 `U13` → 入口路徑消失 | **無**。code-generation 應補一條測試：`app.routes` 中路徑為 `/api/brain/ws` 的 WebSocket 路由恰為 1 條、且端點函式屬 `brain_gateway` 模組 |
| 契約增量 C-1～C-7＋重產 `ws-contract.json`／`frontend/src/types/ws-contract.d.ts`（`functional-spec.md` §十一之二） | `U13`（讀寫新欄位）、DEMO 前端的刪除或改寫、`U14` | 模型改了而衍生物沒重產 → CI 紅燈；衍生物重產而前端未跟上 → `tsc -b` 紅燈（`page` 缺，`functional-spec.md` §十一之二第 6 點） | **有**：`ci.yml:299-300`（`dump_ws_contract.py --check`）、`ci.yml:218-219`（`check:ws-types`）、`ci.yml:222-223`（`npm run build` 含 `tsc -b`） |
| DEMO 前端：`frontend/src/pages/BrainPage.tsx`、`App.tsx:89-99`、`Sidebar.tsx:212-219` | `U13` | DEMO 頁只帶 `bearer` 一個子協定（`BrainPage.tsx:98-100`）→ `U13` 下握手 403 | **部分**：`tsc -b` 只抓到型別（`page` 缺）；**握手不相容沒有任何閘門抓得到**（無 `/brain` 的 e2e） |
| `U14` 入口頁 | `U13` | `U13` 單獨上線＝部署一個沒有呼叫端的端點（B6 信心假說不成立） | 無（排程約束） |
| `ADR-0020` 核可 | **早於**含 C-1～C-7 的 commit | 依賴它的規則不得合併（`NFR13.41` ③） | 人工（`inception/decisions/` 目前到 `0019`） |

### 5.3 一條比同批更強的約束：DEMO 不得先於 `U13` 進 `ut`

DEMO 把 token 回送進**回應標頭**（`brain_router.py:275`，`functional-spec.md` F-1）。DEMO 的 commit 與本 intent 其他單元在同一分支；
若本分支以「逐 Bolt 合併」方式把 B1～B5 先送進 `ut`，**DEMO 會隨之部署到公開的 staging**，在 B6 合併前一直帶著這個缺陷。
兩種滿足方式（擇一，屬合併策略，非本站決定）：(a) 整個 intent 以一次合併進 `ut`；(b) 逐 Bolt 合併時，第一次合併即移除 DEMO
後端與前端（屆時 `/brain` 無頁面，直到 B6）。**不允許**的形狀：DEMO 先上、B6 後到。

### 5.4 回滾

| 情境 | 做法 | 結果與殘留 |
|---|---|---|
| 部署 job 本身失敗 | 既有 `rollback` job（`deploy.yml:542` 起）：還原 last-good、開 revert PR、交 Deploy Doctor | last-good 是合併前的 `ut`——不含任何 brain 單元，入口頁與 `/api/brain/ws` 一起消失，前後端一致 |
| 部署成功但第 4.4 節實測失敗（L2／L3） | **不會自動回滾**（實測是人工步驟）。維運者開 revert PR 還原該次合併 | 同上。Redis 中已寫入的 session key 舊程式不讀，隨 24h TTL 消失；本單元無 DDL，沒有資料表要還原。**同批的其他單元有 DDL**（例：`U4`／`U5`／`U18`），其表在回滾後保留——屬各單元自身的回滾說明 |
| 只需停用入口頁、保留其他單元 | 無開關（本單元無 feature flag，`NFR13.44` 禁止新增環境變數） | 只能以 revert 程式達成；若日後需要，屬新的設計決定 |

## 六、環境設定（三環境分離）與文件同步

### 6.1 變數

本單元讀取的環境變數只有 `REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD`（`NFR13.44` ①），三者皆**既有**：

| 範圍 | 位置 | 現況 | 本單元的變化 |
|---|---|---|---|
| staging | `docker-compose.deploy.yml:117-119`（無 `:-`）；`render-env.sh:127-129`（URL／USER 為字面值、PASSWORD 來自 secret）；`render-env.sh:71` 拒絕空 `REDIS_PASSWORD`；`deploy/.env.example:101-111` | 已是必要 | 無 |
| CI 測試 stack | `docker-compose.test.yml:93-95`（`:-` 內嵌測試值） | 有預設 | 無——`ui-regression` 的後端照常啟動 |
| 本機 dev | `backend/.env.example:101-109` | 已記載；但 `LOCAL-DEV.md:23` 寫成「缺了只是 session 功能不可用」 | **語意變更**：缺值或 `REDIS_USER=default` → 後端拒絕啟動（`NFR13.32`）。須改 `LOCAL-DEV.md`（6.3） |

**單一行程守門的部署面補充**（細化 `reliability-design.md` §九的「限制」）：`backend` 服務的 `environment:` 是**逐鍵列舉**
（`docker-compose.deploy.yml:84-147`、`docker-compose.test.yml:78-125`），沒有 `env_file:`。故 `WEB_CONCURRENCY`／`UVICORN_WORKERS`
即使出現在 `deploy/.env` 或主機 shell，**也不會進入容器**——除非有人把它加進 `environment:` 或映像 `ENV`，而這兩處正是
`reliability-design.md` §九 第 1、2 項的檢查對象。剩下看不到的只有「在主機上手動 `docker run -e`」這類繞過 compose 的操作。

### 6.2 `validate_env_contract.py` 會不會擋

| 檢查 | 對本單元的結果 |
|---|---|
| 部署 stack 的變數都被寫入、範本完整、範圍分離、範本無占位值 | **通過**：無新變數 |
| 「backend 讀得到的變數都記載於 `backend/.env.example`」（`validate_env_contract.py:242-262`） | **通過，但對本單元是空轉**：其偵測式 `PY_ENV_READ`（`:88`）只認 `os.environ.get(...)` 與 `os.getenv(...)`，**不認** `os.environ["X"]`——而 `reliability-design.md` §九寫明三個 Redis 變數以 `os.environ[...]` 取值。三者剛好已記載，所以結論不變；但這道檢查看不見本單元的讀取。**真正的閘門是 `NFR13.44` ① 的 AST 測試**，code-generation 須讓它涵蓋下標形式（`ast.Subscript` 於 `os.environ`），不得只 grep `os.environ`／`os.getenv` 的呼叫引數 |

### 6.3 `LOCAL-DEV.md` 必改段落（`NFR13.43`；`project.md ## Mandated`；同一 PR）

| 行 | 現文（摘） | 改為 |
|---|---|---|
| `:23` | 「大腦編排的 session 還原（跨頁脈絡）｜Redis｜session 相關功能不可用」 | 「後端啟動本身（U13 起）＋大腦入口頁」需要 Redis 的三個變數：缺值或 `REDIS_USER=default` → **後端拒絕啟動**；Redis 暫時不可達不阻止啟動，入口頁握手以 1011 關閉 |
| `:24-25` 之後 | （U10、U11 兩列啟動拒絕條件） | 補一列「後端啟動本身（U13 起）」：`REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD` 缺任一或 `REDIS_USER=default` 即拒絕啟動 |
| `:17-20` 的功能表 | A1／A3 需要 LLM 金鑰 | 補一列「大腦入口頁（U13 起）｜PostgreSQL＋Redis＋`OPENROUTER_API_KEY`｜**每一輪**回「內部錯誤」（不降級）」——本機與 staging 同形（`OPEN-GW13-7`） |
| `:26` 嵌入列 | `fulltext`／`stub` 不需外部服務 | 補一句：選 `fulltext` 時入口頁每個有交辦的輪次都會記一筆 `episodic_write_failed` WARNING（`observability-design.md` §三揭露，`OPEN-GW13-18`），屬預期 |
| `:79` | 「沒有它，大腦編排的 session 相關功能不可用」 | 「沒有它，後端（U13 起）拒絕啟動；它暫時斷線時入口頁握手失敗」 |
| `:593` 疑難排解列 | 「session／跨頁脈絡相關功能連不上」 | 拆成兩列：「後端啟動就掛、訊息提到 `REDIS_*`」與「入口頁連線立刻被關閉（1011）」，原因與檢查方式各自對應 |

驗收（沿用 `NFR13.43`）：`LOCAL-DEV.md` 內「session 相關功能不可用」出現 0 次、含 `REDIS_USER=default` 字串；PR diff 同時含 `backend/main.py` 與 `LOCAL-DEV.md`。

### 6.4 `DEPLOY.md`（建議，非 blocking——本單元無 DDL，不觸發 schema 同步規則）

- `DEPLOY.md:24` 的 `OPENROUTER_API_KEY` 列「缺了會怎樣」只寫 A1／A3／優化——補「大腦入口頁每一輪失敗」（措辭依 `IG1` 的裁決）。
- 新增一節「入口頁部署後實測」，內容即第 4.4 節（指令、預期、三層判讀），使 `OPEN-GW13-6` 的實測不只存在於本 record。

## 七、單一行程守門（`NFR13.33`＋帶入項 16）

設計已由 `reliability-design.md` §九定案（三類檔案的文字／YAML 檢查），本站只補基礎設施面的兩點：
1. 6.1 節的「無 `env_file:`」事實是第 2 項檢查得以完整的前提——**應一併斷言** `backend` 服務沒有 `env_file` 鍵；否則日後有人加上
   `env_file: .env`，`deploy/.env` 裡的 `WEB_CONCURRENCY` 就會無聲生效而三項檢查全部仍綠。
2. 部署後一次性複核（build-and-test）：`docker top cloud360-backend-1` 只見一個 uvicorn 行程（無 multiprocessing 子行程）。

## 八、空 `OPENROUTER_API_KEY`（`OPEN-GW13-7`，承接 `intent-router` 的 `I-1`）

**事實**：`render-env.sh:21` 把它標為 optional（「A1 design agent; empty disables generation」）、`:109` 為 `${OPENROUTER_API_KEY:-}`；
`deploy.yml:71-91` 的必要 secret 檢查只含 `POSTGRES_PASSWORD`／`JWT_SECRET`／`REDIS_PASSWORD`；CI 測試 stack 明確設為空字串
（`docker-compose.test.yml:83`）。`U13` 上線後，空金鑰的後果由「A1 不能產圖」擴大為「入口頁每一輪 `error(INTERNAL_ERROR)`」
（`BR67.1`；`U11` 無快路徑）。行為面（大聲失敗、不降級）已在 functional-design 定案，**本站只決定部署面要不要擋**——
這會改變 A1／A3／C1 在無金鑰時的既有部署行為，屬跨單元決定，**已出題 `IG1` 交使用者裁決**，本站不代答。
在裁決前，本規格不改 `render-env.sh`、`deploy.yml`、`deploy/.env.example`。

**CI 面的確定後果（不論 `IG1` 怎麼答）**：`ui-regression` 的測試 stack 金鑰為空，所以 `U14` 的 e2e 走到 `classify` 的每一輪
都會收到 `error(INTERNAL_ERROR)`。`U14` 的 e2e 能斷言的是握手、`ready`、狀態訊息、`prompt_guard` 攔截（在 `classify` 之前，
`NFR13.6`）與錯誤呈現，**不能**斷言交辦成功——這個限制要寫進 `U14` 的測試計畫，而不是在 e2e 失敗後才發現。

## 九、訊框大小的部署層一半（`OPEN-GW13-13`）

`scalability-requirements.md:42-45` 把「uvicorn 交給應用前仍緩衝到 16 MiB」的部署層一半指派到本站。逐層查證：

| 層 | 能否限制單一 WebSocket 訊框 | 依據 |
|---|---|---|
| uvicorn `--ws-max-size` | 能，但**全域**（同行程所有 WS） | 協作 WS 收整張架構圖 XML，上限 `MAX_DIAGRAM_XML_CHARS = 2 * 1024 * 1024` **字元**（`collab_router.py:33`）；位元組數依編碼與 JSON 跳脫可達數倍，本站無量測可安全選值 |
| nginx | 不能。升級後 nginx 只轉送位元組流，不解析訊框；`client_max_body_size` 只作用於 HTTP 請求本文 | nginx WebSocket 代理文件（同 4.2） |
| Cloudflare／`cloudflared` | 未查證（本站未找到官方對代理 WebSocket 訊框大小的上限數值） | — |

**結論**：部署層**沒有**只作用於 `/api/brain/ws` 的控制點。殘留維持 `nfr-requirements` 已揭露的形狀（應用層 64 KiB 拒絕、
傳輸層 16 MiB 緩衝），連線上限 200（`NFR13.17`）使最壞緩衝量有界但很大（200 × 16 MiB）。若日後要收緊，前提是先量測協作 WS
的實際最大訊框位元組數，再決定全域 `--ws-max-size`——屬新的跨單元決定，本站不做。

## 十、ADR-0006 四面向（基礎設施層，逐格對照上游 `security-requirements.md` 與 `security-design.md`）

| 面向 | 上游判定 | 本站判定 | 內容 |
|---|---|---|---|
| IAM | 適用 | **適用（無新基礎設施身分）** | 不新增雲端／容器身分、不改 Redis ACL。實測（4.4）需要一個具 `K1.view` 的測試帳號——用既有角色，不新增權限 |
| Encryption | — | **適用（無新增，記載路徑）** | 外部 TLS 終結於 Cloudflare edge；edge→`cloudflared` 為 tunnel 加密；`cloudflared`→nginx→backend 在 `edge` bridge 上為明文 HTTP，與既有 REST 的 `Authorization` 標頭同一信任邊界（主機內）。token 只在**請求**標頭（`NFR13.7`），回應不含——4.4 的 curl 檢查是其部署面複驗 |
| Network exposure | 適用（本 intent 唯一新增的對外面） | **適用** | 不新增埠、服務、ingress；新端點經既有 `location /api/` 公開。連線數／頻率／訊框皆為應用層限制（第九節殘留）。**DEMO 先於 `U13` 上線會公開一個把 token 寫進回應標頭的端點**（5.3），是本站唯一新識別的暴露路徑 |
| Audit logging | 適用 | **適用** | 只用既有容器 log（json-file，50m×5，`docker-compose.deploy.yml:62-68`）。nginx 預設 access log 格式不含 `Sec-WebSocket-Protocol`，token 不會因代理而落地（**推論**：本檔無自訂 `log_format`）；Cloudflare 端的日誌行為未查證。實測腳本不印內容、不印 token |

PBT hard constraint：N/A（基礎設施層；純函式 PBT 由 `NFR13.42` 在 CI 的 `unittest` 執行，見 `cicd-pipeline.md`）。

## 十一、指派給本站的事項處置表

| 來源 | 事項 | 處置 | 落點 |
|---|---|---|---|
| `OPEN-GW13-6`（`OQ-8`） | nginx／cloudflared 是否透傳 `Sec-WebSocket-Protocol` | nginx 靜態判定透傳；Cloudflare 兩跳**未查證**；定出三層實測與回退。**未結案**——實測後才結 | 本檔第四節；實測執行落 `build-and-test` |
| `OPEN-GW13-7`（`I-1`，`H-21`） | 空 `OPENROUTER_API_KEY` 使入口頁每輪失敗 | 部署面處置**出題 `IG1`**，待使用者裁決；CI 面後果已寫明 | 第八節；問題檔 |
| `OPEN-GW13-10` | DEMO 刪除與前端同批 | 同批矩陣＋「DEMO 不得先於 `U13` 進 `ut`」＋路由唯一性測試建議 | 第五節 |
| `OPEN-GW13-13`（部署層一半） | uvicorn 16 MiB 緩衝 | 部署層無控制點；殘留維持並寫明前提 | 第九節 |
| 帶入項 16（`NFR13.33`） | 單一行程守門另查 `WEB_CONCURRENCY`／`UVICORN_WORKERS` | 補「無 `env_file`」斷言與部署後 `docker top` 複核 | 第六節 6.1、第七節 |
| 帶入項 6（`NFR13.43`） | `REDIS_*` 成為啟動必要；`LOCAL-DEV.md` 同步 | 逐行列出 6 處改動 | 第六節 6.3 |
| `NFR13.44` | 不新增環境變數；`validate_env_contract.py` 綠 | 確認通過，並揭露其偵測式看不到 `os.environ[...]` | 第六節 6.2 |
| 帶入項 26（R-09） | Redis 故障與認證共用預設執行緒池 | 記入共享基礎設施表；量測落 build-and-test | 第三節 |

## 十二、Assumptions & Open Questions

- **假設**：uvicorn 預設伺服器端 ping 為 20 秒、且其 ping 足以維持 nginx 與 Cloudflare 的閒置計時（第 4.3 節）——本站未實讀未釘版的 uvicorn 原始碼；第 4.4 節 L3 實測後保持連線 > 120 秒可順帶驗證。
- **假設**：JWT 長度遠低於 nginx 8 KiB 標頭緩衝。
- **未查證**：Cloudflare 對 `Sec-WebSocket-Protocol` 的透傳、閒置上限、訊框上限。
- **開放**：`IG1`（問題檔）。
