# Performance Requirements — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T02:11:18Z（`date -u` 取值）。
>
> 單元類型 `ui`（`produces_kinds` 使本站只產出 performance／security／tech-stack／traceability 四份）。
> **識別字**：可繼承 inception NFR 者用 `NFR<父條>.140` 起（`.140` 區段實查為空，見問題檔前言）；無法誠實繼承任何 inception NFR 者
> 以 `EPN-nn` 宣告為孤兒，並在 `traceability.json` 的 `reverse` 段逐條寫明理由。`EPN-nn` 是需求，`EPN1` 是問題。
>
> **`EPN1`=A 已定案**（2026-10-17T03:08:46Z 經選單作答，`nfr-requirements-questions.md:83`）：`EPN-04` 為定案需求（每段最多 500 則）。
> `[EP4]` 選項 A 原文的「對話都在」（`functional-design-questions.md:147`）由 `EPN1`=A 改讀為「最近 500 則都在」（有上限）；設計檔不回改。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `functional-design/functional-spec.md` | §二之一（C-8 的 `_names_for` 與四個呼叫點）、§五 W2／W7／W10、§六之一（連線狀態機） |
| `functional-design/rules.md` | `BR92.1`（每頁一條連線）、`BR92.5`（關閉碼與退避）、`BR93.1`（不緩衝）、`BR93.4`（記憶體 store）、`BR93.7`（turnId 合併）、`BR96.3`（不自動導航）、`BR98.3`（無障礙）、`BR98.5`（零 HTTP） |
| `carried-review-items.md` | R-01（名稱查詢多一道可見性判定）、R-02（未儲存畫布不自動開圖） |
| `inception/requirements-analysis/requirements.md` | `NFR1`–`NFR11`（`:400`–`:585`）逐條判定 |
| `inception/contract-design/contract-summary.md` | `x-concurrent-connections`（`:910` 起）：三處各一條連線、同 key 允許多條並存 |
| repo 實測 | `brain_gateway_rules.py:69-79`（連線、訊框、速率上限）、`brain_gateway.py:1043-1044`／`:1100`（首字計時）、`:1287`／`:1292`（交辦關鍵路徑）、`membership_service.py:367-379`（可見性判定為一條 SQL）、`redis_gateway.py:103`（session 24 小時） |

## 一、可繼承 inception NFR 的要求

| ID | 要求 | 目標 | 量測方式 | 父條與繼承理由 |
|---|---|---|---|---|
| `NFR2.140` | 脈絡列以可機械比對的形式暴露作業對象三元組，供 `NFR2` 的比率測試逐欄比較 | 三個名稱與三個識別碼各有穩定的 `brain-*` testid 或 `data-*` 屬性；`no-object` 與 `unavailable` 兩態可與 `default` 區分 | Playwright：在三頁各讀一次三元組，比對逐欄相同；`NFR2` 的比率本身由 `build-and-test` 計算 | `NFR2`（跨頁面上下文保留率，`requirements.md:430`）：母體逐字為入口頁、`/workspace`、`/assessment` 三處——正是本單元擁有的三個掛載點。本單元不計分，只提供可量測面 |
| `NFR2.141` | 子頁面就緒後的首次對齊**不受快照與 bootstrap 先後影響** | 快照先到、後到兩案的最終三元組相同 | Playwright（`routeWebSocket` 控制送出時機）兩案（`BR97.5`） | `NFR2`：若對齊是時序賭局，比率測試的結果會隨網路抖動而變，`NFR2` 失去可重現性 |
| `NFR3.140` | 前端收到內容 token **即呈現**，不緩衝到 `done` | 送出第一個 `token` 訊框後、送出 `done` 之前，畫面已出現該文字 | Playwright（`routeWebSocket`）：送 token 後**不送 done**，斷言文字可見（`expect(...).toBeVisible()` 預設逾時內） | `NFR3`（首字回應 P50 ≤ 2 秒，`requirements.md:482`）：伺服器端量的是到 WS 第一個內容 token（`brain_gateway.py:1043-1044`）；前端緩衝會使使用者感受到的首字時間＝完整回覆時間，而伺服器數字仍然好看 |
| `NFR3.141` | C-8 在交辦關鍵路徑上新增的名稱查詢**成本為常數** | 見 `EPN-06` 的語句數上界；不呼叫任何 LLM、不發任何對外 HTTP | `TestClient`／假 facade：以 SQLAlchemy 事件計數（`tech-stack-decisions.md` 的 `EPN-23`） | `NFR3`：`_set_target_confirmed`（`brain_gateway.py:1301`）在 `_dispatch` 之前（`:1292`），位於分類結束之後、第一個內容產生之前，其耗時直接計入 `toFirstContentMs`（`:1100`，`t_classify_end` → `t_first_content`），吃首字預算 |
| `NFR4.140` | 重連後畫面上的作業對象與工作項**一律以伺服器推送覆蓋**，前端不保留第二份正本 | 後端重啟、頁面未重新整理：重連成功後脈絡列與常駐區等於伺服器推送值；本地對話紀錄保留 | 自動化主檔為 `routeWebSocket` 版：以 1011 關閉、重連、第二次 ready 後推送與本地不同的值，斷言畫面被覆蓋且對話紀錄保留。真實 backend 重啟（`AC2.1.4`）在 e2e 內無法由 Playwright 觸發，交 `tcms-test-cases` 分桶（只能手動或部署後實測） | `NFR4`（狀態外部化與重啟還原，`requirements.md:500`）：正本在 Redis；前端若以本地狀態優先，重啟還原在畫面上不成立 |
| `NFR11.140` | 在入口頁完成一次交辦（含成本問答）全程**不發生頁面切換** | `pathname` 變更 **0** 次 | Playwright：記錄 `page.url()` 的 pathname 序列（`BR96.3`） | `NFR11`（跨功能任務的頁面切換次數須嚴格少於基準，`requirements.md:563`）。本條是正向貢獻，不在其母體內；把情境加進母體不屬本站職權（同 `U23` 的 `NFR11.100` 處置） |

