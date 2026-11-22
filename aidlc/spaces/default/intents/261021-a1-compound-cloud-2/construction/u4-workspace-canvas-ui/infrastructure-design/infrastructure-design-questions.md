# Infrastructure Design Questionnaire — U4: u4-workspace-canvas-ui

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)
> 追溯上游基準：
> - [security-design](../nfr-design/security-design.md) (NFR4.5, NFR4.6)
> - [logical-components](../nfr-design/logical-components.md)

---

## 1. 基礎設施設計範疇說明 (Infrastructure Scope for UI Unit)

依據 `produces_kinds`，`u4-workspace-canvas-ui` 作為 `ui` 類型單元，產出：
- `infrastructure-specification.md`: 前端 SPA 靜態託管規格與 Nginx/Vite 代理設定。
- `monitoring-design.md`: 瀏覽器端渲染耗時與 Core Web Vitals 效能追蹤。
- `cicd-pipeline.md`: 前端 Vite build、TypeScript 型別檢查與 Vitest/Jest 單元測試。
- `traceability.json`: 追溯上游 `NFR4.5`, `NFR4.6`。

---

## 2. 關鍵確認問卷 (Clarifying Questions)

### Q1. 前端靜態構建與部署模式 (SPA Hosting Model)
前端 React 元件如何部署與構建？
- [A] **沿用既有 Vite build 輸出至 `frontend/dist`**：由 Nginx 提供靜態託管並代理 API 請求至後端，零架構變更。（推薦）
- [B] **獨立 SSR 伺服器部署**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出全套 UI Infrastructure Design 產物前，請確認以下彙整摘要正確無誤：

- **構建部署 (Q1)**: [A] 沿用既有 Vite build 與 Nginx 靜態託管架構。

Does this all look correct before I generate the infrastructure design artifacts for U4?
- Looks correct
- Request changes

[Answer]: Looks correct
