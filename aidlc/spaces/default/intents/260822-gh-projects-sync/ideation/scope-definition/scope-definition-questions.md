# Scope Definition & Prioritization — 釐清問題

> Stage: scope-definition（Ideation 1.4）· Depth: Standard · Scope: aidlc-github-projects-sync
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> 上游輸入：`../intent-capture/intent-statement.md`（intent-statement）、`../feasibility/feasibility-assessment.md`（feasibility-assessment）、`../feasibility/constraint-register.md`（constraint-register）。

## Sources

### 已定案的能力清單（來自上游，本站只做分級與排序，不重新定義）

| # | 能力 | 來源 |
| --- | --- | --- |
| CAP-1 | 綁定建立：intent 誕生時自動開 issue、加入看板、設為 In progress，並把 issue 編號寫回 intent 的紀錄 | [intent:Q7] [feas:Q8] |
| CAP-2 | 推送觸發的狀態同步：讀取已推送的進度紀錄，依對照表映射，寫入看板狀態 | [feas:Q2] [feas:Q4] |
| CAP-3 | PR 觸發的狀態同步：PR 開啟→In review、合併→Done；優先於推送觸發 | [feas:Q2] [feas:Q9] |
| CAP-4 | 排程對帳：低頻掃描並補齊差異 | [intent:Q6] |
| CAP-5 | 失敗通報：工作流程紅燈＋自動開 issue；對帳發現不一致亦視為失敗 | [intent:Q9] |
| CAP-6 | 寫入前回讀確認：比對不符即中止寫入並開 issue | [feas:Q10] |
| CAP-7 | 細粒度 stage 進展外置：Status 只用三態，19 個 stage 的細節承載於他處（**落點未定**） | [feas:Q4] |
| CAP-8 | README 增加一段指向 Project #16 的指路文字 | [intent:Q11] |
| CAP-9 | 憑證可行性實測：以最小可行呼叫驗證 App 鑄出的 token 是否真的帶組織層看板寫入權 | [feas:RSK-7] |
| CAP-10 | 驗證層：映射邏輯 dry-run 斷言 ＋ 對真實測試項目的端到端驗證 | [feas:Q6] |

### 上游的關鍵約束（影響分級與排序）

- [feas:RSK-7] 憑證鑄造是否帶組織層看板寫入權**未經驗證**，且是整條路徑的單點失敗：若不成立，GitHub App 的定案不成立、須退回個人憑證，所有以 App 身分為前提的設計都要重做。
- [feas:RSK-1] CAP-1 的首次建立時尚無既有對象可回讀，CAP-6 的保護在該時刻不成立。
- [feas:DEP-1/DEP-2] 建立與安裝 App、存入識別碼與私鑰為外部人工依賴，阻擋 CAP-1 至 CAP-6 的任何實際寫入，也阻擋 CAP-9。
- [feas:C-T3] 遠端只看得到已推送的內容；CAP-2 的即時性上限由此決定。
- [intent:Q3] 成功指標三項：零人工更新、一致率（分母只算已綁定項目）、可追溯。
- [intent:Q12] 未綁定的既有項目不進一致率分母。

### 規則層

- [memory:M1] `project.md#Forbidden` — 不得以 repo 內新增的實作程式承載本機制。
- [memory:M2] `project.md#Mandated` — `tcms-test-cases` 為 blocking，需實際跑綠的自動化與突變驗證。
- [memory:M3] `org.md#Way of Working` — trunk 為 `ut`，短生命週期分支，deploy-on-merge。

### 本站更正的一項上游誤記

- feasibility 的 stage 日誌曾記為「無外部時程（intent-capture Q4／Q5 已定）」，但逐字核對後，intent-capture Q4 選的是 A、B、C，「D. 沒有外部壓力」**未被選取**，Q5 只談決策權。時程從未被問過，故本站補問（Q6）。

---

## Q1. 第一個值得部署的最小切片是什麼？

> 說明：deploy-on-merge 之下，每個合併都是一次真實部署 [memory:M3]。所以「最小切片」問的是：哪一組能力合起來，第一次合併進 trunk 時是有意義且不會弄壞看板的？

A. 只做 CAP-9（憑證實測）— 第一次合併只證明「App 能寫看板」，不碰任何真實 item。零風險，但看板上看不到任何成果。
B. CAP-9 ＋ CAP-1 — 憑證實測加綁定建立。第一次合併後，新開的 intent 會自動出現在看板上。有可見成果，但狀態不會再變。
C. CAP-9 ＋ CAP-1 ＋ CAP-3（PR 觸發）＋ CAP-6（回讀）— 加上 PR 生命週期的狀態流轉。看板從此會自己動，且有寫入保護。
D. CAP-9 ＋ CAP-1 ＋ CAP-2 ＋ CAP-3 ＋ CAP-5 ＋ CAP-6 — 兩條觸發都做齊、含失敗通報，只把排程對帳與細粒度外置留到第二批。
E. 一次做完全部 — 不分批。
X. Other (please specify)

