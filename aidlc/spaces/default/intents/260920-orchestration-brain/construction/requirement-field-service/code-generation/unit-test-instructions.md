# Unit Test Instructions — `U20 requirement-field-service`

## 一、框架與設定

- 後端：Python 內建 `unittest` ＋ `unittest.mock` ＋ `starlette.testclient.TestClient`，**不是 pytest**；不使用 `hypothesis`（PBT 不適用，`security-requirements.md` 第六節）。
- 測試資料庫：`backend/tests/helpers.py` 的 in-memory SQLite（`StaticPool`），每個測試自建資料。
- 真實 PostgreSQL：`backend/tests_pg/`，以 `DATABASE_URL`（`postgresql+psycopg://…`）連線；缺值時**大聲失敗**（`require_pg_url`），不退回 SQLite。
- 前端：本單元無前端程式，不跑 Playwright。

## 二、本單元的執行指令（皆限定本單元的檔案）

在 `backend/` 目錄：

```bash
# 測試執行器就緒檢查（Step 2；檔案尚不存在前先以既有兄弟檔確認可載入）
python3 -m unittest tests.test_membership_data -v

# 本單元的 SQLite 測試（Step 4／6／8／10）
python3 -m unittest tests.test_requirement_field_data tests.test_requirement_field_service tests.test_requirement_field_facade tests.test_requirement_field_http -v

# 本單元的 PostgreSQL 測試（Step 6；需 DATABASE_URL 指向真實 PostgreSQL，CI 的 concurrency job 執行）
python3 -m unittest tests_pg.test_requirement_field_pg -v

# OpenAPI 漂移檢查（Step 10）
python3 scripts/dump_openapi.py --check
```

在 `frontend/` 目錄（只驗型別檔已同步，不跑 e2e）：

```bash
npm run check:types
```

資料表收斂與 CASCADE（Step 3／4）只在 CI 的 `memory-schema` job 上驗證（真實 PostgreSQL、步驟 0／A–E）。

## 三、測試清單與數量（standard：每元件 5–8 個）

| 檔案 | 元件 | 案例 |
|---|---|---|
| `test_requirement_field_data.py` | ORM 模型 | ① ORM 欄位集合等於 `schema_rbac.sql` `J)` 區塊的該表欄位 ② 可空性一致（`value`、`cleared_at`、`updated_on_behalf_of` 可空；`updated_by` 不可空）③ `updated_on_behalf_of` 為長度 64 的字串、無外鍵 ④ 三欄唯一鍵存在 ⑤ CHECK 擋下「有值且已清空」 |
| `test_requirement_field_service.py` | 資料存取 | ① 同欄重複寫入列數為 1 ② 列已存在時呼叫首寫路徑不拋 `IntegrityError` ③ 清空從未填過為 no-op 且不建列 ④ 清空已清空為 no-op、`cleared_at` 不變（注入固定時鐘）⑤ 清空第四種列為 no-op ⑥ 讀取對該表恰 1 次 SELECT（0 列與 8 列兩種資料）⑦ 寫入路徑對該表 0 次 SELECT ⑧ SQLite 版本 ≥ 3.35 守衛 |
| `test_requirement_field_pg.py` | 資料存取（PostgreSQL） | ① PG 方言 upsert 正確 ② 條件式清空正確 ③ 兩個併發清空只生效一次（barrier 釘住順序，不用 `sleep`） |
| `test_requirement_field_facade.py` | 業務邏輯 | ① 三態推導與第四種列回 null 溯源 ② `unfilledCount` 與各組計數由同一份明細推導 ③ 定義外保留列不顯示、不計數 ④ 使用者空值寫入即清空 ⑤ 代寫路徑空值寫入被拒 ⑥ 錯綁別組、未宣告代寫組、超長值被拒 ⑦ 同進程呼叫的待核准與全域層拒絕 ⑧ 拒絕 log 欄位正確且所有 log 不含值；no-op 不記 INFO；依賴非預期例外不放行；回滾後值不變 |
| `test_requirement_field_http.py` | API | 十二列 allow／deny 矩陣（`code-generation-plan.md` §二）；回應欄位集合；四類 422 不回顯唯一標記字串（含本體帶 `updated_by`）；非整數 `system_id` → 404；`raise_server_exceptions=False` 下依賴失敗回 500 且無寫入 |

## 四、突變驗證（每項：套用 → 確認紅 → 還原 → 確認綠）

| 突變 | 預期紅燈 |
|---|---|
| 拿掉 per-project 成員判定 | 「非成員有 `K4.edit` 寫入」列 |
| 拿掉全域 `K4.edit` 檢查 | 「只有 view 的成員寫入」列、代寫標示列 |
| 拿掉待核准檢查 | 待核准列（HTTP 與同進程） |
| 清空改回「先讀後改」 | PostgreSQL 併發清空案例 |
| 收斂 `DO` 區塊改為無條件轉型 | CI `memory-schema` 步驟 D（重跑後值被清） |
| log 改為帶入值 | 「log 不含值」案例 |

結果記入 `code-summary.md`。

## 五、覆蓋率

repo 無覆蓋率量測機制（`team.md`）；以上列每個元件 5–8 個案例與突變驗證作為實際門檻，不宣稱百分比。

## 六、Mock 與測試資料

- 身分：`app.dependency_overrides[get_current_user]` 回傳測試建立的 `User`；`get_db` 覆寫為測試 session。
- 角色：直接寫 `users.role`；權限矩陣由 `ensure_role_permissions_seeded(db, force=True)` 播種，**不 mock `user_can`**——真實的授權路徑必須被執行。
- 專案與成員：以 `MembershipFacade.create_project_with_owner` 與 `invite_member` 建立，不直接插 `project_members` 列（避免繞過 `U19` 的不變量）。
- 時間：寫入與清空的時間戳由呼叫端傳入，測試注入固定值。
- 唯一標記字串：每個 422 與 log 案例使用 `uuid4()` 產生的值，斷言回應與 log 不含它。
