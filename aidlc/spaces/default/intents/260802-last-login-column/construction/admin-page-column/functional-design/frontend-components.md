# Frontend Components — U3 `admin-page-column`

> Stage: functional-design（Construction 3.1）· Unit: `admin-page-column`（kind: **ui**）
> 上游來源：`../../../inception/units-generation/unit-of-work.md`、`unit-of-work-story-map.md`、`../../../inception/requirements-analysis/requirements.md`（下稱 requirements）、`../../../inception/application-design/components.md` C-5／C-6、`component-methods.md` C-5／C-6、`services.md`、`../../../inception/user-stories/stories.md`（下稱 stories）、`../../../inception/refined-mockups/interaction-spec.md`、`mockups.md`、`design-system-mapping.md`、`accessibility-checklist.md`。、`../../../inception/delivery-planning/bolt-plan.md`（B3 DoD —— e2e fixture 策略的定案處）
> 問答定案：Q1=A（在地時區 + 釘住測試環境；**格式依上游**，見問題檔 Revision）、Q2=A（桌面 e2e 回歸涵蓋三項操作）、Q3=A（純 CSS 斷點）。
> 事實查證 S1〜S9 見 `functional-design-questions.md` 的 `## Sources`。

## 元件層級

```
管理頁（既有，內部擴充 — 對應 C-6）
 |
 +-- 表格佈局（既有，新增一欄）        <- 768px 以上顯示
 |    +-- 表頭列：6 欄
 |    +-- 每列
 |         +-- 最後活動時間儲存格（新增 — 對應 C-5）
 |
 +-- 卡片佈局（新增）                  <- 768px 以下顯示
      +-- 每張卡片：6 個欄位逐行
           +-- 最後活動時間儲存格（同一個元件）
```

**兩份標記同時存在於 DOM**，由斷點類別控制顯示（Q3=A）。儲存格元件在兩種佈局中是**同一個**，不是兩套實作 —— 這是 stories AC-4.2「標示語彙跨佈局一致」得以成立的結構基礎。

## 新增元件：最後活動時間儲存格（C-5）

### 屬性設計

| 屬性 | 型別 | 必填 | 允許 undefined |
|---|---|---|---|
| 最後活動時間 | 時間字串（UTC）或**空** | **是** | **否** |
| 逾期旗標 | 布林 | **是** | **否** |

**兩者皆必填、型別不含 undefined** —— 正規化責任在呼叫端（見下方 §資料傳遞的正規化契約），不在元件內。

### 元件不持有狀態

| 面向 | 定案 |
|---|---|
| 內部狀態 | **無** —— 純呈現元件 |
| 逾期判定 | **不自行計算**，旗標由屬性傳入 |
| 當下時刻 | **不讀取** |

**為何不自行計算**：在算繪過程中讀取當下時刻會觸發既有的渲染純度 lint 規則。`interaction-spec.md` 已據此定下「旗標由呼叫端傳入」的形狀；U2 的定案讓這個值有了明確來源 —— 來自 API 回應。

### 狀態與呈現

| 狀態 | 觸發 | 呈現 |
|---|---|---|
| 正常 | 有時間值、旗標為假 | 時間值，一般字色 |
| 逾期 | 有時間值、旗標為真 | **圖示 + 時間值**，警示色，圖示帶文字替代 |
| 無紀錄 | 時間值為空 | **可聚焦**的破折號 |
| 無紀錄 · 聚焦 | 鍵盤或滑鼠聚焦 | 顯示說明文字，並有可見焦點框 |
| 無紀錄 · 懸停 | 滑鼠懸停 | 顯示同一段說明文字 |

**沒有載入態與錯誤態** —— 頁面層整塊替換整個表格（stories AC-1.9），元件在那兩種情況下不會被渲染。

完整色階、圖示樣式、文字替代措辭與焦點框規格見 `interaction-spec.md` 與 `design-system-mapping.md`，**本檔不重述**。

### 不可能出現的組合

**時間為空且旗標為真**：U1 的判定契約保證無紀錄態一律回傳否。**元件不需防禦此組合**。

## 時間的顯示形式

| 面向 | 定案 | 誰定的 |
|---|---|---|
| **格式** | `YYYY-MM-DD HH:MM`（補零、24 小時制） | **上游已定案**（`refined-mockups-questions.md` 前言列為「不重問」） |
| **時區** | **瀏覽器在地時區** | 本站 Q1 |
| 實作形式 | **帶明確選項的格式化**，不是無參數呼叫 | 兩者相加的必然結果 |

### 對齊修正（非本站新定案）

Q1 選項 A 的字面描述是「沿用既有實務（無參數呼叫）」，但依 S1，既有 4 處的無參數呼叫輸出的是 locale 相依格式，**不是**上游定死的格式。

本站沿用的是既有實務的**時區政策**（在地而非固定 UTC），格式依上游。**這是對齊修正，非本站新定案** —— 落差的來源與拆解記於問題檔 Q1 的 Revision 段；上游檔案不回改。

**為何時區是在地**：依 S1，全前端 4 處一致採用瀏覽器在地時區。稽核者看到自己所在時區的時間 —— 對「這個帳號多久沒動了」的判斷正是想要的；固定 UTC 會讓他每次都要心算。

### 測試環境的釘住（配套決定）

依 S3，Playwright config **既未設 `locale` 也未設 `timezoneId`**，因此 e2e 的時間斷言會隨執行環境漂移。**在 config 釘住兩者。**

不確定性的來源是未釘住的測試環境，不是顯示選擇 —— 修在測試層才是修在它真正所在的地方，而不是為了遷就測試而改產品行為。

## 資料傳遞的正規化契約（C-6）

**規則**：從 API 回應取得的兩個欄位，在傳給儲存格元件**之前**必須收斂 —— 時間為「值或空」，旗標為「真或假」，**兩者皆不得為 undefined**。

### 為何型別已由 U5 產生之後仍然必要

產生的型別描述的是**後端已部署之後**的形狀。但：

| 情境 | 後果 |
|---|---|
| 前端先部署、後端後到 | 回應中根本沒有這兩個欄位 |
| 既有資料抓取不做欄位驗證或白名單 | 缺席的欄位直接成為 undefined 流進元件 |

儲存格元件的兩個屬性皆為必填且不含 undefined，**正規化就是這個介面得以成立的前提**。

**這條契約讓「部署順序無硬性約束」的論證真正成立**，而不只是因為執行期碰巧不會爆。

## 型別來源的變更

| 面向 | 變更前 | 變更後 |
|---|---|---|
| 使用者物件型別 | **手寫的本地介面** | **U5 產生的型別** |
| 與後端的連結 | **無** —— `team.md` 已如實記載：抓取結果為 `any` 直接放行，`tsc -b` 對前後端 schema 落差無效 | 建置期會失敗 |

