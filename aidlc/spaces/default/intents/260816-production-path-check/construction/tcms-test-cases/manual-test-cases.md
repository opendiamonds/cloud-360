# 手動測試案例 — 禁止 production 路徑的 contract 檢查修正

> Intent：`260816-production-path-check`（issue #509）
> 由 `tcms-test-cases` stage 產出。本檔是手動案例的**授權來源**，同步工具讀的就是它。

## 本 intent 的手動案例數：0

**這不是漏寫，是分桶判定的結果。** 依 `test-case-authoring.md` §1 的判準，「不能或不該
自動化」只有四種情形：每跑一次要花錢（LLM 路徑）、依賴 CI 無法保證的外部服務、需要人的
判斷、需要真實環境殘值。本 intent 的受測對象是 `scripts/validate_repo_contract.py` 的
禁止路徑檢查 —— 一支不連網、不呼叫 LLM、不讀環境變數、只跑 `git ls-files` 並比對字串的
腳本。四種情形一項都不成立。

同一份標準的 §1 也明文禁止重複覆蓋：「能，而且已經有腳本 → **不寫手動案例**。重複覆蓋
沒有加分。」自動化層已斷言的行為若再寫一份手動案例，等於製造兩個真實來源，其中一份
必定悄悄過期 —— 那正是 `operation/test-case-management-plan.md` 要防的事。

因此本檔**不含任何 `## TC:` 案例**。逐項判定見下方覆蓋盤點；未寫成腳本的項目列為
open item 並附理由，不藏進「等人去手動測」。

---

## 覆蓋盤點

外部可觀察行為共 **14 項**。分桶結果：

| 桶 | 數量 |
|---|---|
| 已自動化 | 10 |
| 待自動化 —— 本 stage 已寫出腳本 | 1 |
| 待自動化 —— 本輪未寫（gate 決定，列為 open item） | 3 |
| 只能手動 | **0** |
| 無法分類 | **0** |

### 已自動化（10 項）

自動化落點：`backend/tests/test_repo_contract_production_paths.py`，
CI 以 `python -m unittest discover -s tests` 探索（`.github/workflows/ci.yml`）。

| # | 外部可觀察行為 | 斷言它的測試 |
|---|---|---|
| B-1 | 已 commit 的 `production` 完整 path part，在**乾淨工作樹**下回傳 1 並列出該路徑 | `test_detects_production_directory_on_clean_worktree` |
| B-2 | `prod` 完整 path part 同樣被擋 | `test_detects_prod_directory_on_clean_worktree` |
| B-3 | `secrets` 完整 path part 同樣被擋 | `test_detects_secrets_directory_on_clean_worktree` |
| B-4 | 違規 path part 是**檔名本身**（非目錄）時同樣被擋 | `test_detects_forbidden_part_as_filename` |
| B-5 | 比對不分大小寫（`Production`） | `test_matching_is_case_insensitive` |
| B-6 | 多個違規全數列出，不只第一個 | `test_reports_every_violation_not_just_the_first` |
| B-7 | 子字串不誤擋（`aidlc-product-agent.md`、`secrets-policy.md` 等真實檔名） | `test_substring_matches_are_not_violations` |
| B-8 | 未追蹤（未 `git add`）的暫存檔不被掃描 | `test_untracked_file_is_not_scanned` |
| B-9 | 無違規的乾淨 repo 回傳 0 且不輸出訊息 | `test_clean_repo_without_violations_passes` |
| B-10 | 真實 repo 全樹（794 個追蹤檔）掃描通過 | CI `repo-contract` job 直接執行 `python3 scripts/validate_repo_contract.py`；本機實測 exit 0 |

> `test_fixture_worktree_is_clean` 不列入上表：它守的是 fixture 自身（工作樹必須乾淨才
> 重現得了 CI 條件），不是產品行為。它是讓其餘測試不會空洞通過的承載件。

### 待自動化 —— 本 stage 已寫出腳本（1 項）

| # | 外部可觀察行為 | 腳本 |
|---|---|---|
| B-11 | CI 的 shallow checkout（`fetch-depth: 1`）下，`git ls-files` 仍列出全部追蹤檔，違規照樣被擋 | `TestShallowCloneScan::test_violation_in_unfetched_commit_is_still_detected`（**本 stage 新增**） |

細節與突變驗證見 `automation-test-plan.md`。

### 待自動化 —— 本輪未寫（3 項，open item）

三項皆已提到核可關卡，使用者選擇本輪只寫 B-11。**它們留在「待自動化」桶，不轉手動**
—— 轉手動會把「還沒寫測試」偽裝成「有人會去測」。

| # | 外部可觀察行為 | 未寫的理由 | 若它壞掉會怎樣 |
|---|---|---|---|
| B-12 | `main()` 的 `checks` tuple 真的包含 `validate_no_production_config_added` | gate 決定本輪不寫 | 有人把它從 tuple 移除時，現有 11 個測試與 CI 全數維持綠燈 —— 與 #509 同一種靜默失效形狀 |
| B-13 | 非 git 工作樹下 `subprocess(check=True)` 拋 `CalledProcessError` 而非靜默回 0 | gate 決定本輪不寫 | 有人加 `try/except` 吞掉例外，就退回「拿不到檔案清單就假裝通過」 |
| B-14 | NFR-3：真實 repo 全掃 < 1 秒 | gate 決定本輪不寫；時間類斷言在共用 runner 上有 flaky 疑慮 | 無自動防迴歸；build-and-test 已實測 0.0151s（門檻的 1/60），但那是一次性量測 |

### 不屬於「外部可觀察的系統行為」（明列，不靜默省略）

- **規則文件的宣稱改寫**（`CLAUDE.md` 第 4 章、`project.md ## Forbidden`、`team.md`
  的落差記載）：文件內容不是系統行為，沒有可執行的預期結果。repo contract 的
  `REQUIRED_TEXT` 只鎖通用 token（`validate_repo_contract.py`、`Scope Overrides` 等），
  本次新寫的具體語句（「`git ls-files` 全域掃描」「path-part 精確比對」）**無機械保護**，
  由 gate 的人工審查承擔。如實記載，不假裝它被測到。

---

## 追溯

- 實作：`scripts/validate_repo_contract.py` 的 `git_ls_files()` 與 `validate_no_production_config_added()`
- 自動化：`backend/tests/test_repo_contract_production_paths.py`（11 個測試）
- Issue：#509 · Branch：`danniel/fix/production-path-check-noop`
- User story：無（issue 驅動的 bugfix scope，`user-stories` stage 依 scope 設定跳過）
