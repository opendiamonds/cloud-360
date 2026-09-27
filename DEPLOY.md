# Cloud-360 部署環境設定說明（Deploy README）

> 給要把本專案部署到**另一個環境**（本機／staging／新機器）的人。  
> 前後端分服務部署時，請特別核對 API／CORS／資料庫三塊。  
> **A1 產圖、A3 評核建議、A1↔A3「優化」協作**皆依賴 **OpenRouter + Claude Code CLI**（見第 0 節）。

---

## 中文版

### 0. LLM 執行鏈路（必讀｜本次更新）

產品**不是**直接呼叫 Anthropic 官方 API，而是：

```text
後端 FastAPI
  → Python 套件 claude-agent-sdk（ClaudeSDKClient）
    → 本機／容器內子行程：Claude Code CLI（@anthropic-ai/claude-code）
      → HTTP：OpenRouter（ANTHROPIC_BASE_URL=https://openrouter.ai/api）
        → 模型（例：google/gemini-3.7-flash）
```

| 元件 | 角色 | 缺了會怎樣 |
|---|---|---|
| `OPENROUTER_API_KEY` | 真正計費、出模型回應 | A1／A3／優化 API 回 500 或錯誤訊息 |
| Claude Code CLI | Agent SDK 的 runtime（子行程） | 請求時失敗：找不到 `claude`／CLI |
| `claude-agent-sdk` | Python 依賴（`requirements.txt`） | 後端無法 import／啟動後相關路由掛掉 |

**仍使用 OpenRouter。** Claude Code CLI 只是殼；credits／402 等錯誤來自 OpenRouter 額度或 `max_tokens` 預扣。

#### 0.1 哪些功能需要 CLI＋OpenRouter

| 功能 | 程式入口 |
|---|---|
| A1 對話產圖 | `backend/services/design_agent.py` |
| A3 改善建議 | `backend/services/review_agent.py` |
| Offline Lens agent 填答 | `backend/services/wa_lens_engine.py` |
| A3「優化」（Design↔Review） | `backend/services/wa_collab_orchestrator.py` |

離線規則打分／啟發式備援可不靠 LLM；但完整建議與協作優化**必須**有 CLI＋金鑰。

#### 0.2 各部署方式如何取得 Claude Code CLI

| 部署方式 | CLI 怎麼來 | 你要做的事 |
|---|---|---|
| **Docker 映像（建議）** | `backend/Dockerfile` 已 `npm install -g @anthropic-ai/claude-code` | `docker compose … --build`；確認 build 有網路可連 nodesource／npm |
| **本機直接跑 uvicorn** | 主機自行安裝 Node 22＋CLI | 見下方「本機安裝 CLI」 |
| **既有容器升級本次功能** | 需**重建** backend image（舊 image 若沒裝 CLI 會掛） | `up -d --build`，不要只用舊 image restart |

本機安裝 CLI（非 Docker）：

```bash
# 需 Node.js 18+（建議 22，與 Dockerfile 一致）
node -v
npm install -g @anthropic-ai/claude-code
which claude   # 應能找到
claude --version
```

容器內驗證（部署後）：

```bash
docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env exec backend which claude
docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env exec backend claude --version
```

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
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/cloud360` | 改成該環境 PostgreSQL 連線字串 |
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

```bash
# 先設好該環境的 DATABASE_URL
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DBNAME'

psql "$DATABASE_URL" -f schema_rbac.sql

# 若 DB 在 Docker 內，範例：
# docker exec -i <db-container> psql -U postgres -d cloud360 < schema_rbac.sql
```

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
| `estimate_sets` | 上傳批次根；`diagram_id` 純標籤（不 FK、不參與授權）；`is_saved` 為 false 時為分析草稿，需命名儲存後才進歷史 |
| `estimates` | 每雲一列；同 Set 內 `cloud` UNIQUE |
| `estimate_line_items` | 解析明細；機械檢查不落庫 |
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

1. **`role_permissions`**：寫入設計預設矩陣（約 **308** 列，11 角色 × 各 Story）。  
2. **`users`**：只建表，不建立固定密碼管理員。

後端若在**空庫**啟動，`init_db()` 也會：建表、必要時 seed `role_permissions`。
Local 環境仍會 seed demo persona 帳號；test/ci 只會建立 `admin/admin123` 供自動化測試使用；staging/production 不會建立固定密碼使用者。全新部署若需要 bootstrap admin，請在第一次啟動前設定 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD` 為強隨機臨時密碼，登入後立刻輪替或清除該 secret。
**新環境仍建議先跑 `schema_rbac.sql`**，行為與文件一致、不依賴啟動順序。

#### 2.4 重要：若沒跑 seed，角色細項會是「全空」

| 情況 | 結果 |
|---|---|
| 只建空表、**沒有**插入 `role_permissions` | 矩陣**全空**（所有角色對所有功能都無檢視／編輯／審核）→ Sidebar 幾乎看不到功能、API 易 403 |
| 有跑 `schema_rbac.sql`（或後端空表自動 seed） | 有設計預設權限；需搭配既有管理員或 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD` 建立的 bootstrap admin 調整 |

因此：**新環境請務必執行 `schema_rbac.sql`（或確認啟動後 `role_permissions` 列數約 308）**，不要只建表不塞預設。

驗證：

```bash
psql "$DATABASE_URL" -c "SELECT count(*) FROM role_permissions;"   -- 預期約 308
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

- [ ] Backend image **重建**（含 `@anthropic-ai/claude-code`）  
- [ ] 容器內 `which claude` 成功  
- [ ] `OPENROUTER_API_KEY` 已設且有餘額  
- [ ] `ANTHROPIC_API_KEY` 為空；`ANTHROPIC_BASE_URL` 指向 OpenRouter  
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
3. 準備 LLM：OpenRouter 金鑰 ＋ **Claude Code CLI**（Docker build 或本機安裝）  
4. 設定後端 `.env`／`deploy/.env`（含 `CORS_ORIGINS`、`JWT_SECRET`、LLM／token 變數，以及 **C1 的 `AWS_*`／`GCP_BILLING_API_KEY`**；全新 staging 可選 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`）並啟動 API
5. 設定前端 `VITE_API_BASE_URL` 後 build／部署  
6. 用既有管理員或 bootstrap admin 登入 → **立刻輪替臨時密碼／清除 bootstrap secret** → 調整角色權限
7. 依第 3.4／3.5 節做 A1／A3／優化與成本頁煙測  
8. **首次部署 brain-infra（Redis／Ollama／PG 18）之前，逐項做完第 5 節的前置條件**  

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

**關係式不成立的後果**：容器會在 Redis 有機會執行 `allkeys-lru` 淘汰之前就被 OOM kill
——把一個優雅的淘汰換成硬重啟，而硬重啟在 `restart: unless-stopped` 之下變成反覆重啟，
且它比淘汰難診斷得多（OOM kill 只在核心日誌裡）。**注意訊號的可達性（審查 R-01）**：淘汰計數雖然在 `INFO` 裡有 `evicted_keys`，但 `INFO` 的 ACL 分類是 `@slow @dangerous`，**本專案設定的兩個身分都不能執行它**——`default` 只有 `@connection`，app 使用者是 `+@all -@admin -@dangerous`。實際可用的替代訊號是以 app 使用者執行 `MEMORY STATS`，以及在主機上跑 `docker stats` 看容器層用量；兩者都不需要放寬任何 ACL。

**`maxmemory 256mb` 的暫定依據**（與六個上限同一形狀：公開基準 ＋ 限期複量）：單一 session
的 key 大小上界（`BrainSession` 除 `messageHistory` 外全是識別碼與短字串，量級由
`messageHistory` 決定）× 24 小時內活躍 session 數上界（TTL 24 小時、每次互動續期）×
安全係數。**一項待確認**：`messageHistory` 若沒有截斷策略，單一 session 可無限成長，
這個推導就不成立，必須反過來以 `maxmemory` 約束 `messageHistory`（`U10` 確認）。

**`maxmemory`／`maxmemory-policy`／`appendonly` 三項一律住在 compose 的 `command:`，
不得移入掛載的 `redis.conf`**：`redis-server` 的 CLI 旗標會**靜默覆寫**檔內同名指令，
兩處都寫會讓檔內那份無聲失效；且兩個數字在同一個服務區塊內才能一眼核對上面的關係式。

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
| `backend/Dockerfile` | 內建 Node 22 ＋ Claude Code CLI |
| `deploy/docker-compose.deploy.yml` | staging／自架 compose |
| `.github/workflows/deploy.yml` | `ut` → 192.168.10.10 自動部署 |
| `aidlc/spaces/default/intents/260802-default/construction/a1/code-generation/a1-a3-multi-agent-summary.md` | A1↔A3 協作實作摘要 |

---

## English Version

### LLM stack（required for A1 / A3 / optimize）

Runtime path: **FastAPI → `claude-agent-sdk` → Claude Code CLI subprocess → OpenRouter**.  
You still need **`OPENROUTER_API_KEY`**. The CLI is only the Agent SDK shell (`npm i -g @anthropic-ai/claude-code`). The official Docker image installs it in `backend/Dockerfile`; bare-metal uvicorn hosts must install Node + CLI themselves. Rebuild the backend image when upgrading this feature.

Optional: `LLM_MAX_OUTPUT_TOKENS` (default `12000`) and `LLM_XML_CONTEXT_MAX_CHARS` to reduce OpenRouter 402 / credit pressure. Keep `ANTHROPIC_API_KEY` empty and `ANTHROPIC_BASE_URL=https://openrouter.ai/api`.

### Env vars

- **Backend** (`backend/.env` from `.env.example`): set `DATABASE_URL`, rotate `JWT_SECRET`, set `CORS_ORIGINS` to the real frontend origin(s), and configure OpenRouter／LLM／token-limit keys for that environment.  
- **C1 FinOps**: set `GCP_BILLING_API_KEY`（required for live GCP catalog prices）. Optionally set `AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY` for Price List Query (pricing:* only, ADR-0018); without them AWS falls back to the public Bulk Price List. Azure needs no key. Legacy `COST_PRICING_STUB`／diagrams cost API have been retired (U3); deploy U3 only with U8.  
- **Frontend** (`frontend/.env` / CI): set `VITE_API_BASE_URL` to the real API root (no trailing slash). Optional `VITE_WS_BASE_URL`; otherwise derived from the API base (`http→ws`, `https→wss`). Rebuild after changing Vite env.  
- **Compose** (`deploy/.env` from `deploy/.env.example`): used with `deploy/docker-compose.deploy.yml`. Staging CI renders the same keys via `deploy/render-env.sh` from GitHub Secrets.  

### Deploy paths

- **Local**: install Claude Code CLI on the host; run API + Vite with matching CORS／API URL.  
- **Docker Compose**: `docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env up -d --build` (must rebuild so the image contains the CLI).  
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
Seeds ~**308** `role_permissions` rows. It does **not** create a fixed-password admin user.

The whole script is ONE transaction, so a server without pgvector aborts it and creates
**no tables at all** — not just the memory tables. The db image must be
`pgvector/pgvector:pg18` in all three composes. Details, the second carrier
(`backend/database.py::_ensure_vector_extension()`, which must run BEFORE
`Base.metadata.create_all()`), and the verification commands are in §2.2.6 of the
Chinese half above.

**A3** `architecture_reviews` stores review scores/findings/suggestions. **`wa_lenses`** stores the active Custom Lens JSON editable by users with **A3.review** (default: Security_Reviewer VER; reviews resolve DB-first, then file fallback). Existing DBs: re-run `schema_rbac.sql` (`IF NOT EXISTS`) or rely on backend `_ensure_a3_schema()` on startup.

**If you create empty tables without seeding `role_permissions`, the matrix is entirely empty** — no view/edit/review for any role, Sidebar stays empty, APIs return 403. Always run `schema_rbac.sql` (or confirm ~308 rows after backend empty-DB seed).

Re-running **wipes and re-seeds** `role_permissions` (backup first if customized). Bootstrap admin creation is handled by backend startup via `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`, not by this SQL script.
