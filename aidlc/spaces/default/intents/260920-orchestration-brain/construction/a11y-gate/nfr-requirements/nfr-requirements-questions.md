# NFR Requirements 問題 — `a11y-gate`（U17，`kind: packaging`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: a11y-gate · Record: 260920-orchestration-brain -->

## 這一輪只問一題，以及為什麼

本單元是 `kind: packaging`——它交付的是一個 devDependency（`@axe-core/playwright`）與一支跑在既有 Playwright 層的掃描 spec，不是執行期程式碼。依 stage 檔的 `produces_kinds`，`performance-requirements`／`scalability-requirements`／`reliability-requirements`／`observability-requirements` 四項對 `packaging` 不適用（限 `service`／`ui`），故本單元只產出 `security-requirements.md`、`tech-stack-decisions.md` 與 `traceability.json`。

Construction 階段的提問應是例外而非常規。下列事項已由上游定案，本輪**不重問**，每一項都能指出定案處：

| 已定案事項 | 定案處（可引用） |
|---|---|
| 工具為 `@axe-core/playwright`，是既有 Playwright 層的 plugin，**不是**新測試框架 | `accessibility-checklist.md`「驗證機制」節（`[DM:D6]`=A） |
| 標準為 WCAG 2.1 AA | `accessibility-checklist.md` 開頭（承 `[R7]`） |
| **違規即 CI 紅燈** | `accessibility-checklist.md`「驗證機制」節 |
| 掃描範圍為**四類頁面、12 次掃描**：入口頁 1、`/memory` 1、專案清單 1、專案詳情三籤各 1、成員清單 admin-view／member-view 各 1、邀請對話框 default／denied 各 1、改選橫幅 single／multi-expanded 各 1 | `accessibility-checklist.md` 修訂 1「axe 掃描點的修訂」＋ `unit-of-work.md:436` |
| `/workspace`、`/assessment`、`/cost`、`/admin/*` **不掃** | `accessibility-checklist.md` 修訂 1 範圍表（`[DM:D11]`=A）。`/admin/*` 的重審是交接事項 `UG-5`，承接站為 `code-generation`（ALWAYS），本站不翻案 |
| axe 只能判定約三成的項目；`[人工]` 項目的驗證時機是 `build-and-test` | `accessibility-checklist.md`「誠實的能力界線」 |
| e2e 不得觸及任何 LLM 路徑 | `test-case-authoring.md` §4.3 |

> **作答後的對齊修正**：上表「12 次掃描」只引了無障礙清單。產出階段核對 `contract-summary.md` 時發現 `K-19`／`K-20` 另列了專案建立頁與成員詳情頁兩個必須可被 axe 掃描的畫面，掃描面因此為 **14 次**（`security-requirements.md` 的 `A11Y-S10`）。這不影響 `A11Y-Q1` 的作答——那一題問的是頁殼既存違規的處置，與掃描次數無關。

## 本輪查到的事實（實讀 repo，2026-10-17）

- `frontend/package.json:26` 只有 `"@playwright/test": "^1.56.0"`，安裝版本為 `1.61.1`；全樹 `axe` 命中只有 `member-pages.spec.ts:641` 一行註解，**尚未引入** `@axe-core/playwright`。
- 依賴慣例是 **caret 範圍 ＋ 已 commit 的 `package-lock.json` ＋ CI 用 `npm ci`**（`team.md` Code Style 節），鎖定靠的是 lockfile 而非 `package.json` 的精確版號。
- 四類頁面的 e2e 都已用 `page.route` 攔截 API（`entry-page.spec.ts` 11 處、`memory-page.spec.ts` 4 處、`project-pages.spec.ts` 6 處、`member-pages.spec.ts` 9 處），12 個掃描狀態所需的資料形狀在既有 spec 裡都已能造出，不需要真實 stack 的種子資料。
- `ui-regression` 以 `timeout 15m npx playwright test` 執行（`ui-regression.md:191`），新 spec 放進 `frontend/tests/e2e/` 即被撿到並成為擋 PR 的閘門。`U14` 已新增 54 案且未量測時間預算。
- 四類頁面都套在共用頁殼（`Layout.tsx`、`Sidebar.tsx`）裡。範圍表只管 `Sidebar` 的**三個新增項**；頁殼其餘部分屬既有、本 intent 不管。**本站未實跑 axe**，所以不知道頁殼目前有幾處既存違規。

---

## A11Y-Q1 — 頁殼的既存違規怎麼處理

**為什麼要問**：「違規即紅燈」是定案，但它沒說「誰的違規」。整頁掃描會把 `Layout`／`Sidebar` 的既有問題一起掃進來，而那些不在本 intent 的管理範圍內——這正是 `[DM:D11]`=A 決定不掃 `/admin/*` 的同一個理由（不讓既有技術債擋住本 intent 的閘門）。差別在於：`/admin/*` 可以整頁不掃，這四類頁面不行。

- A. **既存違規列成明文基準清單**：第一次實跑時把頁殼現有違規以「規則 id ＋ 元素選擇器」逐筆列在 spec 旁的基準檔，只擋清單以外的新違規；清單只准縮小、不准擴大，並由一條測試鎖住。代價：基準清單本身要人維護，且同一條規則若在同一個舊元素上換了寫法可能被誤放行。
- B. **整頁掃描、不排除，掃到的既存違規在本單元一起修掉**。代價：要修的量在實跑前未知；修的是共用頁殼，影響每一頁，而那些頁面（`/workspace` 等）本 intent 沒有 e2e 掩護。
- C. **只掃本 intent 新增的容器**（`AxeBuilder.include()` 指定新元件的根節點），頁殼完全不掃。代價：`Sidebar` 三個新增項在頁殼裡，會跟著被排除；新元件與頁殼交界的問題（例如重複的 landmark、標題層級跨元件跳級）抓不到。
- D. **整頁掃描，但以 `.exclude()` 排除頁殼的既有區塊**，保留 `Sidebar` 三個新增項。代價：排除粒度要逐一界定，排除過寬會把新違規一起藏起來。
- X. Other (please specify)

[Answer]: A  <!-- answered 2026-10-17 via picker -->
