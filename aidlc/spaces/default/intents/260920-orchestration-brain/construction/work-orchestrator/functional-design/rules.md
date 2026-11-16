# Rules — `U12 work-orchestrator`

## 一、識別字區段：`BR51.x`–`BR58.x`

已佔用：`BR1`–`BR8`（11 個單元）、`BR21`–`BR28`（`U24`）、`BR31`–`BR35`（`U15`）、
`BR41`–`BR47`（`U20`）。本單元取 **`BR51`–`BR58`**。本檔刻意不寫出他單元識別字的字面形式。

> **修訂 1（2026-10-12，依 `reviews/review-01.md` 的 R-01～R-13）**：新增 `BR51.6`–`BR51.8`、
> `BR52.6`–`BR52.7`、`BR53.4`、`BR55.7`、`BR56.5`–`BR56.8`、`BR58.5`；改寫 `BR51.1`、`BR51.3`、
> `BR52.4`、`BR53.3`、`BR55.1`、`BR55.3`、`BR55.4`、`BR56.1`–`BR56.3`、`BR57.1`–`BR57.5`、`BR58.1`–`BR58.3`。
> 各處修改與發現的對應見 `functional-spec.md` 第十一節。
>
> **修訂 2（2026-10-12，依 `reviews/review-02.md` 的 R-03、R-08、R-10、R-14～R-19）**：改寫 `BR51.7`、
> `BR52.4`、`BR52.7`、`BR53.4`、`BR55.1`、`BR55.4`、`BR56.1`、`BR56.3`、`BR56.7`、`BR57.1`、`BR57.4`；
> 規則數不變。對應見 `functional-spec.md` 第十二節。

## 二、規則（source of truth）

