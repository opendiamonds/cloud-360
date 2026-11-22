# NFR Design Questionnaire — U4: u4-workspace-canvas-ui

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)
> 追溯上游基準：
> - [security-requirements](../nfr-requirements/security-requirements.md) (NFR4.5, NFR4.6)
> - [functional-spec](../functional-design/functional-spec.md)

---

## 1. 單元非功能設計邊界說明 (NFR Design Scope for UI Unit)

本單元 `u4-workspace-canvas-ui` 為前端 UI 元件，產物包含：
1. **performance-design.md**: 250ms CSS GPU 硬體加速過渡動畫規格。
2. **security-design.md**: postMessage 雙向校驗白名單。
3. **logical-components.md**: 前端 UI 元件與 hook 架構。

---

## 2. 非功能設計關鍵問卷 (Clarifying Questions)

### Q1. postMessage 來源白名單校驗模式 (Origin Whitelisting Pattern)
在監聽 Draw.io iframe 回傳之事件時如何校驗？
- [A] **限制 `event.origin === window.location.origin`**：僅接受同源或受信任白名單，其餘來源直接 return 忽視。（推薦）
- [B] **不校驗 origin**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 UI NFR Design 產物前，請確認以下彙整摘要正確無誤：

- **來源校驗 (Q1)**: [A] 限制 `event.origin === window.location.origin`。

Does this all look correct before I generate the NFR design artifacts for U4?
- Looks correct
- Request changes

[Answer]: Looks correct
