# 本機開發環境（Local Development）

> 目標：在本機把 **Cloud-360 的所有功能**跑起來，不只是不需要 LLM 的那些。
> 本檔補齊 `DEPLOY.md` §3.1 的六行摘要 —— 那節假設你已經知道隱性依賴，這節不假設。

---

## 0. 先理解一件事：哪些功能需要什麼

**這是本檔最重要的一節。** 只裝 `requirements.txt` 是跑不起全部功能的 —— 有兩個依賴不在任何依賴宣告檔裡。

| 功能面 | 需要 | 缺了會怎樣 |
|---|---|---|
| 登入／RBAC／使用者管理（J1、J3a、J3b） | **只要 PostgreSQL** | — |
| 架構圖 CRUD／分享（A2、A4） | 只要 PostgreSQL | — |
| Well-Architected 離線規則打分（A3 的規則層） | 只要 PostgreSQL | — |
| **A1 對話產圖** | PostgreSQL ＋ **一個能認證的 LLM 供應商**（見下方 H1） | API 回 **500** |
| **A3 改善建議** | 同上 | 建議階段降級為 `rules_only` |
| **A3「優化」（Design↔Review 協作）** | 同上 | 失敗 |
| **Offline Lens agent 填答** | 同上 | 降級為規則啟發式（會寫 WARNING log） |
| 動態 SVG 圖示 | n8n webhook（**選填**，見下方「圖示目錄」） | 用灰底 fallback 圖示，不中斷 |
| **大腦入口頁（U13 起，`/api/brain/ws`）** | PostgreSQL ＋ **Redis** ＋ **`OPENROUTER_API_KEY`**（分類走 OpenRouter） | 缺金鑰：連線照常建立，但**每一輪**都回「內部錯誤」（`error(INTERNAL_ERROR)`，不降級）；本機與 staging 同形。staging 部署時此金鑰為必要 secret（`deploy.yml` 缺它即中止） |
| **建庫本身（全部功能的前提）** | PostgreSQL ＋ **pgvector 擴充**（見第 2 節 H4） | `schema_rbac.sql` 整個交易中止，**一張表都建不出來** |
| **後端啟動本身（U13 起）＋ 大腦入口頁** | **Redis** 的三個變數 `REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD`（見第 1 節的 `redis-cli ping`） | 三者缺任一，或 `REDIS_USER=default` → **後端拒絕啟動**。Redis 只是**暫時連不上**時後端照常啟動（client 延遲連線），入口頁的連線在握手時以 **1011** 關閉；連上之後才斷則該輪回「工作階段暫時無法存取」、連線保留 |
| **後端啟動本身（U10 起）** | `backend/.env` 的 **`BRAIN_SESSION_HISTORY_MAX`**（required、**無預設**） | **後端直接拒絕啟動**並列出需要的設定。這不是降級，是大聲失敗——把缺值讀成「無上限」會讓單一 Redis key 無上界成長，而那是無聲的（`BR3.5`） |
| **後端啟動本身（U13 起）** | `backend/.env` 的 **`REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD`**（三者皆 required） | **後端直接拒絕啟動**：缺任一（`KeyError`）或 `REDIS_USER=default`（`ValueError`，`default` 已被收窄為 `+@connection`）。啟動時**不連線**，所以 Redis 暫時不可達不會擋啟動 |
| **後端啟動本身（U11 起）** | `backend/.env` 的 **`BRAIN_ROUTER_CONFIDENCE_THRESHOLD`**（required、**無預設**） | **後端直接拒絕啟動**並列出需要的設定。同樣是大聲失敗——門檻缺值時「信心不足就先問、不要亂做」這條路徑的判定基準不存在，而把缺值讀成某個預設門檻，等於讓它由一個沒有人選過的數字決定（`BR3.4`）。另四個 `BRAIN_ROUTER_*` 缺值只會記 WARN／INFO 並取預設 |
| 記憶檢索的 embedding | 依 `EMBEDDING_PROVIDER` 而定（見第 3 節）。本機的向量檢索走 **`fastembed`**；**`ollama` 是部署 stack 專用**——本機設得出合法值（啟動會過）但連不上，失敗發生在第一次 embed | 選 `fulltext`／`stub` 時不需任何外部服務。選 `fulltext` 時入口頁**每個有交辦的輪次**都會記一筆 `episodic_write_failed` WARNING（`fulltext` 下寫不了記憶），屬預期（`OPEN-GW13-18`） |

### 兩個「不在 requirements.txt 裡」的硬依賴

**H1 — LLM 供應商（OpenRouter）**：A3 Review／Lens 與多數 LLM 路徑經 **LangGraph + OpenRouter HTTP**（`OPENROUTER_API_KEY`）。映像與本機 **不再**需要為 A3 安裝 `@anthropic-ai/claude-code`。

```
FastAPI → langgraph_runtime / LangChain → OpenRouter → 模型
```

供應商環境仍由 `LLM_PROVIDER`（`backend/services/llm_provider.py`）整理：

| `LLM_PROVIDER` | 認證來源 | 適用 |
|---|---|---|
| `openrouter`（程式預設，**唯一可用值**） | `OPENROUTER_API_KEY` | 部署與本機皆同 |
| ~~`cli`~~ | **已退役（2026-10-02，RAID R-11）** | 設它會退回 `openrouter` 並記一行 ERROR。A3 遷移到 LangGraph 之後已無 `claude` CLI 子行程可認證，而該模式仍會刪除 `ANTHROPIC_AUTH_TOKEN`／`BASE_URL`，使金鑰被清空而健康檢查仍回報正常 |

本機直接設 `OPENROUTER_API_KEY`。驗證：後端啟動後打 A3 評核，建議串流有文字增量（或無金鑰時走啟發式／備援，並出現 WARNING／降級）。

`cli` 模式下程式仍可能**主動刪除**兩組變數（避免殘值干擾 Anthropic 相容客戶端）：

