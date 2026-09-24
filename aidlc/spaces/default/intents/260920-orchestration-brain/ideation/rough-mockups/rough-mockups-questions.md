# Rough Mockups — 問題檔

本檔為 `rough-mockups` 階段的正式決策紀錄。所有 `[Answer]:` 由使用者填答，
AI 不得代答。回答格式為選項字母（可複選者以逗號分隔），或 `X` 並附文字說明。

## 適用性判定（CONDITIONAL stage）

本 stage 的 condition 為「Execute when user-facing UI is part of the
initiative」。本 intent 要建立一個**全新的統一入口頁**（大腦頁），且既有的
`/workspace`、`/assessment` 要加入共享工作階段——皆為使用者可見的 UI 變更。
依 `project.md` 的 `rough-mockups:c7`，判定**適用，EXECUTE**。

## 已由上游定案、不重問

依 `scope-definition:260822-c5`，每一項都附可引用的定案原文：

- **共享工作階段的涵蓋頁面** — intent-capture [Q7]=A：「只有入口頁 ＋
  `/workspace` ＋ `/assessment`：實際會用到 AI 的頁面。」本站不重問範圍。
- **成本答案的呈現位置** — [Q14]=A：「就地在入口頁呈現：大腦把成本 agent
  的串流轉送到入口頁，使用者不離開入口頁就看到答案。」本站不重問是否導向
  `/cost`，只問**呈現形式**。
- **成本關注者為直接服務對象** — intent-capture 修訂 1 的 Target Customer 表。
- **能力分級** — scope-definition [S11]=A 後為 9 Must／1 Should；唯一的
  Should 是能力 7 主動通知推播。本站不重問分級。
- **串流為 Must、推播為 Should** — 同上。故本站對推播只畫「若存在時的落點」，
  不把它當必然存在。
- **作業對象採「專案 → 系統 → 架構圖」三層** — [Q5]=B。本站不重問層級模型，
  只問它在畫面上**要不要可見、可見的話在哪**。

## 查證紀錄（非來源，不得作為 artifact 的依據）

出題前對 repo 現況做的唯讀查證，只用於讓題目與選項貼合事實。依
`intent-capture:c8`，查證結果用於出題與選項設計，不直接寫進產出。

- V1 — **既有路由**（`frontend/src/App.tsx`）：`/login`、`/403`、
  `/waiting-approval`、`/workspace`、`/assessment`、`/cost`、`/admin/users`、
  `/admin/authorization-requests`、`/admin/role-permissions`，以及 `/` 的
  導向與 `*` fallback。**沒有入口頁**。`/` 的導向依權限決定
  （`can('C1','view')` 者導 `/cost`）。
- V2 — **Sidebar 現有三個群組**（`frontend/src/components/Sidebar.tsx`）：
  **架構**（`/workspace`、`/assessment`）、**成本**（`/cost`）、
  **系統管理**（`/admin/*`）。群組以功能分類，非以 user story 代碼分層。
- V3 — **既有對話 UI 為 `ChatBox.tsx`**：已有訊息清單、頭像縮寫、
  textarea 輸入區（`min-h-[44px]`、`max-h-[120px]`）。可作為入口頁對話區的
  既有形狀參照，不需從零設計。
- V4 — **Sidebar 收合狀態已持久化**：`NavChromeContext.tsx` 以
  `cloud360.nav.sidebarCollapsed` 存於 localStorage。
- V5 — **既有成本畫面**為 `CostPage`（路由 `/cost`），成本建議有 SSE 串流
  端點 `GET /api/cost/v1/sets/{set_id}/advice/stream`，送的是 job 狀態事件
  （`progress`／`completed`／`timeout`／`failed`／`heartbeat`），非 token 串流。

---

## R1. 統一入口頁要放在 Sidebar 的哪裡？

V2 顯示 Sidebar 現有三個功能群組（架構／成本／系統管理）。入口頁是跨所有
功能的，不屬於其中任何一類。

- A. **置於三個群組之上，作為獨立的第一個項目**（不歸入任何群組），
  並把 `/` 的預設導向改為入口頁。
- B. **新增第四個群組**（例如「助理」），入口頁放其中；`/` 導向維持現狀。
- C. **置頂為獨立項目，但 `/` 導向維持現狀**（使用者要自己點進去）。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-22T00:36:09Z | Mode: guided -->

## R2. 入口頁的版面骨架要哪一種？

