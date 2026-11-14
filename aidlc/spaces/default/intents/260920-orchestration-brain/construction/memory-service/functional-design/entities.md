# 實體模型 — `U8 memory-service`

> 本單元**不擁有資料庫結構**——那是 `U5 memory-data` 的範圍（契約 `K-05`，
> 已交付）。本檔描述的是 `U8` 在其契約 `K-08` 之後對外呈現的**邏輯實體**，
> 以及它在寫入與讀取端必須強制的屬性語意。
>
> 技術無關：型別為邏輯型別，不含 SQL、不含框架。與已交付結構的對齊關係寫在
> §三的對照表，供追溯用。

## 〇、上游依據（逐一指名）

| 上游 | 本檔用到它的什麼 |
|---|---|
| `inception/domain-design/components.md` `MemoryStore`（`:178-236`） | 兩個實體與其屬性清單、擁有者與可見範圍的語意 |
| `inception/contract-design/contract-summary.md` `K-08`（`:589-680`） | `MemoryView`／`MemoryAuditEventView` 的對外形狀、授權模型 |
| `inception/requirements-analysis/requirements.md` | `FR4.1`（三種記憶）、`FR4.3`／`FR4.3a`／`FR4.3b`（最小權限、擁有者、可見範圍） |
| `inception/units-generation/unit-of-work.md`（`:117-121`） | `U8` 的擁有與交付、依賴 `U5`／`U6` |
| `inception/user-stories/stories.md` | `US4.1`／`US4.2`／`US4.3`／`US4.4` 共 12 條 AC |
| 本站問題檔 `[FD1]`=B、`[FD4]`=A、`[FD2]`=A、`[FD3]`=A | 寫入端歸屬、semantic 的手動路徑、稽核查詢授權、可見範圍值集合 |

## 一、實體（機讀真實來源）

