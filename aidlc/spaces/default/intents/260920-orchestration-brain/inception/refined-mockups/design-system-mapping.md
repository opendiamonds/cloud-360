# Design System Mapping — 統一入口大腦

<!-- Stage: refined-mockups（Inception 2.5）· Record: 260920-orchestration-brain -->

## 這份檔在做什麼

把 `mockups.md` 的 10 格畫面與 `interaction-spec.md` 的 10 個元件，逐一對應到
**本 repo 實際生效的**設計系統。所有引用的 token 與 class 皆為本站唯讀查證所得，
附檔名與行號供機械複驗；**沒有任何一項是憑印象寫的**——依 `project.md` 的
`refined-mockups:c1`（引用工具鏈設定值前必須先確認哪一份真的生效）與
`rough-mockups:rev1-c15`（沿用慣例前必須先量測既有樣本）。

---

## 1. 設計 token 的真實來源

**`frontend/tailwind.config.js` 是死碼。** Tailwind v4.3.0 下它需要由 CSS 的
`@config` 指令載入，而全前端 `src/*.css` 的 `@config` 命中為 **0**。實際生效的是
`src/index.css` 的 `@theme` 區塊。

| Token 類別 | 實際定義 | 值 |
|---|---|---|
| 字體 | `--font-sans` | `'Inter', system-ui, sans-serif` |
| 品牌色 | `--color-brand-50` … `--color-brand-900` | 10 階，`#eff6ff` → `#1e3a8a`（即 Tailwind 的 blue 色階） |
| 動畫 | `--animate-slideInDown`、`--animate-fadeInUp` | 各 `0.4s ease-out forwards`，含對應 `@keyframes` |
| **斷點** | **`@theme` 未定義** | 故為 Tailwind v4 預設：`sm` 640／`md` 768／`lg` 1024／`xl` 1280／`2xl` 1536 |

**斷點的實際用量**（全 `src/` 掃描）：`md:` **19** 處、`lg:` **2** 處、`sm:` **1** 處、
`xl:`／`2xl:` **0** 處。等於只有 `md:` 在真正工作——`[DM:D7]`=A 因此只用它。

> **2026-10-02T13:27:03Z 更正（`review-02` 的 `R-05`，Minor）**：`md:` 的實際用量為 **22** 處，
> 不是 19（`grep -ro 'md:' frontend/src | wc -l`）。`lg:` 2、`sm:` 1 兩者與原文相符。
> **不影響 `[DM:D7]`＝A 的單一斷點決定**（`md:` 仍是唯二非零斷點中的壓倒性多數），
> 但它是一條指令就能算出的數字。依 `refined-mockups:c3` 原句不改寫，在此記現值；
> 同一數字在 `refined-mockups-questions.md` 的 V-1／D7／自檢表三處亦為 19，
> 那是上一輪已核可的問答紀錄，同樣不回改。

**本 intent 不新增任何 token**，不擴充 `@theme`，也**不刪除**死碼
`tailwind.config.js`（刪它會動到既有 22 處斷點的語意，屬既有頁面的迴歸風險，
而本 intent 對既有頁面零 e2e 掩護）。

---

## 2. 既有元件的沿用決定

