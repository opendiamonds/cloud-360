# Business Logic Model — U3 `admin-page-column`

> Stage: functional-design（Construction 3.1）· Unit: `admin-page-column`（kind: ui）
> 上游來源：`../../../inception/application-design/components.md` C-5／C-6、`component-methods.md` C-5／C-6、`services.md`、`../../../inception/refined-mockups/interaction-spec.md`、`mockups.md`、`design-system-mapping.md`、`accessibility-checklist.md`、`../../../inception/requirements-analysis/requirements.md`（下稱 requirements）、`../../../inception/user-stories/stories.md`（下稱 stories）、`../../../inception/units-generation/unit-of-work.md`、`unit-of-work-story-map.md`。、`../../../inception/delivery-planning/bolt-plan.md`（B3 DoD —— e2e fixture 策略的定案處）
> 元件層級、屬性設計、互動流程與 API 整合點見 `frontend-components.md`。
> **產出集合說明**：本單元 `kind: ui`，依 stage 的 `produces_kinds`，適用產出為 `business-logic-model.md` 與 `frontend-components.md`；`business-rules.md`／`domain-entities.md` 僅適用 service／spec／library 類單元，本單元不產出。
> 問答定案：Q1=A（在地時區 + 釘住測試環境；**格式依上游**）、Q2=A、Q3=A。事實查證 S1〜S9 見 `functional-design-questions.md` 的 `## Sources`。

## 本單元做什麼

把 U2 帶進 API 回應的兩個欄位，呈現在管理頁的使用者清單上 —— 桌面為表格新增一欄，768px 以下改為卡片佈局。

**這是本 intent 的核心價值落點**：前面四個單元交付的東西，稽核者一個都看不到；到這裡他才真的「一眼看出哪些帳號已逾期未活動」。也是唯一的 **L 級**單元（13 條 AC）。

## 觸發點

**管理頁的使用者清單每次算繪**。既有的資料抓取流程完全不動（既有行為不退化，見 `frontend-components.md`）。

## 主流程

```
管理頁載入（既有流程，不動）
 |
 +-- 既有的使用者清單抓取
 |     |
 |     +-- 載入中 / 錯誤 --> 頁面層整塊替換整個表格（既有模式）
 |                          本單元的儲存格元件在此不會被渲染
 |
 +-- 取得清單資料（型別來自 U5 產生的型別）
 |
 +-- 逐列傳遞前正規化 (R2)
 |     |
 |     +-- 時間欄位缺席或為 undefined --> 收斂為「空」
 |     +-- 旗標欄位缺席或為 undefined --> 收斂為「假」
 |
 +-- 依斷點呈現兩份標記之一 (R3，純 CSS)
      |
      +-- 768px 以上：表格，新欄位於角色之後、操作之前（共 6 欄）
      |    卡片那份標記存在但由 display:none 隱藏
      |    (display:none 的子樹原生排除於無障礙樹, 不需 aria-hidden)
      |
      +-- 768px 以下：卡片，每張逐行呈現 6 個欄位
           表格那份標記存在但由 display:none 隱藏
           (同上, 不需 aria-hidden)
 |
 +-- 儲存格元件依傳入的兩個屬性選擇狀態
      |
      +-- 時間為空 -----------> 可聚焦破折號 + 說明文字
      +-- 有時間、旗標為假 ---> YYYY-MM-DD HH:MM（在地時區），一般字色
      +-- 有時間、旗標為真 ---> 圖示 + 同格式時間，警示色，圖示帶文字替代
```

**文字 fallback**：管理頁沿用既有的清單抓取流程；載入與錯誤時整塊替換整個表格，本單元的元件不會被渲染。取得資料後，逐列在傳遞給儲存格元件之前完成正規化（缺席或未定義的欄位收斂為「空」與「假」）。佈局由 768px 斷點以純 CSS 切換，兩份標記同時存在於 DOM，非當前佈局的那份以 `display: none` 隱藏 —— 該子樹原生就被瀏覽器排除在無障礙樹之外，**不需要另外設定 `aria-hidden`**。儲存格元件依傳入的兩個屬性選擇三種呈現之一：時間為空時顯示可聚焦破折號與說明文字；有時間且未逾期時以 `YYYY-MM-DD HH:MM`（瀏覽器在地時區）顯示；逾期時額外加上帶文字替代的圖示並變為警示色。

