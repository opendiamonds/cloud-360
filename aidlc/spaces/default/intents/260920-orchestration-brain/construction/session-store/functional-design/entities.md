# Entity Model — `U10 session-store`

> 本檔是本單元**實體形狀**的唯一真實來源。工作流程與狀態轉換在
> `functional-spec.md`；決策邏輯在 `rules.md`。
> 技術無關：不含程式、SQL 或框架名稱。

## 本檔的上游（逐字出處，供下游複驗）

| 上游 | 它給了本檔什麼 |
|---|---|
| `components.md:95-129` | `SessionContext` 元件的整段宣告。`:124-129` 的 `entities:` 區塊逐字給出 `BrainSession` 的識別碼（`sessionKey`）與八個屬性，是本檔 `BrainSession` 的直接前身；`:121-123` 逐字把 Redis 列為 `external_dependencies`、`kind: cache`、`purpose: session 狀態外部化；第 5 個部署服務` |
| `requirements.md:125`（`FR2.1`）／`:133-137`（`FR3.1`–`FR3.3`）／`:182`（`FR6.1`）／`:500-504`（`NFR4`） | 五條需求決定了本檔的全部實體邊界：共享範圍三頁、逐頁開新對話、新對話不共享歷程但沿用作業對象、可隨時切回、多輪指涉，以及「一律放 Redis、重啟可完整還原」 |
| `unit-of-work.md:131-135` | `U10` 的擁有與交付逐字，含「獨立那段保留但不併入共享流」——它是 `[S2]`=A 的上游邊界 |
| `unit-of-work-story-map.md:115` | 該列逐字把 `U10 session-store` 對應到 `US2.1`、`US2.2`、`US3.1`、`US6.1`、`US9.1` 五則故事（該表的計數欄為 `5`）——本檔的實體集合只為這五則故事存在，多出來的實體就是範圍外 |
| `contract-summary.md:684-742`（`K-09`） | 本單元對外的 `public_interface` 與 `data_shape`，以及 `OQ-1` 的原文 |

## 本檔推翻了已核可契約的哪兩處（逐字範圍與授權依據）

`contract-summary.md:1433` 的 `OQ-N4` 逐字把兩項形狀改動指派給本站並授權：
「`U10`（其 `public_interface` 與 `data_shape` **皆需改**）」。本檔依該授權改兩處，
**並明記第三處超出授權、須另立 ADR**：

| # | 已核可的原形狀（逐字） | 本檔的形狀 | 授權依據 |
|---|---|---|---|
| 1 | `K-09.data_shape.BrainSession.fields` 逐字含**一個** `messageHistory` | 歷程下沉到 `ConversationSegment`，每段各一份 | `OQ-N4` 逐字授權 `data_shape`（`[S1]`=A、`[S2]`=A） |
| 2 | `x-session-key-derivation.why_one_key.therefore` 逐字「同一個 key、**同一組** `currentProjectId`／`currentSystemId`／`currentDiagramId`」 | 作業對象亦下沉到 `ConversationSegment`，每段各一組 | `OQ-N4` 逐字授權 `data_shape`（`[S3]`=A）。**但 `OQ-N4` 只點名 `messageHistory`，沒有點名作業對象**——這一半是本站跑契約端點三問時查出的，見 `functional-spec.md` 的 `D-S10-2` |
| 3 | `K-02` 的 `SharingModePayload`／`SetSharingModePayload`／`WorkTargetPayload`／`SetWorkTargetPayload` 皆無段或頁面識別欄位 | 四者各加一個識別欄位 | **超出 `OQ-N4` 的授權**（它只授權 `U10`）。`K-02` 由 `U2 brain-ws-contract` 擁有且**已施工完成**，故須另立 `ADR-0020` 追認，見 `functional-spec.md` 的 `D-S10-1` |

## Source of truth

