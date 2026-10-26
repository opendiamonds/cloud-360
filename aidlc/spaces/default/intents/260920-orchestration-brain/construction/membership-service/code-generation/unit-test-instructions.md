# 單元測試指示 — `U19 membership-service`

> Testing Contract 解析為 **`methodology: test-after`**、**`test_strategy: standard`**
> （每元件 5–8 個測試 ＋ 關鍵邊界的整合測試），scope floor 為
> 「既有測試套件維持綠燈、不另加新測試底線」。兩者皆為義務，互不取代。
>
> 本檔的每一條指令都**只跑本單元的測試**。`Build and Test` 會對每個單元各跑一次
> 它的指令，故一條 `python -m unittest discover` 這樣的全套命令會把整個套件
> 重跑 24 遍。

## 一、測試框架：沿用既有，零新依賴

| 項目 | 值 |
|---|---|
| 後端框架 | Python 內建 `unittest` ＋ `hypothesis` ＋ `unittest.mock`。**不是 pytest** |
| HTTP 層 | `starlette.testclient.TestClient`（`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，前置條件已滿足） |
| 預設 DB | in-memory SQLite（`backend/tests/helpers.py` 的 `make_session()`） |
| **真實 PostgreSQL** | 僅 `backend/tests_pg/`，由新 `concurrency` CI job 提供 service container |
| 前端 | **本單元無前端面**（成員頁是 `U24`；實測 `frontend/src` 對 `projects` 命中數為 0），故無 Playwright 指令 |

### 1.1 每個測試檔的第一件事

在匯入**任何**應用模組之前先匯入 `tests.helpers`：

```python
import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub
```

它做兩件事：把 `backend/` 與 `backend/services/` 插進 `sys.path`（**任何環境都必要**），
以及在 `psycopg` **未安裝時**才裝 stub（`helpers.py:19` 的
`if importlib.util.find_spec("psycopg") is None`——CI 裝了它，故 CI 只走
`sys.path` 那一半）。51 個既有測試檔中有 29 個這麼做，分三種寫法
（`import tests.helpers` 10 個、`from tests.helpers import ...` 20 個、
`from tests import helpers` 2 個；三者都會執行該模組的 module-level 副作用）。

## 二、執行指令（本單元專屬，複製即可跑）

### 2.1 既有測試路徑（SQLite／mock；`backend` CI job 會跑到）

```bash
cd backend
python -m unittest -v \
  tests.test_membership_data \
  tests.test_membership_facade \
  tests.test_membership_endpoints
```

### 2.2 真實 PostgreSQL 路徑（新 `concurrency` CI job）

```bash
cd backend
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cloud360 \
  python -m unittest -v tests_pg.test_membership_concurrency
```

**前置條件**：一個**真實的** PostgreSQL（含 `pgvector`，因為 `schema_rbac.sql`
的第一條敘述是 `CREATE EXTENSION vector`）且已套用 `schema_rbac.sql`。
本機建法見 `LOCAL-DEV.md` 第 2 節。

**`DATABASE_URL` 必須顯式帶 `+psycopg` 後綴**——裸 `postgresql://` 會回頭依賴
SQLAlchemy 的隱含預設，而該預設在 2.1 由 `psycopg2` 改為 `psycopg`。
**測試讀不到 `DATABASE_URL` 時必須大聲失敗，不得退回 SQLite 預設**：
退回 SQLite 會讓整個 job 綠燈而鎖從未存在。

### 2.3 為什麼是兩條指令而不是一條

`with_for_update()` 在 SQLAlchemy 2.1.1 的 SQLite dialect 下**被靜默丟棄**
（編譯出的 SQL 是 `SELECT p.id, p.name FROM p WHERE p.id = ?`，無鎖子句、
無錯誤、無警告）。故併發守門的測試在既有路徑上會在**完全沒有鎖**的情況下通過。
隔離是**結構性**的：`backend/tests_pg/` 不被 `discover -s tests` 看到，
所以不需要任何 env guard，也沒有東西可以忘記設。

