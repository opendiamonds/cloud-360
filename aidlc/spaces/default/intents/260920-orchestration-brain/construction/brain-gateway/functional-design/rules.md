# Rules — `U13 brain-gateway`

## 一、識別字區段：`BR61.x`–`BR67.x`

已佔用：`BR1`–`BR8`（11 個單元）、`BR21`–`BR28`（`U24`）、`BR31`–`BR35`（`U15`）、`BR41`–`BR47`（`U20`）、
`BR51`–`BR58`（`U12`）。本單元取 **`BR61`–`BR67`**。引用他單元的規則一律寫成「`U<n>` 的規則 x.y」，不寫出他單元
識別字的字面形式。

四題定案（修訂 2 未新增題目）：`[GW1]`=A（子協定 `cloud360.brain.v1` ＋ `bearer.<jwt>`，伺服器只回送前者）、`[GW2]`=A（先送終止事件，
episodic 記憶背景寫入，失敗只記 WARNING）、`[GW3]`=A（握手期 Redis 不可用 → 1011；握手結束後 → 該輪
`error(INTERNAL_ERROR)`、連線保留）、`[GW4]`=A（`user_message` 增加 `page` 欄位）。出處：`functional-design-questions.md`。

> **修訂 1（2026-10-12，依 `reviews/review-01.md` 的 R-01～R-12）**：新增 `BR62.6`、`BR64.11`、`BR65.5`、`BR67.10`、
> `BR67.11`（規則數 44 → 49）；改寫 `BR61.5`、`BR61.7`、`BR62.1`、`BR62.5`、`BR63.2`、`BR63.3`、`BR64.6`、`BR64.9`、
> `BR65.2`、`BR65.3`、`BR66.1`、`BR66.2`、`BR67.2`、`BR67.5`、`BR67.6`、`BR67.8`；並把引用他單元規則的寫法統一為
> 「`U<n>` 的規則 x.y」。逐項對應見 `functional-spec.md` §十二。依賴契約增量的規則一律引用 `functional-spec.md` §十一。
>
> **修訂 2（2026-10-12T22:45Z，依 `reviews/review-02.md` 的 R-01～R-07）**：新增 `BR63.6`、`BR64.12`、`BR64.13`、`BR67.12`
> （規則數 49 → 53）；改寫 `BR61.7`、`BR63.1`、`BR63.2`、`BR64.6`、`BR64.8`、`BR64.9`、`BR64.10`、`BR64.11`、`BR67.5`、
> `BR67.7`、`BR67.10`、`BR67.11`。逐項對應見 `functional-spec.md` §十三。

## 二、規則（source of truth）

