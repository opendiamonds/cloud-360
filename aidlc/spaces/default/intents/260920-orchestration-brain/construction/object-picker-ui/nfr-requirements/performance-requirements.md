# Performance Requirements — `U16 object-picker-ui`

> 撰寫時間 2026-10-18T01:07:04Z（`date -u` 取值）。
>
> 單元類型 `ui`、無後端變更（`produces_kinds` 使本站只產出 performance／security／tech-stack／traceability 四份）。
> **識別字**：可繼承 inception NFR 者用 `NFR<父條>.160` 起（區段實查為空，見問題檔前言）；無法誠實繼承任何 inception NFR 者
> 以 `OPN-nn` 宣告為孤兒，並在 `traceability.json` 的 `reverse` 段逐條寫明理由。
>
> **綁定**：`functional-spec-corrections.md` 的 `F-02`、`F-03`、`F-05` 在本檔落地；衝突時以該附錄為準。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `functional-design/functional-spec.md` | §四（消費的四支 API 與 `setWorkTarget`）、§五 W1–W6、§六（兩個狀態機）、§八 `OPEN-OP16-7`（`NFR11` 情境） |
| `functional-design/rules.md` | `BR11.2`（不本地改脈絡列）、`BR12.1`／`BR12.4`（重抓、關閉丟棄）、`BR13.4`（搜尋不發請求）、`BR14.4`（擋重複觸發）、`BR15.*`（無障礙） |
| `functional-design/functional-spec-corrections.md` | `F-02`（斷線自動關閉，`BR11.5`）、`F-03`（身分未決）、`F-05`（系統清單延後抓） |
| `inception/requirements-analysis/requirements.md` | `NFR1`–`NFR11`（`:400`–`:585`）逐條判定 |
| repo 實測 | `projectsApi.ts:59-104`（抓取殼無 `AbortSignal`）、`objectCreateAction.ts:9-10`（非冪等、一次一請求）、`AuthContext.tsx:79-84`（`refreshMe` 失敗即拋、無 catch）、`brainSession.ts:56-57`（`setWorkTarget` 回 `boolean`） |

## 一、可繼承 inception NFR 的要求

| ID | 要求 | 目標 | 量測方式 | 父條與繼承理由 |
|---|---|---|---|---|
| `NFR2.160` | 由選單發出的切換**不在前端本地改寫脈絡列**；脈絡列只在伺服器回推 `work_target` 後更新（`BR11.2`） | 送出 `set_work_target` 之後、伺服器回推之前，脈絡列三個名稱與 `data-state` 不變；回推之後等於回推值；隨後切到另一個子頁面，三元組與回推值逐欄相同 | Playwright（`routeWebSocket`）：攔下客戶端送出的 `set_work_target` 但**延遲**回推，斷言期間脈絡列未變；回推後斷言更新；再導向 `/workspace` 斷言三元組相同 | `NFR2`（跨頁面上下文保留率，`requirements.md:430`）以「切換前後三元組逐欄相同」計分。若選單在本地先改脈絡列而伺服器拒絕（例如非擁有者被 `HierarchyNotFound` 拒，`functional-spec.md` §四之一），畫面與伺服器正本分歧，換頁後三元組改變，`NFR2` 的分子被一個前端捷徑污染 |
| `NFR11.160` | 在入口頁、`/workspace`、`/assessment` 三處完成「換作業對象」與「就地建立專案／系統並切過去」**不發生頁面切換** | 每處每情境 `pathname` 變更 **0** 次 | Playwright：記錄 `page.url()` 的 pathname 序列，三頁 × 兩情境（`OPEN-OP16-7`） | `NFR11`（跨功能任務的頁面切換次數須嚴格少於基準，`requirements.md:563`）。現行流程換對象或建專案要切到 `/projects`；本條是正向貢獻。把情境加進 `NFR11` 的母體是 `build-and-test` 的職權（`requirements.md:577-578`），本站只提供可量測面（同 `U14` 的 `NFR11.140`、`U23` 的 `NFR11.100` 處置） |

## 二、本單元自有的效能與資源要求（孤兒，無 inception 父條）

