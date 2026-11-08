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

## 重新查驗（Request Changes 後）

查驗時間：`2026-10-20T06:13:32Z`（`date -u` 取值）。查驗基準：HEAD `fa51564`。

### 觸發原因

使用者對整個 code-generation 站送出 Request Changes，原文：

> 「修正 functional-design/merge-blockers.md 列出的 19 項合併前必修，各在所屬單元修正並附測試；需人工裁決的項目（#7、#8 等）逐項問我。object-picker-ui 的 R-08、R-09 已修，重新審查即可。」

引擎因此把本單元計畫檔的勾選全部重設為未勾。本單元程式早在 `7ce1bee` 落地，本輪**不改任何應用程式碼**，只逐項對照 repo 現況重新查驗並勾回。

### 19 項合併前必修與本單元的關係

- `merge-blockers.md` 的 19 項中，**劃給 `brain-infra` 的為 0 項**。
- 第 18 項（Redis `maxmemory 256mb`＋`noeviction` 的容量）劃給 `session-store`／`work-orchestrator`。設定雖位於本單元交付的 `deploy/docker-compose.deploy.yml`，**本輪不修改它**，留待 `session-store` 由人裁決。

#### 跨單元落點（review-03 R-04 補，2026-10-30）

「劃給本單元 0 項」是就清單的單元欄而言；下表列出修法實際碰到（或可能碰到）本單元 13 個交付檔的四項，以及檔案修改權屬。負責單元與處置取自 `functional-design/merge-blockers.md` 的對應列；落點以 `git diff --stat 763a45a 7a50a40` 與 `grep` 實查，不採清單敘述。

| # | 負責單元 | 會改到本單元哪個檔（實查） | 本單元負責的段落是否被動到 | 改完是否需回頭重驗本單元勾選 |
|---|---|---|---|---|
| 15 | `membership-service`（已修正，計畫 Step 15c） | 實際修法落在 `backend/main.py` startup 呼叫 `ensure_project_members_on_startup()`（`backend/main.py:24`、`:98`）與新檔 `backend/services/membership_backfill.py`，**皆非本單元檔**；附帶同步本單元檔 `DEPLOY.md` §2.2.10（`:951`）與 `LOCAL-DEV.md`（成員回填說明）。`deploy.yml` 無回填步驟——回填改由 backend 啟動承擔，故不需部署步驟 | 否。§2.2.10 屬 U19，本單元負責 §1.4、§2.2 表、§2.2.6、§3.3、§5.1–5.11；`backend/database.py` 未改 | 已涵蓋：變動早於收據 `reviewed-source-549cadcafb78.tsv`（10-25），並經「共用檔異動後重新驗證」（10-29）逐檔比對；之後若再改 `DEPLOY.md`／`LOCAL-DEV.md`，須依同節的 hunk 子集方法重驗 Step 12、13 |
| 16 | `membership-service`（已修正，計畫 Step 15d） | 實際修法為 `SET LOCAL lock_timeout`，落在 `backend/services/membership_service.py`、`membership_errors.py`、`user_router.py`（`grep -rln lock_timeout`），**皆非本單元檔**；本單元的 `backend/database.py` engine 設定（含連線池）**未改**（`grep pool_size\|max_overflow\|lock_timeout backend/database.py` 零命中） | 否 | 不需。若日後改以 engine 層（`backend/database.py` 的 `create_engine` 參數）設定連線池或逾時，屬改動本單元檔，須重驗 Step 2（呼叫順序）與兩支單元測試 |
| 18 | `session-store`／`work-orchestrator`（已修正，`session-store` 計畫 Step 14） | `deploy/docker-compose.deploy.yml` redis `command:` 的容量註解（`:259-271`，`maxmemory 256mb` 與 `noeviction` 值不變）、`deploy/.env.example`、`backend/.env.example`、`LOCAL-DEV.md`、`DEPLOY.md`——**皆為本單元檔** | 是（同一服務的 `command:` 與範本檔），但只改註解與新增變數，本單元的判準（`--appendonly yes`、`--maxmemory`、policy 旗標存在、七個本單元變數）不變 | 已涵蓋：變動（10-23）早於收據（10-25），10-29 比對兩份 compose 與兩份 `.env.example` 逐位元等於收據。日後若改 `maxmemory` 值或 policy，須重驗 Step 6 第四格與 `traceability.json` 的 `AC2.1.4`／`S-8` 註記 |
| 19 | `brain-gateway`（已查證，非合併前阻擋） | 不需改檔。守門已存在於本單元檔 `.github/workflows/deploy.yml`：「Require the secrets that must not default」步驟 `:80`，`env:` 帶入 `OPENROUTER_API_KEY` 於 `:85`，缺值檢查 `:92`，錯誤說明 `:100`；rollback job 同樣帶入於 `:695`（`grep -n OPENROUTER_API_KEY` 實查，於 HEAD `c6a40f9`）。該行由 `fa8ce42`（U13）加入，非本單元 | 否（本單元在同一步驟只負責 `REDIS_PASSWORD`） | 不需。若 `brain-gateway` 日後改動該步驟的必填清單，須重驗 Step 10（`env:` 只新增 `REDIS_PASSWORD`）與 Step 14 |

### 逐步查驗摘要（43 個勾選：勾回 42、未勾 1）

| Step | 結果 | 查驗依據（開檔實看） |
|---|---|---|
| 1 | 3／3 勾回 | `unit-test-instructions.md` 第三節有本單元專屬命令；兩支 validator 可執行。**註**：本機 PATH 無 `python`，只有 `python3`（3.13.7），所有命令以 `python3` 執行 |
| 2 | 2／2 | `schema_rbac.sql:63` 為 `CREATE EXTENSION IF NOT EXISTS vector;`；`backend/database.py:89` 呼叫 `_ensure_vector_extension()`，`:90` 才是 `create_all()`（計畫寫的 `:76` 已因後續單元位移，判準不變） |
| 3 | 2／2 | 測試檔存在，見下方命令結果 |
| 4 | 3／3 | `render-env.sh:75` 必填檢查、`:92` `$` 擋阻名單含 `REDIS_PASSWORD`；heredoc `:131–137` 寫出七個變數（計畫的 `:44–49`／`:59` 已位移） |
| 5 | 2／2 | 測試檔存在，見下方命令結果 |
| 6 | 6／6 | `backend.environment:` 七者無 `:-`（`:117–123`）；`redis`／`ollama` 服務、`edge`／`internal` 分段、`db_pg18`／`redis_aof`／`ollama_models` 三個 volume、全服務 `logging:` 與 `memory:`、兩個新 `healthcheck`、兩者 `restart: unless-stopped`、backend 對 `redis`（`service_healthy`）與 `ollama`（`service_started`）兩條 `depends_on`；`cloudflared` 只在 `[edge]`。ACL 資產採 `command:` 的 `--user` 旗標（`:277–291`），與原交付相同形式 |
| 7 | 2／2 | test compose：Redis 三者 ＋ `EMBEDDING_PROVIDER: stub`、`redis` 服務含自己的 ACL、無 `ollama`、無 AOF／`maxmemory`／具名 volume、只有 `redis` 有 `restart:`、backend 只有 `db`／`redis` 兩條 `depends_on`（`redis` 那條是本單元新增的唯一一條）、db 映像 `pgvector/pgvector:pg18` |
| 8 | 2／2 | root `docker-compose.yml:17` 為 `pgvector/pgvector:pg18`；無 `logging:`／`networks:`／`memory:`，`ports:` 保留 |
| 9 | 2／2 | 兩份 `.env.example` 皆以未註解 `KEY=` 列出七個變數 |
| 10 | 4／4 | 探測步驟（`:313`）以 401 為通過；rollback 迴圈寫 `restored=` 不用 `exit`；`git blame` 確認本單元（`7ce1bee`）在 `env:` 只新增 `REDIS_PASSWORD`（`:75`／`:112`／`:682`），`:76` 的 `OPENROUTER_API_KEY` 由後續 `fa8ce42`（U13）加入，非本單元；`ollama pull` 步驟（`:250`）用 `exec -T` 並區分兩情形 |
| 11 | **2／3** | 兩支 validator 綠；**全套 unittest 非全綠，未勾**——見下方 |
| 12 | 3／3 | `DEPLOY.md` §2.2 表列 vector 擴充、§2.2.6、§5（5.1–5.11）；英文半部 `### Database` 有 vector 一句 |
| 13 | 3／3 | `LOCAL-DEV.md` 第 0 節硬依賴表、H4（pgvector ＋ `pg_available_extensions` 檢查）、H5（`postgres_data` 跨大版本處置） |
| 14 | 3／3 | 見下方 `gh api` 結果 |
| 15 | 3／3 | `source-manifest.json` 13 個路徑全部存在；`traceability.json` 46 列（OK 40／N/A 4／Deferred 2），**每個 `OK` 指向的檔皆存在**（9 個不同目標）；本檔存在 |

### 各命令的實際結果

| 命令 | 結果（取自實際輸出） |
|---|---|
| `python3 -m unittest tests.test_vector_extension_bootstrap tests.test_render_env_redis -v`（`backend/`） | `Ran 16 tests in 0.587s` → `OK` |
| `python3 scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.`，exit 0 |
| `python3 scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.`，exit 0 |
| `python3 -m unittest discover -s tests`（`backend/`） | `Ran 1204 tests` → `FAILED (failures=28, skipped=1)`；`ERROR:` 類測試 0 個 |
| `gh api repos/opendiamonds/cloud-360/actions/secrets`（只取名稱） | 13 個名稱，**含 `REDIS_PASSWORD`** |
| `gh api repos/opendiamonds/cloud-360/actions/variables`（只取名稱） | 2 個名稱，**不含 `REDIS_PASSWORD`** |

**全套 28 個失敗的歸屬**：28 個 `FAIL:` 全部在 `test_mcp_bridge_app`／`test_mcp_bridge_e2e`／`test_mcp_bridge_topology`（U21 `mcp-bridge`），以 `grep -v mcp_bridge` 篩後為 0。失敗訊息逐字為「mcp 版本為 1.29.0，本單元釘選 2.3.0。請在 backend/ 執行：pip install -r requirements.txt」——本機安裝的 `mcp` 為 1.29.0，`backend/requirements.txt:71` 釘 `mcp==2.3.0`。這是**本機環境與釘選版本不符**，不是本單元缺陷，也不在本單元的檔案範圍；本輪不擅自安裝套件。Step 11 第三格因此**維持未勾**，待在依賴已同步的環境重跑全綠後再勾。

**`gh api` 判定**：`REDIS_PASSWORD` 在 secrets、不在 variables，二元判準成立。它從未以 variable 形式存在（2026-09-27 那次查詢兩處皆無，本次只在 secrets），故「誤存為 variable 須重新產生金鑰」的條件**未觸發**，`OPEN-1` 的「尚不存在」已由現況解除。輸出的值一律未轉錄，只看名稱。

### 後續單元對本單元檔案的變更（如實記錄，不屬本單元缺陷）

