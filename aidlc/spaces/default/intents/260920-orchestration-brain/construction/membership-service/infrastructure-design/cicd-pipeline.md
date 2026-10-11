# CI/CD — `U19 membership-service`

> 本單元是本 intent 第一個**真的需要新 CI 載體**的單元。
> `U7` 新增五個端點卻零新 job；本單元新增一個 job，而理由只有一個：
> `[N1]`=A 選的機制在既有測試環境中**靜默消失**。

## 一、既有管線的機械事實（本站解析 `ci.yml`，非引述 `team.md` 的摘要）

`team.md ## Deployment` 把管線描述為「依序為 `repo-contract` → `frontend` →
OpenAPI drift → `backend` → `docker-build`」。**那是一份摘要，不是 job 圖**，
而本 intent 已經為「照 `team.md` 的描述寫 job 圖」付過一次代價
（`brain-infra` 的 `infrastructure-design` 審查 `R-02`，Major）。

本站以腳本解析 `needs:` 邊：

| job | `needs` |
|---|---|
| `gate` | （無） |
| `repo-contract` | `gate` |
| `frontend` | `gate` |
| `backend` | `gate` |
| `memory-schema` | `gate` |
| `docker-build` | `gate` |

**6 個 job；除 `gate` 外的 5 個全部且僅 `needs: gate`，故彼此並行。**
OpenAPI drift **不是獨立 job**，是 `backend` job 內的一個 step；
`frontend` job 另有兩道型別漂移閘門。

### 1.2 「閘門」這個詞在 `ut` 上目前名不符實——本站實查 branch protection

本站以 `gh api` 查了兩條分支的保護設定：

| 分支 | 必要狀態檢查 |
|---|---|
| **`ut`**（整合主幹，deploy-on-merge 的目標） | **完全沒有**（API 回應中 `required_status_checks` 這個 key **不存在**），且 `rulesets` 為空陣列 |
| `main`（對外發佈線） | **恰好一個**：`Repository contract`（`strict: true`）——它是 `repo-contract` job 的 `name:` 逐字值 |

**後果，必須被誠實讀成兩句話而不是一句**：

1. **六個 job 全部會紅燈**（紅燈本身是真的，`exit 1` 就是 `exit 1`）；
2. **但在合併進 `ut` 這條路徑上，沒有一個紅燈會擋住合併。** 它們是**訊號**，
   不是**閘門**。本檔 §三 的「會紅燈（抓得到）」一律按此解讀：
   抓得到 ＝ 人看 PR 的 checks 時看得到，**不等於**機械阻擋。

**這同時更正了一個被繼承的理由。** `memory-schema` 的既有註解以
「改名會讓 branch protection 的必要檢查變成缺少必要檢查」為由刻意不改名——
**那個風險對 `memory-schema` 今天不成立**（`ut` 無必要檢查；`main` 的唯一必要檢查
是 `Repository contract`）。**真正被名稱鎖住的 job 是 `repo-contract`。**
該註解的謹慎方向是對的、結論（不改名）也無害，但它寫下的依據需要被更正，
否則下一個人會以為每個 job 的 name 都受 branch protection 保護。

**本站不改那段註解**（它屬 `U5`／`U18` 的交付物，且改 `.github/` 的註解不在本單元
範圍內），只在此記下實測結果。記為 `OPEN-ID19-6`。

**對 `[ID1]`=A 的影響：無。** 選新 job 的理由從未依賴 branch protection——
它依賴的是「結構性隔離 ＋ 自己的 check name ＋ 並行故 wall-clock 約為 0」，
三項都不受此影響。但 `OPEN-ID19-6` 指出一件該被決定的事：
**若團隊要讓本單元的併發覆蓋面真的不可繞過，必須把該 check（以及其餘五個）
加進 `ut` 的必要檢查清單**——那是 repo 層設定決定，不是本 stage 能做的。

## 二、新增的 job（`[ID1]`=A）

### 2.1 形狀

