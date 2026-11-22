# Functional Design 問題檔 — `U10 session-store`

> 本單元的 depth 為 **Minimal**，故只問「預設錯了會造成真實重工」的題目。
> 下方「上游已定案、不重問」一節逐項列出被省略的事項與其定案出處。

## 本站的指派來源（不是我自己挑的題目）

`contract-design` 的 `contract-summary.md` 把**兩項**待決逐字指派給本站，並明訂
兩者**必須一併決定**：

| id | 逐字內容 | 指派落點（逐字） |
|---|---|---|
| `OQ-1` | 「切回共享對話時，獨立那段的內容如何處置（保留／捨棄／可回溯）」 | `:1423`「**無站承接**——`domain-design` 未定案並轉移 `units-generation`，該站亦未定案。須與 `functional-design` 的歷程 schema 一併決定」 |
| `OQ-N4` | 「**`BrainSession` 的形狀撐不起 `[DD:E6]`=A 自己要求的『兩段』。**」`messageHistory` 只有**一個**、`append_message(session_key, role, text)` **沒有任何參數說這則訊息屬於哪一段** | `:1433`「`functional-design`（3.1，CONDITIONAL、per-unit…）。**與 `OQ-1` 必須一併決定**——分段的表達方式與切回時的處置是同一個設計」 |

**轉移鏈的兩端都合規，缺口卻因此落在中間**：`domain-design/memory.md:36` 自承未定案
並轉移 `units-generation`；而 `unit-of-work.md:479` 逐字「`OQ-1`…的轉移條件是
『`domain-design` 被 skip』，而它**實際已執行並完成**，故六項不轉進本站」。本站是第一個
同時具備**指派**與**材料**（歷程 schema 本身）的站，故在此定案。

**`OQ-N4` 的授權範圍（逐字）**：「`U10`（其 `public_interface` 與 `data_shape`
**皆需改**）」。故下方選項中改動 `K-09` 的介面與資料形狀**在既有授權內**；改動
`K-02`（`U2 brain-ws-contract`，**已施工完成**）則**超出**該授權，須另立 ADR 追認。
既有先例為 `brain_ws_contract.py:94-95` 逐字記載的
「`select_clarify_candidate` 為 `functional-design` 審查 R-02 新增…**此擴充超出 `K-02`
的條款，由 `ADR-0019` 作為上游追認的載體**」——同型改動有前例且有載體。

---

## [S1] 「獨立對話」的作用範圍是哪一個？

**為什麼這是本站的第一題**：兩條已核可的上游**不能同時成立**，而選哪一邊決定
`sharingMode` 的基數、`messageHistory` 的分段鍵與 `K-02` 的扇出規則。

- **session 層那一邊**：`x-session-key-derivation` 逐字「**一個使用者一個大腦
  session**」，且「`sharingMode` 是**那一個** session 的欄位，**不是第二個 session**」。
  `K-02` 的 `sharing_mode` 訊息逐字「**同一 session key 的其他連線亦收到此訊息**」，
  `x-concurrent-connections.state_change_fanout` 把 `sharing_mode` 列為三類扇出狀態之一。
- **逐頁那一邊**：`FR3.1` 逐字「使用者得在 `/workspace` 與 `/assessment` 由脈絡元件
  開啟一段新對話」（**只有這兩頁**，入口頁不在內）。`AC3.1.1` 的 Then 逐字
  「該頁進入一段新對話，且**入口頁的脈絡不受影響**」。
- **衝突的機制**：單一 `sharingMode` ＋ 現行扇出 ⇒ 在 `/workspace` 按下「改為獨立
  對話」時，入口頁的連線**也會**收到 `sharing_mode: isolated`，於是入口頁改讀獨立
  那段的（空）歷程。`AC3.1.1` 的後半句因此不成立。

### 選項

