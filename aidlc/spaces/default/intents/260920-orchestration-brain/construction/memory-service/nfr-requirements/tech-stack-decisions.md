# 技術選擇 — `U8 memory-service`

> **本單元零新依賴、零新服務、零新容器。** 它用的每一樣東西都已在 repo 內
> 且已在部署環境運行。本檔的價值不在「選了什麼」，而在**逐項證明沒有新東西**
> ——`NFR8` 的部署設定完整性因此自然成立。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `codekb/chiton/technology-stack.md` | brownfield 技術棧盤點（本檔的對照基準） |
| `inception/contract-design/contract-summary.md` | `K-08`（facade ＋ http）、`K-06`（EmbeddingPort）、`K-05`（schema） |
| `functional-design/`（本單元） | 三層形狀與五個 facade 方法 |
| `team.md` `## Code Style` | 後端分層規則、logger 命名、`HTTPException` 風格、單一真實來源 |
| `requirements.md` `NFR8` | 新增元件的部署設定完整性 |

## 一、選擇表（全部沿用，無新增）

| 面向 | 選擇 | 是否新增 | 理由 |
|---|---|---|---|
| 語言／執行期 | Python 3.12 | **沿用** | 既有 backend |
| Web 框架 | FastAPI（`fastapi[standard]==0.141.1`，已釘選） | **沿用** | 既有；本單元新增的是 router 而非框架 |
| ORM／資料存取 | SQLAlchemy（既有 `database.py` 的 engine） | **沿用** | `U5` 的表已由 `models.py` 鏡像 |
| 資料庫 | PostgreSQL ＋ pgvector（`pgvector/pgvector:pg18`） | **沿用** | `U5` 已交付並已在兩份 compose 與兩個 CI job 使用 |
| 向量產生 | `U6 EmbeddingPort`（四實作） | **沿用** | `U6` 已交付；本單元是它的消費端 |
| 測試框架 | 內建 `unittest` ＋ `hypothesis` ＋ `starlette.testclient` | **沿用** | `team.md` 記載的既成事實（**未使用 pytest**） |
| 真實 PostgreSQL 測試 | 既有 `memory-schema` 與 `concurrency` 兩個 CI job | **沿用** | `U5`／`U19` 已交付；本單元加步驟不加 job |
| 向量索引 | **HNSW**（`[N2]`=B） | **新增一個索引** | 見 §二——這是本單元唯一的結構變更 |

### 1.1 `NFR8` 在本單元的判準

| id | 需求 | 二元判準 | 來源 |
|---|---|---|---|
| **`NFR8.20`** | 本單元**零新部署設定、零新依賴** | ① `backend/requirements.txt` 的 diff 為空；② 本單元 diff 不含 `deploy/`、`deploy/render-env.sh`、任一 `.env.example`、`deploy/docker-compose.*.yml`；③ `python3 scripts/validate_env_contract.py` 綠燈；④ `gh api repos/<owner>/<repo>/actions/secrets` 的名稱集合不變 | `NFR8` |

**`NFR8` 在本單元自然成立**（不需額外努力）：本單元不引入容器、不引入服務、
不引入環境變數。這與 `U5` 引入 Ollama（第 6 個服務，連帶 `.env.example` 與
`render-env.sh` 三處同步）形成對照——**那一次才是 `NFR8` 真正被考驗的時候**。

**但 `[N2]`=B 的 HNSW 索引不在 `NFR8` 的範圍內**：它是**結構**變更
（`schema_rbac.sql` ＋ `DEPLOY.md`），不是**部署設定**變更
（`deploy/` ＋ `.env`）。兩者的 blocking 規則不同、判準不同，刻意分開記載。

## 二、唯一的結構變更：HNSW 索引（`[N2]`=B）

| 項目 | 內容 |
|---|---|
| 為什麼需要 | `memory_records` 目前**沒有任何向量索引**（實測 `ivfflat`／`hnsw` 命中 0），相似度檢索為逐列計算距離 |
| 為什麼是 HNSW 而非 ivfflat | ivfflat 的 `lists` 參數依列數決定，而該表**目前是空表**；空表上建的 ivfflat 品質差且需重建。HNSW 可在空表上建立 |
| 落點 | `schema_rbac.sql` 的 `I)` 區塊（`U5` 擁有的區塊） |
| 連帶 blocking 義務 | 四項，逐項列於 `performance-requirements.md §三之二`：`schema_rbac.sql`、`DEPLOY.md`、`run_meta_schema_migration.py` 的 `EXPECTED_INDEXES`、`verify_memory_schema.sql` 的新 `S` 斷言 |
| 未評估的成本 | HNSW 的建索引記憶體與 staging 的 RAM 餘裕（`N8-5`）。`U5` 引入 Ollama（第 6 個服務）後已動用過一次餘裕，而本站沒有該主機的可用記憶體數字 |

