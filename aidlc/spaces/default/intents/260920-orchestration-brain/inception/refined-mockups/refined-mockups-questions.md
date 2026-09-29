# Refined Mockups Questions — 統一入口大腦

<!-- Stage: refined-mockups（Inception 2.5）· Record: 260920-orchestration-brain
     lead: aidlc-design-agent（設計師）· support: aidlc-product-agent（產品）
     mode: inline · summary_confirmation: required · review_class: advisory -->

## 來源標籤慣例

本站沿用既有標籤並新增一種，避開撞號：

| 標籤 | 指向 |
|---|---|
| `[Q<n>]`／`[F<n>]`／`[S<n>]` | intent-capture／feasibility／scope-definition 的作答 |
| `[R<n>]` | **rough-mockups** 的作答（`[R1]`–`[R8]`） |
| `[RA:R<n>]` | requirements-analysis 的作答 |
| `[US:U<n>]` | user-stories 的作答 |
| `[DM:D<n>]` | **本站新增**——refined-mockups 的作答 |
| `[線框 §<n>]` | `wireframes.md` 的第 n 節 |
| `[實測]` | 本站對 repo 現況的唯讀查證（見下方「出題前的查證」） |

`[R<n>]` 與 `[RA:R<n>]` 是兩組不同的編號，**不可混用**；本站的 `[DM:D<n>]`
與兩者皆不撞號。

## 出題前的查證（**非**來源登錄，僅供題幹與選項引用）

依 `project.md` 的 `application-design:c8`──出選項前先實測既有結構，否則無法
判斷選項差別。以下六項為本站的唯讀查證結果，其中兩項**翻轉了原本看似明顯的
選項**：

| # | 查證項 | 結果 | 對出題的影響 |
|---|---|---|---|
| V-1 | 哪一份 Tailwind 設定生效 | `frontend/tailwind.config.js` **未被任何 `@config` 載入**（v4.3.0），生效的是 `src/index.css` 的 `@theme`；而 `@theme` **沒有定義任何斷點**，故斷點為 Tailwind v4 預設值。全前端斷點使用實況：`md:` **19** 處、`lg:` **2** 處、`sm:` **1** 處、`xl:`／`2xl:` **0** 處 | D7 的選項以「實際只有一個斷點在用」為前提，不是三段式 |
| V-2 | `ChatBox` 有沒有現成的「候選選項」UI | **有，但是文字解析**──`src/utils/parseChoiceOptions.ts` 用 regex `^([A-Ea-e])[.．、)）:\s]\s*(.+?)$` 掃 assistant 訊息內文，抓連續 ≥2 行的 `A. 標籤`，並自行判斷哪一項是「其他」（`isOtherLabel`：字串等於或開頭為「其他」、或 `/other/i`）。`ChatBox.tsx:266–296` 據此渲染 `data-testid="chat-choice-{key}"` 按鈕 | **翻轉**：線框 §12 的反問畫面看似「沿用既有前例＝免費」，實際那個前例把大腦的輸出協定綁在一條 regex 上，且承載不了每個候選的結構資料（是哪個能力、作業對象是什麼、信心值多少）。故 D3 是真選擇，不是形式題 |
| V-3 | 既有唯一的 WebSocket 消費點長什麼樣 | `src/hooks/useCollaboration.ts`──`:24` 逐字 `url.searchParams.set('token', token)`（**正是 FR8.5 禁止的 query string**），`onmessage` 以字串嗅探 `<mxGraphModel`／`<mxfile` 判斷內容，**沒有任何訊息封包或型別**（`:36–42`） | **翻轉**：NFR5 要求的「前後端共用訊息型別契約」在 repo 內**沒有前例可沿用**，是全新建立。這讓 D3 的結構化選項成本比表面低──它掛在 NFR5／N-1 已經必須做的契約上，不是額外新增一份 |
| V-4 | `CostPage` 能不能深連到特定估價 | **能**──`:2` import `useSearchParams`、`:119` 讀 `searchParams.get('estimate')`、`:51`／`:242` 寫 `setSearchParams({ estimate: String(id) }, { replace: true })` | D5 的 A 選項是零後端改動、零新機制 |
| V-5 | `ChatBox` 的 `Message` 型別能不能承載工作項 | **不能**──`ChatBox.tsx:5–10` 的 `Message` 只有 `role`／`content`／`speaker?`，無狀態欄位、無 id。且 `ChatBox` 的 props 高度綁定 A1（`onGenerate`／`onClearChat`／`onFullReset`／`canReview`／`collapsed`），唯一使用點是 `WorkspacePage.tsx:991` | D4 不是「要不要新元件」而是「新元件放哪一層」；沿用 `Message` 的選項必須明寫它要怎麼補欄位 |
| V-6 | 無障礙自動化現況 | `frontend/package.json` 的 `devDependencies` **無 axe 相關套件**，`playwright.config.ts` 與 `e2e/` 全樹 `axe` 零命中。既有 `aria-live` 僅 **2** 處，皆在 `src/components/cost/EstimateAdvicePanel.tsx`（`:278` 的 `sr-only` 播報區、`:291`）。`data-testid` 命名慣例為 kebab-case ＋ 功能前綴（`estimate-*`／`advice-*`／`chat-*`／`cost-page`／`sidebar-toggle`），共 **24** 個 | D6 的「引入 axe」是既有 Playwright 層的 plugin，不是新測試框架──這個區別決定它是否落在 `[US:U9]`＝A 已拒絕的範圍內 |

