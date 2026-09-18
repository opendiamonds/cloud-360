# Interaction Specification — 最後活動時間欄位

<!-- Stage: refined-mockups（Inception 2.5）· 元件規格採 .claude/knowledge/aidlc-design-agent/component-spec-template.md 的格式。
     來源標籤定義見 refined-mockups-questions.md 的 ## Sources。 -->

## 上游輸入

- **wireframes**（`../../ideation/rough-mockups/wireframes.md`）：無紀錄態可聚焦、逾期態圖示＋變色的既定機制，本檔細化其互動細節。
- **user-flow**（`../../ideation/rough-mockups/user-flow.md`）：Flow 1 的「抄錄絕對時間值」與 Flow 3 的小螢幕存取，界定本元件需支援的操作。
- **stories**（`../user-stories/stories.md`）：AC-2.4（可聚焦與說明）、AC-2.5（可區分）、AC-4.2（跨佈局一致）為本檔的行為契約。
- **requirements**（`../requirements-analysis/requirements.md`）：FR-2.4、NFR-2 界定可及性義務。
- **team-practices**（`../practices-discovery/team-practices.md`）：前端 lint 的渲染純度規則直接約束本元件的實作形狀（見「實作約束」）。

## LastActivityCell

| Field | Value |
|---|---|
| Component | `LastActivityCell` |
| Description | 在使用者清單中呈現單一帳號的最後活動時間，含逾期標示與無紀錄態 |
| Category | display |

### States

| State | Description | Trigger | 呈現 |
|---|---|---|---|
| `default` | 有活動紀錄且未逾期 | 該帳號有時間值且距今未超過 90 天 | `2026-08-07 14:52`，`text-slate-300` |
| `overdue` | 有活動紀錄但已逾期 | 時間值距今**超過** 90 天（嚴格大於，不含恰為 90 天） | `(!) 2026-04-01 09:10`，時間值 `text-amber-300`，圖示帶文字替代 |
| `empty` | 無活動紀錄 | 該帳號的時間值為空 | 可聚焦的 `—`，`text-slate-300` |
| `empty:focus` | 無紀錄態獲得焦點 | Tab 鍵或滑鼠點擊 | 顯示說明「尚無活動紀錄」，並有可見的焦點框 |
| `empty:hover` | 無紀錄態滑鼠懸停 | mouseover | 顯示同一段說明文字 |

**本元件沒有 `loading` 與 `error` 狀態** —— 載入與錯誤由頁面層整塊替換整個表格處理（stories AC-1.9），元件不會在那兩種情況下被渲染。

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| `lastActivityAt` | `string \| null` | yes | — | ISO 8601 時間字串；`null` 表示無紀錄 |
| `isOverdue` | `boolean` | yes | — | 是否逾期。**由呼叫端傳入，元件不自行計算** —— 見「實作約束」 |

### Responsive Behaviour

| Breakpoint | Behaviour |
|---|---|
| mobile (<768px) | 元件出現在卡片內的「最後活動:」行，樣式與桌面完全一致；卡片本身承擔佈局責任 |
| tablet / desktop (≥768px) | 元件出現在表格的第 4 欄儲存格內（角色之後、操作之前） |

跨佈局的呈現語彙**完全相同** —— 同一個元件、同一組樣式，只是容器不同（stories AC-4.2）。

### Accessibility

| 面向 | 規格 |
|---|---|
| 鍵盤 | `empty` 態的破折號可聚焦（`tabIndex={0}`），Tab 序遵循該列的視覺順序；`default` 與 `overdue` 態為純文字，不可聚焦 |
| 螢幕閱讀器 | `empty` 態帶 `aria-label="尚無活動紀錄"`；`overdue` 態的 `(!)` 圖示帶文字替代「已超過 90 天未活動」，時間值本身照常朗讀 |
| 焦點可見性 | `empty:focus` 必須有可見的焦點指示，不得僅靠 `outline: none` 後的顏色變化 |
| 色彩 | 逾期的 `amber-300` 為**輔助**訊號；`(!)` 圖示與其文字替代承擔主要語意（NFR-2 的非色彩傳達要求） |

### 與既有「角色」欄破折號的區分（stories AC-2.5）

