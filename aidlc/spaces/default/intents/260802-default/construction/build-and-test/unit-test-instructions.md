# Unit Test Execution


### 現況

單元測試位於 `backend/tests/`，以 SQLite in-memory 為主（不需 PostgreSQL）；`psycopg2` 在 `helpers.py` 內 mock。涵蓋：

| 檔案 | 範圍 | 類型 |
|---|---|---|
| `test_rbac.py` | normalize／seed／user_can／arch 同步 | example |
| `test_auth.py` | bcrypt、JWT、`get_current_user` | example + PBT |
| `test_collab.py` | 分享 ACL、chat | example + PBT |
| `test_design_agent.py` | system／user prompt | example + PBT |
| `test_diagram_builder.py` | geometry／XML | example + PBT |
| `test_j5_authz.py` | Pending 閘門、核准、catalog | example |
| `test_wa_rule_engine.py` | **A3** 規則加權／扣分／同 XML 不變性 | example + **Hypothesis PBT** |
| `test_review_authz.py` | **A3** A3 RBAC、diagram ACL、DTO | example |

相依：`hypothesis`（`backend/requirements.txt`）。

### 執行

```bash
cd backend
pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

### 預期結果（2026-07-23 實測）

- `Ran 61 tests ... OK`（0 failures）  
- 含 U-A3：`test_wa_rule_engine`、`test_review_authz`

### 測試失敗時

1. 讀 unittest 輸出定位失敗案例  
2. 對照對應 `services/*.py` 修正  
3. 重跑至全綠

### 仍待擴充

| 範圍 | 狀態 |
|---|---|
| FastAPI TestClient（reviews SSE HTTP） | ❌ 見 integration 手動場景 |
| frontend 單元測試 | ❌ 無 test runner（CI：lint + tsc build） |
