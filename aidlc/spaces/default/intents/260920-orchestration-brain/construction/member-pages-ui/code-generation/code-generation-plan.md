# Code Generation Plan — `U24 member-pages-ui`

> 單元類型 `ui`。本單元**零新端點、零新持久層、零新環境變數、零新依賴**；
> 全部驗證落在 Playwright e2e（前端無 unit／component 測試框架，`TS-U24-2`）。
>
> 方法論由下方 **Testing Contract** 決定：**`test-after`**——
> 逐層實作後再寫並執行該層的測試。本計畫的步驟順序即照此排列，
> 並**省略本單元不適用的層**（data model／repository／API endpoint 皆屬 `U19`），
> 不改動方法論本身。

## 一、本單元要交付什麼

| # | 交付物 | 落點（workspace，非 record） |
|---|---|---|
| 1 | `<LiveRegion />` 共用元件 | `frontend/src/components/LiveRegion.tsx`（**新建**） |
| 2 | 成員域抓取函式層 | `frontend/src/membership/membershipApi.ts`（新建） |
| 3 | 失敗訊號型別 | `frontend/src/membership/failureSignal.ts`（新建） |
| 4 | 成員清單頁 | `frontend/src/pages/MembersListPage.tsx`（新建） |
| 5 | 成員詳情頁 | `frontend/src/pages/MemberDetailPage.tsx`（新建） |
| 6 | 邀請對話框 | `frontend/src/components/membership/InviteMemberDialog.tsx`（新建） |
| 7 | 交棒橫幅（宿主＋操作列） | `frontend/src/components/membership/ReselectionBanner.tsx`（新建） |
| 8 | `Layout` 掛載點 | `frontend/src/components/Layout.tsx`（**既有檔，就地修改**） |
| 9 | 路由與導覽 | `frontend/src/App.tsx`、`frontend/src/components/Sidebar.tsx`（既有檔，就地修改） |
| 10 | e2e 測試 | `frontend/tests/e2e/member-pages.spec.ts`（新建） |

## 二、已定案的設計決定（本計畫只執行，不重新決定）

| 決定 | 內容 | 來源 |
|---|---|---|
| `[F1]`=A | 橫幅宿主掛在 `Layout` 內 | `nfr-requirements` |
| `[F2]`=A | 掛載時打一次 REST | 同上 |
| `[F4]`=A | 三種操作後**就地更新**，不整份重抓 | 同上 |
| `[N1]`=A | 清單上限 **100** 列，超過不渲染清單、改顯示提示 | 同上（數字來源 `user_router.py:147` 的 `MAX_PAGE_SIZE`） |
| `[N2]`=A | 橫幅查詢**不快取** | 同上 |
| `[N3]`=B＋`R-07` | 每一條對使用者無聲的失敗路徑都要輸出一筆 console 訊號 | 同上 |
| `[N4]`=A | `<LiveRegion />` **由本單元自建**，`U23` 之後沿用 | 同上（推翻 `[F3]`=A 的排序理由） |
| `[ND1]`=A | 每頁各掛一個實例、props 驅動不持有狀態、`role="status"` 寫死 | `nfr-design` |
| 審查 `R-01` | `canManage` ＝ per-project `role` ∈ {owner, admin} **AND** `can("K3","edit")` | `nfr-design` §一之三 |
| 審查 `R-04` | `FailureSignal` 兩欄皆為**字面值聯集** | `nfr-design` §四 |
| 審查 `R-07` | `Layout` 的掛載**不走** `slotRegistry` portal（獨立 root 取不到 `useAuth()`、且 portal 失敗為靜默 no-op） | `nfr-design` §三之一 |

## 三、實作步驟（`test-after`，逐層實作後補該層測試）

- [x] **Step 1 — 專案結構與設定確認（零變更）**
  確認無需新增依賴、無需改 `package.json`、無需改 `playwright.config.ts`
  （`testDir: './tests/e2e'` 已涵蓋新檔）。本步驟只做確認與記錄，不寫程式。
  追溯：`TS-U24-1`、`TS-U24-7`。

