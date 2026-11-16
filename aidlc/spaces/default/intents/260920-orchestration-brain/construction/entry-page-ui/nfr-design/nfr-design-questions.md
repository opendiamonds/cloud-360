# NFR Design 問題檔 — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T04:06:39Z（`date -u` 取值）。**本站出題數為 1（`EPD1`）。**
>
> 本站的主要工作是把 `../carried-review-items.md` 的 15 項（functional-design 8 項、nfr-requirements 7 項）與其中五項使用者裁決
> 落成具體設計。逐項查過之後，除 `EPD1` 外的每一個設計選擇都落在下列三種之一：(1) 使用者裁決或帶入項的 Required action 已指定方向；
> (2) 已核可規則的字面或既有程式只容許一種**正確**做法（其餘做法會製造新的正確性問題，依 `project.md` 的
> `requirements-analysis:260822-ra-c5` 不出成假選擇，改在產出內揭露）；(3) 模組內部結構或常數，預設錯了是局部修改。Depth **Minimal**。
>
> **未作答期間的產出狀態**：四份產出依建議項 A 撰寫；凡會因 `EPD1` 改變的段落，就地標「（`EPD1` 依賴）」並寫明 B／C 時的改法。

## 〇、上游已定案、本站不重問

| 事項 | 定案 | 出處 |
|---|---|---|
| 名稱查詢套用 `U23` 可見性，不可見即三名稱皆 null；須有被移出建立者的雙向測試 | 使用者 2026-10-17T02:06:14Z 裁決 | `../carried-review-items.md` functional-design `R-01` |
| 首次對齊在畫布有未儲存內容時不自動開圖 | 同上裁決 | 同上 `R-02` |
| 對話清除綁登入／登出事件、不依賴 `User.id`、不重掛路由樹 | 同上裁決 | 同上 `R-03` |
| 大腦的對象目錄（`_build_catalog`）、反問標籤、唯一命中設定目標同樣套可見性 | 使用者 2026-10-17T03:58:59Z 裁決 | 同上 nfr-requirements `R-01` |
| 名稱查詢每組 ≤ 5 條 SQL、快照 ≤ 15 條（含 `_authorize` 一次） | 同上裁決 | 同上 nfr-requirements `R-02` |
| 對話紀錄每段 500 則上限 | `EPN1`=A | `../nfr-requirements/nfr-requirements-questions.md:83` |
| 名稱查詢不設逾時、不在前端寫死 4000 字、零新依賴、零新環境變數 | nfr-requirements 定案 | `../nfr-requirements/performance-requirements.md` §四、`tech-stack-decisions.md` |
| `U13` 不得 import `services.membership_facade`／`membership_service`／`main` | 既有靜態鎖 | `backend/tests/test_brain_gateway_limits.py:380-382` |

## 一、刻意不出成題目的設計選擇（附理由）

| # | 設計選擇（本站定案） | 不出題的理由 |
|---|---|---|
| 1 | 可見性以 `MembershipFacade` 的 **factory** 注入 `BrainGateway`／`build_brain_gateway`（必填、無預設），由 `main.py` 傳入；每個受守門的 facade 呼叫點以 `project_visible=<factory>(db).project_visibility(principal)` 就地產生閉包 | nfr-requirements `R-03` 的 Required action 已指定「注入物須暴露 `project_visibility`、由 `main.py` 組裝」；`_HierarchyResolver` 與 `_build_catalog` 每次自開 session，閉包必須綁同一個 session，只能注入 factory（`security-design.md` §二之一） |
| 2 | 目錄的可見性守門放在 `U7` 的 `list_projects`／`list_systems`（加必填 `project_visible`），不放在 `U13` 內自行過濾 | 兩者唯一的應用程式呼叫端就是 `_build_catalog`（`grep` 實查，`security-design.md` §三之一）；放在 facade 才能被 `S2`／`S3` 靜態鎖涵蓋並 fail-closed，放在 `U13` 則任何新呼叫端都會靜默繞過。改的是簽章、不是語意，`test_hierarchy_service.py` 兩處補一個關鍵字 |
| 3 | 子頁面收到 4403 **不導航**；入口頁收到 4403 先 `refreshMe()` 再由 `DefaultRedirect` 重判；子頁面的大腦掛點只在 `can('K1','view')` 時掛載 | `BR92.5` 字面「4403 → Navigate 到 `/`」在子頁面會形成**無限迴圈**：`K1` 被撤銷而 `A1` 仍在時，`DefaultRedirect`（`App.tsx:28`）把 `/` 導回 `/workspace`，面板再連、再 4403。另一個做法（照字面導航）會製造正確性問題，不是可選項；偏離在 `security-design.md` §五之二揭露 |
| 4 | 對話清除以 `AuthProvider` 新增的 `subscribeAuthBoundary` 事件訂閱承載；`login()`／`logout()` 第一行同步通知 | 裁決已指定「綁事件本身」；訂閱回呼內 setState 是 `react-hooks/set-state-in-effect` 允許的唯一形狀（effect 內監聽 user 為 error 級） |
| 5 | turnId 對照由「（段, 訊息索引）」改為「段」，位置以 turnId 在該段陣列中尋找 | `EPN1`=A 的「從最舊整則移除」會使所有索引位移，原形狀必然寫到錯的訊息；這是 `EPN-04` 的直接後果，不是選擇（`performance-design.md` §二之二） |
| 6 | 抖動範圍維持 [0.8, 1.0]，理由改述為「降低同步」；宣告持續 1011 情境下可完整重試的同時分頁數為 3 | nfr-requirements `R-07` 的 Required action 允許「改述理由」；實查被限流的握手**不計入**窗（`brain_gateway_rules.py:642-647`）且在 accept 前關閉，放寬抖動不改變預算（`performance-design.md` §一之三） |
| 7 | `/assessment` 的未存檔判定為「有未存檔上傳或未存回的優化結果」 | 裁決點名「未存檔上傳」；`optimizeDraft` 是同頁唯一另一種只在記憶體中、換圖即遺失的使用者產出。既有下拉改選（`AssessmentPage.tsx:1262-1270`）會清掉協作預覽，故協作預覽不列入（頁面本身就視其為可丟棄） |
| 8 | e2e spec 禁手寫訊框的 lint 選擇器限定為「同時有 `type` 與 `payload` 鍵」的物件字面量，並把既有三條子協定規則抽成常數在兩個設定區塊共用 | 只看 `type` 鍵會誤擋既有的 `member-pages.spec.ts:573`；flat config 對同一條規則**以後者取代前者**，不重列既有選擇器會使 tests 目錄失去子協定保護（`logical-components.md` §一之三） |