| 項目 | 值 | 理由 |
|---|---|---|
| job id／name | `concurrency` ／ 名稱須點出「真實 PostgreSQL 的併發行為」 | **新增一個 check 不影響任何既有必要檢查**（實測：`ut` 無必要檢查、`main` 只有 `Repository contract`，見 §一之二）。名字說出它驗什麼，而不是再製造一個「name 比內容窄」的 job |
| `needs` | `gate`（與其餘五個相同） | 保持全並行；**wall-clock 增量約為 0** |
| `if` | `needs.gate.outputs.is_sync != 'true'`（沿用五個既有 job 的同一條件） | 同步型 push 不跑測試套件 |
| service container | `pgvector/pgvector:pg18`，與 `memory-schema` 同一 image、同形 health-check | `schema_rbac.sql` 的第一條敘述是 `CREATE EXTENSION vector`；標準 `postgres:*-alpine` 跑不過（`memory-schema` 的既有註解已記載） |
| Python | `actions/setup-python@v5`，`python-version: '3.12'`，`cache: pip`，`cache-dependency-path: backend/requirements.txt` | 與 `backend` job 同一個 `cache-dependency-path`，故命中它填的 pip cache |
| 建表 | `psql -f schema_rbac.sql`（**一次就夠**） | 冪等性由 `memory-schema` 的第二次套用驗（`BR1.3`），本 job 不重複那件事 |
| **連線字串** | job 層 env `DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5432/cloud360`，**測試從 `os.environ["DATABASE_URL"]` 讀它**（缺值即大聲失敗，不得退回 SQLite 預設） | **零新環境變數**：`DATABASE_URL` 已是既有變數（`backend` job 的兩個 step 已設同一形式），故 §2.1 的「零新環境變數」不被破壞。`+psycopg` 後綴必須顯式——裸 `postgresql://` 會回頭依賴 SQLAlchemy 的隱含預設，而該預設在 2.1 由 `psycopg2` 改為 `psycopg`（兩個既有 step 的註解逐字記載這件事）。**退回 SQLite 是本 job 唯一不可接受的失敗方式**：它會讓整個 job 綠燈而鎖從未存在 |
| 測試執行 | `python -m unittest discover -s tests_pg` | 見 §2.2 |
| `timeout-minutes` | **必須明確設定**（值由 `code-generation` 定） | 併發測試的失敗模式是**卡住**，不是紅燈。靠 runner 預設的 360 分鐘等於把 runner 佔住數小時 |

### 2.2 新測試根目錄 `backend/tests_pg/`，以及它為什麼是結構性隔離

| 事實 | 值 |
|---|---|
| `backend/tests/` 既有測試檔數 | **51**（`ls backend/tests/test_*.py \| wc -l`），**全部**走 in-memory SQLite 或 mock |
| 需要真實 PostgreSQL 的既有測試 | **0** 個——本單元是第一個 |
| `skipUnless`／`skipIf` 的既有先例 | **0** 個（全樹 grep） |
| `backend` job 的測試步驟 | `python -m unittest discover -s tests -v`，**無 PostgreSQL service**，env 只有 `JWT_SECRET` |

**所以放進 `backend/tests/` 的真實 PG 測試會在 `backend` job 連線失敗。**
把它用 env guard 跳過是可行的，但 `unittest` 的「跳過」與「通過」在輸出上
**無法分辨**（`OK (skipped=1)`）：環境變數哪天從 job 裡掉了，覆蓋面會**靜默消失
而 CI 全綠**。新目錄是**結構性**隔離——`discover -s tests` 看不到它，
不需要任何條件式邏輯，沒有東西可以忘記設。

**兩個測試根目錄的存在本身必須被寫下來**，否則下一個人新增真實 PG 測試時
會放回 `backend/tests/` 並踩同一個洞。落點：`backend/tests_pg/__init__.py`
的 docstring ＋ `LOCAL-DEV.md`（非 blocking，見 §五之三）。

**本機怎麼跑它**（這是契約的另一端，不寫下來就沒有人擁有）：開發者需要一個
**真實的** PostgreSQL 與 `DATABASE_URL`，然後
`cd backend && DATABASE_URL=... python -m unittest discover -s tests_pg`。
`LOCAL-DEV.md` 第 2 節已有本機 PostgreSQL（含 pgvector）的建法，故前置條件已存在、
只是沒人寫下這條指令。與 §五之三 的兩支腳本同屬 `OPEN-ID19-3`。

