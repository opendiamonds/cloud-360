# 技術選型 — `U20 requirement-field-service`

## 〇、零新套件

全部沿用既有技術棧（`codekb/chiton/technology-stack.md`、`team.md`）：

| 層 | 選擇 | 依據 |
|---|---|---|
| HTTP | FastAPI router，prefix `/api/requirements`，掛在既有 `main.py` | 同 `membership_router`／`hierarchy_router` 的掛法 |
| 資料存取 | SQLAlchemy ORM ＋ 新的 `SystemRequirementField` 模型（`BR47.4`） | `backend/models.py` 目前只有 `ProjectMember`／`ReselectionEvent`，無本表模型 |
| 資料庫 | PostgreSQL（`U18` 已交付的表） | — |
| 回應模型 | Pydantic，三個路由皆顯式宣告 `responses={403,404,422}` | `BR46.1`；`U19` 查證過 `openapi.json` 原本非 2xx/422 的宣告數為 0 |
| 型別產物 | 重新產生 `openapi.json` 與 `frontend/src/types/api.d.ts` | CI 的 OpenAPI 漂移閘門 |
| 測試 | `unittest` ＋ `TestClient`（**非 pytest**）；不使用 `hypothesis` | PBT 不適用（`security-requirements.md` 第六節） |

## 一、upsert 的實作：依連線方言

| id | 決定 | 理由 |
|---|---|---|
| **`NFR20.31`** | `BR43.5` 的單一 upsert 以資料庫方言的 `insert … on conflict do update` 實作，依連線方言選擇 PostgreSQL 或 SQLite 的建構式；**不得**退回先查後寫，也不得以捕捉 `IntegrityError` 後重試代替 | 測試走 in-memory SQLite（`backend/tests/helpers.py`），正式為 PostgreSQL；兩者皆支援 `ON CONFLICT … DO UPDATE` 但由不同的方言建構式產生。先查後寫會在併發首寫時回 500（`NFR20.17`） |

**一個會讓測試無聲失效的陷阱，先寫下來**：SQLite 的 `ON CONFLICT` 需要衝突目標有唯一
約束或唯一索引。若測試的建表路徑是 ORM 的 `metadata.create_all` 而模型漏宣告三欄唯一鍵，
SQLite 會在執行期拋「ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE
constraint」——這會被誤讀成方言問題。故 `BR47.4` 的 ORM／DDL 一致性測試必須涵蓋唯一鍵。

## 二、計數器測試形狀

| id | 決定 | 理由 |
|---|---|---|
| **`NFR20.32`** | 查詢次數以 SQLAlchemy 的 `before_cursor_execute` 事件計數，依目標表名過濾 | `NFR20.1`／`NFR20.2`／`NFR20.4` 的二元判準需要它；不需新套件 |

## 三、不採用的選項（逐項附理由）

| 不採用 | 理由 |
|---|---|
| 樂觀並行控制（版本欄或 `If-Match`） | 需要 `U18` 再加一欄並觸發一次 blocking 同步；`OPEN-RF20-2` 已揭露最後寫入者勝的後果，`U23` 以儲存後重讀緩解 |
| 跨請求快取（Redis 或 in-process） | 見 `performance-requirements.md` 第三節 |
| 獨立稽核表 | 見 `observability-requirements.md` 第〇節 |
| 依欄位做型別驗證（數字、區域代碼） | `functional-spec.md` 的 Assumptions：`K-17` 的 `value: str` 與上游皆無型別要求 |