```yaml
entity_model_version: 1
unit: session-store
storage: "Redis，單一 session key（[DD:E6]=A／ADR-005）"

entities:
  - name: BrainSession
    summary: 一個使用者的大腦工作階段。彙總根；整個生命週期以單一 Redis key 承載。
    identifier: sessionKey
    attributes:
      - name: sessionKey
        logical_type: string
        required: true
        unique: true
        description: >
          由 `U13` 在握手成功後以**已驗證使用者的 id** 推導（`x-session-key-derivation`
          逐字「一個使用者一個大腦 session」）。本單元**不產生**它，只接收。
      - name: userId
        logical_type: integer
        required: true
        references: "users.id（既有表，本單元不擁有）"
        description: 本 session 的歸屬人。與 sessionKey 同源，供讀取端免再解析。
      - name: pageModes
        logical_type: "map<PageScope, SharingMode>"
        required: true
        allowed_keys: [workspace, assessment]
        default: "{workspace: shared, assessment: shared}"
        description: >
          **每一個「可開啟獨立對話」的頁面各自的模式**（`[S1]`=A）。
          鍵集合**不含入口頁**——`FR3.1` 逐字只允許 `/workspace` 與 `/assessment`
          開啟獨立對話，入口頁恆讀共享段。
      - name: segments
        logical_type: "map<SegmentId, ConversationSegment>"
        required: true
        min_size: 1
        max_size: 3
        description: >
          至少含 `shared`；`workspace`／`assessment` 為選用，僅在該頁**首次**切到
          獨立對話時建立，之後**保留且可重入**（`[S2]`=A）。
      - name: expiresAt
        logical_type: timestamp
        required: true
        derived: true
        description: >
          由 TTL 推導而非獨立可寫；每一次互動後重算（`K-09` 的
          `observable_side_effects` 逐字「全部方法都會續期 TTL」）。
    entity_constraints:
      - id: EC1
        statement: "`segments` 必含鍵 `shared`。"
        why: "共享段是三處共享工作階段的承載體（`FR2.1`），它不是選用的。"
      - id: EC2
        statement: "`pageModes` 的鍵集合恰為 `{workspace, assessment}`，不得含入口頁。"
        why: "`FR3.1` 逐字只列這兩頁；`AC3.1.1` 要求入口頁的脈絡不受影響。"
      - id: EC3
        statement: "`pageModes[P] == isolated` ⇒ `segments[P]` 必存在。"
        why: "否則該頁進入一個不存在的段，`AC3.1.1` 的『該頁進入一段新對話』無著落。"
      - id: EC4
        statement: "`segments` 的鍵值域恰為封閉集合 `{shared, workspace, assessment}`。"
        why: >
          段識別**就是**擁有它的頁面（共享段除外），故不需要額外的識別碼產生器，
          也使「重入同一段」（`[S2]`=A）由構造成立而非靠額外的查找。
      - id: EC5
        statement: "`expiresAt` 不得由呼叫方指定。"
        why: "TTL 是唯一的清除機制（`ADR-005` 的 Alternatives Rejected 逐字拒絕『TTL ＋ 顯式清除並存』）。"
      - id: EC6
        statement: "本實體的任何欄位都不得出現在任何 log 或錯誤訊息中。"
        why: >
          本 repo 為 public 且 Actions log 公開可讀（`project.md` 逐字「一次意外 echo
          即等同公開發布」），而本單元持有的是**個人對話內容**。

  - name: ConversationSegment
    summary: 一段對話。彙總內的實體，由 BrainSession 組合擁有；自己持有歷程與作業對象。
    identifier: "segmentId（在其 BrainSession 內唯一）"
    attributes:
      - name: segmentId
        logical_type: enum
        required: true
        allowed_values: [shared, workspace, assessment]
        description: "`shared` 為三處共享的那一段；另兩個各為該頁的獨立段。"
      - name: messageHistory
        logical_type: "ordered list<SessionMessage>"
        required: true
        default: "[]"
        description: >
          **本段自己的**訊息，依寫入順序。`AC3.1.2`（獨立段不含共享訊息）與
          `AC6.1.3`（獨立段無法解析指向共享產出的指涉詞）兩條都由
          「讀取視圖只含本段」這個形狀滿足，而不是靠執行期過濾。
      - name: currentProjectId
        logical_type: "integer|null"
        required: false
        references: "Project（ProjectHierarchy／U7 擁有）"
        description: "null 表示該層尚未選定。"
      - name: currentSystemId
        logical_type: "integer|null"
        required: false
        references: "System（ProjectHierarchy／U7 擁有）"
      - name: currentDiagramId
        logical_type: "integer|null"
        required: false
        references: "user_diagrams（既有表，ProjectHierarchy／U7 擁有）"
      - name: createdAt
        logical_type: timestamp
        required: true
        description: "本段建立的時刻。共享段的建立時刻即 session 的建立時刻。"
    entity_constraints:
      - id: EC7
        statement: >
          三個作業對象欄位**允許部分非空**——包含
          `{projectId: null, systemId: null, diagramId: 非空}` 這個組合。
        why: >
          **實測** `hierarchy_service.py:261-273`：只給 `diagram_id` 時，
          `resolve_work_target` 僅在 `diagram.system_id is not None` 時推導上層，
          否則回 `{projectId: None, systemId: None, diagramId: X}` 並**刻意不拒絕**
          （逐字「圖本身的擁有者已驗證過」）。成因是 `OPEN-H11`（新建的圖從未被
          指派系統歸屬），該缺口**至今無承接站**。故 `AC9.1.1` 的「完整的三層路徑」
          對這類圖**不可滿足**；本實體如實儲存部分三元組，**不推導、不補齊、不拒絕**。
      - id: EC8
        statement: >
          本實體**不驗證**三層之間的階層一致性（例如 systemId 非 null 時
          projectId 是否必須非 null）。
        why: >
          `K-02` 的 `WorkTargetPayload` 逐字「三層之間的階層一致性規則**不由本契約
          定義**……那是 `U7 hierarchy-service` 的責任。這是刻意的界線，不是遺漏」。
          本單元儲存的是 `K-07` **解析後**的結果，重新驗一次會形成兩套可能分歧的規則。
      - id: EC9
        statement: "`messageHistory` 的筆數上限是一個**具名參數**，不是本檔的常數。"
        why: >
          `ADR-016` 逐字「數值由 `nfr-requirements` 決定」，`unit-of-work.md:479`
          逐字確認它「**留在 `nfr-requirements`**，本站不假裝接手」。本站只定義它的
          **存在**與**缺值行為**（見 `rules.md` 的 `BR3.5`），不填數字。

  - name: SessionMessage
    summary: 一則訊息。值物件——同角色、同內容、同序號者不可區分，無獨立身分。
    identifier: null
    attributes:
      - name: sequence
        logical_type: integer
        required: true
        description: "段內單調遞增的寫入序。它表達順序，不是全域識別碼。"
      - name: role
        logical_type: string
        required: true
        description: >
          訊息的發話方。**值域不在本站定案**——`K-09.append_message` 逐字
          `role: str`（未約束），而本單元不是對話協定的擁有者（那是 `K-02`／`U13`）。
          本站只要求它非空且由呼叫方提供。
      - name: text
        logical_type: string
        required: true
        description: "訊息文字。供 `U11` 解析指涉詞（`FR6.1`）；本單元不解讀其內容。"
      - name: createdAt
        logical_type: timestamp
        required: true
    entity_constraints:
      - id: EC10
        statement: "值物件不可就地修改——更正一則訊息的方式是追加新訊息，不是改寫舊的。"
        why: >
          `K-09.behaviour_semantics.retry_and_idempotency` 逐字「`append_message`
          **非冪等**」。能就地改寫會讓「非冪等」這個宣告失去意義，也讓
          `U11` 讀到的順序不再等於發生順序。

relationships:
  - from: BrainSession
    to: ConversationSegment
    cardinality: "1 — 1..3"
    kind: composition
    direction: "BrainSession 擁有 ConversationSegment"
    note: >
      組合而非關聯：段不能脫離 session 存在，且 TTL 到期時**一起**消失
      （`ADR-005` 逐字「三者一起消失」）。
  - from: ConversationSegment
    to: SessionMessage
    cardinality: "1 — 0..N"
    kind: composition
    direction: "ConversationSegment 擁有其 SessionMessage，有序"
  - from: ConversationSegment
    to: "Project / System / user_diagrams"
    cardinality: "0..1 each"
    kind: reference_by_id
    direction: "ConversationSegment 以識別碼指向，不持有物件"
    note: >
      跨彙總一律以 id 參照（`ddd-patterns.md` 逐字「Reference other aggregates by
      ID」）。三者皆由 `ProjectHierarchy`（`U7`）擁有，解析與授權由 `K-07` 承擔。
  - from: BrainSession
    to: WorkItem
    cardinality: "1 — 0..N"
    kind: "同 key 共存，但**不由本單元擁有**"
    direction: "WorkItem 以 sessionKey 指向 BrainSession"
    note: >
      工作項集合放在同一個 session key 之下（`K-09.data_shape` 的 note ＋ `K-11`），
      但其形狀與狀態機由 `U12 work-orchestrator` 擁有。本單元只保證**同生共死**：
      TTL 到期時工作項集合與段一起消失。
```