| 被刪除的變數 | 留著會怎樣 |
|---|---|
| `ANTHROPIC_BASE_URL`／`ANTHROPIC_AUTH_TOKEN`／`ANTHROPIC_API_KEY` | 只要**非空**就可能蓋掉預期路由 |
| `ANTHROPIC_DEFAULT_SONNET_MODEL`／`_OPUS_`／`_HAIKU_` | 別名映射可能把模型名又導回錯誤 slug |

`openrouter` 模式下，`OPENROUTER_API_KEY` 會在啟動時被映射為 `ANTHROPIC_AUTH_TOKEN`（供仍走 Anthropic 相容客戶端的路徑），且 `ANTHROPIC_API_KEY` 必須留空。

> ⚠️ **金鑰欄位留空就是留空，不要填佔位字串。** 程式判斷「有沒有設定」看的是非空，所以 `OPENROUTER_API_KEY=your_openrouter_api_key_here` 會被當成真金鑰送出去，換來一個離肇因三層遠的 401。範本現在一律出空值、範例寫在註解裡，`scripts/validate_env_contract.py` 也會擋下佔位值。同一個陷阱也適用 `N8N_WEBHOOK_URL`：留著 `your_n8n_webhook_url_here` 會讓每個節點發一次必然失敗的請求，圖照樣出來、但圖示全是灰底。

### 圖示目錄

`N8N_WEBHOOK_URL` 那支 webhook 回傳的是**整份目錄**（一次約 1.1 MB），由後端自己在裡面比對服務名稱。兩件事值得先知道：

- **目錄目前只收 AWS**（315 項）。GCP／Azure 的服務一定比對不到，圖示會是灰底 —— 這是預期行為，不是壞掉。
- **目錄用服務全名，架構圖用縮寫**。`SNS` 在目錄裡叫 `Simple Notification Service`，兩者沒有共同子字串。後端有一份對照表處理常見縮寫（S3、SNS、SQS、SES、KMS、ELB、MSK、IAM、ECS、EKS、ECR、VPC、CDN、ASG）；表以外的縮寫比對不到就落到灰底，並寫一行 WARNING。

比對不到時**一律**回灰底佔位圖，不會退而求其次給一個相近的圖示 —— 錯的圖示比灰底更難發現。

---

## 1. 一次性前置檢查

```bash
# 資料庫
psql --version                      # 需要 PostgreSQL client
pg_isready -h localhost -p 5432     # 需要一個跑著的 server

# ⚠ pgvector：本機建庫的硬依賴（見第 2 節 H4）。必須有一列，否則 schema_rbac.sql
#   會整個交易中止、一張表都建不出來。
psql "postgresql://postgres:postgres@localhost:5432/postgres" \
  -c "SELECT name, default_version FROM pg_available_extensions WHERE name='vector';"

# Redis：session store（第 5 服務）。沒有它的三個變數，後端（U13 起）拒絕啟動；
# 它暫時斷線時入口頁握手失敗（1011）。
redis-cli ping                      # 應回 PONG；沒有的話 brew install redis / apt install redis

# U10 session-store：每段歷程上限。required、**無預設**——沒設它，後端在
# startup 就拒絕啟動（不是降級）。值 200，理由見第 3 節的 .env 註解。
grep -q '^BRAIN_SESSION_HISTORY_MAX=' backend/.env \
  && echo 'BRAIN_SESSION_HISTORY_MAX 已設定' \
  || echo '請在 backend/.env 設 BRAIN_SESSION_HISTORY_MAX=200（缺它後端不啟動）'

# U11 intent-router：意圖路由的信心門檻。required、**無預設**——沒設它，後端
# 在 startup 就拒絕啟動（不是降級）。值 0.7，理由見第 3 節的 .env 註解。
grep -q '^BRAIN_ROUTER_CONFIDENCE_THRESHOLD=' backend/.env \
  && echo 'BRAIN_ROUTER_CONFIDENCE_THRESHOLD 已設定' \
  || echo '請在 backend/.env 設 BRAIN_ROUTER_CONFIDENCE_THRESHOLD=0.7（缺它後端不啟動）'

# LLM 鏈路（A1／A3 必要：OpenRouter 金鑰）
# 映像與 A3 不再需要 Node／claude CLI
test -n "${OPENROUTER_API_KEY:-}" && echo "OPENROUTER_API_KEY 已在環境" || echo "請在 backend/.env 設定 OPENROUTER_API_KEY"

# 選用：本機 embedding。**本機的向量檢索走 fastembed，不是 ollama**——
# ollama 在本機連不上：服務名過得了 NFR7.1 的驗證，但解析不到（見第 3 節）。
# python3 -c "import fastembed" 2>/dev/null && echo "fastembed 已安裝" || echo "需 pip install 'fastembed>=0.7,<0.8'"

# Python
python3 --version                   # CI 用 3.12
```

### 先確認 port 沒被佔用

```bash
for p in 5432 6379 8000 5173 8080; do   # 8080：MCP bridge（可選，見 3. 後端的「本機啟動 MCP bridge」）
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 \
    && echo ":$p 被佔用 → $(lsof -nP -iTCP:$p -sTCP:LISTEN | awk 'NR==2{print $1}')" \
    || echo ":$p 可用"
done
```

**後端的 port 不是固定的** —— `DEPLOY.md` 寫 8000，但那只是慣例。若 8000 被別的東西佔著（例如本機的 K8s／kind、其他專案），換一個即可，只要 `frontend/.env` 的 `VITE_API_BASE_URL` 跟著改。下文以 `8010` 為例。

---

## 2. 資料庫

### ⚠️ H4：本機 PostgreSQL 必須先裝 pgvector（不裝就一張表都建不出來）

**這一步是必做前置，不是附註。** `schema_rbac.sql` 在 `BEGIN;` 之後的第一條敘述是
`CREATE EXTENSION IF NOT EXISTS vector;`（U5 記憶表的 `vector(1024)` 欄位需要它）。

而本機走的是**主機安裝的 PostgreSQL**，不是 compose 的 db 容器——所以那個容器映像帶不帶
pgvector 跟你無關，重要的是**你主機上那顆 PostgreSQL**有沒有裝。