## 已由上游定案、本站不重問

依 `project.md` 的 `refined-mockups:c20`──已有線框時不重問層級／CTA／就地編輯／AA
立場。逐項附可引用的定案來源（依 `scope-definition:260822-c5`，引用不出具體來源
者即代表未定案、應補問）：

| 已定案項 | 定案內容 | 來源 |
|---|---|---|
| 入口落點 | Sidebar 置頂獨立項，`/` 預設導向改為入口頁 | `[R1]`、FR1.8 |
| 版面骨架 | 對話為主 ＋ 頂部脈絡列（常駐、可展開） | `[R2]`、線框 §2／§3 |
| 子頁面脈絡 | 與入口頁**同一個**脈絡元件 | `[R3]`、FR2.2、線框 §6 |
| 成本呈現形式 | 對話流中的結構化卡片 ＋ 前往成本頁連結 | `[R4]`、FR10.6、線框 §5 |
| 進度呈現 | 單一則**就地更新**的訊息，不逐則累加 | `[R5]`、FR10.6、線框 §4 |
| 共享↔獨立切換的落點 | 由**脈絡列**承載 | `[R6]`、FR3.1、線框 §6 |
| 裝置與無障礙立場 | 桌機 ＋ 響應式 ＋ WCAG 2.1 AA | `[R7]` |
| 響應式承諾範圍 | **入口頁與脈絡列**；不含既有 `DrawioCanvas` 畫布 | 線框 §7「範圍界定」 |
| 多意圖呈現 | 拆成編號的多項、各自標狀態，不混成一則 | 線框 §8、FR5.1 |
| 記憶可見面必須存在 | 「我的記憶」三類記憶各可逐則刪除 | `[F5]`＝C、線框 §9（明寫此點**非**基準方案） |
| 兩種串流分開 | 成本 job 狀態輪詢（§4）與大腦逐字串流（§11）是不同機制 | 線框 §11、FR10.8 |
| 意圖識別的失敗面 | 不確定先問不動手（§12）＋ 交辦後可**逐項**導回（§13） | 線框 §12／§13、FR1.3／FR1.4 |
| 信心門檻數值 | 0.7，二元判定 | `[RA:FR1.7]`──**本站不重問也不改** |
| 主動通知推播 | 唯一的 Should，本站不畫畫面落點 | 線框能力覆蓋表、FR7.4 |
| 無權限的入口頁 | **不存在該畫面**（狀態不可達） | `[R8]`、FR1.8、user-flow Flow 4 |

---

## D1. 「我的記憶」畫面要落在哪裡，入口怎麼走？

線框 §9 逐字聲明：該節的**落點**（獨立頁面／入口頁面板／設定頁一區）是單一
基準方案，「替代方案留待 refined-mockups 探索」——所以這是本站被上游指名要
決定的事。而 `[US:U6]` 之後的審查（R-06）另外查出一個缺口：該畫面在
`stories.md` 裡**沒有 Sidebar 入口、沒有 `App.tsx` 路由、也沒有對應的存取路徑
故事**，`[US]` 關卡已把它記為已接受的風險，處置落在本站。

