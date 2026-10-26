# 基礎設施規格 — `U19 membership-service`

> 本單元**零新基礎設施元件**（零新進程、零新監聽埠、零新環境變數、零新外部服務、
> 零新資料庫物件），但**不是**零基礎設施工作。與 `U7 hierarchy-service`
> （那一個真的是零）的差別在兩件事：
>
> 1. `[N1]`=A 選的 `FOR UPDATE` 在既有測試環境中**靜默消失**，故它需要一個
>    新的執行環境才驗得到（`[ID1]`=A）。
> 2. 兩張表將同時存在**兩條建表路徑**，而既有的三道閘門沒有一道比對它們（§四）。

## 一、上游依據（逐一指名，避免本站看起來像憑印象判定）

| 上游產出 | 它說了什麼 | 對本站的意義 |
|---|---|---|
| `logical-components.md §四` | 五列表逐項宣告零新進程／埠／環境變數／外部服務／資料庫物件；**新 CI job「本站不預選」** | 本站的唯一待決項即那一列，已由 `[ID1]`=A 定案 |
| `security-design.md §一之二` | 鎖以 `projects.id` 遞增順序取得；不可靠 `IN (...) FOR UPDATE` | 它是應用層設計，**但無機械強制**（`OPEN-ND19-2`）——本站記下它在 CI 層同樣沒有閘門 |
| `reliability-design.md §二之一` | `U7` 的 `create_project`（`:98`）自己 `db.commit()`，故天真的 `[ND1]`=A 實作是兩個交易 | 交易邊界歸 `U19`，屬 `code-generation`；本站只記它是 blocking 前置 |
| `reliability-design.md §三` | 回填沿用 `U18` 的 `[P1]`=A 形狀：獨立腳本、冪等、自我終檢、`DEPLOY.md` 記步驟 | 本站定部署步驟的**位置與順序**（§五） |
| `performance-design.md §二之二`、`scalability-design.md §三` | 兩處**刻意不加索引**，各附判準 | 本站不新增索引，並在 §二的服務表註明 |
| `observability-design.md §一` | 四類 log 的級別、欄位與事件名前綴；鎖等待走應用層計時 | 全部落在 `monitoring-design.md` |
| `observability-design.md §二` | 四項觀測面（追蹤／metrics／告警／SLO）刻意不設，承接 `observability-setup`（`CONDITIONAL`） | 本站不補，並重述 `OPEN-ND19-7` 的落空風險 |
| `components.md:863`–`:871`、`functional-spec.md §八` | ADR-0006 四面向的三欄對照 | 本站的 Network exposure 一格有新增內容（CI service container），見 §六 |
| `contract-summary.md`（`K-15`／`K-16`／`K-07`） | 兩張表由 `U18` 擁有；`projects` 由 `U7` 擁有；本單元是兩張表的唯一寫入端 | 共用資源表的歸屬欄（§三） |

## 二、Deployment

| Facet | Choice | Rationale |
|---|---|---|
| 計算模型 | **`embedded`**——既有 FastAPI process 內的新 router ＋ 新 service 類別 ＋ 一處既有端點的前置檢查 | `unit-of-work.md:307` 逐字；無新容器、無新 systemd 單元、無 sidecar |
| 網路拓樸 | **不新增監聽埠、不新增 ingress 規則、不改 `deploy/nginx.conf`** | 新端點掛在既有 `/api/` 之下，走既有 nginx 反向代理 |
| 儲存策略 | **不新增資料庫物件。** 兩張表由 `U18` 的 `schema_rbac.sql` `J)` 區塊交付；本單元是唯一寫入端 | `entities.md` 的 `owned_ddl_by` 欄；例外是 `[FD3]`=A 的 `cause` 欄，屬對 `U18` 區塊的回補（§四之三） |
| 環境設定 | **零新環境變數。** 鎖等待 WARN 門檻刻意設為程式常數而非 env | `observability-design.md §一之二` 的理由：一個 log 門檻不值得 `render-env.sh` ＋ `.env.example` ＋ compose 三處同步的成本 |
| 環境布局 | 三個範圍全部沿用，**不新增第四個**：本機 dev（`backend/.env`）、CI 測試、部署（`deploy/.env`） | `project.md` 的環境設定契約；本單元不觸發它的任何一條 |
| IaC 取徑 | **不動 `deploy/`**。唯一的基礎設施變更在 `.github/workflows/ci.yml`（新增一個 job） | `[ID1]`=A |
| 資源配額 | **不新增任何容器的 CPU／記憶體上限**，不改 `db` 的配額 | 鎖不增加常駐記憶體；交易壽命短（無外部呼叫，`reliability-design.md §一`） |

