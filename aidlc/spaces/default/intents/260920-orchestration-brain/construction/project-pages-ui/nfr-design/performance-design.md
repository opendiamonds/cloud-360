# 效能設計 — `U23 project-pages-ui`

> 撰寫時間 2026-10-15T23:26:04Z（`date -u` 取值）。
>
> 承接 `../nfr-requirements/performance-requirements.md` 的 `NFR11.100`–`.102` 與 `PPN-01`–`PPN-07`，以及帶入項
> functional-design `R-04`、nfr-requirements `R-02`（索引落點，主體在 `logical-components.md` §三）與 `R-05`。本站把「判準」變成
> 「做法」：每一條寫出落在哪個模組、哪個時點、以什麼結構承載，以及被改壞時哪一個檢查會紅。模組名稱以 `logical-components.md`
> §一 為準。本站未執行任何程式或測試；凡依賴套件行為者標明取得方式。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-requirements/performance-requirements.md` | `PPN-01`–`PPN-07`、§二之一（4 的依據）、§二之二（順序與不進佇列者）、§三（不設硬上界的代價） |
| `../functional-design/rules.md` | `BR85.1`（單一份 `fieldsBySystem`）、`BR88.1`（兩層抓取形狀）、`BR88.3`（佇列、不截斷、卸載不再發） |
| `../functional-design/frontend-components.md` §二、§三、§六 | 元件樹與 state 持有者；7 個端點與次數 |
| `../carried-review-items.md` | functional-design `R-04`；nfr-requirements `R-02`、`R-05` |
| repo 實測 | `backend/database.py:37`（`create_engine(db_url)`，無 pool 參數）、`schema_rbac.sql:594-606`（`project_members` DDL）、`backend/services/membership_service.py:299`（`project_ids_where_admin`） |

## 一、前端扇出佇列（`PPN-01`–`PPN-05`、帶入項 functional-design `R-04`）

### 一之一、結構

一支自寫的非元件模組 `frontend/src/projects/fanoutQueue.ts`（`PPN-21`：零新依賴；檔名依 `team.md` 的「其餘 camelCase」）。
它**不持有任何 React state**，只負責「在途數 < 上限才取下一個」與「取消後不再發出」。兩層抓取形狀（`BR88.1`）不變：
純抓取函式（`projectsApi.listSystems`、`requirementsApi.readFields`、`projectsApi.listDiagramChanges`）原樣保留；佇列位於
**呼叫端那一層**（effect 內），state 更新仍在 `.then` 中、受 `cancelled` 旗標保護。

```text
// fanoutQueue.ts（介面層示意，非實作）
export const FANOUT_CONCURRENCY = 4;                       // PPN-01；唯一的定義處
export interface FanoutQueue {
  enqueue<T>(task: () => Promise<T>): Promise<T>;          // FIFO；在途 < 上限即發
  cancel(): void;                                          // 尚未發出者不再發出（PPN-04）
}
export function createFanoutQueue(limit = FANOUT_CONCURRENCY): FanoutQueue;
// 取消後，尚未發出的 task 其 Promise 以 FanoutCancelled 拒絕；呼叫端已有 cancelled 旗標，一律忽略
```

| 頁面 | 佇列實例 | 入列內容與順序（`PPN-02`） | 清除端 |
|---|---|---|---|
| `ProjectsListPage` | 每次 effect 建一個 | 端點 1 完成後，依**專案 id 遞增**入列 P 個端點 2 | effect cleanup 呼叫 `cancel()` |
| `ProjectDetailPage` | 每次 effect 建一個 | 端點 1、2 依序完成後，**先**依系統 id 遞增入列 S 個端點 5（K4 view 時），**再**依系統 id 遞增入列 S 個端點 7 | 同上 |

**FIFO 即是順序保證**：順序由「入列順序」決定，佇列本身不排序、不重排；`PPN-02` 只要求呼叫端以兩段迴圈依序入列。
「使用者目前選取的系統優先」不實作（`performance-requirements.md` §二之二 已定：進頁時的選取即第一個發出者）。

**不進佇列的請求**（與 `performance-requirements.md` §二之二 逐項一致）：端點 1、詳情頁進頁的那一次端點 2、建立系統後的
系統清單重讀、端點 3／4、`k` 次端點 6、儲存後的端點 5 重讀（W6 第 6 步）、`[重新整理]`（`BR85.6`）。它們直接呼叫純抓取函式。
**不進佇列的請求在佇列未清空時也立即發出**——這是刻意的：使用者按了儲存，不該等其他系統的扇出完成。代價是那一刻在途數
可短暫為 4 ＋ 該動作的請求數（以使用者動作為上界），`PPN-01` 的量測只計扇出端點，構造上不觸發儲存，故不衝突。

### 一之二、與 state 的接合（不就地修改、載入子狀態）

- 每一個扇出結果以函式型更新寫入**新**的 `Map`：`setSystemsByProject(prev => new Map(prev).set(id, result))`
  （`react-hooks/immutability`，`team.md` Code Style）。失敗寫入 `'failed'`。
- **Map 中缺鍵 ＝ 載入中**：清單列以「鍵不存在」渲染既有 `systems-loading` 子狀態，不另設 `queued` 狀態——排隊中與在途中
  對使用者沒有差別，且不新增狀態就不會有「狀態轉移漏寫」的缺陷面。`PPN-03` 的「第 5、6 列顯示載入子狀態而非『尚無系統』」
  直接由此成立：「尚無系統」只在鍵存在且值為空陣列時渲染。
- 總覽的「未填需求欄位 Σ」與「待補的需求」以「S 個系統的鍵**全部**存在」為完整條件（`BR85.2`、`BR88.3`）；未齊時顯示載入中。
- `PPN-05`（切籤零請求）：籤切換只改 `?tab=`（`replace`），三籤都讀頁面已持有的 state；佇列與 effect 的依賴陣列**不含** tab，
  故切籤不重建佇列。

### 一之三、卸載（`PPN-04`）

effect cleanup 依序做兩件事：`cancelled = true`、`queue.cancel()`。已在途的請求**不中止**（既有抓取函式沒有 `AbortSignal`
參數，`team.md` 的「沿用現有形狀」），其結果被 `cancelled` 旗標丟棄；尚未發出者永不發出。故卸載後的新請求數為 0，
`PPN-04` 的「3 秒內端點 2 總數 ≤ 4」= 卸載前已發出的那一批。

### 一之四、測法與突變

全部在既有 Playwright（`PPN-23`）。計數一律以 `page.on('request')` ＋ `page.on('requestfinished')` ／ `requestfailed` 對
**扇出端點的 URL 樣式**（端點 2：`/api/hierarchy/projects/\d+/systems$`；端點 5、7 各自的樣式）維護在途計數與最大值。

| 判準 | 構造 | 斷言 | 必須紅的突變 |
|---|---|---|---|
| `PPN-01` | 以 API 建 6 個專案；`page.route` 對端點 2 延遲 1 秒 | 在途最大值**恰 4**（不是 ≤4：若實作退化成序列，≤4 會靜默通過） | `enqueue` 改成直接執行（等同 `Promise.all`）→ 6 |
| `PPN-01`（詳情） | 建 3 個系統；端點 5、7 皆延遲 1 秒 | 最大值恰 4 | 同上 |
| `PPN-02` | 同上，記錄請求 URL 序列 | 前 S 個皆為端點 5、系統 id 遞增；後 S 個為端點 7、遞增 | 兩段迴圈對調 → 紅 |
| `PPN-03` | P＝6、第 5、6 個端點 2 延遲 3 秒 | 延遲期間第 5、6 列為載入子狀態；最終 6 列皆為「N 個系統」 | `slice(0, 4)` → 第 5、6 列缺 |
| `PPN-04` | P＝8、端點 2 延遲 2 秒，進頁 0.5 秒後導航離開 | 3 秒內端點 2 總數 ≤ 4 | 拿掉 cleanup 的 `cancel()` → 8 |
| `PPN-05` | 載入完成後切籤三次 | `/api/**` 計數不增 | 把 tab 放進 effect 依賴 → 紅 |
| `NFR11.100`–`.102` | 見上游量測方式 | pathname 序列／`history.length` | 建立系統後 `navigate` → `NFR11.100` 紅 |

## 二、伺服器查詢形狀（`PPN-06`、`PPN-07`）

### 二之一、可見集合：以 `UNION` 讓兩半各走自己的索引

`BR87.3` 要求兩支函式共用**同一個私有可見性子句**。本站把它定為一個私有函式回傳**一個** `UNION` 選取式，兩支公開函式
都由它組出——謂詞只有一份，而查詢形狀能讓 `PPN-07` 的索引真的被用到：

```text
# membership_service.py（示意）
def _visible_project_ids_select(user_id):          # 唯一的可見性定義
    member_half = select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
    owner_half = select(Project.id).where(
        Project.owner_user_id == user_id,
        ~exists().where(ProjectMember.project_id == Project.id))
    return union(member_half, owner_half)
def visible_project_ids(db, *, user_id):           # 1 條 SQL
    sub = _visible_project_ids_select(user_id).subquery()
    return sorted(r[0] for r in db.execute(select(sub.c[0])))
def is_project_visible(db, *, project_id, user_id): # 1 條 SQL
    sub = _visible_project_ids_select(user_id).subquery()
    return db.execute(select(sub.c[0]).where(sub.c[0] == project_id)).first() is not None
```

**為什麼不用 `OR` 寫成單一 `WHERE`**：`WHERE EXISTS(成員列) OR (擁有者 AND NOT EXISTS(...))` 是以 `projects` 為驅動表，
逐列探測唯一索引——成本隨**全部專案數**線性增加，新索引 `ix_project_members_user_id` 永遠用不上。拆成 `UNION` 後，
成員那一半以 `user_id` 為條件從 `project_members` 出發（新索引）、擁有者那一半走 `ix_projects_owner_user_id`
（`schema_rbac.sql:353`）、`NOT EXISTS` 走 `uq_project_members_project_user`（`project_id` 前導）。`is_project_visible`
把 `project_id` 條件放在外層，PostgreSQL 會把它推入兩個分支，成員那一半因而變成 `(project_id, user_id)` 的唯一索引探測。

**如實記載**：索引是否被選用由 planner 依表大小決定，小表時選 seq scan 是**正確**行為，故本站**不設** `EXPLAIN` 斷言
（在 SQLite 測試庫上也無意義）。`PPN-07` 的可判定部分是「索引存在於 DDL、ORM 與既有資料庫」，見 `logical-components.md` §三。

### 二之二、兩支列舉端點的語句數（`PPN-06`）

| 端點 | 語句序列（與 P／S 無關） |
|---|---|
| 專案清單 | `K2 view` 判定（`list_projects_by_ids` 第一行）→ 可見 id 的 `UNION`（1 條）→ `SELECT … FROM projects WHERE id IN (…) ORDER BY id`（1 條；**可見集合為空時不發**，直接回 `[]`，避免 `IN ()`） |
| 系統清單 | `K2 view`（`project_exists` 第一行）→ 存在檢查（1 條）→ `is_project_visible`（1 條）→ `K2 view`（`list_systems_unscoped` 第一行）→ `SELECT … FROM systems WHERE project_id = ? ORDER BY id`（1 條） |

`K2` 判定本身發幾條語句由 `services.rbac.user_can` 決定（本站未展開），但它與 P、S 無關，故不影響「P＝1 與 P＝8 相等」。
空集合短路只影響 P＝0，`PPN-06` 比較的是 P＝1 與 P＝8，兩者都走 `IN`。

**測法**：`backend/tests/test_project_visibility_queries.py`（新檔）在 `setUp` 以 `event.listen(engine, "before_cursor_execute", fn)`
掛計數器、`tearDown` 以 `event.remove` 卸除（`PPN-06` 的清除端）。每案先建資料、**呼叫一次暖身**（排除首次 lazy 載入），
再歸零計數後打端點。斷言：P＝1 與 P＝8 的計數相等；S＝1 與 S＝8 的計數相等。

| 必須紅的突變 | 結果 |
|---|---|
| `list_visible_projects` 改為對每個候選專案呼叫 `is_project_visible` | P＝8 比 P＝1 多 7 條 → 紅 |
| `list_projects_by_ids` 改為逐 id `db.get(Project, pid)` | 同上 |
| 系統清單改為逐系統查詢欄位或子物件（lazy load） | S＝8 比 S＝1 多 → 紅 |

## 三、上限 4 的定位與連線池（帶入項 nfr-requirements `R-05`，改寫上游 §二之一 的說法）

上游把 4 寫成由連線池「確認」的數字。本站更正其**定位**，數值不變：

- **4 是經驗值，作用是限制「單一使用者一次進頁」的突發**，不是連線池的保護機制。`backend/database.py:37` 的
  `create_engine(db_url)` 未設 pool 參數，採 SQLAlchemy 預設（常駐 5、溢出 10、取連線逾時 30 秒；取得方式：SQLAlchemy
  文件的預設值，本站未讀安裝版原始碼），且 backend 為單一 uvicorn 進程，故**全體使用者共用 15 條連線**。
- **耗盡條件**：每位使用者扇出期間在途最多 5（佇列 4 ＋ `Layout` 的待確認改選查詢 1），**3 位使用者同時進入系統數多的專案**
  即可佔滿 15 條；第 4 位的任何請求（含登入以外的所有 API）會等待連線，超過 30 秒則失敗。上限 4 或 8 都改變不了這件事——
  只改變需要幾位使用者同時進頁。
- **本站不改池設定**：改 `pool_size` 是部署層的決定（影響 PostgreSQL 的 `max_connections` 預算），不屬本單元；本 repo 也
  沒有連線等待的量測。此限制記為已知代價，與 `performance-requirements.md` §三 的「不設硬上界」並列在核可關卡揭露。

## 四、不做的事（沿用上游，不重述理由）

前端快取清單、批次端點、毫秒級延遲目標、首屏與 bundle 預算——理由見 `performance-requirements.md` §五。

## 五、本檔各節與需求的對應

| 需求 | 本檔落點 |
|---|---|
| `PPN-01` | §一之一（常數與佇列）、§一之四（測法）、§三（定位更正） |
| `PPN-02` | §一之一（兩段入列、FIFO） |
| `PPN-03` | §一之二（缺鍵＝載入中、不截斷） |
| `PPN-04` | §一之三 |
| `PPN-05` | §一之二 末點 |
| `PPN-06` | §二之二 |
| `PPN-07` | §二之一（查詢形狀使索引可被用到）；DDL／遷移落點見 `logical-components.md` §三 |
| `NFR11.100`–`.102` | §一之四 末列（量測方式沿用上游） |
| 帶入項 functional-design `R-04` | §一之一（優先序與不進佇列者） |
| 帶入項 nfr-requirements `R-05` | §三 |
