# Business Rules — `U10 session-store`

> 本檔是本單元**決策邏輯**的唯一真實來源。實體形狀在 `entities.md`；
> 工作流程與狀態轉換在 `functional-spec.md`。
> 下方的規則摘要表由腳本自 YAML 區塊產生，**不手寫數字**。

## 本檔的上游（每條規則的 `source` 欄另有逐字出處）

| 上游 | 它決定了哪些規則 |
|---|---|
| `requirements.md:125`（`FR2.1`） | `BR2.8`（共享範圍恰三頁，不含 `/cost` 與 `/admin/*`） |
| `requirements.md:133-137`（`FR3.1`–`FR3.3`） | `BR2.2`（入口頁不得切換）、`BR2.3`／`BR2.4`／`BR2.5`（逐頁切換與段的建立保留）、`BR3.2`（讀取視圖只含本段）、`BR4.2`（沿用作業對象） |
| `requirements.md:182`（`FR6.1`） | `BR3.3`（順序穩定，供 `U11` 解析第 N−1 輪產出） |
| `requirements.md:500-504`（`NFR4`） | `BR1.2`（不得放行程記憶體）、`BR6.1`（Redis 不可用大聲失敗）、`BR7.1`（重啟還原） |
| `components.md:97-110` | `SessionContext` 的 `behaviour` 與 `responsibilities` 逐字，是 `BR1.x`／`BR2.x`／`BR4.x` 三組的共同來源；`:111` 逐字 `interaction: 驗證並解析作業對象的三層識別` 即 `BR4.6` 的委派對象 |
| `unit-of-work.md:131-135` | `BR2.5`／`BR2.6`（保留但不併入共享流） |
| `unit-of-work-story-map.md:115` | 本檔規則的驗收面只限 `US2.1`／`US2.2`／`US3.1`／`US6.1`／`US9.1` 五則故事；逐條對應見 `traceability.json` |
| `contract-summary.md:684-742`（`K-09`） | `BR1.1`／`BR1.3`／`BR1.6`／`BR5.1`–`BR5.3`／`BR6.2`／`BR6.3` 全部為其逐字轉錄 |

## Source of truth