**這是本 intent 中「型別保護」由宣稱變成事實的落點。**

## API 整合點

| 面向 | 定案 |
|---|---|
| 資料來源 | **既有的使用者清單抓取流程**，不新增資料源 |
| 抓取形狀 | **不得改變** —— 既有形狀受 lint 規則約束（抓取與狀態更新必須分離） |
| 新增請求 | **無** —— requirements C-6 的抓取形狀約束因此自動滿足 |

## 佈局切換（Q3=A）

| 面向 | 定案 |
|---|---|
| 斷點 | **768px**（Tailwind `md`），上游已定 |
| 手段 | **響應式類別**：兩份標記都在 DOM，由斷點類別控制顯示 |
| 禁止 | **不得**以 JS 量測視窗寬度決定渲染哪一份 |

### 為何禁止 JS 版斷點

依 S9，`react-hooks/set-state-in-effect` 是 **error 級** lint 規則。JS 版斷點的初始量測必須在 effect 內設定狀態，**直接違反該規則 → CI 紅燈**。依 S7，全前端零 `matchMedia`／`innerWidth`，也沒有先例可沿用。

**這不是風格偏好，是既有工具鏈的硬性約束。**

### 兩份標記並存的可及性處理：由切換機制本身解決

隱藏的那份標記仍在 DOM 中，但**不需要額外管理 `aria-hidden`**。

切換以**基於 `display: none` 的響應式類別**達成（Tailwind 的 `hidden` / `md:hidden` 即為此），而 `display: none` 的子樹**本來就被瀏覽器排除在無障礙樹之外** —— 螢幕閱讀器不會讀到它。

| 後果 | 處置 |
|---|---|
| 螢幕閱讀器讀到重複內容 | **不會發生** —— `display: none` 已排除 |
| 屬性與斷點條件不同步 | **不存在此風險** —— 沒有需要同步的屬性 |

**明確警告**：**不得**改以 JS 動態設定 `aria-hidden` 來達成同一效果。那需要在 effect 內設定狀態，會撞上 Q3 本來就要規避的 error 級 lint 規則（S9）。切換機制與可及性處理必須是**同一個** CSS 機制。

**跨佈局的無障礙屬性一致性**由上游 `accessibility-checklist.md` 的 **R-2** 追蹤（驗證方式：兩種 viewport 各驗一次，標為部分可自動化）。本站不重複定義，也不宣稱它是本站新引入的。

## 表格結構

| 面向 | 定案 |
|---|---|
| 新欄位置 | **角色之後、操作之前** |
| 變更後總欄數 | **6 欄**（依 S5，既有為 5 欄：使用者／授權狀態／角色／操作／啟用） |
| 斷點以下 | 卡片佈局，每張逐行呈現 6 個欄位 |

## 既有行為不得退化（NFR-7）

| 既有行為 | 約束 |
|---|---|
| 角色調整、啟停用、授權操作 | 桌面與小螢幕皆維持可用，行為一致 |
| 載入態與錯誤態 | **沿用既有整塊替換模式**，不做骨架（stories AC-1.9） |
| 既有角色欄的空值呈現 | **不動**（stories AC-2.5：新欄位僅以可及性手段與它區分） |
| 資料抓取形狀 | **不得改變** |
| 觸控目標 | 小螢幕卡片佈局下不小於 44×44（stories AC-4.3） |

### 桌面回歸的驗收落點（Q2=A，本站補上的缺口）

requirements NFR-7 點名三項操作，但 stories AC-4.3 的 Given **只限定小螢幕** —— 桌面回歸原本無 AC 落點。此缺口自 refined-mockups 起追蹤，已標明由本單元承接。

**本站定案**：新增桌面 e2e 回歸涵蓋三項操作。依 S4，既有 e2e 只有一支檔案、6 個 case、**無一導覽至 Admin 頁**；本單元本來就要寫 repo 第一個 Admin 頁 e2e（team-practices 規則 C），把三項操作一併涵蓋是在同一支檔案多寫幾個 case，不是新建機制。

## 不引入的東西

| 事項 | 為何 |
|---|---|
| 等寬字體 | `design-system-mapping.md` 明確排除 —— 新的排版語彙，且既定字級下既有字體的數字已足夠對齊掃讀 |
| i18n 函式庫、日期函式庫 | 依 S2，repo 零此類依賴；AD-5 不新增外部依賴（C-8 是唯一具名例外） |
| 骨架載入態 | stories AC-1.9 已定案沿用既有整塊替換 |
| 元件內部狀態 | 純呈現元件，無狀態 |

## 不屬於本單元的事

| 事項 | 歸屬 |
|---|---|
| 逾期判定門檻與邏輯 | U1（C-1） |
| 兩個欄位出現在 API 回應中 | U2（C-4） |
| 型別的產生機制 | U5（C-8） |
| 誰進得了管理頁 | U4（C-7）與既有端點層權限檢查 |
| 五種狀態的色階、圖示、可及性屬性細節 | refined-mockups 已定死，本單元依規格實作 |

---

## Revision 1（2026-08-11）— 分頁（C-9 前端半）

承 units-generation Revision 1（C-9 前端併入本單元）、application-design 的 AD-10／AD-12、refined-mockups Revision 1 的定案 5〜9 與 `PaginationControl` 規格。

### 新增元件：分頁控制（C-9 前端）

規格的單一來源是 `refined-mockups/interaction-spec.md` 的 `PaginationControl`（六個狀態、五個 props、無障礙義務），**此處不重述以免兩份漂移**。本節只補實作層的三個約束：

| 約束 | 內容 | 若違反 |
|---|---|---|
| **渲染位置在表格／卡片容器之外** | 既有的 `isLoading`／`error` 三元式會把**整個容器內容**替換成單一訊息；控制項若在容器內，切頁時會連同表格一起消失、鍵盤焦點退回頁面主體 | AC-5.10 直接失敗，且 WCAG 2.4.3 |
| **不自行抓取、不自行判斷忙碌** | 兩者皆由呼叫端傳入（與最後活動時間儲存格的逾期旗標同一形狀，理由亦同：渲染純度 lint 規則） | CI 紅燈 |
| **總頁數為導出值** | 由 `total` 與 `pageSize` 計算，不另設 prop、不另存 state | 兩份來源會漂移 |

### 三種抓取路徑對應三種畫面行為，互不共用旗標

這是本單元 Revision 1 最容易做錯的一件事。既有程式碼只有**一個** `isLoading`，而現在需要三種不同的畫面行為：

