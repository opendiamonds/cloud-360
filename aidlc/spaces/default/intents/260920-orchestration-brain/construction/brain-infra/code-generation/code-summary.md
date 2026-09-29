# Code Summary — `U1 brain-infra`（`packaging`）

## 〇、一句話

本單元讓 Redis（第 5 服務）、Ollama（第 6 服務）與 PG 18 ＋ pgvector 在三份 compose、
`render-env.sh`、兩份 `.env.example`、`deploy.yml` 與兩份部署文件上同時落地，並補上一個
**真的會穿過 `/api` 並查 Postgres** 的部署後探測——本 repo 在此之前對 `/api` 的部署期
命中數是 **0**。

**沒有一行應用程式邏輯。** 產出是 YAML、shell、SQL、GitHub Actions 與文件。

## 一、改了什麼（13 個檔）

| 檔 | 改動 | 對應改動清單 |
|---|---|---|
| `schema_rbac.sql` | `BEGIN;` 之後第一條加 `CREATE EXTENSION IF NOT EXISTS vector;`，檔頭涵蓋清單補 X 區塊與 pgvector 前置檢查註解 | 11 |
| `backend/database.py` | 新增 `_ensure_vector_extension()`，**呼叫點在 `create_all()` 之前** | 12 |
| `backend/tests/test_vector_extension_bootstrap.py` | 新檔，7 個測試（含呼叫順序與 `DEPLOY.md` blocking 同步） | 測試 |
| `backend/tests/test_render_env_redis.py` | 新檔，9 個測試（`subprocess` 跑真實 `bash`） | 測試 |
| `deploy/render-env.sh` | 必填檢查 ＋ `$` 擋阻名單各加入 `REDIS_PASSWORD`；heredoc 寫出七個變數（六字面值 ＋ 一個走 `${…}`） | 4a／4b／4c |
| `deploy/.env.example` | 列出七個新變數（未註解的 `KEY=` 形式） | 5 |
| `backend/.env.example` | 列出七個變數的本機值 | 10 |
| `deploy/docker-compose.deploy.yml` | `backend.environment:` 七者無 `:-`；新增 `redis`／`ollama`；`networks:` 分段；三個 volume（PG volume 改名）；全部服務 `logging:` ＋ 記憶體上限；兩個新 healthcheck；兩條 `depends_on`；redis `command:` 承載 AOF ＋ maxmemory ＋ ACL | 6／7／16a／17a／17b |
| `deploy/docker-compose.test.yml` | Redis 三者 ＋ `EMBEDDING_PROVIDER: stub`；新增 `redis`（含自己的 ACL）；`networks:`；全部服務 `logging:` ＋ 上限（值與 deploy 不同）；redis healthcheck；db 映像改 PG 18 ＋ pgvector；只有 redis 有 `restart:`、只有一條 `depends_on` | 8／16b／17b |
| `docker-compose.yml`（repo 根） | **只改** db 映像為 `pgvector/pgvector:pg18`，並就地警告 `postgres_data` volume 跨大版本不相容 | 9 |
| `.github/workflows/deploy.yml` | deploy job：required-secrets ＋ `env:` 加 `REDIS_PASSWORD`、新增「Pull the embedding model」與「Probe the data plane」兩步；rollback job：`env:` 加 `REDIS_PASSWORD`、健康檢查迴圈併入探測 | 1／2／3／15 |
| `DEPLOY.md` | 新增第 5 節（5.1–5.11），十一項必寫內容；§2.2 表加 X 列 ＋ 新增 §2.2.6；§1.4 加七個變數；§3.3 加 brain-infra 部署注意；**英文 `### Database` 補 vector extension 一行**（唯一寫兩半的項目） | 13 |
| `LOCAL-DEV.md` | §0 硬依賴表 ＋3 列；§1 前置檢查加 pgvector／Redis／port 6379；§2 新增 H4（pgvector）與 H5（volume 不相容）；schema 演進表補「唯一在 `create_all` 之前的例外」；§3 `.env` 加七個變數；§9 常見卡關 ＋4 列；**更正既有錯誤敘述**（`schema_rbac.sql` 不建 admin/admin123） | 14 |

