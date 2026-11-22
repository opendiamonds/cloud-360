# Performance Design — U4: u4-workspace-canvas-ui

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)

## 1. 前端動畫效能設計 (Performance Architecture)
- 採用 CSS `transition: transform 250ms cubic-bezier(0, 0, 0.2, 1); will-change: transform;` 觸發瀏覽器 Compositor 硬體加速圖層，確保在 4K 畫布縮放時維持 60 FPS。

