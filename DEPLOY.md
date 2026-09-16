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
        → 模型（例：anthropic/claude-sonnet-4.6）
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
| `LLM_MODEL`／`ANTHROPIC_DEFAULT_SONNET_MODEL` | OpenRouter 模型 slug | 例：`anthropic/claude-sonnet-4.6` |
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
| `AWS_DEFAULT_REGION` | `us-east-1` | Bulk Price List 固定用 `us-east-1` 端點即可 |
| `COST_PRICING_USE_SDK` | `0` | 釘在 `0`（公開 Bulk）。IAM 版 Price List Query API 已停用，見下方說明 |
| `GCP_BILLING_API_KEY` | 選填（C1） | **有 GCP 圖要真實估價時必填**（Cloud Billing Catalog）；勿 commit |
| `COST_PRICING_STUB` | 本機可選 `1` | **staging／正式部署勿設**；CI test stack 才用 stub |

#### 1.1.1 C1 成本估價（本次 FinOps 部署必讀）

三雲查價行為：

| 雲 | 需要的環境變數 | 未設定時 |
|---|---|---|
| **AWS** | **不需**金鑰（可選 `AWS_DEFAULT_REGION=us-east-1`） | 走公開 Bulk Price List；首次 EC2 查價約 1–2 分鐘 |
| **GCP** | **`GCP_BILLING_API_KEY`**（Catalog API key） | GCP 列無法取得官方價（維持未定價／查價失敗） |
| **Azure** | **不需**額外金鑰 | Retail Prices 公開 API |

Compose／staging 請寫在 **`deploy/.env`**（見 `deploy/.env.example` 的「C1 成本估價」段）；本機 bare-metal 寫在 **`backend/.env`**。  
`ut` 自動部署會由 `deploy/render-env.sh` 從 GitHub Secrets 寫入同名變數——請在 repo Settings → Secrets 新增：

- `AWS_DEFAULT_REGION`（可選，預設 `us-east-1`）
- `GCP_BILLING_API_KEY`（要估 GCP 圖則必填）

**AWS 帳號憑證不在此列，而且不要加。** `render-env.sh` 不再寫出 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`，`docker-compose.deploy.yml` 也不再傳遞。兩個理由：ADR-0001 把供應商憑證排除在本 repo 的範圍之外；`aidlc/spaces/default/memory/project.md` 的 C1 計價規則只准公開免帳號端點，而 Price List Query API 走 IAM。即使在 GitHub Secrets 設了同名 secret，也不會進到容器裡。

**禁止**把真實金鑰寫進 `.env.example` 或 commit 進 git。

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
# C1 — AWS Pricing（走公開 Bulk Price List，不需帳號憑證）
AWS_DEFAULT_REGION=us-east-1
COST_PRICING_USE_SDK=0

# C1 — GCP Catalog（要估 GCP 架構圖時必填）
GCP_BILLING_API_KEY=...
```

Azure Retail Prices **不需**寫入金鑰。改完後 `docker compose … up -d`（必要時 `--force-recreate backend`）。

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
| A | `users` | 帳號、角色、啟用狀態 |
| A | `user_diagrams` | 架構圖 XML |
| A | `diagram_shares` | 圖分享（多對多） |
| B | `users.last_opened_diagram_id` | 上次開啟的圖 |
| B | `users.last_activity_at` | **最後活動時間**（UTC，可為 NULL＝從未活動）。見 2.2.3 |
| B | `user_diagram_chats` | 使用者×圖 的聊天紀錄（A4） |
| E | `architecture_reviews` | **A3** Well-Architected 評核結果（分數／發現／建議） |
| E | `wa_lenses` | **A3** Offline Custom Lens 現行標準（具 A3 **審核** 者可編輯） |
| C | `role_permissions` | 角色 × Story 的檢視／編輯／審核 |
| F | **C1** `diagram_cost`／`diagram_cost_line`／`pricing_cache`／`cost_audit_event` | **成本估算**（FinOps C1） |
| D | 預設使用者 `admin` | 見下方 |

#### 2.2.4 C1 成本表（DDL 摘要）

| 表 | 說明 |
|---|---|
| `diagram_cost` | 每圖一列：估價區域、月預算（B2） |
| `diagram_cost_line` | 每圖×mxCell：時數、SKU／小時價覆寫 |
| `pricing_cache` | 公開價目快取（UK: cloud+sku+region；`hourly` 為 `NUMERIC(12,6)` 等效小時單價） |
| `cost_audit_event` | 覆寫與預算稽核 |

**既有環境升級**：重跑 `schema_rbac.sql`（含四表 `CREATE IF NOT EXISTS` 與 C1h～C1o 種子），或依賴後端啟動時 `database._ensure_cost_schema()` + `ensure_missing_role_permissions()`（**勿**對 brownfield 重跑整份 SQL 的 `DELETE FROM role_permissions`）。

**RBAC 增量**：`C1h`／`C1r`／`C1b`／`C1o` 共 44 列；`role_permissions` 新環境總列數 **352**。

驗證：

