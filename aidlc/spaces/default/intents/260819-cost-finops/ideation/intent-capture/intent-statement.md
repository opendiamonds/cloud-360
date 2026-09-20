# Intent Statement — 成本估算與 FinOps（C1 第一輪）

<!-- Stage: intent-capture（Ideation 1.1）· 來源標籤定義見 intent-capture-questions.md 的 ## Sources。
     每個實質主張都掛有來源標籤；未掛標籤的內容不得存在。 -->

## Problem Statement

- 目前成本數字靠試算表或口頭估，無法對到架構圖上的實際資源，報價不可信 [Q1]
- 原始請求為：實作成本估算與 FinOps，從 C1 TCO／流量預算預測做起，再及於 C2 定價模型與 C3 Data Egress；第一輪先做到從架構圖擷取資源、查詢雲端報價、以圓餅圖拆解 TCO，並允許覆寫每日運作時數 [desc]
- 觸發是使用者故事 C1–C3 已寫、A 柱產圖後需要銜接「查看預估成本」，而非已發生的超支事故 [Q4]

## Target Customer

| 受益者 | 獲得什麼 | Source |
| --- | --- | --- |
| 雲端架構師 | 產圖後得到可對外說明、且能對到圖上資源的成本數字；超支時在成本畫面看到視覺標示，並在進入產品時看到站內通知 | [Q2] [Q5] [Q11] [Q16] |
| FinOps 分析師 | 可重算、可拆解的月費數字；能設定預算上限；官方 API 缺價或失敗時可覆寫單價並標記 Manual Override；超支時在成本畫面看到視覺標示，並在進入產品時看到站內通知 | [Q5] [Q10] [Q11] [Q15] [Q16] |
| 工程主管 | 架構變更造成的預算影響可見；超支時在成本畫面看到視覺標示，並在進入產品時看到站內通知 | [Q5] [Q10] [Q11] [Q16] |

開發／維運被確認為 stakeholder（在意實作與維護成本、以及估價過程不要碰到雲端供應商 production），但未被確認為本能力的直接使用者，亦非超支警告的收件人，故不列為上表受益者 [Q5] [Q11] [memory:M2]

## Success Metrics

- 能從架構圖擷取資源、以雲端官方報價 API 查出報價、以圓餅圖顯示每項資源成本與總額，並可用「每日運作時數」重算每月總費用 [desc] [Q3] [Q12]
- 官方報價 API 缺價或失敗時，單價可人工覆寫並標記 Manual Override [Q15]
- 可設定每月預算上限；超支時 FinOps 分析師、工程主管與雲端架構師在成本畫面看到視覺標示（總額變色或橫幅），並在進入產品時看到站內通知。此預算與警告屬本輪 C1 必做，不是 C2／C3 [Q3] [Q10] [Q11] [Q16]
- 本輪不交付 C2（pricing models）與 C3（data egress）[desc] [Q9]
- 本輪入口包含 Sidebar 的 C（成本／FinOps）以及產圖成功後 CTA「查看預估成本」[Q13] [memory:M5]
- 本輪不實作 FinOps 核准流（數字須經 FinOps 核准才對外）；該否決權形態已定義、留給後續 [Q6] [Q14]

## Initiative Trigger

- 使用者故事 C1–C3 已寫好，A 柱產圖後需要銜接「查看預估成本」[Q4]

## Initial Scope Signal

### Workflow-selected scope

<!-- 僅證明 workflow 起跑時選定的 scope，不代表使用者確認的產品邊界。 -->

- `mvp`（workflow-selected）[scope]

### User-confirmed product boundary

- 使用者確認 `mvp` 即為其意圖的產品邊界：先交核心、略過 Operation [Q8]
- 本輪只做 C1；C2／C3 不在本輪交付 [Q9]
- 本輪 C1 必做範圍為：擷取資源、官方報價 API、圓餅拆解、每日運作時數覆寫、API 缺價或失敗時的單價 Manual Override、每月預算上限、超支時成本畫面視覺標示與進入產品時的站內通知（收件人為 FinOps 分析師、工程主管、雲端架構師）、Sidebar C 入口與產圖後 CTA [Q3] [Q9] [Q10] [Q11] [Q12] [Q13] [Q15] [Q16]
- 範圍與優先序由你拍板 [Q6]
- FinOps 對「數字怎麼算」的否決權被定義為核准流；本輪不實作該核准流 [Q6] [Q14]
- 查報價必須走雲端官方報價 API，且不得使用 production credentials [Q12] [memory:M2] [memory:M4]

### 適用的既有約束

- cost calculator 為 property-based testing 的 hard-constraint 落點，測試不得只有 example-based [memory:M1]
- 雲端供應商 production 環境、production credentials、direct production IaC 等不在本 repository 範圍內，除非經新 ADR 核可 [memory:M2]
- security baseline 為常設 hard constraint（IAM、encryption、network exposure、audit logging）[memory:M3]
- 不得 commit 私鑰或 AWS／Azure／GCP 的 credential 字串 [memory:M4]
- Sidebar 導覽依 user story 大類分層；既有 A／J 先套用，後續功能比照 [memory:M5]

## Assumptions & Open Questions

None.

## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-19T05:15:38Z
**Iteration:** 2

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | ✅ Resolved | Prior Finding 1 (Major) | Q5=A 人工覆寫 vs Q12=C 矛盾 | Q15=B 明確區分時數覆寫（隨時）與單價覆寫（API 缺價或失敗時），intent-statement 第 25 行與 stakeholder-map FinOps 欄均已更新。已關閉。 |
| 2 | ✅ Resolved | Prior Finding 2 (Major) | 警告機制不可測 | Q16=B 確立「成本畫面視覺標示 + 進入產品時站內通知」；Q11=B 點名三位收件人；兩份文件一致。已關閉。 |
| 3 | ✅ Resolved | Prior Finding 3 (Minor) | C2/C3 引用 Q3=C 未選定文字 | 第 27 行改為 `[desc]` 引用，使用 "pricing models" / "data egress"。已關閉。 |
| 4 | ✅ Resolved | Prior Finding 4 (Minor) | API 失敗路徑未說明 | Q15=B 及第 25 行明確定義「API 缺價或失敗時可覆寫」，不再靜默回傳 None。已關閉。 |
| 5 | ✅ Resolved | Prior Finding 5 (Minor) | 「該圖所屬雲」路由無來源 | 兩份文件均未出現該措辭。已關閉。 |
| 6 | Minor | stakeholder-map.md FinOps 欄 | FinOps 欄「在意什麼」未列「能設定預算上限」，但 intent-statement Target Customer 表的 FinOps 列有此項；兩份文件對 FinOps 的關切不一致 | 在 stakeholder-map.md FinOps 欄補上「能設定預算上限」以對齊 intent-statement |
| 7 | Minor | intent-statement.md 第 28 行 | `[Q4]` 掛在入口設計主張上（"本輪入口包含 Sidebar 的 C…"）；Q4 是觸發理由，非入口設計決策；[Q13] 才是正確的決策來源（同行已有引用） | 移除第 28 行的 `[Q4]` 引用，或改為說明 Q4 提供背景脈絡的行內備注，避免誤解決策依據 |

### Summary

五項迭代一發現均已確實修復，來源標籤完整、矛盾已消除、警告機制可測。新增兩項 Minor 發現（stakeholder-map FinOps 欄遺漏預算上限、第 28 行 Q4 引用混淆觸發理由與設計決策），不阻擋交付。工程團隊可依本 intent-statement 啟動下一階段，無須再回問產品。