| 路徑 | 觸發 | 畫面行為 | 旗標 |
|---|---|---|---|
| **初次載入** | 進入頁面 | 既有的整塊替換（容器內「載入中…」，分頁控制尚未存在） | 既有 `isLoading` |
| **切換頁次** | 使用者點分頁控制 | 容器內「載入中…」，**分頁控制留在畫面上**並標記忙碌 | **新設** `isBusy` |
| **刪除後的背景重抓** | 就地移除後的重新同步 | **完全不進入任何載入態** —— 就地移除已給了立即回饋；回應抵達時靜默替換 | **無旗標** |

**第三列是最容易做錯的**：手上最順手的既有工具是 `fetchUsers()`，它會先 `setIsLoading(true)` —— 照那樣實作，每刪一列整張表就閃一次載入畫面，字面上仍通過「頁次不變、該列已移除」，實際卻打斷逐帳號查驗的節奏。**刪除後的重抓不得沿用 `fetchUsers()`。**

**背景重抓失敗時**：保留就地移除後的畫面（使用者看到的仍是正確結果），以既有 toast 提示同步失敗，**不回滾、不跳錯誤畫面**。

### 三處現行的整份重抓皆須改

| 位置 | 現行行為 | 改為 |
|---|---|---|
| 啟停用成功（`AdminPage.tsx:113`） | `fetchUsers()` 整份重抓 | **就地更新該列**，不重抓 |
| 刪除成功（`:129`） | `fetchUsers()` 整份重抓 | **就地移除該列 ＋ `total` 本地遞減 → 背景重抓當前頁**（見上） |
| 角色調整失敗（`:91-94` 的 `catch`） | `fetchUsers()` 整份重抓 | **不重抓** —— 失敗不得把使用者彈回第 1 頁 |

角色調整**成功**路徑（`:89`）已是就地更新，不需改動。

**漏改任一處，該路徑就會把頁次拉回第 1 頁**，而其餘路徑正確 —— 這種部分正確最難在人工測試中發現，e2e 需對停用與刪除各斷言一次「頁次不變」。

### 逾期旗標的正規化必須收斂在抓取函式內

切頁會是純抓取函式的**第三個**呼叫點（既有兩個：初次載入的 effect、使用者主動重新整理）。正規化若寫在呼叫端而非抓取函式內，**新增的切頁路徑很可能忘記套用**，使該頁整頁不帶逾期標示 —— 而該頁的每一列看起來都「正常」。

### 併發保護

快速連續刪除會發出多個重疊的背景重抓。既有的 `cancelled` flag 只防「元件卸載後 setState」，**不防**「兩個重疊請求以非發出順序返回」—— 較舊的回應在較新的之後抵達會覆寫 state，讓剛被刪除的列短暫重新出現。

**只有「最後發出」的重抓回應能寫入 state**：遞增請求序號（回應抵達時比對是否仍為最新）或 `AbortController`（發出新請求前中止前一個），擇一。

### 資料傳遞的變更

抓取函式的回傳值由 `DbUser[]` 變為整個 envelope（**不在函式內拆解**，維持既有的三層拆分形狀）。呼叫端把 `items` 放進既有的 `users` state，把 `total`／`page`／`page_size` 供給分頁控制。

**型別來源**：envelope 的型別**採用產生的型別**（`UserListPage`），與既有的使用者物件型別同一來源，不手寫。這是 requirements C-9 明文要求的一環 —— 現行 `res.json()` 回 `any` 並宣告為陣列，envelope 一到就會把非陣列塞進清單 state 而 `tsc -b` 完全無感。

### 空清單態（第六態）

`items` 為空時（超出範圍的頁次，或該頁的最後一列被刪除）：容器內顯示置中訊息與「回到第 1 頁」，**分頁控制照常呈現於容器外**。沿用既有「容器內單一置中訊息」的版式語彙，替換的是容器內容、不是控制項。

### 不屬於本單元的事（Revision 1 追加）

- 分頁查詢與 envelope 的**產生**（屬 U2）
- `UserListPage` 型別的**產生**（屬 U5）
- 每頁筆數的**決定**（已由 application-design 定案為 20，本單元只消費回應中的值、不寫死前端常數）

---

## Review — Revision 1

> **修正紀錄（2026-08-11，iteration 1 的 4 Major ＋ 3 Minor 全數處理）**
>
> - **Major 1**（U2 的 `business-logic-model.md` 未隨 Revision 1 更新、與同單元兩份 artifact 自相矛盾）：該檔補上 Revision 1 段 —— 本單元做什麼、觸發點、驗證強度表三處皆納入 envelope 與分頁查詢，並明記「仍然零資料庫變更」。
> - **Major 2**（Q1 拒絕共用工廠，實作卻用了工廠）：**實作保留工廠**，理由記入 U2 的 `business-logic-model.md`：application-design 的 C-4 明文把工廠列為兩個合法手段之一（「不得設可靜默通過的預設值，**或**改以單一共用工廠」），而 Q1 是在更早、資訊較少的時點選了另一個；且 Q1 駁回的具體代價（被迫處理範圍外的 `requested_role` 缺陷）在實作中未發生。實際採用**兩者兼具**：欄位無預設值 ＋ 共用工廠。不回改 Q1 的問答紀錄。
> - **Major 3**（正規化契約未落地）：**已在程式碼實作** —— `AdminPage.tsx` 的 `applyPage` 對 `items`／`total`／`page`／`page_size` 與每列的兩個新欄位收斂（`?? null`／`?? false`／`?? 0`），啟停用的回應落地點同樣收斂。理由寫進註解：產生的型別是**編譯期**保證，而 `res.json()` 是執行期的 `any`，型別只是斷言。
> - **Major 4**（e2e fixture 策略未在本單元文件出現）：`business-logic-model.md` 補上「e2e fixture 策略」段，明記採用選項 (a)、實測成本與涵蓋到的 AC。
> - **Minor 5**（44x44 誤併入「定案 5〜9」）：兩個單元的問題檔皆更正為 `interaction-spec.md` 的 O-9。
> - **Minor 6**（AC-5.11 人工驗證義務未承認）：`business-logic-model.md` 補上該義務與具體檢查方式。
> - **Minor 7**（驗證強度表未涵蓋 Revision 1 新增行為）：補上十列，其中焦點行為、併發保護、背景重抓不進載入態三項**誠實標記為無自動化驗證**。
>
> 以下 Review 內文保留原判定時的觀察，不回改。

**Verdict:** NOT-READY（已修正，見上方修正紀錄）
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-11T02:03:02Z
**Iteration:** 1

