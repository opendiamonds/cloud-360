# 技術選型 — `U19 membership-service`

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


## 一、技術選型增量：一項，而它是 repo 的第一次

| 層 | 採用 | 本單元的增量 |
|---|---|---|
| 語言／框架 | Python／FastAPI（既有） | **零** |
| ORM | SQLAlchemy 2.x（既有） | **一項：`with_for_update()`** —— 見 §二 |
| 驅動 | `psycopg`(v3)（既有） | **零** |
| 資料庫 | PostgreSQL（既有服務 `db`） | **零**——兩張表由 `U18` 交付 |
| 測試 | `unittest` ＋ `hypothesis`（既有，**非 pytest**） | **零新套件**；但新增兩種測試形狀，見 §三 |
| 部署 | 既有 `deploy/` compose | **零新環境變數** |

**不新增任何 Python 套件。**

## 二、`with_for_update()`：repo 的第一個列鎖

| 事實 | 取得方式 |
|---|---|
| `with_for_update` 全樹命中數 **0** | grep |
| 隔離等級為 PostgreSQL 預設 **READ COMMITTED** | `backend/database.py:37` 逐字 `engine = create_engine(db_url)`，無 `isolation_level` |
| `SessionLocal` 為全域共用的 `autocommit=False, autoflush=False` | `backend/database.py:38` |

`[N1]`=A 要求在成員變更前鎖住父 `projects` 列。SQLAlchemy 2.x 的
`select(Project).where(...).with_for_update()` 即為它，**不需要新套件、不需要改
engine 設定、不需要改 `SessionLocal`**（`NFR12.5`）。

**它是零前例，所以它需要自己的測試**（`NFR12.4`）——而這一點不能只靠「記得寫」：
`unit-of-work.md` 對 `U22` 已記過「一個 flaky 的併發測試等於沒有測試」，
且 `playwright.config.ts:17` 與 `ui-regression` 都容忍 flaky。故本單元的併發測試
**必須以 barrier 釘住交錯順序，不得以 `sleep` 製造**。

### 一個會讓這條鎖在測試中無聲失效的陷阱，寫下來以免重踩

`backend/tests/helpers.py` 在任何 DB import 之前把驅動換成 in-memory SQLite。
本站**實測**了兩件事，而第二件比第一件危險得多：

| 實測 | 結果 |
|---|---|
| 原生 SQLite 執行 `SELECT ... FOR UPDATE` | **語法錯誤**（逐字 `near "FOR": syntax error`） |
| SQLAlchemy 對 SQLite dialect 編譯 `select(...).with_for_update()` | **靜默丟掉該子句**——編譯結果為 `SELECT projects.id FROM projects WHERE projects.id = ?`，**沒有** `FOR UPDATE`，且**不報錯** |

**所以危險不是「測試會失敗」，而是「測試會通過而鎖根本不存在」。**
在既有 SQLite 路徑上寫一個併發測試，它會綠燈——因為 SQLAlchemy 把鎖拿掉了，
而兩個「交易」在 in-memory SQLite 的整庫鎖之下本來就不會真的並行。
這正是本 repo 反覆踩到的那種形狀：**違反後全綠**。

故本單元的併發測試**必須**走真實 PostgreSQL；把它放在 SQLite 路徑上
比不寫它更糟，因為它會產生一個假的覆蓋證據。

`U5` 已為此建立了載體：`ci.yml` 的 `memory-schema` job（真實 `pgvector/pgvector:pg18`
service container），而 `U18` 已在同一個 job 內加過第二個步驟。
**本單元的併發測試應沿用同一個 job 的形狀**；是擴充該 job 或新增一個，
由 `code-generation` 決定，**本站不預選**。記為 `OPEN-N19-5`。

## 三、兩種新的測試形狀（零新套件，但形狀是新的）

| 形狀 | 對象 | 為什麼不能用既有形狀 |
|---|---|---|
| **併發測試（真實 PG ＋ barrier）** | `[N1]`=A 的鎖 | SQLite 不支援 `FOR UPDATE`（見上）；`sleep` 製造的交錯會 flaky |
| **property-based 測試（`hypothesis`）** | `selectSuccessor` 的**排列不變性** | 這是 ADR-0006 的 hard constraint 在本 intent 的**第一個**真正落點。前三個單元都是 DDL 故判 N/A；本單元有純函式故它是 blocking |

`team.md` 已記載 repo 既有 13 個 `@given` 皆落在純函式模組——`selectSuccessor`
的形狀與它們一致，故 PBT 是**沿用既有實踐**而非新引入。

## 四、不採用的選項（逐項附理由）

| 不採用 | 理由 |
|---|---|
| `SERIALIZABLE` 隔離 | 會為子集引入第二種 session 形狀（既有 `SessionLocal` 全域共用），並需要重試迴圈與其測試 |
| deferred constraint trigger | **與既有資料正面衝突**：每個既有專案的 `project_members` 今天都是零列（`reliability-requirements.md` §三），該 trigger 會讓任何碰到既有專案的交易失敗 |
| 建 ORM model | **不適用本單元**——兩張表的 model 由誰建屬 `U18`／`U20` 的範圍；本單元是服務層，讀寫經由 session 與既有 model 機制。若 `U19` 的實作需要 model，它必須逐條對齊 `U18` DDL 的全部約束（`U7` 那輪的教訓） |
| 快取 per-project 角色 | 會引入「權限已撤銷但快取未失效」的窗口，而撤銷正是本單元的核心功能（`performance-requirements.md` §一） |
| 引入 metrics／tracing 套件 | repo 無既有管線；屬獨立工具鏈決策，不由本單元夾帶（`observability-requirements.md` §四） |
