# 手動測試案例 — 本機 LLM 供應商與架構圖圖示

> 由 `tcms-test-cases` stage 產出，同步工具讀取的就是本檔。
> 格式契約見 `aidlc/spaces/default/knowledge/aidlc-quality-agent/test-case-authoring.md`。
> 標題是同步鍵——改標題會在 TCMS 建出第二個案例，而不是更新第一個。

同步：

```bash
python3 scripts/tcms_sync.py \
  --file aidlc/spaces/default/intents/260802-last-login-column/construction/tcms-test-cases/manual-test-cases.md \
  --dry-run
```

---

## TC: LLM_PROVIDER=cli 時 A1 產圖可用，且全程不需 OpenRouter 憑證

- plan: 本機 LLM 供應商與架構圖圖示（手動）
- priority: P1

### 目的

驗證本機開發者能**只靠自己已登入的 `claude` CLI**跑通 A1，不必持有 OpenRouter 金鑰。

此路徑在自動化層零覆蓋：`ui-regression` 的 Playwright 套件刻意不碰任何 LLM
呼叫（會產生費用且外部不穩），所以只能以手動案例守住。

### 背景

`claude-agent-sdk` 不是 HTTP client，它會 **spawn 一個 `claude` CLI 子行程**：

```
FastAPI → claude-agent-sdk → claude CLI 子行程 → 供應商 → 模型
```

`LLM_PROVIDER=cli` 時由 CLI 用自己的登入認證（macOS Keychain／`~/.claude`），
後端會主動**刪除**會蓋掉該登入的環境變數。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. `claude` CLI 已登入，且以下指令有回應：
   ```bash
   claude -p "回一個字：好"
   ```
6. `backend/.env` 設定為：
   ```
   LLM_PROVIDER=cli
   OPENROUTER_API_KEY=
   ```
   `OPENROUTER_API_KEY` 必須**留空**，不可填佔位字串——程式判斷「有沒有設定」
   看的是非空。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 確認 `backend/.env` 的 `LLM_PROVIDER=cli` 且 `OPENROUTER_API_KEY` 為空值 | 兩者符合 |
| 2 | 重啟後端 | 啟動無錯誤，`/openapi.json` 可取得 |
| 3 | 觀察後端啟動 log | 出現 `LLM_PROVIDER=cli：已移除 ...，改用 claude CLI 自帶的登入認證`（若 `.env` 內無殘留變數則不會出現此行，屬正常） |
| 4 | 瀏覽器開啟前端，以 `admin` / `admin123` 登入 | 進入 `/workspace` |
| 5 | 在架構對話輸入框輸入一段需求，例如「幫我設計一個處理使用者上傳文件並呼叫 AI 模型的無伺服器架構」並送出 | 顯示進行中狀態，最終取得**文字回應**（可能是澄清提問，也可能直接產圖，兩者皆算通過） |
| 6 | 觀察後端 log | **無** 401、**無** 404、無 `There's an issue with the selected model` |
| 7 | 確認未使用 OpenRouter：檢查 `.env` 的 `OPENROUTER_API_KEY` 仍為空 | 仍為空，且步驟 5 已成功 |

### 通過條件

- 步驟 5 取得真實模型回應（非錯誤訊息、非佔位文字）。
- 步驟 6 log 中沒有任何認證或模型不存在的錯誤。
- 全程未提供任何 OpenRouter 憑證。

### 失敗徵兆與對應肇因

| 徵兆 | 可能肇因 |
|---|---|
| 回應為「尚未設定 OPENROUTER_API_KEY」 | `LLM_PROVIDER` 沒讀到 `cli`（拼字、未重啟後端） |
| CLI 回 404 model 不存在 | `.env` 殘留 `ANTHROPIC_DEFAULT_*_MODEL`，見案例「.env 殘留 OpenRouter 變數時 cli 模式仍可用」 |
| CLI 提示 connectors disabled / takes precedence over your claude.ai login | 有非空的 `ANTHROPIC_AUTH_TOKEN` 或 `ANTHROPIC_API_KEY` |

### 追溯

- 實作：`backend/services/llm_provider.py`
- 文件：`LOCAL-DEV.md` 第 0 節 H1
- PR #499
- User story：A1

---

## TC: backend/.env 殘留 OpenRouter 變數時，cli 模式仍可正常取得模型回應

- plan: 本機 LLM 供應商與架構圖圖示（手動）
- priority: P1

### 目的