```yaml
rules:
  # ---- BR61：握手與認證 -------------------------------------------------------
  - id: BR61.1
    statement: "大腦唯一的 WebSocket 端點為 /api/brain/ws，掛在 /api/ 之下；DEMO 檔整支移除"
    category: constraint
    applies_to: 路由掛載
    trigger: 部署
    logic: >
      新模組以 APIRouter 的 websocket("/ws") 宣告，由 main.py 以 prefix="/api/brain" 掛載。
      刪除 backend/services/brain_router.py，移除 main.py:7 的 import 與 main.py:110-112 的 DEMO 註解與
      include_router（DEMO 檔 :27 逐字「整支取代本檔」）。
    violation_behaviour: "掛在 /api/ 以外 → nginx 的 location / 走 try_files 回 HTML，握手失敗；保留 DEMO → 同一路徑兩個 handler"
    source: "K-12 x-hard-constraints.path_prefix（contract-summary.md:873-876）；[RA:FR8.3]；brain_router.py:27"

  - id: BR61.2
    statement: "子協定標頭以純函式解析：逗號切分、去空白、逐字比對 cloud360.brain.v1；bearer 項以第一個點切分"
    category: validation
    applies_to: parse_subprotocol_offer（純函式）
    trigger: 收到 HTTP Upgrade
    logic: >
      offered = header 依 "," 切分並 strip。hasProtocolName = "cloud360.brain.v1" ∈ offered（逐字、區分大小寫）。
      bearerToken = 第一個以 "bearer." 開頭的項目 .split(".", 1)[1]；結果為空字串時視為不存在。
      不得以 split(".") 取兩段（JWT 本身含兩個點）。本函式不讀 query string、不做 I/O。
      協定名 cloud360.brain.v1 為契約增量 C-1（functional-spec.md §十一）。
    violation_behaviour: "split('.') 會在任何真實 JWT 上取錯段，握手全部 4401"
    source: "brain_ws_contract.py:410-433（WsSubprotocol 與其實作陷阱）；[GW1]=A"

  - id: BR61.3
    statement: "客戶端未提供 cloud360.brain.v1 時，不 accept、直接拒絕升級"
    category: validation
    applies_to: 握手
    trigger: hasProtocolName == false
    logic: >
      呼叫 websocket.close() 於 accept 之前（Starlette 回 HTTP 403，瀏覽器端為連線失敗）。
      理由：瀏覽器規定伺服器回送的子協定必須是客戶端提供的其中之一，而 BR61.4 禁止回送 bearer 項，
      故此時沒有任何合法的 accept 形狀。此情形只會由客戶端程式錯誤或舊客戶端造成，不需要可讀的關閉碼。
    violation_behaviour: "改為回送 bearer.<jwt> 以求相容 → 違反 [GW1]=A，token 進回應標頭"
    source: "[GW1]=A；functional-design-questions.md GW1 題幹"

  - id: BR61.4
    statement: "認證與 K1 判定在 accept 之前完成；accept 一律只回送 cloud360.brain.v1，絕不回送 bearer 項"
    category: authorization
    applies_to: 握手
    trigger: hasProtocolName == true
    logic: >
      accept 之前（pre-accept）只做三件事：BR61.2 的解析、以 asyncio.to_thread 在**同一個** DB session 內完成
      get_user_from_token(token, db, record=True) ＋ rbac.user_can(db, user.role, "K1", "view",
      authorization_status=user.authorization_status) ＋ mint_principal(user)（session 關閉前鑄造，見 BR62.1）。
      三者皆通過才 accept(subprotocol="cloud360.brain.v1")。
      **最小 pre-accept／post-accept 暴露面**：pre-accept 階段伺服器不讀任何訊息訊框、不寫任何 session 狀態；
      需要送出 4401／4403／1011 時，accept 之後**立即** close，中間不送任何訊息、不讀任何訊框——
      未通過認證的客戶端最多取得一個「已升級、隨即收到關閉訊框」的連線，從未取得可讀寫的通道。
      必須 accept 才能送關閉碼，是因為 accept 之前的 close 只會變成 HTTP 403，客戶端看不到 4401／4403。
    violation_behaviour: "先 accept 再認證 → US8 DoD 第 3 點點名的 pre-accept 暴露面；回送 bearer 項 → token 進回應標頭，比請求標頭更常被代理與開發工具記錄"
    source: "[GW1]=A；K-12 x-authorization-responsibility.handshake（contract-summary.md:993-995）；stories.md US8 DoD 第 3 點"

  - id: BR61.5
    statement: "帶協定名但缺 bearer 項、token 無效或過期、帳號不存在或已停用 → accept 後以 4401 關閉；query string 一律不讀"
    category: authorization
    applies_to: 握手
    trigger: BR61.4 認證失敗（前提：hasProtocolName == true）
    logic: >
      bearerToken 不存在、或 get_user_from_token 拋 HTTPException（401 與 403「已停用」兩種）→ 4401。
      本端點**從不讀取** websocket.query_params，token 只放在 query string 的握手因此**一定被拒**，但拒絕形狀有兩種，
      測試必須分別斷言：(a) 帶 cloud360.brain.v1、token 只在 query string → 無 bearer 項 → accept 後 4401；
      (b) 不帶 cloud360.brain.v1（舊 DEMO 形狀）→ 依 BR61.3 未 accept 即拒絕（HTTP 403）。
    violation_behaviour: "讀 query string 的 token（collab_router.py:270 的既有前例）→ token 進 nginx 與 cloudflared 的 access log"
    source: "K-12 x-hard-constraints.token_transport（contract-summary.md:877-881）；K-12 verification（:1013-1014）；x-close-codes 4401（:989）；[RA:FR8.5]；AC8.1.3；review-01 R-11"

  - id: BR61.6
    statement: "已認證但無 K1.view（含帳號未核准）→ accept 後以 4403 關閉"
    category: authorization
    applies_to: 握手
    trigger: user_can(..., "K1", "view", ...) 為 false
    logic: "未核准帳號由 user_can 的 authorization_status 分支回 false（rbac.py:151-153），一併走 4403"
    violation_behaviour: "放行 → 無大腦權限的角色取得大腦通道"
    source: "K-12 x-close-codes 4403（contract-summary.md:990）；x-authorization-responsibility.handshake"

  - id: BR61.7
    statement: "握手結束之前的伺服器內部錯誤（含 SessionBackendUnavailable）→ accept 後以 1011 關閉；握手在 ready 送出時結束"
    category: error_handling
    applies_to: 自升級請求到送出 ready 為止（含 hello 之後的 load 與 list_items）
    trigger: 認證、閘道元件取得、load 或 list_items 拋出 BR61.5／BR61.6 以外的例外
    logic: >
      **握手結束的時點定義為送出 ready 的那一刻**。順序為 hello 驗證 → load → list_items → ready → 狀態推送
      （functional-spec.md GW-W1；連線在 hello 驗證通過時即以 loading 登錄，BR63.1）。故 load 與 list_items 位於 ready **之前**，其失敗（含 SessionBackendUnavailable，
      [GW3]=A 前半）一律 1011，並先自登錄移除、丟棄暫存佇列。ready 之後的失敗一律依 BR67.2。log 只記例外類別名稱（BR67.3）。
    violation_behaviour: "回空 session 繼續服務 → 違反 U10 的「不降級」（session-store reliability-requirements.md:64）；分界不明 → 同一個 load 失敗在測試裡無法決定期望 1011 還是 error"
    source: "[GW3]=A；K-12 x-close-codes 1011（contract-summary.md:992）；review-01 R-05"

  - id: BR61.8
    statement: "accept 之後首則訊息必須是 hello 且 v == 1；相容則進入載入，否則以 4400 關閉並帶 expected 與 received"
    category: validation
    applies_to: 版本協商
    trigger: accept 之後收到第一個訊框，或 10 秒內未收到任何訊框
    logic: >
      以 WsUnvalidatedEnvelope 解析原始 dict 取 v 與 type（brain_ws_contract.py:725-748）。
      type == "hello" 且 v == 1 且 WsClientEnvelope.model_validate(原始 dict) 通過 → 進入 BR61.7 的載入，載入成功才送
      ready{protocolVersion: 1}（turnId null）。其餘（非 JSON、type 不是 hello、v 不等於 1、10 秒逾時）→ close(4400,
      reason="expected=1 received=<整數或 invalid>")。received 只取整數，不回放客戶端任意字串。
      10 秒為本站選定，非上游數值（見 functional-spec.md Assumptions）。
    violation_behaviour: "不設逾時 → 已認證連線可無限期停在 awaiting_hello，不在登錄中也收不到狀態"
    source: "K-12 x-handshake.step_2／step_3（contract-summary.md:949-950）；x-close-codes 4400（:991）"

  # ---- BR62：身分、工作階段與段 ------------------------------------------------
  - id: BR62.1
    statement: "身分只來自連線；每則客戶端訊息（hello 除外）在同一個 DB session 內重新驗證 token、判定 K1 並鑄造 principal"
    category: authorization
    applies_to: 每則客戶端訊息
    trigger: ready 之後收到客戶端訊息
    logic: >
      以一次 to_thread 開一個 DB session，依序 get_user_from_token(token, db, record=True)、user_can(K1, view)、
      mint_principal(user)，再關閉 session。**principal 必須在 session 關閉前鑄造**：record_activity 會 commit
      （activity.py:96），sessionmaker 預設 expire_on_commit（database.py:38），session 關閉後再讀 user 的屬性會
      DetachedInstanceError；mint_principal 回傳的 Principal 是只含 user_id／role／is_approved 的不可變值，關閉後可安全使用。
      結果三分：
        (a) HTTPException 401（token 無效或**已過期**，JWT 預設 8 小時，auth.py:33）或 403（停用）→ close(4401)，
            reason "credentials-expired-or-invalid"；客戶端應重新登入或以新 token 重連（使用者可見行為，見 functional-spec.md §八）；
        (b) K1 判定為假 → close(4403)；
        (c) 其他例外（DB 暫時不可用等）→ **不關閉**，本則訊息不處理，以新 turnId 送 error(INTERNAL_ERROR)，連線保留。
      客戶端訊息內不得有任何身分欄位（WsClientEnvelope extra="forbid"）。
      record=True 逐則呼叫使長時間連線的 users.last_activity_at 持續更新（節流 5 分鐘由既有 record_activity 承擔）。
      **撤權或停用的生效時點**：有訊息往來的連線在下一則訊息生效；閒置連線由 BR62.6 在至多 60 秒內生效。
    violation_behaviour: "只在握手驗一次 → 連線期間被停用或撤權的帳號仍可交辦；session 關閉後才鑄造 → DetachedInstanceError 使每則訊息都失敗；DB 抖動時關閉 → 使用者被錯誤地踢回登入"
    source: "K-12 per_connection_principal（contract-summary.md:996-997）；K-16 identity_passing（:1641-1645）；[RA:FR8.4]；AC8.1.2；review-01 R-07"

  - id: BR62.2
    statement: "使用者 token 只存在連線物件的記憶體內"
    category: policy
    applies_to: Connection.bearerToken、SubprotocolOffer.bearerToken
    trigger: 任何時刻
    logic: "不寫入 session、工作項、記憶、log、關閉原因、錯誤訊息。唯一的傳出點是 U12 三個方法的 bearer_token 參數"
    violation_behaviour: "token 外洩到任何持久或可讀的位置"
    source: "work-orchestrator code-summary.md §七第 1 點；ADR-0006 IAM"

  - id: BR62.3
    statement: "session key 由純函式 session_key_for(user_id) 推導；本單元不寫 meta.userId"
    category: calculation
    applies_to: session_key_for／user_id_from_session_key（純函式）
    trigger: 握手認證成功
    logic: >
      session_key_for(u) = "brain:session:" + str(u)，u 為正整數；user_id_from_session_key 為其反函數，
      格式不符即拋 ValueError。U10 的 K-09 介面沒有寫 meta.userId 的方法（session_store.py:514-543 的
      _ensure_meta 以 null 建立），本單元在不改 K-09 的前提下**不寫它**；需要歸屬人的讀取端以
      user_id_from_session_key 推導（目前全樹無讀取端，見 functional-spec.md §六 F-12）。
    violation_behaviour: "兩個使用者推導出同一鍵 → 互相看到對方的作業對象與歷程"
    source: "K-12 x-session-key-derivation（contract-summary.md:886-889）；session-store code-summary.md:150 第 3 項"

  - id: BR62.4
    statement: "W1：載入 session；不存在時以預設狀態回應，不寫入"
    category: policy
    applies_to: 連線建立
    trigger: hello 驗證通過之後、ready 之前
    logic: >
      to_thread 呼叫 SessionStore.load(session_key)。回 None 時視為預設狀態（只有 shared 段、兩頁 shared、
      作業對象三層 null）並據以推送，**不呼叫任何寫入方法**——K-09 沒有 create，第一次寫入時 U10 自行建立
      （_ensure_meta）。
    violation_behaviour: "為了建立而呼叫寫入方法 → 只開頁面不互動也會產生 session 並續期"
    source: "session-store functional-spec.md W1 第 3–5 步；U10 的規則 1.6"

  - id: BR62.5
    statement: "訊息所屬的段由純函式 resolve_segment(page, page_modes) 決定"
    category: calculation
    applies_to: resolve_segment（純函式）
    trigger: 處理 user_message
    logic: >
      page == "entry" → "shared"；page ∈ {workspace, assessment} → page_modes[page] == "isolated" ? page : "shared"。
      page 取自 user_message 的 page 欄位——契約增量 C-2（functional-spec.md §十一，[GW4]=A）；缺欄位即
      INVALID_REQUEST（不預設為 entry）。**實作狀態：在 C-2 合入契約之前為 blocked。**
    violation_behaviour: "一律寫 shared 或缺欄位時預設 entry → 獨立對話的訊息靜默混進共享歷程，[RA:FR3.2] 被違反"
    source: "session-store functional-spec.md W2 第 2 步（明列為 U13 的動作）；session_types.py:54-65；[GW4]=A"

  - id: BR62.6
    statement: "就緒的連線每 60 秒在背景重新驗證一次 token、帳號狀態與 K1；不通過即關閉"
    category: authorization
    applies_to: 閒置或只收推播的連線
    trigger: 連線進入就緒後每 60 秒
    logic: >
      與 BR62.1 同一個 to_thread 程序，但 record=False（閒置不是互動，不得更新最後活動時間）。結果：
      401／403 → close(4401)；K1 為假 → close(4403)；其他例外 → 記 WARNING，下一個週期重試，不關閉。
      關閉前自登錄移除，故撤權或停用後的推播外洩窗至多 60 秒。週期為本站選值。
    violation_behaviour: "不重驗 → 被停用的帳號只要不送訊息，就能無限期持續收到推播與狀態訊息"
    source: "review-01 R-07；ADR-0006 IAM"

  # ---- BR63：連線登錄與扇出 -----------------------------------------------------
  - id: BR63.1
    statement: "連線登錄在行程內，以 session key 為鍵；hello 驗證通過即登錄（載入中），本單元假設單一後端行程"
    category: constraint
    applies_to: ConnectionRegistry
    trigger: hello 驗證通過／連線關閉
    logic: >
      hello 驗證通過、**讀取 session 之前**即以 phase=loading 登錄；載入失敗（1011）或關閉時移除，集合為空即刪鍵。
      登錄早於讀取，是為了讓讀取期間發生的狀態改變一定會扇出到本連線（BR63.6 先暫存、ready 後依序送出）——
      若先讀後登錄，讀取與登錄之間的扇出會漏掉本連線，客戶端停在舊快照直到下一次狀態改變。
      本單元不偵測多行程；假設的依據是 backend/Dockerfile:30 的 uvicorn 指令無 --workers（K-12 引用為 :37，
      實為 :30，見 functional-spec.md §六 F-10）。
    violation_behaviour: "先讀後登錄 → 握手期的狀態改變漏送；多行程時跨連線扇出靜默失效，[RA:NFR2] 默默降級"
    source: "K-12 fanout_mechanism_and_its_assumption（contract-summary.md:932-943）；review-02 R-03"

  - id: BR63.2
    statement: "新連線 ready 之後只對它推送當前狀態快照，再依序送出載入期間暫存的訊息"
    category: policy
    applies_to: 連線建立（含重連）
    trigger: 送出 ready
    logic: >
      以 BR62.4 載入的 session 與 BR61.7 取得的 list_items 結果，依序送 sharing_mode（workspace、assessment 各一則，
      帶 scope，契約增量 C-3）、work_target（每個存在段各一則，帶 segment，契約增量 C-4）、work_items（三者 turnId 皆為
      null），**之後**才依 BR63.6 送出暫存佇列，最後把 phase 改為 ready。
      **排序保證**：三種狀態訊息都是整份狀態（每個 scope、每個段、整個工作項集合各一份完整值），而暫存佇列中的每一則
      都晚於登錄、依產生順序送出，故每一類狀態「最後收到的那一則」必為最新狀態；快照可能暫時比佇列中較舊的一則新，
      但佇列最後一則會把它收斂到最新。
      **實作狀態：sharing_mode 與 work_target 兩則在 C-3／C-4 合入之前為 blocked**（functional-spec.md §十一）。
    violation_behaviour: "不推送 → 重連或新開分頁時脈絡列空白；先送佇列再送快照 → 較新的扇出被較舊的快照蓋掉"
    source: "K-12 on_connect（contract-summary.md:930-931）；session-store functional-spec.md W1 第 6 步（逐鍵／逐段）；OPEN-WO12-3；review-02 R-03"

  - id: BR63.3
    statement: "sharing_mode、work_target、work_items 三種狀態訊息在狀態改變時推給該 key 的全部存活連線"
    category: policy
    applies_to: 狀態訊息
    trigger: set_sharing_mode／set_work_target 成功、referent 解析成功，或 U12 經 sink.emit_session 送出
    logic: >
      對 registry[session_key] 的每一條連線送出；客戶端依 scope／segment（契約增量 C-3／C-4，functional-spec.md §十一）
      自行過濾。不只送給觸發的那一條。
    violation_behaviour: "只送觸發的連線 → 同一作業對象跨三頁不一致（[RA:FR2.2]）"
    source: "K-12 state_change_fanout（contract-summary.md:921-924）；session-store rules.md 的扇出帶識別規則"

  - id: BR63.4
    statement: "同一連線的送出以 asyncio.Lock 序列化；送出失敗即自登錄移除，不向上拋"
    category: error_handling
    applies_to: 對單一連線的每次送出
    trigger: 任一送出
    logic: "送出前取 Connection.sendLock；WebSocketDisconnect 或其他送出例外 → 移除該連線、記 DEBUG，呼叫端照常繼續"
    violation_behaviour: "一條斷線的分頁讓扇出迴圈或 U12 的背景工作中斷"
    source: "U12 的 sink 失敗不擴散規則（work-orchestrator rules.md）；本站新定"

  - id: BR63.5
    statement: "伺服器不緩衝、不重播已送出或未送達的訊息"
    category: policy
    applies_to: 全部送出
    trigger: 目標連線不存在或已斷線
    logic: >
      送不到即丟棄（記 DEBUG 計數，不記內容）。重連後的狀態由 BR63.2 重新推送；輪次訊息（含推播）不補送。
    violation_behaviour: "自行緩衝 → 與 K-12 server_side 逐字相反，且多一份行程內狀態"
    source: "K-12 x-retry-and-idempotency.server_side（contract-summary.md:987）；fanout_vs_no_replay（:925-929）"

  - id: BR63.6
    statement: "phase=loading 的連線不直接收訊息：扇出與推播先進入其有界暫存佇列，ready 之後依序送出"
    category: constraint
    applies_to: Connection.pendingOutbound
    trigger: 對 phase=loading 的連線送出任何訊息
    logic: >
      狀態訊息與伺服器發起輪次的訊息（emit_turn 的內容與 done）依產生順序附加到佇列；佇列上限 256 則。超過上限 →
      以 1011 關閉本連線（客戶端重連即取得新快照），不丟棄單則訊息以免造成不收斂。phase=ready 之後佇列不再使用。
      ready 之前不得對客戶端送出任何非 ready 訊息（K-12 的 hello → ready 順序）。
    violation_behaviour: "載入中直接送 → 客戶端在 ready 之前收到狀態訊息，違反握手順序；無上界 → 載入卡住時記憶體無限成長"
    source: "review-02 R-03；K-12 x-handshake.step_3（contract-summary.md:950）"

  # ---- BR64：每一輪 ------------------------------------------------------------
  - id: BR64.1
    statement: "turnId 由伺服器以 secrets.token_urlsafe(16) 鑄造，每則客戶端請求一個"
    category: constraint
    applies_to: TurnLedger.turnId
    trigger: 收到 hello 以外的客戶端訊息；或 U12 呼叫 emit_turn
    logic: >
      user_message 的 turnId 承載該輪的全部輪次訊息；set_work_target／set_sharing_mode／correct_work_item 的
      turnId 只在失敗時以單則 error 出現，成功時只用於 log 關聯。turnId 同時是 U11 classify 與 U12 dispatch 的
      turn_id，作為整條鏈的關聯鍵。
    violation_behaviour: "可猜或重複的 turnId → 終止事件被歸到錯誤的一輪"
    source: "brain_ws_contract.py:46-48（turnId 產生方式屬 U13）；progress-channel security-design.md S-5（鑄造用密碼學安全來源）"

  - id: BR64.2
    statement: "入站訊息兩步驗證：WsUnvalidatedEnvelope 之後，把**原始 dict** 交給 WsClientEnvelope"
    category: validation
    applies_to: ready 之後的每個訊框
    trigger: 收到訊框
    logic: >
      非 JSON、非物件、WsClientEnvelope 驗證失敗（含偷帶 turnId 或身分欄位、未知 type、v 不等於 1、缺必填的
      page／scope／segment）、ready 之後再收到 hello → error(INVALID_REQUEST)，以新 turnId 送出；連線保留。
      不得以 WsUnvalidatedEnvelope 的欄位子集重建 dict 再驗（brain_ws_contract.py:740-743）。
    violation_behaviour: "以欄位子集重建 → extra=forbid 看不到偷帶的 turnId，U2 的規則 2.13 的執行期拒絕靜默失效"
    source: "brain-ws-contract code-summary.md:324（H-3）；brain_ws_contract.py:740-743；brain-ws-contract security-requirements.md:276"

  - id: BR64.3
    statement: "user_message 的文字去空白後為空、或長度超過 4000 字元 → error(INVALID_REQUEST)，不進任何下游"
    category: validation
    applies_to: UserMessagePayload.text
    trigger: 收到 user_message
    logic: >
      上限取自 session_store.DEFAULT_MESSAGE_MAX_CHARS（session_store.py:113），import 該常數，不另抄數值。
      在 prompt_guard 與 LLM 之前檢查，使超長輸入不產生任何計費呼叫。
    violation_behaviour: "先呼叫分類再由 append_message 拒絕 → 白付一次 LLM 呼叫"
    source: "construction.md「Validate and sanitize all inputs at system boundaries」；session-store OPEN-N10-6"

  - id: BR64.4
    statement: "同一連線的客戶端訊息依收到順序逐則處理，前一則處理完才讀下一則"
    category: constraint
    applies_to: 每條連線的接收迴圈
    trigger: 收到訊息
    logic: >
      一則 user_message 的處理到 dispatch 回傳並送出終止事件為止（U12 不等待能力即回傳，work_orchestrator.py:237）；
      背景工作的推送不受此限（經 sink，BR65）。
    violation_behaviour: "並行處理 → 同一連線兩輪交錯、歷程順序與畫面順序不一致"
    source: "本站新定；K-12 user_message 非冪等（contract-summary.md:983-985）"

  - id: BR64.5
    statement: "prompt_guard 先於一切：命中即送固定拒絕訊息並以 done 結束，不呼叫 LLM、不寫歷程、不寫記憶"
    category: policy
    applies_to: user_message
    trigger: is_platform_self_modification(text) 為 true
    logic: >
      送 token{text: prompt_guard.REFUSAL_MESSAGE}，再送 done。不呼叫 append_message：歷程會作為 recent_messages
      進入下一輪的分類 prompt（intent_routing.py:175-190），寫進去等於讓被攔下的文字繞過攔截進入模型。
      不寫 episodic（BR67.7）。U11 classify 內另有同一檢查（intent_routing.py:435），收到
      PlatformSelfModificationRefused 時同樣處置——雙重檢查是刻意的縱深。
    violation_behaviour: "以 error 結束 → 違反 K-12 prompt_guard_case；寫入歷程 → 攔截被下一輪繞過"
    source: "K-12 x-per-message-guard（contract-summary.md:1008-1010）；prompt_guard_case（:974）；intent_routing_errors.py:84-101"

  - id: BR64.6
    statement: "user_message 的處理順序：驗證 → 攔截 → 讀 session → 預取記憶 → 分類 → 寫使用者訊息 → 反問、請求指定或交辦 → 寫回覆 → 終止"
    category: policy
    applies_to: user_message
    trigger: 收到 user_message
    logic: >
      1 BR64.2／BR64.3／BR62.1；2 BR64.5；3 解析段（BR62.5）並 to_thread load(session_key)；4 BR67.10 預取記憶；
      5 依段取 IntentRouter（BR67.6）並 await classify(principal, session, text, turn_id=T)；
      6 to_thread append_message(session_key, segment, "user", text)——**不論 classify 成功或拋出路由失敗**都寫
      （攔截命中除外，BR64.5）；7 below_threshold → BR64.8；有 referent → 以 BR64.12 取目錄，再走 BR64.9 或 BR64.11；之後 to_thread load 取最新
      session，await dispatch(principal, session, decision, utterance=text, segment_id=segment, turn_id=T, bearer_token, sink)；
      8 BR64.10；9 依 BR64.7 送終止事件；10 BR67.7。
      **先讀後寫的理由**：U11 以該段最後 N 則作為 recent_messages（intent_routing.py:175-190、intent_routing_context.py:163），
      並另以 user_text 放入本句（intent_routing_context.py:182）；先寫入再讀會讓本輪原句在 prompt 中出現兩次，每輪重複計費且
      干擾判讀。K-12 只要求「寫入歷程」，未規定先後。dispatch 之前必須重讀，因為第一次對話時段在寫入之後才存在
      （work_orchestrator.py:244-245 在段不存在時拋 ValueError）。
    violation_behaviour: "先寫後讀 → 本句重複進 prompt；分類失敗時不寫 → 失敗的輪次不留痕；交辦前不重讀 → 新使用者的第一句一律 ValueError"
    source: "K-12 x-observable-side-effects.on_user_message（contract-summary.md:1003-1005）；intent-router functional-spec.md W1；OPEN-WO12-3；review-01 R-08"

  - id: BR64.7
    statement: "每輪至多一個終止事件；有內容才可送 done，否則送 error(EMPTY_RESPONSE)；終止後不再送任何輪次訊息"
    category: constraint
    applies_to: TurnLedger（純狀態機）
    trigger: 每則輪次訊息
    logic: >
      非空白 token 或 cost_card 送出成功 → hasContent = true。要結束時：hasContent → done，否則
      error(EMPTY_RESPONSE)。已在 done／error／ended_silent → 拒絕放行並記 WARNING（不拋）。
      clarify 不算內容（它不是終止，該輪仍開著）。
    violation_behaviour: "零內容 done → 使用者看到空白成功態；兩個終止事件 → 消費端狀態機無法判定一輪是否結束"
    source: "K-12 x-termination-semantics（contract-summary.md:956-972）；U2 的規則 2.6 與規則 2.7（brain-ws-contract rules.md:193-213）"

  - id: BR64.8
    statement: "低於門檻時送 clarify 並保留候選與原句；選定意圖後先依原句重新找出對象，不得帶舊對象交辦"
    category: policy
    applies_to: 反問
    trigger: decision.below_threshold；或收到 select_clarify_candidate
    logic: >
      送 clarify{kind: "intent", candidates}（turnId T，由 IntentDecision.candidates 逐欄轉成契約 ClarifyCandidate；kind 為
      契約增量 C-7），建 PendingClarify(T, kind="intent", candidates, segment, utterance=原句)；該輪不終止。candidates 為空 →
      error(INTERNAL_ERROR)。
      收到 select：無 PendingClarify → 新 turnId 送 error(INVALID_REQUEST)；candidateId 非 null 且不在集合內 →
      error(INVALID_REQUEST, turnId T) 並清除；candidateId 為 null → 該輪 ended_silent，**不送任何狀態訊息與終止事件**；
      等待選擇時收到新的 user_message → 舊輪 ended_silent，開新輪。
      candidateId 非 null 且在集合內：
        kind=target → 依 BR64.11 (a) 的選定路徑；
        kind=intent → 組 IntentDecision(intents=(Intent(候選.capability, None),), confidence, below_threshold=False)，
        **再依 BR64.13 以原句找出對象**，依其結果走 BR64.9（唯一）、BR64.11（多筆或不一致）或直接交辦（原句未點名任何對象），
        全程沿用 turnId T。
      **為何不能直接以 referent=None 交辦**：低於門檻時 U11 回的 intents 必為空（intent_routing_predicate.py:263-275），
      候選只有 id／label／capability／confidence（intent_routing_types.py:183-196），句中的對象在這一步已經遺失；
      直接交辦就是對舊作業對象或未選定狀態建立工作項，畫面無任何提示。
    violation_behaviour: "null 時送 done → 零內容 done；送 work_target → 脈絡列被動到，AC1.2.3 不成立；選定後以 referent=None 交辦 → 句中點名的對象被靜默忽略"
    source: "U2 的規則 2.14（brain-ws-contract rules.md:307-329）；brain_ws_contract.py:358-376；review-02 R-02"

  - id: BR64.9
    statement: "意圖帶 referent 且在使用者可見的對象目錄中唯一相符時，先更新該段的作業對象再交辦"
    category: policy
    applies_to: dispatch 之前（解析成功的路徑）
    trigger: decision.intents 中有非 null 的 referent
    logic: >
      全部非 null referent 經 casefold 與去空白後必須相同，否則屬 BR64.11 (c)。以 BR64.12 取得對象目錄後依序比對
      （casefold 後精確相等）：
        1 當前段**已選專案**時，先比對該專案下的系統名稱——恰一筆 → 取它；
        2 否則（**含脈絡列尚未選定**）比對目錄中全部系統名稱與全部專案名稱。
      **恰一筆相符**才走本規則：set_work_target(session_key, segment, principal, project_id, system_id 或 None, None)，
      成功即依 BR63.3 扇出 work_target，再重讀 session 交辦。零筆或多筆相符一律走 BR64.11。
      第 2 步使 AC1.1.5 的主情境（脈絡列未選定、句中為系統名稱）可解析：該系統名稱在目錄中唯一時即命中。
      **U12 不讀 referent**（work_orchestrator.py 全檔 grep 為 0 命中，dispatch 只讀段的作業對象），故本單元是 referent
      唯一的讀取端。
    violation_behaviour: "不更新 → 句中點名的系統不會被用上，AC1.1.5 不成立；只在已選專案下找系統 → 未選定時系統名稱永遠找不到"
    source: "OPEN-WO12-3（work-orchestrator functional-spec.md:259）；intent-router functional-spec.md OPEN-IR11-4（:346-372）；stories.md:43（AC1.1.5）；review-01 R-01；review-02 R-01"

  - id: BR64.10
    statement: "交辦回傳後，把本輪送出的 token 文字以 assistant 角色寫入同一段歷程，再送終止事件"
    category: policy
    applies_to: 回覆歷程
    trigger: 一輪即將以 done 結束（交辦、BR64.11 (b)(c) 的固定句型；攔截命中除外）
    logic: >
      to_thread append_message(session_key, segment, "assistant", 本輪 token 文字以換行串接)。失敗（含
      SessionBackendUnavailable、SessionMessageTooLong）→ 記 WARNING，照常送 done——內容已送達使用者。
      超過 4000 字元時截斷至上限並以「…」結尾（只截 assistant 文字，使用者原句永不截斷）。
    violation_behaviour: "不寫回覆 → 下一輪分類只看得到使用者單方面的話，指涉詞解析失去上一輪的結果"
    source: "K-12 on_user_message（「U13 會寫入 session 的對話歷程」）；本站新定截斷處置"

  - id: BR64.11
    statement: "referent 無法唯一解析時不得交辦給舊作業對象：多筆相符改走對象反問，零筆相符或對象不一致以固定句型請使用者指定"
    category: policy
    applies_to: dispatch 之前（解析失敗的路徑）
    trigger: 有非 null referent 但不符合 BR64.9 的「恰一筆相符」；或 BR64.13 在原句中找到多個不同對象
    logic: >
      三種情況，皆**不呼叫 dispatch**：
      (a) 多筆相符（同名系統分屬不同專案、或系統名與專案名同時相符）→ 送 clarify{kind: "target", candidates}
          （kind 為契約增量 C-7）。候選為每一筆相符對象：id＝"target-<n>"（n 自 1 起依目錄順序）、label＝「<系統名>（專案：
          <專案名>）」或「專案：<專案名>」、confidence＝null、capability＝**本輪判定中第一個意圖的 capability**——
          多意圖且 capability 不同時，候選不表達意圖（意圖已確定，反問的只是對象），全部意圖原樣保存在
          PendingClarify.decision；U14 以 kind=="target" 辨識並只顯示 label，不以 capability 呈現。
          建 PendingClarify(T, kind="target", 候選 → (project_id, system_id) 的對應, segment, utterance, decision)；
          使用者選定後 set_work_target、扇出 work_target、重讀，以原 decision（**全部意圖**）交辦，沿用 turnId T。
      (b) 零筆相符 → 送 token「找不到名為「<referent>」的系統或專案。請在上方脈絡列選定作業對象後再說一次。」＋ done。
      (c) 多個意圖指向不同對象 → 送 token「這句話提到了不同的對象，請一次只針對一個對象交辦，或先在脈絡列選定。」＋ done。
      (b)(c) 的可觀察結果（可測）：該段歷程恰增加兩筆（user 一筆、assistant 一筆，依 BR64.6 與 BR64.10）；工作項集合不變；
      各段作業對象不變；不送 work_target、work_items；**不呼叫 MemoryFacade.write**（BR67.7 明列排除）。
      解析時 HierarchyForbidden → 依 BR67.1 送 error(UNAUTHORIZED)；目錄取得失敗的其他例外 → error(INTERNAL_ERROR)。
      **為何不交給 U12**：U12 只讀段上的作業對象（work_orchestrator.py:244-251、_build_items），帶著舊對象交辦會在使用者
      明講的對象以外的地方建立工作項、且畫面無任何提示。
    violation_behaviour: "帶舊作業對象交辦 → 工作項建立在錯的系統上，使用者看不出來"
    source: "review-01 R-01（使用者裁決）；review-02 R-05；U12 的 [WO1]=A（固定句型、不新增 LLM 呼叫）"

  - id: BR64.12
    statement: "對象目錄＝使用者可見的全部專案及其系統，在一次 to_thread、同一 DB session 內經 HierarchyFacade 取得，專案數上限 50"
    category: constraint
    applies_to: build_target_catalog
    trigger: BR64.9 或 BR64.13 需要比對名稱
    logic: >
      list_projects(principal)（hierarchy_facade.py:275-280，只回請求者為擁有者的專案）→ 對每個專案 list_systems(principal,
      project_id=…)（:282-288）。全部經 facade，授權照常；**不得**直呼 hierarchy_service 或直讀表。K-07 沒有跨專案查系統的
      方法（已查證：facade 只有上列兩個列舉方法），故為 1＋N 次查詢，N ≤ 50。專案數超過 50 → 不比對系統名稱、只比對專案名稱，
      並記 INFO 計數（不記名稱）；目錄只在當輪使用、不快取（避免跨輪看到已刪除或已授權變更的對象）。
      可見範圍與 K-07 的 resolve_work_target 一致：以成員身分（非擁有者）可見的專案，K-07 目前也不允許設為作業對象，
      故不納入目錄是一致而非遺漏（見 functional-spec.md OPEN-GW13-16）。
    violation_behaviour: "繞過 facade 查詢 → 讀到使用者無權看的專案名稱；無上限 → 專案很多的使用者每輪付出無界的查詢量"
    source: "review-02 R-01；hierarchy_facade.py:273-288；K-07 的擁有者範圍規則（U7 的規則 6.1）"

  - id: BR64.13
    statement: "反問後選定意圖時，以原句對對象目錄做名稱掃描，找出句中點名的對象"
    category: calculation
    applies_to: scan_targets_in_utterance（純函式）
    trigger: BR64.8 的 kind=intent 選定
    logic: >
      對目錄中每個長度 ≥ 2 的系統名稱與專案名稱，以 casefold 判定是否為原句的子字串；同一專案下系統命中時專案名的命中不另計。
      結果三分：無命中 → 原句未點名任何對象，依當前作業對象交辦（與高信心路徑 referent 為 null 時同）；恰一個對象 →
      走 BR64.9 的更新路徑；多個不同對象 → 走 BR64.11 (a)（若各命中同名）或 (c)。
      **已知限制（揭露）**：只認得逐字出現的名稱；代名詞（「那張圖」）或簡稱無法辨識，此時視為未點名、依當前作業對象交辦——
      與高信心路徑上 U11 把代名詞解析回當前作業對象的行為一致。
    violation_behaviour: "不掃描 → 反問選定後句中點名的對象被靜默忽略，對舊對象交辦"
    source: "review-02 R-02（使用者裁決方向：在 PendingClarify 保存原始資訊並套 BR64.11）"

  # ---- BR65：交給 U12 的 sink ---------------------------------------------------
  - id: BR65.1
    statement: "sink 綁 session key 而不綁單一 socket；每次呼叫 U12 時新建"
    category: constraint
    applies_to: GatewaySink
    trigger: 呼叫 dispatch／correct／list_items
    logic: "U12 的背景工作在原連線斷線後仍會呼叫 sink；sink 每次送出時才查 registry，不持有 socket 參照"
    violation_behaviour: "綁 socket → 使用者換分頁或重連後收不到完成通知"
    source: "work-orchestrator functional-spec.md:33-39；code-summary.md §七第 4 點"

  - id: BR65.2
    statement: "emit_session 扇出；emit_in_turn 只寫進發起它的那一輪，且逐則立即送出"
    category: policy
    applies_to: GatewaySink.emit_session／emit_in_turn
    trigger: U12 呼叫
    logic: >
      emit_session(WorkItemsPayload) → BR63.3。emit_in_turn(turn_id, msgs)：turn_id 必須等於 originTurn 且該輪
      未終止，送到發起連線並標 hasContent；不符或已終止 → 丟棄並記 WARNING。msgs 中的每一則 token **各自成為一個
      WebSocket 訊框、收到即送**，不合併、不等待其餘——這是逐則串流的傳輸能力，保留給上游未來產生多則或逐字內容時使用
      （本輪內容來源見 functional-spec.md OPEN-GW13-15）。
    violation_behaviour: "把 in_turn 訊息送到別的連線 → 別的分頁收到不屬於它任何一輪的 token；合併緩衝 → 傳輸層失去逐則串流的能力"
    source: "work-orchestrator functional-spec.md:35-38；brain_ws_contract.py:513-521（輪次訊息分類）；[RA:FR8.1]"

  - id: BR65.3
    statement: "emit_turn 是伺服器發起的推播：新 turnId，送給該 key 的全部存活連線，每條連線依序收內容後收 done"
    category: policy
    applies_to: GatewaySink.emit_turn
    trigger: U12 的完成、失敗、逾時與停掉訊息
    logic: >
      鑄造新 turnId；對 registry[session_key] 每條存活連線依序送 msgs（token／cost_card），再送 done（msgs 非空由 U12
      保證，work_orchestrator.py:1060-1061）。session key 由交辦者的 user id 推導，故推播只到交辦者本人的連線。
      零條存活連線 → 丟棄（BR63.5）。推播內容是否寫入歷程見 BR65.5。
    violation_behaviour: "以使用者以外的鍵扇出 → 別人收到我的完成通知（AC7.1.3）"
    source: "work-orchestrator functional-spec.md:39；[RA:FR7.1]／[RA:FR7.2]；US7.1"

  - id: BR65.4
    statement: "送出前一律包成 WsEnvelope 並通過模型驗證；驗證失敗不送"
    category: validation
    applies_to: 全部出站訊息
    trigger: 任一送出
    logic: "WsEnvelope.model_validate({v:1, type, turnId, payload}) 通過才 send_text(model_dump_json)；失敗記 ERROR（類別名）"
    violation_behaviour: "送出型別不符的訊息 → 前端窮盡 switch 進入未知分支"
    source: "brain_ws_contract.py WsEnvelope 的三個 validator；work-orchestrator code-summary.md §七第 4 點（由 U13 包成 WsEnvelope）"

  - id: BR65.5
    statement: "推播的 token 文字以 assistant 角色寫入它所屬工作項的那一段歷程；段不明時不寫"
    category: policy
    applies_to: GatewaySink.emit_turn
    trigger: emit_turn 送出之後
    logic: >
      sink 建立時記下段：dispatch 的 sink 取本輪段；correct 的 sink 在呼叫前以 load_work_items 讀出該工作項的
      segmentId（U12 存於工作項的伺服器內部欄位）；list_items 的復原掃描 sink 涵蓋多個工作項，**段不明，不寫**（揭露於
      functional-spec.md §八）。寫入在背景 to_thread 執行（不阻擋推播），截斷同 BR64.10，失敗記 WARNING。不寫 episodic——
      背景工作完成時 U12 已寫 procedure 記憶，再寫 episodic 會重複。
      **與 BR64.10 的理由一致**：兩者都為了讓下一輪的指涉詞解析（「剛才那個」）看得到系統說過的話；推播正是使用者最常
      回指的內容，不寫入就與 BR64.10 的理由自相矛盾。
    violation_behaviour: "不寫 → 「把剛才那張圖拿去檢視」在下一輪看不到產圖完成的訊息"
    source: "review-01 R-09；work-orchestrator entities.md（segmentId 欄位）；U8 的規則 7.2（procedure 由 U12 寫）"

  # ---- BR66：其餘客戶端訊息 -----------------------------------------------------
  - id: BR66.1
    statement: "set_work_target：以連線的 principal 與段識別呼叫 U10，成功即扇出 work_target"
    category: authorization
    applies_to: set_work_target
    trigger: 收到 set_work_target
    logic: >
      段識別取自契約增量 C-5 的 segment（functional-spec.md §十一）。三個識別字串轉為正整數（null 保持 null；非十進位數字 →
      INVALID_REQUEST）。to_thread set_work_target(session_key, segment, principal, ...)，SessionStore 的 hierarchy_facade 由
      本單元注入一個**每次呼叫開獨立 DB session** 的轉接器。成功 → 扇出該段的 work_target。HierarchyForbidden →
      UNAUTHORIZED；HierarchyNotFound → INVALID_REQUEST。**實作狀態：在 C-4／C-5 合入之前為 blocked。**
    violation_behaviour: "寫入客戶端原值 → K-07 的檢查成為裝飾（U10 的設計已擋，本單元不得繞過 SessionStore）"
    source: "contract-summary.md:307／:311；session-store functional-spec.md W6"

  - id: BR66.2
    statement: "set_sharing_mode：以頁面範圍呼叫 U10，成功即扇出 sharing_mode 與該段的 work_target"
    category: policy
    applies_to: set_sharing_mode
    trigger: 收到 set_sharing_mode
    logic: >
      頁面範圍取自契約增量 C-6 的 scope（functional-spec.md §十一）。to_thread set_sharing_mode(session_key, scope, mode)；
      回傳的 BrainSession 中該頁所讀段的作業對象一併扇出（W4 第 4 步：重入獨立段時推送該段作業對象）。
      **實作狀態：在 C-3／C-4／C-6 合入之前為 blocked。**
    violation_behaviour: "不推該段作業對象 → 切到獨立對話後脈絡列仍顯示共享段的值"
    source: "session-store functional-spec.md W3 第 7 步、W4 第 4 步、W5"

  - id: BR66.3
    statement: "correct_work_item：呼叫 U12 的 correct；找不到即 INVALID_REQUEST"
    category: policy
    applies_to: correct_work_item
    trigger: 收到 correct_work_item
    logic: "await correct(principal, session_key, workItemId, bearer_token, sink)；WorkItemNotFound → error(INVALID_REQUEST)；成功時的訊息由 U12 經 sink 送出（emit_session ＋ emit_turn）"
    violation_behaviour: "本單元自行改工作項 → 繞過 U12 的比對後寫入"
    source: "work-orchestrator code-summary.md §七第 7 點；K-12 correct_work_item 冪等（contract-summary.md:986）"

  # ---- BR67：錯誤、日誌、執行環境 ----------------------------------------------
  - id: BR67.1
    statement: "例外 → error code 與固定訊息的對應是封閉表，訊息不含任何例外原文"
    category: error_handling
    applies_to: error_for（純函式）
    trigger: 處理任一客戶端請求時拋出例外
    logic: >
      LlmUnavailable／LlmBudgetExceeded／EmptyCandidates／MalformedRouting → INTERNAL_ERROR「大腦暫時無法判讀這句話，請再說一次」；
      SessionBackendUnavailable → INTERNAL_ERROR「工作階段暫時無法存取，請稍後再試」；
      SessionMessageTooLong → INVALID_REQUEST「訊息太長，請縮短後再送出」；
      HierarchyForbidden → UNAUTHORIZED「你沒有權限選擇這個作業對象」；
      HierarchyNotFound → INVALID_REQUEST「找不到這個作業對象」；
      WorkItemNotFound → INVALID_REQUEST「找不到這個工作項」；
      pydantic ValidationError／JSON 解析失敗 → INVALID_REQUEST「訊息格式不正確」；
      其餘（含 dispatch 的 ValueError、BR62.1 (c) 的重驗失敗）→ INTERNAL_ERROR「處理時發生錯誤，請再說一次」。
    violation_behaviour: "把 str(exc) 放進 message → 堆疊、SQL 或內部路徑外洩（U2 的規則 2.9）"
    source: "brain_ws_contract.py:303-323；brain-ws-contract security-requirements.md:296；intent-router reliability-requirements.md:57"

  - id: BR67.2
    statement: "握手結束（ready 已送出）之後遇到 SessionBackendUnavailable：該輪送 error(INTERNAL_ERROR)，連線保留"
    category: error_handling
    applies_to: ready 之後的每一則請求
    trigger: 任一 SessionStore 呼叫拋 SessionBackendUnavailable
    logic: "依 BR67.1 送 error；不關閉、不清登錄；下一則訊息照常處理。ready 之前的同一例外屬 BR61.7（1011）"
    violation_behaviour: "關閉連線 → Redis 抖動一次全部連線同時重連"
    source: "[GW3]=A 後半；session-store reliability-requirements.md:64；review-01 R-05"

  - id: BR67.3
    statement: "log 不得含 token、query string、使用者文字、回覆文字、referent 與候選標籤"
    category: policy
    applies_to: 本單元全部 log
    trigger: 任何 log
    logic: >
      logger 名稱 "cloud360.brain_gateway"。允許欄位：connId、sessionKey、turnId、訊息 type、error code、
      關閉碼、例外類別名稱、elapsedMs、計數。
    violation_behaviour: "本 repo 為 public、Actions log 公開可讀，一次 log 即等同公開"
    source: "team.md Forbidden（敏感資料）；session-store security-requirements（對話內容不入 log）；team.md logger 命名"

  - id: BR67.4
    statement: "關閉原因只用 ASCII、至多 123 位元組、不含 token"
    category: constraint
    applies_to: websocket.close 的 reason
    trigger: 任何關閉
    logic: "固定字串：credentials-expired-or-invalid（4401）、forbidden（4403）、expected=1 received=<n|invalid>（4400）、internal-error（1011）"
    violation_behaviour: "超過 123 位元組 → 關閉訊框違反 RFC 6455；中文每字 3 位元組，易超限"
    source: "RFC 6455 §5.5（控制訊框酬載上限 125 位元組，扣 2 位元組關閉碼）；本站新定"

  - id: BR67.5
    statement: "事件迴圈上不得有同步的 Redis、DB 或嵌入呼叫——本單元自己的呼叫一律 to_thread；U11 的記憶檢索以預取移開；U12 內部的同步 store 呼叫為具名殘留"
    category: constraint
    applies_to: 事件迴圈
    trigger: 任一同步 I/O
    logic: >
      對 U12 code-summary R-05 的決定：(1) 本單元呼叫的 load／append_message／set_sharing_mode／set_work_target／
      load_work_items 與 get_user_from_token、HierarchyFacade 一律 to_thread（RedisGateway 退避重試以
      time.sleep 進行，redis_gateway.py:99 MAX_RETRIES=2）；會呼叫嵌入的 MemoryFacade 呼叫走 BR67.12 的專用有界執行器；
      (2) U11 classify 內的同步記憶檢索由 BR67.10 移出事件迴圈；
      (3) U12 對 self._store 的同步呼叫**不包裝**——本單元無法在不改 U12 的前提下把同步方法變成可 await；列為
      OPEN-GW13-4 的具名殘留（只剩此一項）。
    violation_behaviour: "同步 I/O 留在迴圈上 → Redis 抖動或 Ollama 變慢時同一行程的全部 WebSocket、collab 廣播與 SSE 一起停"
    source: "work-orchestrator code-summary.md:176-180（R-05）；K-12 x-event-loop（contract-summary.md:1011-1012）；US8 DoD 第 1 點；review-01 R-03"

  - id: BR67.6
    statement: "WorkOrchestrator 與 SessionStore 一個行程一個；IntentRouter 一個段一個（三個），共用一個預取轉接器"
    category: constraint
    applies_to: 元件生命週期
    trigger: 行程啟動（BR67.11）
    logic: >
      以 app 建構 WorkOrchestrator（不 import main）。IntentRouter 的段在建構子固定（intent_routing.py:340），而每輪的段不同，
      故依 shared／workspace／assessment 各建一個，三者的 memory_facade 皆為 BR67.10 的預取轉接器。三個實例在行程內重用，
      TLS 握手各付一次，不在 handler 內建構。
    violation_behaviour: "每個請求建 router → 每輪多付一次 TLS 握手（intent-router code-summary.md:254）；只建一個 → 獨立段的分類讀到共享段的歷程"
    source: "intent-router code-summary.md:254；work-orchestrator code-summary.md §七第 2 點"

  - id: BR67.7
    statement: "以 done 結束、非攔截、且有交辦的使用者輪次，終止事件送出之後在背景寫一筆 episodic 記憶；失敗只記 WARNING"
    category: policy
    applies_to: 輪次結束
    trigger: 使用者發起的一輪以 done 結束且本輪呼叫過 dispatch
    logic: >
      以 BR67.12 的記憶執行器執行：開獨立 DB session，MemoryFacade(db).write(principal, "episodic", content)，
      content = "使用者：<原句>\n大腦：<本輪 token 文字>"（同 BR64.10 的截斷）。
      **不寫的輪次（窮舉）**：攔截命中（BR64.5）、error 結束、ended_silent、BR64.11 (b)(c) 的請求指定句、伺服器發起的推播
      輪次（BR65.5）、記憶熔斷開啟時（BR67.12）。
      失敗（含嵌入提供者不可用、執行器逾時）→ WARNING（例外類別名）；不送任何訊息、不影響該輪與後續輪次。
    violation_behaviour: "寫入成功才送 done → Ollama 一出問題整個大腦無法回覆（[GW2] 選項 B 的代價）；把請求指定句寫成記憶 → 記憶被「找不到對象」污染"
    source: "[GW2]=A；memory-service rules.md:305-313（U8 的規則 7.1）；memory-service nfr-design logical-components.md:55；review-02 R-05"

  - id: BR67.8
    statement: "本單元不鑄造 request_key、不開關也不 drain 進度通道"
    category: constraint
    applies_to: ProgressChannel
    trigger: 不適用
    logic: >
      進度通道唯一的生產者是 A1 的 design agent，而它只經 agent_router 被呼叫：agent_router 鑄造鍵（agent_router.py:131）、
      open（:138）、把鍵傳入 run_design_agent（:154），由 run_design_agent 在其內部 drain，最後 agent_router close（:162）。
      U12 以 ASGI 呼叫該端點，事件在該端點內被收齊。本單元沒有任何事件來源可 drain；K-18 對本單元的消費端宣告列入契約
      追認（functional-spec.md OPEN-GW13-12）。
    violation_behaviour: "本單元另開通道 → 一個永遠沒有生產者的通道；或與 agent_router 重複 open 同鍵"
    source: "agent_router.py:131-162；work-orchestrator functional-spec.md:259；review-01 R-10"

  - id: BR67.9
    statement: "既有 5 個 SSE 端點的程式不在本單元的變更範圍"
    category: constraint
    applies_to: 變更範圍
    trigger: 實作
    logic: "本單元的 diff 不得觸及 agent_router、review_router、lens_router、collab_router、advice_stream_router 的路由函式"
    violation_behaviour: "改動既有串流行為 → AC8.1.4 不成立"
    source: "[RA:FR8.2]；AC8.1.4"

  - id: BR67.10
    statement: "U11 的記憶檢索由本單元在 await classify 之前預取，注入的轉接器只回傳預取結果"
    category: constraint
    applies_to: 注入 IntentRouter 的 memory_facade 轉接器（本單元擁有）
    trigger: 每則 user_message 進入分類之前
    logic: >
      U11 在 async classify 內**同步**呼叫 memory_facade.search（intent_routing.py:217-225），而嵌入走同步 httpx.Client
      （embedding_port.py:610），逾時預設 10 秒（:125）。本單元擁有注入的轉接器，故：
      (1) 預取：在 BR67.12 的記憶執行器上（**不用** asyncio.to_thread 的共用執行緒池）開獨立 DB session，
          MemoryFacade(db).search(principal, text, kinds=("semantic","procedure"), limit=5)——kinds 與 limit 與 U11 的取用值
          相同（intent_routing.py:108、:113），以一條契約測試鎖住兩邊一致；等待上限 3 秒（asyncio.wait_for），逾時或失敗
          記下「失敗」而非拋出；熔斷開啟時不預取、直接記為失敗。
      (2) 傳遞：預取結果放入 contextvars.ContextVar，於同一個 task 內 await classify；ContextVar 依 task 隔離，
          並行的其他使用者輪次讀不到。
      (3) 轉接器的 search(principal, query, kinds, limit)：只讀 ContextVar；principal 的 user_id 與 query 與預取時不同、
          kinds 不是預取 kinds 的子集、或預取失敗 → 拋例外，由 U11 依其既有設計降級為不帶記憶分類；否則依 kinds 過濾、
          取前 limit 筆回傳。**轉接器內不得有任何 I/O。**
      可驗證性：(a) 以會睡 10 秒的嵌入替身驅動一輪，同時量測另一個 coroutine 的排程延遲須遠小於 1 秒；(b) 見 BR67.12 的
      執行緒池隔離測試。
    violation_behaviour: "在迴圈上同步嵌入 → Ollama 不可用時每則入口頁訊息讓整個行程停擺至多 10 秒"
    source: "review-01 R-03（使用者裁決）；review-02 R-07；intent_routing.py:192-235（記憶不可用時降級）"

  - id: BR67.11
    statement: "閘道元件在行程啟動時、於既有設定檢查之後與 init_db 之前建立；設定錯誤讓啟動失敗，握手時元件不存在即 1011"
    category: constraint
    applies_to: 元件生命週期
    trigger: FastAPI startup
    logic: >
      main.py 既有 startup hook 的順序為 configure_provider_env → configure_embedding_env → configure_session_env →
      configure_intent_routing_env → init_db（main.py:55-77）。本單元的建立插在 configure_intent_routing_env 之後、init_db 之前，
      依序：
        1 Redis client：build_redis_client(os.environ["REDIS_URL"], user=os.environ["REDIS_USER"], password=os.environ["REDIS_PASSWORD"])
          （redis_gateway.py:510-536）。三者任一缺值（KeyError）或 REDIS_USER 為 default（該函式拋 ValueError）→ 啟動失敗。
          **不在啟動時連線**：該函式只建 ConnectionPool.from_url 與 Redis 物件，兩者皆延遲到第一個指令才連線，故 Redis 暫時不可用
          不會讓後端起不來，而是在握手時以 1011 呈現（BR61.7）。三個變數已存在於 backend/.env.example、deploy/.env.example、
          render-env.sh 與兩份 compose，本單元**不新增環境變數**，故無 LOCAL-DEV.md 同步義務；若實作時發現須新增，同一 PR 須同步
          LOCAL-DEV.md（project.md 規則）。
        2 RedisGateway 與 SessionStore（history_max 由已驗證的 BRAIN_SESSION_HISTORY_MAX 取得）；
        3 記憶執行器（BR67.12）與預取轉接器；
        4 三個 IntentRouter（建構子呼叫 resolve_routing_config，故必須在 configure_intent_routing_env 之後）；
        5 WorkOrchestrator(app, session_store)；
        6 連線登錄。
      全部存於 app.state.brain_gateway；只建立一次，不需互斥。握手時 app.state 沒有閘道元件（例如未觸發 startup 的
      TestClient(app)）→ 1011 並記 ERROR，不在請求路徑上延遲建立。
    violation_behaviour: "排在 configure_intent_routing_env 之前 → 門檻缺值時的錯誤訊息來自 router 建構而非設定檢查；延遲到握手才建立 → 設定錯誤每個握手都 1011"
    source: "review-01 R-12；review-02 R-06；main.py:55-77；redis_gateway.py:510-536"

  - id: BR67.12
    statement: "會呼叫嵌入的工作（記憶預取、episodic 寫入）一律走專用的有界執行器，並以熔斷避免每則訊息重付逾時"
    category: constraint
    applies_to: 記憶執行器（本單元擁有，一個行程一個）
    trigger: BR67.10 的預取、BR67.7 的寫入
    logic: >
      ThreadPoolExecutor(max_workers=4, thread_name_prefix="brain-memory")，於 startup 建立（BR67.11）、shutdown 時關閉。
      認證、session 讀寫、hierarchy 等其他同步呼叫仍用 asyncio.to_thread 的預設執行緒池——嵌入變慢時最多佔滿這 4 條執行緒，
      不會排擠它們。等待上限：預取 3 秒（BR67.10）、episodic 寫入 15 秒（大於嵌入逾時 10 秒，讓單次正常完成）。
      熔斷：任一次預取或寫入逾時或拋例外 → 開啟 30 秒，期間預取直接記為失敗（U11 降級）、episodic 跳過（記 WARNING 計數），
      30 秒後下一次呼叫照常嘗試，成功即關閉。四個數值為本站選值。
      已知殘留：逾時只放棄等待，執行緒內的嵌入呼叫仍會跑到它自己的 10 秒逾時為止；上限 4 條執行緒即是這個殘留的上界。
      可驗證性：以 4 個以上並行的慢嵌入替身驅動，同時量測 BR62.1 的重驗與 session load 仍在 1 秒內完成。
    violation_behaviour: "用共用池 → 少數並行的慢嵌入即讓全部連線的認證與讀取排隊；無熔斷 → Ollama 停擺期間每則訊息都多等 3 秒"
    source: "review-02 R-07；embedding_port.py:125"

```

