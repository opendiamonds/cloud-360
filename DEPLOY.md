# Cloud-360 部署環境設定說明（Deploy README）

> 給要把本專案部署到**另一個環境**（本機／staging／新機器）的人。  
> 前後端分服務部署時，請特別核對 API／CORS／資料庫三塊。  
> **A1 產圖、A3 評核建議、A1↔A3「優化」協作**皆依賴 **OpenRouter**（見第 0 節；映像**不再**內建 Claude Code CLI）。

---

## 中文版

### 0. LLM 執行鏈路（必讀｜本次更新）

產品**不是**直接呼叫 Anthropic 官方 API，而是：

```text
後端 FastAPI
  → LangGraph／LangChain（A1 Design、A3 Review／Lens、cost advice）
    → HTTP：OpenRouter（OPENROUTER_API_KEY）
      → 模型（例：google/gemini-3.7-flash；A1 Design 預設 google/gemini-2.5-flash）
```

| 元件 | 角色 | 缺了會怎樣 |
|---|---|---|
| `OPENROUTER_API_KEY` | 真正計費、出模型回應 | A1／A3／優化 API 回 500 或錯誤訊息 |
| `langgraph`／`langchain-openai` 等 | Python 依賴（`requirements.txt`） | 後端無法 import／相關路由掛掉 |

**仍使用 OpenRouter。** credits／402 等錯誤來自 OpenRouter 額度或 `max_tokens` 預扣。`backend/Dockerfile` **不再**安裝 Node／`@anthropic-ai/claude-code`。

#### 0.1 哪些功能需要 OpenRouter

| 功能 | 程式入口 |
|---|---|
| A1 對話產圖 | `backend/services/design_agent.py` |
| A3 改善建議 | `backend/services/review_agent.py` |
| Offline Lens agent 填答 | `backend/services/wa_lens_engine.py` |
| A3「優化」（Design↔Review） | `backend/services/wa_collab_orchestrator.py` |

離線規則打分／啟發式備援可不靠 LLM；但完整建議與協作優化**必須**有 OpenRouter 金鑰。

#### 0.2 部署與映像

| 部署方式 | LLM runtime | 你要做的事 |
|---|---|---|
| **Docker 映像（建議）** | 純 Python 映像（無 Claude CLI） | `docker compose … --build`；確認 `OPENROUTER_API_KEY` |
| **本機直接跑 uvicorn** | 同上（HTTP 呼叫 OpenRouter） | 設定 `OPENROUTER_API_KEY`（或本機 `LLM_PROVIDER=cli` 僅影響 Design 等仍走 Anthropic 相容環境變數之路徑） |
| **既有容器升級** | 需**重建** backend image（舊 image 可能仍含 Node／CLI，可清掉） | `up -d --build` |

#### 0.3 OpenRouter／token 相關變數（本次更新）

| 變數 | 說明 | 建議 |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter 金鑰 | 各環境專用，勿進 git |
| `ANTHROPIC_BASE_URL` | 預設 `https://openrouter.ai/api` | 通常維持 |
| `ANTHROPIC_AUTH_TOKEN` | 可空；啟動時由 `OPENROUTER_API_KEY` 映射 | 可留空 |
| `ANTHROPIC_API_KEY` | **必須為空** | 避免走 Anthropic 直連 |
| `LLM_MODEL`／`ANTHROPIC_DEFAULT_SONNET_MODEL` | OpenRouter 模型 slug | 例：`google/gemini-3.7-flash` |
| `LLM_MAX_OUTPUT_TOKENS` | Agent 輸出 token 上限（對應 `CLAUDE_CODE_MAX_OUTPUT_TOKENS`） | 預設 `12000`；出現 402 credits 可降到 `8192` |
| `LLM_XML_CONTEXT_MAX_CHARS` | 送入 LLM 的架構 XML 字元上限 | 預設 `32000` |

若 OpenRouter 回 `402 … requires more credits, or fewer max_tokens`：先確認帳戶餘額，並在該環境 `.env` 降低 `LLM_MAX_OUTPUT_TOKENS` 後重啟 backend。

---

### 1. 建議調整的環境變數（.env）

#### 1.1 後端 `backend/.env`

範本：`backend/.env.example` → 複製為 `backend/.env` 後修改。

| 變數 | 本機常見值 | 新環境建議 |
|---|---|---|
| `APP_ENV` | `local` | `staging`／實際環境名（勿用路徑含 `prod`／`production` 的目錄名，見 repo contract） |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/cloud360` | 改成該環境 PostgreSQL 連線字串。**必須保留 `+psycopg` 後綴**——它顯式指定 driver 為 psycopg v3，不寫就退回 SQLAlchemy 的隱含預設，而那個預設會隨版本改變（2.0 是 psycopg2、2.1 是 psycopg）|
| `JWT_SECRET` | 範本預設字串 | **務必更換**成長隨機字串 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 改成**前端實際網址**（逗號分隔，勿結尾斜線）例：`https://app.example.com` |
| `OPENROUTER_API_KEY` | 本機金鑰 | 該環境專用金鑰（勿提交進 git） |
| `ANTHROPIC_BASE_URL` | `https://openrouter.ai/api` | 通常維持；與 OpenRouter 接法一致 |
| `ANTHROPIC_AUTH_TOKEN` | 可空（啟動時可由 OPENROUTER 映射） | 依部署方式填入或留空讓程式映射 |
| `ANTHROPIC_API_KEY` | **必須為空** | 維持空，避免 SDK 走 Anthropic 直連 |
| `LLM_MODEL`／`ANTHROPIC_DEFAULT_SONNET_MODEL` | 範本模型 slug | 依該環境要用的模型調整 |
| `LLM_MAX_OUTPUT_TOKENS` | `12000` | 餘額緊時可降；見第 0.3 節 |
| `LLM_XML_CONTEXT_MAX_CHARS` | `32000` | 大圖面可調，但會影響 token 用量 |
| `N8N_WEBHOOK_URL` | 選填 | 有用動態 icon 再填 |
| `N8N_USER` | 選填 | 存取 n8n webhook 所需之 Basic Auth 帳號 |
| `N8N_PASSWORD` | 選填 | 存取 n8n webhook 所需之 Basic Auth 密碼 |
| `AWS_ACCESS_KEY_ID` | 選填（C1） | 目錄價 IAM 使用者（ADR-0018）；最小權限見 1.1.1；勿 commit 真值 |
| `AWS_SECRET_ACCESS_KEY` | 選填（C1） | 與上成對；空則走公開 Bulk；**不得**把真值寫進版控檔 |
| `AWS_DEFAULT_REGION` | `us-east-1` | Price List／Bulk 端點區域 |
| `COST_PRICING_USE_SDK` | `0`／`auto` | `0`＝偏公開 Bulk；有 IAM 憑證時可 `auto`／`1`（agent 查價，見 ADR-0018） |
| `GCP_BILLING_API_KEY` | 選填（C1） | **有 GCP 圖要真實估價時必填**（Cloud Billing Catalog）；勿 commit |

#### 1.1.1 C1 成本估價（本次 FinOps 部署必讀）

三雲查價行為（ADR-0018）：

| 雲 | 需要的環境變數 | 未設定時 |
|---|---|---|
| **AWS** | 可選 `AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY`（僅 `pricing:GetProducts`、`pricing:DescribeServices`、`pricing:GetAttributeValues`）；可選 `AWS_DEFAULT_REGION` | 無憑證仍可啟動；查價降級公開 Bulk Price List（或略過，見 U5／FR5.10） |
| **GCP** | **`GCP_BILLING_API_KEY`**（Catalog API key，建議綁 Cloud Billing API） | GCP 列無法取得官方價（維持未定價／查價失敗） |
| **Azure** | **不需**額外金鑰 | Retail Prices 公開 API |

Compose／staging 請寫在 **`deploy/.env`**（見 `deploy/.env.example` 的「C1 成本估價」段）；本機 bare-metal 寫在 **`backend/.env`**。  
`ut` 自動部署會由 `deploy/render-env.sh` 從 GitHub Secrets 寫入同名變數——請在 repo Settings → Secrets 新增（皆可選，缺則服務仍須能啟動）：

- `AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY`（目錄價 IAM；**不要**授 Cost Explorer／CUR／帳單類權限）
- `AWS_DEFAULT_REGION`（可選，預設 `us-east-1`）
- `GCP_BILLING_API_KEY`（要估 GCP 圖則必填）

**日誌／錯誤訊息不得含 secret 值**（變數名可出現）。`docker-compose.test.yml` 與 CI **不**注入真密鑰。

**禁止**把真實金鑰寫進 `.env.example` 或 commit 進 git。repo contract 以值樣式 regex 攔 `AWS_SECRET_ACCESS_KEY=`／`GCP_BILLING_API_KEY=` 形賦值（見 ADR-0018 §6）；空值與變數名引用允許。

#### 1.2 前端 `frontend/.env`（build 時注入）

範本：`frontend/.env.example` → 複製為 `frontend/.env` 或在 CI 注入同名變數。

| 變數 | 本機常見值 | 新環境建議 |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | 改成**後端 API 根 URL**（勿結尾斜線）例：`https://api.example.com` |
| `VITE_WS_BASE_URL` | 可不設 | 可不設：會由 API base 自動 `http→ws`／`https→wss`；若 WS 與 HTTP 不同網域再單獨設定 |

建置範例：

```bash
cd frontend
cp .env.example .env
# 編輯 VITE_API_BASE_URL=https://api.example.com
npm ci
npm run build
```

> Vite 變數在 **build／dev 啟動時**寫進前端包；改 `.env` 後需重新 build 或重啟 `npm run dev`。

#### 1.3 前後端對照（必對齊）

```text
前端 VITE_API_BASE_URL  ──►  後端實際對外 URL
前端瀏覽器 Origin       ──►  必須出現在後端 CORS_ORIGINS
前端 WS（自動或 VITE_WS_BASE_URL）──►  後端同一主機的 /api/collab/ws/...
```

#### 1.4 Compose 部署用 `deploy/.env`

範本：`deploy/.env.example` → 複製為 `deploy/.env`（**勿 commit**）。  
與 `deploy/docker-compose.deploy.yml` 搭配；公開站點的 CI 部署會由 `.github/workflows/deploy.yml` 從 secrets 產生此檔。

除資料庫／JWT／`PUBLIC_URL` 外，請一併填入第 0.3 節的 OpenRouter 與 token 上限變數，以及 **第 1.1.1 節的 C1 AWS／GCP 變數**（本次 FinOps 部署）。

範例（寫入 `deploy/.env`，值勿 commit）：

```bash
# C1 — AWS Pricing（可選 IAM 目錄價憑證；空則公開 Bulk）
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
COST_PRICING_USE_SDK=0

# C1 — GCP Catalog（要估 GCP 架構圖時必填）
GCP_BILLING_API_KEY=

# brain-infra（U1）— 七個變數，compose 引用時皆**無 `:-` fallback**，故全部 required。
# 只有 REDIS_PASSWORD 是憑證；其餘六個是固定值，`render-env.sh` 直接寫出。
REDIS_URL=redis://redis:6379/0
REDIS_USER=cloud360
REDIS_PASSWORD=                      # openssl rand -hex 32；**不得含 `$`**
EMBEDDING_PROVIDER=ollama            # ollama｜fastembed｜fulltext｜stub
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_EMBED_MODEL=bge-m3
FASTEMBED_MODEL=multilingual-e5-large
EMBEDDING_TIMEOUT_SEC=10             # 本清單原本漏列它；render-env.sh 一直在寫

# session-store（U10）— compose 引用時同樣**無 `:-` fallback**，故 required。
# 字面值，不是憑證。程式端**刻意無預設**：缺值時 backend 在 startup 拒絕啟動
# （BR3.5），因為把缺值讀成「無上限」會讓單一 Redis key 無上界成長且無聲。
BRAIN_SESSION_HISTORY_MAX=200        # 每段歷程筆數上限；段數上界 3，故總量 3 倍
```

Azure Retail Prices **不需**寫入金鑰。改完後 `docker compose … up -d`（必要時 `--force-recreate backend`）。

**brain-infra 的七個變數少寫任一個，`python3 scripts/validate_env_contract.py` 就紅燈**
（那正是它們刻意不帶 fallback 的用途）。反過來，在 compose 那邊補上 `:-` 不只是「加了
預設值」，是**把這道閘門拿掉**——變數變空字串、服務照常啟動、功能靜默降級。首次部署前
請先讀第 5 節的前置條件（主機加密、磁碟、記憶體、新 secret）。

---

### 2. 資料庫：要建哪些表、預設資料怎麼塞

#### 2.1 建議做法（一支腳本搞定）

**SQL 檔位置（repo 根目錄）：**

```text
schema_rbac.sql
```

補充說明：`aidlc/spaces/default/intents/260802-default/construction/plans/schema-rbac-notes.md`  
（`schema.sql` 僅核心 DDL 參考，**完整新環境請用 `schema_rbac.sql`**。）

執行：

**先看你在哪個環境**——兩種形式不是偏好問題，部署主機上只有第一種能用：

| 環境 | 用哪一種 | 為什麼 |
|---|---|---|
| **部署主機**（`192.168.10.10`，`deploy/docker-compose.deploy.yml`） | **`docker exec` 形式**（下方 A） | `db` 服務**沒有 host port**——整個 deploy stack 只有 `frontend` 發布埠（`deploy/docker-compose.deploy.yml` 的 `ports:`）。這是刻意的暴露面控制，**不要為了讓 `psql` 能連就去發布 5432** |
| **本機開發**，或任何能直連該 DB 的環境 | **`psql "$DATABASE_URL"` 形式**（下方 B） | 本機 PostgreSQL 直接可連 |
| **CI 的 `ui-regression` stack** | **兩種都不用** | `deploy/docker-compose.test.yml` 把本檔掛進 `/docker-entrypoint-initdb.d/`，空 volume 啟動時自動執行 |

**A — 部署主機（容器內，預設走這條）：**

```bash
# <db-container> 可用 `docker compose -f deploy/docker-compose.deploy.yml ps -q db` 取得
docker exec -i <db-container> psql -U postgres -d cloud360 < schema_rbac.sql
```

**B — 本機或可直連 DB 的環境：**

```bash
# 先設好該環境的 DATABASE_URL
# 注意：這一份是給 psql 用的，**不能**帶 `+psycopg` 後綴——psql 不認得該形式。
# backend/.env 裡給應用程式用的那一份才需要 `postgresql+psycopg://`（見上表）。
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DBNAME'

