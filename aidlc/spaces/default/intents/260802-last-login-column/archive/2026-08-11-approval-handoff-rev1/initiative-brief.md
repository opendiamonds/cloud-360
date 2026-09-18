# Initiative Brief — 帳號最後活動時間（稽核欄位）

<!-- Stage: approval-handoff（Ideation 1.7）· 來源標籤定義見 approval-handoff-questions.md 的 ## Sources。
     本文件為 ideation 全階段的彙整交接件（one-pager）；各主張的原始出處為所引 artifact，本文件不新增未經核可的內容。 -->

## 上游輸入

- **intent-statement**、**stakeholder-map**（`../intent-capture/`）：問題陳述、受益者與已確認的產品邊界。
- **scope-document**、**intent-backlog**（`../scope-definition/`，Revision 1）：五項 Must 能力、排除清單與 proto-unit 依賴序。
- **feasibility-assessment**、**constraint-register**（`../feasibility/`，另含 raid-log）：conditional GO 結論、約束與風險處置。
- **wireframes**（`../rough-mockups/`，另含 user-flow）：桌面表格與小螢幕卡片的概念視覺、三條使用者流程。
- **competitive-analysis**（market-research 產出）：該 stage 依 scope 跳過，本件不存在，無市場面輸入 — 屬 scope 設計而非缺漏。
- **team-assessment**（team-formation 產出）：該 stage 依 scope 跳過，本件不存在；團隊實況見 `## 團隊計畫`。

## 問題與意圖

管理者無法得知帳號的最後活動時間，因而無法滿足存取稽核對「帳號是否仍在使用」的查驗需求（intent-statement）。本 initiative 在使用者管理介面加入「最後活動時間」欄位與逾期標示，並為稽核角色開通檢視權限。

- **受益者**（stakeholder-map）：`Platform_Admin`（管理介面直接看到帳號活躍度，免另行查詢）、`Security_Reviewer`（取得存取稽核所需的帳號活動證據）。
- **決策模式**：Danniel 單獨決定範圍與優先序，不需團隊共識。
- **觸發**：自發建立的稽核能力，屬機會性改善，無外部期限。

## 市場驗證

market-research 依 scope 跳過（內部管理功能，無市場面問題），competitive-analysis 不存在；本 initiative 的正當性來自稽核需求本身，不依賴市場驗證。

## 可行性與風險要點

feasibility-assessment 結論為 **conditional GO**，四個前提均已於 ideation 內落地為已確認決策：

1. 證據事件定錨為「任何有效活動」（欄位語意隨之為「最後活動時間」）。
2. 上線前歷史空窗已接受 — 既有帳號的值為空，顯示「無紀錄」。
3. 變更套用路徑選定 — 服務啟動時自動補齊結構＋最小範圍權限更新，不重跑整份初始化腳本。
4. `Security_Reviewer` 權限擴張風險已接受並記錄（raid-log R3）。

風險現況（raid-log）：R1 寫入頻率成本（mitigate，設計階段必答）、R2 誤重跑初始化腳本（avoid，部署文件明載）、R3 權限擴張（accept）、R4 語意重定錨（accept＋monitor）。約束要點（constraint-register）：schema／seed 變更觸發 `schema_rbac.sql`＋`DEPLOY.md` 同步義務（blocking）；合併進 `ut` 即自動部署 staging；活動資料保存上限值待定。

## 範圍邊界

scope-document（Revision 1）確立五項 Must，一起上線才算完成；依賴序見 intent-backlog：

| Proto-Unit | 能力 | 依賴 |
| --- | --- | --- |
| PU-1 | 記錄帳號最後活動時間 | 鏈頭 |
| PU-2 | 管理介面顯示欄位 | PU-1 |
| PU-3 | 逾期未活動視覺標示 | PU-2；N 值於 requirements-analysis 定案 |
| PU-5 | 行動響應式卡片改造（Revision 1 新增） | PU-2、PU-3 |
| PU-4 | `Security_Reviewer` 檢視權限開通 | 無技術依賴，平行、排序殿後 |

**Won't Have**：登入／活動歷史紀錄、門檻 N 可設定介面、欄位級權限控制、依時間排序／篩選。**未承諾**：稽核報表匯出（不在範圍、不在排除清單）。

## 概念視覺

wireframes 與 user-flow 已核可（reviewer READY）：桌面表格在「角色」與「操作」間新增欄位（絕對時間 `YYYY-MM-DD HH:MM`、逾期 `(!)` 標示、無紀錄可聚焦破折號）；小螢幕為一帳號一卡片；WCAG 2.1 AA 全裝置底線；三條使用者流程（稽核查驗、日常管理、小螢幕存取）。

## 團隊計畫

team-formation 依 scope 跳過（team-assessment 不存在）：單一決策者（Danniel）＋ AI agents 執行全部建造工作，approval gate 為人機協作的控制點。無外部資源需求，無時程、預算或組織性阻塞（feasibility 已確認）。

## 交接未決項

以「已記錄未決」狀態交接，各項依既定時點定案，ideation 不補決 [Q1]：

| # | 未決項 | 定案時點 |
| --- | --- | --- |
| 1 | 逾期門檻 N 值（整體上線前置） | requirements-analysis |
| 2 | 活動資料保存上限與清除語意 | requirements-analysis |
| 3 | PU-1 寫入頻率緩解手段（節流／彙整／非同步） | 設計階段（raid-log R1 必答） |
| 4 | PU-5 前端回歸驗證涵蓋面 | inception |
| 5 | 響應式斷點值、skeleton 載入慣例查證、wireframes 一處 [Q5] 標籤修訂 | refined-mockups |

## Go/No-Go 建議

**GO** [Q2] — conditional GO 四前提已全數落地、風險均有處置、五項 Must 依賴序已定；核可本 brief 即交接進 Inception（8 站、每站各一個 approval gate）。

## Assumptions & Open Questions

- [assumption] 上表五項未決項為 ideation 已知的完整清單 [Q1]；若 inception 發現新未決項，依協定於該 stage 記錄，不回改本件
- [assumption] 團隊計畫以「單一決策者＋AI agents」為既定事實陳述；若未來引入其他協作者，權責劃分需另行界定
