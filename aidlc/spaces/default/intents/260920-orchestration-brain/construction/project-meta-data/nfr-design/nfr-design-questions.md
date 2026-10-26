# NFR Design 問題檔 — `U18 project-meta-data`

> Depth 為 `Minimal`，且本單元的產出只有 `security-design.md`（`produces_kinds`
> 把 performance／scalability／reliability／observability／logical-components
> 五項篩掉——它們的 kind 清單不含 `spec`）。本站**只問一題**。
>
> 前兩個 `spec` 單元（`U5 memory-data`、`U7 hierarchy-service`）的 nfr-design
> 沒有問題檔，因為沒有需要人工裁決的事。**本站有一件**，見下。

## 〇、不重問的事（上游已定案，可引用選項字母）

| 事項 | 定案處 | 引用 |
|---|---|---|
| 既有環境的新物件建立路徑 | 本單元 `nfr-requirements` | `[P1]`=A（獨立腳本、大聲失敗、不動啟動路徑、`DEPLOY.md` 記步驟），落為 `NFR8.2`–`NFR8.5` |
| 不建 ORM model | 本單元 `tech-stack-decisions.md` §二 | 兩項理由（`spec` 不讀寫；避免重演 `U7` 的建表權威問題） |
| 驗證載體 | 本單元 `tech-stack-decisions.md` §三 | 沿用 `U5` 的 `memory-schema` job 形狀；擴充或新增由 `code-generation` 決定 |
| 三態模型的語意 | `ADR-015` ＋ `BR1.3`／`BR1.4` | 無列／有值／`value` 為 NULL 且 `cleared_at` 有值 |
| COMMENT 義務的內容 | 契約 `K-15` 的 `ddl_comment_requirement` ＋ `BR2.2` | 三件事逐字 |
| 加密面不適用 | 本單元 `security-requirements.md` §二 | 三張表無憑證／token／金鑰；`value` 是架構假設非個人機敏資料 |
| 網路暴露面不適用 | 同上 | 零端點、零進程、零監聽埠；獨立腳本是手動 CLI 非服務 |

## 一、`[ND1]` 四條外鍵的 `ON DELETE` 行為 —— 本站唯一需要裁決的事

### 為什麼這件事必須問，而不是由我選

**`BR2.3`（已核可）只說「四條外鍵必須存在且指向正確的表」，沒有說 `ON DELETE`。**
`entities.md`、契約 `K-15` 的 `foreign_keys` 清單、`rules.md` 全部沒有提到它。
而 `U4` 已交付的 DDL 把這件事當成**必須逐條表態**的事項：

| 既有外鍵（`U4` 已交付） | `ON DELETE` | 出處 |
|---|---|---|
| `systems.project_id → projects.id` | `RESTRICT` | `schema_rbac.sql:351` |
| `user_diagrams.system_id → systems.id` | `RESTRICT` | `schema_rbac.sql:384`，COMMENT（`:391`）逐字寫明理由「`SET NULL` would itself create the `BR2.1` violation」 |
| `diagram_change_records.diagram_id → user_diagrams.id` | **`CASCADE`** | `schema_rbac.sql:395` |
| `projects.owner_user_id → users.id` | **刻意不決定** | `schema_rbac.sql:330` 無子句，COMMENT（`:345`）逐字「Deletion behaviour of the referenced user is deliberately NOT decided (OQ-H1, landing U7) — no ON DELETE clause」 |

**所以本 repo 的慣例是：要嘛決定，要嘛在 COMMENT 寫明沒決定與落點。**
本單元四條外鍵目前兩者皆無。

### 而「稽核表的父列被刪時怎麼辦」在本 intent 已經被**用兩種相反的方式**回答過

| 單元 | 稽核表 | 做法 | 已核可依據 |
|---|---|---|---|
| `U4` | `diagram_change_records` | 父列（架構圖）被刪時**一起刪** | `schema_rbac.sql:395` 的 `ON DELETE CASCADE` |
| `U5` | `memory.memory_audit_events` | **完全不設外鍵**，父列被刪後稽核獨立存活 | 使用者裁決 `[M1]`=A；斷言 `S8`（無外鍵）＋ `S11`（刪除後稽核仍在） |

兩者都是已核可的現況，方向相反。`reselection_events` 是本 intent 第**三**張稽核表，
所以這不是「照慣例做」就能解決的——**沒有單一慣例**。

### 具體後果：這件事會不會弄壞已交付的程式

`hierarchy_service.delete_project()`（`:147`–`:162`，**`U7` 已交付**）只有兩道守門：

- `:153` `is_default` 為真即拒（`BR4.2`）
- `:156` 底下仍有系統即拒，訊息含剩餘系統數（`BR4.4`）

**沒有任何一道關於成員。** 而 `components.md:886` 逐字把 `ProjectMember` 的寫入端
列為「建立專案時的自動寫入 ＋ 邀請成功」——也就是說 `U19` 落地後，
**每一個新建專案都至少有一列成員**。

