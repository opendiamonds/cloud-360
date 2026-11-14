# Code Summary — `a11y-gate`（U17，`kind: packaging`）

<!-- Stage: code-generation（Construction 3.5）· Unit: a11y-gate · Record: 260920-orchestration-brain · 寫於 2026-10-17T23:17Z（`date -u` 取值） -->

## 一、步驟狀態

計畫 Step 1–14 全部完成並已在 `code-generation-plan.md` 打勾；Step 15 即本檔、`traceability.json`、`source-manifest.json`。沒有在任何停損條件處停下：

| 停損條件（計畫第四節） | 實際 | 是否觸發 |
|---|---|---|
| 單一新元件需要結構性改動 | 三處修改皆為單一屬性或 Tailwind 色階 class | 否 |
| 新元件違規總數超過 10 筆 | 3 種違規、8 個節點次 | 否 |
| 頁殼節點取不到穩定選擇器（`D-04`） | 唯一一筆頁殼違規取得 `role=paragraph[name="…"]`（見第十一節第 5 點，**請審查者確認這個判斷**） | 否 |
| 交界類規則實際出現 | 第一次實跑零筆 | 否 |
| `npm audit` 新套件樹有 high／critical | 新套件樹零筆 | 否 |

最終結果：`a11y.spec.ts` **21 passed**（本機與 `CI=1` 各一次，皆 13.4s）。

## 二、Step 1 前提複驗

- `C-02`／`D-02` 表中的 test-id 逐一 `grep -rn` 於 `frontend/src`：全部存在。`memory-zone-semantic`／`memory-zone-episodic` 的字面命中為 0，原因是它們由 `MemoryZone.tsx:255` 的樣板字串 `` `memory-zone-${fragment}` `` 產生，`memoryLabels.ts` 的映射表確認三個片段為 `semantic`／`procedural`／`episodic`——不是缺失。
- 文字定位器：`正在載入專案…`（`ProjectDetailPage.tsx:283`）、`正在載入需求欄位…`（`OverviewTab.tsx:54`、`RequirementsTab.tsx:234`）、`載入中…`（`MembersListPage.tsx:163`、`MemberDetailPage.tsx:207`）皆存在。
- `playwright.config.ts`：`fullyParallel: false`、`workers: 1`、`retries: process.env.CI ? 1 : 0`、`timeout: 30_000`——未變。
- `ReselectionBanner.tsx:242` 仍為 `<div data-slot="reselection-banner">`。
- 記憶摘要籤的內容節點（`C-02` 留給本站指定）：`memory-summary-unavailable`（`MemorySummaryTab.tsx:11`）。

## 三、Step 2 執行器與單元專屬指令

`npm run build` ＋ `npx vite preview --port 4173 --strictPort`（背景）＋ `BASE_URL=http://localhost:4173 npx playwright test tests/e2e/memory-page.spec.ts`：**15 passed（12.9s）**，攔截層可用，不需 Docker。之後本單元只跑 `tests/e2e/a11y.spec.ts`（`unit-test-instructions.md` 第三節的指令），未再跑其他 spec。完成後已停掉 preview server。

## 四、Step 3 套件事實（`A11Y-S1`–`A11Y-S4`、`T-1`／`T-2`）

| 項目 | 值 |
|---|---|
| 選定版本 | `@axe-core/playwright@4.13.0`（帶入 `axe-core@4.13.0`） |
| 發布日 | `@axe-core/playwright` 4.13.0：2026-08-11T17:07:40Z；`axe-core` 4.13.0：2026-08-05T16:53:07Z。選定日 2026-10-17，分別滿 67／73 天 |
| 未選最新版的理由 | `latest` 為 4.14.0，發布於 2026-10-15，僅 2 天，不滿 14 天 |
| peer 範圍 | `playwright-core: ">= 1.0.0"`；已安裝 `playwright-core` 為 1.61.1（`@playwright/test` 1.61.1） |
| 授權 | 兩者皆 `MPL-2.0` |
| `package.json` 寫法 | `"@axe-core/playwright": "^4.13.0"`，位於 `devDependencies`；`dependencies` 不含它 |
| lockfile | `node_modules/@axe-core/playwright` 與 `node_modules/axe-core` 兩個條目皆有 `integrity`（sha512）、`dev: true`；`git diff --stat` 為 `package.json +1`、`package-lock.json +24` |
| `npm audit`（全量後過濾） | 全樹 5 筆（high 3：`brace-expansion`、`browserslist`、`source-map-js`；moderate 1：`baseline-browser-mapping`；low 1：`dompurify`）。**新套件樹 0 筆**：`axe-core` 無任何相依，新樹只有這兩個套件，故 5 筆必然是既存的 |

> 現況（2026-11-08 補記，合併前必修第 40 列 (f)）：本節的 `^4.13.0` 已過時，現為精確 `"4.13.0"`；見第十七節第 5 小節現況表（第十八節更新 test 數與掃描點數）。

**過程中的一次修正**：第一次以 `npm install --save-dev @axe-core/playwright@^4.13.0` 安裝時，caret 範圍被解析成 4.14.0（違反 14 天規則）。改以精確版本 `@4.13.0` 重裝，npm 仍以預設 save-prefix 寫入 `^4.13.0`，而 lockfile 鎖在 4.13.0。**後果要知道**：CI 用 `npm ci`，以 lockfile 為準，不受影響；但任何人日後以 `npm install`（非 `ci`）重解析時可能浮到 4.14.x。

## 五、Step 10 第一次實跑的完整違規清單（`A11Y-S9` 規則 3 的比對基準）

以**空的** `a11y-baseline.json` 跑 21 個 test：18 個掃描點全紅（3 個非掃描 test 綠）。18 個結果檔都在斷言前寫出（`D-03` 的先寫檔順序在實跑中成立）。彙整自 `test-results/a11y-scan-results/*.json`：

**合計 25 個節點次、4 種（規則 ＋ 穩定選擇器）組合**：

| # | 規則 | 節點（穩定選擇器） | 是否在新元件根節點內 | 出現的掃描點 | 節點次 | 分類（計畫第四節） |
|---|---|---|---|---|---|---|
| 1 | `aria-prohibited-attr` | `span[aria-label="連線中"]`（`ContextBar.tsx` 的連線中骨架） | 是（`brain-entry-page`） | 01、13、14 | 3 | 第 1 類：新元件，修掉 |
| 2 | `select-name` | `[data-testid="member-detail-role-select"]` | 是（`member-detail-page`） | 10、15 | 2 | 第 1 類：新元件，修掉 |
| 3 | `color-contrast` | `[data-testid="reselection-banner-acknowledge"]`（白字 on `#e17100`，3.19:1） | 是（`[data-slot="reselection-banner"]`） | 13、14、18 | 3 | 第 1 類：新元件，修掉 |
| 4 | `color-contrast` | Sidebar 空選單提示 `<p>`「目前角色尚未開放任何功能選單，請聯絡管理員調整權限。」（`#99a1af` on 白，2.6:1）；第一次實跑時穩定選擇器為 `null`，見下方說明 | 否 | 01–17 | 17 | 第 2 類：頁殼既有，列入基準 |

> 現況（2026-11-08 補記，合併前必修第 40 列 (f)）：上表第 4 筆的「2.6:1、列入基準」已過時——`Sidebar.tsx` 該提示已改 `text-gray-600`，基準現為 0 筆（`"entries": []`）；見第十七節第 5 小節現況表。

第 18 點只掃橫幅外層（`include`），所以第 4 筆沒有出現在第 18 點。第一次實跑沒有任何交界類規則（第 3 類）出現。

**第 4 筆的處置**：
- **它確實是頁殼既有節點**：`git log -S` 顯示該字串由 `af73f03f`（2026-07-11，`feat(rbac)`）引入；出現條件 `!showCoreSection && !showAdminSection`（`Sidebar.tsx:324`）只看 A1／A3／J3a／J3b，本 intent 沒有改動這個節點或其條件。它在每個掃描點都出現，是因為攔截層的 `/me` 只給各頁所需的 K 系列權限——真實上只具 K 系列權限的使用者也會看到它。
- **第一次實跑時選擇器為 `null`**：我寫的 role 對照表漏了 `p`。`<p>` 的隱含 role 是 `paragraph`（HTML-AAM），`D-04` 定義的名稱取法是「`aria-label`、`aria-labelledby` 指向的文字或其文字內容」，依此可得 `role=paragraph[name="目前角色尚未開放任何功能選單，請聯絡管理員調整權限。"]`——不依賴位置，符合 `C-03`。把 `p: 'paragraph'` 補進對照表後，該筆以此選擇器列入基準。
- 基準檔現為 **1 筆**（`frontend/tests/e2e/a11y-baseline.json`），附 `reason`。
  - 現況（2026-11-08 補記，合併前必修第 40 列 (f)）：此「1 筆」已過時，基準現為 0 筆；見第十七節第 5 小節現況表。

### 修改的新元件（重開已交付單元，限無障礙屬性）

