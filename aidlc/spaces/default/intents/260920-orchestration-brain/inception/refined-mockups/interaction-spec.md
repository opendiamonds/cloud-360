# Interaction Specification — 統一入口大腦

<!-- Stage: refined-mockups（Inception 2.5）· Record: 260920-orchestration-brain
     格式依 .claude/knowledge/aidlc-design-agent/component-spec-template.md -->

## 讀法

本檔用 `component-spec-template.md` 的欄位格式逐一規格化本 intent 新增的元件。
**不規格化既有元件**（`ChatBox`、`Layout`、`Sidebar`、`PaginationControl`、
`EstimateHistoryDrawer`）——它們的沿用方式在 `design-system-mapping.md`。

每個元件的 `Props` 欄只列**畫面需要的資料**，不預設後端的回應形狀；型別契約的
正式落點是 NFR5／N-1 要求的 WS 訊息型別來源（見 `mockups.md` 交接事項 H-2）。

**測試識別碼**沿用既有慣例：kebab-case ＋ 功能前綴。既有 24 個的前綴為
`estimate-*`／`advice-*`／`chat-*`／`cost-page`／`sidebar-toggle`；本 intent
一律用 **`brain-*`** 前綴，記憶頁用 **`memory-*`**。

---

## 三條不變量（本站明文釘住，供測試斷言）

這三條不是元件規格，是**跨元件的約束**。它們存在的理由都一樣：`[DM:D1]`=C、
`[DM:D2]`=D、`[DM:D4]`=C 三個定案各自製造了「同一件事有兩個位置」的結構，而
兩個位置若各自持有自己的判斷或副本，畫面上**不會有任何跡象顯示哪一個是對的**。
使用者在提問時已看過這三項代價並選擇並存，故處置是把單一來源寫成規格，不是
回頭改決定。

| # | 不變量 | 來自 | 可斷言的形式 |
|---|---|---|---|
| **INV-1** | 工作項的兩個渲染位置（常駐區、對話流）讀**同一份** work-item 集合；差異只在過濾條件 | `[DM:D4]`=C | 對任一 work-item id，兩處渲染的 `status` 必須相等；常駐區的集合必須等於全集依 `status ∈ {處理中, 等待中}` 的過濾結果 |
| **INV-2** | 兩個建立入口（`ObjectPicker` 的表單、`CreateConfirmCard`）呼叫**同一個** `ObjectCreateAction`；授權檢查、稽核紀錄、錯誤訊息各只有一份 | `[DM:D2]`=D | 兩條路徑的失敗訊息文案相同；程式層 grep 建立操作的呼叫點應**恰有一處**實作、兩處呼叫 |
| **INV-3** | 記憶入口的兩個位置（Sidebar 項、入口頁捷徑）用**同一個**顯示條件 | `[DM:D1]`=C | 兩處的顯示條件必須解析到同一個判定（目前為「已登入」，見 `mockups.md` M0 的查證） |

---

## ContextBar（脈絡列）

| Field | Value |
|---|---|
| Component | ContextBar |
| Description | 常駐顯示目前作業對象（專案 / 系統 / 架構圖），並承載共享↔獨立切換與對象切換 |
| Category | navigation |

**既有決定，本站不改**：`[R2]`（常駐但不佔寬度、可展開）、`[R3]`（與子頁面同一個
元件）、`[R6]`（共享↔獨立切換由它承載）。本站只補狀態表與無障礙細節。

### States

| State | Description | Trigger |
|---|---|---|
| default-collapsed | 單行顯示三層對象名稱 ＋ 共享徽章 ＋ 展開鈕 | page load |
| expanded | 顯示專案／系統／架構圖／最後異動四欄 ＋ 兩個動作鈕 | 點展開鈕 |
| no-object | 顯示「尚未選定」，展開鈕仍可用但展開後只有 `[切換對象]` | 無作業對象 |
| independent | 共享徽章改為 `[獨立]`，並在該頁生效 | 使用者選「改為獨立對話」 |
| loading | 對象名稱位置顯示骨架列 | 對象資料載入中 |
| error | 顯示「無法載入作業對象」＋ 重試；`[切換對象]` 仍可用 | 載入失敗 |

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| object | `{ projectName, systemName, diagramName, lastModifiedAt } \| null` | yes | — | `null` 即 no-object 態 |
| sharing | `'shared' \| 'independent'` | yes | `'shared'` | 顯示哪一個徽章 |
| onSwitchObject | `() => void` | yes | — | 開啟 `ObjectPicker` |
| onToggleSharing | `() => void` | yes | — | 切換共享↔獨立 |

