# 手動測試案例 — 261116-brain-create-diagram（大腦直接建立新架構圖）

> 只收「只能手動」的行為。外部可觀察行為的完整盤點與分桶理由見同目錄的 `automation-test-plan.md`。
> 本檔三案都落在 repo 的結構性盲區：前兩案需要**真實路由模型**（後端測試的路由一律是替身，
> `ui-regression` 的 stack 刻意不設模型金鑰），第三案需要**已有歷史資料的真實 PostgreSQL**
> （單元測試走 SQLite，build-and-test 的 PostgreSQL 驗證只跑了欄位相關的 SQL 敘述）。
>
> 共用環境（以下各案的前置條件會引用）：
>
> - **本機 stack**：依 `LOCAL-DEV.md` 第 0 節備妥 PostgreSQL（含 pgvector，已套用 `schema_rbac.sql`）與 Redis，
>   後端 `cd backend && uvicorn main:app --reload --port 8010`、前端 `cd frontend && npm run dev`。
>   **改了 `backend/.env` 一定要重啟後端**——`--reload` 只監看 `.py`。
> - **模型**：`backend/.env` 設 `APP_ENV=local`、`LLM_PROVIDER=claude-code`、`BRAIN_ROUTER_TIMEOUT_SEC=60`，且
>   `claude -p "回一個字：好"` 有回應；或設 `LLM_PROVIDER=openrouter` 與有效的 `OPENROUTER_API_KEY`。
>   **每跑一次都會花費模型用量。**
> - **帳號**：本機 `admin`／`admin123`（`APP_ENV=local` 且未設 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD` 時由 `init_db()` 建立）。

## TC: 真實模型下對沒有圖的系統說要畫圖，大腦建立草稿並產圖後轉為正式

- plan: 261116 大腦建立架構圖：真實模型路徑（手動）
- priority: P1

### 目的

驗證本 intent 的主路徑在真實模型下走得通：作業對象是一個還沒有任何圖的系統時，說「幫我畫一張……架構圖」，大腦在該系統下新建一張草稿、交給架構設計產圖，產圖存回後該圖轉為正式並出現在專案頁，而不是回「這個系統下沒有掛上的架構圖」。

### 背景

修改前，系統下沒有圖時大腦只會回「這個系統下沒有掛上的架構圖」，使用者必須先到工作區建空白圖。本 intent 讓大腦自己建圖（FR1.1、FR1.2、FR1.5）。

**既有自動化層為何沒抓到**：`test_brain_diagram_creation_flow.py` 以替身路由指定「模型回了 p=0.9」，工作編排也是替身，驗的是「模型回了 X 之後系統怎麼做」；`diagram-drafts.spec.ts` 攔截整條 WebSocket。兩層都**不經過真實模型與真實產圖**，所以「真實模型對這句話是否給出高的『要新的一張』機率」以及「真實產圖存回後狀態真的轉正式」沒有任何 CI 斷言。

### 受測介面

- UI: `/` — 大腦入口頁：對話輸入框、脈絡列（作業對象）、工作項卡片
- UI: `/projects/:projectId` — 專案頁：系統的架構圖清單（草稿標示）、已掛圖計數、最近變更
- API: `POST /api/collab/diagrams` → 200 — 大腦以使用者 token 建草稿（`as_draft=true`）
- API: `PUT /api/collab/diagrams/{diagram_id}` → 200 — 產圖存回（`finalize=true`）
- API: `GET /api/hierarchy/diagram-changes` → 200 — 最近變更
- 外部相依: LLM 供應商（`claude` CLI 或 OpenRouter）

### 前置條件

1. 本機 stack 與模型依檔頭「共用環境」備妥，以 `admin`／`admin123` 登入。
2. 在 `/projects` 建立專案「電商」，在其下建立系統「電商前台系統」。**不要**掛任何架構圖到該系統。
3. 回到 `/`，脈絡列選定 專案「電商」／系統「電商前台系統」。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 在入口頁輸入「幫我畫一張電商網站的 AWS 架構圖」並送出 | 出現一張以「已交給架構設計處理」開頭的工作項卡片；**不得**出現「這個系統下沒有掛上的架構圖」；**不得**出現反問 |
| 2 | 觀察脈絡列 | 作業對象多出第三層架構圖，名稱為「電商網站的 AWS 架構圖」 |
| 3 | 工作項仍在處理中時，另開分頁到 `/projects/<電商的 id>` | 「電商前台系統」的架構圖清單出現該圖並帶「草稿」標示；已掛圖計數**不含**這張 |
| 4 | 等工作項結束 | 卡片狀態為「完成」；**不得**停在處理中超過 300 秒 |
| 5 | 重新整理專案頁 | 該圖的「草稿」標示消失；已掛圖計數為 1 |
| 6 | 檢視專案頁的最近變更 | 有一筆摘要為「經大腦建立「電商網站的 AWS 架構圖」」的變更，另有一筆產圖存檔的變更 |
| 7 | 檢視後端 log | 有一行 `diagram_decision` 且含 `category=create`；該行**不得**含「電商網站」字樣；全程**不得**出現 `Traceback` |

### 通過條件

- 第 1 步交給架構設計且沒有反問、第 3 步標示為草稿且不計入、第 5 步轉為正式，三者全部成立才算通過。
- 第 7 步的 `diagram_decision` 行不含使用者原文，且 `Traceback` 為 0 筆。

### 失敗徵兆與對應肇因

| 徵兆 | 可能肇因 |
|---|---|
| 第 1 步出現「要新建一張架構圖，還是修改目前的圖？」 | 系統下其實已有圖（含他人看不到的草稿）；或路由模型沒回 `wants_new_diagram`，機率退化為不明 |
| 回覆「建立架構圖需要架構編輯權」 | 登入帳號沒有 A1 edit；換有架構編輯權的帳號 |
| 回覆「新圖是否建立成功不確定……」 | 建圖超過 15 秒（`DIAGRAM_CREATE_TIMEOUT_SEC`）；查資料庫是否被鎖 |
| 第 5 步仍是草稿 | 產圖存回沒有帶 `finalize=true`，或產圖失敗（卡片會寫「沒有完成：…」） |

### 追溯

- 實作：`backend/services/brain_gateway.py`、`backend/services/brain_diagram_creation.py`、`backend/services/collab_router.py`、`backend/services/work_orchestrator_capabilities.py`、`frontend/src/components/projects/SystemDiagrams.tsx`
- 自動化對應：`backend/tests/test_brain_diagram_creation_flow.py::CreateFlowTest::test_system_without_diagrams_creates_one_draft_switches_and_dispatches`（替身路由）；`frontend/tests/e2e/diagram-drafts.spec.ts`（攔截層）
- PR／commit：尚未提交（分支 `danniel/feat/brain-create-diagram`）
- User story：FR1.1、FR1.2、FR1.5、FR6.1、FR6.2、FR6.4、FR7.1（本 intent 未執行 user-stories，以 FR 編號追溯）

## TC: 真實模型下已有圖時依句意分辨新建、修改與反問

- plan: 261116 大腦建立架構圖：真實模型路徑（手動）
- priority: P1

### 目的

驗證真實模型對「新的一張」「改一下」「畫一張」三種說法給出的判定，讓系統分別新建、修改目前的圖、或反問；判錯會讓使用者的圖被覆蓋，或多出不要的圖。

### 背景

判定由路由在同一次請求多問一題「是否要一張新的圖」取得機率 p，再依門檻 t（現值 0.7）查表（FR2.1、FR2.2）。判定表本身以 property-based 測試鎖住，但**模型對真實句子給出的 p 是否落在對的區間**，只能以真實模型驗證。

**既有自動化層為何沒抓到**：`test_brain_diagram_creation.py` 的性質測試以任意 p 驗證判定表；`test_brain_diagram_creation_flow.py` 以替身路由指定 p。兩者都不知道真實模型對「幫我改一下這張圖，加上 CDN」會回多少。`NFR1` 的 10 句新標註集只能在部署後量測（build-and-test 記為 Unverified）。

### 受測介面

- UI: `/` — 大腦入口頁：對話輸入框、脈絡列、工作項卡片、反問候選按鈕
- UI: `/projects/:projectId` — 專案頁：系統的架構圖清單
- API: `POST /api/collab/diagrams` → 200 — 只有判定為新建時才應被呼叫
- 外部相依: LLM 供應商（`claude` CLI 或 OpenRouter）

### 前置條件

1. 先完成上一案「真實模型下對沒有圖的系統說要畫圖……」，使「電商前台系統」下有一張**正式**的圖。
2. 脈絡列選定 專案「電商」／系統「電商前台系統」／該張圖。
3. 記下專案頁上「電商前台系統」的架構圖張數（應為 1）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 輸入「幫我把這張圖加上 CloudFront CDN」並送出 | 卡片以「已交給架構設計處理」開頭；脈絡列的架構圖層**仍是同一張**（名稱不變） |
| 2 | 等工作項結束後重新整理專案頁 | 該系統的架構圖仍為 1 張；**不得**多出新圖 |
| 3 | 輸入「幫我畫一張新的災難備援架構圖」並送出 | 卡片以「已交給架構設計處理」開頭；脈絡列的架構圖層切到一張名為「災難備援 架構圖」的新圖 |
| 4 | 重新整理專案頁 | 該系統的架構圖為 2 張（新圖在產圖完成前帶「草稿」標示） |
| 5 | 脈絡列改選回第一張圖，輸入「幫我畫一張架構圖」並送出 | 出現反問「要新建一張架構圖，還是修改目前的圖？」與「新建一張架構圖」「修改目前的圖」兩個按鈕及「都不要」；**不得**直接建立新圖 |
| 6 | 點「修改目前的圖」 | 卡片以「已交給架構設計處理」開頭；專案頁該系統的圖仍為 2 張 |

### 通過條件

- 第 2 步張數維持 1、第 4 步張數為 2、第 6 步張數仍為 2，三者全部成立才算通過。
- 第 5 步出現反問而非直接新建。

### 失敗徵兆與對應肇因

| 徵兆 | 可能肇因 |
|---|---|
| 第 1 步多出一張新圖 | 模型對修改句給出 p ≥ 0.7；記錄句子與 log 中的 `diagram_decision`，交 `NFR1` 標註集處理 |
| 第 3 步改到了第一張圖 | 模型對「另一張新的」給出 p < 0.3 |
| 第 5 步直接新建 | 模型對無指示詞的句子給出 p ≥ 0.7；或反問因 `new_or_modify` 未進 WS 契約而被丟棄（查瀏覽器 console） |

### 追溯

- 實作：`backend/services/brain_diagram_creation.py`（`decide`）、`backend/services/intent_routing_decisions.py`、`backend/services/brain_gateway.py`、`frontend/src/components/brain/ClarifyCandidates.tsx`
- 自動化對應：`backend/tests/test_brain_diagram_creation.py::DecidePropertiesTest::test_monotonic_in_p`（判定表）；`backend/tests/test_brain_diagram_creation_flow.py::ClarifyFlowTest::test_new_or_modify_when_unclear_and_create_choice_creates`（替身路由）
- PR／commit：尚未提交（分支 `danniel/feat/brain-create-diagram`）
- User story：FR2.1、FR2.2、FR2.4、FR3.4（本 intent 未執行 user-stories，以 FR 編號追溯）

## TC: 既有資料庫升級後 backend 自行補上草稿狀態欄位且既有圖皆為正式

- plan: 261116 大腦建立架構圖：部署與升級（手動）
- priority: P1

### 目的

驗證在**已有架構圖的真實 PostgreSQL** 上換成新版 backend，啟動時會自行補上 `user_diagrams.status`、既有圖全部視為正式、各讀圖頁面不出現 500；這是本 intent 唯一一個不經人工遷移指令的 schema 變更。

### 背景

`models.UserDiagram.status` 被 ORM 映射後，所有讀圖查詢都會選取它；舊 volume 若沒有這一欄，工作區、專案頁、評核的讀圖端點會全數 500，而部署後探針只打登入、抓不到（code-generation 審查 Major，使用者裁決改為啟動時自動補欄）。補欄失敗會讓 backend 啟動失敗，日誌關鍵字 `diagram status schema 補丁失敗`。

**既有自動化層為何沒抓到**：`test_diagram_drafts_schema.py` 在 SQLite 上驗證；build-and-test 在本機一次性 PostgreSQL 17 上只執行了欄位相關的 SQL 敘述（無 pgvector、無 psycopg2，未經 SQLAlchemy、未跑完整 `schema_rbac.sql`）。**真實的「舊 volume ＋ 新 backend 啟動」組合**沒有任何自動化層碰得到。

### 受測介面

- UI: `/workspace` — 工作區：歷史架構圖清單
- UI: `/projects/:projectId` — 專案頁：系統的架構圖清單
- API: `GET /api/collab/diagrams` → 200 — 每一列帶 `diagram_status`
- API: `GET /api/collab/diagrams/{diagram_id}` → 200 — 明細帶 `diagram_status`

### 前置條件

1. 本機 PostgreSQL 有一個以**合併前**的 `ut`（或目前 staging 版）建立、且已有至少兩張架構圖的資料庫；以 `psql "$DATABASE_URL" -c "SELECT count(*) FROM user_diagrams"` 確認張數 ≥ 2。
2. 確認欄位尚不存在：`psql "$DATABASE_URL" -c "\d user_diagrams"` 的輸出**沒有** `status`。
3. 切到本分支，**不要**手動執行 `schema_rbac.sql` 或 `run_hierarchy_migration.py`。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 啟動後端 `cd backend && uvicorn main:app --port 8010` | 啟動 log 出現 `diagram status schema 補丁完成：已補 user_diagrams.status（既有圖為 ready）`；**不得**出現 `diagram status schema 補丁失敗`；uvicorn 進入 `Application startup complete` |
| 2 | `psql "$DATABASE_URL" -c "SELECT status, count(*) FROM user_diagrams GROUP BY status"` | 只有一列 `ready`，計數等於前置條件 1 的張數 |
| 3 | `psql "$DATABASE_URL" -c "SELECT conname FROM pg_constraint WHERE conname='ck_user_diagrams_status'"` | 回一列 `ck_user_diagrams_status` |
| 4 | 再重啟後端一次 | 啟動 log 改為 `diagram status schema 檢查完成（欄位已存在）`；第 2 步的查詢結果不變 |
| 5 | 以 `admin` 登入，開 `/workspace` 的歷史架構圖清單 | 列出全部既有圖，**沒有**任何一張帶「（草稿）」；瀏覽器 Network 中 `GET /api/collab/diagrams` 為 200 |
| 6 | 開任一已掛圖系統所屬的 `/projects/<id>` | 系統的架構圖清單正常顯示，**沒有**「草稿」標示 |

### 通過條件

- 第 1 步啟動成功且無補丁失敗訊息、第 2 步全為 `ready` 且張數一致、第 5 步回 200，三者全部成立才算通過。

### 失敗徵兆與對應肇因

| 徵兆 | 可能肇因 |
|---|---|
| 啟動失敗且 log 有 `diagram status schema 補丁失敗` | 連線帳號沒有 `ALTER TABLE user_diagrams` 權限，或表被長交易鎖住；依 `DEPLOY.md` 回復段處理 |
| 啟動成功但 `/api/collab/diagrams` 回 500 且 log 有 `column user_diagrams.status does not exist` | `init_db()` 沒有呼叫 `_ensure_diagram_status_schema()`，或被包進吞例外的區塊 |
| 第 2 步出現 `draft` | 補欄時預設值不是 `'ready'`（`hierarchy_migration._ensure_diagram_status_column` 與 `schema_rbac.sql` 不一致） |

### 追溯

- 實作：`backend/database.py`（`_ensure_diagram_status_schema`）、`backend/services/hierarchy_migration.py`（`_ensure_diagram_status_column`）、`schema_rbac.sql`、`DEPLOY.md`
- 自動化對應：`backend/tests/test_diagram_drafts_schema.py::TestDiagramStatusStartupPatch::test_startup_patch_marks_existing_diagrams_ready`（SQLite）
- PR／commit：尚未提交（分支 `danniel/feat/brain-create-diagram`）
- User story：FR6.5（本 intent 未執行 user-stories，以 FR 編號追溯）