| 既有元件 | 本 intent 的處置 | 依據 |
|---|---|---|
| `Layout.tsx`（22 行） | **直接沿用**。入口頁與 `/memory` 皆包在 `<Layout>` 內，沿用 `flex h-screen w-full bg-gray-50 overflow-hidden font-sans` 外殼與 `min-h-0 overflow-y-auto` 內容區 | 既有全部頁面皆如此；`App.tsx` 每條路由都包 `<Layout>` |
| `Sidebar.tsx`（320 行） | **擴充兩個獨立項**（「入口」`[*]`、「我的記憶」`[#]`），置於三個既有群組之外。沿用 `groupHeaderClass` 以外的項目樣式 | `[R1]`、`[DM:D1]`=C |
| `ChatBox.tsx`（385 行） | **不沿用元件，沿用視覺語彙**（見下節） | 查證結果，理由詳述於 §3 |
| `PaginationControl.tsx` | **直接沿用**於記憶頁的情節記憶分頁 | `mockups.md` M6；不自創分頁 |
| `EstimateHistoryDrawer.tsx` | **不使用**。`[DM:D1]`=C 選了獨立頁而非抽屜，故此形狀在本 intent 無落點 | `[DM:D1]`=C |
| `RouteGuard.tsx` 的 `ProtectedRoute` | **直接沿用**於 `/memory`（不包 `CapabilityRoute`） | 前例 `App.tsx:38–41` 的 `/waiting-approval`；理由見 `mockups.md` M0 |
| `RouteGuard.tsx` 的 `CapabilityRoute` | **沿用**於入口頁，`storyId` 待 **OQ-11** 定案 | `[RA:FR1.8]`；既有五條路由皆此形狀（如 `App.tsx:49` 的 `storyId="A1"`） |
| `NavChromeContext.tsx` | **沿用**（由 `Layout` 提供，無需改動） | 既有機制 |
| `config/api.ts` 的 `apiUrl()`／`wsUrl()` | **必須沿用**。`team.md` 記載 52 處 `fetch()`（10 支檔）一致使用 `apiUrl()`；WS 用 `wsUrl()` | `team.md ## Code Style`「前端 API 呼叫現況」 |
| `DrawioCanvas.tsx` | **不碰**。線框 §7 明文界定響應式承諾範圍不含它 | 線框 §7「範圍界定」 |
| `Layout.tsx` 的 `data-slot="cost-banner"` | **不使用**。那是 C1 超支橫幅的既有擴充點，與本 intent 無關 | 查證所得（`Layout.tsx:16`） |

---

## 3. 為什麼新建 `BrainChat` 而不沿用 `ChatBox`

**這是本站的決定，故附完整理由與查證。**

`ChatBox` 的 props 高度綁定 A1 產圖流程（`ChatBox.tsx:12–29`）：
`onGenerate`／`onClearChat`（「只清對話、保留畫布」）／`onFullReset`（「全部重置
（畫布 + 對話）」）／`canReview`（審核模式）／`collapsed`（「收合對話面板，讓架構圖
佔滿剩餘寬度」）。其中三個直接指涉 draw.io 畫布，而入口頁沒有畫布。唯一使用點是
`WorkspacePage.tsx:991`。

更關鍵的是 `Message` 型別（`ChatBox.tsx:5–10`）只有 `role`／`content`／`speaker?`
——**無 id、無狀態欄位**。入口頁需要承載的是工作項（五個狀態）、結構化 clarify
候選、成本卡片、串流游標，沒有一個放得進 `content: string`。

因此新建 `BrainChat`，並**逐項沿用 `ChatBox` 的視覺語彙**，使兩處在使用者眼中是
同一種介面：

| 視覺元素 | 沿用的實際 class | 來源 |
|---|---|---|
| 使用者訊息泡泡 | `rounded-2xl rounded-tl-none text-gray-700` | `ChatBox.tsx:229` |
| 大腦訊息泡泡 | `rounded-2xl rounded-tr-none text-gray-800 bg-brand-50/30` | `ChatBox.tsx:230` |
| 輸入列外框 | `relative flex items-end bg-white border border-gray-200/80 rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-brand-500/20 focus-within:border-brand-500 transition-all duration-300 p-2` | `ChatBox.tsx:348` |
| 輸入框 | `min-h-[44px]`、`max-h-[120px]`、`text-[14px]`、`resize-none` | `ChatBox.tsx:361` |
| 送出鈕（可用） | `bg-gradient-to-br from-brand-600 to-indigo-600 text-white shadow-md shadow-brand-500/30` | `ChatBox.tsx:370` |
| 送出鈕（停用） | `bg-gray-100 text-gray-300 cursor-not-allowed` | 同上 |
| 候選鈕（一般） | `border-brand-100 bg-brand-50/40 text-brand-800 hover:bg-brand-50 hover:border-brand-300` ＋ `px-3.5 py-2.5 rounded-xl text-sm font-semibold` | `ChatBox.tsx:284–287` |
| 候選鈕（退出／其他） | `border-dashed border-gray-300 text-gray-600 hover:border-brand-400 hover:bg-brand-50/50` | `ChatBox.tsx:286` |
| 載入中三點 | `w-2 h-2 bg-brand-500 rounded-full animate-bounce`，延遲 0／0.15s／0.3s | `ChatBox.tsx:255–257` |
| 小圓點指示 | `w-2.5 h-2.5 rounded-full bg-brand-500 animate-pulse` | `ChatBox.tsx:124` |
| 小型動作鈕 | `px-2.5 py-1.5 rounded-full border text-xs font-bold` | `ChatBox.tsx:153/160` |
| 圖示鈕 | `w-9 h-9 rounded-xl bg-white border border-gray-200 text-brand-600` | `ChatBox.tsx:101` |