### Responsive Behaviour

| Breakpoint | Behaviour |
|---|---|
| `< 768px` | 收成單行、長名稱換行堆疊不截斷、不橫向捲動（承線框 §7／§10） |
| `>= 768px` | 預設佈局 |

**只有一個斷點**：`[DM:D7]`=A，理由與查證見 `mockups.md` M8。

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | `region`，`aria-label="目前作業對象"`（承線框 §3 的既有註記） |
| Keyboard interaction | 展開鈕為 disclosure（`aria-expanded`），Enter／Space 切換；兩個動作鈕在 Tab 序內 |
| Contrast ratio | 共享／獨立徽章 4.5:1；徽章**不只靠顏色**區分，文字即 `共享`／`獨立` |
| Screen reader | 對象變更時以 `aria-live="polite"` 播報新對象名稱（沿用 `EstimateAdvicePanel.tsx:278` 的 `sr-only` 播報區形狀） |
| Focus management | 展開後焦點留在展開鈕；收合不移動焦點 |

### Test ids

`brain-context-bar`、`brain-context-toggle`、`brain-context-sharing-badge`、
`brain-context-switch-object`

---

## WorkItemStore（狀態來源，非視覺元件）

| Field | Value |
|---|---|
| Component | WorkItemStore |
| Description | 工作項的單一狀態來源；兩個視圖（常駐區、對話流）皆由它取值 |
| Category | display（狀態容器） |

**它存在的唯一理由是 INV-1**。`[DM:D4]`=C 讓工作項有兩個渲染位置；若沒有一個
共同來源，兩處會各自持有副本。

### 狀態集合

`[RA:FR1.2]` 鎖定狀態值集合**不得少於五個**：`處理中`／`等待中`／`完成`／
`失敗`／`已停掉`。本檔**不定義狀態機的轉換條件與終端性**——上游明寫那是下游的事
（見 `mockups.md` 交接事項 H-4）。本檔只定：

- 每個 work-item 必有 `id`、`label`、`status`、`capability`（交給哪個能力）。
- `等待中` 的項另帶 `waitingOn: id`（在等哪一項）；畫面據此在該項下方顯示一行說明。
- `失敗` 的項另帶 `failureReason: string`；畫面必須顯示它。
- `已停掉` 的項另帶 `sideEffect: 'none' | 'unknown' | string`；畫面必須把它
  講出來（`[RA:FR1.4]` 逐字要求「畫面應明講原本那件有沒有留下東西」）。
  `'unknown'` 是合法值——線框 §13 明寫本站不承諾系統真能做到「停掉時不留半成品」，
  故畫面必須能誠實表達「不確定有沒有留下東西」，不得只有 `'none'` 一種。

### 契約端點三問（本站自檢 2 的結果，逐欄指名）

依 `project.md` 的送審前自檢第 2 項——每一個宣告的**欄位**（誰寫、誰讀、誰清）與
**方法**（誰擁有、誰呼叫）都要能指名，缺一即缺口。本站對**整個 stage 的全部產出**
跑過一次，結果如下（**含兩處查出的缺口**）：

