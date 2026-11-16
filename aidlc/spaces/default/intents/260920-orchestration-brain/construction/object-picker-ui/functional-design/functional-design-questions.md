# Functional Design 問題檔 — `U16 object-picker-ui`

> 單元類型 **`ui`**（`unit-of-work.md:52`），故 `produces_kinds` 只要求
> `functional-spec.md`、`frontend-components.md`、`traceability.json` 三份
> （`entities: [service, spec, library]`、`rules: [service, spec, library]` 皆不含 `ui`）。
> **`rules.md` 仍會產出**：`traceability` sensor 要求每個 `OK` 覆蓋項的 target 指名
> 存在於 `rules.md` 的 `BRx.y`——先例 `U15 memory-page-ui`、`U24 member-pages-ui`
> 同為 `ui` 且同樣產出 `rules.md`。
>
> 本檔為 **QUESTION-ONLY** 階段的產出（stage 檔 Step 1–3）。四題，皆屬「猜錯會造成
> 真實重工」的類型；其餘一律列入下表「已由上游定案、不重問」，或列入 §六「本站預定
> 處置（非提問）」並附理由供審查。
>
> 起草時間 2026-10-17T23:45:36Z（以 `date -u` 取值）。

## 一、上游已定案、本站不重問

| 事項 | 定案 | 出處（逐字核對過） |
|---|---|---|
| 本單元的交付範圍 | 切換對象選單 ＋ 就地建立表單 ＋ `CreateConfirmCard` | `unit-of-work.md:196`；`bolt-plan.md:354` |
| 「改為獨立對話」控件**不屬本單元** | 屬 `U14` | `unit-of-work.md:180`；`contract-summary.md:1026-1027`（K-13 `ownership_note`） |
| 本單元承載的故事 | 僅 `US9.2`（`AC9.2.1`–`AC9.2.3`） | `unit-of-work-story-map.md:62`、`:121` |
| 選定即伺服器端持久化 | 選定 → 送 `set_work_target` WebSocket 訊息；**不得本地先改脈絡列**（伺服器回推 `work_target` 才更新） | K-13 `observable_side_effects`（`contract-summary.md:1037-1046`）；`U14` `BR97.7`（`entry-page-ui/functional-design/rules.md:517-524`） |
| 重複選取的語意 | 冪等；本單元**不需去重**，但不得倚賴回呼只被呼叫一次；送出失敗不自動重送 | K-13 `retry_and_idempotency`（`contract-summary.md:1047-1050`） |
| 選單掛在哪裡 | `ContextBar`，而它同時掛在入口頁、`/workspace`、`/assessment` 三處 | K-13 `provides_to_U16.scope`（`contract-summary.md:1025`）；實讀 `EntryPage.tsx:45`、`WorkspacePage.tsx:930`、`AssessmentPage.tsx:1240` |
| 建立的唯一寫入路徑 | 一律呼叫 `U23` 已交付的 `objectCreateAction`，**不得自建** | `INV-2`（`interaction-spec.md:32`）；K-07 `single_write_path`（`contract-summary.md:541-543`）；`OPEN-PP23-8`（`project-pages-ui/functional-design/functional-spec.md:303`）；`objectCreateAction.ts:1-13` |
| 建立失敗的文案 | 三類（名稱重複／無權限／其他）＋ 空名稱前端擋下；文案由 `objectCreateAction` 持有，**兩個入口相同** | `interaction-spec.md:376`；`objectCreateAction.ts:26-39`；`U23` `BR82.2` |
| 建立非冪等、不自動重試 | 一次呼叫一次請求；進行中旗標擋重複觸發 | K-07 `retry_and_idempotency`（`contract-summary.md:536-538`）；`objectCreateAction.ts:9-10` |
| 建立表單欄位 | **只有名稱** | `interaction-spec.md:287`；`hierarchy_router.py` 的 `CreateProjectIn`／`CreateSystemIn` 只有 `name`（實讀） |
| 建立成功後 | 呼叫端把作業對象切到新建的對象 | `interaction-spec.md:377`（`ObjectCreateAction` 的「成功後」列）、`:546`（流程 A 第 3 步） |
| `ObjectPicker` 的六個狀態 | `default`／`loading`／`empty`／`no-match`／`error`／`creating`；`loading`／`error`／`no-match` 時**建立入口仍可用** | `interaction-spec.md:268-273`；`mockups.md:502` |
| `empty` 與 `error` 必須可區分 | 已定案 | `accessibility-checklist.md:83`（U-7） |
| 無障礙 | `role="dialog"` ＋ `aria-modal="true"`；Escape 關閉；方向鍵移動；**焦點陷在選單內**；關閉後焦點回 `[切換對象]`；搜尋框有可見 label 或 `aria-label="搜尋作業對象"`（不得只用 placeholder）；`no-match` 以 `aria-live="polite"` 播報結果數 | `interaction-spec.md:293-296`；`accessibility-checklist.md:60`、`:63`、`:78`、`:92` |
| `ObjectPicker` 的 `data-testid` | `brain-object-picker`、`brain-object-search`、`brain-object-item-{id}`、`brain-object-create-project`、`brain-object-create-system`、`brain-object-create-name` | `interaction-spec.md:300-301` |
| `ContextBar` 內「切換對象」鈕的 testid | `brain-context-switch-object` | `entry-page-ui/functional-design/frontend-components.md:143` |
| `CreateConfirmCard` 的規格（若做） | 對話流內 `article`、不陷焦點；`[建立]`／`[取消]`／`[改個名字]`；`submitting`／`success`／`error`／`cancelled`；信心再高也一律先確認 | `interaction-spec.md:305-355`；`mockups.md:283-330` |
| 驗證方式 | **Playwright e2e**（前端無 unit／component 測試框架）；WebSocket 以既有 `page.routeWebSocket` ＋ `src/brain/testing/wsFrames.ts` 假伺服器斷言 `set_work_target` 訊框 | `unit-of-work.md:198`；`team.md ## Testing Posture`；`entry-page.spec.ts:37`、`:1071` 的先例 |
| 前端資料抓取形狀 | 兩層抓取（純抓取函式／呼叫端 `.then.catch.finally`／`useEffect` 內 `cancelled` flag）；`apiUrl()`；state 一律回傳新物件 | K-13 `data_fetch_shape`／`url_building`／`immutability`（`contract-summary.md:1051-1054`）；`team.md ## Code Style` |
| 授權權威在伺服器 | 前端的顯示條件只是呈現；建立一律經 `require_story_action`（`K2`）＋擁有者檢查（`U7` `BR6.5`） | `FR9.5`（`requirements.md:219-229`）；K-07 `authorization_model`；`hierarchy_router.py:237-272` |
| 不新增 story id | 本單元沿用 `K2`（view 列清單、edit 建立） | `U3` 已交付 `rbac_seed_data.py:327-337` |