這決定整個 intent 的主畫面。既有 `ChatBox.tsx`（V3）可作為對話區的形狀參照。

- A. **純對話單欄**：整頁就是一個對話串，作業對象與 session 資訊以對話中的
  訊息或頂部細列呈現。最簡單，但脈絡資訊不常駐。
- B. **對話為主 ＋ 右側脈絡面板**：右欄常駐顯示目前作業對象（專案／系統／
  架構圖）與本次 session 的重點資訊。脈絡永遠可見，但佔寬度。
- C. **對話為主 ＋ 頂部脈絡列**：頂部一條窄列顯示作業對象，可點開展細節。
  折衷：常駐但不佔寬度。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: C  <!-- 2026-09-22T00:36:09Z | Mode: guided -->

## R3. 「目前作業對象」在子頁面（`/workspace`、`/assessment`）要怎麼呈現？

[Q7]=A 已定共享範圍含這兩頁。問題是使用者切過去時，怎麼知道脈絡還在、
且指的是哪一個對象。

- A. **與入口頁相同的脈絡呈現**（同一個元件，跟著使用者走）。
- B. **子頁面只顯示一條輕量提示列**（例如「目前：專案 A／系統 B」），
  點擊可回入口頁。
- C. **子頁面不顯示**：脈絡只在入口頁可見，子頁面靠既有的頁面內選擇器。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-22T00:36:09Z | Mode: guided -->

## R4. 成本答案在入口頁的呈現形式？

[Q14]=A 已定「就地在入口頁呈現」，本題只問**形式**。V5 顯示成本端送的是
job 狀態事件，且既有 `CostPage` 有完整的表格與圖。

- A. **純文字訊息**：像一般對話回覆，成本數字寫在文字裡。
- B. **結構化卡片**：在對話流中插入一張含金額、幣別、主要項目的卡片，
  並附「到成本頁看完整分析」的連結。
- C. **文字 ＋ 精簡表格**：對話流中直接嵌一個小表格。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: B  <!-- 2026-09-22T00:36:09Z | Mode: guided -->

## R5. 成本 job 跑的時候（`progress` 事件），畫面要顯示什麼？

V5：成本建議是非同步 job，會持續送 `progress` 與 `heartbeat`，最後送
`completed`／`timeout`／`failed`。feasibility 的 C-S6 已定「狀態事件要轉譯
進大腦的訊息流」，本題問它長什麼樣。

- A. **單一則會就地更新的進度訊息**（例如「正在分析成本…」原地變化，
  完成後被結果取代）。
- B. **逐則累加的進度訊息**（每個 progress 事件都是新的一則，保留歷程）。
- C. **只有一個載入指示器**（不顯示文字進度）。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-22T00:39:22Z | Mode: guided -->

## R6. 在子功能頁「另開新對話」（能力 3，Must）的入口放哪？

能力 3 是 Must：「可在子功能各自開啟新對話」——在 `/workspace` 或
`/assessment` 內開一段與入口頁無關的新對話。

- A. **子頁面內的對話區有「新對話」按鈕**，按下後該頁的對話脫離共享 session。
- B. **脈絡列／面板上有切換**（共享 ↔ 獨立），由脈絡元件統一承載。
- C. **只能從入口頁開**：子頁面不提供，使用者回入口頁操作。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: B  <!-- 2026-09-22T00:39:22Z | Mode: guided -->

## R7. 裝置與無障礙底線？

`phases/ideation.md` 要求成功標準可量測；無障礙若不定，下游會各自假設。

- A. **桌機優先，鍵盤可操作即可**：不承諾 WCAG 等級，但對話輸入與送出、
  Sidebar 導覽須可純鍵盤完成。
- B. **桌機優先 ＋ WCAG 2.1 AA**：對比度、焦點可見、螢幕閱讀器標籤皆納入。
- C. **桌機 ＋ 平板／手機響應式 ＋ WCAG 2.1 AA**。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: C  <!-- 2026-09-22T00:39:22Z | Mode: guided -->

採 C 的已揭露代價（提問時列於選項說明）：

1. 頂部脈絡列（R2=C）與成本卡片（R4=B）在窄螢幕的行為都必須在線框中畫出來，
   不能只畫桌機版。
2. 既有頁面（尤其含 `DrawioCanvas` 的 `/workspace`）本來就是桌機導向，
   本 intent 對它們的響應式承諾範圍需在下游界定——本站只承諾**入口頁與脈絡
   列**的響應式，不隱含承諾重繪既有畫布。
