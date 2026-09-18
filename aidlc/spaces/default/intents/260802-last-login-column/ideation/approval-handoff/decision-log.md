# Decision Log — Ideation 全階段決議紀錄

<!-- Stage: approval-handoff（Ideation 1.7）· 彙整 ideation 各 stage 問題檔的已選答案與 gate 決議。
     每筆決議的正式來源為該 stage 問題檔的 [Answer] 紀錄與 audit shard；本文件為交接用彙整，非新決策。 -->

## 上游輸入

彙整範圍涵蓋 ideation 七站：intent-capture（intent-statement、stakeholder-map）、market-research（依 scope 跳過，competitive-analysis 不存在）、feasibility（feasibility-assessment、constraint-register、raid-log）、scope-definition（scope-document、intent-backlog，含 Revision 1）、team-formation（依 scope 跳過，team-assessment 不存在）、rough-mockups（wireframes、user-flow）、approval-handoff（本站）。

## Intent Capture（1.1，2026-08-02）

| # | 決議 | 出處 |
| --- | --- | --- |
| 1 | 業務問題定性為存取稽核需求（帳號是否仍在使用） | Q1 |
| 2 | 成功指標：介面顯示最後登入時間且可與後端對照；超過 N 天未登入帶視覺標示 | Q3 |
| 3 | 無觸發事件，屬自發機會性改善，無外部期限 | Q4 |
| 4 | stakeholder：`Platform_Admin`（Q5）；矛盾解消後補列 `Security_Reviewer` | Q5、Q13 |
| 5 | Danniel 單獨決策，不需團隊共識；影響者未指認 | Q6 |
| 6 | 溝通需求僅決議紀錄（decisions-log on-demand）；回報節奏未指認 | Q7 |
| 7 | `feature` scope 確認為產品邊界（32 stages、Standard 深度已揭露） | Q8 |
| 8 | 稽核只需最後一次時間，不留歷史；資料模型預留擴充路徑 | Q9 |
| 9 | 為 `Security_Reviewer` 開通使用者管理介面檢視權限 | Q10 |
| 10 | 可見範圍放寬為 4 個管理類角色，維持既有權限粒度，不做欄位級控制 | Q11、Q12 |
| 11 | 門檻 N 不在本階段定值，留 requirements-analysis；N 為固定值、不做設定介面 | Q14 |

## Market Research（1.2）

依 scope 跳過，無決議。

## Feasibility（1.3，2026-08-03）

| # | 決議 | 出處 |
| --- | --- | --- |
| 1 | 「帳號仍在使用」以任何有效憑證活動為準；欄位語意定錨為「最後活動時間」，上游「最後登入」表述不回改 | Q1、Q8 |
| 2 | 接受上線前歷史空窗；空值顯示「無紀錄」、不套逾期標示 | Q2 |
| 3 | 變更套用路徑：服務啟動時自動補齊＋最小範圍權限更新；不重跑整份初始化腳本 | Q3 |
| 4 | 活動資料有保存上限（值待定）；假設無外部法規適用（未經法務確認） | Q4 |
| 5 | 無時程、預算或組織性阻塞 | Q5 |
| 6 | 驗證採受控測試（比對任何活動時刻），不要求第二資料來源 | Q6、Q6a |
| 7 | `Security_Reviewer` 權限擴張風險處置為接受，記入 raid-log R3 | Q7 |
| 8 | 結論：conditional GO（四前提如 feasibility-assessment 所載） | 全卷 |

## Scope Definition（1.4，2026-08-03；Revision 1，2026-08-04）

| # | 決議 | 出處 |
| --- | --- | --- |
| 1 | 四項能力全列 Must、一起上線才算完成；不設 Should／Could 層 | Q1 |
| 2 | 交付排序採 dependency-first；細部經濟排序留 delivery-planning | Q2 |
| 3 | Won't Have：歷史紀錄、N 值設定介面、欄位級權限、排序／篩選；稽核報表匯出為「未承諾」（不列排除） | Q3 |
| 4 | 部署資產同步義務內建於 (a)、(d) 的 DoD，不另立 backlog 項 | Q4 |
| 5 | Revision 1：rough-mockups Q5a 觸發回跳修訂，行動響應式卡片改造（PU-5）納入為第五項 Must，重走 approval gate 核可 | Revision 1 |

## Team Formation（1.5）

依 scope 跳過，無決議；團隊實況為單一決策者＋AI agents（記於 initiative-brief）。

## Rough Mockups（1.6，2026-08-04）

| # | 決議 | 出處 |
| --- | --- | --- |
| 1 | 新欄位插在「角色」之後、「操作」之前 | Q1 |
| 2 | 時間顯示採絕對時間 `YYYY-MM-DD HH:MM` | Q2 |
| 3 | 逾期標示採警示圖示＋時間值變色（非僅顏色傳達） | Q3 |
| 4 | 空值採破折號；元素可聚焦，聚焦／hover 顯示說明（文案留 refined-mockups） | Q4、Q4a |
| 5 | 無障礙底線 WCAG 2.1 AA＋行動響應式；小螢幕卡片式佈局（觸發 scope 擴充回跳，見 scope-definition Revision 1） | Q5、Q5a |
| 6 | 兩份 artifact 共 5 項 assumption 確認保留（Accept assumptions） | Assumption Confirmation |

## Approval & Handoff（1.7，2026-08-06）

| # | 決議 | 出處 |
| --- | --- | --- |
| 1 | 五項未決項以「已記錄未決」狀態交接進 inception，ideation 不補決 | Q1 |
| 2 | initiative-brief 以 GO 為建議 | Q2 |


## Revision 週期（因分頁納入範圍，2026-08-10〜11）

| # | 決議 | 出處 |
| --- | --- | --- |
| 1 | 使用者清單分頁納入本 intent，列為第六項 Must 能力 (f)／PU-6；依規則回跳上游以 Modify 模式修訂 | scope-definition Revision 2 R1／R2 |
| 2 | 排序／篩選維持 Won't Have —— 分頁是本次唯一新增的清單互動 | scope-definition Revision 2 R3 |
| 3 | PU-6 對 PU-5 的約束記為**避免重工**而非技術依賴，下游可在記明緩解方式的前提下覆寫 | scope-definition Revision 2 |
| 4 | 分頁控制形式為**頁碼式**（非游標式、非無限滾動） | rough-mockups Revision 1 R1 |
| 5 | **全域逾期計數本輪不採用、不畫入線框**，僅記於 Assumptions；處置比照「稽核報表匯出」的未承諾先例 | rough-mockups Revision 1 iteration 3〜4 |
| 6 | 「分頁損害 intent 核心價值」的主張**撤回** —— 上游記載的核心價值是**逐帳號**的稽核證據取得，非全域掃描；分頁對它影響輕微 | rough-mockups Revision 1 iteration 1 |