| 面向 | 最後活動時間欄的 `—` | 角色欄的 `—`（既有，不修改） |
|---|---|---|
| 可聚焦 | ✅ `tabIndex={0}` | ❌ 純文字 |
| 說明文字 | ✅「尚無活動紀錄」 | ❌ 無 |
| `aria-label` | ✅ 有 | ❌ 無 |
| 視覺樣式 | 與角色欄**相同** | — |

依 [Q2] 定案，區分**僅落在可及性層面**，視覺維持一致。這滿足 AC-2.5 的「至少在可及性層面可區分」，且不動既有欄位（那超出本 intent 範圍）。

## 實作約束（承 team-practices 的既有 lint 規則）

這兩項不是設計偏好，是既有工具鏈的硬約束 —— 違反會直接 CI 紅燈：

1. **逾期判定不得在渲染階段執行** —— 「距今超過 90 天」需要當下時間，而在 render 或 `useMemo` 內取用當下時間會觸發既有的渲染純度 lint 規則。`isOverdue` 因此設計為由呼叫端傳入的 prop，判定邏輯放在資料處理階段。這同時讓判定成為可單元測試的純函式（stories 的 DoD 要求）。
2. **資料抓取形狀不得改變** —— 本元件不自行抓取資料；其資料來自既有的使用者清單抓取流程。該流程的形狀受既有 lint 規則約束（抓取與狀態更新必須分離），新增欄位不得改變該形狀。

## 互動流程對應

| user-flow 的步驟 | 本元件的支援 |
|---|---|
| Flow 1 步驟 2「掃讀最後活動時間欄」 | `default`／`overdue` 態的絕對時間格式，可直接目視比對 |
| Flow 1 步驟 3「逾期帳號即讀辨識 → 抄錄時間值」 | `overdue` 態的 `(!)` ＋ 變色提供即讀訊號；時間值為可選取的純文字，支援複製 |
| Flow 1 步驟 4「無紀錄帳號 → 讀取說明」 | `empty:focus`／`empty:hover` 顯示「尚無活動紀錄」 |
| Flow 3 步驟 2「逐卡片掃讀最後活動列」 | 卡片內的同一元件，語彙一致 |

## Assumptions & Open Questions

- [assumption] `isOverdue` 由呼叫端傳入的設計，使元件本身無時間相依性、可被純粹地測試；但這也意味著「當下時間」的取得時機由呼叫端決定（例如每次資料抓取時計算一次），該時機的選擇留給實作
- [assumption] `empty` 態的可聚焦元素在螢幕閱讀器中的朗讀順序未實測；假設它會在該列的角色欄之後、操作欄之前被讀到
- [assumption] （開放問題）逾期圖示的具體實作形式（純文字 `(!)`、SVG 圖示、或圖示字型）未定 —— 線框以 `(!)` 表達是因 ASCII 線框的字元限制，實作可用視覺更佳的圖示，只要保留文字替代

---

## Revision 1（2026-08-11）— PaginationControl

新增元件規格。承 `mockups.md` Revision 1 的五項定案與 `stories.md` US-5 的 AC-5.7、AC-5.9、AC-5.10。

| Field | Value |
|---|---|
| Component | `PaginationControl` |
| Description | 使用者清單的頁碼式分頁控制；本 intent 唯一新增的**可觸發**互動元件 |
| Category | navigation |

### States

| State | Description | Trigger | 呈現 |
|---|---|---|---|
| `default` | 多頁、目前不在邊界 | 總頁數 > 1 且 1 < 目前頁次 < 總頁數 | 上一頁、頁碼序列（目前頁高亮）、下一頁、總筆數，全部可觸發 |
| `first-page` | 位於第 1 頁 | 目前頁次 = 1 | 「上一頁」**停用**（非隱藏），其餘同 `default` |
| `last-page` | 位於最後一頁 | 目前頁次 = 總頁數 | 「下一頁」**停用**（非隱藏），其餘同 `default` |
| `single-page` | 只有一頁 | 總頁數 ≤ 1 | 整組**呈現但停用**（非隱藏）；總筆數照常顯示 |
| `busy` | 切頁中，新資料未到 | 使用者觸發切頁後至回應到達前 | 整組標記忙碌狀態；**控制項不消失**、目前頁次仍可辨識；焦點停留在剛觸發的按鈕 |
| `out-of-range` | 目前頁次超出實際範圍 | 回應的目前頁次 > 總頁數 | 目前頁次照常回顯（不夾頁）；容器內為空清單態，控制項本身仍可用 |