**審查範圍**：`admin-page-column`（`frontend-components.md`／`business-logic-model.md`／`functional-design-questions.md`）與 `user-object-serialization`（`business-rules.md`／`domain-entities.md`／`functional-design-questions.md`）兩單元的 Revision 1（2026-08-11，PU-6 分頁）新增內容；pre-Revision-1 內容僅在與 Revision 1 牴觸時觸及。逐字核對的上游：`decisions.md` AD-10／AD-11／AD-12（含「與載入狀態機的關係」「併發保護」兩段）、`components.md`／`component-methods.md` C-9 與 C-4／C-6 Revision 1、`unit-of-work.md` Revision 1（含 U2／U3「實作注意」）、`stories.md` US-5 十一條 AC、`interaction-spec.md` 的 `PaginationControl`、`requirements.md` FR-6.x／NFR-8〜10。額外核對：`backend/services/user_router.py`、`frontend/src/pages/AdminPage.tsx`、`frontend/src/components/LastActivityCell.tsx`、`frontend/src/types/api.d.ts`、`frontend/tsconfig.app.json`——**這些檔案在目前分支（`danniel/feat/last-activity-column-and-pagination`）的工作目錄中已有大量未提交變更**（`git diff --stat` 顯示 `user_router.py` +76/-28、`AdminPage.tsx` +246/-123，另有全新的 `LastActivityCell.tsx`／`PaginationControl.tsx`／`frontend/src/types/`／`backend/tests/test_user_list_endpoint.py`），等於本輪設計已有一份幾近完成的實作可供逐字核對，比純書面推演更能驗證「設計說的話，程式碼真的做得到嗎」。

### 事實查證

