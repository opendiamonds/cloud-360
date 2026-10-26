# Unit Test Instructions — `object-picker-ui`（U16）

<!-- Stage: code-generation（Construction 3.5）· Unit: object-picker-ui · Record: 260920-orchestration-brain -->

## 一、框架與設定

- **Playwright e2e**（chromium 單一 project），沿用 `frontend/playwright.config.ts`，本單元**不改**這份設定。
- 前端沒有 unit／component 測試框架（`team.md` D 項不採）；`objectPickerModel` 的純函式以 e2e 例子驗證。後端零變更，無後端測試。
- **ESLint**：本單元在 `frontend/eslint.config.js` 新增選單檔案集合的區塊，`npm run lint` 是其中六類禁令的承載者（`nfr-requirements-corrections.md` `N-03`）。
- 新 spec 放在 `frontend/tests/e2e/`，`ui-regression` 的 `npx playwright test` 會自動撿到。

## 二、本單元的測試

| 檔案 | 內容 |
|---|---|
| `frontend/tests/e2e/object-picker.spec.ts`（新，`describe('U16 object picker')`） | 選取、建立、權限、請求數、身分未決、斷線、輸入處理、型別邊界、頁面切換、鍵盤與焦點（計畫 Step 7 清單） |
| `frontend/tests/e2e/a11y.spec.ts`（`U17` 的檔，加兩個掃描點） | 選單 `default` 態、建立表單錯誤態 |
| `npm run lint` | 選單檔案的主控台、瀏覽器儲存、`innerHTML`、`RegExp`、直接建立匯入、`new WebSocket` 禁令 |

## 三、執行方式（只跑本單元）

本機沒有 Docker 時，以 `vite preview` 服務前端（正式建置；請求計數類案例**必須**對它跑，避免開發模式 `StrictMode` 的雙掛載使請求數加倍）。

```bash
# 終端機一
cd frontend
npm run build
npx vite preview --port 4173 --strictPort

# 終端機二：本單元
cd frontend
BASE_URL=http://localhost:4173 npx playwright test tests/e2e/object-picker.spec.ts --reporter=list
BASE_URL=http://localhost:4173 npx playwright test tests/e2e/a11y.spec.ts --reporter=list

# 回歸（OPEN-OP16-4：修改了 U14 的 ContextBar）
BASE_URL=http://localhost:4173 npx playwright test tests/e2e/entry-page.spec.ts tests/e2e/entry-page-live.spec.ts --reporter=list

# lint
npm run lint
```

結束後停止 preview 伺服器。**不得**以 `npx playwright test`（不指定檔案）代替上述指令。

## 四、預期結果與覆蓋目標

- `object-picker.spec.ts` 全綠；`a11y.spec.ts` 全部 test（原 22 ＋ 新 2）全綠且 `a11y-baseline.json` 不變；回歸 spec 全綠；`npm run lint` 0 errors、warning 數不增。
- 覆蓋以行為計：`rules.md` 22 條中可自動化者、`OPN-*` 19 條中有 e2e 或 lint 檢查者，每條至少一個斷言；不以程式行數計（前端無覆蓋率工具）。
- 突變 M1–M16 每一道都必須紅在 `security-design.md` §六與 `nfr-design-corrections.md` 指定的檢查；M9 必須實際看到紅燈。

## 五、攔截與資料準備

- **登入**：`page.addInitScript` 寫入 `sessionStorage` 的固定假 token，並以 `page.route('**/api/auth/me')` 回傳所需權限（含 `K1`／`K2` 的 view／edit 組合）。身分未決情境回 **200 但不含 `id`**（`N-01`），不得回 500 使路由守衛導走。
- **假大腦**：沿用 `entry-page.spec.ts` 的 `routeWebSocket` 形狀；訊框只經 `src/brain/testing/wsFrames.ts` 的建構器（`eslint.config.js:94` 禁止手寫）。
- **HTTP**：`page.route` 樁 `/api/hierarchy/projects`、`…/systems`、兩支 `POST`；延遲與錯誤以 route handler 控制。
- 不得使用真實帳密或真實 token。

## 六、不屬本單元的測試

- `AC9.2.3` 的「經 `require_story_action`」授權面：屬 `U7`，依 `F-01` 讀為 Deferred。
- 螢幕閱讀器實際唸出內容、手機實機操作：交 `build-and-test` 與 `tcms-test-cases`。
