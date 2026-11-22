# Team & Mob Allocation — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: delivery-planning (2.9) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [bolt-plan](bolt-plan.md)
> - [unit-of-work](../units-generation/unit-of-work.md)
> - [contributions](../user-stories/contributions/)

---

## 1. 代理人團隊分派總覽 (Mob Allocation)

依據本專案之 AI-DLC 執行配置（Stage 1.5 Team Formation 標定為跳過，採單一自主 AI 代理人矩陣）：所有 Bolt 之程式碼生成、架構實作與測試檔撰寫，統一由 `aidlc-developer-agent` 擔任主責開發代理人（Primary Developer），並由各領域專業代理人協同驗證。

| Bolt ID | Bolt Name | 主責代理人 (Lead Mob) | 協同與審查代理人 (Support Mobs) | 交付範疇 |
| :--- | :--- | :--- | :--- | :--- |
| **Bolt 1** | `bolt-icon-gateway` | `aidlc-developer-agent` | `aidlc-quality-agent` (Mock 測試與 Fallback 驗證) | 後端圖示 I/O 與網路逾時處理 |
| **Bolt 2** | `bolt-diagram-builder` | `aidlc-developer-agent` | `aidlc-architect-agent` (幾何佈局審查)、`aidlc-quality-agent` (幾何斷言測試) | 混合雲 mxGraph 幾何核心函式庫 |
| **Bolt 3** | `bolt-design-agent` | `aidlc-developer-agent` | `aidlc-architect-agent` (Agent 提示詞與 RBAC 契約) | Agent 服務層與對話 Tool 擴充 |
| **Bolt 4** | `bolt-workspace-canvas` | `aidlc-developer-agent` | `aidlc-design-agent` (WCAG 2.1 對比度與 UI 動效) | 前端 React 元件與 Draw.io 畫布整合 |

---

## 2. 責任邊界與交接協議 (Handoff Agreements)

1. **單一代理人無縫交接**:
   - 由於所有 Bolt 皆由主系統代理人統一在整合工作區實作，無需跨人工作業等待時間，但嚴格遵循「前一 Bolt 測試通過始得推進下一 Bolt」之原則。
2. **測試驅動驗收 (Quality Agent Gate)**:
   - 每個 Bolt 產出後，必須在 Stage 3.6 Build and Test 執行本地自動化測試，確認現有功能不受回歸影響。