## 二、五個最容易做錯的地方，以及本次怎麼處理

清單裡有五處是經對抗式審查才修正的，照舊版直覺實作會踩到。逐項對照：

| # | 陷阱 | 本次做法 | 怎麼知道沒踩 |
|---|---|---|---|
| 3 | 把七個變數全做成 `deploy.yml` 的 `env:` | **只有 `REDIS_PASSWORD` 進 `env:`**；其餘六個是 `render-env.sh` 的字面值 | `test_render_env_redis.py` 案例 4／4b：即使完全不提供或明確傳入空字串，六者仍渲染為非空字面值。突變驗證（改成 `${NAME:-}`）→ 3 個測試紅 |
| 4b | `$` 擋阻名單漏掉 `REDIS_PASSWORD`（**無聲**失敗） | 加入名單，共七個名字 | 案例 2 以 `ab$cd` 斷言非零退出。突變驗證（移出名單）→ 1 個測試紅 |
| 12 | 照既有六支 `_ensure_*` 的形狀放在 `create_all()` **之後** | 放在**之前**，並在 docstring 寫明它是家族唯一例外 | 案例 2 以共用 parent mock 斷言 `mock_calls` 順序。突變驗證（搬到之後）→ 紅，訊息印出實際順序 |
| 17b | ACL 資產只做 deploy 側（test stack 每個 PR 全紅） | **兩份 compose 各有自己的 `command:` ACL**，不共用檔；test 側用內嵌測試值 | `docker compose config` 兩份皆 exit 0；服務集合差集實算為 `{cloudflared, ollama}` |
| 15 | `docker compose exec` 無 `-T`；判定命令觸發 `set -e` | 一律 `exec -T`；兩個判定命令都在 `if` 條件位置取值 | 以獨立 harness 實跑四種情形（模型在／不在 × pull 成功／失敗），皆符合規格 |

另外兩個易錯點：

- **`/api/auth/login` 的「通」是 HTTP 401，不是 2xx。** 探測刻意用固定的不存在使用者名稱
  `__cloud360_deploy_probe_no_such_user__`。實測：回 401 → exit 0；回 200 → exit 1。
  寫成「回 2xx 才算通」會是一個永遠不通過的檢查。
- **重試次數與逾時**：`deploy` 側 `N=30`／`T=10`（最壞 450s），`rollback` 側 `N=18`／`T=10`
  （每輪兩個 request，最壞 450s）。**約束式右側未實測**，`up -d --build` 是無界項——
  這一點記為 open item，不宣稱已滿足（見 §四）。

## 三、驗證結果

| 命令 | 結果 |
|---|---|
| `cd backend && python -m unittest tests.test_vector_extension_bootstrap tests.test_render_env_redis -v` | **16 tests OK** |
| `cd backend && python -m unittest discover -s tests -v` | **365 tests OK**（基線 349 ＋ 本單元 16；基線在補裝 `openpyxl==3.1.5` 後為全綠） |
| `python3 scripts/validate_env_contract.py` | **passed** |
| `python3 scripts/validate_repo_contract.py` | **passed** |
| `docker compose -f deploy/docker-compose.deploy.yml --env-file <rendered> config` | exit 0；七個變數與 redis `command:` 內插結果逐一核對無誤 |
| `docker compose -f deploy/docker-compose.test.yml config` | exit 0 |
| 兩份 compose 的服務集合差集 | 實算 `{cloudflared, ollama}`，符合 `§六` (c) |
| `deploy.yml` 全部多行 `run:` 的 `bash -n` | 16 個區塊全部 ok |
| 探測／pull 步驟的分支行為 | 以獨立 harness 實跑 8 種情形，全部符合規格 |
| 三項突變驗證 | 全部由綠轉紅，再還原轉綠——測試非空洞 |
| `pgvector/pgvector:pg18`、`redis:8-alpine`、`ollama/ollama:latest` | Docker Hub tag 實地查證存在 |