`git log --oneline 7ce1bee..HEAD -- <source-manifest.json 的 13 個路徑>` 共 21 筆：

```
624c170d 功能(entry-page-ui): U14 大腦入口頁、脈絡列與子頁面大腦面板
8677b7d0 功能(project-pages-ui): U23 專案頁、成員可見性與寫入路徑守門
763a45af 功能(mcp-bridge): U21 MCP bridge 與需求欄位工具
fa8ce421 功能(brain-gateway): U13 大腦 WebSocket 入口與契約增量
6dff4d45 功能(requirement-fields): U20 需求欄位服務與代寫者欄收斂
c2e5687a feat: add script to validate embedding provider values during deployment
c3d9ef8f 文件(local-dev): 補完 cli 模式退役的同步，並修掉一個會誤判新舊碼的排錯判準
9781a97a 修正(llm): 移除已退役的 LLM_PROVIDER=cli 模式，消除靜默失敗
369a5468 整合(merge): 併入 ut（含 #683 成本工作區最佳化）
b4f0cdc3 重構(a3): Assessment Review/Lens 改走 LangGraph 並修正串流 state
5fd8f14f 功能(cost): 上傳前工作負載表單並送交 AI 建議
c282a88a 整合(merge): 將 origin/ut 併入 c1-workspace-optimize
f06dd1e7 整合(deps): 併入 ut（含 #678 LangGraph 遷移），並修正相容改寫指向未安裝的驅動
b6ed2390 fix(env): 在 backend/.env.example 補充 DESIGN_LLM_MODEL 並優化 validate_env_contract 的目錄排除
4b589eb5 修正(deps): 以 psycopg v3 ＋ 顯式 driver 根治，移除 sqlalchemy<2.1 釘版
fd4d8ea1 Merge remote-tracking branch 'origin/danniel/fix/postgres-driver-psycopg3' into danniel/docs/orchestration-brain-ideation
4194cd28 修正(database): 自動相容 postgresql 連線字串的 psycopg2 驅動
bc4eb69d 修正(deps): psycopg stub 補上 __version__，並記載驅動升級的本機步驟
c80aba97 修正(deps): PostgreSQL 驅動改用 psycopg v3，並以 URL 顯式指定不依賴隱含預設
9e141456 功能(hierarchy-data): projects／systems／diagram_change_records 三表與一次性遷移
74ed2cc5 功能(cost): 官方估價教學彈窗與目錄 SKU 規格描述
```

需特別記下的三處語意變動：

1. **`--maxmemory-policy` 已由 `allkeys-lru` 改為 `noeviction`**（`git log -S noeviction` 指向 `c2e5687a`；compose 註解引 `NFR4.50`／`[N3]=A`）。Step 6 第四格依原交付形狀（`command:` 含 `--appendonly yes`＋`--maxmemory`＋policy 旗標）勾回，**但 policy 值已被後續決定改變**。本單元 `traceability.json` 的 `AC2.1.4` 註記與第 1 節故事追溯表仍寫 `allkeys-lru`，屬過期敘述；本輪依指示不改寫既有產出，記於此處。容量本身是第 18 項，歸 `session-store`。
2. `render-env.sh` 與兩份 `.env.example` 由後續單元加入 `EMBEDDING_TIMEOUT_SEC`、`BRAIN_SESSION_HISTORY_MAX` 等變數（同出自 `c2e5687a`），使計畫引用的行號全部位移；七個本單元變數與其守門判準不變，本單元兩支測試仍綠。
3. deploy compose 多了第七個服務 `mcp-bridge` 與 `mcp` 網段（`internal: true`，U21），`traceability.json` 的「服務集合差集 `{cloudflared, ollama}`」與 `S-9` 的「deploy 六個服務」計數因此已非現況；`cloudflared` 仍只在 `edge`，D-3 的核心判準不受影響。**`mcp` 網段的明文往返屬合併前必修 #7，本單元的網路分段不處理 encryption**（review-03 R-05 補）：本單元的分段控制只處理 network exposure（誰能連到誰、誰對外），不提供傳輸加密；使用者 JWT 在 `mcp` 網段以明文往返的殘餘風險，由 #7 的人工裁決（2026-10-24，`mcp-bridge` 計畫 §八，記為對「本機迴環或加密」的例外）承擔，不得讀成已由本單元覆蓋。

另：`c2e5687a` 的 commit 訊息為英文 `feat:`，不符 `team.md` 的中文 type 規則；非本單元產生，僅記錄。

### 本輪副作用

執行測試會重新產生 `backend/**/__pycache__` 與 `backend/.hypothesis`（本輪未設 `PYTHONDONTWRITEBYTECODE=1`）。依本檔第六節所述，若之後要登記本站審查收據，須在跑測試**之後**才記 `REVIEW_REQUESTED`。

### Step 11 第三格補勾（conductor，`2026-10-20T06:22:00Z`）

使用者裁決以獨立環境解決版本不符：建立 `backend/.venv`（已在 `.gitignore`），以 `backend/.venv/bin/pip install -r backend/requirements.txt` 照釘選安裝（含 `mcp==2.3.0`），系統 Python 與依賴舊版 `mcp` 的 `claude-agent-sdk` 不受影響。在該環境重跑 `backend/.venv/bin/python -m unittest discover -s tests`（`backend/`）：`Ran 1204 tests` → `OK`，上述 28 個 `mcp_bridge` 失敗消失。Step 11 第三格據此勾回，計畫 43／43 完成。之後各單元的完整測試一律以 `backend/.venv/bin/python` 執行。

## 重做（Code Generation 自頭重來，2026-10-24）

因審查收據過期（SOURCE_REVIEW_STALE），使用者選擇 Code Generation 自頭重來；本單元計畫於 `2026-10-24T22:01Z` 前後重新核可。本輪**未改動任何應用程式碼**：developer 逐步對照現行程式驗證 15 個步驟，全部判定 verified、無 fixed，後續單元的刻意改動（deploy.yml、compose、`DEPLOY.md`、`LOCAL-DEV.md`）保留不動。

- 單元專屬測試（`backend/`，`HYPOTHESIS_STORAGE_DIRECTORY=<scratchpad>/hyp PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_vector_extension_bootstrap tests.test_render_env_redis -v`）：`Ran 16 tests … OK`（7＋9）。
- 全套（同前綴，`discover -s tests`）：`Ran 1319 tests … OK (skipped=3)`。本輪以前綴避免產生 `.hypothesis`／`.pyc`，不再有上一節所述的副作用。
- `validate_env_contract.py`、`validate_repo_contract.py`：皆 passed。
- Step 14 secret 複查（只查名稱）：`REDIS_PASSWORD` 在 secrets、不在 variables（variables 僅 `APP_ID`、`GH_AW_DEFAULT_MODEL_COPILOT`），判準成立。
- 與計畫字面不同但保留的兩處（皆既存、有註解理由）：`--maxmemory-policy` 為 `noeviction`（`NFR4.50`／`[N3]=A`）；ACL 置於 redis 的 `command:` 而非獨立 aclfile（aclfile 不做變數內插、repo 為 public），兩個 stack 各自一份。
- `source-manifest.json` 的 13 個路徑與 `traceability.json` 的 46 列經複核仍成立，所有 `OK` 列 target 皆存在；`AC2.1.4` 仍為 Deferred。

## 共用檔異動後重新驗證

時間戳：`2026-10-29T16:18:47Z`（`date -u`）。本節**未改動任何程式、測試或部署資產**。比對基準為本單元最新審查收據 `reviewed-source-549cadcafb78.tsv`（mtime 2026-10-25 06:09，三份收據中最新）。

### 逐檔結論

收據列出 13 個檔，以 `shasum -a 256` 逐檔比對現況：**11 個逐位元相同**（`LOCAL-DEV.md`、兩份 `.env.example`、`backend/database.py`、兩支測試檔、兩份 deploy compose、`render-env.sh`、根 `docker-compose.yml`、`schema_rbac.sql`；mode 亦相同）；**2 個不同**：`.github/workflows/deploy.yml`、`DEPLOY.md`。兩檔工作樹與 `HEAD`（`c6a40f9`）相同，變動全在 `7a50a40`。

收據的兩個雜湊**不等於任何一個已 commit 的版本**（收據建立於 10-25，當時工作樹含之後才併入 `7a50a40` 的部分改動），所以改用「部分套用」證明：取 `624c170`（前一個 commit 版本）到 `7a50a40` 的 diff，以 `difflib` 切成 hunk，窮舉全部子集套回 `624c170`，找出雜湊等於收據的子集。兩檔皆**恰有一個**子集命中，故收據之後的變動就是其補集，**沒有任何來源不明的變動**：

| 檔案 | hunk 數 | 收據＝`624c170` ＋ | 收據之後新增（＝現況與收據的全部差異） | 來源 |
|---|---|---|---|---|
| `deploy.yml` | 8 | hunk 1（`:520` 註解內的行號 `deploy/docker-compose.deploy.yml:258-261` → `:307-310`，屬 `U10` 的「Verify sessions survive a Redis restart」步驟） | hunk 0（`:35-43` deploy job `outputs:` 加 `brain_ws_probe_failed`）、2（`:596` 步驟 6a 加 `id: brain_ws_probe`）、3（`:656-657` rollback job 開頭註解）、4＋5（`:798-805` 「Open a revert PR for the bad merge」的 `if` 改為 `always() && needs.deploy.outputs.brain_ws_probe_failed != 'true'` 與其註解）、6＋7（`:889`、`:944-947` notify 的 env 與「刻意未開」文字） | 合併前必修 **#26(a)**（`entry-page-ui`） |
| `DEPLOY.md` | 19 | 其餘 16 個 hunk | hunk 3（`:729-738`，§2.2.9 U18 節的「誠實的代價」段，改為 `create_all` 會建表、只缺 COMMENT 與 U20 收斂） | 合併前必修 **#24(d)**（`requirement-field-service`） |
| 同上 | | | hunk 17、18（`:2228`、`:2238`，§5.13 入口頁部署後實測：6a 失敗只還原 last-good、不開 revert PR） | 合併前必修 **#26(b)**（`entry-page-ui`） |

**是否觸及本單元**：否。本單元在 `deploy.yml` 負責的是 deploy job 的「Require the secrets that must not default」與 `env:` 的 `REDIS_PASSWORD`（`:80-135`）、「Verify the Redis ACL actually took effect」（`:209`）、「Pull the embedding model into the Ollama volume」（`:259`）、「Probe the data plane through /api」（`:322`），以及 rollback job「Restore the last-good deployment」的 `env:` 與併入探測的健康檢查迴圈（`:682-787`）；上表的新增 hunk 無一落在這些步驟內。revert 步驟的 `if` 改動不讀也不改 `restore` 的 `restored` 輸出，還原 last-good 與本單元的探測照舊對每一種失敗來源執行。本單元在 `DEPLOY.md` 負責 §1.4、§2.2 表與 §2.2.6、§3.3、§5（5.1–5.11）與英文 `### Database` 的 vector 一句；變動落在 §2.2.9（U18）與 §5.13（U14），不在其內。`test_vector_extension_bootstrap.py` 案例 6 讀 `DEPLOY.md` 的兩處 vector 記載，仍綠。

