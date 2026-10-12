# 基礎設施規格 — `U20 requirement-field-service`

## 一、資源清單：零新增

| 項目 | 現況 | 本單元的變化 |
|---|---|---|
| 服務／容器 | `deploy/docker-compose.deploy.yml` 的既有服務 | 無 |
| 監聽埠 | 後端既有埠，經 nginx `location /api/` 代理 | 無（新 router 在 `/api/requirements`） |
| 資料表 | `system_requirement_fields`（`U18`） | `updated_on_behalf_of` 收斂為 `VARCHAR(64)`、去外鍵（`BR47.1`） |
| 環境變數 | — | 無（`NFR8.120`） |
| 加密 | 既有 PostgreSQL volume、Cloudflare Tunnel TLS | 無變化（`security-design.md` 第一節） |

## 二、部署順序（承 nfr-design 審查 `review-01` R-05）

**事實**：`deploy.yml` 只部署容器，**不執行任何遷移腳本**（`run_meta_schema_migration.py`、
`run_hierarchy_migration.py` 在 `.github/workflows/deploy.yml` 與 `deploy/*.sh` 皆零命中）；
`schema_rbac.sql` 只在空 volume 執行。既有環境的表結構演進一律靠人工執行遷移腳本
（`DEPLOY.md` 2.2.9）。

| 情境 | 後果 | 處置 |
|---|---|---|
| `U18` 與 `U20` 同批上線，遷移未跑 | `system_requirement_fields` 不存在 → 本單元三個端點全部 500 | 與 `U18` 既有義務相同：上線後立即執行一次 `run_meta_schema_migration.py`；本單元**不新增**另一支腳本 |
| `U18` 已上線並跑過遷移（舊定義），`U20` 後上線、遷移未重跑 | 欄位仍為 integer ＋ 外鍵 → **只有帶代寫標示的寫入**失敗（字串寫入 integer 欄），使用者自填與讀取正常 | 重跑一次同一支腳本即可收斂（`reliability-design.md` 第三節的條件式 `DO` 區塊） |

**部署前置步驟（寫進 `DEPLOY.md` 2.2.9）**：合併含本單元的變更後，於 staging 執行
`cd backend && python scripts/run_meta_schema_migration.py`；腳本的後條件包含此欄的型別與
「無外鍵」檢查，失敗即非零結束碼。**收斂期間**表會短暫取 `ACCESS EXCLUSIVE` 鎖（只在欄位仍為
舊型別時發生，表內無代寫值，時間可忽略）；`DO` 區塊設 `lock_timeout`，等不到鎖即失敗而非
無限等待（承 nfr-design `review-01` R-06）。

**這一段為什麼要寫在本單元**：deploy-on-merge 之下，「程式已上線、資料表尚未收斂」是一個
真實的中間狀態（`delivery-planning:c6` 的同形約束）；它的失敗面窄（只影響代寫寫入），但
不寫下來，第一個看到 500 的人會以為是程式錯誤。

## 三、回滾

| 回滾什麼 | 做法 |
|---|---|
| 程式 | 既有 `deploy.yml` 的 rollback job（還原 last-good）；舊程式不讀寫此欄的代寫值以外的任何新東西 |
| 資料表收斂 | **不回滾**。舊程式（`U18` 時期）沒有任何寫入此欄的路徑，`VARCHAR` 欄位對它無影響；回滾成 integer 反而需要丟棄已寫入的代寫值 |

## 四、ADR-0006 四面向（基礎設施層）

| 面向 | 判定 |
|---|---|
| IAM | 不在基礎設施層（應用層授權見 `security-design.md`）；遷移以既有 DB 帳號執行，不新增角色或權限 |
| Encryption | 無變化 |
| Network exposure | 無新埠、無新服務 |
| Audit logging | 遷移腳本只印主機與資料庫名，**不印 `DATABASE_URL`**（`run_meta_schema_migration.py:55` 的既有約束，本單元的新檢查沿用同一輸出方式） |