- **A（建議）— 獨立對話為「逐頁」**：`sharingMode` 由單一欄位改為「每個可開啟獨立
  對話的頁面各一個模式」（`/workspace`、`/assessment` 各自可為 `shared`｜`isolated`，
  入口頁**恆為** `shared`）。`messageHistory` 以**段識別**分組，段識別即
  `shared`／`workspace`／`assessment`。`sharing_mode` 與 `set_sharing_mode` 兩則
  訊息各加一個頁面識別欄位，扇出只送給**同一頁**的連線。
  - **好處**：`FR3.1`（逐頁）、`AC3.1.1`（入口頁不受影響）、`AC3.1.2`（獨立段不含共享
    訊息）、`AC3.1.4`（切回後共享段原樣）**全部可滿足**；且獨立模式期間 `FR2.1` 的
    三處共享在其餘兩頁**維持有效**。
  - **代價**：改動 `K-09` 的 `data_shape`（在 `OQ-N4` 授權內）**以及** `K-02` 的
    `SharingModePayload`／`SetSharingModePayload`（**超出授權**）。`K-02` 由
    `U2 brain-ws-contract` 擁有且**已施工完成**（`backend/services/brain_ws_contract.py`），
    故須：新立 `ADR-0020` 追認、改該模組、重跑前端型別產生，並回報尚未施工的 `U13`。
- **B — 獨立對話為「整個 session」**：保留單一 `sharingMode` 與現行扇出；按下「改為
  獨立對話」時三處**一起**進入獨立模式。`messageHistory` 仍依 `OQ-N4` 分為兩段。
  - **好處**：`K-02` 完全不動（已施工單元不受影響），改動面最小，只動 `K-09`——完全
    落在 `OQ-N4` 的既有授權內。
  - **代價**：`AC3.1.1` 的「入口頁的脈絡不受影響」**不成立**，須回報 `user-stories`
    並把該子句標為**不可滿足**；且獨立模式期間 `FR2.1` 的「跨三處延續」暫停
    ——而 `FR2.1` 與 `FR3.1` 都是 **Must**。
- **C — 獨立對話掛在「單一條連線」上**：模式不進 Redis、不扇出，由連線自己持有。
  - **代價**：**直接違反 `NFR4`** 逐字「大腦的 session 與工作狀態**一律放 Redis，
    不得放行程記憶體**」——重啟後獨立對話消失，而 `AC2.1.4` 正是重啟還原。另外同一頁
    開兩個分頁會得到兩種模式。**不建議**。
- **D — 本站不定案，再往下游轉一次。**
  - **代價**：`OQ-1` 與 `OQ-N4` 的落點逐字就是本站，且契約逐字「須與 `functional-design`
    的歷程 schema 一併決定」。而歷程 schema **必須**在本站寫出來（它是 `entities.md`
    的交付物），所以轉走之後本站仍得先假設一個答案才能交付——那就是「無來源的定案」。

[Answer]: A（逐頁）
<!-- answered 2026-10-09T12:16:26Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔（project.md refined-mockups:1de098c0） -->

---

## [S2]（`OQ-1`）切回共享對話時，獨立那段怎麼處置？

**已被上游縮小的範圍**：`unit-of-work.md:133` 逐字已寫「獨立那段**保留**但不併入
共享流」，`AC3.1.4` 只斷言**共享那一段**不受影響（故事本文逐字「刻意不對獨立那段的
去向下斷言」）。所以真正未定的是**保留下來的那一段還能不能回去**。

### 選項

- **A（建議）— 保留且可重入**：切回共享後，獨立那段原樣留在同一個 session key 之下；
  再次切到獨立時**回到同一段**而非開新的一段。TTL 到期時與共享那段**一起**消失
  （`ADR-005` 逐字「三者一起消失」）。
  - **好處**：`unit-of-work.md:133` 的「保留」與 `AC3.1.4` 同時成立，且保留下來的
    那一段**有讀者**（重入即讀）。
  - **代價**：筆數上限（`DG-5`，由下一站 `nfr-requirements` 定數值）必須明訂是套在
    **每一段**還是**全部段之和**上。本站會明訂為每段獨立計算並寫出理由。
- **B — 保留但不可重入**：切回共享後那一段留著，但再次切到獨立一律開**新的**一段，
  舊的只能等 TTL 到期。
  - **代價**：保留的那些段**沒有任何讀者**，是純粹的死資料，且佔用同一個 Redis key
    的容量——多次切換會讓單一 key 無上界成長。這與 `refined-mockups` 自檢查出的
    `RecentConversations.hidden` 不可達問題**是同一個形狀**（狀態存在但永不可達）。