## 二、本單元承載的故事與其 AC

| AC | 落在 `U16`？ | 預定處置 |
|---|---|---|
| `AC9.2.1`（建立專案 → 它出現在我可選的作業對象中） | **是** | 「出現在可選的作業對象中」的畫面面在本單元；**其可滿足性取決於 `OP2`**（見 §三 事實 2） |
| `AC9.2.2`（在某專案下建立系統 → 歸屬於該專案且可被選為作業對象） | **是** | 系統建立入口的位置與顯示條件取決於 `OP4` |
| `AC9.2.3`（不具權限者嘗試建立 → 被拒，且拒絕經 `require_story_action`） | **部分** | 拒絕本身由 `U7` 的端點承擔（已交付、已有 `TestClient`）；本單元承擔的是**畫面面**：無 `K2 edit` 者不渲染建立入口（沿用 `U23` `BR82.4` 的同一判定），以及 403 映射為「無權限」文案的呈現（以 e2e 攔截回應驗證） |

→ `upstream_ids` 為 **3 條**。

## 三、本站查出的事實（提問的前提）

以下五項皆為**實讀磁碟**所得，前四項各自支撐一題。

**事實 1 — 對話式建立沒有任何觸發端。** `CreateConfirmCard` 的觸發是「大腦辨識為
建立意圖」（`interaction-spec.md:326`、`:545`），但：

- 伺服器→客戶端訊息型別為封閉的九值 `ready／token／clarify／work_items／cost_card／
  sharing_mode／work_target／done／error`（`ws-contract.json:759-772`），**沒有任何一值
  能承載「請確認建立」**。