psql "$DATABASE_URL" -f schema_rbac.sql
```

> **下文所有 `psql "$DATABASE_URL" -c "..."` 的驗證指令同理**：在部署主機上請改為
> `docker exec -i <db-container> psql -U postgres -d cloud360 -c "..."`。
> 本檔不在每一處重複這句，只在此處定義一次。

#### 2.2 這支 SQL 會建立的表／欄位

| 區塊 | 物件 | 用途 |
|---|---|---|
| X | **擴充 `vector`（pgvector）** | `CREATE EXTENSION IF NOT EXISTS vector;`，**`BEGIN;` 之後的第一條敘述**。U5 記憶表的 `vector(1024)` 欄位需要它。見 2.2.6 |
| A | `users` | 帳號、角色、啟用狀態 |
| A | `user_diagrams` | 架構圖 XML |
| A | `diagram_shares` | 圖分享（多對多） |
| B | `users.last_opened_diagram_id` | 上次開啟的圖 |
| B | `users.last_activity_at` | **最後活動時間**（UTC，可為 NULL＝從未活動）。見 2.2.3 |
| B | `user_diagram_chats` | 使用者×圖 的聊天紀錄（A4） |
| E | `architecture_reviews` | **A3** Well-Architected 評核結果（分數／發現／建議） |
| E | `wa_lenses` | **A3** Offline Custom Lens 現行標準（具 A3 **審核** 者可編輯） |
| C | `role_permissions` | 角色 × Story 的檢視／編輯／審核 |
| F | **C1 退場** `archive_diagram_cost`／`archive_diagram_cost_line`／`archive_pricing_cache`／`archive_cost_audit_event` | **舊成本表（已 rename；應用零讀寫；≥90 天後另開 chore DROP）** |
| G | **U2 估價上傳** `estimate_sets`／`estimates`／`estimate_line_items`／`estimate_shares`／`estimate_audit_events`／`advice` | **新 `/api/cost/v1` 持久化（Advice 正文屬 U7）** |
| H | **U4 階層** `projects`／`systems`／`diagram_change_records` | **專案 → 系統 → 架構圖 階層的三張新表**。見 2.2.7 |
| H | `user_diagrams.system_id` | **架構圖歸屬的權威來源**（可為空；`ON DELETE RESTRICT`）。**既有環境需另跑一次性遷移指令**，見 2.2.7 |
| I | **U5 記憶層** `memory` schema ＋ `memory.memory_records`／`memory.memory_audit_events`；**U8 新增** `ix_memory_records_embedding_hnsw` | **本 repo 的第一個獨立 schema**（在此之前全樹無 `CREATE SCHEMA`）。含 `vector(1024)` 欄位、`embedding_model`、grant 邊界。見 2.2.8；向量索引（opclass `vector_cosine_ops`）見 **2.2.12** |
| J | **U18 專案中繼資料** `project_members`／`reselection_events`／`system_requirement_fields` | **per-project 成員與角色、改選稽核、系統層需求欄位值**。三張表皆為全新，**無資料遷移**。見 2.2.9 |
| K | **U9 保留系統 actor** `users` 的一列（`SYSTEM.retention-purge`） | **90 天記憶清除的稽核 actor**。不是人、無法登入、零權限。**刪掉它會讓每一次清除的整個交易中止**。見 2.2.11 |
| D | 預設使用者 `admin` | 見下方 |

#### 2.2.4 C1 成本表退場（U3 `legacy-cost-retirement`）

| 表 | 說明 |
|---|---|
| `archive_diagram_cost` | 舊 `diagram_cost` rename；應用**不得**讀寫 |
| `archive_diagram_cost_line` | 舊 `diagram_cost_line` rename；應用**不得**讀寫 |
| `archive_pricing_cache` | 舊 `pricing_cache` rename；應用**不得**讀寫 |
| `archive_cost_audit_event` | 舊 `cost_audit_event` rename；應用**不得**讀寫 |

**保留期**：自本退場合併日起 **≥90 天**；**最早可 DROP 日不早於 2026-12-18**（合併若晚於 2026-09-19 則以合併日 +90 天為準）。到期物理 `DROP` 另開 chore／operation（本 unit 不做自動 DROP）。

**既有環境升級**：後端啟動時 `database._ensure_cost_schema()` 會將仍存在的 live 表 `RENAME TO archive_*`。新環境以 `schema_rbac.sql` 直接建立 `archive_*`（可為空）。**勿**再建立 live 四表。

**合併約束**：本退場須與 U8（新估價工作區 UI）**同批**部署。

驗證：

```bash
psql "$DATABASE_URL" -c "\d archive_diagram_cost"
psql "$DATABASE_URL" -c "SELECT count(*) FROM role_permissions WHERE story_id LIKE 'C1%';"
```

#### 2.2.5 U2 估價上傳表（`estimate-intake-api`）

| 表 | 說明 |
|---|---|
| `estimate_sets` | 上傳批次根；`diagram_id` 純標籤（不 FK、不參與授權）；`is_saved` 為 false 時為分析草稿，需命名儲存後才進歷史；`workload_context_json` 為上傳時選填的工作負載／預算上下文（給 AI 建議） |
| `estimates` | 每雲一列；同 Set 內 `cloud` UNIQUE |
| `estimate_line_items` | 解析明細；`spec_description` 為目錄價 API 查出的規格說明（查不到則空）；機械檢查不落庫 |
| `estimate_shares` | 分享名單 PK `(set_id, user_id)` |
| `estimate_audit_events` | 事件稽核（無金額／原文） |
| `advice` | 建議空殼；`estimate_set_id` UNIQUE／PK；正文屬 U7 |

**既有環境升級**：`database._ensure_estimate_intake_schema()` 於啟動時 `CREATE IF NOT EXISTS`；新環境亦可由 `schema_rbac.sql` 建立。RBAC：`C1`＝上傳與檢視；**已無** `C1h`／`C1r`／`C1o`／`C1b`。

#### 2.2.6 pgvector 擴充（U1 `brain-infra`）

`schema_rbac.sql` 在 `BEGIN;` 之後的第一條敘述是：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**為什麼是第一條**：本檔是**單一交易**（`BEGIN` … `COMMIT`）。`vector` 型別必須在任何
宣告 `vector(N)` 欄位的表被建立之前存在；而伺服器**沒有安裝** pgvector 時，這一行是
`could not open extension control file` 這個**硬 ERROR**，交易一旦中止，之後每一條敘述
都以 `current transaction is aborted` 失敗、`COMMIT` 退化為 ROLLBACK ——結果是**一張表
都沒建**，不論你有沒有要用記憶功能。

**由兩處承載，互補而非二選一**（`NFR6.2`）：

| 承載 | 涵蓋的環境 | 為什麼另一處涵蓋不到 |
|---|---|---|
| `schema_rbac.sql` 的上述敘述 | **空 data volume 初始化**（兩份 compose 都把本檔掛進 `/docker-entrypoint-initdb.d/`）＋**本機 `psql` 手動建庫** | 這兩條路徑都在 backend 啟動**之前**執行 |
| `backend/database.py` 的 `_ensure_vector_extension()` | **既有非空 volume** | 既有 volume 不會重跑 initdb 腳本 |

**`_ensure_vector_extension()` 的呼叫位置是一條硬約束**：它在
`Base.metadata.create_all()` **之前**，與其餘六支 `_ensure_*_schema()` 方向相反（那六支
都在 `create_all()` 之後，因為它們補的是 `create_all` 不會做的 `ALTER`）。放錯邊的後果
不是「少一個擴充」，是 **uvicorn 啟動失敗**（`init_db()` 由 startup 事件同步呼叫），
在 `restart: unless-stopped` 之下變成重啟迴圈。這條順序由
`backend/tests/test_vector_extension_bootstrap.py` 守著。

**映像前置**：三份 compose 的 db 映像皆為 `pgvector/pgvector:pg18`。**基底映像同時由
Alpine（musl）換成 Debian（glibc）**——這不是附帶細節，它就是下面第 5.4 節升版程序需要
處理 collation 的唯一理由。

驗證：

```bash
psql "$DATABASE_URL" -c "SELECT extname, extversion FROM pg_extension WHERE extname='vector';"
# 應有一列。沒有的話先確認伺服器裝得到它：
psql "$DATABASE_URL" -c "SELECT * FROM pg_available_extensions WHERE name='vector';"
```

#### 2.2.7 U4 專案／系統階層表與一次性遷移（`hierarchy-data`）

| 物件 | 說明 |
|---|---|
| `projects` | 階層最上層。`owner_user_id` FK → `users`；`is_default` 為**遷移冪等的承載**，每位使用者至多一列為真（部分唯一索引 `uq_projects_default_per_owner`）。刪除仍有 `systems` 的 Project 會被拒絕（`ON DELETE RESTRICT`） |
| `systems` | 階層中間層。`project_id` FK → `projects`（`ON DELETE RESTRICT`）；`is_default` 每個專案至多一列為真（`uq_systems_default_per_project`——範圍是**專案**，不是擁有者） |
| `user_diagrams.system_id` | **新增欄位，可為空**。架構圖歸屬的**權威來源**；`user_id` 只回答「誰建的」，不回答歸屬。FK → `systems` 且為 `ON DELETE RESTRICT`——刪除 System 時**拒絕刪除**而非把本欄設為 NULL |
| `diagram_change_records` | 架構圖變更紀錄。**本輪只寫不讀**（沒有任何讀取端）。`source` 是封閉列舉、本輪唯一值 `brain_orchestration`；`actor_user_id` **必填**。保存期 90 天、以 `created_at` 為截止欄位（索引 `ix_diagram_change_records_created_at`），**但清除機制本輪尚未落地——這張表實際上不會被清除** |

**「每位使用者至多一組預設專案／系統」不是單一約束**：資料庫只保證「每位使用者至多一個預設專案」與「每個專案至多一個預設系統」。「預設系統一定掛在該使用者的預設專案底下」**沒有任何約束擋住**，它由遷移程序（目前 `is_default` 的唯一寫入端）的執行順序供應。日後若出現第二個 `is_default` 寫入端，這個複合性質就不再自動成立。

##### 前進步驟（既有環境的唯一路徑）

`schema_rbac.sql` **只在空 data volume 執行**（兩份 compose 把它掛進 `/docker-entrypoint-initdb.d/`），所以既有的 `192.168.10.10` **不會**經過它。既有環境取得 H) 區塊的結構與完成資料遷移的唯一路徑是這支指令：

```bash
# 在 backend/ 目錄，且 DATABASE_URL 已指向目標資料庫
cd backend
python scripts/run_hierarchy_migration.py
```

預期輸出（三個計數即 `BR2.6` 要求的進度紀錄）：

```
hierarchy migration 完成：
  處理的使用者數        users_processed       = <持有至少一張圖的使用者數>
  新建的預設專案／系統組 default_pairs_created = <本次新建的組數>
  改寫的架構圖數        diagrams_assigned     = <本次掛入的圖數>
終檢通過：user_diagrams 中 system_id IS NULL 的列數為 0（AC9.1.4）。
```

**結束碼 0 才算成功。** 非零即代表終檢未通過（或 DDL／寫入被拒），此時**不得**繼續部署。指令**不會**以警告帶過失敗——這是刻意的，`backend/database.py` 的六支 `_ensure_*` 補丁全部 `except Exception: logger.warning`，本指令不沿用那個形狀。

指令**可重跑**：DDL 為 `IF NOT EXISTS` 形狀；資料面的冪等判準是 `system_id IS NOT NULL`（已掛好的圖不會被重新指派），預設專案／系統「存在就取用、不存在才建」。第二次跑的預期輸出是 `default_pairs_created = 0`、`diagrams_assigned = 0`，而 `users_processed` 仍為使用者數（它算的是走訪數，不是改動數）。

驗證：

```bash
psql "$DATABASE_URL" -c "\d projects"
psql "$DATABASE_URL" -c "\d systems"
psql "$DATABASE_URL" -c "\d diagram_change_records"

# 不變量（AC9.1.4）：必須為 0
psql "$DATABASE_URL" -c "SELECT count(*) FROM user_diagrams WHERE system_id IS NULL;"

# 每位持有圖的使用者恰好一組預設：兩個 count 應相等，且每一列都是 1
psql "$DATABASE_URL" -c "
  SELECT p.owner_user_id, count(*) AS default_projects
  FROM projects p WHERE p.is_default GROUP BY 1 HAVING count(*) <> 1;"
#   應回 0 列

# 兩個部分唯一索引都在
psql "$DATABASE_URL" -c "
  SELECT indexname FROM pg_indexes
  WHERE tablename IN ('projects','systems') AND indexname LIKE 'uq_%';"
#   應有 uq_projects_default_per_owner 與 uq_systems_default_per_project
```

##### 靜止前置條件（**目前的管線做不到，必讀**）

**遷移期間應用不得接流量。** 理由不是效能而是正確性：遷移進行中若有人透過既有 A1 頁面新建一張圖，那張圖不帶 `system_id`（既有儲存路徑不知道這一欄存在），終檢的計數就不為 0 —— 而那不是遷移的錯，卻會讓部署失敗。

**這個有序窗口目前沒有承載者。** `.github/workflows/deploy.yml:121–124` 是單一個

```
docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env up -d --build --remove-orphans
```

把整座 stack **一次**拉起來，`:126` 緊接著就開始等前端回應。**管線裡沒有任何一點是 db 起來而 backend 沒起來的**，所以容器重建造成的中斷是一個**無序的競爭窗口**，不是這裡需要的有序窗口。不要把它當成靜止已經生效。

在管線補上有序步驟之前，本次遷移請以**手動**方式取得窗口：

```bash
# 1) 只起資料庫
docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env up -d db
# 2) 確認 backend 沒有在跑（應無輸出）
docker compose -f deploy/docker-compose.deploy.yml ps --status running --services | grep -x backend
# 3) 跑遷移（在能連到該 DB 的環境，DATABASE_URL 指向它）
cd backend && python scripts/run_hierarchy_migration.py
# 4) 結束碼為 0 且上述不變量查詢回 0 之後，才把其餘服務拉起來
docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env up -d --build --remove-orphans
```

##### 中途失敗是**合法且可恢復**的狀態

遷移的交易邊界是**逐使用者一個交易**：某位使用者的專案／系統建立與其圖的改寫要麼全成要麼全不成；跨使用者則可留下部分進度。所以中途失敗後資料庫會處在「**部分使用者已遷移**」的狀態。

**這不是壞掉。** 處置方式是找出失敗原因、處置後**重跑同一支指令**——已完成的使用者會被原樣跳過，未完成的會被補上。看到下面這種混合狀態時不要試圖手動修補：

```bash
psql "$DATABASE_URL" -c "
  SELECT (SELECT count(*) FROM user_diagrams WHERE system_id IS NOT NULL) AS migrated,
         (SELECT count(*) FROM user_diagrams WHERE system_id IS NULL)     AS pending;"
```

最常見的失敗原因是殘留列指向不存在的使用者（孤兒圖）。它們不會被遷移處理（遷移只走訪 `users` 裡真的存在的擁有者），因此會被計入殘留而讓終檢失敗——這是刻意的，孤兒列需要人工判斷：

```bash
psql "$DATABASE_URL" -c "
  SELECT d.id, d.user_id FROM user_diagrams d
  LEFT JOIN users u ON u.id = d.user_id
  WHERE d.system_id IS NULL AND u.id IS NULL;"
```

##### 回復程序（`decisions.md` ADR-002／ADR-003 逐字：清空 `system_id` 並刪除新建的 `projects`／`systems` 列）

回復**不需要**刪除欄位或表——`system_id` 可為空，而既有頁面完全不讀它，所以清空即等於回到遷移前的可觀察行為。

**先看一眼會動到什麼，再動手**（這一步不可省略——它是唯一能在變更前發現「使用者已自己搬過圖」的機會）：

```bash
psql "$DATABASE_URL" <<'SQL'
SELECT
  (SELECT count(*) FROM user_diagrams d JOIN systems s ON s.id = d.system_id
     WHERE s.is_default)                                   AS will_be_cleared,
  (SELECT count(*) FROM user_diagrams d JOIN systems s ON s.id = d.system_id
     WHERE NOT s.is_default)                               AS on_user_made_systems,
  (SELECT count(*) FROM systems  WHERE NOT is_default)     AS user_made_systems,
  (SELECT count(*) FROM projects WHERE NOT is_default)     AS user_made_projects,
  (SELECT count(*) FROM diagram_change_records)            AS change_records;
SQL
```

- `on_user_made_systems` **不為 0**：使用者已把圖搬到自建系統上。那些歸屬**不是**遷移的產物，回復不得碰它們——下面的 SQL 也確實不會碰（它只清掛在**預設**系統上的）。
- `user_made_systems` 不為 0：其中若有掛在預設專案底下的，第 3 步會被 `RESTRICT` 擋下，那個預設專案會**留著**並被第 4 步的檢查報出來。這是正確行為，不是失敗。
- `change_records` 不為 0：見下方注意事項 3。

```bash
psql "$DATABASE_URL" <<'SQL'
BEGIN;
-- 1) 只清掛在**預設系統**上的歸屬。使用者搬到自建系統上的圖原樣不動。
--    必須在刪 systems 之前——否則 ON DELETE RESTRICT 會擋住第 2 步。
UPDATE user_diagrams SET system_id = NULL
 WHERE system_id IN (SELECT id FROM systems WHERE is_default);
-- 2) 刪除遷移建立的預設系統。此時它們之下已無圖，RESTRICT 不會擋。
DELETE FROM systems WHERE is_default;
-- 3) 刪除遷移建立的預設專案，但**只刪其下已無任何系統的**。
--    使用者若在預設專案底下自建過系統，該專案留著——硬刪會被 RESTRICT 擋掉並中止整個交易。
DELETE FROM projects p
 WHERE p.is_default
   AND NOT EXISTS (SELECT 1 FROM systems s WHERE s.project_id = p.id);
-- 4) 確認。這四個數**可以不為 0**，各自有明確含義，見下表。
SELECT
  (SELECT count(*) FROM user_diagrams d JOIN systems s ON s.id = d.system_id
     WHERE s.is_default)                               AS still_on_default_systems,
  (SELECT count(*) FROM systems  WHERE is_default)     AS default_systems_left,
  (SELECT count(*) FROM projects WHERE is_default)     AS default_projects_left,
  (SELECT count(*) FROM user_diagrams d JOIN systems s ON s.id = d.system_id
     WHERE NOT s.is_default)                           AS on_user_made_systems;