**不裝的後果比想像的大**：`IF NOT EXISTS` 只抑制「擴充已存在」；伺服器**沒有安裝**
pgvector 時是 `could not open extension control file` 這個**硬 ERROR**。`schema_rbac.sql`
是**單一交易**（`BEGIN` … `COMMIT`），交易一旦中止，之後每一條敘述都以
`current transaction is aborted` 失敗、`COMMIT` 退化為 ROLLBACK ——結果是**一張表都沒建**
（全部資料表、308 列 RBAC 預設矩陣全沒有），**不論你碰不碰記憶功能**。

```bash
# 前置檢查：必須有一列
psql "postgresql://postgres:postgres@localhost:5432/postgres" \
  -c "SELECT name, default_version FROM pg_available_extensions WHERE name='vector';"
```

沒有那一列時，二擇一：

| 做法 | 指令 |
|---|---|
| **裝到主機的 PostgreSQL 上**（建議，維持既有的 bare-metal 流程） | macOS：`brew install pgvector`；Debian／Ubuntu：`apt install postgresql-17-pgvector`（版號跟著你的 server 走）；或由原始碼 `make && make install` |
| **改用 repo 根的 compose 提供 db** | `docker compose up -d db`（該檔的 db 映像已是 `pgvector/pgvector:pg18`，publish `5432`，連線字串不變） |

### ⚠️ H5：既有的 `postgres_data` volume 與 PG 18 不相容

repo 根 `docker-compose.yml` 的 db 映像由 `postgres:15-alpine` 改為
`pgvector/pgvector:pg18`——**跨三個大版本**。PGDATA 的格式不跨大版本相容，而該檔掛的是
具名 volume `postgres_data` 且 `restart: always`：**既有 volume 會讓容器進入重啟迴圈**
（日誌寫 `database files are incompatible with server`）。**沒有任何 CI 閘門涵蓋這條路徑。**

若你之前用過那個 compose 起 db，二擇一：

```bash
# (a) 本機資料可丟：移除 volume 重建（最快）
docker compose down
docker volume rm cloud-360_postgres_data 2>/dev/null || docker volume ls | grep postgres_data
docker compose up -d db
psql "postgresql://postgres:postgres@localhost:5432/cloud360" -f schema_rbac.sql

# (b) 要保留資料：先以舊映像 dump，再以新映像 restore
#     （把 image 暫時改回 postgres:15-alpine → pg_dump → 改回 pg18 → 移除 volume → restore）
```

> volume 的實際名稱帶 compose 專案名前綴，而根 compose 沒有 `name:`，所以前綴是**目錄名**
> ——在 `cloud-360/` 下是 `cloud-360_postgres_data`，在名為 `chiton` 的 worktree 下會是
> `chiton_postgres_data`。用 `docker volume ls | grep postgres_data` 確認實際名稱再刪。

### 建庫

```bash
createdb -U postgres -h localhost cloud360
psql "postgresql://postgres:postgres@localhost:5432/cloud360" -f schema_rbac.sql
```

`schema_rbac.sql` 會建立 `vector` 擴充、全部資料表，以及 308 列 RBAC 預設矩陣。

> **它不建立固定密碼管理員。** （這一行先前寫「以及預設帳號 `admin` / `admin123`」，與
> `schema_rbac.sql:11` 逐字的「不建立固定密碼管理員；bootstrap admin 由後端依環境變數
> 建立」直接矛盾，且該檔全檔唯一的 `INSERT INTO` 是 `role_permissions`。已更正。）
> 本機的 `admin / admin123` 是**後端啟動時**建的：`APP_ENV=local`／`test`／`ci` 之下
> `init_db()` 會建 bootstrap admin，`local` 另外建 11 位 persona demo 帳號。

### ⚠️ 兩條 schema 演進路徑（踩過就會懂）

| 路徑 | 何時執行 | 注意 |
|---|---|---|
| `schema_rbac.sql` | 你手動跑，或 Docker 的 db 容器**在資料目錄為空時**跑一次 | 既有資料庫**不會**自動重跑（隱性依賴 H2） |
| `backend/database.py` 的 `_ensure_*_schema()` | **每次後端啟動** | 這才是既有環境真正的遷移機制 |

**實務結論**：改了 `schema_rbac.sql` 卻只重啟容器 → 不生效。反過來，多數欄位新增只要**重啟後端**就會被 `_ensure_*_schema()` 的 `ALTER TABLE ... IF NOT EXISTS` 補上（例如 `estimate_line_items.spec_description`）。

**一個例外，改 `database.py` 時要知道**：`init_db()` 裡的 `_ensure_*` 現在有**七支**，
其中六支在 `Base.metadata.create_all()` **之後**（它們補 `create_all` 不會做的 `ALTER`），
而 **`_ensure_vector_extension()` 在它之前**——`vector` 型別必須先存在，否則宣告 `vector`
欄位的表在 `create_all()` 裡就會以 `type "vector" does not exist` 失敗，而那是**啟動失敗**
（`init_db()` 由 startup 事件同步呼叫）。新增補丁時照既有形狀擺在後面是對的；**唯獨擴充類
必須在前面**。這條順序由 `backend/tests/test_vector_extension_bootstrap.py` 守著。

### ⚠️ H6：`schema_rbac.sql` 不會給你 `U5`／`U18` 的表，而 `U19` 的程式會真的去讀它們

**這一節是 `U19 membership-service` 加的，而它是第一個在執行期真的讀寫
`project_members`／`reselection_events` 的程式**（`U18` 是純 DDL，所以它不會在
本機壞掉）。

`schema_rbac.sql` 的 `I)`／`J)` 兩個區塊只在**空 volume**（或你手動跑整個檔案）
時生效。既有的本機資料庫拿不到它們，而既有環境的唯一路徑是**兩支獨立腳本**，
**順序嚴格**：