| 欄位／方法 | 誰寫 | 誰讀 | 誰清 |
|---|---|---|---|
| work-item 的 `id`／`label`／`status`／`capability` | **大腦**，經 WS 訊息（型別契約的落點為 NFR5／N-1） | `WorkItemDock` ＋ `WorkItemList` | **缺口——見下方 G-1** |
| work-item 的 `waitingOn` | 大腦，於產生 `等待中` 項時 | `WorkItemDock`／`WorkItemList` 的說明行 | 隨該項一同清除 |
| work-item 的 `failureReason` | 大腦，於轉入 `失敗` 時 | 同上 | 同上 |
| work-item 的 `sideEffect` | **大腦**，於轉入 `已停掉` 時；值域 `'none' \| 'unknown' \| string` | 同上 | 同上 |
| 作業對象 `object` | 三個寫入端：大腦（從敘述認出）、`ObjectPicker.onPick`、`CreateConfirmCard` 建立成功後 | `ContextBar`（入口頁與子頁面同一元件） | **缺口——見下方 G-2** |
| `sharing` | `ContextBar.onToggleSharing` | `ContextBar` ＋ 該頁的對話區 | 不適用（恆為兩值之一） |
| clarify 候選 | 大腦，經 `clarify` 訊息 | `ClarifyCandidates` | 使用者直接輸入新句子時轉 `stale`（承 user-flow Flow 5） |
| `estimateId`／`estimateLabel` | 成本回應 | `CostAnswerCard` | 不適用（隨訊息不可變） |
| 記憶列的擁有者與可見範圍 | **記憶層**依已驗證身分設定（`[RA:FR4.3a]`／`[RA:FR4.3b]`） | `MemoryPage` | 使用者逐則刪除（`[RA:FR4.6]`）＋ 90 天 workflow（`[RA:FR4.5a]`） |

| 方法 | 誰擁有 | 誰呼叫 |
|---|---|---|
| `WorkItemStore` | **入口頁**（它是唯一同時渲染兩個視圖的頁面；子頁面不渲染工作項） | `WorkItemDock`、`WorkItemList` 讀；WS 訊息處理器寫 |
| `ObjectCreateAction` | **後端的建立端點**；前端側的呼叫封裝由入口頁擁有 | `ObjectPicker.onCreate`、`CreateConfirmCard.onConfirm`（恰兩處，INV-2） |
| `ContextBar.onSwitchObject`／`onToggleSharing` | 承載脈絡列的那一頁（入口頁或子頁面） | `ContextBar` |

### 兩處契約缺口（本站查出，不自行定案）

| # | 缺口 | 為什麼它是缺口而不是細節 |
|---|---|---|
| **G-1** | **沒有任何一端負責清除 work-item 集合。** 誰寫、誰讀都指得出來，誰清指不出來 | 若永不清除，長時間使用後常駐區的過濾成本與對話流的渲染量單向成長；而「什麼事件代表一批工作結束」是語意問題不是實作細節——切到獨立對話算不算？重新載入頁面算不算？跨 session 還原（`[RA:NFR4]` 要求重啟後脈絡可還原）時舊工作項要不要回來？ |
| **G-2** | **沒有任何一端負責把作業對象清回 `no-object`。** `ContextBar` 宣告了 `no-object` 狀態、線框 §2 也畫了它，但三個寫入端都只會設值，沒有一端會清 | `no-object` 因此只在**首次使用**可達，之後永不可達——這正是 `project.md` 的 `functional-design:c10` 警告的形狀：狀態在文件上看起來已處理，實際是死碼。可能的清除事件（切到獨立對話、刪除該對象、登出）都未定案 |

兩項皆列為 `mockups.md` 的交接事項 **H-8**，指派 `domain-design`（2.6，CONDITIONAL，
skip 則轉 `units-generation`，ALWAYS）。**本站不自行定案**——它們是狀態語意問題，
需要與 `[RA:NFR4]` 的重啟還原一併決定。

### 兩個視圖的過濾條件

| 視圖 | 過濾 | 排序 |
|---|---|---|
| 常駐區（`WorkItemDock`） | `status ∈ {處理中, 等待中}` | 依建立順序 |
| 對話流（`WorkItemList`） | 不過濾 | 依建立順序，附屬於觸發它的那一則訊息 |

**可斷言的形式見 INV-1。** 若兩處顯示不同狀態，判為實作缺陷而非設計意圖。

---

## WorkItemDock（常駐區）

| Field | Value |
|---|---|
| Component | WorkItemDock |
| Description | 脈絡列下方的常駐區，只列未完成的工作項 |
| Category | display |

### States

| State | Description | Trigger |
|---|---|---|
| hidden | 無未完成項時整區不渲染（**不留空殼**） | 過濾結果為空 |
| expanded | 列出未完成項，各帶狀態徽章與「不是這個」 | 有未完成項且寬螢幕 |
| collapsed | 單行計數 `進行中 (N) [v]` | 窄螢幕預設，或使用者手動收起 |

`hidden` 態使畫面對「`等待中` 是否可達」不敏感——即使該狀態永不出現，
常駐區仍正確（見 `mockups.md` M1）。

