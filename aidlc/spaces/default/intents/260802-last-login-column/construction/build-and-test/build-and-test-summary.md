# Build and Test Summary

## 本階段做了什麼

把五個單元的實作放在一起建置、執行全部測試層，並**刻意弄壞每一道新 gate 一次**以確認它們真的會失敗。

## 結果：全綠

| 層 | 結果 |
|---|---|
| Backend 單元（含 4 個 property-based） | 140 / 140 |
| Playwright e2e（真實 docker stack） | 14 / 14 |
| Lint ／ typecheck ／ build | 0 errors |
| 三道新 CI gate | 皆通過，且皆已實測會在違反時 exit 1 |
| Repo contract | 通過 |

## 三項測試底線的達成

| 底線 | 觸發 | 落點 | 達成 |
|---|---|---|---|
| **A** 授權矩陣變更需 allow/deny 雙向測試 | C-7 的 `J3a` 開通 | `test_j3a_view_permission.py`（allow 1、deny 5） | ✅ |
| **B** 端點變更需 `TestClient` 測試 | C-4 的三個構造點 ＋ C-9 的 envelope／參數／422 | `test_user_list_endpoint.py`（17 個） | ✅ **本 repo 第一支** |
| **C** 前端資料形狀變更需 e2e 斷言 | C-5／C-6／C-9 前端 | `regression.spec.ts`（8 個新 case） | ✅ **本專案第一批進入管理頁的 case** |

## 本階段的實質發現（不是走過場）

1. **真實 stack 實跑抓到一個讀程式碼看不出來的缺陷** —— `schema_rbac.sql` 不寫 `updated_by`，使權限補丁在所有由該腳本建立的環境（含 staging）靜默失敗。
2. **修復了一個既有的失效 e2e case** —— 「Developer 看不到系統管理區」自 J5 授權流程起就在失敗（按鈕改名、目的地改變），而 `ui-regression` 是真閘門。不修的話本 PR 會因與本 feature 無關的原因紅燈。
3. **三道新 gate 全部以刻意違反實測過** —— 自我驗證的機制不這樣做就不知道它是否真的有效。

## 誠實揭露的缺口（未消除，已承接）

| 缺口 | 承接 |
|---|---|
| C-2 的「失敗先復原」分支無自動化驗證 | 部署後人工核對 |
| 真實啟動流程的整合（補欄、權限套用）無自動化 | 補丁函式本身已有測試；整合以部署後核對日誌承接，指示寫在 `DEPLOY.md` 2.2.3／2.2.5 |
| 四項無障礙義務為人工（焦點可見、44x44、AC-5.11 介面不存在、對比度） | 無 axe、無 jsx-a11y；`accessibility-checklist.md` 已逐項標記 |
| 前端無 unit／component 測試層 | team-practices 明確不採納引入；e2e 為唯一自動化層 |
| `ui-regression` 在 CI 上尚未跑過本輪的 14 個 case | 待 PR 觸發 |

## 下一步

CI Pipeline（3.7）—— 三道新 gate 已寫進 `.github/workflows/ci.yml`，該階段確認其配置與觸發條件。