**送出快捷鍵沿用 `Ctrl+Enter`／`Cmd+Enter`**（`ChatBox.tsx:354`），不改為 Enter
送出——改它會讓同一個產品裡兩個對話框行為不同。

**`ClarifyCandidates` 沿用候選鈕的樣式但不沿用其資料路徑**：`ChatBox` 的候選來自
`parseChoiceOptions` 的文字解析，`[DM:D3]`=A 改為結構化訊息。視覺相同、來源不同
——理由見 `mockups.md` M2。

---

## 4. 間距與圓角尺度（量測既有樣本所得）

`wireframing-guide.md` 建議統一間距尺度。本 repo **未宣告**尺度，但實際使用集中在：

| 用途 | 實際值 | 樣本 |
|---|---|---|
| 區塊內距 | `p-6` | `ChatBox.tsx:338` 的輸入列容器 |
| 控件內距 | `px-3.5 py-2.5`（候選鈕）、`px-2.5 py-1.5`（小鈕）、`p-2.5`（送出鈕） | `ChatBox.tsx:284/153/370` |
| 圓角 | `rounded-2xl`（泡泡、輸入列）、`rounded-xl`（候選鈕、圖示鈕）、`rounded-full`（小鈕、指示點）、`rounded-lg`（次要圖示鈕） | 同上 |
| 元素間距 | `gap-2`、`space-y-1`、`mt-1`、`mt-4` | `ChatBox.tsx:266`、`Sidebar.tsx:144` |

本 intent 的新元件一律從上表取值，**不引入新的間距或圓角值**。

---

## 5. 測試識別碼命名

既有 **24** 個 `data-testid`，慣例為 kebab-case ＋ 功能前綴：

| 既有前綴 | 例 |
|---|---|
| `estimate-*` | `estimate-upload-zone`、`estimate-privacy-badge` |
| `advice-*` | `advice-pending`、`advice-category-saving` |
| `chat-*` | `chat-choice-options`、`chat-choice-{key}` |
| 單一 | `cost-page`、`sidebar-toggle`、`cloud-override-picker` |

**本 intent 一律用 `brain-*`，記憶頁用 `memory-*`。** 完整清單見
`interaction-spec.md` 各元件的「Test ids」。不重用 `chat-*`——它已指涉 A1 的產圖
對話，重用會讓既有 e2e 的選擇器誤中入口頁。

---

## 6. 無障礙既成慣例（量測結果，非宣稱）

| 項 | 實測結果 | 對本 intent 的意義 |
|---|---|---|
| `aria-live` 既有用法 | **僅 2 處**，皆在 `src/components/cost/EstimateAdvicePanel.tsx`（`:278` 的 `sr-only aria-live="polite"` 播報區、`:291`） | 本 intent 的播報沿用 `:278` 的 `sr-only` 播報區形狀 |
| `focus:outline-none` | **7 處，全部都有補償**——6 處同元素帶 `focus:ring`／`focus:border`（`LastActivityCell.tsx:47`、`PaginationControl.tsx:73`、`LoginPage.tsx:158/169/182/193`），第 7 處 `ChatBox.tsx:361` 由容器 `:348` 的 `focus-within:ring-2` ＋ `focus-within:border-brand-500` 補償 | **既有程式沒有無補償的 `outline: none`**。這是應該保護的既有紀律，本 intent 的新元件必須維持——不是一個要修的缺口 |
| `focus-within` | 3 處 | 容器級焦點指示是既有形狀，`BrainChat` 的輸入列沿用 |
| `aria-expanded` | `Sidebar.tsx:126/182/215` 的三個群組標題 | 脈絡列與常駐區的 disclosure 沿用同一形狀 |
| `aria-current` | 線框 §1 註記要求，既有 Sidebar 未使用 | 本 intent 的兩個獨立項**新增** `aria-current="page"`；這是補強而非沿用 |
| 觸控目標下限 | `min-h-[44px]`（`ChatBox.tsx:361`） | 符合 WCAG 2.1 AA 的 44×44；本 intent 全部可點元素比照 |