### 2.1 三個範圍皆不觸發的二元判準（驗證落點在 `code-generation`）

1. `python3 scripts/validate_env_contract.py` 綠燈；
2. 本單元的 diff **不含** `deploy/`、`deploy/render-env.sh`、任一 `.env.example`、
   `deploy/docker-compose.*.yml`、`deploy/nginx.conf`；
3. `backend/database.py` 的 diff **為空**——這是 `NFR12.5`（不改 `SessionLocal`
   的隔離等級）唯一的機械判準，而它同時擋下「順手加一支 `_ensure_*_schema()`」
   （§四之二說明為什麼那樣做會壞事）。

**為什麼第 3 項要單獨列**：`[N1]`=A 勝過 `SERIALIZABLE` 的理由之一正是不碰全域
session factory（`logical-components.md §三`）。那個理由若在實作時被放棄，
`[N1]` 的取捨基礎就不成立，而 diff 是唯一看得出來的地方。

## 三、Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| PostgreSQL（既有，部署與本機） | database | **不變**：不改隔離等級（維持預設 READ COMMITTED）、不改連線池、不新增索引 | 本單元是 repo 內**第一個**對它取列鎖的消費者（`with_for_update` 全樹零前例）。鎖是查詢層行為，不是服務設定 |
| PostgreSQL service container（**新**，僅 CI） | database（ephemeral） | `pgvector/pgvector:pg18`，與 `memory-schema` job 同一個 image；`POSTGRES_DB: cloud360`、health-check 同形 | `[ID1]`=A 的新 `concurrency` job 自帶。**只存在於 CI**，不是部署面元件。用同一個 image 的理由是 `schema_rbac.sql` 的第一條敘述是 `CREATE EXTENSION vector`——標準 `postgres:*-alpine` 跑不過 |
| logging 管線（既有） | log aggregation | **不變**：stdout／stderr → docker logs | 新增 logger `cloud360.membership`；四類事件有穩定事件名前綴（`monitoring-design.md`） |
| Redis（既有） | cache／session | **本單元不使用** | 授權判定刻意不快取（`NFR12.9`）：快取會製造「權限已撤銷但快取未失效」的窗口，而撤銷正是本單元的核心功能 |
| Ollama（既有） | embedding | **本單元不使用** | — |

**本單元不新增的服務類別**（逐一列出，避免被讀成遺漏）：cache、queue、search、
CDN、DNS、load balancer、secrets store。零新外部依賴邊界
（`reliability-design.md §四`），故也沒有熔斷器或 bulkhead 的落點。

## 四、Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| `projects` 表 | `U7`（`K-07`） | `U7`（讀寫）、**`U19`（取 `FOR UPDATE` 列鎖）** | `U19` 只讀它以驗存在與取 `owner_user_id`，但**對它取鎖**。`U7` 的既有程式不知道這件事——`delete_project` 會阻塞（`logical-components.md §三之一`，`OPEN-ND19-9`） |
| `project_members` 表 | `U18`（`K-15`） | **`U19`（唯一寫入端）**、`U20`／`U24`（經 facade 讀） | `BR1.1`：禁止跳過 facade 直接讀寫。**無機械強制**（`OPEN-FD19-3`） |
| `reselection_events` 表 | `U18`（`K-15`） | 同上 | `[FD3]`=A 的 `cause` 欄是對 `U18` 區塊的回補 |
| `SessionLocal`（全域 session factory） | 既有 | 全部 router 與 service | **本單元不改它**（`NFR12.5`，判準見 §2.1 第 3 項） |
| `logging` 管線 | 既有 | 全部模組 | 新增一個 logger 名稱，不改管線 |
| `memory-schema` job 的 postgres container | `U5`／`U18` | **刻意不共用** | `[ID1]`=A 選了新 job 而非擴充它，理由見 §四之一 |
| CI 的 pip cache | 既有（`backend` job 填） | `backend` job ＋ 新 `concurrency` job | 兩者的 `cache-dependency-path` 同為 `backend/requirements.txt`，故新 job 命中既有 cache |

