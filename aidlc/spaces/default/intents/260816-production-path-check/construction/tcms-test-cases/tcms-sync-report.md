# 驗證關卡與 TCMS 同步報告 — 禁止 production 路徑的 contract 檢查修正

> Intent：`260816-production-path-check`（issue #509）
> 依 `project.md` 的既有 correction（「produces 清單是 artifact 集合的正式來源，
> 不自創檔案」），`/tcms-verify` 的報告併入本檔第 1、2 節，不另開檔案。

## 結論

| 項目 | 結果 |
|---|---|
| 第 1 層 機械檢查 | **通過**（既有資產 27/27，0 ERROR 0 WARN）＋ 1 項工具限制，非案例缺陷 |
| 第 2 層 語意審查 | **通過** |
| TCMS 同步 | **本輪 0 筆寫入** —— 手動端無案例可建、自動化端無工具路徑；逐項理由見第 3 節 |

---

## 1. 第 1 層：機械檢查

### 1.1 `python3 scripts/tcms_validate.py --all`

```
驗證 27 個案例……
通過 27/27　ERROR 0　WARN 0
機械檢查全數通過。
```

exit 0。

**但要說清楚它驗了什麼**：`--all` 的兩個目標是寫死的 ——
`DEFAULT_MANUAL` 指向 **`260802-last-login-column`** 這個**上一個 intent** 的
`manual-test-cases.md`，`DEFAULT_SPEC` 指向 `frontend/tests/e2e/regression.spec.ts`
（`scripts/tcms_validate.py:37-42`）。所以這 27/27 是**既有資產的迴歸確認**，
不是本 intent 產出的驗證。把它讀成「本 intent 通過機械檢查」是錯的。
列為 open item OI-3。

### 1.2 `--file <本 intent 的 manual-test-cases.md>`

```
沒有要驗證的對象。用 --file／--spec／--all 指定。
```

exit **1**。

**這不是案例缺陷，是工具沒有「零手動案例」這個概念。** 判定依據與 skill 明列的
例外（追溯指向未合併分支）同型：退出碼非 0，但成因不落在工具自己宣告的四類檢查
（必填欄位、空洞預期、追溯目標存在、API/UI 比對）中任何一類 —— 它在 argparse 之後、
檢查之前就因為「目標清單為空」而中止。本檔沒有 `## TC:` 是分桶判定的結果，理由逐項
寫在 `manual-test-cases.md`。列為 open item OI-2。

### 1.3 本 intent 實際被機械驗證的部分

手動案例為 0，故機械層改以**可判定的替代證據**確認產出正確，全部實測：

| 檢查 | 指令 | 結果 |
|---|---|---|
| 回歸測試全綠 | `cd backend && .venv/bin/python -m unittest tests.test_repo_contract_production_paths` | Ran 11 / OK |
| 後端既有測試無迴歸 | `cd backend && .venv/bin/python -m unittest discover -s tests` | Ran 223 / OK |
| AC-6 測試被 CI 指令探索到 | `python -m unittest discover -s tests -v`，grep 模組名 | 11 次（11 個測試全被探索） |
| AC-3 現況通過 | `python3 scripts/validate_repo_contract.py` | exit 0 |
| 環境設定 contract | `python3 scripts/validate_env_contract.py` | exit 0 |
| AC-4 CI 未被更動 | `git diff --name-only`／`--cached --name-only` | `.github/workflows/ci.yml` 不在清單 |
| AC-5 規則與機制一致 | grep `team.md` 的「恆為 no-op」「兩條規則」「這兩項」「不逕自變更腳本行為」 | 四者皆 0 命中 |

---

## 2. 第 2 層：語意審查

手動案例為 0，skill 的七點中第 1～5 點與第 7 點沒有審查對象。**唯一有對象、也是決定
性的一點是第 6 點（是否與自動化層重複）** —— 因為正是它把手動案例數壓成 0。逐點記錄：

| # | 審查點 | 判定 | 理由 |
|---|---|---|---|
| 1 | 目的指向真會失敗的行為 | N/A | 無手動案例 |
| 2 | 回歸案例背景寫出缺陷原貌 | N/A | 無手動案例。缺陷原貌記在 `backend/tests/test_repo_contract_production_paths.py` 的模組 docstring（症狀、成因、為何 `scripts/tests/` 不是可接受的落點） |
| 3 | 步驟可被外人執行 | N/A | 無手動案例 |
| 4 | 受測介面涵蓋實際碰到的介面 | N/A | 無手動案例；自動化端的 `@api`／`@ui` 缺口見 `automation-test-plan.md` §3 |
| 5 | 通過條件二元可判 | N/A | 無手動案例 |
| 6 | **是否與自動化層重複** | **通過（且為零手動案例的成因）** | 逐項核對 14 項外部可觀察行為：10 項已有自動化斷言、1 項本 stage 新寫、3 項明列為未寫的 open item。**沒有任何一項是「自動化做不到」**。依撰寫標準 §1，為已自動化的行為另寫手動案例即製造雙份真實來源，明文禁止 |
| 7 | 規格與 `stories.md` 的 AC 一致 | 改以 `requirements.md` 核對，**通過** | 本 intent 為 bugfix scope，`user-stories` stage 依 scope 設定跳過，`stories.md` 不存在（引擎的 `consumes_absent` 已標記）。改對照 `<record>/inception/requirements-analysis/requirements.md`：AC-1→`test_detects_production_directory_on_clean_worktree`、AC-2→`test_substring_matches_are_not_violations`、AC-3→實測 exit 0、AC-4→`git diff` 清單、AC-5→grep 四項皆 0 命中、AC-6→discover 探索到 11 個。**六條 AC 逐條有對應證據，無一僅以文字宣稱帶過** |