**新增真實 PG 測試時放 `backend/tests_pg/`，不要放回 `backend/tests/`**
——後者會在 `backend` job 連線失敗（該 job 無 PostgreSQL service，
其測試步驟只設 `JWT_SECRET`）。

## 三、測試檔與測試數（standard：每元件 5–8 個）

| 檔案 | 元件 | 測試數 | 覆蓋什麼 |
|---|---|---|---|
| `backend/tests/test_membership_data.py` | 資料模型 ＋ 資料存取 | **8** | ORM↔DDL 欄位名一致（含 `cause`）；`ReselectionEvent.__table__.foreign_keys` 為空；約束與索引名稱集合相等；`ix_reselection_events_unack` 帶 `where`；`resolve_project_role` 查得／查無（`None`）；`list_members` 的欄位集合；**聚合查詢 ↔ 逐專案判定的等價測試**（`NFR12.12`） |
| `backend/tests/test_membership_facade.py` | 業務邏輯 ＋ 純函式 ＋ 稽核 | **8** | **`select_successor` 的排列不變性（PBT，`@given`，blocking）**；守門三條路徑各自命中與放行；`invite_member` 非冪等；`remove_member` 冪等；**指定第二位管理者後兩位都能執行管理動作**；稽核列五個事實齊備 ＋ `cause` 正確；`previous_owner_user_id` 在兩種 `cause` 下的語意；**人工角色變更不得產生橫幅**（`BR5.5` 的 `cause` 過濾）；自動改選冪等 |
| `backend/tests/test_membership_endpoints.py` | API／端點 | **7** | allow/deny 雙向（2xx／403）；新端點的 status code ＋ `response_model` 欄位集合；停用端點 409 的狀態碼 ＋ `LastAdminGuardReport` 欄位集合（含專案名稱）；既有自我停用守門仍生效；既有「最後一位可編輯角色的全域管理員」守門仍生效；新守門在 `is_active` 寫入**之前**；`create_project_with_owner` 成功後必然存在建立者的成員列 |
| `backend/tests_pg/test_membership_concurrency.py` | 併發（真實 PG） | **3** | `FOR UPDATE` 真的存在（兩個並行交易被序列化、守門不被繞過）；不同專案不互相阻塞（`NFR12.13`）；`assert_can_deactivate` 不取鎖（`NFR12.3`） |

合計 **26** 個測試，分佈符合 standard 的「每元件 5–8」（併發那一檔是 3，
因為它只有三個斷言面，而硬湊到 5 個會製造恆真測試）。

### 3.1 合併前必修第 1、4、10、15、16 項（Request Changes 修訂，計畫 Step 15）

新增測試落在既有三支檔與 `tests_pg/`（超出每元件 5–8 的部分是必修項的回歸測試，`scope_floor` 允許為特定缺陷加最窄的測試）：

| 項 | 檔案 | 案例（通過條件） |
|---|---|---|
| #1＋#4 | `test_membership_facade.py` | 最後一位管理者停用、有合格接手人 → 守門放行，接手人成為 `project_admin` 並寫一筆 `auto_reselection` 事件；無合格接手人 → `LastAdminGuard`；候選中待核准／停用／只有 `K3.view` 的成員一律不被選中；非擁有但為最後管理者的專案也被改選 |
| #4 | `test_membership_endpoints.py` | 邀請已停用帳號 → 拒；邀請待核准帳號 → 拒（皆不寫成員列） |
| #10 | `test_membership_endpoints.py` | 注入單一專案改選失敗 → 停用端點 500，本體列出該專案 id；其他專案已改選；重送停用 → 補跑成功，且已成功的專案不產生第二筆事件 |
| #15 | `test_membership_data.py` | 補齊函式：無成員列的專案 → 擁有者成為 `project_admin`；重跑不重複；終檢失敗拋出 |
| #16 | `test_membership_facade.py` | PostgreSQL dialect 下取鎖前送出 `SET LOCAL lock_timeout`（mock 連線記錄 SQL）；SQLite 下不送；`MembershipLockTimeout` → 端點 503 |
| #16 | `tests_pg/test_membership_concurrency.py` | 一個交易持鎖時，第二個交易約 5 秒後得到 `MembershipLockTimeout`（真實 PG，CI 的 `concurrency` job） |