回歸案例。驗證 `.env` 裡**殘留的 OpenRouter 設定不會癱瘓 cli 模式**。

這是實測踩過的缺陷：模型名稱正規化與環境變數刪除**互相抵銷**，導致每次
請求都 404。

### 背景（缺陷原貌）

`ANTHROPIC_DEFAULT_*_MODEL` 定義的是 CLI 的**別名**指向哪個實際模型，
不是「要用哪個模型」。所以即使程式已把殘留的 gateway slug 正規化成 `sonnet`，
子行程仍會照著這個變數把 `sonnet` 映射回原本的 slug：

```
LLM_PROVIDER=cli + .env 殘留 ANTHROPIC_DEFAULT_SONNET_MODEL=anthropic/claude-sonnet-4.6
→ claude -p ... --model sonnet
→ 404 There's an issue with the selected model (anthropic/claude-sonnet-4.6)
```

這一族變數容易被漏掉，因為它既不認證也不路由——不在「哪些變數會蓋掉 CLI
登入」的心智模型裡。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. `claude` CLI 已登入。
6. `backend/.env` **刻意**設定成一個從 OpenRouter 切回來、殘值未清的狀態：
   ```
   LLM_PROVIDER=cli
   OPENROUTER_API_KEY=
   ANTHROPIC_BASE_URL=https://openrouter.ai/api
   ANTHROPIC_DEFAULT_SONNET_MODEL=anthropic/claude-sonnet-4.6
   LLM_MODEL=anthropic/claude-sonnet-4.6
   ```

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 依上述前置設定 `backend/.env`（保留全部三個殘留變數） | 設定完成 |
| 2 | 重啟後端 | 啟動成功 |
| 3 | 觀察啟動 log | 出現 `LLM_PROVIDER=cli：已移除 ANTHROPIC_BASE_URL、ANTHROPIC_DEFAULT_SONNET_MODEL，改用 claude CLI 自帶的登入認證` |
| 4 | 登入前端並在 A1 送出任一架構需求 | 取得真實模型回應 |
| 5 | 檢查後端 log **沒有** `There's an issue with the selected model` | 無此訊息 |
| 6 | 檢查後端 log **沒有** 404 | 無 404 |

### 通過條件

- 步驟 3 的移除訊息包含 `ANTHROPIC_DEFAULT_SONNET_MODEL`（不只認證那三個）。
- 步驟 4 取得回應而非錯誤。

### 備註

殘留變數**留在 `.env` 裡是無害的**——程式在執行期刪除它們。本案例的重點正是
「即使沒清乾淨也不該壞」。若要順手清掉也可以，但不影響本案例判定。

### 追溯

- 實作：`backend/services/llm_provider.py` 的 `_CLI_ALIAS_MODEL_VARS`
- 自動化對應：`backend/tests/test_llm_provider.py::CliModeClearsConflictingVars`
- PR #499 · commit 2511e3d
- User story：A1

---

## TC: LLM_PROVIDER=openrouter 但未設金鑰時，回應可直接指出肇因

- plan: 本機 LLM 供應商與架構圖圖示（手動）
- priority: P2

### 目的

驗證**缺少金鑰**這個最常見的設定錯誤，得到的是一句說得出肇因的訊息，
而不是離肇因三層遠的上游 401。

### 背景

範本曾經出貨**非空**佔位字串（`OPENROUTER_API_KEY=your_openrouter_api_key_here`），
而程式判斷「有沒有設定」看的是非空——照著範本複製、還沒填金鑰的人拿到的
不是「你還沒設定」，而是 OpenRouter 回的 `401 Missing Authentication header`。
範本現已一律出空值、範例寫在註解裡。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — 錯誤訊息呈現於對話串，非獨立頁面

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. `backend/.env` 設定為：
   ```
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=
   ANTHROPIC_AUTH_TOKEN=
   ```

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 依前置設定 `.env`（兩個憑證欄位皆**留空**，不要填任何佔位字串） | 設定完成 |
| 2 | 重啟後端 | 啟動成功（缺金鑰不該讓 API 起不來） |
| 3 | 登入前端並在 A1 送出任一架構需求 | 回應為明確訊息，內容包含 `尚未設定 OPENROUTER_API_KEY`，且提示可改用 `LLM_PROVIDER=cli` |
| 4 | 確認訊息**不是** 401 / Missing Authentication header | 不含這類上游錯誤字樣 |
| 5 | 把 `OPENROUTER_API_KEY` 改成佔位字串 `your_openrouter_api_key_here` 並重啟 | 此時會被當成真金鑰送出，得到上游 401——**這是預期中的錯誤示範**，用以說明為何欄位必須留空 |
| 6 | 將 `OPENROUTER_API_KEY` 改回空值並重啟 | 回到步驟 3 的明確訊息 |