- 意圖路由的能力值域為封閉的三值 `architecture-design`／`well-architected-review`／
  `cost-finops`（`backend/services/intent_routing_types.py:50-54`），**沒有建立能力**。
- `U2`、`U11`、`U12`、`U13` 皆已交付（各自 `code-generation` 目錄存在）。`U7` 的
  `functional-spec.md:218` 寫「對話式建立由大腦端轉成對同一端點的呼叫」——但大腦端
  沒有任何單元承接這件事。

所以照 `unit-of-work.md:196` 字面做出的 `CreateConfirmCard`，在現有管線下**永遠不會
被渲染**。這是上游契約缺口，依 `units-generation:260822-ug-L2` 標出、不逕自修改已
交付的上游。

**事實 2 — 選單只能選系統，但 `AC9.2.1` 要求「專案」可被選。**
`interaction-spec.md:281` 的 `onPick` 型別為 `(systemId) => void`、描述為「依專案分組
列出可選**系統**」（`:261`）。而新建的專案**沒有任何系統**——`create_project_with_owner`
只建專案與建立者的成員列，不建系統（實讀 `membership_facade.py` 該方法與
`hierarchy_service.py:159-174` 的 `create_system` 需另行呼叫）。故照規格，一個剛建立的
專案在選單裡只有群組標題、沒有可選項，`AC9.2.1` 的 Then「它出現在我**可選的**作業
對象中」不成立。
另一方面，協定**容許**只有專案層的作業對象：`SetWorkTargetPayload` 的 `systemId`／
`diagramId` 可為 null（`ws-contract.json` 的該 schema），`resolve_work_target` 也接受只給
`project_id`（`hierarchy_service.py:301-303`）。

**事實 3 — 選單看得到的專案，大腦不一定接受。**
選單的清單來源 `GET /api/hierarchy/projects` 回傳「成員列 ∪（擁有者且零成員列）」
（`hierarchy_router.py:151-168`；`membership_facade.py:482-498`）——**被邀請的非擁有者
成員看得到**。但 `set_work_target` 經 `resolve_work_target` 解析時，每一層都套**擁有者**
範圍：`assert_project_owned_by` 在 `project.owner_user_id != user_id` 時拋
`HierarchyNotFound`（`hierarchy_service.py:73-77`、`:299-309`），閘道收到例外即回單則
`error` 訊框、不扇出 `work_target`（`brain_gateway.py:1540-1562`）。
這正是 `U23` 已記載的 `OPEN-PP23-6` 第 ③ 項（「大腦的專案目錄仍為擁有者範圍……被邀請
的成員在專案頁看得到的專案，大腦的對象解析與脈絡列看不到」，
`project-pages-ui/functional-design/functional-spec.md:301`），該項明寫「本 intent 內無
自然承接站」。本單元是**第一個把這個落差變成使用者可點擊控件**的單元。

**事實 4 — 「+ 新增系統」的父專案與顯示條件未定。**
`interaction-spec.md:284` 只寫「無選定專案時 `disabled` ＋『先選一個專案』」，但選單裡
「選定專案」的意義未定義（選單選的是系統，見事實 2）。而伺服器的建立系統除 `K2 edit`
外**還要求請求者是該專案擁有者**（`U7` `BR6.5`；`hierarchy_router.py:237-272`）。
`U23` 的 `SystemCreateAction` 已以 `owner_user_id === 目前使用者 id && can('K2','edit')`
作為渲染條件（`SystemCreateAction.tsx:9-11`、`:31`）。`K2 edit` 只有
`Project_Architect`／`Project_Editor`／`Project_Admin`／`Platform_Admin` 四個角色持有
（`rbac_seed_data.py:327-337`）。

**事實 5（不出題，影響 §六）— `ContextBar` 沒有掛載點。** K-13 的 `props_contract`
宣告 `ContextBar` 提供 `onObjectSelected(target)` 與 `currentTarget`
（`contract-summary.md:1028-1030`），但已交付的 `ContextBar` 只接受 `sharingToggle` 一個
prop（`ContextBar.tsx:22`），註解寫「切換對象鈕只在 `U16` 提供選單時渲染，本單元不渲染」
（`:20`）。作業對象與送出函式改由 context 提供：`useBrainSession()` 的 `target` 與
`setWorkTarget(ids): boolean`（`brainSession.ts:30-34`、`:57`；`useBrainConnection.ts:331-335`）。
故本單元**必須修改 `U14` 擁有的 `ContextBar.tsx`** 才能接上。處置見 §六 第 1 項。