### 回歸（暫存區副本）

副本：以 `rsync` 複製工作樹（排除 `.git`、`node_modules`、`.venv`、`__pycache__`、`.hypothesis`）到 scratchpad 的 `recheck-brain-infra/`，`git init` 後以原 repo 的 `git ls-files -z` 清單重建追蹤集合（3099 檔，與原 repo 逐條相同），供 `validate_repo_contract.py` 的 `git ls-files` 掃描使用。直譯器為工作樹的 `backend/.venv/bin/python`，一律 `PYTHONDONTWRITEBYTECODE=1` ＋ `-B`。執行完已刪除副本；工作樹未新增任何 `.pyc` 或 `.hypothesis` 檔（以 `find -newer` 核對）。

- 單元專屬測試（`backend/`，`-m unittest tests.test_vector_extension_bootstrap tests.test_render_env_redis -v`）：`Ran 16 tests … OK`（7＋9）。
- 全套（`backend/`，`-m unittest discover -s tests`）：`Ran 1326 tests in 92.503s` → `OK (skipped=3)`；輸出中的 `ERROR:` 記錄列為測試刻意走失敗路徑的日誌，非測試失敗（`FAIL:`／`ERROR:` 測試標頭 0 筆）。
- `validate_env_contract.py`、`validate_repo_contract.py`：皆 passed（exit 0）。
- 計畫 Step 1–15 逐項重驗仍成立（Step 14 以 `gh api` 只查名稱：`REDIS_PASSWORD` 在 secrets，variables 僅 `APP_ID`、`GH_AW_DEFAULT_MODEL_COPILOT`；Step 15：`traceability.json` 46 列＝40 OK／2 Deferred／4 N/A，`upstream_ids` 與列集合一致，OK 列 target 全存在；`source-manifest.json` 13 路徑全存在）。與計畫字面不同的兩處沿用上一節的記載（`noeviction`、ACL 置於 `command:`），本輪無新增偏離。

## 重新驗證審查（review-03）五項文件修正的處置（2026-10-29T22:23:17Z）

- **R-01**：計畫 Step 6 第四格就地標註 `noeviction` 取代 `allkeys-lru`（見計畫該格）。
- **R-02**：`traceability.json` 的 AC2.1.4、S-8、S-9 三列 note 已追加 HEAD `c6a40f9` 的實查（deploy 7 個服務、記憶體上限 deploy 7 ＋ test 4 共 11 項、policy `noeviction`）。
- **R-03（review-04 R-07 改寫，2026-10-29T22:48:06Z）**：`unit-test-instructions.md` **現已直接修正**（第三節兩處命令改為 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B`、補「直譯器與快取」說明段、第四節標題改為「規劃 6 個；實作 7 個」「規劃 5 個；實作 9 個」、第五節補實作合計 16），由 conductor 在第三次重開的計畫修訂階段（核可**之前**）完成，開發者以 `grep` 核對屬實（:43、:58 兩處 `.venv/bin/python -B`；:66、:80 兩處實作數；:46、:99 合計 16）。上一輪不改的**真正原因**：Plan Approval 綁定的是計畫、測試說明（`unit-test-instructions.md`）與 Testing Contract 三者的內容，核可**之後**改其中任一份都會讓核可失效、之後一切 shell 指令都會被擋；`traceability.json` 與 `code-summary.md` 不在綁定範圍內，計畫的勾選（`- [ ]` → `- [x]`）也不計入，所以上一輪能改那兩份檔、能勾計畫，卻不能改說明檔。上一輪計畫 R-03 格被勾成「已改檔」與事實不符（review-04 R-06），正確做法是在核可之前的計畫修訂階段改，本輪即如此。以下替代命令與實數保留作為交接紀錄，現與說明檔一致：
  - 本單元專屬命令：`cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest tests.test_vector_extension_bootstrap tests.test_render_env_redis -v`
  - 全套：`cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests`
  - 理由：本機 PATH 無 `python`；系統 `python3` 的 `mcp` 為 1.29.0（釘選 2.3.0），全套會有與本單元無關的失敗；`-B` 與 `PYTHONDONTWRITEBYTECODE=1` 避免 `.pyc` 改變來源指紋。
  - 測試數實數（`grep -c 'def test_'`）：`test_vector_extension_bootstrap.py` **7**（說明檔寫 6）、`test_render_env_redis.py` **9**（說明檔寫 5，審查未點到），合計 16。
- **R-04**：見上方「跨單元落點」表。
- **R-05**：見「後續單元對本單元檔案的變更」第 3 點末句。
- **收尾**：`python3 scripts/validate_repo_contract.py` → passed。

## 審查 review-04 四項修正的處置與第三次重開的勾選重驗（2026-10-29T22:48:43Z）

本節**未改動任何程式、測試、部署資產或 `unit-test-instructions.md`**；只改本檔、`traceability.json`（I2 一列 note）與計畫的勾選。查驗基準 HEAD `c6a40f9`。

### 四項修正

- **Major（review-04 R-06，計畫 R-03 格勾選不實）**：`unit-test-instructions.md` 現況以 `grep` 核對屬實——`.venv/bin/python -B` 兩處（:43、:58）、`實作 7 個`（:66）、`實作 9 個`（:80）、實作合計 16（:46、:99）；兩支測試檔 `grep -c 'def test_'` 為 7 與 9。該檔變動由 conductor 於核可前完成（`git diff --stat` 為 `+7 −5`）。計畫上一節 R-03 格據此勾回。
- **Minor（R-07，R-03 理由不一致）**：已改寫上一節「R-03」條，寫明綁定範圍（計畫、測試說明、Testing Contract 三者內容；勾選與 `traceability.json`、本檔不在其內）與「核可之前改」的正確做法。
- **Minor（R-08，I2 note 漏改）**：`traceability.json` 的 I2 列 note 末尾已追加「截至 HEAD `c6a40f9` 實查：deploy 7 個服務、記憶體上限共 11 項」。數字以 `grep -n 'memory:'` 實查兩份 compose：deploy 7 項（:77、:182、:323、:364、:386、:411、:454）、test 4 項（:73、:137、:184、:201）。之後以腳本掃全部 46 列 note 的舊形式（「六個 deploy」「6 個服務」「十個服務」「deploy 六」「六個服務」「6 個 deploy」）：命中只剩 S-8（「十個服務」「deploy 六」）與 I2（「六個 deploy」），兩列皆已帶「截至 HEAD」標註並註明上文為交付當時敘述，無其他殘留。`json.load` 可解析。
- **Minor（R-09，勾選數與摘要矛盾）**：說明如下節。

### 重開會重設計畫勾選；本輪勾回的數量

引擎在本單元重開時會把計畫全部勾選重設為未勾，所以計畫的勾選狀態在任何一次重開後的那段時間內都與本檔的查驗摘要不一致；**勾選結果以本節為準**。本輪開工時計畫有 55 格未勾（`grep -c '^- \[ \]'`）、0 格已勾；逐格以讀檔／`grep`／實跑核對後全部勾回，現況 `grep -c '^- \[x\]'` 為 **55**、`grep -c '^- \[ \]'` 為 **0**。計畫唯一的改動是 55 處 `- [ ]` → `- [x]`。

55 格的組成：「共用檔異動後的重新驗證與補審」2 格、「review-03 五項」5 格、「review-04 四項」5 格、「三、實作步驟」Step 1–15 共 43 格。

**仍未勾的格：0。** brief 提到的「第 291 行附近原本就刻意未勾的那格（本機 6a 類項目）」在現行計畫中不存在：第 291 行是第四節逐層適用表的 `Environment/build configuration` 列，非勾選格；計畫全部勾選格都在 :44–:280 之間，其中沒有 6a 類項目（6a 屬 `entry-page-ui` 的部署後實測，見本檔「共用檔異動後重新驗證」表 #26）。上一輪摘要「勾回 42、未勾 1」的那一格是 Step 11 第三格（全套 unittest），已於 `2026-10-20T06:22:00Z` 補勾，本輪重跑仍全綠。

### 逐步查驗（本輪實查，行號為現況）

| 格 | 結果 | 依據 |
|---|---|---|
| 共用檔異動 重新驗證 | 勾回 | 以 `sha256` ＋ mode 逐檔比對兩份收據：對 `reviewed-source-549cadcafb78.tsv` 為 11 同、2 異（`deploy.yml`、`DEPLOY.md`，來源已於「共用檔異動後重新驗證」節以 hunk 子集證明）；對最新收據 `reviewed-source-47672a01e28d.tsv`（review-04 用）**13 個檔全部相同**，review-04 之後無任何本單元檔變動 |
| 共用檔異動 回歸 | 勾回 | 見下方「回歸」 |
| review-03 R-02／R-04／R-05／收尾 | 勾回 | AC2.1.4、S-8、S-9 三列 note 含「截至 HEAD」；跨單元落點表與第 3 點末句存在；validator 綠 |
| review-03 R-03 | 勾回 | 見上方 Major |
| review-04 五格 | 勾回 | 見上方四項；收尾見下方 |
| Step 1 | 3／3 | `backend/.venv/bin/python` 存在且跑得起 unittest；說明檔第三節有本單元專屬命令（:43）；兩支 validator 執行 exit 0 |
| Step 2 | 2／2 | `schema_rbac.sql:63` `CREATE EXTENSION IF NOT EXISTS vector;`；`backend/database.py:89` `_ensure_vector_extension()` 在 `:90` `create_all()` 之前 |
| Step 3 | 2／2 | 測試檔 7 個 `def test_`，實跑綠（見下方） |
| Step 4 | 3／3 | `deploy/render-env.sh:75` 必填檢查、`:92` `$` 擋阻名單含 `REDIS_PASSWORD`、heredoc `:131–137` 寫出七個變數（六個字面值 ＋ `REDIS_PASSWORD=${REDIS_PASSWORD}`） |
| Step 5 | 2／2 | 測試檔 9 個 `def test_`，實跑綠 |
| Step 6 | 6／6 | `backend.environment:` 七個變數無 `:-`（`:117–123`）；`redis`（`:184`）／`ollama`（`:325`）服務、`edge`／`internal` 網段、`db_pg18`／`redis_aof`／`ollama_models` 三個 volume、全服務 `logging:` 與 `memory:`、`redis`／`ollama` 的 `healthcheck`（`:309`、`:345`）與 `restart: unless-stopped`（`:188`、`:337`）、backend 兩條 `depends_on`（redis `service_healthy`、ollama `service_started`）；redis `command:` 含 `--appendonly yes`（`:256`）、`--maxmemory 256mb`（`:258`）與 `--maxmemory-policy`（`:273`，值 `noeviction`）——依該格註記，勾選只代表旗標存在，**不代表 `allkeys-lru` 成立**；ACL 以 `command:` 的 `--user`（`:290`、`:296`）承載；`cloudflared` 只在 `[edge]`（`:406`） |
| Step 7 | 2／2 | test compose：backend 有 Redis 三者與 `EMBEDDING_PROVIDER` 預設 `stub`；redis 有自己的 `--user` ACL（`:160`、`:166`）；無 `ollama` 服務、無 `--appendonly`／`--maxmemory`、redis 無具名 volume；`restart:` 只有 redis（`:143`）；backend `depends_on` 只有 db 與 redis；db 映像 `pgvector/pgvector:pg18`；四個服務皆有 `memory:` 與 `logging:` |
| Step 8 | 2／2 | 根 `docker-compose.yml:17` 為 `pgvector/pgvector:pg18`；無 `logging:`／`networks:`／`memory:`，`ports:` 保留 |
| Step 9 | 2／2 | 七個變數在 `deploy/.env.example` 與 `backend/.env.example` 各以 `^KEY=` 出現 1 次 |
| Step 10 | 4／4 | 探測步驟 `:322`（401 為通過，`:353`）；rollback 迴圈以 `restored=` 寫 `$GITHUB_OUTPUT`（`:726`、`:786`），`:740–790` 的 `exit` 只出現在註解；`git blame` 確認 `7ce1bee` 在三處 `env:` 只新增 `REDIS_PASSWORD`（`:84`、`:121`、`:693`），`OPENROUTER_API_KEY`（`:85`）出自 `fa8ce42`；`ollama pull` 步驟 `:259` 以 `exec -T` 並區分「拉取失敗但模型已在」與「不在」兩情形（`:291`、`:293`） |
| Step 11 | 3／3 | 兩支 validator 綠；全套 unittest 綠（見下方） |
| Step 12 | 3／3 | `DEPLOY.md:236` §2 表列 vector、§2.2.6（`:290`）、§5.1–5.11（`:1531`–`:2128`）；英文 `### Database`（`:2294`）有 vector 一句；英文半部其餘未擴大 |
| Step 13 | 3／3 | `LOCAL-DEV.md:23` 硬依賴表、H4（`:140`，含 `pg_available_extensions` 檢查 `:157`）、H5（`:167`，`postgres_data` 跨大版本處置） |
| Step 14 | 3／3 | `gh api …/actions/secrets` 名稱含 `REDIS_PASSWORD`（1 筆）；`…/actions/variables` 名稱僅 `APP_ID`、`GH_AW_DEFAULT_MODEL_COPILOT`，`REDIS_PASSWORD` 0 筆；從未存為 variable，重新產生金鑰的條件未觸發。只讀名稱，未讀值 |
| Step 15 | 3／3 | `source-manifest.json` 13 個路徑全部存在；`traceability.json` 46 列（OK 40／N/A 4／Deferred 2），`upstream_ids` 與列集合一致，OK 列的 9 個不同 target 全部存在；本檔存在 |