**一項已知的 token 不一致**：`PaginationControl.tsx:73` 的焦點環用
`focus:ring-blue-400` 而非 `brand-*` token。記憶頁會沿用該元件，故會繼承這個
不一致。**本 intent 不修它**——它是既有元件的既有問題，在本 intent 內改它等於
動到 Admin 頁的分頁（無 e2e 掩護）。列為觀察項，不列為回補項。

---

## 6b. `team-practices` 這個上游在本 intent 的落點

本 stage 的 frontmatter 宣告消費 `team-practices`（`required: false`）。**本 intent
沒有這個檔**——`practices-discovery` 只在另兩個 intent 跑過
（`260819-cost-finops`、`260802-last-login-column` 的
`inception/practices-discovery/team-practices.md`），而依該 stage 的 outputs 說明
逐字「On affirmation, content is promoted to
aidlc/spaces/<active-space>/memory/team.md and project.md」，其內容的現行落點是
**`aidlc/spaces/default/memory/team.md`**。

本檔實際使用該層的三條規則（逐條附出處）：

| 用到的規則 | `team.md` 的出處段 | 本檔哪裡用到 |
|---|---|---|
| 前端 API 呼叫一律走 `apiUrl()`／`wsUrl()`；52 處 `fetch()`（10 支檔）一致沿用；認證標頭仍是手寫 | `## Code Style`「前端 API 呼叫現況」 | §2 的 `config/api.ts` 一列——本 intent 的 WS 必須走 `wsUrl()` |
| 前端**完全沒有** unit／component 測試框架，唯一自動化層是 Playwright e2e | `## Testing Posture`「既成事實」 | `accessibility-checklist.md` 的驗證機制——`[DM:D6]`=A 之所以選 Playwright plugin 而非新框架 |
| 前端資料抓取必須拆兩層（純抓取函式 ／ 呼叫端更新 state ／ `useEffect` 內用 `cancelled` flag），因 `react-hooks/set-state-in-effect` 為 error 級 | `## Code Style`「前端：lint 規則造成的結構約束」 | 本 intent 全部新增的資料來源（記憶清單、對象清單、工作項）都必須沿用此形狀，否則 CI 紅燈 |

**第三條是本檔新增的約束**，先前四份產出都沒提到它：`mockups.md` 的 `loading`／
`error` 態與 `interaction-spec.md` 的 `MemoryZone`／`ObjectPicker` 都會抓資料，
而那條 lint 規則是 error 級——不照 `AdminPage.tsx` 的 `fetchUserList` / `fetchUsers`
/ `useEffect` 三段形狀寫就過不了 `npm run lint`。

## 7. 圖表與圖示

- **不新增任何圖表套件**。本 intent 無圖表需求（成本卡片是數字與分項清單，
  非圖表）。此立場與 `project.md` 的 `refined-mockups:c21`（C1 成本頁圓餅自畫 SVG
  不新增套件）同向。
- **圖示沿用既有做法**：既有程式用 inline SVG（`Sidebar.tsx`、`ChatBox.tsx`），
  無圖示套件。本 intent 比照。`mockups.md` 的 ASCII 圖示（`(o)`／`(x)`／`(!)` 等）
  只是線框表記法，不是實作圖示——實作時對應到 inline SVG ＋ 文字標籤。

---

## 8. 本 intent 新增的依賴

**一項**：`@axe-core/playwright`（`[DM:D6]`=A）。它是既有 Playwright 層的 plugin，
不是新測試框架，故不落在 `[US:U9]`＝A 拒絕的範圍（那條拒絕的是「引入前端
unit／component 測試框架」與「把 `OPENROUTER_API_KEY` 放進 CI」）。