## 二、本單元自有的效能與資源要求（孤兒，無 inception 父條）

| ID | 要求 | 目標 | 量測方式 |
|---|---|---|---|
| **`EPN-01`** | **每頁至多一條大腦連線**（`BR92.1`）；頁面卸載即關閉 | 穩態下每分頁 `readyState` 為 OPEN 的大腦連線 **≤ 1**；換頁後舊頁連線在新頁連線 open 之前或同時進入 CLOSING／CLOSED；開發模式 `StrictMode`（`frontend/src/main.tsx:7`）的雙重 effect 不留下殭屍連線 | Playwright：`page.on('websocket')` 記錄每條連線的 open／close，在三頁間切換 5 次後斷言未關閉者恰 1 條。上限依據：`U13` 每 key 10 條（`brain_gateway_rules.py:70`），每分頁 1 條使同一使用者可開 10 個分頁 |
| **`EPN-02`** | 退避重連**加抖動且只往下抖** | 第 n 次等待 ＝ `BR92.5` 排程值 × 亂數 ∈ [0.8, 1.0]；單次 ≤ 15 秒；以**累計經過時間** ≥ 60 秒（非次數）為放棄判準；放棄後自動嘗試 **0** 次，只由「重新連線」按鈕觸發 | Playwright：`routeWebSocket` 全部拒絕握手，以 `page.clock` 快轉，斷言每次間隔落在 [0.8×, 1.0×] 排程值內、首次失敗後 60 秒內不出現「無法連線到大腦」、之後不再有新連線。理由：同一使用者的多分頁在後端重啟時同秒重連，`U13` 每 key 每分鐘 30 次握手（`brain_gateway_rules.py:79`） |
| **`EPN-03`** | 終止性關閉碼**不重連** | 收到 4401、4403、4400（含 `ready` 版本不符）後，自動發起的新連線 **0** 條 | Playwright（`routeWebSocket`）：三個關閉碼各一案，等待 20 秒（快轉）後新連線計數為 0 |
| **`EPN-04`**（`EPN1`=A） | 對話紀錄**每段最多 500 則**，超過時移除最舊者並在該段頂端顯示「較早的對話已不在畫面上」 | 每段陣列長度 ≤ 500；被移除的訊息其 turnId 對照同時移除（`EPN-05`） | Playwright（`routeWebSocket`）：灌入 501 則，斷言第 1 則不可見、說明出現、第 2–501 則可見 |
| **`EPN-05`** | turnId 對照（`BR93.7`）與訊息**同生同死** | 對照表的鍵集合 ⊆ store 內現存訊息的 turnId 集合（任何時刻）；登出清空時兩者一起清空 | 由 `EPN-04` 的 e2e 附帶斷言：被移除那一輪再收到 `token` 時**另建**一則而非寫進不存在的位置（不得拋例外、不得畫面崩潰）；前端無 unit 框架，故以可觀察行為驗證 |
| **`EPN-06`** | 名稱查詢（C-8 的 `_names_for`）的資料庫成本**為常數上界**，不隨專案、系統、圖的數量成長 | 每次推送：**1 次** `asyncio.to_thread`、**1 個** DB session；每組去重後的三元組 SQL 語句數 **≤ 4**（R-01 的可見性判定 1 條，`membership_service.py:368` 逐字「一條 SQL」；三層名稱各至多 1 次主鍵查詢）；握手快照至多 3 組 → **≤ 12**；扇出點每次 1 組 → **≤ 4**。合併成較少語句者亦符合 | `unittest`：以 SQLAlchemy `before_cursor_execute` 事件計數（`EPN-23`），分別在 1 個與 50 個專案的資料下斷言語句數相同 |
| **`EPN-07`** | 名稱查詢**失敗不阻斷**握手、扇出與交辦 | 任何例外 → 該組三名稱 null、記一筆 `work_target_names_failed`；握手不 1011、扇出照常、`_dispatch` 照常 | `unittest`：假 facade 拋 `HierarchyForbidden` 與一般例外各一案（`functional-spec.md` §二之一第 8 點的握手案之外，補扇出點一案）。**不設逾時**，理由見問題檔 §一第 2 點 |
| **`EPN-08`** | 本單元新增的前端程式**零 HTTP 請求**（`BR98.5`） | 入口頁從掛載到完成一次交辦，`/api/` 請求集合與本單元上線前相同（只有既有的 `/api/auth/me` 等）；子頁面新增的掛點不使既有頁面的 HTTP 請求數增加 | Playwright：`page.on('request')` 收集 `/api/` 路徑，入口頁斷言集合不含本單元新路徑；子頁面比對掛載面板前後的請求數相等 |
| **`EPN-09`** | 無障礙的可量測面（`BR98.3`；掃描本身屬 `U17`） | 串流中該則 `aria-busy=true`、完成時寫入既有 `LiveRegion` **恰 1 次**；`prefers-reduced-motion: reduce` 時游標無動畫 | Playwright：`page.emulateMedia({ reducedMotion: 'reduce' })` 後斷言游標元素的 `animation-name` 為 `none`；LiveRegion 內容在 done 前為空、done 後為該則全文 |

