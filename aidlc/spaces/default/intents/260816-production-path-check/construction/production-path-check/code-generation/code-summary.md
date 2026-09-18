# Code Summary — 禁止 production 路徑的 contract 檢查修正

- Intent：`260816-production-path-check`（issue #509）
- Branch：`danniel/fix/production-path-check-noop`
- 計畫：同目錄 `code-generation-plan.md`（5 步，全數完成）

## 變更檔案

| 檔案 | 變更 | 對應需求 |
|---|---|---|
| `scripts/validate_repo_contract.py` | +24 / −5 | FR-1～FR-4、NFR-2 |
| `backend/tests/test_repo_contract_production_paths.py` | **新增** 215 行 / 10 個測試 | FR-8～FR-10、AC-1、AC-2、AC-6 |
| `aidlc/spaces/default/memory/project.md` | `## Forbidden` 一條 bullet 改寫 | FR-6 |
| `aidlc/spaces/default/memory/team.md` | 刪 1 bullet、改 3 句、加 1 段解決註記 | FR-7、AC-5 |
| `CLAUDE.md` | 第 4 章「禁止路徑」一行改寫 | FR-6（落點補齊，人工確認於 audit shard 的 `HUMAN_TURN 2026-08-17T23:40:58Z`；該次回合即為此決策的核可，`CLAUDE.md` 的實際寫入時間為 `23:41:16Z`，晚於它 18 秒。決策本身記於該 stage 的 `code-generation-questions.md` Q2（附 `[Answer]: A` tag），比照 Q3 的形式可獨立複驗） |

**未變更**：`.github/workflows/ci.yml`（NFR-1，已以 `git diff --name-only` 確認不在清單）、`FORBIDDEN_NEW_PATH_PARTS` 的內容。

## 關鍵實作決定

**比對基準改為 `git ls-files -z` 全域掃描。** 加 `-z` 而非用 plain form：後者會套用 `core.quotePath` 把非 ASCII 檔名逸出成 `"\344\270\255..."`，破壞 path-part 比對。本 repo 目前 0 個非 ASCII 追蹤檔名，但這是一個繁體中文文件 repo，風險是真實的。

**`git_diff_name_only()` 直接移除而非與新 helper 並存。** 它只有一個呼叫點（即被修的函式），保留會留下死碼，違反 `team.md` 記載的「零死碼區塊」紀律。此為對計畫字面（「新增 helper」）的偏離。

**函式名 `validate_no_production_config_added` 與常數 `FORBIDDEN_NEW_PATH_PARTS` 刻意不改名**，儘管 `added`／`NEW` 在語意上已不精確 —— 兩者在 `requirements.md`、`project.md`、`team.md` 中被逐字引用，改名會斷掉追溯鏈。

**docstring 寫進「不要改回 diff 基準」的警告與原因。** 這道檢查的失敗模式是**靜默**的（改回 diff 基準後 CI 仍全綠），所以防復發不能只靠測試，還要讓下一個讀者在動手前就看到理由。

**測試隔離：** 以 `importlib.util.spec_from_file_location` 載入受測腳本（不污染 `sys.path`），每個測試在 `tempfile` 內 `git init` + `git add -A` + `git commit`，再 `mock.patch.object(contract, "ROOT", repo)`。**commit 是承載步驟** —— 未提交的 fixture 會讓舊的 diff 版程式碼「剛好」找得到東西，測試就會對著它該抓的 bug 通過。另加 `assert_worktree_clean()` 斷言 `git status --porcelain` 為空，把這個前提變成可失敗的檢查而非註解。

git 設定逐次以 `-c` 傳入（`user.email`／`user.name`／`commit.gpgsign=false`／`core.excludesFile=os.devnull`／`init.defaultBranch=main`），fixture 既不讀也不寫使用者的全域設定。其中 `core.excludesFile=os.devnull` 防的是：個人 global gitignore 可能靜默漏掉某個 fixture 檔，讓測試空洞地通過。

測試**零非標準庫 import**（刻意不引 `tests.helpers`，那會拉進 SQLAlchemy），在裸 Python 上也能跑。

## 測試

