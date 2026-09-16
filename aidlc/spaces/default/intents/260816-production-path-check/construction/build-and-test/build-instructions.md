# Build Instructions — 260816-production-path-check

- Intent：`260816-production-path-check`（issue #509）
- 上游：`<record>/construction/production-path-check/code-generation/code-generation-plan.md`、同目錄的 `code-summary.md`
- Test Strategy：**Minimal**（`aidlc-state.md` 第 18 行）

> **上游路徑註記**：本 stage 的 directive 把 consumes 解析成字面的
> `construction/{unit-name}/code-generation/…`（placeholder 未展開）。bugfix scope 無
> unit-of-work，實際落點是 `construction/production-path-check/code-generation/`。
> 成因與交接說明見 `<record>/construction/code-generation/memory.md` 的 Open questions。

## 前置條件

| 項目 | 需求 | 驗證 |
|---|---|---|
| Python | 3.13（`backend/.venv`） | `backend/.venv/bin/python -V` |
| Node | 專案 `package-lock.json` 對應版本 | `node -v` |
| git | 需在 git 工作樹內 | `git rev-parse --is-inside-work-tree` |

**git 是本次變更新增的硬依賴面**：`validate_no_production_config_added()` 改用 `git ls-files`，
而新增的回歸測試會 `git init` 暫存 repo。在無 `git` 或非 git 目錄執行時，
`subprocess.run(..., check=True)` 會拋例外而非靜默通過 —— 這是刻意的（fail fast，
不讓檢查在拿不到檔案清單時假裝通過）。

**依賴安裝**（本次未新增任何依賴，NFR-2）：

```bash
cd backend  && python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cd frontend && npm ci
```

## 建置與驗證指令

依 `.github/workflows/ci.yml` 的四個 job 逐一對應，順序即 CI 的實際順序：

```bash
# job 1: repo-contract
python3 scripts/validate_repo_contract.py
python3 scripts/validate_env_contract.py

# job 2: frontend（lint + tsc -b + build）
cd frontend && npm run lint && npm run build

# job 3: backend（import smoke + unit tests）
cd backend && ./.venv/bin/python -c "import main; print('app:', main.app.title)"
cd backend && ./.venv/bin/python -m unittest discover -s tests -v

# job 4: docker-build（buildx 建兩個 image，push: false）
```

`npm run build` 內含 `tsc -b`，型別檢查隨建置觸發，沒有獨立的 typecheck 指令。

## 疑難排解

**`npm run lint` 出現 3 個 warning 是既有狀態，不是本次引入。** 三處皆為
`react-hooks/exhaustive-deps`（`AssessmentPage.tsx:365`、`LoginPage.tsx:36`、
`WorkspacePage.tsx:301`）。CI 只擋 error（`npm run lint` 未加 `--max-warnings 0`），
exit code 為 0。

> `team.md` `## Code Style` 記的第三處是 `WorkspacePage.tsx:279`，**實測已漂移到 301**。
> 檔案與規則相同，只是行號過期。本次變更未觸及前端，故不在此修改 `team.md`
> （該段落受 practices-discovery gate 治理），僅如實記載供下一輪覆核。

**系統 `python3` 跑不動後端測試套件是既有狀況。** 24 個測試模組中 17 個因缺
`sqlalchemy`／`hypothesis`／`fastapi`／`jwt`／`starlette` 而 import 失敗。一律使用
`backend/.venv/bin/python`。唯一的例外是本次新增的
`test_repo_contract_production_paths.py` —— 它零非標準庫依賴，兩個直譯器下都能跑。

**`validate_repo_contract.py` 若在 CI 紅燈**，先確認是哪一項檢查：本次修改的
`validate_no_production_config_added()` 現在會回報**版控中所有**違規路徑，
不再只看未提交的變更。若它擋下了合理的檔案，那是語意由「不得新增」轉為
「不得存在」的預期後果，處理方式是討論豁免機制（見 `requirements.md` 的開放問題），
**不是把它改回 diff 基準** —— 那會讓這道檢查回到 CI 恆為 no-op 的狀態。
