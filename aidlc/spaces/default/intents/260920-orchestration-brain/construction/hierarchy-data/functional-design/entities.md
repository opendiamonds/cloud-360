# Entities — `U4 hierarchy-data`（`spec`）

<!-- Stage: functional-design（Construction 3.1）· Unit: hierarchy-data · kind: spec -->

## 〇、本檔的定位

本檔是**資料形狀**的真實來源。決策邏輯在 `rules.md`，有序行為（遷移流程、生命週期）
在 `functional-spec.md`。三者不重複；衝突時各以自己的主題為準。

技術中立：不含 SQL、不含 ORM、不含欄位型別的資料庫方言。
`logical_type` 是邏輯型別，實體型別由 `code-generation` 依 PostgreSQL 決定。

**本單元不擁有任何授權判定**——`K-04` `behaviour_semantics.authorization_responsibility`
逐字寫「**無**」。資料的存取授權由 `K-07` 的 facade 承擔。

---

## 一、source of truth

```yaml
entities:
  - name: Project
    description: >
      階層的最上層。一個專案有多個系統。專案是「跨雲分析」等專案層級面向的未來
      掛載點（[RA:FR9.4] 明文本次不納入）。
    attributes:
      - name: id
        logical_type: identifier
        required: true
        unique: true
      - name: name
        logical_type: short_text
        required: true
        constraints: 非空白
      - name: owner_user_id
        logical_type: identifier
        required: true
        references: User
        constraints: >
          指向既有的使用者實體。**刪除使用者時本欄的行為本站不定案**——
          見 functional-spec.md §八 的 OQ-H1，落點 U7（本行初版誤指 §六，審查 R-12）。
      - name: is_default
        logical_type: boolean
        required: true
        default: false
        constraints: >
          **遷移建立的「預設專案」標記**。每位使用者至多一個 is_default 為真的專案
          （見 entity_constraints）。本欄是遷移冪等的承載（Q3=A），不是使用者可編輯的屬性。
      - name: created_at
        logical_type: timestamp
        required: true
    entity_constraints:
      - "每位使用者至多一個 `is_default` 為真的 Project——這是遷移冪等的資料庫層保證
         （Q3=A）。重跑時『存在就取用、不存在才建』；**不會建出第二個預設 Project**
         由本表的約束保證，而**不會建出第二「組」**（Project ＋ System 的配對）
         另需 BR2.5 的獨佔寫入紀律，不是單靠約束——見 rules.md §三 與 System 區塊的
         同一項保留條件（本行初版逐字寫「由約束而非程式流程保證不會建出第二組」，
         審查 R-07：保留條件當時只加在 System 區塊，漏了本區塊）"
      - "刪除 Project 時，若其下仍有 System，該刪除必須被拒絕（BR1.1）"
    relationships:
      - target: System
        cardinality: one-to-many
        direction: Project 擁有多個 System
      - target: User
        cardinality: many-to-one
        direction: 每個 Project 有一個擁有者

  - name: System
    description: >
      階層的中間層。一個系統對應一份架構圖檔與其中多張圖
      （components.md ProjectHierarchy.behaviour 逐字）。
    attributes:
      - name: id
        logical_type: identifier
        required: true
        unique: true
      - name: project_id
        logical_type: identifier
        required: true
        references: Project
      - name: name
        logical_type: short_text
        required: true
        constraints: 非空白
      - name: is_default
        logical_type: boolean
        required: true
        default: false
        constraints: >
          **遷移建立的「預設系統」標記**。與 Project.is_default 同一個用途：
          承載遷移冪等（Q3=A）。
      - name: created_at
        logical_type: timestamp
        required: true
    entity_constraints:
      - "**每個 Project 至多一個 `is_default` 為真的 System**，唯一性以 `project_id`
         為範圍。**不是**以擁有者為範圍——`System` 沒有 `owner_user_id` 欄位，
         擁有者只能經 `project_id` 上溯取得，而唯一性約束**無法以另一張表 join 來的值
         為範圍**（審查 R-01，Critical：初版正是那樣寫的，照描述做不出來）。
         **『每位使用者至多一組預設專案／系統』由兩層約束遞移得出**：
         使用者層的唯一性由 Project 承擔（每位使用者至多一個 is_default Project），
         而預設 System 建在該預設 Project 之下，故每位使用者的預設 System 也至多一個。
         兩個約束都只引用自己表內的欄位，都是可建的。
         **保留條件（iteration 2 審查 R-07，Major）**：上面那個遞移論證還需要第三個前提——
         `is_default` 為真的 System 總是建在該使用者 `is_default` 為真的 Project 底下——
         而**沒有任何約束擋住**『預設 System 掛在非預設 Project 底下』。那個耦合由
         `BR2.5` 的流程供應，不是由約束供應。所以「每位使用者至多一組預設」這個**複合**性質
         並非單靠資料庫保證；今天成立的唯一理由是遷移是 `is_default` 的唯一寫入端。
         完整分界見 `rules.md §三`"
      - "刪除 System 時，若其下仍有架構圖（ArchitectureDiagram.system_id 指向它），
         該刪除必須被拒絕（BR1.2）。**這是 DG-2 的解——就「刪除造成懸空」這一條路而言**；
         遷移之後的另兩條路（改回空、新插入不帶值）本單元未關，見 OQ-H2（審查 R-08）"
    relationships:
      - target: Project
        cardinality: many-to-one
        direction: 每個 System 屬於一個 Project
      - target: ArchitectureDiagram
        cardinality: one-to-many
        direction: System 擁有多張架構圖

  - name: ArchitectureDiagram
    description: >
      **既有實體，本單元只為它增加一個欄位。** 現況為 user_diagrams：
      直接掛在使用者底下，另經 diagram_shares 多對多分享。
      本單元不改變它的既有欄位、不改變 diagram_shares 的行為
      （decisions.md:140–143 逐字「本站不改變 diagram_shares 的行為」）。
    attributes:
      - name: id
        logical_type: identifier
        required: true
        unique: true
        constraints: 既有欄位，不變
      - name: owner_user_id
        logical_type: identifier
        required: true
        references: User
        constraints: >
          **既有欄位，語意明確化而非改變**：它是「誰建的」，**不是**「屬於哪個系統」。
          歸屬的權威來源是 system_id（decisions.md ADR-002）。本單元不改它的值、
          不改它的必填性。
      - name: system_id
        logical_type: identifier
        required: false
        references: System
        constraints: >
          **本單元新增的唯一欄位。** 歸屬的權威來源。可為空是為了讓欄位能先加上去、
          再由遷移填滿——遷移完成的那一刻它必須全部非空（BR2.1／AC9.1.4，
          而 AC9.1.4 的 Given 逐字就是「遷移已執行」）。
          刪除其所指的 System 時，該刪除被拒絕而非把本欄設為 NULL（BR1.2）。
          **但本欄在本設計裡永遠可為空，而 BR1.2 只擋刪除那一條路**：
          遷移之後「把已掛好的圖改回空」與「新插入的圖不帶本欄」兩條路
          本單元都沒有禁止，後者正是既有 A1 儲存路徑的行為。
          收成 NOT NULL 能一次關掉兩條，但與 AC9.1.3 衝突，
          故列為 OQ-H2 不定案（functional-spec.md §八，iteration 2 審查 R-08）。
    entity_constraints:
      - "遷移完成的那一刻，system_id 為空的列數必須為 0（BR2.1）。這是 AC9.1.4 的資料面表述。
         **這不等於此後恆為 0**——本欄仍可為空，遷移後的維持只覆蓋刪除那一條路（BR1.2），
         其餘兩條路是 OQ-H2（審查 R-08）"
      - "本單元不新增、不修改、不刪除任何既有欄位；只增加 system_id"
    relationships:
      - target: System
        cardinality: many-to-one
        direction: 每張圖屬於一個 System（遷移後）

  - name: DiagramChangeRecord
    description: >
      架構圖被異動時寫入的一列紀錄，帶來源需求的摘要與一個輕量標籤
      （components.md 逐字：不建 Requirement 實體、不建多對多關聯表）。
      **本輪只寫不讀**（Q2=A），且**只涵蓋大腦交辦的異動**（Q4=A）——
      涵蓋面由 source 欄位自己宣告，見該欄位的 constraints。
    attributes:
      - name: id
        logical_type: identifier
        required: true
        unique: true
      - name: diagram_id
        logical_type: identifier
        required: true
        references: ArchitectureDiagram
      - name: source
        logical_type: string_enum
        required: true
        allowed_values: [brain_orchestration]
        constraints: >
          **本輪唯一合法值為 brain_orchestration。** 本欄的存在理由是讓這張表的
          **涵蓋面成為可查詢的事實而不是散文裡的一句話**：唯一的寫入端是
          U12 WorkOrchestrator（components.md 的 dependents 邊逐字「架構圖被異動時
          寫入變更紀錄」），而它是大腦的交辦層——經既有 A1 頁面直接編輯的圖
          **不經過它**。未來若 A1 儲存路徑也要寫入，新增一個列舉值即可，
          **不需要 schema 遷移**。
          **這是 Q4=A 的承載形式**：使用者選的是「讓表名說真話」，本站改以資料宣告
          取代改名，理由是改實體表名會牴觸 K-04 已核可的 tables 清單
          （逐字列 diagram_change_records）。此具體化已於彙整摘要向使用者揭露並獲確認。
      - name: actor_user_id
        logical_type: identifier
        required: true
        references: User
        constraints: >
          **這次變更是誰做的。** 上游 components.md 的 Entity Ownership 表逐字把
          actorUserId 列為本實體的欄位之一；初版**靜默漏掉了它**（審查 R-02，Critical）。
          它不是可有可無的中繼資料：`WorkOrchestrator` 可能代表一個**共享工作階段**行動，
          而該階段可以有多位參與者——沒有這個欄位，紀錄說得出「圖變了」，
          說不出「是誰讓它變的」，而後者正是 §六 Audit logging 面向的實質內容。
          **寫入端與取值方式（iteration 2 審查 R-09，Minor）**：寫入端與 source 同一個——
          `U12 WorkOrchestrator`（`components.md` 的 dependents 邊逐字「架構圖被異動時寫入變更紀錄」）。
          但**它在一個有多位參與者的共享工作階段裡怎麼認定「行動者是誰」，本站無法定案**：
          `WorkOrchestrator` 的內部設計不屬本單元。列為 `U12` 自己 functional-design 的開放問題，
          不留成隱含假設——因為本欄之所以要還原，理由正是多參與者這個情境。
      - name: requirement_summary
        logical_type: long_text
        required: true
        constraints: 來源需求的摘要。非空白
      - name: requirement_label
        logical_type: short_text
        required: true
        constraints: >
          components.md 逐字的「一個輕量標籤」。刻意不做成獨立實體、不做多對多——
          那是該檔明文排除的。
          **命名沿用上游的 requirementLabel**；初版簡寫為 label，屬未揭露的改名，
          已還原（審查 R-02 的連帶）。
      - name: created_at
        logical_type: timestamp
        required: true
    entity_constraints:
      - "**本實體在本 intent 結束時沒有任何讀取端**（Q2=A，DG-3 的處置）。
         這是**已接受的狀態**而非遺漏：讀取面（架構圖的變更歷程畫面）不在
         scope-document.md 能力 9 的字面範圍內（逐字只有「專案 → 系統 → 架構圖 階層」）。
         未來讀取端與觸發時機見 functional-spec.md §五"
      - "**不得**被讀成完整的變更歷程——source 為 brain_orchestration 的列只涵蓋
         大腦發起的異動。任何未來的讀取端必須先讀 source 再決定怎麼呈現（BR3.1）"
    relationships:
      - target: ArchitectureDiagram
        cardinality: many-to-one
        direction: 多列紀錄指向同一張圖

  - name: User
    description: >
      **既有實體，本單元不改動它。** 在此列出只是為了讓 Project.owner_user_id 與
      ArchitectureDiagram.owner_user_id 的 references 有指向。
    attributes:
      - name: id
        logical_type: identifier
        required: true
        unique: true
        constraints: 既有欄位，不變
    entity_constraints:
      - "本單元不新增、不修改、不刪除 User 的任何欄位"
    relationships:
      - target: Project
        cardinality: one-to-many
        direction: 一位使用者擁有多個專案
```