## 三個本站定案的取捨

### 一、時間格式與時區：上游定格式，本站定時區

| 面向 | 誰定的 |
|---|---|
| 格式 `YYYY-MM-DD HH:MM` | **上游已定案**，本站依循 |
| 時區 = 瀏覽器在地 | **本站 Q1 定案** |
| Playwright config 釘住 locale 與 timezone | **本站 Q1 定案** |

**必須明記的對齊修正**：Q1 選項 A 的字面描述是「沿用既有實務（無參數呼叫）」，但依 S1 的既有實務其輸出為 locale 相依格式，**不是**上游定死的格式。本站沿用的是既有實務的**時區政策**，格式依上游。這是對齊修正、**非本站新定案**；落差的來源與拆解記於問題檔 Q1 的 Revision 段，上游檔案不回改。

**為何釘住測試環境而不是改產品行為**：依 S3，Playwright config 既未設 locale 也未設 timezone，所以 e2e 的時間斷言本來就會隨執行環境漂移。這個不確定性的來源是**未釘住的測試環境**，不是顯示選擇 —— 修在測試層才是修在它真正所在的地方。

### 二、桌面回歸：補上上游缺的 AC 落點

requirements NFR-7 點名三項操作（角色調整、啟停用、授權），但 stories AC-4.3 的 Given **只限定小螢幕**。這個缺口自 refined-mockups 起追蹤，`phase-check-inception.md` 標明由本單元承接。

**本站補上**：新增桌面 e2e 回歸涵蓋三項操作。依 S4，既有 e2e 只有一支檔案、6 個 case、**無一導覽至 Admin 頁** —— 本單元本來就要寫 repo 第一個 Admin 頁 e2e（team-practices 規則 C），把三項操作一併涵蓋是在同一支檔案裡多寫幾個 case，不是新建機制。

### 三、佈局切換：純 CSS 不是風格偏好，是工具鏈約束

依 S9，`react-hooks/set-state-in-effect` 是 **error 級**規則；JS 版斷點的初始量測必須在 effect 內設定狀態，**直接違反它 → CI 紅燈**。依 S7，全前端零 `matchMedia`／`innerWidth`，也沒有先例可沿用。

**原以為的代價其實不存在**（reviewer iteration 1 更正）：切換以基於 `display: none` 的響應式類別達成，而 `display: none` 的子樹**本來就被排除在無障礙樹之外** —— 視覺隱藏與無障礙排除是**同一條 CSS 規則**，沒有需要同步的屬性，也就沒有不同步的風險。初版把這個由 CSS 免費解決的問題寫成「必要配套」與「本站新引入的缺口」，是**過度謹慎導致的誤判**。

**但有一條必須明寫的警告**：**不得**改以 JS 動態設定 `aria-hidden` 來達成同一效果 —— 那需要在 effect 內設定狀態，會撞回 Q3 本來就要規避的 error 級 lint 規則。切換機制與可及性處理必須是同一個 CSS 機制。

## 本單元的驗證強度（分項評估）

| 項目 | 驗證方式 | 強度 |
|---|---|---|
| 表頭出現新欄位 | Playwright e2e（team-practices 規則 C 的最低要求） | **強** |
| 至少一列顯示時間值或無紀錄佔位 | 同上 | **強** |
| 三項既有操作在桌面不退化 | **本站新增**的桌面 e2e 回歸（Q2=A） | **強** —— 補上原本沒有 AC 落點的缺口 |
| 時間顯示的格式與時區 | e2e 斷言 + **config 釘住 locale／timezone** | **強**（釘住之後才強；未釘住時此斷言會隨環境漂移） |
| 前後端欄位形狀一致 | U5 的型別產生 + 建置期失敗 | 由 U5 承載 |
| 逾期判定正確 | **不在本單元** —— 屬 U1 的純函式測試 | 由 U1 承載 |
| 小螢幕卡片佈局與觸控目標尺寸 | **無自動化驗證** —— viewport 切換與觸控尺寸驗證屬尚未存在的測試形狀 | **無**（如實記載） |
| 對比度符合 WCAG AA | **無自動化驗證** —— 現行工具鏈無對比度檢查 | **無**（自 Inception 起追蹤的既有缺口） |
| 跨佈局的無障礙屬性一致 | 上游 `accessibility-checklist.md` **R-2**（4.1.2，兩種 viewport 各驗一次） | **部分**（上游已評為部分可自動化）—— **非本站新引入**，初版誤標，已更正 |