### 回歸（暫存區副本）

以 `rsync` 複製工作樹（排除 `.git`、`node_modules`、`.venv`、`__pycache__`、`.hypothesis`）到 scratchpad 的 `rev04-brain-infra/`，直譯器為工作樹的 `backend/.venv/bin/python`，一律 `PYTHONDONTWRITEBYTECODE=1` ＋ `-B`，`HYPOTHESIS_STORAGE_DIRECTORY` 指向副本內。

- 單元專屬（`-m unittest tests.test_vector_extension_bootstrap tests.test_render_env_redis`）：`Ran 16 tests in 0.498s` → `OK`。
- 全套（`-m unittest discover -s tests`）：`Ran 1326 tests in 90.976s` → `OK (skipped=3)`，exit 0，`FAIL:`／`ERROR:` 測試標頭 0 筆。
- 兩支 validator 於工作樹以 `python3 -B`（`PYTHONDONTWRITEBYTECODE=1`）執行：皆 passed。以 `find -newer` 核對，工作樹未新增任何 `.pyc` 或 `.hypothesis` 檔。副本已刪除。

**處置紀錄（`2026-10-29T22:49:49Z`）**：review-04 新發現 1 Major ＋ 3 Minor 全數處置；計畫勾選 55／55（`grep -c '^- \[x\]'`）；`python3 scripts/validate_repo_contract.py` → passed（exit 0）；`traceability.json` 以 `python3 -I` 的 `json.load` 驗證可解析。

## 合併前必修：共用檔集中修正的處置（2026-10-31 Request Changes；本節逐格 append，開始於 `2026-10-31T16:44:20Z`）

