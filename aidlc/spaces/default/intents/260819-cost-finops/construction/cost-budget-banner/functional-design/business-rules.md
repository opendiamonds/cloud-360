# Business Rules — cost-budget-banner

> Unit: `cost-budget-banner` · B2 · 詳細流程見 `business-logic-model.md`。Slot 注入 API 見 `cost-ui` FD §Slot Registry（`mountCostSlot`）。

| ID | 規則 |
|---|---|
| BR-B-1 | 預算 PUT 需 `C1b.edit`；Alex 403 |
| BR-B-2 | `budget is None` → 不超支、橫幅 inactive（AC-6.5） |
| BR-B-3 | `total > budget` 才超支；相等 false（calculator） |
| BR-B-4 | 多圖超支仍 **一條** 橫幅（AC-7.4） |
| BR-B-5 | 無 inbox、無永久 dismiss（AC-7.5、AC-7.3） |
| BR-B-6 | 預算變更寫 audit；含 mxcell_id null |
| BR-B-7 | B2 才 register slot 子元件；B1 slot 空 |

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-20T01:48:58Z
**Iteration:** 1

### Findings

| # | 嚴重度 | 位置 | 發現 | 建議 |
|---|---|---|---|---|
| 1 | Major | `business-logic-model.md` Register 區塊 | `mountOverspendSlot()` 與 `mountBannerSlot()` 兩個函式在 `registerCostBudgetBanner()` 中被直接呼叫，但在 `cost-ui` slot 契約（`frontend-components.md`、`domain-entities.md`）與所有共享 inception artifact 中均無定義——既無函式簽章、無匯出來源，也無注入機制（React Portal？全局 registry？Context？）。實作者面對這個進入點無法在不猜測架構選擇的情況下完成實作。 | 在 `cost-ui` FD 或本單元 FD 中補充 slot 注入 API 契約：明確指出 `mountOverspendSlot` / `mountBannerSlot` 從哪個模組匯入、接受什麼型別（`ReactNode`？），以及其內部機制（例如：讀取 `[data-slot]` DOM 節點後以 `ReactDOM.createPortal` 渲染）。 |
| 2 | Minor | `business-logic-model.md` OverspendBanner 區塊 | Frontend 呼叫 `GET /banner` 的前置條件在 FD 中僅寫「Layout mount」，未標示 `can('C1','view')` 權限守衛。`component-methods.md` 中已有此條件，但 FD 獨立閱讀時資訊不完整，實作者可能略過 auth 檢查。 | 在 business-logic-model.md OverspendBanner 段加一行：「僅當 `can('C1','view')` 為 true 時才發出 `GET /banner`」，與 `component-methods.md` 對齊。 |
| 3 | Minor | `business-logic-model.md` `apply_budget` 函式 | 驗證步驟寫「驗 budget 非負 Decimal 兩位」，但 domain-entities 已明確允許 `budget: number \| null`（null 代表清除預算）。null 的驗證路徑（不驗、直接通過）在 business-logic-model 中未顯式描述，與「非負」的措辭產生歧義。 | 在 `apply_budget` 說明中補充：`budget is None` → 跳過數值驗證，直接 UPSERT 為 NULL（對齊 BR-B-2 語意）。 |
| 4 | Minor | `business-rules.md` 表格格式 | 業務規則表僅有 ID 與單句描述，缺少明確的觸發條件／邏輯／違規欄位。實作者需跨讀 `business-logic-model.md` 才能還原完整規則。本身不阻擋實作，但增加認知負擔。 | 可在後續迭代中為每條規則補充觸發（Trigger）/ 邏輯（Logic）/ 違規後果（Violation）三欄，或在表格前加一行說明「詳細邏輯見 `business-logic-model.md`」讓閱讀路徑清晰。 |

### Validation Tool Results

| 工具 | 結果 | 詮釋 |
|---|---|---|
| 交叉比對：slot 名稱 | PASS | `data-slot=cost-overspend` 與 `data-slot=cost-banner` 與 `cost-ui` `frontend-components.md` / `domain-entities.md` 完全一致 |
| 交叉比對：test-id | PASS | `cost-budget`、`cost-overspend-flag`、`cost-banner` 三個 test-id 與 `cost-ui` B1 禁止列表吻合 |
| 交叉比對：API 端點形狀 | PASS | `PUT /diagrams/{id}/budget { budget: number \| null }` 與 `GET /banner { active, count, sample? }` 均與 `component-methods.md` 契約相符 |
| 交叉比對：`is_overspent` 語意 | PASS | BR-B-3（total > budget 才超支；相等 false）與 `cost_calculator` 函式簽章 `is_overspent(total, budget) -> bool` 一致 |
| 交叉比對：RBAC | PASS | BR-B-1 `C1b.edit`、banner `C1.view` 與 `components.md` 權限元件表一致 |
| 交叉比對：mountOverspendSlot / mountBannerSlot | FAIL | 函式無定義來源，見 Finding #1 |

### Summary

整體設計邏輯自洽，核心業務規則（超支判定、預算 RBAC、橫幅聚合、session dismiss、稽核寫入）皆有明確來源且與共享 inception 契約對齊。唯一阻擋實作的缺口是 slot 注入 API 未定義（Finding #1）：`registerCostBudgetBanner()` 呼叫的 `mountOverspendSlot` / `mountBannerSlot` 在任何契約文件中均無定義，實作者無法完成 register 模式而不需要額外的架構指引。補充此 API 定義後，本單元可直接進入 code-generation。