### 通過條件

- 步驟 3 的訊息同時點名 `OPENROUTER_API_KEY` 與 `LLM_PROVIDER=cli` 兩條出路。
- 步驟 2 後端仍能啟動。

### 追溯

- 實作：`backend/services/llm_provider.py` 的 `llm_auth_ready` / `auth_error_message`
- 範本：`backend/.env.example`
- 佔位值防線：`scripts/validate_env_contract.py` 第七道檢查（掃描範本，非使用者的 `.env`）
- User story：A1

---

## TC: LLM_PROVIDER 填入無效值時退回 openrouter 並記警告，不使 API 中止

- plan: 本機 LLM 供應商與架構圖圖示（手動）
- priority: P3

### 目的

驗證一個**選填變數的拼字錯誤不會讓整個後端起不來**，而是退回預設並留下可查的警告。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. `backend/.env` 設定為：
   ```
   LLM_PROVIDER=anthropic-direct
   OPENROUTER_API_KEY=
   ```
   （`anthropic-direct` 是刻意的無效值；有效值只有 `openrouter` 與 `cli`。）

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 依前置設定 `.env` | 設定完成 |
| 2 | 重啟後端 | **啟動成功**，不因無效值而中止 |
| 3 | 觀察 log | 出現 WARNING：`LLM_PROVIDER='anthropic-direct' 不是有效值（可用：openrouter、cli），退回 openrouter` |
| 4 | 登入前端並在 A1 送出需求 | 因已退回 openrouter 且無金鑰，得到「尚未設定 OPENROUTER_API_KEY」的明確訊息 |
| 5 | 把值改成 `  CLI  `（前後含空白、大寫）並重啟 | 被正規化為 `cli`，不出現警告 |

### 通過條件

- 步驟 2 後端啟動成功。
- 步驟 3 警告訊息列出有效值清單。
- 步驟 5 大小寫與前後空白不影響判定。

### 追溯

- 實作：`backend/services/llm_provider.py` 的 `get_provider`
- 自動化對應：`backend/tests/test_llm_provider.py::ProviderSelection`
- User story：A1

---

## TC: 架構圖節點顯示正確的 AWS 圖示，縮寫服務（SNS／KMS／S3）不得誤配

- plan: 本機 LLM 供應商與架構圖圖示（手動）
- priority: P1

### 目的

回歸案例。驗證架構圖上每個節點拿到的是**該服務自己的圖示**，特別是三個實測
會誤配的縮寫服務。

### 背景（缺陷原貌）

n8n webhook 回傳的是**整份圖示目錄**（約 1.1 MB、315 項，目前只收 AWS），
由後端自行在其中比對服務名稱。舊實作有兩個問題：

1. **比對全滅時退回 `data[0]`**，而目錄第一項是 `Auto-Scaling-group`。實測
   315 項裡沒有任何 `icon_name` 含 `SNS` 或 `KMS`——它們叫
   `Simple Notification Service` 與 `AWS Key Management Service`。於是 SNS 與
   KMS 節點都畫出 Auto Scaling 的圖示，**且完全沒有 log**。
2. **取第一個子字串命中**：`S3` 唯一的子字串命中是 `S3 on Outposts`，於是拿到
   錯的儲存服務圖示。

