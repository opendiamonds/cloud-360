# 測試結果（261116-brain-create-diagram）

> 執行日期 2026-11-22（UTC），本機 macOS，分支 `danniel/feat/brain-create-diagram`（未 commit）。所有數字取自指令輸出，未手寫。

## 1. 建置

| 指令 | 結果 |
|---|---|
| `npm run lint` | `0 errors, 2 warnings`（皆為既存的 `exhaustive-deps`） |
| `npm run build`（含 `tsc -b`） | 成功（chunk 大小警告為既存） |
| `npm run check:types` | 「API 型別檔與規格檔一致。」 |
| `dump_openapi.py --check` | 「規格檔與後端程式碼一致。」 |
| `dump_ws_contract.py --check` | 「WS 契約規格檔與後端程式碼一致。」 |
| `validate_repo_contract.py` | passed |
| `validate_env_contract.py` | passed |

## 2. 單元與整合測試

| 指令 | 結果 |
|---|---|
| `cd backend && .venv/bin/python -m unittest discover -s tests`（最終一次，所有修正之後） | `Ran 1618 tests in 151.425s` — `OK (skipped=3)` |
| 同上（code-generation 修訂 1 結束時的基準） | `Ran 1613 tests` — `OK (skipped=3)` |

各單元的 `unit-test-instructions.md` 指令皆為上述全套的子集，以全套執行一次涵蓋，不重複計數。

新增的 5 個測試：
- `test_diagram_drafts_schema`：`test_startup_patch_failure_propagates_instead_of_being_swallowed`、`test_init_db_fails_when_the_status_patch_fails`
- `test_brain_diagram_creation_flow`：`test_create_404_is_reported_as_permanent_not_retry_later`、`test_decision_is_logged_by_category_without_utterance_or_title`
- `test_diagram_drafts_hierarchy`：`test_diagrams_without_updated_at_sort_last_on_every_dialect`

### 突變驗證

| 突變 | 預期紅燈的測試 | 結果 | 還原後 |
|---|---|---|---|
| `_ensure_diagram_status_schema` 拿掉 `raise`（吞掉例外） | `test_startup_patch_failure_propagates_instead_of_being_swallowed` | FAIL | OK |
| `init_db` 以 `try/except: pass` 包住補丁呼叫 | `test_init_db_fails_when_the_status_patch_fails` | FAIL | OK |
| 拿掉 404 分支（落回「請稍後再試一次」） | `test_create_404_is_reported_as_permanent_not_retry_later` | FAIL | OK |
| `ORDER BY` 拿掉 `.nulls_last()` | `test_diagrams_without_updated_at_sort_last_on_every_dialect` | FAIL | OK |
| `diagram_decision` 日誌把使用者原文寫進欄位 | `test_decision_is_logged_by_category_without_utterance_or_title` | FAIL | OK |
| `diagram_decision` 日誌拿掉 `category` | 同上 | FAIL | OK |

## 3. PostgreSQL 遷移驗證（本機一次性 PostgreSQL 17.7）

腳本與限制見 `integration-test-instructions.md` §3。輸出：

```
== 2. 啟動補丁的 DDL（hierarchy_migration._ensure_diagram_status_column 逐字）
既有列狀態：ready,ready,ready
== 3. 補完後重跑新版 schema_rbac.sql 的 status 區塊（可重跑性）
status 區塊連跑兩次：OK
CHECK 約束數：1
== 4. 空 volume 路徑：只跑 schema 區塊（不經啟動補丁）
空表加欄＋CHECK：OK
== 5. CHECK 擋下非法值
擋下：violates check constraint "ck_user_diagrams_status"
== 6. 排序 updated_at DESC, id DESC（SQLAlchemy .desc() 不加 NULLS 子句）
PostgreSQL：b,c,a
PostgreSQL（修正後 NULLS LAST）：c,a,b
```

（`b` 的 `updated_at` 為 NULL。）同樣資料在 SQLite 的 `ORDER BY updated_at DESC, id DESC` 結果為 `c,a,b`——兩種方言排 NULL 的位置相反，已改為 `NULLS LAST`。

## 4. 前端 e2e（Playwright，本機替身版）

`BASE_URL=http://localhost:4173 npx playwright test tests/e2e/{diagram-drafts,project-pages,entry-page,object-picker,brain-assistant}.spec.ts` → `137 passed (1.8m)`。

**未在 CI 的 `docker-compose.test.yml` stack 上執行**；所有 API 與 WebSocket 皆為 spec 內替身。

## 5. Target Verification Matrix（最終）

| Target ID | Expected | Actual | Evidence | Owning Stage | Verdict |
|---|---|---|---|---|---|
| TC-SUITE | 後端全套 0 失敗 | 1618 tests OK（skipped=3） | §2 | build-and-test | Met |
| TC-FE | lint 0 errors、build 成功、型別一致 | 符合 | §1 | build-and-test | Met |
| NFR1 | 準確率 ≥ 80% | 未量測 | 需 staging 部署後的真實路由模型 | 無承接 stage | Unverified |
| NFR2 | 首字 P50 ≤ 2000 ms | 未量測 | 同上 | 無承接 stage | Unverified |
| NFR3 | 冪等三案 | 綠 | §2 | build-and-test | Met |
| NFR4 | 類別入日誌、無原文與圖名 | 綠＋兩項突變紅 | §2 | build-and-test | Met |
| NFR5 | TestClient、Playwright、權限雙向 | 綠 | §2、§4 | build-and-test | Met |
| FR6.5-PG | PostgreSQL 上補欄、可重跑、CHECK 生效 | 成立 | §3 | build-and-test | Met |

## 6. 失敗處理

依 stage 定義，NFR1／NFR2 為 `Unverified` 即本站失敗。

- **診斷**：不是程式或測試的缺陷。兩者量的是真實路由模型在部署環境中的準確率與延遲；本分支尚未合併，staging 上沒有這版程式，本機也沒有真實路由模型可用。
- **可替換面向中有無修法**：沒有。換函式庫、映像、旗標或演算法都不會讓本機量得到 staging 上的真實模型行為。唯一的取得方式是合併部署後依 `performance-test-instructions.md` §2 量測，而那是流程順序問題，不是可在 code-generation 套用的修正。
- **本站內修正嘗試**：0 次（不在本站可修的範圍）。
- **Loop-back**：0／3。
- 待使用者裁決：接受失敗並進入關卡（量測移到合併後），或中止。

**使用者裁決（2026-11-22）**：接受失敗——NFR1／NFR2 記為未量測，進入本站核可關卡；合併部署到 staging 後比照前例量測（觸發量測執行須另取得使用者同意）。