```bash
psql "$DATABASE_URL" -c "\d diagram_cost"
psql "$DATABASE_URL" -c "SELECT count(*) FROM role_permissions WHERE story_id LIKE 'C1%';"
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
- Secrets：至少 `JWT_SECRET`、`OPENROUTER_API_KEY`、`POSTGRES_PASSWORD` 等；**本次 C1 請再加**（可選）`AWS_DEFAULT_REGION`、`GCP_BILLING_API_KEY`（由 `render-env.sh` 寫入 `deploy/.env`）。AWS 帳號憑證**不要加**，見第 1.1.1 節  
- 公開：`https://cloud360.danniel.cc`；內網：`http://192.168.10.10:8090`  

部署本次 A1↔A3／token 相關變更時：確認 runner 上的 compose **會 rebuild backend**（workflow 已 `up -d --build`），且 GitHub Secrets 的 OpenRouter 金鑰有效；可選在 secrets／產生的 `.env` 加上 `LLM_MAX_OUTPUT_TOKENS`。

部署 **C1 FinOps** 時：確認上列 AWS／GCP secrets 已設，且 backend 出站可達官方價目 host；煙測成本頁對 AWS／GCP／Azure 圖各查一次價。

#### 3.4 本次功能升級檢查清單（A1↔A3 優化）

- [ ] Backend image **重建**（含 `@anthropic-ai/claude-code`）  
- [ ] 容器內 `which claude` 成功  
- [ ] `OPENROUTER_API_KEY` 已設且有餘額  
- [ ] `ANTHROPIC_API_KEY` 為空；`ANTHROPIC_BASE_URL` 指向 OpenRouter  
- [ ] （建議）`LLM_MAX_OUTPUT_TOKENS=12000` 或更低，避免 402  
- [ ] **無需**為本次功能重跑 SQL（無 schema 變更）  
- [ ] 煙測：Assessment 對含高風險報告按「優化」→ 出現新舊比對／儲存取消；Workspace 產圖正常  

#### 3.5 本次功能升級檢查清單（C1 FinOps）

- [ ] 已跑／確保 C1 四表與 `C1`／`C1h`～`C1o` 種子（見 2.2.4）  
- [ ] `deploy/.env` 或 GitHub Secrets 已設 **`GCP_BILLING_API_KEY`**（估 GCP 必填）；AWS 走公開 Bulk，不需憑證  
- [ ] **未**在 staging 設 `COST_PRICING_STUB=1`  
- [ ] Backend recreate 後出站可達 AWS／GCP／Azure 價目 host  
- [ ] 煙測：成本頁選 AWS／GCP／Azure 圖 → 區域下拉僅該雲 → 已映射服務有官方價  

---

### 4. 建議部署順序（摘要）

1. 準備 PostgreSQL，設定 `DATABASE_URL`  
2. 執行 `psql "$DATABASE_URL" -f schema_rbac.sql`  
3. 準備 LLM：OpenRouter 金鑰 ＋ **Claude Code CLI**（Docker build 或本機安裝）  
4. 設定後端 `.env`／`deploy/.env`（含 `CORS_ORIGINS`、`JWT_SECRET`、LLM／token 變數，以及 **C1 的 `AWS_*`／`GCP_BILLING_API_KEY`**；全新 staging 可選 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`）並啟動 API
5. 設定前端 `VITE_API_BASE_URL` 後 build／部署  
6. 用既有管理員或 bootstrap admin 登入 → **立刻輪替臨時密碼／清除 bootstrap secret** → 調整角色權限
7. 依第 3.4／3.5 節做 A1／A3／優化與成本頁煙測  

---

### 5. 相關文件

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
- **C1 FinOps**: set `GCP_BILLING_API_KEY`（required for live GCP catalog prices）. AWS uses the public Bulk Price List and needs no credentials — do not add them. Azure needs no key. Do **not** set `COST_PRICING_STUB=1` on staging.  
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

Creates: `users`, `user_diagrams`, `diagram_shares`, `user_diagram_chats`, **`architecture_reviews` (A3)**, **`wa_lenses` (editable offline Lens)**, `role_permissions`, plus `last_opened_diagram_id`.  
Seeds ~**308** `role_permissions` rows. It does **not** create a fixed-password admin user.

**A3** `architecture_reviews` stores review scores/findings/suggestions. **`wa_lenses`** stores the active Custom Lens JSON editable by users with **A3.review** (default: Security_Reviewer VER; reviews resolve DB-first, then file fallback). Existing DBs: re-run `schema_rbac.sql` (`IF NOT EXISTS`) or rely on backend `_ensure_a3_schema()` on startup.

**If you create empty tables without seeding `role_permissions`, the matrix is entirely empty** — no view/edit/review for any role, Sidebar stays empty, APIs return 403. Always run `schema_rbac.sql` (or confirm ~308 rows after backend empty-DB seed).

Re-running **wipes and re-seeds** `role_permissions` (backup first if customized). Bootstrap admin creation is handled by backend startup via `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD`, not by this SQL script.