### 額外的語意判定：新腳本本身

第 6 點的反面 —— 本 stage 新寫的 B-11 是否只是既有 10 個測試的重複？**不是。**
既有測試全部在 `git init` 出來的完整暫存 repo 上執行，沒有一個碰到「歷史被截斷」
這個 CI 的實際條件；`build-and-test-summary.md` 對此只有文字宣稱、無任何斷言。
突變驗證（`automation-test-plan.md` §突變驗證）另證明它會對原始缺陷紅燈，
且 fixture 退化成完整 clone 時會被自身的守衛擋下，不會空洞通過。

---

## 3. TCMS 同步

`~/.tcms.conf` **存在**（`/Users/jiangzhengdao/.tcms.conf`），所以本節不是
「因缺設定而跳過」—— 是**沒有東西可以同步**，兩條路徑各有明確成因。

### 3.1 手動案例（`--file`，建立＋更新）

```
$ python3 scripts/tcms_sync.py --file <record>/construction/tcms-test-cases/manual-test-cases.md --dry-run
… 沒有解析到任何案例（案例標題格式為 '## TC: <標題>'）
exit 1
```

**結果：0 筆建立、0 筆更新。** 成因是本 intent 的手動案例數為 0（分桶判定，
非漏寫）。工具沒有靜默跳過，它明說解析到 0 個案例 —— 這正是應有的行為。
未執行不帶 `--dry-run` 的版本：沒有案例可寫。

### 3.2 自動化案例（`--spec`，只更新不建立）

```
$ python3 scripts/tcms_sync.py --spec backend/tests/test_repo_contract_production_paths.py --dry-run
… 沒有解析到任何規格註解。每個 test 前需要一個含 @purpose／@step 等標記的 /** */ 區塊。
exit 1
```

**結果：0 筆更新。** 兩個獨立成因，任一單獨存在都足以讓它同步不了（見
`automation-test-plan.md` §4）：

1. **解析器只認 Playwright**：`DESCRIBE_LINE` 認 `test.describe('...')`、`TEST_LINE`
   認 `test('...')`（`scripts/tcms_sync.py:133-134`），且規格註解必須是 `/** */`
   區塊。Python 的 `unittest.TestCase` 與 `"""docstring"""` 一行都對不上。
2. **TCMS 上根本沒有對應案例可更新**：自動化案例由 junit plugin 從測試結果建立，
   而全 `.github/workflows/` 只有 `ui-regression` 對接 Kiwi TCMS，`ci.yml` 的 backend
   job 不產生也不上傳 junit 結果。`--spec` 是**只更新、不建立**的工具，找不到案例時
   本來就該什麼都不做（建了會是永遠沒有執行結果的孤兒）。

### 3.3 落地的 TCMS 變更

| 項目 | 數量 |
|---|---|
| 建立的案例 | 0 |
| 更新的案例 | 0 |
| 寫入的 TestPlan | 無 |

**本 intent 的測試覆蓋完全落在 repo 內**（`backend/tests/test_repo_contract_production_paths.py`
的 11 個測試，每個 PR 由 `ci.yml` 的 backend job 執行）。這符合
`test-case-management-plan.md` 的單一真實來源原則：自動化的主檔本來就是 repo 的
spec code，TCMS 只存中繼資料與歷史結果 —— 本例是連中繼資料的搬運路徑都還不存在。

---

## 4. Open items

| # | 項目 | 影響 | 建議處置 |
|---|---|---|---|
| OI-1 | Python 測試沒有進 TCMS 的路徑（junit 只接 Playwright、`--spec` 只解析 `.ts`） | backend 的 223 個測試在 TCMS 上完全不可見；判讀覆蓋率的人只看得到前端 6 個 e2e | 需同時動 `ci.yml`（產出並上傳 junit）與 `tcms_sync.py`（Python spec 解析）。本 intent 的 NFR-1 明訂不動 `ci.yml`，故超出範圍 |
| OI-2 | `tcms_validate.py` 對「零手動案例」的 intent 回 exit 1 | 驗證關卡對這類 intent 無法以退出碼判定通過與否 | 讓 `--file` 在解析到 0 個案例時區分「檔案不存在／格式壞掉」（ERROR）與「本 intent 宣告零手動案例」（正常，exit 0） |
| OI-3 | `tcms_validate.py --all` 的 `DEFAULT_MANUAL` 寫死指向 `260802-last-login-column` | 隨 intent 累積，`--all` 會一直驗越來越舊的那一份，卻讀起來像「全部都驗了」 | 改為掃描 `aidlc/spaces/*/intents/*/construction/tcms-test-cases/manual-test-cases.md` 全集，或至少改讀 active-intent 游標 |
| OI-4 | 格式契約缺 `- CLI:`／`@cli` 受測介面種類 | 非 HTTP、非 UI 的受測對象（`scripts/` 整族、workflows）寫不出過得了機械檢查的案例 | 於 `TESTING.md` §2 新增該行型別，`tcms_validate.py` 一併做目標路徑存在性核對。已在核可關卡提出，使用者選擇本輪不改工具 |
| OI-5 | B-12／B-13／B-14 三支自動化測試未寫 | 見 `automation-test-plan.md` §2 的風險欄，其中 B-12（`main()` 佈線）與 #509 屬同一種靜默失效形狀 | 留待下一輪；已附具體寫法，不需重新設計 |
