# Unit Test Instructions — 260819-cost-finops（B1）

> Framework: Python `unittest` + Hypothesis（`backend/tests/`）  
> Upstream: `cost-calculator`／`cost-api`／`cost-schema-rbac` code-summary

## Setup

```bash
cd backend
pip install -r requirements.txt
export COST_PRICING_STUB=1   # test_cost_api 預設；也可 rely on setdefault
```

## Run

```bash
# 全套（CI 同形）
python3 -m unittest discover -s tests -v

# C1 子集
python3 -m unittest tests.test_cost_calculator tests.test_cost_api -v
```

## Expected Coverage（B1 新增）

| 模組 | 檔案 | 案例數 | 重點 |
|---|---|---|---|
| cost-calculator | `test_cost_calculator.py` | 6 | Hypothesis：加總、pie、邊界 |
| cost-api | `test_cost_api.py` | 5 | FinOps allow、Developer 403、422、budget 404 |
| import 邊界 | `validate_cost_calculator_boundary.py` | 1 gate | 禁 httpx/sqlalchemy/fastapi in calculator |

## Pass Criteria

- `discover -s tests`：**223/223 OK**（B1 前 212 + 11 C1）
- Hypothesis 任一 `@given` 失敗即 CI 紅
- boundary script exit 0

## Test Data

- `test_cost_api` 使用 in-memory SQLite + `make_user`／`make_diagram`（`tests/helpers.py`）
- EC2 圖 XML：`style="aws4"` + label `EC2`（對應 `sku_map.yaml`）
