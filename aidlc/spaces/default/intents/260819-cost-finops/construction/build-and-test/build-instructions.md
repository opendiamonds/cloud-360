# Build Instructions — 260819-cost-finops（B1）

> Consumes: 五 unit `code-generation/code-summary.md`

## Prerequisites

| 項目 | 版本／備註 |
|---|---|
| Python | 3.12+（CI 用 3.x；本機 3.13 已驗） |
| Node.js | 22（CI）；本機 20+ 可建 |
| PostgreSQL | 本機 dev 或 `deploy/docker-compose.test.yml` |
| Playwright | `npx playwright install chromium`（e2e 首次） |

## Dependency Install

```bash
cd backend && pip install -r requirements.txt
cd frontend && npm ci
```

## Environment

| 範圍 | 來源 | C1 相關 |
|---|---|---|
| 本機 dev | `backend/.env`（範本 `backend/.env.example`） | 可選 `COST_PRICING_STUB=1` 免外網查價 |
| CI test stack | `deploy/docker-compose.test.yml` | 內嵌 `COST_PRICING_STUB=1` |
| 部署 | `deploy/.env`（`render-env.sh`） | **不**設定 stub；走 Price List 或 miss |

`scripts/validate_env_contract.py` 要求 backend 讀到的變數皆列於 `backend/.env.example`。

## Build Commands

```bash
# Frontend：lint + API 型別 drift + tsc + vite
cd frontend && npm run lint && npm run check:types && npm run build

# Backend：無 compile；import smoke + unittest
cd backend && python3 -c "import main"
python3 -m unittest discover -s tests -v

# OpenAPI 漂移
cd backend && DATABASE_URL=sqlite:///tmp/o.db JWT_SECRET=test \
  python3 scripts/dump_openapi.py --check

# Repo／env／calculator 邊界
python3 scripts/validate_repo_contract.py
python3 scripts/validate_env_contract.py
python3 scripts/validate_cost_calculator_boundary.py
```

## Verification Checklist

1. 上述命令皆 exit 0
2. `openapi.json` 含 `/api/cost/*` 且與 `dump_openapi.py --check` 一致
3. test stack 起來後 Playwright 成本區塊 5/5 綠

## Troubleshooting

| 現象 | 處理 |
|---|---|
| `validate_env_contract` 缺變數 | 補 `backend/.env.example` + `LOCAL-DEV.md` |
| cost PUT hours 404 | 確認 `get_snapshot()` 已 commit（B1 修正） |
| 成本頁空列表 | FinOps 無 A1.edit 看不到自有圖；e2e 用 Project_Architect |
| Playwright 無 browser | `npx playwright install chromium` |
