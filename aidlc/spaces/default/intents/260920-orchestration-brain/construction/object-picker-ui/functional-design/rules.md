# Rules — `U16 object-picker-ui`

## 一、本檔存在的理由與識別字區段

> **為什麼一個 `ui` 單元有這份檔。** stage 檔的 `produces_kinds` 把 `rules` 限定在
> `[service, spec, library]`；但同一個 stage 的 `traceability` sensor 要求每個 `OK`
> 覆蓋列的 target 指名至少一個存在於本檔的規則識別字
> （`.claude/tools/aidlc-sensor-traceability.ts:490-508`）。先例 `U15 memory-page-ui`、
> `U24 member-pages-ui` 同為 `ui` 且同樣產出本檔（`U24` 記為 `OPEN-MP24-4`），本單元
> 沿用同一處置，不另開同義 open item。

### 識別字區段：`BR11.x`–`BR15.x`

sensor 以 `/\bBR\d+\.\d+\b/g` 掃**整份**本檔，任何出現在本檔的他單元識別字都會被當成
本檔的孤兒規則。本 intent 已佔用的群組號（以 `grep -oE 'id: BR[0-9]+'` 對全部 20 份
`rules.md` 實算）：`1`–`8`（各 service／spec／library 單元）、`21`–`28`（`U24`）、
`31`–`35`（`U15`）、`41`–`47`（`U20`）、`51`–`58`（`U12`）、`61`–`67`（`U13`）、
`71`–`78`（`U21`）、`81`–`88`（`U23`）、`91`–`98`（`U14`）。`11`–`19` 未被佔用，
本單元取 **`11`–`15`**。

**本檔刻意不寫出他單元規則識別字的字面形式**；需要引用時寫成「`U14` 的 97.7 號規則」
這種不會被 sensor 匹配的形式。

## 二、規則（source of truth）

