# Unit Test Instructions

```bash
cd backend && python -m unittest discover -s tests -v
```

**實測結果：140 個測試通過**（本 intent 之前為 94，新增 46）。

## 本 intent 新增的三支測試檔

| 檔案 | 測試數 | 涵蓋 | 測試底線 |
|---|---|---|---|
| `tests/test_activity.py` | 19 | 兩個時間判定的邊界與性質（含 **4 個 property-based**）、記錄器的提交契約與節流行為 | ADR-0006 的 property-based hard constraint 在本 intent 的落點 |
| `tests/test_user_list_endpoint.py` | 17 | **本 repo 第一支 `TestClient` 測試**。回應欄位集合（雙向相等）、欄位**值**、時區位移、分頁三值、切頁、超出範圍、七種非法參數、非分頁參數、兩個更新端點 | team-practices **底線 B** |
| `tests/test_j3a_view_permission.py` | 10 | 授權 allow/deny **雙向** ＋ 啟動補丁的四個分支 | team-practices **底線 A** |

## 一項既有基礎設施的修改

`tests/helpers.py` 改用 `StaticPool`：預設的 `SingletonThreadPool` 讓每個執行緒拿到**各自的空** in-memory 資料庫，而 `TestClient` 在另一個執行緒裡跑 app —— 沒有這個改動，端點測試會看到 `no such table: users`。既有 94 個測試不受影響（已複跑確認）。

## 誠實揭露：仍然沒有自動化涵蓋的部分

| 缺口 | 承接方式 |
|---|---|
| C-2 的「失敗先復原」分支 | 需注入資料庫失敗；未做。部署後人工核對 |
| C-3 補欄與 C-7 權限套用的**真實啟動流程**整合 | 測試以強制模式直接建表、從不呼叫 `init_db()`。**但補丁函式本身現在有測試**（4 個分支），且兩者皆已在真實 docker stack 上人工核對過 |
| 前端邏輯 | 本專案**無** unit／component 測試框架（team-practices 明確不採納引入）。前端的唯一自動化層是 e2e |
