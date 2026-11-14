## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本次為單次 ADVISORY 審查，未執行任何測試或建置，只讀程式與差異，並引用 conductor 已跑的結果。四層結構（隔離、狀態、就緒、掃描）大致照 `security-design.md` 與 C-01..C-08、D-01..D-08 實作：HTTP 與 WebSocket 兜底最先註冊，18 個掃描點都有就緒與排除項，include 範圍與就緒 test-id 一致，掃描結果在斷言前先寫檔，過期檢查讀 18 個檔且不足即失敗，基準選擇器不用 nth-child。`p → paragraph` 這一筆確為頁殼既有節點（`git log -S` 指向 `af73f03f`，2026-07-11），三處元件修改經 `git diff` 確認只動屬性或 Tailwind 色階，`traceability.json` 的 OK 目標都是單一存在的檔案。判 READY，因為沒有 Critical 且 Major 為 2 項。需要人在閘門上權衡的有兩項。第一，閘門對入口頁只掃到「連線中」這一個降級狀態。第二，唯一的基準條目放行了新功能目標使用者在入口頁真的看得到的對比不足，而且該條目是在停損條件觸發後才擴充 role 對照表取得選擇器。其餘為 Minor。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | frontend/tests/e2e/a11y.spec.ts:182-187, :378-385, :513-523 | 掃描點 01、13、14、19 的入口頁都停在 `ContextBar` 的 `connecting` 狀態。`/api/brain/ws` 以空 handler 接管，永遠不送 `ready` 訊框，而 `ContextBar.tsx:37` 在 `status !== 'ready'` 時就是 `connecting`。`default`、`independent`、`no-object`、`unavailable` 四個狀態與連線後的入口頁 UI 從未被 axe 掃過；第一筆新元件違規（`span[aria-label="連線中"]`）恰好就出在這個降級狀態。`entry-page.spec.ts:58` 已有可讓連線進入 ready 的假伺服器。code-summary 第十一節第 7 點與第十四節第 7 點有揭露，但這是給 `build-and-test` 的開放項，不是 N-9「違規即紅燈」的覆蓋。`ContextBar` 同時掛在 `WorkspacePage.tsx:930` 與 `AssessmentPage.tsx:1240`（K-13），那兩處也無掃描。 | 至少增掃一個「已連線」的入口頁狀態（讓空 handler 改送 ready 訊框，沿用 `src/brain/testing/wsFrames.ts` 的建構器，`ContextBar` 進入 `default` 或 `no-object`）；或由使用者明確裁決接受只掃 connecting 狀態，並把該限制寫進 `unit-test-instructions.md` 與 N-9 的覆蓋說明，而不只留在交接清單。 | New |
| R-02 | Major | frontend/tests/e2e/a11y-baseline.json:5-6; frontend/tests/e2e/a11y.spec.ts:642-661; frontend/src/components/Sidebar.tsx:324-328 | 唯一的基準條目放行 Sidebar 空選單提示 `<p>` 的 `color-contrast`（`text-gray-400` 約 2.6:1）。(a) 事實面屬實：該字串由 `af73f03f`（2026-07-11）引入，並非本 intent 新增。(b) 但出現條件是 `!showCoreSection && !showAdminSection`（`Sidebar.tsx:324`），即沒有 A1、A3、J3a、J3b 權限的帳號；這正是只用大腦入口、專案、記憶的新功能使用者，所以入口頁對本 intent 的目標使用者確實有一段 AA 不合格文字。(c) 修法是 `Sidebar.tsx` 一個 class，而 `git diff` 顯示本 intent 已在改這支檔（`showEntry`、`showProjects`）。(d) 選擇器取得的過程：計畫第四節的停損是「頁殼節點取不到穩定選擇器就停下回報」（D-04）。第一次實跑得到 `null`，實作者隨後在 `stabilize()` 的 role 對照表補上 `p: 'paragraph'`，條目才得以進基準。code-summary 第十一節第 5 點有誠實揭露並請審查者確認，但等於是閘門在停損觸發後被擴充到可放行。`implicit` 對照表也因此成為開放的放行面（`a`、`button`、`li`、`h1-h4` 等頁殼節點之後都能取到 role＋文字名稱而進基準）。 | 由使用者裁決：優先將 `Sidebar.tsx:325` 的 `text-gray-400` 改為達 4.5:1 的色階（與本次三處屬性修正同性質，順手移除唯一的基準條目，讓基準清單為空）；若仍選擇列入基準，則在 `a11y-baseline.json` 的 reason 補上「受影響的是只具 K 系列權限的帳號」，並記錄 D-04 停損在此以擴充 role 對照表處置。 | New |
| R-03 | Minor | frontend/tests/e2e/a11y-baseline.json:6; frontend/tests/e2e/a11y.spec.ts:669 | 基準鍵 `role=paragraph[name="…"]` 不是可解析的 Playwright 定位器：`paragraph` 角色不從內容取名，`getByRole('paragraph', { name })` 找不到該節點。它只是以文字為鍵的識別字串，與 `selector` 欄名稱暗示的「選擇器」不同。任何其他頁殼 `<p>` 只要文字相同且 `color-contrast` 同樣失敗，也會被一併放行；文案一改則同時出現過期與新違規，會大聲失敗，這一側是安全的。 | 在 `a11y-baseline.json` 或 spec 註解註明該鍵是「role＋文字」識別字而非定位器，避免日後有人拿去除錯；或改用 `p` 外層的 `div` 加穩定屬性後以屬性定位（若選擇修 Sidebar 則此項自動消失）。 | New |
| R-04 | Minor | frontend/package.json:25; frontend/package-lock.json | `package.json` 寫 `"@axe-core/playwright": "^4.13.0"`，lockfile 鎖在 4.13.0（`git diff --stat` 為 +24）。A11Y-S3 的 14 天規則是被 caret 在 `npm install` 時以 4.14.0 繞過的（code-summary 第四節自述）。CI 與 `frontend/Dockerfile:8` 都用 `npm ci`，不受影響；但任何人日後 `npm install` 重解析會浮到不滿 14 天的版本。授權為 MPL-2.0，已記錄，僅 devDependency。 | 將 `package.json` 改為精確版本 `4.13.0`（或 `npm install --save-exact`），使規則由 manifest 本身承載，不靠使用者記得用 `npm ci`。 | New |
| R-05 | Minor | frontend/tests/e2e/a11y.spec.ts:703-707 | `incomplete`（needs review）只附在 Playwright attachment 上，不影響紅綠；code-summary 第十四節第 5 點確認 `ui-regression` 無 artifact 上傳，綠燈時 axe 結果零留存。`color-contrast` 在有背景圖或疊層時常以 `incomplete` 回報，因此該類節點既不被擋、也看不到。A11Y-S8 只規定 violations 擋閘，這符合上游；缺口在可見性。 | 在 `build-and-test` 判定是否補 artifact 上傳；至少在 `unit-test-instructions.md` 註明「綠燈不代表 incomplete 為空」。 | New |
| R-06 | Minor | frontend/src/pages/MemberDetailPage.tsx:239; frontend/src/components/brain/ContextBar.tsx:53 | 屬性修正本身正確且 `git diff` 確認 `MemberDetailPage.tsx` 只增 1 行、`ReselectionBanner.tsx` 只換兩個色階 class（amber-600→700、hover 700→800，白字對比約 5.0:1），無 test-id、行為或版面變動。兩點可更好：(a) `aria-label="專案角色"` 與正上方 `<h2>專案角色</h2>` 同字但各自維護，改用 `aria-labelledby` 指向該 `h2` 的 id 可只留一個來源。(b) `ContextBar` 骨架 `<span role="img" aria-label="連線中">` 讓輔助科技多唸一個「連線中，圖片」，但狀態切換後沒有播報；載入指示通常用 `role="status"`。另外 `ContextBar.tsx` 為未追蹤檔（U14 尚未提交），無法用 `git diff` 驗證「只動一個屬性」，只能依 code-summary 第五節的自述。 | 可選：(a) 改 `aria-labelledby`；(b) 評估骨架改 `role="status"` 或在 U14 提交後以 diff 複驗該行為唯一變動。 | New |
| R-07 | Minor | frontend/tests/e2e/a11y.spec.ts:1045-1049; frontend/tests/e2e/a11y.spec.ts:1055 | 過期檢查要求結果目錄恰為 18 個檔，與 `-g` 單跑、`--shard` 或任何子集執行都會紅（code-summary 第十一節第 10 點已承認為設計）；且 `seen` 集合也納入 `inNewRoot` 的條目，因此一筆只對得到新元件節點的基準條目永遠不算過期、也永遠不放行。後者無害（掃描層仍判 fresh 而失敗），前者只是使用手感，但 `unit-test-instructions.md` 與 TCMS 同步若以單案跑會誤報。 | 在 `unit-test-instructions.md` 明寫「本檔必須整檔執行，不得 `-g` 或 shard」；確認 `ui-regression` 不 shard。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| conductor：`a11y.spec.ts`（含 `CI=1`） | 21 passed | 引用，未重跑；與 spec 中 18 掃描點＋手機寬度＋2 個基準檢查共 21 個 `test()` 相符 |
| conductor：member-pages、entry-page、a11y 合跑 | 80 passed | 引用；對三處屬性修正未破壞既有 e2e 提供佐證 |
| conductor：project-pages、memory-page | 38 passed | 引用 |
| conductor：`npm run lint`、`npm run build` | 0 errors、2 baseline warnings；build 通過 | 引用 |
| conductor：linter、type-check、required-sections sensor | 通過 | 引用 |
| conductor：traceability sensor | `upstream ID set is empty` | 預期且已揭露（無 `NFRx.y` 或 AC 上游）；`traceability.json` 29 項中 26 OK、1 N/A、2 Deferred，OK 目標皆指向單一存在的檔案，未見不實狀態 |
| 唯讀核對：`git log -S` 於 `Sidebar.tsx` | `af73f03f` 與 `55b1704a`（皆 2026-07-11） | 確認基準條目為頁殼既有節點 |
| 唯讀核對：`git diff` 於 `package.json`、`MemberDetailPage.tsx`、`ReselectionBanner.tsx` | 僅屬性或 class 變動 | 確認第 4 點的「純屬性」主張；`ContextBar.tsx` 因未追蹤無法比對 |