**本站未新增任何驗證缺口**（reviewer iteration 1 更正）。初版宣稱純 CSS 方案引入了「`aria-hidden` 與斷點不一致」的新缺口 —— 那是誤判：`display: none` 已由瀏覽器原生排除於無障礙樹。跨佈局的無障礙一致性是上游 `accessibility-checklist.md` **R-2** 既有的追蹤項，不是本站產生的。

表中標為「無」的兩項（小螢幕卡片佈局與觸控尺寸、對比度）皆為**繼承自上游**的既有缺口，非本站引入。

## 與其他單元的介面

| 對象 | 介面 | 方向 |
|---|---|---|
| **U5**（型別契約） | 取用其產生的使用者物件型別，不再手寫 | 本單元**依賴** U5 |
| **U2**（序列化） | 消費其回應中的兩個欄位 | 本單元**依賴** U2（經 U5 間接） |
| **U1** | 無直接介面 —— 逾期旗標由 API 傳入，本單元不呼叫 U1 的任何函式 | 無 |
| **U4** | 無程式碼耦合。但 U4 決定主要 persona 進不進得了這個頁面 | **驗收依賴** |

## 本單元不做的事

| 事項 | 為何 |
|---|---|
| 計算逾期 | 旗標由 API 傳入；在算繪中讀取當下時刻會觸發既有 lint 規則 |
| 改變資料抓取的形狀 | 見 `frontend-components.md` 的「API 整合點」與「既有行為不得退化」；既有形狀受 lint 規則約束（抓取與狀態更新分離） |
| 重新設計載入態與錯誤態 | stories AC-1.9 已定案沿用既有整塊替換模式 |
| 改動既有的角色欄空值呈現 | stories AC-2.5 已定案：新欄位僅以可及性手段與它區分 |
| 引入 i18n、日期函式庫或等寬字體 | 依 S2 repo 零此類依賴；`design-system-mapping.md` 明確排除等寬字體 |
| 重新評估待授權與逾期同列的雙警示色 | `mockups.md` 已把該最壞情境實際畫進範例並判定可接受 |

## 事實查證（本站主張的依據）

