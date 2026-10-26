# 基礎設施規格 — `U21 mcp-bridge`

> 承接 `../nfr-design/` 六份產出、`../functional-design/functional-spec.md` §八（H-1–H-12）與 `brain-infra` 已定案的 `[I6]`=A／`[I7]`=A。
> 部署目標是自有 staging 主機 `192.168.10.10` 上的 docker compose（`deploy/docker-compose.deploy.yml`，對外經 Cloudflare Tunnel，ADR-0007）；
> **不是 AWS**，雲端 production 不在範圍內（ADR-0001／ADR-0002）。本單元新增**一個** compose 服務（第七個），不新增 volume、埠、
> 環境變數或 secret。本站未執行任何測試、Python 或 docker 指令；所有 `<檔名>:<行號>` 皆以 `sed -n`／`grep -n` 於 HEAD `45bf7b3` 的工作樹逐行印出核對。
> 本檔與 `monitoring-design.md`、`cicd-pipeline.md` 的規則識別字只用 `BR71`–`BR78`；本站自訂的編號皆非規則：`IC-<n>` 是本檔第六節的
> `code-generation` 必做清單，`CC-<n>` 是 `cicd-pipeline.md` 第三節的 CI 實作約束。

## 一、Deployment

| Facet | Choice | Rationale |
|---|---|---|
| 運算模型 | **獨立容器**：compose 的第七個服務 `mcp-bridge`，與 `backend` 同一映像、不同 `command` | `[I6]`=A；`components.md:642-646` 的 `McpBridge` 逐字「跑獨立進程」；H-1 |
| 進程與副本數 | 單一容器、單一 uvicorn 進程、**單一副本** | bridge 無狀態、可多實例（`NFR21.23`），但本版無實際 client（`OPEN-MB21-1`），第二副本沒有負載可分；compose 單主機也沒有負載平衡器可分流 |
| 監聽 | 容器內 `0.0.0.0:8080`（compose `command` 明列 `--host 0.0.0.0`）；程式預設 `127.0.0.1`（`R-18`） | `NFR21.16` ①②；容器內若監聽迴環，同網段的 `backend` 連不到 |
| 網路拓樸 | 只在 `internal`（`deploy/docker-compose.deploy.yml:416`），**無 `ports:`**；呼叫 `http://backend:8000` 經 `internal` | `backend` 是唯一同時在 `edge`／`internal` 的服務（`:167-169`），故 bridge 經 `internal` 可達它；`edge` 成員（`frontend`、`cloudflared`）**到不了** bridge |
| 對外路徑 | **無**。不經 nginx、不經 tunnel | `components.md:646`「不得對外暴露，僅供同主機的大腦進程連接」 |
| 儲存 | **無 volume**；設定檔（`generated_tools.json`、`agents.json`、`allowlist.json`）隨映像打包於 `/app/mcp_bridge/` | `backend/Dockerfile:19` 的 `COPY . .` 把整個 `backend/` 帶入；`.dockerignore` 不排除 `mcp_bridge/`（實讀：只排除 `.env*`、`__pycache__/`、`*.py[cod]`、`.pytest_cache/`、`.venv/`、`venv/`） |
| 環境 | 本機 dev：`python -m mcp_bridge --backend-url http://127.0.0.1:8000`（不讀任何 `.env`）；CI：不起容器，以 `unittest` 內的驗證拓樸執行（`../nfr-design/reliability-design.md` §6.2）；staging：compose 服務；production：範圍外 | 三環境皆**零新增變數**（`BR71.1`、`NFR21.17`、H-6） |
| IaC | compose 檔 ＋ `deploy.yml`（既有）；不新增任何 IaC 工具 | ADR-0007 的既有形狀 |
| 資源額度 | 記憶體上限 **`512m`**（暫定、未量測，推導見第二節之二）；CPU 不設限（與其餘六個服務一致） | `[I2]`=C ＋ `[I2b]` 反轉後版本；nfr-design 審查 `R-08` |
| 映像 | `build: {context: ../backend, network: host}`，與 `backend` 完全相同（`:80-82`）；第一順位**不改** `backend/Dockerfile`；第二退路只在 Dockerfile 加獨立 virtualenv（第五節） | H-1、H-5、`NFR21.41` |
| 成本 | 零金額成本（自有主機、無雲端資源）；主機資源：記憶體上限 512m（上限非保留量）、日誌至多 250m（50m × 5）、映像層與 `backend` 內容相同而以內容雜湊去重 | FinOps：本單元的資源成本只有容量上限，無按量計費項 |