| # | 查證 | 結果 |
|---|---|---|
| 1 | AD-10／AD-11 的 Decision＋Consequences 逐項是否命中 `business-rules.md` BR-P1〜P4 | **命中**：envelope 四欄無預設值、offset 查詢保留 `ORDER BY id`、頁次語意（回顯不夾頁）、框架原生範圍約束、422 不含帳號資料，逐條對應 |
| 2 | AD-12「與載入狀態機的關係」（三路徑三行為互不共用旗標、禁沿用 `fetchUsers()`）與「併發保護」兩段是否命中 `frontend-components.md` | **命中**：兩段的每一句實質內容（含背景重抓失敗處置、序號／`AbortController` 擇一）皆在「三種抓取路徑對應三種畫面行為」「併發保護」兩節逐字對應，且是本輪唯一一處把上游 Minor 5（「背景重抓失敗未傳到 U3 實作注意」）確實落地的地方 |
| 3 | `unit-of-work.md` U2／U3「實作注意（Revision 1 追加）」共 10 條是否逐條命中兩單元的 Revision 1 內容 | **全數命中**（U2 四條見 `business-rules.md` BR-P1〜P4；U3 六條見 `frontend-components.md` 對應章節），無遺漏 |
| 4 | `AdminPage.tsx:89`／`:91-94`／`:113`／`:129` 四處行號引用 | **逐字精確**：`:89` 為角色調整成功的 `setUsers` 就地更新；`:91-94` 恰為 `catch { showToast(...); fetchUsers(); }` 四行；`:113`／`:129` 恰為啟停用／刪除成功路徑的 `fetchUsers()` 呼叫。四處引用無一偏移 |
| 5 | 「無新問題」清單引用的 AD-10／AD-11（該站問題檔 Q8〜Q10）、AD-12、units-generation Q4 是否存在 | **存在**：`application-design-questions.md` Q8／Q9／Q10、`units-generation-questions.md` Q4 逐字核對皆命中所述主題 |
| 6 | 「無新問題」清單將「44x44」歸入「refined-mockups Revision 1 的定案 5〜9」 | **不成立**：`mockups.md` 定案 5〜9（版位／單頁／邊界按鈕／空清單態／切頁進行中）逐項核對，沒有一項是觸控目標尺寸；44x44 的實際定案處是 `interaction-spec.md` Accessibility 表的 **O-9**（見 Finding 5） |
| 7 | 【對真實程式碼】`business-rules.md` Q1「不採共用工廠函式」及 Revision 1「與既有三個構造點的關係」段落所稱「三個構造點…手寫具名引數」現況描述 | **與程式碼不符**：`user_router.py` 工作目錄版本已把三個構造點全部改為呼叫單一共用工廠 `_to_user_schema()`——正是 Q1 明文駁回的「選項二」（見 Finding 2） |
| 8 | 【對真實程式碼】`frontend-components.md`「資料傳遞的正規化契約（C-6）」（Revision 1「逾期旗標的正規化必須收斂在抓取函式內」延伸適用於分頁路徑）是否落地 | **未落地**：`AdminPage.tsx` 的 `applyPage`（`setUsers(data.items)`）與 `<LastActivityCell lastActivityAt={u.last_activity_at} isOverdue={u.is_overdue} />` 之間沒有任何 `?? null`／`?? false` 收斂（見 Finding 3） |
| 9 | 【對真實程式碼】`PaginationControl` 渲染位置是否在容器外（AD-12／AC-5.10 的結構前提） | **相符**：`AdminPage.tsx` 的容器 `<div>` 在第 377 行閉合，`<PaginationControl>` 於第 382 行、容器外渲染 |
| 10 | 【對真實程式碼】三處整份重抓（`:113`／`:129`／`:91-94`）是否已依 AD-12／FR-6.5 改為就地更新或背景重抓 | **相符**：`handleToggleActive`／`handleRoleChange` 成功路徑改為 `setUsers` 就地更新且移除 `fetchUsers()`；`handleDelete` 改為就地移除＋`total`本地遞減＋`resyncCurrentPageInBackground`；角色調整失敗的 `catch` 已不再呼叫任何重抓 |
| 11 | `user-object-serialization/business-logic-model.md` 是否隨 Revision 1 更新 | **未更新**：全檔零 `Revision 1`／`分頁`／`C-9`／`envelope`／`UserListPage` 命中，「本單元做什麼」「觸發點」「主流程」仍描述舊範圍（見 Finding 1） |
| 12 | AC-5.11「介面不存在」子句（`unit-of-work.md` AC 對照表指派 U3、人工驗證）是否於 `admin-page-column` 兩份 Revision 1 文件中被承接 | **未承接**：兩份文件全文對「排序」「篩選」「sort」「filter」零命中（見 Finding 6） |

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Major | `user-object-serialization/functional-design/business-logic-model.md`（全檔，Revision 1 缺席） | **U2 的 `business-logic-model.md` 完全未隨 Revision 1 更新，與同單元 Revision 1 已核可的 `business-rules.md`／`domain-entities.md` 產生自我矛盾。** `business-rules.md` Revision 1 明文宣告「envelope 是本單元的第四個回應構造點」、`unit-of-work.md` 記載 U2「複雜度 M → L」，但 `business-logic-model.md` 的「本單元做什麼」（「三個構造點各加兩個欄位…零資料庫變更」）、「觸發點」（「三個回傳使用者物件的 API 端點」）與「本單元的驗證強度」表隻字未提第四個構造點、分頁查詢邏輯或 422 路徑——同一單元的兩份必要產出（`produces_kinds` 對 `service` kind 同時要求 `business-logic-model.md` 與 `business-rules.md`／`domain-entities.md`）對「這個單元現在做什麼」給出不一致的答案。此檔既有的「主流程」ASCII 圖（序列化流程）已為 pre-revision 內容立下先例，本應有對應的分頁查詢流程圖（驗參數→計數查詢→offset/limit 查詢→組 envelope→422 分支），但完全缺席 | 為 `business-logic-model.md` 補一個 `## Revision 1` 區塊：更新「本單元做什麼」／「觸發點」以納入 envelope 構造點，新增分頁查詢的主流程圖，並擴充「本單元的驗證強度」表以涵蓋 BR-P1〜P5 各自的可測性 |
| 2 | Major | `user-object-serialization/functional-design/business-rules.md`「Q1 如何保證三個構造點都帶出兩個新欄位」；同檔 Revision 1「與既有三個構造點的關係」段 | **已核可的 Q1 決定（拒絕共用工廠函式）及其 Revision 1 延伸主張，已被真實程式碼推翻。** `backend/services/user_router.py`（工作目錄，`danniel/feat/last-activity-column-and-pagination` 分支未提交變更）已新增 `_to_user_schema()` 單一共用工廠，並讓清單、啟停用、角色調整三個端點**全部**改呼叫它——這正是 Q1 明文比較後駁回的「選項二」。駁回的具體理由（工廠會被迫決定要不要補上範圍外的 `requested_role` 漏傳缺陷、需要「繞道」）在實際實作中並未發生：兩個 PUT 端點呼叫工廠時單純不傳 `requested_role`，沿用函式簽章 `Optional[str] = None` 的預設值，與駁回前的行為完全相同，看不出所稱的「繞道」或「異味」。Revision 1 新增的「與既有三個構造點的關係」段落更進一步，把「三個構造點…手寫具名引數」當作既有事實去類比 envelope 這個第四個構造點，而這個「既有事實」現在是錯的。這不影響 R1 本身的保護力（必填宣告在任何呼叫路徑下都一樣拋錯），但意味著文件對「為何選擇一」的論證基礎已不成立，若有人依文件字面把工廠函式拆回三處手寫，是在做無意義的重工 | 回頭核實 Q1：若共用工廠函式在實測後確認可行且無需碰觸範圍外缺陷，誠實更正 Q1 的論證（依 `project.md` 的「只修理由不改決定」或视實際情況改判定），並同步修正「與既有三個構造點的關係」對現況的描述 |
| 3 | Major | `frontend-components.md`「資料傳遞的正規化契約（C-6）」；Revision 1「逾期旗標的正規化必須收斂在抓取函式內」 | **正規化契約在真實程式碼中完全未落地。** 兩處文字都把「兩個欄位在傳給儲存格元件之前必須收斂為值或空／真或假，不得為 undefined」當作硬性規則（Revision 1 並將其延伸適用到新的 `applyPage`／切頁路徑）。但 `frontend/src/pages/AdminPage.tsx` 的 `applyPage`（`setUsers(data.items)`）與渲染呼叫點（`<LastActivityCell lastActivityAt={u.last_activity_at} isOverdue={u.is_overdue} />`）之間沒有任何 `?? null`／`?? false` 之類的收斂邏輯——資料直接從回應流到元件 props。由於本 Bolt 的前後端已同批未提交、同批部署（`bolt-plan.md`：「U2 不得單獨部署」），目前這條路徑在「正常」情境下不會被觀察到故障；但文件自己把這條規則描述為「讓部署順序無硬性約束的論證真正成立」的必要前提——這個論證目前的前提並不成立，一旦未來真的出現前後端版本錯位（文件設想的正是這個情境），程式碼沒有任何防線 | 於 `applyPage`（或抓取函式內）補上正規化步驟（如 `items: data.items.map(u => ({ ...u, last_activity_at: u.last_activity_at ?? null, is_overdue: u.is_overdue ?? false }))`），使文件與程式碼一致；或者，若團隊判定「同批部署」已使正規化非必要，應在文件中誠實降級此規則的必要性與理由，而非維持一條聽起來是硬性約束、實際未被遵守的規則 |
| 4 | Major | `frontend-components.md`／`business-logic-model.md`（admin-page-column，Revision 1 全段缺席）；`functional-design-questions.md`「無新問題」清單 | **US-5 DoD 明文要求「不得默認略過」的 e2e fixture 策略（AC-5.3／AC-5.6／AC-5.7 如何在測試中湊出超過一頁的帳號），在 admin-page-column 的兩份 Revision 1 文件中完全沒有出現，也未被列為上游來源。** `stories.md`（已是兩份文件列名的上游來源）US-5 DoD 明文要求「交付規劃前須擇一並記錄：(a) 於 e2e 內以註冊建立超過一頁的帳號數…(b) 若成本不可接受，記為已評估的成本取捨並指派人工驗證。**不得默認略過**」。`bolt-plan.md`（B3 DoD）已選定 (a)，`frontend/tests/e2e/regression.spec.ts`（工作目錄）也已據此實作——但這個決定的落點是 `bolt-plan.md`（delivery-planning 的產出），兩份 admin-page-column 的 Revision 1 文件的「上游來源」清單完全沒有列出它，文件本身也對 fixture 策略隻字未提。若只讀這兩份「Construction 階段最後一份設計文件」，找不到這個「不得默認略過」的決定該去哪裡查 | 在 `frontend-components.md` 的 Revision 1（或「本站定案」表）補一句：e2e 以公開註冊端點造超過一頁帳號（承 `stories.md` DoD、`bolt-plan.md` B3 DoD），並把 `bolt-plan.md` 補進文件頭的上游來源清單 |
| 5 | Minor | `functional-design-questions.md`（admin-page-column／user-object-serialization 皆同）「無新問題」清單 | 「分頁控制的版位、單頁與邊界處置、空清單態、**44x44** —— refined-mockups Revision 1 的定案 5〜9」一句把 44x44 併入「定案 5〜9」的引用範圍，但逐條核對 `mockups.md` 的定案 5（版位）／6（單頁）／7（邊界按鈕）／8（空清單態）／9（切頁進行中）後，沒有一項與觸控目標尺寸相關；44x44 的實際定案處是 `interaction-spec.md` Accessibility 表的 O-9 項（該文件自己的 reviewer 才剛把前一版誤引的 O-5 更正為 O-9，見 `mockups.md` Review — Revision 1 Finding 5）。決定本身存在且正確，只是引用位置不精確，與本專案「掛引用前必須逐字核對」的既有紀律不符 | 把該句改為「…空清單態 —— refined-mockups Revision 1 的定案 5〜8；44x44 —— `interaction-spec.md` Accessibility 表 O-9」 |
| 6 | Minor | `frontend-components.md`／`business-logic-model.md`（admin-page-column，Revision 1 全段缺席） | AC-5.11 的「介面不存在」子句（系統中不存在依最後活動時間排序或篩選清單的使用者介面）由 `unit-of-work.md` 的 AC 對照表（「AC-5.11…U3（介面不存在子句，人工）」）與 `stories.md` DoD 指派給本單元做人工驗證，但 admin-page-column 兩份 Revision 1 文件全文對「排序」「篩選」「sort」「filter」零命中，未在「本單元的驗證強度」「不屬於本單元的事」等任何一處承認自己擁有這項人工驗證義務 | 在 `frontend-components.md` 或 `business-logic-model.md` 補一條：AC-5.11 的介面不存在子句由本單元人工驗證（靜態檢查：程式碼中不存在排序／篩選 UI） |
| 7 | Minor | `business-logic-model.md`（admin-page-column）Revision 1「分頁狀態的邏輯模型」與「決策表」 | Revision 1 新增了狀態表與決策表，但未同步擴充 pre-revision 既有的「本單元的驗證強度（分項評估）」表以涵蓋新增的 U3 承載 AC。併發保護（`AbortController`／請求序號）邏輯本身，核對 US-5 十一條 AC 與其 DoD 指派表後，找不到任何一條要求對它寫測試或人工驗證——它是一條「只能靠讀 code 確認有沒有做對」的規則，卻沒有像 pre-revision 表格對觸控尺寸／對比度那樣被誠實標記為「無自動化驗證」 | 擴充「本單元的驗證強度」表，為併發保護、`isBusy` 正確渲染等 Revision 1 新增行為補上誠實的驗證強度標註（多數應標為「無自動化驗證，靠讀 code／人工」） |

