# Build Instructions — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: build-and-test（Construction）· 上游：全部 12 個單元的 code-generation-plan.md 與 code-summary.md -->

## 「build」在本 intent 的意義

本 intent 的交付物**沒有編譯產物**。code-generation 交付的 10 個 composite action、7 支
workflow 與 23 支 `.sh`／`.py`（見各單元 `code-summary.md` 的「交付物與實際行數」）全部由
GitHub Actions runner 直接執行，不經 transpile、bundle 或打包。

因此本階段的「build」由**三件實際存在的事**構成，逐一在下方給指令：

| # | 實際的建置動作 | 何時需要 | 產物 |
| --- | --- | --- | --- |
| B-1 | 執行環境備妥（python3 ＋ PyYAML ＋ bash） | 每次要跑本 intent 的任何測試 | 無（環境） |
| B-2 | gh-aw `.lock.yml` 重新編譯 | **只有**在改動四支 gh-aw workflow 的 `.md` 時 | `.github/workflows/{ui-regression,pr-reviewer,lint-fix,contract-guard}.lock.yml` |
| B-3 | 既有應用程式建置（frontend／backend） | 每次 PR（既有 `ci.yml` 的 job） | `frontend/dist/` 等既有產物 |

**B-3 對本 intent 是回歸驗證，不是本 intent 的產物**：`git status` 顯示本 intent 未觸及
`backend/` 或 `frontend/` 的任何檔案。跑它的理由是 brownfield 的 Test Validation
安全網（`.claude/knowledge/aidlc-shared/brownfield.md`），不是因為它會產生新東西。

## B-1：執行環境

### 依賴清單（實測，非推測）

| 依賴 | 版本要求 | 誰需要它 | 查證方式 |
| --- | --- | --- | --- |
| `python3` | 3.9+ | 全部 18 支 `.py` | 全數使用 `from __future__ import annotations`；本機實測環境為 3.13.7 |
| **PyYAML** | 任意近期版本 | **8 支腳本** | 本機實測 6.0.3；下方列出是哪 8 支 |
| `bash` | **3.2 為底線** | 5 支 `.sh` 與三支 impl workflow | 五支 `.sh` 的檔頭逐字宣告不使用關聯陣列／`mapfile`／`${var^^}`；本機 GNU bash 3.2.57 全綠 |
| `gh` CLI | 2.x | **只有 live 測試層**與 workflow 執行期 | 本機實測 2.96.0 |
| `gh aw` | **必須是 `v0.81.6`** | 只有 B-2 | 見 B-2 的警告 |

需要 PyYAML 的 8 支：

```
.github/actions/aidlc-sync-ci-guard/check-ci-yml.py
.github/actions/aidlc-sync-ci-guard/run-probe-tests.py
.github/actions/aidlc-sync-forward/run-live-tests.py
.github/actions/aidlc-sync-forward/run-orchestration-tests.py
.github/actions/aidlc-sync-reconcile/run-reconcile-tests.py
.github/actions/aidlc-sync-reverse/run-reverse-tests.py
.github/actions/aidlc-sync-selftest/check-agentic-steps.py
.github/actions/aidlc-sync-selftest/run-selftest-tests.py
```

### 安裝

```bash
python3 -m pip install --user pyyaml
```

**PyYAML 在 GitHub runner 上是否預裝，本階段無法實測**——這一項是 U-9 交還清單第 5 項
逐字登錄的未驗證項（`aidlc-sync-selftest.yml` 第一段依賴 `actions/setup-python@v5`）。
它會在 Bolt 4 的首次真實 CI 執行時得到答案，本階段不臆測。

### 環境變數

離線層（stub／fixture／behaviour）**不需要任何環境變數**——這是刻意的設計，見 U-1 的
`code-summary.md`：邏輯與 YAML 介面分離，使「零 I/O」是可測的事實而非宣稱。

live 層的變數見 `integration-test-instructions.md`，不在建置範圍。

## B-2：gh-aw `.lock.yml` 重新編譯

### 觸發條件

**只有**改動下列四支 `.md` 的**任何內容（含 frontmatter 內的純註解）**時才需要：

```
.github/workflows/ui-regression.md
.github/workflows/pr-reviewer.md
.github/workflows/lint-fix.md
.github/workflows/contract-guard.md
```

實測依據（U-10b `code-summary.md:41`）：`frontmatter_hash` 對 frontmatter 的**任何**文字
變動都敏感——只改一行註解文字，hash 由 `804bda34…` 變為 `381ec1ed…`。

### 指令