### Responsive Behaviour

| Breakpoint | Behaviour |
|---|---|
| `< 768px` | 預設 `collapsed`；理由見 `mockups.md` M8（四個固定區塊會壓縮對話區） |
| `>= 768px` | 預設 `expanded` |

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | `region`，`aria-label="進行中的工作"` |
| Keyboard interaction | 收合鈕為 disclosure；每項的「不是這個」在 Tab 序內 |
| Label / aria-label | 每個「不是這個」的 `aria-label` **必須含該項的工作描述**（承線框 §13 的既有註記——多個同名按鈕螢幕閱讀器無法分辨） |
| Screen reader | 狀態變更以 `aria-live="polite"` 播報，格式為「<工作描述>：<新狀態>」 |
| Contrast ratio | 狀態徽章 4.5:1；**五個狀態皆以文字為主要載體**，圖示與顏色為輔（見 `accessibility-checklist.md` P-3） |

### Test ids

`brain-workitem-dock`、`brain-workitem-dock-toggle`、`brain-workitem-{id}`、
`brain-workitem-{id}-status`、`brain-workitem-{id}-reject`

---

## ClarifyCandidates（反問候選）

| Field | Value |
|---|---|
| Component | ClarifyCandidates |
| Description | 意圖信心不足時列出候選判讀，使用者選一個或要求重講 |
| Category | input |

**`[DM:D3]`=A：資料來自結構化 `clarify` 訊息，前端不做文字解析。**

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| candidates | `{ id, label, capability, targetHint? }[]` | yes | — | 順序即顯示順序 |
| onPick | `(id) => void` | yes | — | 選定某候選 |
| onRestate | `() => void` | yes | — | 「都不是，我再講一次」 |
| disabled | `boolean` | no | `false` | 送出中時停用 |

**`confidence` 不在 Props 內，且不得加入。** 理由是一條已登記的上游不確定性：
**OQ-10** 記載 `[RA:FR1.6]`（路由層必須輸出 0–1 信心值）**可能不成立**，屆時
`[RA:FR1.3]` 的觸發條件改以「候選並列且無單一最高分」表達，而上游明寫
「畫面本身不必改」。若把信心值列為必填 Prop，替代表達就渲染不出來——畫面會
因為一個尚未定案的模型選型而壞掉。完整說明見 `mockups.md` M2。

### States

| State | Description | Trigger |
|---|---|---|
| default | 列出候選 ＋ 退出鈕 | 收到 `clarify` 訊息 |
| picking | 被選中的候選顯示載入指示，其餘停用 | 點某候選 |
| stale | 整組候選淡化並停用 | 使用者直接輸入新的一句話（承 user-flow Flow 5 的 Error path——舊候選作廢，不殘留等待） |

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | `role="group"`，`aria-label="請選擇你指的是哪一件事"`（承線框 §12 的既有註記） |
| Keyboard interaction | 方向鍵在候選間移動、Enter 選定；退出鈕為該組**最後一個**可聚焦項，使鍵盤使用者不需離開群組即可退出 |
| Screen reader | 詢問訊息以 `aria-live="polite"` 播報 |
| Contrast ratio | 候選鈕與退出鈕 4.5:1；退出鈕以**虛線邊框**而非僅顏色區分（沿用 `ChatBox.tsx:288` 既有「其他」選項的 `border-dashed` 形狀） |

### Test ids

`brain-clarify`、`brain-clarify-candidate-{id}`、`brain-clarify-restate`

---

## ObjectPicker（切換對象選單，含就地建立）

| Field | Value |
|---|---|
| Component | ObjectPicker |
| Description | 依專案分組列出可選系統，並提供就地建立專案／系統 |
| Category | navigation |

### States

