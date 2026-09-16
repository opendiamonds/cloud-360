# 自動化測試計畫 — 禁止 production 路徑的 contract 檢查修正

> Intent：`260816-production-path-check`（issue #509）
> 涵蓋覆蓋盤點中的「待自動化」桶。分桶結果見 `manual-test-cases.md`。

## 1. 本 stage 寫出的腳本

### B-11 — shallow checkout 下仍掃到全部追蹤檔

| 項目 | 內容 |
|---|---|
| 落點 | `backend/tests/test_repo_contract_production_paths.py` |
| 測試 | `TestShallowCloneScan::test_violation_in_unfetched_commit_is_still_detected` |
| 層級 | Backend 單元／行為（stdlib `unittest`） |
| 新依賴 | 無（`subprocess`／`tempfile`／`contextlib` 皆為標準庫） |

**為什麼落在這一層**：受測對象是 repo 根目錄的 Python 腳本，既無 HTTP 端點（`TestClient`
不適用）也無 UI（Playwright 不適用）。`backend/tests/` 是 CI **唯一**會探索的 Python 測試
路徑（`ci.yml` 以 `working-directory: backend` 跑 `python -m unittest discover -s tests`），
放在 `scripts/tests/` 會滿足「有寫回歸測試」卻永遠不在 PR 上執行 —— 那正是本 bug 的失敗
形狀，不可接受。此判斷沿用同檔既有 10 個測試的落點理由。

**它斷言的具體條件**（不是「測試 shallow clone 正常」）：

1. fixture 真的是被截斷的 clone：`git rev-list --count HEAD` 為 `1`（來源 repo 有 2 個
   commit）。這一條是承載件 —— 若 `--depth` 被 git 忽略而退化成完整 clone，測試會在此
   停下，而不是空洞地通過。
2. clone 的工作樹乾淨：`git status --porcelain` 為空（重現 CI 的 checkout 條件）。
3. 違規路徑**只存在於未被抓取的第一個 commit**，檢查仍回傳 `1`，且 stderr 含
   `deploy/production/config.yml`。

**為什麼值得寫**：`build-and-test-summary.md` 宣稱「淺 clone（`fetch-depth: 1`，CI 的
預設）亦不影響 `git ls-files`」。這是修正能否在 CI 生效的前提，但在此之前**沒有任何測試
釘住它**。若該宣稱是錯的，#509 的修正會在 CI 再次靜默無效 —— 同一種失敗形狀第二次。

**實作細節（踩到的坑）**：clone 必須用 `file://` URL（`source.as_uri()`）。git 對
plain local path 的 clone **會忽略 `--depth`**，只印一行提示就交回完整歷史；沒有第 1 條
斷言的話，測試會在毫無察覺的情況下退化成「測了一次普通 clone」。

### 突變驗證

依 `test-case-authoring.md` §5，跑綠不算寫完，必須看它紅過。做了兩次突變，每次都先
`grep` 確認檔案真的被改到（§5 記載過「突變沒生效卻被誤讀成測試沒抓到」的前例）。

**突變 1 —— 把比對基準改回修正前的 working-tree diff**
（在 `validate_repo_contract.py` 插入 `_MUTATION_diff_name_only()`，
把 `for path in git_ls_files():` 換成 `for path in _MUTATION_diff_name_only():`；
`grep` 確認兩處都在檔案裡）：

```
Ran 11 tests in 1.089s
FAILED (failures=7)

FAIL: test_violation_in_unfetched_commit_is_still_detected
    self.assertEqual(code, 1)
AssertionError: 0 != 1
```

紅燈原因是 `0 != 1` —— 檢查對真實違規回報「通過」，也就是**未偵測到違規**，不是 import
或 fixture 壞掉。7 項失敗＝既有 6 項（code-generation 已記錄）＋本次新增的 1 項，
新測試確實對著它要防的缺陷紅燈。還原後 11 個全綠（md5 比對確認腳本逐位元組還原）。

**突變 2 —— 讓 fixture 退化成完整 clone**（拿掉 `--depth 1`，`grep` 確認該行已變）：

```
AssertionError: '2' != '1'
- 2
+ 1
 : fixture must be a truncated clone; a full history would make this test pass
   without exercising the shallow case
```

第 1 條斷言擋下了退化的 fixture。這證明「shallow」不是註解裡的一句宣稱，而是可失敗的
檢查。還原後複驗綠燈。

### 執行結果

| 指令 | 結果 |
|---|---|
| `cd backend && .venv/bin/python -m unittest tests.test_repo_contract_production_paths` | Ran 11 tests / **OK** |
| `cd backend && .venv/bin/python -m unittest discover -s tests` | Ran **223** tests / **OK**（222 → 223） |
| `cd backend && python3 -m unittest tests.test_repo_contract_production_paths`（系統直譯器） | Ran 11 tests / **OK** —— 零非標準庫依賴的宣稱成立 |
| `python3 scripts/validate_repo_contract.py` | exit 0 |
| `python3 scripts/validate_env_contract.py` | exit 0 |

