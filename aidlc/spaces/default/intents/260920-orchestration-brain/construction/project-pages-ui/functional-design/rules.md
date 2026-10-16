# Rules — `U23 project-pages-ui`

> 建檔時間 2026-10-15T14:57:34Z（以 `date -u` 取值）。

## 一、本檔存在的理由與範圍界線

`produces_kinds` 把 `rules` 限定在 `[service, spec, library]`，`ui` 不在其中；但同一個
stage 的 `traceability` sensor 無條件要求本檔存在，且每個 `OK` 列須指名本檔的規則。
`U24` 已實測此牴觸並記為 `OPEN-MP24-4`，本單元沿用同一處置：產出本檔，內容限定於
**本單元自己**的規則。

**識別字區段 `BR81`–`BR88`。** 已用群組實測為單位數群組、`21`–`28`、`31`–`35`、
`41`–`47`、`51`–`58`、`61`–`67`、`71`–`78`，下一個未用的十位群組是 `8x`。

**本檔不寫出任何他單元規則的識別字字面形式**：sensor 以 `\bBR\d+\.\d+\b` 掃整份檔，
寫出來就會被當成本檔的孤兒規則（`U24` 初版即因此回報 16 個假孤兒）。他單元規則一律
寫成「`U7` 的規則 6.2」這種形式。

**與 `U24` 的差別**：`[PP1]`=A 使本單元的 code-generation **含後端變更**（`U7` 的兩支
列舉端點），故 `BR87` 一組是伺服器端規則，驗證層為 `TestClient` 與 ast 靜態測試而非 Playwright。

**修訂 1**（2026-10-15T22:33:15Z）：依第一輪審查新增 `BR84.7`（R-02）、`BR85.6`（R-08）、
`BR87.7`（R-03）、`BR88.3`（R-11）；改寫 `BR84.4`（R-06）、`BR85.2`（R-07）、`BR86.2`（R-10）、
`BR87.1`／`BR87.5`（R-01、`[PP3]`=A）、`BR87.2`（R-04）、`BR87.3`（R-03）、`BR87.6`（R-05）。
規則由 35 條增為 39 條。
其餘七組全部是外部可觀察的畫面行為。

## 二、規則（machine-readable source of truth）