| State | Description | Trigger |
|---|---|---|
| default | 搜尋框 ＋ 分組清單 ＋ 底部兩個建立入口 | 開啟 |
| loading | 清單位置顯示骨架列；建立入口仍可用 | 清單載入中 |
| empty | 無任何專案時只顯示「+ 新增專案」＋ 一行說明 | 清單為空 |
| no-match | 搜尋無結果時顯示「沒有符合的對象」，**保留**建立入口 | 搜尋無命中 |
| error | 顯示「無法載入清單」＋ 重試；建立入口仍可用 | 載入失敗 |
| creating | 建立表單就地展開（名稱單欄） | 點任一建立入口 |

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| groups | `{ projectId, projectName, systems: { id, name }[] }[]` | yes | — | 分組清單 |
| currentSystemId | `string \| null` | yes | — | 標示「目前」 |
| onPick | `(systemId) => void` | yes | — | 選定 |
| onCreate | `(kind: 'project' \| 'system', name: string, parentProjectId?) => Promise<void>` | yes | — | **必須是 `ObjectCreateAction`**（INV-2） |

**「+ 新增系統」的停用條件**：無選定專案時 `disabled` ＋ 一行說明「先選一個專案」。
依 `interaction-design-patterns.md` 的 Constraints——先停用無效選項，不要選完才報錯。

**建立表單只要名稱**：其餘欄位待 `domain-design` 依 **OQ-14** 定案（交接事項 H-1）。

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | `role="dialog"` ＋ `aria-modal="true"`（它是覆蓋層），或 `role="listbox"` 若實作為下拉 |
| Keyboard interaction | Escape 關閉；方向鍵在項目間移動；焦點陷在選單內；關閉後焦點回 `[切換對象]` 鈕 |
| Label / aria-label | 搜尋框有可見 label 或 `aria-label="搜尋作業對象"`（不只用 placeholder——`ux-guide.md` 明列 placeholder-only 為失敗形式） |
| Screen reader | `no-match` 態以 `aria-live="polite"` 播報結果數 |

### Test ids

`brain-object-picker`、`brain-object-search`、`brain-object-item-{id}`、
`brain-object-create-project`、`brain-object-create-system`、`brain-object-create-name`

---

## CreateConfirmCard（對話式建立的確認卡）

| Field | Value |
|---|---|
| Component | CreateConfirmCard |
| Description | 對話流中，建立意圖被辨識後的確認卡；確認後才寫入 |
| Category | feedback（含動作） |

**這道確認是本站的設計決定，不是使用者的定案。** 完整理由見 `mockups.md` M5：
`[DM:D2]`=D 讓建立成為由意圖識別觸發的**寫入**操作，而 `[RA:NFR1]` 對意圖識別
只承諾 80% 準確率；誤建會在資料庫累積使用者沒要求的資料列，且**沒有任何畫面會
提示那是誤建**。

**這道確認與 `[RA:FR1.7]` 的 0.7 門檻無關**：信心 0.99 也要確認，因為問題不是
「大腦有多確定」而是「使用者有沒有要」。它不推翻任何上游定案——`[RA:FR1.3]`
管信心不足時不交辦，本規則管寫入型交辦一律確認，兩者疊加。

### States

| State | Description | Trigger |
|---|---|---|
| default | 顯示類型、名稱 ＋ 三個動作（建立／取消／改個名字） | 辨識為建立意圖 |
| submitting | `[建立]` 轉 `建立中...` 並停用全部動作 | 點建立 |
| success | 卡片轉為結果訊息，並**自動把作業對象切為新建的對象** | 建立成功 |
| error | 就地顯示錯誤（名稱重複／無權限），**卡片不消失**，可改名重試 | 建立失敗 |
| cancelled | 卡片轉為一行「已取消」 | 點取消 |

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| kind | `'project' \| 'system'` | yes | — | 要建立什麼 |
| name | `string` | yes | — | 大腦從敘述中取出的名稱 |
| parentProjectId | `string \| null` | no | `null` | `kind='system'` 時必要 |
| onConfirm | `() => Promise<void>` | yes | — | **必須是 `ObjectCreateAction`**（INV-2） |
| onCancel | `() => void` | yes | — | 取消 |
| onRename | `() => void` | yes | — | 改個名字；回到哪個狀態未定（見 Assumptions） |

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | `article` ＋ 標題（它在對話流內，不是 modal，故**不**陷焦點） |
| Keyboard interaction | 三個動作在 Tab 序內；`[建立]` 為預設焦點 |
| Screen reader | 卡片出現時以 `aria-live="polite"` 播報「即將建立 <類型>：<名稱>，請確認」 |
| Contrast ratio | `[建立]` 為 primary、4.5:1；三個動作皆有文字 label，不只靠圖示 |

### Test ids