## 四、問題

## OP1. 對話式建立（`CreateConfirmCard`）沒有觸發端，本單元怎麼處理？

前提見 §三 事實 1。`US9.2` 三條 AC **不要求**對話式建立——選單的就地建立已足以滿足
三條（AC 的 When 只寫「我建立一個專案」）。對話式建立來自 `[DM:D2]`=D 的「兩個入口
並存」（`mockups.md:37`），是交付清單的一項，不是 AC。

- **A.（建議）本單元只做選單與就地建立；`CreateConfirmCard` 不實作，記為
  `OPEN-OP16-1`「對話式建立無觸發端」交 conductor 在核可關卡重新提交使用者**（比照
  `OPEN-PP23-6` 的處置形狀）：零上游改動、零死碼。代價：`unit-of-work.md:196` 與
  `bolt-plan.md:354` 的交付清單少一項，`[DM:D2]`=D 的「對話那一半」在本 intent 不落地，
  必須在本站產出與關卡**明寫為範圍縮減**；`INV-2` 的可斷言形式（「恰一處實作」）仍成立
  （`objectCreateAction` 已是唯一實作，呼叫點為 `U23` 兩處 ＋ 本單元選單）。
- **B. 本單元補齊整條管線**：新增建立能力至 `ROUTABLE_CAPABILITIES`、新增一個伺服器→
  客戶端訊息型別（如 `create_confirm`）、`U12` 產生它、`U13` 轉送、前端渲染卡片。
  代價：改動四個已交付單元的契約——`ws-contract.json` 的兩道漂移閘門要重跑、
  `intent_routing_types.py` 的封閉集合與其 property-based 測試（ADR-0006 PBT 的
  agent routing 落點）要改、需新 ADR 追認超出 K-02 的擴充（先例 `ADR-0019`）；
  複雜度由 M 升為 L 以上，且 `kind: ui` 不再成立。
- **C. 前端自行偵測建立句型**（例如在送出前以字串比對「開一個叫 X 的專案」）並渲染卡片：
  不動後端。代價：繞過意圖路由，等於在瀏覽器裡建第二套意圖判斷（違反 `team.md`「單一
  真實來源」）；句型比對的誤判沒有任何信心值可依；且使用者訊息照樣送給大腦，同一句話
  會同時得到大腦的回覆與一張卡片。
- **D. 先把 `CreateConfirmCard` 元件寫好、接上 `objectCreateAction`，但不掛到任何
  訊息上，等日後有觸發端再接**：交付清單字面上完整。代價：一個永遠不渲染的元件就是
  死碼，而 `team.md` 記載全 repo「零 TODO 且無死碼區塊」是應保護的紀律；e2e 也只能靠
  測試專用入口強行渲染它，驗到的不是使用者會走的路徑。
- **X. Other**

[Answer]: A  <!-- answered 2026-10-17T23:49:49Z via picker; 範圍縮減，CreateConfirmCard 記為 OPEN-OP16-1 -->

## OP2. 選單裡什麼可以被選為作業對象？

前提見 §三 事實 2。

- **A.（建議）專案與系統都可選**：專案列送 `{projectId, systemId: null, diagramId: null}`，
  系統列送 `{projectId, systemId, diagramId: null}`。零系統的專案仍可被選，`AC9.2.1` 成立；
  協定與 `resolve_work_target` 皆已支援，零後端改動。代價：偏離 `interaction-spec.md:281`
  的 `onPick(systemId)` 型別與 `:261` 的「列出可選系統」，須在本站產出明記為**對齊修正**
  （依 `refined-mockups:c3`，不回改上游）；脈絡列會出現「只有專案、沒有系統」的作業對象，
  而 `ContextBar` 已能顯示任一層為 null 的組合（`ContextBar.tsx:28-33` 只渲染非 null 層）。
- **B. 只有系統可選；零系統的專案顯示群組標題 ＋「尚無系統」**：與 `interaction-spec`
  字面一致。代價：`AC9.2.1` 的 Then 在「建了專案、還沒建系統」時不成立，只能把它重新
  詮釋為「專案出現在清單中（但不可選）」——那是改寫 AC 的語意，不是滿足它。
