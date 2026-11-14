## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-05 | Fixed | Minor | unit-test-instructions.md 第三節末已 append「綠燈不代表 incomplete 為空」一段，說明只以 violations 決定紅綠、ui-regression 無 artifact 上傳、要看 incomplete 須讀 test-results 附件或 pw-report.json。是否補 artifact 上傳留給 build-and-test，這是原審查就允許的處置。 |
| R-06 | Fixed | Minor | (a) MemberDetailPage.tsx 的 h2 已有 id member-detail-role-heading，select 改為 aria-labelledby 指向它，git diff 可見。(b) ContextBar.tsx 骨架已改 role="status"，該檔現已被 git 追蹤，diff 僅此一行與註解。另見下方新發現 2。 |
| R-09 | Fixed | Minor | code-summary.md 第四、五（兩處）、十、十四節各加一行現況指標，git diff 對該檔為 224 行純新增、0 行刪除，原文未動。指標指向的第十七節現況表本身已過時，見新發現 1。 |
| R-11 | Fixed | Minor | 實數 test( 為 28，@purpose／@given／@step 以外各標籤皆 28，@note 28（原 15 加 13），@step 60，@api 0。第 21、22 點 @story 為 N-9、US9.2。git diff 確認沒有任何既有 describe 或 test 名稱被改。計畫 Step 14 已勾。 |
| R-12 | Fixed | Minor | source-manifest.json 已補 frontend/src/components/brain/ConversationView.tsx。該檔實際存在，計畫字面寫的 components/ConversationView.tsx 不存在，以實際路徑為準的偏離已記入第十八節。 |
| R-13 | Still applies | Minor | traceability.json 已補 US9.2 並更新 A11Y-S9、N-9、D-04 的數字，但 A11Y-S10 的 note 仍寫「現況 24 個掃描點（01–18、20–25）」，而同檔 N-9 note 與 spec 現況為 25 個（含第 26 點）。第 20 至 25 點除 US9.2 外也沒有對應上游 id。同檔兩則 note 彼此矛盾。 |
| R-14 | Fixed | Minor | 第 26 掃描點存在（a11y.spec.ts:732-742 與 test 於 :1292），網址 /projects/not-a-number/members/OTHER_ID。讀碼推演：Number("not-a-number") 為 NaN，invalidProjectId 為 true，showLoading 為 false，shownError 取 PROJECT_NOT_FOUND_MESSAGE，:259-261 渲染 member-detail-error，member-detail-page 根節點 :246 無條件渲染，角色下拉在 canManage 區塊內不會出現。就緒與排除斷言與畫面一致。 |
| R-15 | Fixed | Minor | 第十七節開頭已加範圍補記，說明 unit-test-instructions.md 現況註記為該輪新增。 |
| R-16 | Fixed | Minor | unit-test-instructions.md 已 append 副本 node_modules 須為完整安裝的說明，並如實記錄本機無網路時以 cp -cR 複製 repo 現有依賴、完整性只由 lint、check:types、build 間接證明。 |

**New findings**

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/code-summary.md > 第十七節 > 5 現況表 | 第四、五、十、十四節新加的四個指標都指向這張表，但表內仍寫 test 數 27、掃描結果檔 24。現行數字是 28 與 25，只存在於第十八節。只讀指標與該表的人會得到過時數字，等於把 R-09 要消除的不一致換了個位置。唯一同時提到第十八節的是第四節那一個指標。 | 在該表加一行或加註「test 數 28、結果檔 25，見第十八節」，或把四個指標改為指向第十八節。原文不刪。 |
| Minor | frontend/src/components/brain/ContextBar.tsx:111 | role="status" 是 live region，輔助科技播報的是內容變化，不是 aria-label。這個 span 沒有文字內容，連線完成後也只是被移除，所以螢幕閱讀器不會唸出「連線中」，註解宣稱的「以禮貌模式宣告」並不成立。改動方向比原 role="img" 好，但效果被高估。 | 可選：在 span 內放視覺隱藏的「連線中」文字，或在註解改述為「語意上標為狀態」而不宣稱會被播報；也可明記為已知限制。不阻擋。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| git diff a11y.spec.ts | 48 行新增、9 行刪除，無既有 describe 或 test 名稱變動 | 唯一新增的 test 是第 26 點，以及 SCANS 內的 memberDetailInvalidProject；其餘為註解與計數文字。第 26 點相對 HEAD 屬新增，但計畫與第十八節已說明由 brain-infra A10 加入，不是本輪隱瞞的程式改動。 |
| 標籤實數 grep | test( 28，@purpose 28，@story 28，@note 28，@step 60，@api 0，@story 值 N-9 共 26、N-9、US9.2 共 2 | 與宣稱一致。 |
| tcms_sync.py 讀碼推演 | @story 規則為 pending.story = value，整行字串原樣保存，只輸出到描述的「User story」行；tcms_validate.py 只在 story 為空時 WARN | N-9、US9.2 單行寫法被正確處理，不會被拆壞或報錯。 |
| spec 內計數字串 | 檔數斷言以 ALL_SCANS 動態計算，說明文字的 25 與實際一致，無遺漏的 24 | 計數沒有硬編碼不一致。 |
| shasum -a 256 收據 8 檔 | package-lock.json、package.json、ReselectionBanner.tsx、a11y-baseline.json 的工作樹與 HEAD 皆等於收據；Sidebar.tsx、ContextBar.tsx、MemberDetailPage.tsx、a11y.spec.ts 的工作樹不同，但 HEAD 版皆等於收據 | 4 同 4 變成立，4 檔的收據值即 HEAD，收據之後的改動恰為工作樹未提交 diff，與第十八節第 0 小節一致。 |
| 計畫 git diff | 內文只有 Step 11 由 [x] 改 [ ]、Step 14 由 [ ] 改 [x]，其餘為新增九之二與九之三兩節；實數 28 勾、1 未勾 | 勾選依據成立。Step 11 的證據檔 a11y.spec.ts 已變動且 M1–M12 未重跑，維持未勾是正確的保守判定。Step 2 字面要求跑 memory-page.spec.ts 而本輪未跑，偏離已記錄。 |
| 突變推演 | 在固定句後注入無名稱 button，位於 member-detail-page 根節點內 | button-name 為 axe 的 critical 規則，該節點屬新元件根節點之內而非基準可收範圍，第 26 點會紅；還原後綠。推演成立，與第十八節記錄一致。本審查未執行任何測試，結果採信其記錄並以讀碼佐證。 |
| 行號核對 | MemberDetailPage.tsx :56、:138-140、:246、:259-261；Sidebar.tsx 248 附近 aria-label；ContextBar.tsx :111 | 皆與紀錄所述一致。 |

### Summary

這一輪把先前 9 項 Minor 中的 8 項落地，原文皆未刪除，第 26 掃描點與計畫勾選（28 勾、1 未勾）都有讀碼與雜湊證據支撐。剩餘的是 traceability.json 內 A11Y-S10 與 N-9 兩則 note 的數字互相矛盾，以及兩項不阻擋的文件與語意瑕疵，皆為 Minor，故判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | frontend/tests/e2e/a11y.spec.ts:182-187, :378-385, :513-523 | 掃描點 01、13、14、19 的入口頁都停在 `ContextBar` 的 `connecting` 狀態。`/api/brain/ws` 以空 handler 接管，永遠不送 `ready` 訊框，而 `ContextBar.tsx:37` 在 `status !== 'ready'` 時就是 `connecting`。`default`、`independent`、`no-object`、`unavailable` 四個狀態與連線後的入口頁 UI 從未被 axe 掃過；第一筆新元件違規（`span[aria-label="連線中"]`）恰好就出在這個降級狀態。`entry-page.spec.ts:58` 已有可讓連線進入 ready 的假伺服器。code-summary 第十一節第 7 點與第十四節第 7 點有揭露，但這是給 `build-and-test` 的開放項，不是 N-9「違規即紅燈」的覆蓋。`ContextBar` 同時掛在 `WorkspacePage.tsx:930` 與 `AssessmentPage.tsx:1240`（K-13），那兩處也無掃描。 | 至少增掃一個「已連線」的入口頁狀態（讓空 handler 改送 ready 訊框，沿用 `src/brain/testing/wsFrames.ts` 的建構器，`ContextBar` 進入 `default` 或 `no-object`）；或由使用者明確裁決接受只掃 connecting 狀態，並把該限制寫進 `unit-test-instructions.md` 與 N-9 的覆蓋說明，而不只留在交接清單。 | Resolved (reviewer) |
| R-02 | Major | frontend/tests/e2e/a11y-baseline.json:5-6; frontend/tests/e2e/a11y.spec.ts:642-661; frontend/src/components/Sidebar.tsx:324-328 | 唯一的基準條目放行 Sidebar 空選單提示 `<p>` 的 `color-contrast`（`text-gray-400` 約 2.6:1）。(a) 事實面屬實：該字串由 `af73f03f`（2026-07-11）引入，並非本 intent 新增。(b) 但出現條件是 `!showCoreSection && !showAdminSection`（`Sidebar.tsx:324`），即沒有 A1、A3、J3a、J3b 權限的帳號；這正是只用大腦入口、專案、記憶的新功能使用者，所以入口頁對本 intent 的目標使用者確實有一段 AA 不合格文字。(c) 修法是 `Sidebar.tsx` 一個 class，而 `git diff` 顯示本 intent 已在改這支檔（`showEntry`、`showProjects`）。(d) 選擇器取得的過程：計畫第四節的停損是「頁殼節點取不到穩定選擇器就停下回報」（D-04）。第一次實跑得到 `null`，實作者隨後在 `stabilize()` 的 role 對照表補上 `p: 'paragraph'`，條目才得以進基準。code-summary 第十一節第 5 點有誠實揭露並請審查者確認，但等於是閘門在停損觸發後被擴充到可放行。`implicit` 對照表也因此成為開放的放行面（`a`、`button`、`li`、`h1-h4` 等頁殼節點之後都能取到 role＋文字名稱而進基準）。 | 由使用者裁決：優先將 `Sidebar.tsx:325` 的 `text-gray-400` 改為達 4.5:1 的色階（與本次三處屬性修正同性質，順手移除唯一的基準條目，讓基準清單為空）；若仍選擇列入基準，則在 `a11y-baseline.json` 的 reason 補上「受影響的是只具 K 系列權限的帳號」，並記錄 D-04 停損在此以擴充 role 對照表處置。 | Resolved (reviewer) |
| R-03 | Minor | frontend/tests/e2e/a11y-baseline.json:6; frontend/tests/e2e/a11y.spec.ts:669 | 基準鍵 `role=paragraph[name="…"]` 不是可解析的 Playwright 定位器：`paragraph` 角色不從內容取名，`getByRole('paragraph', { name })` 找不到該節點。它只是以文字為鍵的識別字串，與 `selector` 欄名稱暗示的「選擇器」不同。任何其他頁殼 `<p>` 只要文字相同且 `color-contrast` 同樣失敗，也會被一併放行；文案一改則同時出現過期與新違規，會大聲失敗，這一側是安全的。 | 在 `a11y-baseline.json` 或 spec 註解註明該鍵是「role＋文字」識別字而非定位器，避免日後有人拿去除錯；或改用 `p` 外層的 `div` 加穩定屬性後以屬性定位（若選擇修 Sidebar 則此項自動消失）。 | Resolved (reviewer) |
| R-04 | Minor | frontend/package.json:25; frontend/package-lock.json | `package.json` 寫 `"@axe-core/playwright": "^4.13.0"`，lockfile 鎖在 4.13.0（`git diff --stat` 為 +24）。A11Y-S3 的 14 天規則是被 caret 在 `npm install` 時以 4.14.0 繞過的（code-summary 第四節自述）。CI 與 `frontend/Dockerfile:8` 都用 `npm ci`，不受影響；但任何人日後 `npm install` 重解析會浮到不滿 14 天的版本。授權為 MPL-2.0，已記錄，僅 devDependency。 | 將 `package.json` 改為精確版本 `4.13.0`（或 `npm install --save-exact`），使規則由 manifest 本身承載，不靠使用者記得用 `npm ci`。 | Resolved (reviewer) |
| R-05 | Minor | frontend/tests/e2e/a11y.spec.ts:703-707 | `incomplete`（needs review）只附在 Playwright attachment 上，不影響紅綠；code-summary 第十四節第 5 點確認 `ui-regression` 無 artifact 上傳，綠燈時 axe 結果零留存。`color-contrast` 在有背景圖或疊層時常以 `incomplete` 回報，因此該類節點既不被擋、也看不到。A11Y-S8 只規定 violations 擋閘，這符合上游；缺口在可見性。 | 在 `build-and-test` 判定是否補 artifact 上傳；至少在 `unit-test-instructions.md` 註明「綠燈不代表 incomplete 為空」。 | Unresolved |
| R-06 | Minor | frontend/src/pages/MemberDetailPage.tsx:239; frontend/src/components/brain/ContextBar.tsx:53 | 屬性修正本身正確且 `git diff` 確認 `MemberDetailPage.tsx` 只增 1 行、`ReselectionBanner.tsx` 只換兩個色階 class（amber-600→700、hover 700→800，白字對比約 5.0:1），無 test-id、行為或版面變動。兩點可更好：(a) `aria-label="專案角色"` 與正上方 `<h2>專案角色</h2>` 同字但各自維護，改用 `aria-labelledby` 指向該 `h2` 的 id 可只留一個來源。(b) `ContextBar` 骨架 `<span role="img" aria-label="連線中">` 讓輔助科技多唸一個「連線中，圖片」，但狀態切換後沒有播報；載入指示通常用 `role="status"`。另外 `ContextBar.tsx` 為未追蹤檔（U14 尚未提交），無法用 `git diff` 驗證「只動一個屬性」，只能依 code-summary 第五節的自述。 | 可選：(a) 改 `aria-labelledby`；(b) 評估骨架改 `role="status"` 或在 U14 提交後以 diff 複驗該行為唯一變動。 | Unresolved |
| R-07 | Minor | frontend/tests/e2e/a11y.spec.ts:1045-1049; frontend/tests/e2e/a11y.spec.ts:1055 | 過期檢查要求結果目錄恰為 18 個檔，與 `-g` 單跑、`--shard` 或任何子集執行都會紅（code-summary 第十一節第 10 點已承認為設計）；且 `seen` 集合也納入 `inNewRoot` 的條目，因此一筆只對得到新元件節點的基準條目永遠不算過期、也永遠不放行。後者無害（掃描層仍判 fresh 而失敗），前者只是使用手感，但 `unit-test-instructions.md` 與 TCMS 同步若以單案跑會誤報。 | 在 `unit-test-instructions.md` 明寫「本檔必須整檔執行，不得 `-g` 或 shard」；確認 `ui-regression` 不 shard。 | Resolved (reviewer) |
| R-08 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/code-summary.md > 十六、Step 16 回歸驗證 > 新狀態的可達性；frontend/src/components/brain/ConversationView.tsx:24-26 | 「24 passed」只證明既有 21 個畫面狀態沒有退步，不能當作新狀態合格的證據。可達性分析本身屬實：`a11y.spec.ts` 第 187、382-385、397-400 行的 WebSocket handler 只回送握手快照，沒有送出使用者訊息或非輪次錯誤訊框；唯一的非 200 回應是第 608 行的 500，沒有 404。結果是「這句沒有送達」「回覆中斷」「你在回覆完成前離開了這一頁」三種狀態都沒被掃過。其中 `ConversationView.tsx:25` 的 `text-xs text-brand-100` 疊在 `bg-brand-600` 上，依 `index.css:9、14` 的色值（`#dbeafe` on `#2563eb`）計算約 4.2:1，低於一般文字的 4.5:1，很可能是 `color-contrast` 違規；重試鈕繼承同色，且 `disabled:opacity-40` 會更淡。閘門目前對這個畫面是靜默放行。Step 16 的停損條款（「新出現的違規應修元件，出現即停下」）在沒有掃描點的狀態上永遠不會觸發。 | 不要把 Step 16 的全綠當成這三個新狀態已通過。在 `build-and-test` 之前（或合併前）補掃描點：在已連線入口頁用 `wsFrames` 建構器送出使用者訊息，再送非輪次錯誤訊框觸發 `rejected`，並加上 `brain-system-notice`；另加一個回 404 的專案詳情或成員頁掃描點。若 `rejected` 態確實有對比違規，依計畫第四節第 1 類把 `text-brand-100` 改成較深的色階，不要收進基準。若選擇不補，需明確把這些狀態記為「閘門未覆蓋，改以人工驗證」，並把該對比疑慮列為已知風險。 | Resolved (reviewer) |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/code-summary.md > 十四、開放項第 9 點（另見第四節、第五節的「基準 1 筆」、檔案表） | 這幾處仍寫 Sidebar 空選單提示的對比 2.6:1「已列入基準」。實際上 `Sidebar.tsx:325` 已改為 `text-gray-600`，`a11y-baseline.json` 在 HEAD 即為 `"entries": []`，`git diff --stat` 對該檔與 `a11y.spec.ts` 皆無輸出。所以沒有違規變成無人把關：該節點已修好，若退步會讓掃描層變紅。不一致只存在於文件，`code-summary-corrections.md` 第三節已更正，主檔卻沒同步，只讀主檔的人會得到錯誤的現況。 | 在 `code-summary.md` 的第四、五、十四節就地加註「已由 corrections 第三節取代」，或直接更新那幾句，讓基準現況只有一種說法。 | Unresolved |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/code-generation-plan.md > 一、範圍；Step 8；unit-test-instructions.md 第 14、21、58-59 行 | 數量宣稱有三個版本：計畫與 `unit-test-instructions.md` 寫 21 個 test、18 個掃描點、讀回 18 或 19 個結果檔；corrections 寫 22 個；實際為 24 個 test、21 個掃描點、21 個結果檔。spec 內的過期檢查（第 1177-1178 行）已用 21，與實跑一致。`unit-test-instructions.md` 凍結不改，但裡面「18 個畫面狀態全部被掃描」的覆蓋目標已不是現況，會讓使用者誤以為覆蓋面是 18 點且完整。 | 在 `code-summary.md` 增一張一次到位的現況表（24 個 test＝21 個掃描點＋1 個手機寬度＋2 個基準檢查），並註明計畫與 `unit-test-instructions.md` 的舊數字已過時、以此表為準。 | Resolved (reviewer) |
| R-11 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/code-generation-plan.md > Step 14 | 計畫 Step 14 仍未勾。計畫要求每個 test 加 @note，目前 27 個 test 中有 12 個沒有；第 21、22 點的 @story 寫 US9.2 而計畫指定 N-9。撰寫標準把 @note 列為非必填，tcms_validate 27 個案例 ERROR 0、WARN 0，所以實質風險低，但計畫與實作對不上，單元無法乾淨結案。 | 二擇一：替缺少的 12 個 test 補 @note，或在計畫就地修訂 Step 14 為 @note 非必填、第 21、22 點 @story 為 US9.2 並勾選。 | Unresolved |
| R-12 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/source-manifest.json > writes | 清單未列 frontend/src/components/brain/ConversationView.tsx，但為了通過第 24 點，本單元在 review-02 期間改過該檔的一個色階 class（text-brand-50）。code-summary 的重做段已自述此事，清單與實際不一致。 | 把該檔補進 writes，或在 traceability 或 corrections 標明該改動的歸屬單元。 | Unresolved |
| R-13 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/traceability.json > A11Y-S9、A11Y-S10、N-9、D-04 | 這幾項的說明數字仍是 21 test、18 點、基準 1 筆，且沒有涵蓋第 20 至 25 點與 U16 的 US9.2。traceability sensor 本就因無 NFRx.y 而回報 fail，數字過時讓人更難分辨哪些是已知落差。 | 更新這幾項的數字與 target，並加入第 20 至 25 點對應的上游 id。 | Unresolved |
| R-14 | Minor | frontend/src/pages/MemberDetailPage.tsx:44-56、:139、:259-261；frontend/tests/e2e/a11y.spec.ts 掃描點 10 與 25 | 顯示條件改寫對掃描點等值：showLoading 為 isLoading 且非 invalidProjectId、shownError 為 invalidProjectId 時取固定句否則取 error；掃描點 10 用數字 PROJECT_ID 17 進頁，invalidProjectId 為 false，兩個條件與改寫前完全相同；非數字時 isLoading 永遠為 true，下方「找不到這位成員」與主內容區都用原始 isLoading 閘住，不會與固定句同時出現。但這個新狀態（詳情頁非數字 projectId 的固定句）沒有掃描點，掃描點 25 只涵蓋成員清單的 404。該狀態用的是與清單頁相同的 text-red-700 字級樣式，實質風險低。 | 在 build-and-test 或下一次動 a11y.spec.ts 時補一個詳情頁非數字 projectId 的掃描點（網址例如 /projects/abc/members/1），或明記接受該缺口；code-summary 第六節第 4 點已列，請 conductor 確實併入 merge-blockers。 | New |
| R-15 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/code-summary.md > 十七（開頭宣稱） | 開頭寫「不改任何程式、測試、共用文件，只寫本節、traceability.json 四則 note、計畫的勾選」，但工作樹同時有 unit-test-instructions.md 新增 2 行「現況註記」（2026-10-31）。該註記是計畫九之二指定要引用的內容，屬預期變動，只是開頭的範圍宣稱不完整。 | 在第十七節補一句說明 unit-test-instructions.md 第 56 行的現況註記為本輪新增，使範圍宣稱與工作樹一致。 | New |
| R-16 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/a11y-gate/code-generation/code-summary.md > 十七 > 2 回歸（副本） | 可複驗性：我以 rsync 複製 frontend 後，repo 現況的 node_modules（Oct 18）在副本內 npm run build 失敗，tsc 報 react-router-dom 與 vite 等 TS2307；改用前輪 a11y-copy 的 node_modules 實體複製後 build 成功。第十七節只寫「rsync 實體複製 frontend」，沒說明 node_modules 需另備一份完整依賴，後人照字面操作會得到建置失敗。 | 在第十七節或 unit-test-instructions.md 的現況註記補一句：副本須使用依 package-lock.json 完整安裝的 node_modules（例如在副本內 npm ci），不可直接沿用 repo 現況的。 | New |

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-09 Not re-checked this round

> R-11 Not re-checked this round

> R-12 Not re-checked this round

> R-13 Not re-checked this round

> R-14 Not re-checked this round

> R-15 Not re-checked this round

> R-16 Not re-checked this round
