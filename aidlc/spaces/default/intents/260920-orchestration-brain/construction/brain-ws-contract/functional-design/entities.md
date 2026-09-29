# Entities — `U2 brain-ws-contract`（`spec`）

## 〇、這個單元的「實體」是什麼

本單元交付的不是資料庫實體，而是**前後端共用的 WebSocket 訊息型別**。它們是傳輸中的
資料形狀，沒有持久化、沒有主鍵、沒有生命週期——所以下面的實體模型描述的是**訊息封包與
其 payload 的結構**，關係欄位描述的是**封包與 payload 的組成關係**，不是資料庫外鍵。

真實來源是後端的 Pydantic 模型（`[C2]`=A）。本檔是那份模型的**邏輯規格**，技術中立、
不含程式碼。

## 一、source of truth

```yaml
entities:
  - name: WsEnvelope
    description: >
      **伺服器→客戶端**訊息的外層封包。K-02:215 的 envelope 逐字宣告
      `direction: server_to_client`，故本實體只涵蓋那個方向。
      **本站初版錯誤地宣稱「兩個方向皆用同一個封包形狀」**（審查 R-05，Major）：
      那是本站的擴充而非上游原文，且它製造不可構造的訊息——hello 發生在任何一輪之前、
      set_sharing_mode 與 set_work_target 是狀態訊息不屬任何一輪（BR2.7 明文不計入
      終止事件上限），三者都無法給出有意義的 turnId，而 turnId 的產生方式又被本站
      歸給 U13。客戶端方向改由 WsClientEnvelope 定義，不含 turnId。
    attributes:
      - name: v
        logical_type: integer_literal
        allowed_values: [1]
        required: true
        constraints: >
          **本站由 K-02 的 `type: integer` 收窄為字面值 `1`**（Q6=A）。收窄的理由：
          Q2=A 定「相容判準為完全相等」，而完全相等在型別層的忠實表達就是字面值；
          且它讓「當前協定版本是 1」這個事實只存在於契約一處，前端不需要第二份副本。
          升版時把字面值改為 2 會讓所有仍寫 1 的消費端立即成為型別錯誤。
          **但字面值只適用於「符合本版」的訊息**——不相容的 hello 在這個型別下不可表示，
          而 K-12 的 4400 關閉要求帶 received。故本契約另定 WsUnvalidatedEnvelope（見下），
          兩者的分工寫在該實體的 constraints（審查 R-03，Critical）。
      - name: type
        logical_type: string_enum
        required: true
        constraints: >
          值域見 WsServerMessageType（**只有它**——審查 R-17 更正：R-05 已把本實體
          收窄為伺服器方向，但此處的 constraints 仍殘留「與 WsClientMessageType
          兩個列舉」的共用封包寫法）。客戶端方向見 WsClientEnvelope。
      - name: turnId
        logical_type: string_or_null
        required: true
        constraints: >
          **欄位必存在，但值可為 null（審查 R-14，Critical 更正）。** 初版定為
          `logical_type: string` ＋ `required: true`（不可為 null），而本站自己明文宣告
          **有四種伺服器訊息不屬於任何一輪**：ready（「在任何一輪之前送出」）與
          sharing_mode／work_target／work_items 三個狀態訊息（functional-spec.md §二
          逐字「它們不屬於任何一輪」）。那四者因此被要求攜帶一個它們沒有的值。
          **兩類的判準（可機械斷言，見 BR1.6）**：
          **輪次訊息**（token／clarify／cost_card／done／error）→ turnId **必為非 null**，
          同一輪的所有訊息共用同一個值（K-02 逐字）。
          **非輪次訊息**（ready／sharing_mode／work_target／work_items）→ turnId **必為 null**。
          **本站不定義它的產生方式**——那是 U13 的責任（K-12 owns 握手與輪次）。
      - name: payload
        logical_type: object
        required: true
        constraints: 形狀由 type 決定（見下方各 payload 實體）；discriminated union 的判別欄位是 type
    entity_constraints:
      - >
        封包是一個以 `type` 為判別欄位的 discriminated union。任何消費端對 `type` 的
        窮盡處理都應能被型別檢查驗證——這是本單元兩道 CI gate 的價值所在。

  - name: WsClientEnvelope
    description: >
      **客戶端→伺服器**訊息的外層封包（審查 R-05 新增）。K-02:270 的 client_to_server
      只列 payload、不列封包欄位，故本封包的欄位集合由本站定義並標示為擴充。
    attributes:
      - name: v
        logical_type: integer_literal
        allowed_values: [1]
        required: true
        constraints: 同 WsEnvelope.v；不相容的入站 hello 見 WsUnvalidatedEnvelope
      - name: type
        logical_type: string_enum
        required: true
        constraints: 值域見 WsClientMessageType
      - name: turnId
        logical_type: "不存在（本欄位已移除）"
        required: false
        constraints: >
          **審查 R-20（Major）：本欄位自客戶端封包移除。** 初版定為
          string_or_null ＋ required: false，同時同一份檔宣告「turnId 由伺服器產生（U13），
          客戶端沒有它」——即客戶端**沒有任何合法理由寫它**，卻被契約允許寫，
          而沒有任何規則要求伺服器忽略或拒絕它（BR2.12 只禁止攜帶「身分」）。
          那是一個客戶端可寫、伺服器未定義如何處置的欄位，正是本站在別處反覆消除的形狀。
          **處置**：客戶端封包**不含** turnId（回到審查 R-05 原本的建議）。
          伺服器以連線與輪次狀態自行判定訊息屬哪一輪——那本來就是 U13 的責任。
          **對應的伺服器義務**見 BR2.13：收到任何帶 turnId 的客戶端訊息即為協定違規。
      - name: payload
        logical_type: object
        required: true
        constraints: 形狀由 type 決定（discriminated union，判別欄位為 type）

  - name: WsUnvalidatedEnvelope
    description: >
      **任一方在信任邊界上解析入站訊息所用的寬鬆封包**（審查 R-03 新增；
      **審查 R-16 由單向改為雙向並更名**，原名 WsUnvalidatedEnvelope 只涵蓋
      客戶端→伺服器，使兩條消費端義務無型別可用）。
      **伺服器側**：讓不相容的 hello 能被反序列化，使 U13 取得 K-12 的 4400 關閉
      所要求的 received 值。
      **客戶端側**：讓 BR3.2（未知 type 安全忽略）與 BR3.5（驗證
      ready.protocolVersion）有型別承載——那兩條規則要求前端表示**封閉列舉與
      字面型別之外**的值，而 WsEnvelope 的封閉 type 與字面 v 在型別上不可表示它們。
    attributes:
      - name: v
        logical_type: integer
        required: true
        constraints: >
          **整數，不收窄為字面值**——這正是它與 WsClientEnvelope 的差別。
          U13 的握手流程：以本型別解析首則訊息 → 取 v → 與本版的 1 比對
          → 相等則之後一律以 WsClientEnvelope 處理；不相等則以 4400 關閉，
          expected=1、received=解析到的 v。
      - name: type
        logical_type: string
        required: true
        constraints: >
          **寬鬆字串，不收窄為列舉**——入站訊息可能來自不同版本的客戶端，
          其 type 可能不在本版列舉內。收窄會讓「未知 type」在型別層不可表示，
          而 BR3.2 正需要能表示它。
      - name: payload
        logical_type: object
        required: true
        constraints: 未經驗證的原始物件；驗證通過後才轉為具體 payload 型別
    entity_constraints:
      - >
        **本實體只用於入站解析的第一步**，不得用於構造出站訊息，且**驗證通過之後**
        不得繼續流入業務邏輯——驗證通過即轉為 WsEnvelope 或 WsClientEnvelope。
        它是信任邊界的閘門（`code-generation-patterns.md` 的
        「External Input → Validate at boundary → Convert to domain type」形狀）。
        **審查 R-16 的更正**：初版寫「不得出現在任何消費端的業務邏輯」，那句過嚴且
        與 BR3.2／BR3.5 直接矛盾——那兩條規則的處置（安全忽略、協商失敗提示）
        **本身就發生在驗證失敗的分支上**，必須讀得到未驗證的值。
      - >
        **expected 與 received 兩個欄位本身沒有型別承載**：K-12:991 要求 4400 關閉
        「帶 expected 與 received」，但那是**關閉訊框的原因字串**，不是訊息 payload。
        Q4=A 把關閉碼排除在契約檔外，而被排除的其實不只「碼」還包括「關閉時要帶的資料」
        ——這一點初版沒有寫出來（審查 R-03）。落點：U13／K-12。

  - name: WsServerMessageType
    description: >
      伺服器→客戶端的 type 值域。**九個值**：K-02:215–269 逐字列舉八個，
      本站新增 ready（審查 R-01，Critical）。
    attributes:
      - name: value
        logical_type: string_enum
        required: true
        allowed_values: [ready, token, clarify, work_items, cost_card, sharing_mode, work_target, done, error]
    entity_constraints:
      - "`done` 與 `error` 是**終止事件**；其餘六個不是（K-12 x-termination-semantics）"
      - "`sharing_mode`、`work_target`、`work_items` 是**狀態訊息**，狀態改變時扇出給同一 session key 的全部存活連線（K-12 x-concurrent-connections）"
      - "components.md 逐字列舉的六種為**下限**，不得更少；K-02 為八種（含修訂新增的 sharing_mode 與 work_target），本站為**九種**"
      - >
        **ready 是本站新增的第九個值（審查 R-01，Critical）。** 由來：K-12 的
        x-handshake.step_3 逐字「伺服器比對 v；**相容則回 `ready`**，不相容則以 4400
        關閉並帶原因」（contract-summary.md:948，全檔唯一命中），而 K-02 的 type 清單
        **沒有 ready**——兩個已核可契約在此直接矛盾。
        **⚠ 授權依據本輪更正（審查 R-23）**：初版寫「K-02:220 逐字寫該清單為下限，
        所以新增在契約自身的條款內」——**那是誤讀**。:220 逐字為
        「`types:` # **components.md 逐字列舉的六種**為下限，不得更少」，
        主詞是 components.md 的六種，該註記說的是「這份清單不得少於那六種」，
        **不是「這份清單本身是下游可以擴充的下限」**。
        **故新增 ready 與新增 select_clarify_candidate 是同一種性質：超出 K-02 的擴充，
        需上游追認。** 本站仍新增它，理由不是授權而是必要性——K-12:948 明文要求它，
        不補則握手完成訊號沒有型別承載；但性質必須標對。
        **初版的錯誤處置**：SM-1 把 K-12 的 ready **訊息**轉成了狀態名 Ready，
        使矛盾在狀態圖上看起來已解決——而實際後果是 U13 依 K-12 送出 ready 時，
        該 type 不在封閉列舉內，會被 BR3.2 判為未知 type 並被前端安全忽略，
        **握手完成訊號靜默消失**。

  - name: WsClientMessageType
    description: >
      客戶端→伺服器的 type 值域。**六個值**：K-02:270–305 逐字列舉五個，
      本站新增 select_clarify_candidate（審查 R-02，Critical）。
    attributes:
      - name: value
        logical_type: string_enum
        required: true
        allowed_values: [hello, user_message, select_clarify_candidate, correct_work_item, set_sharing_mode, set_work_target]
    entity_constraints:
      - "`hello` 必須是握手後的**首則**訊息（K-12 x-handshake.step_2）"
      - "客戶端**不得**在任何訊息內自帶身分——principal 綁在連線上（K-12 x-authorization-responsibility）"
      - >
        **select_clarify_candidate 是本站新增的第六個值（審查 R-02，Critical），
        且它超出 K-02 的條款、需上游追認。** 與 server 方向不同，K-02:270 的
        client_to_server 清單**沒有「下限」註記**，所以這是一個真正的擴充。
        新增它的理由：AC1.2.2（選定候選後依該候選交辦）與 AC1.2.3（選「都不是」）
        在原契約下**傳輸面不可構造**——五個既有 client type 裡沒有一個能承載候選的 id
        （UserMessagePayload 只有 text），而 ClarifyCandidate.id 因此是一個
        **有寫入端、無讀取端的懸空欄位**（K-10 於 contract-summary.md:763 定義它，
        無任何契約消費它）。且 K-12:920 一帶逐字寫「U14 的**唯一**後端通道是本端點」，
        所以不存在「走別條路」的可能。
        **初版的錯誤處置**：把 AC1.2.2 標 Deferred 並在 target 寫「走既有 user_message
        或 U11 定義的路徑」——但 U11 不擁有任何傳輸面，那條路徑不存在，
        Deferred 把一個契約缺口寫成了單純的分工。

  # --- server → client payloads（八個）---

  - name: ReadyPayload
    description: >
      握手完成訊號（審查 R-01 新增）。K-12 的 x-handshake.step_3 要求相容時回 ready。
    attributes:
      - name: protocolVersion
        logical_type: integer_literal
        allowed_values: [1]
        required: true
        constraints: >
          回送伺服器接受的版本，使客戶端可自行確認協商結果而不必推論。
          **本站選這個欄位而非空 payload 的理由**：空 payload 會讓「ready 到了」與
          「ready 的內容正確」無法區分；帶版本則使 BR1.1 的不變量在握手回覆上也成立。
    entity_constraints:
      - "**非終止事件**，不計入 BR2.7 的每輪至多一個終止事件"
      - "它在任何一輪之前送出，故其 envelope 的 turnId 語意見 BR1.3 的適用範圍說明"

  - name: TokenPayload
    description: 內容 token。串流回覆的最小單位。
    attributes:
      - name: text
        logical_type: string
        required: true
        constraints: >
          **非空白**。K-02 逐字「零內容不得以 done 結束」——空白 token 不算內容，
          見 K-12 的終止語意。

  - name: ClarifyPayload
    description: 信心值低於門檻時列出的候選判讀（AC1.2.1／AC1.2.2／AC1.2.3 的傳輸面）。
    attributes:
      - name: candidates
        logical_type: array_of ClarifyCandidate
        required: true
        min: 1
        constraints: 空陣列無意義——若無候選則不應送 clarify

  - name: ClarifyCandidate
    description: 一個候選判讀。
    attributes:
      - name: id
        logical_type: string
        required: true
      - name: label
        logical_type: string
        required: true
      - name: capability
        logical_type: string
        required: true
      - name: confidence
        logical_type: number_or_null
        required: false
        min: 0
        max: 1
        constraints: >
          **選填，且不得列為必填**（components.md 逐字、mockups.md H-2）。
          定義域 0–1（AC1.2.4）。容許 null 使 OQ-10（路由層能否產出可比較的信心值）
          若收斂為「不能」時本型別不需改動。

  - name: WorkItemsPayload
    description: 工作項集合的當前狀態。狀態訊息，會扇出。
    attributes:
      - name: items
        logical_type: array_of WorkItem
        required: true
        min: 0
        constraints: 空陣列合法（尚無工作項）

  - name: WorkItem
    description: 一個工作項。
    attributes:
      - name: workItemId
        logical_type: string
        required: true
      - name: label
        logical_type: string
        required: true
      - name: status
        logical_type: string_enum
        required: true
        allowed_values: ["處理中", "等待中", "完成", "失敗", "已停掉"]
        constraints: 五值為**下限**（[RA:FR1.2]）
      - name: capability
        logical_type: string
        required: true
      - name: waitingOn
        logical_type: string_or_null
        required: true
        constraints: null 表示未等待任何東西；status 為「等待中」時應為非 null
      - name: failureReason
        logical_type: string_or_null
        required: true
        constraints: null 表示未失敗；status 為「失敗」時應為非 null
      - name: sideEffect
        logical_type: string_with_sentinels
        required: true
        allowed_values: ["none", "unknown", "<任意描述文字>"]
        constraints: >
          **兩個哨兵值 ＋ 自由文字**（Q3=A，保留 K-02 原形狀）。`none` 表示確定沒有副作用；
          `unknown` 是**合法值**且語意明確——components.md 逐字「系統不承諾停掉時不留半成品」，
          所以 unknown 不是「還沒填」而是「系統誠實地不知道」。其餘字串為副作用的描述。
          **型別註記義務**：TS 的 `"none" | "unknown" | string` 會塌縮為 `string`，
          IDE 不提示那兩個字面值，故產生的型別檔**必須**在該欄位上方保留說明註解，
          否則這兩個哨兵值的語意會在消費端流失。

  - name: CostCardPayload
    description: 成本卡片。
    attributes:
      - name: estimateSetId
        logical_type: integer
        required: true
        constraints: "**required 是本契約的不變量**（K-02 X-01）"
      - name: savingText
        logical_type: string_or_null
        required: true
      - name: comparisonText
        logical_type: string_or_null
        required: true
      - name: qualityText
        logical_type: string_or_null
        required: true
      - name: unavailableReasons
        logical_type: object_or_null
        required: true
      - name: costPageUrl
        logical_type: string
        required: true

  - name: SharingModePayload
    description: 當前共享模式。狀態訊息，會扇出；亦於連線建立時推送。
    attributes:
      - name: mode
        logical_type: string_enum
        required: true
        allowed_values: [shared, isolated]

  - name: WorkTargetPayload
    description: 當前作業對象（專案／系統／架構圖三層）。狀態訊息，會扇出；亦於連線建立時推送。
    attributes:
      - name: projectId
        logical_type: string_or_null
        required: true
      - name: systemId
        logical_type: string_or_null
        required: true
      - name: diagramId
        logical_type: string_or_null
        required: true
    entity_constraints:
      - >
        三層皆可為 null（尚未選定）。**本站不定義三者之間的階層一致性規則**
        （例如 systemId 非 null 時 projectId 是否必須非 null）——那是 U7 hierarchy-service
        的責任，本單元只定義傳輸形狀。這是刻意的界線，不是遺漏。

  - name: DonePayload
    description: 終止事件——成功產出可呈現的回覆。
    attributes:
      - name: turnId
        logical_type: string
        required: true
    entity_constraints:
      - "前置條件：純文字回覆必須包含**非空白文字**（K-12）。內部推理、控制事件與空白不算內容"
      - "**零內容的 done 在契約上不可能發生**，但消費端不假設對方守約——見 rules.md BR3.3"

  - name: ErrorPayload
    description: 終止事件——未能產出可呈現的回覆。
    attributes:
      - name: code
        logical_type: string_enum
        required: true
        allowed_values: [EMPTY_RESPONSE, INTERNAL_ERROR, UNAUTHORIZED, INVALID_REQUEST]
        constraints: >
          **封閉列舉，本站定義（Q1=A）。** K-02:269 逐字寫「code 的集合見 K-12」，
          但 K-12 定義的是 **WebSocket 關閉碼**（4401／4403／4400／1011），
          **沒有定義 error 訊息的 code**——那是一個懸空引用，本站補上它。
          初版三個的由來：`EMPTY_RESPONSE` 來自 N-14 已定；`INTERNAL_ERROR` 對應
          關閉碼 1011 在「連線仍在、只有這一輪失敗」時的訊息層等價物；
          `UNAUTHORIZED` 對應「有權限問題但連線仍在」（連線建立期的無權限走 4403 關閉，
          不走這裡）；`INVALID_REQUEST` 對應**客戶端請求本身不合法**——
          **本輪補入（審查 R-04，Major）**，由來是上游另有兩處明文的失敗情境無 code 可用：
          contract-summary.md:288 逐字「成功回一則 sharing_mode 訊息帶新模式；**失敗回 error**」，
          :308 逐字「成功回一則 work_target 訊息帶解析後的三層識別；**授權或解析失敗回 error，
          code 見 K-12**」。其中「**解析**失敗」（三層識別解析不出、階層不一致）既非
          EMPTY_RESPONSE、非 UNAUTHORIZED，歸入 INTERNAL_ERROR 又會把使用者輸入問題
          報成伺服器錯誤。
          **:308 是第二處指向 K-12 的懸空 code 引用**——初版只處理了 :269 那一處。
          **新增 code 必須改後端 Pydantic 模型並重跑兩道 gate**——這是封閉列舉的代價，
          也是它的目的。
      - name: message
        logical_type: string
        required: true
        constraints: 人類可讀的說明；**不得包含內部實作細節**
      - name: turnId
        logical_type: string
        required: true

  # --- client → server payloads（五個）---

  - name: HelloPayload
    description: 握手後首則訊息，承載協定版本。
    attributes:
      - name: v
        logical_type: integer_literal
        required: true
        allowed_values: [1]
        constraints: >
          與 WsClientEnvelope.v 同值同型別；入站解析見 WsUnvalidatedEnvelope。
          **token 不在此處**——走 Sec-WebSocket-Protocol 標頭
          （K-12 x-hard-constraints.token_transport）。
          **界線（審查 R-06，Major）**：本 payload 不含 token 欄位，只排除了
          「token 放在**訊息內**」這一條路徑。**它對 query string 零約束**——
          query string 位於 URL，不在 envelope 內，本契約的型別碰不到它。
          實際擋住 AC8.1.3 的是 K-12 的 x-hard-constraints.token_transport
          （contract-summary.md:876–880，明文屬 U13，該處逐字點名既有前例
          collab_router.py:270 正是 query string）。
          初版宣稱「兩者合起來使 token 走標頭在型別上是唯一可構造的形狀」——**那是假的**，
          而它是一條安全面（ADR-0006 network exposure）的 AC，錯誤的型別保證感比沒有保證更危險。

  - name: UserMessagePayload
    description: 使用者送出的一句需求。
    attributes:
      - name: text
        logical_type: string
        required: true

  - name: SelectClarifyCandidatePayload
    description: >
      選定一個候選判讀（審查 R-02 新增）。它是 ClarifyCandidate.id 的唯一讀取端。
    attributes:
      - name: candidateId
        logical_type: string_or_null
        required: true
        constraints: >
          **非 null 表示選定該候選**（值必須是同一輪 clarify 所送出的某個
          ClarifyCandidate.id）；**null 表示「都不是，我再講一次」**（AC1.2.3）。
          **本站選「一個欄位兩種語意」而非兩個 client type 的理由**：兩者是同一個
          決策點的兩個結果，分成兩個 type 會讓消費端必須處理「兩者都沒來」的第三種狀態；
          且 AC1.2.3 逐字要求「脈絡列與作業對象**不變**」——用 null 表達「不選」使
          「不送 work_target」成為自然的實作，而那正是 BR1.2 讓 AC1.2.3 可表達的機制。
    entity_constraints:
      - >
        **伺服器對 null 的處置**：回到輸入狀態，**不送 work_target、不送 work_items**
        （AC1.2.3 的「不變」）。對非 null 的處置：依該候選交辦，流程回到 US1.1 第一步
        （AC1.2.2）。兩者的**實作**在 U13／U11，本單元只定義傳輸形狀。
      - >
        **不驗證 candidateId 是否屬於當前輪次**——那需要伺服器持有上一輪的候選集合，
        屬 U13 的 session 狀態責任。本單元只保證欄位存在且型別正確。

  - name: CorrectWorkItemPayload
    description: 逐項更正一個工作項（[RA:FR1.4]）。
    attributes:
      - name: workItemId
        logical_type: string
        required: true
    entity_constraints:
      - "其餘工作項不受影響（K-02 逐字）"
      - "**冪等**——已停掉者再更正為 no-op（K-12 x-retry-and-idempotency）"

  - name: SetSharingModePayload
    description: 把「改為獨立對話」的選擇傳到伺服器。
    attributes:
      - name: mode
        logical_type: string_enum
        required: true
        allowed_values: [shared, isolated]

  - name: SetWorkTargetPayload
    description: 把選定的作業對象傳到伺服器。
    attributes:
      - name: projectId
        logical_type: string_or_null
        required: true
      - name: systemId
        logical_type: string_or_null
        required: true
      - name: diagramId
        logical_type: string_or_null
        required: true

relationships:
  - from: WsEnvelope
    to: WsServerMessageType
    cardinality: "n:1"
    direction: "伺服器封包的 type 取自此列舉"
  - from: WsClientEnvelope
    to: WsClientMessageType
    cardinality: "n:1"
    direction: "客戶端封包的 type 取自此列舉"
  - from: WsEnvelope
    to: "ReadyPayload｜TokenPayload｜ClarifyPayload｜WorkItemsPayload｜CostCardPayload｜SharingModePayload｜WorkTargetPayload｜DonePayload｜ErrorPayload"
    cardinality: "1:1"
    direction: "伺服器封包持有恰好一個 payload（九種之一），型別由 type 判別"
  - from: WsClientEnvelope
    to: "HelloPayload｜UserMessagePayload｜SelectClarifyCandidatePayload｜CorrectWorkItemPayload｜SetSharingModePayload｜SetWorkTargetPayload"
    cardinality: "1:1"
    direction: "客戶端封包持有恰好一個 payload（六種之一），型別由 type 判別"
  - from: WsUnvalidatedEnvelope
    to: WsClientEnvelope
    cardinality: "1:0..1"
    direction: >
      入站解析的第一步。驗證通過（v == 1 且 type 在列舉內）即轉為 WsClientEnvelope；
      不通過則不轉換——v 不符走 4400 關閉（U13），type 不符走 BR3.2 的安全忽略
  - from: SelectClarifyCandidatePayload
    to: ClarifyCandidate
    cardinality: "n:0..1"
    direction: >
      candidateId 非 null 時指向同一輪 clarify 送出的某個 ClarifyCandidate.id。
      **這是 ClarifyCandidate.id 的唯一讀取端**（審查 R-02：初版它是懸空欄位）
  - from: ClarifyPayload
    to: ClarifyCandidate
    cardinality: "1:n"
    direction: "組成；至少一個"
  - from: WorkItemsPayload
    to: WorkItem
    cardinality: "1:n"
    direction: "組成；可為零個"
```