## 三、`EPN-06` 的推導（為什麼是 4 與 12）

- 可見性判定：`R-01` 裁決要求名稱查詢套用 `U23` 的判準；非測試程式唯一合法來源是 `MembershipFacade.project_visibility`
  （`membership_facade.py:518-532`），其內部 `is_project_visible` 為**一條 SQL**（`membership_service.py:367-379`，docstring 逐字）。
  一組三元組只有一個所屬專案，故 1 條。
- 三層名稱：`functional-spec.md` §二之一第 2 點逐字「每個非 null 的識別碼各**一次主鍵查詢**」，至多 3 條。
- 快照：至多 3 段（shared、workspace、assessment），去重後通常 1 組；上界 3 × 4 ＝ 12。
- 不得出現的形狀：以 `list_projects`／`list_systems`／`list_diagrams_of_system` 全量列舉再過濾（`functional-spec.md` §二之一第 2 點已排除），
  或在迴圈內逐專案呼叫可見性判定——兩者都使語句數隨資料量成長，正是 `EPN-06` 以「1 個與 50 個專案語句數相同」要擋的。

## 四、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 前端首字毫秒目標 | 伺服器已量 `toFirstContentMs`；前端以「不緩衝」的二元判準約束（`NFR3.140`），一個量不到的毫秒數擋不住任何真實失敗 |
| 名稱查詢逾時 | 問題檔 §一第 2 點 |
| 心跳／ping | `U13` 每 60 秒重驗身分（`brain_gateway.py:98` 的 `REVALIDATE_INTERVAL_SEC`），伺服器側已有存活判定；前端心跳會增加訊框而撞上每連線每分鐘 120 訊框的上限（`brain_gateway_rules.py:76`） |
| 分頁隱藏時暫停連線 | 背景完成的推播（`BR93.5`，`AC10.1.4`）需要連線存活；暫停會使推播落空 |
| 對話紀錄的位元組上限 | 問題檔 §一第 4 點 |