```yaml
rules_version: 1
unit: session-store

rules:
  # ── 群組 1：session 身分與存活期 ─────────────────────────────────────────
  - id: BR1.1
    statement: "本單元不產生 session key；它由呼叫方（U13）在握手成功後提供。"
    category: constraint
    applies_to: "K-09 的全部方法"
    trigger: "任何方法被呼叫"
    logic: "IF 呼叫方未提供 session key THEN 拒絕該呼叫（參數錯誤）"
    violation_behaviour: "拒絕；不自行推導、不自行產生"
    source: "x-session-key-derivation 逐字「U13 在握手成功後產生」、「derived_from: 已驗證使用者的 id。一個使用者一個大腦 session」"
  - id: BR1.2
    statement: "全部 session 狀態一律存於 Redis 的單一 key 之下，不得放行程記憶體。"
    category: constraint
    applies_to: "BrainSession 全體（含全部段、歷程、作業對象、頁面模式）"
    trigger: "任何讀寫"
    logic: "IF 任何狀態被保存在行程記憶體（含快取、模組層變數、連線物件）THEN 違反"
    violation_behaviour: "設計層禁止；驗證方式為重啟還原測試（BR7.1）"
    source: "NFR4 逐字「大腦的 session 與工作狀態一律放 Redis，不得放行程記憶體」；K-09.hard_rule"
  - id: BR1.3
    statement: "TTL 為 24 小時，且 K-09 的每一個方法都續期。"
    category: policy
    applies_to: BrainSession
    trigger: "load／set_work_target／append_message／set_sharing_mode／touch 任一成功返回"
    logic: "IF 方法成功 THEN 重設該 key 的 TTL 為 24 小時並重算 expiresAt"
    violation_behaviour: "未續期即等同縮短使用者的 session，屬缺陷"
    source: "ADR-005；K-09.behaviour_semantics.observable_side_effects 逐字「全部方法都會續期 TTL」"
  - id: BR1.4
    statement: "TTL 到期時，該 session 的全部段、歷程、作業對象與工作項集合一起消失。"
    category: policy
    applies_to: "BrainSession 及同 key 的 WorkItem 集合"
    trigger: "TTL 到期"
    logic: "IF TTL 到期 THEN 整個 key 消失；下次進入即為全新 session，全部段的作業對象回到未選定"
    violation_behaviour: "部分到期（例如段留著而作業對象消失）會製造 ADR-005 明確拒絕的中間態"
    source: "ADR-005 逐字「TTL 到期三者一起消失」；其 Alternatives Rejected 逐字拒絕「分成兩個 key」"
  - id: BR1.5
    statement: "不存在顯式清除路徑——TTL 是唯一的清除機制。"
    category: constraint
    applies_to: BrainSession
    trigger: "任何「清除 session」的需求"
    logic: "IF 有人要求顯式清除 THEN 不提供該操作"
    violation_behaviour: "新增第二條清除路徑即新增第二個要測的失敗模式"
    source: "ADR-005 的 Alternatives Rejected 逐字「TTL ＋ 顯式清除並存：兩條清除路徑就是兩個要測的失敗模式，而 TTL 已足夠」"
  - id: BR1.6
    statement: "載入一個不存在的 key 回「無」而非錯誤。"
    category: validation
    applies_to: "SessionStore.load"
    trigger: "load 一個尚未建立或已到期的 key"
    logic: "IF key 不存在 THEN 回傳「無」（新 session 的合法起點）；不 raise"
    violation_behaviour: "把「新使用者第一次進入」當成錯誤處理會讓首次使用不可用"
    source: "K-09.public_interface 逐字 returns: `BrainSession | None`"

  # ── 群組 2：段與共享模式（[S1]=A 逐頁） ─────────────────────────────────
  - id: BR2.1
    statement: "段識別為封閉集合 {shared, workspace, assessment}；不接受其他值。"
    category: validation
    applies_to: "全部帶段識別的方法"
    trigger: "任何帶段識別的呼叫"
    logic: "IF 段識別不在允許集合內 THEN 拒絕該呼叫"
    violation_behaviour: "拒絕；不自動建立未知段"
    source: "entities.md EC4；FR3.1 逐字只列 /workspace 與 /assessment 兩頁"
  - id: BR2.2
    statement: "入口頁恆讀共享段，且不得切換模式。"
    category: authorization
    applies_to: "set_sharing_mode"
    trigger: "以入口頁為範圍呼叫 set_sharing_mode"
    logic: "IF 範圍為入口頁 THEN 拒絕"
    violation_behaviour: "拒絕；入口頁沒有獨立模式這個狀態"
    source: "FR3.1 逐字「使用者得在 /workspace 與 /assessment 由脈絡元件開啟一段新對話」（入口頁不在內）；AC3.1.1 逐字「入口頁的脈絡不受影響」"
  - id: BR2.3
    statement: "set_sharing_mode 必須帶頁面識別，且只改該頁的模式。"
    category: constraint
    applies_to: "set_sharing_mode；pageModes"
    trigger: "使用者在某一頁按下「改為獨立對話」或「切回共享對話」"
    logic: "IF 呼叫帶頁面 P 與模式 M THEN 只寫 pageModes[P] = M，其餘頁面不動"
    violation_behaviour: "改動其他頁的模式會讓 AC3.1.1 的「入口頁的脈絡不受影響」不成立"
    source: "[S1]=A；AC3.1.1"
  - id: BR2.4
    statement: "切到獨立模式時，若該頁的段不存在則建立；已存在則重入同一段。"
    category: policy
    applies_to: "set_sharing_mode(P, isolated)；segments"
    trigger: "pageModes[P] 由 shared 變為 isolated"
    logic: "IF segments[P] 不存在 THEN 建立它並以 BR4.2 初始化作業對象；ELSE 原樣重入，不清空、不新建"
    violation_behaviour: "每次都新建會讓 [S2]=A 的「可重入」失效並讓單一 key 無上界成長"
    source: "[S2]=A（OQ-1 定案）；unit-of-work.md:133 逐字「獨立那段保留但不併入共享流」"
  - id: BR2.5
    statement: "切回共享模式不刪除該頁的獨立段。"
    category: policy
    applies_to: "set_sharing_mode(P, shared)；segments"
    trigger: "pageModes[P] 由 isolated 變為 shared"
    logic: "IF 切回共享 THEN 只改 pageModes[P]；segments[P] 原樣保留直到 TTL 到期"
    violation_behaviour: "刪除即違反已核可的 unit-of-work.md:133「保留」"
    source: "[S2]=A；unit-of-work.md:133"
  - id: BR2.6
    statement: "兩段之間沒有任何合併路徑——獨立段的訊息永不併入共享段。"
    category: constraint
    applies_to: "segments"
    trigger: "任何時刻"
    logic: "IF 有人要求把獨立段併入共享段 THEN 不提供該操作"
    violation_behaviour: "併入會讓 AC3.1.2（獨立段不含共享訊息）在反方向被破壞，且 AC6.1.3 的負向驗收失去意義"
    source: "unit-of-work.md:133 逐字「不併入共享流」；AC3.1.2；AC6.1.3"
  - id: BR2.7
    statement: "模式變更的狀態訊息仍扇出給該 key 的全部存活連線，並帶頁面識別供客戶端自行過濾。"
    category: policy
    applies_to: "sharing_mode 狀態訊息（由 U13 送出）"
    trigger: "pageModes 任一鍵改變"
    logic: "IF pageModes[P] 改變 THEN 送出一則帶範圍 P 的狀態訊息給該 key 的全部存活連線；非該頁的客戶端忽略它"
    violation_behaviour: "改成「只送給同頁連線」會需要伺服器知道每條連線屬於哪一頁，那要改握手（見 functional-spec.md 的 D-S10-1 為何不走這條）"
    source: "x-concurrent-connections.state_change_fanout 逐字「推送給該 key 的全部存活連線」——本規則刻意**不改**這條，只給 payload 加識別欄位"

  - id: BR2.8
    statement: "共享工作階段恰涵蓋三頁；/cost 與 /admin/* 不讀任何段，也不出現在 pageModes。"
    category: constraint
    applies_to: "pageModes；段的讀取"
    trigger: "任何頁面要求讀取或切換段"
    logic: "IF 頁面不在 {入口頁, /workspace, /assessment} 內 THEN 它既不讀任何段，也不得出現在 pageModes 的鍵集合中"
    violation_behaviour: "讓 /cost 或 /admin/* 讀到共享段會使該頁出現脈絡列，違反 AC2.1.3"
    source: "FR2.1 逐字「不含 /admin/* 與 /cost」；K-09.shared_scope 逐字「共享工作階段涵蓋統一入口、/workspace、/assessment 三處，不含 /admin/* 與 /cost」；AC2.1.3"

  # ── 群組 3：對話歷程 ───────────────────────────────────────────────────
  - id: BR3.1
    statement: "append_message 必須帶段識別；沒有段識別的追加是錯誤，不得預設為共享段。"
    category: validation
    applies_to: "SessionStore.append_message"
    trigger: "追加一則訊息"
    logic: "IF 呼叫未指明段 THEN 拒絕；不預設任何段"
    violation_behaviour: "拒絕。預設為共享段正是 OQ-N4 逐字指出的兩種壞結果之一（「附加進同一份歷程 → FR3.2 在切回時被違反」）"
    source: "OQ-N4 逐字「append_message(session_key, role, text) 沒有任何參數說這則訊息屬於哪一段」"
  - id: BR3.2
    statement: "一個段的讀取視圖只含該段自己的訊息。"
    category: constraint
    applies_to: ConversationSegment
    trigger: "讀取某段的歷程"
    logic: "IF 讀取段 S 的歷程 THEN 只回 S 的訊息，不含任何其他段的訊息"
    violation_behaviour: "違反 FR3.2 逐字「新對話不共享任何訊息歷程」"
    source: "FR3.2；AC3.1.2；AC6.1.3"
  - id: BR3.3
    statement: "段內訊息的順序即寫入順序，且該順序對讀取端穩定。"
    category: constraint
    applies_to: "ConversationSegment.messageHistory"
    trigger: "讀取歷程"
    logic: "IF 讀取 THEN 以 sequence 遞增序回傳"
    violation_behaviour: "順序不穩定會讓 U11 的「第 N−1 輪產出」無法定位，FR6.1 失效"
    source: "FR6.1 逐字「第 N 輪應能正確解析指向第 N−1 輪產出的指涉詞」"
  - id: BR3.4
    statement: "筆數上限**每段獨立計算**；超限時丟棄該段最舊的訊息。"
    category: policy
    applies_to: "ConversationSegment.messageHistory"
    trigger: "追加後該段筆數超過上限"
    logic: "IF 該段筆數 > 上限 THEN 自該段最舊端丟棄到等於上限為止；其他段不受影響"
    violation_behaviour: "套在「全部段之和」上會讓一頁的活躍對話擠掉另一頁的歷程，而兩者在使用者眼中無關"
    source: "DG-5（數值由 nfr-requirements 定）；段數上界為 3（entities.md EC4）故總量仍有界"
  - id: BR3.5
    statement: "筆數上限的參數缺值時，服務不得啟動；不得把「無值」解讀為「無上限」。"
    category: validation
    applies_to: "本單元的啟動設定"
    trigger: "服務啟動"
    logic: "IF 上限參數未設定 THEN 大聲失敗並列出需要的設定；不以無上限啟動"
    violation_behaviour: "以無上限啟動會讓單一 Redis key 無上界成長，而這是無聲的"
    source: "既有前例 ADR-008／K-01 的 EMBEDDING_PROVIDER 逐字「刻意無預設：偵測不到選定提供者時須大聲失敗」"
  - id: BR3.6
    statement: "訊息內容不得出現在任何 log、錯誤訊息或例外文字中。"
    category: constraint
    applies_to: "SessionMessage.text 與整個 ConversationSegment"
    trigger: "任何記錄或拋出"
    logic: "IF 要記錄或拋出 THEN 只帶 sessionKey 與段識別，不帶 text、不帶整個物件"
    violation_behaviour: "本 repo 為 public、Actions log 公開可讀，而本單元持有個人對話內容"
    source: "project.md 逐字「一次意外 echo 即等同公開發布」；entities.md EC6"

  # ── 群組 4：作業對象（[S3]=A 分段） ────────────────────────────────────
  - id: BR4.1
    statement: "作業對象掛在段層——每一段各自一組三層識別。"
    category: constraint
    applies_to: "ConversationSegment 的三個作業對象欄位"
    trigger: "任何讀寫作業對象"
    logic: "IF 讀或寫作業對象 THEN 一律指明是哪一段的"
    violation_behaviour: "單一組共用會讓 AC3.1.4 的「作業對象與我離開時相同」不可能成立（使用者可在獨立段改它）"
    source: "[S3]=A。**本條推翻** x-session-key-derivation.why_one_key.therefore 逐字的「同一組」，見 entities.md 的推翻對照表第 2 列"
  - id: BR4.2
    statement: "新建一個獨立段時，以當前共享段的作業對象初始化它。"
    category: calculation
    applies_to: "BR2.4 的建立路徑"
    trigger: "segments[P] 首次建立"
    logic: "IF 建立 segments[P] THEN 其三個作業對象欄位 = 共享段當下的三個值（逐欄複製，含 null）"
    violation_behaviour: "不初始化會讓 AC3.1.3（獨立對話第一則訊息說「這張圖」即可指向切換前那張）失敗"
    source: "FR3.2 逐字「沿用當前的作業對象」；AC3.1.3"
  - id: BR4.3
    statement: "set_work_target 必須帶段識別，且只改該段。"
    category: constraint
    applies_to: "SessionStore.set_work_target"
    trigger: "設定作業對象"
    logic: "IF 呼叫帶段 S THEN 只寫 S 的三個欄位；其他段不動"
    violation_behaviour: "寫到別段會讓該段的「離開時狀態」被遠端改寫"
    source: "[S3]=A；AC3.1.4"
  - id: BR4.4
    statement: "切回共享模式時，讀回共享段自己的作業對象，不沿用獨立段的值。"
    category: policy
    applies_to: "set_sharing_mode(P, shared) 之後的讀取"
    trigger: "pageModes[P] 變回 shared"
    logic: "IF 切回共享 THEN 該頁讀共享段的歷程與共享段的作業對象——兩者都與離開時相同"
    violation_behaviour: "沿用獨立段的值即違反 AC3.1.4 的 Then（它逐字要求訊息歷程**與作業對象**兩樣都相同）"
    source: "AC3.1.4；[S3]=A"
  - id: BR4.5
    statement: "作業對象允許部分三元組；本單元不推導上層、不補齊、不因缺層而拒絕。"
    category: validation
    applies_to: "ConversationSegment 的三個作業對象欄位"
    trigger: "儲存 K-07 解析後的結果"
    logic: "IF 解析結果某層為 null THEN 原樣儲存 null；不嘗試推導，不拒絕"
    violation_behaviour: "拒絕會讓 OPEN-H11 的既有架構圖無法被選為作業對象；推導會與 K-07 形成兩套可能分歧的規則"
    source: "entities.md EC7／EC8；hierarchy_service.py:261-273 的實測行為；K-02 的 WorkTargetPayload 逐字把階層一致性歸給 U7"
  - id: BR4.6
    statement: "作業對象一律先經 K-07 的 HierarchyFacade.resolve_work_target 驗證，再儲存。"
    category: authorization
    applies_to: "SessionStore.set_work_target"
    trigger: "設定作業對象"
    logic: "IF 設定作業對象 THEN 先以呼叫方傳入的 principal 呼叫 K-07 解析；成功則存解析結果，失敗則原樣向上傳遞例外"
    violation_behaviour: "少了這一步，本單元可以把任何人的識別碼解析成合法的作業對象"
    source: "K-09.set_work_target.note 逐字「經 K-07 的 HierarchyFacade.resolve_work_target 驗證三層識別……HierarchyForbidden 原樣向上傳遞」；hierarchy_facade.py:277-281 逐字「這是同進程路徑，沒有任何 router 層會替它補上範圍檢查」"
  - id: BR4.7
    statement: "每一段的作業對象各自驗證——不得因共享段驗過就讓獨立段沿用未驗的值。"
    category: authorization
    applies_to: "BR4.2 的初始化路徑與 BR4.3 的寫入路徑"
    trigger: "建立新段（BR4.2）或設定某段的作業對象（BR4.3）"
    logic: "IF 寫入任何段的作業對象 THEN 該次寫入自己經過 BR4.6 的驗證"
    violation_behaviour: "作業對象自 [S3]=A 起變成**每段一組**，驗證若仍只做一次，就會有 N−1 組未驗的值"
    source: "ADR-0006 的 IAM 面在本單元的新落點（見 functional-spec.md §六）。BR4.2 的複製來源是**已驗證過的**共享段值，故初始化路徑以「來源已驗證」滿足本條，不需重驗——此例外逐字記於此，不留給實作推測"

  # ── 群組 5：授權委派與暴露面 ───────────────────────────────────────────
  - id: BR5.1
    statement: "本單元不自行判權。"
    category: authorization
    applies_to: "K-09 的全部方法"
    trigger: "任何呼叫"
    logic: "IF 需要授權判定 THEN 委派給 K-07（作業對象）或由呼叫方負責；本單元不讀 role_permissions、不呼叫 require_story_action"
    violation_behaviour: "自建第二套判定會與 K-07 分歧，且兩層 facade 不得互相假設對方已檢查"
    source: "K-09.behaviour_semantics.authorization_responsibility 逐字「本單元不自行判權；set_work_target 的授權由 K-07 承擔」"
  - id: BR5.2
    statement: "本單元不自行從請求取身分；principal 一律由呼叫方傳入。"
    category: constraint
    applies_to: "SessionStore.set_work_target"
    trigger: "需要身分時"
    logic: "IF 需要 principal THEN 使用參數傳入的那一個；不讀 request、不讀 websocket、不讀模組層狀態"
    violation_behaviour: "自取身分會讓同進程呼叫者得以用別人的身分寫入"
    source: "K-07 的 identity_passing 形狀；hierarchy_facade.py 的同型約束"
  - id: BR5.3
    statement: "本單元不暴露任何 HTTP 或 WebSocket 端點。"
    category: constraint
    applies_to: "整個單元"
    trigger: "任何時刻"
    logic: "IF 有人要為本單元加一條對外路徑 THEN 不加——對外面一律經 U13 的既有端點"
    violation_behaviour: "新增對外面會繞過 U13 的握手與身分驗證"
    source: "K-09 的 in-process 宣告；consumers 逐字為 [U11, U12, U13] 三個同進程元件"

  # ── 群組 6：失效行為與冪等 ─────────────────────────────────────────────
  - id: BR6.1
    statement: "Redis 不可用時大聲失敗——不降級、不退回行程記憶體、不以空 session 繼續。"
    category: policy
    applies_to: "K-09 的全部方法"
    trigger: "Redis 連線或指令失敗"
    logic: "IF Redis 不可用 THEN raise SessionBackendUnavailable 向上傳遞；不回傳空的 BrainSession"
    violation_behaviour: "回空 session 會讓使用者的脈絡**看起來**只是被清掉，與 TTL 到期不可區分——那是最壞的無聲失敗"
    source: "K-09.public_interface 的每一個方法都列 raises: [SessionBackendUnavailable]；NFR4 禁止行程記憶體退路；construction.md 逐字「Errors must be surfaced」"
  - id: BR6.2
    statement: "load／touch／set_work_target／set_sharing_mode 冪等可重試；append_message 非冪等。"
    category: constraint
    applies_to: "K-09 的全部方法"
    trigger: "重試"
    logic: "IF 重試冪等方法 THEN 結果與單次相同；IF 重試 append_message THEN 會產生第二則訊息"
    violation_behaviour: "把 append_message 當成冪等會讓重試製造重複訊息"
    source: "K-09.behaviour_semantics.retry_and_idempotency 逐字"
  - id: BR6.3
    statement: "本單元不負責訊息重播；重連的客戶端不會收到已送出的輪次訊息。"
    category: constraint
    applies_to: "與 U13 的邊界"
    trigger: "客戶端重連"
    logic: "IF 客戶端重連 THEN 由 U13 依 BR7.3 推送**當前狀態**；本單元不保留已送出的輪次訊息"
    violation_behaviour: "把狀態推送誤當成歷史重播會讓兩者的責任混在一起"
    source: "x-retry-and-idempotency.server_side 逐字「伺服器不重送已送出的訊息；不緩衝、不重播」；x-concurrent-connections.fanout_vs_no_replay 逐字區分兩者"

  # ── 群組 7：重啟還原與可達狀態 ─────────────────────────────────────────
  - id: BR7.1
    statement: "backend 重啟後，既有 session 的全部段、歷程、每段作業對象與每頁模式完整還原。"
    category: constraint
    applies_to: BrainSession
    trigger: "backend 重啟"
    logic: "IF 重啟且 TTL 未到期 THEN 全部狀態原樣可讀；不得有任何欄位因重啟而遺失或回到預設"
    violation_behaviour: "任何只存在行程記憶體的欄位都會在這裡現形"
    source: "NFR4 的可測不變量逐字「重啟 backend 後，既有對話的脈絡與作業對象仍可完整還原」；AC2.1.4"
  - id: BR7.2
    statement: "「尚未選定」是一個真正可達的狀態，而非只在首次使用可達一次。"
    category: constraint
    applies_to: "ConversationSegment 的三個作業對象欄位"
    trigger: "TTL 到期後再次進入，或使用者清除某層的選定"
    logic: "IF TTL 到期 THEN 下次進入時全部段的作業對象皆為未選定"
    violation_behaviour: "若該狀態不可達，脈絡列宣告的「尚未選定」就是死碼"
    source: "ADR-005 的 Consequences 逐字「no-object 狀態因此真的可達（不只首次使用），ContextBar 宣告的該狀態不再是死碼」；AC2.2.3"
  - id: BR7.3
    statement: "連線建立時，推送該 key 每一段的當前狀態與每頁的當前模式，各帶識別。"
    category: policy
    applies_to: "與 U13 的邊界（on_connect）"
    trigger: "新連線建立"
    logic: "IF 新連線建立 THEN 推送 pageModes 的每一鍵與每一存在段的作業對象，各帶識別；客戶端取屬於自己那一頁的"
    violation_behaviour: "只推送「當前模式」這個單一值會讓逐頁模式在重連後不可知，該頁會回到錯誤的段"
    source: "x-concurrent-connections.on_connect 逐字「新連線建立時推送當前 work_target 與 sharing_mode（見 K-02），使該頁的脈絡列立即正確，無需額外讀取端點」——本條只把它擴為逐段／逐頁"
```

