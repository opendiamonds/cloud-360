# A3 User Stories Revision — Plan & Questions

> Stage: Inception → User Stories（revision）  
> Scope: `stories.md` §A3（中／英）  
> Requirements: `requirements/a3-well-architected-requirements.md`（已核准）


### 評估結論
執行 **User Stories 修訂**（見 `user-stories-assessment.md`）。

### 執行檢查清單（Part 2）

- [x] 修訂 `stories.md` 中文 §A3：AC 分 **本期 MVP**／**下期**；補入口；規則＋LLM；持久化；AWS 為主預留多雲
- [x] 同步修訂 English Version §A3
- [x] 調整操作流程／系統回饋／BDD 對齊 MVP
- [x] 微調 A1「後續引導」Well-Architected 銜接 A3（中／英）
- [x] Q4=D：不連動 personas／SRS／unit-of-work（待 Units Generation）
- [x] 更新 `aidlc-state`／`audit`（本回合）

---

## Question 1
A3 故事結構要怎麼改？

A) **維持單一 A3**：用狀態標記（✅ 本期／⏳ 下期）改寫現有 AC

B) **拆成 A3a／A3b**：A3a＝MVP 評核；A3b＝PDF＋SPOF 模擬（下期）

C) 維持單一 A3，但 AC 只寫 MVP；全文理想能力移到「Future」小節

D) Other (please describe after [Answer]: tag below)

[Answer]:Ａ

### Question 2
產圖後「Well-Architected」引導與工作區按鈕，故事裡要怎麼寫？

A) 兩者都寫進 A3 操作流程（產圖後 CTA ＋ 工作區按鈕 ＋ 儀表板）

B) 產圖後 CTA 寫在 **A1** 後續引導；A3 只寫工作區按鈕＋儀表板

C) 只強調儀表板（對齊舊文）；按鈕／CTA 留待 FD

D) Other (please describe after [Answer]: tag below)

[Answer]:Ａ

### Question 3
Hannah／Fiona 協作敘述在 MVP 怎麼處理？

A) 保留雙角色：MVP 改為「同一報告檢視不同支柱／發現」；SPOF 協作標 ⏳ 下期

B) MVP 以單一發起者為主；Fiona 審核標 ⏳

C) 維持原文協作（含 SPOF），僅 AC 列表標期別

D) Other (please describe after [Answer]: tag below)

[Answer]:Ａ

### Question 4
改完 `stories.md` 後還要連動哪些？（可複選，例如 `A,B`）

A) 只改 `stories.md`

B) `personas.md`（若評核流程敘述需對齊）

C) `cloud-360-srs.md` 最佳實踐相關段落（標 MVP）

D) 暫不連動；等 Units Generation 再改 unit-of-work

E) Other (please describe after [Answer]: tag below)

[Answer]:Ｄ

### Question 5
雙語？

A) 中文與 English **同步改**

B) Other (please describe after [Answer]: tag below)

[Answer]:Ａ