### 逐項攻擊結果摘要

1. 四層：兜底 `page.route('**/api/**')` 與 `routeWebSocket(/.*/)` 在 `isolate()` 最先註冊（:178、:182），具體樣式其後；就緒層、先寫檔後斷言（:697-701 在 :715 之前）、穩定選擇器（無 nth-child，:1027 並以靜態檢查擋下）、過期檢查讀 18 檔且不足即失敗（:1048-1049），皆成立。
2. `p → paragraph`：見 R-02、R-03。
3. 規則 1 靜態檢查：根節點清單涵蓋 C-03 的十個 test-id、三個 Sidebar 新增項及 D-01 的橫幅外層，並加了 test-id 前綴比對（比 C-03 更嚴）；以 role＋名稱表達的新元件子孫只靠執行期 `closest()`（:631）擋，靜態檢查擋不住，但最壞結果是掃描層大聲失敗，不會滑進基準。
4. 三處元件修改：見 R-06。
5. C-07：入口頁的閘實為 `K1 view`（`App.tsx:34`），第 18 點只帶 `C1` 使落地在 `/cost`；`include` 限縮到 `[data-slot="reselection-banner"]`，就緒項以該根節點為範圍（:589-595），且 `/cost` 只放行 `GET /api/cost/v1/sets`，其餘 `/api` 呼叫會被兜底記錄而讓測試紅，故不會掃到舊頁內容。
6. M1-M12：與 spec 程式碼對得上（M1、M2 對應 :178-187；M3、M4 對應 :585-605；M6、M8、M12 對應 :1018-1033；M7 對應 :1045-1057；M9 對應 :993-1004；M11 對應 :564-567、:589-595），未見不合理的宣稱。
7. `traceability.json`：未見不實狀態；三處元件修改未對應任何追溯條目，但列於 `source-manifest.json`，屬可接受的粗粒度。
8. 相依：見 R-04。
