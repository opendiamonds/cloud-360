# Code Generation Plan — 禁止 production 路徑的 contract 檢查修正

- Intent：`260816-production-path-check`
- Scope：bugfix（無 unit-of-work；bugfix scope 依設計跳過 units-generation 與 application-design）
- 依據：`<record>/inception/requirements-analysis/requirements.md`（FR-1～FR-10、NFR-1～NFR-3、AC-1～AC-6）
- 測試策略：Minimal（bugfix scope）—— 針對該缺陷的回歸測試，既有測試維持全綠

## 追溯（計畫步驟 ↔ 需求）

| 步驟 | 實作需求 | 驗收標準 |
|---|---|---|
| Step 1 | FR-1、FR-2、FR-3、FR-4、NFR-2 | AC-1、AC-2 |
| Step 2 | FR-8、FR-9、FR-10 | AC-1、AC-2、AC-6 |
| Step 3 | Definition of Done（突變驗證） | — |
| Step 4 | FR-6、FR-7 | AC-5 |
| Step 5 | FR-5、NFR-1、NFR-3 | AC-3、AC-4、AC-6 |

> 本 intent 無 user story（bugfix 由 GitHub issue #509 直接驅動），故追溯的上游是 FR/AC 而非 story id。

---

## Step 1 — 修正 `scripts/validate_repo_contract.py`

- [ ] 新增 `git_ls_files()` helper，沿用既有 `git_diff_name_only()` 的形狀（`subprocess.run(..., cwd=ROOT, check=True, text=True, capture_output=True)`），不引入新依賴（NFR-2）
- [ ] 改寫 `validate_no_production_config_added()`：比對基準由 `git diff --cached ∪ git diff` 改為 `git ls-files` 全域掃描（FR-2）
- [ ] 保留既有的 `Path(path).parts` 精確 path-part 比對邏輯，**不改為子字串比對**（FR-3）
- [ ] 保留違規時列出所有路徑並回傳非 0 的行為（FR-4）
- [ ] 更新函式 docstring：寫明改為全域掃描的原因（CI 是乾淨 checkout，diff 兩集合皆空，原檢查恆為 no-op），讓下一個讀者不會把它改回 diff 基準

**不改**：`FORBIDDEN_NEW_PATH_PARTS` 的內容、其他任何 contract 檢查、`.github/workflows/ci.yml`（NFR-1）。

## Step 2 — 回歸測試 `backend/tests/test_repo_contract_production_paths.py`

- [ ] 檔案落點為 `backend/tests/`，檔名 `test_*.py`（FR-8 —— 唯一會被 `ci.yml:135` 的 `python -m unittest discover -s tests` 探索到的 Python 測試落點）
- [ ] 模組 docstring 註明：它測的是 repo 根目錄的 `scripts/validate_repo_contract.py`，放在此處是因為這是 CI 唯一的 Python 測試探索路徑
- [ ] 以 `importlib.util.spec_from_file_location` 載入受測腳本（避免污染 `sys.path`）
- [ ] 每個測試在 `tempfile.TemporaryDirectory()` 內 `git init` 一個隔離 repo，commit 測試檔案後 **patch 受測模組的 `ROOT`** 指向該暫存目錄（FR-9、FR-10）
- [ ] git 身分以 `-c user.email=` / `-c user.name=` 逐次傳入，不依賴也不修改使用者的全域 git 設定
- [ ] 測試案例：
  - [ ] **AC-1**：乾淨工作樹（commit 後無 staged／unstaged）+ 版控中有 `deploy/production/config.yml` → 回傳非 0，且輸出含該路徑
  - [ ] **AC-2**：版控中有 `agents/aidlc-product-agent.md`、`docs/secrets-policy.md` 等含子字串但非完整 path part 的檔案 → 回傳 0，不誤擋
  - [ ] **AC-1 補強**：`prod` 與 `secrets` 各自作為完整 path part 的情境（三個禁用詞逐一覆蓋，不只測 `production`）
  - [ ] 乾淨且無違規的 repo → 回傳 0

## Step 3 — 突變驗證

- [ ] 把 Step 1 的修正暫時還原為原本的 diff 基準，重跑 Step 2 的測試，**確認 AC-1 的測試轉為紅燈**
- [ ] 確認紅燈原因是「未偵測到違規」而非 import／fixture 錯誤（否則等於測試根本沒測到東西）
- [ ] 還原修正，確認回到綠燈
- [ ] 依 `test-case-authoring.md` §5：沒看過它紅過，就不算寫完

## Step 4 — 規則層同步

- [ ] **FR-6**：`aidlc/spaces/default/memory/project.md` 的 `## Forbidden` —— 語意由「不得**新增**」改為「不得**存在**」，並註明檢查方式為 `git ls-files` 全域掃描
- [ ] **FR-7**：`aidlc/spaces/default/memory/team.md` 的 `## Deployment` → 「已知的規則宣稱與機制落差」小節，**三處一併改**：
  - [ ] 開頭句「現有**兩條**規則…」→ 單數
  - [ ] 刪除「禁止 production 路徑」該條 bullet
  - [ ] 收尾句「**這兩項**不是『缺工具』…**本輪不逕自變更腳本行為**」→ 單數，且不再宣稱不變更腳本行為
- [ ] 依 AC-5 **通篇重讀**該段落確認無內部矛盾（不能只做字串刪除就宣告完成）

> Step 4 涉及 `team.md` 的 gate 治理段落，已於 requirements-analysis 的 Q3 取得人工確認，並在 `requirements.md`「關於編輯 `team.md` 的權限」記明為有意識的例外、非先例。

## Step 5 — 驗證

- [ ] `python3 scripts/validate_repo_contract.py` → exit 0（AC-3、FR-5）
- [ ] `python3 scripts/validate_env_contract.py` → exit 0
- [ ] `cd backend && python -m unittest discover -s tests` → 新測試被探索到且全綠（AC-6），既有測試維持全綠
- [ ] `git diff --name-only` 確認 `.github/workflows/ci.yml` **不在**變更清單（AC-4）
- [ ] 計時 `validate_no_production_config_added()` 單次執行 < 1 秒（NFR-3）

## 不做的事

- 不改 `.github/workflows/ci.yml`（NFR-1）
- 不改 `FORBIDDEN_NEW_PATH_PARTS` 的內容
- 不順手修 `validate_no_obvious_secrets()` 的掃描範圍（範圍邊界明列為獨立問題）
- 不修改 `discovered-rules.md`（屬另一個 intent 的 record；列入完成摘要待辦）
- 不建立任何 path part 含 `prod`／`production`／`secrets` 的**真實**檔案 —— 測試情境只存在於暫存目錄（FR-9）
