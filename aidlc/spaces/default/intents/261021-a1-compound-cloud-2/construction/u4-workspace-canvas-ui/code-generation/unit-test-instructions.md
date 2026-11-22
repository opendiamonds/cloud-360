# Unit Test Instructions — U4: u4-workspace-canvas-ui

> Stage: code-generation (3.5) · Phase: Construction · Scope: feature · Depth: Standard
> Unit: `u4-workspace-canvas-ui` (kind: `ui`)

---

## 1. 測試框架與環境設置 (Test Framework & Environment Setup)

- **框架**: TypeScript / Vite (`tsc --noEmit` & `npm run build`)
- **檔案路徑**: `frontend/src/pages/WorkspacePage.tsx`, `frontend/src/components/DrawioCanvas.tsx`
- **執行環境**: Node.js / Bun (`/opt/homebrew/bin/bun` 或 `npm`)

---

## 2. 單元執行指令 (Unit-Scoped Test Command)

在執行任何驗證前，確保執行以下專屬此前端單元的編譯與型別檢查指令：

```bash
cd frontend && npm run build
```

---

## 3. 測試範圍與覆蓋率目標 (Coverage Targets & Test Cases)

- **目標**: TypeScript 型別檢查 0 errors，Vite 建置 0 warnings。
- **功能驗證清單**:
  1. Provider 選單切換至 `compound` 時狀態正確更新且標籤高對比度符合 WCAG AA。
  2. 生成帶有多雲拓撲之 XML 時觸發 `fitWindow` 自適應畫布縮放 postMessage。
  3. ChatBox 支援多雲混合雲架構範例導引。

