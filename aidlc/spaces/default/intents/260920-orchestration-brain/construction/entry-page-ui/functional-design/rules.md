# Rules — `U14 entry-page-ui`

> 建檔時間 2026-10-17T00:00:48Z（以 `date -u` 取值）。

## 一、本檔存在的理由與範圍界線

`produces_kinds` 把 `rules` 限定在 `[service, spec, library]`，`ui` 不在其中；但同 stage 的
`traceability` sensor 要求 `OK` 列指名本檔的規則，故沿用 `U23`／`U24` 的處置：產出本檔，
內容限定於**本單元自己**的規則。

**識別字區段 `BR91`–`BR98`**（派工指定）。

**本檔不寫出任何他單元規則的識別字字面形式**：sensor 以 `\bBR\d+\.\d+\b` 掃整份檔，
寫出來會被當成本檔的孤兒規則。他單元規則一律寫成「`U2` 的規則 3.5」的形式。

**作答依據**：`functional-design-questions.md` 的 EP1–EP6 全部為 A（2026-10-16T23:57:32Z）。
`[EP2]`=A 使本單元的 code-generation **含後端變更**（`U2` 契約模組、`U13` 推送），故 `BR97.2`
的驗證層含 `TestClient`；其餘規則皆為外部可觀察的畫面行為，驗證層為 Playwright（真實 stack
或 `routeWebSocket`，見 `BR98.4`）。

**修訂 1**（2026-10-17，依第一輪審查與兩項使用者裁決）：新增 `BR93.7`（R-05）；改寫 `BR93.4`（R-06）、
`BR94.7`（R-07，偏離揭露）、`BR97.2`（R-04 ＋ 裁決：`U7` 新增唯讀方法）、`BR97.5`（R-02）、`BR97.6`（R-03）、
`BR98.2`（裁決：移至另一 intent）、`BR98.4`（R-01）。規則由 48 條增為 49 條。

## 二、規則（machine-readable source of truth）

