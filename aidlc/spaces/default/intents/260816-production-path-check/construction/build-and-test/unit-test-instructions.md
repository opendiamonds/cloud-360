# Unit Test Instructions — 260816-production-path-check

- Test Strategy：**Minimal**（`aidlc-state.md` 第 18 行）→ 依 stage 檔的 Step 4-8，
  **只產出本檔**，跳過 integration／performance／security 三份（跳過理由見
  `build-and-test-summary.md` 的「跳過的測試類型」）。
- 上游：`<record>/construction/production-path-check/code-generation/code-generation-plan.md`
  的 Step 2、Step 3；`code-summary.md` 的「測試」節。

## 框架與執行方式

本 repo 的後端測試框架是 Python 內建 **`unittest`**（**不是 pytest**），
搭配 `hypothesis`（property-based）與 `unittest.mock`。沒有 `pytest.ini`、
沒有 `conftest.py`，也沒有覆蓋率量測機制。

```bash
# CI 的實際指令（ci.yml:135，working-directory: backend）
cd backend && python -m unittest discover -s tests -v

# 只跑本次新增的回歸測試
cd backend && ./.venv/bin/python -m unittest tests.test_repo_contract_production_paths -v
```

**測試落點必須是 `backend/tests/`。** 這是 CI 唯一的 Python 測試探索路徑
（`ci.yml` 的 `backend` job 有 `defaults: run: working-directory: backend`，
第 135 行 `discover -s tests`）。放在 `scripts/tests/` 之類的位置會字面滿足
「有寫測試」卻永不執行 —— 這正是本 intent 要修的缺陷形狀（FR-8、AC-6）。

## 本次的測試清單（10 個，對應 FR／AC）

檔案：`backend/tests/test_repo_contract_production_paths.py`

| 測試 | 驗收依據 |
|---|---|
| `test_detects_production_directory_on_clean_worktree` | **AC-1**（核心：乾淨工作樹下偵測 `production` 完整 path part） |
| `test_detects_prod_directory_on_clean_worktree` | AC-1（`prod`） |
| `test_detects_secrets_directory_on_clean_worktree` | AC-1（`secrets`） |
| `test_substring_matches_are_not_violations` | **AC-2**（用本 repo 的真實檔名，如 `aidlc-product-agent.md`） |
| `test_filename_itself_as_path_part` | FR-3 邊界 |
| `test_matching_is_case_insensitive` | FR-3（`FORBIDDEN_NEW_PATH_PARTS` 全小寫 + `part.lower()`） |
| `test_reports_every_violation_not_just_the_first` | **FR-4**（一次列出全部違規） |
| `test_untracked_file_is_not_scanned` | 規則治理的是版控內容 |
| `test_clean_repo_passes` | 無違規時回 0 |
| `test_fixture_worktree_is_clean` | fixture 自身的守衛（見下） |

Minimal 策略的門檻是「1 test per requirement + happy-path floor」，
本次 10 個測試涵蓋 FR-1～FR-4 與 AC-1／AC-2，符合並略高於該門檻。

## 這些測試為何不是恆真的

三個承載設計，缺任何一個測試就會變成空洞通過：

1. **fixture 必須 commit。** 未提交的 fixture 會讓**舊的** diff 版程式碼「剛好」
   找得到東西，測試就會對著它該抓的 bug 通過。`assert_worktree_clean()` 斷言
   `git status --porcelain` 為空，把這個前提變成可失敗的檢查而非註解。
2. **`ROOT` 用 `mock.patch.object` 覆寫。** `git_ls_files()` 在呼叫時才查 module global，
   所以 patch 生效；受測函式因此指向暫存 repo，不掃真實 repo（FR-9、FR-10）。
3. **git 設定逐次以 `-c` 傳入**（`commit.gpgsign=false`、`core.excludesFile=os.devnull` 等），
   fixture 既不讀也不寫使用者的全域設定。其中 `core.excludesFile` 防的是：
   個人 global gitignore 可能靜默漏掉某個 fixture 檔，使測試空洞通過。

## 突變驗證（Definition of Done 要求）

依 `test-case-authoring.md` §5「突變驗證：沒看過它紅過，就不算寫完」。

```bash
# 1) 把 validate_no_production_config_added() 還原成 diff 基準
# 2) 重跑
cd backend && ./.venv/bin/python -m unittest tests.test_repo_contract_production_paths
#    預期：6 個偵測型測試紅燈，皆為 AssertionError: 0 != 1
# 3) 還原修正，確認回到 10/10 綠燈
```

**紅燈原因必須是 `0 != 1`（未偵測到違規），不是 import 或 fixture 錯誤。**
若紅燈訊息是 `ModuleNotFoundError` 或 fixture 例外，代表測試根本沒跑到受測邏輯，
突變驗證不成立。實際執行結果記於 `build-test-results.md`。

## 新增測試時的注意事項

- **不得**在真實 repo 建立任何 path part 含 `prod`／`production`／`secrets` 的檔案 ——
  那會觸發這道檢查本身，且會把違規路徑寫進共用 git 歷史（FR-9）。測試情境**只能**
  存在於 `tempfile` 暫存目錄。
- 沿用零非標準庫 import 的形狀，讓這支測試在裸 Python 上也能跑。