```bash
cd backend
# 1) U4：projects／systems（J) 的外鍵指向它們）
python scripts/run_hierarchy_migration.py && echo "exit=$?"
# 2) U5 ＋ U18：memory schema ＋ 三張 project-meta 表
python scripts/run_meta_schema_migration.py && echo "exit=$?"
# 3) U19：既有專案的成員回填（**沒跑的話你會被鎖在自己的專案外面**）
python scripts/backfill_project_members.py --dry-run && echo "exit=$?"
python scripts/backfill_project_members.py && echo "exit=$?"
```

第 3 步的後果值得寫清楚：`project_members` 是全新表，既有專案全部**零成員**，
而 `resolve_project_role` 對零成員專案回 `None`、`BR1.6` 要求當成拒絕
——所以**連你自己建的專案都會被判為非成員**。症狀是 `/api/membership/*` 一律
403 而不是任何錯誤訊息。細節與驗證指令見 `DEPLOY.md` 第 2.2.10 節。

#### ⚠️ 一個本機專屬的陷阱：**後端先啟動過，你就會拿到沒有 COMMENT 的表**

`U19` 把 `ProjectMember` 與 `ReselectionEvent` 納入 `Base`，所以
`backend/database.py` 的 `Base.metadata.create_all()`（啟動時跑）成為
**第二條建表路徑**。它的 `checkfirst=True` 只建**缺少的**表，既有表一律不動。

於是在一個**沒跑過 `run_meta_schema_migration.py`** 的本機資料庫上：

| 順序 | 結果 |
|---|---|
| 先跑腳本、後啟動後端 | 正確：腳本建表（含 COMMENT），`create_all` no-op |
| **先啟動後端、後跑腳本** | 該資料庫**永久缺 COMMENT**——`CREATE TABLE IF NOT EXISTS` 整段 no-op，之後再跑 `schema_rbac.sql` 也補不回來 |

嚴重度**低且限本機**（COMMENT 是給人讀的防呆機制，不影響行為），但它說明一件事：
**兩條建表路徑不等價，而只有一條被驗**（`verify_meta_schema.sql` 的 14 條斷言裡
只有 `P12` 碰 COMMENT，且它驗的是 `system_requirement_fields`）。
要修就是整個重來（下面那一段），或手動補 COMMENT。

### 真實 PostgreSQL 的測試（`backend/tests_pg/`）

`U19` 引入**第二個測試根**。`backend/tests/` 的 51＋ 個測試檔全部走 in-memory
SQLite，而 `backend/tests_pg/` 需要一個**真實的** PostgreSQL：

```bash
cd backend
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cloud360 \
  python -m unittest discover -s tests_pg -v
```

前置條件：目標資料庫已套用 `schema_rbac.sql`（含 `U19` 回補的
`reselection_events.cause`）。**`DATABASE_URL` 必須顯式帶 `+psycopg` 後綴**，
而**讀不到它時這些測試會大聲失敗、不會退回 SQLite**——退回 SQLite 會讓整個
測試綠燈而鎖從未存在。

**為什麼不能把真實 PG 測試放回 `backend/tests/`**：`with_for_update()` 在
SQLAlchemy 的 SQLite dialect 下**被靜默丟棄**（編譯出的 SQL 無鎖子句、無錯誤、
無警告），所以併發測試在那裡會**綠燈而鎖根本不存在**。隔離是結構性的：
`discover -s tests` 看不到 `tests_pg`，沒有東西可以忘記設。

> 這些測試會在目標資料庫裡建立並清除自己的 `users`／`projects`／
> `project_members`／`reselection_events` 列（使用者名帶 `u19pg-` 前綴）。
> 它們不碰既有資料，但**它們不是唯讀的**——若你的 `cloud360` 裡有你在意的
> 本機資料，建一個丟棄用的資料庫跑它們。

要整個重來：

```bash
dropdb -U postgres -h localhost cloud360 && createdb -U postgres -h localhost cloud360
psql "postgresql://postgres:postgres@localhost:5432/cloud360" -f schema_rbac.sql
```

> 重跑 `schema_rbac.sql` 會 `DELETE FROM role_permissions` 後重播預設矩陣 —— **在 Admin UI 上調過的權限會被蓋掉**。

---

## 3. 後端

### `backend/.env`

從範本複製再改，範本本身就是本機開發的完整清單（每個 backend 讀得到的變數都必須列在裡面，由 `scripts/validate_env_contract.py` 強制）：

```bash
cp backend/.env.example backend/.env
```

最小可跑的內容長這樣：