## 二、Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| `mcp-bridge`（新增） | MCP 工具伺服器（streamable HTTP、無狀態、`json_response=True`） | 逐鍵定義見本節之一 | 零認證的面只有 `/healthz` 與 `initialize`／`tools/list`，只回公開資訊（`NFR21.19`） |
| `backend`（既有） | bridge 的唯一下游；授權判定者 | 不改。bridge 以使用者 token 呼叫三條需求欄位路由（同步 `def`，佔 anyio 執行緒池，`../nfr-design/logical-components.md` §三） | `backend` 的 `memory: 2g`（`:179`）不需因 bridge 調整：bridge 的請求與直接呼叫 API 的請求在 backend 端同形 |
| `db`、`redis`、`ollama`（既有） | bridge **不直接**使用 | 不改 | 三者因 bridge 加入 `internal` 而多一個可達來源（第四節） |
| `frontend`（nginx）、`cloudflared`（既有） | 與 bridge **無路徑** | 不改；**不得**為 bridge 新增 nginx `location` 或 tunnel ingress | 兩者只在 `edge`（`:365`、`:390`），解析不到 `mcp-bridge`；要讓它們連到 bridge 必須把它們加進 `internal`，那會直接推翻 D-3 分段（`:386-389` 的註解） |

### 二之一、compose 服務定義（逐鍵；`code-generation` 依此寫入）

| 鍵 | 值 | 依據 |
|---|---|---|
| `build` | `{context: ../backend, network: host}` | H-1；與 `backend`（`:80-82`）同形，`network: host` 使建置期 `pip install` 可連外 |
| `restart` | `unless-stopped` | `NFR21.32` |
| `command` | `["python","-m","mcp_bridge","--backend-url","http://backend:8000","--host","0.0.0.0","--port","8080"]`；第二退路改首項為 `/opt/mcp-venv/bin/python` | H-1、`R-18`、`NFR21.16` ②、`NFR21.41`；`--max-concurrency` 不列（預設 16，`NFR21.21`）。**不含 `${…}`**（IC-1） |
| `environment`／`env_file` | **不寫** | `BR71.1`；IC-1 |
| `healthcheck` | `test` 以 `python -c` ＋ `urllib` 探 `http://127.0.0.1:8080/healthz`、200 為通過；`interval: 10s`、`timeout: 5s`、`retries: 3`、`start_period: 10s` | H-2、H-3：**必須覆寫**映像內建的 `HEALTHCHECK`（`backend/Dockerfile:27-28` 探 8000），否則容器恆為 `unhealthy`。用映像的系統直譯器即可（`urllib` 為標準庫），兩條依賴路線相同 |
| `depends_on` | `[backend]`，**不帶 `condition`** | `BR71.4`、`NFR21.25`：bridge 啟動不連 backend，backend 尚未就緒時只讓該次呼叫回 `backend_unavailable` |
| `stop_grace_period` | `15s` | `../nfr-design/reliability-design.md` §八；關係式見第七節 |
| `networks` | `[internal]` | `[I6]`=A、`NFR21.16` ② |
| `ports` | **不存在** | 同上 |
| `logging` | `*json_file_bounded` | `NFR21.32`；使日誌總上界由 1500m 變為 1750m（第三節） |
| `deploy.resources.limits.memory` | `512m` | 第二節之二 |

示意（≤ 15 行，非實作；healthcheck 的 `test` 略寫）：

```yaml
mcp-bridge:
  build: {context: ../backend, network: host}
  restart: unless-stopped
  command: ["python", "-m", "mcp_bridge", "--backend-url", "http://backend:8000", "--host", "0.0.0.0", "--port", "8080"]
  healthcheck:
    test: ["CMD", "python", "-c", "<urllib 探 http://127.0.0.1:8080/healthz，200 即 exit 0>"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 10s
  depends_on: [backend]
  stop_grace_period: 15s
  networks: [internal]
  logging: *json_file_bounded
  deploy: {resources: {limits: {memory: 512m}}}
```

### 二之二、記憶體上限 `512m` 的推導（暫定、未量測；納入 nfr-design 審查 `R-08`）

| 項 | 值 | 取得方式 |
|---|---|---|
| 緩衝位元組上界 | 16 ×（65536 ＋ 1048576）＝ **17825792 位元組（17 MiB）** | shell 整數運算；`../nfr-design/scalability-design.md` §六 |
| 放大係數 | 取 `R-08` 給的區間上緣 **10 倍**（JSON 解碼成 Python 物件、structured content 與文字各一份、JSON-RPC 回應再序列化一份） | `R-08` 的 Required action：「至少 3 到 10 倍」；**未量測** |
| 請求相關駐留上界（估計） | 17825792 × 10 ＝ **178257920 位元組（170 MiB）** | shell 整數運算 |
| 進程常駐量（估計） | **≤ 200 MiB**：bridge 進程只 import `mcp_bridge`、`mcp`、`httpx`、`uvicorn`、`starlette`、`pydantic`，**不** import `main` 與 `langgraph`／`sqlalchemy` 等 backend 的重型依賴 | **估計，未量測**；不得引用 `backend` 的 `2g`——那是含 LLM 路徑的行程 |
| 合計（估計） | 170 ＋ 200 ＝ 370 MiB | — |
| 定值 | **`512m`**，對估計合計約 1.38 倍餘裕 | `bc` 計算 512／370；取 2 的冪次方便日後以 `docker stats` 對照 |

