# Build & Test Results

> 全部為**實際執行**的結果，於 2026-08-11 在本機環境取得。

## 摘要

| 項目 | 結果 | 本 intent 之前 |
|---|---|---|
| Backend 單元測試 | **140 通過**（0 失敗） | 94 |
| Playwright e2e | **14 通過**（0 失敗） | 6（其中 1 個實際已失效） |
| Frontend lint | **0 errors**、3 warnings | 0 errors、3 warnings（未新增） |
| Frontend `tsc -b` ＋ build | 通過 | 通過 |
| Backend import smoke | 通過 | 通過 |
| OpenAPI 規格漂移 gate | 一致（exit 0） | （新增） |
| 前端型別漂移 gate | 一致（exit 0） | （新增） |
| 規格不得被靜態供出 | 通過 | （新增） |
| `validate_repo_contract.py` | **通過** | 通過 |

## 三道新 gate 的有效性實測

不刻意弄壞一次，就無從得知自我驗證的機制是否真的會失敗：

| Gate | 刻意違反的方式 | 結果 |
|---|---|---|
| OpenAPI 規格漂移 | 改 `openapi.json` 中一個欄位名 | **exit 1**，訊息指出該跑 `python scripts/dump_openapi.py` |
| 前端型別漂移 | 改 `api.d.ts` 中一個欄位名 | **exit 1**，訊息指出該跑 `npm run gen:types` |
| 規格不得被靜態供出 | 把 `openapi.json` 複製進 `dist/` | **命中並 exit 1** |

三者移除違反後皆回到 exit 0。

## 在真實 PostgreSQL stack 上的驗證（設計記載為「無自動化驗證」的部分）

| 項目 | 方法 | 結果 |
|---|---|---|
| C-3 既有環境補欄 | `psql -c "\d users" \| grep last_activity_at` | `last_activity_at \| timestamp with time zone` **存在** |
| C-7 權限套用 | 把 `can_view` 改回 `false` 後重啟後端 | 日誌 `J3a 權限套用：已套用`；資料庫值變 `t` |
| 補丁的四態日誌 | 觀察兩次啟動 | 首次 `已跳過（已為可檢視）`、改回 false 後 `已套用` |
| 回應的時區位移 | `curl` 清單端點 | `"2026-08-11T02:35:27.483688Z"` —— **帶 `Z`** |

**這一輪實跑抓到一個讀程式碼看不出來的缺陷**：`schema_rbac.sql` 的 `INSERT` 不含 `updated_by`，故真實資料庫的該欄為 `NULL`；原實作只認 `"system_seed"`，會把 `NULL` 誤判為人工調整而**在所有由該腳本建立的環境（含 staging）靜默失敗**。已修正並以 `test_applies_when_row_came_from_the_sql_seed` 釘住。

## 逐條 AC 的驗證落點

36 條 AC 中，US-5 的 11 條為本輪新增。每一條的驗證者見各單元的 `../*/nfr-requirements/` 與 `../admin-page-column/functional-design/business-logic-model.md` 的驗證強度表。**四項誠實標記為無自動化驗證**：焦點可見、44x44 觸控尺寸、AC-5.11 的介面不存在子句、C-2 的失敗復原分支。

## 已知的環境差異

| 差異 | 影響 |
|---|---|
| 本機 Python 3.13，CI 為 3.12 | 兩者皆通過；規格輸出經上游實測在兩版本間位元相同 |
| 本機需 `npx playwright install chromium` | CI 的 gh-aw workflow 另行處理 |
| `ui-regression` 在 CI 上的首次執行 | **仍待 PR 觸發** —— 本輪的 14 個 case 是在本機的同構 stack 上跑的 |