```bash
cat > backend/.env <<'EOF'
APP_ENV=local
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cloud360
JWT_SECRET=dev_only_change_me
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# LLM 供應商：openrouter 是唯一可用值。`LLM_PROVIDER=cli` 已退役（RAID R-11
# 已修）：設它會退回 openrouter 並記一行 ERROR。注意舊的 backend/.env.example
# 預設值就是 cli，若你的 .env 是在 2026-10-01 之前複製的，把那一行改成
# openrouter（或刪掉）。
LLM_PROVIDER=openrouter

# 必填。留空＝未設定；
# 千萬不要填佔位字串，那會被當成真金鑰送出去。
OPENROUTER_API_KEY=

# 留空即依供應商取預設（cli → sonnet）
LLM_MODEL=

# --- brain-infra（U1）：Redis ＋ embedding ---
# 本機用 localhost；部署 stack 用 compose 服務名（redis／ollama），由 deploy/.env
# 決定，兩者不共用設定。
REDIS_URL=redis://localhost:6379/0
# 不得為 `default`（最小權限）。本機若跑的是沒設 ACL 的 Redis，自己建一個：
#   redis-cli ACL SETUSER cloud360 on '>本機密碼' '~*' '+@all' '-@admin' '-@dangerous'
REDIS_USER=cloud360
REDIS_PASSWORD=
# U10 session-store：每段對話歷程的筆數上限。required、**無預設**——缺值時
# 後端在 startup 大聲失敗，**不會**以「無上限」啟動（BR3.5）。
# 上限**每段獨立計算**（至多三段：shared／workspace／assessment），故總量上界
# 是 3 倍而非 200 則總和。值 200：3 × 200 × 約 500 B ≈ 300 KB／session。
BRAIN_SESSION_HISTORY_MAX=200
# U11 intent-router：意圖路由層的五個設定。**只有門檻 required、無預設**——
# 缺它後端在 startup 大聲失敗；其餘四個缺值取預設並記 WARN／INFO。
# 門檻值域為 0 < t <= 1：設 0 會讓「最高分 >= 門檻」恆真、反問路徑永不觸發，
# 而那是一條 Must（「判不出來先問我，不要亂做」）靜默失效。
# 本機**不需要** OPENROUTER_API_KEY 也能跑本單元的測試（全部用替身）；
# 要真的讓路由層打模型才需要金鑰（見本節的 OPENROUTER_API_KEY）。
# 換 BRAIN_ROUTER_MODEL 不需改程式，但準確率數字不可跨模型沿用。
BRAIN_ROUTER_MODEL=typesafe/jev-1.13
BRAIN_ROUTER_TIMEOUT_SEC=5
BRAIN_ROUTER_MAX_CALLS_PER_TURN=1
BRAIN_ROUTER_MAX_RETRIES=0
BRAIN_ROUTER_CONFIDENCE_THRESHOLD=0.7
# 允許值：ollama｜fastembed｜fulltext｜stub。required、**無預設**——值不在清單內
# 或缺值時會啟動失敗並列出可選值（不會靜默降級）。
#   ollama    **部署 stack 專用**——本機設得出合法值但連不上，見下方 OLLAMA_BASE_URL
#   fastembed 不另起服務，但**首次使用會下載**模型（ONNX，行程內執行）。
#             **本機要真的驗向量檢索，用這個。**
#   fulltext  不做向量檢索，退回全文搜尋（零下載、零額外服務）
#   stub      完全不算 embedding；CI 的 ui-regression stack 用的就是它
EMBEDDING_PROVIDER=fulltext
# 只有 EMBEDDING_PROVIDER=ollama 時才用到。**本機的兩種失敗方式不同，別搞混：**
# （a）保留下面的服務名 → 啟動**會過**（NFR7.1 驗的是主機名形式，不是可解析性；
#      BR1.5 禁止啟動探測），失敗發生在第一次 embed()，是
#      EmbeddingProviderUnavailable 夾 ConnectError（名稱無法解析）。
# （b）改成 localhost／127.0.0.1／IP／對外網域 → **啟動就失敗**，訊息會說
#      主機名必須是 compose 內部服務名。
# NFR7.1 之所以這麼嚴：該服務的 HTTP API 零認證、不 publish host port，
# 網段隔離是它唯一的存取控制。
# 本機要向量檢索請改用 fastembed。維度須為 1024（對齊 vector(1024)）
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_EMBED_MODEL=bge-m3
# 只有 EMBEDDING_PROVIDER=fastembed 時才用到。維度亦須 1024
FASTEMBED_MODEL=multilingual-e5-large
# 選填，預設 10。embedding 外部呼叫的逾時上界（秒）。非正數或非數字會記 WARN
# 後取預設，不終止啟動。它保護的是「提供者掛掉時不要無限期掛住記憶路徑」，
# 不是首字回應的延遲預算。
EMBEDDING_TIMEOUT_SEC=10

# --- 選填 ---
# N8N_WEBHOOK_URL=https://.../webhook/get-icon
# N8N_USER=
# N8N_PASSWORD=
# 查價（C1／U5）：**檔案快取 → boto3 Pricing Query API → 公開 Bulk**（不再寫 Postgres pricing_cache）。
# 可選填 `AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY`（僅 pricing:GetProducts／DescribeServices／GetAttributeValues；ADR-0018）。
# 未設時走公開 Bulk Price List。本機**不必**持有雲端憑證即可啟動（FR11.4）。
# GCP：設定 `GCP_BILLING_API_KEY`（Cloud Billing Catalog API）。
# Azure：公開 Retail Prices API（prices.azure.com，免金鑰）。
# 禁止把真金鑰寫進版控檔；log／錯誤訊息不得含 secret 值（變數名可出現）。
EOF
```

> **`+psycopg` 這個後綴只給應用程式用**，因為它是 SQLAlchemy 的 driver 指定語法。
> 上面用 `psql` 建庫的指令**不能**加它——`psql` 不認得這個形式，會直接連線失敗。
> 兩處刻意不同：`psql` 用裸的 `postgresql://`，`backend/.env` 用 `postgresql+psycopg://`。

> `JWT_SECRET` 未設時會**靜默 fallback 到程式碼內的預設字串**（依賴風險 R2），不會報錯。本機無所謂，但要知道它不會提醒你。

要改用 OpenRouter 的話，把 `LLM_PROVIDER` 改成 `openrouter` 並填入 `OPENROUTER_API_KEY` 即可，其餘不用動——所有 `ANTHROPIC_*` 變數都由程式依模式自動處理（openrouter 模式自動填寫，cli 模式主動刪除，見第 0 節 H1 的表）。

> **本機設定與部署設定是分開的兩套，不要互相抄。** `backend/.env`／`frontend/.env` 只服務本機 bare-metal 執行；部署走 `deploy/.env`（由 `deploy/render-env.sh` 產生，範本 `deploy/.env.example`）。把 `localhost` 來源寫進部署範本、或把 `POSTGRES_*`／`PUBLIC_URL` 寫進本機範本，`scripts/validate_env_contract.py` 都會擋下（CI 紅燈）。


> **金鑰安全**：`.env` 已被 `.gitignore` 涵蓋（`.gitignore:17`），可以安心放本機金鑰。`validate_repo_contract.py` 會對受版控文字檔做密鑰**值樣式**掃描（ADR-0018 §6）；空值與變數名引用允許，真值賦值會紅燈。仍不要把真金鑰貼進程式碼、測試或文件。

### 建議用 venv（避免污染系統 Python）