- [x] **Step 2 — 驗證測試執行器並記下本單元專屬指令**
  執行 `cd frontend && npx playwright test tests/e2e/member-pages.spec.ts --list`
  確認收集機制可用（檔案尚不存在時應回報 0 個測試而非設定錯誤）。
  指令記入 `unit-test-instructions.md`。
  追溯：`TS-U24-2`。

- [x] **Step 3 — `failureSignal.ts`：失敗訊號的封閉型別（實作）**
  `SignalKind` 五個字面值、`SignalEndpoint` 六個路徑樣板、`emitFailureSignal()`。
  **刻意沒有 `message`／`detail`／`displayName` 欄位**，使 `SEC-U24-1` 成為型別層保證。
  追溯：`SEC-U24-1`、`SEC-U24-6`。

- [x] **Step 4 — `<LiveRegion />`（實作）**
  `{ message, srOnly? }`、不持有狀態、`role="status"` 寫死於元件內、
  `data-testid="live-region"`。做成**可共用形狀**供 `U23` 沿用（`HO-U24-1`）。
  追溯：`BR27.1`、`TS-U24-6`、`HO-U24-1`。

- [x] **Step 5 — `membershipApi.ts`：抓取函式層（實作）**
  六個純抓取函式，**不碰 state**（`TS-U24-4`：`react-hooks/set-state-in-effect`
  為 error 級）。URL 一律經 `apiUrl()`（`TS-U24-3`）。手寫 `Authorization: Bearer`
  沿用既有 40 處形狀。422 以 `detail` 的**型別**分流（字串 vs 物件陣列，`BR23.1`）。
  每個失敗路徑呼叫 `emitFailureSignal()`。
  追溯：`SEC-U24-4`、`SEC-U24-6`、`TS-U24-3`、`TS-U24-4`。

- [x] **Step 6 — `ReselectionBanner.tsx` 與 `Layout.tsx` 掛載（實作）**
  `<ReselectionBannerHost>` 帶 `role="status"`、**無條件渲染**、只放要被朗讀的文字；
  `<ReselectionBannerActions>` 的兩個控件放在宿主**之外**的兄弟節點
  （`role="status"` 隱含 `aria-atomic="true"`）。掛載時先 `can("K3","view")`，
  為 false 則**不發請求**（`UIP-2` 的 0 次）。直接渲染於 `Layout.tsx` 的 React 樹內。
  追溯：`BR21.1`、`BR21.3`、`BR26.1`–`BR26.3`、`UIP-2`。

- [x] **Step 7 — `MembersListPage.tsx`（實作）**
  兩層抓取形狀（純函式 ＋ 呼叫端更新 state ＋ `useEffect` 的 `cancelled` flag）。
  `canManage` ＝ 自己那一列的 `role` ∈ {owner, admin} **AND** `can("K3","edit")`。
  100 列渲染閘放在「資料→視圖」轉換點。載入／錯誤經 `<LiveRegion />`。
  追溯：`UIP-1`、`UIP-4`、`BR22.1`–`BR22.3`、`BR25.2`、`SEC-U24-5`。

- [x] **Step 8 — `InviteMemberDialog.tsx`（實作）**
  角色只提供列舉內選項；422 兩種語意分流的文案；成功後**就地新增一列**。
  追溯：`BR23.1`、`UIP-3`、`AC12.6.1`。

- [ ] **Step 9 — `MemberDetailPage.tsx`（實作）**
  角色下拉（就地更新）、`[移出專案]` ＋ 二次確認（就地移除）、409 最後管理者守門文案。
  **變更紀錄區塊**：依 `OPEN-MP24-7`，取得資料的端點不存在，故渲染一個明確的
  「尚無法取得變更紀錄」佔位並在程式註解指向 `OPEN-MP24-7`——**不捏造資料、
  不留空白區塊**。
  追溯：`UIP-3`、`UIP-5`（Deferred）、`BR24.1`–`BR24.3`、`OPEN-MP24-7`。