COMMIT;
SQL
```

第 4 步的四個數怎麼讀：

| 欄 | 應為 | 不是的話代表什麼 |
|---|---|---|
| `still_on_default_systems` | **0** | 第 1 步沒清乾淨——**這是真正的失敗**，不要 `COMMIT`，回報後人工處置 |
| `default_systems_left` | **0** | 第 2 步被擋——同上，真正的失敗 |
| `default_projects_left` | 0 **或**使用者在其下自建過系統的那幾個 | 不為 0 時以 `SELECT p.id FROM projects p WHERE p.is_default AND EXISTS (SELECT 1 FROM systems s WHERE s.project_id = p.id);` 列出來人工判斷。**這是預期內的狀態，不是錯誤** |
| `on_user_made_systems` | 與回復**前**那一次查詢的同名欄位相等 | 不相等代表本程序誤動了使用者的歸屬——**立刻 `ROLLBACK`** |

三個注意事項：

1. **步驟順序不可調換**：`user_diagrams.system_id` 與 `systems.project_id` 都是 `ON DELETE RESTRICT`，先刪 `systems` 會被拒絕。這正是 `BR1.2` 在保護的行為，不是障礙。
2. **只碰遷移的產物**。初版的第 1 步寫成 `WHERE system_id IS NOT NULL`——那會連同使用者自己搬過的歸屬一起清掉，與本節第 2 點的宣稱直接矛盾；而初版第 4 步的檢查跑在那個清空之後，恆為 0，**是一個不可能失敗的檢查**（iteration 1 審查 R-02，Major）。現行版本改以「掛在預設系統上」為範圍，並把檢查拆成回復前後兩次比對。
3. `diagram_change_records` **不在回復範圍內**：本輪它沒有任何寫入端上線（寫入端是後續單元），回復時表應為空。若不為空，那是稽核資料，刪除前須人工確認。另注意 `diagram_id` 是 `ON DELETE CASCADE`——刪除架構圖會連帶銷毀它的變更紀錄，這是已揭露並由人工裁決保留的取捨。

#### 2.2.8 U5 記憶層 schema（`memory-data`）

**本 repo 的第一個 `CREATE SCHEMA`。** 在此之前全樹無 `CREATE SCHEMA`、無
`search_path`（契約 `K-05` 的 `precedent`）。兩張表**刻意不在 `public`**
——`BR1.2` 的 grant 邊界整個作用方式就是「只開放 `memory` schema」，
表落在 `public` 會讓該邊界**完全失效而功能上看不出來**。

| 物件 | 說明 |
|---|---|
| `memory` schema | 獨立 schema，非獨立 database——刻意保留原生跨 schema join（兩表皆參照 `public.users`） |
| `memory.memory_records` | 9 欄。三種 `kind`（`semantic`／`procedure`／`episodic`）共用一張表 |
| `memory.memory_audit_events` | 刪除與可見範圍變更的稽核軌跡。**對 `memory_records` 沒有外鍵**（見下） |

**三件最容易被誤讀的事：**

1. **`embedding` 可為 NULL 是刻意的，不是缺漏。** `EMBEDDING_PROVIDER=fulltext`
   模式下建立的列沒有 embedding，之後不會被向量檢索看到，除非重新 embed。
   把它收緊為 `NOT NULL` 或回填預設值**會破壞該降級路徑**。
2. **`embedding_model` 必填，且相似度檢索必須附它的過濾條件。**
   **同維度不等於同向量空間**——不加這道過濾會讓跨模型檢索回垃圾**且不報錯**
   （`decisions.md` ADR-008）。這是本層唯一**完全靜默**的失敗模式：
   型別、維度、索引、查詢全部正常，只有結果在語意上無意義。
3. **稽核表對記憶表沒有外鍵，這是刻意的（`DG-1`）。**
   `FR4.5` 要 90 天刪除、`FR4.7` 要刪除留稽核；設了外鍵就必須在兩個壞結果中
   選一個而**兩者都違反已核可需求**（`CASCADE` 使 `FR4.7` 在 90 天後失效、
   `RESTRICT` 使 `FR4.5` 無法執行）。代價是 `memory_id` **沒有參照完整性保護**。

**只有 `episodic` 受 90 天保存期約束**（`FR4.5` 逐字），且該 `kind` 的
`expires_at` 由 CHECK 強制必填——清除作業**依 `expires_at` 選列**，
所以 NULL 的 episodic 列永遠不會被選中，漏填的後果是**永久保留且沒有任何跡象**。

稽核事件自身的保存期為 **90 天，以其 `occurred_at` 為鍵**（不隨記憶消失）。
`occurred_at` 有索引，否則清除查詢是全表掃描——而這張表本輪**沒有讀取端**，
不會有人順手建它。

驗證：

```bash
# schema 與兩張表的位置（兩列，table_schema 皆應為 memory）
psql "$DATABASE_URL" -c "SELECT table_schema, table_name FROM information_schema.tables
  WHERE table_name IN ('memory_records','memory_audit_events') ORDER BY 1,2;"

# embedding 的型別應為 vector(1024)
psql "$DATABASE_URL" -c "SELECT format_type(a.atttypid, a.atttypmod)
  FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
  JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='memory' AND c.relname='memory_records' AND a.attname='embedding';"

# 稽核表**不得**有指向 memory_records 的外鍵（應回 0）
psql "$DATABASE_URL" -c "SELECT count(*) FROM information_schema.table_constraints tc
  JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name=tc.constraint_name
  WHERE tc.table_schema='memory' AND tc.table_name='memory_audit_events'
    AND tc.constraint_type='FOREIGN KEY' AND ccu.table_name='memory_records';"

# occurred_at 索引應存在
psql "$DATABASE_URL" -c "SELECT indexname FROM pg_indexes
  WHERE schemaname='memory' AND tablename='memory_audit_events';"
```

CI 的 `memory-schema` job（交付物 `N-2`）會對真實 PostgreSQL 執行
`backend/scripts/verify_memory_schema.sql` 的全部斷言，並**套用
`schema_rbac.sql` 兩次**以驗證可重跑性——「可重跑」只跑一次時永遠是真的。

> 原文寫「全部 12 條斷言」，而該檔之後已被兩個單元擴充：`U9` 加了 `S13`、
> `U8` 加了 `S14`／`S15`（見 2.2.12）。改為不寫死數字，使它不再隨每次擴充
> 而過期。（`S2` 在該檔不存在，是既有的編號空缺，非遺漏。）

**既有非空 volume 的建立路徑尚未定案。** `schema_rbac.sql` 只在空 volume 執行
（掛載為 `/docker-entrypoint-initdb.d/`），而既有環境的演進路徑是
`backend/database.py` 的啟動補丁。記憶 schema 走哪一條**本輪未決**，
部署到既有的 `192.168.10.10` 之前必須先決定。

**`NFR6.1`——episodic memory 的靜態加密由主機層承載（磁碟／LUKS），
不在應用層或資料庫欄位層。** 不選欄位層加密的理由是它會**取消一個已核可的能力**
（密文無法全文檢索，而 `fulltext` 是支援的降級路徑）。

> **本 repo 無法驗證這一項。** 它不是 CI 可檢查的事實（CI 不跑在資料庫主機上），
> 也不是應用層可檢查的事實（PG 看不到底層區塊裝置的加密狀態）。
> 故它是**運維承諾而非閘門**。
>
> **`192.168.10.10` 的目前狀態：未經本 repo 確認。** 部署負責人須在此處
> 填入實際狀態（已啟用磁碟加密／未啟用／不適用）並註明確認日期。
> 留白不代表已加密。

#### 2.2.9 U18 專案中繼資料三表與一次性結構建立（`project-meta-data`）

per-project 成員與角色、改選稽核、系統層需求欄位值。**三張表皆為全新、沒有既有資料
要搬**（契約 `K-15` 的 `observable_side_effects` 逐字「不含任何資料寫入」）——這是它
與 2.2.7 的 `U4` 最大的差別：那裡有資料遷移與靜止前置條件，這裡沒有。

| 物件 | 說明 |
|---|---|
| `project_members` | 6 欄。per-project 成員身分與角色，是 per-project 授權判定（`K-16` 的 `MembershipFacade`）的資料基礎。唯一鍵 `(project_id, user_id)` |
| `reselection_events` | **9 欄**（原 8 欄；第 9 欄 `cause` 由 `U19` 依 `[FD3]`=A 回補）。per-project 角色變更的稽核軌跡，兼橫幅已讀狀態的載體。**對 `projects` 沒有外鍵**（見下） |
| `system_requirement_fields` | 9 欄。某系統的某個需求欄位的值（agent 需要的架構假設，如 SLA／TPS／預算）。唯一鍵 `(system_id, agent_group, field_key)` |

**五件最容易被誤讀的事：**

1. **`reselection_events` 對 `projects` 沒有外鍵，這是刻意的（`[ND1]`=A）。**
   `FR12.4b` 存在的理由正是事後查得出某人的 `project_admin` 是怎麼來的，而
   `CASCADE` 會把答案一起刪掉、`RESTRICT` 會擋住專案刪除。代價是 `project_id`
   **沒有參照完整性保護**，唯一寫入端是 `K-16` 的 facade（應用層保證，不是資料庫
   保證）。形狀與 2.2.8 的 `memory.memory_audit_events.memory_id` 一對一對照。
2. **`reselection_events` 沒有保存期限，而這也是刻意的。**
   `memory.memory_audit_events` 有 90 天（`NFR7.2`），本表**沒有**：母體不同
   （記憶稽核的母體是每日對話，改選事件的母體是「專案 owner 帳號被停用」這種罕見
   事件），且 `components.md:886` 逐字定下「清＝`acknowledged_at`，**事件列本身不刪**
   ——刪了就失去稽核」。**不要照 2.2.8 的樣子補一個 90 天清除作業**，那會刪掉
   `FR12.4b` 的稽核。
3. **`project_members.project_id` 是 `ON DELETE CASCADE`，而這同時是在保護既有程式。**
   `hierarchy_service.delete_project()` 只守兩道門（預設專案、底下仍有系統），
   **沒有任何一道關於成員**；而 `U19` 落地後每個新建專案至少有一列成員。
   若改成 `RESTRICT`，`db.delete(project)` 會在 commit 丟出**未被捕捉的
   `IntegrityError`**，使用者看到 500 而不是 `BR4.4` 那種帶訊息的衝突回應。
4. **`project_members.role` 與全域角色同名不同義。**
   本表的 `project_admin` 是**專案內**的身分，與 `users.role`／`role_permissions`
   的全域 `Project_Admin` 是兩回事；`FR12.6` 要求**兩層串聯、任一層不過即拒**。
   資料庫無法強制區分，只在 COMMENT 中標明。
5. **`reselection_events.cause` 讓兩種角色變更共用一張表，而它改變了兩欄的語意。**
   `U19` 依 `[FD3]`=A 回補此欄（`auto_reselection`／`manual_role_change`），
   **關閉了原本留在表 COMMENT 裡的 `OPEN-ND18-3`**。兩項連帶後果都是刻意的：
   `previous_owner_user_id` 在 `auto_reselection` 下是**被停用的 owner**、在
   `manual_role_change` 下是**執行變更的管理者**（`BR5.4`，兩者都回答「這次變更
   是誰造成的」）；`acknowledged_at` **只對 `auto_reselection` 有意義**（`BR5.5`）。
   因此**橫幅查詢必須同時過濾 `cause = 'auto_reselection'` 與
   `acknowledged_at IS NULL`**——漏掉 `cause` 過濾會讓每一次人工角色變更都彈出
   一則文案為「系統自動把管理權交給你」的橫幅，而那對人工變更是錯的訊息。
   本欄**有** CHECK（`ck_reselection_events_cause`），這是它與 `previous_role`／
   `new_role`（刻意無 CHECK）的分野：它的兩個值是定案而非未決事項。

**`system_requirement_fields` 的三種狀態必須保持可區分**（`ADR-015`）：

| 狀態 | 列是否存在 | `value` | `cleared_at` |
|---|---|---|---|
| 從未填過 | **無列** | — | — |
| 已填 | 有列 | 有值 | NULL |
| 曾填後清空 | **有列** | **NULL** | **有值** |

`value` **可為 NULL 是刻意的**：收緊為 `NOT NULL` 會讓前兩種以外的第三態無法表達，
而畫面要求區分它們——代價是清空動作失去稽核軌跡。
`ck_system_requirement_fields_cleared_has_null_value` 擋下「同時有值又已清空」的列。

該表的**表 COMMENT 是防呆機制而非文件義務**（`BR2.2`）：欄位定義（`agent_group` →
`field_key`）是**程式內的常數**，定義被移除後其值列**保留**、畫面不渲染該組、
未填計數只算**當前已宣告**的欄位。不寫下來的話，「資料庫裡有、畫面上看不到」的列
會被下一個人當成髒資料清掉——被清掉的是使用者曾經填過的值。
CI 的 `P12` 斷言會檢查這段 COMMENT 存在且含那三件事。

##### 前進步驟（既有環境的唯一路徑，`NFR8.5`）

`schema_rbac.sql` 只掛在 `/docker-entrypoint-initdb.d/`，故它**只在空 volume 執行**
——既有的 `192.168.10.10` 這三張表（以及 2.2.8 的 `memory` schema 與兩張表）
**一張都拿不到**。既有環境的唯一路徑是下面這支獨立指令，它一次建立
**`U5` ＋ `U18` 的全部新物件**（`[P1]`=A）：

```bash
# 前置條件：2.2.7 的 run_hierarchy_migration.py 必須**先**跑過
# （J) 的兩條外鍵指向 projects／systems）。沒跑過的話本指令會以可讀訊息擋下，
# 不會丟一個生的 UndefinedTable。
cd backend
# DATABASE_URL 指向目標資料庫（給應用程式用的那一份，帶 +psycopg 後綴）
python scripts/run_meta_schema_migration.py
echo "exit=$?"    # 必須為 0
```

**這支腳本不複製 DDL**：它直接解析 `schema_rbac.sql` 的 `X)`／`I)`／`J)` 三個區塊
並執行同一份文字，所以那三個區塊的 DDL 只有一份——**與 2.2.7 的
`run_hierarchy_migration.py` 刻意不同**（那支在 `services/hierarchy_migration.py`
另有一份物化，`schema_rbac.sql` 的檔頭逐字「DDL 兩處並存，改一處必須改另一處」）。
副作用是 CI 的 `memory-schema` job（它套用 `schema_rbac.sql`）與這支腳本
**不可能漂移**。

全部 DDL 包在**一個交易**內（PostgreSQL 的 DDL 可交易），並在 COMMIT **之前**
逐項查證後條件，所以：

> **結束碼 0 ⟺ 1 個 schema ＋ 5 張表 ＋ 7 個索引 ＋ 9 條 CHECK／UNIQUE ＋ 3 條外鍵
> 刪除行為（另驗 1 條必須不存在的外鍵）＋ 4 段表 COMMENT ＋ `memory` 的 grant
> 全部存在。**
>
> （CHECK／UNIQUE 由 8 條增為 9 條：`U19` 依 `[FD3]`=A 回補的
> `ck_reselection_events_cause`。)

任一項不成立即 rollback 並以非零碼結束（`NFR8.3`）——資料庫維持執行之前的狀態，
處置後重跑即可（全部 DDL 為 `IF NOT EXISTS` 形狀，`BR2.1`，已實測重跑為 exit 0）。
**不動啟動路徑**（`NFR8.4`：`backend/database.py` 不新增補丁）——理由是
`restart: unless-stopped` 之下任何建表失敗會變成**重啟迴圈**，而那比「少幾張表」
更難診斷。

**誠實的代價**：這仍是**手動步驟，忘了跑就沒有表**，而 `deploy.yml` 不呼叫任何
遷移腳本（2.2.7 的那支也沒被呼叫）。失敗至少很明顯：`U19`／`U20` 的任何查詢會立即
報 `relation "project_members" does not exist`，不是靜默降級。

驗證：

```bash
# 三張表都在 public（三列）
psql "$DATABASE_URL" -c "SELECT table_name FROM information_schema.tables
  WHERE table_schema='public' AND table_name IN
  ('project_members','reselection_events','system_requirement_fields') ORDER BY 1;"

# 欄位數應為 6 / 9 / 9（reselection_events 因 U19 回補 cause 而由 8 增為 9）
psql "$DATABASE_URL" -c "SELECT table_name, count(*) FROM information_schema.columns
  WHERE table_schema='public' AND table_name IN
  ('project_members','reselection_events','system_requirement_fields')
  GROUP BY 1 ORDER BY 1;"

# joined_at 必須是 NOT NULL（應回 NO）——自動改選直接讀它，可為 null 會讓挑選
# 在空值上無序，每次選出不同人而沒有任何錯誤
psql "$DATABASE_URL" -c "SELECT is_nullable FROM information_schema.columns
  WHERE table_name='project_members' AND column_name='joined_at';"

# project_members → projects 的 ON DELETE 應為 CASCADE（confdeltype 應回 c）
psql "$DATABASE_URL" -c "SELECT con.confdeltype FROM pg_constraint con
  JOIN pg_class t ON t.oid=con.conrelid JOIN pg_class rt ON rt.oid=con.confrelid
  WHERE t.relname='project_members' AND con.contype='f' AND rt.relname='projects';"

# reselection_events **不得**有指向 projects 的外鍵（應回 0）
psql "$DATABASE_URL" -c "SELECT count(*) FROM pg_constraint con
  JOIN pg_class t ON t.oid=con.conrelid JOIN pg_class rt ON rt.oid=con.confrelid
  WHERE t.relname='reselection_events' AND con.contype='f' AND rt.relname='projects';"