`brain-create-confirm`、`brain-create-confirm-submit`、
`brain-create-confirm-cancel`、`brain-create-confirm-rename`

---

## ObjectCreateAction（共用寫入路徑，非視覺元件）

| Field | Value |
|---|---|
| Component | ObjectCreateAction |
| Description | 建立專案／系統的唯一寫入路徑；兩個入口共用 |
| Category | （動作契約） |

**它存在的唯一理由是 INV-2**。`[DM:D2]`=D 有兩個建立入口；若各自實作，授權檢查、
稽核紀錄與錯誤訊息就會有兩份，而兩份必有一份先過期。

### 契約

| 項 | 內容 |
|---|---|
| 輸入 | `kind`、`name`、`parentProjectId?` |
| 授權 | 一律經 `require_story_action`（`[RA:FR9.5]` 逐字：不得有任何繞過該 dependency 的路徑，含同進程直呼 service 層）。角色集合見 **OQ-14** |
| 失敗訊息 | 兩個入口顯示**相同文案**；至少區分「名稱重複」「無權限」「其他」三類 |
| 成功後 | 回傳新建對象的 id；呼叫端負責把作業對象切過去 |
| 稽核 | 建立動作留紀錄（行為主體為使用者本人，形狀承 `[RA:FR10.3]` 的同一原則） |

**可斷言的形式**：程式層 grep 建立操作應**恰有一處實作、兩處呼叫**。

---

## CostAnswerCard（成本答案卡片）

| Field | Value |
|---|---|
| Component | CostAnswerCard |
| Description | 對話流中呈現成本答案，並深連到同一份估價 |
| Category | display |

**既有決定**：`[R4]`（結構化卡片 ＋ 前往成本頁連結）、`[RA:FR10.6]`、`[RA:FR10.7]`
（就地在入口頁呈現）。**本站新增**：`[DM:D5]`=A 的深連。

### States

| State | Description | Trigger |
|---|---|---|
| progress | **同一則訊息就地更新**的進度文字（不是本元件——見下方註） | 收到 `progress` 事件 |
| default | 總額 ＋ 分項 ＋ 具名該份估價的連結 | 收到 `completed` |
| no-estimate-id | 同上但連結改為無參數 `[到成本頁 ->]` | 回應未帶估價 id |
| failed | 顯示失敗訊息，可分辨「已失敗」與「還在跑」 | 收到 `failed` |
| timeout | 顯示逾時訊息，同上可分辨 | 收到 `timeout` |

**`progress` 不由本元件承載**：`[R5]` 定案進度是「單一則就地更新的訊息」，
它是訊息流裡的一則文字，`completed` 後**被本卡片取代**。兩者是同一個訊息槽的
兩種內容，不是兩個並存的元件。`failed`／`timeout` 各須有可見訊息
（`[RA:FR10.5]`）。

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| systemName | `string` | yes | — | 卡片標題 |
| total | `{ amount, currency, period }` | yes | — | 月預估總額 |
| breakdown | `{ label, amount }[]` | yes | — | 分項；分類粒度取自既有成本回應（見 Assumptions） |
| estimateId | `string \| null` | yes | — | `null` 即 `no-estimate-id` 態 |
| estimateLabel | `string \| null` | no | `null` | 連結文字裡具名的估價名稱 |

**連結目標**：`/cost?estimate=<estimateId>`。零後端改動——`CostPage.tsx:2` 已
import `useSearchParams`、`:119` 已讀該參數、`:51`／`:242` 已寫它。

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | `article` ＋ 標題（承線框 §5 的既有註記） |
| Label / aria-label | 連結文字**自足**——含估價名稱，不用「點這裡」 |
| Contrast ratio | 金額 4.5:1；**金額不只靠顏色表達**（承線框 §5） |
| Screen reader | `progress` → `default` 的替換以 `aria-live="polite"` 播報「成本估算完成」 |

### Test ids

`brain-cost-card`、`brain-cost-card-total`、`brain-cost-card-link`

---

## StreamingMessage（大腦自身回覆的逐字串流）

| Field | Value |
|---|---|
| Component | StreamingMessage |
| Description | 大腦回覆的逐字顯示，游標停在最後一個字 |
| Category | display |

