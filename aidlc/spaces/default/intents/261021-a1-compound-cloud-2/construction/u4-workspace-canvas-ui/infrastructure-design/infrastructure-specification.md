# Infrastructure Specification — U4: u4-workspace-canvas-ui

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)

## 1. 靜態託管規格 (Static Hosting Specification)
- **打包工具**: Vite 5.x
- **建置產物**: 靜態資源輸出至 `frontend/dist`
- **伺服器託管**: Nginx 靜態伺服器，配置 SPA fallback（`try_files $uri $uri/ /index.html`）。

