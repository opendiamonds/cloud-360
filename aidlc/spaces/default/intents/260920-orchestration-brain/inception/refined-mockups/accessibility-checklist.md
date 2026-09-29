# Accessibility Checklist — 統一入口大腦（WCAG 2.1 AA）

<!-- Stage: refined-mockups（Inception 2.5）· Record: 260920-orchestration-brain
     依 .claude/knowledge/aidlc-design-agent/accessibility-wcag.md 的 POUR 四原則 -->

## 適用範圍（先劃清界線，否則清單會宣稱它管不到的東西）

`[R7]` 定案「桌機 ＋ 響應式 ＋ WCAG 2.1 AA」，而線框 §7 的「範圍界定」逐字把
**響應式**的承諾範圍限縮為**入口頁與脈絡列**，明寫本 intent「不隱含承諾重繪既有
畫布」。本清單沿用同一條界線並把它擴及全部無障礙項目：

| 範圍 | 畫面 | 本清單是否管 |
|---|---|---|
| ✅ 本 intent 新增 | 入口頁（`BrainChat`、`ContextBar`、`WorkItemDock`、`ClarifyCandidates`、`CostAnswerCard`、`StreamingMessage`、`CreateConfirmCard`、`ObjectPicker`） | **管** |
| ✅ 本 intent 新增 | `/memory`（`MemoryPage`／`MemoryZone`） | **管** |
| ✅ 本 intent 改動 | `Sidebar` 新增的兩個獨立項 | **管**（只管新增的兩項） |
| ❌ 既有、本 intent 不改 | `/workspace` 的 `DrawioCanvas`、`/assessment`、`/cost`、`/admin/*` | **不管**——`[R7]` 未承諾，且本 intent 對它們零 e2e 掩護 |
| ⚠️ 既有、本 intent 沿用 | `PaginationControl`（記憶頁分頁） | **管其在記憶頁的表現**，但不修它本身的既有問題（見 §5） |

---

## 驗證機制（`[DM:D6]`=A）

引入 **`@axe-core/playwright`**，對入口頁與 `/memory` 各執行一次自動掃描，
**違規即 CI 紅燈**。它是既有 Playwright 層的 plugin，不是新測試框架。

**誠實的能力界線**：`accessibility-wcag.md` 逐字記載自動掃描「catches ~30% of
issues」。因此本清單**逐項標明**驗證方式，不讓「有 axe 了」被讀成「AA 已達成」：

| 標記 | 意義 |
|---|---|
| `[axe]` | axe 能機械判定，違規即 CI 紅燈 |
| `[人工]` | axe 判不到，須人工驗證；驗證時機為 `build-and-test`（3.6） |
| `[設計已定]` | 已在 `mockups.md`／`interaction-spec.md` 定案為規格，實作照做即成立；`[axe]` 或 `[人工]` 為其驗收 |

**這道閘門改變了什麼**：`stories.md` 的 `AC-A11Y.1`／`AC-A11Y.2` 在 `[US]` 關卡
被記為「無自動化承載層」的已接受風險。`[DM:D6]`=A 讓其中 **`[axe]` 標記的部分
取得承載**；`[人工]` 標記的部分**仍然沒有**。這是部分改善，不是缺口消除——
不得把本清單的存在當成 AA 已可驗證。

---

## P — Perceivable（可感知）

| # | 要求 | 落點 | 驗證 |
|---|---|---|---|
| P-1 | 所有非裝飾性圖示有文字替代；裝飾性圖示 `alt=""` 或 `aria-hidden="true"` | 全部新元件的 inline SVG | `[axe]` |
| P-2 | 一般文字對比 ≥ 4.5:1；大字（≥18px bold 或 ≥24px）≥ 3:1；UI 元件 ≥ 3:1 | 全部新元件。沿用的 `brand-*` 色階為 Tailwind blue 色階，`brand-600` 起對白底達 4.5:1 | `[axe]` |
| P-3 | **不得只靠顏色傳達意義** | 五個工作項狀態（`處理中`／`等待中`／`完成`／`失敗`／`已停掉`）**皆以文字為主要載體**，圖示與顏色為輔；共享／獨立徽章文字即 `共享`／`獨立`；成本金額不只靠顏色 | `[設計已定]` ＋ `[人工]` |
| P-4 | 成本卡片的分項數字有結構語意（非純視覺排版） | `CostAnswerCard` 的 `breakdown` 以 `<dl>`／`<table>` 表達，不用純 `<div>` 排版 | `[axe]` 部分（表格標頭）＋ `[人工]` |
| P-5 | 標題階層不跳級 | 記憶頁 `h1`「我的記憶」＋ 三區各 `h2`；入口頁 `h1`「入口」 | `[axe]` |
| P-6 | 無每秒閃爍 3 次以上的內容 | 串流游標、`animate-pulse`、`animate-bounce` 皆為 ≥0.4s 週期 | `[人工]` |

