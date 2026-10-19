# Unit Test Instructions — `a11y-gate`（U17）

<!-- Stage: code-generation（Construction 3.5）· Unit: a11y-gate · Record: 260920-orchestration-brain -->

## 一、框架與設定

- **Playwright e2e**（chromium 單一 project），沿用 `frontend/playwright.config.ts`：`fullyParallel: false`、`workers: 1`、CI 下 `retries: 1`、單 test 逾時 30 秒、reporter 為 `list`／`json`（`pw-report.json`）／`junit`。本單元**預設不改**這份設定；唯一例外是計畫 Step 11 的 `D-03` 備案。
- **`@axe-core/playwright`**：本單元新增的 devDependency，以 `AxeBuilder` 對已開啟的頁面跑 axe-core。
- 前端沒有 unit／component 測試框架（`team.md` D 項不採），本單元的全部自動化都在 e2e 層。後端不受影響，無後端測試。
- 新 spec 放在 `frontend/tests/e2e/`，`ui-regression` 的 `npx playwright test` 會自動撿到；`frontend/tests` 不在任何 tsconfig 內，spec 本身不受 `tsc -b` 檢查，但會被 `eslint .` 掃到。

## 二、本單元的測試（全部在一支檔案）

`frontend/tests/e2e/a11y.spec.ts`，`describe('U17 a11y gate')`，21 個 `test()`：

| 類別 | 數量 | 內容 |
|---|---|---|
| 掃描點 | 18 | 依 `security-requirements-corrections.md` `C-02` 表第 1–17 列 ＋ `C-07` 第 18 點；每點：隔離層 → 狀態層 → 就緒層 → 掃描層 |
| 手機寬度 | 1 | 375×812 下入口頁 `scrollWidth <= clientWidth`（`C-06`） |
| 基準清單靜態檢查 | 1 | 不開頁面：規則 1／4／5 ＋ 每點 `ready` 非空（`M12`） |
| 基準清單過期檢查 | 1 | 檔案最末：讀回 18 個掃描點的寫檔結果，判定過期條目 |

另有 `frontend/tests/e2e/a11y-baseline.json`（資料檔，非測試）。

## 三、執行方式（只跑本單元）

本機沒有 Docker 時，以 `vite preview` 服務前端；本 spec 全部走攔截層，不需要後端、資料庫或 compose stack。

```bash
# 終端機一：建置並服務前端（同源，攔截才能涵蓋 /api 與 WebSocket）
cd frontend
npm run build
npx vite preview --port 4173 --strictPort

# 終端機二：只跑本單元
cd frontend
BASE_URL=http://localhost:4173 npx playwright test tests/e2e/a11y.spec.ts --reporter=list
```

模擬 CI 的重試行為（計畫 Step 11 的 `M10` 需要）：

```bash
cd frontend
CI=1 BASE_URL=http://localhost:4173 npx playwright test tests/e2e/a11y.spec.ts --reporter=list
```

有 Docker 時亦可對 compose stack 跑（與 `ui-regression` 相同的 `BASE_URL`）：

```bash
cd frontend
BASE_URL=http://localhost:8090 npx playwright test tests/e2e/a11y.spec.ts --reporter=list
```

**不得**以 `npx playwright test`（不指定檔案）代替上述指令——那會重跑整個 e2e 套件。

## 四、預期結果與覆蓋目標

- 21 個 `test()` 全綠。
- 覆蓋目標以**掃描面**計，不以程式行數計：`C-02`／`C-07` 的 18 個畫面狀態全部被掃描，且每個掃描點的就緒斷言證明掃到的是預期的畫面。80% 行覆蓋率對一支測試檔不適用（本單元沒有被測的產品程式碼，除非 Step 10 修了新元件）。
- 突變驗證 `M1`–`M12` 每一道都必須紅在 `security-design.md` 第八節與 `security-design-corrections.md` `D-08` 指定的那一層。

## 五、攔截與資料準備

- **登入**：`page.addInitScript` 寫入 `sessionStorage.setItem('token', <固定假值>)`，並以 `page.route('**/api/auth/me')` 回傳該掃描點所需的權限組合（形狀沿用 `member-pages.spec.ts:115-129`）。不得使用真實帳密或真實 token（`A11Y-S6`）。
- **兜底**：HTTP 與 WebSocket 兜底**最先**註冊（Playwright 後註冊者優先），具體端點在其後註冊（`C-01`、`D-05`）。
- **資料形狀**：從 `entry-page.spec.ts`、`memory-page.spec.ts`、`project-pages.spec.ts`、`member-pages.spec.ts` 複製最小必要部分，不抽共用模組、不改那四支檔。
- **掃描結果檔**：寫在 `testInfo.project.outputDir` 下的固定子目錄，每個掃描點一檔、同名覆寫；必須在任何斷言之前寫入（`D-03`）。

## 六、不屬本單元的測試

- `[人工]` 項目（O-1 純鍵盤流程、O-12 焦點陷阱、R-4 播報內容、landmark 唯一與標題層級、`OPEN-ND24-1` 兩個播報區的先後、§27 的 `/admin` 錯誤態）交 `build-and-test` 與 `tcms-test-cases`。
- `U23`／`U24`／`U14`／`U15` 的功能行為已由各自的 e2e 涵蓋，本單元不重複斷言。