`busy`／`out-of-range` 兩態是 `LastActivityCell` 沒有的 —— 後者由頁面層整塊替換處理（AC-1.9），而本元件**刻意不落在被替換的容器內**，這正是它需要自己的載入態的原因。

### Props / Inputs

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | `number` | yes | — | 目前頁次（1 起算），直接取自回應的分頁資訊 |
| `pageSize` | `number` | yes | — | 每頁筆數，取自回應（非前端常數 —— 後端為真相來源） |
| `total` | `number` | yes | — | 總筆數，取自回應 |
| `isBusy` | `boolean` | yes | — | 是否切頁中。**由呼叫端傳入**，元件不自行判斷 —— 與 `LastActivityCell` 的 `isOverdue` 同一形狀，理由亦同（渲染純度 lint 規則） |
| `onPageChange` | `(page: number) => void` | yes | — | 切頁回呼；元件不自行抓取資料 |

總頁數由 `total` 與 `pageSize` 導出，**不另設 prop** —— 兩份來源會漂移（承 `team.md ## Code Style` 的單一真實來源規則）。

### Responsive Behaviour

| Breakpoint | Behaviour |
|---|---|
| mobile (<768px) | 簡化呈現：省略「上一頁／下一頁」文字標籤只留箭頭、頁碼序列較短、總筆數簡化為「N 筆」。**能力集合不變** |
| tablet / desktop (≥768px) | 完整呈現：含文字標籤、較長的頁碼序列、「共 N 筆」 |

AC-5.7 要求的「一致」是**能力集合與邊界處置**，不是外觀 —— 已核可線框明訂小螢幕「因寬度較窄而簡化呈現」，要求外觀一致會使線框自身不通過該 AC。

### Accessibility

| 面向 | 規格 |
|---|---|
| 鍵盤 | 每個頁碼與前後頁按鈕皆可 Tab 到達並以 Enter／Space **觸發**（WCAG 2.1.1）。標準高於 `LastActivityCell` 的「可聚焦」—— 後者是靜態元素，本元件是互動元素 |
| 目前頁次的語意 | 目前頁碼帶 `aria-current="page"`；**不僅以顏色**表達 —— 具體為**方括號包覆 `[2]`**（沿用已核可線框的表達）＋ `font-extrabold`，顏色為輔助訊號。具體樣式對應見 `design-system-mapping.md` 的「目前頁碼」列（NFR-2、AC-5.9、checklist P-6） |
| 停用態 | 邊界與單頁的停用以 `disabled` 屬性表達，輔助技術可讀出「已停用」，不只是視覺變淡 |
| 忙碌態 | 整組帶忙碌標記（`aria-busy`），輔助技術得知內容更新中；**焦點不被搬移**（AC-5.10） |
| 焦點可見性 | 聚焦時須有可見的焦點指示（checklist O-2／WCAG 2.4.7），不得僅以 `outline: none` 後的顏色變化表達 |
| 觸控目標 | 小螢幕上每個可觸發目標不小於 44x44（checklist **O-9** —— 本輪為分頁控制新增的項目；O-5 是既有三個操作的既有項目，不涵蓋本元件）。小螢幕分頁列是本 feature **最擠的觸控區**，US-4 的 AC-4.3 只綁三個既有操作、文義涵蓋不到本元件 |

### 實作約束（承 team-practices 的既有 lint 規則）

1. **`isBusy` 與總頁數的計算不在渲染階段做不純運算** —— 與 `LastActivityCell` 的 `isOverdue` 同一約束來源。
2. **不自行抓取資料** —— 切頁以 `onPageChange` 回呼交回頁面層，由頁面層沿用既有的抓取／狀態更新拆分（requirements C-6、C-10）。
3. **控制項不得渲染在會被載入／錯誤態整塊替換的容器內** —— 這是 AC-5.10 的結構前提，不是樣式偏好。

## Assumptions & Open Questions（Revision 1 追加）

- [assumption] 頁碼序列過長時的收合規則（顯示幾個頁碼、省略號位置）沿用線框示例（`1 [2] 3 4 ... 9`），具體演算法留實作；它不影響任何一條 AC
- [assumption] `aria-current="page"` 與 `aria-busy` 為本站選定的機制；若 Construction 找到同樣滿足 AC-5.9／AC-5.10 且更貼合既有程式碼的做法，可替換並於該 stage 的 diary 記明理由