**不得直接取 17 MiB 加常駐量**（`R-08` 原文）。量測落點兩處：`build-and-test` 在 16 個 1 MiB 回應下以 `docker stats` 取峰值（`R-08`）；
部署後依 `DEPLOY.md` §5.6 的複量程序（首次部署成功日 ＋ 7 日內，負責人 Danniel）把第七個容器一併量測。**被 OOM kill 的後果**：
`restart: unless-stopped` 使容器重啟（數秒，無狀態、無資料遺失）；本版無 client，使用者影響為 0；但若峰值確實逼近 512m，重啟迴圈會
在 `docker inspect` 的 `RestartCount` 上看得到（`monitoring-design.md` 第一節）。

## 三、Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| `backend` 映像與 `backend/Dockerfile` | `brain-infra`（部署形狀）／既有 | `backend`、`mcp-bridge` | 同一份 Dockerfile 建出兩個服務；`mcp-bridge` 以 `command` 與 `healthcheck` 覆寫 `CMD`（`:30`）與 `HEALTHCHECK`（`:27-28`）。**改 Dockerfile 會同時影響兩者**；第二退路的 `/opt/mcp-venv` 也會出現在 `backend` 映像內（`backend` 進程不使用它） |
| `backend:8000`（經 `internal`） | 既有 | `frontend`（經 `edge`）、`mcp-bridge`（經 `internal`） | bridge 只以 HTTP ＋ 使用者 token 進入；授權全由 facade 判定（`BR75.1`、`NFR21.12`）；bridge 不走同進程直呼 |
| backend 同步端點執行緒池（anyio 預設 40，套件預設值、**未實測**） | Python 執行環境 | 全部同步路由；bridge 至多佔 16 | 由 bridge 的並行閘 16 與 httpx 連線池 16 共同給出上界（`../nfr-design/logical-components.md` §三；`R-02` 的 shield 修正後須維持此上界，見 `cicd-pipeline.md` 第三節 CC-6） |
| compose `internal` 網段 | `brain-infra` | `backend`、`db`、`redis`、`ollama`、`mcp-bridge` | 成員 4 → 5；同網段 ICC 全通（`:409-411`），見第四節 |
| 容器日誌總量上界 2GB（`json_file_bounded`） | `brain-infra` | 七個服務 | 50m × 5 × 7 ＝ **1750m**（shell 實算），仍在 2GB 內；第八個服務將恰達 2000m（`brain-infra` `infrastructure-specification.md` 7.5 已預告） |
| `deploy` job 的 30 分鐘預算（`deploy.yml:28`） | 既有 | 全部部署步驟 | 本單元新增一個有界步驟 12 × 5 ＝ 60 秒，使 `DEPLOY.md` §5.9.1 的有界合計由 1260 秒變 1320 秒、兩個無界項的剩餘預算由 540 秒降為 **480 秒**（shell 實算；`cicd-pipeline.md` 第二節） |
| CI `backend` job | 既有 | 全部 backend 測試、三道漂移閘門 | 本單元新增一道閘門與 `timeout-minutes: 15`；第二退路另加一步建 venv |

## 四、網路暴露面與 blast radius 重算（`OPEN-MB21-12`、H-11；承接 `brain-infra` 7.4 的前向指標）

**對外（`edge`、host 埠）零新增**；`internal` 網段內**新增一個**可達端點。計數規則沿用 D-3 原表：某目標的「可達來源」＝同網段其他成員數。

| 目標 | D-3 分段後（原值） | 加入 `mcp-bridge` 後 | 說明 |
|---|---|---|---|
| `redis` | 3 | **4**（`backend`／`db`／`ollama`／`mcp-bridge`） | 與 `brain-infra` 7.4 一致 |
| `ollama` | 3 | **4**（`backend`／`db`／`redis`／`mcp-bridge`） | 同上 |
| `db` | 3（`backend`／`redis`／`ollama`） | **4** | 本站補算（7.4 只列 redis／ollama） |
| `backend` 經 `internal` | 3（`db`／`redis`／`ollama`） | **4** | 本站補算；`edge` 側不變（`frontend`、`cloudflared`） |
| `mcp-bridge:8080` | — | **4**（`backend`／`db`／`redis`／`ollama`）＋ **host 上任何行程** | `edge` 成員 0；host 可達見下 |

**方向要寫對**：這是 D-3 效益的部分侵蝕，不是失效——`cloudflared`（唯一持續連網際網路的容器）與 `frontend` 仍碰不到任何 `internal` 成員，
包括 bridge。**host 可達面**：`deploy/docker-compose.deploy.yml:412-414` 的註解逐字承認 bridge 網段的 subnet 從 host 可路由，故 `192.168.10.10`
上的任何行程（含自架 runner）能以容器 IP 連 `mcp-bridge:8080`。能拿到的只有 `/healthz` 與 `tools/list` 的公開資訊；任何工具呼叫都須帶
一個有效的使用者 JWT，並經 facade 判權。這與 `redis:6379`／`ollama:11434` 屬同一類 host-local 主體（`security-design.md` D-2 主體類 2），
`DEPLOY.md` §5.11 的「分段隔離什麼、不隔離什麼」須把 `mcp-bridge:8080` 加進清單（IC-9）。

