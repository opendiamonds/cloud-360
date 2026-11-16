# Rules — `U20 requirement-field-service`

## 一、識別字區段：`BR41.x`–`BR47.x`

`traceability` sensor 以 `BR<數字>.<數字>` 的形式掃**整份** `rules.md`，任何出現在
本檔的他單元識別字都會被當成本檔的孤兒規則。本 intent 已佔用的區段（實算 14 份
`rules.md`）：`BR1`–`BR8` 由 11 個 `service`／`spec`／`library` 單元各自使用（含同功能域
的 `U19 membership-service` 與 `U18 project-meta-data`，前者的識別字已寫進出貨程式的
docstring）、`BR21`–`BR28` 為 `U24`、`BR31`–`BR35` 為 `U15`。本單元取 **`BR41`–`BR47`**，
理由同 `U15`：沿用 `BR1.x` 會讓同一個識別字在同一個功能域裡指兩件無關的事。

**本檔刻意不寫出他單元識別字的字面形式**，引用時以「單元＋所指的事」描述。

## 二、規則（source of truth）

```yaml
rules:
  # ---- BR41：授權 --------------------------------------------------------
  - id: BR41.1
    statement: 待核准（pending／rejected）帳號一律拒絕，先於其他任何檢查
    category: authorization
    applies_to: RequirementFieldFacade 的三個公開方法
    trigger: 任何 read_fields／write_field／clear_field 呼叫
    logic: >
      IF principal.is_approved 為 false THEN 拒絕，理由為 pending；不查系統、不查角色、
      不讀不寫。
    violation_behaviour: raise RequirementFieldForbidden(story_id='K4', reason='pending')
    source: "ADR-0006 IAM 面；U15 修補時於 U8 落地的同一判定（hierarchy_facade.py 的 Principal.is_approved）"
    note: >
      U15 的審查查出「有角色的待核准帳號仍可通過授權」是跨 facade 的缺口（R-05，
      HierarchyFacade／MembershipFacade 仍未補）。本單元是新寫的 facade，直接在第一行
      補上，不留第三處同形缺口。

  - id: BR41.2
    statement: 全域層——讀需 K4.view，寫與清空需 K4.edit；在 facade 內評估，router 不掛 require_story_action
    category: authorization
    applies_to: RequirementFieldFacade
    trigger: 通過 BR41.1 之後
    logic: >
      IF action 為 read 且 user_can(role, 'K4', 'view') 為 false THEN 拒絕；
      IF action 為 write 或 clear 且 user_can(role, 'K4', 'edit') 為 false THEN 拒絕。
    violation_behaviour: raise RequirementFieldForbidden(story_id='K4', action=<action>, system_id=<id>)
    source: "FR12.6 兩層串聯；K-17 authorization_model；已交付的 U19 membership_facade.py:93-111 先例"
    note: >
      K-17 的 anti_double_check 字面寫「全域層由 router 承擔、facade 不得重複」，但
      U13 brain-gateway 是同進程呼叫端、不經 dependency 鏈——照字面做，U13 的路徑上
      全域層不會被檢查。U19 遇到同一件事，處置是 facade 以 user_can 自行評估、router
      不掛 dependency。本站依該已交付先例（project.md 的「已落地結構裁決」），
      anti_double_check 要防的「同一層檢查兩次」仍成立。

  - id: BR41.3
    statement: 系統存在與其所屬專案一律經 HierarchyFacade.get_project_of_system 取得；該呼叫隱含要求 K2.view
    category: authorization
    applies_to: RequirementFieldFacade
    trigger: 通過 BR41.2 之後
    logic: >
      呼叫 HierarchyFacade(db).get_project_of_system(principal, system_id)。
      IF 系統不存在 THEN 回 NotFound；IF 得到 HierarchyForbidden（呼叫端缺 K2.view）
      THEN 也回 NotFound，與 U19 對同一情形的處置一致（membership_facade.py 的
      _assert_project_exists）。
    violation_behaviour: raise RequirementFieldNotFound(system_id=<id>)
    source: "K-17 delegation；U7 的「同進程呼叫端不得繞過其 facade」；hierarchy_facade.py:374"
    note: >
      【review-01 R-04 更正】原理由寫「不以錯誤碼洩漏系統是否存在」，那不成立：
      持有 K4.view 的非成員對存在的系統得 403（BR41.4）、對不存在的系統得 404，
      而 system id 是可枚舉的整數，存在性仍可被探測。本站維持 K-17 on_denied 要求的
      Forbidden，不宣稱不洩漏存在性；能探測到的只有「某個 id 的系統存在」，取不到
      任何欄位內容。另：全部 11 個 canonical role 的 K2.view 皆為 True，故這個隱含
      前置今天只會擋到非 canonical role，但它是 BR41 的第三個全域權限，寫明以免漏看。

  - id: BR41.4
    statement: per-project 層——該專案的成員（project_admin 或 member）可讀，寫與清空亦同；非成員一律拒絕
    category: authorization
    applies_to: RequirementFieldFacade
    trigger: 通過 BR41.3、已知 project_id 之後
    logic: >
      role = MembershipFacade(db).resolve_project_role(principal, project_id)。
      IF role 為 None THEN 拒絕。IF role 為 project_admin 或 member THEN 放行
      （寫入是否允許已由 BR41.2 的 K4.edit 決定）。本單元不自行查 project_members 表。
    violation_behaviour: raise RequirementFieldForbidden(story_id='K4', action=<action>, system_id=<id>)
    source: "[FD4]=A；K-17 delegation（per-project 判定只有一份，ADR-012）；FR12.6"

  - id: BR41.5
    statement: 授權判定先於任何欄位的讀寫；拒絕時不讀、不寫、不回傳任何欄位值
    category: authorization
    applies_to: RequirementFieldFacade
    trigger: 每次呼叫
    logic: BR41.1 → BR41.2 → BR41.3 → BR41.4 依序；任一步失敗即中止，之後的驗證與存取都不發生。
    violation_behaviour: 不適用（本規則定義順序）
    source: "K-17 hard_rule"

  - id: BR41.6
    statement: 每次拒絕寫一行 log，欄位為 story_id、action、system_id、principal 的 user_id，不含任何欄位值
    category: policy
    applies_to: RequirementFieldFacade
    trigger: BR41.1–BR41.4 任一拒絕
    logic: 以 cloud360.<module> 命名的 logger 寫 warning；不寫 value、不寫 on_behalf_of。
    violation_behaviour: 不適用
    source: "ADR-0006 audit logging 面；team.md 的 logger 命名慣例"

  # ---- BR42：輸入驗證 ----------------------------------------------------
  - id: BR42.1
    statement: agent_group 必須是當前已宣告的組
    category: validation
    applies_to: write_field、clear_field
    trigger: 通過授權之後
    logic: IF agent_group 不在 field_definitions_v1 的 groupKey 集合 THEN 拒絕。
    violation_behaviour: raise UnknownFieldKey(agent_group, field_key)
    source: "K-17 write_field raises；[R12]=D"

  - id: BR42.2
    statement: field_key 必須在該 agent_group 底下已宣告；屬於別組的 key 一律拒絕
    category: validation
    applies_to: write_field、clear_field
    trigger: 通過 BR42.1 之後
    logic: >
      IF field_key 不在該組的 fieldKey 集合 THEN 拒絕——即使它在另一組底下存在。
      判定對象是程式內定義，不是資料表內已有的列（列可能比定義活得久）。
    violation_behaviour: raise UnknownFieldKey(agent_group, field_key)
    source: "AC11.2.2（欄位錯綁到別組即紅燈）；K-17 write_field note"

  - id: BR42.3
    statement: on_behalf_of 只能是 null 或當前已宣告的 groupKey
    category: validation
    applies_to: write_field
    trigger: 通過 BR42.2 之後
    logic: IF on_behalf_of 非 null 且不在 groupKey 集合 THEN 拒絕。
    violation_behaviour: raise RequirementFieldValidationError(field='on_behalf_of')
    source: "[FD1]=A"

  - id: BR42.4
    statement: 去除首尾空白後的 value 長度不得超過 2000 字元
    category: validation
    applies_to: write_field
    trigger: 通過 BR42.3 之後
    logic: IF len(strip(value)) > 2000 THEN 拒絕，該欄不變。
    violation_behaviour: raise RequirementFieldValidationError(field='value')
    source: "phases/construction.md 的「邊界輸入驗證」；欄位為人填的短文字（線框 §17）"

  - id: BR42.5
    statement: 帶有 on_behalf_of 的寫入，去除空白後不得為空字串；代寫路徑要清空必須呼叫 clear_field
    category: validation
    applies_to: write_field
    trigger: on_behalf_of 非 null 且 BR43.1 之後 value 為空字串
    logic: >
      拒絕，該欄不變。BR43.2 的「空值即清空」只適用於 on_behalf_of 為 null 的寫入
      （即使用者經畫面填寫）。
    violation_behaviour: raise RequirementFieldValidationError(field='value')
    source: "[FD3]=A 的適用範圍；review-01 R-06"
    note: >
      [FD3]=A 針對的是人在畫面把輸入框刪空。agent 路徑（U13／U21）產生空字串或只有
      空白的參數並不罕見，若照樣視為清空，使用者先前填的值會被靜默清掉，且 BR45.3
      會丟掉代寫標示，清空被記成「本人清空」——BR45.2 要保護的區分在這條路徑失效。
      K-17 已有表達明確意圖的 clear_field，代寫路徑用它即可。

  # ---- BR43：值的語意 ----------------------------------------------------
  - id: BR43.1
    statement: 寫入前去除 value 的首尾空白；存入的是去除後的字串
    category: calculation
    applies_to: write_field
    trigger: 通過 BR42 之後
    logic: value := strip(value)
    violation_behaviour: 不適用
    source: "[FD3]=A 的前提（只有空白的輸入也要被視為空）"

  - id: BR43.2
    statement: 不帶 on_behalf_of 的寫入，去除空白後為空字串時視為清空
    category: policy
    applies_to: write_field
    trigger: on_behalf_of 為 null，且 BR43.1 之後 value 為空字串（帶 on_behalf_of 者見 BR42.5）
    logic: 改走 clear_field 的語意（BR43.3／BR43.4／BR43.7），不落地空字串。
    violation_behaviour: 不適用
    source: "[FD3]=A；ADR-015"
    note: >
      這讓「已清空」態在使用者路徑上可達（契約自檢原本記載它只有 U13／U21 能觸發，
      J-20）。沒有新增任何控件——已核可線框 §15–§18 不變。

  - id: BR43.3
    statement: 對「從未填過」的欄位清空是 no-op，不建立列
    category: policy
    applies_to: clear_field（含 BR43.2 轉入者）
    trigger: 該 (system, group, key) 無列，或有列而 value 與 clearedAt 皆為 null（BR44.1 視為 never_filled 的第四種列）
    logic: 不寫入；回傳 filledState 為 never_filled 的 FieldView。
    violation_behaviour: 不適用
    source: "ADR-015（清空＝填過後被清空；從未填過＝無列）"
    note: 若建立一列「已清空」，會出現一個從未有過值卻被標為清空的欄位，三態的語意就破了。

  - id: BR43.4
    statement: 對「已清空」的欄位再次清空是 no-op，clearedAt 與 updatedBy 不變
    category: policy
    applies_to: clear_field
    trigger: 該列 value 為 null 且 clearedAt 非 null
    logic: 不寫入；回傳現況。
    violation_behaviour: 不適用
    source: "K-17 retry_and_idempotency（清空冪等、clearedAt 是否更新須一致）"
    note: 選「不更新」是因為狀態沒有改變；更新會讓「誰清的」變成「最後一個重複按的人」。

  - id: BR43.5
    statement: 寫入以單一 upsert 完成；同一欄位的併發首寫不得產生伺服器錯誤，結果為最後寫入者勝
    category: constraint
    applies_to: write_field
    trigger: 每次有效寫入
    logic: >
      以 (system_id, agent_group, field_key) 唯一鍵 upsert：無列則插入、有列則覆寫
      value、clearedAt 設 null、更新 updatedAt／updatedBy／updatedOnBehalfOf。
    violation_behaviour: 不適用
    source: "K-17 write_field 冪等（覆寫同一列）；U18 的三欄唯一鍵"
    note: 先查後寫的兩步做法在兩個併發首寫時會撞唯一鍵而回 500。

  - id: BR43.6
    statement: 對已填欄位寫入相同的值仍視為一次寫入（更新 updatedAt、updatedBy、updatedOnBehalfOf）
    category: policy
    applies_to: write_field
    trigger: 新值等於現值
    logic: 照 BR43.5 覆寫。
    violation_behaviour: 不適用
    source: "K-17 write_field（覆寫同一列）"
    note: 與 BR43.4 不對稱是刻意的——寫入同值時「最後一次確認者」本身就是有意義的溯源，而重複清空沒有新事實。

  - id: BR43.7
    statement: 清空一個已填欄位：保留列、value 設 null、clearedAt 設為當下、更新 updatedAt 與 updatedBy
    category: policy
    applies_to: clear_field（含 BR43.2 轉入者）
    trigger: 該列 value 非 null
    logic: 單一 UPDATE；updatedOnBehalfOf 依 BR45.3 設 null。
    violation_behaviour: 不適用
    source: "ADR-015；K-17 clear_field note"

  # ---- BR44：讀取與計數 --------------------------------------------------
  - id: BR44.1
    statement: 每個欄位的 filledState 由列推導且對任何列都有定義——value 非 null 為 filled；value 為 null 且 clearedAt 非 null 為 cleared；其餘（無列，或有列而 value 與 clearedAt 皆為 null）為 never_filled
    category: calculation
    applies_to: read_fields、write_field、clear_field 的回傳
    trigger: 每次推導 FieldView
    logic: >
      IF value 非 null THEN filled；ELSE IF clearedAt 非 null THEN cleared；
      ELSE never_filled。三個分支窮盡全部組合（U18 的 CHECK 已排除「有值且已清空」）。
    violation_behaviour: 不適用
    source: "ADR-015；mockups.md M12；U18 指派本單元的 OPEN-CG18-7（review-01 R-02）"
    note: >
      第四種列（列存在、value 與 clearedAt 皆為 null）經本 facade 不可達——寫入必設
      value、清空必設 clearedAt——但直接 SQL、手動修資料或日後其他寫入路徑都造得出。
      U18 的 CHECK 允許它且刻意不收緊，揭露給本單元判定。本站判定為「從未填過」：
      它沒有值、也沒有清空紀錄，對使用者與計數的意義與無列相同；寫入時由 BR43.5 的
      upsert 自然覆蓋，清空時依 BR43.3 為 no-op。不新增 facade 守門——它真正的來源
      是非 facade 路徑，facade 守門擋不到。OPEN-CG18-7 由本站結案。

  - id: BR44.2
    statement: unfilledCount 等於當前已宣告欄位中 filledState 為 never_filled 或 cleared 的數目
    category: calculation
    applies_to: read_fields
    trigger: 每次讀取
    logic: "unfilledCount 為已宣告欄位中 filledState 不等於 filled 者的個數"
    violation_behaviour: 不適用
    source: "FR11.3；AC11.3.1–AC11.3.3"

  - id: BR44.3
    statement: 資料表內存在、但定義已不再宣告的列，不出現在回應的分組中，也不計入任何計數
    category: policy
    applies_to: read_fields
    trigger: 讀到 agent_group 或 field_key 不在當前定義內的列
    logic: 忽略該列；不刪除它。
    violation_behaviour: 不適用
    source: "[UG:G9]=A；U18 表 COMMENT"

  - id: BR44.4
    statement: 分組明細與 unfilledCount 由同一次資料庫查詢的結果推導，並在同一個回應內回傳
    category: constraint
    applies_to: read_fields
    trigger: 每次讀取
    logic: >
      以單一查詢取該系統的全部列，於記憶體內對照定義產生各組明細，再由同一份明細
      計算各組的 filledCount／totalCount 與 unfilledCount。不提供只回計數的端點。
    violation_behaviour: 不適用
    source: "不變量 I-4；K-17 read_fields note；US11／US12 共同 DoD"

  - id: BR44.5
    statement: 每個已宣告欄位都出現在回應中，無列者以 never_filled 合成
    category: calculation
    applies_to: read_fields
    trigger: 每次讀取
    logic: 以定義為主迴圈、列為查表；回應的欄位集合恆等於定義的欄位集合。
    violation_behaviour: 不適用
    source: "AC11.2.2（組內欄位集合與該 agent 的宣告一致）"

  - id: BR44.6
    statement: 分組依 displayOrder 排序、組內欄位依宣告順序；每組帶 title、filledCount、totalCount
    category: calculation
    applies_to: read_fields
    trigger: 每次讀取
    logic: 決定性排序，不依賴字典序或資料庫回傳順序。
    violation_behaviour: 不適用
    source: "AC11.2.2（每一組的標題為該 agent 名稱）；線框 §17 的「3/5 已填」"

  # ---- BR45：寫入者溯源 --------------------------------------------------
  - id: BR45.1
    statement: updatedBy 一律為已驗證 principal 的 user_id，包括由大腦代寫的情形
    category: policy
    applies_to: write_field、clear_field
    trigger: 每次有效寫入或清空
    logic: updatedBy := principal.user_id；不接受呼叫端另行指定。
    violation_behaviour: 不適用
    source: "ADR-015；FR11.6（稽核主體必須是使用者本人）"

  - id: BR45.2
    statement: updatedOnBehalfOf 只在呼叫端明確帶入時有值；使用者經畫面填寫時為 null
    category: policy
    applies_to: write_field
    trigger: 每次有效寫入
    logic: updatedOnBehalfOf := on_behalf_of 參數（已經 BR42.3 驗證）。
    violation_behaviour: 不適用
    source: "[FD1]=A；U18 欄位 COMMENT（一律填或一律空都會讓使用者無法分辨哪些值是自己填的）"

  - id: BR45.3
    statement: 清空一律把 updatedOnBehalfOf 設為 null
    category: policy
    applies_to: clear_field
    trigger: BR43.7
    logic: 契約的 clear_field 沒有 on_behalf_of 參數，清空的發起者以 updatedBy 表達。
    violation_behaviour: 不適用
    source: "K-17 clear_field 簽章"

  - id: BR45.4
    statement: on_behalf_of 只是標示，不授予任何權限
    category: authorization
    applies_to: write_field
    trigger: 呼叫端帶入 on_behalf_of
    logic: 授權完全依 BR41 以 principal 判定；on_behalf_of 不參與任何授權分支。
    violation_behaviour: 不適用
    source: "FR11.6（agent 不得做使用者不能做的事）"
    note: >
      後果須誠實記下：任何有寫入權的使用者都能把自己的寫入標成「由大腦（某 agent）
      請求」。這不影響授權、updatedBy 仍是本人，但標示本身可被自填。驗證「真的是
      大腦發起」需要 U21 的 agent 身分機制（OQ-15），不在本單元。

  - id: BR45.5
    statement: updatedAt 在每次有效寫入或清空時更新；no-op（BR43.3、BR43.4）不更新
    category: calculation
    applies_to: write_field、clear_field
    trigger: 有實際狀態變化或 BR43.6
    logic: updatedAt := 交易當下時間。
    violation_behaviour: 不適用
    source: "K-17 FieldView 形狀；mockups.md M12 的「最後更新」"

  # ---- BR46：錯誤處理 ----------------------------------------------------
  - id: BR46.1
    statement: facade 只拋領域例外；router 轉成 403／404／422，且三者都在 route decorator 的 responses 顯式宣告
    category: constraint
    applies_to: RequirementFieldFacade 與其 router
    trigger: 任何例外
    logic: >
      RequirementFieldForbidden → 403；RequirementFieldNotFound → 404；
      UnknownFieldKey、RequirementFieldValidationError → 422。
    violation_behaviour: 未宣告的狀態碼不會進入 openapi.json 與產生的型別檔
    source: "K-17 on_denied（不是 HTTPException）；U19 的教訓：openapi.json 原本非 2xx/422 的宣告數為 0"

  - id: BR46.2
    statement: 失敗的寫入不留下任何部分狀態
    category: constraint
    applies_to: write_field、clear_field
    trigger: 驗證或資料庫錯誤
    logic: 每次寫入或清空為單一交易；失敗即回滾，該欄維持呼叫前的值與 filledState。
    violation_behaviour: 不適用
    source: "AC11.2.3（儲存失敗時畫面須能保留使用者輸入——前提是伺服器端沒有半套寫入）"

  - id: BR46.3
    statement: 對外錯誤訊息為固定文字，不含例外原文、不含欄位值
    category: policy
    applies_to: router
    trigger: 任何錯誤回應
    logic: detail 只帶錯誤類別與定址欄位（system_id、agent_group、field_key）。
    violation_behaviour: 不適用
    source: "ADR-0006；U22 查出的「例外原文送進 SSE」同類缺陷"

  - id: BR46.4
    statement: PUT 本體的形狀錯誤也走領域例外的 422 形狀，不得回顯輸入值
    category: constraint
    applies_to: router
    trigger: PUT 本體缺 value、型別不符或含未知欄位
    logic: >
      框架預設的請求驗證會在 422 的 detail 回顯原始輸入，且形狀（清單）與領域例外
      （固定文字）不同。本 router 的本體驗證不得依賴框架回顯：型別與長度檢查落在
      facade 並拋 RequirementFieldValidationError，或以僅作用於本 router 的處置把
      框架的驗證錯誤轉成同一形狀。具體做法由 code-generation 決定；硬要求兩點：
      回應不含輸入值、U23 只需處理一種 422 形狀。
    violation_behaviour: 不適用
    source: "BR46.3 的完整性；review-01 R-05"

  # ---- BR47：資料表變更（[FD1]=A）-----------------------------------------
  - id: BR47.1
    statement: system_requirement_fields.updated_on_behalf_of 改為可空的 VARCHAR(64)、不帶外鍵，欄位 COMMENT 改寫為 agent 組識別字
    category: constraint
    applies_to: schema_rbac.sql 的 J) 區塊
    trigger: 本單元 code-generation
    logic: >
      受影響的部署資產逐一列出（review-01 R-01 實查後更正）：
      (1) schema_rbac.sql 的 J) 區塊——該欄的 CREATE TABLE 定義與其 COMMENT ON COLUMN；
      (2) DEPLOY.md 第 2.2.9 節——該節目前**完全沒有**提到這一欄（只有
      system_requirement_fields「9 欄」一列），故要補的是一行說明：此欄為 agent 組
      識別字、刻意不帶外鍵、null 表示使用者自己填的。欄數維持 9，不需改。
      觸發 project.md ## Mandated 的 blocking 同步。
      【更正】本規則初稿寫「同步 DEPLOY.md 的外鍵數 8 → 7」：DEPLOY.md 沒有這個數字，
      「8 條外鍵」只出現在 U18 的 code-summary.md 與 traceability.json，那不是部署資產，
      依 refined-mockups:c3 不回改。
    violation_behaviour: 未改則代寫路徑的每一筆都會被外鍵擋下
    source: "[FD1]=A（FD1-R 以完整代價重新確認）；U18 的 OPEN-CG18-6（指派本單元）"

  - id: BR47.2
    statement: 變更須能讓任何「已用舊定義建過表」的資料庫收斂，且可重跑
    category: constraint
    applies_to: schema_rbac.sql 的 J) 區塊（run_meta_schema_migration.py 直接解析並執行它）
    trigger: 本單元 code-generation
    logic: >
      CREATE TABLE IF NOT EXISTS 不會改既有欄位，故 J) 區塊須補可重跑的收斂敘述：
      移除該欄指向 users 的外鍵（若存在），並把欄位型別改為 VARCHAR(64)，既有值一律
      轉為 null。收斂範圍是**所有**可能已跑過舊 J) 區塊的資料庫：本機 dev，以及
      「U18 若先於本單元合併並在 staging 執行 run_meta_schema_migration.py」的 staging
      ——U18 與 U20 屬不同 Bolt，這個順序是可能的。重跑兩次結果相同是硬要求。
    violation_behaviour: 本機、CI 與 staging 的資料庫形狀不一致，而沒有任何東西會告訴你
    source: "U18 的「schema_rbac.sql 只在空 volume 執行」已知約束；review-01 R-01(c)"
    note: >
      既有值一律轉為 null 的理由：舊定義下此欄是 users 的 id，轉成字串後（例如「123」）
      不屬於任何 groupKey，會違反 BR42.3，而且也不可能還原成它代表的 agent。實際上
      目前沒有任何程式寫過此欄（全樹 grep updated_on_behalf_of 只命中 schema_rbac.sql
      的兩處），故不會有值被丟掉。另須誠實記下一處張力：K-15 的 observable_side_effects
      逐字為「不含任何資料寫入」，而型別轉換在 PostgreSQL 會重寫該欄；在沒有任何值的
      前提下不改變任何資料內容，但它不再是純 DDL。

  - id: BR47.3
    statement: 收斂結果必須有機械驗證——該欄的型別是 character varying，且該欄上沒有任何外鍵
    category: constraint
    applies_to: backend/scripts/verify_meta_schema.sql、run_meta_schema_migration.py 的後條件
    trigger: 本單元 code-generation
    logic: >
      verify_meta_schema.sql 補一條以欄位為單位的斷言（型別、無外鍵）。
      **不能**用 run_meta_schema_migration.py 既有的 FORBIDDEN_FKS 機制表達：它以
      (表, 被參照表) 為鍵，而同一張表的 updated_by 合法地指向 users，加
      (system_requirement_fields, users) 會誤擋 updated_by。後條件是否另加欄位級
      檢查由 code-generation 決定，但兩邊不得互相矛盾。
    violation_behaviour: 沒有斷言時，BR47.2 的「重跑收斂」是無法驗證的宣稱
    source: "review-01 R-01(e)"

  - id: BR47.4
    statement: 本單元新增 system_requirement_fields 的 ORM 模型，並以一致性測試鎖住它與 DDL；upsert 依連線方言實作
    category: constraint
    applies_to: backend/models.py、backend/tests
    trigger: 本單元 code-generation
    logic: >
      backend/models.py 目前只有 ProjectMember 與 ReselectionEvent，沒有本表的模型。
      新增模型時，比照 U19 的 test_membership_data.py 補 ORM／DDL 一致性測試（欄位集合、
      可空性、唯一鍵、CHECK）。BR43.5 的單一 upsert 以資料庫方言的
      insert ... on conflict do update 實作，依連線方言選擇（測試用 SQLite、正式為
      PostgreSQL，兩者皆支援該語法但由不同的方言建構式產生）；不得退回先查後寫。
    violation_behaviour: 模型與 DDL 漂移、或 upsert 只在其中一種資料庫上正確
    source: "review-01 R-01(f)；team.md 的「單一真實來源」：跨語言副本須有鎖住一致的測試"
```