- **C. 只有系統可選，但建立專案成功後自動把作業對象切到該專案**：建立當下 `AC9.2.1`
  成立（依 `interaction-spec.md:377` 的「成功後切過去」）。代價：使用者一旦切走，就
  **再也選不回**那個專案，直到替它建一個系統——「可選」只在建立後的一瞬間成立。
- **D. 三層都可選（專案／系統／架構圖）**：最完整。代價：選單需要逐系統列出架構圖，
  而目前**沒有**「依系統列出架構圖」的端點（`hierarchy_router.py` 只有專案、系統、
  變更紀錄的列舉），需新增後端端點與 `TestClient` 測試；且新建的圖多無系統歸屬
  （`OPEN-H11`），清單會漏掉它們。
- **X. Other**

[Answer]: A  <!-- answered 2026-10-17T23:49:49Z via picker -->

## OP3. 選單看得到、大腦卻不接受的專案（被邀請的非擁有者成員），怎麼呈現？

前提見 §三 事實 3。不處理的後果：成員點了一個清單上的專案，伺服器回 `error`、脈絡列
不變，使用者看不出為什麼。

- **A.（建議）照列，但非擁有者的專案（與其下系統）不可選，以停用列 ＋ 一行說明
  「大腦目前只能以你建立的專案為作業對象」呈現**：判定式 `owner_user_id === 目前使用者
  id`，與 `U23` `SystemCreateAction` 的擁有者判定同一欄位、同一方向（`SystemCreateAction.tsx:9-11`），
  不另行推導。沿用 `U24`／`U15` 的同一條理由——**永不渲染一個送出必然被拒的控件**。
  零後端改動；`OPEN-PP23-6` ③ 的落差被**看得見地**呈現而非隱藏。代價：成員看得到
  卻選不了，需要那一行說明承擔解釋；`owner_user_id` 在前端多一個使用點（`U23` 的
  `PPN-16` 只約束 `U23` 自己的程式）。
- **B. 前端過濾，只列擁有者的專案**：畫面上沒有不可選的列。代價：等於在前端再實作
  一次可見範圍（與伺服器的「成員列 ∪ 擁有者」並存兩份規則），且成員在專案頁看得到的
  專案在選單裡**無聲消失**，比 A 更難理解。
- **C. 照列且可選，送出被拒時在選單內顯示錯誤**：程式最少。代價：使用者看到可點的
  控件、點了才失敗——正是 `U24` 兩段式 `canManage` 剛消除的形狀；且閘道的 `error` 訊框
  沒有 turnId，本單元要另做「把這則錯誤歸給剛才那次選取」的對應。
- **D. 把大腦端的解析改為成員可見範圍**（`resolve_work_target`／`describe_work_target`
  改用 `project_visible`）：根治。代價：改動已交付的 `U7`／`U10`／`U13` 的授權範圍，
  屬 ADR-0006 IAM 面向的變更（擴大可解析的資源集合），需新 ADR 與 allow/deny 雙向測試；
  `OPEN-PP23-6` 已把它交使用者決定是否另開 intent，本單元單方面做會越過那個決定。
- **X. Other**

[Answer]: A  <!-- answered 2026-10-17T23:49:49Z via picker -->

## OP4. 「+ 新增系統」放在哪裡、何時出現？（「+ 新增專案」何時出現一併定）

前提見 §三 事實 4。

- **A.（建議）每個專案群組標題旁各一個「+ 新增系統」，父專案即該群組；只在
  `owner_user_id === 目前使用者 id && can('K2','edit')` 時渲染**（與 `SystemCreateAction`
  逐字同一判定）。底部只留「+ 新增專案」，只在 `can('K2','edit')` 時渲染（與 `/projects/new`
  的 `CapabilityRoute storyId="K2" action="edit"` 同一判定，`App.tsx:146`）。無 `K2 edit`
  且清單為空時，`empty` 態只顯示說明、不顯示建立入口。代價：偏離 `mockups.md` M4 的
  「底部兩個並排按鈕」與 `interaction-spec.md:284` 的「先選一個專案」停用說明——
  父專案由位置決定，「先選」這個狀態不再存在。須記為對齊修正。
