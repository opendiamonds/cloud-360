# 安全需求 — `U19 membership-service`

> 本單元是 `service`，故五個 NFR 類別**全部適用**（前三個 `spec` 單元只有 security）。
>
> **本站引入新的 parent id `NFR12`，理由先寫在這裡。** 上游 `requirements.md` 的
> `NFR1`–`NFR11` 逐一讀過（`:400`／`:430`／`:482`／`:500`／`:510`／`:520`／`:531`／
> `:537`／`:547`／`:553`／`:563`），**沒有一條是關於 per-project 授權、成員關係或
> 其併發正確性**——它們分別涵蓋意圖識別準確率、上下文保留率、首字回應時間、狀態
> 外部化、WebSocket 契約閘門、記憶 schema 隔離、episodic 保存稽核、部署設定完整性、
> 成本、路由模型可替換性、頁面切換次數。`NFR12` 在該檔的命中數為 **0**（實測）。
>
> 故本單元的 NFR 是**本站新增**而非承接，並**指派回補**（見 `traceability.json`
> 的 `OPEN-N19-1`）。不把它們硬掛到某個不相干的 parent 之下——那會讓追溯表看起來
> 有上游依據而實際沒有。

## 〇、上游依據

| 上游產出 | 本站用到它的什麼 |
|---|---|
| `functional-spec.md`（本單元） | §2.1–§2.9 九條工作流程；§三 狀態機；§四 `[FD1]`=A 的對齊修正；§八 ADR-0006 四面向的三欄對照 |
| `rules.md`（本單元） | 29 條規則，特別是 `BR1.1`–`BR1.6`（授權模型）、`BR2.1`–`BR2.3`（守門）、`BR6.1`–`BR6.4`（既有端點擴充） |
| `requirements.md` | `FR12.0`–`FR12.6b`；`NFR1`–`NFR11` 逐一讀過，**無一涵蓋本單元** |
| `contract-summary.md` | 契約 `K-16` 的 `authorization_model` 全段、`existing_endpoint_extension`、`auditing`、`retry_and_idempotency` |
| `codekb/chiton/technology-stack.md` | 既有技術棧；`database.py:37` 的 `create_engine` 未設 `isolation_level`（本站實讀複驗） |

## 一、本站的核心定案：`[N1]`=A 關掉 `BR2.1` 的併發繞過

### 這是實地查證出來的缺陷，不是假設

| 查證項 | 結果 | 取得方式 |
|---|---|---|
| 隔離等級 | **READ COMMITTED**（PostgreSQL 預設） | `backend/database.py:37` 逐字 `engine = create_engine(db_url)`，**無 `isolation_level` 參數** |
| repo 是否用過列鎖 | **零前例** | `with_for_update` 全樹零命中 |
| 上游是否定過本單元的併發行為 | **沒有** | `requirements.md` 的併發條款是 `FR13.1`／`FR13.2`（**agent 進度事件**的隔離）；`K-16` 只為**邀請**定了「單一交易」 |

**競態軌跡**：某專案有兩位管理者 `A`／`B`；`A` 降 `B`、`B` 同時降 `A`。
兩個交易各自讀到管理者數 2 → 都判定「移除後剩 1」→ 都放行 → 各自更新**不同列** →
快照隔離不報寫寫衝突（PostgreSQL 只在**同一列**上報）→ commit 後**管理者數 = 0**。
同一軌跡也適用於「兩位管理者同時自我移出」與「兩個停用請求同時命中同一專案的兩位管理者」。

