# Decision Log — IDEATION（AI-DLC 與 GitHub Projects 的進度同步）

<!-- Stage: approval-handoff（Ideation 1.7）· IDEATION 全期決策紀錄。
     本檔與 <record>/decisions-log.md 不同：後者是使用者明確要求時才追加的對話決議紀錄，
     本檔是 stage 的 produces 產出，記錄 IDEATION 各站問題檔的已答決策。 -->

## 上游輸入

決策來源為三站的問題檔與其產出：**intent-statement**／**stakeholder-map**（intent-capture）、**feasibility-assessment**／**constraint-register**（feasibility）、**scope-document**／**intent-backlog**（scope-definition）。依 scope 設計不存在 **competitive-analysis**、**team-assessment**、**wireframes**。

## Intent Capture（1.1）

| # | 決策 | 來源 |
| --- | --- | --- |
| D-1 | 業務問題為四項並存：狀態失真、重複記帳、需求來源分散、對外可視性不足 | Q1 |
| D-2 | 受益者四類：唯一開發者、其他協作者、不參與開發的觀看者、未來的自己 | Q2＋Q10 |
| D-3 | 成功指標三項：零人工更新、一致率、可追溯 | Q3 |
| D-4 | 觸發點三項：已被咬到、流程剛穩定、準備擴大協作 | Q4 |
| D-5 | 決策模型：單一決策者；協作者為受影響方，告知即可不需同意 | Q5 |
| D-6 | 同步節奏：事件驅動即時更新 ＋ 低頻排程對帳 | Q6 |
| D-7 | 需求清單正本置於 Project #16；README 維持現有敘述不改結構 | Q7 |
| D-8 | 產品邊界與工作流選定的 scope 一致 | Q8 |
| D-9 | 失敗通知：workflow 紅燈 ＋ 自動開 issue；對帳不一致亦視為失敗 | Q9 |
| D-10 | 觀看者為正式受益對象（修正 Q2 與 Q1-D 的不一致） | Q10 |
| D-11 | README 只增加一段指路文字；本次實質交付物為同步機制一項 | Q11 |
| D-12 | 一致率的分母只涵蓋已綁定到 intent 的項目 | Q12 |

**取代紀錄**：D-7 取代了原始描述中「以 README.md 作為所有 intent 的需求來源」的框架。原始描述的文字保留在 intent-statement 的問題陳述中並註明其被取代，未被刪除。

## Feasibility（1.3）

| # | 決策 | 來源 |
| --- | --- | --- |
| D-13 | CI 端憑證形式：GitHub App（組織層看板讀寫），與個人帳號解耦 | Q1 |
| D-14 | 事件定義：推送 ＋ PR 生命週期兩條 | Q2 |
| D-15 | 綁定機制：**確定綁定**——自動建立追蹤項目時把編號寫回 intent 的紀錄，之後查表不猜 | Q8（取代 Q3=D） |
| D-16 | Status 只用三態，細粒度進展外置 | Q4 |
| D-17 | 決定性與代理判斷的分界：混合，以代理為主但映射規則以明確對照表寫入提示並逐項引用 | Q5 |
| D-18 | 驗證方式：映射邏輯 dry-run 斷言 ＋ 對真實測試項目的端到端 | Q6 |
| D-19 | intent 誕生時自動開 issue、加入看板、設 In progress | Q7 |
| D-20 | 延遲上限：推送後 5 分鐘內；PR 事件優先於推送 | Q9 |
| D-21 | 錯綁防護：寫入前回讀比對，不符即中止並開 issue | Q10 |

**取代紀錄**：D-15 取代 Q3 的原答案（由代理依標題語意推測）。取代理由是它與 D-19 抵觸——自動建立的當下編號本就是已知事實——且推測式綁定會使 D-12 的一致率指標失去可定義的分母。Q3 的原答案保留並加註取代說明，未改寫。

**假設狀態變更**：intent-capture 的假設「看板寫入權限問題將由補上授權解決，不需改變機制設計」在本站被推翻——該假設指向本機 CLI 授權，而 CI 端需要另一把憑證。已於 raid-log 標為「已被本階段取代」。

## Scope Definition（1.4）

| # | 決策 | 來源 |
| --- | --- | --- |
| D-22 | 交付意向：一次做完全部不分批（範圍層宣告，不決定 Bolt 切分） | Q1 |
| D-23 | 十項能力 CAP-1～CAP-10 全部列為 Must | Q2＋Q2b |
| D-24 | 排序偏好 risk-first，但憑證實測為 Must 且**不構成交付批次** | Q3 |
| D-25 | 細粒度進展的落點：看板自訂欄位 | Q4 |
| D-26 | Won't Have 四項：反向同步、跨 repo 支援、自動關閉 issue、既有 71 項的一次性對正 | Q5＋Q8 |
| D-27 | 無硬時程 | Q6 |
| D-28 | 既有項目的歷史漂移本次不處理 | Q7 |
| D-29 | 自訂欄位由機制自動建立；框架不支援則退回人工 | Q9 |

**補正紀錄**：D-26 的第四項由 Q8 補上——Q7 選擇不處理既有漂移，但 Q5 未勾選對應的排除項。依 `project.md` 規則不得由 AI 擅自補進排除清單，故經人工確認後補上。原答案保留並加註。

**上游誤記更正**：feasibility 的 stage 日誌曾記為「無外部時程（intent-capture Q4／Q5 已定）」並據此省略時程題，但逐字核對後 intent-capture Q4 選的是 A、B、C，「D. 沒有外部壓力」未被選取。時程從未被問過，故於本站補問（D-27）。

## Approval & Handoff（1.7）

| # | 決策 | 來源 |
| --- | --- | --- |
| D-30 | 五項未解項（U-1～U-5）全部確認知悉並接受，帶著它們進入 INCEPTION | Q1 |
| D-31 | Go/No-Go 判定：**Conditional GO** | Q2 |
| D-32 | reverse-engineering 的掃描範圍限定兩塊：AI-DLC 狀態表徵、既有代理式工作流程的形狀與慣例 | Q3 |

## 期間發生的非問答決策

| # | 事項 | 說明 |
| --- | --- | --- |
| E-1 | 實作載體約束 | 使用者於 intent-capture 進行中下達：同步機制以代理式工作流程或 Actions 承載，不得以 repo 內新增的實作程式實作。已於該站的 §13 儀式留存為 `project.md ## Forbidden` 的常設規則。 |
| E-2 | 憑證缺陷修復 | 私鑰原被存為 Actions 變數而非 secret；本 repo 為 PUBLIC、有 5 名協作者、變數在 log 中不遮罩。實測確認未對匿名者外洩（HTTP 401）。使用者已重新產生私鑰、改存 secret、刪除變數。 |

## Assumptions & Open Questions

- 本檔記錄的是**決策**，不是它們的正確性；D-15、D-26 等取代與補正紀錄保留了被取代的原答案，以維持決策軌跡可回溯。 [assumption]
- E-1 的常設規則已寫入規則層，未來所有 intent 皆適用；使用者當時的指示原文是針對本機制，升格為常設規則是其於 §13 儀式的明確選擇。 [assumption]