### 2.3 這個 job 要驗什麼：三條斷言

| # | 斷言 | 為什麼只有真實 PostgreSQL 驗得到 |
|---|---|---|
| 1 | **`FOR UPDATE` 真的存在**：兩個並行交易對同一專案的成員變更被序列化，守門不被繞過（`BR2.1`／`NFR12.1`） | **本站實測**（`sqlalchemy 2.1.1`）：`with_for_update()` 在 SQLite dialect 下編譯出的 SQL 是 `SELECT p.id, p.name FROM p WHERE p.id = ?`——**鎖子句整段不見，且無錯誤、無警告**。在既有測試路徑上這條測試會在**完全沒有鎖**的情況下通過 |
| 2 | **不同專案不互相阻塞**（`NFR12.13`） | 同上：沒有鎖就沒有阻塞，SQLite 上這條恆真 |
| 3 | **`assertCanDeactivate` 不取鎖**（`NFR12.3`） | 同上 |

**順序須以 barrier 釘住，不得用 `sleep`**（`unit-of-work.md` 對 `U22` 已記過
「一個 flaky 的併發測試等於沒有測試」）。失敗時須印出兩個執行緒各自卡在哪一步
（barrier 前／取鎖中／已提交）——只印 `assertEqual` 失敗對診斷無用。

### 2.4 刻意**不**放進這個 job 的東西

| 不放 | 理由 |
|---|---|
| PBT（`selectSuccessor` 的排列不變性） | 純函式、不讀 DB（`BR4.1`），`hypothesis` 已在 `requirements.txt`。它屬既有 `backend` job |
| `NFR12.12` 的聚合查詢等價測試 | 它比對「聚合查詢」與「逐專案判定」的結果，**不需要鎖**，SQLite 的 `GROUP BY ... HAVING` 足夠。它屬既有 `backend` job 的 `backend/tests/` |
| `U18` 的 `P1`–`P12` schema 斷言 | 已在 `memory-schema`，不搬動 |
| `schema_rbac.sql` 的冪等性（第二次套用） | 已由 `memory-schema` 的 `BR1.3` 步驟驗，不重複 |

**這張表存在的理由**：新 job 很容易變成「所有難測的東西都丟進去」的垃圾桶，
而它每多一項就多一份把 container 建起來的理由，最後會變成第二個
「name 比內容窄」的 job。

## 三、既有閘門：本單元必須讓它們綠燈，以及兩項覆蓋不足（性質不同，不要混為一談）

下表第 3 項與第 6 項都會讓本單元的某些錯誤通過，但**兩者的性質不同**：

| 項 | 性質 |
|---|---|
| 第 3 項（顯式 409 宣告） | **根本沒有閘門。** 不是閘門太寬，是這條變更路徑上沒有任何自動化斷言 |
| 第 6 項（ORM ↔ DDL 一致性） | **閘門存在但射程比名字窄**：`T25` 只比對欄位名，不比對約束、索引、partial 條件與外鍵的有無 |

| # | 閘門 | 所在 job | 本單元的義務 | 漏了會怎樣 |
|---|---|---|---|---|
| 1 | **OpenAPI spec drift**（`dump_openapi.py --check`） | `backend` | 新端點落地後重 dump `openapi.json` | **會紅燈**（抓得到） |
| 2 | **API type contract drift**（`npm run check:types`） | `frontend` | 重跑型別產生器並 commit `src/types/api.d.ts` | **會紅燈**（抓得到）。注意它與第 1 項**在不同 job 且並行**，兩邊各自獨立紅燈 |
| 3 | **顯式 409 宣告**（`BR6.2`／`BR6.6` 形狀） | — | 新端點與擴充的既有端點須寫 `responses={409: ...}` | **不會紅燈**。FastAPI 不從 `raise HTTPException` 推導狀態碼，故漏宣告時 spec 與型別都「正確地」少了它，兩道漂移閘門都綠 |
| 4 | **backend `unittest`** | `backend` | 新測試檔放進 `backend/tests/` 即被撿到；**須在匯入任何應用模組之前先匯入 `tests.helpers`**（51 個既有測試檔中有 **29** 個這麼做，分三種寫法：`import tests.helpers  # noqa: F401` **10** 個、`from tests.helpers import ...` **20** 個、`from tests import helpers` **2** 個；三者都會執行該模組的 module-level 副作用，故都有效）。它做兩件事：把 `backend/` 與 `backend/services/` 插進 `sys.path`（**在任何環境都必要**），以及在 `psycopg` **未安裝時**才裝 stub（`helpers.py:19` 的 `if importlib.util.find_spec("psycopg") is None`——CI 裝了它，故 CI 走的只有 `sys.path` 那一半） | 測試不執行而無人察覺 |
| 5 | **`repo-contract`**（兩支 validator） | `repo-contract` | 本單元宣稱零新部署設定（§2.1 的三項判準） | **會紅燈** |
| 6 | **ORM ↔ DDL 一致性**（`T25` 形狀） | `backend` | 兩張新 ORM model 須納入該測試；**並擴充它比對約束與索引，而非只比欄位名** | 見下方 |