```yaml
entities:
  - name: MemoryRecord
    description: >
      一則記憶。三種 kind 共用同一個實體與同一組屬性，不分表——kind 是屬性而非
      型別分支。擁有者與可見範圍是本實體的授權基礎，讀取一律經過它們。
    identifier: memoryId
    attributes:
      - name: memoryId
        type: identifier
        required: true
        unique: true
        description: 由持久層指派；對外為不透明識別字
      - name: kind
        type: enum
        required: true
        allowed_values: [semantic, procedure, episodic]
        description: >
          封閉集合（FR4.1 的三種記憶）。**不是**型別分支：三者在同一個實體內，
          差別只在保存期（見 expiresAt 的約束）與寫入端（見 §二之一）
      - name: ownerUserId
        type: reference
        required: true
        references: User（既有 baseline 實體）
        description: >
          **由本單元在寫入時依呼叫者的已驗證身分設定**，不得由呼叫方自行指定
          （FR4.3a）。這是寫入端強制，不是輸入欄位——見 BR1.1／BR1.2
      - name: visibilityScope
        type: enum
        required: true
        default: owner
        allowed_values: [owner, platform]
        description: >
          封閉集合，由 [FD3]=A 定案。owner＝僅擁有者可見（最窄，預設）；
          platform＝全平台可見。放寬只有一個方向（owner → platform），
          故「比較哪個更寬」是可判定的——見 BR5.2
      - name: content
        type: text
        required: true
        constraints: 去除前後空白後長度須大於 0
        description: 記憶的文字內容。**稽核事件刻意不複製它**（見 MemoryAuditEvent）
      - name: embedding
        type: vector
        required: false
        description: >
          **可為空是刻意的**：fulltext 提供者模式下建立的列沒有向量，
          該列在重新 embed 之前不會被向量檢索看到。NULL 是有意義的狀態而非缺陷
      - name: embeddingModel
        type: string
        required: true
        description: >
          產生 embedding 的模型識別字。**相似度檢索必須以它分群**——同維度不等於
          同向量空間，少了這道過濾會回垃圾且不報錯（BR3.2）。
          即使 embedding 為 NULL 本欄仍必填
      - name: createdAt
        type: timestamp
        required: true
        description: 寫入時刻
      - name: expiresAt
        type: timestamp
        required: false
        description: >
          僅 episodic 必填（createdAt ＋ 90 天）；semantic／procedure 為空。
          清除作業**依本欄選列**，故 episodic 漏填的後果是永久保留且無跡象
    entity_constraints:
      - id: EC1
        statement: kind 為 episodic 時 expiresAt 必須非空
        rationale: >
          FR4.5 的 90 天只約束 episodic；而清除依 expiresAt 選列，
          故一列 expiresAt 為空的 episodic 永遠不會被選中
      - id: EC2
        statement: 去除前後空白後 content 長度須大於 0
        rationale: 空白記憶無檢索價值，且會污染相似度結果
      - id: EC3
        statement: visibilityScope 與 kind 皆為封閉集合，集合外的值一律拒絕寫入
        rationale: >
          kind 來自 FR4.1；visibilityScope 來自 [FD3]=A。
          開放字串會讓「放寬」失去可判定的方向性（BR5.2 失去依據）
    relationships:
      - target: MemoryAuditEvent
        cardinality: one-to-many
        direction: MemoryRecord ← MemoryAuditEvent
        description: >
          一則記憶可有多筆稽核事件。**但這不是參照完整性關係**：稽核事件刻意
          比它描述的記憶活得久（見 MemoryAuditEvent.memoryId），
          故本關係在持久層沒有外鍵，是應用層的語意關係
      - target: User
        cardinality: many-to-one
        direction: MemoryRecord → User
        description: ownerUserId 指向擁有者

  - name: MemoryAuditEvent
    description: >
      對一則記憶做過什麼的紀錄。**刻意不含記憶內容**——它比記憶活得久，
      若含內容則「保留稽核」等於「保留被刪除的使用者資料」，
      使用者以為刪了而它還在，FR4.5 的 90 天刪除形同虛設。
    identifier: auditEventId
    attributes:
      - name: auditEventId
        type: identifier
        required: true
        unique: true
      - name: memoryId
        type: identifier
        required: true
        description: >
          **不透明識別字，不是參照**。刻意無參照完整性：稽核必須在它描述的記憶
          消失之後仍然存在（FR4.7），而 FR4.5 要求該記憶會消失。
          代價明寫：memoryId 可能指向一列已不存在的記憶（DG-1 已由 U5 的結構
          定案為「如此設計」，非未決項）
      - name: actorUserId
        type: reference
        required: true
        references: User（既有 baseline 實體）
        description: >
          做這件事的人。清除路徑無自然使用者（排程觸發、無人在迴圈內），
          故 U9 以一列保留的系統 actor 承擔——本單元不產生該類事件
      - name: action
        type: enum
        required: true
        allowed_values: [deleted_by_user, purged_by_retention, scope_changed]
        description: >
          封閉集合。**本單元只產生 deleted_by_user 與 scope_changed 兩種**；
          purged_by_retention 由 U9 產生。
          **本集合沒有「建立」的值**——見 §二之二，這是本站裁決一項上游矛盾的依據
      - name: previousScope
        type: enum
        required: false
        allowed_values: [owner, platform]
        description: action 為 scope_changed 時必填；其餘為空
      - name: newScope
        type: enum
        required: false
        allowed_values: [owner, platform]
        description: action 為 scope_changed 時必填；其餘為空
      - name: occurredAt
        type: timestamp
        required: true
        description: >
          **本欄是稽核自身的保存期鍵**（90 天），不是它所描述記憶的時間。
          兩者是各自獨立的時鐘
    entity_constraints:
      - id: EC4
        statement: action 為 scope_changed 時 previousScope 與 newScope 皆須非空且彼此不同
        rationale: >
          AC4.3.1 要求稽核答得出「由什麼範圍改成什麼範圍」；
          兩者相同代表沒有發生變更，不該產生事件（BR5.4）
      - id: EC5
        statement: action 非 scope_changed 時 previousScope 與 newScope 皆須為空
        rationale: 避免讀者把刪除事件的空白範圍誤讀為「改成了空」
      - id: EC6
        statement: 本實體不得含 content、embedding 或任何可識別的記憶內容
        rationale: 見本實體的 description——它比記憶活得久
    relationships:
      - target: MemoryRecord
        cardinality: many-to-one
        direction: MemoryAuditEvent → MemoryRecord
        description: 語意關係，**無參照完整性**（見 memoryId）
      - target: User
        cardinality: many-to-one
        direction: MemoryAuditEvent → User
        description: actorUserId 指向行為人
```

## 二、實體集合的人話摘要

兩個實體，一個關係，而那個關係**刻意不是外鍵**。

