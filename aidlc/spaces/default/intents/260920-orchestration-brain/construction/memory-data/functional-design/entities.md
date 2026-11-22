# 實體模型 — `U5 memory-data`

> 本檔的 ```yaml 區塊是**實體的單一真實來源**。下方散文為人類可讀摘要，
> `functional-spec.md` 的 ER 圖為衍生檢視，兩者皆不得與此區塊矛盾。
>
> **本單元擁有 DDL**（與 `U7` 相反）：記憶獨立 schema ＋ 兩張表 ＋ 向量索引
> ＋ grant 邊界。故 `project.md` 的 **blocking 同步規則觸發**——
> `schema_rbac.sql` 與 `DEPLOY.md` 必須在 `code-generation` 同步更新。
>
> **驗證載體是真實 PostgreSQL CI job（`N-2`），不是既有測試路徑**：
> 既有測試在 `tests/helpers.py` 改走 in-memory SQLite，而 **SQLite 沒有 schema
> 概念**，對本契約沒有任何驗證路徑（契約 K-05 的 `verification` 逐字）。

## 實體定義（單一真實來源）

```yaml
schema:
  name: memory
  form: 同一個 PostgreSQL database 內的獨立 schema（保留原生跨 schema join 能力）
  boundary: grant 只開放記憶 schema
  precedent: >
    **本 repo 零前例**——全樹無 `CREATE SCHEMA`、無 `search_path`
    （契約 K-05 的 `schema_isolation.precedent` 逐字；
    `unit-of-work.md:218` 同樣點名這一點）。
  idempotency: >
    全部 DDL 與 grant 以可重跑安全寫法撰寫（`CREATE SCHEMA IF NOT EXISTS`／
    `CREATE TABLE IF NOT EXISTS`／重複 GRANT 無害）。**無資料遷移**，
    故無 `K-04` 那類的重跑風險（契約 K-05 的 `retry_and_idempotency`）。