- **B. 維持底部兩鈕；父專案＝目前作業對象的專案**：與線框一致。無作業對象專案時停用並
  說明「先選一個專案」；目前專案非自己擁有時停用並說明「只能在你建立的專案下新增系統」。
  代價：要在**別的**專案下建系統，得先關選單、選那個專案、再開選單——兩步；且依賴
  `OP2`=A（專案可選），否則零系統的專案永遠成不了「目前專案」。
- **C. 維持底部兩鈕；「+ 新增系統」展開的表單多一個「所屬專案」下拉（只列自己擁有的）**：
  一步完成、與線框位置一致。代價：表單由「只要名稱」（`interaction-spec.md:287`）變成
  兩欄，且在覆蓋層 dialog 裡再放一個下拉，鍵盤與焦點陷阱的處理變複雜。
- **D. 選單內只做「+ 新增專案」，系統一律到專案頁建立（`U23` 已交付）**：本單元最簡單。
  代價：`AC9.2.2` 在本單元沒有入口，只能靠 `U23`；`[DM:D2]`=D 的「選單就地建立」只剩一半。
- **X. Other**

[Answer]: A  <!-- answered 2026-10-17T23:49:49Z via picker -->

## 五、其他單元指派給 `U16` 的義務與預定處置

以 `object-picker-ui`、`U16`、`ObjectPicker`、`ObjectCreateAction`、`CreateConfirmCard`
五個詞 grep `inception/**` 與 `construction/**`（審查紀錄 `reviews/` 只作證據、不作指派
來源）。逐項列出：