突變（每項先 `grep` 確認突變已寫入，還原後確認為 0）：合格謂詞拿掉 `is_active`／`approved`／`K3.edit` 任一條件 → 對應案例紅；拿掉失敗回報 → #10 案例紅；拿掉「無成員列」條件 → #15 重複案例紅；拿掉 `SET LOCAL lock_timeout` → #16 mock 案例紅。

完整套件一律以 `backend/.venv` 執行：`cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests`（本機系統 Python 的套件版本與 `requirements.txt` 不一致）。`tests_pg/` 需真實 PostgreSQL，本機無 Docker 時以 CI 結果為準並據實記為本輪未驗。

## 四、Mock／stub 指引

| 對象 | 做法 |
|---|---|
| DB session | `backend/tests/helpers.py` 的 `make_session()`（in-memory SQLite ＋ `StaticPool`）。`tests_pg/` **不用它**——它要真實連線 |
| `get_db` | `app.dependency_overrides[get_db]`（`database.py:31`，穩定的模組層函式） |
| `get_current_user` | `app.dependency_overrides[get_current_user]`（`services/auth.py:39`） |
| 啟動副作用 | 以 `TestClient(app)` 直接使用**不觸發** `@app.on_event("startup")` 的 `init_db()`，故不需要真實 DB |
| 外部呼叫 | **本單元零外部依賴邊界**（無 LLM、無 webhook、無 HTTP 出口），故沒有要 mock 的外部服務 |
| 時間 | `joined_at` 的 tie-break 測試需要**相同**的時間戳，直接以固定 `datetime` 建構 `MemberSnapshot`，不要依賴 `now()` |

## 五、測試資料管理

- 角色權限種子：`ensure_role_permissions_seeded(db, force=True)`（`make_session()` 已做）。
- **本單元的 `role_permissions` seed 未變更**，但 `K3`／`K4` 的 story id 需存在；若不存在則屬 `U3 rbac-story-ids` 範圍，不在本單元補。
- 每個測試自行建立所需的 `projects` 與 `project_members` 列；**不共用跨測試的狀態**。
- `tests_pg/` 的併發測試：每個測試自建專案與成員，結束時清理自己建的列（真實 DB 不會每次重建）。

## 六、覆蓋率目標

`org.md` 宣告 `feature` scope 的最低 **80% line coverage**。如實記載現況：
本 repo **沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、
CI 無 coverage step），故該數字目前**既無法量測也無法強制**。
本檔**不弱化那個宣稱**，而以 `team.md` 的 A／B／C 三項規則作為本單元
實際可判的門檻（見 `code-generation-plan.md §四`）。

## 七、突變驗證（每支腳本都必須做，結果寫進 `code-summary.md`）

| 測試 | 突變 | 必須變成 |
|---|---|---|
| `select_successor` 的 PBT | tie-break 改成只按 `joined_at`（移除 `user_id`） | **紅燈** |
| 併發守門（`tests_pg`） | 移除 `with_for_update()` | **紅燈** |
| 停用端點的 409 | 把 `assert_can_deactivate` 的呼叫移到 `is_active` 寫入**之後** | **紅燈** |
| 橫幅的 `cause` 過濾 | 移除 `cause = 'auto_reselection'` 條件 | **紅燈** |
| ORM↔DDL 一致性 | 在 `ReselectionEvent.project_id` 加上 `ForeignKey` | **紅燈** |

**突變驗證的意義在於證明測試碰得到真實的失敗面。** 一個無論實作對錯都通過的
測試不是測試——`construction.md` 逐字禁止它（「Do not generate tests that always
pass regardless of implementation」）。