**`brain-infra` 的 `security-design.md` D-3 表**已被該站終局收據凍結，本站不回改；本表即 `OPEN-MB21-12` 的落點，`DEPLOY.md` §5.11 是
維運者實際會讀的那一份，由 `code-generation` 同步（IC-9）。

## 五、映像與依賴路線（`NFR21.37`、`NFR21.38`、`NFR21.41`；H-5）

| 面 | 第一順位（`mcp` 進 `backend/requirements.txt`） | 第二退路（獨立 virtualenv） |
|---|---|---|
| 依賴檔 | `backend/requirements.txt` 新增 `mcp==<精確版本>` 一行 | `backend/requirements.txt` 不變；新檔 `backend/requirements-mcp.txt`，非註解行恰為 `mcp==<精確版本>` |
| Dockerfile | **不改**（`git diff backend/Dockerfile` 為空） | 在 `USER appuser`（`:23`）**之前**加：建立 `/opt/mcp-venv`、以其 `pip` 安裝 `requirements-mcp.txt`；`CMD`（`:30`）與 `HEALTHCHECK`（`:27-28`）不變 |
| compose `command` 首項 | `python` | `/opt/mcp-venv/bin/python`（工作目錄沿用 `WORKDIR /app`，`:14`；`-m mcp_bridge` 以 `/app` 為匯入根） |
| 映像內容 | `mcp` 進入 backend 執行期映像（backend 進程不 import 它，`OPEN-MB21-15` 已揭露） | `mcp` 與其傳遞依賴只在 `/opt/mcp-venv`；兩個服務的映像都含它 |
| CI | `docker-build` job 建 `./backend` context（`ci.yml:626-632`），已涵蓋 | 同左，且涵蓋 venv 建立步驟——Dockerfile 壞掉在 PR 階段紅燈 |

**venv 必須在 `USER appuser` 之前建立**：之後的 `RUN` 以 uid 10001 執行，寫不進 `/opt`；建立後不需 `chown`（只讀即可執行）。路線由
`code-generation` 第一步判定並在計畫核可關卡呈現（`functional-spec.md` §十二 第 6 點）；本站只定兩條路線各自的基礎設施形狀。

## 六、環境設定與文件同步：`code-generation` 必做清單

| # | 檔案 | 必做（第一順位） | 第二退路的差異 | 依據 |
|---|---|---|---|---|
| IC-1 | `deploy/docker-compose.deploy.yml` | 新增第二節之一的服務；**服務區塊內不含 `${`、不含 `environment:`／`env_file:`**；更新三處註解：檔頭 `:4-6`（「Only nginx is reachable…」的服務清單加 `mcp-bridge`）、`:65`（`50m x 5 x 6 services = 1.5GB` → 7、1.75GB）、`:412-414`（host 可達清單加 `mcp-bridge:8080`）；在服務區塊內寫 `stop_grace_period` 的關係式註解（第七節） | `command` 首項改 venv 直譯器 | H-1、`NFR21.32`、`BR71.1` |
| IC-2 | `backend/Dockerfile` | 不改 | 第五節 | `NFR21.41` |
| IC-3 | `backend/requirements.txt`／`requirements-mcp.txt` | `mcp==…` 一行，註解比照檔頭釘選紀律寫明理由 | 新檔 | `NFR21.37`、`NFR21.38` |
| IC-4 | `.github/workflows/ci.yml` | `backend` job 加漂移閘門與 `timeout-minutes: 15` | 另加建 venv 步驟與 `cache-dependency-path` | `cicd-pipeline.md` 第二節 |
| IC-5 | `.github/workflows/deploy.yml` | `deploy` job 新增非阻擋的 bridge 健康紀錄步驟；env 對照表**不改**；`rollback` job 不改 | 無 | H-8、`NFR21.32` 的部署後實測；`cicd-pipeline.md` 第四節 |
| IC-6 | `DEPLOY.md` | ① 新增一小節說明第七個服務（角色、零對外埠、零變數、與 `backend` 同映像）＋三條驗證指令（見下）；② §5.6 暫定值表加一列 `mcp-bridge` `512m` 與其依據、把「六個服務」「六個容器」「六個數字」改為七；③ §5.9.1 預算表加一列（60 秒、有界）並把約束式改為「有界 1320 秒、無界剩餘 480 秒」；④ §5.11 見 IC-9 | ① 加註映像內 `/opt/mcp-venv` 的用途 | H-7、`brain-infra` 第 28 項 |
| IC-7 | `LOCAL-DEV.md` | **建議**（非 blocking）補一節本機啟動 bridge：`python -m mcp_bridge --backend-url http://127.0.0.1:8000`（預設監聽 `127.0.0.1:8080`）；並在「先確認 port 沒被佔用」的迴圈（`LOCAL-DEV.md:112`）註明 8080 | **升為必做**：寫明本機跑 `backend/tests` 前須先建 repo 根目錄的 `.mcp-venv/`（指令與 CI 相同），否則本單元測試以 `AssertionError` 失敗（不是 skip） | H-10；`project.md ## Mandated` 的同步規則之由來（問題檔 #7） |
| IC-8 | `deploy/render-env.sh`、`deploy/.env.example`、`backend/.env.example`、`deploy/docker-compose.test.yml`、`frontend/nginx.conf`、`deploy/cloudflared/config.yml` | **皆不改**。若實作發現需要任何環境變數，`project.md` 的三處同步規則與 `LOCAL-DEV.md` 規則**完整適用**，並須回本站重審（零變數是 `BR71.1` 的已核可字面） | 同左 | H-6、H-9 |
| IC-9 | `DEPLOY.md` §5.11 | 「分段隔離什麼、不隔離什麼」段的 host 可達清單加 `mcp-bridge:8080`；「healthcheck 的已知盲點」表加一列：`/healthz` **不證明**工具宣告正確、allowlist 生效或能呼叫 `backend`（`brain-infra` `monitoring-design.md:177` 的「不證明」欄） | 同左 | `OPEN-MB21-12` |
| IC-10 | `schema_rbac.sql`／`DEPLOY.md` 的 schema 同步 | **不觸發**：無 DDL、無 seed 變更 | 同左 | H-12 |
| IC-11 | 提交前 | `python3 scripts/validate_repo_contract.py`、`python3 scripts/validate_env_contract.py` | 同左 | `project.md ## Mandated` |

