# Code Generation Plan — security-reviewer-permission（U4）

> Unit: `security-reviewer-permission`（C-7）· 上游：本單元的 `../functional-design/business-rules.md`（R1〜R4，含 R4 的**四態**記錄契約）、AD-7。

## 落點：兩處預設值來源 ＋ 一支啟動補丁

| 項目 | 檔案 |
|---|---|
| 預設值來源 1（後端種子） | `backend/services/rbac_seed_data.py` |
| 預設值來源 2（初始化腳本） | `schema_rbac.sql` |
| 既有環境的目標式套用 | `backend/database.py::_apply_security_reviewer_j3a_view()` |
| 部署文件 | `DEPLOY.md` 2.2.5 |

**兩處都改是 blocking**（requirements FR-4.3）：任一處未同步即視為未完成。

## 補丁的四項契約（缺一皆為嚴重後果）

1. **必須排在既有權限種子之後** —— 順序錯誤會讓 308 列預設矩陣不被建立。
2. **只更新不插入** —— 插入會在空表情境建立孤兒列，使後續 seed 因表非空而整份跳過，**全系統 RBAC 端點盡數拒絕存取，且沒有任何測試會發現**。
3. **條件式套用** —— 不覆蓋管理者在 Admin UI 上的人工調整。
4. **四態日誌**，且後兩態同級（皆 warning、皆需人工處置）。

## 測試計畫

`tests/test_j3a_view_permission.py`：allow/deny **雙向**（team-practices 底線 A）＋ 補丁函式的四個分支。

**已知缺口**：雙向測試涵蓋的是**種子預設值**，不涵蓋真實啟動流程的套用（測試以強制模式直接建矩陣、從不呼叫 `init_db()`）。承接方式為啟動日誌的三態記錄 ＋ 部署後人工核對。