錯的圖示比灰底更難發現——灰底至少看得出來沒拿到。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布
- 外部相依: n8n webhook（`N8N_WEBHOOK_URL`）——回傳整份圖示目錄的 JSON 陣列，由後端 `diagram_builder` 比對服務名稱後以 base64 內嵌進 mxGraph XML

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. LLM 供應商可用（`LLM_PROVIDER=cli` 或有效的 `openrouter` 金鑰）。
6. `backend/.env` 設定有效的 webhook：
   ```
   N8N_WEBHOOK_URL=https://n8n.danniel.cc/n8n/webhook/cloudicon
   ```
   確認可達（應回 HTTP 200 且為 JSON 陣列）：
   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' -X POST \
     https://n8n.danniel.cc/n8n/webhook/cloudicon \
     -H 'Content-Type: application/json' \
     -d '{"service":"Lambda","provider":"AWS"}'
   ```

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 依前置設定 `N8N_WEBHOOK_URL` 並**重啟後端** | 設定生效 |
| 2 | 登入前端，於 A1 送出一段會用到多種服務的需求，例如「設計一個 AWS 無伺服器架構，包含 Lambda、S3、DynamoDB、SNS、KMS、CloudWatch、API Gateway、CloudFront、WAF」 | 產出架構圖 |
| 3 | 檢視圖上 **Lambda** 節點 | 顯示 AWS Lambda 圖示（非灰底、非其他服務） |
| 4 | 檢視 **S3** 節點 | 顯示 Simple Storage Service 圖示，**不得**是 `S3 on Outposts` 的圖示 |
| 5 | 檢視 **SNS** 節點 | 顯示 Simple Notification Service 圖示，**不得**是 Auto Scaling group 圖示 |
| 6 | 檢視 **KMS** 節點 | 顯示 AWS Key Management Service 圖示，**不得**是 Auto Scaling group 圖示 |
| 7 | 檢視 DynamoDB、CloudWatch、API Gateway、CloudFront、WAF 節點 | 各自顯示對應圖示 |
| 8 | 確認圖上**沒有任何兩個不同服務共用同一個圖示** | 無重複誤配 |
| 9 | 檢查後端 log | 無 `查無 ... 的圖示` 的 WARNING（本案例的服務都應命中） |

### 通過條件

- 步驟 3–7 每個節點都顯示各自正確的圖示。
- 步驟 8 無重複誤配（這是舊缺陷最明顯的外觀特徵：多個服務長得一模一樣）。

### 備註

**既有的圖不會自動更新**。圖示是產圖當下以 base64 內嵌進 mxGraph XML 的，
所以修改 `N8N_WEBHOOK_URL` 後必須**重新產一張圖**才看得到差異。

### 追溯

- 實作：`backend/services/diagram_builder.py` 的 `_select_icon_entry` / `_SERVICE_ABBREVIATIONS`
- 自動化對應：`backend/tests/test_diagram_icons.py::Selection`
- 文件：`LOCAL-DEV.md` 第 0 節「圖示目錄」
- PR #499 · commit 806d5d0
- User story：A1

---

## TC: N8N_WEBHOOK_URL 未設定時圖示降級為灰底，產圖流程不中斷

- plan: 本機 LLM 供應商與架構圖圖示（手動）
- priority: P2

### 目的

驗證 n8n 是**選填依賴**：沒有它，架構圖照樣產得出來，只是圖示變成灰底佔位圖。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布
- 外部相依: n8n webhook（本案例刻意不設定）

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. LLM 供應商可用。
6. `backend/.env` 的 `N8N_WEBHOOK_URL` **留空**：
   ```
   N8N_WEBHOOK_URL=
   ```
   注意是留空，**不是**填佔位字串——填了佔位字串屬於另一個案例。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 依前置把 `N8N_WEBHOOK_URL` 設為空值並重啟後端 | 設定生效 |
| 2 | 登入前端，於 A1 送出任一 AWS 架構需求 | **成功產出架構圖**，不報錯、不中斷 |
| 3 | 檢視圖上各節點 | 全部為灰底方塊，方塊中央有服務名稱文字 |
| 4 | 確認節點的連線、群組（VPC／AZ／Subnet）、標籤都正常 | 圖的結構完整，只有圖示是佔位圖 |
| 5 | 檢查後端 log | 不應出現 n8n 請求失敗的 WARNING（未設定屬預期狀態，不是失敗） |

### 通過條件

- 步驟 2 產圖成功。
- 步驟 3 為灰底佔位圖且可辨識服務名稱。
- 步驟 5 未設定時不製造噪音 log。

### 追溯

- 實作：`backend/services/diagram_builder.py` 的 `fetch_icon_from_n8n`
- 自動化對應：`backend/tests/test_diagram_icons.py::FetchSucceeds::test_unset_webhook_url_returns_the_placeholder`
- 文件：`LOCAL-DEV.md` 第 0 節功能對照表
- User story：A1

---

## TC: n8n webhook 不可用時降級為灰底並留下 WARNING，不得靜默

- plan: 本機 LLM 供應商與架構圖圖示（手動）
- priority: P1

### 目的

回歸案例。驗證每一條圖示降級路徑**都說得出話**。

### 背景（缺陷原貌）

HTTP 非 200 時舊實作是直接 `return fallback_svg`，**一行 log 都沒有**：

```python
if response.status_code != 200:
    return fallback_svg          # ← 原本這裡沒有任何 log