```yaml source-of-truth
rules:
  # ── BR91：落地與入口 ──────────────────────────────────────────
  - id: BR91.1
    statement: 已核准且具 K1 view 的使用者造訪 / 時，/ 直接渲染入口頁；K1 判斷位在 isPending 判斷之後、其他權限判斷之前
    category: authorization
    applies_to: App.tsx 的 DefaultRedirect、路由 /
    trigger: 造訪 /
    logic: >
      IF isLoading THEN 不渲染；ELSE IF isPending THEN 導 /waiting-approval；
      ELSE IF can('K1','view') THEN 渲染 EntryPage（不再導向別處）；
      ELSE 沿用既有瀑布（A1 → A3 → C1 → J3a → J3b → /403）。
    violation_behaviour: K1 置於 isPending 之前 → 未核准帳號落進入口頁，繞過等待授權頁（AC1.4.3 要防的形狀）
    source: "AC1.4.1、AC1.4.3（stories.md:93 的對齊修正）、K-13（contract-summary.md:1032、:1035）"

  - id: BR91.2
    statement: 不具 K1 view 者的落地與 Sidebar 行為與本單元上線前完全相同
    category: authorization
    applies_to: DefaultRedirect、Sidebar
    trigger: 造訪 / 或渲染 Sidebar
    logic: >
      IF NOT can('K1','view') THEN 不渲染 Sidebar 的「入口」項，且 / 依既有瀑布導向；
      權限矩陣被調整為不具任何落地權限時仍導 /403。
    violation_behaviour: 無 K1 者看到入口卻每次被 4403 關閉；或既有的全無權限處置被繞過
    source: "AC1.4.2、AC1.4.4"

  - id: BR91.3
    statement: 萬用路由 * 導向 /，不直接渲染入口頁
    category: constraint
    applies_to: App.tsx 的 * 路由
    trigger: 造訪不存在的路徑
    logic: "IF 路徑不符任何路由 THEN Navigate 到 /（replace），再由 BR91.1／BR91.2 決定落點"
    violation_behaviour: 任何打錯的網址都變成入口頁，網址列與畫面不一致
    source: "functional-design-questions.md 第一節"

  - id: BR91.4
    statement: Sidebar 的「入口」為第一層獨立項、置於最上方，以 K1 view 顯示
    category: constraint
    applies_to: Sidebar.tsx
    trigger: 渲染 Sidebar
    logic: >
      IF can('K1','view') THEN 在所有群組與獨立項之前渲染「入口」NavLink（to="/"，end 比對），
      目前頁帶 aria-current="page"。不歸入任何群組。
    violation_behaviour: 入口被埋進群組或排在其他項之後，與已核可的 M0／線框 §14 不符
    source: "[R1]、mockups.md M0、Sidebar.tsx:214-215 的 U23 註解"

  - id: BR91.5
    statement: 入口頁頁首的「我的記憶」捷徑以 canSeeMemoryEntry 判定顯示，與 Sidebar 同一判定
    category: constraint
    applies_to: EntryPage 頁首
    trigger: 渲染入口頁
    logic: "IF canSeeMemoryEntry({ isAuthenticated }) THEN 渲染捷徑連到 /memory；不得另寫判定"
    violation_behaviour: 兩個入口各自判斷，下一個加權限的人只改一處（INV-3 要防的形狀）
    source: "INV-3、memory-page-ui/code-generation/code-summary.md:89"

  # ── BR92：連線與協定（消費端義務）──────────────────────────────
  - id: BR92.1
    statement: 入口頁、/workspace、/assessment 各自持有一條大腦連線；子協定兩項皆由型別取值，網址不含查詢參數
    category: constraint
    applies_to: useBrainConnection（每頁一個）
    trigger: 三頁之一掛載
    logic: >
      以 wsUrl() 組出掛在 /api/ 之下的端點（不帶任何查詢參數）；
      new WebSocket(url, [protocolName, scheme + separator + token])，三個值皆以
      WsSubprotocol 的欄位型別取值（不寫字面量，受 ADR-0019 §5 的 lint 規則約束）。
      頁面卸載即關閉該頁的連線。
    violation_behaviour: 字面量寫死 → 後端改值時沒有閘門紅燈、握手靜默失敗；token 進網址 → AC8.1.3 失敗
    source: "contract-summary.md:911-916、U13 交接第 1 項（brain-gateway/code-generation/code-summary.md:228-244）、AC8.1.3"

  - id: BR92.2
    statement: 連線開啟後先送 hello，收到 ready 且 protocolVersion 等於本版才進入可用狀態；之前輸入列停用
    category: validation
    applies_to: useBrainConnection
    trigger: 連線 open、收到 ready
    logic: >
      open → 送 hello{v:1}；收到 ready → IF payload.protocolVersion != 1 THEN 視為協商失敗、
      關閉連線並顯示「版本不相容，請重新整理頁面」，不重試；ELSE 進入 ready。
      ready 之前輸入列、候選、「不是這個」皆停用。
    violation_behaviour: 不核對 → ready.protocolVersion 成為無讀取端的欄位（U2 的規則 3.5）
    source: "U2 的規則 3.5（brain-ws-contract/functional-design/rules.md:380）"

  - id: BR92.3
    statement: 客戶端送出的每則訊息都帶它所屬的頁面或段
    category: validation
    applies_to: sendUserMessage、setWorkTarget、setSharingMode
    trigger: 送出 user_message／set_work_target／set_sharing_mode
    logic: >
      user_message.page ＝ 送出頁（entry／workspace／assessment），不得預設；
      set_work_target.segment ＝ 該頁目前讀取的段（入口頁恆為 shared；子頁面依其共享模式為 shared 或頁名）；
      set_sharing_mode.scope ＝ 該子頁面頁名。入口頁不送 set_sharing_mode。
    violation_behaviour: 缺欄位 → 伺服器回 error(INVALID_REQUEST)；預設 entry → 獨立對話的訊息靜默寫進共享段
    source: "U13 交接第 2、4 項；ws-contract.d.ts:255、:184"

  - id: BR92.4
    statement: 狀態訊息依 scope／segment 過濾，只套用到讀取該段的頁面
    category: validation
    applies_to: 連線的訊息分派
    trigger: 收到 sharing_mode 或 work_target
    logic: >
      sharing_mode：只在 scope 等於本頁頁名時套用（入口頁忽略全部 sharing_mode）。
      work_target：只在 segment 等於本頁目前讀取的段時套用到脈絡列；其餘段的 work_target
      保存在該段的暫存，供切換模式時立即顯示。
    violation_behaviour: 獨立對話的脈絡列顯示共享段的值
    source: "U13 交接第 3 項"

  - id: BR92.5
    statement: 關閉碼決定後續：4401 請重新登入、4403 回到落地判斷、4400 不重試、其他與未 accept 以有上限的退避重連至少 60 秒
    category: policy
    applies_to: useBrainConnection
    trigger: 連線關閉或握手被拒
    logic: >
      4401 → 顯示「連線已失效，請重新登入」＋ 按鈕（登出後導 /login），不自動重連、不自動跳轉；
      4403 → Navigate 到 /（K1 已被撤銷，由 BR91.2 重新決定落點）；
      4400 → 同 BR92.2 的版本不相容處置；
      其他（含 1011、網路中斷、握手未被接受）→ 指數退避重連（1、2、4、8、15、15… 秒，單次上限 15 秒），
      自第一次失敗起累計至少 60 秒才停止，停止後顯示「無法連線到大腦」＋「重新連線」按鈕。
      重連成功即重新 hello，伺服器推送的狀態訊息覆蓋畫面上的作業對象與工作項。
    violation_behaviour: 不退避 → 額滿時重試風暴；少於 60 秒即放棄 → 舊登錄約 40 秒後才釋放，被擋的分頁永遠連不上；4401 自動重連 → 無限迴圈
    source: "U13 交接第 7、8 項、[GWND1]=A、AC2.1.4"

  - id: BR92.6
    statement: 未知 type 安全忽略；error.code 以窮盡 switch 處理；error.message 原樣顯示
    category: validation
    applies_to: 連線的訊息分派、ErrorNotice
    trigger: 收到任一訊息
    logic: >
      先以 WsUnvalidatedEnvelope 解析；type 不在 WsServerMessageType 九值內 → 忽略並 console.warn（不含內容）。
      error.code 的 switch 必須窮盡四值（以 never 檢查讓新增 code 時 tsc -b 紅燈）；message 原樣顯示。
    violation_behaviour: 新 type 讓畫面崩潰；新 code 被默默當成 INTERNAL_ERROR
    source: "U2 的規則 3.1、3.2（brain-ws-contract/functional-design/rules.md:332、:341）、U13 交接第 9 項"

  - id: BR92.7
    statement: 不自動重送未收到終止事件的 user_message
    category: policy
    applies_to: sendUserMessage、Turn 狀態機
    trigger: 連線中斷且有尚未終止的使用者輪次
    logic: >
      該輪轉為 interrupted：保留已顯示內容 ＋「回覆中斷」＋ 重試鈕；重試只在使用者按下時以同一原文重送一次。
    violation_behaviour: 自動重送 → 非冪等的 user_message 觸發兩次交辦
    source: "U2 的規則 3.4（brain-ws-contract/functional-design/rules.md:369）"

  - id: BR92.8
    statement: 本單元的程式不讀、不寫、不記錄 token 的任何部分，console 不輸出訊息內容
    category: constraint
    applies_to: 本單元全部前端程式
    trigger: 任何日誌或錯誤處理
    logic: "token 只出現在 new WebSocket 的子協定陣列；console 只記 type、code 與關閉碼，不記 payload"
    violation_behaviour: token 或使用者原句出現在瀏覽器主控台或錯誤回報
    source: "AC8.1.3、ADR-0006 audit logging 面"

  # ── BR93：對話紀錄與串流 ──────────────────────────────────────
  - id: BR93.1
    statement: 每個 turnId 對應一則大腦訊息；token 訊框收到即附加，不緩衝到 done
    category: constraint
    applies_to: Transcript、StreamingMessage
    trigger: 收到 token
    logic: >
      以 turnId 為鍵；首見的 turnId 新建一則 streaming 訊息；每個 token 立即附加並重繪；
      done → 該則轉 done；error → 該則轉 error 並顯示 message。prompt_guard 的固定拒絕訊息是一般的 token 輪次，不特殊處理。
    violation_behaviour: 緩衝到 done 才顯示 → 改寫後的 AC8.1.1 在畫面層失效
    source: "deferred-ac-rulings.md:7（AC8.1.1 改寫）、AC1.1.3、AC10.2.3"

  - id: BR93.2
    statement: 收到零內容的 done 視為契約違規，顯示「沒有收到回覆」＋ 重試，不留空白訊息
    category: validation
    applies_to: StreamingMessage
    trigger: 收到 done 而本輪未收到任何非空白 token 與 cost_card
    logic: "該則轉 empty-stream；console.warn 記一筆（只含 turnId）"
    violation_behaviour: 留下一則空白訊息，使用者分不出是壞了還是沒回答
    source: "U2 的規則 3.3（brain-ws-contract/functional-design/rules.md:355）、interaction-spec.md StreamingMessage"

  - id: BR93.3
    statement: 使用者輪次的「等待回覆」狀態在任一輪終止或連線關閉時解除
    category: constraint
    applies_to: Transcript
    trigger: 送出 user_message 後
    logic: >
      送出後標記 awaitingReply=true 並停用送出鈕；任一輪的 done／error 或連線關閉時解除。
      契約不提供「這則 user_message 對應哪個 turnId」的關聯（客戶端不得帶 turnId），
      故本規則以「任一輪終止」近似，見 OPEN-EP14-4。
    violation_behaviour: 送出鈕永久停用；或在回覆中可連送多則
    source: "ws-contract.d.ts 的 WsClientEnvelope（無 turnId）、OPEN-EP14-4"

  - id: BR93.4
    statement: 畫面上的對話紀錄由應用程式層的單一記憶體 store 依段保存；換頁不丟，重新整理、開新分頁或登出即清空
    category: policy
    applies_to: BrainTranscriptProvider（App 層，包在路由之外）
    trigger: 任何訊息附加；登出；頁面重新載入
    logic: >
      三段：shared、workspace、assessment，各自一份訊息陣列（使用者原句、大腦訊息、反問、成本卡片、
      工作項清單的錨點）；另有一份跨段的 turnId → (段, 訊息索引) 對照，供 BR93.7 合併。各頁顯示其目前讀取段的那一份。
      不寫入 localStorage、sessionStorage 或 IndexedDB。
      **登出清空的實作形狀**（審查 R-06）：Provider 以目前使用者 id 為 React key 掛載（未登入為固定字串），
      使用者改變即重新掛載、state 自然重設——**不得**以 useEffect 監聽 user 再呼叫清空（react-hooks/set-state-in-effect 為 error 級）。
      重新載入後若該段為空且（作業對象非空或工作項非空），對話區顯示一行「先前的對話大腦仍記得，只是這裡不再顯示」。
    violation_behaviour: 存進瀏覽器儲存 → 使用者原句以明文落地（ADR-0006 加密面新增落點）；不跨頁保存 → AC3.1.4 失效
    source: "[EP4]=A、AC2.1.4、AC3.1.2、AC3.1.4"

  - id: BR93.5
    statement: 伺服器發起的輪次附加到接收頁目前讀取的段
    category: policy
    applies_to: Transcript
    trigger: 收到一個非本頁送出所觸發的新 turnId（例如背景工作完成的推播）
    logic: >
      envelope 不帶段資訊；本規則以接收頁目前讀取的段為落點。使用者停在入口頁時即為共享段（AC10.1.4 的情境）。
    violation_behaviour: 推播無處可放而被丟棄；或硬塞進共享段而在子頁面的獨立對話中看不到
    source: "brain-gateway/functional-design/functional-spec.md:58（emit_turn 送該 key 全部存活連線）、OPEN-EP14-3"

  - id: BR93.6
    statement: 串流中不逐字播報；完成時播報一次；游標閃爍遵守 prefers-reduced-motion
    category: constraint
    applies_to: StreamingMessage
    trigger: streaming 與 done
    logic: "streaming 時該則 aria-busy=true；done 時把整段寫入既有 LiveRegion 一次；reduced-motion 時游標不閃爍"
    violation_behaviour: 螢幕閱讀器持續打斷自己
    source: "interaction-spec.md StreamingMessage 無障礙列、LiveRegion.tsx"

  - id: BR93.7
    statement: 頁面卸載時，該頁連線上未終止的輪次轉為 interrupted；任何頁收到 store 中已存在的 turnId，一律合併進原訊息
    category: constraint
    applies_to: useBrainConnection 的 cleanup、Transcript
    trigger: 頁面卸載（含在串流中點 Sidebar 換頁）；收到 token／cost_card／done／error 且 turnId 已在 store
    logic: >
      卸載 cleanup 時，對本連線送出後尚未收到 done／error 的使用者輪次與 streaming 中的訊息，轉 interrupted，
      說明為「你在回覆完成前離開了這一頁」＋ 重試鈕（不自動重送，與 BR92.7 一致）。
      收到 turnId 已在 store 的訊息（例如伺服器發起的輪次送到所有存活連線，新頁的連線接到同一輪的後續）：
      依 turnId 找到原訊息所在段與位置，附加內容；原為 interrupted 者回到 streaming。**不得**依 BR93.5 另建新訊息。
    violation_behaviour: 舊頁的半成品與新頁的新訊息並存，同一輪顯示兩次；或卸載後 store 永遠留著 streaming 的訊息
    source: "審查 R-05、AC1.1.4（交辦後切到架構圖生成頁）、brain-gateway/functional-design/functional-spec.md:57-58"

  # ── BR94：工作項 ──────────────────────────────────────────────
  - id: BR94.1
    statement: 每頁一份工作項集合，以 work_items 訊息整份取代；常駐區與對話流皆由它推導
    category: constraint
    applies_to: WorkItemStore、WorkItemDock、WorkItemList
    trigger: 收到 work_items
    logic: >
      work_items 是狀態訊息：收到即以 payload.items 整份取代集合（不合併、不本地推算）。
      兩個視圖只讀這一份；任一 workItemId 在兩處的 status 必須相等。
    violation_behaviour: 兩處各持副本，不同步時畫面出現兩個互相矛盾的狀態（INV-1 要防的形狀）
    source: "INV-1（interaction-spec.md:31）、AC1.1.1、AC1.3.2（改寫）、AC5.1.1"

  - id: BR94.2
    statement: 常駐區只列處理中與等待中，空集合時整區不渲染；窄螢幕預設收合為一行計數
    category: constraint
    applies_to: WorkItemDock
    trigger: 集合變更、視窗寬度
    logic: "過濾 status ∈ {處理中, 等待中}；結果為空 → 不渲染；寬度 < 768px 預設 collapsed（進行中 (N)）"
    violation_behaviour: 留空殼；窄螢幕時對話區被擠出首屏
    source: "mockups.md M1、M8、interaction-spec.md WorkItemDock"

  - id: BR94.3
    statement: 五個狀態以文字為主要載體，並各自顯示其附帶說明
    category: constraint
    applies_to: WorkItemDock、WorkItemList
    trigger: 渲染一個工作項
    logic: >
      徽章文字即狀態值（處理中／等待中／完成／失敗／已停掉），圖示與顏色為輔。
      等待中 → 下一行「在等：<waitingOn>」；失敗 → 下一行 failureReason；
      已停掉 → 下一行依 sideEffect：none ＝「沒有留下任何東西」、unknown ＝「不確定有沒有留下東西」、
      其他字串 ＝ 原樣顯示。unknown 不得當成 none 呈現。
    violation_behaviour: 只靠顏色區分；把 unknown 講成沒留下東西，等於替系統承諾它不承諾的事
    source: "AC1.1.2、AC1.3.1、AC5.1.2、mockups.md M1 狀態表、ws-contract.d.ts WorkItem.sideEffect"

  - id: BR94.4
    statement: 處理中與等待中的項目有「不是這個」；按下即送 correct_work_item，等下一則 work_items 才改變畫面
    category: constraint
    applies_to: WorkItemDock、WorkItemList
    trigger: 使用者按「不是這個」
    logic: >
      送 correct_work_item{workItemId}；該鈕轉為停用直到下一則 work_items 到達；不在本地把狀態改成已停掉。
      aria-label 必須含該項的 label。完成、失敗、已停掉的項目不渲染此鈕。
    violation_behaviour: 本地先改狀態 → 伺服器拒絕時畫面說謊；同名按鈕無法被螢幕閱讀器分辨
    source: "AC1.3.1、AC5.1.3（改寫）、線框 §13、interaction-spec.md WorkItemDock 無障礙列"

  - id: BR94.5
    statement: 對話流中的工作項清單附在它首次出現時的那一則大腦訊息下，保留全部狀態
    category: constraint
    applies_to: WorkItemList
    trigger: 某 workItemId 首次出現在 work_items
    logic: >
      記錄該 id 首次出現時該段最後一則大腦訊息作為錨點；之後只更新狀態、不移動位置。
      已停掉的項目與更正後新建的項目同時可見，各帶自己的狀態。
    violation_behaviour: 被停掉的項目從對話流消失，使用者看不到更正前後的對照
    source: "AC1.3.3、mockups.md M9"

  - id: BR94.6
    statement: 工作項與候選一律顯示伺服器給的 label，前端不另抄能力名稱表
    category: constraint
    applies_to: WorkItemDock、WorkItemList、ClarifyCandidates
    trigger: 渲染
    logic: "顯示 WorkItem.label 與 ClarifyCandidate.label；capability 只作為 data 屬性，不譯成中文"
    violation_behaviour: 前端與後端各有一份能力名稱，改名時只改一處（team.md 單一真實來源）
    source: "work_orchestrator_rules.py:330-336、functional-design-questions.md 第一節"

  - id: BR94.7
    statement: 成本工作進行中以該工作項的處理中徽章就地更新呈現，不另產生進度訊息
    category: constraint
    applies_to: WorkItemList、CostAnswerCard
    trigger: 成本工作項存在且未終止
    logic: >
      同一個工作項在對話流中只有一個位置；處理中 → 完成時徽章就地更新，cost_card 以伺服器發起的輪次
      附加在其後。不為進度新增訊息。
      **與 AC10.1.3「該則進度訊息被結構化卡片取代」的差異**（審查 R-07）：卡片是**附在其後**，不是**取代**原位置。
      取代需要知道卡片屬於哪個工作項，而 CostCardPayload 沒有 workItemId、WorkItem 也沒有 estimateSetId，
      前端無從配對。此為對 U12 已登錄處置（work-orchestrator/functional-design/functional-spec.md:313）的照做，
      並列為 functional-spec.md 的偏離 D-7 於關卡揭露。
    violation_behaviour: 每次狀態變更都新增一則訊息（AC10.1.2 要防的形狀）
    source: "AC10.1.2、AC10.1.3、work-orchestrator/functional-design/functional-spec.md:313"

  # ── BR95：反問 ────────────────────────────────────────────────
  - id: BR95.1
    statement: kind=intent 的反問以「我不確定你指的是哪一件事」為提示，每個候選顯示 label 與「就是這個」
    category: constraint
    applies_to: ClarifyCandidates
    trigger: 收到 clarify 且 kind=intent
    logic: "依 candidates 順序渲染；群組最後一項為「都不是，我再講一次」"
    violation_behaviour: 意圖反問與對象反問畫成同一種，使用者不知道在選什麼
    source: "AC1.2.1、U13 交接第 5 項、mockups.md M2"

  - id: BR95.2
    statement: kind=target 的反問以「你指的是哪一個？」為提示，只顯示 label，且恆有「都不是」回絕，候選只有一個時亦然
    category: constraint
    applies_to: ClarifyCandidates
    trigger: 收到 clarify 且 kind=target
    logic: "候選鈕只顯示 label；群組最後一項為「都不是」，按下送 candidateId:null"
    violation_behaviour: 只有一個候選時使用者無法說不是這個，只能被迫接受
    source: "U13 交接第 6 項（brain-gateway/code-generation/code-summary.md:237）"

  - id: BR95.3
    statement: 候選不顯示信心值
    category: constraint
    applies_to: ClarifyCandidates
    trigger: 渲染
    logic: "ClarifyCandidate.confidence 不讀、不渲染"
    violation_behaviour: 若 OQ-10 收斂為「無可比較的信心值」，畫面會壞
    source: "[DM:D3]=A、interaction-spec.md:218-231"

  - id: BR95.4
    statement: 選定候選只在使用者按下時送出一次；之後該組進入 picking，收到下一則訊息即結束
    category: validation
    applies_to: ClarifyCandidates
    trigger: 使用者按下候選
    logic: >
      送 select_clarify_candidate{candidateId}；被選中者顯示載入、其餘停用；本組不再接受第二次選擇。
      不得在使用者未選擇時送出任何 select 訊息（null 只代表使用者按了回絕）。
    violation_behaviour: 客戶端在無選擇時送出 null，伺服器把它當成「都不是」
    source: "AC1.2.2、ws-contract.d.ts SelectClarifyCandidatePayload"

  - id: BR95.5
    statement: 回絕（都不是）後焦點回輸入列，脈絡列與作業對象不變；使用者直接輸入新句子時舊候選轉 stale
    category: constraint
    applies_to: ClarifyCandidates、輸入列
    trigger: 按回絕，或在候選未決時送出新的 user_message
    logic: >
      回絕 → 送 candidateId:null，該組淡化停用，焦點移到輸入列；不改脈絡列（伺服器此時不送 work_target）。
      候選未決時送出新句 → 舊組轉 stale（淡化停用），不殘留等待。
    violation_behaviour: 回絕後脈絡列被清空；舊候選仍可點，與新的一輪混在一起
    source: "AC1.2.3、interaction-spec.md ClarifyCandidates 狀態表"

  # ── BR96：成本卡片 ────────────────────────────────────────────
  - id: BR96.1
    statement: 成本卡片依已交付的 CostCardPayload 呈現：非 null 的三段文字、無法取價的原因、伺服器給的成本頁連結
    category: constraint
    applies_to: CostAnswerCard
    trigger: 收到 cost_card
    logic: >
      依序顯示 savingText、comparisonText、qualityText（null 者略過）；unavailableReasons 非 null 時
      顯示一行「部分項目無法取價」並列出其鍵；連結 href 取 costPageUrl（不自行組網址），
      連結文字「到成本頁看估價表 #<estimateSetId> 的完整分析」。三段文字皆為 null 時顯示「這份估價表目前沒有可說明的建議」。
    violation_behaviour: 自組網址與伺服器不一致；或為了湊 M3 的總額而顯示不存在的數字
    source: "AC10.1.3、[DM:D5]=A、work_orchestrator.py:835-845、mockups.md:548 的 [assumption]"

  - id: BR96.2
    statement: 成本的逾時與失敗以工作項的失敗狀態與 failureReason 呈現，兩者文字不同
    category: constraint
    applies_to: WorkItemList、WorkItemDock
    trigger: 成本工作項轉為失敗
    logic: "顯示伺服器給的 failureReason（逾時與失敗為不同字串）；不以前端判斷改寫"
    violation_behaviour: 畫面停在最後狀態，或兩種終態看起來一樣
    source: "AC10.2.1、AC10.2.2、work_orchestrator.py:858、:878"

  - id: BR96.3
    statement: 成本問答全程停在入口頁；卡片連結只在使用者點擊時導航
    category: constraint
    applies_to: EntryPage
    trigger: 成本工作進行到完成
    logic: "收到 cost_card 或工作項完成時不自動 navigate"
    violation_behaviour: 使用者被帶離入口頁
    source: "AC10.1.4"

  - id: BR96.4
    statement: 無 C1 權限時，成本工作項以失敗呈現並顯示伺服器給的權限說明
    category: authorization
    applies_to: WorkItemList
    trigger: 成本工作項因 403 失敗
    logic: "與 BR96.2 同一呈現路徑；前端不預先隱藏或攔截成本問題（授權由伺服器端判定）"
    violation_behaviour: 前端自行攔截 → 畫面顯示的拒絕與伺服器的授權判定可能不一致
    source: "AC10.1.5、deferred-ac-rulings.md:9（AC10.2.4 改寫）"

  # ── BR97：脈絡列與子頁面 ─────────────────────────────────────
  - id: BR97.1
    statement: 脈絡列只掛在入口頁、/workspace、/assessment 三處
    category: constraint
    applies_to: ContextBar 的掛載點
    trigger: 渲染頁面
    logic: "三處以外（含 /cost、/admin/*、/projects、/memory）不渲染脈絡列、不開大腦連線"
    violation_behaviour: 不在共享範圍的頁面顯示共享脈絡
    source: "AC2.1.1、AC2.1.2、AC2.1.3、[RA:FR2.1]"

  - id: BR97.2
    statement: 脈絡列以 work_target 帶來的名稱顯示三層；某層有識別碼但名稱為 null 時顯示「（無法顯示名稱）」；三層皆 null 顯示「尚未選定」
    category: constraint
    applies_to: ContextBar；work_target 的契約增量（U2、U13）
    trigger: 套用 work_target
    logic: >
      顯示「projectName / systemName / diagramName」，null 的層略過；
      識別碼非 null 而名稱 null → 該層顯示「（無法顯示名稱）」；三個識別碼皆 null → 「尚未選定」。
      名稱由伺服器在推送 work_target 時以連線的 principal 經 **U7 新增的單一唯讀方法**查得（使用者 2026-10-17 裁決，
      含未歸屬系統的圖；機制、失敗語意與呼叫點見 functional-spec.md §二之一）；名稱查詢的任何失敗只使該層為 null，
      不得使握手或扇出失敗。前端不發 HTTP 查名稱。名稱只在推送時更新——改名或刪除後到下一次推送前會陳舊（OPEN-EP14-16）。
      展開態不顯示「最後異動」（無來源，OPEN-EP14-11）。
    violation_behaviour: 顯示空白或錯誤；名稱查詢故障使入口頁連不上；或前端另走 HTTP，推翻 contract-summary.md:916-917 的唯一通道條款
    source: "[EP2]=A 與其修訂 1、AC1.1.5、AC2.1.1、AC2.2.3、AC9.1.1、AC10.1.1、functional-spec.md §二之一"

  - id: BR97.3
    statement: 子頁面的脈絡列有「改為獨立對話／切回共享對話」切換；徽章以伺服器回推的 sharing_mode 為準
    category: constraint
    applies_to: ContextBar（子頁面）
    trigger: 使用者按切換
    logic: >
      送 set_sharing_mode{mode, scope=本頁}；徽章與段切換只在收到 scope 相符的 sharing_mode 後發生（不樂觀更新）。
      入口頁不渲染此切換。
    violation_behaviour: 樂觀更新後伺服器拒絕，畫面與伺服器的段不一致
    source: "AC3.1.1、[R6]、K-13 的 ownership_note、ws-contract.d.ts:184"

  - id: BR97.4
    statement: 子頁面在脈絡列下有可收合的「問大腦」精簡對話面板，送出帶本頁 page；既有對話區與串流端點不動
    category: constraint
    applies_to: SubpageBrainPanel、WorkspacePage、AssessmentPage
    trigger: 子頁面掛載
    logic: >
      面板預設收合（寬窄螢幕皆然）；展開後顯示本頁目前讀取段的對話紀錄、反問、工作項清單與輸入列，
      與入口頁同一套元件。WorkspacePage 右側既有設計對話與 AssessmentPage 的既有流程不改。
    violation_behaviour: 子頁面沒有對大腦說話的入口 → US3.1 不可觀察；改寫既有對話 → AC8.1.4 風險
    source: "[EP1]=A、AC3.1.1、AC3.1.3、AC8.1.4"

  - id: BR97.5
    statement: 子頁面的首次對齊等頁面就緒才做：首筆相符的 work_target 先暫存，頁面就緒後只判斷一次；之後的推送只更新脈絡列，非本頁回聲者才提示
    category: policy
    applies_to: WorkspacePage、AssessmentPage 的同步掛點
    trigger: 子頁面掛載後收到本頁所讀段的 work_target；頁面就緒
    logic: >
      **就緒閘門**（審查 R-02）：/workspace ＝ bootstrapDone 為真（既有 state，WorkspacePage.tsx:269-301，`:297` 於 finally 設定；
      該流程先 await fetchDiagrams 才打 bootstrap，故就緒時圖清單請求已結束）；/assessment ＝ 圖清單請求已結束
      （新增一個在 fetchDiagrams 的 then／finally 回呼內設定的「清單已結束」旗標——事件回呼中 setState 為 lint 允許的形狀）。
      就緒前收到的 work_target 存為 pendingInitialTarget（後到者覆蓋先到者），**旗標不消耗**。
      就緒且已有 pendingInitialTarget（快照先到）或就緒後收到首筆（快照後到）時，**只判斷一次**，然後消耗旗標：
      (1) 本頁有網址參數 diagramId（/assessment 由 WorkspacePage.tsx:441 進入）→ 頁面優先，不改開，交 BR97.6；
      (2) 否則 IF 目標 diagramId 非 null 且在本頁圖清單中 is_owner=true 且不等於目前開啟的圖 →
          /workspace 以既有 handleLoadDiagram（:304）開它；/assessment 以 setDiagramOverride 選它；
      (3) 否則交 BR97.6 以目前開啟的圖判斷是否回寫。
      **之後的 work_target**：只更新脈絡列；IF diagramId 等於目前開啟的圖，或等於本頁最近一次送出的 set_work_target 的
      diagramId（自己的回聲）THEN 不提示；ELSE 在脈絡列下顯示「作業對象已改為 <名稱>」＋「開啟這張圖」（僅自有圖有此鈕）。
      圖清單請求失敗（清單為空且請求未成功）時視為擁有者未知：兩個方向都不同步，並顯示「無法確認這張圖的擁有者，未同步作業對象」。
    violation_behaviour: 快照比 bootstrap 早到時被 bootstrap 覆蓋，AC1.1.4／AC2.2.1 變成時序賭局；使用者自己開圖卻收到「作業對象已改為…」
    source: "[EP3]=A、審查 R-02、AC1.1.4、AC2.2.1、AC9.1.3、WorkspacePage.tsx:269-301"

  - id: BR97.6
    statement: 首次對齊之後，子頁面「目前選定的圖」每次改變都依其來源與擁有者決定是否回寫作業對象
    category: policy
    applies_to: WorkspacePage（currentDiagramId）、AssessmentPage（selectedDiagramId ＝ diagramOverride ?? urlDiagramId）
    trigger: 就緒且首次對齊完成後，選定的圖改變；或 BR97.5 第 (1)、(3) 情形
    logic: >
      以狀態變化驅動（審查 R-03），涵蓋全部路徑——/workspace：bootstrap 開上次的圖（:282）、下拉改選（handleLoadDiagram :313）、
      儲存新圖（:823）、新建空白畫布（handleNewDiagram :333）、刪除（:371）；/assessment：網址參數（由 :441 進入）、
      下拉改選（AssessmentPage.tsx:1268）、上傳後存成新圖（:560）、存回優化結果（:743）、刪除（:813）。
      ① 新值非 null 且 is_owner=true 且不等於作業對象的 diagramId → 送 set_work_target{projectId:null, systemId:null, diagramId,
         segment=本頁所讀段}（伺服器以 hierarchy_service.py:310-322 推導系統與專案），記為本頁最近一次送出值；
      ② 新值非 null 且非自有（別人分享）→ 不送；脈絡列下顯示「這張圖是別人分享的，不會成為大腦的作業對象」（由 render 推導，不另存 state）；
      ③ 因**刪除**而變為 null，且被刪的圖等於作業對象的 diagramId → 送 set_work_target{projectId, systemId（取自目前的 work_target）,
         diagramId:null}（刪除處理器明確呼叫，不靠 null 推斷）；
      ④ 因新建空白畫布或評核頁的未存檔上傳而變為 null → 不送，作業對象維持；脈絡列下顯示「目前畫布未存檔，作業對象維持 <名稱>」；
      ⑤ 由 BR97.5 第 (2) 情形開的圖等於作業對象，依 ① 的「不等於」條件自然不送（不往返）。
      送出由 effect 執行（送 WebSocket 訊息不是 setState，不違反 react-hooks/set-state-in-effect）。
      **孤兒圖**（系統歸屬為 null）：① 照送，伺服器存 systemId=null、projectId=null；脈絡列只顯示圖名（由 U7 新方法取得）。
      此時 AC2.2.1「指向同一個系統」不成立，列為 OPEN-EP14-17 於關卡揭露。
    violation_behaviour: 由 workspace 進 assessment 後作業對象沒跟上；畫布顯示 X 而脈絡列是 Y；作業對象停在已刪除的圖
    source: "[EP3]=A、審查 R-03、AC2.2.1、AC2.2.2、hierarchy_service.py:89-96、:310-322"

  - id: BR97.7
    statement: 「切換對象」鈕只在 U16 提供選單掛載時渲染；選定回呼一律轉成 set_work_target
    category: constraint
    applies_to: ContextBar 的 U16 掛載點
    trigger: U16 回呼 onObjectSelected
    logic: "未掛載選單 → 不渲染該鈕；收到 onObjectSelected(target) → 送 set_work_target（segment 依 BR92.3），不本地改脈絡列"
    violation_behaviour: 渲染點了沒反應的鈕；或本地先改、伺服器拒絕後畫面說謊
    source: "K-13（contract-summary.md:1029-1030、:1037）"

  - id: BR97.8
    statement: 子頁面切換模式時，對話區立即改顯示新段的紀錄；切回共享時共享段的紀錄與作業對象與離開時相同
    category: constraint
    applies_to: SubpageBrainPanel、ContextBar
    trigger: 收到 scope 相符的 sharing_mode
    logic: >
      isolated → 顯示該頁段的紀錄（新段為空）；shared → 顯示 BR93.4 store 中的共享段紀錄；
      作業對象改為 BR92.4 保存的該段 work_target。獨立段的紀錄在切回共享後保留於 store（不刪除、不顯示）。
    violation_behaviour: 獨立對話顯示共享訊息；切回後共享段的紀錄消失
    source: "AC3.1.2、AC3.1.4、OQ-1（獨立段去向，本規則只保證不刪除）"

  # ── BR98：空狀態、無障礙、資料來源、驗證策略 ──────────────────
  - id: BR98.1
    statement: 入口頁空狀態只顯示大腦能交辦的兩張卡：A 架構設計、C 成本，依權限顯示；點卡片填入範例句、不自動送出
    category: constraint
    applies_to: EntryEmptyState
    trigger: 共享段紀錄為空
    logic: >
      卡 A（「架構設計與檢視」）顯示條件 canArch('view') OR can('A3','view')；卡 C（「成本分析」）顯示條件 can('C1','view')；
      點擊 → 範例句填入輸入列並聚焦，不送出。另附「或直接說出你要做什麼」。兩張皆不可見時只顯示歡迎語與該句。
      卡片為 list 內的 button。其餘六張不渲染。
    violation_behaviour: 顯示大腦無法交辦的能力卡，點了得不到結果
    source: "[EP5]=A、wireframes.md:733-776 §20（偏離其「八張」字面）、intent_routing_types.py:50-54"

  - id: BR98.2
    statement: 「最近的對話」本單元不渲染
    category: policy
    applies_to: EntryPage
    trigger: 不適用
    logic: >
      不渲染該區塊、不提供「+ 新對話」。使用者 2026-10-17 裁決：**移到另一個 intent**，本 intent 不做；
      記為待另開 intent 的候選需求，前提是先定對話的保存期限與資料來源（OPEN-EP14-2）
    violation_behaviour: 不適用
    source: "[EP5]=A、使用者裁決（2026-10-17）、session-store/nfr-requirements/nfr-requirements-questions.md:83"

  - id: BR98.3
    statement: 無障礙：脈絡列與常駐區為具名 region；狀態變更與完成播報寫入既有 LiveRegion；testid 用 brain-* 前綴（Sidebar 項沿用 sidebar-* 慣例）
    category: constraint
    applies_to: 本單元全部元件
    trigger: 渲染
    logic: >
      ContextBar：region、aria-label「目前作業對象」、展開鈕 aria-expanded；WorkItemDock：region、aria-label「進行中的工作」；
      反問：role=group 並具名；播報一律經 frontend/src/components/LiveRegion.tsx，不另建、不用 toast。
    violation_behaviour: axe 掃描（U17）紅燈；螢幕閱讀器不知道狀態變了
    source: "interaction-spec.md 各元件無障礙列、unit-of-work.md:228、K-13 provides_to_U17"

  - id: BR98.4
    statement: e2e 分兩層：真實 stack 驗連線與非交辦行為；交辦類畫面以 routeWebSocket 扮演伺服器，且樁訊框只能由 src 之下受 tsc -b 檢查的型別化建構器產生
    category: policy
    applies_to: frontend/tests/e2e 的入口頁 spec；frontend/src/brain/testing/ 的訊框建構器
    trigger: 撰寫與執行 e2e
    logic: >
      真實 stack：握手、ready、狀態推送、prompt_guard 攔截、錯誤呈現（金鑰為空時 INTERNAL_ERROR）、BR91 的落地、Sidebar。
      routeWebSocket：工作項兩處同步、五狀態、反問兩種 kind、回絕、逐項導回、成本卡片、逾時與失敗可區分、零內容 done、
      4401／4400／退避、BR97.5 的快照先到與後到、BR93.7 的換頁合併。
      **型別承載機制**（審查 R-01）：frontend/tests 不在任何 tsconfig 內（tsconfig.app.json 只 include src、tsconfig.node.json
      只 include vite.config.ts），故 e2e 檔本身不受 tsc -b 檢查。因此：(a) 每種伺服器訊息一個建構函式與每個情境的完整訊框序列，
      放在 frontend/src/brain/testing/wsFrames.ts（純模組，不 import 任何 vite 專屬 API），以 components['schemas'] 的型別逐欄組出
      WsEnvelope，由既有的 npm run build（tsc -b）檢查；(b) 編碼函式簽章為 encodeFrame(env: WsEnvelope): string；
      (c) e2e spec 只能呼叫這些匯出函式取得要 send 的字串，不得在 spec 內手寫 JSON 訊框（code review 檢核；spec 內出現 "type":
      字面量即違反）。該模組不被任何 app 程式 import，故不進生產 bundle。
      **突變驗證**：在 code-generation 對契約做一次欄位改名（例如 WorkTargetPayload.diagramName → diagramTitle）並重產型別檔，
      確認 npm run build 以 wsFrames.ts 的型別錯誤紅燈，還原後轉綠；結果寫進 tcms-test-cases 的 automation-test-plan.md。
      **不採用**新增 tests 用 tsconfig（理由見 functional-spec.md §十二 R-01）。不新增依賴。
    violation_behaviour: 交辦類 AC 在 CI 無任何自動化斷言；或樁的訊框與契約漂移而無人察覺
    source: "[EP6]=A、[US:U9]=A（stories.md:628-632，字面偏離見 functional-spec.md §八）、cicd-pipeline.md:82-86"

  - id: BR98.5
    statement: 本單元新增的前端程式不發任何 HTTP 請求；唯一後端通道是大腦連線
    category: constraint
    applies_to: 本單元新增的元件與 hook
    trigger: 任何資料需求
    logic: >
      名稱、作業對象、工作項、反問、成本卡片皆來自 WebSocket。BR97.5／BR97.6 讀取的圖清單與 is_owner
      是子頁面既有狀態（既有的 HTTP 呼叫），本單元不新增呼叫。
    violation_behaviour: 新增 U14 → U7 的 HTTP 邊，推翻已核可契約條款
    source: "contract-summary.md:303、:916-917、[EP2]=A"
```

