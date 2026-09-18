# Quality Gates

## 本 intent 之後的完整閘門清單

| # | 閘門 | 位置 | 擋什麼 | 對本 intent 有效？ |
|---|---|---|---|---|
| 1 | Repo contract | `repo-contract` job | 必要文件、必要文字、文件語言、禁止路徑與內容 | ✅（本 intent 新增大量 record 文件） |
| 2 | Frontend lint | `frontend` job | ESLint **error**（不擋 warning） | ✅ |
| 3 | **API type contract drift** | `frontend` job | 型別檔沒跟著規格檔重產 | ✅ **新增** |
| 4 | Typecheck ＋ build | `frontend` job | 型別錯誤、建置失敗 | ⚠️ 見下方「既有落差」 |
| 5 | **Spec must not be served statically** | `frontend` job | 規格檔落進 `dist/` 而被公開 | ✅ **新增** |
| 6 | Backend import smoke | `backend` job | 語法錯誤、壞掉的 import、router 接線 | ✅ |
| 7 | **OpenAPI spec drift** | `backend` job | 規格檔沒跟著後端程式碼重 dump | ✅ **新增** |
| 8 | Backend unittest | `backend` job | 140 個測試 | ✅ |
| 9 | Docker build | `docker-build` job | Dockerfile 壞掉 | ✅（未受影響，但仍會跑） |
| 10 | `ui-regression`（gh-aw） | 每個 PR 對短生命週期 stack | 14 個 e2e case；`stats.unexpected != 0` 即 `exit 1` | ✅ |

## 三道新閘門的有效性已實測

**自我驗證的機制不刻意弄壞一次，就不知道它是否真的有效。**

| 閘門 | 刻意違反 | 結果 |
|---|---|---|
| 3 | 改 `api.d.ts` 一個欄位名 | **exit 1** |
| 5 | 把 `openapi.json` 複製進 `dist/` | **命中並 exit 1** |
| 7 | 改 `openapi.json` 一個欄位名 | **exit 1** |

三者移除違反後皆回到 exit 0。

## 既有落差（如實記載，本 intent 縮小但未消除）

| 落差 | 狀態 |
|---|---|
| `tsc -b` 對「後端回應形狀」無感 | **本 intent 大幅縮小**：`AdminPage` 已改用產生的型別，回應形狀變更現在會在建置期失敗。但**其餘 51 處資料抓取仍是手寫型別**（C-8 的採用範圍限縮，Q5=A 的既有定案） |
| `validate_repo_contract.py` 的 secret 掃描看不到 `backend/`／`frontend/` | 既有機制落差（`team.md` 已記載）。本 intent **未擴大**它，亦未修復 |
| `validate_no_production_config_added()` 在 CI 上恆為 no-op | 同上。以 `git diff` 為輸入，而 CI 是乾淨 checkout |
| 無覆蓋率量測 | `org.md` 的 80% 宣告仍無法量測、無法強制。本 intent 以三項變更範圍內、二元可判的測試底線（A／B／C）作為實際門檻 |
| 無自動化無障礙檢查 | 無 axe、無 jsx-a11y。四項無障礙義務為人工 |

## 誤報風險的處置

漂移檢查最大的失敗模式不是漏報，是**誤報** —— 會在無關 PR 上變紅的 gate 訓練人忽略紅燈，連帶削弱真漂移時的訊號。

處置：`fastapi`／`pydantic` **精確等值釘選**。實測規格輸出在同一組版本下位元決定性、跨版本會飄；本 repo 12 支依賴全部未 pin、CI 每次重新解析最新版，不釘這兩支就會誤報。**升版時必須在同一個 PR 內重新 dump 規格並重產型別檔** —— 屆時 gate 變紅是正確行為。
