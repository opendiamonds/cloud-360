# 部署後追加：專案頁的大腦入口與架構圖計數

- 紀錄時間（`date -u`）：開工 `2026-11-15T02:11:05Z`，收尾 `2026-11-15T02:28:26Z`（UTC）
- 分支：`danniel/feat/project-page-brain-entry`（從 `origin/ut` 開出）
- 未 commit、未 push、未跑 `gh`、未觸發 CI、未連 staging 或任何共用 DB／Redis
- 只動前端；**後端、`openapi.json`、`ws-contract.json` 零變更**（`git diff --stat -- backend openapi.json ws-contract.json` 無輸出）

## 範圍揭露（本階段新增、已核可 scope／requirements 尚未涵蓋）

2026-11-15 使用者在 staging 看過專案總覽頁後選定「先做 1＋2，3 開新 intent」。第 1、2 項是**部署後才新增的範圍**，
已核可的 `scope-document.md`、`requirements.md`、`stories.md` 都沒有涵蓋，**不得**讀成任何既有 FR／AC 的自然延伸。
第 3 項「讓大腦新建一張架構圖」**不在本次範圍**：沒有做，也沒有為它鋪路（未動大腦後端、未動 ws 契約、未新增任何
大腦能力；前端「問大腦」面板送出的仍是既有 `user_message`）。

同一段揭露逐處寫在程式內：`frontend/src/projects/workspaceHandoff.ts` 檔頭、`ProjectTargetNotice.tsx` 檔頭、
`SystemDiagrams.tsx` 檔頭、`OverviewTab.tsx` 檔頭、`ProjectDetailPage.tsx` 檔頭、`WorkspacePage.tsx:65-67` 註解、
`project-pages.spec.ts` 新 describe 的檔頭。

### 回補項（指派回上游，由主 session 決定落點；本輪未改 `requirements.md`／`stories.md`）

1. **requirements 新 FR（建議草稿，待上游定案）**
   - 專案總覽每個系統提供「在工作區建立架構圖」：經既有作業對象設定把對象設為該系統，**伺服器確認後**才前往工作區，
     工作區以空白畫布開啟；作業對象僅限使用者擁有的專案（`[OP3]`=A），非擁有者停用並說明；無 `K1` 或無 `A1 edit` 不顯示。
   - 專案總覽的「架構圖」計數＝使用者自己的、掛在本專案各系統的架構圖張數；缺 `A1 view` 顯示「尚無法取得」；
     載入中與失敗分別標示，不顯示 0。此 FR **取代** `BR86.1`／`OPEN-PP23-1` 的固定佔位。
   - 專案頁在 `K1 view` 時掛脈絡列、作業對象提示與收合的「問大腦」面板，讀寫共享段；進頁不改作業對象，
     目前對象不在本專案時提供一鍵改設（非擁有者停用並說明）。
2. **user-stories 新 AC**：對應上面三條各補 AC（含拒絕態、無 K1 態、計數的排除條件）。本輪 e2e 規格註解暫掛
   `US9.1`（兩案）、`US11.3`、`US2.1`，回補後應改指新 AC。
3. **traceability**：`hierarchy-service`／`entry-page-ui` 等單元的 `traceability.json` 未補記，待回補時一併加
   `scope: added-after-deployment` 的 coverage 列。
4. **TCMS**：新增 4 個自動化案例未同步，屬 `tcms-test-cases` stage。

## 設計決定與理由

### 第 1 項：系統卡片的「在工作區建立架構圖」