## 2. 未寫出腳本的項目（open item）

三項在核可關卡上提出，使用者選擇本輪只寫 B-11。**明列於此而非默默略過**，因為「待自動化
但沒寫」與「不需要自動化」是兩件不同的事。

| # | 行為 | 打算怎麼寫（留給下一輪） | 不寫的風險 |
|---|---|---|---|
| B-12 | `main()` 真的呼叫 `validate_no_production_config_added` | `mock.patch.object` 把其餘四個 validator 覆寫為回 0、`ROOT` 指向含違規的暫存 repo、斷言 `contract.main()` 回 1。可行性已確認：`checks` tuple 在 `main()` **呼叫時**才從 module globals 解析，patch 得到 | 現有 11 個測試全部直接呼叫該函式，沒有一個證明它被接上。有人把它從 tuple 移除，測試與 CI 全綠 |
| B-13 | 非 git 工作樹時 fail-fast | 在非 git 的暫存目錄上呼叫，`assertRaises(subprocess.CalledProcessError)` | 這是本次**新增的環境面依賴**（`build-and-test-summary.md` §建置狀態）。有人加 `try/except` 就退回「拿不到清單就假裝通過」 |
| B-14 | NFR-3：真實 repo 全掃 < 1 秒 | 對真實 `ROOT` 計時並斷言 < 1.0s | 無自動防迴歸。已知現值 0.0151s／794 檔（門檻的 1/60），餘裕大，風險低 |

## 3. 規格註解（§4.4）與其格式缺口

新測試已依 `project.md` 必做 3b 加上結構化註解（`@purpose`／`@given`／`@step`／`@pass`／
`@story`），寫在 Python 的 class docstring 內、緊鄰測試方法。`@story` 填 `issue #509`
—— 本 intent 是 issue 驅動的 bugfix scope，`user-stories` stage 依 scope 設定跳過，
沒有 story id 可填。

**刻意不填 `@api`／`@ui`**。撰寫標準 §4.4 要求兩者至少有一個，且都會被
`tcms_validate.py` 機械比對（端點對 `openapi.json`、路徑對 `App.tsx`）。受測對象是
repo 根目錄的 CLI 腳本，兩者皆不存在 —— 捏造一個過得了比對的假端點，比省略更糟：
它會讓下一個改那支 API 的人以為這個案例與他有關。

這是 code-generation 與 build-and-test 兩站都已標記、交由本 stage 判定的缺口。本 stage
的判定是：**這是格式契約對「非 HTTP、非 UI 受測對象」的真實缺口**，不是本測試的瑕疵。
修法（新增 `- CLI:`／`@cli` 介面種類，並讓它一樣機械核對目標路徑存在）已在核可關卡
提出，使用者選擇本輪不改工具。缺口保留，記在此處。

## 4. 已知的工具鏈限制：Python 測試沒有進 TCMS 的路徑

本節是分桶之外的發現，直接影響 `tcms-sync-report.md` 的結果，記在這裡讓下一輪能接手：

1. **`tcms_sync.py --spec` 只解析 Playwright**：`DESCRIBE_LINE` 認 `test.describe('...')`、
   `TEST_LINE` 認 `test('...')`（`scripts/tcms_sync.py:133-134`）。Python 的
   `unittest.TestCase` 一行都對不上，`--spec` 對 `.py` 檔會解析出 0 個案例。
2. **junit 回寫只接 Playwright**：全 `.github/workflows/` 只有 `ui-regression` 對接
   Kiwi TCMS；`ci.yml` 的 backend job 不產生也不上傳 junit 結果。TCMS 上因此**不存在**
   對應這 11 個 Python 測試的自動化案例，而 `--spec` 是**只更新、不建立**的工具。

兩者合起來的結論：本 intent 的自動化測試無法（也不該勉強）進 TCMS。要改變這件事需要動
`ci.yml`（新增 junit 產出與上傳）與 `tcms_sync.py`（新增 Python spec 解析），兩者都超出
本 intent 的範圍 —— `NFR-1` 明訂本次不動 `ci.yml`。

## 5. `team.md` 三條測試底線的判定

| 底線 | 判定 | 理由 |
|---|---|---|
| **A** — `role_permissions` 變更需 allow/deny 雙向測試 | N/A | 本次不觸及權限矩陣、角色或任何授權路徑 |
| **B** — 新增或修改 HTTP 端點需 `TestClient` 測試 | N/A | 不新增也不修改任何端點；`openapi.json` 未變 |
| **C** — 前端資料形狀變更需 e2e 斷言 | N/A | 不觸及 `frontend/`；無資料形狀變更 |
