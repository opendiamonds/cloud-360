## Review
**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/construction/draft-ui/code-generation/code-generation-plan.md > findings report | 與本單元的前端直接相關：新前端依賴 `diagram_status`，而新 backend 在舊 volume 上缺 `user_diagrams.status` 欄位時，工作區與專案頁讀圖全數 500。已重新查證：`database.py`／`main.py` 啟動路徑沒有補欄位（`hierarchy_migration.py` 檔頭仍明寫「不掛在啟動路徑上」），`DEPLOY.md` 2.2.7「草稿狀態欄位」仍只寫手動執行 `run_hierarchy_migration.py` 並稱「可重跑：欄位已在就不動」。仍需人在關卡上裁決（啟動補丁或明列合併前檢查項），本單元無法自行處置。 | 與本單元的前端直接相關：新前端依賴 `diagram_status`，而新 backend 在舊 volume 上缺 `user_diagrams.status` 欄位時，工作區與專案頁讀圖全數 500。已重新查證：`database.py`／`main.py` 啟動路徑沒有補欄位（`hierarchy_migration.py` 檔頭仍明寫「不掛在啟動路徑上」），`DEPLOY.md` 2.2.7「草稿狀態欄位」仍只寫手動執行 `run_hierarchy_migration.py` 並稱「可重跑：欄位已在就不動」。仍需人在關卡上裁決（啟動補丁或明列合併前檢查項），本單元無法自行處置。 | New |
| R-02 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/construction/draft-ui/code-generation/code-generation-plan.md > findings report | 與本單元無直接程式關聯（後端 `decide`）。我同意偏差 #2 的方向：判定表第三列與 FR6.3b 互相衝突時，以「再說一次不另建」為準較安全。仍請人確認接受，並在需求或交接紀錄註明 FR2.2 第三列對草稿作業對象由 FR6.3b 取代。 | 與本單元無直接程式關聯（後端 `decide`）。我同意偏差 #2 的方向：判定表第三列與 FR6.3b 互相衝突時，以「再說一次不另建」為準較安全。仍請人確認接受，並在需求或交接紀錄註明 FR2.2 第三列對草稿作業對象由 FR6.3b 取代。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/construction/draft-ui/code-generation/code-generation-plan.md > findings report | 本單元可補充的證據：`ClarifyCandidates.tsx` 只渲染 `c.label`，後端（`brain_diagram_creation.py` 的 `with_truncation_note`）把「（其餘請用切換對象選取）」附在**最後一筆候選的標籤**上。`resume_draft_or_new` 的最後一筆依契約 C6 是「新建一張」，所以超過上限時按鈕會讀成「新建一張（其餘請用切換對象選取）」，說明句被讀成按鈕動作的一部分。偏差 #3 的另一半（FR3.5 失效時的說明句）前端也無處可放，因為 `ClarifyPayload` 沒有文字欄。不阻擋，但 tcms-test-cases 不得把 FR3.5 的說明句標為已覆蓋。 | 本單元可補充的證據：`ClarifyCandidates.tsx` 只渲染 `c.label`，後端（`brain_diagram_creation.py` 的 `with_truncation_note`）把「（其餘請用切換對象選取）」附在**最後一筆候選的標籤**上。`resume_draft_or_new` 的最後一筆依契約 C6 是「新建一張」，所以超過上限時按鈕會讀成「新建一張（其餘請用切換對象選取）」，說明句被讀成按鈕動作的一部分。偏差 #3 的另一半（FR3.5 失效時的說明句）前端也無處可放，因為 `ClarifyPayload` 沒有文字欄。不阻擋，但 tcms-test-cases 不得把 FR3.5 的說明句標為已覆蓋。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/construction/draft-ui/code-generation/code-generation-plan.md > findings report | 仍成立，範圍收窄並補證據。分享路徑已確認沒問題：`ShareModal.tsx` 對失敗回應 `alert(data.detail …)`，使用者看得到 409 的句子。評核路徑仍有缺口：`AssessmentPage.tsx` 的下拉清單（約 1319 行）列出含草稿的全部圖且不標示，發起評核失敗時（約 943 行）用 `res.text()` 直接顯示，畫面上是 `{"detail":"這張圖還是草稿，請先完成產圖"}` 的原始 JSON。另外 `WorkspacePage.goWellArchitected` 手上已有 `diagram_status`，卻對草稿照常寫回並導向評核頁，使用者要到下一頁才被拒。 | 仍成立，範圍收窄並補證據。分享路徑已確認沒問題：`ShareModal.tsx` 對失敗回應 `alert(data.detail …)`，使用者看得到 409 的句子。評核路徑仍有缺口：`AssessmentPage.tsx` 的下拉清單（約 1319 行）列出含草稿的全部圖且不標示，發起評核失敗時（約 943 行）用 `res.text()` 直接顯示，畫面上是 `{"detail":"這張圖還是草稿，請先完成產圖"}` 的原始 JSON。另外 `WorkspacePage.goWellArchitected` 手上已有 `diagram_status`，卻對草稿照常寫回並導向評核頁，使用者要到下一頁才被拒。 | New |
| R-05 | Minor | frontend/src/components/projects/SystemDiagrams.tsx > SystemRow 的「把架構圖掛到「…」」下拉（`candidates.map`，約 140–160 行） | 這個下拉列出「不在本系統下的我的圖」，其中包含草稿（例如草稿目前掛在系統 A，使用者在系統 B 的列看到它），選項文字沒有「（草稿）」標示。FR6.4 要求使用者要能辨識草稿，本單元只在已掛載清單（`attached`）加了 `DraftBadge`，同一檔內另一個列出圖的地方被漏掉，使用者可能在不知道是草稿的情況下把它搬到別的系統。偏差清單與 code-summary 都沒有提到這一處。 | 在該選項文字加上「（草稿）」（沿用 `isDraft`），並在 `diagram-drafts.spec.ts` 補一個斷言；或在偏差清單明寫「此下拉刻意不標示」與理由。 | New |
| R-06 | Minor | frontend/src/pages/WorkspacePage.tsx > `interface Diagram`（`diagram_status` 為選填，型別 'draft' 或 'ready'）；frontend/tests/e2e/diagram-drafts.spec.ts > `DiagramStub` | 本單元把 `MyDiagram` 改由產生型別推導，理由是「漏接欄位會在 `check:types` 與 `tsc -b` 紅燈」，但工作區仍用手寫的 `Diagram` 介面，且欄位是選填：後端改名或漏回該欄位時，歷史選單的「（草稿）」標示與 `data-draft` 會靜默消失，型別檢查不會報錯。e2e 的 `DiagramStub` 也是手寫，不是由產生型別推導，所以 stub 與真實回應若分歧，三個案例仍會綠燈。這正是 `team.md` 記載的「手寫 interface 讓前後端 schema 落差無效」的同一形狀。 | 讓 `Diagram` 以 `components['schemas']['DiagramDetail']` 或 `MyDiagramItem` 為基底（至少 `diagram_status` 取自產生型別且為必填），並讓 `DiagramStub` 以 `MyDiagramItem` 型別宣告。 | New |
| R-07 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/construction/draft-ui/code-generation/traceability.json | 本單元的追溯只宣告 `FR6.4` 一項，但計畫 Step 16 與 17 明列本單元承擔 `FR6.2`（手動存檔才送 `finalize`）、`FR6.4a`（計數排除草稿）、`FR3.4`（反問可點選）。這三項各有程式與 e2e 案例，卻不在追溯表，下游的覆蓋盤點與 TCMS 同步會把它們算成沒有承接單元。 | 補上 `FR6.2`、`FR6.4a`、`FR3.4` 三列，target 分別指向 `frontend/src/pages/WorkspacePage.tsx`、`frontend/src/components/projects/OverviewTab.tsx`、`frontend/src/components/brain/ClarifyCandidates.tsx`。 | New |
| R-08 | Minor | frontend/src/components/brain/ClarifyCandidates.tsx > 群組 `aria-label` 與「都不是」按鈕 | 四種新反問共用既有的 `aria-label`「請選擇你指的是哪一個」與回絕按鈕「都不是」。`new_or_modify`（「新建一張」／「修改目前的圖」）與 `resume_draft_or_new` 的選項是動作而不是「哪一個東西」，螢幕閱讀器念出的群組名稱與按鈕「都不是」語意不通。不影響功能，行為（回絕送 `candidateId: null`）正確。 | 依 `kind` 提供對應的 `aria-label`（可併入 `PROMPTS` 表），並讓動作型反問的回絕按鈕改為「都不要」或「我再講一次」。 | New |

