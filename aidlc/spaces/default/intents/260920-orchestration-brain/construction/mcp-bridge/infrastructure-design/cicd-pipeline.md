# CI/CD 管線 — `U21 mcp-bridge`

> **結論先講：不新增 job。** 既有 `backend` job 加一道漂移閘門與一個 `timeout-minutes`；第二退路下再加一步建 venv。`deploy` job 加一個
> **非阻擋**的部署後健康紀錄步驟；`rollback` job、`ui-regression` 的測試 stack、`docker-build` job 皆不改。規則識別字只用 `BR71`–`BR78`；
> `CC-<n>` 為本檔的 CI 實作約束、`IC-<n>` 為 `infrastructure-specification.md` 第六節的必做清單，兩者皆非規則。
> 本站未執行任何 workflow 或測試；`ci.yml`／`deploy.yml` 的行號皆於 HEAD `45bf7b3` 以 `grep -n`／`sed -n` 核對。

## 一、Stage → Gate 對照

| 管線階段 | 既有 job／step | 本單元在此被驗證的東西 | 本單元需要的變更 |
|---|---|---|---|
| repo contract | `ci.yml:141-176`（`validate_repo_contract.py`、`validate_env_contract.py` 等） | 零新增變數：`mcp-bridge` 服務區塊無 `${…}`，`compose_variables()`（`scripts/validate_env_contract.py:101`）掃不到新變數；`backend/mcp_bridge/` 無 `os.environ`／`os.getenv`，`backend/.env.example` 不需增列 | 無 |
| frontend | `ci.yml:178` 起 | 無關（`frontend/package.json` 無變更，`NFR21.38`） | 無 |
| backend import smoke | `ci.yml:264-272`（`import main`） | `main` 不 import `mcp_bridge`——bridge 是獨立進程（**CC-1**） | 無 |
| OpenAPI 漂移 | `ci.yml:281-289` | bridge 不在 backend 加任何路由，`openapi.json` 不因本單元改變；**但**它是產生器的輸入，`openapi.json` 改了而工具產物沒重產由下一列抓 | 無 |
| WS 契約漂移 | `ci.yml:299-300` | 無關 | 無 |
| **MCP 工具宣告漂移（新增）** | 新步驟，緊接 `:300` 之後、`:303` 之前 | `python scripts/gen_mcp_tools.py --check`：自已 commit 的 `openapi.json` ＋ `allowlist.json` 重產，與已 commit 的 `generated_tools.json` 比對（`BR72.9`、`NFR21.31`） | **新增一步**（第二節 S-1） |
| backend 單元測試 | `ci.yml:303-306`（`unittest discover -s tests -v`） | `NFR21.*` 中全部 `unittest`／PBT／YAML 斷言；T-1–T-8；兩條依賴路線下皆**實際執行**、skip 為 0（`NFR21.30`） | 第二退路：之前加建 venv 的一步（S-3） |
| 真實 PostgreSQL job | `ci.yml:308` 起、`:531` 起 | 本單元無 DDL | 無 |
| Docker 建置 | `ci.yml:614-632`（`./backend` context，`push: false`） | bridge 與 backend 共用 context，第二退路的 Dockerfile 改動在此於 PR 階段驗證 | 無 |
| `ui-regression`（gh-aw） | `deploy/docker-compose.test.yml` | 不含 bridge（`brain-infra` 第 26 項、H-9） | 無 |
| 部署 | `deploy.yml:126-129` 的 `up -d --build --remove-orphans` | 第七個服務建立 | 無（同一行指令自動涵蓋） |
| **部署後健康紀錄（新增）** | 新步驟，放在資料面探測（`deploy.yml:313` 起）之後、Redis 重啟驗證（`:398` 起）之前 | `mcp-bridge` 容器達 `healthy`（`NFR21.32` 的部署後實測） | **新增一步、非阻擋**（第四節） |
| 回滾 | `deploy.yml:547` 起 | last-good 早於本單元時，`--remove-orphans` 移除 bridge 容器 | 無 |

## 二、CI 的具體變更（全部在 `backend` job，`ci.yml:242-306`）

| # | 變更 | 第一順位 | 第二退路 | 依據 |
|---|---|---|---|---|
| S-1 | 步驟 `MCP tool spec drift`：`run: python scripts/gen_mcp_tools.py --check`，**不帶 `env:`** | ✔ | ✔ | H-4、`NFR21.31`；不帶 `env:` 的理由同 `:294-298` 的 WS 閘門註解——產生腳本只 import 純函式 `mcp_bridge.generator`，不 import `main`，紅燈只能代表產物漂移 |
| S-2 | job 層 `timeout-minutes: 15` | ✔ | ✔ | nfr-design 審查 `R-09` 第 3 點；同檔先例 `ci.yml:557`；本分支最近 4 次成功的 `backend` job 為 82／107／94／104 秒（`gh run view` 讀出的起訖時間戳相減），15 分鐘＝900 秒，約為最大值的 8.41 倍 |
| S-3 | 步驟 `Create isolated MCP venv`，在 `Run unit tests` 之前：於 repo 根目錄建 `.mcp-venv/`（`python -m venv`），以其 `pip` 安裝 `backend/requirements-mcp.txt` | — | ✔ | `../nfr-design/reliability-design.md` §6.3；repo 根目錄不在映像 build context 內，`.gitignore:38` 的 `*venv/` 涵蓋 |
| S-4 | `actions/setup-python` 的 `cache-dependency-path` 改為多行，含 `backend/requirements.txt` 與 `backend/requirements-mcp.txt` | — | ✔ | 不改則 pip 快取鍵不隨 `requirements-mcp.txt` 變動；只影響速度，不影響正確性 |