## 三、規則摘要

| 群 | 規則 | 一句話 |
|---|---|---|
| 授權 | `BR41.1`–`BR41.6` | 待核准先拒 → 全域 `K4`（facade 內評估）→ 系統存在 → 是該專案成員；判定先於讀寫，拒絕留不含值的 log |
| 驗證 | `BR42.1`–`BR42.5` | 組與 key 必須已宣告、錯綁別組即拒；代寫標示只能是已宣告的組；值上限 2000 字；代寫路徑不得以空值清空 |
| 值語意 | `BR43.1`–`BR43.7` | 去空白；使用者的空值寫入視為清空；清空從未填過或已清空皆為 no-op；寫入單一 upsert、最後寫入者勝 |
| 讀取與計數 | `BR44.1`–`BR44.6` | 三態推導對任何列都有定義（第四種列視為從未填過）；未填＝從未填過＋已清空；不再宣告的列不顯示不計數；明細與計數同一次查詢 |
| 溯源 | `BR45.1`–`BR45.5` | 寫入者恆為本人；代寫標示只在呼叫端帶入時有值、清空時為空、不授予權限 |
| 錯誤 | `BR46.1`–`BR46.4` | 領域例外 → 403／404／422 並顯式宣告；失敗不留半套；錯誤訊息不含原文與值，框架的 422 也一樣 |
| 資料表 | `BR47.1`–`BR47.4` | 代寫欄改為 agent 組識別字、去外鍵；可重跑地收斂本機與 staging；欄位級斷言；新增 ORM 模型與一致性測試 |
