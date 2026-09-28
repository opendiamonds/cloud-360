# CI/CD Pipeline — cost-calculator

> Unit: `cost-calculator` · library · embedded backend

## 1. 管線位置

| Job | 步驟 | 本 unit |
|---|---|---|
| `ci.yml` → `backend` | `python -m unittest discover -s tests -v` | `test_cost_calculator.py` Hypothesis |
| `ci.yml` → `repo-contract` | `validate_repo_contract.py` + **新增** cost import gate | 禁 httpx/sqlalchemy/fastapi in `cost_calculator.py` |
| `docker-build` | 建 backend image | calculator 隨 `backend/` COPY，無獨立 image |

## 2. 新增 CI 契約（code-generation 交付）

```bash
# scripts/validate_cost_calculator_boundary.py（或併入 validate_repo_contract）
python3 scripts/validate_cost_calculator_boundary.py
```

失敗條件：`backend/cost/cost_calculator.py` 出現禁用 import。

## 3. 不引入

- 獨立 package publish
- 前端 build 步驟
- 新 GitHub secrets

## 4. B1 / B2

同一 CI 路徑；B2 不增 calculator 管線。

## 5. Code Gen 檢查清單

- [ ] unittest 全綠
- [ ] import boundary 腳本在 repo-contract job
