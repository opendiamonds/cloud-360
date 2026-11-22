# Monitoring Design — U4: u4-workspace-canvas-ui

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)

## 1. 前端效能監控 (Client-Side Performance Tracking)
- **動畫幀率監控**: 於開發與 Staging 環境利用 `performance.now()` 追蹤 250ms fitWindow 動畫執行週期，標定 dropped frame 異常。
- **渲染耗時**: 記錄 XML 接收至 DOM 渲染完成耗時。

