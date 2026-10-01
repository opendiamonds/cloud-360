# Build Instructions — A3 LangGraph refactor

> Intent `261001-a2-langgraph` · Minimal · brownfield

## 依賴安裝

```bash
cd backend
python3 -m venv .venv   # 若尚無
source .venv/bin/activate
pip install -r requirements.txt   # 含 langgraph、langchain-openai
```

## 環境

- 本機：`backend/.env`（需 `OPENROUTER_API_KEY` 才跑真 LLM；單元測試 mock，不需真金鑰）
- 部署：`deploy/render-env.sh` → `deploy/.env`（見 DEPLOY.md）
- 映像**不再**需要 Node／Claude Code CLI

## 建置／驗證

```bash
# Import smoke
cd backend && .venv/bin/python -c 'from main import app; print("app_ok")'

# （可選）前端型別
cd frontend && npm ci && npx tsc -b --pretty false
```

## 疑難

| 症狀 | 處理 |
|---|---|
| `No module named langgraph` | 使用 `backend/.venv` 並 `pip install -r requirements.txt` |
| 容器內找不到 claude CLI | 預期行為；A3 已改 OpenRouter／LangGraph |