---

## O — Operable（可操作）

| # | 要求 | 落點 | 驗證 |
|---|---|---|---|
| O-1 | 全部功能可純鍵盤操作 | 脈絡列展開、切換對象、建立表單、候選選擇、工作項「不是這個」、記憶刪除、分頁 | `[人工]`（axe 判不到「能不能走完流程」） |
| O-2 | 每個可互動元素有可見焦點指示，且**不得無補償地 `outline: none`** | 全部新元件。**既有程式 7 處 `focus:outline-none` 全部都有補償**（6 處同元素、`ChatBox.tsx:361` 由容器 `:348` 的 `focus-within:ring-2` ＋ `focus-within:border-brand-500`）——這是要維持的既有紀律，不是要修的缺口 | `[axe]` 部分 ＋ `[人工]` |
| O-3 | Tab 序符合視覺順序 | 入口頁：頁首 → 記憶捷徑 → 脈絡列 → 常駐區 → 對話流 → 輸入列 | `[人工]` |
| O-4 | 無鍵盤陷阱 | `ObjectPicker` 是唯一陷焦點者（它是覆蓋層），必須 Escape 可出、關閉後焦點回 `[切換對象]` | `[人工]` |
| O-5 | 候選群組以方向鍵移動、Enter 選定；退出鈕為群組**最後一個**可聚焦項 | `ClarifyCandidates`（承線框 §12 的既有註記） | `[設計已定]` ＋ `[人工]` |
| O-6 | 觸控目標 ≥ 44×44 CSS px | 全部可點元素。輸入框沿用既有 `min-h-[44px]`（`ChatBox.tsx:361`） | `[人工]` |
| O-7 | 相鄰觸控目標間距 ≥ 8px | 候選鈕 `gap-2`（8px）、工作項列表 `space-y-*` | `[設計已定]` |
| O-8 | 無時間限制，或可延長／關閉 | 本 intent 無倒數或自動關閉的 UI。成本 job 的 `timeout` 是後端行為，其訊息不自動消失 | `[設計已定]` |
| O-9 | 動畫遵守 `prefers-reduced-motion` | 串流游標閃爍、載入三點、`--animate-slideInDown`／`--animate-fadeInUp` | `[人工]`（`interaction-design-patterns.md` 明列此要求） |
| O-10 | 就地確認列不使用 `window.confirm` | 記憶刪除、建立確認——皆為 DOM 內元素 | `[設計已定]`（理由：瀏覽器 modal 無法套用無障礙規格，且會阻塞事件迴圈） |

---

## U — Understandable（可理解）

| # | 要求 | 落點 | 驗證 |
|---|---|---|---|
| U-1 | 頁面語言在 HTML 宣告 | 既有 `index.html` 的 `lang`——**本站未查證其現值**，列為 `[人工]` 待確認 | `[axe]` |
| U-2 | 表單輸入有**可見** label 或 `aria-label`，**不得只靠 placeholder** | `ObjectPicker` 的搜尋框、建立表單的名稱欄、對話輸入框 | `[axe]` |
| U-3 | 錯誤訊息具體、以文字說明（非只有紅框） | 建立失敗（名稱重複／無權限／其他三類）、記憶載入失敗、串流中斷、成本 `failed`／`timeout` | `[設計已定]` ＋ `[人工]` |
| U-4 | 導覽在各頁一致 | `Sidebar` 兩個新項在全部頁面位置相同；脈絡列在入口頁與子頁面為**同一個元件**（`[R3]`） | `[設計已定]` |
| U-5 | 焦點或輸入不造成非預期的情境變更 | 選候選、切換對象會改變畫面內容——皆由**使用者明確點擊**觸發，非焦點或輸入觸發 | `[設計已定]` |
| U-6 | 破壞性操作需確認 | 記憶逐則刪除（就地確認列）；建立雖非破壞性但因由意圖識別觸發而一律確認（理由見 `mockups.md` M5） | `[設計已定]` ＋ `[人工]` |
| U-7 | **`empty` 與 `error` 態必須可區分** | 記憶頁三區、`ObjectPicker` 清單。理由：兩者共用「沒有記憶」的畫面會讓使用者在讀取失敗時以為記憶被清空，而記憶正是他被承諾可稽核與刪除的資料 | `[設計已定]` ＋ `[人工]` |