### 3.1 第 3 項的理由必須更正（本站主動揭露，因上游已凍結）

`nfr-design` 的 `security-design.md §三之二` 與本單元上游多處引用一個測量：
「`openapi.json` 的 55 個 operation 宣告的狀態碼只有 `{200, 422, 201, 204}`，
非 2xx/422 的宣告數為 **0**」，並據此說漂移閘門對狀態碼層級是盲區。

**本站重新量測（`python3` 解析 `openapi.json`）：**

| | 那個測量 | 今天 |
|---|---|---|
| paths | — | **47** |
| operations | 55 | **62** |
| 狀態碼分佈 | `{200, 422, 201, 204}`，非 2xx/422 為 0 | `{200: 56, 201: 3, 204: 3, **404: 1**, **409: 4**, 422: 51}` |

**`409` 已宣告在四個端點**：`POST /api/hierarchy/projects`、
`DELETE /api/hierarchy/projects/{project_id}`、
`POST /api/hierarchy/projects/{project_id}/systems`、
`DELETE /api/hierarchy/systems/{system_id}`——全部由本 intent 的 `U7` 交付。

| 項目 | 狀態 |
|---|---|
| **`BR6.2` 的結論** | **仍然成立**。FastAPI 不從 `raise HTTPException` 推導狀態碼，故不顯式宣告就不進 spec，而兩道漂移閘門比對的是「已 commit 的位元組 vs 重新產生的位元組」，兩邊都少同一項時一致 |
| **它陳述的理由** | **已過期**。閘門從來不是對**已宣告**的非 2xx 盲目——它只對「raise 了但沒宣告」盲目。而「零前例」的說法已不成立：有四個先例，其中一個正好在 `[ND1]`=A 要移動的那個端點上 |
| 這個測量的傳播範圍 | 本 intent 多份已核可產出（inception 的 `requirements.md`、`contract-summary.md`、`unit-of-work.md`、`bolt-plan.md`，以及本單元的 `rules.md`／`entities.md`） |

**本站不回改上游**（`refined-mockups:c3` 的形狀：下游修正上游已核可 artifact 的
內部瑕疵時，在本站明記「這是對齊修正、非本站新定案」）。
`nfr-design` 的審查 `R-02` 已獨立查出同一件事，本節是它在 CI 層的落點。
記為 `OPEN-ID19-4`。

### 3.2 第 6 項：既有一致性測試的射程比它看起來窄

`test_hierarchy_service.py` 的 `T25` 鎖住 ORM 與 `schema_rbac.sql` 的一致性，
但它比對的是 `{c.name for c in model.__table__.columns}` 對 DDL 欄位集合
——**只有欄位名**。約束名、索引名、partial 條件、外鍵的有無都不在射程內。

而本單元要加的兩張 ORM model 恰好有三項**不在欄位名裡**的事實：

