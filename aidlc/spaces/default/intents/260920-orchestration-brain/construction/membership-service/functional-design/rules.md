# 業務規則 — `U19 membership-service`

> 計數一律由 parser 解析本檔 yaml 區塊的 `rules[].id` 實算。
> 規則 id 前綴為 **`BR`**（框架的 `ID_PATTERNS.BR` 為 `/\bBR\d+\.\d+\b/`）。
>
> **本檔所有以反引號開頭的純量都加了引號**——`U5`／`U7`／`U18` 那幾輪各踩過一次
> 「反引號開頭的 YAML 純量使整個區塊不解析，而五個 sensor 全綠因為沒有一個解析它」。

## 本檔的範圍

本單元是 `service`：交付 per-project 授權判定的**唯一來源**、成員生命週期
（邀請／移出／角色變更）、**自動改選**與其稽核、以及「專案不得失去最後一位管理者」
的**共同上游守門**；另擴充一處既有端點（停用使用者）的回應契約。

**不在本檔**：三張表的 DDL（契約 `K-15`，屬 `U18`）、需求欄位的讀寫（`K-17`，屬 `U20`）、
成員頁畫面（`U24`）、全域功能權限的判定（既有 `require_story_action`，**本元件不得重新實作**）。

```yaml
rules:
  # ---- BR1.x 授權模型（K-16 的 authorization_model）----
  - id: BR1.1
    statement: >
      受保護操作的唯一入口是 MembershipFacade，且它同時是 per-project 授權判定的
      唯一提供者。
    category: authorization
    applies_to: 全部受保護操作
    trigger: 任何讀寫成員關係或依賴 per-project 角色的操作
    logic: >
      IF 呼叫端需要知道「某 principal 在某 project 是什麼角色」或需要改動成員關係
      THEN 必經本 facade；禁止跳過它直接讀 project_members 表。
    violation_behaviour: >
      繞過者得到未經授權檢查的資料。**此規則無機械強制**（同 `K-07` 的 `OQ-N2`）
      ——殘留缺口如實記載，不宣稱已守住。
    source: "契約 `K-16` 的 `authorization_model.sole_entry` ＋ `ADR-012`"

  - id: BR1.2
    statement: >
      兩層串聯：全域功能權限那一層由既有 require_story_action 承載，per-project
      那一層由本 facade 判定；任一層不過即拒。
    category: authorization
    applies_to: 專案資料的任何存取
    trigger: 存取專案資料時
    logic: >
      IF 全域層不過 THEN 拒絕；ELSE IF per-project 層不過 THEN 拒絕；ELSE 允許。
    violation_behaviour: >
      只檢查一層會讓「具全域權限但非本專案成員」的人讀到專案資料
      ——`AC12.5.2` 的 deny 側正是它。
    source: "`FR12.6` ＋ 契約 `K-16` 的 `two_layer_rule`"

  - id: BR1.3
    statement: >
      `sync` 同進程呼叫本 facade 是**預期且允許**的；被禁止的是跳過 facade
      直接讀表。
    category: policy
    applies_to: U20／U13／U21 對本 facade 的呼叫
    trigger: 同進程呼叫時
    logic: IF 呼叫經由 facade THEN 允許，不論是同進程或跨進程。
    violation_behaviour: >
      不適用——本條是**消歧義宣告**。寫下它的理由：`ADR-012` 明記這兩件事不同，
      而 `ProjectHierarchy` 上一輪正是把它們寫成同一句話而自相矛盾
      （`project.md` 的 `domain-design:72ea0719` 記過）。
    source: "契約 `K-16` 的 `forbidden_bypass` 逐字"

  - id: BR1.4
    statement: >
      principal 由呼叫端傳入，facade 不自行從 request 取身分；projectId 為具名參數，
      不得藏在 payload 內。
    category: authorization
    applies_to: 每一個 facade 方法
    trigger: 方法呼叫時
    logic: >
      第一個參數為 principal（已驗證身分 ＋ 其全域角色）；資源上下文以具名參數傳遞。
    violation_behaviour: >
      facade 自取身分會讓 `U13`（WebSocket）無法使用它——握手之後每則訊息都在同一個
      連線裡、**不經 FastAPI 的 dependency 鏈**，故它必須自行保存握手時的 principal
      並逐次傳入。
    source: "契約 `K-16` 的 `identity_passing` ＋ `resource_context`"

  - id: BR1.5
    statement: >
      授權未通過時 raise MembershipForbidden（或 MissingGlobalPermission），
      **不是** HTTPException；判定先於任何讀寫，失敗即中止。
    category: authorization
    applies_to: 全部受保護操作
    trigger: 授權判定未通過時
    logic: >
      IF 判定未過 THEN raise 領域例外並中止；router 層負責轉 403。
      同進程呼叫端自行處置。
    violation_behaviour: >
      raise HTTPException 會讓同進程呼叫端（`U20`／`U13`）被迫處理 HTTP 層型別，
      而 `U13` 是 WebSocket，根本沒有 HTTP 回應可回。
    source: "契約 `K-16` 的 `on_denied` ＋ `hard_rule`"

  - id: BR1.6
    statement: >
      resolveProjectRole 回 None 代表**非成員**，呼叫端須當成拒絕，不得當成預設角色。
    category: authorization
    applies_to: resolveProjectRole 的回傳值
    trigger: 判定 per-project 角色時
    logic: IF 查無該 (project, user) 列 THEN 回 None；呼叫端 IF None THEN 拒絕。
    violation_behaviour: >
      把 None 當成 `member` 會讓**任何**具全域權限的人取得專案的一般成員權限
      ——`AC12.5.2` 的 deny 側直接失效。
    source: "契約 `K-16` 的 `public_interface` 第一項逐字"

  # ---- BR2.x 共同上游守門（[FD1]=A）----
  - id: BR2.1
    statement: >
      **每個專案在任何時刻至少有一位 role 為 project_admin 的成員。**
      三條路徑（停用帳號、自我降級、自我移出）必須經過**同一個**守門判定，
      且該判定位於三者的共同上游。
    category: constraint
    applies_to: assertCanDeactivate／changeRole／removeMember
    trigger: 任何可能減少某專案管理者數的操作執行前
    logic: >
      IF 該操作完成後某專案的 project_admin 數會變成 0
      THEN raise LastAdminGuard(projects=[那些專案]) 並中止。
    violation_behaviour: >
      留下**沒有任何管理者的專案**：沒人能邀人、沒人能改角色，而成員仍看得到它。
      `[FD1]`=A 的選擇理由正是三個選項裡只有它不會產生這種死專案。
    source: "`[FD1]`=A ＋ 契約 `K-16` 的 `last_admin_guard` ＋ `AC12.3.1`–`.3`"

  - id: BR2.2
    statement: >
      **不另立「至少一位成員」的謂詞。**
    category: policy
    applies_to: 守門的實作
    trigger: 實作 BR2.1 時
    logic: >
      BR2.1 成立 ⇒ 每個專案至少有一位管理者 ⇒ 至少有一位成員。
      故成員那一面是**推論**，不是獨立規則。
    violation_behaviour: >
      不適用——本條是**禁止**：加上第二個謂詞會是一段永不獨立命中的死碼，
      而 `project.md` 記過「不可達的規則是死碼，卻在文件上長得像已解決」。
    source: "`[FD1]`=A 的後果 1 與 3"

  - id: BR2.3
    statement: >
      守門判定**唯讀、無副作用**，且可安全重試。
    category: constraint
    applies_to: assertCanDeactivate
    trigger: 既有停用端點呼叫它時
    logic: 只查詢、不寫入；同一輸入多次呼叫結果相同。
    violation_behaviour: >
      有副作用的守門在被拒的路徑上會留下殘留狀態，而 `AC12.5.3`
      要求「拒絕不留下半套狀態」。
    source: "契約 `K-16` 的 `observable_side_effects` 第三項逐字"

  # ---- BR3.x 成員生命週期 ----
  - id: BR3.1
    statement: >
      建立專案者自動成為該專案的 project_admin，且該寫入與專案建立在**同一個交易**內。
    category: constraint
    applies_to: 建立專案的流程
    trigger: 專案建立時
    logic: >
      IF 專案建立成功 THEN 必然存在一列 (projectId, 建立者, project_admin)；
      兩者同交易，任一失敗則一起回滾。
    violation_behaviour: >
      分開交易會出現**沒有管理者的專案**——而 BR2.1 的守門只在「減少管理者」時觸發，
      擋不住「一開始就沒有」。
    source: "`FR12.1` ＋ `components.md:538-539` 逐字"

  - id: BR3.2
    statement: >
      缺少對應全域功能權限的使用者**不得被邀請**；被拒時不得留下半套狀態。
    category: validation
    applies_to: inviteMember
    trigger: 邀請執行前
    logic: >
      IF 受邀者缺少對應的全域功能權限 THEN raise MissingGlobalPermission 並中止；
      整個操作在**單一交易**內，故被拒時成員清單不新增任何列。
    violation_behaviour: >
      `AC12.5.1`（說明他缺什麼）與 `AC12.5.3`（清單未新增任何列）同時失效。
      半套狀態尤其危險：清單多一列而那個人實際上用不了專案。
    source: "`FR12.6a` ＋ `AC12.5.1`／`AC12.5.3` ＋ 契約 `K-16` 的 `invite_member.note`"

  - id: BR3.3
    statement: >
      inviteMember **非冪等**：重複邀請同一 (project, user) 必須被拒，不得建立第二列。
    category: validation
    applies_to: inviteMember
    trigger: 邀請已是成員者時
    logic: IF 該 (project, user) 已存在 THEN 拒絕；呼叫端不得自動重試。
    violation_behaviour: >
      建立第二列會讓 resolveProjectRole 的結果取決於查詢順序
      ——而 `project_members` 的唯一約束會先擋下它，故真正的失敗是**錯誤訊息無意義**
      （資料庫層的唯一約束違反而非業務語意）。
    source: "契約 `K-16` 的 `retry_and_idempotency` 第一項逐字"

  - id: BR3.4
    statement: >
      removeMember 對「該使用者已不是成員」**回成功**（冪等），不 raise。
    category: policy
    applies_to: removeMember
    trigger: 移出一個已非成員者時
    logic: IF 查無該列 THEN 視為成功（回 None）。
    violation_behaviour: >
      不適用——本條是 `[FD2]`=A 的定案。契約逐字把它留給實作（「由實作定但須一致」），
      故這裡的價值在於**把它固定下來**：`U24` 因此不需要處理「404 其實是成功」，
      競態下兩位管理者同時移除同一人時兩邊畫面一致。
    source: "`[FD2]`=A ＋ 契約 `K-16` 的 `retry_and_idempotency` 第二項"

  - id: BR3.5
    statement: >
      一個專案可同時有**多位** project_admin；指定第二位**不得覆寫**第一位。
    category: constraint
    applies_to: changeRole
    trigger: 把某成員改為 project_admin 時
    logic: >
      IF 已有其他 project_admin THEN 新增而非取代——角色不互斥。
    violation_behaviour: >
      覆寫會讓第一位管理者**靜默失去權限**。`AC12.2.4` 刻意斷言
      「兩位都能執行管理動作」，使覆寫成為可觸發的紅燈。
    source: "`FR12.3` ＋ `AC12.2.4`"

  - id: BR3.6
    statement: >
      成功邀請與成功移出是**一級行為**，不是拒絕條款的反面。
    category: constraint
    applies_to: inviteMember／removeMember
    trigger: 操作成功時
    logic: >
      成功邀請 ⇒ 成員清單必然多一列；成功移出 ⇒ 必然少一列，且該成員其後讀取
      本專案資料被拒。
    violation_behaviour: >
      只驗拒絕面會讓「邀請其實沒寫進去」通過全部測試
      ——`[US:review-02 R-01]` 的唯一 Critical 正是它：其餘九條 AC 的 Given
      都預設「該專案另有成員」，而在 `US12.6` 落地前沒有任何東西產生那個人。
    source: "契約 `K-16` 的 `invite_member`／`remove_member` note 逐字 ＋ `US12.6`"

  # ---- BR4.x 自動改選與純函式 ----
  - id: BR4.1
    statement: >
      selectSuccessor 是**純函式，不讀 DB**：輸入成員集合、輸出被選中者。
    category: constraint
    applies_to: selectSuccessor
    trigger: 設計與實作時
    logic: >
      簽章只接受 list[MemberSnapshot]；不得注入 session、不得讀取任何外部狀態。
    violation_behaviour: >
      讀 DB 會讓 ADR-0006 的 PBT hard constraint **失去作用對象**
      ——property-based 測試無法對一個需要資料庫的函式生成輸入。
      這是結構前提，不是風格偏好。
    source: "契約 `K-16` 的 `select_successor` ＋ `unit-of-work.md:448` 逐字"

  - id: BR4.2
    statement: >
      挑選規則為「最早加入」，平手時以 (joinedAt, userId) 做**決定性** tie-break。
    category: calculation
    applies_to: selectSuccessor
    trigger: 自動改選時
    logic: >
      以 (joinedAt, userId) 為排序鍵取最小者。形狀沿用 repo 既有的
      best_clouds（`backend/cost/estimate_readers.py:247-251`，
      `key=lambda item: (-item[1], item[0])`）。
    violation_behaviour: >
      只以 joinedAt 排序時，兩位成員加入時間完全相同就**沒有穩定順序**
      ——`ORDER BY` 的結果取決於資料庫回傳順序，每次改選可能選出不同人，
      而這是**靜默的**：沒有錯誤，只有不穩定的結果。`AC12.4.2` 正是它的斷言。
    source: "`FR12.4`／`FR12.4a` ＋ `AC12.4.1`／`AC12.4.2`"

  - id: BR4.3
    statement: >
      自動改選**必須冪等**：owner 已被停用且該專案已有新管理者時，重跑不得再選一次。
    category: constraint
    applies_to: 自動改選流程
    trigger: 重跑或部分失敗後重試時
    logic: >
      IF 該專案已有 project_admin（排除被停用的 owner）THEN 不執行改選、不寫事件。
    violation_behaviour: >
      部分失敗後的重跑會產生**第二次改選事件**，使橫幅重複出現且稽核多一筆
      不曾發生的變更。
    source: "契約 `K-16` 的 `retry_and_idempotency` 第四項逐字"

  - id: BR4.4
    statement: >
      自動改選的觸發條件是 project_owner 的**帳號被停用**，不是專案被刪除或成員離開。
    category: policy
    applies_to: 自動改選流程
    trigger: 停用帳號成功之後
    logic: >
      IF 被停用者是某專案的 owner 且該專案另有成員 THEN 對該專案執行一次改選。
    violation_behaviour: >
      與 BR2.1 的守門次序有關：守門先判（可能擋下整個停用），改選在停用**成功之後**
      才跑。次序反了會對一個其實沒被停用的帳號產生改選事件。
    source: "`FR12.4` ＋ `AC12.4.1` 的 Given（「帳號**已被**停用」）"

  # ---- BR5.x 稽核（[FD3]=A）----
  - id: BR5.1
    statement: >
      角色變更與自動改選**皆**須留稽核，記下誰、何時、對誰、舊角色、新角色。
    category: constraint
    applies_to: changeRole／自動改選
    trigger: 任何 per-project 角色變更成功時
    logic: 寫一列 ReselectionEvent，五個事實齊備。
    violation_behaviour: >
      不留紀錄則**事後無從得知某人的 project_admin 是怎麼來的**
      （`FR12.4b` 逐字）。自動改選尤其必要：它由系統發起、無人按下按鈕。
    source: "`FR12.4b` ＋ 契約 `K-16` 的 `auditing.rule`"

  - id: BR5.2
    statement: >
      稽核**不得只沿用** `_audit_append`。
    category: constraint
    applies_to: 稽核的承載形式
    trigger: 實作稽核時
    logic: >
      必須寫進 UI 讀得到的持久層（ReselectionEvent）；
      `_audit_append` 寫 logger.info，**UI 讀不到**。
    violation_behaviour: >
      `AC12.2.2` 斷言的是**使用者可見的**變更紀錄；寫進 log 會讓該 AC 永遠紅燈，
      而既有的三張稽核表都是 cost／estimate／diagram 範圍。
    source: "契約 `K-16` 的 `auditing.hard_constraint` ＋ `[US:Q-11]`（Critical）"

  - id: BR5.3
    statement: >
      兩種角色變更寫**同一張表**，以 cause 區分（auto_reselection／manual_role_change）。
    category: policy
    applies_to: ReselectionEvent 的寫入
    trigger: 寫稽核時
    logic: >
      自動改選 ⇒ cause = auto_reselection；人工 changeRole ⇒ cause = manual_role_change。
    violation_behaviour: >
      不適用——本條是 `[FD3]`=A 的定案。價值在於 `AC12.2.2` 的變更紀錄是
      **一次查詢、一個來源**，兩種來源天然按 occurredAt 合併；
      另立一張表則需 UNION 兩表並自行排序，且兩表欄位幾乎相同而違反
      `team.md` 的「單一真實來源」。
    source: "`[FD3]`=A ＋ `OPEN-ND18-3`（本站關閉）"

  - id: BR5.4
    statement: >
      previousOwnerUserId 在兩種 cause 下指**不同的人**，而這是刻意的。
    category: policy
    applies_to: ReselectionEvent.previousOwnerUserId
    trigger: 寫稽核時
    logic: >
      cause = auto_reselection ⇒ 被停用的 owner；
      cause = manual_role_change ⇒ **執行變更的管理者**（`AC12.2.2` 的「誰」）。
    violation_behaviour: >
      不適用——本條是**消歧義宣告**。兩者都回答「這次變更是誰造成的」。
      寫下它的理由：下一個人看到同一欄指兩種人會想拆成兩欄，
      而拆欄會讓 `AC12.2.2` 的查詢需要依 cause 取不同欄位。
    source: "`[FD3]`=A 的後果 ＋ `AC12.2.2` 的 Then（「誰在何時」）"

  - id: BR5.5
    statement: >
      acknowledgedAt 只對 cause = auto_reselection 有意義；manual_role_change 的列永遠為空。
    category: constraint
    applies_to: ReselectionEvent.acknowledgedAt
    trigger: 寫稽核與查詢橫幅時
    logic: >
      寫入 manual_role_change 時不設 acknowledgedAt；
      橫幅查詢**必須**同時過濾 cause = auto_reselection 與 acknowledgedAt IS NULL。
    violation_behaviour: >
      漏掉 cause 過濾會讓**每一次人工角色變更都彈出一則橫幅**
      ——而橫幅的文案是「系統自動把管理權交給你」，對人工變更是錯的訊息。
      這是 `[FD3]`=A 引入的新失敗面，故必須有自己的規則。
    source: "`[FD3]`=A 的後果 3 ＋ `FR12.4c` 的 Given"

  - id: BR5.6
    statement: >
      橫幅已讀狀態以**事件識別字**為鍵，不是 per-user 布林值。
    category: constraint
    applies_to: acknowledgedAt
    trigger: 使用者按下「知道了」時
    logic: 設定該**事件列**的 acknowledgedAt；不得以 (project, user) 的旗標取代。
    violation_behaviour: >
      per-user 布林值會讓同一人**第二次**被改選時看不到橫幅
      ——而那正是 `FR12.4c` 要防的情境。`AC12.4.4` 斷言跨裝置不再出現，
      故狀態必須在伺服器端而非瀏覽器。
    source: "契約 `K-16` ＋ `AC12.4.4` ＋ `FR12.4c-i`"

  # ---- BR6.x 既有端點的契約擴充 ----
  - id: BR6.1
    statement: >
      既有停用端點在執行 is_active 寫入**之前**呼叫 assertCanDeactivate；
      命中則回 **409** 並列出那些專案。
    category: constraint
    applies_to: 既有的停用使用者端點
    trigger: 停用請求進來時
    logic: >
      三道檢查全部在 `target_user.is_active = request.is_active` 之前執行：
      既有的自我停用守門、既有的最後一位可編輯角色全域管理員守門、本單元的新守門。
    violation_behaviour: >
      寫入之後才檢查等於沒有檢查。**這個檢查是唯一防線**：該端點做的是 UPDATE，
      外鍵對 UPDATE 零效力，而 `projects.owner_user_id` 的 COMMENT 逐字為
      「deletion behaviour ... deliberately NOT decided」——那是刻意留的未決項，
      不是既有的保護。
    source: "`FR12.5a` ＋ 契約 `K-16` 的 `existing_endpoint_extension`"

  - id: BR6.2
    statement: >
      route decorator 必須**顯式**宣告 409 的 response model。
    category: constraint
    applies_to: 既有停用端點的 route 宣告
    trigger: 加入 409 行為時
    logic: 'responses={409: {"model": LastAdminGuardReport}}'
    violation_behaviour: >
      實測 `openapi.json` 的 55 個 operation 宣告的狀態碼只有
      `{200:53, 422:45, 201:1, 204:1}`，**非 2xx/422 的宣告數為 0**。
      不顯式宣告則該契約不進 spec、前端產不出型別，
      而 `dump_openapi.py --check` **保持綠燈**——漂移閘門對本變更無效。
    source: "`FR12.5b`（更正後）＋ `[US:V-08]`"

  - id: BR6.3
    statement: >
      既有的兩道保護**不得被本變更削弱**。
    category: constraint
    applies_to: 既有停用端點
    trigger: 修改該端點時
    logic: >
      自我停用守門與最後一位可編輯角色的全域管理員守門照原樣保留；
      本單元的新守門與它們是**不同層級**（前兩者管全域與自我，新的管 per-project）。
      **本站實地核對後的行號**（`grep -n` 直接取，非從切片回推）：
      函式 `update_user_active` 在 `:645`；自我停用守門的條件在 `:654`、其 raise 在 `:655`；
      最後一位可編輯角色的全域管理員守門的條件在 `:676`、其訊息在 `:679`；
      `target_user.is_active = request.is_active` 在 `:682`。三道檢查都必須在 `:682` 之前。
    violation_behaviour: >
      重構該端點時把既有檢查一併改掉，會在加上一道保護的同時拿掉兩道。
      三者的位置與條件須在 code-generation 以測試逐一鎖住。
    source: "契約 `K-16` 的 `preserved_existing_protections`"

  - id: BR6.4
    statement: >
      本變更與其既有消費端**不可分批**部署。
    category: policy
    applies_to: Bolt 切分
    trigger: 規劃部署批次時
    logic: >
      改既有端點的回應契約，而 AdminPage.tsx 是既有消費端，兩者同批。
    violation_behaviour: >
      先部署後端會讓既有畫面收到一個它不認識的 409 而顯示未處理的錯誤。
      `delivery-planning:c6` 只適用於**既有**端點的回應形狀變更——這一條正是，
      故該約束在此**成立**（與 `U2` 那次判為不適用的理由正好相反）。
    source: "契約 `K-16` 的 `batch_constraint`；Bolt 切分仍是 2.9 的決定"
```

