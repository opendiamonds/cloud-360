# 實體模型 — `U7 hierarchy-service`

> 本檔的 ```yaml 區塊是**實體的單一真實來源**。下方散文為人類可讀摘要，
> `functional-spec.md` 的 ER 圖為**衍生檢視**，兩者皆不得與此區塊矛盾。
>
> 技術中立：下列「邏輯型別」不綁任何資料庫或語言。本單元**不擁有 DDL**
> ——DDL 屬 `U4 hierarchy-data`（已交付並登記完成）。本檔記載的約束若與
> `U4` 已交付的實體有落差，逐處在 `constraints` 或 `notes` 內明標。

## 實體定義（單一真實來源）

```yaml
entities:
  - name: Project
    identifier: projectId
    description: >
      階層的最上層。一個專案底下有多個系統。它是作業對象三層識別的第一層。
    attributes:
      - name: projectId
        logical_type: identifier
        required: true
        unique: true
      - name: name
        logical_type: text
        required: true
        max_length: 255
        constraints:
          - 去除前後空白後長度必須大於 0（空白名稱不合法）
          - >
            **無資料庫唯一約束**。名稱唯一性由服務層檢查並回「衝突」
            （`[F5]`=C）。此為刻意的取捨：加唯一索引會動到已交付單元 `U4`
            的 schema 並觸發 `project.md` 的 blocking 同步規則。
            代價是已知的 TOCTOU——檢查與寫入之間的空窗仍可能建出同名
            （見 `rules.md` `BR3.3` 與 `functional-spec.md` 的殘餘風險段）。
      - name: ownerUserId
        logical_type: reference
        required: true
        references: User（既有實體，不屬本單元）
        constraints:
          - >
            **無刪除連動語意，而這是 `OQ-H1`、其落點是本單元。**
            `schema_rbac.sql:347` 的 COMMENT 逐字：「U4: who owns this project.
            Deletion behaviour of the referenced user is **deliberately NOT
            decided** (`OQ-H1`, **landing U7**) — no ON DELETE clause, same as
            `user_diagrams.user_id`」。本單元就是 `U7`，故這一項**指派給本站**。
          - >
            **射程限定（審查 iteration 2 的 `R-07`）**：沒有 on-delete 子句等於
            `NO ACTION`，所以「會被參照完整性擋下」**只對硬刪除成立**。
            **對停用路徑完全無效**——既有停用端點（`user_router.py:682`（端點 decorator 在 `:644`））做的是
            `target_user.is_active = …`，一個 `UPDATE`，而
            `unit-of-work.md:446` 逐字「**外鍵對 UPDATE 零效力**」。
            上一版未限定射程，等於暗示有一道資料庫 backstop 保護停用路徑，
            而那道保護不存在。
          - >
            **本站的處置是明寫退回，不在此定案**（`OPEN-H12`）。理由：擁有者被
            刪除或停用時專案該如何處置，是**成員與接手人語意**的問題
            （轉給誰？是否先要求指定接手人？），而該語意屬契約 `K-16`——
            `MembershipFacade.assert_can_deactivate`
            （`contract-summary.md:1693-1699` 一帶）正是為此存在，且其
            `last_admin_guard` 已定下「專案不得失去最後一位管理者」。
            在本單元定案會與 `K-16` 的 `LastAdminGuard` 形成兩套互相不知道的
            規則。承接站：`U19 membership-service`（`assert_can_deactivate`
            的擁有者）。
      - name: isDefault
        logical_type: boolean
        required: true
        default: false
        description: >
          遷移為每個持有架構圖的使用者建立的「預設專案」標記。
        constraints:
          - 預設組**可改名、不可刪除**（`[F6]`=A，見 `rules.md` `BR4.1`／`BR4.2`）
          - >
            **本欄位不是本單元可寫的。** `U4` 的欄位註解逐字（`schema_rbac.sql:345`）
            「Written **ONLY** by `services/hierarchy_migration.py`;
            **not a user-editable attribute**」。故本單元的建立路徑一律寫入
            `false`（`BR2.3`）、改名路徑不得改動它（`BR4.1`）；唯一寫 `true`
            的是遷移程式，而遷移不屬本單元。`components.md` 把它列為一般屬性
            且未宣告任何寫入限制——這是本站實讀 `U4` 交付物查出的**第四處落差**
            （見 `functional-spec.md` §二），下游不得把它當成可設定的旗標。
      - name: createdAt
        logical_type: timestamp
        required: true
    entity_constraints:
      - 每個專案恰屬於一個擁有者
    relationships:
      - target: System
        cardinality: one-to-many
        direction: Project → System
        description: 一個專案有多個系統
        constraints:
          - >
            **刪除受限**：專案底下仍有系統時不得刪除。此為 `U4` 已交付實體
            的既有語意（參照宣告為 restrict），本單元的端點照該語意回
            「衝突」並說明剩餘系統數（`[F3]`=A）。**不級聯**。

  - name: System
    identifier: systemId
    description: >
      階層的中層，作業對象三層識別的第二層。架構圖歸屬於系統。
    attributes:
      - name: systemId
        logical_type: identifier
        required: true
        unique: true
      - name: projectId
        logical_type: reference
        required: true
        references: Project
      - name: name
        logical_type: text
        required: true
        max_length: 255
        constraints:
          - 去除前後空白後長度必須大於 0
          - 唯一性同 `Project.name`——服務層檢查，無資料庫約束（`[F5]`=C）
      - name: isDefault
        logical_type: boolean
        required: true
        default: false
        description: 遷移建立的「預設系統」標記
        constraints:
          - 同 `Project.isDefault`：可改名、不可刪除（`[F6]`=A），
            且**同樣只能由遷移程式寫入**（見 `Project.isDefault` 的第二條約束）
      - name: createdAt
        logical_type: timestamp
        required: true
    entity_constraints:
      - 每個系統恰屬於一個專案
    relationships:
      - target: Project
        cardinality: many-to-one
        direction: System → Project
        description: 每個系統屬於一個專案
      - target: Diagram（既有 user_diagrams，不屬本單元）
        cardinality: one-to-many
        direction: System → Diagram
        description: >
          架構圖以一個可為空的系統參照表達歸屬，且**該參照是歸屬的權威來源**
          （不是「誰建的」那個欄位）。遷移後該參照為空的架構圖列數必須為 0。
        constraints:
          - >
            **本不變量由 `U4` 擁有並已有測試**（`tests.test_hierarchy_migration`
            15 項通過，含失敗路徑）。本單元在寫入路徑上不得製造新的空歸屬：
            建立架構圖不屬本單元，但刪除系統會使其底下架構圖的歸屬懸空，
            故不可刪除仍有架構圖的系統（`rules.md` `BR4.3`）。

  - name: DiagramChangeRecord
    identifier: changeRecordId
    description: >
      架構圖每次被異動時留下的一列紀錄，帶來源需求的摘要與一個輕量標籤。
      **刻意不建 Requirement 實體、不建需求↔系統的多對多關聯表**（ADR-009）。
    attributes:
      - name: changeRecordId
        logical_type: identifier
        required: true
        unique: true
      - name: diagramId
        logical_type: reference
        required: true
        references: Diagram（既有 user_diagrams，不屬本單元）
        constraints:
          - >
            **刪除連動為級聯**：架構圖被刪除時其變更紀錄一併消失。
            此為 `U4` 已交付實體的既有語意，非本站決定。**其後果必須被下游知道**
            ——變更紀錄不是永久稽核軌跡，它的壽命綁在架構圖上。
          - >
            **壽命的第二個界限是保存期**：`U4` 的資料表註解逐字（`schema_rbac.sql:416`）
            「Retention **90 days** keyed on `created_at` (`U4-R1`);
            the purge mechanism itself is **not in this repo** (`U4-R2`)」。
            兩個後果方向相反，下游不得假設任一方：清除機制若落地，
            90 天前的紀錄查不到；它既然目前不存在，實際行為是紀錄一直累積。
            記為 `rules.md` `BR5.5` 與 `OPEN-H8`。
      - name: source
        logical_type: enumeration
        required: true
        allowed_values: [brain_orchestration]
        description: >
          紀錄這次異動由哪條路徑產生。
        constraints:
          - >
            **`components.md` 的實體屬性清單沒有這個欄位，而 `U4` 已交付的實體
            有，且必填、且其允許值只有一個。** 這是本站實讀 `U4` 交付物查出的
            落差（見 `functional-spec.md` 的「與上游宣告的落差」段）。
            後果：變更紀錄的寫入端**在資料層就只能承載大腦編排這一條路徑**；
            任何其他異動路徑（例如既有 A1 設計 agent 直接改圖）若要寫紀錄，
            必須先擴充允許值集合——那是 `U4` 的 schema 變更，不是本單元可做的。
      - name: actorUserId
        logical_type: reference
        required: true
        references: User（既有實體，不屬本單元）
        description: 這次異動是誰做的
        constraints:
          - >
            **必須是實際造成異動的人，不得預設為 session 擁有者。**
            `U4` 的欄位註解逐字（`schema_rbac.sql:420`）「The writer (`U12`) must store the user who
            actually caused the change and **must NOT default to the session
            owner** (`OQ-H3` still open)」，以及「NOT NULL on purpose — a record
            that says 'the diagram changed' but not 'who changed it' fails the
            audit-logging face」。見 `rules.md` `BR5.6`——本單元是 facade 的
            擁有者，故是唯一能規定此取值來源的地方。
      - name: requirementSummary
        logical_type: text
        required: true
        constraints:
          - 去除前後空白後長度必須大於 0（空摘要不合法）
      - name: requirementLabel
        logical_type: text
        required: true
        max_length: 255
        description: >
          輕量標籤。`[DD:E8]`=C 的理由逐字是「可用同一標籤搜尋它影響過哪些圖」
          ——那句話描述的是一個讀取端，而讀取端在本輪之前不存在（`DG-3`）。
          `[F2]`=A 讓它存在。
      - name: occurredAt
        logical_type: timestamp
        required: true
        constraints:
          - >
            **邏輯名與 `U4` 交付的實體欄位名不同**（該處為建立時間戳）。
            本檔沿用 `components.md` 的邏輯名；對應關係記於
            `functional-spec.md` 的落差段，避免下游以為是兩個不同的時間。
    entity_constraints:
      - 每筆紀錄恰指向一張架構圖
      - 每筆紀錄恰有一個行為者
    relationships:
      - target: System
        cardinality: many-to-one
        direction: DiagramChangeRecord → System
        description: 每筆變更紀錄經架構圖上溯到一個系統
        constraints:
          - >
            **這是間接關係，不是直接參照**：紀錄指向架構圖，架構圖指向系統。
            故「查某系統的全部變更紀錄」必須經架構圖轉一手；而架構圖的系統
            參照可為空（遷移後應為 0 列，由 `U4` 的不變量保證）。