本項已列為 `mockups.md` 的回補項 **N-9**。除此之外本 intent **不新增任何前端
執行期依賴**——現有 `dependencies` 僅 5 項（`html2canvas`、`jspdf`、`react`、
`react-dom`、`react-router-dom`），本 intent 全部需求可由它們滿足。

---

## Assumptions & Open Questions

- `@theme` 未定義斷點，故斷點為「Tailwind v4 預設值」——此推論基於 v4 的行為，
  **未以實際編譯輸出驗證** `md:` 是否確實等於 768px [assumption]
- `BrainChat` 沿用的 13 項視覺 class 皆逐字取自 `ChatBox.tsx` 的指定行號，但
  **未實際渲染比對**兩者外觀是否一致 [assumption]
- 記憶頁沿用 `PaginationControl` 的決定基於它「是既有分頁元件」，但本站
  **未檢視其 props 契約是否適用於記憶清單**（既有使用情境為 Admin 使用者清單） [assumption]
- 既有骨架屏形狀未逐頁量測——`RouteGuard.tsx` 的 `LoadingScreen` 是整頁 spinner
  而非骨架屏，兩者不同；記憶頁與 `ObjectPicker` 的 `loading` 態究竟沿用哪一種
  未定（`mockups.md` 交接事項 H-5） [assumption]

---

# 修訂 1（2026-10-02T13:05:52Z）— 能力 11／12 的元件與 token 對映

既有各節（token 真實來源、既有元件沿用決定、`BrainChat` 的新建理由、間距尺度、
測試識別碼、無障礙既成慣例、`team-practices` 落點、圖表圖示、新增依賴）**全部有效**。

## 11. 能力 11／12 的新元件與既有元件的對映

| 新元件 | 沿用既有的什麼 | 為什麼不是全新 | 新增的部分 |
|---|---|---|---|
| `ProjectList` | `AdminPage.tsx` 的表格形狀與兩層抓取（`fetchUserList` → `.then` → state） | 它是「清單 ＋ 每列進入詳情」，與使用者清單同形 | 四種狀態的骨架屏（既有 `AdminPage` 無骨架，只有整塊文字） |
| `ProjectDetailTabs` | `aria-expanded` 的 disclosure 形狀（`Sidebar.tsx:126/182/215`） | — | **籤列是 `role="tablist"`，本 repo 無既有前例**；方向鍵切換 ＋ Tab 進出面板為新建 |
| `SystemCreateAction` | `ObjectCreateAction`（既有的共用寫入路徑，非視覺元件） | 它只是第三個觸發點 | 無新寫入路徑 |
| `RequirementFieldGroup` | `LoginPage.tsx:158-193` 的 `label` ＋ `input` ＋ `focus:ring` 形狀 | 標準表單欄位 | `fieldset` ＋ `legend` 的分組（既有表單皆為平鋪，無分組前例） |
| `MemberList` | 同 `ProjectList`；「最後活動」欄直接沿用 `LastActivityCell.tsx` | 欄位語意相同（全域活動） | `viewerRole` 驅動的兩種視角 |
| `InviteMemberDialog` | **既有 5 個 modal 的 shell**：`ShareModal.tsx:93-94`、`cost/EstimateSaveModal.tsx:67-69`、`cost/EstimateShareModal.tsx:109-110`、`cost/EstimateCalculatorGuideModal.tsx:105-107`、`cost/EstimateHistoryDrawer.tsx:56-57`——五者皆 `role="dialog"` ＋ `aria-modal="true"` ＋ Escape 關閉 ＋ 開啟時把焦點送進面板 | modal 的外殼與 Escape 是既有形狀，照抄即可 | **焦點陷阱與焦點返還兩項既有程式都沒有**（實查：`ShareModal.tsx:47` 與 `EstimateSaveModal.tsx:25` 只做初始 `.focus()`，全樹無 trap、無返還觸發元素）——這兩項是新建 |
| `ReselectBanner` | `EstimateAdvicePanel.tsx:278` 的 `sr-only` 播報區形狀 | 播報機制相同 | `role="status"`（既有 2 處皆為 `aria-live="polite"`，本元件**不能**用它，見下） |
| `RecentConversations` | `Sidebar.tsx` 的群組收合形狀 | disclosure 相同 | 時間分組的 `h3` ＋ `list` 結構 |

