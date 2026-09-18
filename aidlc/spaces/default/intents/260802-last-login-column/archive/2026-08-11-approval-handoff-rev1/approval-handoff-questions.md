# Approval & Handoff — 釐清問題

> Stage: approval-handoff（Ideation 1.7）· Depth: Standard · Scope: feature
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> 上游輸入：intent-statement、stakeholder-map（intent-capture）；scope-document、intent-backlog（scope-definition，Revision 1）；feasibility-assessment、constraint-register、raid-log（feasibility）；wireframes、user-flow（rough-mockups）。
> 已由上游定案、本階段**不重問**（stage 檔範例題的省略清單）：stakeholder 對 intent 與 scope 的同意（單一決策者已逐 gate 核可）；預算／資源承諾（feasibility Q5 已確認無時程、預算或組織性阻塞）；mockups 是否反映共識（rough-mockups gate 已核可）；market research 支撐（該 stage 依 scope 跳過，無市場面輸入）；mob 編制與排程（team-formation 依 scope 跳過，單一決策者＋AI agents 執行）。

## Sources

- [ideation:*] 本 intent 全部七個 ideation 站的已核可 artifacts 與問題檔已選答案（intent-capture 14 題、feasibility 8＋2 題、scope-definition 4 題＋Revision 1、rough-mockups 5＋2 題）。
- [raid] `../feasibility/raid-log.md` — R1–R4 風險處置、A1–A4 假設、D1–D3 依賴。
- [backlog] `../scope-definition/intent-backlog.md` — PU-1→PU-2→PU-3→PU-5 依賴鏈、PU-4 平行。

## Q1. 交接進 Inception 的未決項清單確認

> Ideation 全程累積的未決項（均已記錄於對應 artifact 的 Assumptions 或 raid-log），交接後各有既定的定案時點：
>
> 1. 逾期門檻 N 值 — requirements-analysis 定案，為整體上線前置 [backlog]
> 2. 活動資料保存上限與清除語意 — requirements-analysis 定案 [raid]
> 3. PU-1 寫入頻率緩解手段（節流／彙整／非同步）— 設計階段必答（raid-log R1）[raid]
> 4. PU-5 前端回歸驗證涵蓋面 — inception 界定 [backlog]
> 5. 響應式斷點值、既有頁面 skeleton 載入慣例查證、wireframes 一處 [Q5] 標籤修訂 — refined-mockups 處理 [ideation:*]

A. 確認以「已記錄未決」狀態交接 — 各項依既定時點於 inception／construction 定案，ideation 不補決。
B. 部分項目需在交接前先定案 — 請指明哪幾項與期望的定案方式。
C. 需新增未決項 — 清單有遺漏，請補充。
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Initiative brief 的 go/no-go 建議方向

> feasibility 的 conditional GO 四前提（活動語意定錨、空窗接受、套用路徑選定、權限擴張風險接受）均已落地為已確認決策；R1–R4 風險均有處置；五項 Must 能力（PU-1～PU-5）依賴序已定。lead agent 擬以 **GO** 為 brief 的建議。

A. 同意 GO 建議 — brief 以 GO 呈現；核可後交接進 Inception（8 站、每站各一個 approval gate）。
B. 改為 conditional GO — 在 brief 中把特定未決項（請指明）升格為進入 Construction 前的硬性前置。
C. 暫緩（HOLD）— 請說明理由與解除條件。
D. Not yet defined
X. Other (please specify)

[Answer]: A