```

## 人類可讀摘要

本單元擁有三個實體，構成「專案 → 系統 → 架構圖」階層的上兩層與其變更軌跡：

| 實體 | 在階層中的角色 | 誰擁有它的 DDL |
|---|---|---|
| `Project` | 第一層；作業對象識別的最外層 | `U4 hierarchy-data`（已交付） |
| `System` | 第二層；架構圖的歸屬目標 | `U4 hierarchy-data`（已交付） |
| `DiagramChangeRecord` | 架構圖異動的軌跡，經圖上溯到系統 | `U4 hierarchy-data`（已交付） |

**本單元不擁有任何 DDL。** 它擁有的是這三個實體的**生命週期與授權**——
讀、建、改、刪的行為規則，以及那些規則如何被強制。資料形狀的權威在 `U4`，
而 `U4` 已登記完成，因此本檔對實體的任何約束敘述都以「實讀 `U4` 交付物」為準，
與 `components.md` 的落差逐處標出而非逕自採信上游宣告。

五個刻意的缺口，皆已在 `yaml` 區塊內就地記載，不在此重述：名稱唯一性只有服務層
檢查（有 TOCTOU）、變更紀錄的壽命綁在架構圖上（級聯刪除）、變更紀錄的保存期為
90 天而清除機制不在本 repo、變更紀錄的來源欄位在資料層只容納一條路徑、
預設標記只能由遷移程式寫入（本單元不得視為可設定的旗標）。

**讀取的列可見範圍不在本檔**：它是行為規則而非資料形狀，落在 `rules.md`
`BR6.1`–`BR6.3`。本輪以 `ownerUserId` 為限，是刻意比最終模型更窄的過渡版
（`OPEN-H7`）。