| ID | 要求 | 目標 | 量測方式 |
|---|---|---|---|
| **`OPN-01`**（`F-05`） | 每次開啟選單的請求數**有常數上界**，不隨專案數成長 | 開啟時 `GET /api/hierarchy/projects` 恰 **1** 次；`GET …/projects/{id}/systems` 只在**展開該群組**時發出，同一次開啟內每個專案至多 **1** 次；未展開任何群組時系統請求 **0** 次 | Playwright：`page.on('request')` 收集 `/api/hierarchy` 路徑；以 `page.route` 回 1 個與 30 個專案兩組資料，斷言開啟後請求數皆為 1；展開一個群組後為 2；收起再展開仍為 2 |
| **`OPN-02`**（`BR12.4`） | 選單關閉後**不再發出**新請求，在途結果**不寫入任何 state** | 關閉後 `/api/hierarchy` 新請求 **0** 次；被丟棄的晚到回應**永不出現在畫面上**；再開啟時重新發出 1 次專案請求，畫面只呈現新回應 | Playwright：第一次專案請求延遲 2 秒並回「舊名稱」，開啟後立即關閉、立刻再開啟，第二次請求即時回「新名稱」；斷言關閉期間無新請求、3 秒後清單只有「新名稱」且「舊名稱」從未可見。（不以主控台警告判定：React 19 已移除卸載後更新的警告，那會是恆真斷言。）抓取殼無 `AbortSignal`（`projectsApi.ts:59-82`），故以丟棄而非中止達成（`tech-stack-decisions.md` 的 `OPN-24`） |
| **`OPN-03`**（`BR14.4`） | 一次送出**恰一個**建立請求 | 對送出鈕連點 3 次、或按 Enter 後立刻再點送出：`POST /api/hierarchy/projects`（或 `…/systems`）恰 **1** 次 | Playwright：`page.route` 延遲 POST 回應 1 秒並計數。依據：`objectCreateAction.ts:9-10` 逐字「非冪等，一次呼叫恰發一次請求，不自動重試」，擋重複觸發是呼叫端的責任 |
| **`OPN-04`**（`F-03`） | 身分未決**不得無限載入** | 開啟時 `user.id` 不是數字 → 呼叫 `refreshMe()` **至多 1 次**；其結果仍非數字或該呼叫拋錯 → 轉 `error` 態（文案「無法確認你的身分，請重新整理頁面」＋ 重試鈕）；重試鈕每按一次再呼叫 1 次 | Playwright：`page.route('/api/auth/me')` 先回 500（使 `user.id` 缺漏）再開啟選單，斷言 `/api/auth/me` 只多 1 次請求、錯誤文案出現、不再發請求。`refreshMe` 失敗會拋（`AuthContext.tsx:79-84` 無 catch），呼叫端必須接住 |
| **`OPN-05`**（`F-02`） | 連線離開 `ready` 時**選單在同一次狀態更新內關閉** | `status` 由 `ready` 轉其他值後，dialog 不存在；焦點在 `ContextBar` 容器；頁面 `LiveRegion` 出現「連線中斷，已關閉作業對象選單」恰 **1** 次；之後客戶端送出的 `set_work_target` **0** 則 | Playwright（`routeWebSocket`）：開啟選單後由伺服器端關閉連線（1011），斷言上述四點 |
| **`OPN-06`**（`BR13.4`） | 搜尋**不發請求** | 在搜尋框輸入 10 個字元：`/api/` 新請求 **0** 次 | Playwright：`page.on('request')` 計數 |
| **`OPN-07`**（`BR15.*`、`F-04`） | 無障礙的可量測面，且**開啟中的選單納入 axe 掃描** | 開啟時焦點在搜尋框；Tab／Shift+Tab 在選單內循環；Escape 關閉後焦點回「切換對象」鈕；每個播報事件只寫入一處播報區（開啟中＝選單內、關閉後＝頁面 `LiveRegion`）；開啟中的選單以 WCAG 2.1 AA 規則掃描**零違規**、不新增基準清單項目 | Playwright 鍵盤序列；axe 掃描以 `U17` 的資料驅動掃描清單新增一個掃描點（`a11y.spec.ts:38` 的 `WCAG_TAGS`、`:711` 的 `scan()`）。現況實查：`U17` 的掃描面**不含**選單（`grep -nE "ObjectPicker\|object-picker\|切換對象\|brain-object"` 對 `a11y-gate/` 與 `a11y.spec.ts` 零命中）——不補即無人掃描 |

## 三、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 清單載入的毫秒目標 | 選單的延遲由 `/api/hierarchy` 決定，本單元不改後端；以請求數上界（`OPN-01`）擋住會隨資料量變慢的那一類真實失敗 |
| HTTP 逾時 | 問題檔 §一第 1 點 |
| 清單快取 | 問題檔 §一第 2 點 |
| 虛擬捲動、筆數上限 | 問題檔 §一第 3 點 |
| 搜尋防抖 | 問題檔 §一第 4 點 |
| 扇出並行上限 | `F-05` 之後系統清單由使用者逐一展開觸發，沒有扇出；`U23` 的 `fanoutQueue` 不再適用（`tech-stack-decisions.md` 的 `OPN-24`） |
