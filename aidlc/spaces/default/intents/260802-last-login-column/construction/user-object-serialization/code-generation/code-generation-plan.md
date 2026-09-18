# Code Generation Plan — user-object-serialization（U2）

> Unit: `user-object-serialization`（C-4 ＋ C-9 後端）· 上游：本單元的 `../functional-design/business-rules.md`（BR-P1〜P5）、`../functional-design/domain-entities.md`（`UserListPage`）、`../nfr-requirements/*`、AD-10／AD-11。

## 落點

全部在 `backend/services/user_router.py` 單一檔案內（本單元不新建模組 —— `user_router.py` 已是 831 LOC 且無 service 層，`team.md ## Code Style` 明訂「修改 `user_router.py` 就地沿用既有形狀，不趁機夾帶 service 層抽取」）。

| 項目 | 形式 |
|---|---|
| `UserSchema` 兩個新欄位 | 加在既有 model 上，**無預設值** |
| `UserListPage` | 新的 response model，四欄**無預設值** |
| 每頁筆數常數 | 模組層 `DEFAULT_PAGE_SIZE = 20`、`MAX_PAGE_SIZE = 100` |
| `_to_user_schema()` | 新的私有工廠，三個構造點共用 |
| 清單端點 | 加兩個查詢參數（框架原生範圍約束）、改回應模型、加計數查詢與 offset/limit |

## 測試計畫

`tests/test_user_list_endpoint.py`（**本 repo 第一支 TestClient 測試**，故一併建立可重用的 fixture 樣板）：以 `app.dependency_overrides` 覆寫 `get_db` 與 `get_current_user`；`TestClient(app)` 不觸發 `@app.on_event("startup")` 的 `init_db()`，故不需要真實資料庫。

涵蓋：欄位集合**相等**（雙向）、欄位**值**與資料庫一致、時區位移、分頁三值（含「總數少於一頁」的分辨情境）、切頁不重複、順序穩定、超出範圍、七種非法參數、非分頁參數不改變結果、兩個更新端點的回應形狀。