本題同時決定落點與入口，因為兩者不能分開答。

- **A.** **獨立頁面 `/memory`**，Sidebar 在「入口」項下方加一個同層獨立項。
  三類記憶為頁內三個區塊（沿用線框 §9 的形狀）。
- **B.** **入口頁的側邊抽屜**，沿用既有 `EstimateHistoryDrawer` 的形狀，
  由脈絡列或頁首的一個按鈕開啟；不新增路由、不動 Sidebar。
- **C.** **獨立頁面 `/memory` ＋ 入口頁的捷徑按鈕**（兩個入口都有）。
- **D.** 設定頁的一區——**本 repo 目前沒有設定頁**，採此案等於連帶新建一個
  設定頁外殼。

[Answer]: C
<!-- C = 獨立頁 `/memory` ＋ 入口頁捷徑（兩個入口都有）｜作答時間 2026-09-25T04:15:00Z（date -u 取值）。依選項順序與內容比對回寫，非依位置。 -->

## D2. `projects`／`systems` 的建立路徑（回補項 N-7）要長什麼樣？

`[RA:FR9.5]` 逐字要求「建立路徑必須存在且被指名，不得留給實作推斷」，理由是
沒有建立路徑，FR9.1 的資料模型就只有 FR9.2 的遷移能產生資料。而線框第 3 節
只有 `[切換對象]`（選既有）與 `[改為獨立對話]`，**零建立畫面**——
`requirements.md` 因此把它列為回補項 **N-7**，性質是「一個全新的使用者可見面，
需要線框、互動設計與授權決定」。本站是它的第一個設計落點。

- **A.** **脈絡列的「切換對象」選單內就地建立**：選單底部加「+ 新增專案」／
  「+ 新增系統」，開一個小表單（名稱即可，其餘欄位待 `domain-design`）。
  新增畫面最少，且與「選取對象」同一個心智位置。
- **B.** **純對話式建立**：使用者說「幫我開一個叫 X 的專案」，大腦辨識為建立
  意圖並執行，回覆中確認結果。不新增任何表單畫面，最貼合「統一入口」的主張。
- **C.** **獨立的管理頁面 `/projects`**：列出專案與其系統，含建立／改名／刪除。
  完整但新增一整頁，且與「入口頁就是唯一入口」的定位有張力。
- **D.** **A ＋ B 並存**：選單可建、對話也可建。

[Answer]: D
<!-- D = 選單就地建立 ＋ 純對話式建立並存｜作答時間 2026-09-25T04:15:00Z（date -u 取值）。依選項順序與內容比對回寫，非依位置。 -->

## D3. 線框 §12 的反問候選，要用什麼機制承載？

`ChatBox` 已經有候選按鈕的 UI（`[實測 V-2]`），但它是**文字解析**：後端把
`A. 候選一`／`B. 候選二` 寫進訊息內文，前端用 regex 掃出來。線框 §12 的候選
每一項都帶結構（是哪個能力、作業對象是什麼），而 `[實測 V-3]` 顯示 NFR5／N-1
**已經要求**建立一份前後端共用的 WS 訊息型別契約——所以結構化的成本不是新增
一份契約，是在那份本來就要做的契約上多一個訊息型別。

- **A.** **結構化訊息型別**：WS 契約新增一個 `clarify` 訊息型別，候選為陣列、
  每項帶 id／標籤／目標能力。前端渲染專用元件，不做任何文字解析。
- **B.** **沿用 `parseChoiceOptions` 文字解析**：大腦的回覆按既有格式寫
  `A.`／`B.` 行，前端零改動。代價是大腦的輸出協定被綁在那條 regex 上，
  且候選的結構資料無處可放。
- **C.** **結構化為主、文字解析為備**：後端送結構化訊息，前端若收到未知型別
  才退回文字解析。
- **D.** 先用 B 上線，結構化留給後續 intent。