`requirements.txt` 對 `fastapi` 與 `pydantic` 做了**精確等值釘選**（`==`）—— 這是 OpenAPI 規格漂移 gate 的前提，`pip install` 會把你環境裡的版本改成釘選值。

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> **從既有環境升上來的人必看**：PostgreSQL 驅動已由 `psycopg2-binary` 換成
> `psycopg[binary]`（v3）。兩者是**不同套件**，舊環境不會自動換掉，必須重跑一次
> 上面的 `pip install -r requirements.txt`。沒裝 psycopg v3 時，`import main`
> 會以 `ModuleNotFoundError: No module named 'psycopg'` 失敗。
>
> 單元測試大多不受影響（`tests/helpers.py` 在偵測到沒裝時會 stub 掉），但
> `tests/test_dotenv_path.py` 的兩個案例是**開子行程**跑 `import main`，
> stub 進不到子行程裡，所以那兩個案例真的需要驅動裝好才會綠。

### 啟動

```bash
cd backend
uvicorn main:app --reload --port 8010
```

**cwd 必須在 `backend/`** —— `main.py` 用的是平坦 import（`from services.x import y`），從 repo 根跑會 `ModuleNotFoundError`。

**IDE Run Configuration**：module `uvicorn`、args `main:app --reload --port 8010`、working directory `backend/`、EnvFile `backend/.env`。

### 啟動時該看到什麼

```
INFO:cloud360.database:正在初始化資料庫與資料表...
INFO:cloud360.database:A4 schema 檢查完成
INFO:cloud360.database:J5 schema 檢查完成
INFO:cloud360.database:A3 schema 檢查完成
INFO:cloud360.database:last_activity schema 檢查完成
INFO:cloud360.database:資料庫已存在 1 位使用者，跳過初始化。
INFO:cloud360.database:role_permissions 已有 308 列，略過 seed
INFO:cloud360.database:J3a 權限套用：已跳過（...）
```

**這些行是遷移的實際證據，不是裝飾。** 任何 `warning` 等級的行都要看 —— 例如 `J3a 權限套用：未命中目標列` 代表權限沒生效。

### 本機啟動 MCP bridge（可選，`U21`）

bridge 是獨立行程（部署上是 compose 的第七個服務），把需求欄位的讀／寫／清空包成 MCP 工具。本機開發平常**不需要**它；
要手動試工具呼叫時，在 backend 起來之後另開一個終端：

```bash
cd backend
python -m mcp_bridge --backend-url http://127.0.0.1:8010
```

- 預設監聽 `127.0.0.1:8080`（`--host`／`--port` 可改）；**不讀任何環境變數**，`backend/.env` 對它沒有作用。
- 啟動成功會看到一行 `startup port=8080 tools=3`；工具宣告檔不合格時是一行 `startup_failed subject=...` 並以非零碼退出。
- 它需要 `mcp` 套件（`backend/requirements.txt` 已釘 `mcp==2.3.0`，照常 `pip install -r requirements.txt` 即可）。
  **建議在 venv 內安裝**：本機的系統 Python 若另裝了要求 `mcp<2` 的工具（例如 `claude-agent-sdk`），裝進同一個直譯器會互相衝突。
- 本單元的測試（`backend/tests/test_mcp_bridge_*.py`）缺 `mcp` 或版本不對時以 `AssertionError` 失敗並指出安裝指令，**不是 skip**。

---

## 4. 前端

```bash
echo 'VITE_API_BASE_URL=http://localhost:8010' > frontend/.env
cd frontend && npm ci && npm run dev
```

→ http://localhost:5173

**`VITE_API_BASE_URL` 是 build 期變數，不是 runtime 變數。** `npm run dev` 會讀 `.env`，但 **Docker 映像是 build ARG** —— 部署時改值必須**重建 frontend image**，只重啟容器不會生效。

---

## 5. 驗證：逐功能確認

```bash
# 取 token
TOK=$(curl -s -X POST http://localhost:8010/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

# 不需要 LLM 的：使用者清單（分頁）
curl -s "http://localhost:8010/api/auth/list?page=1" -H "Authorization: Bearer $TOK" \
  | python3 -m json.tool | head -20

# 完整 API 地圖
open http://localhost:8010/docs
```

**A1／A3 要在 UI 上驗**：登入 → Workspace 輸入一句架構描述 → 應該串流出圖。若回 500，照這個順序查：

0. **你改的 `.env` 跟跑起來的 process 是不是同一份 checkout。** 這個 repo 常同時存在多個
   worktree，症狀是「`backend/.env` 明明有值，API 卻回報尚未設定 `OPENROUTER_API_KEY`」。
   查法：
   ```bash
   # 找出跑著的 uvicorn 究竟在哪個目錄
   lsof -p "$(pgrep -f 'uvicorn main:app')" | awk '$4=="cwd" {print $NF}'
   ```
   **2026-10-02 更正**：本節原本教人以錯誤訊息裡有沒有「本機開發也可改設
   `LLM_PROVIDER=cli`」來分辨新舊碼——該句已隨 cli 模式退役從
   `auth_error_message()` 移除，**那個判準現在會把新碼誤判成舊碼**。改用上面的
   `lsof` 查法，或直接看 `llm_provider.py` 是否含 `_RETIRED_PROVIDERS`（含＝新碼）。
1. `backend/.env` 的 `OPENROUTER_API_KEY` 有沒有值（**必填**；`LLM_PROVIDER=cli` 已退役，不再是免金鑰的替代路徑）
2. 若日誌出現「`LLM_PROVIDER=...` 已退役」的 ERROR，把 `backend/.env` 那一行改成
   `openrouter` 或刪掉（**本步取代原本的「`command -v claude` 找不找得到」**——A3 遷移到
   LangGraph 之後全樹已無子行程呼叫，`claude` CLI 不再是任何路徑的依賴）
3. `ANTHROPIC_API_KEY` 是不是**留空**
4. OpenRouter 餘額（402 錯誤來自額度，或 `max_tokens` 預扣過高 → 調低 `LLM_MAX_OUTPUT_TOKENS`）