**兩條路線下 `requirements.txt` 的安裝步驟（`ci.yml:259`）都不變**：第一順位因 `mcp` 已在其中而自然安裝；第二退路下主直譯器沒有 `mcp`，
純函式 PBT、`--check` 與非 SDK 單元測試照常在主直譯器執行（`NFR21.40`），只有端到端案例經 venv 子進程（`../nfr-design/reliability-design.md` §6.1–§6.2）。

## 三、讓既有 job 保持有效的實作約束（`code-generation` 必須遵守）

| # | 約束 | 違反時的症狀 |
|---|---|---|
| **CC-1** | `backend/main.py` 與任何 router **不得** import `mcp_bridge`；bridge 只以獨立進程存在 | 第二退路下 import smoke（`:264-272`）與 OpenAPI 漂移（`:281-289`）會因 `mcp` 不在主直譯器而紅燈——看起來像別處壞了 |
| **CC-2** | `gen_mcp_tools.py` 與 `mcp_bridge.generator` 不讀環境變數、不 import `main`／`mcp`／`httpx` | S-1 需要 `env:` 或在第二退路下 import 失敗；紅燈不再只代表產物漂移 |
| **CC-3** | 本單元全部測試檔內 `skipTest`／`skipUnless`／`skipIf`／`SkipTest` 出現 0 次；前置條件不成立一律 `AssertionError`（`../nfr-design/reliability-design.md` §6.3） | 缺 `mcp` 或缺 venv 時測試靜默跳過，CI 綠燈而 T-1／T-2 從未執行 |
| **CC-4** | 第二退路的子進程一律以 `asyncio.create_subprocess_exec` 啟動、測試端不阻塞事件迴圈；單案等待上限 30 秒，逾時以 `AssertionError` 失敗並終止子進程（nfr-design 審查 `R-09` 第 1、3 點） | 阻塞式 `subprocess.run` 使同事件迴圈內的 backend 無法回應 → 死結 → 只能靠 S-2 的 15 分鐘上限中止 |
| **CC-5** | 部署檔的結構斷言以 `yaml.safe_load` 解析 `deploy/docker-compose.deploy.yml`（`PyYAML` 已在 `backend/requirements.txt`），路徑以測試檔位置推得 repo 根。斷言集合＝`NFR21.32` 原判準 ＋ `NFR21.16` ② ＋ 本站新增四項：`environment` 與 `env_file` 兩鍵不存在；`stop_grace_period` 為 `15s`；`command` 含 `--backend-url` 與 `http://backend:8000`；`ci.yml` 的 `backend` job 含 `gen_mcp_tools.py --check` 與 `timeout-minutes` | compose 被改壞（例如加了 `ports:` 或 `environment:`）而任何 CI 閘門都看不到——既有 validator 不解析 compose 的 `ports:`／`networks:`（`deploy/docker-compose.deploy.yml:28-30`） |
| **CC-6** | nfr-design 審查 `R-02` 的修正（shield 與閘門名額）落地後，**進行中的 backend 請求數 ≤ 16** 必須仍成立（名額歸還不得早於 backend 交換結束，或放棄 shield） | backend 同步執行緒池（anyio 預設 40，未實測）被 bridge 佔用的上界失守；`infrastructure-specification.md` 第三節的共享資源邊界不再成立 |
| **CC-7** | 部署健康步驟（第四節）的取值命令以不觸發 `set -e` 的形式執行（條件位置或顯式容錯），步驟結束碼由判定邏輯決定且恆為 0（比照 `deploy.yml` 資料面探測的 `PROBE-CONTRACT P-5` 註解，`:331-334`） | `docker inspect` 在容器尚未建立時回非零 → 步驟意外失敗 → 一個本應只是 warning 的狀況觸發整個 stack 的 rollback |

## 四、部署策略與環境推進

**環境推進**：本機 dev（開發者手動 `python -m mcp_bridge`）→ CI（`unittest` 驗證拓樸，不起容器）→ PR 合併進 `ut` → staging 部署（deploy-on-merge，
ADR-0007／ADR-0008）。production 不在範圍內。三個環境之間**沒有任何設定要推進**：零環境變數，差異只在 `--backend-url`（命令列參數）。