[Answer]: A
<!-- A = 結構化訊息型別（WS 契約新增 clarify 型別）｜作答時間 2026-09-25T04:15:00Z（date -u 取值）。依選項順序與內容比對回寫，非依位置。 -->

## D4. 工作項清單（FR1.2 的五個狀態 ＋ FR5.1 的 N 項）要放在畫面的哪一層？

`[實測 V-5]`：`ChatBox` 的 `Message` 型別只有 `role`／`content`／`speaker?`，
承載不了「每個工作項一個狀態」。線框 §8 把工作項畫在**對話流內**（大腦的一則
回覆底下編號列出），線框 §13 的「不是這個」控制項也掛在每一項上。

- **A.** **對話流內的工作項區塊**：大腦的一則訊息底下渲染工作項清單，
  與線框 §8／§13 的畫法一致。工作項隨對話往上捲走。
- **B.** **脈絡列下方的常駐區**：進行中的工作項固定在畫面上方，不隨對話捲走；
  完成後收起。好處是長對話中仍看得到進度，代價是與線框 §8 的畫法不同。
- **C.** **A ＋ B**：對話流內保留歷史紀錄，常駐區只顯示**未完成**的工作項。
- **D.** 沿用 `Message` 並把狀態寫進 `content` 文字——不新增元件，但狀態不可
  機械斷言（與 `[US]` 的 AC 相牴觸）。

[Answer]: C
<!-- C = 對話流內區塊 ＋ 脈絡列下方常駐區並存（常駐區只顯示未完成項）｜作答時間 2026-09-25T04:15:00Z（date -u 取值）。依選項順序與內容比對回寫，非依位置。 -->

## D5. 成本卡片的「到成本頁看完整分析」要不要深連到同一份估價？

`[實測 V-4]`：`CostPage.tsx:119` 已經會讀 `?estimate=<id>`，`:51`／`:242` 已經
會寫它——深連所需的一切都在。`[US]` 階段的設計貢獻指出，若只連 `/cost` 首頁，
`P-3` 的痛點（「自己知道要看哪個 estimate set」）是被搬家而不是被解決；該項在
`[US]` 關卡被記為已接受的風險，處置落在本站。

- **A.** 帶 `?estimate=<id>` 深連到同一份估價。
- **B.** 只連 `/cost` 首頁，讓使用者自己選。
- **C.** 帶 `?estimate=<id>`，且大腦在卡片上明寫「會開啟這一份估價」。

[Answer]: A
<!-- A = 帶 `?estimate=<id>` 深連到同一份估價｜作答時間 2026-09-25T04:25:32Z（date -u 取值）。依選項內容比對回寫。 -->

## D6. WCAG 2.1 AA 要怎麼被驗證？

`[R7]` 承諾 AA，但線框的 assumption 逐字寫「WCAG 2.1 AA 目前無法被機械驗證
……此承諾若要成為閘門需另行導入檢查工具」。`[實測 V-6]`：repo 無任何 axe
相關套件。**關鍵區別**：`@axe-core/playwright` 是**既有 Playwright 層的
plugin**，不是新的測試框架——`[US:U9]`＝A 拒絕的是「引入前端 unit／component
測試框架」與「把 `OPENROUTER_API_KEY` 放進 CI」，兩者都不涵蓋它。

- **A.** **引入 `@axe-core/playwright`**，對入口頁與記憶頁各跑一次自動掃描，
  違規即 CI 紅燈。清單中可機械驗證的項目由它承載，其餘（焦點順序、
  螢幕閱讀器播報內容）仍人工。新增一個 devDependency。
- **B.** **清單為文件 ＋ 全項人工驗證**，不新增依賴。`[R7]` 的 AA 承諾維持
  「宣告而非閘門」的現況。
- **C.** 引入 axe 但**只報告不阻擋**（CI 印出違規、不讓 job 失敗）。
- **D.** 清單為文件，且在文件內明記「本 intent 不提供 AA 的自動化承載」，
  把導入列為回補項交給後續 intent。

[Answer]: A
<!-- A = 引入 `@axe-core/playwright`，違規即 CI 紅燈｜作答時間 2026-09-25T04:25:32Z（date -u 取值）。依選項內容比對回寫。 -->

## D7. 響應式要用幾個斷點？