**IC-6 ① 的三條驗證指令**（維運者在 `192.168.10.10` 手動執行，不需 token）：

| 驗證 | 指令形狀 | 通過條件 |
|---|---|---|
| 無對外埠 | `docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env port mcp-bridge 8080` | 無輸出或錯誤（未映射） |
| 只在 `internal` | `docker inspect --format '{{json .NetworkSettings.Networks}}' <mcp-bridge 容器>` | 鍵集合恰為 `cloud360_internal` |
| 健康 | `docker inspect --format '{{.State.Health.Status}}' <mcp-bridge 容器>` | `healthy` |

## 七、部署、優雅關閉與回滾

- **部署方式**：deploy-on-merge 至 `ut`，`deploy.yml:126-129` 的 `up -d --build --remove-orphans` 一併建立第七個服務；**重建（recreate）單一副本**，
  不做 blue/green 或 canary——無實際 client，也沒有流量可分。
- **優雅關閉關係式**（寫進 compose 註解，比照 `redis` 的 `REQUIRED RELATIONSHIP` 形狀）：`stop_grace_period` ≥ 單一 `/mcp` 請求的最大牆鐘時間 ＋ 1 秒
  ＋ 關閉本身。現值：工具呼叫上限 10 秒（`NFR21.1`）→ 15 秒成立。**nfr-design 審查 `R-01` (b)** 若在 `code-generation` 為 `/mcp` 加入
  「本體讀取期限 ＋ 整體處理上限」，其總和必須 ≤ 13 秒，否則同一個 PR 內必須調高 `stop_grace_period`（IC-1）。uvicorn 的
  `timeout_graceful_shutdown` 預設不限（`../nfr-design/reliability-design.md` §八），故截斷只由 Docker 的 SIGKILL 決定。
- **bridge 單獨失效時**：部署照常成功（健康紀錄步驟只發 warning，`cicd-pipeline.md` 第四節）；止損為 `docker compose … stop mcp-bridge`——
  無狀態、無資料、無 client，停用不影響任何其他服務；修正以 fix-forward PR 或 revert PR 走正常管線。
- **整個 stack 回滾**（既有 `rollback` job）：還原 last-good 後同樣 `up -d --build --remove-orphans`；若 last-good 早於本單元，`--remove-orphans`
  會**移除** `mcp-bridge` 容器——這是正確結果（last-good 不含該服務）。沒有 volume，回滾不留殘骸。
- **高風險變更的閘門**：本單元對 `internal` 網段新增一個成員，屬網路暴露面的變更。Plan＝本節與第四節；Impact＝第四節的 blast radius 表；
  Rollback＝刪除服務區塊後 `up -d --remove-orphans`。human approval gate 為 `code-generation` 的計畫核可關卡加上合併 PR 的人工審查；
  本站與 `code-generation` 都不直接對 staging 執行任何指令。

## 八、ADR-0006 四面向（基礎設施層；逐格對照上游 `requirements.md:617-620` 與 `../nfr-design/security-design.md` §九）

