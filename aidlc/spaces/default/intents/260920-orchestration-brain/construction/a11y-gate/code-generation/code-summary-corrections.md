# 更正附錄 — `a11y-gate` 的 Code Summary（審查 review-01 的處置）

<!-- Stage: code-generation（Construction 3.5）· Unit: a11y-gate · 寫於 2026-10-17T23:35Z（`date -u` 取值） -->

## 一、這份附錄是什麼、讀法規則

`reviews/review-01.md` 判 **READY**，另有 2 Major（R-01、R-02）＋ 5 Minor（R-03–R-07）。使用者選擇當場修 Major。審查收據記下後，`code-generation-plan.md`、`unit-test-instructions.md`、`code-summary.md`、`traceability.json` 已凍結、未改動。

**讀法規則**：
1. 本附錄與 `code-summary.md` 衝突時，**以本附錄為準**。
2. 本附錄記載的修正**未經重新審查**。它是對審查發現的處置，不是審查通過的證明。
3. `traceability.json` 凍結：其中 `A11Y-S9` 的 note（「基準 1 筆」）、`A11Y-S10`（「擴為 18 點」）、`D-04` 的 note（「唯一頁殼條目以 role=paragraph 取得」）以本附錄第二、三節為準；狀態與 target 不受影響（仍為同一個存在的檔案）。

## 二、R-01（Major）— 增列已連線狀態的入口頁掃描點

- **新增第 20 個掃描點** `20-entry-connected`，test 名稱 `20 入口頁已連線狀態`（`describe` 不變；既有 21 個 test 的名稱全部未改，TCMS 鍵不受影響）。
- **造法**：狀態層以後註冊者優先的規則覆寫隔離層的空 handler，收到 `hello` 時送出 `F.snapshotFrames(...)`（`src/brain/testing/wsFrames.ts` 的建構器，形狀沿用 `entry-page.spec.ts:58` 的 `BrainServer`；未手寫訊框，tests 區塊的 lint 禁令通過）。快照含 ready、兩則 sharing_mode、帶專案與系統的 `work_target`、一個 `running` 工作項。
- **就緒層證明已連線**：`brain-context-bar` 的 `data-state="default"`、`brain-context-name-project` 可見；排除項為標籤「連線中」的骨架（新增 `{ label }` 型 probe，以 `getByLabel(…, { exact: true })` 定位——骨架只有 `aria-label`、沒有 test-id）與 `brain-context-none`。
- **掃描結果**：第一次實跑即 **0 筆違規**（基準為空），不需修改任何元件。
- **過期檢查的檔數**：期望檔案清單本來就由 `ALL_SCANS`（`SCANS` 的值）推導，增列後自動變為 **19 檔**；規格註解中寫死的「18」已同步改為 19。
- **test 總數**：`a11y.spec.ts` 由 21 個變為 **22 個 `test()`**（19 個掃描點 ＋ 手機寬度 ＋ 2 個基準檢查）；檔案 1109 行。
- **仍未涵蓋**（如實記載）：`independent`、`unavailable` 兩態，以及 `WorkspacePage.tsx:930`／`AssessmentPage.tsx:1240` 上的 `ContextBar`，仍未被掃描。`code-summary.md` 第十四節第 7 點縮小為這兩態與那兩處掛載點。

### 新掃描點的突變驗證

| # | 突變 | 指定紅燈層 | 實際 | 還原後 |
|---|---|---|---|---|
| MA | 握手快照去掉第一個訊框（`connectedSnapshot().slice(1)`，即不送 `ready`） | 就緒層 | `[就緒層] brain-context-name-project 須可見`（element(s) not found） | 綠（雜湊位元組相同） |
| MB | `ContextBar.tsx` 的名稱節點（只在已連線且有作業對象時渲染）內加無 `alt` 的 `<img>`，重建 | 掃描層 | 第 20 點：`[掃描層] 20-entry-connected 有基準以外的 WCAG 2.1 AA 違規`，`image-alt` ×2（專案、系統兩個名稱節點）、`inNewRoot: true`；**同次執行的第 01 點綠**——證明這個元素在原本的掃描面之外 | 還原（雜湊位元組相同）並重建，全量 22 passed |

## 三、R-02（Major）＋ R-03（Minor）— 修 Sidebar 對比，基準清單歸零