| 主張 | 查證方式 | 結果 |
|---|---|---|
| 既有時間顯示皆為瀏覽器在地時區 | 全前端搜尋時間格式化呼叫 | **成立**（S1）—— 4 處，皆無參數 |
| 無參數呼叫的輸出**不是**上游定死的格式 | 比對上游格式規定與該呼叫的實際輸出形式 | **成立** —— 這是本站對齊修正的依據 |
| Playwright config 未釘住 locale 與 timezone | 讀取 config | **成立**（S3）—— 這使「釘住測試環境」成為本站的配套決定 |
| 既有 e2e 無一導覽至 Admin 頁 | 列舉單一 spec 檔的全部 case | **成立**（S4）—— 6 個 case，4 個身分驗證、2 個 RBAC |
| 既有表頭為 5 欄，新增後為 6 欄 | 讀取表頭定義 | **成立**（S5） |
| 全前端零 `matchMedia`／`innerWidth` | 全前端搜尋 | **成立**（S7）—— JS 版斷點無先例可循 |
| `set-state-in-effect` 為 error 級 | `team.md` 已載明的 lint 規則清單 | **成立**（S9）—— 這是否決 JS 版斷點的決定性依據 |

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-09T16:28:06Z
**Iteration:** 1

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Major | `business-logic-model.md`「三、佈局切換」；`frontend-components.md`「佈局切換（Q3=A）」「必要配套：兩份標記並存的可及性處理」 | **`aria-hidden` 必須「與斷點條件一致」的要求，與 Q3 自己禁止的機制互相矛盾，且未處理標準做法已免費解決此問題的事實。** Q3=A 的決定性理由是「不得以 JS 量測視窗寬度」（`react-hooks/set-state-in-effect` 為 error 級）；但要讓一個 HTML 屬性（`aria-hidden`）隨斷點動態翻轉，唯一不靠 JS 的手段就是依賴 CSS `display: none`（Tailwind 的 `hidden`／`md:hidden`／`md:table` 等 responsive class 正是這個效果）—— 而 `display:none`（含 `visibility:hidden`）的元素**本來就會被瀏覽器自動排除在無障礙樹之外**，不需要另外設定 `aria-hidden`，也就不存在「與斷點條件不一致」這種風險（因為視覺顯示與無障礙排除是同一條 CSS 規則）。兩份 artifact 都沒有講清楚「純 CSS：由斷點類別控制顯示」具體是什麼機制（全文零 `display`／`hidden`／`md:table`／`md:hidden` 字樣），也沒有處理這個標準行為，於是把一個標準做法已經免費解決的問題，宣告成「必要配套」與「本站新引入、現行工具鏈不會發現的缺口」。更值得注意的實作風險：若開發者真的按字面理解「需要一個會隨斷點翻轉的 `aria-hidden`」，最直覺的實作路徑是用 JS 量測寬度再設屬性——那正好撞回 Q3 本來要規避的 error 級 lint 規則（CI 會擋下，屬自我限制的失敗模式，故不到 Critical）。「跨佈局無障礙屬性一致」本身也不是本站首次發現：`accessibility-checklist.md` 的 R-2 已就同一主題（「跨佈局的無障礙屬性一致」，4.1.2）評為「⚠️ 部分可自動化」，兩份 artifact 的表頭都把 `accessibility-checklist.md` 列為上游來源，卻沒有在此處引用或核對 R-2，逕自宣稱是「本站新引入」的缺口。 | 明確二選一並寫進 artifact：①（建議）刪除「必須設定 aria-hidden」的要求，改寫為「以 Tailwind responsive display class（`hidden md:table` / `md:hidden` 等）控制顯示即足夠——`display:none` 的元素原生排除於無障礙樹，不需額外的 `aria-hidden` 管理，也無『不同步』風險」，並同步移除驗證強度表中「無」的那一列（風險本不存在）；②若真的有理由要顯式 `aria-hidden`，必須說明在禁用 JS 斷點量測的前提下如何做到「隨斷點動態翻轉」，並回應這與 Q3 決定性理由的張力。無論哪個方向，都要回頭核對並引用 `accessibility-checklist.md` R-2，而非把已追蹤的既有項目重新標記為本站新發現。 |
| 2 | Minor | `business-logic-model.md` L109「本單元不做的事」表 | **懸空的內部引用 `R4`。** 主流程 ASCII 圖內文只明確標出 `R2`（正規化）與 `R3`（斷點呈現），`R4` 只在「本單元不做的事」表的「改變資料抓取的形狀」列出現一次，兩份 artifact 全文都沒有任何地方定義 `R4`（也沒有 `R1`）。讀者無法從文件內部解析這個標籤指的是哪條規則。 | 補上 `R1`／`R4` 的定義（或把編號體系寫成清單），或直接移除該列的 `R4` 標籤，改用純文字敘述（該列本身文字已足夠自明，標籤是多餘的）。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `python3 scripts/validate_repo_contract.py` | PASS（`Cloud-360 repository contract validation passed.`） | 文件語言、必要檔案／文字、禁止路徑與內容均合規，不受本次審查影響 |
| 事實查證 S1〜S9 逐項重測 | S1／S2／S3／S4／S5／S7／S9 皆與 repo 現況相符（`frontend/eslint.config.js`、`eslint-plugin-react-hooks@7.1.1` 原始碼、`playwright.config.ts`、`regression.spec.ts`、`AdminPage.tsx`、`package.json` 逐一核對） | 三項定案（Q1／Q2／Q3）的事實基礎成立；`react-hooks/set-state-in-effect` 經原始碼確認 `severity: Error`、`preset: Recommended`，S9 為決定性依據且屬實 |
| 上游契約交叉核對（`components.md`／`component-methods.md` C-5／C-6、`unit-of-work.md`、`unit-of-work-story-map.md`、`verification/phase-check-inception.md`、`accessibility-checklist.md`、`interaction-spec.md`、`design-system-mapping.md`） | 除 Finding 1 的 R-2 未交叉引用外，其餘引用（AC 編號、C-5/C-6/C-7/C-8 職責邊界、U1〜U5 依賴邊、13 條 AC／唯一 L 級、NFR-7 桌面回歸缺口的承接、AD-5/AD-9 例外範圍）逐條核實無誤 | `phase-check-inception.md` 位於 `<record>/verification/`（非 `inception/verification/`），初查一度疑似斷鏈，覆核後確認存在且內容與本站引用逐字相符；不構成 finding |

