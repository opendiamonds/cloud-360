# 部署後追加：全站大腦小助手與全站一條大腦連線

- 紀錄時間（`date -u`）：開工 `2026-11-15T07:02:19Z`，收尾 `2026-11-15T16:14:52Z`（UTC）
- 分支：`danniel/feat/global-brain-assistant`（從 `origin/ut` `a821d8c` 開出，已含 PR #721）
- 未 commit、未 push、未跑 `gh`、未觸發 CI、未連 staging 或任何共用 DB／Redis
- 只動前端；**後端、`openapi.json`、ws 契約零變更**（`git diff --stat -- backend openapi.json ws-contract.json frontend/src/types` 無輸出）
- 未做「大腦新建架構圖」（另開 intent）

## 範圍揭露（本階段新增、已核可 requirements／user-stories 尚未涵蓋）

2026-11-15 使用者以選單選定「全站統一用小助手」。以下全部是**部署後新增的範圍**，已核可的 `requirements.md`、
`stories.md` 都沒有涵蓋，不得讀成任何既有 FR／AC 的自然延伸：

1. 入口頁以外的每一頁右下角放浮動按鈕，點開是大腦對話窗，窗頂含作業對象與「切換對象」。
2. **取代 `[EP1]`=A 的面板形式**：`entry-page-ui` functional-design 的 EP1 選了「子頁面收合的『問大腦』面板」，
   本輪把工作區、評估頁、專案頁的那個面板（`SubpageBrainPanel`）移除、由小助手取代；三頁**只保留作業對象列**
   （脈絡列、同步提示、共享／獨立切換，專案頁另有作業對象提示）。EP1 的前提「不重寫工作區與評估頁既有的對話區」
   **仍成立**：兩頁既有的設計／評核對話區一行未動。
3. **連線由「每頁一條」改為「全站一條」**：取代 `EPN-01`（每頁一條、換頁即關舊開新）。

同一段揭露逐處寫在程式內：`BrainAssistant.tsx` 檔頭、`BrainConnectionProvider.tsx` 檔頭、`brainRoutePage.ts` 檔頭、
`brainAssistant.ts` 檔頭、`useBrainConnection.ts` 檔頭、`brainSession.ts` 檔頭、`App.tsx`／`Layout.tsx` 掛點註解、
`WorkspacePage.tsx`／`AssessmentPage.tsx`／`ProjectDetailPage.tsx`／`EntryPage.tsx` 的大腦區塊註解、
`brain-assistant.spec.ts` 檔頭。

### 回補項（指派回上游，由主 session 決定落點；本輪未改 `requirements.md`／`stories.md`）

1. **requirements 新 FR（建議草稿，待上游定案）**
   - 全站浮動小助手：具 `K1 view` 者在入口頁以外的每一頁可見；收合為右下角按鈕（可辨識名稱、收合期間有新回覆時
     顯示未讀）；展開為非強制回應對話窗（作業對象＋切換對象、對話、反問、工作項、輸入），可關閉、Esc 關閉，
     開啟焦點進輸入框、關閉焦點回按鈕，窄螢幕全螢幕；展開狀態跨頁保留；不遮住工作區畫布右下角縮放控件。
   - 小助手讀寫目前頁的讀取段（工作區／評估頁依共享／獨立，其餘頁為共享段，與入口頁同一段）。
   - **取代** `BR97.4` 的「子頁面收合『問大腦』面板」形式；`BR97.1` 的作業對象列保留。
2. **requirements／NFR**：全站至多一條大腦連線、換頁不重連（取代 `EPN-01` 的「每頁一條」）。`page` 由路由推導：
   `/workspace`→workspace、`/assessment`→assessment、其餘→entry。
3. **user-stories 新 AC**：對應上兩條各補 AC（含無 K1、入口頁不顯示、Esc／焦點、未讀、單一連線）。本輪 e2e 規格
   註解暫掛 `US2.1`、`US8.1`、`US3.1`，回補後改指新 AC。
4. **`[EP1]` 的處置紀錄**：EP1 為已核可答案，依 `team.md` Corrections 不回改上游，取代事實以本檔為準向下游傳遞；
   上游若要留痕，建議在 `entry-page-ui` 的 functional-design 以 Revision 段註記「面板形式已於部署後由小助手取代」。
5. **traceability**：`entry-page-ui` 單元的 `traceability.json` 未補記，回補時加 `scope: added-after-deployment` 列。
6. **TCMS**：新增 6 個自動化案例、改名 1 個、改寫 9 個既有案例的規格註解，均未同步（屬 `tcms-test-cases` stage）。

## 連線改為全站一條的判斷依據

**結論：`page` 是每則訊息各自帶，不是握手時決定 → 採「一條連線，依目前路由帶 `page`」，換頁不重連。**

| 證據 | 位置 |
|---|---|
| 握手只送 `hello{v}`，沒有 page | `frontend/src/brain/useBrainConnection.ts:192` `ws.send(clientFrame('hello', { v: PROTOCOL_VERSION }))`；契約 `frontend/src/types/ws-contract.d.ts:140` `HelloPayload` 只有 `v` |
| `page` 是 `user_message` 的欄位 | `ws-contract.d.ts:255` `page: "entry" \| "workspace" \| "assessment"`；送出處 `useBrainConnection.ts:431` |
| 閘道逐則依 `payload.page` 決定段 | `backend/services/brain_gateway.py:1368` `turn.segment = rules.resolve_segment(payload.page, page_modes)`；`brain_gateway_rules.py:156-162` |
| `set_sharing_mode` 逐則帶 `scope` | `useBrainConnection.ts:462`；閘道 `brain_gateway.py:1714` |
| 快照在 ready 後一次送出**全部 scope** 的 `sharing_mode` 與 session 內各段的 `work_target` | `brain_gateway.py:994` `for scope in PAGE_SCOPES`；`:607` `_snapshot_segment_ids` |

因此換頁不需要重新握手：原本 effect 依賴含 `page` 才會「換頁即重連」，那是實作選擇，不是協定要求。改法：

- 連線只由 `BrainConnectionProvider` 呼叫一次（`frontend/src/components/brain/BrainConnectionProvider.tsx:21`），
  掛在 `BrowserRouter` 內、`Routes` 外（`App.tsx:60`／`:265`），換頁不重掛。
- effect 依賴改為 `[enabled, token, attempt]`（`useBrainConnection.ts:416`），不含 `page`。
- 原本只記「本頁 scope」的共享模式改為記**全部 scope**（`useBrainConnection.ts:334`），各段作業對象改為 state
  （`:344`）；目前頁的 `sharingMode`／`readSegment`／`target` 在 render 時推導（`:125-127`）。
- 送出時 `user_message.page` 帶目前路由推導值（`:431`）；`set_work_target.segment` 帶目前讀取段（`:470`）。
- 路由 → page 的對應只寫一處：`frontend/src/brain/brainRoutePage.ts:14-16`（`SUBPAGES`）與 `:23` `pageForPath`。
- 未改 ws 契約或後端（不需要改，故沒有停下回報的情形）。

**換頁後的首次對齊**：原本每次進工作區／評估頁都會新開連線、收到快照，同步掛點靠 `work_target` 事件取得初始對象。
全站一條之後快照早已到過，不會再有事件。處置：`useTargetSyncCore` 掛載時若連線已 ready 且 `target` 有值，暫存為
「快照先到」那一支（`frontend/src/brain/useWorkspaceTargetSync.ts:154`），等頁面 `onPageReady` 對齊；不在此對齊、
不 setState。`target` 是 render 時依本頁 page 推導的值，不受「子元件 effect 先於父元件」影響。`object-picker`、
`entry-page` 的快照先到／後到與換頁同步案例全綠（見測試）。

## 設計決定與理由

| 決定 | 理由 |
|---|---|
| 連線與小助手狀態放在路由外層的 `BrainConnectionProvider`；小助手元件掛在 `Layout`（`Layout.tsx:34`） | brief 要求掛在全站 Layout。`Layout` 每條路由各一份、換頁重掛，狀態若放在元件內會隨換頁消失，所以狀態（展開、草稿、已讀點）上提到路由外層 |
| 不用 localStorage，狀態只在記憶體 | 換頁保留已由路由外層達成；對話紀錄本身只在記憶體（`EPN-13`），展開狀態落盤沒有意義，且免去讀寫失敗的分支。重新整理回到收合 |
| `BrainSession`（context＋唯一 `LiveRegion`）只在 provider 掛一次（`BrainConnectionProvider.tsx:61`）；各頁移除自己的 `BrainSession` 包裝，改用 `useBrainSession()` | 頁面與小助手同時存在時，若各包一層會出現兩個 `brain-live` 播報區、同一句播報兩次 |
| 各頁大腦掛點以 `brain.enabled` 把關（`WorkspacePage.tsx:113`、`AssessmentPage.tsx:247`、`ProjectDetailPage.tsx:117`），`enabled` 只在 provider 由 `can('K1','view')` 算一次 | 單一真實來源；與原本各頁 `brainEnabled = can('K1','view')` 等價 |
| 入口頁不顯示小助手（`BrainAssistant.tsx:43`，`isEntryPagePath`） | 入口頁本身是整頁對話；入口頁與小助手讀同一段，紀錄只有一份（e2e 斷言入口頁對話區該句恰 1 則） |
| 未讀：連線計「入口頁以外終止的輪次」（done／帶輪次 error／反問，`useBrainConnection.ts:170-171`），provider 記已讀點，展開或收合時對齊（`BrainConnectionProvider.tsx:47`、`:56`） | 判定依**畫面**（是否在入口頁）而非 page：專案、記憶、成本頁的 page 也是 entry，以 page 判會讓那三頁永遠沒有未讀（第一版即如此，e2e 抓到後改正）。setState 都在事件回呼內，不在 effect body |
| 換人登入／登出：收合、清草稿、已讀點對齊（`BrainConnectionProvider.tsx:39`） | 與對話紀錄同一個身分邊界事件；回覆數是連線層累計值，不歸零，故對齊而非歸零 |
| 窗頂重用 `ContextBar`（`BrainAssistant.tsx:111`），新增可選 `testIdPrefix`／`regionLabel`（`ContextBar.tsx:36-38`，預設值即原值） | brief：重用既有元件、不另寫一套；子頁面同時有頁內作業對象列與小助手，測試 id 與區域名稱需可區分（axe `landmark-unique`）。小助手內不放共享／獨立切換（`sharingToggle={false}`），切換留在頁內作業對象列 |
| 對話區、反問、工作項沿用 `ConversationView`（`:113`），輸入沿用 `BrainInput`（`:117`） | 同上 |
| 對話窗 `role="dialog"`、`aria-modal="false"`（`:79`），Esc 在窗上關閉（`:86`）；窗內作業對象選單自行處理 Esc 並 `stopPropagation`，所以 Esc 先關選單、再按才關小助手 | 非強制回應：使用者仍可操作頁面；e2e 驗證「選單開著時 Esc 只關選單」 |
| 焦點只在使用者按下開啟／關閉後的 commit 移動（`focusRequestRef`，`:48`、`:63`、`:68`）；輸入框停用（未就緒）時落在對話窗本身 | 換頁後小助手重掛而仍展開時不搶頁面焦點；窄螢幕展開時按鈕隱藏，關閉的同一個事件內無法聚焦，必須等 commit |
| 窄螢幕（< 768px）`fixed inset-0` 全螢幕，展開時按鈕隱藏 | brief |
| **工作區按鈕上移至 `bottom-24`、對話窗跟著上移**（`:44` `aboveCanvasControls`） | 實測：以 Playwright 載入真實 `embed.diagrams.net/?embed=1&ui=min…`，draw.io 底部有 32px 狀態列、右端是縮放比例選單（「100%」）；在工作區量得 1280×720 時畫布 iframe `{x:709,y:145,w:538,h:542}`、按鈕（`bottom-4`）`{x:1208,y:648,w:56,h:56}`，1440×900 時 iframe `{x:709,y:145,w:698,h:722}`、按鈕 `{x:1368,y:828}`——按鈕正好蓋在縮放選單上。改為 `bottom-24` 後由 e2e 以幾何斷言「按鈕不與畫布底部 32px 的右端 96px 重疊」 |
| 刪除 `SubpageBrainPanel.tsx` 與其專屬測試 id `brain-subpage-panel`／`brain-subpage-panel-toggle` | 三處掛載移除後已無人使用；`grep -rn` 確認 `src` 內只剩 `BrainAssistant.tsx:15` 註解說明它已刪除、無任何程式引用；測試內只剩新 e2e 的「不存在」斷言 |

## 改動檔與行（`grep -n` 實查）

- 新檔 `frontend/src/brain/brainRoutePage.ts`：`:14-16` 對應表、`:23` `pageForPath`、`:28` `ENTRY_PAGE_PATH`、`:30` `isEntryPagePath`
- 新檔 `frontend/src/brain/brainAssistant.ts`：`:19` `unread`、`:24` `useBrainAssistant`
- 新檔 `frontend/src/components/brain/BrainConnectionProvider.tsx`：`:21` 唯一一次 `useBrainConnection`、`:39` 身分邊界、`:47` `setOpen`、`:56` 未讀推導、`:61` 唯一 `BrainSession`
- 新檔 `frontend/src/components/brain/BrainAssistant.tsx`：`:43` 顯示條件、`:44` 工作區上移、`:48`／`:63`／`:68` 焦點請求、`:79` dialog、`:86` Esc、`:111` 窗頂作業對象列、`:113` 對話區、`:117` 輸入、`:124` 按鈕、`:130` 按鈕上的 Esc
- 刪除 `frontend/src/components/brain/SubpageBrainPanel.tsx`
- `frontend/src/brain/useBrainConnection.ts`：檔頭改述、`:64` `assistantSurface`、`:107` 簽章、`:125-127` 推導、`:144` ref 同步、`:170-171` 未讀計數、`:334` 全 scope 模式、`:344` 段對象 state、`:416` effect 依賴、`:431` user_message、`:470` set_work_target
- `frontend/src/brain/brainSession.ts`：`:42` `enabled` 說明、`:52` `assistantReplyCount`、檔頭與 `subscribe` 說明改述
- `frontend/src/brain/useWorkspaceTargetSync.ts`：`:154` 掛載時取現值作為待對齊對象
- `frontend/src/components/brain/ContextBar.tsx`：`:36-38` 可選 props、`:109` `aria-label={regionLabel}`、七個測試 id 改為前綴模板（預設值不變）
- `frontend/src/App.tsx`：`:4` 匯入、`:60`／`:265` provider
- `frontend/src/components/Layout.tsx`：`:5` 匯入、`:34` `<BrainAssistant />`
- `frontend/src/pages/EntryPage.tsx`：移除自有連線與 `BrainSession` 包裝，`:42` 作業對象列
- `frontend/src/pages/WorkspacePage.tsx`：`:14` 匯入、`:112-113` 改用全站連線、`:968-969` 只留作業對象列與同步提示
- `frontend/src/pages/AssessmentPage.tsx`：`:11` 匯入、`:246-247`、`:1241-1242`
- `frontend/src/pages/ProjectDetailPage.tsx`：`:20` 匯入、`:116-117`、`:317-318`
- 新檔 `frontend/tests/e2e/brain-assistant.spec.ts`（6 案）；改 `entry-page.spec.ts`、`project-pages.spec.ts`、`entry-page-live.spec.ts`
- 無 DDL、無 seed、未動 `database.py`／`nginx.conf`／`.env.example`／`render-env.sh` → **不觸發** `schema_rbac.sql`／`DEPLOY.md`／`LOCAL-DEV.md` 同步

## 測試名稱：改名清單與改寫清單

**改名（1 個，非改不可）**：

| 檔案 | 舊名（TCMS 案例名） | 新名 | 理由 |
|---|---|---|---|
| `entry-page-live.spec.ts` | `U14 entry page live stack › 三頁各自一條連線且前一頁的已關閉` | `U14 entry page live stack › 三頁切換全程只有一條大腦連線` | 舊名斷言的正是本輪刻意取代的行為（每頁一條、前一頁關閉）；保留舊名會讓 TCMS 上的案例名稱與實際斷言相反。舊名已寫進新案例的 `@purpose`，同步時需在 TCMS 把舊案例標為廢止 |

**名稱不變、只改內容與規格註解（9 個）**：

| 案例（`<describe> › <test>`） | 改了什麼 |
|---|---|
| `U14 entry page › 三頁切換後未關閉的大腦連線恰一條` | 由「每次換頁新開 1 條」改為「連線總數始終 1、hello 1 則」（名稱仍為真） |
| `U14 entry page › 工作區 4403 且 K1 撤銷時不導航並卸載掛點` | 面板改為小助手按鈕 |
| `U14 entry page › 子頁面切換獨立對話以伺服器回推為準` | 面板改為小助手對話窗 |
| `U14 entry page › 子頁面送出帶本頁 page 與所讀段` | 從小助手送出 |
| `U14 entry page › 成本頁與使用者管理頁不掛脈絡列` | 連線數由 0 改為「每次整頁載入 1 條、同時存活 1 條」（成本頁現在有小助手） |
| `U14 entry page › 無 K1 時子頁面不掛大腦且不送作業對象` | 加斷言小助手按鈕不存在 |
| `U14 entry page › 串流中換頁後同一輪合併為一則` | 換頁不再中斷該輪：改斷言仍是 streaming、沒有「你在回覆完成前離開了這一頁」、無新連線，後續 token 合併 |
| `U14 entry page › 登出再換人登入時對話區清空` | 面板改為小助手（展開狀態跨頁保留，第二頁不再點按鈕） |
| `Project page brain entry › mounts the context bar and brain panel only with K1 view` | 面板改為小助手；開啟後先關閉再操作頁上提示（浮動窗蓋在頁面右側） |

## ADR-0006 四面向判定

| 面向 | 判定 | 影響與處置 |
|---|---|---|
| IAM | **適用（不新增授權路徑）** | 小助手只送既有訊息（`user_message`、`set_work_target`、`select_clarify_candidate`、`correct_work_item`），伺服器仍以 K1 握手與擁有者範圍判定。前端顯示以 `K1 view` 把關（G2 突變證明「無 K1 也顯示」會紅）；`enabled` 只在 provider 計算一次，無 K1 不開連線（e2e 斷言無 K1 時連線 0 條）。無新端點、無矩陣變更 |
| encryption | **不適用（附理由）** | 無新儲存欄位、無新傳輸通道；展開狀態與草稿只在記憶體，不寫 localStorage／sessionStorage |
| network exposure | **適用（連線數下降，無新暴露面）** | 無新 HTTP path、無新 ws 訊息型別、無新埠。全站一條取代每頁一條：同一分頁任何時刻至多一條 `/api/brain/ws`；但記憶、成本、管理等原本不開大腦連線的頁面，現在對具 K1 者也保持那一條連線（成本頁案例已改寫並揭露）。連線仍只在具 K1 時建立 |
| audit logging | **不適用（附理由）** | 無新寫入；作業對象變更沿用既有閘道路徑。未新增日誌 |

PBT hard constraint：路由 → page 對應是三分支的查表，未動 agent routing（伺服器端意圖路由）、IaC generator、cost calculator，無 PBT 義務。

## 測試實跑（全部在 `$S/ga-copy` 副本）

環境：`rsync`（brief 指定的排除項）建立副本、前端 `node_modules` 以 `cp -Rc` 複製；`npm run build` 後以
`npx vite preview --host 127.0.0.1 --port 8090 --strictPort` 起前端，`BASE_URL=http://localhost:8090` 執行，全部
`page.route`／`routeWebSocket` 攔截；跑完已停掉 preview（`curl` 回 `000`）。後端未改，未跑 `unittest`。

- `npm run lint`：`✖ 2 problems (0 errors, 2 warnings)`（`AssessmentPage.tsx:394`、`WorkspacePage.tsx:356` 皆 `exhaustive-deps`，既存）
- `npm run build`：`✓ built in 549ms`（既存的 chunk 大小提示）；`npx tsc -b` 無輸出
- `npm run check:types`：`API 型別檔與規格檔一致。`；`npm run check:ws-types`：`WS 契約型別檔與規格檔一致，且 sideEffect 的哨兵值說明仍在（BR4.4）。`
- 程式改完、既有測試尚未改寫時（`entry-page`、`object-picker`、`project-pages` 三檔）：`8 failed`、`118 passed (4.7m)`——8 個失敗正是上表改寫的 8 個參照面板／每頁一條的案例（`project-pages` 那 1 個另有「浮動窗遮住提示」的第二輪修正）；`object-picker` 全綠
- 收尾，可在攔截層下跑的 8 支 spec（`a11y`、`brain-assistant`、`entry-page`、`member-pages`、`memory-page`、`object-picker`、`project-pages`、`sidebar-landmarks`）：`205 passed (2.4m)`
- 全部 11 支 spec（收尾前最後一次全量）：`206 passed`、`20 failed (5.6m)`。20 案全在 `entry-page-live.spec.ts`（5）、`estimate-workspace.spec.ts`（2）、`regression.spec.ts`（13）——需真實 stack，依 brief 交給 CI，與上一輪相同的一組
- 新增 `brain-assistant.spec.ts`：`6 passed`
- `python3 -B scripts/tcms_validate.py --spec`：`brain-assistant.spec.ts` `通過 6/6　ERROR 0　WARN 0`；`entry-page.spec.ts` `通過 63/63　ERROR 0　WARN 0`；`project-pages.spec.ts` `通過 29/29　ERROR 0　WARN 3`（3 個 WARN 皆既有案例的「OpenAPI 未宣告 500」）；`entry-page-live.spec.ts` `通過 5/5　ERROR 0　WARN 0`

**關於 `page.on('websocket')`**：brief 要求以它計數。實測連線被 `page.routeWebSocket` 攔下、不連真實伺服器時，該事件**不觸發**
（第一版斷言 `Expected: 1 / Received: 0`）。攔截層 spec 改以 init script 包住 `window.WebSocket`（以 accessor 接住
routeWebSocket 之後的替換）計數頁面建立的大腦連線，並同時斷言攔截層收到 1 條、`hello` 1 則；G3 突變證明此計數能看到第 2 條。
需要真實 stack 的 `entry-page-live.spec.ts` 仍以 `page.on('websocket')` 計數（真實連線時事件會觸發），交給 CI。

## 突變驗證（副本內；改錯 → 重建 → 跑對應案例 `--retries=0` → 還原 → sha256）

腳本 `$S/ga-mutate.py`（`try/finally` 必還原）。每項還原後 sha256 與基線、與 repo 皆相同（`baseline_match=True repo_match=True`），最後重建 `exit 0`。

