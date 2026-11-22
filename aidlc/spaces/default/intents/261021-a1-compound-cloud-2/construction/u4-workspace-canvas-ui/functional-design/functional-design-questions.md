# Functional Design Questionnaire — U4: u4-workspace-canvas-ui

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u4-workspace-canvas-ui` (kind: `ui`)
> 追溯上游基準：
> - [unit-of-work](../../../inception/units-generation/unit-of-work.md)
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C4)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR1.1~FR1.3, NFR5, CON3)
> - [stories](../../../inception/user-stories/stories.md) (US1.1~US1.3)

---

## 1. 單元實作職責與前端介面說明 (Functional Scope & UI Components)

本單元 `u4-workspace-canvas-ui` 負責前端畫布與工具列操作元件：
- **主要檔案**: `frontend/src/pages/WorkspacePage.tsx`, `frontend/src/components/Toolbar.tsx`, `frontend/src/components/DrawioCanvas.tsx`
- **Toolbar 擴充**: Provider 下拉選單新增「混合雲 (Compound)」。
- **意圖聯動**: 接收 SSE 多雲繪圖事件後自動同步更新 Toolbar Provider 狀態為 `compound`。
- **視窗自動適應 (Fit-to-Window)**: 在 Draw.io XML 載入後 250ms 內平滑平移並縮放至全視窗可見（四周邊距 $\ge 20\text{px}$，預設 32px）。

---

## 2. 功能細部設計關鍵問卷 (Clarifying Questions)

### Q1. Provider 下拉選單之視覺鍵值 (Toolbar Option Key-Value)
在 `Toolbar.tsx` 中新增混合雲選項時，其 value 與 label 定義為何？
- [A] **`{ value: "compound", label: "混合雲 (Compound)" }`**：與後端 C1/C4 合約小寫 `compound` 保持完全一致。（推薦）
- [B] **`{ value: "multi-cloud", label: "Multi-Cloud" }`**。

[Answer]: [A]

### Q2. 畫布自適應縮放之觸發時機與通訊協定 (Fit-to-Window Protocol)
DrawioCanvas 接收到 XML 並渲染於 iframe 後，如何觸發縮放？
- [A] **透過 postMessage 發送 `{"action": "fitWindow", "padding": 32}`**：在收到 XML 載入完成通知後，延遲 50ms（等待 DOM 排版）發送 fitWindow 訊息，動畫過渡時長 250ms ease-out。（推薦）
- [B] **以手動滾輪縮放**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `frontend-components.md`、`rules.md`、`functional-spec.md` 與 `traceability.json` 前，請確認以下彙整摘要正確無誤：

- **Toolbar 選項 (Q1)**: [A] `{ value: "compound", label: "混合雲 (Compound)" }` 精確對齊後端合約。
- **縮放通訊協定 (Q2)**: [A] postMessage `fitWindow` (padding=32px, 250ms ease-out 平滑過渡)。

Does this all look correct before I generate the functional design artifacts for U4?
- Looks correct
- Request changes

[Answer]: Looks correct