### 4.1 為什麼不共用 `memory-schema` 的 container（`[ID1]`=A 的理由，記在這裡供日後重審）

`memory-schema` job 的既有註解逐字記載一個刻意的妥協：它的 `id` 與 `name`
「現在都比它的內容窄」（`U18` 的 `P1`–`P12` 也掛在那裡），而**刻意不改名**，
因為 GitHub 的 check name 取自 job 的 `name`，改它會讓 branch protection 的必要
檢查變成「缺少必要檢查」。

**本站查證了那個理由，而它對 `memory-schema` 不成立**——詳見
`cicd-pipeline.md §一之二`：`ut` 沒有任何必要檢查，`main` 只有一個
（`Repository contract`，即 `repo-contract` job 的 `name`）。
**真正被名稱鎖住的是 `repo-contract`，不是 `memory-schema`。**

決定不變（新增而非擴充），但理由換成下表這三項**實測**依據：

| 動作 | 本站實測後的評估 |
|---|---|
| **新增**一個 job | **選這個。** 新 check 不影響任何既有必要檢查；且 `concurrency` 這個名字說出它驗什麼 |
| **改名**既有 job | 不需要做，故不評估。（附帶更正：對 `memory-schema` 而言今天並不危險，危險的是改 `repo-contract`） |
| 在既有 job 上**再掛第三類東西** | 不選。`pip install` 是**串行**加進一個目前只跑 `psql`、完全不需要 Python 的 job；且「Memory schema」這個名字會第三次失真 |

新 job 的代價是第二座 container 的 runner 分鐘數。**wall-clock 代價約為 0**：
本站以腳本解析 `ci.yml` 的 `needs:` 邊，確認 6 個 job 中除 `gate` 外的 5 個
**全部且僅** `needs: gate`，彼此並行；第 6 個加進去仍然並行。

### 4.2 本站查出的一件事：兩張表將同時存在兩條建表路徑，而三道閘門沒有一道比對它們

本單元必須新增 `ProjectMember` 與 `ReselectionEvent` 的 ORM model
（它是唯一寫入端，而寫入走 SQLAlchemy——本站實查 `backend/services/*.py` 的
`db.execute(text(` 命中數為 **0**，故 raw SQL 不是本 repo 的寫入慣例）。
一旦它們進入 `Base`，`backend/database.py:90` 的
`Base.metadata.create_all(bind=engine)`
就會在**任何缺表的資料庫**上把它們建出來——`create_all` 預設 `checkfirst=True`，
故它建的是**缺少的**表，而既有表一律不動。

於是同一張表有兩個建表權威：

| 路徑 | 何時生效 | 誰驗它 |
|---|---|---|
| `schema_rbac.sql` 的 `J)` 區塊 | 空 volume 的 entrypoint，或手動跑 `run_meta_schema_migration.py` | **`memory-schema` job 的 `P1`–`P12`** |
| `Base.metadata.create_all()` | 後端啟動時，若表不存在；**以及每一次 `tests/helpers.py` 的 `make_session()`** | **沒有任何閘門** |

**`U7` 已經踩過這個洞，而且把教訓逐字寫在 `backend/models.py` 裡**
（`Project` 的 `__table_args__` 上方）：

> 「**約束必須與 DDL 逐條對齊，不只是欄位。** ……把這三張表納入 `Base` 之後，
> **建表的權威就從 raw DDL 換成了這裡**——少寫一條 CHECK 就等於在測試環境裡
> 悄悄移除它（`U4` 的 `test_change_record_source_is_a_closed_enum`
> 在本單元第一次跑全套時就因此紅燈）。」

**既有的一致性測試只比對欄位名，不比對約束與索引。** `test_hierarchy_service.py`
的 `T25` 逐字鎖住 `Project`／`System`／`DiagramChangeRecord` 的
`{c.name for c in model.__table__.columns}` 對 DDL 欄位集合——
**約束名、索引名、partial 條件、外鍵的有無都不在它的射程內**。

