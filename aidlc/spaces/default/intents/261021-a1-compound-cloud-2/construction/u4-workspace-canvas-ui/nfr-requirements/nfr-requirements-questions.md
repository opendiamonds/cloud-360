# NFR Requirements Questionnaire — U4: u4-workspace-canvas-ui

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)
> 追溯上游基準：
> - [functional-spec](../functional-design/functional-spec.md)
> - [rules](../functional-design/rules.md)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (NFR1, NFR5)

---

## 1. 單元非功能需求邊界說明 (NFR Scope for UI Unit)

依據 `produces_kinds`，`u4-workspace-canvas-ui` 作為 `ui` 單元，需要評估：
1. **Performance**: 縮放動畫嚴格限制 250ms ease-out，DOM 渲染不卡頓（幀率維持 60 FPS）。
2. **Security**: Content Security Policy (CSP) 防護，防止 Draw.io iframe 遭受 clickjacking 或惡意腳本注入。
3. **Tech Stack**: React 18, TypeScript, Vite, Tailwind CSS。

---

## 2. 非功能性需求關鍵問卷 (Clarifying Questions)

### Q1. 畫布動效與幀率保護 (Animation Frame Rate & Performance)
在執行 250ms fitWindow 視窗縮放動畫時，如何確保不掉幀？
- [A] **使用 CSS `transform: scale() translate()` GPU 硬體加速**：透過 `requestAnimationFrame` 與硬體加速圖層進行變形過渡，避免頻繁引發重排 (Reflow)。（推薦）
- [B] **使用 JavaScript setInterval 計算**。

[Answer]: [A]

### Q2. 無障礙性色弱與對比規範 (Accessibility & High Contrast)
前端 Toolbar 與標籤之對比度標準為何？
- [A] **全面符合 WCAG 2.1 AA**：文字對比 $\ge 4.5:1$，圖形/標籤元件對比 $\ge 3:1$，支援鍵盤 Tab 鍵焦點巡覽。（推薦）
- [B] **僅遵循預設瀏覽器對比度**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 UI NFR 產物前，請確認以下彙整摘要正確無誤：

- **動效效能 (Q1)**: [A] 250ms CSS GPU 硬體加速縮放，保證 60 FPS 無卡頓。
- **無障礙性 (Q2)**: [A] 嚴格達成 WCAG 2.1 AA 對比度與鍵盤焦點支援。

Does this all look correct before I generate the NFR requirements artifacts for U4?
- Looks correct
- Request changes

[Answer]: Looks correct