所有測試、突變只在 scratchpad 的實體副本 `bi-copy/` 執行（`rsync` 自工作樹，排除 `.git`／`node_modules`／`.venv`／`__pycache__`／`.hypothesis`／`dist`／`test-results`／`*.tsbuildinfo`；`node_modules` 取自 `a11y-copy` 的實體複本，副本內無指向 repo 的絕對 symlink）。後端一律 `backend/.venv/bin/python -B -P`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=<副本>/backend`、`HYPOTHESIS_STORAGE_DIRECTORY=<副本>/backend/.hypothesis`。突變只施加在**副本**的檔案上，repo 檔案從未被改成突變版；每次突變後重新 `rsync` 還原副本並複跑綠，並比對 repo 檔 `sha256` 前後相同、副本與 repo 逐位元相同（執行器：scratchpad 的 `bi_mut.py`）。

### A1（第 20／29 列，記憶專用資料庫角色）——**停下回報，本格未改任何檔**

計畫要求「密碼以 `psql -v` 變數由部署端帶入，不寫進 SQL」，並把 `CREATE ROLE` 放進 `schema_rbac.sql`。查證後此機制與 `schema_rbac.sql` 的**兩條既有執行路徑都衝突**，屬計畫明文的「角色建立與既有 `schema_rbac.sql` 重跑語意衝突」，依指示停下、不自行決定：

1. **空 volume 路徑**：`deploy/docker-compose.deploy.yml:55` 與 `deploy/docker-compose.test.yml:57` 把本檔掛進 `/docker-entrypoint-initdb.d/01-schema_rbac.sql`。官方映像以 `psql -v ON_ERROR_STOP=1` 執行 `.sql`，**無法傳入自訂 `-v` 變數**；未定義的 `:'memory_db_password'` 會原樣留在 SQL 中成為語法錯誤，而本檔是單一交易（檔頭「本檔是**單一交易**（BEGIN … COMMIT）」）→ 整個交易中止，一張表都不會建。
2. **既有環境路徑**：`backend/scripts/run_meta_schema_migration.py:95` `BLOCKS_TO_RUN = ("X", "I", "J")`，它以 SQLAlchemy 直接執行 `I)` 區塊的文字（`:26`「直接解析 `schema_rbac.sql` 的 `X)`／`I)`／`J)` 三個區塊並執行同一份文字」）——psql 變數與 `\gexec` 等 meta-command 在這條路徑都不存在。
3. 另外，psql 不在 dollar-quote（`DO $$ … $$`）內做變數內插，故現有 `I)` 區塊（`schema_rbac.sql:548-566`）的 DO 形狀也無法直接承載密碼。

需要使用者裁決的設計點（建議項僅供參考，未採行）：(A) `schema_rbac.sql` 只以 DO 區塊冪等建立**無密碼**的 `LOGIN` 角色與 grant／`REVOKE`（兩條路徑都可執行），密碼另由部署端設定——空 volume 用 `/docker-entrypoint-initdb.d/` 下一支讀 `MEMORY_DB_PASSWORD` 環境變數的 `.sh`，既有環境由 `deploy.yml` 一個 `psql -v` 步驟執行 `ALTER ROLE … PASSWORD :'pw'`；(B) 角色與密碼完全移出 `schema_rbac.sql`，由獨立腳本建立（`schema_rbac.sql` 只保留 grant，但角色不存在時 grant 失敗，需另處理順序）；(C) 其他。另一項連帶事實：記憶專用 session 能否「讀不到 `public` 任一表」取決於 memory-service 的查詢是否 join `public.users`／`project_members`（可見範圍判定），屬 memory-service 單元，裁決前宜一併確認。

`MEMORY_DB_PASSWORD` 名稱查證（`gh api repos/opendiamonds/cloud-360/actions/secrets --jq '.secrets[].name'`，只列名稱、未讀值）：secrets 為 `AIDLC_SYNC_TOKEN APP_ENV APP_PRIVATE_KEY COPILOT_GITHUB_TOKEN JWT_SECRET KIWI_TCMS_PASSWORD KIWI_TCMS_URL KIWI_TCMS_USERNAME N8N_WEBHOOK_URL OPENROUTER_API_KEY POSTGRES_PASSWORD REDIS_PASSWORD SLACK_BOT_TOKEN`——**`MEMORY_DB_PASSWORD` 尚未存在**；variables 為 `APP_ID GH_AW_DEFAULT_MODEL_COPILOT`（亦無）。

### A2（第 21 列，獨自一人的專案不擋停用）——完成

- `backend/services/membership_service.py`：`projects_losing_last_admin` 新增「還有其他成員」查詢（`:640` `projects_with_others`），回傳條件改為 `:660` `project_id in projects_with_others and not qualified[project_id]`；docstring 更新判準、獨人專案理由與查詢次數。**為完成本格必要的連帶修改**：`reselect_for_project` 在「無候選且無其他成員」時記 `reselect_skipped reason=no_other_members` 並回 `None`（`:1022`；新增 helper `_has_other_members` `:970`）——不改的話守門放行後改選會拋 `NoQualifiedSuccessor`，停用端點對已正確停用的帳號回 500（首跑實測即此狀況）。
- 既有測試依新規則修改（皆為原本以「獨人專案」當 deny 夾具的案例；未把新案例加進共用檔）：`test_membership_endpoints.py` 的 `test_E6`（計畫點名）與 `test_E3`（計畫未點名，但同一前提，不改即紅）各先邀一位不合格成員 carol；`test_membership_facade.py` `test_F2` 同；`test_membership_data.py` `test_M7` 的參照實作加「有其他成員」條件、(4) 加不合格成員、新增 (5) 獨人專案不擋（該檔出現在 membership-service 與 project-pages-ui 兩份 manifest，屬共用檔）。
- `DEPLOY.md` 刪除使用者小節新增「停用的前置條件——獨自一人的專案不擋」段。
- 新測試 `backend/tests/test_membership_lone_owner.py`（3 個）：預設獨人專案停用 200 → 刪除 200（專案、系統隨之清除）；另有不合格成員時停用 409 且 `is_active` 未寫；非預設獨人專案停用 200、刪除 409（`owned_projects`）。
- 實跑：相關 7 支（hierarchy／membership／user_delete）`Ran 104 tests` → `OK`。
- 突變：M1 拿掉放行條件 → 案例 1、3 紅；M2 守門一律放行（`if False`）→ 案例 2 紅；M3 拿掉改選的 `no_other_members` 略過 → 案例 1、3 紅。三者還原後皆綠，`membership_service.py` repo `sha256` 前後皆 `921ea8fe45f0a445…`（A6 改動同檔後會變，屆時另記）。

### A4（第 27、28 列的 `user_router.py` 與 `DEPLOY.md` 部分）——完成

- `backend/services/user_router.py`：新增 `_UserPurgeSummary`（`:559`）；`_purge_empty_default_projects`（`:577`）回傳實際刪除筆數；`_hard_delete_user`（`:611`）回傳摘要（`:684`）、docstring 記載預檢到 commit 無鎖的競態；兩處 `_audit_append`（`:1043`、`:1258`）結果欄寫入「連帶清除空預設專案 N 筆、系統 N 筆、需求欄位值 N 筆」；規則 2 的 409 `detail` 附 `_DELETE_BLOCKED_NEXT_STEP`（`:358`、`:656`）。（行號為本格完成時；A8 改同檔後見 A8 段。）
- `DEPLOY.md`：§2.2.7 寫明結束碼 2（呼叫方式錯誤、未執行任何事）；刪除使用者小節新增稽核筆數、409 下一步提示、無鎖競態三段。
- 新測試 `backend/tests/test_user_delete_audit_counts.py`（4 個）；與既有 `test_user_delete_hierarchy`、`test_system_account_protection` 合跑 `Ran 20 tests` → `OK`。
- 突變：M1 刪除端點稽核拿掉筆數 → 案例 1、3 紅；M2 拒絕端點同 → 案例 2 紅；M3 409 拿掉提示 → 案例 4 紅；M4 需求欄位筆數固定 0 → 案例 1、2 紅。還原後皆綠，`user_router.py` repo `sha256` 前後皆 `1246b2f70ae0b0ac…`。
- 交接（非共用檔、留在 hierarchy-data）：第 28 列 (a) `run_hierarchy_migration.py` `main()` docstring 的結束碼 2、(b) `MigrationCounts` docstring 的低報說明。

### A3（第 25 列，刪除專案／系統要求 `project_admin`）——完成（`2026-10-31T16:51:45Z`）

**可達性查證結論：可達。** 建立者可被降為一般成員：
- `backend/services/membership_facade.py:339-402` `change_role`：`:364-366` 的 `_require_project_role(..., admin=True)` 只要求**呼叫者**是管理者，不排除目標是擁有者；`:377-382` `assert_still_has_admin` 只要求變更後仍有 ≥1 位管理者；`:383` `set_member_role` 直接改寫。故「另一位管理者把建立者降級」與「建立者在另有管理者時自我降級」都成立（既有 `test_membership_facade.py` `test_F2` 的 allow 側即建立者自我降級；新測試案例 1、2 以 HTTP `PATCH` 由 bob 降級 alice）。
- 其餘改寫成員列的入口**不會**降級建立者：邀請 `membership_service.add_member`（`:855-859`）對已是成員者拒絕，不改寫既有列；自動改選 `reselect_for_project`（`:1009` 起）只把接手人升為 `project_admin`（`:1068`），不降任何人；`remove_member` 會刪除建立者的成員列，但那條路徑已由可見性守門處理（被移出的建立者看不到專案 → 404，既有 `test_project_write_guard.py` 的 removed_owner 案例）。

**改動**：
- `backend/services/hierarchy_facade.py`：新增 `PROJECT_ADMIN_REQUIRED_DETAIL`（`:98`）與 `HierarchyProjectAdminRequired(HierarchyForbidden)`（`:101`，轉 403，router 唯一轉譯點不必改）；`delete_project`／`delete_system` 新增必填注入參數 `project_admin: Callable[[int], bool]`，在擁有者檢查**之後**判定（`:343`、`:380`）——非擁有者仍得 404，既有回應形狀不變；本模組照舊不 import 成員關係符號（`BR87.3`）。
- `backend/services/membership_service.py`：新增 `can_administer_project`（`:430`）。
- `backend/services/membership_facade.py`：新增 `project_admin_check`（`:552`），回傳注入用閉包。
- `backend/services/hierarchy_router.py`：兩個刪除端點傳入 `project_admin=...project_admin_check(principal)`。
- `backend/tests/test_hierarchy_service.py`：8 處直呼 facade 的 `delete_project`／`delete_system` 補上 `project_admin=ALWAYS_VISIBLE`（必填參數的機械性跟進，判定語意未改）。

**一處需要使用者知悉的等價條件**：計畫寫「同時要求呼叫者為該專案 `project_admin`」，第 25 列 (b) 允許「依查證結果定出的等價條件」。`can_administer_project` 的成立條件是「角色為 `project_admin`」**或**「該專案沒有任何成員列且呼叫者是擁有者」。第二支只在回填（後端啟動時自動執行）之前出現，與可見集合的「擁有者那一半」同一條件；不加它會讓既有已核可的 `test_project_write_guard.py` (c) 案例（`@purpose 回填未跑時，擁有者仍能刪除自己的空專案`）轉紅，那是改變既有決定而非本列要修的缺陷。被降級的建立者有成員列，不走這一支。若使用者認為零成員列的擁有者也應被擋，需另行裁決並修改 (c) 案例。

**測試**：新檔 `backend/tests/test_project_delete_requires_admin.py`（4 個：降級建立者刪專案 403 且資料不變、刪系統 403、仍為管理者的建立者刪系統與專案 204、非擁有者管理者仍 404）。與 `test_project_write_guard`、`test_hierarchy_service`、`test_project_visibility_static`、三支 membership 測試合跑 `Ran 109 tests` → `OK`。

**突變**：M1 `delete_project` 拿掉檢查 → 案例 1 紅；M2 `delete_system` 拿掉 → 案例 2 紅；M3 `can_administer_project` 對有成員列者一律 False → 案例 3（allow 側）紅；M4 拿掉零成員列擁有者分支 → `test_project_write_guard` 的 (c) 兩案紅。全部還原後綠；`hierarchy_facade.py` repo `sha256` 前後皆 `770b8034592bcfc3…`，`membership_service.py` 前後皆 `7a10aaeca5f14a66…`。

**交接**：project-pages-ui 的 `code-summary.md` 十二節第 1 項揭露文字須依本結論同步（第 25 列 (d)；該檔屬 project-pages-ui 單元，本輪不改）。

### A6（第 31 列共用檔部分）——完成（`2026-10-31T17:01:30Z`）

- (a) `backend/services/membership_service.py` `admin_count_after`（`:458`）改為 join `users`、只數通過 `is_qualified_successor` 的管理者（`:508`，含 `_cache`）；docstring 記載理由與查詢次數。
- (e) 新增 `assert_can_be_promoted_to_admin`（`:519`），沿用同一謂詞，不合格回 `MissingGlobalPermission`（422，`reason` 區分「帳號已停用」「帳號尚未通過授權核准」或角色不足）；`membership_facade.py` `change_role` 在 `previous_role != project_admin` 且目標為 `project_admin` 時呼叫（`:392`）。
- (f) `membership_facade.py` `_authorize_global`（`:101`）加 `principal.is_approved`（`:118`）；`list_my_pending_reselections`（`:617`）與 `acknowledge_reselection`（`:634`）各補 `_authorize_global(principal, "view")`（`:629`、`:639`）。
- (b) `DEPLOY.md` §2.2.10 開頭框拿掉「`owner_user_id` 指向不存在的使用者」的歸因，改為依終檢剩餘數與 `INSERT` 例外判斷（說明 `projects.owner_user_id` 有外鍵，該原因不可能成立）。
- (c)(g) `DEPLOY.md` §2.2.10 新增「成員守門的兩個前提」小節（`:1077`）；`schema_rbac.sql` `J)` 區塊 `project_members` 之前加同義註解（`:595`，**純 `--` 註解、無 DDL／COMMENT ON 變更**，故不觸發 schema 同步規則；`run_meta_schema_migration.py` 解析該區塊的哨兵不受影響，全套測試已涵蓋）。
- 既有測試的必要跟進（原本把只有 `K3.view` 的 carol 升為管理者，(e) 起被拒）：`test_membership_endpoints.py` `test_E2`、`test_membership_facade.py` `test_F6`／`test_F8` 先把 carol 的**資料庫**全域角色改為持 `K3.edit`（principal 於 setUp 鑄造，不受影響）；`test_F5` 末段 alice 的管理動作由「升 carol 為管理者」改為「移出 carol」並斷言已移出（驗的仍是 alice 未被覆寫、仍能執行管理動作）。
- 新測試 `backend/tests/test_membership_eligibility_guards.py`（8 個）：(a) 另一位管理者停用時自我降級 409、待核准時自我移出 409、合格時自我降級 200；(e) 升只有 `K3.view` 者 422、升待核准者 422、升合格者 200；(f) 待核准 principal 直呼 facade 被 `MembershipForbidden` 擋、改回核准後成功；無 `K3` 者呼叫橫幅兩方法皆被擋、有 `K3.view` 者照常。
- 實跑：與 membership／hierarchy／project 相關 8 支合跑 `Ran 114 tests` → `OK`。
- 突變：M1 管理者計數不看合格 → (a) 兩個 deny 案紅；M2 拿掉升任檢查 → (e) 兩個 deny 案紅；M3 拿掉 `is_approved` → (f) 待核准案紅（以 ERROR 呈現：未被全域層擋下後於後續步驟拋出其他例外，仍為紅）；M4 拿掉清單方法的全域判定、M5 拿掉 acknowledge 的全域判定 → 橫幅案紅。全部還原後綠；`membership_service.py` repo `sha256` 前後皆 `a9b00ca070a510fb…`，`membership_facade.py` 前後皆 `8574ed36315d565b…`。
- 交接（非共用檔）：第 31 列 (b) `membership_backfill.py:28-29` docstring 的孤兒擁有者歸因（membership-service）；(d) `AdminPage.tsx:172` 停用失敗不更新該列、不顯示 `failed_project_ids`（前端 admin 頁，計畫明文留在所屬單元）。

### A5（第 30 列）——完成（`2026-10-31T17:29:49Z`）

- (b) `backend/scripts/run_meta_schema_migration.py`：`EXPECTED_FK_DELETE_ACTIONS`（`:202`）由 3 條擴為 `J)` 區塊的全部 7 條，鍵加入**欄名**（`project_id`／`user_id`／`invited_by`／`promoted_user_id`／`previous_owner_user_id`／`system_id`／`updated_by`），核對查詢 join `pg_attribute` 以 `conkey` 比對欄位，錯誤訊息帶 `schema.table.column`。
- (a) `backend/scripts/verify_meta_schema.sql`：新增 `P17`（`:279`，`system_requirement_fields` 恰為 9 欄）；檔頭補 `P17` 與總數 17；(c) `P5` 註解「8 欄」更正為 9 欄。
- (c) `.github/workflows/ci.yml`：`memory-schema` job 註解「12 條／P1-P16」改為 17 條／P1-P17，`:383` 的歸屬改為「P1–P12 U18、P13／P14 U19、P15／P16 U20、P17 第 30 列」，步驟名稱改為 `(P1-P17)`（步驟名不是 check name，不影響 branch protection）；`DEPLOY.md` §2.2.9 的結束碼語意「3 條外鍵」→「7 條外鍵（逐欄核對）」、「全部 16 條斷言」→ 17 條並補歸屬、「本節的 `P1`–`P12`」→ `P1`–`P17`。
- 測試（計畫未列檔名，依「每個行為改動附測試」新增）：`backend/tests/test_meta_schema_expectations.py`（2 個）——以腳本自己的 `extract_blocks` 解析 `J)` 區塊，斷言 `EXPECTED_FK_DELETE_ACTIONS` 恰等於該區塊全部 `REFERENCES`（含欄名與 CASCADE／NO ACTION）；`P17` 的 N、`J)` 的欄位行數、`EXPECTED_TABLES` 三者皆為 9。實跑 `OK`。
- 突變：M1 刪 `invited_by` 列 → 案例 1 紅；M2 `system_id` 期望改 `a` → 案例 1 紅；M3 拿掉 `P17` 的標記 → 案例 2 紅。還原後綠，sha256 前後相同（`run_meta_schema_migration.py` `37d504ea…`、`verify_meta_schema.sql` `a3e1d937…`）。
- **未驗**：`P17` 與 7 條外鍵的實際查詢只在 CI 的真實 PostgreSQL job 執行，本機不連 DB，**未實跑**；本機只驗了清單與 DDL 一致。

### A7（第 32、34、36、37 列的 `DEPLOY.md` 文字）——完成

- §2.2.11：新增「併入 `main` 後的首次煙霧測試就是那一次 `dry_run=true`，失敗即停用排程」（32 (f)）與「併入 `main` 當天必有一則假的『清除逾期』issue」的三項辨識條件（標題前綴、原因句、建立時間早於第一次排程 run 且尚無 `event=schedule` 的 run）與處置（第一次排程成功後手動關閉；監看者只去重不自動關閉）（32 (d)）。依據：`memory-retention-watchdog.yml` 的 `cron "23 6 * * *"`、`state=never` 分支與 `ISSUE_TITLE_PREFIX`；`memory-retention-purge.yml` 的 `cron "41 17 * * *"`。
- 容量表：`≈ 308.8` 那一列標明 695,400 B 是**序列化位元組下界**、不含 key／欄位配置開銷並假設配置器開銷近零（多約 3% 即跌破 300），並要求 staging 首次部署以 `MEMORY USAGE <key> SAMPLES 0` 實量（34 (g)）；新增「追加一則訊息的成本」列：`append_message.lua` 每次重編整段、最多約 200 KB、滿段約 3 ms／次、未計入 `NFR3.40`（34 (b)）。
- 容量表註腳：Redis 大版本升級後須重跑 `test_work_orchestrator_capacity.py` 與 `tests_redis/` 的工作項 Lua 測試，理由是 `cjson_encoded_size` 重現的是 Redis 內附 cjson 的跳脫規則（36 (c)）。
- 懸空引用：「`U13` code-summary 第 4.5 節」改為 `U13 brain-gateway` code-summary 第八節「揭露事項」的 `OPEN-GW13-6` 列（實查該檔：無 4.5 節，第八節表格第 252 行為 Cloudflare 透傳未實測）（37 (c)）。
- 本格為純文件，無可執行行為，故無測試與突變。

### A8（第 33 列共用檔部分）——完成，`query` 上限一項**停下回報**

- (a) `backend/services/memory_facade.py`：新增 `MemoryUserReferenceCounts`（`:109`）與 `count_references_to_user`（`:519`）；`backend/services/user_router.py` 移除 `MemoryRecord`／`MemoryAuditEvent` 匯入，改 `from services.memory_facade import MemoryFacade`（`:52`），預檢在 `:475` 經 facade 取兩類筆數，迴圈接受預先算好的整數。**取捨**：兩條計數查詢寫在 facade 內（以 ORM model 直接查），而不是下放到 `memory_service.py`——後者非共用檔、計畫明文留在 memory-service 單元；若該單元偏好分層一致，可把這兩條查詢移入 `memory_service.py` 並由 facade 委派（行為不變，交接清單已列）。
- (b) `backend/services/memory_errors.py:51` `MemoryError` 更名為 `MemoryServiceError`（三個子類別、`__all__` 同步），`memory_facade.py` 匯入與 `__all__` 同步。**全 repo 引用實查**：`grep -rn '\bMemoryError\b'` 在應用程式碼只命中這兩支檔，intent-router 與 memory-page-ui 所屬檔**零引用**（計畫列出的「含 intent-router 與 memory-page-ui 所屬檔」以實查為準：無需改動）。不保留別名（保留即仍遮蔽內建）。
- (e) `backend/services/memory_router.py`：`MEMORY_CONTENT_MAX_CHARS = 4000`（`:101`），`MemoryCreateRequest.content` 加 `max_length`（`:127`）→ 超過回 422；`openapi.json` 重 dump（`content` 多 `maxLength: 4000` 與描述）、`frontend/src/types/api.d.ts` 重產（只有描述一行變），皆於副本產生後複製回 repo，副本 `npm run check:types` → 「API 型別檔與規格檔一致」。
- (e) **`query` 上限停下回報**：查證結果與計畫前提不符——`memory_router.py` **沒有**任何帶 `query` 的端點（檔內「本檔有五條路由，不是六條」明文不為 `search` 開端點）；`query` 只存在於同進程的 `MemoryFacade.search`，呼叫端是 `intent_routing.py:226` 與 `brain_gateway.py:1707`（入口頁預取）。在 facade 拒絕超過 4000 字元的 `query` 會改變這兩個呼叫端對長訊息的行為（拋 `MemoryInvalidInput` 而非檢索），屬新的設計決定（拒絕、截斷或由呼叫端先截），需使用者裁決；本輪未改。
- (g) `.github/workflows/ci.yml:627` 步驟名改為 `Run real-PostgreSQL tests (membership C1-C4, memory V1/D1-D2, purge atomicity, requirement field G1-G4)`（實查 `backend/tests_pg/` 四支檔的 `def test_`）。
- 新測試：`backend/tests/test_memory_input_limits.py`（4 個：常數為 4000、恰 4000 字元 201、4001 字元 422 且未寫入、中文 4000／4001 的字元計數邊界）；`backend/tests/test_memory_reference_counts.py`（4 個：`user_router.py` 不 import 兩個記憶 model〔ast〕、刪除預檢經 facade 且 409 帶記憶筆數〔spy〕、facade 回兩類筆數、`MemoryServiceError` 不遮蔽內建且兩模組皆無 `MemoryError`）。與 `test_user_delete_hierarchy`、`test_user_delete_audit_counts` 合跑 `Ran 21 tests` → `OK`。
- 突變：上限 M1 拿掉 `max_length` → 4001 兩案紅；M2 上限 3999 → 4000 三案紅；計數 M1a 重新 import 記憶 model → ast 案紅；M1b 預檢改回直接 ORM、不經 facade → spy 案紅；M2 facade 記憶列數固定 0 → 兩案紅；M3 補回 `MemoryError` 別名 → 更名案紅。全部還原後綠，各檔 repo `sha256` 前後相同（`memory_router.py` `4b521634…`、`user_router.py` `2f68a1a6…`、`memory_facade.py` `db83e67b…`、`memory_errors.py` `378b16be…`）。

### A9（第 34 列共用檔部分）——完成

- (a) `backend/services/session_store.py`：`SESSION_ROLE_MAX_CHARS = 32`（`:153`），`append_message` 在 `:317` 拒寫超長 `role`（`ValueError`，只帶長度不帶值；拒絕而非截斷）。
- (h) `_ensure_meta` docstring（約 `:626`）更正：沒有任何方法會補上 `meta.userId`（`set_work_target` 也不寫）；本模組改寫 `meta` 時只把它原樣帶過（`_write_meta_and_expire`）。審查原文「無讀取端」與實查不完全一致（`_write_meta_and_expire` 與 `session_types` 會讀出再寫回），故文字寫成「原樣帶過、沒有寫入端給它非 null 值」。
- (d)(e)(f)(i) `.github/workflows/deploy.yml`：「placed LAST」改為如實描述（在資料面探測、公開網址與 mcp-bridge 紀錄之後，但步驟 6a 在它之後）；ACL 驗證與重啟還原兩步驟改以 `docker compose exec -T -e REDISCLI_AUTH=…` 帶密碼並先 `::add-mask::`，不再以 `--pass` 出現在 redis-cli 的命令列（註解寫明：`-e KEY=VALUE` 仍會出現在自架 runner 主機端的 `docker compose exec` argv，此暴露接受）；`hgetall | sort` 改為逐欄位 `snapshot()`（欄位名＋值同列，外加 `hlen`），能抓到兩欄位值互換；`:520` 一帶的引用改為 `docker-compose.deploy.yml:309-314`（實查該段即 healthcheck 區塊）。
- 新測試 `backend/tests/test_session_role_limit.py`（3 個：恰 32 字元可寫、33 字元拒寫且 FakeRedis 無任何寫入指令〔附對照：合法追加確實被同一過濾器看見〕、300,000 字元被擋）；與 `test_session_store_behaviour` 合跑 `Ran 62 tests` → `OK (skipped=3)`（3 個 skip 為既有的真實 Redis 案例）。
- 突變：M1 拿掉長度檢查 → 兩案紅；M2 上限 31 → 32 字元案紅。還原後綠，`session_store.py` repo `sha256` 前後皆 `d70c5330…`。
- `snapshot()` 以 Homebrew bash 5 對假的 hash 模擬一次（scratchpad `snap_sim.sh`）：舊的 `hgetall | sort` 對兩欄位值互換**未偵測**，新 `snapshot()` 偵測到。`deploy.yml` 本身**未實跑**（需要部署 stack 與 runner）；`REDISCLI_AUTH` 搭配 `--user` 的行為以 redis-cli 文件為據，首次部署即驗。
- 交接：session-store 的計畫 9.3 須依 (d) 修正後重勾（第 34 列 (d) 原文）；(c) `test_session_store_behaviour.py:1357`、`:1360` 的長 key 去值斷言、(j) session-store 的 `unit-test-instructions.md` 與 code-summary 改寫——皆屬 session-store 單元檔，本輪不改。

### A10（第 35 列 (c)、第 40 列 (a)(d)(i)）——完成

- `frontend/src/components/Sidebar.tsx:248`「我的記憶」`<nav>` 補 `aria-label="我的記憶"`；`frontend/src/pages/MemberDetailPage.tsx:284` `<h2 id="member-detail-role-heading">`、`:292` 角色下拉改 `aria-labelledby` 指向它；`frontend/src/components/brain/ContextBar.tsx:111` 連線中骨架 `role="img"` → `role="status"`。
- `frontend/tests/e2e/a11y.spec.ts`：原 27 個 test 中缺 `@note` 的 12 個（03、04、06、08、11、12、13、14、15、16、17、22）補上；第 21、22 點的 `@story US9.2` 保留；新增掃描點 `26-member-detail-invalid-project`（網址 `projectId` 為 `not-a-number`，就緒為 `member-detail-error` 含「查不到這個專案」、排除「載入中…」與角色下拉）與 test「26 成員詳情頁專案編號非數字」；掃描點數註解與過期檢查的說明由 24 改為 25。現況：28 個 test、28 個 `@note`（`grep -c`）。`a11y-baseline.json` **未變動**（`git diff` 空）。第 15 點 `@note` 所稱「焦點管理由 member-pages.spec.ts 承擔」已查證（該檔 `:987` 移出確認對話框焦點案例）。
- 新 e2e `frontend/tests/e2e/sidebar-landmarks.spec.ts`（2 個：名為「我的記憶」的導覽地標恰一個且包住連結；入口／專案／我的記憶三個 `<nav>` 名稱皆非空且互不相同；兩案皆斷言無未攔截的 `/api` 請求）。
- 副本驗證：`npm run lint` → 0 errors、2 warnings（既有 `exhaustive-deps`）；`npm run check:types` → 一致；`npm run build` → 成功；`vite preview`（`:4199`）上跑 `a11y`、`memory-page`、`member-pages`、`project-pages`、`sidebar-landmarks` 五支 → `91 passed`。
- 突變（副本改檔 → 重建 → 跑 → 還原 → 重建 → 跑；執行器 scratchpad `fe_mut.py`）：M1 拿掉 `aria-label` → sidebar 兩案紅；M2 改成與「專案」同名 → 兩案紅；M3 `aria-labelledby` 指向不存在的 id → a11y 第 10 點紅；M4 `invalidProjectId` 固定 false → a11y 第 26 點紅。全部還原後綠，repo 檔 `sha256` 前後相同。

### A11（第 38 列 (a)）——完成（CI 安裝未驗）

- `backend/requirements.txt:78-79` 加 `sse-starlette==3.0.3`、`mcp-types==2.3.0`（版本取自 `backend/.venv/bin/python -m pip show`），附理由註解。`pip check` → `No broken requirements found.`。
- **未驗**：CI 的 `pip install -r requirements.txt` 需要網路，本機不連網，未實跑；首次 CI 即驗。
- **為完成本格必要的連帶修改**：全套首跑時 `test_mcp_bridge_static.py` 的 `test_route_a_single_exact_pin` 紅——它以 `^mcp\b` 取「mcp 的釘選行」，而 `\b` 會把 `mcp-types==2.3.0` 也算進來。改為 `^mcp(?![-\w])`（只取 `mcp` 本身）並加註解；突變「再加一行 `mcp==2.3.1`」→ 該案仍紅，還原後綠。此檔屬 mcp-bridge 單元（不在共用檔清單），但不改即無法讓 A11 的既有套件保持綠。
- 未做突變：拿掉 `sse-starlette`／`mcp-types` 的釘選**沒有任何測試會紅**（釘選不是可執行行為；CI 安裝本身才是驗證）。

### A12（驗證，實體副本）——完成（CI 才有的 PostgreSQL job 未驗）

- 後端全套（副本，`-B -P`、`PYTHONDONTWRITEBYTECODE=1`、`HYPOTHESIS_STORAGE_DIRECTORY` 在副本）：`Ran 1358 tests in 92.873s` → `OK (skipped=3)`，exit 0（首跑 1 個 FAIL 即上述 `test_mcp_bridge_static`，修正後重跑全綠）。本單元自身兩支（`test_vector_extension_bootstrap` 7、`test_render_env_redis` 9）包含在內。
- `backend/scripts/dump_openapi.py --check`（副本）→ 「規格檔與後端程式碼一致」。
- 前端（副本、`node_modules` 為依 `package-lock.json` 完整安裝的實體複本）：`npm run lint` 0 errors／2 warnings（既有）；`npm run check:types` 一致；`npm run build` 成功。
- e2e（副本 `vite preview :4199`，全走 `page.route()`）：`a11y`、`memory-page`、`member-pages`、`project-pages`、`sidebar-landmarks` → `91 passed`。
- `python3 scripts/validate_repo_contract.py` → passed；`python3 scripts/validate_env_contract.py` → passed（皆於工作樹以 `-B`、`PYTHONDONTWRITEBYTECODE=1` 執行）。
- **未驗（只在 CI）**：`memory-schema`（含新的 `P17` 與 7 條外鍵的逐欄核對）、concurrency job（`tests_pg/`）、`ui-regression` 的真實 stack；`deploy.yml` 的三項修改（`REDISCLI_AUTH`、`snapshot()`、註解）只能在部署時驗證。
- 工作樹未留下快取或建置產物：以 `find`（排除 `.venv`／`node_modules`／`.git`）查 120 分鐘內的 `__pycache__`、`.hypothesis`、`dist`、`*.tsbuildinfo`、`test-results`、`pw-report.json`、`junit.xml` → 0 筆。（`backend/tests_pg/__pycache__` 與 `frontend/dist` 存在，但 mtime 為 10-07／10-27，早於本輪，非本輪產物，未動。）

### A13（收尾）——`2026-10-31T17:45:42Z`

**本節改動的應用檔（33 個，已補入 `source-manifest.json`，現共 46 筆）**：`.github/workflows/{ci,deploy}.yml`、`DEPLOY.md`、`schema_rbac.sql`（純註解）、`openapi.json`、`backend/requirements.txt`、`backend/scripts/{run_meta_schema_migration.py,verify_meta_schema.sql}`、`backend/services/{hierarchy_facade,hierarchy_router,membership_facade,membership_service,memory_errors,memory_facade,memory_router,session_store,user_router}.py`、`backend/tests/{test_hierarchy_service,test_mcp_bridge_static,test_membership_data,test_membership_endpoints,test_membership_facade}.py`（既有測試的必要跟進）、新測試 8 支（`test_membership_lone_owner`、`test_project_delete_requires_admin`、`test_user_delete_audit_counts`、`test_meta_schema_expectations`、`test_membership_eligibility_guards`、`test_memory_input_limits`、`test_memory_reference_counts`、`test_session_role_limit`）、前端 `Sidebar.tsx`、`brain/ContextBar.tsx`、`MemberDetailPage.tsx`、`types/api.d.ts`、`tests/e2e/a11y.spec.ts`、新 e2e `tests/e2e/sidebar-landmarks.spec.ts`。

**超出計畫明列範圍、需 conductor 知悉的四處**：(1) `backend/services/hierarchy_router.py` 不在共用檔清單，但 A3 的注入判定必須由 router 傳入；(2) `backend/tests/test_mcp_bridge_static.py` 屬 mcp-bridge，A11 不改即紅；(3) 新測試多了兩支——`test_memory_reference_counts.py`（計畫「計數走門面的測試」未給檔名）與 `test_meta_schema_expectations.py`（A5 依「每個行為改動附測試」新增）；(4) `test_membership_endpoints.py` 除計畫點名的 `test_E6` 外，`test_E3`、`test_E2` 也需跟進，另 `test_membership_facade.py`（F2、F5、F6、F8）、`test_membership_data.py`（M7）、`test_hierarchy_service.py`（8 處呼叫）——全部是新規則下原夾具不再成立的機械性跟進，未在共用測試檔加入新案例。

**停下回報、未完成的兩項**：A1（第 20／29 列，記憶專用資料庫角色——密碼承載方式與 `schema_rbac.sql` 兩條執行路徑衝突；`MEMORY_DB_PASSWORD` 尚不存在於 repository secrets）；A8 的 `query` 上限（`memory_router.py` 無 `query` 端點，只有同進程的 `MemoryFacade.search`，限制方式需裁決）。兩者登錄於 `traceability.json` 的 `OPEN-MB20-ROLE`、`OPEN-MB33-QUERY`。

**交接給各所屬單元（本輪不改）**：
- memory-service：記憶表存取改用記憶專用 session（待 A1 裁決後才有 session 可用）；第 33 列 (c) 讀取過濾 `expires_at`、(d) 拒絕日誌的 `memory_id` 注入、(f) facade 重拋分支測試；可選：把 `count_references_to_user` 的兩條查詢下放到 `memory_service.py`。
- membership-service：第 31 列 (b) `membership_backfill.py:28-29` docstring 的孤兒擁有者歸因。
- 前端 admin 頁（所屬單元）：第 31 列 (d) `AdminPage.tsx:172` 停用失敗不更新該列、不顯示 `failed_project_ids`。
- hierarchy-data：第 28 列 (a) `run_hierarchy_migration.py` `main()` docstring 結束碼 2、(b) `MigrationCounts` docstring 的低報說明。
- project-pages-ui：第 25 列 (d) code-summary 十二節第 1 項揭露文字依 A3 結論同步。
- memory-purge：第 32 列 (a)(c)(e)（哨符副本、核准入口突變、workflow 檔頭行號）；(b) 另開 issue。
- session-store：第 34 列 (c) 長 key 去值斷言、(j) 單元紀錄改寫、(d) 修後重勾計畫 9.3。
- work-orchestrator：第 36 列 (a) Lua 取捨註解、(b) 修剪後再送停掉的案例、(c) 真實 `cjson.encode` 比對案例、(d) code-summary 措辭。
- brain-gateway：第 37 列 (a) merge-blockers 第 19 列狀態字（conductor）、(b) 部署測試、(d)(e) 單元紀錄。
- mcp-bridge：第 38 列 (b) 設計檔取代註記、(c) 405 案例、(d) NUL bridge e2e。
- memory-page-ui：第 35 列 (a)(b) 焦點處理。
- a11y-gate：第 40 列 (b)(c)(e)–(h) 單元紀錄更正。
- conductor：第 2 列 (b)、第 17 列狀態字更正（計畫明文由 conductor 處理）。

**計畫勾選實算**：引擎重開本單元時把計畫勾選全部重設為未勾（本輪開始時 `grep -c '^ *- \[x\]'` 為 0、`- [ ]` 為 68）。逐格以證據重勾：Step 1–15 與前三節共 55 格（證據為本節 A12 的全套測試、兩支 validator、`gh api` 只列名稱〔`REDIS_PASSWORD` 在 secrets、不在 variables〕，以及上一輪「逐步查驗」表所列行號的現況重查——`schema_rbac.sql:63`、`backend/database.py:89-90`、`render-env.sh:75`、deploy compose `:256`／`:273`、兩份 compose 的 `pgvector/pgvector:pg18`、兩份 `.env.example` 的變數、`deploy.yml` 的探測／ollama／`restored=`／三處 `REDIS_PASSWORD` env；`unit-test-instructions.md` 的 `.venv/bin/python -B`（3 處）與「實作 7／實作 9」），本節 A2–A7、A9、A10、A12、A13 共 10 格。**未勾 3 格**：A1（停下回報）、A8（`query` 上限停下回報，其餘子項已完成）、A11（釘選已完成，但格內「CI 安裝驗證」本機無法執行）。最終 `grep -c` 見下行。

**處置紀錄（`2026-10-31T17:45:42Z`）**：`validate_repo_contract.py`、`validate_env_contract.py` 皆 passed；`traceability.json` 增 16 列（`MB-20`、`MB-21`、`MB-25`、`MB-27`–`MB-38` 共 12 列、`MB-40`）與兩個 open item，現 `upstream_ids` 62／`coverage` 62，`python3 -I` 的 `json.load` 可解析；計畫勾選 65／68（未勾 3）。

## 使用者裁決後補做 A1 與 A8 的 `query` 上限（`2026-10-31T23:19:56Z`）

**裁決來源**：conductor 轉達，使用者於 `2026-10-31T23:00:19Z` 前後逐題裁決：
- **A1（第 20／29 列）＝「SQL 建角色，部署另設密碼」**：`schema_rbac.sql` 以可重跑寫法（DO 區塊判斷 `pg_roles`）建 `cloud360_memory`，不帶密碼、不含 psql 變數，只授 `memory`、撤銷 `public`；密碼由部署流程在 schema 套用之後以 `ALTER ROLE … PASSWORD` 設定，值來自 secret `MEMORY_DB_PASSWORD`；test compose 以內嵌測試值設定。
- **A8 `query`＝「facade 內截斷到 4000 字元」**：`MemoryFacade.search` 收到超過 4000 字元的 `query` 時只取前 4000 字元做 embedding 與搜尋、不報錯；兩個呼叫端不改。
- A11 的 CI 安裝驗證：維持未勾，理由見 A11 段（本機不連網）。

上文 A1 段「停下回報」與 A8 段「`query` 上限停下回報」為當時的狀態，**已由本節取代**（不回改上文，保留決策經過）。

### A1——完成

- `schema_rbac.sql`：`I)` 區塊 BR1.2 段新增 `DO $$ … IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cloud360_memory') THEN CREATE ROLE cloud360_memory LOGIN; …`（`:596`），之後是 `GRANT USAGE ON SCHEMA memory`、兩表 DML、序列 `USAGE, SELECT`、兩條 `ALTER DEFAULT PRIVILEGES IN SCHEMA memory`、`REVOKE ALL ON ALL TABLES/SEQUENCES IN SCHEMA public`、`REVOKE CREATE ON SCHEMA public` 與 `COMMENT ON ROLE`（`:611`）。全段無 psql 變數、無 meta-command，故 initdb（`psql -f`）與 `run_meta_schema_migration.py`（DBAPI cursor、無參數 `execute`）兩條路徑都可執行。原有對 `current_user` 的授權保留（現行 `memory_service.py` 用的帳號），說明改寫為「它不構成邊界」。檔頭涵蓋清單補 `I)` 列與兩條驗證查詢。
- `deploy/initdb/02-memory-role-password.sh`（新檔，755）：密碼的**唯一**實作。擋空值與 `$`，查不到角色時明說要先跑 `run_meta_schema_migration.py`，以 psql `\getenv` 從環境讀密碼、`ALTER ROLE cloud360_memory WITH LOGIN PASSWORD :'memory_db_password'`，密碼不出現在容器內任何命令列，也不被印出。
- `.github/workflows/deploy.yml`：三處 `env:`（必要 secret 檢查、render-env、rollback 的 render-env）加入 `MEMORY_DB_PASSWORD`；必要 secret 檢查加入它與說明；新步驟「Set the memory-only database role password」位於「Build and start the stack」之後，先 `::add-mask::`，等 `pg_isready`，再以 `docker compose exec -T -e MEMORY_DB_PASSWORD=… db bash -s < deploy/initdb/02-memory-role-password.sh` 執行（主機端 argv 的暴露與 `REDISCLI_AUTH` 同屬已接受的暴露，註解寫明）。
- `deploy/render-env.sh`：`MEMORY_DB_PASSWORD` 列入必填檢查、`$` 擋阻名單、heredoc 輸出與檔頭變數表。
- `deploy/docker-compose.deploy.yml`：backend `MEMORY_DB_PASSWORD: ${MEMORY_DB_PASSWORD}`（無 fallback）。`deploy/docker-compose.test.yml`：db 與 backend 皆有 `MEMORY_DB_PASSWORD: ${MEMORY_DB_PASSWORD:-test_memory_db_password_not_for_production}`，db 掛載 `./initdb/02-memory-role-password.sh` 為 initdb 的 `02-`（排在 `01-schema_rbac.sql` 之後）。`docker compose -f deploy/docker-compose.test.yml config -q` 解析通過（只解析，未起容器）。
- `deploy/.env.example`、`backend/.env.example`：列出 `MEMORY_DB_PASSWORD=`（空值）並說明。
- `backend/database.py`：`MEMORY_DB_ROLE`、`MemoryDatabaseNotConfigured`、純函式 `build_memory_database_url`（`:63`，換掉使用者與密碼、保留主機／埠／資料庫，裸 `postgresql://` 改 `+psycopg`，空密碼或非 PostgreSQL 回 `None`）、`memory_engine`（`:83`，`create_engine` 不連線）、`memory_db_boundary_enabled`（`:91`）、`get_memory_session`（`:96`，未設定時拋錯，**不退回**擁有者帳號）；`init_db` 在未設定時記一行 WARNING（`:156`）。
- `backend/scripts/run_meta_schema_migration.py`：`I)` 哨兵加入 `CREATE ROLE cloud360_memory LOGIN` 與 public 的 `REVOKE`；後條件加入「角色存在、對 `memory` 有 `USAGE`、讀不到 `public.users`」。
- `backend/scripts/verify_memory_role.sql`（新檔）＋ `.github/workflows/ci.yml` 的 memory-schema job 新步驟「Verify the memory-only role boundary (R0-R3)」：以同一支 script 設定 CI 測試密碼，再**以 `cloud360_memory` 本身連線**斷言 R0（身分正確且非 superuser）、R1（逐表 SELECT 全部 `insufficient_privilege`，且表數 > 0）、R2（`memory` 兩表可寫可讀可刪，交易內 ROLLBACK）、R3（不能在 `public` 建表）。
- `DEPLOY.md` §2.2.8 新增「記憶專用資料庫角色」小節（`:613`）：先前寫法讓邊界看起來已生效的更正、物件與步驟表、誠實現況、**首次部署與既有環境的順序**（既有環境必須在含本變更的部署之前先跑 `run_meta_schema_migration.py`，否則部署步驟會失敗並 rollback）、psql 驗證指令、輪替與回滾；§2.2 表 `I` 列與 §2.2.9 結束碼語意同步。`LOCAL-DEV.md` 新增 H7（本機預設不啟用、啟用步驟與驗證）。
- `backend/tests/test_render_env_redis.py`：基準環境補 `MEMORY_DB_PASSWORD`（必填檢查新增後的必要跟進）。
- 新測試 `backend/tests/test_memory_db_role.py`（7 個）：SQL 形狀（`pg_roles` 包住的無密碼 `CREATE ROLE`、全檔無 psql 變數與 meta-command）；授權只涉 `memory`、三條 `REVOKE` 齊；連線字串組法（含特殊字元密碼往返、SQLite／空密碼回 `None`）；未設定時拋錯不退回；`render-env.sh` 對未設定／空字串／`$`／正常值；密碼 script 拒絕空值與 `$`、只經 `\getenv`、可執行；deploy／CI／兩份 compose 的接線。
- 突變：M1 `CREATE ROLE` 帶 `PASSWORD :'pw'` → 案例 1 紅；M2 拿掉 tables 的 `REVOKE` → 案例 1、2 紅（哨兵同時擋下）；M3 連線字串保留原使用者 → 案例 3 紅；M4 未設定時退回 `SessionLocal` → 案例 4 紅；M5 拿掉 render-env 的必填檢查 → 首跑**存活**（未設定時 `set -u` 本身就會失敗），補上「空字串」案例後紅；M6 拿掉 script 的空值檢查 → 案例 6 紅；M7 拿掉部署步驟的 `::add-mask::` → 案例 7 紅。全部還原後綠，repo 檔 `sha256` 前後相同。
- **未驗（只在 CI／部署）**：角色在真實 PostgreSQL 上的建立、授權與 R0–R3；deploy 步驟實際執行。
- **部署前阻擋**：`gh api …/actions/secrets` 與 `/variables` 只列名稱（`2026-10-31T23:19:56Z`），`MEMORY_DB_PASSWORD` **兩處皆無**——在使用者建立 secret 之前，`deploy.yml` 的必要 secret 檢查會失敗。登錄為 `OPEN-MB20-SECRET`（blocking-before-deploy）。