#### 本單元必須逐條對齊的清單（本站從 `schema_rbac.sql` 的 `J)` 區塊逐行抄出）

| 物件 | DDL 現況 | ORM 必須 |
|---|---|---|
| `project_members` 的 `project_id` | `REFERENCES projects (id) ON DELETE CASCADE` | 宣告 `ForeignKey(..., ondelete="CASCADE")` |
| `project_members` 的 `user_id` | `REFERENCES users (id)`，**無 `ON DELETE` 子句**（`OQ-H1` 刻意未決） | 宣告 FK **且不帶** `ondelete` |
| `project_members` 的 `invited_by` | `REFERENCES users (id)`，nullable | 同上，`nullable=True` |
| `ck_project_members_role` | `CHECK (role IN ('project_admin','member'))` | 宣告同名 `CheckConstraint` |
| `uq_project_members_project_user` | `UNIQUE (project_id, user_id)` | 宣告同名 unique 約束 |
| `project_members` 的額外索引 | **刻意沒有**（兩個方向各有理由，見該區塊註解） | **不得**自行補 `index=True` 在 `user_id` 上 |
| **`reselection_events.project_id`** | **刻意無外鍵**（`[ND1]`=A，稽核須在專案被刪後存活） | **不得宣告 `ForeignKey`**——這是最容易被習慣性加上的一條 |
| `ix_reselection_events_unack` | `ON (promoted_user_id) WHERE acknowledged_at IS NULL`（**partial**） | 宣告同名 `Index` 並帶 `postgresql_where`＋`sqlite_where`（形狀照 `uq_projects_default_per_owner` 的既有先例） |
| `ix_reselection_events_project_id` | 普通 btree | 宣告同名 `Index` |
| `previous_role`／`new_role` | **刻意無 CHECK** | **不得**加 `CheckConstraint`；封閉列舉由應用層 `BR5.4` 承載（`entities.md` 的 `allowed_values` 即此） |
| 表與欄位 COMMENT | 兩張表皆有完整的表與欄位 COMMENT | ORM 的 `comment=` 非必要（COMMENT 由 DDL 路徑給），但**若 ORM 建表則 COMMENT 不存在**——見下方的殘留缺口 |

#### 殘留缺口（本站如實記載，不假裝已關閉）

即使上表逐條對齊，`create_all()` 建出來的表仍然**沒有 COMMENT**。
而本站實查 `verify_meta_schema.sql`：**12 條斷言裡只有 `P12` 碰 COMMENT，
且它驗的是 `system_requirement_fields` 的表 COMMENT**
（`:191` 的 `obj_description('public.system_requirement_fields'::regclass, ...)`，
全檔只有這一處 `obj_description`／`col_description`）。
**`project_members` 與 `reselection_events` 的 COMMENT 在任何路徑上都沒有斷言。**
所以：

- **在 CI 與部署的乾淨環境裡**，`schema_rbac.sql` 先跑，`create_all` no-op，一切正確。
- **在一個既有的本機資料庫上**（沒跑過 `run_meta_schema_migration.py`），
  後端啟動的 `create_all` 會先建出表，於是該環境永久缺 COMMENT，
  且之後再跑 `schema_rbac.sql` 也補不回來（`CREATE TABLE IF NOT EXISTS` 整段 no-op）。

後果嚴重度：**低且限本機**（COMMENT 是給人讀的防呆機制，不影響行為），
但它說明一件該被寫下的事——**兩條建表路徑不等價，而只有一條被驗**。
記為 `OPEN-ID19-1`。

#### 可執行的補強（指派 `code-generation`，本單元下一站，`ALWAYS`）

擴充 `T25` 形狀的測試，使它除欄位名之外另比對三項，三項都是二元可判：

1. `ReselectionEvent.__table__.foreign_keys` 為**空集合**（`[ND1]`=A 的刻意無外鍵）；
2. 兩張表的 `__table__.constraints` 與 `__table__.indexes` 的**名稱集合**
   與 `schema_rbac.sql` 的 `J)` 區塊宣告的名稱集合相等；