## 規則摘要（**由腳本自上方 YAML 區塊實算產生**）

> 產生方式：以 `^  - id: (BR\d+\.\d+)$` 與 `^    category: (\w+)$` 兩條 regex 自同一份
> 檔案解析，群組計數為解析結果的分組大小，總數為解析結果的長度。
> 本表的任何數字都**不是**手寫的——`project.md` 記載的「`rules.md` 總數寫 22、實際 24」
> 那次失誤正是手寫造成的。本摘要在 `BR2.8` 補入後**整表重跑**，不是只改那一格。

| 群組 | 主題 | 條數 | 類別 |
|---|---|---|---|
| `BR1.x` | session 身分與存活期 | **6** | constraint／policy／validation |
| `BR2.x` | 段與共享模式 | **8** | authorization／constraint／policy／validation |
| `BR3.x` | 對話歷程 | **6** | constraint／policy／validation |
| `BR4.x` | 作業對象 | **7** | authorization／calculation／constraint／policy／validation |
| `BR5.x` | 授權委派與暴露面 | **3** | authorization／constraint |
| `BR6.x` | 失效行為與冪等 | **3** | constraint／policy |
| `BR7.x` | 重啟還原與可達狀態 | **3** | constraint／policy |
| | **合計** | **36** | |

### 類別分佈