| 事實 | 若 ORM 寫錯 |
|---|---|
| `reselection_events.project_id` **刻意無外鍵** | 習慣性加上 `ForeignKey` → `create_all` 建出有外鍵的表，與 `[ND1]`=A 的「稽核須在專案被刪後存活」相反。**`memory-schema` 的 P 斷言驗的是 `schema_rbac.sql` 建的表，看不到這一條** |
| `ix_reselection_events_unack` 是 **partial** | 漏 `postgresql_where` → 索引仍存在、查詢仍正確，失敗模式是**效能而非正確性**（`U18` 的 DDL 註解逐字記載，並為此設了 `P8`） |
| `previous_role`／`new_role` **刻意無 CHECK** | 習慣性加 `CheckConstraint` → 與 DDL 不一致 |

**`U7` 已經踩過這類洞並把教訓逐字寫進 `backend/models.py`**
（`Project.__table_args__` 上方）：納入 `Base` 之後「建表的權威就從 raw DDL
換成了這裡——少寫一條 CHECK 就等於在測試環境裡悄悄移除它」。
完整的逐條對齊清單在 `infrastructure-specification.md §四之二`。

**可執行補強**（指派 `code-generation`）：`T25` 除欄位名之外另比對
① `ReselectionEvent.__table__.foreign_keys` 為空集合、
② 兩張表的約束與索引**名稱集合**與 DDL 宣告相等、
③ `ix_reselection_events_unack` 帶 `where` 條件。三項皆二元可判。

## 四、測試義務彙整（驗證落點全部在 `code-generation`）

來自 `team.md` 的 A／B／C 規則、`project.md` 的交叉要求與 ADR-0006：

| # | 義務 | 來源 | 落點 |
|---|---|---|---|
| 1 | **allow/deny 雙向 `TestClient`**：具 `K3`／`K4` → 2xx，無 → 403，缺一不可 | `team.md` 規則 A ＋ B 的交叉要求 | `backend/tests/` |
| 2 | **新端點的 status code ＋ `response_model` 欄位集合斷言** | `team.md` 規則 B | `backend/tests/` |
| 3 | **既有停用端點的 409 回應**：狀態碼 ＋ `LastAdminGuardReport` 的欄位集合（`FR12.5b` 的 DoD） | `team.md` 規則 B ＋ `BR6.2` | `backend/tests/` |
| 4 | **既有兩道保護不得被削弱**（`BR6.3`）：自我停用、最後一位可編輯的全域管理者 | `BR6.3` | `backend/tests/` |
| 5 | **PBT：`selectSuccessor` 的排列不變性**（**blocking**，ADR-0006） | `BR4.1`／`BR4.2` | `backend/tests/`（既有 `backend` job） |
| 6 | **聚合查詢 ↔ 逐專案判定的等價測試**（`NFR12.12`） | `[N3]`=C | `backend/tests/` |
| 7 | **併發守門三條斷言** | `[N1]`=A ＋ `[ID1]`=A | **`backend/tests_pg/`（新 job）** |
| 8 | **ORM ↔ DDL 一致性擴充**（§三之二 的三項） | `team.md`「單一真實來源」 | `backend/tests/` |
| 9 | **前端資料形狀的 e2e 斷言**（規則 C） | `team.md` 規則 C | **不在本單元**：成員頁是 `U24`。本單元無前端面（`frontend/src` 對 `projects` 命中數為 **0**） |

**第 4 項是本單元最危險失效模式的唯一對策**：
`logical-components.md §二之二` 把「既有停用端點的前置檢查未被呼叫」列為
**靜默**失效——停用照常成功，而 `AC12.3.3` 的保護消失。
**沒有那個測試，拿掉這道檢查不會有任何東西變紅。**

## 五、部署與回滾

### 5.1 部署策略：沿用，不新增

| 項目 | 值 |
|---|---|
| 策略 | **deploy-on-merge 到 staging**（合併進 `ut` 觸發 `deploy.yml`），沿用 ADR-0007／ADR-0008 |
| 本單元的變更 | **零**：不改 `deploy.yml`、不改任一 compose、不改 `nginx.conf`、不改 `render-env.sh` |
| 回滾 | 沿用既有 `rollback` job（還原 last-good、開 revert PR、dispatch Deploy Doctor） |

### 5.2 回滾的一項不對稱，本站寫明

`deploy.yml` 的回滾還原的是**映像**。而本單元引入的第三支一次性腳本
（成員回填）是**資料動作**，映像回滾**不會**撤銷它。