新增 10 個測試，超出計畫列出的 4 個情境：AC-1（`production` 完整 path part）、`prod` 與 `secrets` 各自的完整 path part、AC-2（子字串不誤擋，用的是本 repo 的真實檔名）、檔名本身作為 path part、大小寫不敏感、多違規全列（FR-4）、未追蹤檔案不掃、乾淨無違規 repo、fixture 自身的乾淨性守衛。

### 突變驗證（DoD 要求）

把 helper 與呼叫點還原為原本的 diff 基準後重跑：

```
Ran 10 tests in 1.140s
FAILED (failures=6)

FAIL: test_detects_production_directory_on_clean_worktree
    self.assertEqual(code, 1)
AssertionError: 0 != 1
```

`0 != 1` 表示檢查對真實違規回報「通過」—— 紅燈原因是**未偵測到違規**，不是 import 或 fixture 壞掉。兩項佐證：`test_fixture_worktree_is_clean` 維持綠燈（fixture 管線健全），四個非偵測型測試也維持綠燈（no-op 檢查本來就滿足「不要誤擋」）。還原修正後 10 個全綠。

### 驗證結果（實際執行）

| 項目 | 結果 |
|---|---|
| `python3 scripts/validate_repo_contract.py` | exit 0 |
| `python3 scripts/validate_env_contract.py` | exit 0 |
| `cd backend && python -m unittest discover -s tests` | **Ran 222 tests / OK**（212 既有 + 10 新增） |
| AC-6：新測試被 `unittest discover` 探索到 | 是（verbose 輸出含該模組 10 次） |
| AC-4：`ci.yml` 未被更動 | 是 |
| NFR-3：單次執行時間 | **0.0151s**（10 次平均 0.0139s，掃描 794 個追蹤檔）—— 門檻 1 秒的約 1/60 |

> 環境註記：系統 `python3` 無法跑完整後端套件（24 個模組中 17 個因缺 `sqlalchemy`／`hypothesis`／`fastapi`／`jwt`／`starlette` 而 import 失敗），這是**既存狀況**、與本次變更無關。222/OK 來自 `backend/.venv/bin/python`。新測試在兩個直譯器下都通過（它零非標準庫依賴）。

## 與計畫的偏離

1. **移除 `git_diff_name_only()`** 而非與新 helper 並存 —— 避免死碼（理由見上）。
2. **`git ls-files -z`** 而非 plain form —— 非 ASCII 檔名安全（理由見上）。
3. **順手修正 `team.md` 的過期行號引用**：Secret 掃描那條 bullet 原引 `validate_repo_contract.py:347`，該函式在本次變更**前**已在 373 行（引用本來就是錯的），現在是 392 行。改為只留函式名不留行號 —— 行號每次編輯都會漂移。此修改落在本來就要重寫的同一段落內。
4. **10 個測試而非計畫列的 4 個情境** —— 補上 FR-4（多違規全列）等計畫未展開的驗收面。
5. **`CLAUDE.md` 第 4 章一併改**（計畫 Step 4 只列 `project.md` 與 `team.md`）—— 經人工確認後補列，理由記於 `requirements.md` 的 FR-6。

## 已知缺口（不在本次修，明列交接）

- **`discovered-rules.md` 第 4 項**（`260802-last-login-column` record）仍描述這道檢查為 no-op。屬另一個 intent 的 record，本 intent 不逕行修改；`team.md` 已加指標說明待下一輪 practices-discovery 標為已解決。
- **新測試沒有 TCMS spec 註解**（`@purpose`／`@given`／`@step`／`@pass`／`@story`）。`test-case-authoring.md` §4.4 的格式要求至少一個 `@api` 或 `@ui`，且兩者都會被機械比對 `openapi.json`／`App.tsx`。這支測試測的是 repo 根目錄的腳本，既無端點也無 UI route，本 intent 亦無 user story（issue 驅動）。**這是格式契約對「非 HTTP、非 UI 測試」的真實缺口**，捏造一個假的 `@api` 比省略更糟。留給 `tcms-test-cases` stage 處理。
- **`validate_no_obvious_secrets()` 的掃描範圍過窄**仍未修（`team.md` 保留該條記載）—— 成因與修法都不同，需求文件的範圍邊界明列為獨立問題。
