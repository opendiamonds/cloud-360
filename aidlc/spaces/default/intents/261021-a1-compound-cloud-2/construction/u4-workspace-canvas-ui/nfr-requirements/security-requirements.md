# Security Requirements — U4: u4-workspace-canvas-ui

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)

## 1. 前端安全需求 (UI Security Targets)
- **postMessage 來源校驗 (NFR4.5)**: 驗證來源 origin 僅為同一網域或受信任之 Draw.io 靜態資源。
- **CSP 規範 (NFR4.6)**: 符合專案安全基線，禁止非受信任的外部腳本載入。
