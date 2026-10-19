# 更正附錄 — `a11y-gate` 的 Security Requirements

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: a11y-gate · 寫於 2026-10-17T14:56:14Z -->

## 這份附錄是什麼、為什麼存在

`security-requirements.md` 送審後（`reviews/review-01.md`，NOT-READY，4 Major ＋ 4 Minor），審查收據一記下，該檔就被凍結、不能再改。正規的補救是重開本站，但在單元並行的建構期裡，跳站會讓**所有單元**的審查與完成紀錄判為過期（`aidlc-lib.ts:11803` 起的註解：跳站的 attempt floor 刻意不分 stage）。使用者因此選了這條路：**原檔不動，在旁邊寫一份逐條取代的更正附錄，並由 `code-generation` 的計畫明文綁定它**。

**讀法規則（不可違反）**：

1. 本附錄與 `security-requirements.md` 衝突時，**以本附錄為準**。
2. `code-generation` 的計畫必須在「帶入項」中逐條列出本附錄的 `C-01`–`C-08`，並在 Testing Contract 中落實其中可驗證的條件。計畫未引用本附錄者，視為未讀完上游。
3. 本附錄**未經審查**。它是對審查發現的處置，不是審查通過的證明。`code-generation` 的審查員應把它納入審查範圍。

## 逐條更正

### C-01 — 取代 `A11Y-S5` 的可驗證條件（審查 `R-01`，Major）

**原文的問題**：`page.on('request')` 對經 `route.fulfill` 處理的請求同樣觸發，分不出攔截與否；且既有 spec 都先放 `**/api/**` 兜底（`entry-page.spec.ts:200`、`member-pages.spec.ts:176-184`），「未被攔截的數量為 0」不是恆成立就是沒有定義。更嚴重的是原文只談 HTTP：入口頁會開 `/api/brain/ws` 與 `/api/collab/ws/**` 兩條 WebSocket（`entry-page.spec.ts:58`、`:256` 以 `routeWebSocket` 接管），而 `playwright.config.ts` 的 `BASE_URL` 指向真實 nginx stack——漏接 WebSocket 就會連到真實大腦閘道，正是 `A11Y-S5` 要防的事。

**取代為**：

- **HTTP**：兜底 handler（`**/api/**`）本身就是偵測器。它**不得**回一個看起來正常的值（例如 `200 []`）；必須以帶特徵的方式處理（例如 `route.abort()`，或回應中帶固定標記），並把每次命中記入一個陣列。每個掃描 `test()` 結束前斷言該陣列為空。具體端點的 handler 一律註冊在兜底**之後**（Playwright 以後註冊者優先）。
- **WebSocket**：每個掃描點都必須以 `page.routeWebSocket` 接管 `/api/brain/ws` 與 `/api/collab/ws/**`；並以 `page.on('websocket')` 記錄所有 WebSocket 的 URL，斷言每一條都落在已接管的兩個樣式內。
- **突變驗證**（交 `code-generation`）：拿掉某一個具體端點的 handler，測試必須紅；拿掉 `/api/brain/ws` 的 `routeWebSocket`，測試必須紅。

### C-02 — 取代 `A11Y-S7` 的可驗證條件（審查 `R-02`，Major）

**原文的問題**：後半條件 `results.passes.length > 0` 恆成立——axe 對任何文件（含 `/login`、`/403` 的空殼）都會回非空的 `passes`。它被寫成「不得在沒掃到東西時通過」的一半機制，會讓人以為有第二道防線。前半「test-id 可見」才是真正承重的，但沒要求載入態已結束，各掃描點的視角專屬 test-id 也沒有命名。

**取代為**：

- 刪除 `results.passes.length > 0`，不以任何 axe 結果欄位當作「有掃到」的證據。
- 每個掃描點在 `analyze()` 之前必須同時滿足下表的**就緒斷言**（可見）與**排除斷言**（數量為 0）。test-id 為 2026-10-17 實讀 `frontend/src` 所得；`code-generation` 實作時若發現名稱已變，以程式為準並在 `code-summary.md` 記下差異。