### 實作者仍需臆測之處（Hunt #1）

逐一走過 US-5 十一條 AC 後，多數 AC 都有清楚的規則、狀態表或決策表可直接落地實作（AC-5.1／5.2／5.4／5.5／5.8 由 `business-rules.md` BR-P1〜P4 與 U1 的既有契約覆蓋；AC-5.6／5.9／5.10 由 `frontend-components.md`／`business-logic-model.md` 的決策表與 `interaction-spec.md` 覆蓋）。找到的具體缺口如下：

1. **`fetchUsers()` 三處呼叫點全部移除後，函式本身是否該保留，兩份文件皆未言明。** `frontend-components.md`／`business-logic-model.md` 沿用「fetchUserList 既有兩個呼叫點：初次載入的 effect、使用者主動重新整理（即 `fetchUsers`）」的說法（承自 `component-methods.md`），但實測 `AdminPage.tsx` 目前 `fetchUsers()` 的**僅有**三個呼叫點正是 AD-12／AC-5.6 要求移除整份重抓的三處（`:91-94`／`:113`／`:129`），且沒有任何獨立的「手動重新整理」按鈕。三處都改掉後，`fetchUsers` 會變成零呼叫者的死碼；`frontend/tsconfig.app.json` 已啟用 `noUnusedLocals: true`，若逐字實作 Revision 1 的所有變更卻不同時刪除該函式，`tsc -b`（CI 的 frontend gate 之一）會直接紅燈。**這正是本 hunt 要找的「必須猜」的地方**——且證據顯示它確實需要猜：真實工作目錄的程式碼已經把 `fetchUsers`／`fetchUserList` 整組改寫為 `fetchUserPage`／`applyPage`／`handlePageChange`／`resyncCurrentPageInBackground`，正確地不留下死碼，但兩份設計文件從未指示這個清理動作，也從未指出舊有的「兩個呼叫點」說法在完成 Revision 1 後將不再成立。
2. **e2e fixture 策略**（見 Finding 4）——只讀 admin-page-column 的兩份文件，找不到 AC-5.3／5.6／5.7 要如何在 e2e 湊出超過一頁帳號的答案；答案存在於未被列為上游來源的 `bolt-plan.md`。
3. **前端正規化的實際收斂點**（見 Finding 3）——文件說「必須收斂」，但沒有給出程式碼形狀（是在 `applyPage` 內 `.map()`，還是在渲染呼叫點各自 `?? null`？），而目前的實作選擇了「兩處都不做」。
4. **AC-5.11 介面不存在子句的驗證方式**（見 Finding 6）——文件未承認擁有這項義務，實作者若沒有另外查 `unit-of-work.md` 的 AC 對照表，不會知道自己該對這件事做點什麼（即便答案只是「維持現狀、不加排序 UI」）。

除以上四點外，未發現其他必須臆測才能動筆的缺口——`interaction-spec.md` 的單一來源原則被兩個單元一致遵守（不重複定義 `PaginationControl` 的狀態與 props），且與真實程式碼逐項核對後，狀態機、就地更新／背景重抓、容器外渲染三項結構性要求都已被正確實作，證明文件在這三個面向的說明是足夠的。

### Summary

四項 Major 發現分兩類：**文件內部一致性**（U2 的 `business-logic-model.md` 未隨 Revision 1 更新而與同單元的 `business-rules.md` 自相矛盾；e2e fixture 決定存在卻未被兩份 Construction 文件承接）與**文件對真實程式碼的失真**（Q1 拒絕共用工廠函式的論證已被工作目錄中的實作推翻；C-6 的正規化契約在程式碼中完全未落地）。後一類發現的可信度較高，因為本次審查難得地能拿已幾近完成、尚未提交的真實實作（`user_router.py`／`AdminPage.tsx`／`LastActivityCell.tsx`／`PaginationControl.tsx`）逐字核對設計主張——多數結構性要求（狀態機分離、容器外渲染、就地更新取代整份重抓、`ORDER BY id` 保留）都通過了核對，證明本輪分頁設計整體站得住腳；但兩處具體規則（共用工廠函式的可行性判斷、前端正規化）已被證明與現況不符，且「`fetchUsers` 死碼」這類文件從未言明、卻已在真實實作中被正確處理的落差，證實了 Hunt #1 的方法論——這正是「文件對，但沒寫全」會讓開發者必須自行填空的具體案例。3 個 Major 落在文件品質與可追溯性（不影響已核可的分頁行為本身是否正確），1 個 Major（正規化）留有實際的執行期風險敞口。依裁決規則（0 Critical、>2 Major 即擋 READY），本輪判定為 NOT-READY；建議依上述 Finding 1〜4 修正後，因缺口性質為文件補強而非架構重定，預期一輪修正即可轉為 READY。

---

## Review — Revision 1（Iteration 2 驗證輪）

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-11T02:18:34Z
**Iteration:** 2

