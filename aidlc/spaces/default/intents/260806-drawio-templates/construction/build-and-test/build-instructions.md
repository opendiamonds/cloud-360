# Build Instructions

## Dependency Installation Steps
- 本專案採用 Python 虛擬環境管理後端依賴。
- 於 `backend/` 目錄下執行：
  ```bash
  pip install -r requirements.txt
  ```

## Environment Setup
- 複製 `backend/.env.example` 為 `backend/.env` 並填入必要的環境變數。
- 主要設定包括 `N8N_WEBHOOK_URL` 與 `OPENROUTER_API_KEY`（若需要調用 LLM）。

## Build Commands
- 本專案為 Python / FastAPI 與 React 前端專案，無須編譯步驟。後端可以直接以啟動服務進行驗證。

## Build Verification Steps
- 執行以下指令驗證後端基本合規性：
  ```bash
  python3 scripts/validate_repo_contract.py
  ```
