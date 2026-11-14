## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

設計本身（DG-1 以不設外鍵處置、BR2.2 不含內容的前提、BR3.1 靜默失敗的說明、BR4.1 的 CHECK 理由）自洽且精簡引用上游足以承載資料層不變量，不因精簡列發現。但有三個會讓開發者必須猜測的缺口。第一，traceability.json 與 story map 指派不符：U5 被指派的是 US4.1 與 US4.5，而 traceability 漏掉 US4.5，並把 AC4.5.1／4.5.2／4.5.3 對應到 BR4.1／4.2／4.3，內容與 stories.md 該三條 AC 的實際文字（grant 邊界、跨 schema join、越權被拒）完全不同。第二，BR2.4 要求「保留的系統行為者識別值」，卻沒說明它如何滿足 actorUserId 為 NOT NULL 且參照 public.users 的設計，已落地程式靠種子帳號 SYSTEM.retention-purge 解決，設計沒有寫。第三，BR1.2 的 grant 針對「記憶層使用的資料庫角色」，但設計從未定義該角色，而已落地程式只能 GRANT 給 current_user。另有四項 Minor。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-data/functional-design/traceability.json > upstream_ids、coverage（AC4.5.1／AC4.5.2／AC4.5.3） | unit-of-work-story-map.md 第 110 行指派給 U5 的故事是 `US4.1`、`US4.5`（第 52、56 行亦同）。traceability.json 的 upstream_ids 沒有 `US4.5`。US4.2／US4.3 反而列入，但它們被指派給 U8／U9，不屬 U5。更嚴重的是 AC4.5.x 對應錯誤：stories.md 第 235-237 行，AC4.5.1 是「應用程式角色對記憶 schema 有權限、對其他 schema 存取不擴大」，AC4.5.2 是「同 database 可執行跨 schema join」，AC4.5.3 是「只被授予記憶 schema 的角色讀既有業務表被資料庫拒絕」。traceability 卻把它們對到 BR4.1（90 天）、BR4.2（清除承載形式）、BR4.3（清除留稽核），那是 AC4.2.x 的內容。結果是 U5 真正被指派的 US4.5 三條 AC 在設計中沒有對應的規則，也沒有驗證項：AC4.5.2（跨 schema join）無任何規則，AC4.5.3 的拒絕行為與 BR1.2 同時要求「單獨授予讀 public.users」存在張力（users 本身是既有業務表）。AC4.1.1／4.1.2／4.1.3 的對應（BR1.1／BR1.2／BR3.1）也只是概念上的資料層前提，AC4.1.3「三種記憶皆可取得」應對到 kind 封閉列舉而非 BR3.1。 | 重建 traceability：加入 US4.5 及 AC4.5.1-4.5.3，改對到 BR1.1／BR1.2 並新增或指名涵蓋「跨 schema join 可行」與「只有記憶 schema 權限的角色讀不到業務表」的規則與驗證載體（N-2）；移除不屬 U5 的 US4.2／US4.3 或明列為 U8 轉交；AC4.1.3 對到 kind 列舉。同時說明 BR1.2 要求的 public.users 讀取權限與 AC4.5.3 如何並存（例如限定為僅 users 的 REFERENCES／SELECT 欄位）。 | New |
| R-02 | Major | construction/memory-data/functional-design/rules.md > BR2.4；entities.md > MemoryAuditEvent.actorUserId | entities.md 把 `actorUserId` 定為 required reference 到 public.users，BR2.4 說清除事件的行為者是「一個保留的系統行為者識別值」，但沒說這個值是什麼、是否必須是 users 表的一列。若參照 users，就必須有一列種子帳號，否則每次清除稽核 INSERT 因外鍵違反失敗，而清除的 DELETE 與稽核 INSERT 同交易，整個清除會中止（schema_rbac.sql 第 811-862 行即在處理此事）；若不參照 users，則 entities 的參照宣告與 NOT NULL 都不成立。誰建立該列、誰能刪、它不能登入如何保證，設計一個字都沒寫，這是契約端點三問中「誰寫、誰清」的缺口。已落地程式用種子帳號 `SYSTEM.retention-purge`（四道鎖）解決，設計被程式超前，但設計文字本身讓開發者必須猜。 | 在 BR2.4 與 entities 補寫：系統行為者是 users 表中的一列保留帳號、由誰種子化、命名與無法登入的保證、不得刪除及刪除後果；並標明程式（schema_rbac.sql 第 862 行附近）是對的一邊。 | New |
| R-03 | Major | construction/memory-data/functional-design/rules.md > BR1.2；functional-spec.md > §八 IAM | BR1.2 的 `applies_to` 是「記憶層使用的資料庫角色」，並要求「授予 memory USAGE 與 DML，不授予 public 寫入」。設計從未定義這個角色：它是不是與應用既有帳號不同的角色、誰建立、如何提供給 U8／U9。若應用只用一個連線角色（部署的 POSTGRES_USER），grant 對它沒有限制作用，邊界是空的，這也是 FR4.4 與 AC4.5.1／4.5.3 的核心。已落地程式只能對 `current_user` 執行 GRANT，且 schema_rbac.sql 第 548-553 行承認未被 CI 驗證（OPEN-CG5-1），N-2 只有 superuser。spec 把 BR1.2 寫成可達成的規則，並未承認「在單一角色部署下它是名目上的」，這與 BR1.1 violation_behaviour 的誠實度不一致，也讓 IAM 面向的判定「適用」缺乏落點。 | 在 BR1.2 與 functional-spec §八補寫：記憶層角色是否獨立、誰建立、單一角色部署下邊界的實際強度；若本輪只做到 current_user 的 GRANT，需如實登錄為殘餘風險（比照 OPEN-M6 的寫法），並說明 AC4.5.3 的驗證需第二個角色的 CI 設置。 | New |
| R-04 | Minor | construction/memory-data/functional-design/entities.md > MemoryRecord.visibilityScope、MemoryAuditEvent.previousScope／newScope | 三欄標為 enumeration，卻沒有 allowed_values，也沒有預設值。AC4.4.3 要求預設為最窄（僅擁有者可見），FR4.3b 要求變更留稽核；OQ-12 只延後「誰能放寬」，不延後「有哪些範圍值」。已落地程式為 VARCHAR(32) 無 CHECK，等於把封閉集合推給 U8。 | 補列範圍值集合與預設值，或明寫「值集合由 U8 契約定義，本表刻意不加 CHECK」並說明理由。 | New |
| R-05 | Minor | construction/memory-data/functional-design/functional-spec.md > §六 ER 圖（memoryId／auditEventId 標 uuid） | ER 圖把主鍵畫成 uuid，entities.md 只寫 identifier，已落地 schema_rbac.sql 第 454 行與 516 行為 `SERIAL`／`INTEGER`。memory_audit_events.memory_id 為 INTEGER，與 memory_records.id 型別一致，但設計與程式對不上；spec 稱 ER 為衍生檢視，卻與實作不一致。 | 以程式為準，把 ER 圖與 entities 的識別碼型別改成整數序號，並說明「不透明」指不透過外鍵、不是不可猜測。 | New |
| R-06 | Minor | construction/memory-data/functional-design/rules.md > BR3.2；functional-spec.md > §〇 | 交付物含「向量索引」與 pgvector 欄位，設計沒有規則涵蓋 `CREATE EXTENSION vector` 由誰建立（含 PostgreSQL 映像是否內建 pgvector）、索引種類與距離運算子。已落地程式選 HNSW cosine（第 503-504 行），且對 BR3.1 的 embedding_model 過濾另建 btree，HNSW 加過濾的召回行為（過濾後結果可能少於 k）設計未討論。 | 補一條規則或開放項：extension 的建立與映像相依、索引種類與距離函式的選定理由、過濾搭配 ANN 的召回行為，並對應到 N-2 的驗證。 | New |
| R-07 | Minor | construction/memory-data/functional-design/functional-spec.md > §一 OPEN-M2；traceability.json > open_items OPEN-M2 | OPEN-M2 說稽核事件無保存期、會無限期累積，承接站為 nfr-requirements。已落地程式第 513-536 行的 COMMENT 明寫「稽核保存期 90 天，以自身 occurred_at 為鍵（NFR7.2）」，即該缺口已被下游關閉並實作。凍結的設計仍呈現為未決，與現況矛盾。 | 在設計加註或另列修正檔，說明 OPEN-M2 已由 NFR7.2 處置，並指出與 BR2.2 的關係（稽核表自身保存期不改變「不含內容」前提）。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 手動比對 story map 第 110 行與 traceability.json | 不一致 | U5 指派 US4.1／US4.5；traceability 缺 US4.5 且 AC4.5.x 對應內容錯誤，見 R-01 |
| 手動比對 stories.md 第 235-237 行與 traceability coverage | 不一致 | AC4.5.1-4.5.3 的實際內容為 grant／跨 schema join／越權被拒 |
| 抽查 schema_rbac.sql 第 440-563、862 行 | 部分不符 | 識別碼型別、系統行為者種子、grant 對象與 OPEN-M2 皆與設計文字有差，見 R-02、R-03、R-05、R-07 |
| rules.md 規則計數（13 條） | 通過 | BR1.x 3、BR2.x 4、BR3.x 3、BR4.x 3，與文字一致；未執行腳本，僅人工核數 |