```

這是最難查的一種降級——服務照常回圖，只是每個 icon 都變灰底，沒有任何地方
說得出為什麼。另一個實例是佔位字串：範本的 `your_n8n_webhook_url_here` 是
**非空**值，程式因此真的拿它去發請求，每個節點都失敗一次。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布
- 外部相依: n8n webhook（本案例刻意指向無效／非 200 位址）

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. LLM 供應商可用。

### 測試步驟

#### 情境一：URL 無效（模擬照抄舊範本佔位值）

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 把 `N8N_WEBHOOK_URL` 設為 `your_n8n_webhook_url_here` 並重啟後端 | 設定生效 |
| 2 | 於 A1 產出一張含多個節點的架構圖 | 產圖成功，圖示全為灰底 |
| 3 | 檢查後端 log | **每個節點**都有一行 WARNING：`向 n8n 取得 <服務> 圖示（供應商：AWS）失敗: Request URL is missing an 'http://' or 'https://' protocol.` |

#### 情境二：webhook 回非 200

| # | 操作 | 預期結果 |
|---|---|---|
| 4 | 把 `N8N_WEBHOOK_URL` 指向一個會回非 200 的位址（例如 `https://n8n.danniel.cc/n8n/webhook/does-not-exist`）並重啟後端 | 設定生效 |
| 5 | 於 A1 產出架構圖 | 產圖成功，圖示全為灰底 |
| 6 | 檢查後端 log | 出現 WARNING 且**包含實際的 HTTP 狀態碼**，例如：`n8n 取得 Lambda 圖示（供應商：AWS）回應 HTTP 404，改用灰底佔位圖` |

#### 復原

| # | 操作 | 預期結果 |
|---|---|---|
| 7 | 把 `N8N_WEBHOOK_URL` 改回 `https://n8n.danniel.cc/n8n/webhook/cloudicon` 並重啟 | 重新產圖後圖示恢復正常 |

### 通過條件

- 情境一、二都**產圖成功**（降級不等於失敗）。
- 情境二的 log **含狀態碼**——這正是舊實作缺的那一行。
- 沒有任何一條降級路徑是靜默的。

### 追溯

- 實作：`backend/services/diagram_builder.py` 的 `fetch_icon_from_n8n`
- 自動化對應：`backend/tests/test_diagram_icons.py::FetchFallsBackLoudly`
- PR #499 · commit 806d5d0
- User story：A1

---

## TC: 非 AWS 服務（GCP／Azure）的圖示降級為灰底，不得給出相近的錯誤圖示

- plan: 本機 LLM 供應商與架構圖圖示（手動）
- priority: P2

### 目的

驗證**目錄裡沒有的服務會誠實地變成灰底**，而不是被硬配到一個看起來很像的 AWS 圖示。

### 背景

n8n 圖示目錄目前**只收 AWS**（315 項，`provider` 全為 AWS）。GCP／Azure 的
服務本來就比對不到，灰底是**預期行為**，不是壞掉。

危險的是「差不多就好」的比對。實測發現的兩個誤配：

- `BigQuery` 命中目錄裡一個叫 **`Q`** 的圖示（`"q"` 是 `"bigquery"` 的子字串）
- `Cloud Spanner` 命中 **`AWS-Cloud`**（`"cloud"` 是 `"cloud spanner"` 的子字串）

兩者都會給出一個看似正常、實則完全錯誤的圖示。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布
- 外部相依: n8n webhook（目錄目前只收 AWS，315 項）

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. LLM 供應商可用。
6. `N8N_WEBHOOK_URL` 設為有效值 `https://n8n.danniel.cc/n8n/webhook/cloudicon` 並已重啟後端。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 於 A1 送出一段 **GCP** 架構需求，例如「設計一個 GCP 架構，使用 Cloud Run、BigQuery、Cloud Spanner、Cloud Storage」 | 產出架構圖 |
| 2 | 檢視 **BigQuery** 節點 | 顯示**灰底佔位圖**，不得是任何 AWS 圖示（尤其不得是單字母 `Q` 的圖示） |
| 3 | 檢視 **Cloud Spanner** 節點 | 顯示**灰底佔位圖**，不得是 AWS-Cloud 圖示 |
| 4 | 檢視其餘 GCP 節點 | 皆為灰底佔位圖 |
| 5 | 檢查後端 log | 每個未命中的服務都有 WARNING：`n8n 目錄（315 項）查無 <服務>（供應商：GCP）的圖示，改用灰底佔位圖` |
| 6 | 於 A1 另外送出一段 AWS 需求 | AWS 服務仍正常顯示各自圖示（確認本規則沒有誤傷 AWS 路徑） |

