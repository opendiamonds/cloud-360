# 更正附錄 — `object-picker-ui` 的 NFR Requirements

> 撰寫時間 2026-10-18T02:09:43Z（`date -u` 取值）。

## 這份附錄是什麼

本站審查（`reviews/review-01.md`）判 **NOT-READY**：0 Critical、3 Major、4 Minor。收據記下後 `performance-requirements.md`／`security-requirements.md`／
`tech-stack-decisions.md`／`traceability.json` 凍結。unit-major 期間不得以跳站重開（跳站會使所有單元的收據失效，見 `nfr-requirements/memory.md`
2026-10-17T14:56:14Z 條），比照 `a11y-gate` 已核可的處置：原檔不動，本附錄逐條處置，**衝突時以本附錄為準**。下游（`nfr-design` 起至
`code-generation`）必須逐條綁定 `N-01`–`N-07`。本附錄**未經審查**。

`R-02` 涉及使用者看得到的搜尋行為，已出成題目 `OPN1`（問題檔 §二），使用者 2026-10-18T02:09:43Z 經選單選 **A**。

## 名詞：選單檔案集合（下文所有靜態檢查的範圍）

依 `functional-design/frontend-components.md:55-63` 的檔案規劃，寫死為：

- `frontend/src/brain/objectPickerData.ts`
- `frontend/src/brain/objectPickerModel.ts`
- `frontend/src/components/brain/ObjectPicker*.tsx`（`ObjectPicker.tsx`、`ObjectPickerGroup.tsx` 及其拆出的子元件，一律以 `ObjectPicker` 開頭）

`code-generation` 若新增選單專屬檔案，必須落在上列路徑樣式內；`ContextBar.tsx` 的擴充不在集合內（它是 `U14` 的檔，只加鈕與 `pickerOpen`）。

## 逐條處置

### N-01 — `OPN-04` 的夾具不可達（審查 `R-01`，Major）

**問題屬實**：`/api/auth/me` 回 500 時 `permissions` 為空（`AuthContext.tsx:98-109`），`can('K1','view')` 為假，`DefaultRedirect`（`App.tsx:30-47`）把使用者導到
`/403`，子頁面也被 `CapabilityRoute` 擋下，選單根本不會渲染。

**更正（取代 `OPN-04` 的量測方式與 `tech-stack-decisions.md` §五自檢 1 的 `OPN-04` 推導）**：第一次 `/api/auth/me` 回 **200、權限齊全、但主體不含 `id`**
（`fetchMe` 以 `data.id` 取值（`AuthContext.tsx:31`），結果為 `undefined`；權限完整使路由守衛放行）。之後的 `/me` 分兩情境：
(a) 仍回不含 `id` 的 200；(b) 回 500（`refreshMe` 拋錯）。兩者都斷言：開啟選單後 `/me` 只多 **1** 次請求、出現「無法確認你的身分，請重新整理頁面」、
按重試鈕再多 **1** 次。目標欄位不變。

### N-02 — 系統清單延後抓與搜尋、「目前」標示的牴觸（審查 `R-02`，Major；`OPN1`=A）

**定案（取代 `OPN-01`、`OPN-06` 的目標與量測，並補 `BR13.1`／`BR13.3`／`BR13.4` 在 `F-05` 之後的行為）**：

1. **開啟**：抓專案清單 1 次。目前作業對象所在的專案**預設展開**並抓其系統清單（目前對象為專案或系統時各 1 次；無目前對象時 0 次）。其餘群組收合。
2. **展開控件**：每個群組的專案列旁一個展開鈕（`aria-expanded`、`aria-controls` 指向該群組的系統清單），鍵盤 Enter／Space 切換；展開觸發該群組的系統清單請求，同一次開啟內至多 1 次。展開鈕與「選定專案」是兩個不同的控件（專案列本身仍可選，`BR13.1`）。
3. **搜尋**：搜尋框**第一次**輸入非空字元時，對所有尚未載入的群組補抓系統清單，經 `U23` 的 `fanoutQueue`（同時最多 4 個、FIFO）；補抓期間清單上方顯示「正在載入系統清單」且 `aria-busy="true"`；之後同一次開啟內再輸入**不發請求**。比對範圍為專案名與已載入的系統名；有命中系統的群組自動展開顯示命中列。單一群組補抓失敗只讓該群組顯示錯誤與重試（`F-05`），其餘照常比對。
4. **零系統**：`BR13.1` 的「尚無系統」只在該群組系統清單已載入且為空時顯示；未載入的群組不顯示任何系統相關文字。
5. **請求數上界（取代 `OPN-01`）**：開啟時 **1～2** 次（專案 1 ＋ 目前所在群組 0～1）；開始搜尋後再加至多 **P − 已載入群組數** 次（P＝專案數），之後恆為 0；任何群組在同一次開啟內至多被抓 1 次。
6. **搜尋請求（取代 `OPN-06`）**：第一次輸入觸發上述補抓；**之後**輸入 10 個字元，`/api/` 新請求 **0** 次。

