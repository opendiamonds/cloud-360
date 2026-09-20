# Tech Stack Decisions — legacy-cost-retirement

> Unit: `legacy-cost-retirement`（U3）· kind: **service**（退場）· Q1–Q6=A。

| 面向 | 決策 | 理由 |
|---|---|---|
| 語言／執行期 | **既有 Python 3**（backend）＋既有前端工具鏈 | brownfield；無新 runtime |
| Schema 遷移 | **雙軌**：`database.py::_ensure_cost_schema`＋`schema_rbac.sql`；`ALTER TABLE … RENAME TO archive_*` | Q2=A；不引入 Alembic |
| HTTP | 移除 FastAPI `cost_router` 舊掛載；無新框架 | FD Q2=A |
| 瀏覽器自動化 | **移除** Python `playwright` 相依與 Calculator 模組 | FD Q4=A；前端 `@playwright/test` 保留 |
| ORM／模型 | 移除對四張 live 成本表的應用映射；**不**新增 archive ORM | Q1=A |
| 環境設定 | 刪舊 stub／calculator 變數；保留 U4 目錄價憑證變數 | Q4=A；env contract 須綠 |
| 測試 | `unittest`＋既有 contract／e2e 刪改；無新測試框架 | Q6=A |
| 同批部署驗證 | 程序檢查清單；無新 CI 套件 | Q3=A |

## 依賴變更（code-gen 必做）

| 套件／檔 | 動作 |
|---|---|
| Python `playwright` | **自 `requirements.txt` 移除** |
| Calculator／spike 模組 | **刪除** |
| `pricing_sdk`／`pricing_client` 等 | **保留**（U5） |
| Alembic | **不引入** |

## 不做

- 不引入新 migration 框架
- 不新增 archive 查詢 API
- 不在本 unit 自動 DROP archive 表

<!-- confirmed: Looks correct -->