### 通過條件

- GCP 服務全部為灰底，且 log 說得出「查無對應」。
- AWS 服務不受影響。

### 備註

若日後 n8n 目錄補上 GCP／Azure 圖示，本案例的預期結果需同步更新——屆時
應改為驗證各雲的圖示正確顯示。

### 追溯

- 實作：`backend/services/diagram_builder.py` 的 `_icon_match_score`
- 自動化對應：`backend/tests/test_diagram_icons.py::Selection::test_a_catalogue_name_buried_in_the_service_name_is_not_a_match`
- 文件：`LOCAL-DEV.md` 第 0 節「圖示目錄」
- User story：A1

---

## TC: A1 以自然語言產出架構圖並正確渲染群組與連線

- plan: A1 架構產圖端到端（手動）
- priority: P1

### 目的

A1 的主線流程：一段自然語言需求 → 一張可讀的架構圖。

此流程在 `ui-regression` 自動化套件中**刻意跳過**（會呼叫 LLM、產生費用、
外部不穩），是手動測案的主要覆蓋對象。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. LLM 供應商可用（`LLM_PROVIDER=cli` 或有效的 `openrouter` 金鑰）。
6. `N8N_WEBHOOK_URL` 已設為有效值（圖示才會出現；未設不影響本案例的結構判定）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 以 `admin` / `admin123` 登入 | 進入 `/workspace` |
| 2 | 在架構對話輸入框輸入具體需求，例如「設計一個 AWS 三層式架構，前端走 CloudFront，應用層用 ECS 跑在兩個可用區的私有子網，資料庫用 RDS 多可用區部署」 | 顯示進行中狀態 |
| 3 | 等待回應完成 | 產出架構圖並渲染於畫布 |
| 4 | 檢視**群組結構** | VPC／可用區／子網等群組正確巢狀，子節點落在對應群組內、未溢出邊界 |
| 5 | 檢視**節點** | 每個提及的服務都有對應節點，且標籤文字正確 |
| 6 | 檢視**連線** | 連線以正交（orthogonal）路徑呈現，起訖端點接在節點上，未與節點圖示重疊 |
| 7 | 檢視跨可用區的元件配置 | 兩個可用區都有內容，符合需求描述的多可用區部署 |
| 8 | 檢查後端 log | 無例外堆疊、無 500 |

### 通過條件

- 步驟 3 成功產圖。
- 步驟 4–7 圖的結構與需求描述一致且可讀。

### 備註

LLM 產出**本質上不是逐字可重現**的，因此本案例判定的是**結構性質**（群組巢狀
正確、節點齊備、連線可讀），不是逐字比對某個固定圖形。

### 追溯

- 實作：`backend/services/agent_router.py`（`POST /api/architecture/generate`）、`backend/services/design_agent.py`、`backend/services/diagram_builder.py`
- 前端：`frontend/src/pages/WorkspacePage.tsx`
- User story：A1

---

## TC: A1 在需求資訊不足時先提出澄清問題，而非逕自臆測產圖

- plan: A1 架構產圖端到端（手動）
- priority: P2

### 目的

驗證 A1 面對**資訊不足**的需求時，會先問清楚關鍵前提（例如雲端平台），
而不是自行假設並產出一張沒有依據的圖。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. LLM 供應商可用。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 以 `admin` / `admin123` 登入並進入 `/workspace` | 進入工作區，架構對話輸入框可見 |
| 2 | 送出一段**刻意不指定雲端平台**的需求，例如「我要一套需求管理與測試生成的系統，可以上傳文件、呼叫 AI 模型、儲存結果」 | 回應是文字提問，畫布上**不得**出現任何架構圖 |
| 3 | 檢視提問內容 | 提問中出現「AWS」「GCP」「Azure」至少 3 個平台選項，且每個選項有一句說明 |
| 4 | 回覆其中一個平台，例如「A. AWS」 | 對話繼續（再問下一個前提，或直接產圖），**不得**回覆無法理解 |
| 5 | 完成必要問答後檢視圖上的服務名稱 | 全部屬於步驟 4 所選平台（選 AWS 則出現 Lambda／S3／RDS 這類名稱），**不得**出現其他雲的服務名（如 BigQuery、Azure Functions） |
| 6 | 檢查後端 log | 無 traceback，無 HTTP 500 |

