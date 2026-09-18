# Code Summary — security-reviewer-permission（U4）

## 實際產出

| 檔案 | 變更 |
|---|---|
| `backend/services/rbac_seed_data.py` | `+3／-1`：`('Security_Reviewer','J3a', True, False, False)` |
| `schema_rbac.sql` | 對應 seed 改為 `true` |
| `backend/database.py` | `_apply_security_reviewer_j3a_view()` ＋ `J3A_PATCH_MARKER` 常數 |
| `DEPLOY.md` | 2.2.5 節：既有環境如何生效、psql 驗證指令、三態日誌的核對指示 |
| `backend/tests/test_j3a_view_permission.py` | **新增 172 行 / 10 個測試** |

## 實作中發現的、設計未預見的分支

**`schema_rbac.sql` 的 `INSERT` 不含 `updated_by`，故真實 staging 的該欄為 `NULL`。**

原實作的「尚未被人工調整」只認 `"system_seed"`（`ensure_role_permissions_seeded()` 寫入的值），會把 `NULL` 誤判為人工調整，**在最需要它的環境靜默失敗** —— 也就是所有由 `schema_rbac.sql` 建立的資料庫，包含 staging。

已改為把 `NULL`／空字串／`system_seed`／本補丁識別字四者都視為「尚未被人工調整」，並以 `test_applies_when_row_came_from_the_sql_seed` 釘住。

**這個分支是在真實 docker stack 上實跑時發現的，不是讀程式碼看出來的** —— 第一次啟動時日誌報「已跳過（已為可檢視）」，把值改回 `false` 重啟後才露出誤判。

## 補上的自動化：先前明文記載為「無自動化驗證」的路徑

reviewer 在 doc-vs-code 比對時查出補丁未遵守 R4 的四態契約（第三態被寫成常態 `info`、且從不寫入補丁識別字）。修正後**一併補上 `J3aStartupPatchTest` 四個 case**，涵蓋四個分支 —— 其中「已被管理員異動」正是 R2 的死角。

這**縮小**了設計記載的缺口（補丁函式本身現在有測試），但**沒有消除**它：真實啟動流程的整合仍需部署後人工核對日誌。文件已據實更新，未宣稱缺口已關閉。

## 驗證結果

| 項目 | 結果 |
|---|---|
| 10 個權限測試 | 通過（allow 1、deny 5、補丁四態 4） |
| 真實 PostgreSQL stack | 把 `can_view` 改回 `false` 重啟 → 日誌 `已套用`、資料庫值變 `t`。**套用路徑實際驗證過** |
| 部署後人工核對指示 | 已寫入 `DEPLOY.md` 2.2.5 |