| # | 掃描點 | 就緒斷言（須可見） | 排除斷言（須為 0 或不可見） |
|---|---|---|---|
| 1 | 入口頁 | `brain-entry-page` | 登入表單、`/403` 頁 |
| 2 | `/memory` | `memory-page` 且至少一個 `memory-zone-*` | `memory-page-identity-error` |
| 3 | 專案清單 | `projects-list-page` ＋ `project-list` | `project-list-skeleton`、`project-list-error` |
| 4–6 | 專案詳情三籤 | `project-detail-page` ＋ 該籤 `project-tab-<key>` 為選取狀態 ＋ 該籤面板內的一個內容 test-id（總覽：`project-count-systems`；需求：至少一個 `requirements-group-*` 或 `requirements-empty`；記憶摘要：該籤的內容節點，`code-generation` 指定） | `project-detail-error`、`project-not-found`、詳情頁的載入態 |
| 7 | 專案建立頁 | `project-create-page` ＋ `project-create-name` | `project-create-error` |
| 8 | 成員清單 admin-view | `members-list-page` ＋ `member-list-table` ＋ `member-list-invite-button` | 「載入中…」文字、`member-list-error` |
| 9 | 成員清單 member-view | `members-list-page` ＋ `member-list-table` | `member-list-invite-button`（這一條就是視角的證據：admin-view 掃成 member-view 時它會出現）、「載入中…」、`member-list-error` |
| 10 | 成員詳情頁 | `member-detail-page` ＋ `member-detail-role-select` | `member-detail-error` |
| 11 | 邀請對話框 default | `invite-dialog` ＋ `invite-dialog-user-id` | `invite-dialog-rejection-reason` |
| 12 | 邀請對話框 denied | `invite-dialog` ＋ `invite-dialog-rejection-reason` | — |
| 13 | 改選橫幅 single | `reselection-banner-host` ＋ `reselection-banner-acknowledge` | `reselection-banner-projects` 展開清單 |
| 14 | 改選橫幅 multi-expanded | `reselection-banner-host` ＋ `reselection-banner-projects` 已展開（`reselection-banner-expand` 的 `aria-expanded="true"`） | — |
| 15 | 移出確認對話框（見 C-04 新增） | `remove-confirm-dialog` | — |
| 16 | 專案清單空狀態（見 C-04 新增） | `project-list-empty` ＋ `project-list-empty-create` | `project-list`、`project-list-error` |
| 17 | 專案清單錯誤態（見 C-04 新增） | `project-list-error` | `project-list-skeleton` |

- **突變驗證**（交 `code-generation`）：把攔截的 `/me` 改成無權限，使頁面導向 `/403`，測試必須在就緒斷言處紅，而不是掃完空頁後綠。

### C-03 — 補強 `A11Y-S9` 基準清單（審查 `R-03`，Major）

**原文的問題**：四條規則只以選擇器位置判斷，擋不住「新元件造成、但 axe 回報在頁殼容器上」的違規——例如 `landmark-unique`（新頁面多了一個同名 landmark）、`heading-order`（新頁面的標題跳級）、`region`（新內容沒落在 landmark 內）、`duplicate-id`。這類違規的回報節點是既有的 `<nav>`／`<main>`，選擇器在頁殼內，會被當成頁殼既存而合法收進清單——與「新元件的違規不得列入基準」直接矛盾。另有三個執行面缺口。

**補強為**（原四條仍有效，以下為追加）：