| 檔案（單元） | 修改 | 修掉的違規 | 不改的東西 |
|---|---|---|---|
| `frontend/src/components/brain/ContextBar.tsx:53`（U14） | 連線中骨架 `<span>` 加 `role="img"`（`aria-label` 保留） | `aria-prohibited-attr`（`aria-label` 不得用在沒有有效 role 的 `span`） | 行為、test-id、版面、class 皆不變。注意：此檔在本 worktree 為**未追蹤**（U14 尚未 commit），本單元的改動會隨 U14 的檔案一起進版控 |
| `frontend/src/pages/MemberDetailPage.tsx:239`（U24） | 角色下拉加 `aria-label="專案角色"`（與其上方 `<h2>專案角色</h2>` 同字） | `select-name` | 行為、test-id、版面不變 |
| `frontend/src/components/membership/ReselectionBanner.tsx:112`（U24） | 確認鈕 `bg-amber-600 → bg-amber-700`、`hover:bg-amber-700 → hover:bg-amber-800` | `color-contrast`（白字 3.19:1 → amber-700 約 5.0:1，以 Tailwind v4 的 amber-700 ≈ `#bb4d00` 計算；修後重跑 axe 已不再回報） | 行為、test-id、版面不變；hover 色同步加深一級，避免 hover 態比靜止態淺 |

## 六、Step 11 突變驗證（`M1`–`M12`）

每一道：備份 → 套用 → 以檔案雜湊與 grep 確認確實改到 → 跑 → 還原 → 確認雜湊與原檔**位元組相同** → 再跑確認綠。改到 `src/` 的兩道（M5、M9）套用與還原後各重建一次。

| # | 突變 | 指定的紅燈層 | 實際紅燈訊息 | 還原後 |
|---|---|---|---|---|
| M1 | 第 03 點拿掉 `reselections(page)`（橫幅查詢的具體 handler） | 隔離層 | `[隔離層] 有未被具體 handler 接管的 /api 請求`：`GET /api/membership/reselections/pending` | 綠 |
| M2 | 拿掉 `/api/brain/ws` 的 `routeWebSocket` | 隔離層，且不得連到真實閘道 | `[隔離層] 有未被具體樣式接管的 WebSocket`：`ws://localhost:8000/api/brain/ws`（由萬用兜底在連線前關閉並記錄） | 綠 |
| M3 | 第 03 點 `/me` 改為無權限（導向 `/403`） | 就緒層 | `[就緒層] projects-list-page 須可見`（element(s) not found） | 綠 |
| M4 | 第 09 點（成員視角）`/me` 改為 K3 view+edit | 就緒層 | `[就緒層] member-list-invite-button 須不存在`（Received: 1） | 綠 |
| M5 | `MemoryPage.tsx` 在 `memory-page` 內加一個無 `alt` 的 `<img>`（重建） | 掃描層 | `[掃描層] 02-memory 有基準以外的 WCAG 2.1 AA 違規`：`image-alt`、`inNewRoot: true` | 綠（還原後重建） |
| M6 | 基準加一筆 `select-name` ＋ `[data-testid="member-detail-role-select"]` | 規則 1 的 test | `規則 1：… 落在新元件（data-testid="member-）` | 綠 |
| M7 | 基準加一筆實際不存在的 `image-alt` ＋ `#a11y-m7-does-not-exist` | 過期檢查 test | 全量跑：20 passed、只有「基準清單沒有過期條目」紅：`基準清單有過期條目（已不再出現），請刪除` | 21 passed |
| M8 | 基準加一筆 `duplicate-id-aria` | 規則 5（規則 1 的 test） | `規則 5：duplicate-id-aria 屬交界類規則，不得進基準` | 綠 |
| M9 | `EntryPage.tsx` 加一個 `position:absolute`、寬 2000px 的元素（重建） | 手機寬度 test | `375px 寬度下文件橫向溢出：{"scrollWidth":2000,"clientWidth":375}` | 綠（還原後重建） |
| M10 | 第 05 點第一次嘗試拋錯（暫時性程式修改，以 `A11Y_M10` 環境變數開啟），以 `CI=1` 跑使 `retries: 1` 生效 | 過期檢查**不得**誤紅 | 執行順序：`05` 失敗 → **緊接著** `05 (retry #1)` 通過 → `06`…→ 過期檢查通過。結果 **1 flaky、20 passed**（`stats.unexpected` 為 0） | 21 passed |
| M11 | 第 18 點的 `include` 改回 `reselection-banner-host` | `D-01` 的「就緒 test-id 必須在 include 子樹內」 | `[就緒層] reselection-banner-host 須可見`，定位器為 `locator('[data-testid="reselection-banner-host"]').getByTestId(…)`（根節點不是自己的子孫，確認鈕亦不在其內） | 綠 |
| M12 | 第 07 點的 `ready` 清空 | 靜態檢查 | `M12：掃描點 07-project-create 的就緒清單為空` | 全量 21 passed |

**M10 的結論**：重試排在失敗的 test 之後、同檔後續 test 之前，寫檔式過期檢查不會誤紅。**`D-03` 備案不需要，`playwright.config.ts` 未改動。**

**M6 揭露一個本站自己補上的缺口**：只比對根節點 test-id 字串時，`member-detail-role-select` 不含 `member-detail-page`，M6 會在靜態檢查**通過**。所以靜態規則 1 加比對新元件的 test-id 前綴（見第十一節第 4 點）；加前綴之前我先實查既有頁面與 Sidebar／Layout 的既有部分都沒有這些前綴。

## 七、Step 12 規則分類實查（`D-06`）

以 `axe-core` 4.13.0 的 `axe.getRules(['wcag2a','wcag2aa','wcag21a','wcag21aa'])`：實際執行 **69 條**規則。`C-03` 規則 5 清單逐條：

| 規則 | 在 WCAG 2.1 AA 標籤下執行？ | 標籤 |
|---|---|---|
| `landmark-unique`、`landmark-no-duplicate-banner`、`landmark-no-duplicate-main`、`landmark-one-main` | 否 | `cat.semantics, best-practice` |
| `region` | 否 | `cat.keyboard, best-practice, …` |
| `heading-order`、`page-has-heading-one` | 否 | `cat.semantics, best-practice` |
| `duplicate-id-aria` | **是** | `cat.parsing, wcag2a, wcag412, …` |
| `list`、`listitem` | **是** | `cat.structure, wcag2a, wcag131, …` |

**與 `C-03` 的陳述一致**（landmark／region／heading 類屬 best-practice、閘門抓不到，交 `build-and-test` 人工；`duplicate-id-aria`／`list`／`listitem` 會執行）。Step 8(a) 的清單**不需調整**，十條全數保留——它擋的是「有人手動把這類條目寫進基準」，與規則當下是否執行無關。附帶：實際執行的規則含 `bypass`（WCAG 2.4.1），它與 landmark 有關但不在規則 5 清單內，第一次實跑沒有出現。

## 八、Step 13 環境與建置檢查

