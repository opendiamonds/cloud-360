# Stage Memory: feasibility

## Interpretations

- 2026-09-16T05:20Z — CONDITIONAL stage 適用性判定：逐項對照 stage condition 三款。**整合約束**成立（引入本 repo 第一個檔案上傳面、引入 LangGraph 這條全新的模型存取路徑、既有 9 個端點與 4 張資料表需退場）；**顯著技術不確定性**成立（三朵雲官方匯出格式各異且無現成解析依賴）；**法規要求**不成立（無 PCI／HIPAA／GDPR 觸發，估價表非個資）。三款中兩款成立，執行本 stage。
- 2026-09-16T05:20Z — 不重問 intent-capture 已核可的產品邊界（完全取代、三類建議皆必備、三角色共用畫面、LangGraph 用於成本 agent、成功指標為時間）；已定案清單登錄於問題檔 [S8]。本 stage 只問解鎖可行性的整合、安全與容量張力。
- 2026-09-16T05:20Z — stage 檔範例題中的「What AWS services and accounts are currently in use?」省略：本 intent 不觸及雲端帳號，部署僅限自有 staging（ADR-0007）。「regulatory/compliance requirements」併入 Q2（檔案留存）與 Q3（內容是否送 LLM）處理，不另開題。

## Deviations

- 2026-09-16T05:21Z — 原規劃 9 題，實際問 10 題。Q10（解析靜默錯誤的處置）是在檢視 Q1–Q9 答案後補問：Q4 只處理「解析不出來」，沒有任何一題處理「解析出來但對錯了」，而後者才是會導致 agent 給出錯誤建議卻無人察覺的失敗模式。此缺口若留到設計階段才發現，代價高於多問一題。
- 2026-09-16T05:23Z — Cursor harness 無 upstream 的 PostToolUse write hook，三份 artifact 寫出後以 `aidlc-write-audit-log.ts` 手動補記 ARTIFACT_CREATED（依 project.md `## Mandated` 規則）。

## Tradeoffs

- 2026-09-16T05:23Z — RISK-01（解析靜默錯誤）的緩解在本階段只寫到「已定處置為 agent 品質檢查，但該處置無確定性保證」，不在 ideation 階段直接主張要補機械檢查。理由：機械檢查的形式（總額對帳？幣別一致性？）取決於解析器的實際資料模型，而該模型要到 domain-design 才成形。此處只保留判斷所需的事實，把決定權留給設計階段，並在 raid-log 指派負責階段。
- 2026-09-16T05:23Z — 對 Q3+Q2 的組合（本地不留檔、完整內容送第三方）與 Q10+Q9 的組合（正確性唯一防線是 LLM，而 LLM 也是時間預算裡最不可控的一段）採取「照實寫成風險，不淡化」的處理，即使兩者都是使用者知情後的選擇。已接受的風險仍須可被後續階段看見。

## Open questions

- 2026-09-16T05:23Z — ISSUE-01（P1 與 project.md M2 的規則衝突）需要一份 ADR 才能解除，但本階段無法指派負責階段——它跨在 ideation 與 construction 之間，現行 stage grid 沒有明確的 ADR 產出時點。已登錄為 DEP-04 並標註「阻擋 construction 開始」，需在 delivery-planning 或更早指派。
- 2026-09-16T05:23Z — T7（3 分鐘）是目標值而非已驗證值。ideation 階段無法實測（需要真實模型、代表性品項數、完整端到端路徑），已移交 nfr-design。若實測不可達，成功指標 P5 本身可能需要重新定義。