- **規則 5 — 交界類規則不得進基準**：規則 id 屬於跨元件結構類者（至少 `landmark-unique`、`landmark-no-duplicate-banner`、`landmark-no-duplicate-main`、`landmark-one-main`、`region`、`heading-order`、`page-has-heading-one`、`duplicate-id-aria`、`list`、`listitem`），**一律不得列入基準**，不論回報節點在哪。第一次實跑若出現這類違規，`code-generation` 逐筆判定歸屬：屬本 intent 造成者修掉；確屬既有頁殼且與本 intent 無關者，停下來回報，不得自行收進清單。
- **規則 5 的一個重要限制（寫附錄時自查發現，審查未提）**：上列規則中，`landmark-*`、`region`、`heading-order`、`page-has-heading-one` 在 axe 的分類裡屬 **`best-practice`** 標籤，不屬 `wcag2a`／`wcag2aa`／`wcag21a`／`wcag21aa`。`A11Y-S8` 把規則集限定為 WCAG 2.1 AA，所以**這幾條根本不會執行**——規則 5 對它們是空轉，而它們要防的交界問題（重複 landmark、標題跳級）**閘門抓不到**。處置：不擴大規則集（那會讓閘門標準悄悄高於已核可的 AA，正是 `A11Y-S8` 要防的事），改把「landmark 唯一、標題不跳級」列入 `build-and-test` 的人工項目（加進 `security-requirements.md` 交接 H-3 的清單）。`code-generation` 選定 axe 版本後，以該版本的規則標籤實查本段的分類，與此不符時以實查為準並記入 `code-summary.md`。
- **規則 1 的根節點清單**：「本 intent 新元件的根節點」明定為下列 test-id 所在的元素：`brain-entry-page`、`memory-page`、`projects-list-page`、`project-create-page`、`project-detail-page`、`members-list-page`、`member-detail-page`、`invite-dialog`、`remove-confirm-dialog`、`reselection-banner-host`；以及 `Sidebar.tsx` 的三個新增 `<nav>`（`aria-label="入口"`、`aria-label="專案"`，以及「我的記憶」所在的那一個，`code-generation` 依實際 DOM 補上可定位的屬性）。基準條目的節點若是上述任一者或其子孫，測試失敗。
- **鍵與選擇器**：基準鍵改為「規則 id ＋ 穩定選擇器」，**不含掃描點**——同一個頁殼違規在多個掃描點出現時只列一筆。穩定選擇器優先使用 `id`、`data-testid`、`aria-label` 或 role 路徑；**不得使用 axe 產生的 `nth-child` 型選擇器**（`Sidebar` 新增三項後這類選擇器會整批位移，使規則 2 在無關變更時誤紅）。
- **規則 2 與重試**：`playwright.config.ts` 設 `retries: 1`。過期判定以**該 `test()` 最後一次嘗試**的掃描結果為準；某筆條目只在部分掃描點出現是正常的（它本來就跨掃描點共用），過期判定為「**所有**掃描點都沒有出現」。

### C-04 — 補上 `K-19`／`K-20` 其餘義務的處置（審查 `R-04`，Major）

**原文的問題**：原文以「契約有一端懸空」為由補入建立頁與成員詳情頁，卻沒有對 `K-19`／`K-20` 的 `required_accessible_behaviour` 與其他狀態套用同一把尺。

**處置表**（每一條都要有承接者）：

| 契約要求 | 處置 | 承接者 |
|---|---|---|
| `K-19`：未填欄位以文字標示（`AC11.2.1`，即 `FR11.2`） | 已有 e2e 斷言；axe 只能判「有無 describedby」 | `U23` 既有 e2e（`requirements-unfilled-*`）＋ 本單元掃描點 5（需求籤）順帶涵蓋結構面 |
| `K-19`：載入態、錯誤態須有 live region | **增列掃描點 17（專案清單錯誤態）**；載入態是過渡狀態，掃描時機不穩，不增列，交人工 | 本單元（錯誤態）／`build-and-test` 人工（載入態） |
| `K-19`：首次使用為空狀態而非空表（`AC11.1.2`） | **增列掃描點 16（空狀態）**；行為本身已由 `project-pages.spec.ts:479-481` 斷言 | 本單元（無障礙面）／`U23`（行為面） |
| `K-19`：儲存失敗輸入值不消失（`AC11.2.3`） | 行為斷言，非無障礙掃描對象 | `U23` 既有 e2e |
| `K-20`：橫幅落地即在 DOM 或 `role="status"` | 掃描點 13–14 ＋ 見 C-06 | 本單元 |
| `K-20`：成員清單無改角色控件（`AC12.2.3`，清單的 O-14） | **已由 `member-pages.spec.ts:466-479` 以 `toHaveCount(0)` 逐一斷言**（清單與詳情兩處） | `U24` 既有 e2e，本單元不重複 |
| `K-20`：移出專案二次確認對話框（線框 §25） | **增列掃描點 15** | 本單元 |
| `K-20`：邀請對話框拒絕態 | 掃描點 12 | 本單元 |
| `K-20`：載入／錯誤態 live region 同 `K-19` | 成員清單錯誤態 `member-list-error` 已有 e2e（`member-pages.spec.ts:541`）；無障礙面交人工 | `build-and-test` 人工 |