**e2e**：以 `page.route` 回 30 個專案、目前對象為專案 7 底下的系統 70：開啟後請求 2 次、專案 7 展開且系統 70 列標「目前」；輸入第一個字後請求增為 31（30＋1）、輸入系統名可命中專案 20 底下的系統；再輸入 10 字元請求仍為 31。另一案：補抓中讓專案 12 的系統清單回 500，斷言只有專案 12 群組顯示錯誤、其他命中照常。

**`OPN-24` 的更正**：`fanoutQueue` **恢復使用**，但只用在第 3 點的搜尋補抓；開啟與展開各為單一請求。關閉選單時呼叫佇列的 `cancel()`（尚未發出者永不發出）並以 `cancelled` 旗標丟棄在途結果（`OPN-02` 照舊）。

### N-03 — 只靠靜態 grep 的「必須紅燈」沒有承載者（審查 `R-03`，Major）

**更正**：凡 `OPN-11`、`OPN-13`、`OPN-14`、`OPN-15`、`NFR5.160`、`OPN-24` 中以 grep 判定的突變，改由 **ESLint 規則**承載，使 `npm run lint`（CI 的 frontend job）紅燈。
在 `frontend/eslint.config.js` 新增一個 `files` 限定為上方「選單檔案集合」的區塊：

| 禁止 | 規則形式 | 承接的需求 |
|---|---|---|
| `console.*` 任何呼叫 | `no-console: error` | `OPN-15` |
| `localStorage`／`sessionStorage`／`indexedDB`／`caches` | `no-restricted-globals` | `OPN-15` |
| `dangerouslySetInnerHTML` 屬性、`innerHTML`／`outerHTML` 指派 | `no-restricted-syntax`（JSXAttribute 名稱、MemberExpression 屬性名） | `OPN-13` |
| `new RegExp(...)`、正規表示式字面量用於搜尋 | `no-restricted-syntax`（`NewExpression[callee.name="RegExp"]`） | `OPN-14` |
| 匯入 `createProject`／`createSystem` | `no-restricted-imports`（`importNames`） | `OPN-11` |
| `new WebSocket(...)` | `no-restricted-syntax` | `NFR5.160` |

e2e 側同時改寫 `OPN-15` 的主控台檢查：不比對名稱字串（`console.log(groups)` 的 `msg.text()` 不含名稱，會是恆綠），改為**以進入選單前為基準**，
選單開啟、搜尋、建立一輪期間新增的主控台訊息數為 **0**（`page.on('console')` 計數，不分類型）。`OPN-24` 的「`fanoutQueue` 匯入為 0」因 `N-02` 而**作廢**。
`OPN-25` 的產出清單加上「`eslint.config.js` 的選單區塊」；每條規則的突變驗證（加一行違規 → `npm run lint` 紅）記入 `automation-test-plan.md`。
這個 lint 區塊同樣是修改共用設定檔，`code-generation` 須在 code-summary 揭露。

### N-04 — `F-01` 的「單一可行解」論證過強、404 成因寫錯（審查 `R-04`，Minor）

**更正**：
- 問題檔 §一第 5 點與 `security-requirements.md` §二末段的「單一可行解」改讀為：**兩支都可行**——第一支要改 `U23` 的 `objectCreateAction`（讓 404 可辨識），
  第二支以前端條件使路徑不可達；本站選第二支，理由是**成本與風險**（不重開唯一寫入路徑 `INV-2`），**不是**只有一解。這是可被推翻的選擇，列入關卡。
- `OPN-16` 的 404 成因更正為「**建立者在選單開啟後被移出專案**」：`owner_user_id === user.id` 仍成立（前端條件放行），但伺服器的可見性守門回 404
  （`hierarchy_router.py:250-252` 的註解逐字「不在請求者可見集合內的專案（含被移出的建立者）回 404」）。repo 內沒有「擁有權轉移」功能，原例子不存在。