> 從哪個目錄啟動 uvicorn **不再影響**讀到哪份 `.env`：`backend/env_bootstrap.py` 把路徑釘死在
> `backend/.env`。先前 `load_dotenv()` 沒給路徑，會從 cwd 一路往上找，曾經摸到家目錄的 `.env`。

---

## 6. 灌示範資料（可選但強烈建議）

全新資料庫只有 `admin` 一個帳號，很多畫面看不出效果（分頁、逾期標示、無紀錄態都要多筆才看得到）。

`init_db()` 在 `users` 表為空時會建立 11 個 persona 帳號；但 `schema_rbac.sql` 已經插了 `admin`，所以那段**不會觸發**。要多筆資料就自己灌。

最省事的方式是用**公開註冊端點**（無需認證），它同時也是 e2e 造資料的手法：

```bash
for i in $(seq 1 25); do
  curl -s -o /dev/null -X POST http://localhost:8010/api/auth/register \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"demo$i\",\"password\":\"demo1234\",\"requested_role\":\"Developer\"}"
done
```

註冊出來的帳號是 `pending`（角色欄為破折號），適合看待授權流程。要**指定角色與時間狀態**（例如逾期、無紀錄）就直接寫 SQL：

```sql
-- 例：讓某帳號變成逾期態（> 90 天）
UPDATE users SET last_activity_at = now() - interval '120 days' WHERE username='demo1';
-- 例：讓某帳號變成無紀錄態
UPDATE users SET last_activity_at = NULL WHERE username='demo2';
```

---

## 7. 跑測試（開發時最有用的迴圈）

```bash
# 後端單元測試 —— 不需要資料庫（in-memory SQLite，psycopg 被 mock 掉）
# 但驅動本身要裝（見上節）：有兩個案例開子行程，mock 進不去
cd backend && python -m unittest discover -s tests -v

# 前端 lint + 型別 + build
cd frontend && npm run lint && npm run build

# API 契約沒漂移（改了後端回應形狀就會紅）
cd backend && python scripts/dump_openapi.py --check
cd frontend && npm run check:types

# 改了後端 API 形狀時，兩份產出物都要重產並 commit
cd backend && python scripts/dump_openapi.py
cd frontend && npm run gen:types
```

### e2e（需要 Docker）

e2e **不跑在本機的 dev server 上**，而是對一個短生命週期的完整 stack（db ＋ backend ＋ nginx）執行：

```bash
docker compose -f deploy/docker-compose.test.yml up -d --build
until curl -sf http://localhost:8090/ >/dev/null; do sleep 3; done
cd frontend && BASE_URL=http://localhost:8090 npx playwright test
docker compose -f deploy/docker-compose.test.yml down -v
```

首次要 `npx playwright install chromium`。這個 stack 的資料庫**每次都是全新的**，只有 `admin` 一個帳號 —— 需要多筆資料的測試得自己用公開註冊端點建。

---

## 8. 兩種本機模式，怎麼選

| | **A. 分開跑**（uvicorn ＋ vite） | **B. Docker compose 全 stack** |
|---|---|---|
| 指令 | 上面第 3、4 節 | `docker compose -f deploy/docker-compose.test.yml up -d --build` |
| 進入點 | :5173（前）／:8010（後） | :8090（nginx 統一入口） |
| 熱重載 | ✓ 前後端都有 | ✗ 要重建映像 |
| Debugger | ✓ IDE 直接掛 | 麻煩 |
| 貼近正式環境 | ✗ 沒有 nginx | ✓ 同一套拓樸 |
| **適合** | **日常開發** | **驗收、e2e、重現部署問題** |

### 只有 B 才驗得到的事（H3）

`frontend/nginx.conf` 的 `proxy_buffering off` 與 600 秒 timeout **是功能前提，不是效能調校**。少了它們，A1／A3 的 SSE 串流會被緩衝住（使用者看到長時間空白後一次爆出）或提前斷線。

模式 A 沒有 nginx，SSE 直接打到 uvicorn —— **所以串流在 A 正常不代表在正式環境正常**。任何動到反向代理層的變更，都要用模式 B 驗一次。

---

## 9. 常見卡關