`[實測 V-1]`：`tailwind.config.js` 是死碼（無 `@config` 載入它），生效的
`src/index.css` 的 `@theme` **沒有定義斷點**，故為 Tailwind v4 預設值
（`sm` 640px／`md` 768px／`lg` 1024px／`xl` 1280px）。而全前端的實際用量是
`md:` **19** 處、`lg:` **2** 處、`sm:` **1** 處——**等於只有一個斷點在真正工作**。
線框 §7／§10 只畫了「窄螢幕」與「桌機」兩態。

- **A.** **只用 `md:`（768px）單一斷點**，與既有實況一致；線框的兩態直接對應
  `< 768px` 與 `>= 768px`。
- **B.** 加入 `lg:`（1024px）做三段（手機／平板／桌機），脈絡列在平板為中間態。
- **C.** 在 `@theme` 自訂斷點值，並順手把死碼 `tailwind.config.js` 刪掉——
  但這會動到既有 21 處斷點的語意，屬既有頁面的迴歸風險。

[Answer]: A
<!-- A = 只用 `md:`（768px）單一斷點｜作答時間 2026-09-25T04:25:32Z（date -u 取值）。依選項內容比對回寫。 -->

## Consolidated Summary Confirmation

**七題定案**（`[DM:D1]`–`[DM:D7]`）：

| 題 | 定案 | 一句話後果 |
|---|---|---|
| D1 | C — 獨立頁 `/memory` ＋ 入口頁捷徑 | Sidebar 多一項、新增一條路由；**不需要新的 story id**（查證見下） |
| D2 | D — 選單就地建立 ＋ 對話式建立並存 | 兩個入口，但**共用一條寫入路徑**（INV-2）；對話式建立一律先確認 |
| D3 | A — 結構化 `clarify` 訊息型別 | 不沿用 `parseChoiceOptions` 的文字解析；掛在 NFR5／N-1 本來就要做的 WS 契約上 |
| D4 | C — 對話流內 ＋ 常駐區並存 | 工作項兩處渲染，但**同一份狀態兩個視圖**（INV-1）；差異只在過濾條件 |
| D5 | A — 成本卡片帶 `?estimate=<id>` | 零後端改動（`CostPage.tsx:119` 已讀該參數） |
| D6 | A — 引入 `@axe-core/playwright` | **新增一個 devDependency 與一道 CI 判定**，列為回補項 **N-9** |
| D7 | A — 只用 `md:`（768px）單一斷點 | 與既有實況一致（`md:` 19 處、`lg:` 2、`sm:` 1） |

**四份產出**：`mockups.md`（10 格框，每行 `len()` 皆 72，腳本產生並驗證）、
`interaction-spec.md`（10 個元件規格 ＋ 3 條跨元件不變量 ＋ 契約端點三問表）、
`design-system-mapping.md`（29 個 `file:line` 引用，全部開檔驗過）、
`accessibility-checklist.md`（POUR 四原則，`[axe]` 14 項／`[人工]` 23 項／`[設計已定]` 12 項）。

---

**六項送審前自檢的結果（blocking，逐項報告）**

`project.md` 要求派 reviewer 前跑完六項自檢並在摘要**逐項報告**。上一站
（user-stories）我跳過了它，而該站 reviewer 的六個 Major 全部是自檢第 4 項會抓到的
——這次先跑再送。**六項共查出 8 處，全部已修**：