- **C — 切回即捨棄**：切回共享的同一個動作刪掉獨立那段。
  - **好處**：單一 key 的容量上界最小、要測的狀態最少。
  - **代價**：**與已核可的 `unit-of-work.md:133` 逐字牴觸**（「保留」），須推翻該單元
    的責任敘述並回報 `units-generation`。
- **D — 本站不定案。** 代價同 `[S1]` 的 D。

[Answer]: A（保留且可重入）
<!-- answered 2026-10-09T12:16:26Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔（project.md refined-mockups:1de098c0） -->

---

## [S3] 切回共享時，「作業對象」要不要也跟著段走？

**本題是我在跑契約端點三問時查出的，不在上游的任何待決清單上。**

`AC3.1.4` 的 Then 逐字是「共享對話的**訊息歷程與作業對象**與我離開時相同」——**兩樣
東西**。而 `x-session-key-derivation.why_one_key.therefore` 逐字是「同一個 key、
**同一組** `currentProjectId`／`currentSystemId`／`currentDiagramId`」，即已核可契約
明文只有**一組**作業對象、兩段共用。同時 `set_work_target` 是 `K-02` 的 client→server
型別之一，**任何一條連線都能呼叫**（已施工：`brain_ws_contract.py` 的
`SetWorkTargetPayload`）。

**所以**：使用者在獨立對話中改了作業對象再切回共享，單一組欄位之下**不可能**讓共享
那段的作業對象「與離開時相同」。`OQ-N4` 只點名了 `messageHistory` 那一半，**沒有**
點名作業對象這一半。

### 選項

- **A（建議）— 作業對象也分段**：每一段各自記住自己的作業對象。切到獨立時以當前
  共享段的值**初始化**（滿足 `FR3.2` 逐字「沿用當前的作業對象」與 `AC3.1.3`），
  之後兩段各自獨立變動；切回共享時讀回共享段自己的值（滿足 `AC3.1.4` 的兩個子句）。
  - **好處**：讓一條 **Must** 故事的 AC 由「條件成立」變回「恆成立」，而不是去收窄它。
  - **代價**：三個作業對象欄位由 session 層下沉到段層，這是 `K-09` 的 `data_shape`
    改動——**落在 `OQ-N4` 逐字授權的 `data_shape` 範圍內**；但它推翻
    `x-session-key-derivation` 的「同一組」那一句，須在本站明記為上游更正並回報。
    `work_target` 扇出需帶段識別（與 `[S1]`=A 是**同一組**改動，不是額外一組）。
- **B — 作業對象維持 session 層單一組**，並把 `AC3.1.4` 的作業對象子句收窄為
  「**不因切換動作本身而改變**」：使用者若在獨立對話中主動改了作業對象，切回後即為新值。
  - **好處**：契約的「同一組」不動，改動面最小。
  - **代價**：`AC3.1.4` 是 Must 故事的 AC，收窄其語意須回報 `user-stories`；該子句
    從此是**條件成立**而非恆成立，且條件（使用者沒去改）不在系統控制內。
- **C — 獨立對話中禁止改作業對象**（isolated 模式下 `set_work_target` 回 `error`）。
  - **代價**：上游**沒有任何一句**支持這個限制。而獨立對話的用途逐字是「手上這段討論
    不被新的問題打斷」（`US3.1`），新問題很可能正是關於**另一個**對象——禁止改對象
    會讓獨立對話對它自己的使用情境失效。
- **D — 本站不定案，回報 `user-stories` 由該站裁決。**
  - **代價**：`user-stories` 在本工作流程中**已完成且在游標之前**，不是有效的承接站
    （這正是 `project.md` 記過兩次的「死指派」形狀）。本題若不定案，`entities.md`
    仍須寫出作業對象欄位掛在哪一層，等於還是由本站代答。

[Answer]: A（作業對象也分段）
<!-- answered 2026-10-09T12:16:26Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔（project.md refined-mockups:1de098c0） -->

---

## 上游已定案、不重問（逐項附定案出處）