| 檢查 | 結果 |
|---|---|
| `npm run lint` | **0 errors、2 warnings**（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344`，皆 `exhaustive-deps`），與本單元動工前相同，未增加。`team.md` 記載的「3 warnings」已過時（本單元前後都是 2） |
| `npx eslint tests/e2e/a11y.spec.ts` | 無輸出（通過；含 tests 區塊的手寫 WS 訊框禁令） |
| `npm run build`（含 `tsc -b`） | 通過 |
| `grep -rn "axe-core" frontend/src` | **0** |
| `dist/` 內 axe | 字面子字串 `axe` 有 2 檔命中，**皆為 Tailwind class `leading-relaxed`**；以整字 `axe`、`AxeBuilder`、`axe.run`、`axe-core`、`dequelabs` 搜尋皆 **0**。`A11Y-S1` 要防的「測試工具被打包進產品」不成立 |
| `python3 scripts/validate_repo_contract.py` | passed |
| `python3 scripts/validate_env_contract.py` | passed |
| `python3 scripts/tcms_validate.py --spec frontend/tests/e2e/a11y.spec.ts` | **21/21 通過，ERROR 0、WARN 0**（第一次跑時第 19 案的步驟預期缺具體證據，已補） |
| `a11y.spec.ts` 耗時（`H-2`） | Playwright 回報 **13.4s**（`time -p`：real 14.20s），本機 `vite preview`、21 個 test、1 worker。CI 的 compose stack 與 GitHub runner 上的實際耗時未量測，交 `build-and-test` |

## 九、計畫第三節帶入事項的結果

| 事項 | 結果 |
|---|---|
| `UG-5`／`H-1`：`/admin/*` | 維持不掃（`[DM:D11]`=A）。第 18 點刻意選 `/cost` 而非 `/admin/*` 作為非入口落地頁，避免與此決定交纏 |
| `H-2`：時間預算 | 本機實測 13.4s（第八節）；`ui-regression` 整體預算交 `build-and-test` |
| `H-3`／`C-06`：`[人工]` 項目 | `AC-A11Y.2` 已由第 19 個 test 自動化並通過突變 M9；`AC-A11Y.1`、O-1、O-12、R-4、landmark 唯一與標題層級、`OPEN-ND24-1` 交 `build-and-test` ＋ `tcms-test-cases` |
| `H-4`：上游無 `NFRx.y` | `traceability.json` 以 `A11Y-S*`／`C-*`／`D-*`／`AC-A11Y.*`／`N-9` 為上游 id；sensor 的 no NFRx.y 照實保留 |
| `D-07`：契約 `brain-*` 前綴落差 | 不改契約、不改程式 id。就緒規格以實際程式 id 為準（`projects-list-page`、`member-*` 等）。交 `build-and-test` 列為跨單元一致性發現 |
| 證據留存缺口 | 不改 `ui-regression`。綠燈時 axe 結果零留存的現況不變，交 `build-and-test` 判定是否補 artifact 上傳 |

## 十、檔案清單

| 檔案 | 動作 |
|---|---|
| `frontend/package.json` | 改：`devDependencies` 新增 `@axe-core/playwright: ^4.13.0` |
| `frontend/package-lock.json` | 改：新增兩個條目（+24 行） |
| `frontend/tests/e2e/a11y.spec.ts` | 新：1058 行，`describe('U17 a11y gate')`，21 個 `test()` |
| `frontend/tests/e2e/a11y-baseline.json` | 新：1 筆基準 |
| `frontend/src/components/brain/ContextBar.tsx` | 改：1 個屬性（U14） |
| `frontend/src/pages/MemberDetailPage.tsx` | 改：1 個屬性（U24） |
| `frontend/src/components/membership/ReselectionBanner.tsx` | 改：2 個色階 class（U24） |

> 現況（2026-11-08 補記，合併前必修第 40 列 (f)）：上表「1058 行／21 個 `test()`」「1 筆基準」「`^4.13.0`」已過時——現為 28 個 `test()`、基準 0 筆、精確 `"4.13.0"`；見第十七節第 5 小節現況表與第十八節。

`frontend/playwright.config.ts`、任何 workflow 檔、後端、DDL、環境變數、secret：**零變更**。

**暫時被改過、已還原的檔**（不在 `source-manifest.json`）：突變 M5 改過 `frontend/src/pages/MemoryPage.tsx`、M9 改過 `frontend/src/pages/EntryPage.tsx`，皆已還原為**位元組相同**（sha256 前綴 `bef9f34086aa`、`61aa958be1ca` 套用前後一致）。內容未變，但檔案 mtime 已變；若引擎的工作區指紋把 mtime 算進去而判為「未宣告的變更」，那是這兩次突變的痕跡，不是本單元的交付。

## 十一、關鍵實作決定

1. **四層結構**照 `security-design.md` 第一節實作：`isolate()`、每點的 `stage`／`interact`、`ready()`、`scan()`，由 `runScan()` 串起。18 個掃描點是一張資料表 `SCANS`，但 21 個 `test()` 都是逐字寫出的獨立呼叫——每個 `test()` 前都要有自己的規格註解，`tcms_sync.py` 的 `parse_spec` 只認 `test('…'` 前一個 `/**` 區塊，迴圈產生的 test 拿不到註解。
2. **隔離層斷言兩次**：就緒之後、掃描之前一次（漏接已發生時掃到的是降級畫面，掃描結果無意義），test 結尾一次。就緒層失敗時若已有漏接記錄，改以隔離層的訊息報紅，讓 M1 這類突變紅在正確的層。
3. **入口頁的閘是 `K1 view`**（`App.tsx` 的 `DefaultRedirect`），不是 `C-07` 寫的 `C1 view`——依 `C-02` 的「名稱已變以程式為準」比照處理。第 1、13、14、19 點帶 K1；第 18 點**不帶** K1、只帶 `C1 view`，使 `DefaultRedirect` 落在 `/cost`。`/cost` 只打一支 `GET /api/cost/v1/sets`，是 API 面最小的既有落地頁（`security-design.md` 第三節允許本站選擇並記錄）；比較過 `/assessment`（16 處 API 呼叫）與 `/workspace`（含 draw.io 內嵌與 collab WebSocket）。
4. **基準規則 1 比 `C-03` 更嚴，兩處**：(a) 執行期與靜態檢查都把 `[data-slot="reselection-banner"]` 當新元件根節點——`D-01` 查出確認鈕、展開鈕、專案清單都在 host 之外，只收 host 會讓這些 U24 節點被當成頁殼收進基準；(b) 靜態檢查加比對新元件 test-id 前綴（`brain-`、`memory-`、`project-`、`projects-`、`member-`、`members-`、`invite-`、`remove-confirm-`、`reselection-banner`、`requirements-`），理由見第六節 M6。以 role＋名稱表達的新元件子孫，靜態檢查仍擋不住，由掃描層的執行期 `closest()` 判定擋下——基準只在「有穩定選擇器、不在新元件根節點內、規則不屬交界類」三者同時成立時才豁免一筆。
5. **穩定選擇器的 role 對照表含 `p → paragraph`**。這是第四節唯一一筆頁殼基準能取得穩定選擇器的原因。我判定這是 `D-04` 定義的忠實實作（隱含 role ＋ 文字內容），不是繞過停損條件；**但它是一個判斷，請審查者確認**。若審查者認為文字內容當名稱不夠穩定，替代做法是 `D-04` 給使用者的兩個選項：在 Sidebar 該節點補屬性，或該掃描點以 `exclude()` 排除。
6. **第 09 點（成員視角）的旋鈕是 `/me` 的 K3 edit**：自身仍是 `project_admin`、但只有 `K3 view`，兩段式 `canManage` 判定為否。這樣突變 M4 能照字面執行（改 `/me` 即讓邀請鈕出現）；若改用 per-project 角色 `member`，改 `/me` 不會讓邀請鈕出現，M4 會變成無效突變。畫面上兩種造法相同。
7. **大腦 WebSocket 用空 handler**（`security-design.md` 第二節）：`brain-entry-page` 在握手未完成時就渲染，不需要送 `ready` 訊框。代價是入口頁以 `ContextBar` 的「連線中」狀態被掃描——第一筆違規正是在這個狀態抓到的；已連線狀態的 `ContextBar` 沒有被掃描（見第十四節）。
8. **專案詳情三籤先落在另一籤再點目標籤**（`D-02`「點 `project-tab-<key>` 切換」），並斷言該籤 `aria-selected="true"` 與兩段載入文字為 0。
9. **第 2 點的就緒片段只用 `memory-zone-semantic`**（`D-02` 允許三者中至少一個；語意區給一筆資料）。
10. **掃描結果檔**寫在 `testInfo.project.outputDir/a11y-scan-results/<掃描點>.json`；Playwright 每次執行開始時會清掉 `outputDir`，所以不會殘留前一次的結果。只跑部分 test（`-g`）時過期檢查會因檔數不足而紅，這是設計上的大聲失敗，不是缺陷。
11. **M10 的注入是暫時性程式修改**（以 `A11Y_M10` 環境變數開啟），驗證完已還原；spec 內**沒有**留任何測試專用的環境變數鉤子。
12. **本機建置的 API／WS 基底指向 `localhost:8000`**（`frontend/.env` 的 `VITE_API_BASE_URL`；M2 的漏接 URL 即 `ws://localhost:8000/api/brain/ws`），不是 preview 的 4173。攔截樣式不綁主機，所以隔離照樣成立；CI 的 compose build 為同源。
13. **`D-05`**：沒有依賴 `page.on('websocket')`，WebSocket 漏接的證據是兜底 handler 內的記錄（M2 實證）。

## 十二、與計畫／上游的偏離

| # | 偏離 | 依據 |
|---|---|---|
| 1 | 入口頁閘以 `K1 view` 實作，非 `C-07` 字面的 `C1 view` | 程式為準（第十一節第 3 點） |
| 2 | 規則 1 的根節點與靜態比對比 `C-03` 更嚴 | 第十一節第 4 點；只會讓更多條目被擋，不會讓任何條目被放行 |
| 3 | 計畫寫「每一層先實作、再寫並跑該層的測試」；本單元的四層都在同一支 spec 內，實際做法是四層寫完後以 Step 10 一次實跑，再以 M1–M12 逐層打 | 本單元沒有產品程式可供分層測試；逐層的驗證由突變表承擔（每一層至少一道突變紅在該層） |
| 4 | Step 10 之後對 spec 做了三次收緊（role 對照表補 `p`、隔離層掃描前斷言、規則 1 前綴），每次收緊後都重跑全量綠 | 第六節 M2、M6 與第五節 |

沒有改 `playwright.config.ts`、沒有改其他單元的 spec、沒有改 `unit-test-instructions.md`、沒有 commit／push。

## 十三、`ADR-0006` 四面向

沿用 `security-requirements.md` 的判定：四面向皆不適用，三個變形分別由隔離層（Network exposure：M1、M2 實證不連外、不連真實閘道）、就緒層（IAM：M3、M4 實證掃錯視角會紅）、掃描層附件（Audit logging：只附 `violations` 與 `incomplete`）承接。token 為固定假值 `a11y-fake-token`（`A11Y-S6`）。本單元新增的唯一供應鏈面是兩個 dev 套件，`npm audit` 零筆、lockfile 帶 `integrity`。PBT 不適用（固定狀態集合）。

## 十四、交給 `build-and-test` 的開放項

1. **重跑 U14／U24 的既有 spec**：本單元改了 `ContextBar.tsx`、`MemberDetailPage.tsx`、`ReselectionBanner.tsx` 的屬性與 class，依派工規則**沒有**跑 `entry-page.spec.ts`／`member-pages.spec.ts`。預期不受影響（三處皆非 test-id、非行為），但未實證。
2. **`ui-regression` 整體時間預算**（`H-2`）：本機 13.4s；CI 上未量測。
3. **`[人工]` 項目**：`AC-A11Y.1`（純鍵盤）、O-1、O-12、R-4、landmark 唯一、標題層級（`region`／`heading-order` 等 best-practice 規則閘門抓不到，第七節實證）、`OPEN-ND24-1`（兩個 `role="status"` 的播報先後）、§27 的 `/admin` 錯誤態。
4. **`D-07` 契約前綴落差**：`K-13`／`K-19`／`K-20` 的 `brain-*` 宣稱與實際 test-id 不符，交使用者裁決改契約或改程式。
5. **證據留存缺口**：`ui-regression` 無 artifact 上傳，綠燈時 axe 結果零留存。
6. **手機寬度檢查的射程**：`Layout` 的根容器 `overflow-hidden`、內容容器 `overflow-x-hidden`，**文件流內**的過寬內容會被裁切而不是產生橫向捲動，所以只量 `documentElement` 抓得到絕對定位造成的溢出（M9），抓不到「內容在 375px 被裁掉」——後者是 WCAG 1.4.10 Reflow 的問題，`AC-A11Y.2` 字面（無橫向捲動）沒有涵蓋。建議人工在 375px 檢視入口頁內容是否完整。
7. **入口頁只在「連線中」狀態被掃描**：已連線、無作業對象、獨立模式等 `ContextBar` 狀態沒有被 axe 掃過（第十一節第 7 點）。
8. **既存 `npm audit` 5 筆**（3 high）不在本單元範圍；其中 `dompurify`（low）屬產品相依鏈，另案處理。
9. **頁殼既有違規**：Sidebar 空選單提示的對比 2.6:1，已列入基準；修它屬頁殼改動，不在本 intent 範圍。
   - 現況（2026-11-08 補記，合併前必修第 40 列 (f)）：本點已過時——該提示已改 `text-gray-600`、基準為 0 筆，退步會讓掃描層變紅；見第十七節第 5 小節現況表。
10. **`team.md` 的 lint 基準數過時**（記 3 warnings，實為 2），留待下一輪 practices-discovery。

## 十五、Sensor 結果

| Sensor | 結果 |
|---|---|
| `aidlc-sensor-traceability.ts` | `pass: false`，`findings_count: 1`，`reason: upstream ID set is empty for unit "a11y-gate"`；`gaps`／`orphans`／`invalid_entries`／`invalid_targets` 皆空。該 sensor 的上游集合只取三個來源：本單元故事的 AC（本單元沒有故事）、`nfr-requirements` 內的 `NFRx.y`（本單元用 `A11Y-S*`）、`functional-design/rules.md` 的 `BRx.y`（本單元沒有）。這就是計畫第八節第 5 點揭露的「no NFRx.y」，照實保留，**不補假父 ID**。`traceability.json` 本身：26 OK（每個 target 皆為單一存在的檔案路徑）、1 N/A（`C-05`）、2 Deferred（`D-07`、`AC-A11Y.1`） |
| `aidlc-sensor-required-sections.ts`（本檔） | `pass: true`，`findings_count: 0` |
| `aidlc-sensor-linter.ts`（`tests/e2e/a11y.spec.ts`） | `pass: true`，0 errors、0 warnings |

## 十六、Step 16 回歸驗證（code-generation Request Changes 2026-10-20 之後）

執行時間 `2026-10-24T13:25:57Z` 前後（`date -u` 取值）。本輪**不改程式**：只對其他單元本輪修正後的生產建置重跑本單元的 spec。

**指令**（依序，皆在 repo 根目錄執行）：

1. `npm --prefix frontend run build`（`tsc -b && vite build`，成功；僅既有的 chunk 大小警告）
2. `npm --prefix frontend run preview -- --port 4173 --strictPort`（背景執行；`curl` 首頁回 `200`）
3. `BASE_URL=http://localhost:4173 frontend/node_modules/.bin/playwright test --config frontend/playwright.config.ts tests/e2e/a11y.spec.ts --retries=0`
4. 停止 preview 伺服器

**結果**：`Running 24 tests using 1 worker` → **`24 passed (17.0s)`**，0 failed、0 flaky、0 skipped。基準清單兩個檢查（「基準清單只收頁殼既有違規」「基準清單沒有過期條目」）皆綠，過期檢查未誤紅。

**數量與本檔前文的差異**：前文（第一節至第十五節）寫的是 21 個 `test()`／18 個掃描點；本次實跑為 24 個 `test()`：21 個掃描點（`01`–`18`、`20`–`22`，其中 `20 入口頁已連線狀態`、`21 切換對象選單預設態`、`22 切換對象選單建立錯誤態` 為前文之後加入）＋ 1 個手機寬度檢查（`19`）＋ 2 個基準清單檢查。掃描結果檔 `frontend/test-results/a11y-scan-results/*.json` 本次寫出 **21** 個，以 `grep -L '"entries": []'` 查得非空者 **0** 個——即 21 個掃描點全部零違規條目。

**基準清單**：`frontend/tests/e2e/a11y-baseline.json` 執行前後 sha256 皆為 `7c1051f6e2bc3943b7c1dbe4da229694455681b8875a346c99279e555edb733f`，內容為 `"entries": []`，**未新增任何條目**。`git status` 顯示該檔與 `a11y.spec.ts` 皆無異動。

**新增違規**：無。故第四節第 1 類（應修元件）的停損條件未觸發，本單元未改任何他單元元件。

**新狀態的可達性（照實記錄，本步不新增掃描點）**：

| 新狀態 | 落點 | 是否被現有掃描點掃到 | 依據 |
|---|---|---|---|
| 系統提示列 `data-testid="brain-system-notice"` | `frontend/src/components/brain/ConversationView.tsx:51-59` | **否** | 只在對話紀錄有 `kind: 'notice'` 項目時渲染；spec 的大腦 WebSocket 接管（`a11y.spec.ts:187`、`:382-385`、`:397-400`）只是空 handler 或在 `hello` 後回送連線快照，沒有任何掃描點送出使用者訊息或非輪次錯誤訊框 |
| 「這句沒有送達」（`USER_INTERRUPT_TEXT.rejected`） | `ConversationView.tsx:12`、`:24-26` | **否** | 需要對話中先有一則使用者訊息、再被伺服器以非輪次錯誤拒絕；同上，沒有掃描點產生使用者訊息 |
| 「查不到這個專案」 | `ProjectDetailPage.tsx:54`（以及 `MembersListPage.tsx` 經 `membershipApi.ts:91` 的固定句） | **否** | 觸發條件為 404；spec 唯一的非 200 回應是 `a11y.spec.ts:608` 的 `projectsApi(page, { status: 500 })`（第 17 點專案清單錯誤態），沒有任何掃描點回 404 |

結論：本次全綠只證明**既有 21 個畫面狀態**在本輪修正後沒有出現新違規；三個新狀態**沒有被任何掃描點覆蓋**，axe 對它們零檢查。是否新增掃描點不屬本步範圍，交 `build-and-test` 與使用者決定。

`source-manifest.json`、`traceability.json` 無檔案變更，未動。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-26T06:11:06Z -->

以既有實作逐步查驗已核可計畫，未修改任何程式碼。

- **計畫勾選**：15／16。未勾 Step 14：計畫字面要求每個 `test()` 都加 `@note`，現行 27 個 test 中 12 個（03、04、06、08、11、12、13、14、15、16、17、22）沒有 `@note`，HEAD 版本同樣缺，屬既存狀況；撰寫標準 §4.4 把 `@note` 列為非必填，`tcms_validate.py --spec a11y.spec.ts` 27/27、ERROR 0、WARN 0。其餘註解齊全（`@api` 0、`@ui` 27 個皆對得上 `App.tsx`）。另：第 21、22 點（U16 加入）的 `@story` 為 `US9.2`，非計畫寫的 `N-9`。
- **測試**：
  - 後端全套 1319 OK（skipped=3），無偶發失敗。
  - 前端 `npm run lint` 0 errors（2 個既存 warning）；兩份 tsconfig `--noEmit` 通過；`vite build` 輸出至 scratchpad。
  - `vite preview` 跑 `a11y.spec.ts`：27 passed（24 掃描點＋手機寬度＋2 個基準檢查），24 個結果檔皆無違規；加 `CI=1` 再跑亦 27 passed（約 19 秒）。`memory-page.spec.ts` 18 passed。
  - 真實 compose stack：本機無 Docker，未跑。
  - `validate_repo_contract.py`、`validate_env_contract.py` 通過；repo 未留下快取或建置產物。
- **閘門與依賴**：`ui-regression` 以整套 Playwright 執行會撿到 `a11y.spec.ts`，post-step 讀 `pw-report.json` 的 `.stats.unexpected` 非 0 或報告不存在即 `exit 1`；無專屬 a11y 步驟，`ci.yml` 不跑 Playwright。`@axe-core/playwright` 4.13.0 精確釘選於 devDependencies，lockfile 兩條目皆 `dev: true` 且有 integrity；產品建置內 axe 字樣 0。發布日與 `npm audit` 需連 registry，本輪未重驗。
- **規則集**：axe-core 4.13.0 在 WCAG 2.1 AA 四標籤下為 69 條；landmark 四條、`region`、`heading-order`、`page-has-heading-one` 不執行，`BOUNDARY_RULES` 十條保留。
- **突變抽驗**（scratchpad 鏡像，repo 未動，還原後 spec sha256 與 repo 一致）：A 重現 Sidebar `text-gray-400` 違規 → 21 紅（include 範圍外的點維持綠，符合預期），餵給 gate 腳本 exit 1；B 拿掉 `/api/brain/ws` 具體接管 → 隔離層紅；C 基準清單加三筆 → 規則 1、5 與過期檢查皆紅；D gate 腳本對 unexpected=0／1／缺檔分別 exit 0／1／1。
- **ADR-0006 四面向**：皆不適用（無權限、資料、網路或稽核變更；隔離層使測試不連外，突變 B 實證；附件只含 `violations`／`incomplete`，token 為假值）。
- **其他合併前必修列的影響**：第 23 列 (c) 對話框焦點圈限 axe 無規則可偵測，本閘門擋不到，修完後須重跑第 11、12、15 點；(a) 非數字 `projectId` 的固定句狀態目前無掃描點覆蓋。第 26 列 R-02 的「真實 stack 從未執行」同樣適用本 spec（未在 compose stack 或 CI runner 跑過，CI 耗時未量測）。Sidebar 兩個 `<nav>`（`:162`、`:218`）缺 `aria-label` 對應 `landmark-unique`（best-practice），在本閘門規則集下不執行，只能人工驗證。
- **本摘要與追溯文件的過時處（原文不回改）**：各處「21 test／18 點／基準 1 筆／`p→paragraph`」已過時，現為 27 test／24 點／基準 0 筆；§十六的 24 test 現為 27；`ContextBar.tsx:53` 現為 `:109`。`traceability.json` 的 A11Y-S9、A11Y-S10、N-9、D-04 note 數字同樣過時，且上游 id 未涵蓋第 21、22 點對應的 U16 項目。`source-manifest.json` 未列 review-02 時本單元改過一個 class 的 `ConversationView.tsx`（該檔歸 entry-page-ui）。計畫與 unit-test-instructions 的「讀回 18 檔」現為 24。

## 十七、共用檔異動後的重新驗證與補審（計畫九之二，2026-10-31）

<!-- 寫入時間：2026-10-31T14:09:40Z（date -u 取值） -->

本輪**不改任何程式、測試、共用文件**。只寫本節、`traceability.json` 四則 note、計畫的勾選。

> 範圍補記（2026-11-08，合併前必修第 40 列 (g)、review-04 R-15）：上句漏列一處——本輪另在 `unit-test-instructions.md` 第三節末新增「現況註記（2026-10-31，共用檔重驗輪）」一段（副本執行方式），屬計畫九之二指定引用的內容。

### 1. 共用檔重驗（收據 `reviewed-source-97f17c16ecf7.tsv`，8 檔）

逐檔 `shasum -a 256` 對收據：**7 檔逐位元相同**（`package-lock.json`、`package.json`、`Sidebar.tsx`、`ContextBar.tsx`、`ReselectionBanner.tsx`、`a11y-baseline.json`、`a11y.spec.ts`）；**1 檔變動**：`frontend/src/pages/MemberDetailPage.tsx`，收據 `ad267843…b7f7` → 現況 `0e513bb2…4226`。

**收據版本可由 git 精確重建**：`git show e2771a0:frontend/src/pages/MemberDetailPage.tsx | shasum -a 256` 為 `ad267843…b7f7`，與收據逐位元相同；`7a50a40`（HEAD）版本為 `0e513bb2…4226`，與工作樹相同（`git status` 該檔無異動）。故收據之後的改動**恰為** `git diff e2771a0 7a50a40`，不需 hunk 子集重建、也不需「無法證明為子集」的退路。該 commit 為合併前必修第 23 列（`member-pages-ui`）：(a) 非數字 `projectId` 改顯示固定句＋訊號、(c) 移出確認框加 `useDialogKeyboard`（Escape、焦點圈限）與關閉後焦點回「移出專案」鈕。

逐 hunk 判定（行號為現況檔）：

| 本單元負責或依賴的部分 | 現況 | 是否被碰到 |
|---|---|---|
| 第四節第 1 類的屬性修正 `aria-label="專案角色"`（本單元 `e2771a0` 唯一一行） | `:289`，緊接 `data-testid="member-detail-role-select"`（`:288`） | 否：`:288-289` 不在任何 hunk 內 |
| 掃描點 10 就緒 `member-detail-page` | `:246` | 否：`:247` 的 hunk 只把 `LiveRegion` 的 `message` 換成 `shownLiveMsg` |
| 掃描點 10 就緒 `member-detail-role-select` | `:288` | 否 |
| 掃描點 10 排除「載入中…」 | `:257` | **是（條件）**：渲染條件 `isLoading` → `showLoading`（`:138`＝`isLoading && !invalidProjectId`）。掃描點以數字 `PROJECT_ID` 進頁（`a11y.spec.ts:369`），`invalidProjectId` 為 false，兩者等值；文字與元素未變 |
| 掃描點 10 排除 `member-detail-error` | `:260` | **是（條件）**：`:259`／`:261` 的 `error` → `shownError`（`:139`），數字 id 下等值；test-id 本身那一行未變 |
| 掃描點 15 互動 `member-detail-remove` | `:378` | 否：`:377` 只新增 `ref={removeButtonRef}` |
| 掃描點 15 就緒 `remove-confirm-dialog` | `:392`（`role="dialog"` `:393`、`aria-modal="true"` `:394`） | 否：`:391` 只新增 `ref={confirmDialogRef}`；`:406` 取消鈕 `onClick` 改呼叫 `closeConfirm` |
| `ReselectionBanner.tsx` 的 `data-slot` | `ReselectionBanner.tsx:242`，該檔與收據逐位元相同 | 否 |
| `a11y-baseline.json` 條目所指節點 | 基準 `"entries": []` | 不適用：無條目 |

結論：沒有任何 hunk 移除或改寫本單元的屬性修正、依賴的 test-id 或文字定位器；兩處條件改寫在掃描點的數字 id 下語意等值。新增的焦點圈限只改鍵盤行為（axe 無對應規則），掃描點 15 的 DOM 只多兩個 `ref`（不輸出屬性）。以下回歸實跑作為行為面的補強。

### 2. 回歸（副本）

副本：`rsync -a` 實體複製 `frontend/` 至 scratchpad 的 `a11y-copy/frontend`（排除 repo 內既存的 `dist`、`test-results`、`junit.xml`、`pw-report.json`、`node_modules/.tmp`）；`find -type l -lname '/*'` 0 筆、所有 symlink 以 `realpath` 解析後落在 repo 內者 0 筆。`npm run build`、`vite preview --port 4173 --strictPort`、Playwright 皆在副本內執行，兩次 preview 用完即停（`curl` 回 `000`）。

| 檢查 | 結果 |
|---|---|
| `npm run build`（`tsc -b && vite build`） | 成功，僅既有 chunk 大小警告 |
| `dist/` 內 axe | 字面子字串命中 2 檔，逐筆看上下文皆為 `leading-relaxed`；與第八節判定相同 |
| `a11y.spec.ts`（`--retries=0`） | **27 passed（18.4s）**，0 failed／flaky／skipped |
| `a11y.spec.ts`（`CI=1`，`retries: 1` 生效） | **27 passed（18.4s）** |
| 掃描結果檔 | 24 個；`grep -L '"entries": []'` 0 個，即 24 個掃描點全部零違規 |
| `a11y-baseline.json` | 跑後 sha256 `7c1051f6…733f`，與收據相同，`entries` 仍為空，**未新增條目** |
| 過期檢查（「基準清單沒有過期條目」） | 綠，未誤紅 |
| `memory-page.spec.ts`（Step 2 執行器複驗） | 18 passed（12.1s） |
| `eslint .` | **0 errors、2 warnings**（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344` 的 `exhaustive-deps`，與重做段「2 個既存 warning」同數，未增） |
| repo 內（唯讀） | `grep -rn "axe-core" frontend/src` 0；`playwright.config.ts` 仍 `fullyParallel: false`（`:14`）、`retries: CI ? 1 : 0`（`:17`）、`workers: 1`（`:18`），`e2771a0..HEAD` 無 commit 改它 |

重做段第 252 行要求「第 23 列 (c) 修完後須重跑第 11、12、15 點」：本次全檔 27 案即含第 11、12、15 點，皆綠。

**repo 未留產物**：`find frontend backend -newermt "2026-10-31 13:50:00"`（本機時區）排除 `node_modules` 為 0 筆；`frontend/dist`、`frontend/test-results`、`frontend/node_modules/.tmp` 亦 0 筆。repo 內既存的 `frontend/dist`（10-27）、`test-results`（10-24）、`junit.xml`、`pw-report.json`（10-27）為前輪留下的 git 忽略檔，本輪未建立也未刪除。

### 3. review-03 各項現況

| ID | review-03 狀態 | 現況（附定位） | 處置 |
|---|---|---|---|
| R-01 | Resolved | 掃描點 20 仍在（`a11y.spec.ts:1184`），本次綠 | 無 |
| R-02 | Resolved | `Sidebar.tsx:325` 為 `text-gray-600`；基準為空 | 無 |
| R-03 | Resolved | 基準為空，無 `role=paragraph` 鍵 | 無 |
| R-04 | Resolved | `package.json:25` 為 `"4.13.0"`（精確） | 無。第四節第 40 行與第十節第 140 行仍寫 `^4.13.0`，為過時陳述，以本列為準 |
| R-05 | Unresolved | `unit-test-instructions.md` 對 `incomplete` 0 命中；`ui-regression` 仍無 artifact 上傳 | **仍成立**。需改共用測試說明或 workflow → 已知限制，見第 6 小節 |
| R-06 | Unresolved | `MemberDetailPage.tsx:289` 仍是 `aria-label` 與上方標題同字各自維護；`ContextBar.tsx:109` 仍為 `role="img" aria-label="連線中"` | **仍成立**（可選建議）。需改程式 → 已知限制 |
| R-07 | Resolved | — | 無 |
| R-08 | Resolved | 掃描點 23、24、25 在（`:1225`、`:1239`、`:1253`），本次綠；`ConversationView.tsx:25` 為 `text-brand-50` | 無。另：第 23 列 (a) 讓**成員詳情頁**也有非數字 `projectId` 的固定句狀態（`MemberDetailPage.tsx:44-56`、`:139`），沿用同一個 `member-detail-error` 元素；掃描點 25 只涵蓋**成員清單**的 404，詳情頁這個狀態無掃描點 → 已知限制 |
| R-09 | Unresolved | 第四節 `:57`、`:64`，第十節 `:143`，第十四節 `:193` 仍寫基準 1 筆／2.6:1 已列入基準 | **只需改紀錄**。本輪只准 append，故以下第 5 小節的現況表**取代**這四行，原文不回改 |
| R-10 | Unresolved | 計畫第一節、`unit-test-instructions.md:14`、`:18`、`:21`、`:60-61` 仍寫 21 test／18 點 | **只需改紀錄**，以第 5 小節現況表為準；計畫內文與測試說明本輪不得改 |
| R-11 | New | 27 個 `test()`，`@note` 15 個（缺 12 個）；`@story US9.2` 於 `a11y.spec.ts:1195`、`:1209`（第 21、22 點），計畫要求 `N-9`；`@api` 0；`describe('U17 a11y gate')`（`:906`） | **仍成立**。補 `@note` 需改測試；改 Step 14 文字需改計畫內文（本輪禁止）→ 已知限制；Step 14 維持未勾 |
| R-12 | New | `source-manifest.json` 的 `writes` 8 筆，仍無 `ConversationView.tsx` | **仍成立**。本輪不准寫 `source-manifest.json` → 已知限制；歸屬在此記明：該檔的 `text-brand-100 → text-brand-50`（`ConversationView.tsx:25`）為本單元於 review-02 期間所改，檔案歸 `entry-page-ui` |
| R-13 | New | `traceability.json` 的 A11Y-S9、A11Y-S10、D-04、N-9 note 數字過時 | **本輪已更新四則 note**（基準 0 筆、24 掃描點、27 test、role 對照表無實際放行條目），`python3 -m json.tool` 驗證合法。`upstream_ids` **未**加入第 21、22 點的 `US9.2`：該 id 屬 U16，加進本單元 upstream 會改變 traceability sensor 的比對集合，留待 conductor 判定；A11Y-S10 的 note 已註明此缺 |

### 4. 勾選重設

依前一輪紀錄逐格判定（計畫內文未改，只改 `[ ]`→`[x]`）：

| 格 | 判定 | 依據 |
|---|---|---|
| Step 1 | 勾 | 本輪重驗：test-id／文字定位器以 27 案就緒斷言實證；`playwright.config.ts` 三項設定見上；`ReselectionBanner.tsx:242` 的 `data-slot` 在且檔案與收據相同 |
| Step 2 | 勾 | 本輪重驗：副本 `memory-page.spec.ts` 18 passed |
| Step 3 | 勾 | `package.json`、`package-lock.json` 與收據逐位元相同；發布日與 `npm audit` 需連 registry，本輪未重驗（沿用第四節） |
| Step 4–9、12 | 勾 | `a11y.spec.ts` 與收據逐位元相同，且本輪 27 案全綠 |
| Step 10 | 勾 | `a11y-baseline.json` 相同；本單元在 `MemberDetailPage.tsx:289` 的第 1 類修正仍在（見第 1 小節） |
| Step 11 | 勾 | 突變的證據檔（spec、基準）逐位元相同；本輪未重跑 M1–M12 |
| Step 13 | 勾 | 本輪重驗：lint 0 errors、build 成功、src 內 axe-core 0、dist 判定同前、兩支 validator 綠、耗時 18.4s（本機 preview） |
| Step 14 | **不勾** | 27 案中 12 案缺 `@note`，第 21、22 點 `@story` 為 `US9.2` 非 `N-9`（R-11 仍成立） |
| Step 15 | 勾 | 三份文件皆在；`source-manifest.json` 漏列 `ConversationView.tsx`（R-12）為已知限制，不影響本格所列內容的存在 |
| Step 16 | 勾 | 本輪以生產建置＋preview 重跑全綠、基準未增、過期檢查未誤紅 |
| 九之二 五格 | 勾 | 本節第 1–5 小節即其結果；「收尾」於本節寫入且 validator 綠後勾 |

**實算**（收尾格勾選後，`grep -c '^- \[x\]'`／`grep -c '^- \[ \]'`）：**已勾 20、未勾 1**（唯一未勾為 Step 14）。

### 5. 現況表（取代第一至十六節的過時數字，R-09／R-10）

| 項目 | 現況 | 過時陳述所在 |
|---|---|---|
| `test()` 數 | **27**＝24 掃描點（01–18、20–25）＋1 手機寬度（19）＋2 基準檢查 | 計畫第一節、第十節 `:142`、`unit-test-instructions.md:14`、`:21`；§十六的 24 |
| 掃描結果檔數 | **24** | 第五節 `:48`、`unit-test-instructions.md` 的 18 |
| 基準條目 | **0**（`"entries": []`） | 第五節 `:57`、`:64`，第十節 `:143`，第十四節 `:193` |
| `@axe-core/playwright` 寫法 | 精確 `"4.13.0"`（`package.json:25`） | 第四節 `:40`、第十節 `:140` 的 `^4.13.0` |
| 本機耗時 | 18.4s（本輪） | 第八節 `:123` 的 13.4s（當時 21 案） |

### 6. 已知限制（待 conductor 併入 merge-blockers）

既有列已涵蓋者：第 23 列（成員詳情的非數字 `projectId` 與對話框焦點）在程式面已修，但其**掃描覆蓋**未被該列處理；第 26 列 R-02（真實 stack）同樣適用本 spec。以下為未被任何既有列涵蓋者：

1. **R-11**：`a11y.spec.ts` 12 案缺 `@note`、第 21、22 點 `@story` 為 `US9.2`；需補註解（改測試）或修訂計畫 Step 14 文字。Step 14 因此未勾，本單元無法乾淨結案。
2. **R-12**：`source-manifest.json` 漏列 `frontend/src/components/brain/ConversationView.tsx`。
3. **R-05**：`incomplete` 只附 Playwright attachment、`ui-regression` 無 artifact 上傳；`unit-test-instructions.md` 未註明「綠燈不代表 incomplete 為空」。
4. **新（掃描覆蓋）**：成員詳情頁的非數字 `projectId` 固定句狀態（第 23 列 (a)，`MemberDetailPage.tsx:44-56`、`:139`、`:259-261`）無掃描點；需新增掃描點（改測試）。
5. **R-06**（可選）：`MemberDetailPage.tsx:289` 改 `aria-labelledby`；`ContextBar.tsx:109` 骨架改 `role="status"` 的評估。
6. **R-13 剩餘**：`traceability.json` 的 `upstream_ids` 未涵蓋第 21、22 點對應的 U16 `US9.2`。

### 7. 收尾

`python3 -B scripts/validate_repo_contract.py`：passed。`python3 -B scripts/validate_env_contract.py`：passed（皆於 repo 根目錄唯讀執行，本節寫入後重跑）。

## 十八、合併前必修第 40 列（計畫九之三，2026-11-08）

<!-- 寫入時間：本輪開工時 `date -u` 為 2026-11-08T03:56:12Z；本節寫入時 shell 已被 plan-approval guard 擋下，無法再取 `date -u`，故不寫一個未經取值的時間 -->

### 0. 開工時的現況（先查再做）

收據 `reviewed-source-311abd498fc2.tsv`（以 Python `hashlib` 逐列解析 tab 欄位；抽 `package.json`、`a11y.spec.ts` 以 `shasum -a 256` 手動複核一致）：9 列（1 列 manifest ＋ 8 檔）中 **4 檔相同**（`package-lock.json`、`package.json`、`ReselectionBanner.tsx`、`a11y-baseline.json`），**4 檔變動**：`Sidebar.tsx`、`brain/ContextBar.tsx`、`MemberDetailPage.tsx`、`a11y.spec.ts`。四檔的收據雜湊皆等於 `git show HEAD:<檔>` 的雜湊，故收據後的改動**恰為**工作樹對 HEAD 的未提交 diff。逐 hunk 讀過：全部標註為 brain-infra 計畫 A10（第 35 列 (c)、第 40 列 (a)(d)(i)，見 `brain-infra/code-generation/code-summary.md` A10 段），內容為 `Sidebar.tsx:248` 補 `aria-label="我的記憶"`、`ContextBar.tsx:111` 骨架 `role="img"`→`role="status"`、`MemberDetailPage.tsx:284`／`:292` 改 `aria-labelledby`、`a11y.spec.ts` 補 12 個 `@note` 與第 26 掃描點。沒有任何 hunk 移除本單元依賴的 test-id、文字定位器、`data-slot` 或基準條目。

因此 Step 18 與 (i) 在本輪開工前**已由 brain-infra 落地**；本輪不重做，只驗證並補其餘項。

### 1. 逐步結果

| Step | 結果（附定位） |
|---|---|
| 17 (a) | `a11y.spec.ts`：`test(` 28、`@purpose` 28、`@given` 28、`@pass` 28、`@story` 28、`@ui` 28、`@note` 28、`@step` 60、`@api` 0（`grep -c`）。第 21、22 點 `@story US9.2` 改為 `@story N-9、US9.2`（`:1219` 附近與 `:1233` 附近兩處；`tcms_sync.py` 的 `@story` 只取最後一行，故以單行第二值保留，不另起第二行）。`parse_spec` 實讀 28 案，兩案 story 為 `N-9、US9.2`、其餘 26 案為 `N-9`。`describe('U17 a11y gate')` 與 28 個 test 名稱未動。`python3 -B scripts/tcms_validate.py --spec frontend/tests/e2e/a11y.spec.ts` → **通過 28/28、ERROR 0、WARN 0**。據此勾 Step 14（偏離：計畫 Step 14 字面寫「21 個 `test()`」，現為 28，以現況表為準） |
| 18 (d) | 已存在：`SCANS.memberDetailInvalidProject`（`id: '26-member-detail-invalid-project'`，`/projects/not-a-number/members/${OTHER_ID}`，就緒 `member-detail-page` ＋ `member-detail-error` 含「查不到這個專案」，排除「載入中…」與 `member-detail-role-select`）與 test「26 成員詳情頁專案編號非數字」，規格註解齊全。全走 `page.route`（`login`、`reselections`）；`a11y-baseline.json` sha256 `7c1051f6…733f` 未變，**未新增豁免** |
| 19 | `a11y.spec.ts:77` 註解改為「我的記憶的 `<nav>` 現已有 `aria-label="我的記憶"`〔`Sidebar.tsx:248`，由 `sidebar-landmarks.spec.ts` 鎖住〕，此處仍以其連結 test-id 定位」。只改註解；`NEW_SIDEBAR_MARKERS` 陣列未動 |
| 20 (i) | 已落地，落地者 brain-infra A10：`ContextBar.tsx:111` 為 `role="status" aria-label="連線中"`；`MemberDetailPage.tsx:284` `<h2 id="member-detail-role-heading">`、`:292` `aria-labelledby="member-detail-role-heading"`。本輪未改元件程式 |
| 21 (b) | `source-manifest.json` 補 `frontend/src/components/brain/ConversationView.tsx`（偏離：計畫字面為 `components/ConversationView.tsx`，該路徑不存在，以實際路徑為準），`writes` 現 9 筆 |
| 21 (c) | `traceability.json` 的 `upstream_ids` 補 `US9.2`（並依 Step 24 補 `MB-40`），`coverage` 同步各加一列，N-9 note 補現況；`upstream_ids` 31、`coverage` 31、集合差為空，`python3 -B -I` 的 `json.load` 可解析 |
| 21 (e)(h) | `unit-test-instructions.md` 第三節末 append 兩段「現況註記（2026-11-08）」：綠燈不代表 `incomplete` 為空；副本 `node_modules` 的來源限制、`cp -cR` 做法、`openapi.json` 須放副本根目錄、`--host 127.0.0.1`。原文未刪 |
| 21 (f) | 第四節（`^4.13.0`）、第五節（表後與「基準 1 筆」條下）、第十節（檔案表後）、第十四節（第 9 點下）各加一行指向第十七節第 5 小節現況表；原文未刪。註：review-03 R-09 所稱「第四節 `:57`、`:64`」實際位於第五節，本輪依實際位置補記 |
| 21 (g) | 第十七節開頭範圍宣稱後加一行，補記 `unit-test-instructions.md` 的 2026-10-31 現況註記為該輪新增 |
| 22 | 副本 `MemberDetailPage.tsx` 在固定句 `<p>` 後注入 `{invalidProjectId && <button type="button" data-testid="a11y-mut-unnamed" />}` → 重建（`dist` 內命中 1）→ 跑 `a11y.spec.ts`：**27 passed、1 failed**，紅的恰為「26 成員詳情頁專案編號非數字」，訊息 `[掃描層] 26-member-detail-invalid-project 有基準以外的 WCAG 2.1 AA 違規`，條目 `rule: button-name`、`impact: critical`、`inNewRoot: true`、`selector: [data-testid="a11y-mut-unnamed"]`；其餘 27 案（含第 10 點，數字 id 不觸發注入）綠。還原（Edit 移除該行）→ `cmp` 與備份逐位元相同、sha256 `d3e02559…` 與 repo 檔相同 → 重建（`dist` 命中 0）→ 全綠。repo 內被測檔未動 |
| 23 | 見第 2 小節。**未完成部分**：repo 內的 `validate_repo_contract.py`、`validate_env_contract.py` 未跑（見第 4 小節） |
| 24 | 本節、`traceability.json` 的 `MB-40` 已寫；**`merge-blockers.md` 第 40 列處置欄未能補記**——該檔在 code-generation record 目錄之外，Edit 被 plan-approval guard 擋下（見第 4 小節）。擬補記的文字附於第 5 小節，供 conductor 貼入 |

### 2. 回歸（Step 23，副本）

副本 `scratchpad/a11y-copy/frontend`：`rsync -a` 複製 `frontend/`（排除 `node_modules`、`dist`、`test-results`、`junit.xml`、`pw-report.json`），`node_modules` 以 `cp -cR` 自 repo 複製並刪去 `.tmp/`；`openapi.json`、`ws-contract.json` 放副本根目錄。副本內絕對路徑 symlink 0、解析後落在 repo 內者 0。不連網路、未 `npm install`。

| 檢查 | 結果 |
|---|---|
| `npm run lint` | **0 errors、2 warnings**（`AssessmentPage.tsx`、`WorkspacePage.tsx:344` 的既有 `exhaustive-deps`），未增 |
| `npm run check:types` | 「API 型別檔與規格檔一致。」 |
| `npm run build` | 成功（僅既有 chunk 大小警告）；review-04 R-16 的 TS2307 **未重現**——repo 現有 `node_modules` 本輪複製後可建置。這份依賴不是本輪重新安裝的，其完整性只由上述三項通過間接證明 |
| `vite preview --host 127.0.0.1 --port 4187 --strictPort` ＋ `BASE_URL=http://127.0.0.1:4187`，`a11y.spec.ts` ＋ `sidebar-landmarks.spec.ts`，`--retries=0` | **30 passed（19.4s）**：a11y 28（25 掃描點＋手機寬度＋2 基準檢查）、sidebar-landmarks 2 |
| 同上，`CI=1`（`retries: 1`）只跑 `a11y.spec.ts` | **28 passed（18.3s）** |
| 突變還原後重跑（同第一列組合） | **30 passed（19.1s）** |
| 掃描結果檔 | 25 個；`grep -L '"entries": []'` 0 個（25 點全部零違規） |
| 基準 | sha256 `7c1051f6…733f`，`entries` 仍空，**未新增**；過期檢查綠 |
| preview | 每次用畢 `pkill`；最後一次停止後 `curl` 回 `000` |

`playwright.config.ts`（repo 唯讀）：`:14` `fullyParallel: false`、`:17` `retries: process.env.CI ? 1 : 0`、`:18` `workers: 1`，未改。

### 3. 勾選重判

收據 4 檔變動（第 0 小節）；本輪以副本回歸重驗。

| 格 | 判定 | 依據 |
|---|---|---|
| Step 1 | 勾 | `playwright.config.ts` 三項設定實讀；`ReselectionBanner.tsx` 與收據相同（`data-slot` 未動）；test-id／文字定位器由 28 案就緒斷言實證 |
| Step 2 | 勾 | 本輪以副本生產建置＋preview 跑 a11y／sidebar-landmarks 30 passed 驗證執行器。偏離：Step 2 字面點名的 `memory-page.spec.ts` 本輪未重跑（該檔屬 memory-page-ui，工作樹已有他單元改動） |
| Step 3 | 勾 | `package.json`、`package-lock.json` 與收據逐位元相同 |
| Step 4–9、12 | 勾 | `a11y.spec.ts` 收據後只有加法改動（掃描點 26、註解），四層函式未動；本輪 28 案全綠 |
| Step 10 | 勾 | 基準相同；第 1 類修正在 brain-infra A10 改寫後仍成立（第 10 點、第 01／13／14 點綠） |
| Step 11 | **不勾** | 證據檔 `a11y.spec.ts` 自收據後已變動，M1–M12 本輪未重跑；Step 22 只重驗了第 26 點的掃描層突變 |
| Step 13 | **不勾** | lint、build、check:types 本輪已重驗；但 repo 內兩支 validator、`grep -rn "axe-core" frontend/src`、`dist/` 內 axe 檢查在 shell 被擋後未能執行 |
| Step 14 | 勾 | Step 17 完成（見上） |
| Step 15 | 勾 | 三份文件皆在；R-12 已補 |
| Step 16 | 勾 | 本輪生產建置＋preview 重跑全綠、基準未增、過期檢查未誤紅 |
| 九之二 五格 | 勾 | 該輪紀錄（第十七節）未變；本輪回歸另作補強 |
| Step 17–22 | 勾 | 見第 1 小節 |
| Step 23 | **不勾** | repo 內兩支 validator 未跑 |
| Step 24 | **不勾** | `merge-blockers.md` 第 40 列未能補記 |

**實算**：shell 被擋後無法跑 `grep -c`，改以 Read 工具讀全檔逐格計數：**已勾 25、未勾 4**（Step 11、13、23、24），共 29 格。

### 4. 本輪的阻斷：plan-approval guard

依 Step 21 (e)(h) 以 Edit 改 `unit-test-instructions.md` 之後，所有 shell 指令與 record 目錄外的 Edit 皆被 PreToolUse hook 擋下，逐字：「Code generation cannot run mutation-capable shell commands for unit a11y-gate because the plan, unit-test instructions, and current Testing Contract do not have a current matching approval.」本輪**未**繞過（未暫時還原該檔、未關閉 guard、未自行跑 `aidlc engine orchestrate next`）。受影響而未完成的項目：

1. repo 內 `python3 -B scripts/validate_repo_contract.py`、`python3 -B scripts/validate_env_contract.py`。
2. `grep -rn "axe-core" frontend/src`、副本 `dist/` 內 axe 字樣檢查（Step 13）。
3. `merge-blockers.md` 第 40 列處置欄補記（Step 24）。
4. 收尾的 repo 產物檢查（`junit.xml`／`pw-report.json`／`.tsbuildinfo` mtime、`git status --porcelain | grep -E '\.pyc|\.hypothesis|__pycache__'`）與刪除 scratchpad 副本。開工時記錄的 mtime：`frontend/junit.xml`、`pw-report.json` 為 11-07 23:44，`node_modules/.tmp/*.tsbuildinfo` 為 11-08 07:08:55，`frontend/dist` 為 11-08 07:08:56，皆早於本輪；本輪所有 build／Playwright 都在副本內執行（cwd 為副本），唯一在 repo 跑過的 Python 是 `python3 -I`（讀 `tcms_sync.parse_spec`，事後查 `scripts/__pycache__/tcms_sync.cpython-313.pyc` mtime 仍為 09-06，未改寫）與 `python3 -B`。

由 conductor 重新取得核可（或依 guard 指示）後補跑上列 1、2、4，並貼入第 5 小節。

### 5. 擬補記於 `merge-blockers.md` 第 40 列處置欄的文字（原文保留，接在「修後重審 a11y-gate」之後）

> **2026-11-08 a11y-gate 處置**：(a) 28 個 test 註解齊全（各標籤 28、`@step` 60、`@api` 0），第 21、22 點 `@story` 改 `N-9、US9.2`，名稱未改；(d) 第 26 點（brain-infra A10 加入）副本突變注入無名稱按鈕 → 第 26 點紅（`button-name`）、還原 → 綠；(i) 已由 brain-infra A10 落地（`ContextBar.tsx:111`、`MemberDetailPage.tsx:284`／`:292`）；(b)(c)(e)–(h) 與 `a11y.spec.ts:77` 過期註解已改。副本 30 passed、`CI=1` 28 passed、基準未增、lint 0 errors。未完成：repo 內兩支 validator（plan-approval guard 擋下）、M1–M12 未重跑。結論：待重審 a11y-gate。

### 6. 已知限制（待 conductor 併入 merge-blockers）

1. Step 11：`a11y.spec.ts` 收據後已變動，M1–M12 未重跑（既有第 40 列可涵蓋，或另列）。
2. 第 4 小節的四項未完成檢查。
3. 計畫 Step 14／一、範圍仍寫「21 個 `test()`」、Step 21 (b) 的路徑少了 `brain/`——計畫內文本輪不得改，以本節與第十七節現況表為準。
4. 第 26 列（真實 stack 從未執行）仍適用本 spec。

### 7. conductor 補完第 4 小節的阻斷項（2026-11-08T04:11:30Z）

本輪改 `unit-test-instructions.md` 之後 plan-approval guard 判定指紋失效；使用者已於 2026-11-08 關閉本 intent 的計畫核可關卡，conductor 重跑 `aidlc engine orchestrate next` 後重新綁定（`plan_approval.status: approved`、`skipped: true`），再補做下列檢查：

- `python3 -B scripts/validate_repo_contract.py`：passed；`python3 -B scripts/validate_env_contract.py`：passed。
- `grep -rn "axe-core" frontend/src`：0 筆；副本 `frontend/dist/` 內 `axe-core`／`axe.run`：0 筆（axe 未進生產建置）。
- repo 測試產物 mtime：`frontend/junit.xml`、`frontend/pw-report.json` 為 2026-11-07 23:44（+08），`frontend/node_modules/.tmp/tsconfig.{app,node}.tsbuildinfo` 為 2026-11-08 07:08（+08），皆早於本輪開工；`git status --porcelain` 過濾 `.pyc`／`.hypothesis`／`__pycache__` 為空。
- scratchpad 副本 `a11y-copy/` 已刪除。
- `merge-blockers.md` 第 40 列處置欄已依第 5 小節文字補記（含本小節的補跑結果）。
- 據此勾選 Step 13、Step 23、Step 24；Step 11（M1–M12 未重跑）維持未勾。
- 重新綁定核可時引擎把計畫 29 格全部重設為未勾（非證據失效）；conductor 依第 3 小節逐格判定加上本小節補跑結果重勾，只改勾選字元：**已勾 28、未勾 1**（Step 11）。

## 整站重跑後的勾選回復（2026-11-08T23:09:27Z）

- 背景：2026-11-08T06:40:14Z 使用者決定重跑整個 code-generation 階段（整站關卡因審查收據失效卡死，唯一出路）。引擎把本計畫勾選全部重設為未勾。
- 依據：以 Python `hashlib` 重算上一次審查留下、與現況最吻合的收據 `reviewed-source-fe1d9914dd4e.tsv`：9 同、0 變。本輪 `REVIEW_REQUESTED` 當下引擎另會產生一份新收據，以那份為準。既有勾選依 HEAD 版回復（差異僅勾選字元）。
- 現況（實算）：28 勾／1 未勾；未勾格沿用 HEAD 的未勾理由：
  - - [ ] **Step 11 — 跑測試並做突變驗證（`M1`–`M12`）**：全綠後逐一套用 `security-design.md` 第八節 `M1`–`M10` 與 `D-08` 的 `M11`／`M12`，每一道：套用 → 確認紅在預期的那一層 → 還原 → 確認綠；`M10` 以環境變數注入一次性失敗並設