> R-01 Reviewer note: Reviewer supplied prior ID R-01

> R-02 Reviewer note: Reviewer supplied prior ID R-02

> R-03 Reviewer note: Reviewer supplied prior ID R-03

> R-04 Reviewer note: Reviewer supplied prior ID R-04

### Summary
本單元的前端範圍乾淨：`finalize` 只由「儲存架構圖」按鈕經 `handleSaveDiagram` 送出，自動存檔（`autosaveDiagramXml`）與評核前寫回兩條路徑都不帶它，後端也只在 `request.finalize` 且圖為草稿時才轉正式；計數排除草稿；點選反問只送 `candidateId`，沒有任何客戶端識別碼被信任；三個 e2e 案例的斷言會因對應突變而紅燈。偏差判斷：#1、#4、#5、#7、#8 合理；#2 方向合理但需人確認（R-02）；#3 是契約缺少文字欄造成的未滿足項，前端只能顯示 label（R-03）；#6 成立（`ObjectPicker` 確實不列圖），但同檔還有一個列圖的下拉被漏標。無 Critical、一項沿用的 Major（R-01 部署順序，需人裁決），其餘為 Minor，判定 READY。我依指示沒有執行任何測試、建置或指令；後端 1601 測試、lint、build 與 Playwright 結果採作者自陳，未獨立複驗。