3. 本 repo **沒有任何自動化 a11y 檢查**（前端唯一自動化層是 Playwright e2e，
   無 axe 類工具）。WCAG 2.1 AA 目前無法被機械驗證，屬宣告而非閘門；
   若要成為可驗證的承諾，需另行導入檢查工具——列為下游的待補承載機制。

## R8. 入口頁的權限落點（矛盾偵測加開）

依 stage-protocol §3 的矛盾偵測，R1=A 與 repo 現況牴觸，故當場定錨。

**衝突內容**：R1=A 的字面是「把 `/` 的預設導向改為入口頁」，但查證顯示
`DefaultRedirect`（`frontend/src/App.tsx:18-28`）**不是固定落地頁**，而是依
權限排序的瀑布式判斷：`canArch('view')` → `/workspace`、`can('A3','view')`
→ `/assessment`、`can('C1','view')` → `/cost`、`can('J3a','view')` →
`/admin/users`、`can('J3b','view')` → `/admin/role-permissions`，皆不符則
導 `/403`。而入口頁是全新的，目前沒有任何 story id 與權限。

若逕自把 `/` 無條件導向入口頁，沒有相應權限的使用者會落在一個用不了的頁面，
且現有的「全無權限 → /403」處置會被繞過。

- A. **給入口頁自己的 story id，置於瀑布之首**：有該權限者 `/` 導入口頁，
  沒有的沿用現有瀑布順序落地。
- B. **對所有已核准使用者開放**：不新增 story id。
- C. **改回 R1=C**：`/` 導向維持現狀，入口頁僅能從 Sidebar 進入。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-22T00:42:24Z | Mode: guided | 矛盾偵測加開 -->

採 A 的後果（提問時已揭露）：

1. **需新增 RBAC story id 與權限矩陣項目**。這會觸發 `team.md` 的
   allow/deny 雙向測試要求，以及 `project.md` 的 `schema_rbac.sql` ＋
   `DEPLOY.md` 同步 blocking 規則（seed 語意變更）。此為本站定案所引入的
   下游義務，需由 requirements-analysis 以後的站承接。
2. **線框需畫出兩種狀態**：有權限者的入口頁、以及 Sidebar 項目在無權限時
   不顯示（不需要另畫「無權限的入口頁」——那個狀態不可達，使用者會被瀑布
   導到別處）。
3. **ADR-0006 的 IAM 面向於本站被觸及**，處置即本題定案，記入產出的
   Assumptions 與下游交接。

## 修訂 1 紀錄（2026-09-23 人工退回）

R1–R8 的作答**未變動**，本輪未新增任何問答。人工於核可關卡退回，理由逐字為：
「補『意圖識別錯誤／不確定』的畫面狀態——使用者如何把走錯的路由導回來。
理由：意圖識別準確率是 Must 級成功指標，但主產出目前 0 格畫面涵蓋其失敗
路徑；wireframing-guide 亦要求五種畫面狀態含錯誤態，目前只有成功態完整。」

據此新增 `wireframes.md` 第 12、13 節與 `user-flow.md` 的 Flow 5，並同步
設計決策摘要、能力覆蓋對照表（能力 1 落點）、核心流程圖與兩檔的 Assumptions。

該輪審查（advisory，單次）回 NOT-READY，兩項新 Major 皆為本輪引入、皆已修正：

| ID | 發現 | 修正 |
|---|---|---|
| PL-04 | 第 13 節畫面自相矛盾：對話說「已停掉」但狀態徽章仍為 `[處理中 (o)]`，且狀態值集合中無此值 | 徽章改為 `[已停掉 (x)]`，狀態值集合補入「已停掉」，並在框中以 `(!)` 明講該項有沒有留下東西 |
| PL-05 | 第 13 節宣稱本站定案「被停掉的工作不得留下半成品」——屬實作層原子性承諾，違反 ideation 的「不得含實作細節」，且與同節 Assumptions 直接矛盾、無上游依據 | 改為只定案畫面層兩件事（可見的終止狀態、必須明講有沒有留下東西），並明寫本站不承諾系統真能做到不留半成品；`user-flow.md` 同步為等價措辭 |

因產出內容已變更，本節的確認欄已重置並重新取得。

## Consolidated Summary Confirmation

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