### 定案內容

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR12.1`** | 任何成員關係變更（`inviteMember`／`removeMember`／`changeRole`／自動改選）在交易開始時先鎖住該 `projects` 列 | 四條路徑的程式中都有該鎖；缺任一條即不合格 |
| **`NFR12.2`** | 鎖的對象是**父 `projects` 列**，不是 `project_members` 的任何一列 | 鎖語句以 `projects` 為標的 |
| **`NFR12.3`** | `assertCanDeactivate` **不取鎖** | 該方法的程式中無鎖語句 |
| **`NFR12.4`** | 併發測試以 barrier 釘住交錯順序，**不得以 `sleep` 製造** | 測試中無 `sleep`／`time.sleep` |
| **`NFR12.5`** | 不改 `SessionLocal` 的隔離等級 | `database.py` 的 `create_engine`／`sessionmaker` 呼叫的 diff 為空 |

### 為什麼鎖父列而不是子列（`NFR12.2` 的理由）

**鎖子列擋不住這個競態**——兩個交易改的本來就是不同子列，鎖它們不會互相阻塞。
鎖父 `projects` 列才能把「對同一專案的成員變更」序列化，而它的語意恰好最窄：
只序列化同一專案，不同專案的成員變更仍可並行。

### 為什麼 `assertCanDeactivate` 不取鎖（`NFR12.3` 的理由）

它是**跨專案**的唯讀掃描。取鎖會讓一次停用請求鎖住該使用者的**全部**專案，
把一個管理者動作變成一個廣域鎖。它的回傳是**那一刻**的事實；
真正的保護在被 `NFR12.1` 的鎖保護的寫入路徑上，不在這個唯讀查詢上。

**誠實的代價**：`assertCanDeactivate` 回「通過」之後、既有端點寫入 `is_active` 之前，
理論上仍有一個窗口讓另一個交易改變該使用者的管理者身分。這個窗口的後果是
**停用一個本應被擋下的帳號**，而它無法以本機制關閉——關閉它要把停用端點整支
納入同一個鎖範圍，而那會跨越 `U19` 與既有 `user_router` 的邊界。記為 `OPEN-N19-2`。

### 為什麼不選另外三個（逐項，非偏好）

| 未選項 | 不選的具體理由 |
|---|---|
| `SERIALIZABLE` ＋ 重試 | 既有 `SessionLocal`（`database.py:38`）是全域共用的 `autocommit=False, autoflush=False`；為子集改隔離等級會引入**兩種 session 形狀**，而重試迴圈本身也需要測試。正確性不輸，複雜度明顯較高 |
| 資料庫 deferred constraint trigger | **與既有資料正面衝突**：目前每一個既有專案的 `project_members` 都是**零列**（審查 `R-02` 的 Critical），故該 trigger 會讓**任何**碰到既有專案的交易失敗，直到回填完成為止 |
| 接受競態 | `BR2.1` 是 `[FD1]`=A 的全部理由。一條在併發下不成立的不變量比死碼更糟——**它看起來成立** |

## 二、`[N2]`=A 拒絕事件的痕跡

`[N2]`=A 的兩條需求**宣告在 `observability-requirements.md` §一**（log 屬觀測載體），
本節只記它們的**安全理由**，不重複宣告——避免同一個 id 有兩個宣告處：

| id（宣告處見 `observability-requirements.md`） | 它在安全面的意義 |
|---|---|
| `NFR12.6`（WARN 級結構化 log，四個欄位） | 授權拒絕是**安全相關事件**；沒有它，反覆的越權嘗試不留任何痕跡 |
| `NFR12.7`（不寫入 `reselection_events`、不新增表） | 把拒絕混入稽核表會讓**使用者可見的**變更紀錄被安全事件淹沒，而 `AC12.2.2` 的讀者是使用者不是維運者 |

**與 `BR5.2` 不衝突，理由寫明**：`BR5.2` 禁止的是**稽核列**只寫 `logger.info`
（因為 `AC12.2.2` 要使用者看得到）。**拒絕不是稽核列**——`reselection_events` 的
`cause` 只有 `auto_reselection` 與 `manual_role_change`，沒有「被拒」這一類。

**選 A 的理由**：拒絕是**高頻事件**（每個非成員的每次嘗試都算一次），寫進資料庫會讓
成員詳情頁的變更紀錄查詢被無關列拖慢，並製造第三種欄位語意（`BR5.4` 已有兩種）。
**殘留限制如實記載**：拒絕紀錄 **UI 讀不到**，而目前沒有任何 AC 要求它可見。

`OPEN-P4`（`U18` 指派給本單元的 `H-8`）由本站**關閉**。

## 三、ADR-0006 四面向：本站的增量

逐格對照上游 `components.md:863`–`:871` 與本單元 `functional-spec.md` §八的三欄表。

| 面向 | 本站的增量 |
|---|---|
| **IAM** | **`NFR12.1`–`NFR12.5` 是 `BR2.1` 在併發下仍然成立的前提。** 沒有它，授權不變量只在單執行緒下為真——而這是一個 IAM 缺陷，不是效能問題 |
| **Encryption** | **無增量**（與 `functional-spec.md` §八相同）：本單元不經憑證／token／金鑰。上游為此面點名的落點是 `McpBridge`（`U21`） |
| **Network exposure** | **無新增暴露面**：零新進程、零新監聽埠（`embedded`）。既有端點的三道檢查次序由 `BR6.1` 承載 |
| **Audit logging** | **`NFR12.6`／`NFR12.7` 補上拒絕那一面**，並明寫它與稽核列（`BR5.1`–`BR5.6`）是**不同載體**。`OPEN-P4` 關閉 |

**PBT 判定：適用且 blocking**（承 `functional-spec.md` §八）。作用對象 `selectSuccessor`，
可失敗性質為**排列不變性**。**`[N3]`=C 的等價測試不是 PBT 的作用對象**——它需要
資料庫，故以明確案例驗證而非生成器。