### 通過條件

- 步驟 2 得到澄清提問而非臆測產圖。
- 步驟 5 最終的圖與步驟 4 所選平台一致。

### 備註

問答輪數不固定，屬 LLM 行為；判定重點是「**資訊不足時會先問**」與
「**答案被採納**」，不是特定的問題數量或文字。

### 追溯

- 實作：`backend/prompts/cloud_architecture_system_prompt.md`、`backend/services/design_agent.py`
- User story：A1

---

## TC: A1 產出的架構圖可儲存，並於清單再次開啟時內容一致

- plan: A1 架構產圖端到端（手動）
- priority: P2

### 目的

驗證 A1 產出的圖能落地保存，且**重新開啟後與當初產出的內容一致**（含圖示）。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- API: `POST /api/collab/diagrams` → 200 — 儲存架構圖
- API: `GET /api/collab/diagrams` → 200 — 架構圖清單
- API: `GET /api/collab/diagrams/{diagram_id}` → 200 — 讀回單張架構圖
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. LLM 供應商可用。
6. `N8N_WEBHOOK_URL` 已設為有效值（用以驗證圖示隨圖一起保存）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 登入並於 A1 產出一張 AWS 架構圖 | 產圖成功且圖示正常 |
| 2 | 記錄圖上的節點數與幾個代表性服務名稱 | 已記錄，作為後續比對基準 |
| 3 | 儲存該架構圖並給一個可辨識的名稱 | 儲存成功並顯示成功回饋 |
| 4 | 離開目前畫面並回到架構圖清單 | 清單中出現剛儲存的項目，名稱正確 |
| 5 | 重新開啟該架構圖 | 圖正常載入 |
| 6 | 比對節點數、服務名稱、群組結構與步驟 2 的紀錄 | 完全一致 |
| 7 | 確認**圖示**仍正常顯示 | 圖示與儲存前相同（圖示以 base64 內嵌於 XML，應隨圖保存） |
| 8 | 重新整理瀏覽器後再開啟一次 | 內容仍一致 |

### 通過條件

- 步驟 6、7 重新開啟後內容與圖示皆與儲存前一致。

### 備註

圖示是**產圖當下**內嵌進 mxGraph XML 的。因此若在儲存後才修改
`N8N_WEBHOOK_URL`，既有的圖**不會**跟著改變——那是預期行為，不是缺陷。

### 追溯

- 實作：`backend/services/diagram_builder.py`（base64 內嵌）、架構圖 CRUD 端點
- User story：A2／A4（架構圖 CRUD／分享）

---

## TC: A1 擋下與雲端架構無關或意圖竄改平台的輸入，且不呼叫 LLM

- plan: A1 架構產圖端到端（手動）
- priority: P1

### 目的

驗證平台自我竄改預檢：命中時**不呼叫 LLM**，直接回固定訊息。

### 背景

依專案規則，design／generate 進 agent 前必須做平台自我竄改預檢（Cloud-360
自身的資料庫、系統值、API key、金鑰等）；命中則不呼叫 LLM，回固定訊息
「此需求毫無相關，請重新輸入」，並以 system prompt 補強。

這同時是**安全**與**成本**控制：不相關或惡意輸入不該消耗 LLM 額度。

### 受測介面

- API: `POST /api/architecture/generate` → 200 — A1 對話產圖；回應含助理訊息與（產圖時）mxGraph XML
- UI: `/workspace` — A1 工作區：架構對話輸入框、送出鈕、圖面畫布

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. LLM 供應商可用（用以確認「有能力呼叫但刻意不呼叫」）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 以 `admin` / `admin123` 登入並進入 `/workspace` | 進入工作區，架構對話輸入框可見 |
| 2 | 送出一段意圖取得平台自身資訊的輸入，例如詢問本系統的資料庫連線設定或金鑰 | 回應為固定訊息「此需求毫無相關，請重新輸入」 |
| 3 | 檢查後端 log | **未**出現 LLM 呼叫（無 claude CLI 子行程、無模型回應紀錄） |
| 4 | 送出一段與雲端架構完全無關的輸入（例如請它寫一首詩） | 回應為同一則固定訊息或明確拒絕，不產出架構圖 |
| 5 | 送出一段正常的雲端架構需求 | **正常產圖**——確認預檢沒有誤擋正當需求 |
| 6 | 檢查回應內容 | 不得洩漏任何環境變數、連線字串、金鑰或系統內部路徑 |