## 二、問題

### EPD1. 被移出的建立者直接送出「設定作業對象」時，伺服器要怎麼處理？

**背景**：兩項裁決已關掉兩條路——名稱（脈絡列看不到專案、系統、圖名）與大腦目錄（說出專案名稱時反問與唯一命中都找不到它）。
但還有第三條路，裁決原文「**也不能經大腦指定該專案／系統**」逐字涵蓋它，而目前沒有任何守門：

- 頁面送出的「設定作業對象」訊息（`brain_gateway.py:1403` 的 `_on_set_work_target`）經 `SessionStore.set_work_target`
  （`session_store.py:387`）→ `_HierarchyResolver`（`brain_gateway.py:564-577`）→ `HierarchyFacade.resolve_work_target`
  （`hierarchy_facade.py:381`），**只檢查擁有者**，不檢查可見性。
- 會走到這條路的兩種情形：
  1. **開自己的圖**：被移出的建立者仍擁有自己畫的圖（圖的擁有者是圖的資料列本身）。這張圖若掛在前專案的系統下，
     `/workspace` 開它時本單元會自動回寫（`BR97.6` ①），伺服器由圖推導出前專案（`hierarchy_service.py:318-322`），
     作業對象就被設成前專案——脈絡列名稱是空的（裁決的效果），但**交辦給 agent 時帶的是前專案**。
  2. **直接指定前專案或其系統的編號**：正常畫面做不到（對象選單讀的是 `U23` 已套可見性的清單），只有手工送訊息或停在舊畫面才會發生。

A. **（建議）直接指定前專案或其系統 → 視同「查不到」；由自己的圖推導出前專案 → 只保留圖，專案與系統留空。**
   你會看到的：被移出的建立者開自己的圖時，脈絡列只顯示圖名、沒有錯誤訊息，作業對象只有這張圖；手工指定前專案時，
   收到的錯誤與今天指定別人的專案**逐字相同**（「查不到」那一句），無法藉此分辨專案是否存在。其他所有人的畫面與行為不變。
   代價：`U7` 的 `resolve_work_target` 多一個必填參數（漏傳即程式錯誤，不會靜默放行）、每次設定作業對象多一條 SQL；
   靜態鎖多涵蓋一個方法並為 `session_store.py` 那一個呼叫點加一筆有理由的例外；既有 3 處測試呼叫補一個參數；
   新增雙向測試（被移出者兩種情形 ＋ 一般擁有者不受影響）。**殘留**：移出**之前**就已設好的作業對象不會被追溯清掉，
   直到使用者改選對象或工作階段**閒置** 24 小時到期（`redis_gateway.py:102-103`，每次互動續期——持續使用就不會到期）；
   在那之前名稱已是空的，但交辦仍帶前專案。
   建議理由：唯一同時做到「不能指定」與「不讓被移出者每開一次自己的圖就看到錯誤」的做法；錯誤句與既有路徑相同，不新增探測面。
B. **一律視同「查不到」，包括由自己的圖推導出來的情形。**
   你會看到的：被移出的建立者在 `/workspace` 開任何一張掛在前專案下的自己的圖，都會看到「查不到」的錯誤（`BR92.6` 原樣顯示），
   作業對象維持原值不變。
   代價：與 A 相同的程式改動；但被移出者的日常操作會反覆出錯，且錯誤說的是「查不到」而他明明開著那張圖——訊息與畫面矛盾。
C. **這條路本次不關，列為已接受的殘留並開 OPEN 項。**
   你會看到的：與現在完全相同。
   代價：零程式改動；裁決的「不能經大腦指定」只對「用講的」成立，對「開自己的圖」與手工訊息不成立——被移出者的交辦仍會帶前專案給 agent。
   `security-design.md` §八須把這一項列為殘留，ADR 草案的 Security 段須逐字寫出。

[Answer]: A <!-- 2026-10-17T04:22:24Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->
