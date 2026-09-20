# Security Test Instructions — 260819-cost-finops（B1）

> NFR：SEC-C-1（calculator 純度）、RBAC C1、定價 URL allowlist  
> Upstream: `cost-calculator`／`cost-api` nfr-requirements

## Static Gates

```bash
python3 scripts/validate_cost_calculator_boundary.py
python3 scripts/validate_repo_contract.py   # 禁 secrets、繁中 record
python3 scripts/validate_env_contract.py    # 三環境不混用
```

## RBAC（team 底線 A + Q3）

| 測試 | 位置 |
|---|---|
| FinOps GET /api/cost/diagrams → 200 | `test_cost_api.py` |
| Developer → 403 | 同上 |
| C1 種子 44 列 | `schema_rbac.sql` + 啟動補丁 |

手動：無 C1.view 角色不可見 `/cost`（CapabilityRoute → `/403`）。

## Network Exposure

| 模式 | 驗證 |
|---|---|
| `COST_PRICING_STUB=1` | 零 outbound pricing HTTP（test stack） |
| 非 stub | 僅 `pricing_urls.yaml` allowlist host；3s timeout |

禁止：在 calculator 內 import httpx；在 n8n 路徑打 Price List。

## Pass Criteria

- boundary + env + repo contract 全綠
- TestClient deny case 存在且通過