3. `ix_reselection_events_unack` 的 `dialect_options` 含 `where` 條件
   （拿掉 `WHERE` 之後索引仍存在、查詢仍正確，失敗模式是效能而非正確性
   ——`U18` 的註解逐字記載這一點，並為此在 DDL 側設了 `P8`）。

### 4.3 `[FD3]`=A 的 `cause` 欄是跨單元 DDL 回補，它有三個落點

| 落點 | 動作 |
|---|---|
| `schema_rbac.sql` 的 `J)` 區塊 | `reselection_events` 加 `cause VARCHAR(32) NOT NULL`；**是否加 CHECK 需與上表的「`previous_role` 刻意無 CHECK」分開判**——`cause` 的兩個值由 `[FD3]`=A 定案，不是未決事項 |
| `backend/models.py` | ORM 同步（否則 `T25` 紅燈） |
| `backend/scripts/verify_meta_schema.sql` ＋ `DEPLOY.md §2.2.9` | 新增一條斷言並更新欄位表（`project.md` 的 blocking 同步規則） |

**既有環境的升級路徑**：`reselection_events` 在既有環境尚未存在
（`U18` 的腳本還沒在 `192.168.10.10` 跑過），故 `cause` 可直接寫進 `J)` 區塊的
`CREATE TABLE`，**不需要 `ALTER TABLE`**。這個便宜只在腳本尚未執行時成立——
一旦它跑過，`cause` 就得走 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`。
**順序前置條件因此是：`cause` 的 DDL 必須與 `U18` 的腳本在同一次部署之前落地。**

## 五、既有環境的執行順序（本站的第二項實質產出）

本單元引入**第三支**一次性腳本（`U4` 的階層遷移、`U5`＋`U18` 的結構建立、
本單元的成員回填）。三者有嚴格順序，而**順序錯誤的後果各不相同**：

| # | 動作 | 前置 | 跳過或順序錯誤的後果 |
|---|---|---|---|
| 1 | `python scripts/run_hierarchy_migration.py` | — | `J)` 的兩條外鍵指向 `projects`／`systems`，表不存在則第 2 步以可讀訊息擋下 |
| 2 | `python scripts/run_meta_schema_migration.py`（`U5`＋`U18` 全部新物件） | 第 1 步 | 兩張表不存在 → 本單元的任何寫入拋 `UndefinedTable`。**但若後端先啟動過，`create_all` 會先建出無 COMMENT 的版本**（§四之二） |
| 3 | **本單元的回填腳本**（`project_members` 補既有專案的擁有者列） | 第 2 步 | 既有專案的擁有者被 `BR1.6` 判為非成員 → 被拒絕存取自己的專案。**非靜默**（使用者立刻發現） |

### 5.1 deploy-on-merge 與手動腳本之間的窗口（本站寫明，不留給下游自己發現）

`org.md` 的部署模型是 **deploy-on-merge**：合併進 `ut` 即自動部署。
而第 2、3 步是**手動**的（`U18` 的 `[P1]`=A 先例）。故存在一個窗口：
程式已上線，回填尚未執行。

| 問題 | 答案（本站實查） |
|---|---|
| 這個窗口裡既有專案的擁有者會被鎖在外面嗎？ | **第一次部署不會。** 本單元的消費端（`U20`／`U13`／`U21`／`U24`）都在後續 Bolt；`hierarchy_facade.list_projects` 目前是 **owner-scoped**（讀 `projects.owner_user_id`，不讀 `project_members`），故既有的專案列表路徑不經本單元 |
| 既有停用端點的前置檢查會誤判嗎？ | **不會，但方向是「過寬」而非「過嚴」**：零成員列時 `assertCanDeactivate` 的 `HAVING count(*) = 1` 找不到任何專案，故它**放行**。保護在回填之後才生效 |
| 那什麼時候真的會鎖人在外面？ | **第一個消費端上線時**。這就是 `NFR12.25` 逐字要求「回填必須在任何消費端上線之前」的理由 |

**對 `delivery-planning` 的交接**：本單元與第一個消費端之間存在一條
**手動步驟邊**——它不是依賴圖上的邊，而是一個部署程序前置條件。
`delivery-planning` 的 Bolt 邊界即一次真實部署，故「回填已在 staging 執行過」
必須是第一個消費端所在 Bolt 的前置條件。記為 `OPEN-ID19-2`。

### 5.2 `DEPLOY.md` 的落點（`project.md` 的 blocking 同步規則）

| 項目 | 落點 |
|---|---|
| 回填腳本的執行步驟與驗證指令 | `DEPLOY.md` **新增 §2.2.10**（接在 `U18` 的 §2.2.9 之後，使三支腳本的順序在文件上也是順序） |
| `cause` 欄位 | `DEPLOY.md §2.2.9` 的 `reselection_events` 欄位說明由「8 欄」改為「9 欄」並補該欄語意 |
| 寫哪一半 | **只寫 `## 中文版` 半部**，沿用 `U18`／`U5` 的既有處置；英文半部已是 39 行對 490 行的縮寫版，早已漂移（該決定屬 repo 級，不在本 stage） |