## 二、實體集合的人類可讀摘要

共 **22 個**實體，逐類實算（腳本解析上方 yaml 的 `- name:`，非目測；審查 R-01／R-02／
R-03／R-05 各新增一個實體後由 18 增為 22）：

| 類別 | 個數 | 成員 |
|---|---|---|
| 封包 | 3 | `WsEnvelope`（伺服器方向）、`WsClientEnvelope`（客戶端方向，R-05 新增）、`WsUnvalidatedEnvelope`（入站寬鬆解析，R-03 新增） |
| type 列舉 | 2 | `WsServerMessageType`（**九**值）、`WsClientMessageType`（**六**值） |
| server→client payload | 9 | `Ready`（R-01 新增）／`Token`／`Clarify`／`WorkItems`／`CostCard`／`SharingMode`／`WorkTarget`／`Done`／`Error` |
| client→server payload | 6 | `Hello`／`UserMessage`／`SelectClarifyCandidate`（R-02 新增）／`CorrectWorkItem`／`SetSharingMode`／`SetWorkTarget` |
| 被組成的子實體 | 2 | `ClarifyCandidate`、`WorkItem` |
| **合計** | **22** | — |

**`BR1.4` 的不變量已機械複驗**：把每個 type 值以 snake→Pascal ＋ `Payload` 後綴正規化後，
九個 server type 與六個 client type **各自一一對應到一個 payload 實體，無缺無餘**
（`server payload 缺: []`、`client payload 缺: []`、`未被任何 type 對應的 payload: []`）。
兩個子實體不參與此對應——判定式見 `rules.md` 的 `BR1.4`。

