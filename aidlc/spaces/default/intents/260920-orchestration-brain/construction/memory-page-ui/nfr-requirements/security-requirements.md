# Security Requirements — `U15 memory-page-ui`

> 本單元**不持有任何授權判定**：記憶的可見範圍與刪除權全部由 `U8` 的
> `MemoryFacade` 承擔（`K-14` `authorization_responsibility` 逐字「前端不自行過濾」）。
> 本檔的要求因此分兩類：①不得讓畫面**削弱**伺服器的判定（例如前端快取繞過刪除）；
> ②不得讓畫面**冒充**授權（例如把 `canDelete` 當成存取控制）。
>
> **識別字**：可繼承 inception NFR 的用 `NFR<parent>.90+`；無法誠實繼承者以
> `SEC-U15-n` 宣告並寫明理由。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/memory-page-ui/functional-design/functional-spec.md` | §四之三（清單含他人的 `platform` 列）、§九之二（ADR-0006 四面向初判） |
| `construction/memory-page-ui/functional-design/rules.md` | `BR31.3`、`BR34.1`、`BR34.5`、`BR35.2`、`BR35.3` |
| `construction/memory-page-ui/functional-design/frontend-components.md` | §四之一、§十之二（不做本機快取） |
| `inception/requirements-analysis/requirements.md` | `NFR4`、`NFR7`、`NFR8` 原文 |
| `inception/contract-design/contract-summary.md` | `K-08`、`K-14` |
| 出貨程式 | `backend/services/memory_service.py:270-283`（`_visible_to`）、`memory_types.py:100`（`SCOPE_WIDENING_ROLES`）、`frontend/src/context/AuthContext.tsx`（token 存放） |

## 一、可繼承 inception NFR 的要求

| ID | 要求 | 可測不變量 | 父條與繼承理由 |
|---|---|---|---|
| `NFR4.90` | 記憶內容**不得**寫入任何瀏覽器儲存 | 本單元新增的檔案（`frontend/src/memory/**`、`MemoryPage.tsx`、`components/memory/**`）中 `localStorage`／`sessionStorage`／`IndexedDB` 三個識別字的命中數為 **0** | `NFR4` 逐字「一律放 Redis，**不得放行程記憶體**」——狀態的權威副本只能在伺服器。前端的同構對應是「不得放瀏覽器儲存」；與 `U24` 的 `NFR4.80` 同一形狀。**既有命中不算**：`AuthContext.tsx` 以 `sessionStorage` 存 token 是既有機制，不在本單元範圍 |
| `NFR7.90` | episodic 記憶內容**只存在於元件 state**，頁面卸載即釋放 | 同 `NFR4.90` 的掃描；另以 e2e 斷言離開 `/memory` 後回到該頁會**重新發出** 3 個 `GET`（證明沒有跨頁快取） | `NFR7` 逐字「episodic memory 為 by-user 的對話歷程，屬個人可識別的使用歷程，其靜態儲存與傳輸的加密要求須於設計階段明確」。本單元的明確答案是**不在用戶端產生靜態儲存**，故用戶端加密問題不成立；傳輸沿用既有 HTTPS（Cloudflare Tunnel）。**判定失效條件**：任何快取記憶內容的改動都使本條轉為需要用戶端加密設計 |
| `NFR7.91` | 刪除確認文案**必須**告知「此刪除會被記錄」 | e2e 斷言確認列的可見文字含「記錄」二字 | `NFR7` 逐字「刪除動作留稽核（FR4.7）」。稽核的**寫入**在 `U8`；本單元的責任是不讓一個留稽核的刪除以使用者察覺不到的方式發生（`BR34.1`）。稽核**查詢面**仍無使用者可見面（`OPEN-MP15-5`／回補項 `N-8`），如實記載 |
| `NFR8.90` | 零新環境變數 | `git diff` 顯示本單元未改動 `deploy/render-env.sh`、`deploy/.env.example`、`frontend/.env.example` | `NFR8` 的失敗模式逐字是「無 fallback 的變數缺值時只會變成空字串，服務照常啟動但功能降級」。本單元無設定項（每頁筆數是程式常數），故該失敗模式不可達——**結構性滿足**，非豁免 |

## 二、本單元自有的安全要求（`SEC-U15-n`，無 inception 父條）

| ID | 要求 | 可測不變量 | 來源與孤兒理由 |
|---|---|---|---|
| `SEC-U15-1` | 前端**不得**以 `owner_user_id`／`visibility_scope` 移除任何一列 | e2e 以路由攔截餵入一筆他人的 `platform` 列，斷言 `memory-item-{id}` 存在於 DOM | `BR31.3`；`K-14`。授權責任的落點規定，`NFR1`–`NFR11` 無對應條目 |
| `SEC-U15-2` | `canDelete` **不是**存取控制：伺服器對非擁有者的 `DELETE` 必須回 404，**與前端是否渲染刪除鍵無關** | 後端 `TestClient`：非擁有者對他人的 `platform` 列發 `DELETE` → 404，且該列仍存在。**此斷言的擁有者是 `U8`**；本單元的義務是在 code-generation 計畫中確認該測試存在，若不存在則記為交接缺口 | `BR35.2` 的 note；ADR-0006 IAM 面。寫成獨立要求，是為了防止下游把「移除 `canDelete`」誤讀為「開放刪除他人記憶」 |
| `SEC-U15-3` | 畫面**不提供**任何可見範圍的設定或放寬控件 | e2e 斷言頁面上無任何含 `scope` 的 `select`／`input`／`button`；本單元原始碼不呼叫 `PUT /api/memory/records/{id}/scope` | `BR35.3`；`memory_types.py:100` 的 `SCOPE_WIDENING_ROLES` 僅兩個平台角色。`OQ-12` 未定案 |
| `SEC-U15-4` | 擁有者欄位的**可見文字**不含他人的數值 id | e2e 對他人的列斷言 `-owner` 的 `innerText` 為「其他使用者」且不含任何數字；數值只出現在 `data-owner-user-id` 屬性 | `BR35.1` 的 note。他人的 user id 屬內部識別字，可見文字不需要它 |
| `SEC-U15-5` | `console` 輸出**不得**含記憶內容 | 本單元新增檔案中所有 `console.*` 呼叫的引數不含 `content`／`record` 變數（code review 可判）；e2e 以 `page.on('console')` 收集輸出並斷言不含種子記憶的內容字串 | 本 repo 為 public、Actions log 公開可讀，而 `ui-regression` 的 Playwright 輸出會進 log（`U24` 的 `BR28.1` 同一理由）。記憶內容屬 `NFR7` 所稱的個人可識別使用歷程 |

## 三、STRIDE（本單元的資料流：瀏覽器 ↔ `/api/memory/records`）

| 威脅 | 本單元的暴露 | 處置 | 落點 |
|---|---|---|---|
| **S** 冒用 | 以他人 token 讀取記憶 | 沿用既有 `Authorization: Bearer`；驗證在伺服器 | 既有機制，非本單元 |
| **T** 竄改 | 偽造 `memory_id` 刪除他人記憶 | 伺服器以擁有者判定，非擁有者 404 | `SEC-U15-2`（`U8` 擁有斷言） |
| **R** 否認 | 使用者否認刪除過某則 | `U8` 寫稽核；本單元以文案告知 | `NFR7.91` |
| **I** 資訊外洩 | ① 他人 `platform` 列出現在我的頁面；② 記憶內容留在瀏覽器或 log | ① **設計上的可見**，非外洩——放寬為 `platform` 是授權操作的結果（`functional-spec.md §四之三`）；② 不落地、不打 log | ① 已核可行為；② `NFR4.90`、`NFR7.90`、`SEC-U15-5` |
| **D** 阻斷服務 | 大量記憶使頁面卡頓 | 伺服器 `clamp_page_size` 上限 200；情節記憶每頁 20 | `UIP-2`、`UIP-5` |
| **E** 權限提升 | 經記憶頁放寬可見範圍 | 畫面無該控件；端點限兩個平台角色 | `SEC-U15-3` |

## 四、ADR-0006 security baseline 四面向（逐項，與上游判定逐字比對）

`functional-spec.md §九之二` 已逐項判定；本表**沿用其判定**，只補上本站新增的可測不變量。

| 面向 | 上游判定 | 本站判定 | 一致？ | 本站新增的可測落點 |
|---|---|---|---|---|
| IAM | 適用 | 適用 | 一致 | `SEC-U15-1`、`SEC-U15-2`、`SEC-U15-3` |
| Encryption | 不適用（無新增落點），附判定失效條件 | 不適用，附同一失效條件 | 一致 | `NFR4.90`、`NFR7.90` 把失效條件寫成可掃描的不變量 |
| Network exposure | 不適用（無新增落點） | 不適用 | 一致 | `NFR8.90`（零新設定即零新暴露面） |
| Audit logging | 適用（稽核查詢面為殘留缺口） | 適用 | 一致 | `NFR7.91`、`SEC-U15-5` |

### 四之一、帶進 code-generation 計畫的事項（交接表）

| 事項 | 來源 | 為何在這裡列 |
|---|---|---|
| `R-01`：刪除後以背景重抓目前頁修正 offset 漏列與誤判 `empty` | functional-design 審查；使用者裁決帶進 code-generation | `UIP-3` 的預算已容許此修法 |
| `R-02`：入口頁捷徑的承載（`U14` 在 B6 早於 `U15` 的 B7，無法匯入 `canSeeMemoryEntry`） | 同上 | INV-3 的單一判定若在 `U14` 落地時不存在，會出現第二份判定 |
| `R-03`：`/me` 失敗時 `user.id` 永遠 `undefined`，頁面無限轉圈 | functional-design 審查（次要） | 本站在處理 `R-01`／`R-02` 的同一交接表中一併列出，**這是本站的補充，非使用者裁決範圍**；code-generation 計畫核可時由使用者確認 |
| `SEC-U15-2` 的後端測試是否存在 | 本站 | 擁有者是 `U8`；本單元只確認 |