```yaml
rules:
  # ---- BR11：掛載與作業對象的送出 ----------------------------------------
  - id: BR11.1
    statement: "「切換對象」鈕由本單元渲染在 `ContextBar` 內，三處掛載（入口頁、/workspace、/assessment）共用同一份元件；只在大腦連線為 `ready` 時渲染"
    category: constraint
    applies_to: "ContextBar 的作業對象列"
    trigger: "ContextBar 每次渲染"
    logic: >
      IF 連線 status === 'ready' THEN 渲染「切換對象」鈕（brain-context-switch-object）；
      ELSE 不渲染（connecting／unavailable／forbidden 等狀態下送出必然不發生）。
      不新增 ContextBar 的 prop、不修改三個頁面檔。
    violation_behaviour: "渲染一個點了沒反應的鈕；或三處各自掛載，形成三份選單"
    source: "K-13 provides_to_U16（contract-summary.md:1023-1030）；U14 的 97.7 號規則；[OP2]=A／[OP4]=A 所需的掛載點"
    note: >
      **對 K-13 props 字面的對齊修正**：K-13 宣告 `onObjectSelected`／`currentTarget` 兩個 prop，
      已交付的 ContextBar.tsx:22 只接受 `sharingToggle`，作業對象與送出改由
      `useBrainSession()` 的 `target`／`setWorkTarget` 提供（brainSession.ts:30-34、:57）。
      本單元以 context 取得兩者，不補 prop——補 prop 會形成兩條資料路徑。
      這是**修改已交付的 U14 檔案**，見 functional-spec.md §三之二與 OPEN-OP16-4。

  - id: BR11.2
    statement: "選定一列 → 呼叫 `setWorkTarget`；**不本地修改脈絡列**，脈絡列只在伺服器回推 `work_target` 後更新"
    category: constraint
    applies_to: "ObjectPicker 的選定動作"
    trigger: "使用者以點擊或 Enter／Space 選定一個可選列"
    logic: >
      專案列 → setWorkTarget({projectId: String(p.id), systemId: null, diagramId: null})；
      系統列 → setWorkTarget({projectId: String(s.project_id), systemId: String(s.id), diagramId: null})。
      回傳 true → 關閉選單（BR11.3）。
      回傳 false（送出當下連線已非 ready）→ 選單不關閉，就地顯示「目前無法切換：與大腦的連線中斷」。
    violation_behaviour: "本地先改、伺服器拒絕後畫面說謊；或連線剛斷時選取無聲失效"
    source: "K-13 observable_side_effects（contract-summary.md:1037-1046）；U14 的 97.7 號規則；useBrainConnection.ts:331-335"

  - id: BR11.3
    statement: "選定成功送出後關閉選單、焦點回到「切換對象」鈕；不去重、不自動重送"
    category: policy
    applies_to: "ObjectPicker 的選定動作"
    trigger: "BR11.2 的 setWorkTarget 回傳 true"
    logic: >
      關閉選單 → 焦點回 brain-context-switch-object。
      重複選取同一列照樣送出（伺服器端冪等）；伺服器回 error 時不重送（由既有斷線語意處理）。
    violation_behaviour: "前端自行去重會在伺服器狀態與畫面不一致時吞掉使用者的修正動作"
    source: "K-13 retry_and_idempotency（contract-summary.md:1047-1050）；interaction-spec.md:294"

  - id: BR11.4
    statement: "子頁面上由選單發出的切換，沿用 `U14` 同步掛點對伺服器回推的既有處理（顯示「作業對象已改為 X」、畫布不自動換圖）；本單元不修改該同步掛點"
    category: policy
    applies_to: "/workspace 與 /assessment 上的選取"
    trigger: "子頁面上 BR11.2 送出後收到 work_target 回推"
    logic: >
      不呼叫、不擴充 useWorkspaceTargetSync 的回聲登記；
      回推由該掛點視為一次外來改變處理（useWorkspaceTargetSync.ts:217-248）。
    violation_behaviour: "為了消除一次提示而改動 U14 的回聲抑制，會把『使用者自己的選擇』與『未儲存畫布被覆蓋』兩件事綁在同一個判斷裡"
    source: "functional-design-questions.md §六 第 4 項；U14 的 97.5／97.6 號規則（首次對齊與狀態驅動回寫）"

  # ---- BR12：清單的取得 ---------------------------------------------------
  - id: BR12.1
    statement: "每次開啟選單重抓清單：先列專案，再對每個專案列系統；扇出沿用 `U23` 的 `fanoutQueue`（同時最多 4 個、FIFO、不截斷）；順序照伺服器的 id 遞增，前端不重排"
    category: constraint
    applies_to: "ObjectPicker 的資料來源"
    trigger: "選單開啟；error 態按重試"
    logic: >
      listProjects(token) → 對每個專案 enqueue(listSystems(token, p.id))；
      全部完成 → 組成群組。不快取（他頁的建立與成員變動都會使快取過期）。
    violation_behaviour: "快取造成剛建立的專案不出現；自行排序使預設專案位置不可預期"
    source: "projectsApi.ts:85-105；fanoutQueue.ts:1-28；hierarchy_router.py:156、:223（依 id 遞增）"

  - id: BR12.2
    statement: "任一請求失敗即整個清單進 `error`；**不呈現部分清單**；`error` 與 `empty` 文案不同"
    category: constraint
    applies_to: "ObjectPicker 的 loading → default／empty／error"
    trigger: "清單請求結束"
    logic: >
      全部成功且專案數 0 → empty；全部成功且 ≥1 → default；
      任一失敗 → error：「無法載入清單」＋ 重試鈕；其中專案清單回 403 時文案為
      「你沒有檢視專案的權限」。error 態不顯示 empty 的說明文字。
    violation_behaviour: "部分清單被讀成完整清單；讀取失敗被讀成『你沒有任何專案』"
    source: "interaction-spec.md:270、:272；accessibility-checklist.md:83（U-7）；U23 的 88.3 號規則的同一原則"

  - id: BR12.3
    statement: "目前使用者 id 尚未取得前，清單維持 `loading`，不渲染任何可選列"
    category: constraint
    applies_to: "BR13.2 與 BR14.3 的擁有者判定"
    trigger: "useAuth().user?.id 不是數字"
    logic: >
      IF user.id 未決 THEN 保持 loading；擁有者判定不以 undefined 比較。
    violation_behaviour: "自己的專案短暫顯示為不可選、建立入口閃現又消失"
    source: "U15 frontend-components.md §四之一 的同型處置；auth-context.ts:29（id 為選填）"

  - id: BR12.4
    statement: "選單關閉時取消尚未發出的扇出，並丟棄在途請求的結果"
    category: constraint
    applies_to: "ObjectPicker 卸載或關閉"
    trigger: "Escape、點選單外、選定成功、建立成功"
    logic: >
      queue.cancel()；effect cleanup 設 cancelled 旗標，在途回應不得 setState。
    violation_behaviour: "已卸載元件 setState；重新開啟後舊結果覆蓋新結果"
    source: "fanoutQueue.ts 契約段（cancel 語意）；team.md 資料抓取兩層形狀"

  # ---- BR13：可選性與呈現 -------------------------------------------------
  - id: BR13.1
    statement: "專案列與系統列都可被選為作業對象（零系統的專案亦可選）"
    category: constraint
    applies_to: "ObjectPicker 的清單列"
    trigger: "渲染清單"
    logic: >
      每個群組的標題列本身是可選列（brain-object-project-{id}）；
      其下每個系統是可選列（brain-object-item-{id}）。
      零系統的專案顯示標題列 ＋「尚無系統」一行。
    violation_behaviour: "新建的專案在建立系統前不可被選，AC9.2.1 不成立"
    source: "[OP2]=A；SetWorkTargetPayload 的 systemId 可為 null（ws-contract.json）；hierarchy_service.py:301-303"
    note: "對 interaction-spec.md:281（onPick(systemId)）與 :261（列出可選系統）的對齊修正"

  - id: BR13.2
    statement: "非請求者擁有的專案（與其下系統）照列但不可選：`aria-disabled` ＋ 群組下一行說明「大腦目前只能以你建立的專案為作業對象」"
    category: authorization
    applies_to: "ObjectPicker 的清單列"
    trigger: "渲染清單"
    logic: >
      selectable(project) = project.owner_user_id === currentUserId。
      false → 該專案列與其系統列 aria-disabled="true"、啟用動作無效、不送任何訊息；
      說明文字以 aria-describedby 連到該群組各列。
      **不過濾**：不可選的列照樣渲染。
    violation_behaviour: "成員點了清單上的專案，伺服器回 error、脈絡列不變且無解釋；或前端過濾形成第二份可見範圍規則"
    source: "[OP3]=A；hierarchy_service.py:73-77、:299-309（擁有者範圍解析）；membership_facade.py:482-498（成員可見清單）；U23 的 OPEN-PP23-6 第 ③ 項"
    note: >
      **這不是授權**：伺服器仍以擁有者範圍解析。移除此判定只會讓畫面出現一個必然被拒的控件，
      不會讓成員把別人的專案設為作業對象。判定欄位與方向與 U23 SystemCreateAction.tsx:31 相同。

  - id: BR13.3
    statement: "目前作業對象的那一列標示「目前」"
    category: constraint
    applies_to: "ObjectPicker 的清單列"
    trigger: "渲染清單"
    logic: >
      target.systemId 非 null → 標示 id 相等的系統列；
      target.systemId 為 null 且 target.projectId 非 null → 標示該專案列；
      兩者皆 null → 不標示。比較一律以字串 id。標示以文字「目前」＋ aria-current="true"。
    violation_behaviour: "只標系統會使只選到專案層的作業對象在選單裡看不出來"
    source: "interaction-spec.md:280（currentSystemId）；mockups.md M4 的「<- 目前」；[OP2]=A 的延伸"

  - id: BR13.4
    statement: "搜尋只在已載入的清單上做前端比對，不發請求；無命中時進 `no-match`，保留建立入口並播報結果數"
    category: calculation
    applies_to: "搜尋框 brain-object-search"
    trigger: "搜尋框輸入"
    logic: >
      q = 去頭尾空白、不分大小寫。專案名包含 q → 整組顯示；
      否則只顯示名稱包含 q 的系統及其群組標題（標題仍可選與否依 BR13.2）。
      q 為空 → 全部顯示。無任何列 → no-match：「沒有符合的對象」，經既有大腦 LiveRegion 播報。
    violation_behaviour: "搜尋時隱藏建立入口，使『找不到就建一個』的路徑斷掉"
    source: "interaction-spec.md:271、:296；mockups.md:502"

  # ---- BR14：就地建立 -----------------------------------------------------
  - id: BR14.1
    statement: "建立一律呼叫既有 `objectCreateAction`，不得自建寫入路徑、不得直接呼叫 createProject／createSystem"
    category: constraint
    applies_to: "選單內兩種建立"
    trigger: "建立表單送出"
    logic: >
      專案 → objectCreateAction(token, 'project', name)；
      系統 → objectCreateAction(token, 'system', name, projectId)。
    violation_behaviour: "授權錯誤映射、文案與非冪等防護出現第二份"
    source: "INV-2（interaction-spec.md:32）；K-07 single_write_path（contract-summary.md:541-543）；objectCreateAction.ts:1-13；U23 的 OPEN-PP23-8"

  - id: BR14.2
    statement: "「+ 新增專案」位於選單底部，只在 `can('K2','edit')` 時渲染"
    category: authorization
    applies_to: "brain-object-create-project"
    trigger: "渲染選單"
    logic: "IF can('K2','edit') THEN 渲染；ELSE 不渲染（不顯示停用鈕）"
    violation_behaviour: "無建立權限者看到一個送出必然 403 的入口"
    source: "[OP4]=A；App.tsx:146 的 CapabilityRoute storyId=\"K2\" action=\"edit\"；rbac_seed_data.py:327-337"

  - id: BR14.3
    statement: "「+ 新增系統」位於每個專案群組標題旁，父專案即該群組；只在 `owner_user_id === 目前使用者 id && can('K2','edit')` 時渲染"
    category: authorization
    applies_to: "brain-object-create-system-{projectId}"
    trigger: "渲染每個群組"
    logic: >
      條件成立 → 渲染；否則不渲染。條件與 BR13.2 的 selectable 為同一欄位、同一方向，
      且兩者**呼叫同一個**擁有者判定函式（frontend-components.md 的 isOwnedByMe），不得各寫一次比較——
      否則可能出現「選不了卻能在底下建系統」的組合（functional-spec.md §二之一）。
    violation_behaviour: "在他人專案下顯示必然被拒的建立入口；或需要『先選一個專案』的兩步操作"
    source: "[OP4]=A；SystemCreateAction.tsx:9-11、:31（逐字同一判定）；伺服器建立系統的擁有者檢查（hierarchy_router.py:237-272）"
    note: "對 mockups.md:260 的底部兩鈕並排與 interaction-spec.md:284 的「先選一個專案」停用說明的對齊修正"

  - id: BR14.4
    statement: "建立表單就地展開、名稱單欄；同時只開一張；送出期間停用並擋重複觸發；失敗就地顯示 objectCreateAction 的錯誤文案，名稱保留、表單不收"
    category: validation
    applies_to: "ObjectPicker 的 creating 態"
    trigger: "點任一建立入口；表單送出"
    logic: >
      開啟另一張表單會收起前一張（名稱丟棄）。
      送出：進行中旗標為 true 時忽略；空白名稱由 objectCreateAction 拋 empty，不發請求。
      失敗：顯示 ObjectCreateError.message（名稱重複／無權限／其他），以 aria-describedby 連到名稱欄。
      取消或 Escape：收起表單，焦點回到開啟它的建立入口。
    violation_behaviour: "重複送出建立兩個同名物件（非冪等）；失敗後名稱被清掉"
    source: "interaction-spec.md:273、:287、:376；objectCreateAction.ts:6-10、:26-39；K-07 retry_and_idempotency"

  - id: BR14.5
    statement: "建立成功 → 把作業對象切到新建的對象、關閉選單、播報；下次開啟時清單照 BR12.1 重抓而含新物件"
    category: policy
    applies_to: "建立成功"
    trigger: "objectCreateAction resolve"
    logic: >
      專案 → setWorkTarget({projectId: String(new.id), systemId: null, diagramId: null})；
      系統 → setWorkTarget({projectId: String(new.project_id), systemId: String(new.id), diagramId: null})；
      播報「已建立並切換到 <名稱>」。setWorkTarget 回 false → 選單不關，提示「已建立，但目前無法切換」，
      清單重抓使新物件出現並可手動選取。
    violation_behaviour: "建立了卻沒切過去，使用者得再找一次；或連線中斷時誤報已切換"
    source: "interaction-spec.md:377（成功後呼叫端負責切過去）；AC9.2.1、AC9.2.2"

  - id: BR14.6
    statement: "無 `K2 edit` 且清單為空時，`empty` 態只顯示說明文字，不顯示任何建立入口"
    category: constraint
    applies_to: "ObjectPicker 的 empty 態"
    trigger: "BR12.2 判定為 empty 且 can('K2','edit') 為 false"
    logic: "顯示「你還沒有任何專案。需要具備建立權限的同事邀請你加入，或請管理者調整你的權限。」"
    violation_behaviour: "照字面顯示「+ 新增專案」，一個送出必然 403 的入口"
    source: "[OP4]=A 的後果段（逐字：無 K2 edit 且清單為空時，empty 態只顯示說明）"
    note: "對 interaction-spec.md:270（empty 只顯示「+ 新增專案」）的對齊修正：僅在有 K2 edit 時照原文"

  # ---- BR15：無障礙與焦點 -------------------------------------------------
  - id: BR15.1
    statement: "選單為 `role=\"dialog\"` ＋ `aria-modal=\"true\"` ＋ 可見標題「切換作業對象」（aria-labelledby）；開啟時焦點進搜尋框"
    category: constraint
    applies_to: "brain-object-picker"
    trigger: "選單開啟"
    logic: "開啟 → 焦點移到 brain-object-search；搜尋框有 aria-label=\"搜尋作業對象\"（不只 placeholder）"
    violation_behaviour: "螢幕閱讀器不知道進了覆蓋層；鍵盤使用者焦點留在背景"
    source: "interaction-spec.md:293、:295；accessibility-checklist.md:78、:92"

  - id: BR15.2
    statement: "焦點陷在選單內（Tab／Shift+Tab 循環）；Escape 關閉（creating 時先收表單）；關閉後焦點回「切換對象」鈕"
    category: constraint
    applies_to: "brain-object-picker"
    trigger: "鍵盤操作；關閉"
    logic: >
      Tab 到最後一個可聚焦元素 → 回第一個；Shift+Tab 反之。
      Escape：creating 態 → 收起表單；否則 → 關閉選單。點選單外 → 關閉。
      任何關閉路徑都把焦點還給 brain-context-switch-object。
    violation_behaviour: "鍵盤陷阱或焦點遺失（accessibility-checklist O-4）"
    source: "interaction-spec.md:294；accessibility-checklist.md:63"
    note: "既有五個 modal 都沒有焦點陷阱與返還（design-system-mapping.md 修訂 1 §11），本單元為新建"

  - id: BR15.3
    statement: "方向鍵在清單列間移動（含不可選列）；Enter／Space 選定可選列；不可選列的啟用動作無效但可聚焦以讀出說明"
    category: constraint
    applies_to: "清單列"
    trigger: "清單內按方向鍵、Enter、Space"
    logic: >
      上下鍵在目前可見（已套搜尋）的列之間移動焦點；首尾不循環。
      aria-disabled 列可聚焦，按 Enter／Space 無效果。
    violation_behaviour: "不可選列無法被鍵盤使用者察覺其存在與理由"
    source: "interaction-spec.md:294；[OP3]=A（照列、停用、附說明）"

  - id: BR15.4
    statement: "選單的播報一律寫入該頁既有的大腦 LiveRegion（conn.announce），不另掛播報區"
    category: constraint
    applies_to: "no-match、清單載入完成、建立成功、切換送出失敗"
    trigger: "上述事件"
    logic: "呼叫 useBrainSession().announce(text)"
    violation_behaviour: "同頁出現兩個 polite 播報區，訊息互相覆蓋或重複唸"
    source: "BrainSession.tsx:9、:19（一頁一個 LiveRegion）；interaction-spec.md:296"