`MemoryRecord` 是三種記憶的單一載體——`kind` 是屬性而不是型別分支，所以三者
共用同一組授權欄位（`ownerUserId` ＋ `visibilityScope`）與同一條檢索路徑。
三者真正的差別只有兩處：**保存期**（只有 `episodic` 有 `expiresAt`）與
**寫入端**（見下）。

`MemoryAuditEvent` 記錄對記憶做過什麼。它的設計核心是**兩個刻意的缺席**：
沒有指向記憶的外鍵（否則稽核會隨記憶一起消失，`FR4.7` 在 90 天後變成空話），
以及沒有記憶內容（否則「保留稽核」等於把使用者以為已刪除的資料留著）。

### 2.1 三種 kind 的寫入端（`[FD1]`=B ＋ `[FD4]`=A）

| kind | 寫入端 | 時機 | 新增的依賴邊 |
|---|---|---|---|
| `episodic` | **`U13 brain-gateway`** | 每輪對話結束 | **`U13` → `U8`（新）** |
| `procedure` | **`U12 work-orchestrator`** | 工作項完成時 | **`U12` → `U8`（新）** |
| `semantic` | **使用者經 `U15` 手動建立** | 使用者主動 | 無新同進程邊；需**新增 `POST /api/memory/records`** |

**兩條新邊必須送到 `delivery-planning`（2.9，ALWAYS）**——
`contract-summary.md:1432` 逐字要求，否則 2.9 排出的 Bolt 序缺這條約束。
記為交接事項 `FD8-1`。

**這一節關閉了 `OQ-N3`**（Critical，`contract-summary.md:1432` 指派本站）。
在它之前 `MemoryFacade.write` 無任何呼叫者，使 `U5`／`U8`／`U9`／`U15`
四個單元惰性、四條 `FR4.*` 失去機制。

### 2.2 `action` 沒有「建立」值——本站據此裁決一項上游矛盾

`contract-summary.md:643` 的 `observable_side_effects` 逐字寫
「**write**／delete／widen_scope **皆**寫稽核事件」，而**同一份檔**的 `:1386`
只寫「`delete` 與 `widen_scope` 皆寫稽核事件」。

本站不選邊，由**已交付的結構**裁決：`action` 的封閉集合是
`deleted_by_user`／`purged_by_retention`／`scope_changed`，
**沒有任何可用於建立的值**；而 `FR4.7`（`requirements.md:170`）逐字只約束
「記憶的**刪除動作本身**」。故 `:1386` 正確、`:643` 為過度宣稱。

**若要讓 `write` 留稽核，必須擴充 `action` 的封閉集合**，那會觸發
`schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步，屬 `U5` 的資料模型範圍。
記為 `FD8-2`（不建議：沒有任何已核可需求要求建立留稽核）。

## 三、與已交付結構的對照（追溯用，非本單元擁有）

本單元的邏輯實體與 `U5` 已交付的結構一對一對應，**無新增欄位、無結構變更**。

| 邏輯屬性 | 已交付結構的對應 | 本站新增的語意 |
|---|---|---|
| `kind` | 既有欄位 ＋ 既有封閉約束 | 無 |
| `ownerUserId` | 既有欄位（非空、參照使用者） | **寫入端強制**（BR1.1／BR1.2） |
| `visibilityScope` | 既有欄位（非空，**結構層無封閉約束**） | **`[FD3]`=A 的兩值封閉集合，以應用層承載**（EC3） |
| `embeddingModel` | 既有欄位（非空） | **檢索必須以它分群**（BR3.2） |
| `expiresAt` | 既有欄位 ＋ 既有條件約束 | 無 |
| `action` | 既有欄位 ＋ 既有封閉約束 | **本單元只產生其中兩種**（§二之二） |
| `previousScope`／`newScope` | 既有欄位（**結構層無封閉約束**） | **兩值封閉集合 ＋ EC4／EC5**，以應用層承載 |

**三處封閉集合由應用層而非結構層承載**，沿用 `U18` 的既有先例
（per-project 角色的封閉列舉在應用層，結構層刻意不加約束）。
代價如實記載：結構層不會擋下集合外的值，故 EC3／EC4／EC5 是**本單元的**
寫入端義務，漏做的後果是髒資料而非寫入失敗。記為 `FD8-3`。