### 通過條件

- 步驟 2、4 被擋下且訊息固定。
- 步驟 3 確認未呼叫 LLM（成本與攻擊面都不該被消耗）。
- 步驟 5 正當需求不受影響（無誤擋）。
- 步驟 6 無任何敏感資訊外洩。

### 追溯

- 規則來源：`aidlc/spaces/default/memory/project.md` `## Mandated`
- 實作：`backend/services/design_agent.py`、`backend/prompts/cloud_architecture_system_prompt.md`
- 安全基準：ADR-0006（IAM／encryption／network exposure／audit logging）
- User story：A1

---

## TC: A3 改善建議在 LLM 可用時產出建議，不可用時降級為 rules_only 且出聲

- plan: A1 架構產圖端到端（手動）
- priority: P2

### 目的

驗證 A3 的兩種狀態都正確：LLM 可用時給出 LLM 建議；不可用時**降級為規則層**
並且**看得出來已降級**。

### 背景

A3 的 Well-Architected 離線規則打分只需要 PostgreSQL，但「改善建議」需要 LLM。
Offline Lens agent 填答在 LLM 不可用時會降級為規則啟發式——這個降級原本是
**靜默**的，使用者看不出 A3 的答案不是 LLM 產生的，後來才補上 WARNING。

### 受測介面

- API: `POST /api/architecture/reviews` → 200 — 建立評核
- API: `GET /api/architecture/reviews/{review_id}` → 200 — 讀回評核與建議
- API: `POST /api/architecture/reviews/{review_id}/retry-suggestions` → 200 — 重試建議產生
- UI: `/assessment` — A3 評核頁：規則層分數與改善建議區塊

### 前置條件

#### 共用

1. PostgreSQL 已啟動且 `cloud360` 資料庫已套用 `schema_rbac.sql`：
   ```bash
   pg_isready -h localhost -p 5432
   ```
2. 後端於專案根目錄啟動（預設 8000；本文件以 `<PORT>` 表示實際埠號）：
   ```bash
   cd backend && source .venv/bin/activate && uvicorn main:app --reload
   ```
3. 前端已啟動，且 `frontend/.env` 的 `VITE_API_BASE_URL` 指向後端實際埠號。
4. 測試帳號 `admin` / `admin123`（`schema_rbac.sql` 內建，角色 Platform_Admin）。

> 改動 `backend/.env` 後**必須重啟後端**：`--reload` 只監看 `.py`，不監看 `.env`。

#### 本案例額外

5. 已有一張可供評核的架構圖（可由 Plan B 的產圖案例先行建立）。

### 測試步驟

#### 情境一：LLM 可用

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 設定可用的 LLM 供應商（`LLM_PROVIDER=cli` 或有效金鑰）並重啟後端 | 設定生效 |
| 2 | 登入後進入 `/assessment` | 頁面正常載入 |
| 3 | 對既有架構圖執行評核 | 規則層分數正常產出 |
| 4 | 取得改善建議 | 產出 LLM 生成的建議內容 |
| 5 | 檢查後端 log | 無降級 WARNING |

#### 情境二：LLM 不可用

| # | 操作 | 預期結果 |
|---|---|---|
| 6 | 將 `.env` 改為 `LLM_PROVIDER=openrouter` 且 `OPENROUTER_API_KEY` 留空，重啟後端 | 設定生效 |
| 7 | 重新執行評核 | **規則層分數仍正常產出**（此層不需 LLM） |
| 8 | 取得改善建議 | 降級為 `rules_only`，且介面或回應可辨識出這是規則層結果 |
| 9 | 檢查後端 log | 出現降級的 WARNING，說得出降級原因 |
| 10 | 還原可用的 LLM 設定並重啟 | 回到情境一的行為 |

### 通過條件

- 情境一產出 LLM 建議。
- 情境二**規則層仍可用**（不因 LLM 缺席而整頁失敗）。
- 情境二的降級**有 log**，不是靜默。

### 追溯

- 實作：`backend/services/wa_lens_engine.py`、`backend/services/review_agent.py`、`backend/services/lens_router.py`
- 文件：`LOCAL-DEV.md` 第 0 節功能對照表
- User story：A3

---