| # | 義務 | 來源（逐字出處） | 預定處置 |
|---|---|---|---|
| D-1 | 沿用 `objectCreateAction`，不得自建建立路徑 | `OPEN-PP23-8`（`project-pages-ui/functional-design/functional-spec.md:303`）；`project-pages-ui/functional-design/rules.md:87`（`BR82.1`）；`objectCreateAction.ts:4` | **承接**。選單建立一律呼叫它；`INV-2` 的 grep 斷言仍為「一處實作」 |
| D-2 | 以 `ContextBar` 掛載點接入選單；選定回呼轉 `set_work_target`、不本地改脈絡列；未掛載不渲染「切換對象」鈕 | K-13（`contract-summary.md:1017-1056`）；`U14` `BR97.7`（`entry-page-ui/functional-design/rules.md:517-524`）；`entry-page-ui/functional-design/traceability.json:78` | **承接**，但掛載形狀須偏離 K-13 的 props 字面（§三 事實 5），見 §六 第 1 項 |
| D-3 | `AC9.2.1`／`AC9.2.2` 的 Then（出現在可選作業對象中）需要本單元的選單 | `rbac-story-ids/functional-design/traceability.json:39`、`:44`、`:81` | **承接**，可滿足性依 `OP2`／`OP4` |
| D-4 | 刪除被拒（專案仍有系統、系統仍有圖）的錯誤訊息「畫面面」 | `hierarchy-data/functional-design/rules.md:222-223`（`BR3.2`，「落點 U7（介面面）與 U16（畫面面）」）；`hierarchy-data/code-generation/traceability.json:40` | **不承接**：本單元的交付（`unit-of-work.md:196`）**不含刪除控件**，選單無刪除入口；刪除的使用者入口若存在應在專案頁。屬 `U23` 範圍的延伸、`U23` 已交付，**本 intent 內無自然承接站**，交 conductor 於關卡重新提交使用者 |
| D-5 | 新建架構圖時的系統歸屬選擇（`OQ-H2`／`OPEN-H11` 的「畫面面」）；連帶 `S-7`（若收成 NOT NULL 的夾具順序） | `hierarchy-data/functional-design/functional-spec.md:284`；`hierarchy-data/code-generation/traceability.json:65`；`hierarchy-data/nfr-requirements/security-requirements.md:169`；`entry-page-ui/functional-design/functional-spec.md:339`（`OPEN-EP14-17`「根治需新建圖時指派系統（U7／U16 的範圍）」） | **不承接**：建圖路徑在既有 `collab_router`／A1（`hierarchy-service/functional-design/functional-spec.md:203-207`），而目前**沒有任何**「指派圖到系統」的寫入端點；本單元做它就要新增後端端點，超出 `kind: ui`。`S-7` 只在 `OQ-H2` 收成 NOT NULL 時成立，本單元不收，故不觸發。**本 intent 內無自然承接站**（`U7` 已交付），交 conductor 於關卡重新提交使用者 |
| D-6 | `U12` 行動者解析失敗（`S-11`）的「訊息呈現」 | `hierarchy-data/nfr-design/security-design.md:146`、`:158`；`hierarchy-data/nfr-design/traceability.json:107` | **不承接**：該失敗發生在大腦改圖的回合內，經閘道 `error` 訊框送到**對話流**，而對話流的錯誤呈現屬 `U14`（已交付）。本單元的畫面不會收到它。記為「落點誤指」並在產出寫明正確落點為 `U14` |
| D-7 | `AC9.1.3`（遷移不改變既有頁面行為）的 e2e 斷言，「落點 U16 或既有 Playwright 層」 | `hierarchy-data/nfr-requirements/security-requirements.md:198`；`hierarchy-data/nfr-requirements/traceability.json:183`；`hierarchy-data/code-generation/code-summary.md:279` | **附帶承接（非本單元 AC）**：本單元本來就要改 `/workspace` 上的 `ContextBar`，順帶加一案「無系統歸屬的既有圖在 `/workspace` 照常開啟、脈絡列只顯示圖名」。夾具可構造（既有存圖路徑不寫 `system_id`）。不列入 `upstream_ids`，於 `traceability.json` 的 note 記明 |
| D-8 | 選單是否把預設專案排最前 | `hierarchy-data/functional-design/functional-spec.md:318` | **不特別排序**：沿用伺服器的 id 遞增（`hierarchy_router.py:156` 的 docstring），預設專案（遷移時建立、id 最小者）自然在前；不在前端另排 |
| D-9 | `NFR11`（跨功能任務的頁面切換次數）在 `U23`／`U16` 量測 | `hierarchy-service/nfr-requirements/traceability.json:142`；`hierarchy-service/nfr-requirements/observability-requirements.md:10` | **不承接，且指出指派與上游不符**：`requirements.md:577-578` 逐字把量測機制落點定在 `build-and-test`（3.6，ALWAYS），不是任何單元。本單元的選單**會**減少切換（入口頁內即可換對象與建立），產出中會列出它影響的情境供 `build-and-test` 計數 |
| D-10 | `US2.x`／`US3.1`／`US9.1` 等多條 AC「承載完全在 U13／U14／U16 的使用者可見層」 | `session-store/code-generation/traceability.json:141-256`、`:897-922` | **不承接**：story map 把那些故事指給 `U14`（`unit-of-work-story-map.md` 主表），`U16` 只承載 `US9.2`。該處的 `U16` 是泛稱消費端，不是指派 |
| D-11 | `BR97.7` 為 N/A、「承接 AC 屬 U16」 | `entry-page-ui/functional-design/traceability.json:78` | 同 D-2，承接 |

## 六、本站預定處置（非提問；產出時寫明理由，供審查攻擊）

1. **`ContextBar` 掛載形狀（§三 事實 5）**：在 `ContextBar.tsx` 內渲染「切換對象」鈕
   （`brain-context-switch-object`）並開啟 `ObjectPicker`；作業對象取自
   `useBrainSession().target`、送出走 `setWorkTarget`。不新增 prop、三個頁面檔不動。
   理由：已交付的 `ContextBar` 以 context 取代了 K-13 的 props，再加 props 會形成兩條
   資料路徑。「切換對象」鈕只在 `status === 'ready'` 時可用（`setWorkTarget` 在未 ready
   時回 `false`、不送），以免渲染點了沒反應的鈕（`BR97.7` 的意圖）。此為對 K-13
   `props_contract` 字面的**對齊修正**，於產出明記。
2. **清單抓取**：先 `listProjects`，再對每個專案 `listSystems`，扇出沿用 `U23` 的
   `fanoutQueue`（同時最多 4 個、FIFO、不截斷；`fanoutQueue.ts:1-28`）。每次開啟選單
   重抓（不快取），因為其他頁面的建立與成員變動都會讓快取過期。任一請求失敗即整個
   選單進 `error` 態（不呈現部分清單——同 `BR88.3`「不把部分資料呈現成完整資料」）。