| 情境 | 回滾後的狀態 |
|---|---|
| 程式已部署、回填已跑、部署失敗後回滾 | 映像回到 last-good，而 `project_members` 的回填列**留著** |
| 那會壞掉嗎 | **不會**。回填寫的是 `(project_id, owner_user_id, 'project_admin', now())`，而 last-good 的程式**不讀這兩張表**（本單元是第一個讀寫者）。多出來的列對舊程式不可見 |
| 需要反向腳本嗎 | **不需要**，理由如上。**但這個結論只在第一次部署成立**——一旦有消費端上線，回滾的語意就要重新評估 |

記為 `OPEN-ID19-5`（named-gap，非本輪缺陷）。

### 5.3 既有環境的三步順序，以及 deploy-on-merge 留下的窗口

完整的三步順序與各自的跳過後果在
`infrastructure-specification.md §五`。此處只記 CI/CD 面的結論：

| 事項 | 結論 |
|---|---|
| 第 2、3 步是**手動** | 沿用 `U18` 的 `[P1]`=A 先例（獨立腳本、非零碼、不動啟動路徑） |
| 窗口的實際風險 | **第一次部署無風險**（本站實查：`hierarchy_facade.list_projects` 是 owner-scoped，不讀 `project_members`；零成員列時 `assertCanDeactivate` 的 `HAVING count(*) = 1` 找不到專案故**放行**，方向是過寬而非過嚴） |
| 真正的風險時點 | **第一個消費端上線時**——即 `NFR12.25` 逐字要求「回填必須在任何消費端上線之前」的理由 |
| 對 `delivery-planning` 的交接 | 「回填已在 staging 執行過」必須是第一個消費端所在 Bolt 的前置條件。它不是依賴圖上的邊，是部署程序前置條件。`OPEN-ID19-2` |
| `DEPLOY.md` | 新增 §2.2.10（接在 `U18` 的 §2.2.9 之後）；§2.2.9 的 `reselection_events` 由「8 欄」改「9 欄」（`[FD3]`=A 的 `cause`）。**只寫中文半部**，沿用既有處置 |
| `LOCAL-DEV.md` | blocking 規則**不觸發**（四項字面觸發條件皆未動），但本站實查它對 `project_members`／`reselection_events`／`run_meta_schema_migration` 的命中數為 **0**，而本單元是第一個在執行期讀寫那兩張表的程式。建議補入（非 blocking），`OPEN-ID19-3` |

### 5.4 CI/CD 的憑證管理：本單元零增量

| 項目 | 值 |
|---|---|
| 新 GitHub secret | **無** |
| 新 job 的資料庫憑證 | `POSTGRES_USER/PASSWORD: postgres`**明文寫在 workflow**，與 `memory-schema` 同形。**這不是洩漏**：service container 的生命週期等於單次 job、不對外 publish、資料為合成測試資料，且它與任何真實環境的憑證無關 |
| `project.md` 的憑證查證規則 | **不觸發**（沒有新增任何憑證型 secret，故無「落在 secrets 還是 variables」可查） |
| 憑證不得含 `$` | **不觸發**（`render-env.sh` 未動） |

## 六、`tcms-test-cases` 的前置提醒（blocking，但不在本站）

`project.md ## Mandated` 逐字要求每個 intent 的 construction 必經
`tcms-test-cases` stage 並完成四項產出，**未完成不得標示該 stage 為完成，
亦不得進入部署階段**。本站只記下這個前置與本單元的分桶**預判**，不代該 stage 產出：

| 桶 | 本單元的項目 |
|---|---|
| 待自動化 | §四 的第 1–8 項全部（八項都有可執行的落點與二元判準） |
| 只能手動 | **本站預判為 0 項**，但這個判定屬 `tcms-test-cases`。候選是「回填腳本在既有環境的實際執行」——它需要一個有既有資料的真實環境，CI 沒有 |
| 已自動化 | 0（本單元尚未實作） |

**該 stage 至今未對本 intent 的任何單元執行過**，而它是 blocking。
這一句不是本站的義務，是本站不該讓它繼續隱形。