# cause 必須存在且為 NOT NULL（應回一列 NO）——U19/[FD3]=A 回補的第 9 欄
psql "$DATABASE_URL" -c "SELECT is_nullable FROM information_schema.columns
  WHERE table_name='reselection_events' AND column_name='cause';"

# cause 的封閉列舉必須在（應回含 auto_reselection 與 manual_role_change 的定義）
psql "$DATABASE_URL" -c "SELECT pg_get_constraintdef(oid) FROM pg_constraint
  WHERE conname='ck_reselection_events_cause';"

# 橫幅查詢用的 partial index 必須存在**且仍是 partial**
# （indexdef 應含 WHERE (acknowledged_at IS NULL)；拿掉 WHERE 只會變慢、不會報錯）
psql "$DATABASE_URL" -c "SELECT indexdef FROM pg_indexes
  WHERE indexname='ix_reselection_events_unack';"

# 三態模型的 CHECK 與三欄唯一鍵都在（應有兩列）
psql "$DATABASE_URL" -c "SELECT conname FROM pg_constraint
  WHERE conname IN ('ck_system_requirement_fields_cleared_has_null_value',
                    'uq_system_requirement_fields_group_key') ORDER BY 1;"

# [UG:G9]=A 的防呆 COMMENT 必須非空且含那三件事
psql "$DATABASE_URL" -c "SELECT obj_description(
  'public.system_requirement_fields'::regclass, 'pg_class');"
```

CI 的 `memory-schema` job 會對真實 PostgreSQL 執行全部 **14** 條斷言
（`backend/scripts/verify_meta_schema.sql`，`P1`–`P12` ＋ `U19` 回補的 `P13`／`P14`），並**套用
`schema_rbac.sql` 兩次**以驗證可重跑性。**該 job 的名稱比它的內容窄**
（它同時跑 2.2.8 的 `S1`–`S12` 與本節的 `P1`–`P12`）——刻意不改名，理由是
GitHub 的 check name 取自 job 的 `name:`，改它會讓 branch protection 的必要檢查
變成「缺少必要檢查」。

**本單元零應用程式碼、零端點、零畫面**，故沒有新環境變數、沒有 `deploy/.env` 變更、
沒有前端建置參數變更。成員與需求欄位的讀寫（含授權）屬後續單元
（`K-16`／`K-17` 的 facade）。

#### 2.2.10 U19 既有專案的成員回填（`membership-service`）

**第三支一次性腳本，而它與前兩支的順序是嚴格的。** `project_members` 是全新表
（契約 `K-15` 的 `observable_side_effects` 逐字「不含任何資料寫入」），而既有專案
全部由 `services/hierarchy_migration.py` 建立且**從未寫過任何成員列**
——所以**每一個既有專案今天都是零成員**。

| # | 動作 | 前置 | 跳過或順序錯誤的後果 |
|---|---|---|---|
| 1 | `python scripts/run_hierarchy_migration.py`（見 2.2.7） | — | `J)` 的外鍵指向 `projects`／`systems`，表不存在則第 2 步以可讀訊息擋下 |
| 2 | `python scripts/run_meta_schema_migration.py`（見 2.2.9） | 第 1 步 | 兩張表不存在 → `U19` 的任何寫入拋 `UndefinedTable` |
| 3 | **`python scripts/backfill_project_members.py`（本節）** | 第 2 步 | 既有專案的擁有者被 `BR1.6` 判為**非成員**而被拒絕存取自己的專案 |

##### 為什麼必須在**任何消費端上線之前**跑（`NFR12.25`）

後果鏈：`resolve_project_role` 對既有專案的任何使用者（**包括該專案真正的
owner**）查無列 → 回 `None` → `BR1.6` 要求當成拒絕 → 消費端
（`U20`／`U13`／`U21`／`U24`）上線時，既有專案的擁有者會被判定為非成員。

**第一次部署不會鎖人在外面**，而這一點要寫清楚以免被誤讀成「不急」：

| 問題 | 答案（實查） |
|---|---|
| 這個窗口裡既有專案的擁有者會被鎖在外面嗎？ | **不會。** 本單元的消費端都在後續 Bolt，而 `hierarchy_facade.list_projects` 目前是 **owner-scoped**（讀 `projects.owner_user_id`，不讀 `project_members`），故既有的專案列表路徑不經本單元 |
| 既有停用端點的新前置檢查會誤判嗎？ | **不會，但方向是「過寬」而非「過嚴」**：零成員列時 `assert_can_deactivate` 的 `HAVING count(*) = 1` 找不到任何專案，故它**放行**。保護在回填之後才生效 |
| 那什麼時候真的會鎖人在外面？ | **第一個消費端上線時。** 這就是 `NFR12.25` 的理由 |

**對部署批次的交接（`OPEN-ID19-2`）**：本單元與第一個消費端之間是一條
**手動步驟邊**——它不在依賴圖上，是一個部署程序前置條件。
「回填已在 staging 執行過」必須是第一個消費端所在批次的前置條件。

##### 前進步驟

```bash
cd backend
# DATABASE_URL 指向目標資料庫（給應用程式用的那一份，帶 +psycopg 後綴）

# 先看會動到幾列（交易一律回滾，不寫入）
python scripts/backfill_project_members.py --dry-run
echo "exit=$?"    # 必須為 0

# 實際回填
python scripts/backfill_project_members.py
echo "exit=$?"    # 必須為 0
```

對每個**沒有任何成員列**的專案插入一列
`(project_id, owner_user_id, 'project_admin', now())`。

- **冪等**：條件是「該專案無任何成員列」，故重跑安全。
- **刻意不處理「已有成員但 owner 不在其中」的專案**——那是人為決定的結果
  （例如 owner 被移出過），回填不得把他加回去。唯一約束
  `uq_project_members_project_user` 也因此不會被違反。
- `joined_at` 用 `now()` 而非專案的 `created_at`：這一列記的是「他**何時成為
  成員**」。用 `created_at` 會讓 `BR4.2` 的「最早加入者」挑選把一位回填出來的
  成員排在所有真實邀請之前，而那不是事實。
- **單一交易 ＋ 自我終檢**（COMMIT 之前斷言「零成員專案數為 0」），故：

> **結束碼 0 ⟺ `projects` 中沒有任何零成員的專案。**

任一項不成立即 rollback 並以非零碼結束——資料庫維持執行之前的狀態。

**刻意不與 2.2.9 的腳本合併**（`OPEN-N19-4` 的定案）：那一支目前**純 DDL、無
資料寫入**，而那正是它能單一交易並自我終檢的前提；把資料動作混進去會讓
「結束碼 0 代表什麼」同時涵蓋兩種不同的保證。

**誠實的代價**：這仍是**手動步驟，忘了跑就沒有列**，而 `deploy.yml` 不呼叫任何
遷移腳本（2.2.7／2.2.9 的那兩支也沒被呼叫）。

驗證：

```bash
# 零成員專案數必須為 0
psql "$DATABASE_URL" -c "SELECT count(*) FROM projects p
  WHERE NOT EXISTS (SELECT 1 FROM project_members m WHERE m.project_id = p.id);"

# 每個專案至少有一位 project_admin（BR2.1 的不變量；應回 0 列）
psql "$DATABASE_URL" -c "SELECT p.id, p.name FROM projects p
  WHERE NOT EXISTS (SELECT 1 FROM project_members m
    WHERE m.project_id = p.id AND m.role = 'project_admin');"

# 回填出來的列：role 為 project_admin、invited_by 為 NULL（系統寫入，無邀請者）
psql "$DATABASE_URL" -c "SELECT project_id, user_id, role, invited_by
  FROM project_members WHERE invited_by IS NULL ORDER BY project_id;"