## 三、規則摘要

| 群組 | 條數 | 管什麼 | 驗證層 |
|---|---|---|---|
| `BR91` | 5 | 落地瀑布、萬用路由、Sidebar 入口、記憶捷徑 | Playwright（真實 stack） |
| `BR92` | 8 | 連線、子協定、hello／ready、頁與段欄位、過濾、關閉碼與退避、未知 type 與 error、不自動重送、不洩漏 | Playwright（兩層）＋ lint |
| `BR93` | 7 | 逐訊框附加、零內容、等待回覆、紀錄 store、推播落點、播報、卸載與 turnId 合併 | Playwright（`routeWebSocket`） |
| `BR94` | 7 | 單一工作項集合、常駐區、五狀態、導回、對話流錨點、label、成本進行中 | Playwright（`routeWebSocket`） |
| `BR95` | 5 | 兩種反問、不顯示信心、選定、回絕與 stale | Playwright（`routeWebSocket`） |
| `BR96` | 4 | 成本卡片、逾時與失敗、停在入口頁、權限失敗 | Playwright（`routeWebSocket`） |
| `BR97` | 8 | 掛載範圍、名稱、共享切換、子頁面面板、就緒閘門與回聲、狀態驅動回寫、選單掛載、模式切換 | Playwright ＋ `TestClient`（`BR97.2` 的伺服器端） |
| `BR98` | 5 | 空狀態卡片、最近的對話、無障礙、e2e 策略與型別化訊框、無 HTTP | Playwright ＋ `tsc -b` ＋ 靜態檢查 |
| **合計** | **49** | | |

條數由本檔 YAML 的 `- id:` 行實算（見 `functional-spec.md` §十之一）。

兩條 `policy` 類規則（`BR98.2`、`BR98.4`）中，`BR98.2` 的 `violation_behaviour` 寫「不適用」：它是**誠實宣告**，
寫下來是為了不讓下游以為「最近的對話」已被某處實作。