## 四、本單元**沒有**做到的事（不美化）

1. **`REDIS_PASSWORD` secret 尚未建立。** 實查 secrets 與 variables 各一次：它不在任何
   一邊（也無 org-level／environment-level）。**不是誤存為 variable，所以不需重新產生
   金鑰**，但必須在第一次部署前建立，否則 deploy job 會在 required-secrets 步驟失敗。
2. **Redis ACL 的 `command:` 未經執行期驗證。** 本機有 docker CLI 但 daemon 未執行。
   這一層沒有任何 CI 閘門。
3. **`rollback` 耗時約束式未實測**（`up -d --build` 無界）。
4. **十個記憶體上限與 `maxmemory` 皆為暫定值**，且**複量期限尚無人指定**。
5. **`§六` 的補閘門 (a)–(d) 未實作**（明文不屬本單元交付）。本單元**不宣稱** compose
   改動有任何自動化保護——九項無閘門項目原樣成立。
6. **`DEPLOY.md` 英文半部的既存落差未修補**，只補了 blocking 同步要求的那一行。

完整清單與嚴重度見 `traceability.json` 的 `open_items`（**11 項**——原 9 項 ＋ conductor 覆核新增的
`OPEN-10`／`OPEN-11`，見 §六）。

## 五、跨單元的三件事

- **`U10 session-store`**：需確認 `BrainSession.messageHistory` 的截斷策略（`maxmemory`
  推導鏈的根），並對 `S-11` 的收窄（三項設定歸 `command:` 獨佔）明示接受或反對。
- **`U6 embedding-port`**：CI 走 `stub`，所以 **e2e 層完全不碰任何 embedding 路徑**；
  四個 provider 實作只由 `U6` 的單元測試覆蓋，**沒有第二道防線**。
- **`U5 memory-data`**：`NFR6.1` 落點 3 的上游衝突（CI job 的 service container 被釘成
  `postgres:16-alpine`）仍未解，且它的 `vector(1024)` 欄位落地時會啟用本單元兩處
  extension 承載的實際效力（在那之前 `schema_rbac.sql` 的行號比較是空集合上的真）。

## 六、Conductor 覆核（不採信派工方的自報，逐項重跑）

本節記載 conductor 自己執行的查證，與 §三 的自報分開列，以便日後看得出哪些是被覆核過的。

### 重跑一致的項目

| 項目 | conductor 實跑結果 |
|---|---|
| 本單元兩支測試 | **16 tests OK**（與自報一致） |
| 既有全套 | **365 tests OK**（與自報一致） |
| `validate_env_contract.py` | passed |
| `validate_repo_contract.py` | passed |
| 五個易錯點逐一開檔核對 | 全部正確——`deploy.yml` 的 `env:` 只加 `REDIS_PASSWORD`（並留註解說明其餘六者為何不進）；`render-env.sh:65` 必填檢查與 `:82` `$` 擋阻名單皆含 `REDIS_PASSWORD`；`_ensure_vector_extension()` 在 `create_all()` 之前且 docstring 寫明它是家族唯一例外;兩份 compose 各有自己的 `command:` ACL 且值不同;探測以 401 為通過條件、`exec -T`、判定命令在 `if` 條件位置 |
| `networks:` 分段（D-3） | 以 YAML 解析核對歸屬：`db`／`redis`／`ollama` 只在 `internal`，`backend` 是唯一跨網段者，`frontend`／`cloudflared` 只在 `edge`，且**不帶 `internal: true`** |
| 服務集合差集 | 以 YAML 解析實算：deploy 6 個、test 4 個，差集 `{cloudflared, ollama}` |
| 三份 compose 的 image 轉換 | deploy `postgres:16-alpine` → `pgvector/pgvector:pg18`；test 同；**根 compose 是 `postgres:15-alpine` → pg18**（跨三個大版本，與 `DEPLOY.md` §5 標題的「16→18」適用範圍不同，後者只管 deploy stack，正確） |
| `source-manifest.json` 完整性 | 以集合比對 `git status` 的非 `aidlc/` 路徑：13 對 13，**無漏列、無虛列、無不存在路徑** |
| 計畫 diff 是否只有 checkbox | 機械核對：兩側各 41 行，**非 checkbox 差異為 0**——核可 fingerprint 仍有效 |
| `DEPLOY.md` 重編號是否留下壞引用 | `NFR5.` 全檔 0 命中——agent 自承弄壞過的兩處確實已修 |
| `LOCAL-DEV.md` 三項必寫 | 皆到位：§0 硬依賴表列 pgvector、H4 給可執行前置檢查（`pg_available_extensions`）、H5 處置 `postgres_data` 不相容並抓到 volume 實際名稱隨目錄名而變（`chiton_postgres_data`）的陷阱；`admin`/`admin123` 的既有錯誤敘述已更正 |

