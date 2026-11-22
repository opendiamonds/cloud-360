# CI/CD Pipeline — U4: u4-workspace-canvas-ui

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)
> 追溯上游基準：
> - [security-design](../nfr-design/security-design.md) (NFR4.5, NFR4.6)

## 1. 前端構建與測試管線 (Frontend Build & Test Pipeline)
- **環境**: Node.js 20 GitHub Actions Runner
- **命令**:
  - `npm run lint` (ESLint 程式碼風格校驗)
  - `npm run build` (TypeScript 編譯與 Vite 打包產物確認)
  - `npm test` (元件渲染與 ProviderSelect 切換測試)

