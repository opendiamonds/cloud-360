# Refined Mockups Questionnaire & UX Design Plan — A1 混合雲繪圖功能

> Stage: refined-mockups (2.5) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [wireframes](../../ideation/rough-mockups/wireframes.md)
> - [user-flow](../../ideation/rough-mockups/user-flow.md)
> - [stories](../user-stories/stories.md)
> - [requirements](../requirements-analysis/requirements.md)
> - [team-practices](../practices-discovery/team-practices.md)

---

## 1. 互動模式與畫面情境 (Interaction Patterns & Scenarios)

本階段將 Ideation 階段的粗略線框 (Rough Mockups) 精化為高保真 (Mid-to-High Fidelity) 互動規格，鎖定以下 4 個核心 UI 畫面與互動狀態：

1. **Screen 1: WorkspacePage 畫布頂部 Toolbar 與 Provider 切換器**
   - 狀態：預設單一雲狀態、下拉選單展開狀態、Compound 選中狀態。
2. **Screen 2: ChatBox 智能對話與混合雲意圖識別**
   - 狀態：輸入自然語言多雲需求、Agent 意圖識別提示、SSE 串流繪圖狀態提示。
3. **Screen 3: DrawioCanvas 混合雲全貌渲染與自動 Fit-to-Window**
   - 狀態：三雲獨立群組佈局（中央 AWS 480px、兩側 Azure/GCP 各 360px、緩衝走廊 120px）、250ms 平滑縮放、直角折線與協議膠囊標籤。
4. **Screen 4: n8n 服務異常容錯狀態 (Resilience / Fallback State)**
   - 狀態：圖示載入中狀態、5.0 秒逾時/500 錯誤後灰底文字向量 SVG Fallback 狀態。

---

## 2. 設計問卷 (UX Design Questions)

### Q1. Toolbar 混合雲入口呈現型態 (Toolbar Provider Selector)
在 WorkspacePage 頂部工具列中，混合雲 (Compound) 選項應如何呈現？
- [A] 維持既有 Provider 下拉選單 (Dropdown)，於 AWS / Azure / GCP 下方新增「混合雲 (Compound)」選項，點擊後即時切換。（推薦，維持既有介面風格且節省工具列水平寬度）
- [B] 改為分段按鈕 (Segmented Control)，將 AWS、Azure、GCP、Compound 並列展示。
- [C] 尚未決定。

[Answer]: [A]

### Q2. Chat 對話多雲意圖識別反饋機制 (Chatbot Multi-Cloud Intent Feedback)
當使用者在 ChatBox 輸入多雲意圖（如「跨 AWS 與 GCP」），後端自動調用 Compound 模式時，前端介面應如何給予反饋？
- [A] Toolbar 之 Provider 下拉選單自動同步切換為 Compound，且 ChatBox 輸出訊息開頭包含「已為您切換至混合雲繪圖模式」，給予使用者清晰反饋。（推薦）
- [B] 僅後台默默切換，不顯示任何提示文字。
- [C] 跳出 Modal 確認視窗詢問使用者是否確定切換。

[Answer]: [A]

### Q3. 畫布最佳視角縮放與動態參數 (Fit-to-Window Animation & Padding)
依據 Reviewer 審查建議 R-01，巨型混合雲 XML 渲染完成後自動觸發 Fit-to-Window，其動畫時長與留白邊距應如何設定？
- [A] 動畫過渡時長設定為 250ms ease-out，畫布四周預留 32px 安全邊距 (Padding)，確保視角切換流暢無瞬切跳動。（推薦）
- [B] 無動態過渡，立即瞬切縮放，留白邊距 10px。
- [C] 不自動縮放，維持目前使用者的既有縮放比例，由使用者手動調整。

[Answer]: [A]

### Q4. 跨雲連線與協議標籤視覺樣式 (Cross-Cloud Edges & Protocol Badges)
依據 Reviewer 審查建議 R-02，跨雲連線之協議標籤在視覺與無障礙上應如何規範？
- [A] 連線採用直角折線 (Orthogonal Routing)；協議標籤位於折線中點，文字採深灰 (#1E293B)，外覆純白膠囊圓角背景 (#FFFFFF, border: 1px solid #CBD5E1)，對比度 > 7:1，完全符合 WCAG 2.1 AA。（推薦）
- [B] 標籤文字直接浮於折線上，無底色遮罩。
- [C] 不顯示協議名稱，僅保留折線。

[Answer]: [A]

### Q5. n8n 圖示服務逾時之 Fallback SVG 視覺標準 (Fallback SVG Visual Standards)
當向 n8n 請求圖示遭遇 5.0 秒逾時或 HTTP 異常時，灰底向量 SVG Fallback 元件應具備何種視覺外觀？
- [A] 採標準 40x40 灰底方塊 (#F1F5F9)，中央繪製服務名稱首字母或簡稱（#475569 深灰色字體），四角圓角 4px，搭配細邊框 (#94A3B8)，兼具品牌可讀性與產圖穩定性。（推薦）
- [B] 顯示紅色警告圖示標註錯誤。
- [C] 留空不繪製圖示。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 mockups.md、interaction-spec.md、design-system-mapping.md 與 accessibility-checklist.md 前，請確認以下彙整摘要正確無誤：

- **Toolbar 呈現 (Q1)**: [A] 既有 Provider 下拉選單新增「混合雲 (Compound)」選項，維持介面一致性。
- **對話回饋 (Q2)**: [A] ChatBox 識別多雲意圖自動切換，並於對話串提示「已切換至混合雲模式」。
- **畫布縮放 (Q3)**: [A] Fit-to-Window 動態時長 250ms ease-out，四周 padding 保留 32px。
- **連線與標籤 (Q4)**: [A] 直角折線 + 中點純白膠囊底色協議標籤（對比度 > 7:1）。
- **容錯圖示 (Q5)**: [A] 灰底向量 SVG Fallback（#F1F5F9 底色 + #475569 文字），兼顧合規與連續性。

Does this all look correct before I generate the refined mockups artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct
