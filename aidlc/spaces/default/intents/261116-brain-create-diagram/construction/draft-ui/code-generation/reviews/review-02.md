## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-11-22T13:29:59Z
**Iteration:** 1

**Prior findings**

| ID | Now | Severity | Note |
|----|-----|----------|------|

**New findings**

| Severity | Location | Finding | Required action |
|----------|----------|---------|-----------------|
| Minor | backend/tests/test_brain_diagram_creation_flow.py > test_create_that_hangs_times_out_and_the_connection_keeps_working（約 516–563 行）；backend/services/brain_gateway.py > `_create_and_dispatch` 的 `self.timing.wait_for(create(), ...)` | 逾時測試把 `wait_for` 換成替身，並以「替身協程被取消」代表「沒有建出圖」，最後斷言只有一張草稿。正式路徑是同進程 ASGI 呼叫 `collab_router.create_diagram`（同步 `def`，在執行緒池內 INSERT），取消等待端並不會中止已在執行緒內的寫入，所以逾時後草稿仍可能稍後才寫入，之後使用者重說時系統下就有兩張同名草稿的視窗（15 秒內）。真正的 `asyncio.wait_for` 加執行緒池取消路徑沒有任何測試走過，「不重試、不交辦」成立，但「不會多出草稿」不成立。 | 在 `code-summary.md` 的修訂 1 偏差段與 `CREATE_UNKNOWN_MESSAGE` 的說明中明寫「逾時後草稿可能稍後才出現，由 FR6.3a 的接續草稿反問收斂」；測試註解不得宣稱逾時等於沒有建圖。若要保證，另以會延遲寫入的真實端點（`dependency_overrides` 加 sleep）補一案。 |
| Minor | backend/models.py:131；schema_rbac.sql:416–419（`user_diagrams.status` 的註解）；backend/services/hierarchy_migration.py 模組 docstring | 三處註解仍寫「既有非空資料庫由 `_ensure_hierarchy_schema()` 補欄位」或「演進路徑是 `_ensure_diagram_status_column()`」，沒有提到修訂 1 新增的啟動補丁 `database._ensure_diagram_status_schema()`（`database.py` 的 `init_db` 才是實際的既有環境升級路徑）。下一位改 DDL 的人會以為只有部署期遷移這一條路，而 DEPLOY.md 已寫成啟動時自動補。 | 三處註解各補一句「啟動時由 `database._ensure_diagram_status_schema()` 補欄位（只補這一欄）」，與 DEPLOY.md「草稿狀態欄位」一節一致。 |
| Minor | frontend/src/pages/WorkspacePage.tsx:26–33（`type Diagram`）；frontend/src/types/api.d.ts:1852（`MyDiagramItem.updated_at: string \| null`） | 修訂宣稱 `Diagram` 改由產生型別推導，但 `updated_at` 仍手寫為 `string`，與產生型別的 `string \| null` 分歧；`fetchDiagrams` 把 `res.json()`（any）直接放行，`tsc -b` 對此無效，後端若回 null，選單的 `new Date(d.updated_at)` 會顯示 1970 年日期。 | `updated_at` 改取自 `MyDiagramItem['updated_at']` 並在選單顯示處處理 null（顯示空字串或破折號），讓「由產生型別推導」的說法對全部欄位成立。 |
| Minor | frontend/src/components/brain/ContextBar.tsx:93；aidlc/spaces/default/intents/261116-brain-create-diagram/construction/draft-ui/code-generation/traceability.json > FR6.4 | FR6.4 要求草稿在「切換對象選單」標示。大腦新建後作業對象就是那張草稿，而脈絡列的「架構圖」層只顯示 `diagramName`，沒有草稿標示；`ObjectPicker` 不列圖所以無處可標。此事已在偏差 #6 說明，但 traceability 仍把 FR6.4 標為 OK，且目標只指向專案頁的 `SystemDiagrams.tsx`。 | 二擇一：脈絡列的圖名後加「（草稿）」（需要作業對象帶狀態，屬契約變更，建議留到後續）；或在 `traceability.json` 的 FR6.4 列以 note 載明「切換對象選單與脈絡列未標示，已知缺口」，避免下游把它讀成完全覆蓋。 |

### Notes

審查範圍為 draft-ui 單元，並依簡報查驗了修訂 1 的跨單元宣稱。逐項結論（皆為靜態閱讀，未執行任何測試）：

1. **Step 23（403 分流）**：`ARCH_FORBIDDEN_DETAIL_PREFIX` 移到 `models.py` 並由 `rbac.require_arch_action` 以同一常數組字串，偵測是前綴比對、只存布林值，且與 `HierarchyForbidden` 的「權限不足：需要 K2.edit」前綴不重疊，分流是對的。端點測試真的讓角色被撤權與 K2 被撤權兩種 403 各跑一次，能失敗。新文字 `CREATE_FORBIDDEN_MESSAGE` 已由開發者標明需人確認。
2. **Step 20（啟動補丁）**：失敗即啟動失敗的理由成立（ORM 已映射該欄，缺欄位時讀圖必然 500），`main.py` 的 startup 對 `init_db()` 沒有吞例外，單一 uvicorn 程序無多工作者競爭。DEPLOY.md、LOCAL-DEV.md、`schema_rbac.sql` 的欄位名、預設值、約束名一致，且回退到舊版後草稿等同正式圖的後果已寫明。唯一缺口是註解（見上表第二列）。
3. **Step 24/25（性質測試）**：性質 1 與性質 4 現在直接斷言判定結果，性質 4 的 p 由測試自己依 t 構造，區域邊界的浮點運算在 [0.5, 1] 內是精確的，不會產生越界 p。碼位上限常數與端點常數有相等測試；預留 12 碼位恰好讓「主題 184＋後綴 4＋重名 12」等於 200。能失敗。
4. **Step 26（前端）**：`readErrorDetail` 正確處理非字串 detail 與非 JSON；掛圖與評核下拉標示草稿；`ClarifyKind` 以 `Record` 窮舉，新增 kind 時編譯會失敗；`finalize` 只由「儲存架構圖」按鈕送出，自動存檔的 PUT 本體在 e2e 中被斷言不含該鍵。
5. **製程備註**：以 `git status` 與 manifest 比對，變更與新增的非 aidlc 檔案全部出現在三個 `source-manifest.json` 的 `writes`，沒有重複、也沒有多出的條目；`work_orchestrator_capabilities.py` 與前端各檔的 diff 沒有雜訊或遺失行；`brain_diagram_creation.py` 內的不可見字元（ZWJ、U+2028／2029）位元組完整。
6. **追溯**：draft-ui 的 `traceability.json` 已含 FR3.4、FR6.2、FR6.4、FR6.4a，目標檔案皆存在。

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

> R-01 Not re-checked this round

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-07 Not re-checked this round

> R-08 Not re-checked this round
