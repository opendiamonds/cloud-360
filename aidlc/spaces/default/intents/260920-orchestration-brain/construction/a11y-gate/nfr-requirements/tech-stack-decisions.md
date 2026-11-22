# Tech Stack Decisions — `a11y-gate`（U17，`kind: packaging`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: a11y-gate · Record: 260920-orchestration-brain -->

## 決定一覽

| # | 決定 | 狀態 |
|---|---|---|
| T-1 | 掃描工具為 `@axe-core/playwright` | 上游已定案（`[DM:D6]`=A），本站沿用 |
| T-2 | 版本以 caret 範圍寫入 `devDependencies`，實際鎖定靠 `package-lock.json` ＋ `npm ci` | 本站定案（沿用 repo 慣例） |
| T-3 | 掃描寫成一支新 spec `frontend/tests/e2e/a11y.spec.ts`，不在既有 spec 內加掃描 | 本站定案 |
| T-4 | 掃描在 `page.route` 攔截的頁面上執行，不需要真實 stack 的種子資料 | 本站定案 |
| T-5 | 既存違規基準清單放在 `frontend/tests/e2e/a11y-baseline.json` | 本站定案（形式由 `[A11Y-Q1]`=A 決定） |
| T-6 | 不新增 CI job；由既有 `ui-regression` 的 `npx playwright test` 撿起 | 本站定案 |

## T-1 `@axe-core/playwright`

**理由**：它是既有 Playwright 層的 plugin，直接在已開啟的頁面上注入 axe-core 並回傳結構化結果，不需要第二個瀏覽器或第二個測試執行器。本 repo 前端唯一的自動化層就是 Playwright（`team.md` Testing Posture「既成事實」），在同一層加掃描是零新框架的做法。

**考慮過而不採的替代**：

| 替代 | 不採的理由 |
|---|---|
| `pa11y` ／ `pa11y-ci` | 自帶 Puppeteer 與自己的執行器，等於在 CI 裡多一個瀏覽器與一套設定；而且它要的是可直接造訪的 URL，本單元的 14 個狀態大多要靠 `page.route` 攔截與點擊才造得出來（邀請對話框的 denied、改選橫幅的 multi-expanded），在 pa11y 裡要重寫一遍 |
| 直接注入 `axe-core`（`page.addScriptTag` ＋ `axe.run`） | 與 T-1 用同一個引擎，只是少了 `AxeBuilder` 的 `withTags`／`include`／`exclude` 與結果型別，要自己寫一層等價的包裝 |
| Lighthouse CI | 輸出是分數而非違規清單；「分數 ≥ 90」與已核可的「違規即紅燈」是不同的閘門語意 |
| `jest-axe` ／ `vitest-axe` | 需要前端 unit／component 測試框架，而 `team.md` 的 D 項已明文不採 |

**授權**：`@axe-core/playwright` 與 `axe-core` 的授權條款**本站未查證**，由 `code-generation` 在選定版本時以 `npm view <pkg> license` 確認並記入 `code-summary.md`。它是 devDependency、不隨產品散布，但仍要知道它是什麼。

## T-2 版本與鎖定

- 寫法沿用 repo 慣例：`"@playwright/test": "^1.56.0"` 是 caret 範圍，真正的版本由已 commit 的 `package-lock.json` 決定，CI 用 `npm ci`（`team.md` Code Style 節；codekb `technology-stack.md:101-116` 記載 19 個 devDependencies 中唯一的精確 pin 是 `openapi-typescript 7.13.0`）。那一個例外為何精確 pin，本站未查證；本套件沒有需要精確 pin 的已知理由，故用 caret，不增加第二個例外。
- 選定版本須發布滿 14 天，且其 peer 範圍涵蓋已安裝的 `@playwright/test`（`A11Y-S3`）。
- 新增的套件樹須過 `npm audit`（`A11Y-S4`）。

## T-3 獨立的 `a11y.spec.ts`

**理由**：

1. **TCMS 案例名稱是 `<describe> › <test>`**（`test-case-authoring.md` §4.4）。把掃描塞進既有 spec 的既有 `test()` 裡，會讓一個既有案例同時代表「功能斷言」與「無障礙掃描」兩件事，紅燈時看不出是哪一件；另開新 `test()` 在既有 `describe` 下雖可行，但 14 個掃描會散在四支檔裡，基準清單也得跟著散。
2. 單一檔案讓 `A11Y-S9` 的四條規則只需要在一處實作。
3. 新檔放進 `frontend/tests/e2e/` 即被撿到，不需改設定。

**代價**：要從四支既有 spec 借用 `page.route` 的攔截資料形狀。借用方式（抽出共用 fixture，或在新 spec 內重建最小資料）由 `code-generation` 決定；若抽出共用 fixture，四支既有 spec 會被改到，屬重開已交付單元的範圍，須在計畫中揭露。

## T-4 攔截層，不用真實 stack

**理由**：四類頁面的既有 e2e 都已用 `page.route` 造出所需狀態（`entry-page.spec.ts` 11 處、`memory-page.spec.ts` 4 處、`project-pages.spec.ts` 6 處、`member-pages.spec.ts` 9 處，2026-10-17 實數），而 member-view／admin-view、denied、multi-expanded 這些狀態在真實 stack 上要靠種子資料與多個帳號才造得出來。攔截層同時滿足 `A11Y-S5`（不連外、不碰 LLM）。

**代價**：掃到的是前端在給定資料下的渲染，不是真實後端回應下的渲染。對無障礙掃描而言這是可接受的——axe 檢查的是 DOM 結構與樣式，不是資料正確性。

## T-5 基準清單的檔案位置

`frontend/tests/e2e/a11y-baseline.json`：與 spec 同目錄、不在 `frontend/src`，所以不進產品 bundle、也不在任何 tsconfig 內。JSON 而非 TS，讓 diff 只呈現資料變更。欄位最少為：掃描點、規則 id、元素選擇器、白話說明（`A11Y-S9` 第 4 條）。

## T-6 不新增 CI job

`ui-regression` 已以 `timeout 15m npx playwright test` 執行整個 `frontend/tests/e2e/`，且它是真閘門（`stats.unexpected` 非 0 即紅）。新 spec 自動納入，失敗即擋 PR，與「違規即 CI 紅燈」的定案一致。時間預算是已知風險，交 `build-and-test` 實測（`security-requirements.md` 交接 H-2）。

## 本單元不引入的東西

- 不引入前端 unit／component 測試框架（`team.md` D 項）。
- 不新增環境變數、compose 服務、secret 或 workflow 檔。
- 不改 `playwright.config.ts`（chromium 單一 project 維持不變）。
