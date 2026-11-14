# 測試指示 — `U7 hierarchy-service`

> 框架為 Python 內建 `unittest` ＋ `starlette.testclient.TestClient`
> （`team.md ## Testing Posture`：本 repo **未使用 pytest**）。
> 測試檔放 `backend/tests/` 即被 `python -m unittest discover -s tests` 撿到。
> 每支測試檔首行必須有 `import tests.helpers  # noqa: F401`——它在任何 DB
> import 之前把 `psycopg2` 換成 `MagicMock()` 並改走 in-memory SQLite。

## 一、檔案與夾具

單一檔案 `backend/tests/test_hierarchy_service.py`。夾具三項：

1. **DB**：沿用 `tests/helpers.py` 的 in-memory SQLite ＋ ORM metadata 建表。
2. **身分覆寫**：以 `app.dependency_overrides` 覆寫 `get_db`（`database.py:31`）
   與 `get_current_user`（`services/auth.py:39`）——兩者皆為穩定的模組層函式。
3. **權限覆寫**：`K2` 的判定走既有 `require_story_action`；以兩個使用者
   （`alice` 具 `K2`、`bob` 不具）建構 allow/deny 兩路。

**不需要真實 DB**：以 `TestClient(app)` 直接使用**不觸發**
`@app.on_event("startup")` 的 `init_db()`。

## 二、必須有的測試（逐項對應規則，二元可判）

### A 群——授權（`team.md` 的 A＋B 規則交叉要求，缺一不可）

| id | 斷言 | 規則 |
|---|---|---|
| `T1` | 具 `K2` 的角色呼叫五個 path 皆得 **2xx** | `BR1.1` |
| `T2` | **不具 `K2`** 的角色呼叫五個 path 皆得 **403** | `BR1.1` |
| `T3` | facade 的拒絕是 `HierarchyForbidden(story_id='K2', action=…)`，**不是** `HTTPException`；router 才轉 403 | `BR1.1`／K-07 `on_denied` |
| `T4` | 不帶 `Principal` 無法呼叫 facade（型別層）；且 `Principal` 無法在 facade 模組外被建構 | `BR1.4` |

### B 群——列可見範圍（本輪兩個 Critical 的處置，**最需要被測**）

| id | 斷言 | 規則 |
|---|---|---|
| `T5` | `alice` 的 `list_projects` **不含** `bob` 的專案 | `BR6.1` |
| `T6` | `alice` 以 `bob` 的 `project_id` 呼叫 `list_systems` → 回**「查不到」而非「無權限」**（不以錯誤碼洩漏存在） | `BR6.1` |
| `T7` | `alice` 以 `bob` 的識別碼呼叫 `resolve_work_target` → 查不到 | `BR6.1` |
| `T8` | `alice` 在 `bob` 的專案底下 `create_system` → **被拒** | **`BR6.5`** |
| `T9` | `alice` 刪除 `bob` 的專案／系統 → **被拒** | **`BR6.5`** |
| `T10` | `project_exists`／`get_project_owner`／`get_project_of_system` 對**他人**的識別碼**仍然回答**（不套列範圍），且回傳型別為 `bool`／`int`／`int`——**不回傳 model 物件、不回傳名稱** | **`BR6.4`** |
| `T11` | `list_diagram_changes` 只回傳 `user_diagrams.user_id` 等於請求者的紀錄 | `BR6.3` |

> `T10` 是 `[F9]`=A 的正面斷言：它**必須**回答，否則 `K-16`／`K-17` 不可實作。
> 同時斷言回傳型別，因為「最小欄位」是「可驗證已知 id」與「可枚舉未知 id」
> 之間的唯一分界（`BR6.4` 的 `violation_behaviour`）。

### C 群——建立與名稱

| id | 斷言 | 規則 |
|---|---|---|
| `T12` | 空白名稱（`""`／`"   "`）→ `HierarchyValidationError`，**非** 500 | `BR3.1` |
| `T13` | 同擁有者下同名專案 → `HierarchyConflictError` ＋ **409** | `BR3.2`／`BR6.6` |
| `T14` | 新建的專案與系統 `is_default` 為 **False** | `BR2.3` |
| `T15` | `create_system` 指向不存在的專案 → `HierarchyNotFound` | `BR2.2` |

### D 群——刪除（三條前置，各自獨立觸發）

| id | 斷言 | 規則 |
|---|---|---|
| `T16` | 刪除 `is_default` 為真的專案／系統 → 被拒 | `BR4.2` |
| `T17` | 刪除底下仍有系統的專案 → **409**，且訊息**含剩餘系統數** | `BR4.4` |
| `T18` | 刪除仍有架構圖的系統 → 被拒，且說明還有幾張圖 | `BR4.3` |
| `T19` | 三者皆不命中才真的刪除，且**不級聯**（刪系統不會連帶刪圖） | `BR4.3`／`BR4.4` |

### E 群——變更紀錄