| 決定 | 理由 |
|---|---|
| 設定作業對象只經既有 `BrainConnection.setWorkTarget`（`ObjectPicker` 用的同一條 `set_work_target`），三層 id 由 `objectPickerModel.targetIdsForSystem` 產生 | brief：沿用既有機制、不另造一套；`String()` 轉換只有一處（`OPN-21`） |
| **送出後等伺服器回推同一個 `systemId` 才導頁**；8 秒（`HANDOFF_TIMEOUT_MS`）未確認則不導頁並顯示「大腦沒有確認作業對象，沒有前往工作區…」 | 伺服器以擁有者範圍解析對象，不合格時不會回推該系統。若送出即導頁，使用者會在「其實沒設成」時落到工作區，存檔後圖不會掛到系統，而畫面看起來正常。同時避免頁面卸載關閉連線與伺服器處理競速。P2 突變證明「不設對象就導頁」會紅 |
| 目前對象已是該系統 → 不送設定、直接前往 | 省一次往返；結果相同 |
| 工作區收到導覽 state（`cloud360StartNewDiagram`）時**開空白畫布**，不還原上次的圖與其對話；bootstrap 結束後以 `replace` 清掉 state，重新整理不再觸發 | 否則使用者落在舊圖上，存檔是更新舊圖而不是建新圖，F1 的「存新圖依作業對象掛到系統」不會發生，動作名稱就是假的。這是本輪唯一動到 `WorkspacePage.tsx` 的地方（約 10 行），e2e 以「上次開的是圖 7、選單值為空」斷言 |
| 事件掛點只在 `SystemDiagrams` 呼叫一次（`useWorkspaceHandoff`），各系統列共用待決狀態 | `brainSession.subscribe` 的契約是一頁一個掛點；專案頁沒有其他同步掛點 |
| **非擁有者：照列、`aria-disabled`、旁附說明**「大腦目前只能以你建立的專案為作業對象」，以 `aria-describedby` 連結；點擊無作用 | brief 與 `[OP3]`=A；說法、`aria-disabled` 可聚焦的形狀與 `ObjectPickerGroup` 一致。擁有者判定用既有唯一一處 `objectPickerModel.isOwnedByMe`（`OPN-12`），不在新元件寫 `owner_user_id`（`PPN-16`）。這不是授權，伺服器照樣以擁有者範圍解析 |
| 連線未就緒時同樣停用並說明「大腦連線就緒後才能設定作業對象」 | `setWorkTarget` 未 ready 時不送；與其按了才報錯，不如事先標示 |
| **沒有 `K1`：不顯示**（不採「只導到 `/workspace`、不設作業對象」） | 這個動作的價值在於存檔後掛到系統，而掛載靠作業對象；沒有大腦連線就沒有作業對象，導到工作區存出來的圖不會掛上，畫面卻像成功——正是要避免的失敗形狀。無 `K1` 者仍可從側欄進工作區，再於本區「掛上」 |
| 缺 `A1 edit` 不顯示（`canArch('edit')`） | brief；工作區沒有編輯權就建不了圖 |
| 系統列在圖清單載入中或失敗時也照列 | 建立動作不依賴圖清單，不該因為清單失敗而消失 |
| 說明句為第二份副本（`workspaceHandoff.NOT_OWNED_TARGET_NOTE`），`ObjectPickerGroup.tsx` 那份未改 | 那份屬已交付 `U16` 且在選單檔案集合的 lint 區塊內；兩者一致由 e2e 各自逐字斷言承擔（`team.md`「單一真實來源」的副本規則）。列為未完成項：日後應收斂成一處 |

### 第 1 項：架構圖計數

| 決定 | 理由 |
|---|---|
| **前端就算得出來，不改後端** | 讀過來源：`OverviewTab.tsx`（原 `:102-105` 固定「尚無法取得」）；能用的資料是 F1 新增的 `GET /api/collab/diagrams` 每列 `system_id`（`collab_router.py:358`：**只對自己擁有的圖給值**）與 `GET /api/hierarchy/projects/{id}/systems` |
| 計數＝「我的圖」中 `system_id` ∈ 本專案系統 id 的張數（`OverviewTab.attachedCount`） | 不數其他專案的系統、未掛載的圖、別人分享給我的圖（伺服器對後者一律給 null，`listMyDiagrams` 也只留 `is_owner`） |
| **可見範圍＝只數自己的圖**，畫面註明「你掛在這個專案各系統的架構圖」 | brief：不得洩漏使用者看不到的圖。若改後端數「系統下全部的圖」，非擁有者成員會得知他打不開的圖的存在與數量；且與旁邊「系統的架構圖」區（只列自己的圖）口徑一致。代價：非擁有者成員看到的是自己的張數（通常為 0），因為依 F1 規則只有專案擁有者能掛圖——已以註明文字避免被讀成「這個專案沒有圖」 |
| 圖清單抓取由 `SystemDiagrams` **上提到 `OverviewTab`**，同一份傳給兩處；掛載／取消後重抓，計數跟著變 | 單一真實來源：同一份事實不抓兩次、不各算一套 |
| 缺 `A1 view` 仍顯示「尚無法取得」並註明「你沒有檢視架構圖的權限」；載入中「載入中…」；失敗「無法取得」 | 不顯示 0（0 會被讀成「沒有圖」）；沿用本籤「未填需求欄位」的三態做法。既有 e2e `renders honest placeholders…` 的世界沒有 A1，斷言不變，只更新其規格註解（名稱未改，TCMS 不孤兒） |

### 第 2 項：專案頁的大腦面板

| 決定 | 理由 |
|---|---|
| 掛脈絡列、作業對象提示、收合的「問大腦」面板，與工作區／評估頁同一組元件（`ContextBar`、`SubpageBrainPanel`），**只在 `K1 view` 時掛載**；無 `K1` 不開連線 | brief；P4 突變證明無 K1 掛載會紅 |
| 連線以 `page='entry'` 開，脈絡列 `sharingToggle={false}` | ws 契約的 `page`／`scope` 只有 entry／workspace／assessment，**不改契約**；專案頁沒有自己的獨立段，讀寫與入口頁相同的共享段，能做的事也與入口頁相同（brief：交給既有大腦流程，前端不新增能力） |
| **進頁不改作業對象**；目前對象不在本專案時顯示琥珀色提示「目前作業對象「…」不在這個專案內，大腦會以它為準回答」＋「把作業對象設為這個專案」 | 作業對象跨頁共用，進頁悄悄改掉會讓別頁的對話對象被換掉。形狀沿用 `SyncNotice`（同一條提示列）；改設只經 `setWorkTarget`、id 由 `targetIdsForProject` 產生；送出失敗說法與 `ObjectPicker` 相同 |
| 非擁有者：按鈕 `aria-disabled` ＋ 同一句說明；連線未就緒或尚未收到作業對象時不渲染提示 | `[OP3]`=A；沒收到對象時無從判斷「在不在本專案內」 |

## 改動檔與行（`grep -n` 實查）

- 新檔 `frontend/src/projects/workspaceHandoff.ts`：`:32` `HANDOFF_TIMEOUT_MS`、`:38` `NOT_OWNED_TARGET_NOTE`、`:41` `isNewDiagramHandoff`、`:56` `useWorkspaceHandoff`、`:64` 導頁、`:71` `onWorkTarget` 確認、`:100` `setWorkTarget`
- 新檔 `frontend/src/components/projects/ProjectTargetNotice.tsx`：`:25` 元件、`:32` 「已在本專案」不渲染、`:38` 改設
- `frontend/src/components/projects/SystemDiagrams.tsx`：`:39` `MyDiagramsLoad`、`:41` `CreateInWorkspace`、`:60` `aria-disabled`、`:175` `useWorkspaceHandoff(brain)`、`:177` 擁有者判定、`:179` `showCreate`、`:233` 每列掛動作；圖清單抓取移出
- `frontend/src/components/projects/OverviewTab.tsx`：`:35` `attachedCount`、`:108` `listMyDiagrams`、`:135` 計數值、`:168` 計數列、`:177` 傳給 `SystemDiagrams`
- `frontend/src/pages/ProjectDetailPage.tsx`：`:116` `brainEnabled`、`:117` `useBrainConnection('entry')`、`:315-320` 大腦區塊、`:339` 傳連線給總覽
- `frontend/src/pages/WorkspacePage.tsx`：`:2` `useLocation`、`:13` 匯入、`:68` `startNewDiagramRef`、`:316` 跳過還原、`:339-341` 清除導覽 state
- `frontend/tests/e2e/project-pages.spec.ts`：`:918` 既有案例規格註解更新（名稱不變）、`:1327` `ProjectBrainServer`、`:1368` `withBrain`、`:1412` 新 describe `Project page brain entry`、`:1426`／`:1456`／`:1488`／`:1516` 四個新案例
- 無 DDL、無 seed、未動 `database.py`／`nginx.conf`／`.env.example`／`render-env.sh` → **不觸發** `schema_rbac.sql`／`DEPLOY.md`／`LOCAL-DEV.md` 同步

## ADR-0006 四面向判定

| 面向 | 判定 | 影響與處置 |
|---|---|---|
| IAM | **適用（不新增授權路徑）** | 兩個新控件都只送既有 `set_work_target`，伺服器仍以 `K1` 握手 ＋ `resolve_work_target` 擁有者範圍判定；前端的擁有者判定只決定畫面是否出現必然被拒的控件（`isOwnedByMe` 不是授權）。非擁有者停用並說明，P1b／P1c 證明「非擁有者按得動」會紅。導頁以伺服器回推為準，不以前端送出為準。掛載面板以 `K1 view` 把關（P4）。無新端點、無矩陣變更 |
| encryption | **不適用（附理由）** | 無新儲存欄位、無新傳輸通道；沿用既有 WebSocket 與 HTTP |
| network exposure | **不適用（附理由）** | 無新 HTTP path、無新 ws 訊息型別、無新埠；專案頁多開一條既有 `/api/brain/ws` 連線（每頁一條，與其他頁相同） |
| audit logging | **不適用（附理由）** | 作業對象變更沿用既有閘道路徑，無新寫入；計數為唯讀。未新增日誌 |

PBT hard constraint：不涉 IaC generator、cost calculator、agent routing 的判定邏輯，無 PBT 義務（agent routing 未改）。

## 測試實跑（全部在 `$S/pb-copy` 副本）

環境：前端 `node_modules` 以 `cp -Rc` 複製；e2e 對副本的正式建置 `vite preview`（`127.0.0.1:4182`、突變用 `:4183`）執行，全部 `page.route`／`routeWebSocket` 攔截。後端未改，未跑 `unittest`。

- `npm run lint`：`✖ 2 problems (0 errors, 2 warnings)`（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:356` 皆 `exhaustive-deps`，既存；後者是 `fetchDiagrams`，非本輪加入的依賴）
- `npm run build`：`✓ built`（既存的 chunk 大小提示）
- `npm run check:types`：`API 型別檔與規格檔一致。`；`npm run check:ws-types`：`WS 契約型別檔與規格檔一致，且 sideEffect 的哨兵值說明仍在（BR4.4）。`
- `project-pages.spec.ts` 全檔：`29 passed (23.5s)`（既有 25 ＋ 新 4）
- 全部 e2e：`200 passed`、`20 failed`（5.5m）。失敗的 20 案全在 `entry-page-live.spec.ts`（5）、`estimate-workspace.spec.ts`（2）、`regression.spec.ts`（13）——三檔以真實帳號登入、需要 ephemeral 後端 stack（`estimate-workspace.spec.ts` 檔頭逐字「對 ephemeral stack（APP_ENV=test）的 seed admin 執行」；`estimate-workspace` 0 處 `page.route`），本輪依 brief 不起後端，與本次改動無關；其餘攔截式 spec（含 `object-picker`、`entry-page`、`a11y`、`member-pages`、`sidebar-landmarks`）全綠
- `python3 -B scripts/tcms_validate.py --spec frontend/tests/e2e/project-pages.spec.ts`：`通過 29/29　ERROR 0　WARN 3`（3 個 WARN 皆既有案例的「OpenAPI 未宣告 500」，非本輪新增）

## 突變驗證（副本內；改錯 → 重建 → 跑對應案例 → 還原 → sha256）

腳本 `$S/pb-mutate.py`。每項還原後的 sha256 與基線、與 repo 皆相同。

| 突變 | 內容 | 紅燈輸出（第一個錯誤） | 還原後 sha256（＝基線＝repo） |
|---|---|---|---|
| P1a | `SystemDiagrams` 的 `enabled` 去掉 `owned` | `disables the create action…` `1 failed`：`Error: expect(locator).toHaveAttribute(expected) failed` | `SystemDiagrams.tsx` `7ca8034c2738a40f2d8f738606b530c5f991fe8b5ff16554ca3e33b2eeedefb7` |
| P1c | 只拿掉點擊守門（`aria-disabled` 仍在） | `1 failed`：`Error: locator.click: Test timeout of 30000ms exceeded.`——非擁有者點下後真的送出並被導到 `/workspace`，下一個控件已不在頁上 | 同上 |
| P1b | `ProjectTargetNotice` 拿掉 `if (!owned) return;` | `1 failed`：`Error: expect(received).toHaveLength(expected)`（`set_work_target` 不再是 0 則） | `ProjectTargetNotice.tsx` `997e0ff338f622e0da8eae9d559af13af2dc325e09c278f44a02f0c6f28a3b61` |
| P2 | `start()` 不送 `setWorkTarget`，直接導頁 | `sets the work target…` `1 failed`：`Error: expect(received).toEqual(expected) // deep equality` | `workspaceHandoff.ts` `348f8f7adf7464e89d9c86011a404e635ebcc1fe394a0f1ef61cbc47339b0049` |
| P3 | 計數值改回固定「尚無法取得」 | `counts my diagrams…` `1 failed`：`Error: expect(locator).toHaveText(expected) failed` | `OverviewTab.tsx` `887b0bbf4987ff0b77236b11980397ccf19062e2da2540aceedf620276d1e4ae` |
| P4 | `{brainEnabled && (` 改為 `{(brainEnabled \|\| true) && (` | `mounts the context bar…` `1 failed`：`Error: expect(locator).toHaveCount(expected) failed` | `ProjectDetailPage.tsx` `6596161df129fc4d537d6f8365ed294d347336d5cd2931f2271f3d82e31d3bb4` |