### A8 `query`——完成

- `backend/services/memory_facade.py`：`MEMORY_QUERY_MAX_CHARS = 4000`（`:111`，列入 `__all__`）；`search` 在授權判定之後、取向量之前截斷（`:339`），docstring 寫明「超出的部分不參與比對」與選截斷不選拒絕的理由。`intent_routing.py`、`brain_gateway.py` 未改。
- 新測試 `backend/tests/test_memory_query_truncation.py`（3 個，以只記錄輸入的 Port 注入）：恰 4000 字元原樣送出；4010 字元不報錯、只送前 4000；4001 個中文字截成 4000 個。
- 突變：M1 拿掉截斷 → 案例 2、3 紅；M2 改成拒絕 → 案例 2、3 紅（ERROR）；M3 上限 3999 → 三案皆紅。還原後綠，`memory_facade.py` repo `sha256` 前後皆 `eae259a0…`。

### A12 重跑（實體副本）

- 後端全套 `Ran 1368 tests in 98.096s` → `OK (skipped=3)`（較前次多 10：A1 的 7、A8 的 3）；`dump_openapi.py --check` 一致。
- 前端 `npm run lint` 0 errors／2 warnings；`check:types` 一致；`build` 成功；e2e（`a11y`、`memory-page`、`member-pages`、`project-pages`、`sidebar-landmarks`）`91 passed`。
- `deploy.yml`、`ci.yml` 以 PyYAML 解析通過，新步驟的 `run` 以 `bash -n` 檢查語法通過；新步驟位於「Build and start the stack」與「Wait for the frontend to answer locally」之間。
- `validate_repo_contract.py`、`validate_env_contract.py` 皆 passed。工作樹 60 分鐘內無 `__pycache__`／`.hypothesis`／`*.tsbuildinfo`／`test-results`／`pw-report.json`／`junit.xml`。

### 收尾

- `source-manifest.json` 增 4 筆（`deploy/initdb/02-memory-role-password.sh`、`backend/scripts/verify_memory_role.sql`、`backend/tests/test_memory_db_role.py`、`backend/tests/test_memory_query_truncation.py`），現 50 筆；`database.py`、`render-env.sh`、兩份 compose、兩份 `.env.example`、`LOCAL-DEV.md` 原已在列。
- `traceability.json`：`MB-20`／`MB-29` 由 `Deferred` 改 `OK`，`MB-33` note 改寫為 `query` 已依裁決完成；`OPEN-MB20-ROLE`、`OPEN-MB33-QUERY` 標為 `closed`；新增 `OPEN-MB20-SECRET`。`json.load` 可解析。
- 交接追加：memory-service 改用 `database.get_memory_session()` 存取記憶表時，須確認其查詢不 join `public` 的表（該角色讀不到 `public.users`／`project_members`）；可見範圍判定若需要 `public` 資料，須在主連線先取得再傳入。
- **計畫勾選實算**：`grep -c '^ *- \[x\]'` = **67**，`- [ ]` = **1**（A11：CI 安裝驗證本機無法執行）。