| 類別 | 條數 |
|---|---|
| constraint | **17** |
| policy | **9** |
| validation | **5** |
| authorization | **4** |
| calculation | **1** |

### 全部規則識別碼（供 `traceability.json` 的 target 逐一核對）

`BR1.1`、`BR1.2`、`BR1.3`、`BR1.4`、`BR1.5`、`BR1.6`、`BR2.1`、`BR2.2`、`BR2.3`、`BR2.4`、`BR2.5`、`BR2.6`、`BR2.7`、`BR2.8`、`BR3.1`、`BR3.2`、`BR3.3`、`BR3.4`、`BR3.5`、`BR3.6`、`BR4.1`、`BR4.2`、`BR4.3`、`BR4.4`、`BR4.5`、`BR4.6`、`BR4.7`、`BR5.1`、`BR5.2`、`BR5.3`、`BR6.1`、`BR6.2`、`BR6.3`、`BR7.1`、`BR7.2`、`BR7.3`

## 讀法：哪幾條是本站**新定**的，哪幾條只是把上游寫下來

這個區分對下游很重要——只是轉錄的規則，改動它要回上游；本站新定的規則，
改動它在本站就能談。

| 性質 | 規則 | 說明 |
|---|---|---|
| **本站新定**（三題定案的直接後果） | `BR2.3`／`BR2.4`／`BR2.5`／`BR3.1`／`BR3.4`／`BR4.1`／`BR4.3`／`BR4.4`／`BR4.7` | `[S1]`=A 逐頁、`[S2]`=A 保留且可重入、`[S3]`=A 作業對象分段 |
| **本站新定**（上游未涵蓋的缺口） | `BR2.6`／`BR2.7`／`BR3.5`／`BR3.6`／`BR4.5`／`BR6.1`／`BR7.3` | 合併禁令、扇出帶識別、上限缺值大聲失敗、日誌禁令、部分三元組、Redis 失效不降級、逐段推送 |
| **轉錄上游**（改它要回上游） | `BR1.1`–`BR1.6`／`BR2.1`／`BR2.2`／`BR2.8`／`BR3.2`／`BR3.3`／`BR4.2`／`BR4.6`／`BR5.1`–`BR5.3`／`BR6.2`／`BR6.3`／`BR7.1`／`BR7.2` | 每一條的 `source` 欄都指向逐字出處 |

**`BR4.7` 是這批裡最容易被漏掉的一條**：`[S3]`=A 把作業對象從一組變成每段一組，
而 `K-07` 的授權檢查原本只在「設定作業對象」時跑一次。若實作沿用原形狀，
段數一多就會有 N−1 組未經檢查的值——這是 `[S3]`=A 自己製造出來的 IAM 面，
不是上游既有的。故本條把它的例外（初始化路徑的來源已驗證）也逐字寫出來，
不留給實作推測。

**`BR2.8` 是追溯自檢補上的**：寫 `traceability.json` 時發現 `AC2.1.3`
（`/cost` 與 `/admin/*` 不顯示共享脈絡列）在原本的 35 條規則裡**沒有任何一條承接**
——`EC2` 只說了 `pageModes` 的鍵集合，沒說「不在共享範圍的頁面不讀任何段」。
這一條是上游 `FR2.1` 與 `K-09.shared_scope` 的轉錄，不是新決定。