| 面向 | 上游判定 | 本站判定 | 基礎設施層的處置 |
|---|---|---|---|
| **IAM** | 適用（三處） | **適用** | 不新增任何身分、服務帳號、GitHub secret 或 variable；容器以映像既有的非 root 使用者 uid 10001 執行（`backend/Dockerfile:21-23`）；CI／deploy workflow 的 `permissions` 不變；部署健康步驟只讀 `docker inspect`，不持有 token |
| **Encryption** | 適用（新增一處） | **適用——內容為經使用者接受的例外** | 上游條件為「HTTP／SSE 則須為**本機迴環或加密**」（`requirements.md:618`）；本單元是 `internal` 網段（非迴環）上的**明文**，兩者皆非，屬使用者 2026-10-14T23:02:07Z 接受的例外（`../carried-review-items.md:25`），殘留：同主機任一容器或 host 行程被攻破即可竊聽 token。`brain-infra` 7.3 寫「以不離開本主機滿足」——本站依 nfr-design 審查 `R-05` 改述為「例外」而非「滿足」，上游檔不回改。靜態：無 volume，不落地任何 token、參數或結果 |
| **Network exposure** | 適用（新增一處） | **適用** | 對外零新增（無 `ports:`、不在 `edge`、無 nginx／tunnel 路徑）；`internal` 新增一個可達端點、blast radius 重算見第四節；host 行程可達；`--host` 程式預設迴環、僅 compose 明列 `0.0.0.0` |
| **Audit logging** | 適用（兩處） | **適用** | 容器日誌沿用 `json_file_bounded`（有界、不外送）；每次工具呼叫恰一行、HTTP 層拒絕一行（`monitoring-design.md` 第四節）；部署健康步驟的結果留在 Actions log（不含請求內容）。讀取面依 `[MBN1]`=A 不新增帶身分紀錄；關聯鍵本版不設（`OPEN-MB21-9` 已結案） |

四格判定欄與上游相同，**無一格相反**；Encryption 一格的**內容**是經使用者接受的例外，不是符合。

**PBT hard constraint**：本站不新增純函式。產生器的 PBT（`NFR21.39`）是 ADR-0006 的落點之一，本站的責任是保證它在 CI 中**兩條依賴路線都實際執行**：
純函式模組不 import `mcp`（`NFR21.40`），故 PBT 在主直譯器執行、不受路線影響；`backend` job 的 `unittest discover` 撿得到；本單元測試的
skip 次數為 0（`cicd-pipeline.md` 第三節 CC-3）。不以 N/A 處理。

## 九、指派給本站的事項處置表

| 來源 | 事項 | 處置 | 落點 |
|---|---|---|---|
| `functional-spec.md` H-1 | compose 服務 | 收斂：逐鍵定義，補上 `--host 0.0.0.0`（`R-18`）與 `stop_grace_period` | 第二節之一 |
| H-2、H-3 | healthcheck、覆寫映像 HEALTHCHECK | 收斂；路徑 `/healthz`——**回寫** `brain-infra` `monitoring-design.md:177` 的路徑欄（該檔不回改，以本列為準） | 第二節之一；`monitoring-design.md` 第一節、第五節 |
| H-4 | 漂移閘門 | 收斂：落 `backend` job——**回寫** `brain-infra` `cicd-pipeline.md:337`（第 22 項）的「擇一」為 `backend`（該檔不回改，以本列為準） | `cicd-pipeline.md` 第二節 |
| H-5 | 依賴路線 | 兩條路線的基礎設施形狀皆已定；擇路由 `code-generation` 第一步 | 第五節 |
| H-6 | env 合約 | 不觸發；IC-1、IC-8 | 第六節 |
| H-7 | `DEPLOY.md` | IC-6、IC-9 | 第六節 |
| H-8 | `deploy.yml` | 無硬編服務數的檢查（實查 `deploy.yml` 全檔，無 `docker compose ps` 的計數斷言）；新增一個非阻擋步驟 | `cicd-pipeline.md` 第四節 |
| H-9 | CI test stack | 不加入——**回寫** `brain-infra` `cicd-pipeline.md:351`（第 26 項）為「`U21` 確認不需要」 | `cicd-pipeline.md` 第一節 |
| H-10 | `LOCAL-DEV.md` | IC-7（第二退路下升為必做） | 第六節 |
| H-11、`OPEN-MB21-12` | blast radius | 收斂並補算 `db`、`backend`、bridge 本身三列 | 第四節 |
| H-12 | schema 同步 | 不觸發 | IC-10 |
| nfr-design `reliability-design.md` §八 | `stop_grace_period: 15s` | 收斂並加關係式 | 第七節 |
| nfr-design `scalability-design.md` §六 ＋ 審查 `R-08` | 記憶體上限 | 收斂：`512m`，放大係數取上緣 | 第二節之二 |
| nfr-design `reliability-design.md` §6.3 | 第二退路的 CI 與映像 | 收斂 | 第五節；`cicd-pipeline.md` 第二節 |
| nfr-design 審查 `R-09` 第 3 點 | `backend` job 無上限 | 收斂：`timeout-minutes: 15`（單案 30 秒上限屬測試碼，留 `code-generation`） | `cicd-pipeline.md` 第二節 |
| nfr-design 審查 `R-01`、`R-02` | `/mcp` 牆鐘上限、shield 與閘門 | 應用層修正留 `code-generation`；本站只定它們對基礎設施的兩個約束（`stop_grace_period` 關係式、並行上界 16 不得被打破） | 第七節；`cicd-pipeline.md` 第三節 CC-6 |