**與成本 job 的狀態輪詢是不同機制**（線框 §11 明文畫開、`[RA:FR10.8]` 明文禁止
把成本做成 token 級巢狀轉送）：本元件承載大腦自己的 token 串流；成本的
`progress` 是狀態事件的就地更新，見 `CostAnswerCard`。

### States

| State | Description | Trigger |
|---|---|---|
| streaming | 內容逐字增長，尾端顯示游標 | 收到內容 token |
| done | 游標移除，內容定稿 | 串流結束 |
| interrupted | 已顯示的內容保留 ＋ 一行「回覆中斷」 ＋ 重試 | 連線中斷 |
| empty-stream | 串流結束但零內容時顯示「沒有收到回覆」＋ 重試（**不留空白訊息**） | 結束且內容為空——**可達性未驗證**，見下方註 |

**`empty-stream` 的可達性未驗證**（本站自檢 1 抓出）：它要求大腦能以零內容 token
結束一次串流，而沒有任何已核可上游說明這是否可能。注意 `[RA:FR1.5]` 的
`prompt_guard` 命中會回**固定拒絕訊息**——那是有內容的，不走此態。本態因此是
**防禦性狀態**，保留理由是零內容若無 fallback 會留下一則空白訊息（使用者看不出
是壞了還是沒回答）。列為 `mockups.md` 交接事項 **H-7**。

### Accessibility

| Requirement | Implementation |
|---|---|
| Screen reader | **串流中不逐字播報**——`aria-live` 設在**完成時**播報整段，或用 `aria-busy="true"` 標示進行中。逐 token 播報會讓螢幕閱讀器持續打斷自己 |
| ARIA role | 訊息為 `article` 或列表項，沿用既有對話訊息的結構 |
| Keyboard interaction | 不可聚焦（純顯示）；`interrupted` 的重試鈕可聚焦 |
| 動畫 | 游標閃爍須遵守 `prefers-reduced-motion`（`interaction-design-patterns.md` 明列） |

### Test ids

`brain-stream-message`、`brain-stream-cursor`、`brain-stream-retry`

---

## MemoryPage / MemoryZone（我的記憶）

| Field | Value |
|---|---|
| Component | MemoryPage（含三個 MemoryZone） |
| Description | 檢視與逐則刪除三類記憶 |
| Category | display（含破壞性動作） |

**路由**：`/memory`，走 `ProtectedRoute` **不包** `CapabilityRoute`
（前例 `App.tsx:38–41` 的 `/waiting-approval`）。把關的是擁有者欄位而非角色——
理由與查證見 `mockups.md` M0。

### States（每個 Zone）

| State | Description | Trigger |
|---|---|---|
| default | 條目清單，各帶 `[刪除]` | 有資料 |
| empty | 「大腦還沒記住關於你的事」＋ 說明何時會開始累積 | 該區為空 |
| loading | 骨架列 | 載入中 |
| error | 「無法載入」＋ 重試——**不得顯示 empty 態** | 載入失敗 |
| deleting | 該條目淡化並停用，其餘可用 | 確認刪除後 |

**`empty` 與 `error` 必須可區分**（本檔明文定案）：兩者若共用「沒有記憶」的畫面，
使用者會在讀取失敗時以為記憶被清空了——而記憶正是他被承諾可以稽核與刪除的資料。

### 三區的條目形狀

| 區 | 每則顯示 | 分頁 |
|---|---|---|
| 語意記憶 | 一句可判斷對錯的自然語言陳述 | 不分頁 |
| 程序記憶 | 一句流程描述 | 不分頁 |
| 情節記憶 | 日期 ＋ 該段對話主題 | **分頁**，沿用既有 `PaginationControl` |

### 刪除的確認

逐則刪除是破壞性操作。本站選**確認**而非 undo，理由是 `[RA:FR4.7]` 要求刪除動作
本身留稽核紀錄——undo 會讓「刪了又復原」在稽核上變成兩筆需互相抵銷的紀錄，
而確認只產生一筆。確認文案須說明兩件事：大腦不再依據它回答、此刪除會被記錄。

**不使用 `window.confirm`**——它是瀏覽器 modal，會阻塞事件迴圈且無法套用
無障礙規格。使用就地的確認列（該條目原地展開「確定刪除？[刪除] [取消]」）。

### Accessibility