---

## 二、實體集合摘要（由上方 yaml 衍生）

**五個實體，其中兩個是既有的**：

| 實體 | 狀態 | 本單元對它做什麼 |
|---|---|---|
| `Project` | **新建** | 完整定義 |
| `System` | **新建** | 完整定義 |
| `DiagramChangeRecord` | **新建** | 完整定義；本輪只寫不讀 |
| `ArchitectureDiagram` | **既有**（`user_diagrams`） | **只加一個欄位** `system_id`，不動任何既有欄位 |
| `User` | **既有** | **完全不動**；列出只為讓 references 有指向 |

**新增欄位總數：1**（`ArchitectureDiagram.system_id`）。
這個數字重要——它是 `AC9.1.3`（遷移不改變既有頁面的使用方式）能成立的原因：
既有頁面讀寫的每一個欄位都沒有被碰。

### 三個新實體的欄位數

| 實體 | 欄位數 | 其中本站新增（上游未要求） |
|---|---|---|
| `Project` | 5 | `is_default`（Q3=A，S-1） |
| `System` | 5 | `is_default`（Q3=A，S-1） |
| `DiagramChangeRecord` | 7 | `source`（Q4=A 的承載形式，S-2） |

---

## 三、本單元對上游的收窄與新增（逐項標明，不混在一起）

