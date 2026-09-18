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

### 兩個「不在 requirements.txt 裡」的硬依賴

**H1 — LLM 供應商**：`claude-agent-sdk` 不是 HTTP client，它會 **spawn 一個 `claude` CLI 子行程**。鏈路長這樣：

```
FastAPI → claude-agent-sdk → claude CLI 子行程 → 供應商 → 模型
```

供應商由 `LLM_PROVIDER` 決定（`backend/services/llm_provider.py`），本機有兩條路：

| `LLM_PROVIDER` | 認證來源 | 適用 |
|---|---|---|
| `cli`（本機範本的預設） | 你自己 `claude login` 的登入（macOS 存在 Keychain） | 本機。不需金鑰、不燒 OpenRouter 額度 |
| `openrouter`（程式預設、部署用） | `OPENROUTER_API_KEY` | 部署；本機想用 OpenRouter 時也可 |

`cli` 模式需要**登入過**的 CLI。SDK 自帶一份 `claude` 執行檔（`claude_agent_sdk/_bundled/claude`），所以不一定要全域安裝 `@anthropic-ai/claude-code`——但**登入不是自帶的**，你得先在終端機跑過 `claude login`（或已在用 Claude Code）。驗證：

```bash
claude -p "回一個字：好"      # 有回應 = 登入可用
```

`cli` 模式下程式會**主動刪除**兩組變數。這不是潔癖：`.env` 是以 `override=True` 載入的，磁碟上或 shell 裡的殘值都會傳進子行程，而設成空字串不夠，必須刪掉。

| 被刪除的變數 | 留著會怎樣 |
|---|---|
| `ANTHROPIC_BASE_URL`／`ANTHROPIC_AUTH_TOKEN`／`ANTHROPIC_API_KEY` | 只要**非空**就會蓋掉 CLI 自己的登入；前兩者還會讓請求被導去別的端點 |
| `ANTHROPIC_DEFAULT_SONNET_MODEL`／`_OPUS_`／`_HAIKU_` | 它們定義 CLI 的**別名**指向哪個實際模型，會把正規化後的 `sonnet` 又映射回 OpenRouter slug |

第二組特別容易漏，因為它既不認證也不路由。實際踩過的症狀：`.env` 留著 `ANTHROPIC_DEFAULT_SONNET_MODEL=anthropic/claude-sonnet-4.6` 時，即使程式已把模型正規化成 `sonnet`，CLI 仍回 404 —— `There's an issue with the selected model (anthropic/claude-sonnet-4.6)`。

`openrouter` 模式下，`OPENROUTER_API_KEY` 會在啟動時被映射為 `ANTHROPIC_AUTH_TOKEN`，且 `ANTHROPIC_API_KEY` 必須留空，否則 SDK 會繞過 OpenRouter 直連 Anthropic。

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

# LLM 鏈路（A1／A3 必要）
node -v                             # 18+，Dockerfile 用 22
command -v claude && claude --version
# 沒有的話：npm install -g @anthropic-ai/claude-code

# Python
python3 --version                   # CI 用 3.12
```

### 先確認 port 沒被佔用

```bash
for p in 5432 8000 5173; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 \
    && echo ":$p 被佔用 → $(lsof -nP -iTCP:$p -sTCP:LISTEN | awk 'NR==2{print $1}')" \
    || echo ":$p 可用"