> 本輪不採信檔案中段的「修正紀錄」自陳區塊，逐項回頭核對上游文件與真實程式碼。查核範圍：`user-object-serialization/functional-design/business-logic-model.md`、同單元 `business-rules.md`；`admin-page-column/functional-design/business-logic-model.md`、本檔（`frontend-components.md`）；兩單元的 `functional-design-questions.md`；`inception/application-design/components.md` C-4；真實程式碼 `backend/services/user_router.py`、`frontend/src/pages/AdminPage.tsx`、`frontend/src/types/api.d.ts`；測試 `backend/tests/test_user_list_endpoint.py`、`frontend/tests/e2e/regression.spec.ts`。

### 逐項驗證（iteration 1 的 4 Major ＋ 3 Minor）

| # | 原 Finding | 判定 | 查核依據 |
|---|---|---|---|
| Major 1 | U2 的 `business-logic-model.md` 未隨 Revision 1 更新，與同單元 `business-rules.md` 自相矛盾 | **部分達成** | 該檔已補上 `## Revision 1（2026-08-11）— 分頁（C-9 後端半）` 區塊（L218-263）：「本單元做什麼」已納入第四個構造點 envelope（L224-235）、「觸發點」已更新（L237-239）、驗證強度表已擴充（L241-251），逐條核對 `business-rules.md` L101-128 的 BR-P1〜P5，五條全數對應到位。自相矛盾已消除。**未達成**部分：iteration 1 建議中「新增分頁查詢的主流程圖」未落地——新增的 Revision 1 區塊全為表格，零 ASCII fenced code block，與原檔既有「主流程」ASCII 圖（L18-50）的體例不對稱，屬完整性殘餘，不影響矛盾本身已解決 |
| Major 2 | Q1 拒絕共用工廠函式，實作卻用了工廠 | **達成**（附帶一項新發現 N1，見下） | 見「Major 2 特別查核」 |
| Major 3 | C-6 正規化契約未落地 | **達成** | 見「Major 3 特別查核」 |
| Major 4 | e2e fixture 策略未在本單元文件出現 | **部分達成** | `admin-page-column/business-logic-model.md` 新增「e2e fixture 策略（reviewer Revision 1 Finding 4）」節（L187-198），記載選項 (a)、可行性依據、成本實測（bcrypt 0.305s／次 ×21≈6.4s）、涵蓋到的 AC，並顯式引用 `bolt-plan.md` B3 DoD。核對 `regression.spec.ts` L127-154 確認測試確實以 21 帳號 fixture 實作，與文件描述一致。**未達成**部分：建議的第二半「把 `bolt-plan.md` 補進文件頭的上游來源清單」未落地——`business-logic-model.md`（L4）與 `frontend-components.md`（L4）的「上游來源」清單皆未列 `../../../inception/delivery-planning/bolt-plan.md`（該檔確實存在），僅內文提及 |
| Minor 5 | 44x44 誤併入「定案 5〜9」 | **達成** | 兩單元 `functional-design-questions.md` 皆已改為「…定案 5〜9；44x44 觸控目標的定案處是 `interaction-spec.md` 的 Accessibility 表 O-9（不在定案 5〜9 之內；reviewer Revision 1 Finding 5 更正）」，兩檔逐字相同，與建議一致 |
| Minor 6 | AC-5.11 人工驗證義務未承認 | **達成** | `business-logic-model.md` 新增「AC-5.11 的人工驗證義務」節（L200-204）並給出具體靜態檢查方式。核對 `unit-of-work.md` L363「AC-5.11 \| U2（契約子句…）＋ U3（介面不存在子句，人工）」，引用逐字相符 |
| Minor 7 | 驗證強度表未涵蓋 Revision 1 新增行為 | **部分達成** | 新增驗證強度表（L206-223）十列，誠實標示切頁期間控制項不消失（弱）、焦點不離開分頁控制（無）、併發保護（無）、背景重抓不進載入態（無）。核對 `regression.spec.ts` 全檔 166 行：確認這四項確實零自動化覆蓋，屬實。但「無障礙的四項」一列的❌判定為整體性 under-claim，見新發現 N3 |

### Major 2 特別查核（C-4 引用逐字性 ＋ 決定本身是否成立）

1. **引用逐字性**：`inception/application-design/components.md` L143 原文為「因此本元件的設計約束是：兩個新欄位在回應模型上**不得設置可靜默通過的預設值**，或改以**單一的共用工廠函式**（接受使用者物件與當下時刻）使三個構造點不可能分歧。」`business-logic-model.md` L259 的引用「兩個新欄位在回應模型上**不得設置可靜默通過的預設值**，**或**改以**單一的共用工廠函式**使三個構造點不可能分歧」**遺漏了「（接受使用者物件與當下時刻）」這個括號子句**，卻標榜「逐字」。這是本 intent 第二次被查出「逐字」引用實際有出入。與上一次不同：這次遺漏的子句不改變引用支撐的論點本身——C-4 確實把「共用工廠函式」列為與「不設預設值」並列的合法手段，此核心主張成立，被省略的只是工廠簽章的描述細節。記為新 Minor（N1），不影響 Major 2 判定，但值得團隊注意這個反覆出現的模式。
2. **決定本身是否站得住腳（對真實程式碼）**：`backend/services/user_router.py` L461-479 的 `_to_user_schema()` 工廠簽章確為 `(user: User, now: datetime, requested_role: Optional[str] = None)`；三個構造點（L519 清單、L663 啟停用、L759 角色調整）皆呼叫它；兩個 PUT 端點呼叫時確實**未傳** `requested_role`、沿用預設值 `None`，與文件所述「不需要任何『繞道』」逐字相符。清單端點的條件式查詢（L514-518，僅 `authorization_status == "pending"` 時查）留在呼叫端、工廠本身不處理，印證「工廠簽章不需繞道」的判斷成立。**結論：Major 2 的判斷（保留工廠、依據 C-4 已允許）達成，程式碼與文件一致。**

### Major 3 特別查核（`applyPage` 與所有寫入 `users` state 的路徑）

逐一列舉 `AdminPage.tsx` 全部四個 `setUsers` 呼叫點：

| 呼叫點 | 資料來源 | 是否含新兩欄 | 收斂狀態 |
|---|---|---|---|
| L73-84 `applyPage`（三個呼叫點共用：初次載入 L92、切頁 L109、背景重抓 L119） | API 回應 `data.items` | 是 | **已收斂**（`?? null` L77、`?? false` L78） |
| L135 `handleRoleChange` 成功路徑 | 展開既有 `u`，只覆寫 `role` | 否 | 無需收斂——未引入新的 undefined 來源 |
| L156-161 `handleToggleActive` 成功路徑 | API 回應 `data` | 是 | **已收斂**（`?? null` L158、`?? false` L159） |
| L182 `handleDelete` 成功路徑 | `filter`，不寫入新資料 | 否 | 無需收斂 |

