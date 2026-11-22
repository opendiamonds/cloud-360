# Discovered Rules — Cloud-360

> Stage: practices-discovery (2.2) · Phase: Inception · Scope: feature
> 記錄專案層級硬性約束規則。

## Mandated

- **ALWAYS** 對每一項變更檢查 ADR-0006 security baseline 的四個面向（IAM、encryption、network exposure、audit logging）。涉及 IAM／權限矩陣／網路暴露／稽核記錄的變更，必須在該 stage 產出中明列 security 影響與處置。
- **ALWAYS** 在向 n8n 請求混合雲服務圖示時發送 `provider = "compound"`，且在 n8n 異常時提供灰底 fallback 容錯。
- **ALWAYS** 在混合雲架構繪圖中採用 Hub-and-Spoke 空間佈局與直角折線跨雲連線，確保三雲群組與協議標籤邊界清楚。

## Forbidden

- **NEVER** 繞過既有 `doreen/feat/*` 分支命名與繁體中文 Conventional Commits 規範。
- **NEVER** 在 `design_agent.py` 中向 Agent 開放 Bash、Read、Write、Edit 等檔案系統與命令列權限（僅允許 `draw_architecture_diagram` 行程內 MCP tool）。
- **NEVER** 引入未經驗證的外部依賴套件或硬編碼憑證至程式碼庫。
