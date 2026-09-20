# Build Instructions — C1 估價上傳改版

> Intent: `260916-estimate-upload-rework` · Stage: build-and-test

## 依賴安裝

```bash
# Backend
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm ci
```

## 環境設定

- 本機：依 [`LOCAL-DEV.md`](../../../../../../LOCAL-DEV.md) 準備 `backend/.env`、`frontend/.env`（範本 `*.env.example`）。
- 部署／CI：`deploy/render-env.sh` → `deploy/.env`；測試 stack 用 `deploy/docker-compose.test.yml`。
- 隱性依賴：`claude` CLI、n8n webhook（見 LOCAL-DEV）。

## Build 指令

```bash
# Backend import / OpenAPI 健全性
cd backend && PYTHONPATH=. .venv/bin/python -c "import main; print(main.app.title)"
cd backend && PYTHONPATH=. .venv/bin/python ../scripts/dump_openapi.py --check

# Frontend production build（含 tsc）
cd frontend && npm run build
```

## Build 驗證

| 檢查 | 通過條件 |
|---|---|
| `import main` | 無例外，印出 app title |
| `dump_openapi.py --check` | exit 0 |
| `npm run build` | exit 0；產出 `frontend/dist/` |

## 常見問題

| 症狀 | 處理 |
|---|---|
| `ModuleNotFoundError: fastapi` | 使用 `backend/.venv`，勿用系統 Python 3.9 |
| vite chunk > 500kB 警告 | 已知；不阻擋 exit 0 |
| OpenAPI drift | 先跑 dump 更新再 `--check` |
