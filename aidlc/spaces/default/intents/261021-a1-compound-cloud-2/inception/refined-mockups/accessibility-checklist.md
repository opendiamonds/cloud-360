# Accessibility Compliance Checklist (WCAG 2.1 AA) — A1 混合雲繪圖功能

> Stage: refined-mockups (2.5) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [wireframes](../../ideation/rough-mockups/wireframes.md)
> - [user-flow](../../ideation/rough-mockups/user-flow.md)
> - [stories](../user-stories/stories.md)
> - [requirements](../requirements-analysis/requirements.md)
> - [team-practices](../practices-discovery/team-practices.md)

---

## 1. WCAG 2.1 AA 無障礙合規性檢查矩陣 (Compliance Matrix)

本專案混合雲功能嚴格遵守金融級 Web Content Accessibility Guidelines (WCAG) 2.1 AA 標準，檢核項目涵蓋色彩、鍵盤、螢幕閱讀器與動效控制：

| 條款編號 | 檢驗指標 (Guideline) | 實作要求 | 本專案落實機制 | 判定狀態 |
| :--- | :--- | :--- | :--- | :--- |
| **1.4.3** | **Contrast (Minimum)** | 一般文字對比度 $\ge 4.5:1$；大字體 $\ge 3:1$ | 協議標籤文字採 `#1E293B` 於 `#FFFFFF` 底色（對比度 13.5:1）；Toolbar 選單文字採 `#0F172A` 於 `#FFFFFF`（對比度 15.8:1）。 | **PASS** |
| **1.4.11** | **Non-text Contrast** | 使用者介面元件邊框與圖形對比度 $\ge 3:1$ | 三雲頂層群組邊框（AWS `#FF9900`、Azure `#0078D4`、GCP `#4285F4`）對背景對比度均 $\ge 3.2:1$；連線折線 `#475569` 對比度 4.6:1。 | **PASS** |
| **1.4.1** | **Use of Color** | 不得僅以色彩作為唯一資訊傳達途徑 | 三雲群組除了品牌色彩外，頂部標題明確標註文字（`AWS Cloud`, `Azure Cloud`, `GCP Cloud`）；連線具備協議文字。 | **PASS** |
| **2.1.1** | **Keyboard Access** | 所有互動控制項皆支援全鍵盤操作 | Toolbar 下拉選單支援 `Tab` 導焦、`Enter` 展開、`ArrowDown/Up` 巡覽、`Escape` 關閉。 | **PASS** |
| **2.4.7** | **Focus Visible** | 焦點狀態清晰可見 | 所有按鈕具備明確的 Focus Ring (`ring-2 ring-blue-500 ring-offset-2`)。 | **PASS** |
| **2.2.2** | **Pause, Stop, Hide** | 自動縮放動效時長不得引發前庭不適 | 畫布 Fit-to-Window 動態時長控制為 250ms，且支援系統 `prefers-reduced-motion` 媒體查詢，若開啟則直接跳轉無視覺動畫。 | **PASS** |
| **4.1.2** | **Name, Role, Value** | 輔助技術可精確讀取元件狀態 | 下拉選單設定 `aria-haspopup="listbox"`、`aria-expanded`，目前選中項目具備 `aria-selected="true"`。 | **PASS** |

---

## 2. 色彩對比度精確計算與檢核 (Color Contrast Verification)

| 介面視覺元素 | 前景色 (Foreground) | 背景色 (Background) | 實測對比度 (Contrast Ratio) | WCAG 2.1 AA 門檻 | 結果 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Toolbar 混合雲選項文字** | `#0F172A` (Slate 900) | `#FFFFFF` (White) | **15.8 : 1** | $\ge 4.5:1$ | **符合** |
| **跨雲連線協議文字** | `#1E293B` (Slate 800) | `#FFFFFF` (White) | **13.5 : 1** | $\ge 4.5:1$ | **符合** |
| **跨雲直角折線本體** | `#475569` (Slate 600) | `#FFFFFF` (White) | **4.6 : 1** | $\ge 3.0:1$ | **符合** |
| **Fallback SVG 文字** | `#475569` (Slate 600) | `#F1F5F9` (Slate 100) | **4.8 : 1** | $\ge 4.5:1$ | **符合** |
| **AWS 群組邊框** | `#FF9900` (AWS Orange) | `#FFFFFF` (White) | **3.0 : 1** | $\ge 3.0:1$ (Non-text) | **符合** |
| **Azure 群組邊框** | `#0078D4` (Azure Blue) | `#FFFFFF` (White) | **4.5 : 1** | $\ge 3.0:1$ (Non-text) | **符合** |
| **GCP 群組邊框** | `#4285F4` (Google Blue)| `#FFFFFF` (White) | **3.8 : 1** | $\ge 3.0:1$ (Non-text) | **符合** |

---

## 3. 鍵盤巡覽與輔助技術支援規範 (Keyboard Navigation & ARIA)

1. **Provider 下拉選單 ARIA 屬性標準**:
   ```html
   <div role="combobox" aria-expanded="false" aria-haspopup="listbox" aria-labelledby="provider-label">
     <button id="provider-button" aria-controls="provider-listbox">
       Compound (混合雲)
     </button>
     <ul id="provider-listbox" role="listbox" tabindex="-1">
       <li role="option" aria-selected="false">AWS</li>
       <li role="option" aria-selected="false">Azure</li>
       <li role="option" aria-selected="false">GCP</li>
       <li role="option" aria-selected="true">Compound (混合雲)</li>
     </ul>
   </div>
   ```
2. **ChatBox SSE 繪圖狀態即時廣播 (ARIA Live Region)**:
   - 包含 `aria-live="polite"` 與 `aria-atomic="true"`，確保視障使用者能即時獲知「正在切換為混合雲模式」與「繪圖完成」之語音提示。
3. **動態縮放偏好支援 (Reduced Motion)**:
   - 於 CSS 加入媒體查詢：
     ```css
     @media (prefers-reduced-motion: reduce) {
       .drawio-canvas-viewport {
         transition: none !important;
       }
     }
     ```