### conductor 查出、agent 未發現的三項

1. **`traceability.json` 的 schema 錯誤（本站唯一的阻塞缺陷）。** `traceability` sensor 實跑
   **failed**：`code-generation` 要求每個 `OK` 列的 `target` 是**一個工作區相對檔案路徑**，
   而 agent 把整段散文寫進 `target`（30+ 列），另有 4 列用了不存在的 status `PARTIAL`
   （合法值只有 `OK`／`GAP`／`ORPHAN`／`Deferred`／`N/A`），以及 4 個上游 id
   （`AC2.1.1`／`AC2.1.2`／`AC2.1.3`／`NFR7.1`）出現在表中但未宣告於 `upstream_ids`。
   **處置**：散文全部保留到新的 `note` 欄位（零資訊損失），`target` 改為真實路徑；
   `US2.1`／`AC2.1.4` 改為 `Deferred`（本單元只交付儲存層，不宣稱 AC 已滿足），
   `NFR6.1`／`ADR-0006` 改為 `OK`（該做的都做了，未做的部分不屬本單元，理由在 `note`）；
   四個缺漏 id 各補一列 `N/A` 並寫明落在哪個單元。重跑 sensor **passed**。
2. **`ollama/ollama:latest` 沒釘版本（`OPEN-10`）。** 同一輪改動的另兩個 image 都釘了主版本，
   這一個沒有，而 `code-summary.md` 原本只記「tag 實地查證存在」，**未記載這個取捨**。
   deploy-on-merge 之下任何重新部署都可能靜默拉到不同版本，且 compose 改動無任何 CI 閘門。
   已在 compose 就地註明並記為 open item；**不逕自挑一個版本號**——那需要先確認與 `bge-m3`
   （dense 1024）的相容性，憑猜寫一個數字比不釘更糟。
3. **`DEPLOY.md` 的 `#### 2.2.x` 編號本來就重複（`OPEN-11`）。** 以 `git show HEAD:DEPLOY.md`
   核對確認是**既有漂移、不是本輪造成**（`2.2.4`／`2.2.5` 各兩次，`2.2.1`–`2.2.3` 排在後面）。
   本單元新增的 `2.2.6` 取第一個空號、落在已錯亂的序列中間。不重排它（repo 級文件整理）。

### 一項環境變動，如實記載

agent 在 Step 1 發現基線有 **6 個 `ModuleNotFoundError: openpyxl`** 失敗，並在本機補裝了
`openpyxl==3.1.5` 後基線轉為 349 全綠。該套件**本來就在 `backend/requirements.txt`**，
所以這不是新增依賴、也不需要改任何檔——但它意味著上面「365 tests OK」這個結果
**依賴本機已補裝該套件**。conductor 的重跑在同一個環境下進行，因此繼承同一個前提。

### 本站在引擎層的驗證覆蓋

`required-sections` 對三份 md 皆 passed，`traceability` 修正後 passed。
**`linter` 與 `type-check` 不適用**——兩者的 filter 分別是 `**/*.{ts,js}` 與 `**/*.{ts,tsx}`，
而本單元沒有產出任何 TS／JS 檔（實際 fire 回「does not match sensor filter」）。
這是真正的不適用，不是跳過。