**掃描次數由 14 增為 17**（`A11Y-S10` 的「14」以本附錄為準）。`security-requirements.md` 的交接 H-2（`ui-regression` 時間預算）同步以 17 次計。

### C-05 — 更正「需求 ID 的來源」的兩句陳述（審查 `R-05`，Minor）

- 原文「`requirements.md` 全文 `WCAG`／`無障礙` 命中數為 0」只在區分大小寫時成立。`requirements.md:260` 的 `FR11.2` 帶 `[accessibility-wcag]` 來源標籤——它是**功能需求**，結論「找不到誠實的上游 NFR」仍成立，且 `FR11.2` 已由 C-04 第一列承接。
- 原文的 `[R7]` 是 **`rough-mockups` 的問題 R7**（WCAG 2.1 AA），與 `requirements.md:502` 的 `[RA:R7]`（Redis 狀態外部化）是不同 stage 的同號標籤，不得混讀。

### C-06 — 補上 `AC-A11Y.2` 的處置（審查 `R-06`，Minor）

`stories.md:653` 的 `AC-A11Y.2`（手機寬度下入口頁無橫向捲動）原文未處置：axe 不檢查橫向溢出，`playwright.config.ts` 只有 Desktop Chrome 一個 project。**處置**：本單元在 `a11y.spec.ts` 加一個 `test()`，以 `page.setViewportSize({ width: 375, height: 812 })` 開入口頁，斷言 `document.documentElement.scrollWidth <= document.documentElement.clientWidth`。它不是 axe 掃描，但與本單元同屬無障礙閘門、同樣擋 PR。`AC-A11Y.1`（純鍵盤完成）維持交 `build-and-test` 人工。

### C-07 — 改選橫幅的最低義務（審查 `R-07`，Minor）

原文「以落地頁為入口頁的視角」語意含糊，且把 `K-20` 最在意的情境（非入口頁的落地頁）推給 `code-generation` 自行決定。**取代為**：

- 掃描點 13–14 的可實作步驟：攔截的 `/me` 帶 `C1 view`（使 `DefaultRedirect` 落在入口頁 `/`），攔截改選事件端點回一筆（13）或多筆並點開展開控件（14）。
- **最低義務（新增）**：另加一個掃描，攔截的 `/me` **不帶** `C1 view`、使落地頁為非入口頁，以 `AxeBuilder.include('[data-testid="reselection-banner-host"]')` 限縮到橫幅節點掃描，受 C-02 的就緒斷言與 C-03 的基準規則約束。橫幅掛在 `Layout.tsx`（實讀確認），所以它在任何落地頁上都存在，限縮掃描不會掃進既有頁面的其他部分。**掃描次數因此為 18。**

### C-08 — 更正 tech-stack 的計數並明定 test 粒度（審查 `R-08`，Minor）

- `tech-stack-decisions.md` T-2 引 codekb「19 個 devDependencies」有誤：`frontend/package.json` 實為 **18** 個（codekb 該節標題寫 19，但同節列出的也只有 18 項——是 codekb 的計數錯誤）。「唯一精確 pin 是 `openapi-typescript 7.13.0`」屬實。
- T-3 補：**每個掃描點一個 `test()`**。`playwright.config.ts` 的單一 test 逾時為 30 秒，把多次掃描串在一個 test 裡有逾時風險，也會讓 TCMS 以 `<describe> › <test>` 逐案記錄的理由（T-3 第 1 點）失效。

## 更正後的總數

掃描 `test()` 18 個（C-04 與 C-07 之後）＋ 手機寬度 `test()` 1 個（C-06）＝ **`a11y.spec.ts` 共 19 個 `test()`**。