- [ ] **Step 10 — 路由與 Sidebar 入口（實作）**
  `App.tsx` 新增兩條路由並以既有 `CapabilityRoute` 包覆（`K3`／`view`）；
  `Sidebar.tsx` 依既有的「按 user story 大類分層」慣例新增入口。
  追溯：`SEC-U24-3`、`project.md` 的 Sidebar 分層規則。

- [x] **Step 11 — 前端行為的測試（`test-after` 的測試步驟）**
  `frontend/tests/e2e/member-pages.spec.ts`，**8 個案例**，逐一對應
  `cicd-pipeline.md` §五 的斷言標的表：
  (1) 100 列上限＋提示、(2) 橫幅請求數（有／無 `K3 view` 兩個分支）、
  (3) 三操作後不重抓、(4) 首次可互動前請求數為 1、
  (5) 四控件在「per-project admin 但缺 `K3.edit`」下全部不存在、
  (6) 四控件在一般成員身分下全部不存在、
  (7) 三條失敗路徑各有 console 訊號且不含使用者文字、
  (8) 橫幅宿主無條件渲染**且** `role="status"`。
  **突變驗證**：每個案例都把修正改回錯的行為、確認紅燈、還原複驗，
  結果記入 `code-summary.md`。
  追溯：全部 `UIP-*`、`SEC-U24-*`、`BR2x.y`。

- [x] **Step 12 — 建置與 lint 驗證**
  `cd frontend && npm run lint`（須維持 0 errors）與 `npx tsc -b`（須通過）。
  **如實記載**：`tsc -b` 對「後端加欄、前端漏接」無效（`team.md` 已記載），
  故它的通過**不構成**資料形狀正確的證據——那由 Step 11 的 e2e 承擔。

- [x] **Step 13 — `source-manifest.json`**
  列出本單元建立／修改／刪除的每一個 application-source 路徑（含殼層與產生器寫的檔）。

- [x] **Step 14 — 文件與追溯**
  `code-summary.md`（含突變驗證結果）與 `traceability.json`。

## 四、刻意**不**做的事（避免 scope 蔓延）

| 不做 | 理由 |
|---|---|
| 不改 `U19` 的任何端點 | `OPEN-MP24-6`（伺服器分頁）與 `OPEN-MP24-7`（變更紀錄端點）都是 `U19` 的契約擴充，而 `U19` 已完成且在游標之前 |
| 不引入前端 unit／component 測試框架 | `team.md` 的 Q4 定案 D 項不採用 |
| 不改 `role_permissions` seed | 本單元只**讀取** `can("K3","edit")` 的既有結果；零 seed 變更即不觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步 |
| 不新增任何環境變數 | `TS-U24-7`；同步義務為空集合 |
| 不沿用 `AdminPage.tsx:104` 的 4 秒 toast | `frontend-components.md:176` 明文禁止（實測無 `role`／`aria-live`） |
| 不走 `slotRegistry` portal | `nfr-design` §三之一 的三個理由 |

## 五、Story 追溯

| 計畫步驟 | 承載的故事／AC |
|---|---|
| Step 6 | `US12.4`（交棒橫幅）：`AC12.4.3`、`AC12.4.4` |
| Step 7、Step 8 | `US12.1`（成員清單）、`US12.6`（邀請）：`AC12.1.1`、`AC12.6.1` |
| Step 9 | `US12.2`（改角色）、`US12.5`／`US12.6`（移出）：`AC12.2.1`、`AC12.2.2`（部分，受 `OPEN-MP24-7` 阻塞）、`AC12.6.2` |
| Step 10 | `US12.1` 的入口可達性 |
| Step 11 | 以上全部的可驗證面 |

## 五之一、合併前必修第 9 項（code-generation Request Changes 修訂，2026-10-23）

**來源**：`construction/functional-design/merge-blockers.md` 第 9 項（`nfr-requirements` `review-05` R-02），劃給本單元。使用者於 2026-10-23 裁決：**前端分頁顯示全部**。