**本站不執行那四項**（屬 `code-generation`），但它們是 `[N2]`=B 的**完整代價**，
不是附帶細節——少做任何一項的後果各不相同：

| 漏做 | 後果 |
|---|---|
| `schema_rbac.sql` | 索引根本不存在；`NFR3.22` 的 `EXPLAIN` 斷言紅燈 |
| `DEPLOY.md` | 違反 `project.md ## Mandated` 的 blocking 規則 → repo contract 風險 |
| `EXPECTED_INDEXES` | 索引**會被建立**（腳本解析 `I)` 區塊）但**不會被驗證**，於是該腳本「結束碼 0」的語意悄悄變窄 |
| `verify_memory_schema.sql` | `memory-schema` job 不檢查它；索引被誤刪或 opclass 改錯時無人察覺 |

## 三、三層形狀（`team.md` 的規則落實）

`team.md` 逐字要求「**新模組／新業務邏輯**一律走三層形狀，純運算下沉到不讀 DB
的函式」，且「不得在 `user_router.py`／`collab_router.py` 之外新建
『router 直寫商業邏輯』的模組」。

| 層 | 模組（建議命名，`code-generation` 可調整但形狀不可變） | 可以碰 DB | 可以拋 `HTTPException` |
|---|---|---|---|
| HTTP | `memory_router.py` | 否 | **是**（唯一可以的一層） |
| Facade（授權的唯一入口，`K-08` 的 `sole_entry`） | `memory_facade.py` | 否（經 service） | 否——拋 `MemoryForbidden`／`MemoryNotFound` |
| Service（業務協調） | `memory_service.py` | **是** | 否 |
| 純函式（排序次級鍵，`NFR3.24`） | `memory_ranking.py` | **否** | **否** |

**`MemoryFacade` 是 `K-08` 宣告的 `sole_entry`**，故授權判定只能在這一層，
不得在 router 或 service 重複一份（`team.md` 的單一真實來源）。

**純函式層是 `NFR3.24` 與其 PBT 落點的結構前提**（`N8-7`）：
它若讀 DB 或拋 `HTTPException`，property-based 測試就寫不下去。
可執行檢查：該模組內 `import` 不含任何 DB session 型別、不含 `HTTPException`。

## 四、命名與風格（`team.md` 的既成事實）

| 項目 | 規則 |
|---|---|
| 檔名 | `snake_case.py`；router 一律 `*_router.py` |
| logger | `logging.getLogger("cloud360.<module>")`——**不用 `__name__`**（`NFR7.33`） |
| `HTTPException` 風格 | 沿用所在函式鄰近寫法（`team.md` 記載 `user_router.py` 同檔混用具名與位置引數，刻意不統一） |
| 前端 API 呼叫 | 沿用 `src/config/api.ts` 的 `apiUrl()` ＋ 手寫 `Authorization` 標頭 ＋ `res.ok` 判斷（`U15` 的範圍，本單元只提供端點） |
| 錯誤處理 | DB／驗證錯誤直接 `raise HTTPException`，不 `try/except` 吞掉；`try/except` 只用在外部依賴邊界（本單元的外部邊界是 `U6` 的 embedding 呼叫） |

## 五、不選用的東西（逐項附理由，避免被讀成遺漏）

| 候選 | 不選用的理由 |
|---|---|
| 快取層（Redis／行程內） | 記憶讀取按呼叫者過濾（`BR2.2`），快取鍵必須含 principal，容易做成跨使用者洩漏。見 `scalability-requirements.md §三` |
| 獨立的記憶服務進程 | 本 intent 的部署模型是單主機 compose（ADR-0007）；新進程會新增容器與部署設定，直接打破 `NFR8` |
| ivfflat 向量索引 | 空表上無法有意義地建立（§二） |
| 前端 unit／component 測試框架 | `team.md` 的 `Q4` 定案 D 不採；前端驗證層是既有 Playwright e2e（屬 `U15`） |
| ORM 層的 `CheckConstraint` 承載封閉集合 | 沿用 `U18` 先例：封閉列舉在應用層，結構層刻意不加（見 `functional-design/entities.md §三`） |