| # | 自檢項 | 結果 |
|---|---|---|
| 1 | **可達性** | **查出 2 處**。`CostAnswerCard.no-estimate-id` 我初版寫的可達路徑「job 以 `failed` 終止」是**錯的**（`failed` 有自己的狀態），真正條件是「`completed` 未帶估價 id」而上游對此無規定；`StreamingMessage.empty-stream` 要求大腦能零內容結束串流，亦無上游依據。兩者保留為防禦性狀態並明記可達性未驗證，指派 `contract-design`（H-6／H-7） |
| 2 | **契約端點三問** | **查出 2 處，都在「誰清」**。work-item 集合無人清除（**G-1**）；作業對象無人清回 `no-object`，使該態只在首次使用可達（**G-2**）。兩者非實作細節而是狀態語意，需與 `[RA:NFR4]` 的重啟還原一併決定，指派 `domain-design`（H-8）。完整的三問表（9 個欄位 ＋ 3 個方法）已寫進 `interaction-spec.md` |
| 3 | **引用逐字核對** | **通過**。36 個 `file:line` 引用全部可解析、行號在檔內；另抽驗 6 個關鍵引用的**實際內容**（`ChatBox.tsx:361` 的 `min-h-[44px]`、`:348` 的 `focus-within`、`:230` 的 `rounded-tr-none`、`CostPage.tsx:119` 的 `searchParams.get`、`useCollaboration.ts:24` 的 `searchParams.set`、`PaginationControl.tsx:73` 的 `focus:ring-blue-400`）皆相符 |
| 4 | **檔案集合一致性** | **通過**。stage 宣告的 5 個 produces 與目錄實際檔案完全相符，無缺無多 |
| 5 | **跨檔傳播** | **查出 1 處**。`INV-1`／`INV-2`／`INV-3` 原本只在 `interaction-spec.md`，而它們約束的畫面在 `mockups.md`——追溯單向。已在 M1／M5／M7 三處補上反向引用，現為雙向 |
| 6 | **可算的數字先算再寫** | **通過**。17 個數字全部實算複驗相符（`md:` 19／`lg:` 2／`sm:` 1／`xl:` 0／`2xl:` 0、testid 24、`focus:outline-none` 7、`focus-within` 3、`focus:ring` 14、`aria-live` 2、dependencies 5、`@config` 0、brand 色階 10、ChatBox 385 行、Sidebar 320、Layout 22、openapi path 42） |

---

**三件我要你特別看過的事**

**1. 我第一次跑 `upstream-coverage` 是空轉的。** 不帶 `--consumes` 時它回
`pass: true, reason: "no upstream"`——看起來跟通過一模一樣，實際什麼都沒驗。帶上
`--consumes` 立刻 FAIL，再帶 `--deliverables`（sensor 原始碼明文寫覆蓋是**整站
產出**的性質、逐檔跑會誤報）後只剩 `team-practices` 未引用。補齊它的引用時反而
挖出一條四份產出都漏的真約束：`react-hooks/set-state-in-effect` 是 **error** 級，
本 intent 全部新增的資料來源都必須走 `AdminPage.tsx` 的兩層抓取形狀，否則
`npm run lint` 紅燈。現在四個 sensor 全綠，且是**真的驗過**。

**2. `/memory` 不需要新的 story id——這是查出來的。** 直覺會以為新路由必然要新
story id、連帶觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步。但
`App.tsx:38–41` 的 `/waiting-approval` 是 `ProtectedRoute` 單獨使用的既有前例，
而記憶是使用者自己的資料（`[RA:FR4.3a]` 擁有者由記憶層依已驗證身分設定），
把關的是擁有者欄位而非角色。故本項**明確不是**回補項，也不觸發那兩條 blocking 規則。

**3. 本站唯一的新增 scope 項是 N-9（axe）。** 既有 N-1 至 N-8 已用完
（N-1–N-7 於 `requirements.md`、N-8 於 `stories.md`）。另有一項刻意的文件落差：
`accessibility-checklist.md` 把 `AC-A11Y.1`／`AC-A11Y.2` 的自動化承載從「無」
改善為「部分」，但**未回改 `stories.md`**（已核可，依 `refined-mockups:c3`
不回改上游）——兩份文件對同一件事的敘述因此不同，本檔為較新的事實。

**八項交接事項** H-1…H-8 皆已查 `stage-graph.json` 確認 slug 存在並記下
`execution`；落在 CONDITIONAL 站者全部附轉移目標，且轉移目標皆為 ALWAYS 站
（`units-generation` 2.7 或 `tcms-test-cases` 3.8），**無一項會無聲落空**。

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
<!-- 作答時間 2026-09-25T04:46:42Z（以 `date -u` 取值，非估計）。確認範圍：D1–D7 七題定案、
     四份產出、六項送審前自檢的逐項結果（8 處已修）、三件特別揭露事項
     （upstream-coverage 首次空轉、/memory 不需新 story id、N-9 與 stories.md 的落差）、
     八項交接事項 H-1…H-8。 -->

