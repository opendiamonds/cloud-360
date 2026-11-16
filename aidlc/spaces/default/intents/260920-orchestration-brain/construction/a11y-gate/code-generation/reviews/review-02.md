## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-24T13:27:41Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | frontend/tests/e2e/a11y.spec.ts:182-187, :378-385, :513-523 | 掃描點 01、13、14、19 的入口頁都停在 `ContextBar` 的 `connecting` 狀態。`/api/brain/ws` 以空 handler 接管，永遠不送 `ready` 訊框，而 `ContextBar.tsx:37` 在 `status !== 'ready'` 時就是 `connecting`。`default`、`independent`、`no-object`、`unavailable` 四個狀態與連線後的入口頁 UI 從未被 axe 掃過；第一筆新元件違規（`span[aria-label="連線中"]`）恰好就出在這個降級狀態。`entry-page.spec.ts:58` 已有可讓連線進入 ready 的假伺服器。code-summary 第十一節第 7 點與第十四節第 7 點有揭露，但這是給 `build-and-test` 的開放項，不是 N-9「違規即紅燈」的覆蓋。`ContextBar` 同時掛在 `WorkspacePage.tsx:930` 與 `AssessmentPage.tsx:1240`（K-13），那兩處也無掃描。 | 至少增掃一個「已連線」的入口頁狀態（讓空 handler 改送 ready 訊框，沿用 `src/brain/testing/wsFrames.ts` 的建構器，`ContextBar` 進入 `default` 或 `no-object`）；或由使用者明確裁決接受只掃 connecting 狀態，並把該限制寫進 `unit-test-instructions.md` 與 N-9 的覆蓋說明，而不只留在交接清單。 | New |
| R-02 | Major | frontend/tests/e2e/a11y-baseline.json:5-6; frontend/tests/e2e/a11y.spec.ts:642-661; frontend/src/components/Sidebar.tsx:324-328 | 唯一的基準條目放行 Sidebar 空選單提示 `<p>` 的 `color-contrast`（`text-gray-400` 約 2.6:1）。(a) 事實面屬實：該字串由 `af73f03f`（2026-07-11）引入，並非本 intent 新增。(b) 但出現條件是 `!showCoreSection && !showAdminSection`（`Sidebar.tsx:324`），即沒有 A1、A3、J3a、J3b 權限的帳號；這正是只用大腦入口、專案、記憶的新功能使用者，所以入口頁對本 intent 的目標使用者確實有一段 AA 不合格文字。(c) 修法是 `Sidebar.tsx` 一個 class，而 `git diff` 顯示本 intent 已在改這支檔（`showEntry`、`showProjects`）。(d) 選擇器取得的過程：計畫第四節的停損是「頁殼節點取不到穩定選擇器就停下回報」（D-04）。第一次實跑得到 `null`，實作者隨後在 `stabilize()` 的 role 對照表補上 `p: 'paragraph'`，條目才得以進基準。code-summary 第十一節第 5 點有誠實揭露並請審查者確認，但等於是閘門在停損觸發後被擴充到可放行。`implicit` 對照表也因此成為開放的放行面（`a`、`button`、`li`、`h1-h4` 等頁殼節點之後都能取到 role＋文字名稱而進基準）。 | 由使用者裁決：優先將 `Sidebar.tsx:325` 的 `text-gray-400` 改為達 4.5:1 的色階（與本次三處屬性修正同性質，順手移除唯一的基準條目，讓基準清單為空）；若仍選擇列入基準，則在 `a11y-baseline.json` 的 reason 補上「受影響的是只具 K 系列權限的帳號」，並記錄 D-04 停損在此以擴充 role 對照表處置。 | New |
| R-03 | Minor | frontend/tests/e2e/a11y-baseline.json:6; frontend/tests/e2e/a11y.spec.ts:669 | 基準鍵 `role=paragraph[name="…"]` 不是可解析的 Playwright 定位器：`paragraph` 角色不從內容取名，`getByRole('paragraph', { name })` 找不到該節點。它只是以文字為鍵的識別字串，與 `selector` 欄名稱暗示的「選擇器」不同。任何其他頁殼 `<p>` 只要文字相同且 `color-contrast` 同樣失敗，也會被一併放行；文案一改則同時出現過期與新違規，會大聲失敗，這一側是安全的。 | 在 `a11y-baseline.json` 或 spec 註解註明該鍵是「role＋文字」識別字而非定位器，避免日後有人拿去除錯；或改用 `p` 外層的 `div` 加穩定屬性後以屬性定位（若選擇修 Sidebar 則此項自動消失）。 | New |
| R-04 | Minor | frontend/package.json:25; frontend/package-lock.json | `package.json` 寫 `"@axe-core/playwright": "^4.13.0"`，lockfile 鎖在 4.13.0（`git diff --stat` 為 +24）。A11Y-S3 的 14 天規則是被 caret 在 `npm install` 時以 4.14.0 繞過的（code-summary 第四節自述）。CI 與 `frontend/Dockerfile:8` 都用 `npm ci`，不受影響；但任何人日後 `npm install` 重解析會浮到不滿 14 天的版本。授權為 MPL-2.0，已記錄，僅 devDependency。 | 將 `package.json` 改為精確版本 `4.13.0`（或 `npm install --save-exact`），使規則由 manifest 本身承載，不靠使用者記得用 `npm ci`。 | New |
| R-05 | Minor | frontend/tests/e2e/a11y.spec.ts:703-707 | `incomplete`（needs review）只附在 Playwright attachment 上，不影響紅綠；code-summary 第十四節第 5 點確認 `ui-regression` 無 artifact 上傳，綠燈時 axe 結果零留存。`color-contrast` 在有背景圖或疊層時常以 `incomplete` 回報，因此該類節點既不被擋、也看不到。A11Y-S8 只規定 violations 擋閘，這符合上游；缺口在可見性。 | 在 `build-and-test` 判定是否補 artifact 上傳；至少在 `unit-test-instructions.md` 註明「綠燈不代表 incomplete 為空」。 | New |
| R-06 | Minor | frontend/src/pages/MemberDetailPage.tsx:239; frontend/src/components/brain/ContextBar.tsx:53 | 屬性修正本身正確且 `git diff` 確認 `MemberDetailPage.tsx` 只增 1 行、`ReselectionBanner.tsx` 只換兩個色階 class（amber-600→700、hover 700→800，白字對比約 5.0:1），無 test-id、行為或版面變動。兩點可更好：(a) `aria-label="專案角色"` 與正上方 `<h2>專案角色</h2>` 同字但各自維護，改用 `aria-labelledby` 指向該 `h2` 的 id 可只留一個來源。(b) `ContextBar` 骨架 `<span role="img" aria-label="連線中">` 讓輔助科技多唸一個「連線中，圖片」，但狀態切換後沒有播報；載入指示通常用 `role="status"`。另外 `ContextBar.tsx` 為未追蹤檔（U14 尚未提交），無法用 `git diff` 驗證「只動一個屬性」，只能依 code-summary 第五節的自述。 | 可選：(a) 改 `aria-labelledby`；(b) 評估骨架改 `role="status"` 或在 U14 提交後以 diff 複驗該行為唯一變動。 | New |
| R-07 | Minor | frontend/tests/e2e/a11y.spec.ts:1045-1049; frontend/tests/e2e/a11y.spec.ts:1055 | 過期檢查要求結果目錄恰為 18 個檔，與 `-g` 單跑、`--shard` 或任何子集執行都會紅（code-summary 第十一節第 10 點已承認為設計）；且 `seen` 集合也納入 `inNewRoot` 的條目，因此一筆只對得到新元件節點的基準條目永遠不算過期、也永遠不放行。後者無害（掃描層仍判 fresh 而失敗），前者只是使用手感，但 `unit-test-instructions.md` 與 TCMS 同步若以單案跑會誤報。 | 在 `unit-test-instructions.md` 明寫「本檔必須整檔執行，不得 `-g` 或 shard」；確認 `ui-regression` 不 shard。 | New |
| R-08 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/code-summary.md > 十六、Step 16 回歸驗證 > 新狀態的可達性；frontend/src/components/brain/ConversationView.tsx:24-26 | 「24 passed」只證明既有 21 個畫面狀態沒有退步，不能當作新狀態合格的證據。可達性分析本身屬實：`a11y.spec.ts` 第 187、382-385、397-400 行的 WebSocket handler 只回送握手快照，沒有送出使用者訊息或非輪次錯誤訊框；唯一的非 200 回應是第 608 行的 500，沒有 404。結果是「這句沒有送達」「回覆中斷」「你在回覆完成前離開了這一頁」三種狀態都沒被掃過。其中 `ConversationView.tsx:25` 的 `text-xs text-brand-100` 疊在 `bg-brand-600` 上，依 `index.css:9、14` 的色值（`#dbeafe` on `#2563eb`）計算約 4.2:1，低於一般文字的 4.5:1，很可能是 `color-contrast` 違規；重試鈕繼承同色，且 `disabled:opacity-40` 會更淡。閘門目前對這個畫面是靜默放行。Step 16 的停損條款（「新出現的違規應修元件，出現即停下」）在沒有掃描點的狀態上永遠不會觸發。 | 不要把 Step 16 的全綠當成這三個新狀態已通過。在 `build-and-test` 之前（或合併前）補掃描點：在已連線入口頁用 `wsFrames` 建構器送出使用者訊息，再送非輪次錯誤訊框觸發 `rejected`，並加上 `brain-system-notice`；另加一個回 404 的專案詳情或成員頁掃描點。若 `rejected` 態確實有對比違規，依計畫第四節第 1 類把 `text-brand-100` 改成較深的色階，不要收進基準。若選擇不補，需明確把這些狀態記為「閘門未覆蓋，改以人工驗證」，並把該對比疑慮列為已知風險。 | New |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/code-summary.md > 十四、開放項第 9 點（另見第四節、第五節的「基準 1 筆」、檔案表） | 這幾處仍寫 Sidebar 空選單提示的對比 2.6:1「已列入基準」。實際上 `Sidebar.tsx:325` 已改為 `text-gray-600`，`a11y-baseline.json` 在 HEAD 即為 `"entries": []`，`git diff --stat` 對該檔與 `a11y.spec.ts` 皆無輸出。所以沒有違規變成無人把關：該節點已修好，若退步會讓掃描層變紅。不一致只存在於文件，`code-summary-corrections.md` 第三節已更正，主檔卻沒同步，只讀主檔的人會得到錯誤的現況。 | 在 `code-summary.md` 的第四、五、十四節就地加註「已由 corrections 第三節取代」，或直接更新那幾句，讓基準現況只有一種說法。 | New |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/code-generation-plan.md > 一、範圍；Step 8；unit-test-instructions.md 第 14、21、58-59 行 | 數量宣稱有三個版本：計畫與 `unit-test-instructions.md` 寫 21 個 test、18 個掃描點、讀回 18 或 19 個結果檔；corrections 寫 22 個；實際為 24 個 test、21 個掃描點、21 個結果檔。spec 內的過期檢查（第 1177-1178 行）已用 21，與實跑一致。`unit-test-instructions.md` 凍結不改，但裡面「18 個畫面狀態全部被掃描」的覆蓋目標已不是現況，會讓使用者誤以為覆蓋面是 18 點且完整。 | 在 `code-summary.md` 增一張一次到位的現況表（24 個 test＝21 個掃描點＋1 個手機寬度＋2 個基準檢查），並註明計畫與 `unit-test-instructions.md` 的舊數字已過時、以此表為準。 | New |

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-07 Not re-checked this round

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `git diff --stat HEAD -- frontend/tests/e2e/a11y.spec.ts frontend/tests/e2e/a11y-baseline.json` | 無輸出 | 兩檔相對 HEAD 無變更；「基準未新增條目、沒有改程式」屬實。HEAD 的基準內容為 `entries: []` |
| 讀取 `a11y.spec.ts` 全檔 | 22 個編號 test＋2 個基準檢查＝24；掃描點 01–18、20–22＝21 | 與建置者回報的 24 passed／21 個結果檔一致 |
| 色值計算（`index.css` brand-100／brand-600） | 約 4.2:1 | 低於 WCAG 2.1 AA 一般文字門檻，支持第一列的疑慮；未跑 axe，屬靜態推算 |

### Summary

本輪只做回歸驗證，宣稱屬實：沒有改程式、基準維持空、可達性分析正確。但這次全綠無法證明新增的對話狀態與「查不到這個專案」符合 WCAG 2.1 AA，而其中一個狀態（「這句沒有送達」的淡色小字）依色值計算就很可能違規。這點需要使用者在核可前權衡：補掃描點，或明確接受該缺口。