### Summary

三個定案（顯示時區與測試環境釘住、桌面回歸的驗收落點、佈局切換採純 CSS）的事實依據（S1〜S9）逐項查證屬實，且「對齊修正」的処理方式（不回改上游、以 Revision 段落記載）符合既有規則。唯一站得住腳的實質缺陷落在 Q3 的必要配套：把「`aria-hidden` 須與斷點條件一致」寫成不可迴避的驗證缺口，卻沒有處理 `display:none` 已經原生解決此問題的事實，也沒有回應這個要求與 Q3 自己禁用 JS 斷點量測之間的張力——這是一個 Major、可低成本修正的問題，不擋 READY；另有一個懸空的 `R4` 引用屬 Minor 文字瑕疵。開發者可依現有兩份文件實作，但落地前應先解決 Finding 1 描述的技術矛盾，避免在無障礙處理上走上一條會撞回既有 lint 護欄的路。

---

## Revision 1（2026-08-11）— 分頁狀態的邏輯模型

| 狀態 | 持有處 | 來源 | 生命週期 |
|---|---|---|---|
| 目前頁次 | 頁面層 | 使用者互動（初始為 1） | 切頁時改變；**處置操作不改變它** |
| 總筆數 | 頁面層 | 最近一次回應的 `total` | 隨每次抓取更新；**刪除時本地遞減**（避免顯示已知錯誤的值） |
| 每頁筆數 | 頁面層 | 最近一次回應的 `page_size` | 隨每次抓取更新；**不寫死前端常數**（後端是真相來源） |
| 總頁數 | **不持有** | 由總筆數與每頁筆數導出 | — |
| 切頁忙碌 | 頁面層 | 切頁動作開始／回應抵達 | **與初次載入的載入旗標分離** |

### 決策表：哪些操作觸發哪種抓取

| 操作 | 頁次 | 抓取 | 畫面 |
|---|---|---|---|
| 進入頁面 | 設為 1 | 抓第 1 頁 | 整塊替換為「載入中…」 |
| 點分頁控制 | 設為目標頁 | 抓該頁 | 容器內「載入中…」，控制項留在畫面上並標忙碌 |
| 角色調整**成功** | 不變 | **不抓** | 就地更新該列 |
| 角色調整**失敗** | 不變 | **不抓** | toast 提示；**不得**整份重抓 |
| 啟停用成功 | 不變 | **不抓** | 就地更新該列 |
| 刪除成功 | 不變 | **背景**抓當前頁 | 先就地移除該列＋總筆數遞減；回應抵達時靜默同步；**不進任何載入態** |
| 背景抓取失敗 | 不變 | — | 保留就地移除後的畫面＋toast；**不回滾、不跳錯誤畫面** |

### 邊界：目前頁次超出範圍

回應的 `page` 回顯請求值、`items` 為空時，頁面**不自動跳頁**（那會與後端的「不夾頁」矛盾），改呈現空清單態並提供回到第 1 頁的入口。此情境在兩條路徑上可達：使用者手動改網址／舊書籤，或刪掉某頁唯一一列後的背景重抓。

### e2e fixture 策略（reviewer Revision 1 Finding 4）

US-5 的 DoD 逐字要求「交付規劃前須擇一並記錄，**不得默認略過**」。決定**已作出**，但先前只落在 `bolt-plan.md` 的 B3 DoD（delivery-planning 的產出，非本單元列名的上游來源），本單元的文件對它零提及。在此明記：