| id | 斷言 | 規則 |
|---|---|---|
| `T20` | `source` 非 `brain_orchestration` → 被拒（允許值只有一個） | `BR5.3` |
| `T21` | 空白 `requirement_summary` → 被拒 | `BR5.4` |
| `T22` | `actor_user_id` 取自**造成異動的行為者**，而非 session 擁有者——以「principal 與 actor 不同」的情境斷言寫入的是後者 | **`BR5.6`** |
| `T23` | `list_diagram_changes` 以標籤查詢可取得紀錄；**以系統查詢對 `system_id` 為空的圖回傳空集合**（`OPEN-H11` 的現況，斷言現實而非願望） | `BR5.1`／`OPEN-H11` |

### F 群——NFR 與契約

| id | 斷言 | 規則 |
|---|---|---|
| `T24` | 每個端點的 `response_model` 欄位集合與規格一致（`team.md` B 規則逐字要求斷言欄位集合） | `NFR5.1` |
| `T25` | **ORM metadata 與 `schema_rbac.sql` 的欄位集合一致**——解析該 SQL 檔的三個 `CREATE TABLE` 區塊，與 model 的 `__table__.columns` 比對 | 決定 1 的「鎖住兩份物化」義務 |
| `T26` | facade／service 模組**不持有任何模組級可變狀態**（以 `inspect` 掃模組層 `dict`／`list`／`set`） | **`NFR4.1`** |

> `T25` 是決定 1 合規的前提。`team.md` 逐字：「新增副本的同一個 PR 必須一併新增
> 鎖住兩者一致的測試；無法寫測試的副本不新增。」

## 三、突變驗證（每一項都要先 RED 再還原）

**做法**：把修正改回錯的行為 → 跑測試確認**紅燈** → 還原 → 複驗綠燈。
每一項都要先以行為探測確認「輸出真的改變了」，避免出現
`embedding-port` 那次的 `M2`——**突變本身是無效的**（內層另有一個 break，
使外層的改動成為 no-op），於是「測試沒抓到」其實是「突變沒發生」。

| # | 突變 | 應該紅的測試 |
|---|---|---|
| `M1` | 移除 `list_projects` 的擁有者過濾 | `T5` |
| `M2` | 把 `BR6.1` 的「查不到」改成「無權限」 | `T6` |
| `M3` | 移除 `create_system` 的擁有者檢查 | `T8` |
| `M4` | 移除 `delete_*` 的擁有者檢查 | `T9` |
| `M5` | 讓 `project_exists` 套上列範圍（即 `[F9]` 的選項 C 行為） | `T10` |
| `M6` | 把 `actor_user_id` 改為取 session 擁有者 | `T22` |
| `M7` | 把拒絕改成 raise `HTTPException` | `T3` |
| `M8` | 讓 `Principal` 可在模組外建構 | `T4` |
| `M9` | 移除刪除前置的剩餘數量訊息 | `T17` |
| `M10` | 在 service 模組加一個模組級 dict 當快取 | `T26` |
| `M11` | 在 model 加一個 `schema_rbac.sql` 沒有的欄位 | `T25` |
| `M12` | 移除 router 的 `responses={409: ...}` 宣告 | **無測試會紅**——見下 |

**`M12` 是刻意列出的已知缺口**：移除 409 宣告後 CI 全綠、契約不進 spec、
前端產不出型別，而**沒有任何自動化會發現**（`unit-of-work.md:447` 逐字「非
2xx/422 的宣告數為 0」）。`T24` 驗的是 response_model 的欄位集合，不是狀態碼宣告。
處置：列為 `OPEN-ID7-2`，並在完成判準加一條人工核對
（`openapi.json` 中該 operation 的 responses 含 `409`）。
**不假裝它被測試覆蓋。**

## 四、不寫的測試（附理由，不留空白）

- **不為 `BR1.3`／`BR3.3`／`BR4.5`／`BR6.2` 寫測試**：四者的
  `violation_behaviour` 皆為「不適用」——它們是誠實宣告而非禁令，
  沒有可失敗的行為。為它們寫測試會產生恆真斷言。
- **不為 `BR1.5` 寫測試**：它約束的是 `U10`／`U12`／`U19`／`U20` 的 import 方式，
  **本單元無法驗證**（`OPEN-H2`）。落點在那四個單元的 code-generation。
- **不寫 property-based 測試**：ADR-0006 的 PBT hard constraint 對本單元判為
  **N/A**（非豁免）——適用對象為 IaC generator、估價表解析器、agent routing；
  `unit-of-work.md` 全檔對 `U7` 無 PBT 指派，`:448` 只指派給 `U19` 的挑選函式。
  本單元**無純函式計算層**（`logical-components.md` §一），授權判定與存在性檢查
  都是二元結果，example-based 即足。
  **失效條件**：若把名稱正規化或可見範圍判定抽成不讀 DB 的純函式，PBT 即適用。
- **不寫前端測試**：本單元零前端（畫面屬 `U23`／`U16`）。
