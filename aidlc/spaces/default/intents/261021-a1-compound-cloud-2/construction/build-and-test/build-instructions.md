# Build Instructions — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: build-and-test (3.6) · Phase: Construction · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 系統建置環境契約

- **後端執行環境**:
  - Python 3.12 (虛擬環境路徑: `.venv/bin/python3`)
  - 核心相依套件: FastAPI, Pydantic, SQLAlchemy, httpx, Starlette
  - 執行前環境變數配置: `PYTHONPATH=backend`
- **前端建置環境**:
  - Node/Bun 執行環境 (路徑: `/opt/homebrew/bin/bun`)
  - 前端工具鏈: Vite v8.3.1, TypeScript 5.x (`tsc -b`)
  - 前端專案路徑: `frontend/`

---

## 2. 逐步建置指引

### 2.1 後端檢查與驗證
在專案根目錄下驗證後端語法與型別無衝突：
```bash
PYTHONPATH=backend .venv/bin/python3 -c "import services.diagram_builder; import services.design_agent; print('Backend modules loaded successfully')"
```

### 2.2 前端編譯建置
在專案根目錄下使用 Bun 執行前端 TypeScript 編譯與生產打包：
```bash
/opt/homebrew/bin/bun run --cwd frontend build
```
預期產出：
- `dist/index.html`
- `dist/assets/index-*.js`
- `dist/assets/index-*.css`
- 驗證標準：`0 errors`, `0 warnings`

