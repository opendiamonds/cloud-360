# Integration Test Instructions — C1 估價上傳改版

> Test Strategy: **Standard** · 跨 unit 邊界與契約

## 框架

- Backend：`unittest` + `TestClient`（與 CI 一致；不引入 pytest）
- 契約／邊界：repo 驗證腳本
- E2E：Playwright（`tests/e2e/estimate-workspace.spec.ts`，需 test stack）

## 指令

```bash
# 全後端 suite（含跨 unit：intake ↔ parser ↔ pricing ↔ advice ↔ langgraph）
cd backend && PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v

# 邊界／契約
python3 scripts/validate_repo_contract.py
python3 scripts/validate_env_contract.py
python3 scripts/validate_cost_calculator_boundary.py
python3 scripts/validate_pricing_lookup_boundary.py

# E2E（可選；需 deploy/docker-compose.test.yml 於 :8090）
cd frontend && BASE_URL=http://localhost:8090 npx playwright test tests/e2e/estimate-workspace.spec.ts
```

## 覆蓋期望

| 邊界 | 期望 |
|---|---|
| U1↔U2 解析→intake | unittest 綠；非法檔拒絕 |
| U2↔U5 pricing | pricing boundary validator exit 0 |
| U3 legacy 退役 | cost calculator boundary exit 0；無舊 HTTP |
| U6↔U7 graph→advice | langgraph + cost_advice unittest 綠 |
| U8↔U9 SPA＋SSE | Playwright estimate-workspace 綠（stack 就緒時） |

## 測試資料

- CSV fixtures：`frontend/tests/e2e/fixtures/`（估價表樣本）
- TestClient：記憶體／SQLite 測試 DB（各 test module helpers）
