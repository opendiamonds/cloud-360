# 可靠性設計 — `U20 requirement-field-service`

## 〇、本單元沒有的模式（附理由）

| 不採用 | 理由 |
|---|---|
| 熔斷器、重試退避 | 沒有外部呼叫；依賴只有同進程的兩個 facade 與同一個 PostgreSQL |
| 降級回應（例如資料庫失敗時回空清單） | 回空清單會被畫面讀成「全部未填」，與真實狀態無法區分——失敗必須是失敗（`NFR20.26`） |
| 健康檢查端點 | 沿用既有後端的健康檢查；本單元無獨立進程 |

## 一、交易邊界（`NFR20.19`／`NFR20.20`）

- 每個寫入或清空請求使用一個 session、一個交易；授權與驗證在交易內**任何寫入之前**完成。
- 寫入與清空都是**單一敘述**（`performance-design.md` 第二節），交易內只有一次寫入，
  故不存在「寫了一半」的中間狀態；失敗即回滾。
- 測試：以 mock 讓 commit 拋錯，之後用**另一個 session** 重讀該欄，值與 `filledState`
  不變（同一個 session 會看到自己未提交的變更，驗不出回滾）。

## 二、冪等與併發清空（`NFR20.21`／`NFR20.22`，承 `review-01` R-08）

- 寫入：upsert 天然冪等。
- 清空：**單一條件式 `UPDATE`**（`WHERE … AND value IS NOT NULL`），取代上一站描述的
  「先讀該列再決定」。先讀後改在兩個併發清空下會兩者都讀到 `filled`、都寫入，使
  `cleared_at`／`updated_by` 被第二者覆蓋，違反 `BR43.4`；條件式 `UPDATE` 讓第二者在
  重新評估條件時得到 0 列。0 列時再讀一次現況作為回傳（no-op）。
- `BR43.3`（從未填過）與 `BR44.1` 的第四種列（有列而 `value`、`cleared_at` 皆為 null）在
  條件式 `UPDATE` 下同樣得到 0 列，自然成為 no-op，不需另寫分支。

## 三、資料表收斂的設計（`NFR20.23`–`NFR20.25`，承 functional-design `review-02` R-01／R-02 與 `review-01` R-04）

### 收斂敘述（寫在 `schema_rbac.sql` 的 `J)` 區塊，`run_meta_schema_migration.py` 直接執行它）

以一個 `DO $$ … $$` 區塊表達，邏輯為：

1. 查 `information_schema.columns`：`updated_on_behalf_of` 的 `data_type` 是否為 `integer`。
   **只有是**，才執行步驟 2–3。
2. 查 `pg_constraint`：該表上**參照 `users`、且只涵蓋 `updated_on_behalf_of` 這一欄**的外鍵
   名稱（以欄位比對 `conkey`，不寫死自動產生的名稱，也不會誤刪 `updated_by` 的外鍵）；
   存在才 `DROP CONSTRAINT`。
3. `ALTER COLUMN updated_on_behalf_of TYPE VARCHAR(64) USING NULL`，並重寫該欄 COMMENT。

已收斂的資料庫上，步驟 1 判定為否，整段不做任何事——**第二次執行不改動任何資料**，也不取
`ACCESS EXCLUSIVE` 鎖。

### 驗證：在真實 PostgreSQL 上走「舊定義 → 收斂 → 重跑」

落點為 CI 既有的 `memory-schema` job（`ci.yml:308`，已有 `pgvector/pgvector:pg18` 服務容器、
已套用 `schema_rbac.sql` 兩次）。新增步驟：

| 步驟 | 動作 | 斷言 |
|---|---|---|
| A | 新腳本把欄位改回舊定義（integer ＋ 指向 `users` 的外鍵），模擬「U18 先上線」的資料庫 | — |
| B | 再套用一次 `schema_rbac.sql` | 型別為 `character varying`、該欄無外鍵、`updated_by` 的外鍵仍在 |
| C | 插入一列 `updated_on_behalf_of = 'cost'` | — |
| D | 再套用一次 `schema_rbac.sql` | 該列的值仍為 `'cost'`（重跑不清資料） |

另：`verify_meta_schema.sql` 增加欄位級斷言（型別、該欄無外鍵）；
`run_meta_schema_migration.py` 的後條件同樣增加欄位級檢查，不符即非零結束碼（`NFR20.25`）。
**不使用**既有的 `FORBIDDEN_FKS`——它以（表、被參照表）為鍵，會把合法的 `updated_by` 外鍵一起擋掉。

`DEPLOY.md` 2.2.9 註明：直接 `psql -f schema_rbac.sql` 的路徑沒有後條件檢查，既有環境請走
`run_meta_schema_migration.py`。

### CASCADE 的驗證（`NFR20.16`）

在同一個 `memory-schema` job 的 `verify_meta_schema.sql` 以真實 PostgreSQL 驗；不在 SQLite 單元
測試宣稱它成立（`helpers.py` 未開 `PRAGMA foreign_keys`）。

## 四、依賴失敗（`NFR20.11`／`NFR20.26`，承 `review-01` R-03）

- 測試形狀：`TestClient(app, raise_server_exceptions=False)`，否則 TestClient 會把伺服器例外
  直接重拋到測試，看不到 500 回應。
- 案例：mock `resolve_project_role` 拋非預期例外 → 回應 500、無任何寫入、回應本體不含
  `unfilledCount`；mock 資料查詢拋錯 → 同上。