3. **搜尋**：只在已載入的清單上做前端比對（專案名或系統名包含關鍵字），不發請求。
4. **子頁面上選取後的提示**：在 `/workspace` 選了新對象，`U14` 的
   `useWorkspaceTargetSync` 會把伺服器回推視為外來改變並顯示「作業對象已改為 X」
   （`useWorkspaceTargetSync.ts:217-248`），畫布不自動換圖。本單元**沿用此行為、不改
   `U14` 的同步掛點**：使用者剛做的選擇被如實告知且不覆蓋畫布上未儲存的內容。代價是
   使用者自己的動作也會收到一次提示——於產出揭露。
5. **載入態**：沿用 `U23` `ProjectList` 已建立的骨架列形狀（`design-system-mapping.md`
   修訂 1 §11），不用整頁 spinner（`H-5` 的同型問題）。
6. **焦點陷阱與焦點返還**：既有五個 modal 都沒有（`design-system-mapping.md` 修訂 1 §11
   的 `InviteMemberDialog` 列逐字），本單元為新建，限定在選單元件內、不抽共用工具
   （只有一個使用點）。

## 七、ADR-0006 四面向 ＋ PBT 預判（自檢第七項，依作答結果於產出定稿）

| 面向 | 預判 | 理由 |
|---|---|---|
| IAM | **適用（呈現層）** | 建立入口與可選性的顯示條件依 `K2 view／edit` 與擁有者欄位；授權權威仍在伺服器（`U7`）。`OP3`=D 會使本面向升為**實質適用**（擴大可解析資源） |
| Encryption | 不適用 | 不新增儲存、不新增傳輸；HTTP 與 WebSocket 皆沿用既有通道 |
| Network exposure | 不適用 | 不新增端點（`OP1`=B、`OP2`=D 例外，屆時重判） |
| Audit logging | 不適用（本單元） | 建立的稽核由 `U7` 的 `create_*` 承擔（K-07 `observable_side_effects`）；`set_work_target` 不寫稽核屬既有設計 |
| PBT（hard constraint） | 不適用 | 本單元不含 IaC generator、cost calculator、agent routing（`OP1`=B 會動到 agent routing，屆時轉為 blocking） |

## 八、歧義分析（Step 3，待作答後填寫）

（作答後逐項檢查含糊答案、跨題矛盾與產出所缺細節。已知的跨題耦合：`OP4`=B 依賴
`OP2`=A；`OP3` 的判定式與 `OP4`=A 的判定式為同一欄位，選定後須確認兩者一致。）

### 八之一、作答後的檢查結果（2026-10-17T23:52:24Z 起草產出前填寫，以 `date -u` 取值）

| 檢查 | 結果 |
|---|---|
| 含糊答案（「大概」「看情況」「混用」） | **無**。四題皆為單一字母，各自指向一個可實作的形狀 |
| 跨題矛盾 | **無**。`OP3`=A 的判定 `owner_user_id === 目前使用者 id` 與 `OP4`=A 的「+ 新增系統」判定（同一欄位、同一方向，再加 `can('K2','edit')`）一致：一個專案若不可選，其群組旁也必不出現「+ 新增系統」——不會出現「選不了卻能在底下建系統」的組合。`OP2`=A 使 `OP4`=B 的依賴失去意義（未選 B），不構成矛盾 |
| 產出所缺細節 | **兩項，皆由本站在產出中定案並寫明理由，不另開追問**：① 登入後 `user.id` 尚未回來的視窗內，`OP3`／`OP4` 的擁有者判定不可判定——比照 `U15` 的同型處置，清單在 `user.id` 成為數字前維持 `loading`（`rules.md` `BR12.3`）；② `OP2`=A 之下「專案列」的 `data-testid` 不在已核可清單內——本站新增 `brain-object-project-{id}`，並把 `brain-object-create-system` 改為帶專案 id 的 `brain-object-create-system-{projectId}`，兩者記為對齊修正（`functional-spec.md §三之一`） |
| `OP1`=A 的後果是否已向使用者揭露 | **是**——選項本文逐字寫明「交付清單少一項……必須在本站產出與關卡明寫為範圍縮減」。產出中以 `OPEN-OP16-1` 承載，關卡由 conductor 重新提交 |