**採用選項 (a)**：於 e2e 內以**公開註冊端點**建立超過一頁的帳號（每頁 20，故建 21 個）。

| 依據 | 內容 |
|---|---|
| 可行性 | `POST /api/auth/register` 無認證依賴，且既有 e2e 套件本來就在用它建帳號 |
| 成本 | 實測 bcrypt 約 0.305s／次，21 個約 6.4s，在 30s 逾時內 |
| 涵蓋到的 AC | AC-5.3（切頁不重複）、AC-5.6（處置後維持頁次）、AC-5.7（兩種佈局） |
| 副作用（正面） | 註冊出的帳號為 `pending`、角色欄為 `—`，順帶構成 AC-2.5「兩個破折號並存」的驗收資料 |

### AC-5.11 的人工驗證義務（reviewer Revision 1 Finding 6）

`unit-of-work.md` 的 AC 對照表把 **AC-5.11 的「介面不存在」子句**指派給本單元做**人工驗證**（靜態檢查：程式碼中不存在依最後活動時間排序或篩選的 UI）。本單元先前未承認這項義務，在此明記。

**驗證方式**：交付前對 `AdminPage.tsx`、`PaginationControl.tsx`、`LastActivityCell.tsx` 靜態檢查，確認不存在排序或篩選的控制項、也不存在會產生 `sort`／`order_by`／`filter` 查詢參數的程式路徑。AC-5.11 的另一半（契約層：帶非分頁參數不改變結果）由 U2 的端點測試自動涵蓋。

### 本單元的驗證強度（Revision 1 新增行為，reviewer Finding 7）

Revision 1 新增的行為不是全部都有自動化驗證，如實標記：

| 行為 | 驗證方式 | 能否真的失敗 |
|---|---|---|
| 表頭出現該欄、列顯示時間值 | e2e | ✅ |
| **NFR-7 回歸：角色調整仍可用、且該列時間欄不變空白** | e2e（reviewer Iteration 2 的新發現 N4 —— 先前宣稱桌面 e2e 已涵蓋三項既有操作，實際只有啟停用；**已補上角色調整的 case**）。**授權操作仍無 e2e 涵蓋**，維持 `stories.md` Finding A 已記載的既有缺口 | ✅（角色調整、啟停用）／❌（授權操作） |
| 分頁控制可見、顯示總筆數與目前頁次 | e2e | ✅ |
| 切頁取得不重複的帳號 | e2e（需 21 帳號 fixture） | ✅ |
| 處置後仍停在原頁次 | e2e | ✅（三處現行整份重抓，照舊寫法必紅） |
| 小螢幕改卡片、分頁控制仍可用 | e2e（`setViewportSize`） | ✅ |
| **切頁期間控制項不消失**（AC-5.10） | e2e 可斷言 DOM 存在，但**時間窗極短**、實務上難穩定捕捉 | ⚠️ 弱 |
| **焦點不離開分頁控制**（AC-5.10） | **無自動化** —— 人工 | ❌ |
| **併發保護**（重疊重抓只取最後一次） | **無自動化** —— 只能靠讀 code 確認。US-5 的 11 條 AC 與 DoD 皆未指派任何驗證者給它 | ❌ |
| **背景重抓不進載入態**（AD-12） | **無自動化** —— 只能靠讀 code 或人工觀察「刪除時整表不閃載入」 | ❌ |
| 無障礙：**目前頁次「非僅顏色」** | **e2e 已自動化** —— `regression.spec.ts` 斷言 `[aria-current="page"]` 的文字為 `[1]`，方括號正是非色彩線索，改成只靠顏色會讓該斷言紅 | ✅ |
| 無障礙：**AT 可讀（`aria-current` 存在）** | e2e（同上一列的同一個 locator） | ⚠️ 弱 —— 只驗屬性存在與其文字，不驗它掛在正確的元素上 |
| 無障礙：焦點可見、44x44 觸控目標 | 人工（無 axe、無 jsx-a11y） | ❌ |

**最後三項是本單元最實質的行為，卻也是最沒有自動化保護的** —— 它們的共同性質是「正確與錯誤在畫面上的差別極小或極短暫」。如實記載，不假稱已涵蓋。