| 症狀 | 原因 | 解法 |
|---|---|---|
| `ModuleNotFoundError: No module named 'services'` | 不在 `backend/` 下啟動 | `cd backend` 再跑 |
| 前端叫得到頁面但 API 全 401／CORS | `CORS_ORIGINS` 沒含前端實際 origin | 對齊 `backend/.env` 與前端 port |
| 改了 `VITE_API_BASE_URL` 沒生效 | 它是 build 期變數 | dev 重啟 vite；Docker 要**重建映像** |
| 改了 `schema_rbac.sql` 沒生效 | 只在空資料目錄執行（H2） | 重建資料庫，或改用 `_ensure_*_schema()` |
| A1 產圖回 500 | 缺金鑰／缺 CLI／`ANTHROPIC_API_KEY` 沒留空 | 見第 5 節的四步 |
| A1 回 402 | OpenRouter 額度或 `max_tokens` 預扣 | 儲值，或調低 `LLM_MAX_OUTPUT_TOKENS` |
| 端點測試 `no such table` | 測試用 in-memory SQLite 需 `StaticPool` | 用 `tests/helpers.py` 的 `make_session()` |
| 手機寬度版面爆掉 | 側邊欄 `w-64` 無斷點折疊（既有問題，全 app） | 已知；由 `260806-a1-a3-ux` intent 處理中 |
| `psql -f schema_rbac.sql` 一張表都沒建，訊息一堆 `current transaction is aborted` | 主機的 PostgreSQL **沒有 pgvector**，第一條 `CREATE EXTENSION` 是硬 ERROR，單一交易整個回滾（H4） | 裝 pgvector 或改用 root compose 的 db，見第 2 節 H4 |
| root compose 的 db 容器反覆重啟，日誌寫 `database files are incompatible with server` | 既有 `postgres_data` volume 是 PG 15 的，映像已改 PG 18（H5） | 移除該 volume 重建，或先 dump 再 restore，見第 2 節 H5 |
| 後端啟動就掛，訊息提到 `EMBEDDING_PROVIDER` | 它是 required、**無預設**，缺值或值不在 `ollama/fastembed/fulltext/stub` 內就大聲失敗 | 在 `backend/.env` 設一個；本機用 `fulltext` 最省事 |
| 設了 `EMBEDDING_PROVIDER=ollama`，後端**正常啟動**，但一用到記憶檢索就拋 `EmbeddingProviderUnavailable`，訊息夾著 `ConnectError`（名稱無法解析） | 範本的 `http://ollama:11434` **過得了** `NFR7.1` 的驗證（它驗主機名的形式，不驗可解析性；`BR1.5` 禁止啟動探測），但 `ollama` 這個名字只在部署 stack 的 compose 網路裡解析得到 | **本機改用 `fastembed`**（`pip install 'fastembed>=0.7,<0.8'`）。`ollama` 只在部署 stack 內成立 |
| 設了 `EMBEDDING_PROVIDER=ollama` 且把主機改成 `localhost`／IP／網域後，後端**拒絕啟動**，訊息提到主機名必須是 compose 內部服務名 | 這是 `NFR7.1` 的刻意行為，不是 bug。該服務零認證、靠網段隔離保護，指到 compose 網路外就是繞過它——記憶文字會以明文送到那個位址 | 同上：本機改用 `fastembed`。不要為了「讓它啟動」而放寬主機名檢查 |
| 後端啟動就掛，訊息提到 model id 不在合法的 `embeddingModel` 集合內 | 改了 `OLLAMA_EMBED_MODEL`／`FASTEMBED_MODEL`，但沒同步 `MEMORY_RECORD_EMBEDDING_MODELS`。擋在啟動是刻意的——否則新舊向量會共用同一個標籤，檢索時被當成可比較而回垃圾且不報錯（ADR-008） | 改回宣告集合內的值，或連同既有列的遷移方式一起改 |
| 後端啟動就掛，訊息提到 `REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD`（`KeyError`）或 `REDIS_USER 不得為 default` | U13 起這三個變數是**後端啟動**的必要條件；`default` 使用者已被收窄為 `+@connection` | 在 `backend/.env` 設齊三個變數，`REDIS_USER` 用 ACL 使用者（建法見第 3 節的 `.env` 註解） |
| 入口頁連線立刻被關閉（關閉碼 **1011**），或對話回「工作階段暫時無法存取」 | 後端起得來（client 延遲連線），但 Redis 此刻連不上：本機沒跑 Redis、或 ACL 使用者沒建／密碼不符 | `redis-cli ping` 應回 PONG；再以 `REDIS_USER` 的身分 `AUTH` 一次確認 ACL |
| 後端啟動就掛，訊息提到 `BRAIN_SESSION_HISTORY_MAX` | 它是 required、**無預設**（`BR3.5`／`NFR8.40`）。缺值不會被讀成「無上限」——那會讓單一 Redis key 無上界成長且無聲 | 在 `backend/.env` 設 `BRAIN_SESSION_HISTORY_MAX=200` |
| 後端啟動就掛，訊息提到 `BRAIN_ROUTER_CONFIDENCE_THRESHOLD` | 它是 required、**無預設**（`BR3.4`／`NFR8.60`）。缺值不會被讀成某個預設門檻——那等於讓「信心不足要不要先問」由一個沒有人選過的數字決定 | 在 `backend/.env` 設 `BRAIN_ROUTER_CONFIDENCE_THRESHOLD=0.7` |
| 後端啟動就掛，訊息提到門檻必須落在 `0 < t <= 1` | 設了 `0`（或大於 1）。擋在啟動是刻意的：門檻 0 會讓反問路徑**永不觸發**，而文件上看起來已解決 | 設一個 0 與 1 之間的值；初版是 `0.7` |
| 啟動 log 出現 `BRAIN_ROUTER_TIMEOUT_SEC 未設定，取預設` 之類的 WARN | 這四個變數**有**預設，缺值只是沒照設定跑，所以是 WARN 不是失敗 | 想消掉 WARN 就在 `backend/.env` 補上；不補也能跑 |
| 對話超過 200 則之後，最舊的訊息不見了 | 這是刻意行為（`BR3.4`）：超限時自該段**最舊**端丟棄。上限**每段獨立**，所以 `/workspace` 的活躍對話不會擠掉 `/assessment` 的歷程 | 不是 bug。要改上限就改 `BRAIN_SESSION_HISTORY_MAX`，並記得部署端要同步 `deploy/render-env.sh` 與 `deploy/.env.example` |

---

## 10. 開發新功能前必讀

| 文件 | 為什麼 |
|---|---|
| `CLAUDE.md` | repo contract、範圍邊界、branch／commit 規則 |
| `aidlc/spaces/default/memory/team.md` | branch 命名、中文 commit type、測試底線 A／B／C |
| `aidlc/spaces/default/memory/project.md` | 專案硬約束（ADR-0006 四面向、schema↔deploy 同步） |
| `aidlc/spaces/default/codekb/cloud-360/` | 逆向工程產出的程式碼知識庫（**先看 `reverse-engineering-timestamp.md` 確認新鮮度**） |
| `DEPLOY.md` | 部署與 schema 演進的正式來源 |

**commit 前一定要跑**：

```bash
python3 scripts/validate_repo_contract.py
python3 scripts/validate_env_contract.py
```

兩支都是 CI `repo-contract` job 的關卡，違反 = CI 紅燈。第二支管的是本機／CI／部署三套環境設定不得混用也不得漏接；它擋下的失敗模式是無聲的——compose 缺值只會變成空字串，服務照常起來但功能默默降級。

**改了設定就要回頭改這份文件**：異動 `backend/database.py` 的 schema 補丁、`deploy/nginx.conf`、任一 `.env.example` 或 `deploy/render-env.sh` 時，同步更新 `LOCAL-DEV.md`。這裡是唯一寫下隱性前置條件（`claude` CLI 子行程、n8n webhook）的地方，過期就等於沒有。
