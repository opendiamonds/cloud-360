# Performance Requirements — U4: u4-workspace-canvas-ui

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)

## 1. 前端效能指標 (UI Performance Targets)
- **縮放過渡動畫**: 250ms ease-out，維持 60 FPS 流暢度。
- **DOM 解析與排版延遲**: 收到 XML 後 50ms 內完成渲染並發起 fitWindow。

