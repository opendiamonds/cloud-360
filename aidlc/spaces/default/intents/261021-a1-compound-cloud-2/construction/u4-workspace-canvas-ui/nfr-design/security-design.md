# Security Design — U4: u4-workspace-canvas-ui

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)
> 追溯上游基準：
> - [security-requirements](../nfr-requirements/security-requirements.md) (NFR4.5, NFR4.6)

## 1. 前端安全架構 (Security Architecture)
- 於 `window.addEventListener("message", ...)` 處理常式嚴格校驗 `event.origin` (NFR4.5)，非受信任來源直接跳出，防杜惡意外部頁面偽造 postMessage 指令。
- 遵循專案 CSP 策略 (NFR4.6)，Draw.io iframe 限制於授權 sandbox 邊界內運行。