## 十、核可關卡須揭露的事項

1. **部署後 bridge 健康檢查是非阻擋的**：bridge 起不來時部署仍為綠燈，只有 Actions 的 warning；後果是「bridge 壞了而沒人收到通知」在本版是可能的。
   本版無 client，選擇不讓它連帶回滾整個 staging；大腦 client 落地時（`OPEN-MB21-1` 的後續 intent）應改為阻擋。
2. **記憶體上限 `512m` 是估計**：常駐量與放大係數皆未量測；量測落 `build-and-test` 與 `DEPLOY.md` §5.6 的複量程序。
3. **`deploy` job 的無界剩餘預算由 540 秒降為 480 秒**（`DEPLOY.md` §5.9.1 的兩個無界項仍未實測）。
4. **host 上的任何行程可連 `mcp-bridge:8080`**（與 `redis`／`ollama` 同一類）；工具呼叫仍須有效使用者 JWT。
5. **Encryption 為經接受的例外**（第八節），不是符合上游條件。
6. **第二退路使 `/opt/mcp-venv` 也出現在 `backend` 映像內**，且本機跑測試多一個前置條件（IC-7）。
7. 第一順位下 `mcp` 進入 backend 執行期映像（`OPEN-MB21-15`，functional-design 已揭露，本站照錄）。

## 十一、Assumptions & Open Questions

- bridge 進程常駐量 ≤ 200 MiB、放大係數 ≤ 10 倍皆為估計 [assumption]
- `docker compose` 的版本支援 `stop_grace_period`、`deploy.resources.limits.memory` 與 YAML anchor（既有六個服務已使用後兩者；`stop_grace_period` 是 compose 規格的既有鍵，本站未在主機查證引擎版本） [assumption]
- `deploy` job 的 `up -d --build` 因第二個服務共用 context 而增加的耗時，預期多為快取命中，**未實測**；併入 `DEPLOY.md` §5.9.1 的既有必填欄位 [assumption]
- 路線（第一順位或第二退路）未定，由 `code-generation` 第一步判定；本檔兩條都給了完整形狀 [assumption]

## 十二、送審前自檢（七項；全部產出寫完後實算，數字皆由 grep／jq／shell 取得，未執行任何測試、Python 或 docker）