[Answer]: E

## Q2. 哪些能力是 Must Have（本 intent 不做就等於沒做）？

（可複選，用逗號分隔。未被選為 Must 的會落到 Should／Could，由後續題目與排序決定。）

A. CAP-1 綁定建立
B. CAP-2 推送觸發同步
C. CAP-3 PR 觸發同步
D. CAP-4 排程對帳
X. Other (please specify)

> 註：本題選項受限於一次最多四個，CAP-5／CAP-6／CAP-9／CAP-10 於下一題續問；CAP-7 由 Q4 單獨處理，CAP-8 為單段文字不需分級。

[Answer]:A, B,C, D

## Q2b. 續上題，這四項哪些是 Must Have？

（可複選）

A. CAP-5 失敗通報
B. CAP-6 寫入前回讀確認
C. CAP-9 憑證可行性實測
D. CAP-10 驗證層（dry-run ＋ 端到端）
X. Other (please specify)

[Answer]:A, B, C, D

## Q3. 排序偏好是什麼？

> 說明：[feas:RSK-7] 是單點失敗且會推翻上游定案，這在客觀上已經把 risk-first 的理由擺在檯面上。但排序是價值判斷不是幾何推導，仍須由你決定，我不預設。

A. Risk-first — 先做 CAP-9，用最小成本確認整條路徑成立，再投入其餘設計與實作。
B. Value-first — 先做看板上看得到的東西（CAP-1、CAP-3），憑證問題邊做邊解。
C. Dependency-first — 純依技術依賴序推進，不特別提前風險項。
D. Risk-first，但 CAP-9 不算一個交付批次 — 把它當成 application-design 展開前的一次性驗證動作，不佔 Bolt。
X. Other (please specify)

[Answer]: D

## Q4. CAP-7（細粒度 stage 進展）的承載落點？

> 說明：[feas:Q4] 決定 Status 只用三態、細節外置，但沒定外置到哪。這個選擇會改變範圍：選看板自訂欄位等於要改動 Project #16 的結構。

A. issue 留言 — 每次 stage 推進在對應 issue 留一則留言。不改看板結構；代價是留言會累積得很長。
B. 看板自訂欄位 — 新增一個文字欄位存目前 stage 名稱。看板上一眼可見；代價是改動一個已有 71 個項目的看板結構。
C. issue body 的固定區塊 — 由工作流程改寫 issue body 中一段標記區塊，永遠只有一份最新狀態。不累積、不改看板結構；代價是會覆寫 issue body 內容。
D. 本次不做 — CAP-7 移出範圍，Status 三態就是全部。細粒度進展留在 record 裡，看板不呈現。
X. Other (please specify)

[Answer]: B

## Q5. 哪些項目要明確列入 Won't Have（本次明確排除）？

（可複選。列入 Won't Have 不代表永不做，而是明確宣告本次不做，避免下游自行補上。）

A. 反向同步 — 有人在看板上手動改 Status 時回寫 AI-DLC 的紀錄
B. 既有 71 個項目的一次性對正 — 把歷史漂移（例如 In review 但 issue 已關閉）修正
C. 跨 repo 支援 — 其他 repo 的 intent 也同步到本看板
D. 自動關閉 issue — workflow 完成時除了設 Done 之外，也把對應 issue 關閉
X. Other (please specify)

[Answer]: A, C, D
>
> **⚠️ 本答案已由 Q8=A 補上 B**：「既有 71 個項目的一次性對正」列入 Won't Have，與 Q7=A 一致。原答案保留作為決策軌跡，不改寫。

## Q6. 有沒有硬時程綁在特定能力上？

> 說明：此題在 intent-capture 與 feasibility 都未被問過（見上方「本站更正的一項上游誤記」）。時程若存在會直接改變分級——沒有時間就得砍 Should。

A. 沒有硬時程 — 做到好為止，沒有外部日期壓力
B. 有一個大致的期望 — 希望在某個時間點前看到看板會自己動（請在答案中說明時間點）
C. 有硬期限 — 綁在特定日期（請在答案中說明日期與綁在哪個能力）
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q7. 既有 71 個項目的漂移要不要在本次處理？

> 說明：[intent:Q12] 已定「一致率分母只算已綁定項目」，所以既有項目不影響指標。但看板上確實存在錯誤狀態（例如標 In review 而 issue 已關閉），對「看板可信度」這個問題陳述而言它們仍是雜訊。

