# A1 Core Gap Fill — Clarification Questions

> Unit: A1 User Story 核心補齊  
> Branch: `luojingting/refactor/a1-agent-sdk-openrouter`（或另開 feat）  
> 目的：對齊 User Story A1 核心 AC／操作流程／系統回饋；不含 A3 Well-Architected 真功能、不含多角色留言協作（偏 A2）  
> **Plan 已合併至** `a1-agent-sdk-code-generation-plan.md`（Phase 2 / Step 7–8）

請在各題 `[Answer]:` 後填入選項字母（可多題一次回覆，例如 `1.A 2.B 3.A`）。

### Question 1
「User Story A1 核心」這次要補哪些？

A) **全套核心**：AC 強化（prompt）+ 產圖後自動存檔 +「全部重置」畫布 + 成功／失敗回饋文案與引導按鈕  
B) **僅 UX／流程**：自動存檔 + 全部重置 + Toast／引導（不改 prompt）  
C) **僅產圖品質**：強化 system prompt（WAF／Aurora／HA、VPC／AZ／連線），不動前端流程  
D) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2
產圖成功後的「自動存檔」行為？

A) 已有 `diagram_id` → 自動 PUT 更新 XML；尚無圖 → 自動建立（標題可用「架構草圖 YYYY-MM-DD」或對話摘要）  
B) 已有 `diagram_id` 才自動存；尚無圖只 Toast，仍要使用者手動「儲存架構圖」  
C) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 3
「全部重置」與現有「清空對話」如何區分？

A) **兩顆按鈕**：「清空對話」（只清 chat，A4）+「全部重置」（清畫布 XML，可選一併清 chat；有 diagram 則寫回空／預設 XML）  
B) **一顆「全部重置」**：同時清畫布 + 對話（取代或合併現有清空對話）  
C) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 4
成功／失敗引導按鈕（「生成 IaC」「Well-Architected 評估」「聯絡架構師」）？

A) **UI 就緒、功能 stub**：點擊顯示「即將推出」Toast（對齊 story 文案，不接真頁）  
B) **只改文案**：成功／失敗 Toast 對齊 story；不加重複 CTA 按鈕  
C) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 5
是否現在就批准執行（依 Q1–Q4 答案寫短 plan 並改 code）？

A) 批准，依我的答案直接實作  
B) 先出短 plan 檔再等我回 A 批准  
C) 取消  
D) Other (please describe after [Answer]: tag below)

[Answer]: B