## 規則摘要（衍生檢視）

| 群組 | 條數 | 管什麼 | 消歧義宣告 |
|---|---|---|---|
| `BR1.x` | 6 | 授權模型（唯一入口、兩層串聯、`sync` 允許、principal 傳遞、拒絕形式、`None` 的語意） | `BR1.3` |
| `BR2.x` | 3 | `[FD1]`=A 的共同上游守門、不另立成員謂詞、守門唯讀 | `BR2.2` |
| `BR3.x` | 6 | 成員生命週期（建立者自動成管理者、邀請前置、非冪等、移出冪等、多位管理者、成功是一級行為） | `BR3.4` |
| `BR4.x` | 4 | 自動改選（純函式、決定性 tie-break、冪等、觸發條件） | — |
| `BR5.x` | 6 | 稽核（`[FD3]`=A 的同表、兩種 `cause`、`previousOwnerUserId` 的雙語意、`acknowledgedAt` 的範圍、事件為鍵） | `BR5.4` |
| `BR6.x` | 4 | 既有端點擴充（檢查次序、顯式 409、不削弱既有兩道、不可分批） | — |

合計 **29 條**（由 `yaml.safe_load` 解析本檔 yaml 區塊實算；逐群 6＋3＋6＋4＋6＋4＝29，相符）。

### 本單元最危險的三條

1. **`BR4.1`**（`selectSuccessor` 為純函式）。它不是風格偏好——違反它會讓
   ADR-0006 的 PBT hard constraint **失去作用對象**，而 PBT 在本單元是
   **blocking 而非 N/A**（這是本單元與 `U18`／`U5` 的關鍵差別）。
2. **`BR5.5`**（`acknowledgedAt` 只對自動改選有意義）。`[FD3]`=A 引入的新失敗面：
   橫幅查詢漏掉 `cause` 過濾，則**每次人工角色變更都彈一則橫幅**，而文案是
   「系統自動把管理權交給你」——對人工變更是錯的訊息。
3. **`BR6.2`**（顯式宣告 409）。違反它**不會有任何東西變紅**：spec 照樣通過
   漂移檢查，前端只是產不出型別。這是本單元唯一「違反後全綠」的規則。