done
```

**後端的 port 不是固定的** —— `DEPLOY.md` 寫 8000，但那只是慣例。若 8000 被別的東西佔著（例如本機的 K8s／kind、其他專案），換一個即可，只要 `frontend/.env` 的 `VITE_API_BASE_URL` 跟著改。下文以 `8010` 為例。

---

## 2. 資料庫

```bash
createdb -U postgres -h localhost cloud360
psql "postgresql://postgres:postgres@localhost:5432/cloud360" -f schema_rbac.sql
```

`schema_rbac.sql` 會建立全部資料表、308 列 RBAC 預設矩陣，以及預設帳號 **`admin` / `admin123`**。

### ⚠️ 兩條 schema 演進路徑（踩過就會懂）

| 路徑 | 何時執行 | 注意 |
|---|---|---|
| `schema_rbac.sql` | 你手動跑，或 Docker 的 db 容器**在資料目錄為空時**跑一次 | 既有資料庫**不會**自動重跑（隱性依賴 H2） |
| `backend/database.py` 的 `_ensure_*_schema()` | **每次後端啟動** | 這才是既有環境真正的遷移機制 |

**實務結論**：改了 `schema_rbac.sql` 卻只重啟容器 → 不生效。反過來，多數欄位新增只要**重啟後端**就會被 `_ensure_*_schema()` 的 `ALTER TABLE ... IF NOT EXISTS` 補上。

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
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cloud360
JWT_SECRET=dev_only_change_me
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# LLM 供應商：cli 用你已登入的 claude CLI，不需任何金鑰（見第 0 節 H1）
LLM_PROVIDER=cli

# 只有 LLM_PROVIDER=openrouter 時才需要。留空＝未設定；
# 千萬不要填佔位字串，那會被當成真金鑰送出去。
OPENROUTER_API_KEY=

# 留空即依供應商取預設（cli → sonnet）
LLM_MODEL=

# --- 選填 ---
# N8N_WEBHOOK_URL=https://.../webhook/get-icon
# N8N_USER=
# N8N_PASSWORD=
EOF
```

> `JWT_SECRET` 未設時會**靜默 fallback 到程式碼內的預設字串**（依賴風險 R2），不會報錯。本機無所謂，但要知道它不會提醒你。

要改用 OpenRouter 的話，把 `LLM_PROVIDER` 改成 `openrouter` 並填入 `OPENROUTER_API_KEY` 即可，其餘不用動——所有 `ANTHROPIC_*` 變數都由程式依模式自動處理（openrouter 模式自動填寫，cli 模式主動刪除，見第 0 節 H1 的表）。

> **本機設定與部署設定是分開的兩套，不要互相抄。** `backend/.env`／`frontend/.env` 只服務本機 bare-metal 執行；部署走 `deploy/.env`（由 `deploy/render-env.sh` 產生，範本 `deploy/.env.example`）。把 `localhost` 來源寫進部署範本、或把 `POSTGRES_*`／`PUBLIC_URL` 寫進本機範本，`scripts/validate_env_contract.py` 都會擋下（CI 紅燈）。


> **金鑰安全**：`.env` 已被 `.gitignore` 涵蓋（`.gitignore:17`），可以安心放 `OPENROUTER_API_KEY`。但要知道**這是唯一的防線** —— `validate_repo_contract.py` 的 secret 掃描只讀 contract 清單內的檔案，**看不到 `backend/`／`frontend/`**（`team.md` 已記為既有機制落差）。所以金鑰**絕不要**寫進 `.env` 以外的地方，例如貼進程式碼、測試或文件。

### 建議用 venv（避免污染系統 Python）

`requirements.txt` 對 `fastapi` 與 `pydantic` 做了**精確等值釘選**（`==`）—— 這是 OpenAPI 規格漂移 gate 的前提，`pip install` 會把你環境裡的版本改成釘選值。

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

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
   worktree，症狀是「`backend/.env` 明明寫著 `LLM_PROVIDER=cli`，API 卻回報尚未設定
   `OPENROUTER_API_KEY`」。查法：
   ```bash
   # 找出跑著的 uvicorn 究竟在哪個目錄
   lsof -p "$(pgrep -f 'uvicorn main:app')" | awk '$4=="cwd" {print $NF}'
   ```
   訊息本身也能分辨版本：新版的那句後面會接「本機開發也可改設 LLM_PROVIDER=cli」，
   沒有那句就是舊碼。
1. `backend/.env` 的 `OPENROUTER_API_KEY` 有沒有值（`LLM_PROVIDER=cli` 時不需要）
2. `command -v claude` 找不找得到
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
# 後端單元測試 —— 不需要資料庫（in-memory SQLite，psycopg2 被 mock 掉）
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