整個模型的中心是**以 `type` 為判別欄位的 discriminated union**。這個形狀是本單元價值的
來源：只要 `type` 是封閉列舉且每個分支的 payload 形狀確定，消費端對訊息的處理就能被型別
檢查窮盡驗證——而這正是本 repo 目前對 WebSocket **完全沒有**的保護（WS 不在 `openapi.json`
的 42 個 path 內，既有兩道閘門對它無效）。

## 三、本站對上游的收窄、新增與補缺（逐項標示，審查 R-01／R-02／R-05 後重寫）

### 收窄（比上游窄）

1. **`v` 由 `K-02` 逐字的 `type: integer` 收窄為字面值 `1`**（Q6=A）——但**只在出站與
   已驗證的入站**；不相容的入站 hello 由 `WsUnvalidatedEnvelope` 以 `integer` 解析（R-03）。

### 新增（上游沒有的）

2. **`ready` server type ＋ `ReadyPayload`**（R-01）。**在契約條款內**：`K-02:220` 逐字寫
   server type 清單為「**下限，不得更少**」。由來是 `K-12:948` 要求相容時回 `ready` 而
   `K-02` 的清單沒有它——兩個已核可契約直接矛盾，本站補上並記下矛盾本身。
3. **`select_clarify_candidate` client type ＋ `SelectClarifyCandidatePayload`**（R-02）。
   **⚠ 超出 `K-02` 的條款，需上游追認**：`K-02:270` 的 client 清單**沒有「下限」註記**。
   由來是 `AC1.2.2`／`AC1.2.3` 在原契約下傳輸面不可構造，且 `K-12:920` 一帶逐字寫
   「`U14` 的唯一後端通道是本端點」，不存在走別條路的可能。
