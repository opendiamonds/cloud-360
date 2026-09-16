# Build and Test Results — 260816-production-path-check

- 執行時間：2026-08-18（本機，branch `danniel/fix/production-path-check-noop`，未 commit）
- 指令來源：`build-instructions.md` 的「建置與驗證指令」節、`unit-test-instructions.md` 的「框架與執行方式」節
- 上游：`code-generation-plan.md` Step 5「驗證」、`code-summary.md`「驗證結果」節

## 執行結果總覽

全數通過。exit code 為直接取得（`echo $?`），非由輸出外觀推斷。

| # | CI job | 指令 | exit | 結果 |
|---|---|---|---|---|
| 1 | `repo-contract` | `python3 scripts/validate_repo_contract.py` | **0** | `Cloud-360 repository contract validation passed.` |
| 1 | `repo-contract` | `python3 scripts/validate_env_contract.py` | **0** | `Cloud-360 environment configuration contract validation passed.` |
| 2 | `frontend` | `npm run lint` | **0** | `✖ 3 problems (0 errors, 3 warnings)` |
| 2 | `frontend` | `npm run build`（含 `tsc -b`） | **0** | `✓ built in 567ms` |
| 3 | `backend` | `python -c "import main; ..."` | **0** | `app: Cloud-360 API` |
| 3 | `backend` | `python -m unittest discover -s tests` | **0** | `Ran 222 tests ... OK` |

第 4 個 job（`docker-build`）未在本機執行 —— 它建 image 但 `push: false`，
本次變更不觸及 Dockerfile 或建置上下文，留給 CI 執行。**這是明列的未執行項，不是通過。**

## 單元測試明細

```
Ran 222 tests in 23.287s
OK
```

- 既有 212 個測試維持全綠（本次變更前的基準亦為 212 / OK）
- 新增 10 個（`tests.test_repo_contract_production_paths`），全綠
- **AC-6 驗證**：以 `ci.yml:135` 的實際指令 `discover -s tests -v` 執行時，
  verbose 輸出含 `test_repo_contract_production_paths` 10 次 —— 該測試確實會被
  既有 CI job 自動探索到，不需要修改 `ci.yml`（NFR-1）

## 突變驗證結果

把 `validate_no_production_config_added()` 與其 helper 還原為原本的 diff 基準後重跑：

```
Ran 10 tests in 1.140s
FAILED (failures=6)

FAIL: test_detects_production_directory_on_clean_worktree
    self.assertEqual(code, 1)
AssertionError: 0 != 1
```

**紅燈原因正確**：`0 != 1` 表示檢查對真實違規回報「通過」—— 是**未偵測到違規**，
不是 import 或 fixture 壞掉。兩項佐證：

- `test_fixture_worktree_is_clean` 維持**綠燈** → fixture 管線健全
- 四個非偵測型測試（AC-2 子字串、乾淨 repo、未追蹤檔、fixture 守衛）維持綠燈 →
  正確，一個 no-op 檢查本來就滿足「不要誤擋」

還原修正後回到 10/10 綠燈。reviewer 獨立重跑得到同樣的 6/10 與同樣的失敗訊息。

## 效能量測（NFR-3）

| 量測 | 值 |
|---|---|
| 冷啟單次 | 0.0151s |
| 後續 10 次平均 | 0.0139s |
| 最大 | 0.0166s |
| 掃描檔案數 | 794（`git ls-files \| wc -l`） |

門檻為 **< 1 秒**，實測約為門檻的 1/60。reviewer 獨立重測為平均 0.0144s／最大 0.0258s，
同一數量級。

## 已知狀況（既有，非本次引入）

**前端 3 個 lint warning。** 皆為 `react-hooks/exhaustive-deps`：`AssessmentPage.tsx:365`、
`LoginPage.tsx:36`、`WorkspacePage.tsx:301`。CI 只擋 error，exit 0。
`team.md` 記的第三處是 `WorkspacePage.tsx:279`，**行號已漂移**（檔案與規則相同）——
本次未觸及前端，故不修改該段落，如實記載供下一輪 practices-discovery 覆核。

**系統 `python3` 無法執行完整後端測試套件。** 24 個模組中 17 個因缺
`sqlalchemy`（9）／`hypothesis`（4）／`fastapi`（2）／`jwt`（1）／`starlette`（1）
而 import 失敗。上表的 222/OK 來自 `backend/.venv/bin/python`。
本次新增的測試零非標準庫依賴，在兩個直譯器下都通過。

**建置 chunk 大小警告。** `index-*.js` 為 970.62 kB（gzip 287.63 kB），
超過 vite 的 500 kB 提示門檻。既有狀況，與本次變更無關，exit code 仍為 0。

## 未執行項

| 項目 | 原因 |
|---|---|
| `docker-build` job | 本次不觸及 Dockerfile 或建置上下文；留給 CI |
| integration／performance／security 測試 | Minimal 策略明示跳過（理由見 `build-and-test-summary.md`） |
| 覆蓋率量測 | 本 repo 無此機制（無 `.coveragerc`、無 `coverage`，CI 無對應 step） |