| # | 項目 | 結果 |
|---|---|---|
| 1 | **可達性** | 每個「偵測 X」逐一可構造：部署後非 `healthy`——手改產物使 `BR71.5` 退出碼 1 → `unless-stopped` 重啟迴圈，或容器根本不存在（`ps -q` 為空 → `inspect` 失敗 → 依 CC-7 判為未健康並發 warning）；`RestartCount` > 0——同上或 OOM kill；漂移閘門紅燈——改 `openapi.json` 或 `allowlist.json` 而不重產；skip 為 0——缺 `mcp` 或 venv 時以 `AssertionError` 呈現；CC-5 的 YAML 斷言——在服務區塊加 `ports:`／`environment:` 即可構造；`startup tools≠3`——產物數量改變而仍通過啟動驗證。**唯一依賴未實測外部行為者**：Docker 對 `stop_grace_period` 的 SIGKILL 時點（compose 規格行為，主機引擎版本未查證，列 Assumptions） |
| 2 | **契約端點三問**（全部產出） | 新增的設定與步驟逐一指名：`stop_grace_period` 寫＝IC-1、讀＝Docker 停止容器時、改＝關係式（第七節）觸發時同 PR 調整；記憶體上限 寫＝IC-1、讀＝Docker、改＝`DEPLOY.md` §5.6 的複量 PR；healthcheck 寫＝IC-1、讀＝Docker 與部署步驟與 `monitoring-design.md` 第一節；部署健康步驟 擁有＝`deploy.yml`、呼叫＝`deploy` job、輸出讀者＝Actions log 的閱讀者；S-1 擁有＝`ci.yml`、讀＝PR 檢查；`.mcp-venv/` 寫＝S-3（CI）與開發者（IC-7）、讀＝`mcp_topology` 的第二退路、清＝runner 結束即消失／本機由 `.gitignore:38` 排除；`/opt/mcp-venv` 寫＝Dockerfile、讀＝compose `command`、清＝映像重建。編號一致性（`grep -ohE`，每個前綴單一樣式）：`IC-1`–`IC-11` 定義 11 個、跨檔引用的 IC 編號全部有定義；`CC-1`–`CC-7` 定義 7 個、引用全部有定義；`S-1`–`S-4` 定義 4 個、引用全部有定義。孤兒：無 |
| 3 | **引用逐字核對**（事實與定位分開驗） | 以 `sed -n` 逐行印出核對：`deploy/docker-compose.deploy.yml:4-6`、`:28-30`、`:62-68`（`:65` 為「50m x 5 x 6 services」）、`:80-82`、`:167-169`、`:179`、`:365`、`:386-390`、`:409-414`、`:416`；`backend/Dockerfile:14`、`:19`、`:21-23`、`:27-28`、`:30`；`ci.yml:141`、`:176-178`、`:242`、`:259`、`:264-272`、`:281-289`、`:294-300`、`:303-306`（`:305` 為 `JWT_SECRET`）、`:308`、`:531`、`:557`、`:614-632`；`deploy.yml:28`、`:100`、`:126-129`、`:313`、`:331-334`（P-5 註解）、`:398`、`:547`；`.gitignore:38`（`*venv/`）；`LOCAL-DEV.md:112`；`scripts/validate_env_contract.py:101`；`requirements.md:617-620`；`components.md:642-646`；`brain-infra` 的 `infrastructure-design-questions.md:222`／`:297`／`:366`、`cicd-pipeline.md:337`／`:338`／`:351`／`:352`、`monitoring-design.md:177`；`../carried-review-items.md:25`／`:44`。另開 `brain-infra` 的 `nfr-design/security-design.md:180-190` 核對 D-2「信任邊界內有兩類主體」的第 2 類為 host-local 行程（含自架 runner）。事實與定位皆相符，本項無更正 |
| 4 | **檔案集合一致性** | 本站 5 個檔（問題檔、三份產出、`traceability.json`）與前例 `brain-gateway/infrastructure-design/` 以 `diff` 比對（排除審查產生的 `reviews/`）**相同** |
| 5 | **跨檔傳播**（按事實，逐種表達 grep 四份 `.md`） | `512m`：規格 10 行、監控 2 行、問題檔 1 行，`cicd-pipeline.md` 0（不涉）；其 80% 門檻 `410m` 只在監控（512 × 0.8 ＝ 409.6）；`15s`：規格 3、`cicd` 1、問題檔 1；`1750m`：規格 2；`1320`／`480`：規格 2／3、`cicd` 1／1（同一組算式）；`timeout-minutes: 15`：規格 3、`cicd` 1、問題檔 1；`8.41`：`cicd` 與問題檔各 1（同一組時間戳）；`/healthz`：四檔皆有、無其他路徑寫法；「非阻擋／warning」：四檔方向一致（無一處寫成讓部署失敗）；healthcheck 節奏「每 10 秒」與輪詢「12 次 × 5 秒」在規格、監控、`cicd` 一致。**本項查出並修正 3 處**：(a) 規格引用 `cicd-pipeline.md` 的約束時用了 `IC-` 前綴，與本檔第六節的必做清單撞號，三處改為 `CC-`，並在檔頭寫明兩種前綴的定義；(b) H-2 列指向監控「第二節」（實為 Alerts），改為第一節與第五節；(c) 監控 SLI 第二列的錯誤率定義含混，改為明確的分子分母與排除的五個錯誤碼。他單元規則字面：四檔與 `traceability.json` 擷取全部 `BR\d+\.\d+`，非 `BR71`–`BR78` 者 0 |
| 6 | **可算的數字先算再寫** | shell 整數運算：16 ×（65536 ＋ 1048576）＝ 17825792；× 10 ＝ 178257920（170 MiB）；50 × 5 × 7 ＝ 1750；12 × 5 ＝ 60；1260 ＋ 60 ＝ 1320；540 － 60 ＝ 480；`backend` job 耗時以起訖時間戳相減 82、107、94、104 秒；`bc`：900 ／ 107 ≈ 8.41、512 ／ 370 ≈ 1.38。`traceability.json` 以 `jq` 實算：`upstream_ids` **41**、`coverage` **41**、`OK` **21**、`N/A` **20**、兩向集合差皆 0、id 無重複；`upstream_ids` 與 `../nfr-requirements/` 以 `grep -ohE '\*\*\`NFR21\.[0-9]+\`\*\*'` 抽出的定義集合以 `diff` 比對**相同**。標為**估計**者：進程常駐 ≤ 200 MiB、放大係數 10 倍、`up -d --build` 的增量耗時 |
| 7 | **ADR-0006 四面向 ＋ PBT** | 第八節逐格對照上游 `requirements.md:617-620`（IAM「適用（三處）」、Encryption「適用（新增一處）」、Network exposure「適用（新增一處）」、Audit logging「適用（兩處）」）與 `../nfr-design/security-design.md` §九（四格「適用」）：本表四格皆「適用」，**判定欄無一格相反**。Encryption 一格的內容依 nfr-design 審查 `R-05` 寫為「經使用者接受的例外」而非「滿足」，並點名 `brain-infra` 7.3 的「以不離開本主機滿足」措辭與本站不同、上游不回改。Network exposure 一格比 `brain-infra` 7.4 多算三列（`db`、`backend`、bridge 本身）並補上 host 可達面。PBT：本站不新增純函式；責任是讓 `NFR21.39` 在兩條路線下都於 CI 實際執行（CC-3、S-1），不以 N/A 處理 |