於是若 `project_members.project_id` 採 `RESTRICT`（或不寫子句，PostgreSQL 預設
`NO ACTION`，對本情境行為相同），`:161` 的 `db.delete(project)` 會在 `commit()`
時丟出**未被捕捉的 `IntegrityError`**，而不是 `BR4.4` 那種帶訊息的
`HierarchyConflictError`。使用者看到的是 500 而非「請先移出成員」。

### 另一側的後果：`FR12.4b` 的稽核會被一個普通的使用者動作毀掉

`FR12.4b`（`requirements.md:307`）逐字：

> 自動改選須留稽核：誰、何時、對誰、舊角色、新角色。**自動改選尤其必要**
> ——它由系統發起、無人按下按鈕，不留紀錄則事後無從得知某人的
> `project_admin` 是怎麼來的。

若 `reselection_events.project_id` 採 `CASCADE`，刪一個專案就連帶刪掉
「這個專案的管理權曾經被系統自動交給誰」的全部紀錄。

### 選項

| 選項 | `project_members.project_id` | `reselection_events.project_id` | `system_requirement_fields.system_id` | 代價 |
|---|---|---|---|---|
| **A（建議）** | `CASCADE` | **不設外鍵**（沿用 `U5` 的 `[M1]`=A） | `CASCADE` | 專案刪除照常可用，不碰已交付的 `U7` 程式；改選稽核存活。代價是 `reselection_events` 會留下指向已刪專案的孤列——與 `U5` 的 `S8`／`S11` 已接受的同一種代價，且須以斷言鎖住「刪專案後稽核仍在」 |
| **B** | `RESTRICT` | `RESTRICT` | `RESTRICT` | 與 `systems.project_id` 一致、參照完整性最強。代價是 `delete_project` 對**任何有成員的專案**（即 `U19` 之後的全部專案）丟未捕捉的 `IntegrityError`，修它要改已交付的 `U7` 程式，屬本單元之外的範圍 |
| **C** | `CASCADE` | `CASCADE` | `CASCADE` | 與 `diagram_change_records` 一致、最簡單。代價是刪專案即毀掉 `FR12.4b` 的改選稽核，而那條逐字說「不留紀錄則事後無從得知某人的 `project_admin` 是怎麼來的」 |
| **D** | `RESTRICT` ＋ 在 `delete_project` 補一道成員守門（比照 `BR4.4` 的形狀與訊息） | **不設外鍵** | `CASCADE` | 語意最乾淨（「還有人在的專案不能刪」是合理的 UX，且與 `BR4.4` 同形），稽核也存活。代價是**要改已交付的 `U7` 程式**（`hierarchy_service.delete_project`），且該改動需要自己的測試——本單元是 `spec`，這會把它的範圍擴到應用層 |

[Answer]: A 稽核不設外鍵，其餘 CASCADE
<!-- 作答時間：2026-10-06T14:54:23Z，取自 audit shard 的 QUESTION_ANSWERED 列而非估計。
     （初稿曾憑感覺寫 14:22:03Z，以 `date -u` 複核後發現偏離，已更正為權威值。） -->

**後果（本站據此設計）**：

1. `BR2.3`（已核可）的「四條外鍵」**收為三條**。這是本站對已核可規則的**修訂指派**，
   不逕自改上游產出；落點與具體修法見 `security-design.md` §三之二。
2. 須新增兩條 CI 斷言，形狀比照 `U5` 的 `S8`／`S11`：
   「`reselection_events` 對 `projects` 無外鍵」（結構）與
   「刪除專案後其改選稽核列仍存在」（行為）。
   `U5` 已證實這兩條**缺一不可**——`S8` 驗手段、`S11` 驗目的。
3. 不碰已交付的 `U7` 程式：`delete_project` 的守門清單不需增加成員那一道，
   `:161` 的 `db.delete(project)` 行為不變。

## 二、不出成題目的事（單一可行解，在此揭露而非假裝有選擇）

依 `project.md` 的規則（「某個結果若是多項已核可決定各自逼出的唯一解，不出成題目」），
下列三項**沒有第二個選項**，在此揭露：

1. **四條外鍵欄位都要有索引。** `U4` 三條外鍵三個索引（`schema_rbac.sql:336`／`:358`／
   `:388`），`models.py` 的六處 FK 欄位帶 `index=True`。PostgreSQL **不會**自動為
   referencing 欄位建索引，而 `entities.md` 宣告了**零個**索引。這是慣例＋資料庫行為
   逼出的唯一解，見 `security-design.md` §四之二。
2. **`reselection_events` 的橫幅查詢需要 partial index。** `[M1]`=B 要求橫幅在
   **每次進入產品**時都看得到，故該查詢是三張表中頻率最高的讀取；而
   `entity_constraints` 逐字「**故不可用專案做唯一鍵**」，等於宣告這張表**完全沒有索引**。
   `U4` 已有 partial index 的慣用法先例（`uq_projects_default_per_owner ... WHERE is_default`）。
3. **九個欄位缺漏須回補而非由本站補上。** 見 `security-design.md` §三——
   本站標出缺口並指派落點，不逕自修改已通過審查的上游產出
   （`project.md`：「發現已核可上游的契約缺口時……不逕自修改已通過 reviewer 的上游產出」）。