| 項 | 性質 | 內容 | 依據 |
|---|---|---|---|
| `Project.is_default`／`System.is_default` | **新增** | 上游未提；承載遷移冪等 | Q3=A |
| `DiagramChangeRecord.source` | **新增** | 上游未提；承載涵蓋面的自我宣告 | Q4=A 的具體化 |
| `DiagramChangeRecord` 的語意 | **收窄** | `components.md` 說「架構圖變更紀錄」，實際只涵蓋大腦路徑 | Q4=A；事實 4 |
| `changeRecordId` → `id`、`occurredAt` → `created_at` | **改名（本站揭露）** | 沿用本 repo 既有實體的欄位命名慣例（`id`／`created_at`），語意不變 | 本站；審查 R-02 的連帶 |
| `System` 刪除行為 | **定案**（上游明文未定） | 其下仍有圖時拒絕刪除 | Q1=A，`DG-2` 的解——**就「刪除」這一條路而言** |
| `Project.owner_user_id` 在刪除使用者時的行為 | **不定案** | 見 `functional-spec.md §八` 的 `OQ-H1`（同檔 `Project.owner_user_id` 的欄位註解一度誤指 `§六`，審查 R-12） | 本站新發現 |
| `ArchitectureDiagram.system_id` 遷移之後由誰保證非空 | **不定案** | 見 `functional-spec.md §八` 的 `OQ-H2`：本欄永遠可為空，而 `BR1.2` 只擋刪除；收成 `NOT NULL` 與 `AC9.1.3` 衝突 | 審查 R-08 |
| `DiagramChangeRecord.actor_user_id` 在多參與者工作階段填誰 | **不定案** | 見 `functional-spec.md §八` 的 `OQ-H3`：寫入端是 `U12`，但「行動者是哪一位」取決於它的內部設計，不屬本單元 | 審查 R-11 |

**四項收窄／新增需回補 scope**（`S-1`／`S-2`／`S-3`／`S-4`，見 `functional-spec.md §八` 的回補表）。
**三項不定案**（`OQ-H1`／`OQ-H2`／`OQ-H3`，同節）。
