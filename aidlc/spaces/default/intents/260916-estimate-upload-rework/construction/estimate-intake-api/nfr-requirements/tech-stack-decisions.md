# Tech Stack Decisions — estimate-intake-api

> Unit: `estimate-intake-api`（U2）· kind: **service** · Q1–Q6=A（NFR）＋ FD Q1–Q6=A。

| 面向 | 決策 | 理由 |
|---|---|---|
| 語言／執行期 | **既有 Python 3**＋FastAPI | brownfield |
| HTTP 模組 | **`backend/cost/estimate_intake_router.py`**、`estimate_intake_service.py`、access／audit 模組 | FD Q1=A；NFR6 三層 |
| 掛載 | **`/api/cost/v1`** via `main.py` | contract C2 |
| 背景任務 | **FastAPI `BackgroundTasks`（或等價 in-process）** | NFR Q6=A；無 Redis |
| ORM／DDL | **SQLAlchemy**＋`database.py` 啟動補丁＋`schema_rbac.sql` 雙軌 | 與既有一致；**不**引入 Alembic |
| 解析 | 呼叫既有 U1 `parse`／`validate` | C1 |
| multipart | FastAPI／Starlette 既有上傳支援 | 無新套件 |
| 測試 | `unittest`＋`TestClient`；allow／deny | team 測試底線 A／B |
| Advice 表 | 本 unit 可建**空殼**（含 `status` 等）；正文由 U7 填 | NFR Q6=A、FD Q5=A |
| 新基礎設施 | **無**（無佇列、無物件儲存、無 Playwright） | NFR8 |

## 依賴變更

| 套件 | 動作 |
|---|---|
| 既有 `fastapi`／`sqlalchemy`／`openpyxl`（U1）等 | **不強制新增**；若缺 multipart 測試依賴沿用 `httpx` |
| Redis／Celery／Alembic／OTel | **不新增** |

## 不做

- 不實作 SPA／SSE
- 不重建舊 `cost_router` diagrams 行為
- 不把手寫 TCMS 塞進本 stage

<!-- confirmed: Looks correct -->