## 三、規則摘要

| 群 | 規則 | 一句話 |
|---|---|---|
| 握手與認證 | `BR61.1`–`BR61.8` | `/api/brain/ws`；兩個子協定、只回送協定名；accept 前認證；4401／4403／1011 先 accept 再立即關；握手在 ready 送出時結束 |
| 身分與工作階段 | `BR62.1`–`BR62.6` | 每則訊息在同一 DB session 內重驗並鑄造 principal；token 只在記憶體；session key 純函式推導；載入不寫；段由純函式決定；閒置連線每 60 秒重驗 |
| 登錄與扇出 | `BR63.1`–`BR63.6` | hello 後即登錄（載入中）、單行程假設；ready 後先送快照再送暫存；狀態訊息扇出全部連線；送出序列化、失敗即移除；不緩衝不重播；載入中有界暫存 |
| 每一輪 | `BR64.1`–`BR64.13` | 伺服器鑄 turnId；原始 dict 驗證；長度上限；逐則處理；攔截優先且不入歷程；先讀後寫；至多一個終止；反問與選擇；referent 唯一相符才更新對象；回覆入歷程；無法唯一解析時反問或請求指定、不交辦；對象目錄（擁有者可見、上限 50 個專案）；反問選定後以原句掃描對象 |
| sink | `BR65.1`–`BR65.5` | 綁 key 不綁 socket；in_turn 只進原輪且逐則送出；emit_turn 推給交辦者全部連線；送前驗型別；推播內容入所屬段歷程 |
| 其餘訊息 | `BR66.1`–`BR66.3` | 作業對象、共享模式、逐項更正 |
| 錯誤與執行環境 | `BR67.1`–`BR67.12` | 封閉錯誤表；握手後 Redis 失效保留連線；log 禁令；關閉原因 ASCII；同步 I/O 離開迴圈；實例數；episodic 背景寫；不碰進度通道；不動 SSE；記憶預取；啟動時依序建立元件；嵌入工作走專用有界執行器與熔斷 |
