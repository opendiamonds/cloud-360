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

第 18 點只掃橫幅外層（`include`），所以第 4 筆沒有出現在第 18 點。第一次實跑沒有任何交界類規則（第 3 類）出現。

**第 4 筆的處置**：
- **它確實是頁殼既有節點**：`git log -S` 顯示該字串由 `af73f03f`（2026-07-11，`feat(rbac)`）引入；出現條件 `!showCoreSection && !showAdminSection`（`Sidebar.tsx:324`）只看 A1／A3／J3a／J3b，本 intent 沒有改動這個節點或其條件。它在每個掃描點都出現，是因為攔截層的 `/me` 只給各頁所需的 K 系列權限——真實上只具 K 系列權限的使用者也會看到它。
- **第一次實跑時選擇器為 `null`**：我寫的 role 對照表漏了 `p`。`<p>` 的隱含 role 是 `paragraph`（HTML-AAM），`D-04` 定義的名稱取法是「`aria-label`、`aria-labelledby` 指向的文字或其文字內容」，依此可得 `role=paragraph[name="目前角色尚未開放任何功能選單，請聯絡管理員調整權限。"]`——不依賴位置，符合 `C-03`。把 `p: 'paragraph'` 補進對照表後，該筆以此選擇器列入基準。
- 基準檔現為 **1 筆**（`frontend/tests/e2e/a11y-baseline.json`），附 `reason`。

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