## 七、對抗式審查的六項發現與處置（iteration 1，判定 NOT-READY）

審查判定 NOT-READY（Critical 0／Major 3／Minor 3，依 >2 Major 判定）。**六項全部處置完成**，
其中五項由 conductor 修，一項（R-06）由使用者裁決。三項修法都**不需動 `code-generation-plan.md`**，
故**未重開 Plan Approval**。

| ID | 嚴重度 | 缺陷 | 處置 |
|---|---|---|---|
| **R-02** | Major | **本單元最核心的新安全控制（`NFR4.1(b)/(c)`）零驗證，而同一輪為「先前沒被驗證的 db 路徑」補了探測——機制一模一樣。** 兩支新測試不碰 ACL；`validate_env_contract.py` 只讀環境變數（刪掉整段 `--user` 不會紅）；`redis-cli ping` 以 `default` 通過，與 ACL 無關。**失敗模式是無聲的**：若 `redis-server` 對重複的 `--user` 去重，`default` 保留內建全權、app 使用者照常建立、容器正常啟動、healthcheck 綠燈 | `deploy.yml` 新增步驟 **Verify the Redis ACL actually took effect**：(1) 以 `default` 執行 `SET` 斷言回 `NOPERM`；(2) 以 app 使用者執行 `ACL WHOAMI` 斷言等於 `REDIS_USER`；(3) `docker inspect` 斷言三個旗標都進到容器 argv。兩個身分用的命令都是**可達的**（`SET` 對 `default`、`ACL WHOAMI` 是 @slow 非 @dangerous）。**`REDIS_USER`／`REDIS_PASSWORD` 從 `deploy/.env` 讀，不在 workflow 新增第二份字面值**——那會違反 `team.md` 的單一真實來源 |
| **R-01** | Major | **三項新 Redis 設定沒有任何已設定身分能查證生效。** `INFO` 是 @slow @dangerous，`default`（只有 @connection）與 app 使用者（`-@dangerous`）**都不能執行**，而 compose 註解卻指名 `INFO evicted_keys` 是那條必要關係式的可數訊號；`CONFIG GET`／`ACL LIST` 同為 @admin @dangerous | 採審查給的選項 **(b)**：**不放寬 ACL**（避免加寬 app 權限或新增第三個憑證與同步點），改把訊號換成真正可達的 `MEMORY STATS` ＋ 主機 `docker stats`，並在 compose 註解與 `DEPLOY.md` 就地明寫「三項設定在執行期無法讀回，改值只能改 compose 重新部署」。ACL 那一問由 R-02 的部署期探測回答 |
| **R-03** | Major | **耗時預算只對 `rollback` 算過，`deploy` 側沒有算式，而這一側本輪多了一個無界的 `ollama pull`（首次約 1.2GB）。** 且該 job 既有的兩個等待迴圈（frontend、tunnel）的 `curl` **沒有 `--max-time`**，所以它們在上界上也無界 | `DEPLOY.md` 新增 **§5.9.1**：五項消費逐項列出並標明哪幾項無界，給出約束式（有界部分合計 **1260s** ⇒ 兩個無界項須 **≤ 540s**）與四個必填實測欄位，並寫明超標時**降重試次數而非放寬 `timeout-minutes`**。**附帶為兩個既有迴圈的 `curl` 補 `--max-time 10`**——這是既有狀態，但不補就寫不出任何有效的約束式；`OPEN-3` 範圍由 rollback 擴為兩個 job |
| **R-04** | Minor | conductor 自述「`target` 改真實路徑」，但 46 列中仍有三列是散文（`US2.1`／`AC2.1.1`／`NFR7.1`）——修法未跑完 | 六列 `target` 全部改為實際落點路徑或 `-`；散文一律留在 `note`。重跑 sensor passed。**附帶查證（審查提供）**：`upstream_ids` 與 `coverage` 的 id 集合雙向完全相等，無 `PARTIAL` 殘留 |
| **R-05** | Minor | `ollama/ollama:latest` 未釘版，只存在於 record 的 `OPEN-10`，**部署者看不到** | `DEPLOY.md` 新增 **§5.9.2**，寫明版本不可重現、為何本輪不逕自挑版本（要先確認與 `bge-m3` dense 1024 相容，猜一個數字比不釘更糟）、以及依賴可重現性前的處置與負責人欄位 |
| **R-06** | Minor | 上游要求記「暫定值＋**期限**」，實作給的是空白欄位；`OPEN-4` 自己寫「沒有日期的限期複量會退化成永遠暫定」——**機制到位、義務未完成** | **使用者裁決**：記為**交付後 blocking 前置**。觸發條件二元可判（`REDIS_PASSWORD` 建立 → 首次部署成功 → 七日內），負責人指定 Danniel，量測方式為 `docker stats` ＋ `MEMORY STATS`。**不填猜測日期**：部署尚未發生、無流量可量，猜的日期會讓下一個人以為它被評估過 |