| 突變 | 內容 | 紅燈輸出 | 還原後 sha256 |
|---|---|---|---|
| G1 | 入口頁也顯示：`!isEntryPagePath(pathname)` → `(!isEntryPagePath(pathname) \|\| true)` | `1 failed`：`Error: expect(locator).toHaveCount(expected) failed`，`> 177 \| await expect(toggle(page)).toHaveCount(0);` | `BrainAssistant.tsx` `ef80fd0c8a1d2d11f63eac415dfcfc4dafb56d684c2d12e5f9981c22a09bfb53` |
| G2 | 沒有 K1 也顯示：`conn.enabled` → `(conn.enabled \|\| true)` | `1 failed`：`Error: expect(locator).toHaveCount(expected) failed`，`> 192 \| await expect(toggle(other)).toHaveCount(0);` | 同上 |
| G3 | 專案頁仍自己開一條：`useBrainConnection('entry', { enabled: can('K1','view'), assistantSurface: true })` | `1 failed`：`Error: expect(received).toBe(expected) // Object.is equality`，`> 261 \| expect(await h.brainSockets()).toBe(1);` | `ProjectDetailPage.tsx` `6bc54a26c41cb9a2a42b38cf7c1578dc33b078323c65152f7ba6d356fa24e317` |
| G4 | Esc 不關閉：對話窗 `e.key === 'Escape'` → `'Esc-mutated'` | `1 failed`：`Error: expect(locator).toHaveCount(expected) failed`，`> 322 \| await expect(assistantWindow(page)).toHaveCount(0);` | `BrainAssistant.tsx` `ef80fd0c…09bfb53`（同上） |
| G5 | 路由對應錯：`/projects` → `workspace` | `1 failed`：`Error: expect(received).toEqual(expected) // deep equality`，`> 215 \| …toEqual({ text: …, page: 'entry' });` | `brainRoutePage.ts` `e57abf37455495c67718bc8666474acd14ded17d02bef6bf51c15e8939b25d53` |

收尾逐檔比對副本與 repo：`useBrainConnection.ts` `6bf308325e52a553aa5c56be94eed482cf5e66b400d498abf3f34aa408eb65cf`、`brain-assistant.spec.ts` `c2d90cce3ca53d37ed16d3bdf1c318f9a755d739559db5329a24d28770188760` 等 5 檔皆相同。

## 快取數（repo 內，開工 vs 收尾）

| 項目 | 開工 | 收尾 |
|---|---|---|
| `*.pyc`（排除 `.venv`、`node_modules`、`.git`） | 243 | 243 |
| `.hypothesis` 檔數 | 352 | 352 |

收尾：`python3 -B scripts/validate_repo_contract.py` → `Cloud-360 repository contract validation passed.`；
`python3 -B scripts/validate_env_contract.py` → `Cloud-360 environment configuration contract validation passed.`

## 未完成項

1. **回補未做**：requirements 新 FR／NFR、user-stories 新 AC、`[EP1]` 的 Revision 註記、traceability（見上方回補項）；e2e 規格註解暫掛既有故事
2. **TCMS 未同步**：6 個新案例；改名 1 個（舊案例需標廢止）；9 個既有案例的規格註解已改，TCMS 描述需重新同步
3. **`entry-page-live.spec.ts` 改名後的案例未實跑**（需真實 stack，交 CI）；其餘需真實 stack 的 19 案同樣未跑
4. **窄螢幕全螢幕沒有自動化案例**：只以 class（`fixed inset-0 … md:…`）實作，未以 e2e 斷言
5. **工作區按鈕上移後的殘餘重疊**：`bottom-24` 避開了 draw.io 狀態列的縮放選單，但在畫布右側時可能落在 draw.io「Format」面板的下緣空白區；選取圖形後該面板內容變長時是否被遮，未驗證
6. **浮動對話窗是非強制回應、展開時蓋住頁面右側**（桌面寬 26rem）：使用者要先關閉才能操作被蓋住的控件（專案頁的作業對象提示即是，見改寫案例）。未做「不遮住」的版面讓位
7. **記憶、成本、管理頁現在也持有大腦連線**（具 K1 者）：符合「全站一條」，但伺服器端的連線數模型由「只在三頁」變為「登入期間常駐」，未在真實 stack 觀察負載
8. **重新整理後展開狀態不保留**（只在記憶體）；brief 只要求換頁保留
9. **CI 未實跑**（依 brief）