| Requirement | Implementation |
|---|---|
| ARIA role | 每區為 `region` ＋ `aria-labelledby` 指向區標題；條目為 `list`／`listitem` |
| Keyboard interaction | 每則的 `[刪除]` 在 Tab 序內；就地確認列出現後焦點移到 `[刪除]`，Escape 取消 |
| Label / aria-label | `[刪除]` 的 `aria-label` **必須含該則的內容摘要**（同 `WorkItemDock` 的理由——多個同名按鈕無法分辨） |
| Screen reader | 刪除完成以 `aria-live="polite"` 播報「已刪除：<摘要>」 |
| Heading hierarchy | 頁標題 `h1`「我的記憶」，三區各為 `h2`；不跳級 |

### Test ids

`memory-page`、`memory-zone-semantic`、`memory-zone-procedural`、
`memory-zone-episodic`、`memory-item-{id}`、`memory-item-{id}-delete`、
`memory-item-{id}-delete-confirm`、`memory-pagination`

---

## 互動流程（補線框未定的時序）

### 流程 A — 對話式建立（`[DM:D2]`=D）

1. 使用者輸入「幫我開一個叫 X 的專案」。
2. 大腦辨識為建立意圖 → 渲染 `CreateConfirmCard`（**不寫入**）。
3. 使用者點 `[建立]` → `ObjectCreateAction` → 成功後 `ContextBar` 切至新對象。
4. 失敗 → 卡片就地顯示錯誤，不消失，可改名重試。

**若辨識錯誤**（把別的需求誤判為建立）：使用者點 `[取消]`，卡片轉「已取消」，
**無任何寫入發生**。這是這道確認要防的那一類。

### 流程 B — 逐項導回時兩個視圖的同步（`[DM:D4]`=C）

1. 使用者點某項的 `[不是這個]`（可在常駐區或對話流任一處點）。
2. `WorkItemStore` 把該項改為 `已停掉` ＋ 設 `sideEffect`。
3. **兩個視圖同時更新**：該項從常駐區移出、在對話流保留並顯示終止狀態與
   `sideEffect` 說明。
4. 大腦改交給正確能力 → 新工作項加入，兩處同時出現。

### 流程 C — 記憶刪除

1. 使用者點某則的 `[刪除]` → 就地確認列展開，焦點移到 `[刪除]`。
2. 確認 → 該則轉 `deleting` → 成功後移除並播報。
3. 失敗 → 該則恢復可用並顯示錯誤訊息（不靜默）。

---

## Assumptions & Open Questions

- `CreateConfirmCard` 的 `[改個名字]` 按下後回到哪個狀態（就地編輯名稱，或回到
  對話輸入列重講）未定，本檔只定該動作存在 [assumption]
- 三區記憶每則的實際欄位集合待資料模型定案；本檔只定兩種顯示形狀 [assumption]
- 成本卡片 `breakdown` 的分類粒度取自既有成本能力的回應結構，**本站與線框皆未
  查證其欄位** [assumption]
- 記憶頁與 `ObjectPicker` 的 `loading` 態宣稱「沿用既有骨架屏慣例」，但本站
  **未逐頁量測既有骨架屏的實際形狀**（`RouteGuard.tsx` 的 `LoadingScreen` 是
  整頁 spinner，不是骨架屏——兩者不同）。已列為 `mockups.md` 交接事項 H-5 [assumption]
- `StreamingMessage` 的「完成時播報整段」是本站依 `accessibility-wcag.md` 的
  `aria-live` 原則推導，**未經螢幕閱讀器實測** [assumption]
- `WorkItemStore` 的 `sideEffect: 'unknown'` 是否真的會被使用，取決於實作層能否
  判定副作用——線框 §13 明寫本站不承諾系統做得到，故畫面保留該值 [assumption]
- **G-1／G-2 兩處契約缺口本站不定案**，已指派 `domain-design`（交接事項 H-8）。
  在它們定案之前，`ContextBar` 的 `no-object` 態**只在首次使用可達** [assumption]
- `CostAnswerCard.no-estimate-id` 與 `StreamingMessage.empty-stream` 兩個狀態的
  可達性皆未驗證（交接事項 H-6／H-7）；兩者皆保留為防禦性狀態，理由各自寫在該
  元件節內 [assumption]