```yaml source-of-truth
rules:
  # ── BR81：專案清單頁與 Sidebar 入口 ─────────────────────────────
  - id: BR81.1
    statement: 專案清單頁與 Sidebar「專案」項以 K2 view 把關
    category: authorization
    applies_to: 路由 /projects、Sidebar 的「專案」項
    trigger: 使用者落地或渲染 Sidebar
    logic: >
      IF NOT can('K2','view') THEN Sidebar 不渲染「專案」項，且直接進入 /projects
      被既有 CapabilityRoute 導向 /403。清單頁、建立頁、總覽籤同此把關。
    violation_behaviour: 無 K2 的角色看得到入口卻在每次請求收到拒絕；或反之，有權者找不到入口
    source: "U3 的規則 6.3、[R11]=A、線框 §14"

  - id: BR81.2
    statement: 清單頁有四個互斥的呈現：loading／default／empty／error，empty 由「取得成功且為空陣列」推導
    category: constraint
    applies_to: ProjectsListPage
    trigger: 清單請求的生命週期
    logic: >
      請求中 → loading（骨架列，非整頁 spinner）；
      成功且非空 → default；成功且為空 → empty；失敗 → error。
      empty 與 error 不得共用同一個呈現。
    violation_behaviour: 讀取失敗被呈現成「還沒有任何專案」，使用者去建立而不是重試
    source: "mockups.md M10、interaction-spec.md ProjectList、AC11.1.2 的同形約束（K-19）"

  - id: BR81.3
    statement: error 態的文字須明寫「這不是你沒有專案」並提供重試；empty 態須有說明與「建立第一個專案」
    category: constraint
    applies_to: ProjectsListPage
    trigger: 進入 error 或 empty 態
    logic: >
      error → 「讀不到專案清單」＋「這不是『你沒有專案』——是這次取得失敗了」＋ [重試]；
      empty → 線框 §15 的說明文字 ＋ [+ 建立第一個專案]；兩者皆不渲染表格。
    violation_behaviour: 兩態文字相同時，e2e 無法區分，使用者也無法區分
    source: "mockups.md M10、線框 §15"

  - id: BR81.4
    statement: 每一列顯示名稱、系統數與系統名；系統數為 0 時第二行為文字「尚無系統」
    category: constraint
    applies_to: ProjectsListPage 的列
    trigger: default 態渲染
    logic: >
      系統數與系統名取自該專案的系統清單回應（每個專案一次請求，見 BR85.1 的扇出形狀）；
      長度為 0 時渲染「尚無系統」，不得留空白行。
      某一專案的系統清單取得失敗時，該列第二行為「系統清單讀取失敗」，不得顯示為 0。
    violation_behaviour: 空白行被讀成「尚在載入」；失敗被讀成「0 個系統」
    source: "mockups.md M10 的邊界態"

  # ── BR82：建立專案與建立系統 ───────────────────────────────────
  - id: BR82.1
    statement: 建立專案與建立系統只有一條共用寫入路徑（objectCreateAction），由本單元建立
    category: constraint
    applies_to: objectCreateAction、ProjectCreatePage、SystemCreateAction
    trigger: 任何建立專案或系統的動作
    logic: >
      兩種建立一律呼叫同一個 objectCreateAction(kind, name, parentProjectId?)；
      U16 之後的兩個入口（選單就地建立、對話式確認）沿用它，不得自建寫入路徑。
      可斷言形式：建立請求的發送點在前端程式中恰有一處。
    violation_behaviour: 三個入口三種錯誤文案與三種驗證，其中一份必先過期
    source: "interaction-spec.md ObjectCreateAction（INV-2）、bolt-plan.md:494 的交錯順序"

  - id: BR82.2
    statement: 建立失敗至少區分「名稱重複」「無權限」「其他」三類文案，且輸入的名稱不消失
    category: validation
    applies_to: objectCreateAction 的錯誤轉譯
    trigger: 建立請求回 409／403／其他失敗
    logic: >
      409 → 名稱重複；403 → 無權限；其餘（含網路失敗、422）→ 其他。
      失敗後表單維持開啟、名稱欄保留原值。空白名稱在送出前即擋下並顯示文字錯誤。
    violation_behaviour: 使用者無法判斷該改名稱還是該找管理者；或必須重打名稱
    source: "interaction-spec.md ObjectCreateAction 的失敗訊息列"

  - id: BR82.3
    statement: 建立請求非冪等，不得自動重試；送出期間按鈕進入 pending 並保持可聚焦
    category: constraint
    applies_to: objectCreateAction
    trigger: 送出建立
    logic: >
      一次使用者動作恰發一次建立請求；pending 期間再次觸發不發第二次。
    violation_behaviour: 重試或連點建立出兩個同名專案，或在第二次收到名稱重複的誤導錯誤
    source: "U7 的規則 2.4（非冪等）、interaction-spec.md SystemCreateAction 的 pending 態"

  - id: BR82.4
    statement: 「建立系統」動作只對專案擁有者且具 K2 edit 者渲染；成功後重讀系統清單
    category: authorization
    applies_to: SystemCreateAction（總覽籤「系統 N」旁）與需求籤空狀態的建立動作
    trigger: 總覽籤或需求籤渲染；建立系統成功
    logic: >
      渲染條件 = ProjectOut.owner_user_id === 目前使用者 id AND can('K2','edit')。
      此條件與伺服器的建立系統擁有者檢查（U7 的規則 6.5）逐字相同，不是另行推導。
      成功後重讀該專案的系統清單，「系統 N」由清單長度得出，不在前端本地加一。
    violation_behaviour: >
      非擁有者看得到按鈕卻必然被拒；或計數本地加一而與伺服器不一致
    source: "AC11.1.1、AC11.1.3、[DM:D12]=A、interaction-spec.md SystemCreateAction"

  - id: BR82.5
    statement: 建立頁是獨立路由，建立專案成功後導向該專案的詳情頁總覽籤
    category: constraint
    applies_to: 路由 /projects/new
    trigger: 建立專案成功（201）
    logic: >
      導向 /projects/<新 id>?tab=overview；此時系統計數為 0，建立系統動作可見（擁有者）。
    violation_behaviour: 建立後停在清單頁，使用者要再找一次剛建立的專案才能建系統
    source: "unit-of-work.md:408 與 K-19 routes 的「建立頁」、US11.1 的身為／以便"

  # ── BR83：專案詳情頁與三籤 ─────────────────────────────────────
  - id: BR83.1
    statement: 三籤為可無障礙存取的 tablist，目前籤以網址查詢參數 tab 表達
    category: constraint
    applies_to: ProjectTabs
    trigger: 進入專案詳情頁或切換籤
    logic: >
      role="tablist" ＋ 每籤 role="tab" 與 aria-selected ＋ 面板 role="tabpanel"；
      左右方向鍵在籤間移動，Tab 進出面板；tab ∈ {overview, requirements, memory}，
      缺省或非法值視為 overview。
    violation_behaviour: 鍵盤與螢幕閱讀器使用者無法切籤；U17 的 axe 掃描無法定址到某一籤
    source: "線框 §16 無障礙註記、wireframes.md「可無障礙存取的籤零前例」、K-19"

  - id: BR83.2
    statement: 需求籤只對具 K4 view 者渲染；無 K4 者看不到該籤，進入 tab=requirements 時退回總覽
    category: authorization
    applies_to: ProjectTabs、RequirementsTab
    trigger: 渲染籤列；網址指定 tab=requirements
    logic: >
      IF NOT can('K4','view') THEN 籤列只有總覽與記憶摘要，tab=requirements 視為 overview。
    violation_behaviour: 三個維運角色（有 K2 無 K4）看得到籤卻每次被拒
    source: "U3 的規則 6.3"

  - id: BR83.3
    statement: 頁首只渲染 [成員]，導向既有路由 /projects/:projectId/members；[設定] 不渲染
    category: constraint
    applies_to: ProjectDetailHeader
    trigger: 專案詳情頁渲染
    logic: >
      IF can('K3','view') THEN 渲染 [成員]；[設定] 一律不渲染（無任何上游定義的目的地）。
    violation_behaviour: 成員頁無入口（U24 F-1 記載的現況延續）；或渲染一個沒有目的地的按鈕
    source: "[PP2]=A、U24 functional-spec.md:83、OPEN-PP23-4"

  - id: BR83.4
    statement: 詳情頁在專案不在可見清單內或系統清單回 404 時，呈現「查不到這個專案」而非錯誤或空專案
    category: constraint
    applies_to: ProjectDetailPage
    trigger: 以網址直接進入某專案
    logic: >
      詳情頁的專案資料取自專案清單回應（無單一專案端點）；id 不在其中 → not-found 態；
      系統清單回 404 → 同一個 not-found 態。不得把它呈現成「尚無系統」。
    violation_behaviour: 非成員看到一個像是空的專案，誤以為自己有存取權
    source: "U7 的規則 6.1 的「查不到即 404，不是 403」語意、BR87.2"

  # ── BR84：需求籤 ───────────────────────────────────────────────
  - id: BR84.1
    statement: 專案沒有系統時，需求籤為空狀態（說明＋建立系統動作），不是空表或無選項的選擇器
    category: constraint
    applies_to: RequirementsTab
    trigger: 該專案的系統清單為空
    logic: >
      不渲染作業對象選擇器與欄位組；渲染說明文字，並在 BR82.4 的條件成立時渲染建立系統動作；
      條件不成立時只渲染說明（說明須寫明由專案擁有者建立）。
    violation_behaviour: 首次使用者面對一個沒有選項的選擇器，不知道下一步
    source: "AC11.1.2、[D-04]"

  - id: BR84.2
    statement: 每個 filled_state 為未填的欄位，旁邊有文字「未填」，且該文字經 aria-describedby 成為該欄位的可及描述
    category: constraint
    applies_to: RequirementField
    trigger: 需求籤渲染欄位
    logic: >
      未填判定一律取自回應的 filled_state，不由前端以值是否為空自行判斷。
      標示為文字節點，不得只是紅框或顏色。
    violation_behaviour: 色盲或螢幕閱讀器使用者得不到「未填」資訊
    source: "AC11.2.1、mockups.md M12 第 1 點"

  - id: BR84.3
    statement: 組標題、欄位標籤、組數、組內欄位集合與 input_hint 全部取自回應，前端不另寫一份
    category: constraint
    applies_to: RequirementsTab
    trigger: 渲染欄位組
    logic: >
      每個 FieldGroupView 渲染為一個 fieldset，legend 為其 title、組內欄位依 fields 順序、
      各欄的 label 為其 label；input_hint 顯示於表單上方。前端不得持有欄位鍵與標籤的對照表。
    violation_behaviour: 欄位錯綁到別組、或後端新增欄位而畫面不出現
    source: "AC11.2.2、U20 的 OPEN-RF20-4／OPEN-RF20-9、team.md 的單一真實來源"

  - id: BR84.4
    statement: 「最後更新」顯示三種值之一：由你／由大腦（<agent> 請求）／從未更新
    category: calculation
    applies_to: RequirementField 的更新者標示
    trigger: 渲染欄位
    logic: >
      updated_at 為空 → 「從未更新」；updated_on_behalf_of 非空 → 「由大腦（<標題> 請求）」；
      否則 updated_by 為目前使用者 → 「由你」，為他人 → 「由其他成員」。
      「由大腦更新但值為空」與「從未更新」因此可區分。
      <標題> 的來源（審查 R-06）：updated_on_behalf_of 是**請求代寫的 agent 組 key**
      （伺服器只驗它屬於已宣告的組，不要求等於該欄位自己所屬的組），故以它的值在
      同一份回應的 groups 中以 group_key 比對、取該組的 title；**不得**取該欄位所屬
      fieldset 的 legend。比對不到時（該組定義已自程式移除，舊列仍保留）降級為「由大腦」，
      不顯示括號、不顯示原始 key。
    violation_behaviour: >
      使用者分辨不出哪些值是自己填的、哪些是對話中被記下的；或標示成錯的 agent
      （取了欄位所屬組而非請求組）
    source: "mockups.md M12 第 2 點、線框 §17、requirement_field_facade.py:352-356 的 on_behalf_of 驗證、schema_rbac.sql:785 的定義移除後保留舊列"

  - id: BR84.5
    statement: 單一 [儲存] 對每個已改動欄位各發一次 PUT；失敗欄位保留輸入值並各自顯示失敗文字
    category: constraint
    applies_to: RequirementsTab 的儲存
    trigger: 按下 [儲存]
    logic: >
      只送已改動欄位；全部完成後重讀一次該系統的 GET（BR85.3）。
      重讀結果套用到成功的欄位；失敗欄位的輸入值以使用者輸入為準、不被重讀結果覆蓋，
      並以文字標示「未儲存」及錯誤的 detail。全部失敗時亦同。
    violation_behaviour: 部分失敗時使用者輸入被重讀覆蓋而消失（AC11.2.3 的反面）
    source: "AC11.2.3、線框 §17 的單一儲存鍵、U20 的寫入端點逐欄 PUT"

  - id: BR84.6
    statement: 把欄位改為空值並儲存即清空該欄；本單元不提供專屬清空控件
    category: policy
    applies_to: RequirementsTab
    trigger: 儲存一個由有值改為空值的欄位
    logic: >
      以空值 PUT 寫入（不帶 on_behalf_of），伺服器將其視為使用者清空；
      重讀後該欄 filled_state 為未填。不呼叫 DELETE。
    violation_behaviour: 不適用——本條是誠實宣告清空的唯一觸發方式，避免下游以為沒有任何清空路徑
    source: "[US:D-15]、unit-of-work.md:540-542、U20 的規則 43.2"

  - id: BR84.7
    statement: 不具 K4 edit 者，需求籤的欄位為唯讀呈現且不渲染 [儲存]；「未填」文字與更新者照常顯示
    category: authorization
    applies_to: RequirementsTab、RequirementField
    trigger: 需求籤渲染（已通過 BR83.2 的 K4 view）
    logic: >
      IF can('K4','edit') THEN 欄位為可編輯輸入框、渲染 [儲存]（BR84.5）；
      ELSE 欄位為 readOnly 輸入框（保留 label、aria-describedby 與「未填」文字的同一結構）、
      不渲染 [儲存]、不建立草稿，並於表單上方顯示一行文字「你可以檢視需求欄位，但沒有編輯權限」。
      更新者標示（BR84.4）與「未填」文字（BR84.2）兩種狀態下相同。
      伺服器照樣判定：此條只是呈現，K4 edit 的拒絕仍由寫入端點負責。
    violation_behaviour: >
      僅有 K4 view 的四個角色（rbac_seed_data.py:349-359 中 view=True／edit=False 者）
      看到可編輯框與 [儲存]，每次儲存必然被拒，並被 BR84.5 呈現成「某欄位未儲存」，
      稀釋 AC11.2.3 的失敗語意
    source: "審查 R-02、U3 的規則 6.3、rbac_seed_data.py:349-359"

  # ── BR85：未填計數與資料扇出 ───────────────────────────────────
  - id: BR85.1
    statement: 詳情頁對每個系統恰發一次需求欄位 GET，結果存成以 system_id 為鍵的單一狀態，總覽與需求籤都只讀它
    category: constraint
    applies_to: ProjectDetailPage 的資料層
    trigger: 進入專案詳情頁（具 K4 view 時）
    logic: >
      進頁時取系統清單，再對每個系統取一次欄位；總覽的「未填需求欄位」與「待補的需求」、
      需求籤的各組 x/y，全部由這份狀態推導。切籤不得再發請求。
    violation_behaviour: 兩處各自查詢，在寫入競態下顯示不同數字（I-4 的違反）
    source: "不變量 I-4、US11／US12 共同 DoD「兩處計數必須讀同一份來源」、U20 的 OPEN-RF20-3"

  - id: BR85.2
    statement: 總覽的「未填需求欄位」為該專案全部系統的 unfilled_count 總和
    category: calculation
    applies_to: OverviewTab
    trigger: BR85.1 的狀態更新
    logic: >
      N = Σ unfilled_count（各系統）。任一系統的欄位取得失敗時，該指標顯示「無法取得」
      而非部分總和。
      **兩處數字的關係**（審查 R-07）：需求籤一次只顯示所選系統的欄位，總覽是全專案的和。
      單一系統的專案中，總覽 N 等於需求籤該系統的「未填」文字數；多系統時，總覽 N 等於
      **逐一選過每個系統**後「未填」文字數的總和——**不是**每個系統各自等於總覽。
      AC11.3.1–AC11.3.3 的 e2e 預言機因此以單一系統專案構造（見 traceability 的 note）。
    violation_behaviour: 部分失敗時顯示一個偏小的數字，被讀成「已填了」
    source: "AC11.3.1、線框 §16"

  - id: BR85.3
    statement: 儲存或清空成功後重讀該系統的 GET，以重讀結果同時更新兩籤；不得本地加減計數
    category: constraint
    applies_to: RequirementsTab 與 OverviewTab
    trigger: BR84.5 的儲存完成
    logic: >
      寫入回應只帶單一欄位、不帶 unfilled_count，故計數只能來自重讀。
    violation_behaviour: 本地推算使 I-4 在前端那一半悄悄失效
    source: "AC11.3.2、U20 的 OPEN-RF20-3"

  - id: BR85.4
    statement: 全部已填時總覽顯示 0，且需求籤不出現任何「未填」標示
    category: constraint
    applies_to: OverviewTab、RequirementsTab
    trigger: 全部系統的 unfilled_count 皆為 0
    logic: 顯示數字 0；需求籤「未填」文字節點數為 0
    violation_behaviour: 0 被隱藏而與「無 K4」無法區分，或殘留未填標示
    source: "AC11.3.3"

  - id: BR85.5
    statement: 不具 K4 view 者，總覽整個不渲染「未填需求欄位」與「待補的需求」，且不發需求欄位請求
    category: authorization
    applies_to: OverviewTab
    trigger: 總覽籤渲染
    logic: IF NOT can('K4','view') THEN 兩區皆不在 DOM 內，BR85.1 的請求不發出
    violation_behaviour: 顯示 0 與 AC11.3.3 的 0 意義相反；或發出必然被拒的請求
    source: "U3 的規則 6.4"

  - id: BR85.6
    statement: 儲存後的重讀失敗時，已成功欄位保留其送出值並標「已儲存、重新整理失敗」，該系統標為失敗並提供重試
    category: constraint
    applies_to: RequirementsTab、ProjectDetailPage 的 fieldsBySystem
    trigger: BR84.5 的 PUT 全部回應後，BR85.3 的重讀 GET 失敗
    logic: >
      成功欄位的草稿**不清除**，改標「已儲存、重新整理失敗」（文字，經 aria-describedby 關聯）；
      失敗欄位照 BR84.5 標「未儲存」；fieldsBySystem 中該系統的值改為 'failed'，
      故總覽依 BR85.2 顯示「無法取得」而不是舊數字；需求籤顯示 [重新整理]，
      按下只重發該系統的 GET，成功後依 BR85.3 套用並清除「已儲存」欄位的草稿。
      LiveRegion 播報「已儲存，但重新整理失敗」。
    violation_behaviour: >
      草稿已清而重讀值不可得 → 使用者輸入的值消失（AC11.2.3 的反面）；
      或總覽停在舊數字，被讀成「儲存沒有生效」
    source: "審查 R-08、AC11.2.3、BR85.2"

  # ── BR86：已核可畫面上無資料來源的四處（[PP2]=A）──────────────
  - id: BR86.1
    statement: 總覽「架構圖」計數位渲染文字「尚無法取得」與原因，不顯示數字
    category: policy
    applies_to: OverviewTab
    trigger: 總覽籤渲染
    logic: 固定文字；不發任何請求、不以其他端點的資料推估
    violation_behaviour: 不適用——本條是誠實宣告，避免下游以為該數字已有來源
    source: "[PP2]=A、OPEN-PP23-1"

  - id: BR86.2
    statement: 「最近變更」照實呈現部分來源，區塊內明寫「只含經大腦、且為你自己擁有之圖的變更」；最多 5 筆，無資料時顯示「你擁有的圖尚無經大腦的變更」
    category: constraint
    applies_to: OverviewTab 的最近變更區
    trigger: 總覽籤渲染
    logic: >
      逐系統查變更紀錄，合併後排序取前 5 筆。排序：created_at 由新到舊；created_at 為 null
      的列排在所有有時間的列**之後**；同時間或同為 null 時依 id 由大到小（決定性 tie-break）。
      任一系統查詢失敗時區塊顯示「部分變更無法取得」並保留已取得的列。
      標示必須同時寫出兩個限制（審查 R-10）：伺服器以**圖的擁有者**判定可見性
      （hierarchy_facade.py:345-357），故非擁有者的成員看不到擁有者的圖的變更；
      只寫「只含經大腦」會讓成員把空區塊讀成「這個專案沒有變更」。
    violation_behaviour: 部分來源被讀成完整歷史；成員把空態讀成專案無變更；null 時間的列位置不定使 e2e 不穩
    source: "[PP2]=A、mockups.md 修訂 1 的五態表（超過 5 筆截斷）、OPEN-PP23-2、OPEN-PP23-6、openapi.json 的 DiagramChangeOut.created_at（可為 null）"

  - id: BR86.3
    statement: 記憶摘要籤渲染一段說明「專案記憶的彙整尚未提供」與唯讀說明，不發記憶請求
    category: policy
    applies_to: MemorySummaryTab
    trigger: 進入 tab=memory
    logic: 固定文字；不得以 /api/memory/records 的個人記憶冒充專案彙整
    violation_behaviour: 不適用——本條是誠實宣告；以個人記憶冒充會把非本專案的內容放在專案頁上
    source: "[PP2]=A、線框 §18 的「本站不主張的一項」、OPEN-PP23-3"

  # ── BR87：專案與系統清單的可見範圍放寬（[PP1]=A，後端）────────
  - id: BR87.1
    statement: >
      專案清單回傳「請求者有成員列的專案」∪「請求者是擁有者、且該專案尚無任何成員列的專案」；
      有成員列的專案一律以成員列為準
    category: authorization
    applies_to: GET /api/hierarchy/projects
    trigger: 任何使用者請求專案清單
    logic: >
      先做 K2 view 的全域判定，不通過回 403——即使可見集合為空也先判定（BR87.2 同）；
      可見集合 = {project_members 中有 (該專案, 請求者) 列}
              ∪ {owner_user_id = 請求者 AND 該專案在 project_members 中零列}；
      依專案 id 遞增回傳。可見性謂詞只寫一份（membership_service 的一個私有子句），
      本條與 BR87.2 共用它（[PP3]=A）。
      擁有者那一半只在零成員列時生效的理由：新專案必有建立者的成員列
      （membership_facade.py:455-460）；零成員列的專案無人能邀請（邀請者須是該專案的
      project_admin，membership_facade.py:244-246），而最後一位管理者不可被移除
      （:296），故「有成員列而擁有者不在其中」只能由擁有者被移出產生——
      正是 AC12.6.2 要求拒絕的狀態。零成員列只出現在回填未跑、或回填後重跑遷移時。
    violation_behaviour: >
      只回擁有者 → 被邀請者清單為空（AC12.6.3 失敗）；
      多回非成員專案 → 授權外洩（AC12.1.3 失敗）；
      擁有者那一半不受「零成員列」限制 → 被移出的建立者仍看得到專案，
      違反 AC12.6.2 且與需求籤的拒絕不一致（審查 R-01）
    source: "[PP1]=A、[PP3]=A、AC12.1.3、AC12.6.3、AC12.6.2（伺服器側讀取拒絕）、U7 的規則 6.2 指名的最終模型（K-16）、backfill_project_members.py:135-137"

  - id: BR87.2
    statement: >
      某專案的系統清單只對 BR87.1 可見集合內的請求者回 200；缺 K2 view 一律 403（不論專案是否存在）；
      其餘（不存在、不可見）一律 404
    category: authorization
    applies_to: GET /api/hierarchy/projects/{project_id}/systems
    trigger: 任何使用者請求某專案的系統清單
    logic: >
      判定順序固定為三步（審查 R-04）：
      ① K2 view —— MembershipFacade.list_visible_systems 第一步呼叫
         HierarchyFacade.project_exists（其內第一行即 K2 view 判定），讓 HierarchyForbidden
         **原樣上拋**，由 router 的既有轉譯回 403（hierarchy_router.py:131-132）。
         **不得**改走 MembershipFacade._assert_project_exists——它把 HierarchyForbidden
         轉成 MembershipNotFound（membership_facade.py:131-132），會讓缺 K2 者得到 404，
         改變既有行為並使既有測試 tests/test_hierarchy_service.py:130-141（T2b，
         斷言非 canonical role 的系統清單為 403）紅燈；
      ② 專案不存在 → MembershipNotFound → 404；
      ③ membership_service.is_project_visible 為假（BR87.1 的同一謂詞）→ MembershipNotFound → 404；
         為真 → HierarchyFacade.list_systems_unscoped 取資料回 200。
      K2 判定因此仍只在 HierarchyFacade 內一份。
    violation_behaviour: >
      成員進得了清單卻打不開專案；非成員可由 404／403 的差別探測專案存在；
      或缺 K2 者由 403 變成 404（既有行為被靜默改變）
    source: "[PP1]=A、[PP3]=A、U7 的規則 6.1 的 404 語意、審查 R-04"

  - id: BR87.3
    statement: 呼叫方向為 router → U19 的 facade → U7 的 facade；U7 不得呼叫 U19
    category: constraint
    applies_to: 兩支列舉端點的 handler
    trigger: 實作或修改這兩支 handler
    logic: >
      handler 委派給 MembershipFacade 新增的兩個方法，後者以 membership_service 的可見性
      查詢判定，並呼叫 HierarchyFacade 新增的兩個方法取資料（K2 判定仍在 HierarchyFacade 內，
      只有一份）。六個新增方法的名稱與簽章（審查 R-03）：
      MembershipFacade.list_visible_projects(self, principal: Principal) -> List[Project]；
      MembershipFacade.list_visible_systems(self, principal: Principal, *, project_id: int) -> List[System]；
      HierarchyFacade.list_projects_by_ids(self, principal: Principal, *, project_ids: Sequence[int]) -> List[Project]
        （第一行 K2 view 判定，集合為空也先判定；依 id 遞增）；
      HierarchyFacade.list_systems_unscoped(self, principal: Principal, *, project_id: int) -> List[System]
        （第一行 K2 view 判定；不做擁有者檢查）；
      membership_service.visible_project_ids(db: Session, *, user_id: int) -> List[int]（遞增）；
      membership_service.is_project_visible(db: Session, *, project_id: int, user_id: int) -> bool。
      後兩者共用同一個私有可見性子句（BR87.1）；形狀沿用 project_ids_where_admin
      （membership_service.py:299）與 project_ids_owned_by（:678-685，membership_service
      已有讀 projects 表的先例）。
      形狀沿用 hierarchy_router.py:173-198 建立專案的既有委派。
      HierarchyFacade 不 import membership 任何符號。
    violation_behaviour: U7 反向呼叫 U19 形成循環（U7 的規則 6.2 記載的理由）；或 K2 判定出現第二份
    source: "[PP1]=A、K-16 的「per-project 授權判定的唯一來源」"

  - id: BR87.4
    statement: 兩支端點的路徑、回應模型與狀態碼不變；只有說明文字改變，openapi.json 須重新 dump
    category: constraint
    applies_to: 兩支列舉端點、openapi.json、frontend/src/types/api.d.ts
    trigger: 修改兩支 handler 的 docstring
    logic: >
      FastAPI 以 docstring 作為 operation 的 description；現行 description 逐字寫
      「以成員身分取得的存取在本輪看不到任何東西」，放寬後為假，必須改寫。
      改寫後 openapi.json 的 description 文字漂移 → 依 CI 漂移閘門重新 dump 並重產型別檔。
      response_model（List[ProjectOut]／List[SystemOut]）與 404 宣告不得改動。
    violation_behaviour: 不重 dump → CI 紅燈；保留舊 docstring → 對外契約說明與行為相反
    source: "openapi.json 現行 description（實測）、team.md 的 OpenAPI drift 檢查"

  - id: BR87.5
    statement: 放寬須附 allow／deny 雙向 TestClient 測試，兩支端點各自涵蓋五種身分，另加缺 K2 一案，皆斷言狀態碼
    category: constraint
    applies_to: backend/tests
    trigger: BR87.1／BR87.2 落地
    logic: >
      五種身分 × 兩支端點（專案清單皆 200，斷言回應中是否含該專案；系統清單斷言狀態碼）：
      ① 擁有者且有成員列 → 清單含、系統清單 200；
      ② 被邀請的成員（非擁有者）→ 清單含、200；
      ③ 非擁有者亦非成員 → 清單不含、404；
      ④ 被移出的擁有者（另有管理者將其移出後，owner_user_id 仍是他）→ 清單不含、404（審查 R-01）；
      ⑤ 零成員列專案的擁有者（直接以 ORM 建立專案而不寫成員列，模擬回填前）→ 清單含、200。
      另一案：非 canonical role（全部 11 個 canonical role 的 K2 view 皆為 True，故只能以
      非 canonical role 構造）→ 兩支皆 403，系統清單對**存在與不存在**的 project_id 皆 403。
      突變驗證（每道須使指定案例紅燈、還原後複綠）：
      M1 拿掉成員那一半 → ②紅；M2 拿掉「零成員列」條件（退回擁有者 ∪ 成員）→ ④紅；
      M3 拿掉擁有者那一半 → ⑤紅；M4 系統清單改經 _assert_project_exists → 缺 K2 案與既有 T2b 紅。
    violation_behaviour: 授權放寬沒有任何會紅的斷言；被移出擁有者路徑零斷言
    source: "team.md Testing Posture 的 A／B 規則、ADR-0006 IAM、審查 R-01／R-04"

  - id: BR87.6
    statement: 放寬只限這兩支列舉端點；其餘以擁有者為範圍的讀寫維持原狀
    category: policy
    applies_to: U7 的其餘端點（建立系統、刪除、變更紀錄、作業對象解析）
    trigger: 實作 BR87.1／BR87.2 時
    logic: >
      建立系統仍只限擁有者（BR82.4 的前提）；變更紀錄查詢仍只回請求者自己的圖
      （故成員在「最近變更」只看到自己的圖，見 OPEN-PP23-6）。
      HierarchyFacade 既有的 list_projects／list_systems **不變**，仍是擁有者範圍；
      它們的呼叫端含 brain_gateway.py:1230-1239 的大腦對象目錄，故被邀請的成員在專案頁
      看得到的專案，大腦的對象解析看不到（審查 R-05，OPEN-PP23-6 第 ③ 項）。
      被移出的建立者在 API 層仍能建立系統、刪除專案與系統（只認擁有者，
      hierarchy_facade.py:213-240），本單元不改（OPEN-PP23-10）。
    violation_behaviour: 不適用——本條是範圍宣告，避免實作者把整個 U7 改成成員範圍
    source: "[PP1]=A 的選項原文只涵蓋兩支列舉端點、[PP3] 題幹第 7 點"

  - id: BR87.7
    statement: 兩個不做擁有者檢查的 HierarchyFacade 方法，在 backend 應用程式碼中只能被 MembershipFacade 呼叫，由 ast 靜態測試鎖住
    category: constraint
    applies_to: HierarchyFacade.list_projects_by_ids、HierarchyFacade.list_systems_unscoped
    trigger: backend 任何 .py 檔的新增或修改
    logic: >
      靜態測試 backend/tests/test_project_visibility_static.py：以 ast 解析 backend 下全部 .py
      （排除 tests/），收集所有 attr 為 list_projects_by_ids 或 list_systems_unscoped 的
      ast.Call；斷言其所在位置的集合恰為 services/membership_facade.py 的 MembershipFacade
      類別內（定義本身不算呼叫）。形狀沿用 tests/test_mcp_bridge_static.py 的 ast.walk 掃描。
      兩個方法的 docstring 另寫明唯一合法呼叫端，但機械強制以本測試為準。
      突變驗證：在 hierarchy_router.py 直接呼叫 list_systems_unscoped → 測試紅；還原 → 綠。
    violation_behaviour: >
      多單元共用的 facade 上多了一個繞過擁有者檢查的讀取口，任何呼叫端（brain_gateway 已持有
      hierarchy facade 工廠）直呼即繞過成員判定，且沒有任何東西會報錯
    source: "審查 R-03、ADR-0006 IAM、tests/test_mcp_bridge_static.py 的先例"

  # ── BR88：資料抓取與播報 ───────────────────────────────────────
  - id: BR88.1
    statement: 每個新資料來源走兩層抓取形狀，網址一律經 apiUrl()
    category: constraint
    applies_to: projectsApi、requirementsApi
    trigger: 任何新增的 fetch
    logic: >
      純抓取函式（不碰 state、回傳資料或拋錯）→ 呼叫端在 then／catch／finally 更新 state
      → useEffect 內以 cancelled 旗標防卸載後 setState。effect body 內不得同步 setState。
    violation_behaviour: react-hooks/set-state-in-effect（error 級）使 CI 紅燈
    source: "unit-of-work.md:460、team.md Code Style"

  - id: BR88.2
    statement: 載入與錯誤態的文字寫入既有 LiveRegion 元件；不得使用 4 秒 toast
    category: constraint
    applies_to: 本單元全部頁面
    trigger: 進入 loading 或 error 態、儲存完成
    logic: >
      沿用 frontend/src/components/LiveRegion.tsx（role="status" 寫死），不另建；
      loading → error 的轉換播報一次；儲存結果（全部成功／部分失敗）播報一次。
    violation_behaviour: 螢幕閱讀器使用者只會發現骨架消失而不知道發生什麼
    source: "[US:D-08]、U24 的 [N4]=A、interaction-spec.md ProjectList 的狀態播報列"

  - id: BR88.3
    statement: 扇出請求（清單頁的系統清單、詳情頁的需求欄位與變更紀錄）以每頁同時最多 4 個在途請求的佇列發出，不截斷總數
    category: constraint
    applies_to: ProjectsListPage、ProjectDetailPage 的扇出
    trigger: 進頁時需要對 P 個專案或 S 個系統各發一次請求
    logic: >
      未定案前的預設（OPEN-PP23-5；nfr-requirements 定出數字後以其為準）：
      每頁一個並行上限為 4 的佇列，完成一個補一個，依清單順序（專案 id／系統 id 遞增）發出。
      排隊中的項目顯示既有的載入子狀態（清單列為 systems-loading，總覽的未填與待補區在全部
      完成前顯示載入中）。**不截斷**：截斷會讓 BR85.2 的總和變成部分和、讓 BR86.2 的最近
      變更漏列，兩者都是把部分資料呈現成完整資料。頁面卸載時佇列中尚未發出的請求不再發出。
    violation_behaviour: >
      P 或 S 大時一次湧出數十個請求；或為了限量而截斷，使計數偏小
    source: "審查 R-11、OPEN-PP23-5、BR85.2"
```