```

## 三、規則摘要（derived view）

| id | 類別 | 一句話 | 違反的後果 |
|---|---|---|---|
| `BR11.1` | constraint | 鈕在 ContextBar 內、只在 ready 時渲染 | 點了沒反應的鈕；三份選單 |
| `BR11.2` | constraint | 選定即送 set_work_target，不本地改脈絡列 | 畫面說謊 |
| `BR11.3` | policy | 送出後關閉、焦點返還、不去重不重送 | 吞掉使用者的修正 |
| `BR11.4` | policy | 子頁面沿用 U14 的「已改為」提示 | 改動 U14 回聲抑制的風險 |
| `BR12.1` | constraint | 每次開啟重抓、扇出沿用 fanoutQueue | 剛建的專案不出現 |
| `BR12.2` | constraint | 任一失敗即 error，不呈現部分清單 | 失敗被讀成「沒有專案」 |
| `BR12.3` | constraint | user.id 未決前維持 loading | 擁有者判定閃爍 |
| `BR12.4` | constraint | 關閉即取消扇出 | 卸載後 setState |
| `BR13.1` | constraint | 專案與系統都可選 | AC9.2.1 不成立 |
| `BR13.2` | authorization | 非擁有者專案照列、停用、附說明 | 點了被拒且無解釋 |
| `BR13.3` | constraint | 目前對象標「目前」 | 專案層對象看不出來 |
| `BR13.4` | calculation | 前端搜尋、no-match 保留建立入口 | 找不到就建的路徑斷掉 |
| `BR14.1` | constraint | 一律經 objectCreateAction | 寫入路徑兩份 |
| `BR14.2` | authorization | 「+ 新增專案」需 K2 edit | 必然 403 的入口 |
| `BR14.3` | authorization | 「+ 新增系統」在群組旁，需擁有者且 K2 edit | 他人專案下的必然被拒入口 |
| `BR14.4` | validation | 單欄就地表單、防重複送出、失敗保留名稱 | 建出兩個同名物件 |
| `BR14.5` | policy | 建立成功即切過去並播報 | 建了卻得再找一次 |
| `BR14.6` | constraint | 無 K2 edit 的空清單只顯示說明 | 必然 403 的入口 |
| `BR15.1` | constraint | dialog ＋ aria-modal ＋ 焦點進搜尋框 | 不知道進了覆蓋層 |
| `BR15.2` | constraint | 焦點陷阱、Escape、焦點返還 | 鍵盤陷阱 |
| `BR15.3` | constraint | 方向鍵移動、不可選列可聚焦不可啟用 | 不可選列不可察覺 |
| `BR15.4` | constraint | 播報寫入既有大腦 LiveRegion | 兩個播報區互相覆蓋 |

**22 條**（`BR11` 4、`BR12` 4、`BR13` 4、`BR14` 6、`BR15` 4）。計數見
`functional-spec.md §九之一` 的取得方式。