### 5.3 `LOCAL-DEV.md`：blocking 規則**不觸發**，但有一項該補的非 blocking 內容

`project.md` 的 blocking 觸發清單逐字為「異動 `backend/database.py` 的 schema 補丁、
`deploy/nginx.conf`、任一 `.env.example` 或 `render-env.sh`」。本單元**四者都不動**
（§2.1 第 3 項正是在守住第一項），故**不觸發**。

**但該規則的存在理由觸發了**：它逐字是「唯一寫下本機執行全部功能所需隱性前置條件
的文件」。本站實查 `LOCAL-DEV.md` 對 `project_members`／`reselection_events`／
`run_meta_schema_migration` 的命中數為 **0**——而本單元是**第一個在執行期真的讀寫
那兩張表的程式**（`U18` 是純 DDL，所以它不在本機壞掉）。

| 項目 | 判定 |
|---|---|
| blocking 同步 | **不觸發**（字面觸發清單四項皆未動） |
| 建議補入（非 blocking） | 既有本機資料庫需跑第 2、3 步；以及 §四之二 的「後端先啟動過會得到無 COMMENT 的表」這個本機專屬陷阱 |
| 落點 | `code-generation`（`ALWAYS`，本單元下一站）。記為 `OPEN-ID19-3` |

**不自行把它升格為 blocking**：規則的觸發清單是上游定的，本站無權擴張它；
把判定寫下來並指派，是能做且該做的。

## 六、ADR-0006 四面向：本站的增量

逐格對照 `functional-spec.md §八` 的三欄表與 `security-design.md §四`。
**兩份上游的判定一致，本站不改任何一格的判定**，只補基礎設施層的落點。

| 面向 | 判定（與兩份上游一致） | 本站的基礎設施增量 |
|---|---|---|
| **IAM** | **適用（本單元的核心）** | 無新的基礎設施層授權元件：授權全在應用層 facade，**不靠** nginx 規則、不靠網段隔離、不靠 IAM policy。CI 的新 container 不持有任何應用憑證（`POSTGRES_PASSWORD: postgres`，與 `memory-schema` 同形，僅 ephemeral CI） |
| **Encryption** | **本單元無落點**（上游為此面點名的落點是 `McpBridge`／`U21`） | **不寫「不適用」**（那會讀成該面向對本修訂不成立）。CI container 的連線是 localhost 容器網路、生命週期為單次 job，不需 TLS |
| **Network exposure** | **適用，有落點** | **本站新增一項上游沒有的落點**：新 `concurrency` job 的 postgres service container。它 `ports: 5432:5432` 僅映射到 runner 的 localhost、生命週期等於 job、資料為合成測試資料。它**不是**部署面的暴露增量。本單元在部署面仍維持零新監聽埠 |
| **Audit logging** | **適用** | 稽核列（`reselection_events`）與結構化 log 兩個載體的界線在 `monitoring-design.md`；本站確認**不新增 log 轉送或保留設定**（沿用既有 docker logs） |

**PBT：適用且 blocking**，作用對象 `selectSuccessor`，性質為排列不變性。
**它跑在既有 `backend` job**（純函式、不需資料庫、`hypothesis` 已在
`requirements.txt`），**不是**新 job 的職責——寫明以免兩個 job 的分工被誤讀。