還原後重建複驗：`Project page brain entry` → `4 passed (2.9s)`。
過程紀錄：P2、P3 的第一版突變寫法過不了 `tsc`（型別收窄、未使用函式），腳本當下中止且檔案停在突變狀態——已從 repo 複製還原並以 sha256 比對確認，之後腳本改為 `try/finally` 必還原，再以可編譯的寫法重跑；表內為重跑結果。
收尾逐檔比對 7 個改動檔副本與 repo 的 sha256 皆相同（`WorkspacePage.tsx` `f53583106fbdd3d10542e0308cec91b0df5494c712a7dd78db98acf13edc2c87`、`project-pages.spec.ts` `02c28c0e6c1c8b85bf72283bde70e2274413e0a7890a65a1cac4ea6f01adc809`）。

## 快取數（repo 內，開工 vs 收尾）

| 項目 | 開工 | 收尾 |
|---|---|---|
| `*.pyc`（排除 `backend/.venv`、`node_modules`、`.git`） | 243 | 243 |
| `.hypothesis` 檔數 | 352 | 352 |

收尾：`python3 -B scripts/validate_repo_contract.py` → `Cloud-360 repository contract validation passed.`；
`python3 -B scripts/validate_env_contract.py` → `Cloud-360 environment configuration contract validation passed.`

## 未完成項

1. **回補未做**：requirements 新 FR、user-stories 新 AC、traceability 補記（見上方回補項）；e2e 規格註解暫掛既有故事
2. **TCMS 未同步**：4 個新自動化案例；既有案例 `renders honest placeholders…` 的規格註解已更新，TCMS 上的描述需重新同步
3. **工作區為「獨立」模式時**：專案頁設定的是共享段的作業對象；若使用者把工作區切成獨立對話，工作區讀的是自己的段，存新圖不會依專案頁設定的系統掛載。本輪未處理（處理需動工作區的段選擇或 ws 契約），僅在此揭露
4. **工作區空白畫布未清 `last_opened`**：以 state 開空白畫布時未呼叫 `setLastOpened(null)`（不在未經使用者動作時寫伺服器狀態）；下次無 state 進工作區仍會還原上次的圖
5. **說明句兩份副本**（`ObjectPickerGroup.tsx` 與 `workspaceHandoff.NOT_OWNED_TARGET_NOTE`）待日後收斂
6. **非擁有者成員的計數通常為 0**（只數自己的圖，見設計決定）；若產品要的是「系統下全部的圖」，需上游定案可見範圍並改後端
7. **真實 stack 未驗**：未在本機或 staging 走過整條流程（含真實 `resolve_work_target` 拒絕非擁有者後的逾時路徑——逾時分支沒有自動化案例）；需 ephemeral stack 的 20 個 e2e 未跑
8. **CI 未實跑**（依 brief）