```

##### 回滾的一項不對稱（`OPEN-ID19-5`）

`deploy.yml` 的回滾還原的是**映像**，而本節是**資料動作**——映像回滾**不會**
撤銷它。這會壞掉嗎？**不會**：回填寫的是
`(project_id, owner_user_id, 'project_admin', now())`，而 last-good 的程式
**不讀這兩張表**（本單元是第一個讀寫者），多出來的列對舊程式不可見。
故**不需要反向腳本**。**但這個結論只在第一次部署成立**——一旦有消費端上線，
回滾的語意就要重新評估。

##### 本單元的其他部署面變更：零

不改 `deploy.yml`、不改任一 compose、不改 `deploy/nginx.conf`、不改
`deploy/render-env.sh`、不改任一 `.env.example`、**不改 `backend/database.py`**
（`NFR12.5`：該檔 diff 為空）。新端點掛在既有 `/api/` 之下
（`/api/membership/*`），走既有 nginx 反向代理，**不新增監聽埠、不新增環境
變數**。唯一的基礎設施變更在 `.github/workflows/ci.yml`（新增 `concurrency`
job，見該檔內的註解）。

#### 2.2.11 U9 保留系統 actor 與 90 天記憶清除（`memory-purge`）

`K)` 區塊 seed 的是 **`users` 的一列**，而不是一張表。它是 90 天記憶清除
（`FR4.5`）寫稽核事件時的 actor。

| 欄位 | 值 |
|---|---|
| `username` | `SYSTEM.retention-purge` |
| `role` | `system`（**不在** `role_permissions` 的授權集合內） |
| `is_active` | `FALSE` |
| `password_hash` | 一個**格式合法**的 bcrypt hash，其明文是一次性隨機值且從未被記錄 |

**為什麼一定要有它**：`memory.memory_audit_events.actor_user_id` 是
`NOT NULL REFERENCES users (id)`，而清除是**排程觸發、無人在迴圈內**
（`FR4.5a`）——沒有自然的使用者可填。填記憶擁有者會讓稽核「對誰刪的」說謊
（`I)` 區塊該欄的 `COMMENT` 逐字），留 NULL 則 `NOT NULL` 不允許。

##### 它會出現在 Admin 使用者清單上，而且**不要刪掉它**

`/api/auth/list` 不知道要排除它，所以管理者會在清單上看到一個無法登入、
沒有任何權限的帳號（`total` 會 +1）。那不是髒資料。

**刪掉它的後果**：自那一刻起，清除的稽核 `INSERT` 全部因外鍵違反而失敗，
而稽核與刪除**在同一個交易內**，所以**整個清除交易中止**、workflow 以非零碼結束。
那是刻意的大聲失敗，但在它被修好之前，90 天保存期不會前進一列。

##### 既有環境取得這一列的路徑

```bash
cd backend && python3 scripts/seed_retention_system_actor.py
```

它 `import` `run_meta_schema_migration.py` 的 `extract_blocks()` 解析本檔的
`K)` 區塊，**SQL 只有一份**；單一交易，並在 COMMIT 之前逐項查證後條件
（那一列存在、`is_active` 為 false、`role` 不在授權矩陣內、`password_hash`
符合 bcrypt 格式），任一項不成立即回滾並以非零碼結束。重跑安全。

> **明文更正（本節最重要的一句）**：
> **不要為了取得這個 seed 而重跑整支 `schema_rbac.sql`。**
> 該檔的 `C) RBAC` 區塊開頭那條逐字為 `DELETE FROM role_permissions;` 的敘述會
> **清掉任何經 Admin UI 調整過的權限矩陣**，然後重播設計預設值（檔頭的注意事項
> 已警告過，但「重跑整支檔」在既有環境聽起來像一個安全操作）。
> 上游的 `infrastructure-specification.md §五` 第 2 步把「重跑 `schema_rbac.sql`」
> 寫成既有環境取得 seed 的**唯一路徑**——那個敘述的代價當時沒有被查證，
> 本節是它的更正。

##### 驗證

```bash
psql "$DATABASE_URL" -c "SELECT id, username, role, is_active FROM users WHERE username = 'SYSTEM.retention-purge'"
#   應回**一列**，且 is_active 為 f

# role 不在授權矩陣內（應為 0）
psql "$DATABASE_URL" -c "SELECT count(*) FROM role_permissions WHERE role = 'system';"

# password_hash 是合法 bcrypt 格式（應為 t）
psql "$DATABASE_URL" -c "SELECT password_hash ~ '^\$2[aby]\$' FROM users WHERE username = 'SYSTEM.retention-purge';"
```

> 在部署主機上請改為
> `docker exec -i <db-container> psql -U postgres -d cloud360 -c "..."`（同 2.1 的說明）。

##### 兩個新的 GitHub Actions workflow

| 檔案 | runner | 觸發 | 職責 |
|---|---|---|---|
| `.github/workflows/memory-retention-purge.yml` | **自架**（`[self-hosted, linux, x64, cloud360]`） | `schedule` 每日 17:41 UTC ＋ `workflow_dispatch`（含 `dry_run`，預設 `true`） | 執行清除（兩條 DELETE ＋ 一次稽核 INSERT） |
| `.github/workflows/memory-retention-watchdog.yml` | **GitHub 託管**（`ubuntu-latest`） | `schedule` 每日 06:23 UTC ＋ `workflow_dispatch` | 查清除最後一次**成功的排程** run，逾 3 天開 issue 並以非零碼結束 |

- **排程要到檔案進入預設分支後才會排入**，這是 GitHub 的既有行為；merge 進 `ut`
  之後不會立刻開始跑。
- **首次啟用前必須先驗證選取條件**：以 `workflow_dispatch` ＋ `dry_run=true`
  手動觸發一次，核對它印出的計數與**選取範圍的邊界**（最舊／最新時間戳 ＋ 最多
  10 筆 id）。理由是**已執行的清除不可回滾**（`OPEN-ID9-4`）——workflow 檔可
  `git revert`、seed 可重建，但刪掉的記憶與稽核列無法復原。
- 清除本體**零新 secret、零新環境變數、零新監聽埠**；`db` 不取得 host port。
  監看者只用內建 `GITHUB_TOKEN`。
- 監看者需要 **`issues: write`**，而本 repo 的既有排程 workflow **無此先例**
  （它們持有 `issues: read` ＋ gh-aw 的 `safe-outputs`）。這是本單元唯一的權限
  增量，替代方案見 `monitoring-design.md §三之三`。

##### 本單元的其他部署面變更：零

不改 `deploy.yml`、不改任一 compose、不改 `deploy/nginx.conf`、不改
`deploy/render-env.sh`、不改任一 `.env.example`、**不改 `backend/database.py`**
（該檔 diff 為空）。`ci.yml` 的 `memory-schema` job 新增一個步驟跑
`backend/scripts/verify_purge_sql.sql`（`R1`–`R10`）。

#### 2.2.12 U8 記憶檢索的 HNSW 向量索引（`memory-service`）

**本單元的唯一結構變更是一個索引**，落在 `schema_rbac.sql` 的 `I)` 區塊
（`U5` 擁有的區塊）。沒有新表、沒有新欄位、沒有 seed、**沒有資料遷移**。

| 物件 | 說明 |
|---|---|
| `memory.ix_memory_records_embedding_hnsw` | `memory_records.embedding` 的 HNSW 索引，opclass 為 **`vector_cosine_ops`** |

##### 三件最容易被誤讀的事

1. **opclass 與查詢的距離運算子必須成對，而不成對是靜默的。**
   本 repo 的那一對是 `vector_cosine_ops` ↔ **`<=>`**
   （`backend/services/memory_service.py` 的 `SEARCH_SQL`）。
   opclass 改錯時索引**被忽略**、查詢**仍然正確**（仍回精確最近鄰）、
   在空表上延遲**看起來一樣好**——`[N2]`=B 的整個投資落空而沒有任何跡象。
   故它由兩道斷言鎖住：`verify_memory_schema.sql` 的 **`S14`**（真實 PG 上以
   `SET enable_seqscan = off` ＋ `EXPLAIN` 驗 planner 真的用得到它）
   與 `backend/tests/test_memory_contract.py` 的 **`C6`**（鎖住 Python 側的
   運算子與本索引的 opclass 是同一對）。

2. **HNSW 而非 ivfflat。** ivfflat 的 `lists` 參數需要先有資料才選得合理，
   而本表在建立索引時是空的；HNSW 可在空表上建立。

3. **`git revert` 不會刪掉這個索引**（`I8-4`）。程式碼可 revert、
   `openapi.json` 可 revert，但 DDL 已經執行過。回滾後索引會留著，
   而**留著是無害的**（只佔空間，不改變查詢正確性），故回滾程序**不要求**
   `DROP INDEX`。寫在這裡只是為了不讓人以為 revert 之後資料庫回到了原狀。
   真要移除：`DROP INDEX IF EXISTS memory.ix_memory_records_embedding_hnsw;`

##### 既有環境的取得路徑：不需要新腳本

`backend/scripts/run_meta_schema_migration.py` 解析並執行 `I)` 區塊
（`BLOCKS_TO_RUN = ("X", "I", "J")`），故索引**會被建立**。
本單元同步把它加進該腳本的 `EXPECTED_INDEXES`——只加 SQL 而不加清單會讓
索引「被建立但不被驗證」，該腳本「結束碼 0」的語意會悄悄變窄而無人察覺。

**與 `U9` 的對照**：`U9` 的系統 actor seed 不能放 `I)`（該腳本逐字宣告
「也不塞任何資料」），故它需要新腳本。**索引是 DDL 而非資料**，所以放 `I)`
完全正確且自動走既有路徑。

##### 後端啟動對 `memory` schema 的新依賴（**部署前必讀**）

本單元為兩張記憶表新增了 ORM 映射（`backend/models.py`），理由是
in-memory SQLite 的測試環境以 `Base.metadata.create_all()` 建表，沒有 ORM
模型就**沒有表可查**，連授權測試都跑不起來。

後果：`init_db()` 的 `Base.metadata.create_all()` 現在會走訪
`memory.memory_records` 與 `memory.memory_audit_events`。

| 情境 | 行為 |
|---|---|
| 兩張表已存在（空 volume 初始化、或已跑過 `run_meta_schema_migration.py`） | `checkfirst` 過濾掉它們，**no-op** |
| `memory` schema **不存在** | `create_all()` 以 `schema "memory" does not exist` 失敗 → **啟動失敗** |
| schema 存在但表不存在 | 由 `models.py` 的 `before_create` 守門**主動拒絕**並印出處置方式 |

第三列的守門是刻意加的：ORM **刻意省略 `embedding` 欄位**
（`NFR8.20` 要求 `backend/requirements.txt` 的 diff 為空，而宣告
`vector(1024)` 需要 `pgvector` 套件）。若放任 `create_all` 建表，會得到一張
**缺少 `embedding` 的 `memory_records`**，而之後重跑 `schema_rbac.sql`
也補不回來（`CREATE TABLE IF NOT EXISTS` 整段 no-op）——向量檢索永久失效
且沒有任何錯誤訊息。大聲失敗遠優於那個結果。

**故部署前置條件（既有環境）**：先跑
`python backend/scripts/run_meta_schema_migration.py`（見 2.2.9），
再啟動後端。順序錯誤的後果是啟動失敗，而非資料損壞。

驗證：

```bash
# 索引存在（應回一列 ix_memory_records_embedding_hnsw）
psql "$DATABASE_URL" -c "SELECT indexname FROM pg_indexes
  WHERE schemaname='memory' AND tablename='memory_records'
    AND indexname='ix_memory_records_embedding_hnsw';"

# 索引型態與 opclass 應為 hnsw / vector_cosine_ops
psql "$DATABASE_URL" -c "SELECT am.amname, opc.opcname
  FROM pg_index i JOIN pg_class ic ON ic.oid=i.indexrelid
  JOIN pg_namespace n ON n.oid=ic.relnamespace
  JOIN pg_am am ON am.oid=ic.relam
  JOIN pg_opclass opc ON opc.oid=i.indclass[0]
  WHERE n.nspname='memory' AND ic.relname='ix_memory_records_embedding_hnsw';"

# planner 在 seqscan 關閉時真的用得到它（計畫中應出現該索引名）
psql "$DATABASE_URL" -c "SET enable_seqscan=off;
  EXPLAIN (COSTS OFF) SELECT id FROM memory.memory_records
  ORDER BY embedding <=> (SELECT ('[' || array_to_string(
    array_fill(0.1::real, ARRAY[1024]), ',') || ']')::vector(1024)) LIMIT 5;"
```

##### 本單元的其他部署面變更：零

不改 `deploy.yml`、不改任一 compose、不改 `deploy/nginx.conf`、不改
`deploy/render-env.sh`、不改任一 `.env.example`、不改 `backend/requirements.txt`、
**不改 `backend/database.py`**（該檔 diff 為空），**也不改 `.github/workflows/ci.yml`**
——`S14`／`S15` 進既有的 `backend/scripts/verify_memory_schema.sql`，
而 `memory-schema` job 已經在執行它。

> **已知的命名落差，如實記載**：`ci.yml` 裡那個步驟的名稱仍是
> `Verify memory schema assertions (S1-S13)`，而該檔現在含 `S1`–`S15`。
> 步驟名因此比內容窄。**刻意不改**：本單元的判準之一是 `ci.yml` 的 diff 為空
> （`NFR8.20` 的可驗證面）。這與該 job 自身註解記載的同形取捨一致
> （「這個 job 的 id 與 name 現在都比它的內容窄……刻意不改」）。

#### 2.2.1 A3 `architecture_reviews`（DDL 摘要）

| 欄位 | 說明 |
|---|---|
| `diagram_id` / `created_by` | FK → `user_diagrams`／`users` |
| `provider` | 預設 `aws` |
| `status` | `pending`／`rules_complete`／`complete`／`rules_only`／`unsupported` |
| `overall_score` | 總分（整數） |
| `scores_json` | JSON：Lens／啟發式支柱分、RiskCounts、`source_of_truth` 等 |
| `findings_json` | JSON 陣列：發現（權威為離線 Lens；失敗時可啟發式備援） |
| `suggestions_text` | Agent 改善建議全文 |
| `error_message`／`rule_pack_version`／`archived` | 錯誤、規則包版本、是否封存 |
| `created_at`／`updated_at` | 時間戳 |

#### 2.2.2 A3 `wa_lenses`（Lens 標準編輯）

| 欄位 | 說明 |
|---|---|
| `lens_id` | 預設 `cloud360-core-mvp` |
| `is_active` | 現行標準列為 `true`（評核優先讀此） |
| `body_json` | 完整 Offline Custom Lens JSON |
| `updated_by` | 最後編輯者（具 A3 審核權限者） |
| `provider` | `aws`／`gcp`／`azure`（每雲一份 active Lens） |

**既有環境升級**：重跑 `schema_rbac.sql`（含 `ALTER … DROP NOT NULL`／`ADD COLUMN IF NOT EXISTS`），或依賴後端啟動時 `database._ensure_a3_schema()`（會補 `xml_snapshot`、`wa_lenses.provider`、`diagram_id` 可空）。  
無對應雲別的 `wa_lenses` 資料時，評核 fallback 至 `backend/lenses/cloud360-core-mvp-lens.json`。

**A3 增量（上傳＋多雲）**：`architecture_reviews.diagram_id` 可 NULL（未建檔上傳）；`xml_snapshot` 存評核 XML；三雲 rule pack ＋ per-cloud Lens。

**A1↔A3 協作優化（本次）**：**無額外 SQL**；沿用既有 `user_diagrams`／`architecture_reviews`。重點是重建含 Claude Code CLI 的 backend image，並設定 OpenRouter／token 變數。

驗證：

```bash
psql "$DATABASE_URL" -c "\d architecture_reviews"
psql "$DATABASE_URL" -c "\d wa_lenses"
psql "$DATABASE_URL" -c "SELECT count(*) FROM architecture_reviews;"
psql "$DATABASE_URL" -c "SELECT id, lens_id, provider, is_active, updated_at FROM wa_lenses ORDER BY id DESC LIMIT 5;"
```

#### 2.2.3 `users.last_activity_at`（最後活動時間）

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP WITH TIME ZONE;
```

| 項目 | 說明 |
|---|---|
| 語意 | 該帳號**最後一次以有效憑證發出請求**的時刻（UTC）。只留最後一次，不留歷史 |
| 寫入頻率 | 同一帳號至多**每 5 分鐘**一次（滑動視窗，基準為上次成功寫入的時刻） |
| `NULL` 的意思 | **從未活動**。上線前的既有帳號全部為此態，管理介面顯示可聚焦的破折號，**不套用逾期標示** |
| 預設值 | **刻意沒有**。設了預設值就無法區分「從未活動」與「剛建立」 |
| 逾期判定 | 距今**超過 90 天**（嚴格大於）。由**後端**計算並隨 API 回應帶出，前端不自行計算（客戶端時鐘不可信） |

**升級既有環境**：兩條路徑都會補上此欄，擇一即可 ——

1. 重跑 `schema_rbac.sql`（可重跑安全；**但會 `DELETE` 並重播 `role_permissions`，Admin UI 調過的權限會被覆寫**，見 2.5）；
2. **建議**：只重啟後端服務 —— 啟動時的 `_ensure_last_activity_schema()` 會執行同一段 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`，不動任何其他資料。

**驗證指令**：

```bash
psql "$DATABASE_URL" -c "\d users" | grep last_activity_at
# 應出現：last_activity_at | timestamp with time zone |
psql "$DATABASE_URL" -c "SELECT username, last_activity_at FROM users ORDER BY id LIMIT 5;"
# 升級後尚未有人活動時，last_activity_at 全為空 —— 這是預期行為
```

#### 2.2.4 使用者清單端點改為分頁（API 契約變更）

`GET /api/auth/list` 的回應由**裸陣列**改為**分頁物件**：

```json
{ "items": [ ... ], "total": 87, "page": 1, "page_size": 20 }
```

| 項目 | 值 |
|---|---|
| 查詢參數 | `page`（≥1，預設 1）、`page_size`（1〜100，預設 20） |
| 非法參數 | 回 **422**，不回傳任何帳號資料 |
| 頁次超出範圍 | 回 **200**、`items` 為空、`page` 回顯請求值（不夾到最後一頁） |

**部署注意**：這是**破壞性契約變更**。前後端必須**同一次部署**上線 —— 只更新後端會讓使用者管理頁在前端 `.map()` 一個物件時直接壞掉。本專案的 deploy-on-merge 會同時部署兩個映像，正常流程下不會出現這個中間態；**但若手動只重建後端映像，請務必一併重建前端**。

#### 2.2.5 `Security_Reviewer` 取得 `J3a` 檢視權限（seed 變更）

`role_permissions` 的預設矩陣中，`('Security_Reviewer', 'J3a')` 由 `false` 改為 **`can_view = true`**（`can_edit`／`can_review` 維持 `false`）。

**既有環境如何生效**：`ensure_role_permissions_seeded()` **只在表為空時**寫入，既有環境不會經過它。後端啟動時另有一支 `_apply_security_reviewer_j3a_view()` 做**目標式更新**：只在該列存在**且**仍為系統種子所寫（`updated_by = 'system_seed'`）時才翻轉，不插入、不覆蓋人工調整。

**驗證指令**：

```bash
psql "$DATABASE_URL" -c "SELECT role, story_id, can_view, can_edit, updated_by FROM role_permissions WHERE role='Security_Reviewer' AND story_id='J3a';"
# 應為：Security_Reviewer | J3a | t | f | system_patch.j3a_view
#   （updated_by 由啟動補丁寫成 system_patch.j3a_view —— 這正是「這一列是補丁改的」
#    的標記，讓第二次以後的啟動落在「已跳過」而非被誤判為管理員異動。
#    若看到 system_seed 或空值且 can_view 為 f，表示補丁**沒有執行**。）
```

啟動日誌會記錄三態之一：`已套用`／`已跳過`／`未命中目標列`。**部署後請核對這行日誌** —— 此變更沒有自動化驗證涵蓋既有環境的套用。

#### 2.3 預設資料會塞什麼

執行 `schema_rbac.sql` 後：

1. **`role_permissions`**：寫入設計預設矩陣（約 **352** 列，11 角色 × 各 Story）。  
2. **`users`**：只建表，不建立固定密碼管理員。

後端若在**空庫**啟動，`init_db()` 也會：建表、必要時 seed `role_permissions`。
Local 環境仍會 seed demo persona 帳號；test/ci 只會建立 `admin/admin123` 供自動化測試使用；staging/production 不會建立固定密碼使用者。全新部署若需要 bootstrap admin，請在第一次啟動前設定 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD` 為強隨機臨時密碼，登入後立刻輪替或清除該 secret。
**新環境仍建議先跑 `schema_rbac.sql`**，行為與文件一致、不依賴啟動順序。

#### 2.4 重要：若沒跑 seed，角色細項會是「全空」

| 情況 | 結果 |
|---|---|
| 只建空表、**沒有**插入 `role_permissions` | 矩陣**全空**（所有角色對所有功能都無檢視／編輯／審核）→ Sidebar 幾乎看不到功能、API 易 403 |
| 有跑 `schema_rbac.sql`（或後端空表自動 seed） | 有設計預設權限；需搭配既有管理員或 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD` 建立的 bootstrap admin 調整 |

因此：**新環境請務必執行 `schema_rbac.sql`（或確認啟動後 `role_permissions` 列數約 352）**，不要只建表不塞預設。

驗證：

```bash
psql "$DATABASE_URL" -c "SELECT count(*) FROM role_permissions;"   -- 預期約 352
psql "$DATABASE_URL" -c "SELECT username, role FROM users WHERE username='admin';"
```

#### 2.5 重跑腳本注意

- 表：`CREATE IF NOT EXISTS`，可重複執行。  
- **`role_permissions`：會先 `DELETE` 再重播預設** → 若已在 Admin UI 調過細項，重跑前請先備份。  
- 既有 `admin` 密碼：**不會**被腳本覆寫。

備份細項範例：

```bash
psql "$DATABASE_URL" -c "COPY role_permissions TO STDOUT WITH CSV HEADER" > role_permissions_backup.csv
```

---

### 3. 依環境部署方式

#### 3.1 本機開發（前後端分開）

1. PostgreSQL + `psql "$DATABASE_URL" -f schema_rbac.sql`  
2. 安裝 **Node 22 + Claude Code CLI**（第 0.2 節）  
3. `backend/.env`：填 `DATABASE_URL`、`JWT_SECRET`、`CORS_ORIGINS`、`OPENROUTER_API_KEY`、可選 `LLM_MAX_OUTPUT_TOKENS`；**C1 另填**第 1.1.1 節 `AWS_*`／`GCP_BILLING_API_KEY`  
4. `cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`  
5. `frontend/.env`：`VITE_API_BASE_URL=http://localhost:8000` → `npm ci && npm run dev`  
6. 驗證：登入 → Workspace 產圖／Assessment 評核或「優化」不應再出現「找不到 CLI」；成本頁對 AWS／GCP 圖應能查到官方價（未設 GCP key 則 GCP 列未定價）

#### 3.2 Docker Compose（自架／另一台 staging）

適用：把整包（db＋backend＋frontend［＋可選 tunnel］）拉到新機器。

```bash
cp deploy/.env.example deploy/.env
# 編輯：POSTGRES_*、JWT_SECRET、OPENROUTER_API_KEY、PUBLIC_URL、
#       LLM_MODEL、LLM_MAX_OUTPUT_TOKENS（建議）、CLOUDFLARED_*（若用 tunnel）、
#       AWS_DEFAULT_REGION、GCP_BILLING_API_KEY（C1 FinOps；見第 1.1.1 節）

# 首次或升級含 Dockerfile 變更（含 Claude Code CLI）時務必 --build
docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env up -d --build

docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env ps
docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env exec backend which claude
```

重點：

- Backend image build 需能存取外網（nodesource、npm registry），否則 CLI 裝不上。  
- 改 `OPENROUTER_API_KEY`／`LLM_MAX_OUTPUT_TOKENS` 後：更新 `deploy/.env` 並 `up -d`（必要時 `--force-recreate backend`）。  
- 改 C1 的 `AWS_*`／`GCP_BILLING_API_KEY` 後：同樣更新 `deploy/.env` 並 recreate backend；容器需能出站 `pricing.us-east-1.amazonaws.com`、`cloudbilling.googleapis.com`、`prices.azure.com`。  
- 改前端 `PUBLIC_URL`：需重建 frontend image（Vite build-arg）。

不含 Cloudflare tunnel 時，可只起 `db`／`backend`／`frontend`，以 `FRONTEND_HOST_PORT`（預設 8090）對內存取；`CORS_ORIGINS`／`VITE_API_BASE_URL` 改為實際 URL。

#### 3.3 專案既有 staging（`ut` → `192.168.10.10`）

- Workflow：`.github/workflows/deploy.yml`（self-hosted runner `cloud360`）  
- 觸發：合併／推送到 `ut`（或手動 `workflow_dispatch`）  
- Secrets：至少 `JWT_SECRET`、`OPENROUTER_API_KEY`、`POSTGRES_PASSWORD` 等；**本次 C1 請再加**（可選）`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_DEFAULT_REGION`、`GCP_BILLING_API_KEY`（由 `render-env.sh` 寫入 `deploy/.env`）。IAM 僅目錄價動作，見第 1.1.1 節／ADR-0018。  
- 公開：`https://cloud360.danniel.cc`；內網：`http://192.168.10.10:8090`  

部署本次 A1↔A3／token 相關變更時：確認 runner 上的 compose **會 rebuild backend**（workflow 已 `up -d --build`），且 GitHub Secrets 的 OpenRouter 金鑰有效；可選在 secrets／產生的 `.env` 加上 `LLM_MAX_OUTPUT_TOKENS`。

部署 **C1 FinOps** 時：確認上列 AWS／GCP secrets 已設，且 backend 出站可達官方價目 host；煙測成本頁對 AWS／GCP／Azure 圖各查一次價。

部署 **brain-infra（U1：Redis／Ollama／PG 18）** 時：

- **新增一個 secret `REDIS_PASSWORD`**（`openssl rand -hex 32`，值不得含 `$`）。它是
  `deploy` job 的「Require the secrets that must not default」步驟與 `render-env.sh` 都會
  檢查的必填值，缺了就不會部署。**其餘六個 brain-infra 變數不要加成 secret**——見第
  5.10 節，把它們做成 `env:` 會讓 backend 拒絕啟動。
- 新增後實地查證它落在 **secrets** 而不是 variables（兩次 `gh api`，指令見第 5.10 節）。
- **PG 16 → 18 是破壞性升版**，不能只靠 merge 觸發自動部署：先走第 5.4 節的七步程序，
  再合併。反向順序會**靜默成功**（首頁正常、資料面全壞）。
- 首次部署後補實測值回第 5.6 節（記憶體）與第 5.9 節（rollback 耗時）。

#### 3.4 本次功能升級檢查清單（A1↔A3 優化）

- [ ] Backend image **重建**（確認映像**無** Node／`@anthropic-ai/claude-code`）  
- [ ] `OPENROUTER_API_KEY` 已設且有餘額  
- [ ] `ANTHROPIC_API_KEY` 為空；`ANTHROPIC_BASE_URL` 指向 OpenRouter（若仍供 A1 ChatAnthropic 使用）  
- [ ] （建議）`LLM_MAX_OUTPUT_TOKENS=12000` 或更低，避免 402  
- [ ] **無需**為本次功能重跑 SQL（無 schema 變更）  
- [ ] 煙測：Assessment 對含高風險報告按「優化」→ 出現新舊比對／儲存取消；Workspace 產圖正常  

#### 3.5 本次功能升級檢查清單（C1 FinOps）

- [ ] 已確認四表為 `archive_*`（或啟動後已 rename）；應用零讀寫  
- [ ] `deploy/.env` 或 GitHub Secrets 已設 **`GCP_BILLING_API_KEY`**（估 GCP 必填）；AWS 可選目錄價 IAM（`AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY`），缺則公開 Bulk  
- [ ] Backend recreate 後出站可達 AWS／GCP／Azure 價目 host  
- [ ] **合併閘門**：U3 退場變更須與 U8 新 Cost UI **同批**合併／部署（勿單獨合 U3）  
- [ ] 煙測：新成本頁（U8）上傳／估價流程可走通（舊 diagrams API 已移除）  

---

### 4. 建議部署順序（摘要）

1. 準備 PostgreSQL，設定 `DATABASE_URL`  
2. 執行 `psql "$DATABASE_URL" -f schema_rbac.sql`  
3. 準備 LLM：設定 **`OPENROUTER_API_KEY`**（映像不再需要 Claude Code CLI）  
4. 設定後端 `.env`／`deploy/.env`（含 `CORS_ORIGINS`、`JWT_SECRET`、LLM／token 變數，以及 **C1 的 `AWS_*`／`GCP_BILLING_API_KEY`**；全新 staging 可選 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`）並啟動 API
5. 設定前端 `VITE_API_BASE_URL` 後 build／部署  
6. 用既有管理員或 bootstrap admin 登入 → **立刻輪替臨時密碼／清除 bootstrap secret** → 調整角色權限
7. 依第 3.4／3.5 節做 A1／A3／優化與成本頁煙測  
8. **首次部署 brain-infra（Redis／Ollama／PG 18）之前，逐項做完第 5 節的前置條件**  
9. **既有環境**（如 `192.168.10.10`）另跑一次性階層遷移：`cd backend && python scripts/run_hierarchy_migration.py`。**必須在應用未接流量的窗口內執行**，且結束碼為 0 才可繼續——步驟、驗證與回復程序見第 2.2.7 節

---

### 5. brain-infra（U1）：前置條件、容量與 PG 16→18 升版

本節是 `Redis`（第 5 個服務）、`Ollama`（第 6 個服務）與 PG 18 ＋ pgvector 落地所需的
**部署環境前置條件與運維程序**。

> **本節每一項都沒有機械閘門。** `scripts/validate_env_contract.py` 只解析環境變數，
> 不解析 compose 的 `deploy.resources`、`logging:` 或 `networks:`；CI 跑在 GitHub runner
> 上，對 `192.168.10.10` 的磁碟、記憶體與加密狀態一無所知。這些事只能靠 code review
> 與運維紀律，所以**寫在這裡就是它唯一的存在形式**。

#### 5.1 主機全碟加密（前置條件，不是 compose 設定）

`192.168.10.10` 的系統碟必須啟用全碟加密（LUKS 或等價機制）。理由：本單元讓主機上同時
落地 Redis 的完整 session 上下文、資料庫 volume（`users` 全表含 `password_hash`、全部
RBAC 矩陣、三種記憶）、升版期的**全庫明文 dump**、以及部署窗口內的 `deploy/.env`。

**選全碟而不是「只加密 Docker 資料目錄」**：後者需要維護一張「哪些目錄在範圍內」的清單，
而那張清單每新增一個服務、每新增一個落地檔就會漏一項，且**沒有任何機械閘門會發現漏項**。
全碟是唯一不需要維護清單的形狀。

**這個決定保護什麼、不保護什麼**（不要讀成比實際更強）：

- **保護**：磁碟離線曝露——磁碟遭竊、主機報廢未清碟、備份介質外流、快照被複製。
- **不保護**：**任何在主機執行中時的曝露**。作業系統一旦掛載，加密對執行中的行程完全
  透明。取得主機 root、或取得任一容器執行權並讀得到 volume 掛載點的人，讀到的是明文。

**要逐一檢查的四個掛載點**（任一若為獨立掛載，就對它重複下面的判定）：

| 掛載點 | 為什麼它在清單上 |
|---|---|
| `/` | 基準 |
| `/var/lib/docker` | 三個具名 volume 的實體位置。搬到獨立的未加密資料碟是常見做法 |
| `/home`（或 `$HOME` 所在掛載點） | 升版 dump 放在 `$HOME/cloud360-upgrade/`（見 5.3） |
| 自架 runner 的工作目錄 | `deploy/.env` 在部署窗口內落在這裡，且部署失敗時會留存到下一次成功部署 |

漏掉其中任一項，會讓「系統碟已加密」與「那份最集中的明文資料其實沒加密」同時為真。

**判定方式（可二元判定）。注意 `lsblk` 的輸出形狀**：LUKS 之下，掛載點所在裝置的
`FSTYPE` 是 `ext4`／`xfs`（那是解密後的映射裝置），`crypto_LUKS` 出現在它的**祖先**上。
**不要**斷言「上一層就是 `crypto_LUKS`」——三大發行版的引導式 FDE 產生 LVM-on-LUKS，
直接父層的 `FSTYPE` 是 `LVM2_member`，那樣寫會在一台正確加密的主機上判成失敗。

```bash
# 對上表每一個掛載點跑一次（以 / 為例）
DEV=$(findmnt -no SOURCE /)            # 先取裝置，避開 MOUNTPOINTS 欄位名的版本差異
                                       # （MOUNTPOINTS 需 util-linux >= 2.37）
lsblk -s -o NAME,FSTYPE "$DEV"         # 反向列出祖先鏈
# 判定 1：鏈中出現 crypto_LUKS 即通過（不必是上一層）
lsblk -s -no FSTYPE "$DEV" | grep -qx crypto_LUKS && echo "LUKS: yes" || echo "LUKS: not found"

# 判定 2：映射裝置為 active 的 LUKS1／LUKS2
cryptsetup status "$(basename "$DEV")" | grep -E 'type:|status:'
```

**ZFS 原生加密是合格但不會出現 `crypto_LUKS` 的情形**，判定 1、2 對它不適用，**不得因此
判為未加密**；改以下列判定，值不為 `off` 即通過：

```bash
zfs get -H -o value encryption <dataset>
```

#### 5.2 解鎖方式，以及它與斷電自動回復的張力

| 解鎖方式 | 對斷電自動回復的後果 |
|---|---|
| **Passphrase** | **主機不會自動回復。** 斷電或重開後開機停在解鎖提示，必須有人到場（或走 KVM／IPMI）輸入。在那之前站台全黑，且 `deploy.yml` 的自架 runner 也不在線——**連回滾都跑不了** |
| **TPM 自動解鎖**（如 `systemd-cryptenroll --tpm2-device=auto`） | 自動回復恢復，代價是**加密對「整台機器被搬走」的防護降級**：碟與 TPM 一起被帶走時可自行解鎖。它仍防「只把碟拆走」 |

**這是一個要做的決定，不是實作者可以順手挑的。** 請在此記下本主機實際採用哪一種，以及
若採 passphrase，誰負責到場：

```text
本主機採用的解鎖方式：____________（passphrase／TPM）
採 passphrase 時的到場負責人與聯絡方式：____________
最後確認日期：____________
```

#### 5.3 升版 dump 檔的三條硬要求（缺一不可）

升版走 dump/restore，而 dump 是**全庫明文**。本 repo 的兩道掃描對它**結構上無效**：
`validate_no_obvious_secrets()` 只讀 contract 檔清單（工作區內的任意 `.sql` 不在其中），
而 `validate_no_production_config_added()` 做 `prod`／`production`／`secrets` 的 path-part
精確比對，`cloud360-dump-20260927.sql` 三者皆不命中。所以一份放在 repo 工作區的 dump，
`git add -A` 會把它撈進去，**兩道檢查都不會響**——而本 repo 是 **public**。

| # | 要求 | 做法 | 通過條件 |
|---|---|---|---|
| 1 | 建立時即 owner-only | 先 `umask 077` 再執行 `pg_dump`（**不是事後 `chmod`**——事後改之前存在一個 world-readable 的時間窗） | `stat -c '%a %U' <dump>` 回 `600` ＋ 執行者帳號 |
| 2 | 只准放 `$HOME` 下的專用目錄 | `$HOME/cloud360-upgrade/`，該目錄本身 `700`。**不得放在 repo 工作區或其任何子目錄** | `realpath <dump>` 的前綴為該目錄；且 dump 存在期間 `git -C <repo> status --porcelain` **不出現任何 `.sql`** |
| 3 | 驗證通過後立即刪除並記錄 | 七步程序的最後一步刪除 dump | 該目錄下無殘留 `.sql`；升版紀錄有刪除時間 |

```bash
mkdir -p "$HOME/cloud360-upgrade" && chmod 700 "$HOME/cloud360-upgrade"
( umask 077; docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env \
    exec -T db pg_dump -U postgres cloud360 > "$HOME/cloud360-upgrade/cloud360-dump-$(date +%Y%m%d).sql" )
stat -c '%a %U' "$HOME/cloud360-upgrade/"*.sql     # 必須是 600 ＋ 你的帳號
git -C "$(pwd)" status --porcelain | grep -c '\.sql' # 必須是 0
```

**不加密 dump 檔本身**是刻意的：多一個金鑰要管，而升版窗口正是最不該增加失敗模式的時候
——回退路徑就是那份 dump，金鑰遺失等於備份等於沒有。它的離線面由 5.1 的全碟加密涵蓋，
5.3 管的是**線上**面（主機執行中時誰讀得到它、它會不會被誤推進版控）。兩者不可互相替代。

#### 5.4 PG 16 → 18 升版程序（手動路徑；七步）

**只走 dump/restore。** `pg_upgrade` 需要舊（16）與新（18）兩套 binaries 連同舊 data
directory，本部署形狀下沒有承載者。

**開始之前必須先過 5.5 的磁碟門檻與 5.6 的記憶體處置。空間不足時不得開始升版**——
七步程序在中途耗盡空間，會同時失去「新 volume 建好」與「dump 檔完整」兩者，而回退路徑
**就是那份 dump**。

| 步 | 動作 | 注意 |
|---|---|---|
| 1 | 量 `DBSIZE`／`DUMPSIZE`，核對 5.5 的逐掛載點門檻 | **量的是舊 volume**（現名見步 4） |
| 2 | 停 `backend`（`docker compose stop backend`） | 步 4 有一條硬條件依賴它：backend 必須是停止的 |
| 3 | 依 5.3 產生 dump（`umask 077`，放 `$HOME/cloud360-upgrade/`） | 三條要求缺一不可 |
| 4 | 以 **新 volume** 起 PG 18 | 見下方兩條硬條件 |
| 5 | 還原 dump，並處理 collation | 基底映像由 musl 換 glibc，text 欄位的既有索引排序與新 libc 不一致：還原後執行 `REINDEX DATABASE cloud360;` |
| 6 | 啟 `backend`，跑 5.7 的手動探測 | 探測回 401 才算通 |
| 7 | 舊 volume ＋ dump **保留至驗證通過**；窗口結束時刪除並記錄 | 見 5.8 |

**步 4 的兩條硬條件**：(a) **不得掛 initdb 目錄**——`/docker-entrypoint-initdb.d/` 內的
`schema_rbac.sql` 會在空 volume 上執行，把即將被還原覆蓋的表先建一遍並重播
`role_permissions`；(b) **backend 必須是停止的**——它的 startup 會跑 `init_db()`（`create_all`
＋ 七支 `_ensure_*`），在還原中途動 schema。

**採用哪一種做法，兩者代價不對稱，請記下實際選的那一個**：

| 做法 | 代價 |
|---|---|
| **裸映像還原**（`docker run` 一個 `pgvector/pgvector:pg18`，只掛新 volume，不用 compose） | 要另寫一次連線參數；但**結構上不可能誤掛 initdb 目錄** |
| **暫移 compose 的 initdb 掛載**（註解掉那一行，還原後復原） | 少一組參數；但**復原那一行是一個人可以忘記的步驟**，忘了之後下一個空 volume 部署就會少掉 schema |

```text
本次升版採用的做法：____________　執行者：____________　日期：____________
```

**volume 命名的完整值**（compose 專案名為 `cloud360`，故具名 volume 的實際名稱是
`cloud360_<宣告名>`）：

| | 宣告名（compose 檔內） | 實際 Docker volume |
|---|---|---|
| 舊（PG 16） | `cloud360_db` | **`cloud360_cloud360_db`** |
| 新（PG 18） | `db_pg18` | **`cloud360_db_pg18`** |

```bash
docker volume ls | grep cloud360      # 兩者在回退窗口內應同時存在
```

**為什麼要改名**：步 4 要求以**新 volume** 起 PG 18，步 7 又承諾**舊 volume** 保留至驗證
通過。在單一 volume 名稱下兩者不可能同時成立——不改名就必須先毀掉舊的，步 7 的回退面
就只剩備份檔一條腿。

**三條排序不變量**（`NFR6.3(b)`）：

1. **先做資料轉換，後合併觸發自動部署。** 反向順序會**靜默成功**：合併先落地會讓
   `deploy.yml` 以 PG 18 映像對**舊 PGDATA** 啟動容器，postgres 拒絕啟動並進入重啟迴圈，
   而站台首頁（靜態檔）仍然正常——第 5.7 節的探測正是為了讓這件事不再靜默。
2. **回滾的覆蓋範圍不對稱。** `deploy.yml` 的 `rollback` job 還原的是**程式碼**
   （last-good commit），它**不會**還原 PGDATA。所以升版窗口內一次自動回滾會讓 PG 16 的
   映像對著 PG 18 的 volume。三個處置選項：(a) 升版窗口內**暫時停用** rollback job；
   (b) 讓它只還原程式碼並接受上述不相容（現況）；(c) 在該窗口內改為人工部署。
   **請記下採用哪一個**，以及若採 (a)，窗口結束後以另一個 PR 復原它，並確認復原後的
   第一次部署真的有 rollback 武裝：

   ```text
   本次升版採用的 rollback 處置：____（a／b／c）
   若採 (a)：復原 PR 連結 ____________　復原後第一次部署 run 連結 ____________
   ```
3. **相容性前置檢查在 `deployment-pipeline` 落地之前只是人工前置。** 即「回滾取出的
   commit 其映像主版本須與當前 PGDATA 相容」目前沒有任何機械檢查，只有本節這段文字。

#### 5.5 磁碟空間門檻（逐掛載點）

**沒有任何一處檢查過主機的磁碟空間，而本單元同時增加三個消費者**：Ollama 模型快取
（`bge-m3` 約 1.2GB，**由部署後的 `ollama pull` 取得後常駐**，不在容器啟動路徑上）、
Redis AOF（隨 session 量成長，受 `maxmemory` 間接約束）、以及升版窗口內的資料庫副本。

**先定義兩個量，否則門檻寫不出來**：

| 量 | 定義與量測 |
|---|---|
| **`DBSIZE`** | **PGDATA 目錄的實際大小**，**不是** `pg_database_size()`（後者不含索引膨脹、不含 WAL、不含其他 database，兩者可差數倍）。**需 root**（`/var/lib/docker` 預設 `0710 root:root`），且**升版前要量的是舊 volume**（改名前／用舊名） |
| **`DUMPSIZE`** | 假設 `pg_dump` 的**預設 plain 格式、未壓縮**。以 `DBSIZE` 為上界估算；**不假設它比較小**——無壓縮的文字輸出對寬表可能更大 |

```bash
sudo du -sb /var/lib/docker/volumes/cloud360_cloud360_db/_data   # DBSIZE（舊 volume）
df -h / /var/lib/docker "$HOME"                                  # 逐掛載點的可用空間
```

| 掛載點 | 升版前所需可用空間 | 涵蓋什麼 |
|---|---|---|
| 承載 Docker volume 的檔案系統（通常 `/var/lib/docker`） | **≥ `DBSIZE` × 2 ＋ max(`DBSIZE` × 0.5, `max_wal_size` 的生效值) ＋ 1.5GB ＋ 2GB** | 新 volume ＋ 保留中的舊 volume（**兩份，不是三份**——dump 在 `$HOME`）；還原期 WAL；模型 volume（含餘裕）；日誌預算上界（見 5.6） |
| `$HOME` 所在檔案系統 | **≥ `DUMPSIZE`** | dump **一份**（5.3 要求它放這裡） |
| 自架 runner 的工作目錄所在檔案系統 | 既有需求，無新增 | `deploy/.env` 極小；`up -d --build` 的建置快取是既有消費 |
| `/`（若上列任一未獨立掛載） | 取該掛載點所涵蓋各項之和 | — |

**還原期 WAL 餘裕為何取「兩者中的大者」**：匯入期間 WAL 的產生量與匯入資料量同級，但
checkpoint 會回收，故比例式餘裕取 `DBSIZE × 0.5`；**但 `max_wal_size` 的預設值就是 1GB**，
所以 `DBSIZE` 小於 2GB 時比例式會低於 WAL 實際可累積的量——故取大者，小型資料庫的下界
即 1GB 而非比例值。

#### 5.6 記憶體上限與日誌上限（本輪為**暫定值**）

**六個服務全部設了 `deploy.resources.limits.memory`，值寫在 `deploy/docker-compose.deploy.yml`
裡（不走環境變數）。** 硬寫的理由是：新增一個 compose 消費的變數就多一個同步點，而本 repo
有這件事的**無聲失敗前例**（`N8N_USER`／`N8N_PASSWORD` 從未被寫入，導致每次部署的架構圖
icons 靜默退回灰底佔位圖）。代價也是它的優點——改容量要走 PR，變成可審查、有版本的變更。
**所以「由部署者依主機餘裕定」的實際語意是「改 PR」**，不是改一個環境變數。

> **⚠ 這一組值是依公開基準推導的暫定值，不是在 `192.168.10.10` 上量出來的。**
>
> | 服務 | 暫定上限 | 依據（公開基準） |
> |---|---|---|
> | `db` | `1g` | `shared_buffers` 預設 128MB ＋ `work_mem` × 連線數 ＋ OS 快取需求 |
> | `backend` | `2g` | Python／uvicorn 行程基線（解譯器＋相依套件本身即數百 MB）× 併發假設 |
> | `redis` | `768m` | 由 `maxmemory` 反推，見下方關係式 |
> | `ollama` | `4g` | `bge-m3` 約 1.2GB ＋ runtime 常駐約 2GB × 安全係數（**兩個數字取自一般認知，未在本主機實測**） |
> | `frontend` | `128m` | nginx 常駐極小 |
> | `cloudflared` | `128m` | tunnel client 常駐極小 |
>
> **兩項給定假設**（本設計給定，可日後複量推翻）：(1) 單主機 staging、單一 uvicorn
> worker、同時處理的 LLM 請求數上限為**個位數**；(2) 同時活躍的 session 數為**個位數到
> 低兩位數**。
>
> **這些是 per-container 上限，不是保留量**，總和超過主機記憶體是正常的。
>
> **這是交付後的 blocking 前置，不是「有空再填」（審查 R-06 定案）**
>
> **觸發條件（二元可判）**：`REDIS_PASSWORD` secret 建立 → 首次部署成功 → **自該次部署起七日內**。
> 在此之前無法量測，因為部署尚未發生、沒有任何真實流量可量（這也是本輪不填一個猜測日期的理由：
> 猜的日期會讓下一個人以為它被評估過）。
>
> **負責人**：Danniel（`REDIS_PASSWORD` 的建立者即量測者——建立 secret 的人是唯一知道首次部署何時
> 發生的人，把兩件事綁在同一個人身上才不會互相等）。
>
> **量測方式（不需放寬任何 ACL，見 §5.11）**：主機上 `docker stats --no-stream` 取六個容器的穩態用量；
> Redis 另以 app 使用者執行 `MEMORY STATS`（`INFO` 不可達，審查 R-01）。
>
> **未完成的後果**：十個記憶體上限與 `maxmemory` 全部停留在「以公開基準推導的暫定值」，
> 而 `OPEN-4` 自己寫明「沒有日期的限期複量會退化成永遠暫定」。**本節被填完之前，
> 不得把這些數字當成已驗證的容量規劃依據。**
>
> **複量期限與擁有者（首次部署後七日內填完）**：
>
> ```text
> 複量負責人：Danniel（已指定，見上）
> 複量期限（日期）：首次部署成功日 + 7 日（實際日期：____________）
> 複量方式：部署後在正常負載下取 `docker stats` 的穩態峰值，改 PR 更新這六個數字
> 複量完成日期與所得數字：____________
> ```

**CI test stack 的值另循一條路**：`deploy/docker-compose.test.yml` 跑在 GitHub-hosted
`ubuntu-latest` 上，其規格是公開文件化的固定值，**不適用主機量測程序**；那四個值只需
保證總和不超過 runner 記憶體並留餘裕（現為 `1g`＋`2g`＋`512m`＋`256m` ≈ 3.75GB）。
**兩份 compose 的記憶體上限值必然不同，這是本項的刻意例外，不是漂移。**

**`maxmemory` 與容器上限的關係式（必須成立，沒有閘門會檢查它）**：

> **`redis` 容器的記憶體上限 ≥ `maxmemory` × 1.5 ＋ 256MB**
>
> 本輪的值：`maxmemory 256mb` → 下界 `256 × 1.5 + 256 = 640m` ≤ 上限 `768m`。**成立。**

| 項 | 依據 |
|---|---|
| × 1.5 | Redis 的 `used_memory` 之外還有 allocator 碎片（`mem_fragmentation_ratio` 一般 1.0–1.5）與輸出緩衝。1.5 是實務的保守下界，**作用是讓關係式可被檢查，不是精確預測** |
| ＋ 256MB | AOF 重寫期間的 copy-on-write 與 `aof_rewrite_buffer`。AOF 由 `NFR4.2` 要求開啟，故此項必存在 |

**關係式不成立的後果**：容器會在 Redis 有機會以 `OOM` 拒絕寫入之前就被 OOM kill
——把一個明確的、可被應用層分類的拒絕換成硬重啟，而硬重啟在 `restart: unless-stopped`
之下變成反覆重啟，且它比拒絕難診斷得多（OOM kill 只在核心日誌裡）。

> ⚠ **本段原本寫的是「在 Redis 有機會執行 `allkeys-lru` 淘汰之前」。`maxmemory-policy`
> 已於 `U10` 改為 `noeviction`（見下方），所以「優雅的淘汰」這個對照項不再存在**——
> 現在的對照項是「可偵測的寫入拒絕」。關係式本身與它的下界數字**沒有改變**。**注意訊號的可達性（審查 R-01）**：淘汰計數雖然在 `INFO` 裡有 `evicted_keys`，但 `INFO` 的 ACL 分類是 `@slow @dangerous`，**本專案設定的兩個身分都不能執行它**——`default` 只有 `@connection`，app 使用者是 `+@all -@admin -@dangerous`。實際可用的替代訊號是以 app 使用者執行 `MEMORY STATS`，以及在主機上跑 `docker stats` 看容器層用量；兩者都不需要放寬任何 ACL。

**`maxmemory 256mb` 的暫定依據**（與六個上限同一形狀：公開基準 ＋ 限期複量）：單一 session
的 key 大小上界（`BrainSession` 除 `messageHistory` 外全是識別碼與短字串，量級由
`messageHistory` 決定）× 24 小時內活躍 session 數上界（TTL 24 小時、每次互動續期）×
安全係數。**該項待確認已由 `U10` 關掉**：`messageHistory` 有截斷策略了——每段上限
`BRAIN_SESSION_HISTORY_MAX`（值 200，required、**無預設**），上限**每段獨立計算**而
段數上界為 3（`shared`／`workspace`／`assessment`），故單一 session 的歷程上界為
`3 × 200 × 每則約 500 B ≈ 300 KB`，而 `300 個同時存活 × 300 KB = 90 MB`，為
`maxmemory 256mb` 的 **35%**。推導因此成立，不需要反過來以 `maxmemory` 約束歷程。

> **這個上界有一項仍然是假設**：每則 500 B 是 *假設值*、不是量測值。單則訊息另有
> 一道 4000 字元的硬上限（程式常數），故最壞情況遠大於以平均值算出的 300 KB——
> 「300 個同時存活」在**平均**假設下成立，在最壞情況下不成立。偵測面是
> `noeviction` 的寫入拒絕與以 app 身分執行的 `MEMORY STATS`，而非事前保證。
>
> **另一項不在本上界之內**：同一個 session key 之下的工作項集合由 `U12` 擁有，
> 它的大小上界不由 `U10` 的歷程上限約束。

**`maxmemory`／`maxmemory-policy`／`appendonly` 三項一律住在 compose 的 `command:`，
不得移入掛載的 `redis.conf`**：`redis-server` 的 CLI 旗標會**靜默覆寫**檔內同名指令，
兩處都寫會讓檔內那份無聲失效；且兩個數字在同一個服務區塊內才能一眼核對上面的關係式。

#### `maxmemory-policy` 為 `noeviction`（`U10`／`NFR4.50`，由 `allkeys-lru` 改）

**部署端必須知道的行為變更，不只是一個設定值**：

- **為什麼改**：本設計寫入的**每一個** key 都帶 TTL（五個 `K-09` 方法全部續期，
  且 `U12` 的工作項集合住在同一個 key 之下），所以 session **只會因 TTL 到期而消失**。
  `allkeys-lru` 之下它**還會因為容量不足而消失**，而這兩種結果在使用者眼中**完全
  相同**——一個是正常行為、一個是容量故障。不可區分的故障等於不可偵測，所以改成讓
  容量問題**有聲**。
- **`noeviction` 之下實際會發生什麼**：Redis 對**寫入**回
  `OOM command not allowed when used memory > 'maxmemory'`，對**讀取照常服務**。
  後端把它對應成 `SessionBackendUnavailable` 並帶原因碼 `redis_oom`，與
  「Redis 不可達」（`redis_unreachable`）在日誌上**可區分**。
- **降級形狀，明寫**：既有 session **仍讀得到**，只是**不能再寫**。這比「少數人無聲
  失去整個 session」好得多，且是**可偵測的**。
- **運維動作**：日誌出現 `reason=redis_oom` 時，處置是調高 `maxmemory`（連同上面
  的關係式一起調容器上限）或縮小 `BRAIN_SESSION_HISTORY_MAX`，**不是**改回
  `allkeys-lru`——改回去只會讓同一個問題變回無聲。
- **這個設定讀不回來**（與 `maxmemory`／`appendonly` 同）：`CONFIG GET` 與 `ACL LIST`
  都是 `@admin @dangerous`，兩個設定身分都不能執行。部署時能證明的是**三個旗標都進了
  容器 argv**（`deploy.yml` 的「Verify the Redis ACL actually took effect」第 3 步會檢查
  `--maxmemory-policy` 存在，但**不會**檢查它的值）。改值的唯一方式仍是改 compose 再重部署。

#### 部署後的 session 還原驗證（`U10`／`NFR4.64`）

`deploy.yml` 新增一個步驟 **`Verify sessions survive a Redis restart (NFR4.53-57)`**，
位置在**全部既有健康檢查之後、記錄 last-good 之前**（即部署序列的最後一道驗證）。

它做的事：以 app ACL 身分寫入一個 fixture session（三段、各有訊息、**三組不同的**
作業對象、`pageModes` 其中一鍵為 `isolated`、TTL 刻意設為 **3600** 而非 86400）→
`docker compose restart redis` → **以 app 身分實際讀回 fixture 成功**為等待條件 →
逐欄比對 → 刪除 fixture。

三件部署端必須知道的事：

1. **這一步會中斷當下使用者的 session，而且沒有被緩解。** `cloud360.danniel.cc`
   經 Cloudflare Tunnel 對外，可能有人正在用。**「反正 stack 剛重啟過」是假的**——
   上面的部署步驟用 `up -d --build --remove-orphans`、**沒有** `--force-recreate`，
   所以未變更的 redis 容器**不會**被重建、它的 session **不會**已經消失。
   能做的只是把這一步放在**最後**，使中斷發生在部署已確認可用之後，不會在一次失敗的
   部署上再疊一次中斷。
2. **等待條件刻意不是 healthcheck。** compose 裡的 `redis-cli ping | grep -q PONG`
   自己的註解就寫著它「**在 AOF 載入期間會通過**」且「不證明 ACL 使用者可用」。
   等它轉綠可能讀到一個載入中的半套資料集——或更糟，在一個空的資料集上回報成功。
   AOF 載入期間資料指令會回 `-LOADING`，所以**一次成功的 `HGET`** 才是資料集真的在
   那裡的最早時刻。重試上限 60 次 × 2 秒 = 總逾時 120 秒。
3. **失敗時讓 deploy job 失敗**，觸發既有的 rollback job（還原 last-good、開 revert
   PR、dispatch Deploy Doctor）。**不是**記一行 warning 繼續。
   `NFR4.57` 的 TTL 斷言是**區間**而非等值（重啟會吃掉幾秒，斷言等值會讓這道檢查
   變成不穩定的）；用 3600 這個與生產 86400 不同的值，使「被重設為滿額」也會被抓到。

**日誌上限（`logging.options`）**：現值 `max-size: 50m`、`max-file: "5"`，加在**兩份
compose 的全部服務**上。

> **總量上界：`max-size` × `max-file` × 服務數 不得超過 2GB。**
> 本輪：`50m × 5 × 6 = 1.5GB`，成立。這個上界是 5.5 磁碟公式裡「日誌預算」那一項的值
> ——若這兩個值完全自由，該項就是一個無界的自由變數（`100m × 5 × 6` 就是 3GB，單這一項
> 吃掉整個餘裕），公式會失去定義。
>
> 上界**只約束 deploy stack**；CI test 的日誌隨 stack 消失。

**方向要寫對**：今天的無界 `json-file` 並不是「保留無限」，而是「保留到**磁碟寫滿**、
然後全站與全部日誌一起失去」。改為有界**移除了一條會摧毀全部證據的路徑**，代價只落在
長回溯調查。另外 `max-size × max-file` 的乘積是**容量**上限而非保留**期**；保留期 =
容量 ÷ 寫入速率，而速率未知且逐服務不同（`backend` 遠高於 `cloudflared`）。

#### 5.6.1 升版窗口內必須另行處置 `db` 的記憶體上限

`db` 的容器記憶體上限在升版窗口內同樣生效，而 **dump/restore 是該容器生命週期中記憶體
用量最異常的一段**（大批 `COPY`、索引重建、`maintenance_work_mem`）。以「正常使用下的
穩態峰值」得到的值，正是**最可能在還原中途被突破**的那一個——而突破的後果是 OOM kill
＋ `restart: unless-stopped` 的重啟迴圈，發生在回退**依賴 dump 完整性**的那個窗口裡。

**處置：升版期間暫時提高到一個明確的值（不是移除），還原與驗證通過後恢復原值，並在升版
紀錄寫下「已恢復」。**

**為何是「提高到明確值」而不是「移除」**：移除上限之後，升版期的 `db` 若吃光主機記憶體，
受害者是**同一台主機上的其他五個容器**，而 5.1 的全碟加密使主機重開需要解鎖（見 5.2）。

**為何不把上限常設為足以涵蓋還原峰值**：那會讓正常運行期間的上限失去保護意義——上限的
目的就是擋住失控的那一個容器。

```text
升版期間 db 的暫時上限：____________（例：4g）
還原與驗證通過日期：____________
**已恢復**原值（1g）日期與 PR／commit：____________
```

#### 5.7 資料面探測（手動升版路徑那一份）

`deploy.yml` 的自動部署路徑已內建這個探測（`deploy` job 一個獨立步驟，`rollback` job
併入其健康檢查迴圈）。**手動升版路徑不經 `deploy.yml`**，所以步 6 要自己跑一次：

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  --connect-timeout 5 --max-time 10 \
  -X POST http://127.0.0.1:8090/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"__cloud360_deploy_probe_no_such_user__","password":"probe"}'
```

**通過條件是 `401`，不是 2xx。** 使用者名稱刻意是一個**不存在**的固定值：`login` 的處理
在任何密碼比對之前先查資料庫，所以 401 同時證明 `frontend → backend` 與 `backend → db`
都通。**2xx 反而代表探測寫錯了**（真的登入成功），所以「回 2xx 才算通」會是一個永遠不會
通過的檢查。它不建帳號、不留稽核列、不需要任何憑證。

**為什麼既有的檢查不夠**：`deploy.yml` 原本的兩個 `curl` 都打 `/`，由 nginx 的
`try_files` 回靜態檔——不經 `location /api/`、不碰 backend、更不碰 db；`db` 的
`pg_isready` 在**容器內部**執行；`depends_on: service_healthy` 只管啟動順序。所以
`backend → db` 斷掉時部署會**綠燈通過**，站台首頁正常而所有需要資料庫的功能全壞。
而把 `db` 移進 `internal` 網段的正是本單元。

**診斷指向（不是通過條件）**：

| 回應 | 指向 |
|---|---|
| `401` | 兩段都通 |
| `502`（持續整個重試窗口） | 最可能是 `backend → db` 斷掉（`create_all` 與七支 `_ensure_*` 都在 startup 路徑上，db 不可達時 uvicorn 不進入服務狀態並反覆重啟）。次要可能：backend 映像本身起不來 |
| `500`／`504`／curl 逾時（`000`） | `backend → redis` 或 `backend → ollama` 斷掉——這兩段**不在** startup 路徑上，所以 backend 會正常服務、在請求處理中才失敗或掛住 |
| `200` 且回 HTML | `/api/` 路由或 `frontend → backend` 斷（落到 `try_files`） |

#### 5.8 回退窗口結束時刪除舊 volume 與 dump，並記錄

回退窗口內舊 volume 與 dump 同時保留。**窗口結束時必須刪除並記錄，否則它們會無限期留著**
——而它們是兩份全庫明文副本。

```text
回退窗口保留期限（自升版完成起）：____________（建議 7 天）
舊 volume（cloud360_cloud360_db）刪除時間：____________
dump 檔刪除時間：____________
```

```bash
docker volume rm cloud360_cloud360_db
rm -f "$HOME/cloud360-upgrade/"*.sql
ls -la "$HOME/cloud360-upgrade/"      # 應無殘留 .sql
```

#### 5.9 `rollback` job 加上探測後的實際耗時

| 項目 | 值 | 狀態 |
|---|---|---|
| `deploy` job 逾時 | 30 分鐘 | 既有 |
| `rollback` job 逾時 | **20 分鐘** | 既有 |
| `deploy` 側探測 | `N=30`、間隔 5s、單次 `--connect-timeout 5 --max-time 10` → 最壞 `30 × (10+5) = 450s ≈ 7.5 分` | 本輪設定 |
| `rollback` 側探測（併入既有迴圈，每輪兩個 request） | `N=18`、間隔 5s、同樣的單次逾時 → 最壞 `18 × (10+10+5) = 450s ≈ 7.5 分` | 本輪設定 |
| `rollback` job 的其餘既有消費 | checkout ＋ `render-env.sh` ＋ **無界的 `up -d --build`** ＋ 該步驟之後三個 `if: always()` 步驟 | — |

**約束式**：`N × (T + 間隔) ≤ 1200s −（`up -d --build` 實測）−（三個 `if: always()` 步驟
實測）−（checkout ＋ render 實測）− 安全餘裕。

> **⚠ 這條式子的右側本輪未實測，`up -d --build` 是其中的無界項。** 選 `N=18` 而非 30 是
> 為了留出餘裕（450s 之後仍有 750s 給其餘各項），但**這不是一個量出來的結論**。逾時的
> 後果是 **rollback 本身被砍掉**：站台留在壞版本、revert PR 沒開。
>
> **首次部署後請實測並填回這裡**：
>
> ```text
> up -d --build 實測耗時：____________
> 三個 if: always() 步驟合計：____________
> checkout ＋ render-env.sh：____________
> rollback job 總耗時：____________　（逼近 20 分鐘時：縮短窗口或提高 timeout-minutes，
>                                    兩者都是需要決定的事，不是實作者可以順手挑的）
> ```

**為何以 `N` 而非 `T` 吸收差額**：`T` 壓太小會讓探測失去區分「backend 還在跑
`init_db()`」與「資料面真的斷了」的能力，而那正是這個窗口存在的理由。附帶：`N=18` 配
上每輪最壞 25s，在**牆鐘**上比它取代的 `30 × 5s = 150s` 迴圈更有耐心，不是更沒耐心。

#### 5.9.1 `deploy` job 的耗時預算（審查 R-03 補入；上一版只算了 rollback）

`deploy` job 的 `timeout-minutes` 是 **30**（`deploy.yml:28`），比 `rollback` 的 20 寬鬆，
但本輪加進這一側的東西**比 rollback 多**，而原本只在探測步驟的註解裡算了自己那一步
（`30 × (10 + 5) = 450s`）——**右側從來沒有列出來**。逾時的後果比 rollback 更糟：
`deploy` job 被砍會被視為部署失敗，於是在一次**好的**合併上觸發自動 `rollback` ＋ revert PR。

同一個 job 內的五項消費，以及哪幾項有界：

| 項目 | 上界 | 有界？ |
|---|---|---|
| `up -d --build` | 取決於 Docker layer cache 與映像下載 | **無界，必須實測** |
| 等待 frontend 迴圈 | `30 × (10 + 5) = 450s` | 有界（本輪為 `curl` 補了 `--max-time 10`；在此之前**無界**） |
| `ollama pull bge-m3` | 首次約 1.2GB 下載；之後為一次 registry 往返 | **無界，必須實測（首次／後續分開記）** |
| Redis ACL 反向探測 | 三個 `exec`／`inspect`，數秒 | 有界 |
| 資料面探測 | `30 × (10 + 5) = 450s` | 有界 |
| 等待 tunnel 迴圈 | `24 × (10 + 5) = 360s` | 有界（同樣是本輪補 `--max-time` 才有界） |

**約束式**：`450 + 450 + 360 + (up -d --build 實測) + (ollama pull 實測) + 數秒 ≤ 1800s`。
已知有界部分合計 **1260s**，所以兩個無界項合計必須 **≤ 540s（9 分鐘）**。

**必填欄位（實測後補上，留空等於沒有預算）**：

- `up -d --build` 實測耗時（冷快取／熱快取）: ____ / ____
- `ollama pull` 實測耗時（首次下載／模型已在 volume）: ____ / ____
- 兩者合計是否 ≤ 540s: ____
- 量測日期與量測者: ____

**若合計超過 540s**，處置是降低探測的重試次數（`N`）而不是延長 `timeout-minutes`——
把逾時放寬會同時延長「站台已經壞掉但 job 還在等」的時間。

#### 5.9.2 Ollama 的版本不可重現（審查 R-05）

`deploy/docker-compose.deploy.yml` 的 `ollama` 服務用 **`ollama/ollama:latest`**，
**沒有釘版本**——而同一輪改動的另兩個映像都釘了主版本（`pgvector/pgvector:pg18`、
`redis:8-alpine`）。本專案是 deploy-on-merge，所以**任何一次重新部署都可能靜默拉到不同的
Ollama 版本**，而 compose 的改動沒有任何 CI 閘門看得到（見 `infrastructure-design` `§六`
的九項無閘門項目）。模型快取 volume `ollama_models` 會留存，但 runtime 版本變動可能改變
embedding 行為，或讓以 `ollama list` 為基礎的 healthcheck 語意改變。

**為什麼本輪不逕自釘一個版本號**：要挑版本必須先確認它與 `bge-m3`（dense 1024）相容；
憑猜寫一個數字會讓下一個人以為那個版本被驗證過，比不釘更糟。

**處置（依賴可重現性之前必做）**：確認相容版本後把 `:latest` 換成具體 tag，並把該版本與
相容性確認結果記在這一節。負責人與期限: ____


#### 5.10 新增的 GitHub secret

本單元新增**一個**憑證型 secret：**`REDIS_PASSWORD`**。

```bash
openssl rand -hex 32     # 產生它。值不得含 `$`（見下）
```

- **必須落在 secrets，不得落在 variables。** Actions variables 為明文、UI 可回讀、且在
  workflow log 中**不遮罩**，而本 repo 為 public、Actions log 公開可讀——一次意外 echo
  即等同公開發布。新增後實地查證兩次：

  ```bash
  gh api repos/<owner>/<repo>/actions/secrets   --jq '.secrets[].name'
  gh api repos/<owner>/<repo>/actions/variables --jq '.variables[].name'
  # REDIS_PASSWORD 必須出現在第一份、且不得出現在第二份
  ```

  **若曾誤存為 variable，僅搬移不足以結案，必須重新產生金鑰**——「應該沒人看過」是沒有
  證據的假設。
- **值不得含 `$`**：docker compose 會對 `--env-file` 的值做內插，`ab$cd` 被**無聲截斷**成
  `ab`，Redis 照樣接受該 ACL 密碼、`redis-cli ping` 照樣回 PONG、healthcheck 照樣過。
  `deploy/render-env.sh` 會擋下這種值（以及空值）。
- **其餘六個 brain-infra 變數不是 secret**，也**不要**為它們新增 secret：它們是
  `render-env.sh` 內的字面值。把它們做成 `deploy.yml` 的 `env:` 會讓六個沒有對應 secret
  的名字解析成**空字串**，而 `EMBEDDING_PROVIDER` 缺值會讓 backend 拒絕啟動 → 部署紅燈
  → 觸發自動 rollback ＋ revert PR。

#### 5.11 Redis ACL 與網段分段：兩件不要「順手修正」的事

1. **`deploy/docker-compose.deploy.yml` 的 `networks:` 一律不帶 `internal: true`。**
   它會斷開該網段的**對外出口**，而 `ollama` 只掛在 `internal` 上——模型永遠拉不下來，
   且失敗形式是啟動時的網路錯誤，不是設定錯誤訊息。分段本身不需要它：一個普通的
   user-defined bridge 沒有 `ports:` 就沒有 host 端口映射，跨 bridge 流量本就被 Docker
   的隔離規則阻擋。
2. **`cloudflared` 不得加進 `internal`。** 它是本 stack 唯一對網際網路持續開著連線的
   容器；把它移出資料面（3 → 0 個可直達的資料面服務）就是分段的主要價值。

**分段隔離什麼、不隔離什麼**（不要讀成比實際更強）：同一網段的成員彼此可達**全部端口**
（ICC 預設開啟），所以 `internal` 上的 `db` 若被攻陷，它**仍然**碰得到 Redis 的全部
session 與零認證的 Ollama；而 bridge 網段的 subnet 從 host 直接可路由，所以
`192.168.10.10` 上的**任何行程**（包含自架 runner）都能以容器 IP 直連 `redis:6379` 與
`ollama:11434`，**完全不需要 `ports:`**。分段隔離的是容器之間，不隔離 host 與容器。

**三個 healthcheck 的已知盲點（刻意接受，不是漏洞）**：

| healthcheck | 不證明什麼 |
|---|---|
| `redis-cli ping` | **不證明 ACL 使用者可用**——`ping` 在 `default` 下也會過；且它在 AOF 載入期間即可回應，所以 `service_healthy` 通過之後、資料集載入完成之前，其他指令會回 `LOADING` |
| `ollama list`（即 `/api/tags`） | **不證明模型存在**——無模型時回空清單而非錯誤。「模型在不在」由部署後的 `ollama pull` 步驟保證 |
| `pg_isready` | 在 **db 容器內部**執行，不證明 `backend` 連得到它。那由 5.7 的探測負責 |

---

### 6. 相關文件

| 文件 | 說明 |
|---|---|
| `schema_rbac.sql` | **建表 + 預設資料（含角色矩陣）** |
| `aidlc/spaces/default/intents/260802-default/construction/plans/schema-rbac-notes.md` | SQL 區塊說明 |
| `aidlc/spaces/default/intents/260802-default/construction/plans/role-permission-design.md` | 角色／細項語意 |
| `backend/.env.example`、`frontend/.env.example`、`deploy/.env.example` | 環境變數範本 |
| `backend/Dockerfile` | 純 Python 映像（OpenRouter／LangGraph；無 Claude CLI） |
| `deploy/docker-compose.deploy.yml` | staging／自架 compose |
| `.github/workflows/deploy.yml` | `ut` → 192.168.10.10 自動部署 |
| `aidlc/spaces/default/intents/260802-default/construction/a1/code-generation/a1-a3-multi-agent-summary.md` | A1↔A3 協作實作摘要 |

---

## English Version

### LLM stack（required for A1 / A3 / optimize）

Runtime path: **FastAPI → LangGraph／LangChain → OpenRouter HTTP**.  
You still need **`OPENROUTER_API_KEY`**. The backend image no longer installs Node or `@anthropic-ai/claude-code`. Rebuild the backend image when upgrading so old CLI layers are dropped.

Optional: `LLM_MAX_OUTPUT_TOKENS` (default `12000`) and `LLM_XML_CONTEXT_MAX_CHARS` to reduce OpenRouter 402 / credit pressure. Keep `ANTHROPIC_API_KEY` empty and `ANTHROPIC_BASE_URL=https://openrouter.ai/api`.

### Env vars

- **Backend** (`backend/.env` from `.env.example`): set `DATABASE_URL`, rotate `JWT_SECRET`, set `CORS_ORIGINS` to the real frontend origin(s), and configure OpenRouter／LLM／token-limit keys for that environment.  
- **C1 FinOps**: set `GCP_BILLING_API_KEY`（required for live GCP catalog prices）. Optionally set `AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY` for Price List Query (pricing:* only, ADR-0018); without them AWS falls back to the public Bulk Price List. Azure needs no key. Legacy `COST_PRICING_STUB`／diagrams cost API have been retired (U3); deploy U3 only with U8.  
- **Frontend** (`frontend/.env` / CI): set `VITE_API_BASE_URL` to the real API root (no trailing slash). Optional `VITE_WS_BASE_URL`; otherwise derived from the API base (`http→ws`, `https→wss`). Rebuild after changing Vite env.  
- **Compose** (`deploy/.env` from `deploy/.env.example`): used with `deploy/docker-compose.deploy.yml`. Staging CI renders the same keys via `deploy/render-env.sh` from GitHub Secrets.  

### Deploy paths

- **Local**: set `OPENROUTER_API_KEY`; run API + Vite with matching CORS／API URL.  
- **Docker Compose**: `docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env up -d --build` (rebuild drops the old Claude CLI image layers).  
- **Project staging**: push／merge to `ut` → `.github/workflows/deploy.yml` on self-hosted runner → `https://cloud360.danniel.cc`.  

No new SQL is required for the A1↔A3 optimize feature; schema remains `schema_rbac.sql`.

### Database

**Script path (repo root):** `schema_rbac.sql`

```bash
psql "$DATABASE_URL" -f schema_rbac.sql
```

Creates: the **`vector` extension** (`CREATE EXTENSION IF NOT EXISTS vector`, the first
statement after `BEGIN;`), `users`, `user_diagrams`, `diagram_shares`, `user_diagram_chats`,
**`architecture_reviews` (A3)**, **`wa_lenses` (editable offline Lens)**, `role_permissions`,
plus `last_opened_diagram_id`.  
Seeds ~**352** `role_permissions` rows. It does **not** create a fixed-password admin user.

The whole script is ONE transaction, so a server without pgvector aborts it and creates
**no tables at all** — not just the memory tables. The db image must be
`pgvector/pgvector:pg18` in all three composes. Details, the second carrier
(`backend/database.py::_ensure_vector_extension()`, which must run BEFORE
`Base.metadata.create_all()`), and the verification commands are in §2.2.6 of the
Chinese half above.

**A3** `architecture_reviews` stores review scores/findings/suggestions. **`wa_lenses`** stores the active Custom Lens JSON editable by users with **A3.review** (default: Security_Reviewer VER; reviews resolve DB-first, then file fallback). Existing DBs: re-run `schema_rbac.sql` (`IF NOT EXISTS`) or rely on backend `_ensure_a3_schema()` on startup.

**If you create empty tables without seeding `role_permissions`, the matrix is entirely empty** — no view/edit/review for any role, Sidebar stays empty, APIs return 403. Always run `schema_rbac.sql` (or confirm ~352 rows after backend empty-DB seed).

Re-running **wipes and re-seeds** `role_permissions` (backup first if customized). Bootstrap admin creation is handled by backend startup via `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`, not by this SQL script.