## 三、規則摘要

| 群組 | 條數 | 管什麼 | 驗證層 |
|---|---|---|---|
| `BR81` | 4 | 清單頁四態、`K2` 把關、Sidebar 入口、列的邊界態 | Playwright |
| `BR82` | 5 | 共用建立路徑、錯誤分類、不自動重試、建立系統的顯示條件、建立頁 | Playwright |
| `BR83` | 4 | 三籤 tablist、`K4` 籤把關、頁首動作、查不到態 | Playwright |
| `BR84` | 7 | 需求籤空狀態、未填文字、標籤來源、更新者三值、逐欄儲存與部分失敗、空值即清空、無 `K4 edit` 唯讀 | Playwright |
| `BR85` | 6 | 同一份來源、專案層總和、重讀不推算、0 的邊界、無 `K4` 隱藏、重讀失敗 | Playwright |
| `BR86` | 3 | 無來源三處的佔位（`[設定]` 不渲染在 `BR83.3`） | Playwright |
| `BR87` | 7 | 兩支列舉端點的可見範圍放寬、判定順序、方法定名、靜態鎖（後端） | `TestClient` ＋ ast 靜態測試 |
| `BR88` | 3 | 抓取形狀、live region、扇出並行上限 | lint ＋ Playwright |
| **合計** | **39** | | |

條數由本檔 YAML 的 `- id:` 行以 `grep -c` 實算（見 `functional-spec.md` §十之一）。

四條 `policy` 類規則（`BR84.6`、`BR86.1`、`BR86.3`、`BR87.6`）的 `violation_behaviour`
寫「不適用」：它們是**誠實宣告**，寫下的理由是避免下游對本單元的保證強度產生過高預期
——以為沒有清空路徑、以為架構圖計數有來源、以為記憶彙整已存在、以為整個 `U7` 都改成成員範圍。