**缺陷**：`frontend/src/pages/MembersListPage.tsx:34`（`MAX_RENDERED_MEMBERS = 100`）與 `:182-187`：成員超過 100 位時整張表不渲染，只顯示「成員過多，請聯絡管理者」。成員頁是唯一的成員管理入口，101 人的專案連「移除成員回到 100 以下」都做不到——`UIP-1` 從效能取捨變成功能斷崖（`nfr-requirements:2d9eec8d` 已記此形狀）。

- [x] **Step 15 — 拿掉 100 列整表隱藏閘，改為前端分頁**：每頁 50 位（模組常數，不做環境變數），以既有清單資料在前端切頁；提供上一頁／下一頁與「第 N／M 頁、共 K 位」；沿用既有 Tailwind 樣式與 `data-testid` 慣例。後端 `list_members` 已回傳全部成員，**不改任何 `U19` 端點**（第四節「不改 `U19` 的任何端點」維持；`OPEN-MP24-6` 伺服器分頁仍為開放項，不在本步範圍）。
- [x] 分頁與既有行為的交互：邀請／改角色／移出後**不整份重抓**（案例 3 的既有保證不變），本地更新後若當前頁變空則退回前一頁；`canManage` 判定不因分頁增加請求（案例 4 不變）；橫幅宿主不受影響。
- [x] 刪除「成員過多，請聯絡管理者」提示與 `MAX_RENDERED_MEMBERS` 常數及其註解，改寫為分頁的事實（不留死碼）。
- [x] **測試**（`tests/e2e/member-pages.spec.ts`）：案例 1 改為「構造 101 位 → 清單存在、第 1 頁 50 列、共 3 頁；翻到第 3 頁可見第 101 位且其管理控件可用」；另加「構造 100 位 → 共 2 頁」。依 `unit-test-instructions.md §七` 名稱穩定性規則，案例 1 若必須改 `test()` 字串，於 `code-summary.md` 記明舊名與新名，供 TCMS 同步時處理孤兒案例。突變：還原 100 列整表隱藏閘 → 案例 1 紅。
- [x] 本單元 e2e 需本機 stack（`deploy/docker-compose.test.yml`）；本機無 Docker daemon 時，至少跑 `npm run lint`、`npm run build`（`tsc -b`）與 `npx playwright test tests/e2e/member-pages.spec.ts --list`，e2e 實跑據實記為未驗（由 CI 的 `ui-regression` 承擔）。
- [x] `merge-blockers.md` 第 9 列回填處置；`code-summary.md` append 本節紀錄；`source-manifest.json`、`traceability.json`（加 `MB-9`；`UIP-1` 相關列更新說明）。
- 追溯：`merge-blockers.md` #9；`UIP-1`、`US12.1`、`AC12.1.1`。

## 五之二、合併前必修第 23 項（2026-10-26 使用者裁決：先修再重審）

**來源**：`construction/functional-design/merge-blockers.md` 第 23 項（code-generation 重做時 review-04 的 Major ＋ Minor）。訊號種類標錯那一項只記 Minor，不在本節範圍。

- [x] **Step 16 — 非數字 `projectId` 不再停在載入中**：`MembersListPage.tsx` 在網址 `projectId` 不是有限數字時，顯示與 404 相同的固定句「查不到這個專案」，並依 `SEC-U24-6` 經 `emitFailureSignal()` 發出訊號；不顯示「載入中…」。沿用 `team.md` 的兩層抓取形狀（不在 effect 內同步 setState）。
- [x] **Step 17 — 兩個對話框的鍵盤行為**：邀請對話框與移出確認框加上焦點圈限（Tab／Shift+Tab 不離開對話框）、Escape 關閉、關閉後焦點回到觸發按鈕；形狀沿用 repo 內既有支援 Escape 的對話框，不新增依賴。
- [x] **Step 18 — 測試**（`tests/e2e/member-pages.spec.ts`，`test-after`）：(a) 非數字 `projectId` → 顯示固定句、不顯示「載入中…」、有一筆失敗訊號；(b) 兩個對話框各斷言 Escape 關閉、Tab 不離開對話框、關閉後焦點回原按鈕。新案例附 `@purpose`／`@given`／`@step`／`@pass`／`@story`／`@ui` 規格註解。
- [x] **Step 19 — 突變驗證**（只在暫存區副本做）：拿掉 Step 16 的處理 → (a) 紅；拿掉 Step 17 的焦點圈限／Escape／焦點回復 → (b) 對應斷言紅。結果記入 `code-summary.md`。
- [x] **Step 20 — 回歸與收尾**：`npm run lint`（0 errors）、`npx tsc -b`、build；`member-pages.spec.ts` 與 `a11y.spec.ts` 全綠（對話框改動後重跑無障礙掃描點 11、12、15）；新檔加入 `source-manifest.json`，`traceability.json` 只更正變為不實的註記；`code-summary.md` 追加第 23 項處置段。
- 追溯：`merge-blockers.md` #23；`SEC-U24-6`、`AC-A11Y.1`、`US12.1`、`US12.6`。