```yaml
rules:
  # ---- BR51：授權與對既有能力的呼叫 ---------------------------------------
  - id: BR51.1
    statement: "呼叫既有 A1／A3／C1 一律走 HTTP（同進程 ASGI 傳輸），並帶使用者本人的 bearer token"
    category: authorization
    applies_to: 對既有能力的每一次呼叫
    trigger: 工作項進入處理中並開始執行
    logic: >
      以 httpx.AsyncClient 搭配 ASGITransport 呼叫同一個 FastAPI app；app 參考由 U13 在建構
      WorkOrchestrator 時傳入（取自 websocket.app），本單元不 import main（避免循環匯入）。
      以 U13 在握手時取得的使用者 token 作為 Authorization 標頭，使既有端點的
      require_story_action／require_arch_action 照常執行。不得同進程直呼既有 service 層。
      ASGI 傳輸一律把回應收齊才交回（httpx 0.28.1 的 body_parts 累積至 app 結束），故本單元
      不依賴任何串流中途的事件，只在回應結束後判定結果（BR56.5）。
    violation_behaviour: 不適用（本規則定義做法）
    source: "X-01／X-02 x-authorization-responsibility；[RA:FR10.2]；review-01 R-02"

  - id: BR51.2
    statement: "使用者 token 只在記憶體內傳遞，不寫入工作項、大腦工作階段、log 或任何持久層"
    category: policy
    applies_to: WorkOrchestrator
    trigger: 每次呼叫
    logic: "token 以參數傳入、用完即棄；工作項只存 dispatchStage，不存任何憑證。"
    violation_behaviour: 不適用
    source: "ADR-0006 IAM 面；X-01 audit_subject"

  - id: BR51.3
    statement: "既有能力回 403 時，工作項轉為失敗，原因說明使用者沒有該功能的權限，不重試"
    category: authorization
    applies_to: 三種能力
    trigger: 呼叫回 403
    logic: "status 失敗；failureReason 為固定句型「你沒有使用〈能力名稱〉的權限，或帳號已被停用」；不呼叫任何其他能力。"
    violation_behaviour: 不適用
    source: "AC10.1.5；X-01；review-01 R-11（auth.py 的 403 也涵蓋帳號已停用）"

  - id: BR51.4
    statement: "架構圖被存回後，經 HierarchyFacade.record_diagram_change 寫一列變更紀錄，actor_user_id 為使用者本人"
    category: policy
    applies_to: architecture-design 工作項
    trigger: BR56.1 存回成功（含 BR55.7 的停掉後才完成的存回）
    logic: "requirement_summary 取 requestText 的前 200 字；requirement_label 為工作項 label；actor_user_id=principal.user_id。"
    violation_behaviour: "寫入失敗時工作項狀態不變（圖已存回），sideEffect 註明「變更紀錄未寫入」並記 error log"
    source: "K-07；hierarchy_facade.py 的 record_diagram_change 必填 actor_user_id"

  - id: BR51.5
    statement: "工作項完成時寫一則 procedure 記憶；寫入失敗不影響工作項狀態"
    category: policy
    applies_to: 進入完成的工作項
    trigger: status 轉為完成
    logic: >
      經 MemoryFacade.write(principal, kind=procedure, content=<能力名稱>＋<label>) 寫入；
      該方法是同步且會呼叫嵌入 Port，一律以 asyncio.to_thread 執行，不得在事件迴圈上直呼。
      寫入失敗記 warning log（不含內容），工作項維持完成。
    violation_behaviour: 不適用
    source: "U8 functional-design 的 [FD4]=B；review-01 R-12(5)"

  - id: BR51.6
    statement: "既有能力回 401 時，工作項轉為失敗，原因請使用者重新登入，不重試"
    category: authorization
    applies_to: 三種能力
    trigger: 呼叫回 401
    logic: >
      status 失敗；failureReason 為「登入已過期，請重新登入後再說一次」。token 是 U13 握手當下的
      快照（JWT 8 小時過期，大腦工作階段 24 小時），等待中的工作項可能在 token 過期後才開始執行。
    violation_behaviour: 不適用
    source: "review-01 R-11；auth.py 的 401「憑證無效或已過期」"

  - id: BR51.7
    statement: "同進程呼叫 U7／U8 的 facade 時，每次呼叫開一個獨立的 DB session、重新自 DB 取使用者並鑄造 Principal，以 asyncio.to_thread 執行，用完即關"
    category: constraint
    applies_to: 背景執行中的 HierarchyFacade／MemoryFacade 呼叫
    trigger: 每次 facade 呼叫
    logic: >
      不沿用任何 request 範圍的 session（背景 task 的生命週期長於發起它的 WebSocket 訊息）；
      以 SessionLocal() 開、finally 關。同一個 session 內以 principal.user_id 重讀 User 並經
      mint_principal 重新鑄造，不沿用握手當下的角色快照——使背景執行期間被降權或停用的使用者，
      在 facade 路徑上與 HTTP 路徑（get_user_from_token 每次重查 DB）得到相同結果。使用者不存在或
      is_active 為假 → 依 BR51.3 失敗。facade 自己的授權照常執行，本單元不繞過。
    violation_behaviour: 不適用
    source: "review-01 R-12(5)；review-02 R-17；hierarchy_facade.mint_principal"

  - id: BR51.8
    statement: "facade 以擁有者範圍拒絕時（HierarchyNotFound），依呼叫點落入既有失敗分支，不改用其他路徑"
    category: authorization
    applies_to: record_diagram_change、list_diagrams_of_system
    trigger: facade 拋 HierarchyNotFound 或 HierarchyForbidden
    logic: >
      record_diagram_change 只允許圖的擁有者（assert_diagram_owned_by）；被分享者經 A1 改了他人
      的圖時，存回成功但變更紀錄寫不進去 → 依 BR51.4 的 violation_behaviour 處理。
      list_diagrams_of_system 被拒 → 依 BR56.1 的「找不到可用的圖」失敗。
    violation_behaviour: 不適用
    source: "review-01 R-12(3)；domain-design R-01（U12 → U7 同進程授權語意）"

  # ---- BR52：工作項的建立與存放 ------------------------------------------
  - id: BR52.1
    statement: "路由結果的每一個意圖落成一個工作項，依原句順序；信心值低於門檻時不建立任何工作項"
    category: constraint
    applies_to: WorkOrchestrator.dispatch
    trigger: 收到 IntentDecision
    logic: "IF below_threshold THEN 回空集合（反問由 U11／U13 處理）ELSE 對 intents 逐一建立工作項。"
    violation_behaviour: 不適用
    source: "[RA:FR5.1]；AC5.1.1；AC1.2.1"

  - id: BR52.2
    statement: "label 以固定句型產生：「〈能力名稱〉：〈作業對象名稱〉」，作業對象未定時省略後半"
    category: calculation
    applies_to: 新工作項
    trigger: 建立時
    logic: "能力名稱取固定對照（架構設計／架構檢視／成本分析）；不放入使用者原句。"
    violation_behaviour: 不適用
    source: "AC1.1.1（標示它被交給哪個能力）"

  - id: BR52.3
    statement: "新工作項的初始狀態為處理中，符合 BR53.1 者為等待中"
    category: calculation
    applies_to: 新工作項
    trigger: 建立時
    logic: "預設處理中；BR53.1 成立時等待中。"
    violation_behaviour: 不適用
    source: "AC1.1.1；AC5.1.2"

  - id: BR52.4
    statement: "每個工作項存成大腦工作階段 Redis key 內的一個獨立欄位，與工作階段同一個到期時間"
    category: constraint
    applies_to: 工作項的讀寫
    trigger: 每次寫入
    logic: >
      欄位名 wi:<workItemId>，值為工作項 JSON。經 U10 SessionStore 新增的三個方法讀寫：
      load_work_items（讀全部 wi:* 欄位）、put_work_item（新建）、update_work_item（BR52.7 的
      比對後寫入）。不另開 key、不另設到期時間。逐項欄位使兩個工作項的更新互不覆蓋。
      put_work_item 與 update_work_item 皆為 Lua 腳本，key 不存在即拒絕寫入（不得以 HSET／HSETNX
      重建一個沒有到期時間、沒有 meta 欄位的 key）；put_work_item 被拒時 dispatch 拋 ValueError
      （工作階段已到期，由 U13 依既有的工作階段失效路徑處理）。
    violation_behaviour: 不適用
    source: "[WO3]=A；K-11 storage；review-01 R-10"

  - id: BR52.5
    statement: "每次狀態改變都寫回工作階段，並把整個工作項集合推送給該工作階段"
    category: policy
    applies_to: 任何狀態或欄位改變
    trigger: 改變發生時
    logic: "寫回後產生 work_items 訊息（WorkItemsPayload，當前全集合），經 sink 的工作階段出口由 U13 扇出。"
    violation_behaviour: 不適用
    source: "brain_ws_contract.WorkItemsPayload（狀態訊息，改變時扇出）"

  - id: BR52.6
    statement: "requestText 取本輪使用者原句；多意圖時每個工作項都收到完整原句"
    category: calculation
    applies_to: WorkOrchestrator.dispatch
    trigger: 建立工作項時
    logic: >
      dispatch 新增 utterance（本輪使用者原句）與 segment_id（本輪訊息所屬的段）兩個輸入，由 U13
      傳入。requestText=utterance 前 2000 字。作業對象取 segment_id 那一段的作業對象，不取其他段。
      多意圖時不切分原句（IntentDecision 沒有原句區段資訊），A1 收到完整原句。
    violation_behaviour: "segment_id 不在工作階段內 → 不建立工作項並拋 ValueError（U13 的程式錯誤）"
    source: "review-01 R-07；intent_routing_types.IntentDecision 不含原句"

  - id: BR52.7
    statement: "工作項的每一次更新都是比對後寫入：只有目前的 status 在預期集合內且 dispatchStage 等於呼叫端讀到的值時才寫入"
    category: constraint
    applies_to: 背景執行、correct、逾期掃描
    trigger: 任何工作項更新
    logic: >
      update_work_item(session_key, work_item_id, expected_statuses, expected_dispatch_stage, new_item)
      以 Redis Lua 腳本原子地讀欄位、比對 status 與 dispatchStage 兩者、皆符合才寫入，回傳是否寫入。
      new_item 必須由呼叫端剛讀到的那份工作項推導（不得用記憶體中較早的副本），使 estimateSetId 等
      其他欄位不被過期值覆蓋。不符合時呼叫端重讀、依新的 status 與 dispatchStage 重算後再試（correct）
      或中止該步（背景執行）。這使「停掉」與「背景推進 dispatchStage」不論交錯順序為何，sideEffect
      都依停掉當下真實的 dispatchStage 決定。
    violation_behaviour: "比對不符 → 不寫入，回 False"
    source: "review-01 R-10；redis_gateway.RedisGateway.eval_script"

  # ---- BR53：等待中（[WO2]=A）---------------------------------------------
  - id: BR53.1
    statement: "同一次交辦中，成本或檢視類工作項排在架構設計工作項之後時，等待該架構設計完成"
    category: calculation
    applies_to: WorkOrchestrator.dispatch
    trigger: 建立工作項時
    logic: >
      IF capability ∈ {cost-finops, well-architected-review} AND 同一次交辦中在它之前有
      architecture-design 工作項 THEN status 等待中，dependsOn 為最近的那一個 architecture-design
      工作項，waitingOn 為其 label。其他組合不等待。
    violation_behaviour: 不適用
    source: "[WO2]=A；AC5.1.2；H-3"

  - id: BR53.2
    statement: "被等待的工作項完成時，等待它的工作項轉為處理中並開始執行"
    category: policy
    applies_to: 等待中的工作項
    trigger: dependsOn 指向的工作項轉為完成
    logic: "status 處理中、waitingOn 與 dependsOn 清為 null，依 BR56 執行。"
    violation_behaviour: 不適用
    source: "AC5.1.2"

  - id: BR53.3
    statement: "被等待的工作項失敗時，等待它的工作項轉為失敗，不執行"
    category: policy
    applies_to: 等待中的工作項
    trigger: dependsOn 指向的工作項轉為失敗
    logic: "status 失敗；failureReason 為「前一項〈label〉沒有完成，這一項沒有執行」；sideEffect none。"
    violation_behaviour: 不適用
    source: "[WO2]=A 的推論"

  - id: BR53.4
    statement: "被等待的工作項被使用者停掉時，唯讀的成本項照常開始；會建立紀錄的檢視項不執行、轉為已停掉"
    category: policy
    applies_to: 等待中的工作項
    trigger: dependsOn 指向的工作項轉為已停掉
    logic: >
      cost-finops：status 處理中、waitingOn 與 dependsOn 清為 null，依 BR56.3 執行（只讀既有估價表，
      不留下任何東西，與被停掉的改圖無關）。
      well-architected-review：status 已停掉、sideEffect none、waitingOn 與 dependsOn 清為 null，
      不呼叫 A3；以伺服器輪次送「〈label〉沒有執行：前一項〈被停掉的 label〉已停掉」。理由：A3 在
      串流開始時就建立檢視紀錄（持久化），而使用者說「不是這個」否定的是整個判讀（BR55.5 請他再說
      一次）；在未被修改的舊圖上自動建立檢視紀錄與此前提矛盾。
      兩者都改變了後項的狀態，故 AC1.3.2／AC5.1.3 的「不受影響」在本規則下不是字面成立，
      traceability 標 Deferred，交使用者裁決（functional-spec 的 OPEN-WO12-7）。
    violation_behaviour: 不適用
    source: "AC1.3.2；AC5.1.3；review-01 R-08；review-02 R-08；review_orchestrator.start_review"

  # ---- BR54：狀態機 ------------------------------------------------------
  - id: BR54.1
    statement: "合法轉換只有：等待中→處理中、等待中→失敗、等待中→已停掉、處理中→完成、處理中→失敗、處理中→已停掉"
    category: constraint
    applies_to: WorkItem.status
    trigger: 任何狀態改變
    logic: "不在清單內的轉換一律拒絕並記 error log；完成、失敗、已停掉為終態，沒有向外的轉換。"
    violation_behaviour: "拒絕轉換，工作項維持原狀態"
    source: "K-11 status_values；AC1.1.2"

  # ---- BR55：逐項更正（[WO4]=A）------------------------------------------
  - id: BR55.1
    statement: "更正把處理中或等待中的工作項轉為已停掉，sideEffect 依停掉當下儲存的 dispatchStage 決定"
    category: policy
    applies_to: WorkOrchestrator.correct
    trigger: 使用者對某一項說「不是這個」
    logic: >
      讀工作項 → 依讀到的 dispatchStage 算 sideEffect → 以 BR52.7 比對 status 與該 dispatchStage 後寫入；
      比對失敗即重讀重算（背景已把 dispatchStage 往前推進時，改依新值算）。
      dispatchStage=not_dispatched → none；request_sent → unknown（請求已送出，系統不知道對方
      是否已留下東西；A3 在串流開始時即建立檢視紀錄）；persisting → 「可能已存回架構圖〈名稱〉」
      （存檔請求已送出、無法取消，見 BR55.7）；result_persisted → 說明文字（architecture-design
      為「已存回架構圖〈名稱〉」，well-architected-review 為「已建立一份檢視紀錄」）。
      cost-finops 只讀取，不建立任何東西，恆為 none。
    violation_behaviour: 不適用
    source: "AC1.3.1；K-11 sideEffect；review-01 R-10"

  - id: BR55.2
    statement: "對終態工作項更正為 no-op，回傳現況"
    category: policy
    applies_to: WorkOrchestrator.correct
    trigger: 目標工作項已是完成、失敗或已停掉
    logic: "不改任何欄位、不推送。"
    violation_behaviour: 不適用
    source: "K-11 retry_and_idempotency（correct 冪等）"

  - id: BR55.3
    statement: "停掉之後，尚未開始的副作用步驟一律不執行：不存回架構圖、不寫記憶、不送卡片、不送完成訊息"
    category: constraint
    applies_to: 已停掉的工作項
    trigger: 背景執行走到下一個副作用步驟
    logic: >
      每一步副作用都以 BR52.7 的比對後寫入推進（預期狀態=處理中、預期 dispatchStage=上一步寫入的值）；比對失敗即中止整條背景執行。
      已送出、無法取消的請求（A1 產圖、A3 檢視、PUT 存檔）不在本規則保證範圍內，由 BR55.1 的
      sideEffect 如實揭露。
    violation_behaviour: 不適用
    source: "AC1.3.1；review-01 R-10"

  - id: BR55.4
    statement: "更正只改變被指定的那一項；等它的工作項依 BR53.4 處置"
    category: policy
    applies_to: WorkOrchestrator.correct
    trigger: 更正成功
    logic: "不等它的工作項完全不受影響；等它的工作項依 BR53.4：成本項開始執行（等待中→處理中），檢視項不執行（等待中→已停掉）。"
    violation_behaviour: 不適用
    source: "AC1.3.2；AC5.1.3；[RA:FR1.4]；review-01 R-08"

  - id: BR55.5
    statement: "停掉後送一則固定訊息請使用者再說一次要做什麼；下一句重新判讀後建立新工作項"
    category: policy
    applies_to: WorkOrchestrator.correct
    trigger: 更正成功
    logic: "訊息：「已停掉〈label〉。請再說一次你要做什麼。」以伺服器輪次送出（BR58.5）；被停掉的工作項保留在集合中。"
    violation_behaviour: 不適用
    source: "[WO4]=A；AC1.3.3（新舊兩項同時可見）"

  - id: BR55.6
    statement: "找不到指定的工作項時拋 WorkItemNotFound，不改任何東西"
    category: validation
    applies_to: WorkOrchestrator.correct
    trigger: workItemId 不在該工作階段
    logic: "以 session_key 為範圍查找；不跨工作階段。"
    violation_behaviour: "raise WorkItemNotFound"
    source: "K-11 correct raises"

  - id: BR55.7
    statement: "停掉時已在途的存檔請求若成功，視為已存回：寫變更紀錄並更新 sideEffect，但不改回狀態"
    category: policy
    applies_to: architecture-design 工作項
    trigger: dispatchStage=persisting 時被停掉，之後 PUT 回 2xx
    logic: >
      圖確實已被改寫，稽核必須如實：依 BR51.4 寫變更紀錄；以比對後寫入（預期狀態=已停掉、預期 dispatchStage=persisting）只把
      sideEffect 改為「已存回架構圖〈名稱〉」、dispatchStage 改為 result_persisted；status 維持
      已停掉；不寫記憶、不送完成訊息。PUT 失敗則 sideEffect 改為 none。
    violation_behaviour: 不適用
    source: "review-01 R-10（PUT 在 threadpool 內，無法取消）"

  # ---- BR56：能力執行 ----------------------------------------------------
  - id: BR56.1
    statement: "架構設計：決定目標圖、讀圖、交給 A1 產圖、比對未被他人修改後存回、寫變更紀錄"
    category: policy
    applies_to: architecture-design 工作項
    trigger: 工作項進入處理中
    logic: >
      目標圖：作業對象已指定圖則用它；只指定系統時經 HierarchyFacade.list_diagrams_of_system
      （U7 新增的唯讀方法）取該系統下使用者擁有的圖，恰有一張則用它；零張 → 失敗「這個系統下
      沒有掛上的架構圖，請在脈絡列選定圖」；多張 → 失敗「這個系統下有多張架構圖，請在脈絡列選定
      要用的那一張」；作業對象為空或只有專案 → 失敗「請先在脈絡列選定架構圖或系統」。步驟：GET 目標圖（取 title、xml_data、updated_at）→
      POST A1（messages=[{role:user, content:requestText}], current_xml；dispatchStage=request_sent）→
      依 BR56.5 判定 → 再 GET 一次比對 updated_at，不同即失敗「這張圖在處理期間被修改過，未覆寫」→
      dispatchStage=persisting → PUT（xml_data=A1 的最後一份 xml，title=GET 取得的 title）→
      dispatchStage=result_persisted → BR51.4 → 完成。
    violation_behaviour: "任一步失敗即失敗，原因為該步的固定句型；不重試"
    source: "[WO6]=A；AC1.1.4；X-02；review-01 R-01、R-06"

  - id: BR56.2
    statement: "架構檢視：以目標圖的 diagram_id 呼叫 A3 建立檢視，完成時送出整體分數與發現數"
    category: policy
    applies_to: well-architected-review 工作項
    trigger: 工作項進入處理中
    logic: >
      目標圖的決定同 BR56.1。POST /api/architecture/reviews（diagram_id、save_diagram=false；
      dispatchStage=request_sent）→ 依 BR56.5 判定 → complete 事件 → dispatchStage=result_persisted
      → 完成，送出「檢視完成：整體分數〈overall_score〉，〈len(findings)〉項發現」。
    violation_behaviour: "失敗即失敗，不重試"
    source: "X-02；review_router.py 的 StartReviewBody；review-01 R-05"

  - id: BR56.3
    statement: "成本分析：取目標圖對應的、使用者看得到的最新一份估價表；沒有就失敗並附成本頁連結"
    category: policy
    applies_to: cost-finops 工作項
    trigger: 工作項進入處理中
    logic: >
      目標圖集合：作業對象已指定圖則為該圖；只指定系統則為 list_diagrams_of_system 的結果（可多張）。
      分頁讀 GET /api/cost/v1/sets（page_size 取上限，結果依建立時間新到舊），找第一份 diagram_id
      在目標圖集合內者即為最新一份，找到即停止翻頁；diagram_id 為空的估價表一律不採用。立即寫入
      estimateSetId。作業對象為空或只有專案 → 失敗「請先在脈絡列選定架構圖或系統」；只指定系統而
      目標圖集合為空 → 失敗「這個系統下沒有掛上的架構圖，請在脈絡列選定圖」；集合非空但翻完找不到
      → 失敗「這張圖尚無估價表，可到成本頁上傳」並附成本頁路徑；
      該份 advice_status 為 none → 失敗「這份估價表還沒有產生建議，可到成本頁產生」並附路徑。
      其後依 BR57 輪詢。
    violation_behaviour: 不適用
    source: "[WO5]=A；X-01 x-invariant-this-contract-adds；AC10.1.1；review-01 R-01"

  - id: BR56.4
    statement: "不自動重試任何對既有能力的呼叫"
    category: constraint
    applies_to: 三種能力
    trigger: 呼叫失敗
    logic: "失敗即工作項失敗；使用者要重試就再說一次。輪詢的連續讀取依 BR57.2，不算重試。"
    violation_behaviour: 不適用
    source: "X-01／X-02 retry_and_idempotency"

  - id: BR56.5
    statement: "A1 與 A3 的 SSE 回應在收齊後依事件判定結果，HTTP 200 不等於成功"
    category: calculation
    applies_to: architecture-design、well-architected-review
    trigger: 回應結束
    logic: >
      A1（message／progress／xml／error）：任一 error → 失敗「架構設計失敗」；有 xml → 取最後一份；
      無 xml → 失敗「架構設計沒有產出圖」，並把 message 文字照轉（使用者看得到模型的提問或拒絕原因）。
      A3（rules_done／lens_done／suggestion_delta／complete／error）：任一 error → 失敗「架構檢視失敗」；
      有 complete → 成功，摘要取 complete 的 overall_score 與 findings；結束時沒有 complete → 失敗
      「架構檢視沒有完成」。非 2xx 依 BR51.3／BR51.6 或失敗「〈能力名稱〉暫時無法使用」。
    violation_behaviour: 不適用
    source: "review-01 R-05；design_agent 的 message／xml／error 事件；review_orchestrator 的 complete／error 事件"

  - id: BR56.6
    statement: "每個處理中的工作項有牆鐘上限，逾時轉為失敗"
    category: constraint
    applies_to: 三種能力
    trigger: 工作項進入處理中
    logic: >
      進入處理中時寫入 deadlineAt：architecture-design 300 秒、well-architected-review 300 秒、
      cost-finops 360 秒（長於 C1 自己的 5 分鐘逾時）。背景執行以 asyncio.wait_for 包住；
      逾時 → 失敗「〈能力名稱〉逾時」，sideEffect 依 BR55.1 的同一張對照表（request_sent → unknown）。
    violation_behaviour: 不適用
    source: "review-01 R-03(1)；advice_orchestrator.TIMEOUT=5 分鐘"

  - id: BR56.7
    statement: "讀取工作項時補做兩種復原：處理中且已過 deadlineAt 的轉為失敗；等待中而被等待者已是終態的補做推進"
    category: policy
    applies_to: list_items、dispatch、correct、U13 重連時的讀取
    trigger: 讀取工作項集合
    logic: >
      背景 task 只存在行程記憶體，重啟後不存在；以 Redis 的儲存值判定而非「本行程有沒有 task」，
      多 worker 下也成立。兩個步驟依序執行：
      (1) 逾期：處理中且 deadlineAt 已過者，以比對後寫入轉為失敗「服務重新啟動或逾時，這一項沒有完成」，
      sideEffect：dispatchStage 為 not_dispatched → none，其他 → unknown。
      (2) 孤兒等待：等待中且 dependsOn 指向的工作項已是終態者（含 (1) 剛轉成失敗的），依被等待者的
      終態套用 BR53.2（完成）／BR53.3（失敗）／BR53.4（已停掉）。這涵蓋「被等待者的終態已寫入、
      推進等待者之前行程重啟或 Redis 暫時不可用」的情況。dependsOn 指向的工作項不存在時視同失敗。
      推進為處理中者寫入 deadlineAt，並由本行程啟動背景執行。
    violation_behaviour: 不適用
    source: "review-01 R-03(2)；review-02 R-03"

  - id: BR56.8
    statement: "sink 送出失敗只記 log，不改變工作項、不讓背景執行拋出未處理例外"
    category: policy
    applies_to: 所有 sink 呼叫
    trigger: sink 拋例外（連線已斷等）
    logic: "捕捉後記 warning log（不含訊息內容），背景執行照常走完；狀態以 Redis 為準，重連時由 work_items 取回。"
    violation_behaviour: 不適用
    source: "review-01 R-03(3)"

  # ---- BR57：成本建議的輪詢與轉譯 ----------------------------------------
  - id: BR57.1
    statement: "以輪詢建議快照取得結果，生成中不新增訊息、不推送"
    category: policy
    applies_to: cost-finops 工作項
    trigger: BR56.3 取得估價表之後
    logic: >
      每 2 秒 GET /api/cost/v1/sets/{set_id}/advice。status=generating → 不改狀態、不推送、不送訊息；
      使用者看到的是同一張處理中的工作項標示（就地維持，不新增訊息）。不使用 /advice/stream：
      ASGI 傳輸把它收齊才交回，中途的 progress／heartbeat 事件收不到，等同一次較慢的快照讀取，且
      WorkItem 沒有進度文字欄位可承載中途事件（OPEN-WO12-5）。
    violation_behaviour: 不適用
    source: "AC10.1.2；review-01 R-02；review-02 R-14"

  - id: BR57.2
    statement: "單次輪詢讀取失敗（401／403 以外）連續 3 次即失敗"
    category: policy
    applies_to: cost-finops 工作項
    trigger: 輪詢回 5xx、404 以外的非 2xx 或傳輸例外
    logic: "連續 3 次 → 失敗「與成本服務的連線中斷」；中間任一次成功即歸零。404 依 BR57.4。"
    violation_behaviour: 不適用
    source: "X-01 stream_read 唯讀冪等"

  - id: BR57.3
    statement: "status=completed：工作項完成，並送出成本卡片，卡片的 estimateSetId 取自工作項"
    category: calculation
    applies_to: cost-finops 工作項
    trigger: 快照 status=completed
    logic: "以快照的 saving_text／comparison_text／quality_text／unavailable_reasons 填 cost_card，estimateSetId 取工作項欄位，costPageUrl 由 estimateSetId 組出；以伺服器輪次送出（BR58.5）。"
    violation_behaviour: 不適用
    source: "AC10.1.3；X-01 x-completed-payload"

  - id: BR57.4
    statement: "逾時與失敗各自轉為失敗，原因的句型不同，使用者分得出來"
    category: calculation
    applies_to: cost-finops 工作項
    trigger: 快照 status=failed、404、generating 且 started_at 已逾 5 分鐘，或 BR56.6 逾時
    logic: >
      failed 且 unavailable_reasons.timed_out 為真 →「成本分析逾時」；failed 其他 →「成本分析失敗」；
      generating 且快照的 started_at 距今已超過 C1 的 5 分鐘逾時 → 立即「成本分析逾時」（快照端點
      不回收過期的 generating 列，只有串流端點會；不等本單元的 360 秒）；
      BR56.6 逾時（快照停在 generating）→「成本分析逾時」；404（建議列已被刪除或估價表不再可見）→
      「找不到這份估價表的建議」。
    violation_behaviour: 不適用
    source: "AC10.2.1；AC10.2.2；advice_stream_router 以 timed_out 區分 timeout／failed；review-02 R-14（estimate_intake_service.get_advice_snapshot 不呼叫 reclaim_stale_generating）"

  - id: BR57.5
    statement: "成本項的等待只是排序：改圖不會讓既有估價表重算"
    category: policy
    applies_to: 等待架構設計的 cost-finops 工作項
    trigger: BR53.2 解除等待
    logic: >
      成本分析讀的是既有估價表與其已完成的建議（[WO5]=A），架構設計完成與否不改變結果。
      完成訊息不得暗示成本已依新圖重算。
    violation_behaviour: 不適用
    source: "review-01 R-13；[WO2]=A 與 [WO5]=A 的交互"

  # ---- BR58：回覆訊息（[WO1]=A）------------------------------------------
  - id: BR58.1
    statement: "編排層的回覆一律為固定句型，不呼叫任何 LLM"
    category: policy
    applies_to: WorkOrchestrator 產生的訊息
    trigger: 工作項建立、轉為等待／完成／失敗／已停掉
    logic: >
      建立：「已交給〈能力名稱〉處理〈作業對象〉」；等待：「〈label〉會在〈被等待的 label〉完成後開始」；
      完成：「〈label〉完成」（成本項附 BR57.5 的限定）；失敗：「〈label〉沒有完成：〈failureReason〉」；
      停掉：BR55.5。
    violation_behaviour: 不適用
    source: "[WO1]=A；[RA:FR8.1]"

  - id: BR58.2
    statement: "交辦後立即送出建立訊息，不等任何能力完成；建立訊息屬於使用者本輪"
    category: policy
    applies_to: WorkOrchestrator.dispatch
    trigger: 工作項建立完成
    logic: "建立與等待訊息以本輪 turnId 經 sink 送出，在 dispatch 回傳之前、在呼叫既有能力之前；U13 之後送本輪的 done。"
    violation_behaviour: 不適用
    source: "AC10.2.3；[RA:FR10.4]；review-01 R-04"

  - id: BR58.3
    statement: "A1 回傳的說明文字在回應結束後一次轉送；成本不轉送任何生成中文字"
    category: policy
    applies_to: architecture-design 與 cost-finops
    trigger: A1 回應結束
    logic: "A1 的 message 文字依序串接，非空白才以一則伺服器輪次送出（BR58.5）；ASGI 傳輸收齊才交回，故不是逐段。C1 只有 BR57 的結果。"
    violation_behaviour: 不適用
    source: "[RA:FR8.1]；X-01 x-streaming-rule；review-01 R-02"

  - id: BR58.4
    statement: "送給使用者的訊息不含例外原文、內部錯誤或 token"
    category: policy
    applies_to: 所有回覆
    trigger: 任何錯誤
    logic: "失敗原因一律取固定句型；例外細節只記在 log（且 log 不含 token 與需求全文）。"
    violation_behaviour: 不適用
    source: "ADR-0006；U22 查出的「例外原文送進 SSE」同類缺陷"

  - id: BR58.5
    statement: "dispatch 回傳之後產生的輪次訊息（token、cost_card）一律放在伺服器發起的新輪次內"
    category: constraint
    applies_to: 背景執行與 correct 送出的訊息
    trigger: 要送 token 或 cost_card 時
    logic: >
      輪次訊息的 turnId 必為非 null 且以 done／error 終止（brain_ws_contract 的 BR1.5／BR1.6）。
      本單元呼叫 sink.emit_turn([訊息…])；U13 為它產生新的 turnId、依序送出、最後送 done。
      非輪次訊息（work_items）經 sink.emit_session 送出，turnId 為 null。本單元不自行產生 turnId。
    violation_behaviour: 不適用
    source: "review-01 R-04；brain_ws_contract._TURN_SCOPED_TYPES"
```