```bash
# 必須是 v0.81.6。本機預設的 gh aw 是 v0.86.2，直接用它會夾帶供應鏈升級。
<釘住的 v0.81.6 binary> compile ui-regression pr-reviewer lint-fix contract-guard
```

> **不要加 `--dir`**（U-10b 的 Step C 實測形狀）。

### 為什麼版本必須釘住 —— 這是本階段最容易踩的一顆雷

U-10b 逐項實測的對照：

| 用哪個編譯器 | 每檔 diff | manifest 變動 |
| --- | --- | --- |
| **v0.81.6（正確）** | 恰 **4 行**（1 行舊 metadata ＋ 1 行新 metadata ＋ 2 行 `paths-ignore`） | **0 行** |
| v0.86.2（本機預設，錯誤） | 每檔 526 行 | `actions/cache` v5.0.5→v6.1.0、`actions/checkout` v7.0.0→v7.0.1、`actions/setup-node` v6.4.0→v7.0.0、防火牆容器 0.27.11→0.27.44、`gh-aw-mcpg` v0.3.30→v0.4.9、`github-mcp-server` v1.4.0→v1.9.0 |

依 ADR-0006，那六個新 SHA 與映像各需安全審查——**用錯版本重編等於在一個看似無關的
PR 裡夾帶六項未審查的供應鏈變更**。

### 驗證重編沒有夾帶東西

```bash
git diff --stat .github/workflows/*.lock.yml     # 期望：每檔 4 行
git diff .github/workflows/*.lock.yml | grep -c 'gh-aw-manifest'   # 期望：0
git diff .github/workflows/*.lock.yml | grep 'compiler_version'    # 期望：無輸出（該欄未變）
```

**已知缺口**：`check-paths-relations.py` 的 `COMPILED:` 檢查驗的是 `paths-ignore` 這條
glob 的一致性，**不驗 `compiler_version`** ⇒ 沒有任何機械檢查擋得住「有人用較新的
gh-aw 重編」。此為 U-10b 交還 gate 的第 5 項，處置由 gate 決定，本階段只如實記載。

## B-3：既有應用程式建置（回歸用）

```bash
# frontend
cd frontend && npm ci && npm run lint && npx tsc -b && npm run build

# backend（無 build step，只有 import smoke）
cd backend && python3 -c "import main"
```

兩者都由既有 `ci.yml` 的 `frontend` 與 `backend` job 承載，本 intent 未改動它們的內容
（只在 `ci.yml` 加了 U-10a 的 `gate` job 與四個 job 的 `if:`）。

## 建置驗證

建置沒有產物可比對，所以「建置成功」由下列三組**可執行的檢查**定義，全部指令與實測
結果見 `build-test-results.md`：

1. 兩支 repo 合約驗證器（`scripts/validate_repo_contract.py`、`scripts/validate_env_contract.py`）
2. 兩支靜態檢查器（`check-ci-yml.py`、`check-agentic-steps.py`、`check-paths-relations.py`）
3. 14 組離線測試套件（見 `unit-test-instructions.md`）

## 疑難排解

| 症狀 | 原因 | 處置 |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'yaml'` | 上表 8 支腳本之一缺 PyYAML | `python3 -m pip install --user pyyaml` |
| 重編後 lock 檔 diff 是數百行 | 用了本機的 v0.86.2 而非釘住的 v0.81.6 | `git checkout -- .github/workflows/*.lock.yml` 後改用正確版本 |
| `.sh` 在某台機器報語法錯誤而本機正常 | 該機的 `bash` 更舊，或 `sh` 而非 `bash` | 五支 `.sh` 的底線是 bash 3.2；確認是用 `bash` 而非 `sh` 執行 |
| live 測試回 `exit 3` 並印 `SKIP：…` | **這不是失敗**，是憑證不存在時的明確跳過 | 見 `integration-test-instructions.md`；離線層不受影響 |
| 三支 impl workflow 的測試在本機表現與 CI 不同 | GitHub 對未指定 `shell:` 的 `run:` 用 `bash -e {0}` | harness 已以 `AIDLC_*_BASH` 對齊；細節見 `unit-test-instructions.md` 的「harness 與 CI 語意對齊」 |

## 與上游的對應

交付物清單與行數引自 12 個單元的 `code-summary.md`；gh-aw 版本釘住的實測證據引自
U-10b 的 `code-generation-plan.md` 與 `code-summary.md`；bash 3.2 底線引自五支 `.sh` 的
檔頭宣告（本站實讀）；PyYAML 於 runner 上的可用性未驗證一事引自 U-9 的 `code-summary.md`
交還清單第 5 項；`ci.yml` 的 job 結構變更引自 U-10a 的 `code-generation-plan.md`。