## 五之三、第 23 項補修：成員詳情頁（2026-10-26T14:59:26Z 使用者裁決：再開一次本單元，現在補修）

**來源**：review-05 R-11（Major，Still applies）——`MemberDetailPage.tsx` 抓取 effect 在 `projectId` 不是有限數字時直接 return、`isLoading` 永遠為 true，`/projects/abc/members/1` 永遠停在「載入中…」且無訊號；原 R-11 涵蓋兩頁，第 23 項原文只寫清單頁。另含 review-05 的新 Minor（對話框其他關閉路徑無焦點斷言）。

- [x] **Step 21 — 詳情頁非數字 `projectId`**：`MemberDetailPage.tsx` 比照 Step 16 的形狀（導出值、不在 effect 內同步 setState），在 `projectId` 不是有限數字時顯示與 404 相同的固定句、經 `emitFailureSignal()` 發一筆訊號、不顯示「載入中…」。
- [x] **Step 22 — 測試**（`member-pages.spec.ts`）：(a) `/projects/abc/members/1` → 固定句、無「載入中…」、一筆訊號；(b) 邀請送出中（以 route 延遲請求）按 Escape 對話框仍在，請求完成後才關閉並把焦點還給「邀請成員」鈕；(c) 移出確認的 409 或 403 路徑關閉後焦點回到「移出專案」鈕。附規格註解。
- [x] **Step 23 — 突變驗證**（只在暫存區副本做）：拿掉 Step 21 → (a) 紅；把送出中的 Escape 停用條件改錯 → (b) 紅；拿掉錯誤路徑的焦點回復 → (c) 紅。結果記入 `code-summary.md`。
- [x] **Step 24 — 回歸與收尾**：lint 0 errors、`tsc -b`、build；`member-pages.spec.ts` 與 `a11y.spec.ts` 全綠；`code-summary.md` 追加補修段，並列出本節與 §五之二 新增的全部 e2e 案例名稱，供 `tcms-test-cases` 同步（案名合併後不得再改）。
- 追溯：`merge-blockers.md` #23；review-05 R-11；`SEC-U24-6`、`US12.2`。

## 六、核可關卡

本計畫與 `unit-test-instructions.md` 的核可問題、`[Approval Fingerprint]` 與
`[Planned Source]` 兩個標籤，**一律寫在 `code-generation-questions.md`**，
不寫在本檔——把標籤寫進本檔會讓指紋自我指涉而永不收斂
（`U11` 那站已實證三次不同值）。

## Testing Contract