entities:
  - name: MemoryRecord
    identifier: memoryId
    table: memory.memory_records
    description: >
      一列記憶。三種 kind 共用一張表（semantic／procedure／episodic）。
    attributes:
      - name: memoryId
        logical_type: identifier
        required: true
        unique: true
      - name: kind
        logical_type: enumeration
        required: true
        allowed_values: [semantic, procedure, episodic]
        constraints:
          - >
            封閉列舉，以 CHECK 約束承載。**只有 `episodic` 受 90 天保存期約束**
            （`FR4.5` 逐字限定 episodic memory）——另兩種無保存期。
            這個區別必須在資料層可判，否則清除作業無從分辨。
      - name: ownerUserId
        logical_type: reference
        required: true
        references: User（既有實體，位於 public schema）
        constraints:
          - >
            **跨 schema 參照**：`memory` schema 的表指向 `public.users`。
            這是刻意選擇獨立 schema 而非獨立 database 的理由——
            契約 K-05 的 `schema_isolation.form` 逐字「保留原生跨 schema join 能力」。
      - name: visibilityScope
        logical_type: enumeration
        required: true
        constraints:
          - 變更須留稽核（`FR4.3b`，見 `MemoryAuditEvent`）
          - 放寬可見範圍的角色集合為 `OQ-12`，**不在本單元定案**
      - name: content
        logical_type: text
        required: true
      - name: embedding
        logical_type: vector(1024)
        required: false
        constraints:
          - >
            **維度固定 1024**，與 `OLLAMA_EMBED_MODEL` 預設 `bge-m3` 的 dense
            維度一致（契約 K-01 對該變數的 validation 逐字要求）。
          - >
            **`fulltext` 模式下建立的列其 embedding 為 NULL**，之後不會被向量
            檢索看到，除非重新 embed（契約 K-05 的 `invariants` 第二條逐字）。
            故本欄可為空，且「為空」是一個**有意義的狀態**而非缺漏。
      - name: embeddingModel
        logical_type: text
        required: true
        constraints:
          - >
            **每列必帶，且相似度檢索只比對同一 `embeddingModel` 的列。**
            理由逐字來自契約 K-05 的 `invariants`：
            「**同維度不等於同向量空間**，不加這道過濾會讓跨模型的檢索回垃圾
            **且不報錯**」（decisions.md ADR-008）。
            這是本單元最重要的不變量——它的失敗模式是**靜默的錯誤結果**，
            不是錯誤訊息。
          - >
            `fulltext` 模式下該欄仍必填（記錄「這列是以何種方式產生的」），
            即使 `embedding` 為 NULL。
      - name: createdAt
        logical_type: timestamp
        required: true
      - name: expiresAt
        logical_type: timestamp
        required: false
        constraints:
          - >
            `episodic` 列為必填（`createdAt` ＋ 90 天）；另兩種 kind 為 NULL。
            以 CHECK 約束把「kind 為 episodic 則 expiresAt 不得為 NULL」寫進資料層
            ——否則一列逾期記憶會因為漏填而永久留存，而**沒有任何跡象**。
    relationships:
      - target: MemoryAuditEvent
        cardinality: one-to-many
        direction: MemoryRecord → MemoryAuditEvent
        description: 一列記憶的刪除與可見範圍變更各留一筆稽核事件
        constraints:
          - >
            **刻意不設外鍵**（`[M1]`=A，見 `MemoryAuditEvent.memoryId`）。
            故這個關係在資料層**沒有參照完整性保護**，是一個邏輯關係。

  - name: MemoryAuditEvent
    identifier: auditEventId
    table: memory.memory_audit_events
    description: >
      記憶的刪除與可見範圍變更的稽核軌跡。**獨立於記憶本體存活。**
    attributes:
      - name: auditEventId
        logical_type: identifier
        required: true
        unique: true
      - name: memoryId
        logical_type: identifier（**不透明值，非外鍵**）
        required: true
        constraints:
          - >
            **刻意不對 `memory_records` 設外鍵**——`DG-1` 的處置
            （使用者裁決 `[M1]`=A，2026-10-06）。
            `FR4.5` 要 90 天刪除、`FR4.7` 要刪除留稽核；設外鍵則兩者必然衝突
            （一併刪除使 `FR4.7` 失去意義，保留則懸空）。不設外鍵使稽核軌跡
            在記憶被清除後**仍然完整且可查**。
          - >
            **代價：本欄沒有參照完整性保護**，可以寫入一個不存在的
            `memoryId` 而資料庫不會擋。緩解是寫入端唯一（`K-08` 的 facade），
            但那是應用層保證而非資料層保證——如實記為 `OPEN-M1`。
      - name: actorUserId
        logical_type: reference
        required: true
        references: User（既有實體，位於 public schema）
        constraints:
          - >
            **90 天清除產生的事件其行為者是誰？** 清除是排程觸發、無人在迴圈內
            （`FR4.5a`），故沒有自然的使用者。本單元定為**系統行為者**，
            見 `rules.md` `BR2.4`。
      - name: action
        logical_type: enumeration
        required: true
        allowed_values: [deleted_by_user, purged_by_retention, scope_changed]
        constraints:
          - >
            **三個值刻意分開 `deleted_by_user` 與 `purged_by_retention`**：
            前者是 `FR4.6`（使用者自行刪除）、後者是 `FR4.5`（90 天逾期）。
            合併成一個「deleted」會讓「使用者主動刪除」與「系統逾期清除」
            在稽核上不可分辨，而兩者的法遵意義完全不同。
      - name: previousScope
        logical_type: enumeration
        required: false
        constraints:
          - 僅 `scope_changed` 時有值（`FR4.3b`）
      - name: newScope
        logical_type: enumeration
        required: false
        constraints:
          - 僅 `scope_changed` 時有值
      - name: occurredAt
        logical_type: timestamp
        required: true
    entity_constraints:
      - >
        **本表不含 `content`、不含 `embedding`。** 這不是省略——它是
        `[M1]`=A 能成立的前提：稽核事件比記憶本體活得久，而若它含記憶內容，
        「保留稽核」就等於「保留被刪除的使用者資料」，使 `FR4.5` 的刪除
        形同虛設。契約 K-05 的 `key_columns` 本來就沒有這兩欄，本站確認並寫明理由。
      - >
        **本表自身的保存期未定**（`OPEN-M2`）。`FR4.5` 只約束 episodic memory，
        沒有一條已核可需求談稽核事件要留多久；而本輪選的 `[M1]`=A 讓它
        無限期累積。這是本決定的直接後果，不得隱藏。
```

## 人類可讀摘要

本單元擁有一個 schema 與兩張表：

| 實體 | 角色 | 保存期 |
|---|---|---|
| `MemoryRecord` | 三種 kind 共用一張表的記憶列，帶 1024 維向量與 `embeddingModel` | **只有 `episodic` 受 90 天約束** |
| `MemoryAuditEvent` | 刪除與可見範圍變更的稽核軌跡，**獨立於記憶存活** | **未定（`OPEN-M2`）** |

**三個最容易被誤讀的點**，皆已在 `yaml` 區塊就地記載：

1. **`embeddingModel` 的過濾不是效能優化，是正確性要求**——少了它，跨模型檢索
   回垃圾**且不報錯**。
2. **`embedding` 為 NULL 是有意義的狀態**（`fulltext` 模式），不是缺漏。
3. **稽核表對記憶表沒有外鍵**，這是 `DG-1` 的處置而非疏漏；代價是失去參照
   完整性保護，已記為 `OPEN-M1`。