- `frontend/src/components/Sidebar.tsx:325` 空選單提示 `<p>`：`text-gray-400` → **`text-gray-600`**，只改這一個 Tailwind 色階 class（Tailwind v4 的 gray-600 ≈ `#4a5565`，白底約 7.5:1；修後 axe 不再回報）。此檔原已有其他單元未 commit 的變更（`showEntry`、`showProjects`），本單元只動這一個 class。
- `frontend/tests/e2e/a11y-baseline.json` 改為 **`"entries": []`**；檔案與兩個基準檢查 test、規則 1／2／4／5 全部保留。
- **R-03**：`stabilize()` role 對照表中的 `p: 'paragraph'` **已移除**——它唯一的用途是取得那一筆基準條目的鍵，條目移除後沒有任何消費者。審查指出的副作用一併消失：`role=paragraph[name=…]` 不是可解析的 Playwright 定位器，只是「role＋文字」識別字串。
- **R-02 的程序面**：審查指出「選擇器在 D-04 停損觸發後才以擴充 role 對照表取得」。這個做法已隨本節撤回；`code-summary.md` 第十一節第 5 點與第十二節第 4 點中關於它的敘述，以本節為準。對照表內其他的隱含 role（`a`、`button`、`li`、`h1`–`h4` 等）仍保留，**它們仍讓頁殼節點能以 role＋文字名稱取得鍵**——這是 `D-04` 原文的第四順位，不是本次新增，但審查指出它是開放的放行面，日後新增任何以 role＋名稱為鍵的基準條目時，審查者應比照本次逐筆確認。

## 四、R-04（Minor）— 精確釘選版本

`npm install --save-dev --save-exact @axe-core/playwright@4.13.0`：`frontend/package.json` 由 `"^4.13.0"` 改為 **`"4.13.0"`**；lockfile 根條目同為 `4.13.0`，`node_modules/@axe-core/playwright` 與 `node_modules/axe-core` 仍為 4.13.0（`integrity` 不變）。`code-summary.md` 第四節「日後 `npm install` 可能浮到 4.14.x」的風險就此消除。

## 五、R-05、R-06、R-07（Minor）— 只記載，不改程式

- **R-07 — 本檔必須整檔執行**：過期檢查要求結果目錄恰為 19 檔，以 `-g`、`--grep`、`--shard` 或任何子集執行時，該 test 必然紅（設計上的大聲失敗）。單案執行或 TCMS 以單案重跑時會誤報；`ui-regression` 以 `npx playwright test` 整套執行、未 shard，不受影響。此限制已寫進過期檢查 test 的 `@given` 註解；`unit-test-instructions.md` 凍結未改，以本條為準。另：`seen` 集合納入 `inNewRoot` 的條目，所以只對得到新元件節點的基準條目不會判為過期——它也永遠不會被放行（掃描層仍判 fresh），無害。
- **R-05 — 綠燈不代表 `incomplete` 為空**：`incomplete`（axe 判不定、需人工）只附在 Playwright attachment，不影響紅綠；`ui-regression` 沒有 artifact 上傳，綠燈時這些結果零留存（`color-contrast` 遇背景圖或疊層時常以 `incomplete` 回報）。是否補上傳交 `build-and-test` 判定。
- **R-06 — 未處置（可選項）**：`aria-labelledby` 取代 `aria-label="專案角色"`、骨架改 `role="status"`、U14 提交後以 diff 複驗 `ContextBar.tsx:53` 只多 `role="img"`——皆未做，留給 `build-and-test` 或 U14／U24 的後續處理。

## 六、檔案與 `source-manifest.json`

本輪改動：`frontend/tests/e2e/a11y.spec.ts`、`frontend/tests/e2e/a11y-baseline.json`、`frontend/src/components/Sidebar.tsx`（新增）、`frontend/package.json`。`source-manifest.json` 已加入 `frontend/src/components/Sidebar.tsx`（嚴格 schema，只有 `writes[].path`），共 8 個路徑。突變 MB 暫時改過 `ContextBar.tsx`，已還原為位元組相同。

## 七、驗證結果

| 檢查 | 結果 |
|---|---|
| `BASE_URL=http://localhost:4173 npx playwright test tests/e2e/a11y.spec.ts` | **22 passed**（14.8s；突變還原後再跑 13.9s） |
| 同上加 `CI=1` | **22 passed**（14.0s） |
| `entry-page.spec.ts` ＋ `member-pages.spec.ts` ＋ `project-pages.spec.ts` ＋ `memory-page.spec.ts`（因 Sidebar 與三處元件屬性變更） | **97 passed**（1.2m） |
| `npm run lint` | 0 errors、2 warnings（與動工前相同） |
| `npm run build`（含 `tsc -b`） | 通過 |
| `aidlc-sensor-linter.ts`（spec） | pass，0／0 |
| `tcms_validate.py --spec` | 22/22，ERROR 0、WARN 0 |
| `validate_repo_contract.py`、`validate_env_contract.py` | 皆 passed |
| `grep -rn "axe-core" frontend/src` | 0 |
| preview server | 已停止 |
