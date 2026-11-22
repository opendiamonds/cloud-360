# CI Configuration — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: ci-pipeline (3.7) · Phase: Construction · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. CI 管線概述

專案採用 GitHub Actions 進行持續整合（`.github/workflows/ci.yml`），由 `scripts/validate_repo_contract.py` 守護專案合約與標準品質檢查。

本次「混合雲架構圖」新增功能與現有 CI 工作流程無縫整合，涵蓋：
1. **靜態合約檢查 (Repo Contract Guard)**:
   - 確保無未經授權的生產環境機敏設定洩漏。
   - 繁體中文 commit 訊息格式校驗。
2. **後端自動化測試**:
   - 執行 `unittest` 自動探索與執行，包括 `backend/tests/test_diagram_builder_compound.py`、`backend/tests/test_design_agent.py` 與 `backend/tests/test_diagram_icons.py`。
3. **前端建置與型別檢查**:
   - 執行 `tsc -b && vite build`，確保前端 TypeScript 零型別錯誤與打包建置成功。

---

## 2. CI Workflow 整合矩陣

```yaml
jobs:
  validate:
    name: Repo Contract & Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate Repo Contract
        run: python3 scripts/validate_repo_contract.py

  backend-test:
    name: Backend Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Run Compound Cloud Tests
        run: |
          PYTHONPATH=backend python3 -m unittest \
            backend/tests/test_diagram_builder_compound.py \
            backend/tests/test_design_agent.py \
            backend/tests/test_diagram_icons.py

  frontend-build:
    name: Frontend Build & Typecheck
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v1
      - name: Install & Build
        run: |
          bun install --cwd frontend
          bun run --cwd frontend build
```