- 此情境下 `other` 文案「建立系統失敗，請稍後再試」會**誘使重試一個永遠不會成功的動作**。本站判定**可接受但須揭露**：觸發條件是選單開著時恰好被移出，
  且下次開啟時該專案已不在清單（`list_visible_projects` 不再回它）；若使用者在關卡上認為不可接受，才是重開 `U23` 的理由。列為關卡事項 `G-6`。

### N-05 — 事實、範圍與比較基準（審查 `R-05`，Minor）

- `OPN-13` 括號內的「全 `frontend/src` 現況亦為 0」**刪除**：`frontend/src/utils/exportReviewPdf.ts:280` 有 `host.innerHTML = …`。我在問題檔階段用的 grep 只搜了
  `dangerouslySetInnerHTML\|new RegExp`，沒搜 `innerHTML` 本身，卻寫成涵蓋兩者的結論。零 `innerHTML` 不是全站慣例，是本單元的要求（由 `N-03` 的 lint 承載）。
- 靜態檢查範圍一律指上方「選單檔案集合」。
- `NFR5.160` 的「`ws-contract.json` 位元相同」與 `OPN-22` 的「`package.json` 鍵集合相同」，比較基準定為**本單元 code-generation 開始時的工作樹**
  （`code-generation` 在動工前記下 `git hash-object ws-contract.json` 與 `jq '.dependencies, .devDependencies | keys' frontend/package.json` 的值，完工時再取一次比對）。
  不以 `HEAD` 或 `ut` 為基準：兩檔目前都有其他單元的未提交變更。

### N-06 — 播報計次與 axe 掃描面（審查 `R-06`，Minor）

- **計次法**（`OPN-05`、`OPN-07`）：以 `page.addInitScript` 在頁面載入前掛一個 `MutationObserver`，觀察頁面 `LiveRegion` 與選單內播報區的 `characterData`／`childList`
  變化，把每次非空 `textContent` 推進 `window.__announcements`；斷言以該陣列的內容與長度判定「恰 1 次」與「只寫一處」。
- **axe 掃描點**（`OPN-07`）擴為**兩態**：`default`（群組展開、含停用的非擁有者群組）與「建立表單展開且顯示錯誤」。新掃描點必須以 `page.route` 樁化選單的全部
  `/api/hierarchy` 請求——`a11y.spec.ts:177-181` 的隔離層（`isolate()`）會中止任何未樁化的 `/api` 請求並使測試失敗。

### N-07 — 引用細節（審查 `R-07`，Minor）

- `OPN-21` 的「目前」比較對象是伺服器回推的 `WorkTargetPayload`（`ws-contract.d.ts:319` 起），不是 `:203`／`:214`（那兩行屬客戶端送出的 `SetWorkTargetPayload`）；兩者欄位型別皆為 `string | null`，結論不變。
- `OPN-21` 的「`tsc` 不一定擋得住」改寫為：數字與字串以 `===` 直接比較時 `tsc -b` 會報 TS2367 並擋下；**擋不住的是經 `any`、`unknown` 轉型或 `String()`／`Number()` 漏在其中一邊**
  （例如 `currentRowKey` 以字串拼出 `"p:7"` 與 `"p:" + id` 比較——型別都是 string，值卻因漏轉而不同）。e2e 斷言照舊。
- 問題檔 §一第 1 點的 `EstimateAdvicePanel.tsx:198`／`:258` 更正為 `new AbortController()` 在 `:199` 與 `:226`、`abort()` 在 `:198` 與 `:258`。

## 交關卡的事項（本站新增）

| # | 事項 | 來源 |
|---|---|---|
| G-6 | 「建立者在選單開啟後被移出」時，建立系統顯示「請稍後再試」會誘使無效重試；本站判可接受，若不接受須重開 `U23` 的 `objectCreateAction` | `N-04` |

（`G-1`–`G-5` 見 `functional-design/functional-spec-corrections.md`。）

## 本附錄改動的需求數

需求 id 集合不變（23 條：繼承 4、孤兒 19）；`OPN-01`、`OPN-04`、`OPN-06`、`OPN-24` 的內容被取代，`traceability.json` 的條目與父條判定不受影響。