### 審查覆核後的重驗結果

| 命令 | 結果 |
|---|---|
| 兩支新測試 | **16 tests OK** |
| `validate_env_contract.py` ／ `validate_repo_contract.py` | 皆 passed |
| `traceability` sensor | **passed**（R-04 修正後） |
| `deploy.yml` 全部多行 `run:` 的 `bash -n` | **17／17 ok**（新增 ACL 探測步驟後） |
| `deploy.yml` YAML 解析 | OK；新步驟無 `env:` 區塊（值改從 `deploy/.env` 讀） |

### ⚠ 本站在引擎層沒有審查收據，原因與上一站不同

`REVIEW_COMPLETED` 無法登記，錯誤為「workspace source changed after REVIEW_REQUESTED」。
**這一次不是 conductor 的順序錯誤**（判定是在 reviewer 回覆後的下一個動作就嘗試登記的），
而是一個**結構性的工具鏈交互**：

引擎的來源指紋硬排除清單（`.claude/tools/aidlc-lib.ts:14117`）含 `.pytest_cache`、
`.mypy_cache`、`.ruff_cache`、`node_modules` 等，**但不含 `__pycache__`，也不含 `.hypothesis`**。
本 repo 用的是 Python 內建 `unittest`（不是 pytest），所以**跑一次測試就會產生 `.pyc` 並改變
來源指紋**。而 conductor 的 brief 逐字要求審查方「自己實際做一次突變確認它真的會紅」——
突變＋還原＋重跑，原始碼被完整還原（審查方自留的 `reviewed-source-*.tsv` 記了 13 個檔的雜湊，
conductor 逐檔比對**內容與權限差異皆為 0**），但 `.pyc` 內嵌來源 mtime，還原後的位元必然不同，
且無法回復成原值。`--retry-pending` 被同一道檢查擋下。

**沒有設定層的解**：`.aidlc-source-paths.json` 的 schema 是 `{"version":1,"paths":[...]}`，
只支援**納入**、不支援排除（`aidlc-lib.ts:15018`）。

**持久預防措施（下一站起適用）**：
1. 執行 Python 時帶 **`PYTHONDONTWRITEBYTECODE=1`**，根本不產生 `.pyc`。
2. **不要在綁定的審查窗口內要求審查方跑測試套件或驗證器**。突變驗證要嘛在 `REVIEW_REQUESTED`
   之前由實作方完成（本站即如此，三項突變已驗），要嘛安排在收據登記之後的獨立一輪。
3. 這兩項本輪**未**寫進 `unit-test-instructions.md`——該檔被 fingerprint 綁定，改它會重開
   Plan Approval。正確落點是規則層，已記入 stage diary 待 learnings 儀式收斂。

**如實記載**：這是**連續第二站**沒有引擎層審查收據。唯一能取回收據的路徑是重設 attempt，
而 `STAGE_JUMPED` 是全 stage 共用的 floor，會作廢 `nfr-requirements`／`nfr-design`／
`infrastructure-design` 三站已 commit 的收據。經使用者裁決不付這個代價。
**審查本身完整跑完且六項發現全數處置**——缺的是簿記，不是覆蓋。