## 實體集合的人話摘要

本單元只有**三個**實體，而它們的層次是刻意的：

- **`BrainSession`** 是彙總根，一個使用者一個。它持有的不再是「一份歷程 ＋ 一組作業
  對象」，而是**一組段**（`segments`）與**每頁的模式**（`pageModes`）。這個改動是
  `OQ-N4` 逐字指派給本站的，理由是原形狀**撐不起 `[DD:E6]`=A 自己要求的「兩段」**。
- **`ConversationSegment`** 是本檔新增的實體，也是整個設計的重心。它同時持有**歷程**
  與**作業對象**——把兩者放在同一層，是因為 `AC3.1.4` 的 Then 逐字要求的正是這兩樣
  東西一起回到「我離開時」的狀態。若只分歷程（`OQ-N4` 點名的那一半）而不分作業對象，
  `AC3.1.4` 就只剩一半成立。
- **`SessionMessage`** 是值物件而非實體：它沒有需要被外界指名的身分，只有順序。

**為什麼段識別是封閉的三值而不是產生的識別碼**（`EC4`）：段識別**就是**擁有它的
頁面。於是 `[S2]`=A 的「保留且可重入」由構造成立——再次切到獨立對話時，要回去的那
一段就是以該頁命名的那一段，不需要任何「找回上一段」的查找邏輯，也不會出現第二個
`workspace` 段。這同時給出筆數上限的自然套用層級：**每段各自計算**（`BR3.4`），因為
段的數量有上界 3，總量仍然有界。

**沒有「獨立對話的歷程併入共享流」這條路**：`unit-of-work.md:133` 逐字「獨立那段
保留但**不併入共享流**」，故兩段之間**沒有任何合併關係**，關係圖上也不該有這條邊。