```json
{
  "version": 1,
  "methodology": "test-after",
  "source": "fallback",
  "ordering": "Implement each testable layer, then write and run that layer's tests.",
  "scope": "agent-orchestration-brain",
  "test_strategy": "standard",
  "project_type": "brownfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. Specific\nmethodology — TDD, BDD, ATDD, or classic test-after — is captured by the\ntesting-strategy stage when it ships.\n\nUntil then, our default per scope is:\n- `mvp`, `enterprise`, `feature`, `infra` → tests written alongside\n  code; minimum 80% line coverage; tests run in CI before merge.\n- `bugfix`, `security-patch` → regression test for the specific\n  bug/vulnerability; existing test suite must remain green.\n- `poc`, `refactor`, `workshop` → existing test suite remains green;\n  no new test floor required.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "### 既成事實\n\n- **Backend 測試框架**為 Python 內建 `unittest` + `hypothesis` + `unittest.mock`，**未使用 pytest**。CI 以 `python -m unittest discover -s tests -v` 執行（`ci.yml`）。測試 DB 策略見 `backend/tests/helpers.py`：在任何 DB import 前 `sys.modules.setdefault(\"psycopg2\", MagicMock())`，改走 in-memory SQLite，每 session `ensure_role_permissions_seeded(db, force=True)`。規模：`backend/tests/` 21 個測試檔（HEAD `c3de2c8`；2026-08-06 版「14 個」已過時）。\n- **Frontend e2e** 為 Playwright（chromium 單一 project），涵蓋登入與 RBAC 可視性；`ui-regression` gh-aw workflow 每 PR 對短生命週期 stack 執行並回報 Kiwi TCMS。**這是真閘門**：`post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`；容忍 `stats.flaky`，`retries: 1`。HEAD 現有 e2e 涵蓋 Admin 最後活動與分頁，**無成本頁 e2e**。\n- **Frontend 完全沒有 unit／component 測試框架**：`frontend/package.json` 的 `devDependencies` 只有 `@playwright/test`，無 vitest、無 jest、無 `@testing-library/*`；`scripts` 只有 `test:e2e`。前端的唯一自動化驗證層就是 Playwright e2e。\n- **Property-based testing**：7 個檔共 13 個 `@given`（HEAD `c3de2c8`；覆蓋 `test_design_agent`、`test_wa_rule_engine`、`test_diagram_builder`、`test_diagram_icons`、`test_collab`、`test_auth`、`test_activity`），皆落在純函式模組，屬自發良好實踐。`project.md` ADR-0006 點名的三個 hard-constraint 落點（IaC generator、cost calculator、agent routing）中，**cost calculator 在本 repo 尚無對應實作模組**，故該約束目前對 repo 現況為 N/A（非豁免、非違反）。本 intent 若新建 calculator 模組，ADR-0006 PBT 約束隨即由 N/A 轉為 blocking。\n- **HTTP 層 TestClient 現況**：`backend/tests/test_user_list_endpoint.py` 用 `starlette.testclient.TestClient` 測 `/api/auth/list` 分頁欄位（樣板在 `tests/helpers.py`）。此為現行唯一 TestClient 使用例；**無 cost router 可測**。\n- **C1 / pricing 測試完全缺席**：無 `test_cost*`；`'C1'`／`\"C1\"` 在 `backend/tests/` 0 命中；`test_rbac.py` 不覆蓋 C1／C2／C3。WA `COST-*` findings 連 example-based 測試都沒有。\n- **完全沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）。`org.md` 宣告的「最低 80% line coverage」目前**既無法量測也無法強制，是宣告而非閘門**。\n- **既有授權測試皆在 service 層**：`test_rbac.py`、`test_j5_authz.py`、`test_review_authz.py` 皆非 HTTP 層測試。\n\n### 本輪新增規則（Q4 定案：A + B + C，D 不採）\n\n依據：本 intent 的六道現有 CI 閘門（`repo-contract`、frontend lint、`tsc -b`、backend import smoke、backend `unittest`、`ui-regression`）逐一查證後，**對「後端漏欄位、序列化成 null、前端渲染成空白」這條失敗路徑全部無效**——不是覆蓋率不足的程度問題，是這條變更路徑上沒有任何自動化斷言存在的有無問題。三項零新依賴的測試底線本輪起生效：\n\n- **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 `role_permissions` 預設值變更，必須有測試同時驗證「該角色能做到」與「其他角色做不到」。零新依賴，直接擴充既有 `test_rbac.py`／`test_j5_authz.py` 形狀。C1 的 RBAC seed 種子已存在（`FinOps_Analyst` 與 C1 相關欄位）；若本 intent 改動 C1 預設值（例如讓架構師 edit 時數），屬 seed 變更，須 A 規則測試。\n- **B — 新增或修改 HTTP 端點需 `TestClient` 測試**：斷言其 status code 與 `response_model` 的欄位集合。採用成本為零——`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，`starlette.testclient.TestClient` 前置條件已滿足；新測試檔放進 `backend/tests/` 即被現有 `python -m unittest discover -s tests` 撿到；`get_db`（`database.py:31`）與 `get_current_user`（`services/auth.py:39`）為穩定的模組層函式，可用 `app.dependency_overrides` 覆寫；以 `TestClient(app)` 直接使用不觸發 `@app.on_event(\"startup\")` 的 `init_db()`，不需要真實 DB。C1 若新增 `/api/cost*` 端點，須依 B 規則補 TestClient 測試，且 CI 的 OpenAPI drift 檢查會要求同步更新 `openapi.json`。\n- **C — 前端資料形狀變更需 e2e 斷言**：例如本次 Admin 表格加欄，須新增至少一個 Playwright case 斷言表頭出現該欄位、且至少一列顯示值或既定的「從未」佔位。用既有 Playwright，不需新依賴，且是目前**唯一**能碰到前端頁面的自動化層。C1 若新建 Cost 頁，資料形狀為全新，須 C 規則 e2e 斷言。\n- **D（不採用）— 引入前端 unit／component 測試框架**：需新增依賴（Vitest 或類似），成本明顯較高，且屬獨立的工具鏈決策，不由本次加欄 feature 夾帶。C 項的 e2e 斷言已覆蓋本 intent 的加欄驗證需求。\n\n- **Q3 定案（A）— C1 HTTP 消費者的最小授權測試義務**：即使 `role_permissions` seed 資料未修改（C1 種子已存在於 `rbac_seed_data.py`），第一個 C1 HTTP 端點落地時仍須補 allow/deny 雙向 TestClient 測試——「具 C1 權限的角色應收到 2xx」與「無 C1 權限的角色應收到 403」兩個案例缺一不可。此為 A 規則與 B 規則的交叉要求，適用於本 intent 新增的任何 `/api/cost*` 端點。\n\n### 80% 覆蓋率門檻的定位\n\n**維持 `org.md` 原文，不在本檔弱化或改寫其宣稱**（把「80% 是目標不是閘門」寫進 `team.md` 會構成 `team.md` 弱化 `org.md` 的矛盾，屬 §13 learning admission 應擋下的形狀）。如實記載目前無法量測、無法強制的現況（見上），並以上述 A/B/C 三項變更範圍內、二元可判、零工具成本的規則作為現階段的實際門檻。導入 `coverage.py` 量測工具列為待補承載機制（見 `discovered-rules.md`）。\n\n---"
    },
    {
      "layer": "project",
      "text": "**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含 property-based 測試，不得只有 example-based：IaC generator、cost calculator、agent routing。其餘模組沿用 `org.md` 的預設門檻。"
    }
  ],
  "obligations": {
    "strategy": "standard",
    "strategy_volume": [
      "Five to eight tests per component.",
      "Unit tests plus integration tests for key boundaries.",
      "Add E2E, performance, or security tests when requirements demand them."
    ],
    "scope_floor": [
      "Keep the existing test suite green.",
      "This scope adds no extra new-test floor beyond the selected test strategy."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "test-after",
    "runner_step": "Verify the existing test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Verify the existing test runner/configuration and record the exact unit-scoped command.",
      "Data model / database behavior - implement.",
      "Data model / database behavior - write and run its tests after implementation.",
      "Repository / data access - implement.",
      "Repository / data access - write and run its tests after implementation.",
      "Business logic - implement.",
      "Business logic - write and run its tests after implementation.",
      "API / endpoint - implement.",
      "API / endpoint - write and run its tests after implementation.",
      "Frontend behavior - implement.",
      "Frontend behavior - write and run its tests after implementation.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:1aedc10dd7de9a19bd06fecb49cbcb5f27456db7ce4b18e81d500355d460bea6",
  "contract_sha256": "sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77"
}
```