A. 不處理 — 已由 [intent:Q12] 排除在指標外，本次完全不碰（若選此項，Q5 的 B 應一併勾選）
B. 一次性人工對正 — 不寫進機制，由你手動清一次，機制只負責之後
C. 納入排程對帳的範圍 — 讓 CAP-4 也掃既有項目並回報不一致（只回報不自動修）
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## 追問（第一輪答案分析後）

## Q8. Q7=A 但 Q5 未勾選 B，兩者需要對齊

> Q7-A 的選項本文寫著「若選此項，Q5 的 B 應一併勾選」，但 Q5 的答案是 A、C、D。依 `project.md` 的規則，使用者未明確列入 Won't Have 的項目，不得由我擅自補進排除清單，只能以「未承諾」狀態記入——所以這個落差必須由你決定，不能由我調和。

A. 漏勾，請補上 — 「既有 71 個項目的一次性對正」列入 Won't Have，與 Q7=A 一致
B. 刻意不勾 — 不處理，但也不宣告排除；以「未承諾」狀態記入 scope 文件（不在範圍、不在排除清單、不推定未來去向）
C. 我要改 Q7 — 既有漂移其實想處理（請說明改成 B 或 C）
X. Other (please specify)

[Answer]:A. 漏勾，請補上 — 「既有 71 個項目的一次性對正」列入 Won't Have，與 Q7=A 一致

## Q9. Q4=B 引入一項新的外部依賴：誰建立那個看板自訂欄位？

> Q4=B 選擇新增一個看板自訂欄位承載細粒度 stage 進展。這會改動一個已有 71 個項目的看板結構，且產生一項先前不存在的前置工作——與 DEP-1（建立 App）同類，都是機制無法自我完成的事。另外，欄位建立完成前 CAP-7 無法運作。

A. 你人工建立一次 — 在 Project #16 手動新增欄位，之後機制只負責寫值。與 DEP-1 併列為上線前置依賴。
B. 由機制自動建立 — 若框架支援建立欄位就讓 workflow 自己建，不支援則退回 A（此選項含一項待驗證的技術假設）。
C. 先不決定 — 列為 application-design 的待決項，本站只記錄依賴存在。
X. Other (please specify)

[Answer]:B. 由機制自動建立 — 若框架支援建立欄位就讓 workflow 自己建，不支援則退回 A（含待驗證的技術假設）

---

## Consolidated Summary Confirmation

在依這些答案產出 scope-document.md 與 intent-backlog.md 之前，請確認彙整內容正確。

A. Looks correct — 依這些答案產出 artifact
B. Request changes — 先修改一個以上的答案再產出
X. Other (please specify)

[Answer]: A. Looks correct
---

## Revision 1（2026-08-23）— ADR-0013 觸發的 scope 擴充

**既有答案與清單一律不動**，本段僅記錄修訂來源與其後果。

### 觸發

reverse-engineering 開始前發現 **ADR-0012**（AI-DLC 與 GitHub Issues／Projects／Wiki 的雙向同步，Accepted 2026-08-16）涵蓋本 intent 的主題，而 IDEATION 四站全程未引用它。比對出四處衝突，經使用者裁決後開立 **ADR-0013** 修訂 ADR-0012 的第 1、5 點與階段表。

### 對本站的影響

| 項目 | 原決定 | 修訂後 | 依據 |
| --- | --- | --- | --- |
| 反向同步（GitHub 狀態變更回寫 record） | Q5=A 列入 Won't Have（W-1） | **移出 Won't Have，納入範圍**，新增能力 CAP-11 與 PU-10 | ADR-0013 決定 2 |
| 映射層級 | intent → Project #16 的一則 issue | **不變**（ADR-0013 決定 1 明文採用本 intent 的做法，不採 ADR-0012 的 intent→Project） | ADR-0013 決定 1 |
| 承載形式 | 不得以 repo 內程式承載 | **不變**（ADR-0013 決定 3 修訂 ADR-0012 的 `scripts/` 指定，與本 intent 一致） | ADR-0013 決定 3 |
| 階段順序 | 直接做 Projects | **不變**（ADR-0013 決定 4 確認階段 1 不構成前置） | ADR-0013 決定 4 |

Q5 的原答案（A、C、D ＋ 經 Q8 補上的 B）保留不改寫；W-1 的移出以本段與 scope-document 的 Revision 段記錄，`Won't Have` 表中該列標註為已移出。

### 未重問的事項

Q1～Q4、Q6、Q7、Q9 與追問 Q8 的答案均不受本次修訂影響，不重問。Q3 的 risk-first 排序偏好在新增 PU-10 後仍成立（PU-0 仍為首位）。