**兩個「無既有前例」是本修訂的真實成本**：`role="tablist"` 與 `role="status"`
在本 repo 全樹**零命中**（實測：`grep -rl` 於 `frontend/src` 各回 0 個檔）。它們不是
沿用而是新建，且都有明確的鍵盤與焦點契約（見 `accessibility-wcag.md` 的鍵盤樣式表）。

> **2026-10-02T13:08:00Z 更正（本站自檢 3 查出，非審查指出）**：本段原寫「**三個**無既有前例」並把
> `role="dialog"` 列入，逐字寫「全樹 `role="dialog"` 零命中」——**那是錯的**。實測
> `role="dialog"` 與 `aria-modal` 各命中 **5 個檔**（見上表該列）。方向錯了：modal
> 的外殼是**既有形狀可照抄**，真正缺的是**焦點陷阱與焦點返還**——這兩項五個既有
> modal 都沒做（只有初始 `.focus()`）。更正後的成本敘述比原版低（少一個全新 role）
> 但風險位置更精確：新建的不是 modal，是它的焦點契約。

## 12. `aria-live="polite"` 與 `role="status"` 的分野（`[D-11]` 的具體落點）

既有 2 處 `aria-live="polite"` 都掛在**已經存在於 DOM、內容之後才變更**的節點上
（`EstimateAdvicePanel.tsx:278`）——那是該屬性的正確用法。

`ReselectBanner` **不能**照抄：它是隨頁面一起渲染的，`aria-live` 只播報掛載**之後**
的內容變更，所以初次渲染的橫幅不會被朗讀。處置是 `role="status"`（隱含 polite 且
在初次渲染即為 live region），或維持 `aria-live` 但在掛載後才插入內容。
**本站選前者**：後者把「什麼時候插入內容」變成一個時序細節，而時序細節在 React
的 effect 排程下不保證。

## 13. 修訂 1 的測試識別碼

沿用第 5 節的 `brain-*` 前綴規則；能力 11／12 另立兩個前綴以免與入口頁混淆。

> **第 5 節的「既有 24 個 `data-testid`」已過時（2026-10-02T13:08:00Z，自檢 3 查出）**：實算為
> **34** 個（`grep -roh 'data-testid="[^"]*"' frontend/src | sort -u | wc -l`）。
> 依 `refined-mockups:c3`，第 5 節為本站上一輪已核可的內容、**不回改**；在此記載
> 現值。前綴慣例（kebab-case ＋ 功能前綴）未變，故該節的規則本身仍成立。

| 前綴 | 用於 | 例 |
|---|---|---|
| `project-*` | 能力 11 的畫面 | `project-list`、`project-create`、`project-tab-overview`、`project-tab-requirements`、`system-create`、`requirement-field-{key}`、`requirement-unfilled-count` |
| `member-*` | 能力 12 的畫面 | `member-list`、`member-invite`、`member-row-{id}`、`member-role-select`、`member-remove`、`invite-deny-reason`、`reselect-banner`、`reselect-banner-expand` |
| `brain-*` | 入口頁（既有規則） | `brain-recent-conversations`、`brain-new-conversation` |

**`member-remove`／`invite-deny-reason`／`reselect-banner` 三個是不變量的斷言點**
（I-5／I-6 與 `AC12.6.2`／`AC12.5.1`）——改名會讓對應的 e2e 失去目標，故列在此處
而非只寫在 `interaction-spec.md`。

## 14. 修訂 1 不新增任何依賴

能力 11／12 的全部新元件可由既有 React ＋ Tailwind ＋ `@theme` token 構成：
籤列、modal、橫幅、骨架屏皆為自寫（`[US:U9]`＝A 已拒絕引入前端測試框架，本站
同樣不引入 UI 套件）。**唯一的例外是無障礙驗證工具**——`[DM:D11]`＝A 要求把 axe
掃描擴到新畫面，而 axe 是既有 Playwright 層的 plugin（`@axe-core/playwright`），
不是新測試框架。該區別已在既有第 8 節與 `[DM:D6]`＝A 處理過，本修訂只擴大它的掃描
範圍，不改變它的性質。