四個路徑逐一核對後**沒有找到未收斂的路徑**：唯二會把新鮮 API 資料寫入這兩欄的地方（`applyPage` 與 `handleToggleActive`）皆已收斂；另兩處不引用回應中的這兩欄，不構成風險。**判定：Major 3 達成，且經核對確實涵蓋全部路徑。**

### 迴歸檢查

核對四份文件在本輪修正前後是否互相矛盾、是否與已核可的 pre-Revision-1 內容矛盾：未發現硬性自相矛盾。`business-logic-model.md`（U2）保留了 pre-Revision-1「為何不做共用工廠函式」整段（L52-65，未回改），並在檔案末新增「與 Q1 的關係」記明偏離，此為 `project.md` 已確立處置慣例的鏡像運用（「下游查證推翻的是選項的理由而非決定本身時，只修理由不改決定」），不算迴歸。

### 新發現

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| N1 | Minor | `user-object-serialization/business-logic-model.md` L259 | Major 2 修正新增的「逐字」引用遺漏 C-4 原文「（接受使用者物件與當下時刻）」括號子句，見「Major 2 特別查核」第 1 點。不影響論證成立，但與本 intent 已多次強調的「逐字核對」紀律不符 | 補回被省略的括號子句，或改標「大意為」而非「逐字為」 |
| N2 | Minor | `admin-page-column/business-logic-model.md` L4；`frontend-components.md` L4 | Major 4 的修正建議「並把 `bolt-plan.md` 補進文件頭的上游來源清單」未落地：兩檔的「上游來源」清單皆未列 `bolt-plan.md`，僅在 e2e fixture 策略節內文提及。實質內容已補齊，此為建議中較次要的一半未完成 | 在兩檔的「上游來源」清單加入 `../../../inception/delivery-planning/bolt-plan.md`（B3 DoD） |
| N3 | Minor | `admin-page-column/business-logic-model.md` Revision 1「本單元的驗證強度」表最後一列 | 「無障礙的四項（焦點可見、非僅顏色、AT 可讀、44x44）｜人工（無 axe、無 jsx-a11y）｜❌」為整體性判定，但實測 `regression.spec.ts` L118-125：`await expect(pager.locator('[aria-current="page"]')).toHaveText('[1]')` 確實以自動化斷言驗證了分頁控制「非僅顏色」表達目前頁次（`interaction-spec.md` L143 明文將此方括號標記歸於 AC-5.9／NFR-2 的「不僅以顏色」要求）；同檔多處 `getByRole` 查詢（如 L120 的 `navigation` landmark、L109 的 `columnheader`）也為「AT 可讀」（accessible name／role 存在）提供部分自動化訊號。表格的❌是對整個「無障礙四項」的籠統判定，未區分「分頁控制的非僅顏色」（有覆蓋）與「LastActivityCell 逾期圖示的非僅顏色」（無覆蓋）等不同實例，屬輕微低估（under-claim） | 拆分該列：「PaginationControl 目前頁次的非僅顏色標示」標為 e2e 已覆蓋（引用 `regression.spec.ts:124`）；其餘（LastActivityCell 圖示替代文字、44x44、完整 AT 可讀性）維持人工／❌ |
| N4 | Major（既有缺口，非本輪修正引入） | `frontend-components.md`「桌面回歸的驗收落點（Q2=A）」節（L167-171）；`business-logic-model.md`「本單元的驗證強度」表「三項既有操作在桌面不退化」列（L89） | 兩處皆宣稱「新增桌面 e2e 回歸涵蓋三項操作」（角色調整、啟停用、授權，對應 `requirements.md` NFR-7），驗證強度評為「強」。但實測 `regression.spec.ts`（repo 唯一 e2e 檔）：桌面情境下只有「切換到第 2 頁…停用一個帳號」（L127-154）測試了**啟停用**一項；全檔對「角色調整」（無任何操作 `<select>` 的測試）與「授權」（僅有使用者自行**註冊**進入待授權態，沒有管理者**核准／處理**授權申請的桌面測試）皆零覆蓋。這與本 intent 已核可的 `inception/user-stories/stories.md` Finding A（L637）記載的缺口是同一件事——該處誠實記載「桌面情境的角色調整、啟停用、授權操作…任何 AC 或 DoD 都沒有要求任何自動化或人工驗證」，並以「單一 Major、有明確且低成本修補路徑」為由判 READY（保留，非宣稱已修）。本檔與 `business-logic-model.md` 這兩處敘述沒有延續 `stories.md` 的誠實保留，逕自寫成「已補上」「強」，對現況過度宣稱。此缺口先於 Revision 1 存在，非本輪分頁修正引入的迴歸，不計入本輪 7 項 finding 的達成率評估，但屬本輪查核範圍內可核對的程式碼事實，如實記載 | 把「三項操作」改寫為「僅『啟停用』一項已有桌面 e2e 覆蓋；『角色調整』與『授權』兩項桌面回歸仍缺 e2e，與 `stories.md` Finding A 記載的既有缺口一致，非本輪處理範圍」，驗證強度表對應列由「強」降為「部分」 |

### Summary

iteration 1 的 4 Major＋3 Minor 逐項獨立查核：Major 3（正規化契約）與 Minor 5／6（引用更正、AC-5.11 人工驗證義務）**完全達成**，皆有程式碼或上游文件逐字核對支持；Major 1／Major 4／Minor 7 **達成核心實質**（矛盾消除、fixture 決定可發現、Revision 1 行為誠實揭露）但各自遺漏建議中的次要部分（流程圖、上游來源清單登錄、無障礙表格的實例區分），屬文件完整性層次的殘餘瑕疵；Major 2 的決定與程式碼一致成立，但修正新增的「逐字」引用本身有一處未加註記的省略（N1）——這是本 intent 第二次被查出「逐字」宣稱與原文有出入，模式值得團隊留意。本輪另查出一項先於 Revision 1 存在、與本輪修正無關的既有過度宣稱（N4）：桌面回歸 e2e 只覆蓋 NFR-7 三項操作中的一項，兩份 functional-design artifact 卻評為「強」，未延續上游 `stories.md` 已誠實記載的保留。現存開放項計 0 Critical、1 Major（N4，既有缺口）、3 Minor（N1／N2／N3），未超過「≤2 Major 不擋 READY」的裁決門檻。**判定 READY**——建議下一次小步修訂處理 N1〜N4，其中 N4 優先權最高（它涉及一個已核可 NFR 的驗收落點是否真的存在，而非本文件的內部一致性），但不構成本輪的 NOT-READY 理由。