| 事項 | 定案（逐字出處） |
|---|---|
| `session_key` 由誰產生、一人幾個 session | `x-session-key-derivation`：「`U13` 在握手成功後產生」、「`derived_from`: 已驗證使用者的 id。**一個使用者一個大腦 session**」 |
| 同一 key 可否有多條並存連線 | `x-concurrent-connections.multiple_allowed`：「同一個 session key **允許多條並存連線**（三個頁面、多個分頁）。伺服器不以連線為狀態單位」 |
| 狀態改變要不要扇出 | 同上 `state_change_fanout`：`work_target`／`sharing_mode`／`work_items` 三類「推送給該 key 的**全部存活連線**」 |
| TTL 的長度與續期時機 | `ADR-005` ＋ `K-09`：單一 key、TTL 24 小時、**每次互動續期**；`behaviour_semantics.observable_side_effects` 逐字「全部方法都會續期 TTL」 |
| TTL 到期時清掉什麼 | `ADR-005`：作業對象、共享狀態、對話歷程、工作項集合**一起消失**，下次進入為全新 session 且作業對象回到未選定 |
| 誰清 session（`OQ-9`） | `ADR-005` 已關閉：TTL 即清除機制，**不另設顯式清除路徑**（其 Alternatives Rejected 逐字拒絕「TTL ＋ 顯式清除並存」） |
| 共享範圍涵蓋哪幾頁 | `FR2.1`／`K-09.shared_scope`：入口頁、`/workspace`、`/assessment` 三處；**不含** `/admin/*` 與 `/cost` |
| 狀態放哪裡 | `NFR4`：一律 Redis，**不得放行程記憶體**；既有三處行程內狀態容器不在本 intent 範圍 |
| 本單元要不要自己判權 | `K-09.behaviour_semantics.authorization_responsibility`：「本單元**不自行判權**；`set_work_target` 的授權由 `K-07` 承擔」 |
| 三層識別怎麼驗證 | `K-09.set_work_target.note`：經 `K-07` 的 `HierarchyFacade.resolve_work_target` 驗證，`HierarchyForbidden` **原樣向上傳遞** |
| 哪些方法冪等 | `K-09.behaviour_semantics.retry_and_idempotency`：`load`／`touch`／`set_*` 冪等可重試；`append_message` **非冪等** |
| 對話歷史的保存期限與筆數上限 | **刻意不在本站定**：`ADR-016` 逐字「數值由 `nfr-requirements` 決定」；`unit-of-work.md:479` 逐字確認它「**留在 `nfr-requirements`**，本站不假裝接手」。本站只把它寫成**具名參數**並明訂缺值行為 |
| 獨立對話要不要沿用作業對象 | `FR3.2` 逐字「新對話**不共享任何訊息歷程**，但**沿用當前的作業對象**」——`[S3]` 問的是**之後**兩段各自變動時的語意，不是初始化 |

## 本站不出成題目、但必須寫進產出的三項推論

1. **對話歷史上限的缺值行為 = 大聲失敗**。既有前例為 `ADR-008` 的 `EMBEDDING_PROVIDER`
   （`K-01` 逐字「刻意無預設：偵測不到選定提供者時須大聲失敗」）。把「無值」解讀為
   「無上限」會讓單一 Redis key 無上界成長，而那是 `project.md` 一再記載的無聲失敗
   形狀。**不在本站填數字**，但缺值時服務不得以「無上限」啟動。
2. **作業對象的三元組必須容許「部分」值**。實測 `hierarchy_service.py:261-273`：只給
   `diagram_id` 時，`resolve_work_target` 僅在 `diagram.system_id is not None` 時推導
   上層，否則回 `{projectId: None, systemId: None, diagramId: X}` 並**刻意不拒絕**
   （逐字「圖本身的擁有者已驗證過」）。成因是 `OPEN-H11`（新建的圖從未被指派系統
   歸屬），**至今無承接站**。故 `AC9.1.1` 的「完整的三層路徑」對這類圖**不可滿足**；
   本站的規則如實允許部分三元組，不偽造上層、也不拒絕儲存。
3. **本單元必須新增一個 Python 依賴（Redis 客戶端）**。實測 `backend/requirements.txt`
   無任何 Redis 客戶端、全 `backend/` 僅 `.env.example` 與 `test_render_env_redis.py`
   兩處提及 `REDIS_*`。這與 `U8` 的「`requirements.txt` diff 必須為空」**相反**，
   且 `requirements.txt` 的檔頭自帶釘選紀律——取用方式由 `code-generation` 決定，
   本站只記錄這個事實不是可選項。