## 三、規則摘要

| 群 | 規則 | 一句話 |
|---|---|---|
| 授權與呼叫 | `BR51.1`–`BR51.8` | 同進程 HTTP 帶使用者 token、token 不落地、403 與 401 分開說；寫變更紀錄與 procedure 記憶；facade 呼叫各開 DB session 並離開事件迴圈 |
| 建立與存放 | `BR52.1`–`BR52.7` | 一個意圖一個工作項；固定句型的 label；逐項欄位存在大腦工作階段；比對 status 與 dispatchStage 後寫入；原句與段由 U13 傳入 |
| 等待中 | `BR53.1`–`BR53.4` | 成本或檢視排在架構設計後就等；前一項失敗就失敗；前一項被停掉時成本照常開始、檢視不執行 |
| 狀態機 | `BR54.1` | 六種合法轉換，三個終態 |
| 逐項更正 | `BR55.1`–`BR55.7` | 依送出進度判斷有沒有留下東西；未開始的步驟不做；只改該項；請使用者再說一次；在途存檔如實記錄 |
| 能力執行 | `BR56.1`–`BR56.8` | 目標圖解析與存回前比對；檢視；成本取最新估價表；SSE 收齊後判定；牆鐘上限；逾期與孤兒等待的復原；sink 失敗不擴散 |
| 成本轉譯 | `BR57.1`–`BR57.5` | 輪詢快照、連續失敗才算斷線、完成出卡片、逾時與失敗可分辨、等待只是排序 |
| 回覆 | `BR58.1`–`BR58.5` | 固定句型不呼叫 LLM、先回覆後執行、A1 文字收齊後轉送、不洩內部錯誤、背景訊息開伺服器輪次 |