4. **`WsClientEnvelope`**（R-05）。`K-02:270` 只列 client payload、不列封包欄位，
   故客戶端封包的欄位集合由本站定義。初版錯誤地宣稱兩方向共用封包——那會要求
   `hello` 與兩個狀態訊息捏造 `turnId`。
5. **`WsUnvalidatedEnvelope`**（R-03）。入站解析的寬鬆型別，使 `K-12` 的 `4400`
   能取得 `received`。
6. **`INVALID_REQUEST` error code**（R-04）。上游 `:288`／`:308` 明文的「解析失敗」
   情境無 code 可用。

### 補缺（上游指向了不存在的定義）

7. **`error.code` 的集合**：`K-02:269` 與 `:308` **兩處**指向 `K-12`，而 `K-12` 定義的是
   WebSocket **關閉碼**（`4401`／`4403`／`4400`／`1011`），不是 `error` 訊息的 `code`。

### 刻意不定義（不收窄也不補）

8. `WorkTargetPayload` 三層之間的階層一致性規則 → `U7`。
9. `expected`／`received` 兩個欄位的型別承載 → `U13`／`K-12`（見 `WsUnvalidatedEnvelope`
   的 entity_constraints；Q4=A 排除的其實不只「碼」，還包括「關閉時要帶的資料」）。

## 四、本站刻意不定義的事

| 不定義 | 歸屬 |
|---|---|
| `turnId` 的產生方式 | `U13`（`K-12` owns 握手與輪次） |
| `candidateId` 是否屬於當前輪次的驗證 | `U13`（需要 session 狀態持有上一輪的候選集合） |
| `expected`／`received` 的型別承載 | `U13`／`K-12`（關閉訊框的原因字串，非訊息 payload） |
| `Sec-WebSocket-Protocol` 的 subprotocol 名稱與編碼格式 | `U13`／`K-12`（見 `functional-spec.md` `§八` 的 Q4=A 代價段，審查 R-07） |
| WebSocket 關閉碼、端點路徑、握手步驟 | `K-12`／`U13`（Q4=A 的界線） |
| 作業對象三層的階層一致性 | `U7 hierarchy-service` |
| 信心值門檻（0.7）的判斷 | `U11 intent-router` |
| 活動記錄（`record=True`）與 token 傳輸 | `U13`（`K-12` x-hard-constraints） |