---

## R — Robust（穩健）

| # | 要求 | 落點 | 驗證 |
|---|---|---|---|
| R-1 | 語意化 HTML；優先原生元素而非 `div role="button"` | 全部新元件 | `[axe]` |
| R-2 | ARIA 角色使用正確且不過度 | `ContextBar` `region`、`WorkItemDock` `region`、`ClarifyCandidates` `group`、`ObjectPicker` `dialog`＋`aria-modal`、記憶三區 `region`＋`aria-labelledby`、條目 `list`／`listitem` | `[axe]` |
| R-3 | 頁面內 id 唯一 | 工作項與記憶條目皆以 id 生成 `aria-labelledby`／`data-testid`，須保證唯一 | `[axe]` |
| R-4 | 動態內容變更有播報 | 沿用 `EstimateAdvicePanel.tsx:278` 的 `sr-only aria-live="polite"` 形狀。播報點：對象變更、工作項狀態變更、成本估算完成、記憶刪除完成、反問訊息出現 | `[人工]`（axe 判不到播報**內容**是否有意義） |
| R-5 | **串流不逐 token 播報** | `StreamingMessage`：串流中以 `aria-busy="true"` 標示，**完成時**播報整段。逐 token 播報會讓螢幕閱讀器持續打斷自己 | `[設計已定]` ＋ `[人工]` |
| R-6 | 同名按鈕以 `aria-label` 區分 | 工作項的「不是這個」須含該項工作描述；記憶的「刪除」須含該則內容摘要（承線框 §13 的既有註記） | `[人工]` |

---

## 五個狀態的非顏色依賴表（P-3 的具體落實）

| 狀態 | 文字 | 圖示 | 額外的非顏色資訊 |
|---|---|---|---|
| 處理中 | `處理中` | `(o)` | 動態載入指示 |
| 等待中 | `等待中` | 無 | 下方一行說明在等哪一項 |
| 完成 | `完成` | `[v]` | — |
| 失敗 | `失敗` | `(!)` | 下方一行失敗原因 |
| 已停掉 | `已停掉` | `(x)` | 下方一行「有沒有留下東西」（含 `unknown` 的誠實表達） |

**每一列都有文字**——這是 P-3 成立的理由，不是圖示或顏色。

---

## 本清單沒有涵蓋的（明講，不留空白）

| 未涵蓋項 | 為什麼 |
|---|---|
| 既有頁面的無障礙現況 | `[R7]` 的承諾範圍不含它們（線框 §7），且本 intent 對它們零 e2e 掩護 |
| 螢幕閱讀器實測（VoiceOver／NVDA） | `accessibility-wcag.md` 列為測試方法之一，但本 intent 無此資源承諾。`[人工]` 項的實際驗證深度由 `build-and-test` 決定 |
| 200%／400% 縮放測試 | 同上，列為 `[人工]` 的建議項而非要求項 |
| 色盲模擬測試 | 同上。P-3 的「不只靠顏色」已從設計層排除大部分風險 |
| `PaginationControl.tsx:73` 的 `focus:ring-blue-400` token 不一致 | 它是既有元件的既有問題；在本 intent 內改它等於動到 Admin 頁的分頁（無 e2e 掩護）。列為觀察項，不列為回補項 |

---

## Assumptions & Open Questions

- `@axe-core/playwright` 對入口頁與 `/memory` 的掃描**能抓到哪些項目**，是依
  `accessibility-wcag.md` 的「~30%」與 axe 規則集的一般認知標記的，**本站未實跑
  驗證**每一個 `[axe]` 標記是否真的被該工具涵蓋 [assumption]
- `index.html` 的 `lang` 屬性現值**本站未查證**（U-1），故列為待確認 [assumption]
- `brand-600` 起對白底達 4.5:1 是依「Tailwind blue 色階」的一般認知，**本站未以
  對比度工具實測**每一組前景／背景配色 [assumption]
- `[人工]` 項的驗證時機標為 `build-and-test`（3.6，ALWAYS），該站的執行不成問題；
  但**驗證深度**（是否含螢幕閱讀器實測）未定 [assumption]
- 本清單把 `AC-A11Y.1`／`AC-A11Y.2` 的自動化承載從「無」改善為「部分」，
  但**未回改 `stories.md`**（已核可，依 `project.md` 的 `refined-mockups:c3`
  不回改上游）；兩份文件的差異是刻意的，本檔為較新的事實 [assumption]
