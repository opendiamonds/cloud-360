# Infrastructure Specification — `U23 project-pages-ui`

> 撰寫時間 2026-10-15T23:44:13Z（`date -u` 取值）。本站是**設計**站：描述需要什麼基礎設施與為什麼，不寫 IaC。
>
> 結論：**零新服務、零新埠、零新環境變數、零新 secret；唯一的資料層變化是一個索引**
> （`ix_project_members_user_id`，使用者裁決沿用 `U18` 的遷移路徑）。下面每一條都附可複驗的指令或行號——
> 「什麼都不用改」若沒有證據支撐，與「沒查」在文件上長得一樣。本站未執行任何程式、測試或遷移；
> 行號皆於撰寫當下以 `grep -n`／`sed -n` 實讀。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-design/logical-components.md` | §一 改動清單；§三 索引與遷移的九項落點（本檔不重抄，只補「如何到達各環境」與回滾） |
| `../nfr-design/security-design.md` | §五之三 `[PPD1]`=A 的刪除者 log；§七 ADR-0006 四面向；§八 殘留 |
| `../nfr-design/performance-design.md` | §二之一 `UNION` 形狀使索引可被選用；§三 連線池與上限 4 的定位 |
| `../nfr-design/nfr-design-questions.md` | `[PPD1]`=A |
| `../functional-design/functional-spec.md` | §三 路由（`/projects`、`/projects/new`、`/projects/:projectId`）；§八之一 同步義務 |
| `../carried-review-items.md` | nfr-requirements `R-02` 使用者裁決：索引寫進 `schema_rbac.sql` ＋ 遷移腳本（含 `EXPECTED_INDEXES`）＋ `DEPLOY.md` 部署後重跑步驟，**不動啟動路徑** |
| `inception/domain-design/components.md`、`inception/contract-design/contract-summary.md` | `K-19`（`U23` → `U17` 的測試標的契約）、`K-16`／`K-17` 的消費面 |
| `inception/delivery-planning/bolt-plan.md` | `U23` 在 `B13`（`:659` 起，Bolt 內順序 `U20` → `U23` → `U21`）；`U18`／`U19` 在 `B11`（`:572`） |

## 一、部署架構：逐項判定（附證據）

| Facet | Choice | Rationale |
|---|---|---|
| 運算模型 | **不變**：既有 docker compose，7 個服務 | `deploy/docker-compose.deploy.yml` 的服務鍵 `db`(:35)、`backend`(:79)、`redis`(:184)、`ollama`(:312)、`frontend`(:353)、`cloudflared`(:375)、`mcp-bridge`(:400)——本單元不新增、不移除。後端改動落在既有 `backend` 容器；前端三頁是既有 `frontend`（nginx）容器提供的靜態資產 |
| 網路（反向代理） | **不變** | `frontend/nginx.conf:16-17` 為 `location /api/ { proxy_pass http://backend:8000;`——涵蓋 `/api/hierarchy/*`、`/api/membership/*`、`/api/requirements/*` 全部消費點；`:35-37` 的 `location / { try_files $uri $uri/ /index.html; }` 使新路由 `/projects`、`/projects/new`、`/projects/:projectId` 的深連結與重新整理回到 SPA，不需新 `location` |
| 埠 | **零新增** | 本單元不新增 compose `ports:`；`FRONTEND_HOST_PORT` 不變。`mcp` 網路（compose :472）與 `mcp-bridge` 不受影響 |
| 儲存策略 | **一個新索引，零新表、零新欄位** | `project_members (user_id)` 的 B-tree 索引；上線方式見 §二之一 |
| 瀏覽器儲存 | **零** | `PPN-17`：新增前端檔對 `localStorage`／`sessionStorage`／`indexedDB` 的 grep 為 0；扇出佇列不落地 |
| 環境變數 | **零新增**（`NFR8.100`） | `deploy/.env.example` 現有 29 個鍵、`backend/.env.example` 23 個、`frontend/.env.example` 1 個（`grep -cE "^[A-Z_]+="`），本單元一個都不加；故 `deploy/render-env.sh` ＋ `deploy/.env.example` 的同步義務為**空集合**，`python3 scripts/validate_env_contract.py` 無新標的 |
| Secret | **零新增** | 不新增憑證、API key 或 GitHub Actions secret；`project.md` 的「secret 須落在 secrets 而非 variables」查證義務不觸發 |
| 環境 | 三個（本機 dev／CI 測試／staging 部署），不變 | 三個環境如何拿到索引不同，見 §二之一 |
| IaC 方式 | 不變：`schema_rbac.sql`（可攜 DDL 正本）＋ `run_meta_schema_migration.py`（既有環境）＋ ORM `__table_args__`（`create_all`） | 雲端 IaC 不在範圍（ADR-0001／ADR-0002） |
| 資源規模 | **不變** | 單一 uvicorn 進程（`backend/Dockerfile:30` 無 `--workers`）、SQLAlchemy 預設連線池（`backend/database.py:37`，常駐 5 ＋ 溢出 10）。上限 4 的扇出對池的影響已在 `performance-design.md` §三 記為已知代價；改池設定屬部署層決定，本單元不動 |

## 二、基礎設施服務

| Service | Role | Configuration | Notes |
|---|---|---|---|
| PostgreSQL（`db`） | database | 新增 `ix_project_members_user_id`（`project_members(user_id)`，非唯一 B-tree，`IF NOT EXISTS`） | 供 `performance-design.md` §二之一 的 `UNION` 成員那一半以 `user_id` 驅動；`uq_project_members_project_user` 不變 |
| FastAPI（`backend`） | application | 程式改動（兩支列舉端點委派、三支寫入加守門、兩個訊息常數、`[PPD1]` log）；**零設定改動** | 不改 `database.py`（使用者裁決，`NFR8.4`「不動啟動路徑」） |
| nginx（`frontend`） | static ＋ reverse proxy | 新增前端資產（三頁 ＋ `fanoutQueue.ts`）；`nginx.conf` 不改 | 見 §一 網路列 |
| Redis／Ollama／mcp-bridge／cloudflared | — | 不碰 | MCP allowlist 只含三條 `/api/requirements/*`（`backend/mcp_bridge/allowlist.json:7`／`:25`／`:36`），不含任何 hierarchy 路徑 |

### 二之一、索引如何到達三種資料庫狀態

| 資料庫狀態 | 誰建出索引 | 證據 | 需要人工嗎 |
|---|---|---|---|
| (a) **全新資料庫**（空 volume） | PostgreSQL initdb 執行 `schema_rbac.sql` 的 `J)` 區塊 `CREATE INDEX IF NOT EXISTS` | 部署 compose `:55`、測試 compose `:57` 皆把 `../schema_rbac.sql` 掛到 `/docker-entrypoint-initdb.d/01-schema_rbac.sql` | 否。`ui-regression` 每個 PR 起的短生命週期 stack 屬此類 |
| (b) **既有資料庫、`project_members` 表尚不存在** | 後端啟動時 `Base.metadata.create_all()`（`backend/database.py:90`）依 ORM 建表，**連同** `__table_args__` 的 `Index` 一併建立 | `create_all` 對它新建的表會發出該表的 `CREATE INDEX`；`logical-components.md` §三 #3 的 ORM 改動是這條路的前提 | 否（但 `DEPLOY.md` 2.2.9 本來就要求對新表跑一次遷移腳本補 COMMENT，見下） |
| (c) **既有資料庫、表已存在但無此索引** | **只有**重跑 `backend/scripts/run_meta_schema_migration.py`（它解析並執行 `schema_rbac.sql` 的 `X`／`I`／`J` 區塊，`:95` `BLOCKS_TO_RUN = ("X", "I", "J")`） | `create_all` 對既有表不補索引；`deploy.yml` 不呼叫任何遷移腳本（`grep -n "run_meta_schema_migration\|migrat" .github/workflows/deploy.yml` 為 0 命中；`DEPLOY.md:691` 逐字「`deploy.yml` 不呼叫任何遷移腳本」） | **是**——部署後人工步驟，見 `cicd-pipeline.md` §二 |

**staging 落在哪一類，取決於合併順序**：`git show origin/ut:schema_rbac.sql | grep -c project_members` 為 **0**——
`ut` 上目前沒有 `project_members`。若 `B11`（`U18`／`U19`）與 `B13`（含本單元）**分批**進 `ut`，staging 在 `B11` 上線時
已建好無索引的表，`B13` 上線屬 (c)；若**同批**進 `ut`，屬 (b)，而 `DEPLOY.md` 2.2.9 對 `U18` 新表要求的那次遷移腳本
執行同時涵蓋本索引（`IF NOT EXISTS` 為 no-op 或補建）。兩種情形下**人工步驟相同**：部署後跑一次遷移腳本並驗證，
故 `DEPLOY.md` 的新段落不需要分情形寫。

**本機 dev**：在本分支上跑過 `B11` 的開發者，其本機資料庫屬 (c)。缺索引時功能正常、只是清單查詢不走索引；
處置是照 `DEPLOY.md` 2.2.9 跑一次遷移腳本。這不觸發 `LOCAL-DEV.md` 的同步義務（見 §三），本站只記載、不新增義務。

**建索引的鎖與可重跑性**：

| 面向 | 內容 |
|---|---|
| 鎖 | 一般的 `CREATE INDEX` 持有 `SHARE` 鎖，建立期間擋寫入、不擋讀取。`project_members` 的列數等於成員資格數（`B11` 上線前為 0），預期為毫秒級；**未實測**（無 staging 列數） |
| 為什麼不用 `CONCURRENTLY` | `CREATE INDEX CONCURRENTLY` 不能在交易內執行，而遷移腳本把全部 DDL 包在**一個交易**內並在 COMMIT 前驗後條件（`DEPLOY.md` 2.2.9）；改用它等於另開一條遷移路徑，違反使用者「沿用 `U18` 路徑」的裁決。以表的規模，收益為零 |
| 可重跑 | `IF NOT EXISTS`。CI 的 `memory-schema` job 對真實 PostgreSQL **連套兩次** `schema_rbac.sql`（`ci.yml:359-374`，第二次即可重跑性驗證），並在 U20 步驟 B 執行遷移腳本（`ci.yml:435-447`），其後條件逐筆查 `EXPECTED_INDEXES`（`run_meta_schema_migration.py:409-417`） |

### 二之二、回滾路徑

| 回滾對象 | 做法 | 影響 |
|---|---|---|
| **程式**（最常見） | `deploy.yml` 的 `rollback` job 還原 last-good（`:596` 起、`:618`）＋ 開 revert PR；或手動 `git revert` | **不需動索引**：舊版 ORM 不宣告它，`create_all` 不會刪索引；舊版遷移腳本的 `EXPECTED_INDEXES` 只查「應存在者是否存在」（`:409-417` 為逐筆 `count(*)`，不檢查多餘索引），多一個索引不會讓舊腳本失敗。**安全面的代價**：程式回滾會讓三條寫入路徑的守門一併消失，被移出的建立者重新取得 API 層的建立系統／刪除專案／刪除系統能力（`OPEN-PP23-10` 的缺口重開）。回滾決策時須知情 |
| **索引**（只在索引本身有問題時） | `DROP INDEX IF EXISTS ix_project_members_user_id;` | 安全：無約束或外鍵依賴它，`uq_project_members_project_user` 獨立存在；後果只有專案清單的成員半邊不走索引。之後重跑遷移腳本會以 `IF NOT EXISTS` 重建 |
| 資料 | 無資料遷移、無回填 | 本單元不寫任何既有列 |

## 三、`project.md` 三條 blocking／同步規則的逐項判定

| 規則 | 觸發條件 | 本單元判定 |
|---|---|---|
| **schema ↔ deploy 同步**（`schema_rbac.sql` ＋ `DEPLOY.md`） | 索引變更 | **觸發**。九項落點見 `logical-components.md` §三 #1–#9（不在此重抄）；本站補的是 §二之一 的三種到達路徑與 §二之二 的回滾 |
| **`LOCAL-DEV.md` 同步** | 異動 `backend/database.py` 的 schema 補丁、nginx 設定、任一 `.env.example` 或 `render-env.sh` | **不觸發**：四者本單元皆不碰（使用者裁決「不動啟動路徑」） |
| **env contract**（三環境分離） | 新增 compose 消費的變數 | **不觸發**：零新變數（§一） |

## 四、共用基礎設施

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| `project_members` 表 | `U18 project-meta-data`（DDL）、`U19 membership-service`（寫入） | `U19`、`U20`、`U21`（經 `U20`）、`U23`（經 `MembershipFacade` 讀取） | 只經 `membership_service`／`MembershipFacade`；`hierarchy_facade.py` 不得引用（`security-design.md` §四 的 grep 為 0） |
| `ix_project_members_user_id` | **`U23`**（本單元新增） | `membership_service._visible_project_ids_select` 的成員半邊 | 唯讀加速結構；無存取面 |
| `schema_rbac.sql` `J)` 區塊、`run_meta_schema_migration.py` | `U18` | `U19`、`U20`、`U23` | 本單元只**追加**一行 DDL、一筆 `EXPECTED_INDEXES`、一個 `BLOCK_SENTINELS["J"]` 項，不改既有項 |
| `openapi.json`、`frontend/src/types/api.d.ts` | 全 repo 共用產物 | 前端全體、`mcp_bridge` 產生器 | 只重 dump／重產；`mcp_bridge/generator.py` 以 operation 為單位取 schema 並去掉 description（`:282`），故 hierarchy 的 description 漂移不影響 `generated_tools.json` |

## 五、ADR-0006 四面向（基礎設施視角；逐格對照 `security-design.md` §七）

| 面向 | nfr-design 判定 | 本站判定 | 基礎設施面的內容 |
|---|---|---|---|
| **IAM** | 適用（擴充） | **適用（擴充）**——相同 | 擴充全在應用層（守門、固定訊息、靜態鎖）。基礎設施層零改動：無新資料庫角色或 grant（新索引不需 grant）、無雲端 IAM、無 GitHub token 權限變更 |
| **Encryption** | 相同 | **相同** | 零新傳輸通道、零新持久資料；索引只含既有的 `user_id` 整數 |
| **Network exposure** | 相同 | **相同** | 零新端點、零新埠、`nginx.conf` 不改；五條受影響路徑皆在既有 `/api/hierarchy/` 下、需驗證身分 |
| **Audit logging** | 適用（擴充，`[PPD1]`=A） | **適用（擴充）**——相同 | 成功刪除加記 `actor_user_id`，落在既有 stdout → docker `json-file` 驅動，保留量依大小輪替（compose `:62-68`：`max-size: 50m`、`max-file: 5`），**不是**依時間保留，也不可查詢。細節見 `monitoring-design.md` §一 |

**PBT**：不適用——本單元不是 IaC generator、cost calculator、agent routing 三個 hard-constraint 落點之一，與 nfr-design §七 一致。