**部署策略**：單一副本的**重建**（`up -d --build` 對內容有變的服務重建容器）。不做 blue/green、canary 或 rolling——無實際 client、沒有流量可分；
重建期間 bridge 不可用數秒，對使用者影響為 0。

**部署後健康紀錄步驟**（`deploy` job 新增，位置見第一節）：

| 項 | 設計 |
|---|---|
| 做什麼 | 以 `docker compose … ps -q mcp-bridge` 取容器 id，輪詢 `docker inspect --format '{{.State.Health.Status}}'` 至多 12 次、每次間隔 5 秒（上界 60 秒） |
| 通過 | 讀到 `healthy` → 印一行 `mcp-bridge healthy` |
| 未通過 | 印 `::warning::`（含最後一次讀到的狀態與 `RestartCount`）＋ `docker compose … logs mcp-bridge --tail=40`；**結束碼 0**（CC-7） |
| 不做 | 不呼叫 `/mcp`、不使用任何 token（Actions log 公開）；不讓部署失敗、不觸發 rollback（`infrastructure-specification.md` 第十節第 1 點） |
| 預算 | 新增有界 60 秒：`DEPLOY.md` §5.9.1 的有界合計 1260 → 1320 秒，無界項剩餘 540 → 480 秒（shell 實算；IC-6 ③） |
| 為何放在資料面探測之後 | 那時 `backend` 已確認可服務；bridge 的健康與 backend 無關（`/healthz` 不連 backend），但放在其後可避免與既有步驟爭用診斷輸出，且早於會中斷 session 的 Redis 重啟驗證 |

## 五、回滾程序

| 情境 | 程序 | 資料面影響 |
|---|---|---|
| bridge 單獨失效（健康步驟 warning、或部署後才發現） | 主機上 `docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env stop mcp-bridge` 止損；以 fix-forward PR 或 revert PR 走正常管線 | 無：bridge 無狀態、無 volume、本版無 client |
| 整個 stack 的部署失敗（既有路徑） | 既有 `rollback` job 還原 last-good（`deploy.yml:547` 起），開 revert PR、交 Deploy Doctor | last-good 早於本單元時，`--remove-orphans` 移除 bridge 容器（正確結果） |
| 要整個撤掉本服務 | 刪除 compose 服務區塊（第一順位另刪 `mcp==` 一行；第二退路另刪 Dockerfile 的 venv 段與 `requirements-mcp.txt`）→ 合併後 `up -d --remove-orphans` 移除容器 | 無 |

## 六、Secrets management

**不新增任何 GitHub secret 或 variable**；`deploy.yml` 的 env 對照表（`:100` 起的 `Write deploy/.env from secrets`）與 `render-env.sh` 不改（H-6、H-8）。
bridge 不持有憑證：使用者 token 只在每次請求的 `Authorization` 標頭中，存在於該請求的 `ContextVar`、請求結束即重設（`BR73.3`），不落地、不進 log。
CI 的測試以測試內產生的 JWT 執行（`JWT_SECRET: ci_only_not_a_real_secret`，`ci.yml:305`），不需真實 token。部署健康步驟不需要任何 secret。
`project.md ## Mandated` 的「新增憑證型 secret 後查證其落在 secrets 而非 variables」本單元**不觸發**（無新增）。

## 七、為何不新增 job

| 候選 | 不採的理由 |
|---|---|
| 獨立的 `mcp-bridge` CI job | 純函式 PBT、`--check`、非 SDK 單元測試都在主直譯器；端到端案例在兩條路線下都能在 `backend` job 內執行（第一順位同直譯器；第二退路經 venv 子進程）。另開 job 只會多一次 `pip install` 而不多驗任何東西 |
| 把 bridge 加進 `ui-regression` 的測試 stack | 前端 e2e 不觸及 MCP 路徑；每個 PR 多起一個容器而不多驗任何東西（H-9） |
| 部署時對 `/mcp` 做真實工具呼叫 | 需要有效使用者 token，而 Actions log 公開；工具呼叫的正確性由 CI 的 T-1–T-8 守 |

## 八、上游回寫（不回改上游檔，以本列為準）

| 上游 | 原文 | 本站定案 |
|---|---|---|
| `brain-infra` `cicd-pipeline.md:337`（第 22 項） | 漂移檢查落 `frontend` 或 `backend` job，「實作時擇一並在此回寫」 | **`backend` job**（產生器以 Python 實作，H-4） |
| `brain-infra` `cicd-pipeline.md:351`（第 26 項） | 「若 `U21` 的驗證需要它，由 `U21` 與 `build-and-test` 決定並回寫本列」 | **不需要**：驗證在 `unittest` 拓樸內完成（H-9） |
| `brain-infra` `cicd-pipeline.md:352`（第 27 項） | 「可直接寫在 compose 的 `environment:` 內」 | bridge 不讀環境變數（`BR71.1`），服務區塊**不寫** `environment:`；`backend:8000` 走命令列參數 |
