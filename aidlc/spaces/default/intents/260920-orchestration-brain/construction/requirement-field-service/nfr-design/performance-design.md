# 效能設計 — `U20 requirement-field-service`

## 〇、設計原則

本單元的效能需求全部是**查詢次數**（`NFR20.1`–`NFR20.5`），不是延遲數字。設計的目標是
讓每個請求的資料庫往返數為常數，且以單一敘述完成每次寫入。不加快取（`NFR20.6`）。

## 一、讀取：一次查詢、記憶體內合成

```
read_fields(principal, system_id):
  authorize(...)                                   # 常數次查詢（第三節）
  rows = SELECT * FROM system_requirement_fields WHERE system_id = :sid   # 恰一次
  by_key = {(r.agent_group, r.field_key): r for r in rows}
  for group in DEFINITIONS (依 displayOrder):
      for field in group.fields:  合成 FieldView（無列 → never_filled）
  計算各組 filledCount／totalCount 與 unfilledCount（同一份明細）
```

- **`NFR20.1`**：資料查詢以 `WHERE system_id = ?` 一次取出該系統全部列，命中 `U18` 的
  `uq_system_requirement_fields_group_key` 前導欄，不需新索引。定義外的保留列在記憶體中
  被忽略（`BR44.3`），**不在 SQL 層過濾**——在 SQL 層用 `IN (定義清單)` 過濾會讓查詢
  形狀隨定義變動，且不減少往返次數。
- **`NFR20.3`**：router 只有一個 GET 操作；計數與明細在同一個回應物件。

## 二、寫入與清空：單一敘述＋`RETURNING`

| 操作 | 敘述 | 往返 |
|---|---|---|
| `write_field`（非空值） | `INSERT … ON CONFLICT (system_id, agent_group, field_key) DO UPDATE SET value, cleared_at = NULL, updated_at, updated_by, updated_on_behalf_of RETURNING *` | **1** |
| `clear_field`（含使用者的空值寫入，`BR43.2`） | `UPDATE … SET value = NULL, cleared_at = now(), updated_at = now(), updated_by, updated_on_behalf_of = NULL WHERE system_id = ? AND agent_group = ? AND field_key = ? AND value IS NOT NULL RETURNING *` | **1**；若 0 列被更新（no-op），再 1 次 `SELECT` 取現況以回傳 |

- **`NFR20.4` 的判準更正**（承 `nfr-requirements` 審查 `review-01` R-02）：upsert 是**一個**
  敘述，不是「INSERT 與 UPDATE 各一次」；計數器的判準為「對該表的寫入敘述恰為 1，且寫入
  路徑無對該表的 `SELECT`」。回應所需的列內容由 `RETURNING` 取得，不另查。
- **`NFR20.5`**：寫入回應只含單一 `FieldView`，不重算計數；清空路徑在 no-op 時允許 1 次
  `SELECT`，這是 `BR43.3`／`BR43.4` 需要回傳現況的必要成本。
- **`RETURNING` 的前提**：PostgreSQL 原生支援；測試走的 SQLite 需 ≥ 3.35（本機實測
  3.50.4）。code-generation 加一條守衛測試，在 SQLite 版本不足時以明確訊息失敗，而不是
  讓 upsert 測試以難懂的語法錯誤失敗。
- **依連線方言產生敘述**（`NFR20.31`）：`sqlalchemy.dialects.postgresql.insert` 與
  `sqlalchemy.dialects.sqlite.insert` 皆提供 `on_conflict_do_update` 與 `returning`；
  依 `session.bind.dialect.name` 選擇。

## 三、授權前段的查詢數為常數

| 步驟 | 查詢 |
|---|---|
| `BR41.1` 待核准 | 0（`Principal.is_approved` 由 `mint_principal` 已填） |
| `BR41.2` 全域 `K4` | 1（`user_can` 讀 `role_permissions`） |
| `BR41.3` 系統→專案 | `HierarchyFacade.get_project_of_system` 內含 `K2.view` 檢查與一次查詢 |
| `BR41.4` per-project 角色 | `MembershipFacade.resolve_project_role` 內含專案存在檢查與一次查詢 |

**計數器**（`NFR20.32`）：測試以 SQLAlchemy 的 `before_cursor_execute` 事件掛在測試 engine
上，記錄每條敘述與其目標表名；`NFR20.1`／`NFR20.2`／`NFR20.4`／`NFR20.5`／`NFR20.7` 都用
同一個計數器判定，不另造量測方式。

**不逐欄授權**：授權結論對整個系統成立，判一次即可。`NFR20.2` 的判準是「0 列與 7 列
兩種資料下總查詢數相等」，而非某個固定數字——後者會在上游 facade 調整內部查詢時誤報。

## 四、不加快取（`NFR20.6`）

理由見 `performance-requirements.md` 第三節。本設計不引入任何 `lru_cache`、模組層 dict
或 Redis 讀取。
