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
3. deploy compose 多了第七個服務 `mcp-bridge` 與 `mcp` 網段（`internal: true`，U21），`traceability.json` 的「服務集合差集 `{cloudflared, ollama}`」與 `S-9` 的「deploy 六個服務」計數因此已非現況；`cloudflared` 仍只在 `edge`，D-3 的核心判準不受影響。

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
